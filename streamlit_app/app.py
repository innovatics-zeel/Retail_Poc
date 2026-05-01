"""
app.py — Innovatics Program 1: Product & Market Intelligence
Run: streamlit run streamlit_app/app.py
"""
import sys
import warnings
warnings.filterwarnings("ignore")

sys.path.insert(0, ".")

import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go

from streamlit_app.db import (
    load_products, get_kpis, attribute_counts,
    price_bands, platform_comparison, top_products,
    color_family_breakdown, save_feedback, data_summary_for_llm,
)

# ── Page config ───────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Innovatics | Market Intelligence",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

PRIMARY  = "#1E3A5F"
ACCENT   = "#2E86AB"
SUCCESS  = "#27AE60"
WARNING  = "#F39C12"
DANGER   = "#E74C3C"
LIGHT_BG = "#F8F9FA"

st.markdown(f"""
<style>
    [data-testid="stAppViewContainer"] {{ background: {LIGHT_BG}; }}
    [data-testid="stSidebar"] {{ background: {PRIMARY}; }}
    [data-testid="stSidebar"] * {{ color: white !important; }}
    .metric-card {{
        background: white; border-radius: 12px; padding: 20px 24px;
        box-shadow: 0 2px 8px rgba(0,0,0,0.08); text-align: center;
    }}
    .metric-value {{ font-size: 2rem; font-weight: 700; color: {PRIMARY}; }}
    .metric-label {{ font-size: 0.85rem; color: #666; margin-top: 4px; }}
    .section-header {{
        font-size: 1.1rem; font-weight: 600; color: {PRIMARY};
        border-bottom: 2px solid {ACCENT}; padding-bottom: 6px; margin-bottom: 16px;
    }}
    .stTabs [data-baseweb="tab-list"] {{ gap: 8px; }}
    .stTabs [data-baseweb="tab"] {{
        background: white; border-radius: 8px 8px 0 0;
        padding: 8px 20px; font-weight: 600;
    }}
    .stTabs [aria-selected="true"] {{
        background: {PRIMARY} !important; color: white !important;
    }}
</style>
""", unsafe_allow_html=True)

# ── Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("## 📊 Market Intelligence")
    st.markdown("**Program 1 — Retail POC**")
    st.markdown("---")

    platform_filter = st.selectbox(
        "Platform", ["All", "nordstrom", "amazon"], key="plt_filter"
    )
    category_filter = st.selectbox(
        "Category", ["All", "mens_tshirts", "womens_dresses"], key="cat_filter"
    )
    st.markdown("---")
    price_range = st.slider("Price Range ($)", 0, 500, (0, 300), key="price_filter")
    st.markdown("---")
    st.caption("Data: Demonstration only · Innovatics © 2026")

# ── Load data ─────────────────────────────────────────────────────────────────
@st.cache_data(ttl=300)
def get_data(platform, category):
    p = None if platform == "All" else platform
    c = None if category == "All" else category
    return load_products(p, c)

df_raw = get_data(platform_filter, category_filter)

df = df_raw.copy()
if not df.empty and "current_price" in df.columns:
    df = df[
        (df["current_price"].isna()) |
        (df["current_price"].between(price_range[0], price_range[1]))
    ]

# ── Header ────────────────────────────────────────────────────────────────────
st.markdown(f"""
<div style='background:{PRIMARY}; padding:20px 28px; border-radius:12px; margin-bottom:24px;'>
    <h1 style='color:white; margin:0; font-size:1.8rem;'>
        📊 Innovatics — Product & Market Intelligence
    </h1>
    <p style='color:#aac; margin:6px 0 0; font-size:0.9rem;'>
        Program 1 · Retail POC · US Apparel Marketplaces
    </p>
</div>
""", unsafe_allow_html=True)

# ── Tabs ──────────────────────────────────────────────────────────────────────
tab1, tab2, tab3, tab4 = st.tabs([
    "📊  Descriptive",
    "💬  Conversational",
    "📈  Predictive",
    "🎯  Recommendations",
])


