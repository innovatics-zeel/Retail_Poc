import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv

from db import get_connection
from llm_config import llm
from utils.history import format_history_for_prompt

load_dotenv()

_TREND_SYSTEM_PROMPT = """
You are a senior fashion retail analyst. Give sharp, executive-ready trend answers.

DATA FIELDS:
- momentum_score: composite trend signal between -1.0 (max decline) and +1.0 (max growth).
  CRITICAL: This is a DECIMAL, not a percentage. -0.874 means -0.874, NOT -87.4%.
- trend_direction: 'Rising', 'Stable', or 'Falling' — the primary signal.
- lifecycle_stage: 'emerging', 'plateau', 'declining'
- attr_key: the attribute type (pattern, material, color_family, fit, neck_type, sleeve_type)

OUTPUT FORMAT:
1. One sentence key finding (bold).
2. A tight markdown table — 2 to 5 rows based on what makes sense. Don't pad.
3. One sentence business action with key numbers bolded.

TABLE RULES:
- 2–5 rows. Use judgment — show only rows that directly answer the question.
- For "declining" questions: pick rows with LOWEST (most negative) momentum_score.
- For "rising/trending" questions: pick rows with HIGHEST momentum_score AND trend_direction='Rising'.
- For "cross-channel" questions: show the SAME attr_value on both Amazon and Nordstrom — 2 rows per attribute.
  Never show the same PATTERN+CHANNEL pair twice.
- Plain text only inside cells — no ** markers inside cells.
- Column headers: attr_value→PATTERN, platform→CHANNEL, trend_direction→TREND, lifecycle_stage→STAGE.
- VELOCITY column: copy the exact momentum_score decimal. e.g. momentum_score=-0.874 → VELOCITY=-0.874.
  NEVER multiply by 100. NEVER add a % sign. -0.874 is correct. -87.4% is WRONG.
- If only 1–2 rows exist for the question, show only those rows. Do not pad with unrelated rows.
- Never invent numbers.

CROSS-CHANNEL OPPORTUNITY RULE (CRITICAL):
A real cross-channel opportunity ONLY exists when one channel is Rising and the other is Falling or Stable.
If BOTH channels for a pattern show trend_direction='Falling' or both show 'Stable', there is NO opportunity.
In that case, state clearly: "No cross-channel opportunity exists in the current data — all patterns are declining on both channels."
Then show the patterns with the LARGEST absolute gap (biggest difference in momentum_score) as a relative comparison, NOT as an investment signal.
NEVER use "invest", "premium", or "push" language when both channels are Falling.

EXAMPLE — declining fastest:
**Short Sleeve is in the steepest decline across both channels.**
| PATTERN | CHANNEL | VELOCITY | TREND |
|---------|---------|---------|-------|
| Short Sleeve | Amazon | -0.49 | Falling |
| Short Sleeve | Nordstrom | -0.61 | Falling |
Cut Short Sleeve from the next buy cycle — **-0.61** on Nordstrom confirms structural, not seasonal decline.

EXAMPLE — rising:
**Cartoon print is the only rising pattern right now, exclusively on Amazon.**
| PATTERN | CHANNEL | VELOCITY | STAGE |
|---------|---------|---------|-------|
| Cartoon | Amazon | +0.24 | emerging |
Invest in **Cartoon** prints on Amazon — the only pattern with positive momentum in the current data.

EXAMPLE — cross-channel, no real opportunity (both channels Falling):
**No cross-channel opportunity exists — Graphic is declining on both Amazon and Nordstrom.**
| PATTERN | CHANNEL | VELOCITY | TREND |
|---------|---------|---------|-------|
| Graphic | Amazon | -0.595 | Falling |
| Graphic | Nordstrom | -0.500 | Falling |
Both channels are in decline — reduce Graphic exposure rather than reallocating between channels.

EXAMPLE — cross-channel, real opportunity (one channel Rising):
**Crew Neck leads on Amazon while Nordstrom has not picked it up yet.**
| PATTERN | CHANNEL | VELOCITY | TREND |
|---------|---------|---------|-------|
| Crew Neck | Amazon | +0.26 | Rising |
| Crew Neck | Nordstrom | -0.31 | Falling |
**+0.57 momentum gap** — push Crew Neck on Amazon while evaluating Nordstrom assortment.
""".strip()

# Balanced dataset: all Rising/Stable + top 15 Falling, filtered by attr_key when specified
_TREND_SCORES_QUERY = """
WITH aggregated AS (
    SELECT
        ts.attr_value                                                                AS pattern,
        ts.attr_key,
        ts.platform,
        -- Use dominant row (most reviews) for ALL signals — keeps momentum & direction consistent
        (array_agg(ts.momentum_score   ORDER BY ts.review_count DESC NULLS LAST))[1] AS momentum_score,
        SUM(ts.review_count)                                                         AS review_count,
        (array_agg(ts.avg_rating       ORDER BY ts.review_count DESC NULLS LAST))[1] AS avg_rating,
        SUM(ts.product_count)                                                        AS product_count,
        (array_agg(ts.trend_direction  ORDER BY ts.review_count DESC NULLS LAST))[1] AS trend_direction,
        (array_agg(ts.lifecycle_stage  ORDER BY ts.review_count DESC NULLS LAST))[1] AS lifecycle_stage,
        (array_agg(ts.retailer_action  ORDER BY ts.review_count DESC NULLS LAST))[1] AS retailer_action
    FROM trend_scores ts
    WHERE 1=1 {attr_filter}
    GROUP BY ts.attr_value, ts.attr_key, ts.platform
),
rising_stable AS (
    SELECT * FROM aggregated
    WHERE trend_direction IN ('Rising', 'Stable')
    ORDER BY momentum_score DESC NULLS LAST
),
declining AS (
    SELECT * FROM aggregated
    WHERE trend_direction NOT IN ('Rising', 'Stable')
    ORDER BY momentum_score ASC NULLS LAST
    LIMIT 15
)
SELECT * FROM rising_stable
UNION
SELECT * FROM declining
ORDER BY momentum_score DESC NULLS LAST
"""

# Maps question keywords → attr_key value in trend_scores
_ATTR_KEY_MAP = [
    (re.compile(r'\bpattern', re.I),                              'pattern'),
    (re.compile(r'\b(material|fabric|cotton|polyester|nylon|silk|wool|linen|elastane|spandex)\b', re.I), 'material'),
    (re.compile(r'\bcolor',   re.I),                              'color_family'),
    (re.compile(r'\bfit\b',   re.I),                              'fit'),
    (re.compile(r'\bneck\b',  re.I),                              'neck_type'),
    (re.compile(r'\bsleeve\b',re.I),                              'sleeve_type'),
]

# Canonical names — maps any variant (lowercase key) → display name
# Handles Amazon CamelCase vs Nordstrom lowercase and known aliases
_ATTR_CANONICAL: dict[str, str] = {
    # pattern
    "graphic print":        "Graphic",
    "graphic":              "Graphic",
    "solid plain colored":  "Solid",
    "solid":                "Solid",
    "floral":               "Floral",
    "striped":              "Striped",
    "printed":              "Printed",
    "embroidered":          "Embroidered",
    "lace":                 "Lace",
    "cartoon":              "Cartoon",
    "camouflage":           "Camouflage",
    "plaid":                "Plaid",
    "sequin":               "Sequin",
    "letter print":         "Letter Print",
    # neck_type
    "crewneck":             "Crew Neck",
    "crew neck":            "Crew Neck",
    "v-neck":               "V-Neck",
    "v neck":               "V-Neck",
    "scoop neck":           "Scoop Neck",
    "off-the-shoulder":     "Off Shoulder",
    "off shoulder neck":    "Off Shoulder",
    "halter":               "Halter Neck",
    "halter neck":          "Halter Neck",
    "one-shoulder":         "One Shoulder",
    "one shoulder neck":    "One Shoulder",
    "strapless":            "Strapless",
    "strapless/tube":       "Strapless",
    "square neck":          "Square Neck",
    "mock neck":            "Mock Neck",
    "henley":               "Henley Neck",
    "henley neck":          "Henley Neck",
    # sleeve_type
    "short sleeve":         "Short Sleeve",
    "long sleeve":          "Long Sleeve",
    "sleeveless":           "Sleeveless",
    "cap sleeve":           "Cap Sleeve",
    "split sleeve":         "Split Sleeve",
    # fit
    "classic fit":          "Classic Fit",
    "classic":              "Classic Fit",
    "slim fit":             "Slim Fit",
    "slim":                 "Slim Fit",
    "regular fit":          "Regular Fit",
    "regular":              "Regular Fit",
    "relaxed fit":          "Relaxed Fit",
    "relaxed":              "Relaxed Fit",
    "fitted":               "Fitted",
    "a-line":               "A-Line",
    "oversized":            "Oversized",
    "tailored":             "Tailored",
    "sheath":               "Sheath",
}