# ═══════════════════════════════════════════════════════════════════════════════
# TAB 1 — DESCRIPTIVE INTELLIGENCE
# ═══════════════════════════════════════════════════════════════════════════════
with tab1:
    if df.empty:
        st.info("No products in the database yet. Run the scraper first: `python scrape_runner.py`")
        st.stop()

    kpis = get_kpis(df)

    # KPI cards
    c1, c2, c3, c4, c5, c6 = st.columns(6)
    for col, val, label in [
        (c1, f"{kpis['total']:,}",         "Total Products"),
        (c2, f"${kpis['avg_price']}",       "Avg Price"),
        (c3, f"{kpis['avg_rating']} ★",     "Avg Rating"),
        (c4, f"{kpis['total_reviews']:,}",  "Total Reviews"),
        (c5, str(kpis.get("platforms", 0)), "Platforms"),
        (c6, str(kpis.get("brands", 0)),    "Brands"),
    ]:
        col.markdown(f"""
        <div class="metric-card">
            <div class="metric-value">{val}</div>
            <div class="metric-label">{label}</div>
        </div>""", unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # ── Top products ───────────────────────────────────────────
    st.markdown('<div class="section-header">🏆 Top Products</div>', unsafe_allow_html=True)
    r1c1, r1c2 = st.columns(2)

    with r1c1:
        top_rev = top_products(df, by="review_count", n=10)
        if not top_rev.empty:
            fig = px.bar(
                top_rev, x="review_count", y="title",
                orientation="h", color="platform",
                color_discrete_map={"nordstrom": ACCENT, "amazon": WARNING},
                title="Top 10 by Review Count",
                labels={"review_count": "Reviews", "title": ""},
            )
            fig.update_layout(height=380, margin=dict(l=0, r=0, t=40, b=0),
                              yaxis=dict(tickfont=dict(size=10)))
            st.plotly_chart(fig, use_container_width=True)

    with r1c2:
        top_rat = top_products(df, by="rating", n=10)
        if not top_rat.empty:
            fig = px.bar(
                top_rat, x="rating", y="title",
                orientation="h", color="platform",
                color_discrete_map={"nordstrom": ACCENT, "amazon": WARNING},
                title="Top 10 by Rating",
                labels={"rating": "Rating", "title": ""},
            )
            fig.update_layout(height=380, margin=dict(l=0, r=0, t=40, b=0),
                              yaxis=dict(tickfont=dict(size=10)),
                              xaxis=dict(range=[0, 5]))
            st.plotly_chart(fig, use_container_width=True)

    # ── Price & Rating distributions ───────────────────────────
    st.markdown('<div class="section-header">💰 Price & Rating Distribution</div>',
                unsafe_allow_html=True)
    r2c1, r2c2 = st.columns(2)

    with r2c1:
        pb = price_bands(df)
        if not pb.empty:
            fig = px.bar(pb, x="band", y="count",
                         title="Products by Price Band",
                         color="count", color_continuous_scale="Blues",
                         labels={"band": "Price Band", "count": "# Products"})
            fig.update_layout(height=320, showlegend=False,
                              margin=dict(l=0, r=0, t=40, b=0))
            st.plotly_chart(fig, use_container_width=True)

    with r2c2:
        if "rating" in df.columns and df["rating"].notna().any():
            fig = px.histogram(
                df.dropna(subset=["rating"]),
                x="rating", nbins=20,
                title="Rating Distribution",
                color_discrete_sequence=[ACCENT],
                labels={"rating": "Rating", "count": "# Products"},
            )
            fig.update_layout(height=320, margin=dict(l=0, r=0, t=40, b=0))
            st.plotly_chart(fig, use_container_width=True)

    # ── Attribute intelligence ─────────────────────────────────
    st.markdown('<div class="section-header">🎨 Attribute Intelligence</div>',
                unsafe_allow_html=True)

    attr_cols = st.columns(3)
    for idx, (col_name, label) in enumerate([
        ("color_family", "Color Families"),
        ("pattern",      "Top Patterns"),
        ("material",     "Top Materials"),
    ]):
        counts = attribute_counts(df, col_name, top_n=8)
        with attr_cols[idx]:
            if not counts.empty:
                fig = px.bar(counts, x="count", y=col_name,
                             orientation="h", title=label,
                             color_discrete_sequence=[PRIMARY])
                fig.update_layout(height=280, margin=dict(l=0, r=0, t=40, b=0),
                                  yaxis=dict(tickfont=dict(size=10)))
                st.plotly_chart(fig, use_container_width=True)

    attr_cols2 = st.columns(3)
    for idx, (col_name, label) in enumerate([
        ("color",       "Top Colors"),
        ("neck_type",   "Neck Types"),
        ("fit",         "Fit Types"),
    ]):
        counts = attribute_counts(df, col_name, top_n=8)
        with attr_cols2[idx]:
            if not counts.empty:
                fig = px.pie(counts, names=col_name, values="count",
                             title=label,
                             color_discrete_sequence=px.colors.qualitative.Set2)
                fig.update_layout(height=280, margin=dict(l=0, r=0, t=40, b=0))
                st.plotly_chart(fig, use_container_width=True)

    attr_cols3 = st.columns(3)
    for idx, (col_name, label) in enumerate([
        ("sleeve_type", "Sleeve Types"),
        ("size",        "Size Availability"),
        ("gender",      "Gender Split"),
    ]):
        counts = attribute_counts(df, col_name, top_n=8)
        with attr_cols3[idx]:
            if not counts.empty:
                fig = px.bar(counts, x="count", y=col_name,
                             orientation="h", title=label,
                             color_discrete_sequence=[ACCENT])
                fig.update_layout(height=280, margin=dict(l=0, r=0, t=40, b=0),
                                  yaxis=dict(tickfont=dict(size=10)))
                st.plotly_chart(fig, use_container_width=True)

    # ── Platform comparison ────────────────────────────────────
    st.markdown('<div class="section-header">🏪 Platform Comparison</div>',
                unsafe_allow_html=True)
    pc = platform_comparison(df)
    if not pc.empty:
        r4c1, r4c2, r4c3 = st.columns(3)
        with r4c1:
            fig = px.bar(pc, x="platform", y="avg_price",
                         title="Avg Price by Platform", color="platform",
                         color_discrete_map={"nordstrom": ACCENT, "amazon": WARNING})
            fig.update_layout(height=280, showlegend=False,
                              margin=dict(l=0, r=0, t=40, b=0))
            st.plotly_chart(fig, use_container_width=True)
        with r4c2:
            fig = px.bar(pc, x="platform", y="avg_rating",
                         title="Avg Rating by Platform", color="platform",
                         color_discrete_map={"nordstrom": ACCENT, "amazon": WARNING})
            fig.update_layout(height=280, showlegend=False, yaxis=dict(range=[0, 5]),
                              margin=dict(l=0, r=0, t=40, b=0))
            st.plotly_chart(fig, use_container_width=True)
        with r4c3:
            fig = px.bar(pc, x="platform", y="total_reviews",
                         title="Total Reviews by Platform", color="platform",
                         color_discrete_map={"nordstrom": ACCENT, "amazon": WARNING})
            fig.update_layout(height=280, showlegend=False,
                              margin=dict(l=0, r=0, t=40, b=0))
            st.plotly_chart(fig, use_container_width=True)

        st.dataframe(
            pc.rename(columns={
                "platform": "Platform", "products": "Products",
                "avg_price": "Avg Price ($)", "avg_rating": "Avg Rating",
                "total_reviews": "Total Reviews", "brands": "Brands",
            }),
            use_container_width=True, hide_index=True,
        )

    # ── Category × Platform heatmap ───────────────────────────
    st.markdown('<div class="section-header">🗺️ Category × Platform Overview</div>',
                unsafe_allow_html=True)
    heat_df = (
        df.groupby(["platform", "category"])
        .agg(count=("url", "count"), avg_rating=("rating", "mean"),
             avg_price=("current_price", "mean"))
        .round(2).reset_index()
    )
    if not heat_df.empty:
        fig = px.scatter(
            heat_df, x="platform", y="category",
            size="count", color="avg_rating",
            color_continuous_scale="RdYlGn",
            hover_data=["count", "avg_rating", "avg_price"],
            title="Products per Category × Platform  (size = count, colour = avg rating)",
            size_max=60,
        )
        fig.update_layout(height=320, margin=dict(l=0, r=0, t=40, b=0))
        st.plotly_chart(fig, use_container_width=True)

    # ── Brand intelligence ─────────────────────────────────────
    st.markdown('<div class="section-header">🏷️ Brand Intelligence</div>',
                unsafe_allow_html=True)
    brand_df = (
        df.groupby("brand")
        .agg(products=("url", "count"), avg_price=("current_price", "mean"),
             avg_rating=("rating", "mean"), total_reviews=("review_count", "sum"))
        .round(2).reset_index()
        .dropna(subset=["brand"])
        .nlargest(15, "products")
    )
    if not brand_df.empty:
        bc1, bc2 = st.columns(2)
        with bc1:
            fig = px.bar(brand_df, x="products", y="brand", orientation="h",
                         title="Top 15 Brands by Product Count",
                         color_discrete_sequence=[PRIMARY])
            fig.update_layout(height=380, margin=dict(l=0, r=0, t=40, b=0),
                              yaxis=dict(tickfont=dict(size=10)))
            st.plotly_chart(fig, use_container_width=True)
        with bc2:
            fig = px.scatter(brand_df, x="avg_price", y="avg_rating",
                             size="total_reviews", hover_name="brand",
                             title="Brand Positioning: Price vs Rating",
                             labels={"avg_price": "Avg Price ($)",
                                     "avg_rating": "Avg Rating"},
                             color_discrete_sequence=[ACCENT])
            fig.update_layout(height=380, margin=dict(l=0, r=0, t=40, b=0),
                              yaxis=dict(range=[0, 5]))
            st.plotly_chart(fig, use_container_width=True)


# ═══════════════════════════════════════════════════════════════════════════════
# TAB 2 — CONVERSATIONAL INTELLIGENCE
# ═══════════════════════════════════════════════════════════════════════════════
with tab2:
    st.markdown("### 💬 Ask a Market Intelligence Question")
    st.caption("Powered by Claude · Answers grounded in your scraped data")

    SUGGESTED = [
        "Which color families are trending in Men's T-shirts?",
        "How does Nordstrom's pricing compare to Amazon?",
        "Which design features drive top-reviewed T-shirts?",
        "What price range is most common for cotton T-shirts?",
        "Which patterns are most popular in Women's Dresses?",
        "What is the average discount percentage on Nordstrom?",
        "Which brands have the most reviews?",
        "Compare rating distributions between platforms",
        "What materials are common in high-rated dresses?",
        "Which fit type is most common for men's T-shirts?",
    ]

    st.markdown("**Suggested questions:**")
    cols_sug = st.columns(2)
    for i, q in enumerate(SUGGESTED):
        if cols_sug[i % 2].button(q, key=f"sug_{i}", use_container_width=True):
            st.session_state["conv_question"] = q

    st.markdown("---")
    question = st.text_input(
        "Your question:",
        value=st.session_state.get("conv_question", ""),
        placeholder="e.g. Which color families are trending in T-shirts under $50?",
        key="conv_input",
    )

    if st.button("🔍 Ask", type="primary", key="ask_btn") and question.strip():
        with st.spinner("Analysing data and generating answer..."):
            try:
                import anthropic
                from config.settings import settings

                data_ctx = data_summary_for_llm(df)
                client = anthropic.Anthropic(api_key=settings.anthropic_api_key)
                response = client.messages.create(
                    model="claude-sonnet-4-6",
                    max_tokens=1500,
                    system="""You are a senior retail market intelligence analyst at Innovatics.
You have access to scraped US apparel marketplace data stored in a normalized database
(products, product_variants, reviews, brands, categories, colors, sizes, platforms).
Answer questions concisely and specifically, always citing numbers from the data.
Structure your answer with: Key Finding, Supporting Data, Implication.
If the data context does not contain enough information, say so clearly — never hallucinate.
Keep answers under 300 words.""",
                    messages=[{
                        "role": "user",
                        "content": f"Data context:\n{data_ctx}\n\nQuestion: {question}",
                    }],
                )
                answer = response.content[0].text

                st.markdown(f"""
<div style='background:white; border-left:4px solid {ACCENT};
     border-radius:8px; padding:20px; margin-top:16px;'>
    <strong style='color:{PRIMARY}'>Answer</strong><br><br>
    {answer.replace(chr(10), '<br>')}
</div>""", unsafe_allow_html=True)

                st.markdown("**📊 Relevant data snapshot:**")
                snapshot_cols = ["title", "brand", "platform", "category",
                                 "current_price", "rating", "review_count"]
                snapshot_cols = [c for c in snapshot_cols if c in df.columns]
                st.dataframe(
                    top_products(df, by="review_count", n=5)[snapshot_cols],
                    use_container_width=True, hide_index=True,
                )

            except Exception as e:
                st.error(f"Could not connect to Claude API: {e}")
                st.info("Make sure `ANTHROPIC_API_KEY` is set in your .env file.")


# ═══════════════════════════════════════════════════════════════════════════════
# TAB 3 — PREDICTIVE INTELLIGENCE
# ═══════════════════════════════════════════════════════════════════════════════
with tab3:
    st.markdown("### 📈 Predictive Intelligence")
    st.caption("Trend analysis based on scraped data + simulated historical signal")

    if df.empty:
        st.info("No data yet. Run the scraper first.")
    else:
        np.random.seed(42)
        weeks = pd.date_range(end=pd.Timestamp.today(), periods=13, freq="W")

        def _synthetic_series(base: float, trend: float = 0.03, noise: float = 0.05):
            vals = [base * (1 + trend * i + np.random.normal(0, noise)) for i in range(13)]
            return [max(0, v) for v in vals]

        avg_price_now   = float(df["current_price"].dropna().mean()) if "current_price" in df.columns else 50
        avg_rating_now  = float(df["rating"].dropna().mean()) if "rating" in df.columns else 4.0
        avg_reviews_now = float(df["review_count"].fillna(0).mean())

        st.markdown('<div class="section-header">🚀 Review Velocity (Weekly Trend)</div>',
                    unsafe_allow_html=True)
        p1c1, p1c2 = st.columns(2)

        with p1c1:
            rev_series = _synthetic_series(avg_reviews_now * 0.7, trend=0.05, noise=0.08)
            trend_df = pd.DataFrame({"week": weeks, "avg_reviews": rev_series})
            x = np.arange(len(trend_df))
            m, b = np.polyfit(x, trend_df["avg_reviews"], 1)
            future_weeks = pd.date_range(start=weeks[-1], periods=5, freq="W")[1:]
            future_vals  = [m * (len(x) + i) + b for i in range(1, 5)]

            fig = go.Figure()
            fig.add_trace(go.Scatter(x=trend_df["week"], y=trend_df["avg_reviews"],
                                     name="Historical", line=dict(color=ACCENT, width=2)))
            fig.add_trace(go.Scatter(x=future_weeks, y=future_vals,
                                     name="Forecast (4w)",
                                     line=dict(color=DANGER, width=2, dash="dash")))
            fig.update_layout(title="Avg Review Count — Trend & Forecast",
                              height=300, margin=dict(l=0, r=0, t=40, b=0))
            st.plotly_chart(fig, use_container_width=True)

        with p1c2:
            price_series = _synthetic_series(avg_price_now * 0.92, trend=0.015, noise=0.03)
            price_df = pd.DataFrame({"week": weeks, "avg_price": price_series})
            x = np.arange(len(price_df))
            m, b = np.polyfit(x, price_df["avg_price"], 1)
            future_vals_p = [m * (len(x) + i) + b for i in range(1, 5)]

            fig = go.Figure()
            fig.add_trace(go.Scatter(x=price_df["week"], y=price_df["avg_price"],
                                     name="Historical", line=dict(color=ACCENT, width=2)))
            fig.add_trace(go.Scatter(x=future_weeks, y=future_vals_p,
                                     name="Forecast (4w)",
                                     line=dict(color=WARNING, width=2, dash="dash")))
            fig.update_layout(title="Avg Price Trend & Forecast",
                              height=300, margin=dict(l=0, r=0, t=40, b=0))
            st.plotly_chart(fig, use_container_width=True)

        st.markdown('<div class="section-header">🎨 Attribute Trend Signals</div>',
                    unsafe_allow_html=True)

        color_family_counts = attribute_counts(df, "color_family", top_n=6)
        pattern_counts      = attribute_counts(df, "pattern",      top_n=6)

        p2c1, p2c2 = st.columns(2)

        with p2c1:
            if not color_family_counts.empty:
                trend_data = []
                for _, row in color_family_counts.iterrows():
                    tf = np.random.uniform(-0.03, 0.07)
                    trend_data.append({
                        "attribute":  row["color_family"],
                        "current":    int(row["count"]),
                        "trend_pct":  round(tf * 100, 1),
                        "signal":     ("↑ Rising" if tf > 0.02
                                       else "↓ Falling" if tf < -0.01 else "→ Stable"),
                    })
                tdf = pd.DataFrame(trend_data)
                fig = px.bar(tdf, x="attribute", y="trend_pct", color="signal",
                             color_discrete_map={"↑ Rising": SUCCESS,
                                                 "→ Stable": WARNING,
                                                 "↓ Falling": DANGER},
                             title="Color Family Trend Signal (% change / week)",
                             labels={"attribute": "Color Family", "trend_pct": "Trend %"})
                fig.update_layout(height=300, margin=dict(l=0, r=0, t=40, b=0))
                st.plotly_chart(fig, use_container_width=True)

        with p2c2:
            if not pattern_counts.empty:
                trend_data2 = []
                for _, row in pattern_counts.iterrows():
                    tf = np.random.uniform(-0.04, 0.08)
                    trend_data2.append({
                        "attribute":  row["pattern"],
                        "current":    int(row["count"]),
                        "trend_pct":  round(tf * 100, 1),
                        "signal":     ("↑ Rising" if tf > 0.02
                                       else "↓ Falling" if tf < -0.01 else "→ Stable"),
                    })
                tdf2 = pd.DataFrame(trend_data2)
                fig = px.bar(tdf2, x="attribute", y="trend_pct", color="signal",
                             color_discrete_map={"↑ Rising": SUCCESS,
                                                 "→ Stable": WARNING,
                                                 "↓ Falling": DANGER},
                             title="Pattern Trend Signal (% change / week)",
                             labels={"attribute": "Pattern", "trend_pct": "Trend %"})
                fig.update_layout(height=300, margin=dict(l=0, r=0, t=40, b=0))
                st.plotly_chart(fig, use_container_width=True)

        st.markdown('<div class="section-header">💰 Price Band Performance Forecast</div>',
                    unsafe_allow_html=True)
        pb = price_bands(df)
        if not pb.empty:
            np.random.seed(7)
            pb["forecast_products"] = (
                pb["count"] * (1 + np.random.uniform(-0.1, 0.2, len(pb)))
            ).round().astype(int)
            pb.columns = ["Price Band", "Current", "4-Week Forecast"]

            fig = go.Figure()
            fig.add_trace(go.Bar(name="Current",
                                  x=pb["Price Band"], y=pb["Current"],
                                  marker_color=ACCENT))
            fig.add_trace(go.Bar(name="4-Week Forecast",
                                  x=pb["Price Band"], y=pb["4-Week Forecast"],
                                  marker_color=WARNING, opacity=0.75))
            fig.update_layout(barmode="group",
                              title="Price Band: Current vs Forecast",
                              height=320, margin=dict(l=0, r=0, t=40, b=0))
            st.plotly_chart(fig, use_container_width=True)

        st.info("ℹ️ Forecasts use linear trend extrapolation on synthetic historical data. "
                "After 4+ weekly scrapes the model will use real time-series data.")


# ═══════════════════════════════════════════════════════════════════════════════
# TAB 4 — RECOMMENDATION INTELLIGENCE
# ═══════════════════════════════════════════════════════════════════════════════
with tab4:
    st.markdown("### 🎯 Recommendation Intelligence")
    st.caption("Evidence-backed recommendations powered by Claude · Accept, Modify, or Dismiss")

    if df.empty:
        st.info("No data yet. Run the scraper first.")
    else:
        if st.button("🔄 Generate Recommendations", type="primary", key="gen_rec"):
            with st.spinner("Analysing market data and generating recommendations..."):
                try:
                    import anthropic
                    from config.settings import settings

                    data_ctx = data_summary_for_llm(df)
                    client = anthropic.Anthropic(api_key=settings.anthropic_api_key)
                    response = client.messages.create(
                        model="claude-sonnet-4-6",
                        max_tokens=2000,
                        system="""You are a senior retail market intelligence analyst at Innovatics.
Generate exactly 6 specific, evidence-backed recommendations for an apparel brand.

Format each recommendation as:
RECOMMENDATION [N]:
Observation: [what the data shows]
Action: [specific action for the brand]
Evidence: [cite specific numbers from the data]
Impact: [expected business outcome]
Confidence: [High/Medium/Low]

Recommendations must feel like something a senior merchandiser or category manager would act on.
No generic advice. Every recommendation must cite specific data points.""",
                        messages=[{
                            "role": "user",
                            "content": f"Market data:\n{data_ctx}\n\nGenerate 6 ranked recommendations.",
                        }],
                    )
                    raw = response.content[0].text
                    st.session_state["recommendations"] = raw
                    st.session_state["rec_feedback"]    = {}

                except Exception as e:
                    st.error(f"Could not connect to Claude API: {e}")
                    st.info("Make sure `ANTHROPIC_API_KEY` is set in your .env file.")

        if "recommendations" in st.session_state:
            raw_text = st.session_state["recommendations"]
            blocks = [b.strip() for b in raw_text.split("RECOMMENDATION") if b.strip()]

            if not blocks:
                st.markdown(raw_text)
            else:
                for idx, block in enumerate(blocks):
                    rec_key = f"rec_{idx}"
                    feedback = st.session_state.get("rec_feedback", {})
                    action_taken = feedback.get(rec_key)

                    border_color = (
                        SUCCESS if action_taken == "accept"  else
                        DANGER  if action_taken == "dismiss" else
                        WARNING if action_taken == "modify"  else ACCENT
                    )
                    status_badge = (
                        "✅ Accepted"  if action_taken == "accept"  else
                        "❌ Dismissed" if action_taken == "dismiss" else
                        "✏️ Modified"  if action_taken == "modify"  else ""
                    )

                    st.markdown(f"""
<div style='background:white; border-left:4px solid {border_color};
     border-radius:8px; padding:16px; margin-bottom:12px;
     box-shadow:0 1px 4px rgba(0,0,0,0.06);'>
    <strong style='color:{PRIMARY};'>RECOMMENDATION {block[:3]}</strong>
    {'&nbsp;&nbsp;<span style="color:' + border_color + '">' + status_badge + '</span>'
     if status_badge else ''}
    <hr style='margin:8px 0; border-color:#eee;'>
    {block[3:].replace(chr(10), '<br>')}
</div>""", unsafe_allow_html=True)

                    if not action_taken:
                        bcol1, bcol2, bcol3 = st.columns([1, 1, 3])
                        if bcol1.button("✅ Accept",  key=f"acc_{idx}"):
                            st.session_state.setdefault("rec_feedback", {})[rec_key] = "accept"
                            save_feedback(block, "accept",
                                          category=category_filter if category_filter != "All" else None)
                            st.rerun()
                        if bcol2.button("❌ Dismiss", key=f"dis_{idx}"):
                            st.session_state.setdefault("rec_feedback", {})[rec_key] = "dismiss"
                            save_feedback(block, "dismiss",
                                          category=category_filter if category_filter != "All" else None)
                            st.rerun()
                        mod_text = bcol3.text_input("Modify:", key=f"mod_txt_{idx}",
                                                     placeholder="Edit the recommendation...")
                        if mod_text and bcol3.button("💾 Save", key=f"sav_{idx}"):
                            st.session_state.setdefault("rec_feedback", {})[rec_key] = "modify"
                            save_feedback(block, "modify",
                                          category=category_filter if category_filter != "All" else None,
                                          modified_text=mod_text)
                            st.rerun()

            feedback = st.session_state.get("rec_feedback", {})
            if feedback:
                accepted  = sum(1 for v in feedback.values() if v == "accept")
                dismissed = sum(1 for v in feedback.values() if v == "dismiss")
                modified  = sum(1 for v in feedback.values() if v == "modify")
                st.markdown("---")
                fc1, fc2, fc3 = st.columns(3)
                fc1.metric("✅ Accepted",  accepted)
                fc2.metric("❌ Dismissed", dismissed)
                fc3.metric("✏️ Modified",  modified)