def _canonical(val: str) -> str:
    """Return the canonical display name for an attr_value."""
    if not val:
        return val
    return _ATTR_CANONICAL.get(val.strip().lower(), val.strip())


def _detect_attr_key(question: str) -> str | None:
    for pattern, key in _ATTR_KEY_MAP:
        if pattern.search(question):
            return key
    return None


def _fetch_trend_data(attr_key: str | None = None) -> list[dict]:
    if attr_key:
        filter_clause = f"AND ts.attr_key = '{attr_key}'"
    else:
        filter_clause = ""
    query = _TREND_SCORES_QUERY.replace("{attr_filter}", filter_clause)
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(query)
            cols = [d[0] for d in cur.description]
            rows = [dict(zip(cols, row)) for row in cur.fetchall()]

    # Normalize attr_value to canonical name so Amazon/Nordstrom variants merge correctly
    for row in rows:
        row["pattern"] = _canonical(row.get("pattern") or "")

    # Dedup here by (pattern, platform) — keep highest momentum_score (first, since sorted DESC)
    seen: set = set()
    deduped: list[dict] = []
    for row in rows:
        key = (row.get("pattern"), (row.get("platform") or "").lower())
        if key not in seen:
            seen.add(key)
            deduped.append(row)

    return deduped


def _calculate_confidence(data: list[dict]) -> float:
    if not data:
        return 0.0
    total = sum(int(row.get("review_count") or 0) for row in data)
    if total > 5000:
        return 0.95
    if total > 1000:
        return 0.85
    if total > 100:
        return 0.70
    return 0.50


_CROSS_CHANNEL_RE = re.compile(
    r'\b(cross.channel|both.channel|amazon.*nordstrom|nordstrom.*amazon|gap|compar)\b',
    re.I,
)
_BOTH_DECLINING_RE = re.compile(
    r'\b(both.channel|across.both)\b.*\b(declin|falling|drop|worst|fastest)\b'
    r'|\b(declin|falling|drop|worst|fastest)\b.*\b(both.channel|across.both)\b',
    re.I,
)
_RISING_RE = re.compile(
    r'\b(rising|trending|trend|gaining|fastest.*rise|what.*trend)\b',
    re.I,
)
_DECLINING_RE = re.compile(
    r'\b(declining|falling|slowest|fastest.*declin|drop|worst)\b',
    re.I,
)


def _is_cross_channel(question: str) -> bool:
    return bool(_CROSS_CHANNEL_RE.search(question))


def _is_rising_question(question: str) -> bool:
    return bool(_RISING_RE.search(question)) and not bool(_DECLINING_RE.search(question))


def _build_both_declining_answer(data: list[dict]) -> str | None:
    """
    For 'declining fastest across both channels' questions:
    find patterns Falling on BOTH Amazon and Nordstrom, return a hardcoded answer.
    Returns None if no such patterns exist.
    """
    from collections import defaultdict
    by_pattern: dict[str, dict] = defaultdict(dict)
    for row in data:
        pat = row.get("pattern")
        plat = (row.get("platform") or "").lower()
        by_pattern[pat][plat] = row

    # Keep only patterns Falling on BOTH channels
    both_falling = []
    for pat, channels in by_pattern.items():
        amz = channels.get("amazon")
        nor = channels.get("nordstrom")
        if amz and nor:
            if amz.get("trend_direction") == "Falling" and nor.get("trend_direction") == "Falling":
                # Use the more negative of the two as the sort key
                worst = min(
                    float(amz.get("momentum_score") or 0),
                    float(nor.get("momentum_score") or 0),
                )
                both_falling.append((worst, amz, nor))

    if not both_falling:
        return None

    both_falling.sort(key=lambda x: x[0])  # most negative first
    top = both_falling[:3]

    lines = ["**These patterns are declining fastest on both Amazon and Nordstrom:**\n"]
    lines.append("| PATTERN | CHANNEL | VELOCITY | TREND |")
    lines.append("|---------|---------|----------|-------|")
    for _, amz_row, nor_row in top:
        pat = amz_row.get("pattern")
        lines.append(f"| {pat} | Amazon | {amz_row['momentum_score']} | Falling |")
        lines.append(f"| {pat} | Nordstrom | {nor_row['momentum_score']} | Falling |")

    worst_pat = top[0][1].get("pattern")
    worst_vel = top[0][0]
    lines.append(
        f"\nCut **{worst_pat}** from the next buy cycle — "
        f"velocity **{worst_vel}** on both channels confirms structural, not seasonal decline."
    )
    return "\n".join(lines)


def _filter_cross_channel(data: list[dict]) -> tuple[list[dict], str | None]:
    """Keep only attr_values that appear on BOTH channels AND have at least one non-Falling channel."""
    from collections import defaultdict
    channel_data: dict[str, dict] = defaultdict(dict)
    for row in data:
        pat = row.get("pattern")
        plat = (row.get("platform") or "").lower()
        channel_data[pat][plat] = row

    both = {p for p, chans in channel_data.items() if "amazon" in chans and "nordstrom" in chans}

    if not both:
        only_amazon = sorted(p for p, chans in channel_data.items() if "nordstrom" not in chans)
        only_nordstrom = sorted(p for p, chans in channel_data.items() if "amazon" not in chans)
        warning = (
            "No attribute appears on BOTH Amazon and Nordstrom in the current data. "
            f"Amazon-only patterns: {only_amazon[:5]}. Nordstrom-only: {only_nordstrom[:5]}."
        )
        return [], warning

    # Among patterns on both channels, check if at least one has a Rising/Stable channel
    has_opportunity = False
    for pat in both:
        rows = channel_data[pat]
        directions = {r.get("trend_direction") for r in rows.values()}
        if "Rising" in directions or "Stable" in directions:
            has_opportunity = True
            break

    if not has_opportunity:
        # All cross-channel patterns are Falling on both sides
        warning = (
            "All attributes that appear on both Amazon and Nordstrom are currently Falling on BOTH channels. "
            "There is no actionable cross-channel opportunity — both channels are in decline for the same attributes."
        )
        filtered = [row for row in data if row.get("pattern") in both]
        return filtered, warning

    filtered = [row for row in data if row.get("pattern") in both]
    return filtered, None


def _build_cross_channel_table(data: list[dict], all_falling: bool = False) -> str:
    """Hardcoded cross-channel comparison — no LLM, no hallucination."""
    from collections import defaultdict
    by_pattern: dict[str, dict] = defaultdict(dict)
    for row in data:
        pat = row.get("pattern")
        plat = (row.get("platform") or "").lower()
        by_pattern[pat][plat] = row

    # Sort by Amazon momentum DESC (best Amazon performance first)
    sorted_pats = sorted(
        by_pattern.items(),
        key=lambda kv: float((kv[1].get("amazon") or {}).get("momentum_score") or -999),
        reverse=True,
    )

    lines = []
    if all_falling:
        lines.append("**No cross-channel opportunity — all shared attributes are declining on both channels.**\n")
    else:
        lines.append("**Cross-channel momentum comparison — Amazon vs Nordstrom:**\n")

    lines.append("| PATTERN | CHANNEL | VELOCITY | TREND |")
    lines.append("|---------|---------|----------|-------|")

    for pat, channels in sorted_pats:
        amz = channels.get("amazon")
        nor = channels.get("nordstrom")
        if amz:
            lines.append(f"| {pat} | Amazon | {amz['momentum_score']} | {amz.get('trend_direction','—')} |")
        if nor:
            lines.append(f"| {pat} | Nordstrom | {nor['momentum_score']} | {nor.get('trend_direction','—')} |")

    if not all_falling:
        # Find best opportunity: largest gap where Amazon >= Nordstrom
        best_pat, best_amz, best_nor, best_gap = None, None, None, -999.0
        for pat, channels in sorted_pats:
            amz = channels.get("amazon")
            nor = channels.get("nordstrom")
            if amz and nor:
                gap = float(amz["momentum_score"]) - float(nor["momentum_score"])
                if gap > best_gap:
                    best_gap, best_pat, best_amz, best_nor = gap, pat, amz, nor
        if best_pat and best_gap > 0:
            lines.append(
                f"\n**{best_pat}** has the strongest Amazon advantage — "
                f"Amazon {best_amz['trend_direction']} ({best_amz['momentum_score']}) vs "
                f"Nordstrom {best_nor['trend_direction']} ({best_nor['momentum_score']}), "
                f"gap of **+{round(best_gap, 4)}**."
            )
        else:
            lines.append("\nNo pattern shows a clear Amazon advantage over Nordstrom in the current data.")
    else:
        lines.append("\nReduce assortment depth on both channels rather than reallocating between them.")

    return "\n".join(lines)


def _build_rising_answer(rising_rows: list[dict]) -> str:
    """Hardcoded rising answer — only shows Rising rows, no LLM, no hallucination."""
    sorted_rows = sorted(rising_rows, key=lambda r: float(r.get("momentum_score") or 0), reverse=True)
    top = sorted_rows[:5]

    lines = [f"**{top[0]['pattern']} is leading with the strongest rising momentum on {top[0]['platform'].title()}.**\n"]
    lines.append("| PATTERN | CHANNEL | VELOCITY | STAGE |")
    lines.append("|---------|---------|----------|-------|")
    for r in top:
        lines.append(
            f"| {r['pattern']} | {r['platform'].title()} "
            f"| {r['momentum_score']} | {r.get('lifecycle_stage') or '—'} |"
        )

    top_pat = top[0]['pattern']
    top_vel = top[0]['momentum_score']
    top_plat = top[0]['platform'].title()
    lines.append(
        f"\nInvest in **{top_pat}** on {top_plat} — "
        f"velocity **{top_vel}** confirms genuine upward momentum."
    )
    return "\n".join(lines)


def _build_trend_answer(question: str, data: list[dict], chat_history: list) -> str:
    history_ctx = format_history_for_prompt(chat_history, max_messages=2)

    # Strip rows from other attr_keys immediately — every code path below (LLM and hardcoded)
    # must only see the attr_key the question asked about.  This is the first line of defence;
    # _fetch_trend_data(attr_key) is the second (SQL-level).
    detected_key = _detect_attr_key(question)
    if detected_key:
        data = [r for r in data if r.get("attr_key") == detected_key]

    # Deduplicate by (pattern, platform)
    seen: set = set()
    deduped: list[dict] = []
    for row in data:
        key = (row.get("pattern"), row.get("platform"))
        if key not in seen:
            seen.add(key)
            deduped.append(row)
        if len(deduped) >= 10:
            break

    # "Declining across BOTH channels" — hardcoded Python answer, no LLM
    if _BOTH_DECLINING_RE.search(question):
        answer = _build_both_declining_answer(deduped)
        if answer:
            return answer

    # For cross-channel gap/comparison questions: only pass patterns present on BOTH channels
    cross_channel_warning: str | None = None
    if _is_cross_channel(question) and not _BOTH_DECLINING_RE.search(question):
        deduped, cross_channel_warning = _filter_cross_channel(deduped)

    if cross_channel_warning and not deduped:
        return (
            "**No cross-channel opportunity exists in the current data.**\n\n"
            "Each platform carries different attribute values — no attribute appears on both "
            "Amazon and Nordstrom with comparable naming, so a momentum gap cannot be calculated. "
            "This is a data coverage gap, not a neutral signal."
        )

    if cross_channel_warning and deduped:
        # Both channels present but ALL are Falling — hardcoded, no LLM
        return _build_cross_channel_table(deduped, all_falling=True)

    if deduped and _is_cross_channel(question) and not _BOTH_DECLINING_RE.search(question):
        # Has real cross-channel data — hardcoded table, no LLM to hallucinate
        return _build_cross_channel_table(deduped, all_falling=False)

    # For "rising/trending" questions: hardcoded Python — no LLM hallucination
    if _is_rising_question(question):
        rising_rows = [r for r in deduped if r.get("trend_direction") == "Rising"]
        if not rising_rows:
            attr_label = (detected_key or "attribute").replace("_", " ")
            stable_rows = sorted(
                [r for r in deduped if r.get("trend_direction") == "Stable"],
                key=lambda r: float(r.get("momentum_score") or -999),
                reverse=True,
            )
            best = stable_rows[0] if stable_rows else None
            best_note = (
                f" Closest to positive momentum: **{best['pattern']}** "
                f"({best['platform']}, velocity {best['momentum_score']}, Stable)."
                if best else ""
            )
            return (
                f"**No {attr_label} is currently Rising in the data.**\n\n"
                f"All {attr_label} values show Falling or Stable momentum.{best_note}"
            )
        return _build_rising_answer(rising_rows)

    anti_hallucination = (
        "\n\nCRITICAL: Use ONLY the rows above. "
        "Do NOT invent rows for any channel not present in the data. "
        "Never call a Falling or Stable item 'trending' or 'rising'."
    )

    prompt = (
        f"{history_ctx}"
        f"User question:\n{question}\n\n"
        f"Trend data (momentum_score is a decimal -1.0 to +1.0, NOT a percentage):\n"
        f"{json.dumps(deduped, default=str)}"
        f"{anti_hallucination}"
    )
    return llm.generate_response(
        system_prompt=_TREND_SYSTEM_PROMPT,
        user_prompt=prompt,
        temperature=0,
    )


def _call_llm_declining(question: str, data: list[dict], history_ctx: str) -> str:
    prompt = (
        f"{history_ctx}"
        f"User question:\n{question}\n\n"
        f"Trend data (ALL entries below are Falling on both channels — do NOT use invest/push language):\n"
        f"{json.dumps(data, default=str)}\n\n"
        "CRITICAL: Both channels are declining. Show the data table but conclude with a REDUCE/CUT recommendation, "
        "never an invest recommendation."
    )
    return llm.generate_response(
        system_prompt=_TREND_SYSTEM_PROMPT,
        user_prompt=prompt,
        temperature=0,
    )


def run_trend_engine_agent(
    question: str,
    intent_response: dict,
    chat_history: list,
) -> dict:
    try:
        attr_key = _detect_attr_key(question)
        data = _fetch_trend_data(attr_key)

        if not data:
            return {
                "success": False,
                "confidence": 0.0,
                "source": "trend_engine_agent",
                "response": "No trend data is available yet — run predictions first.",
            }

        confidence = _calculate_confidence(data)
        response = _build_trend_answer(
            question=question,
            data=data,
            chat_history=chat_history,
        )

        return {
            "success": True,
            "confidence": confidence,
            "source": "trend_engine_agent",
            "data": data,
            "response": response,
        }

    except Exception as exc:
        return {
            "success": False,
            "confidence": 0.0,
            "source": "trend_engine_agent",
            "response": f"Trend agent failed: {exc}",
        }
