"""
Chatbot smoke test — 5 key scenarios covering every agent route.
Usage: venv/bin/python3 test_chatbot.py
"""
import sys
sys.path.insert(0, "chatbot")

from dotenv import load_dotenv
load_dotenv()

from orchestrator import orchestrator

TESTS = [
    {
        "id": 1,
        "label": "Mark-down candidates",
        "question": "Which products should I mark down? Show high-price, zero-review items",
        "expect_agent": "sql_agent",
        "expect_in_response": ["Ambuto", "2,178", "0"],
        "bad_patterns": ["no matching", "no products", "no high-price"],
    },
    {
        "id": 2,
        "label": "Price gap Amazon vs Nordstrom",
        "question": "What is the median price gap between Amazon and Nordstrom?",
        "expect_agent": "sql_agent",
        "expect_in_response": ["14.23", "64.71"],
        "bad_patterns": ["0.00", "no gap", "same price"],
    },
    {
        "id": 3,
        "label": "Rising patterns",
        "question": "Which patterns are rising the fastest right now?",
        "expect_agent": "trend_engine_agent",
        "expect_in_response": ["Cartoon", "Rising"],
        "bad_patterns": ["-100", "no patterns are rising"],
    },
    {
        "id": 4,
        "label": "Declining patterns",
        "question": "What patterns are declining fastest across both channels?",
        "expect_agent": "trend_engine_agent",
        "expect_in_response": ["-0."],           # negative velocity present
        "bad_patterns": ["-100", "no patterns"], # no fake -100% velocity
    },
    {
        "id": 5,
        "label": "Customer review complaints",
        "question": "What do customers complain about most in men's t-shirts?",
        "expect_agent": "vector_agent",
        "expect_in_response": ["star", "%"],
        "bad_patterns": ["embeddings", "not available", "cannot import"],
    },
]

SEP = "─" * 70

def run_tests():
    passed = 0
    failed = 0

    for t in TESTS:
        print(f"\n{SEP}")
        print(f"TEST {t['id']}: {t['label']}")
        print(f"Q: {t['question']}")
        print(SEP)

        try:
            result = orchestrator.process_question(
                session_id=f"test_{t['id']}",
                question=t["question"],
            )

            tool_response = result.get("tool_response") or {}
            agent = tool_response.get("source", "unknown")
            response = result.get("response", "")
            success = result.get("success", False)

            print(f"Agent  : {agent}")
            print(f"Success: {success}")
            print(f"Response:\n{response[:500]}")

            issues = []

            if agent != t["expect_agent"]:
                issues.append(f"WRONG AGENT: got '{agent}', expected '{t['expect_agent']}'")

            for kw in t["expect_in_response"]:
                if kw.lower() not in response.lower():
                    issues.append(f"MISSING: '{kw}'")

            for bad in t["bad_patterns"]:
                if bad.lower() in response.lower():
                    issues.append(f"BAD PATTERN FOUND: '{bad}'")

            if not success:
                issues.append("success=False")

            if issues:
                print(f"\n❌ FAIL: {' | '.join(issues)}")
                failed += 1
            else:
                print(f"\n✅ PASS")
                passed += 1

        except Exception as e:
            print(f"\n❌ CRASH: {e}")
            import traceback; traceback.print_exc()
            failed += 1

    print(f"\n{SEP}")
    print(f"RESULTS: {passed}/{len(TESTS)} passed")
    if failed:
        print("Fix the failures above before running the full 10-question UI test.")
    else:
        print("All tests passed — safe to test in the UI.")
    print(SEP)
    return failed == 0


if __name__ == "__main__":
    ok = run_tests()
    sys.exit(0 if ok else 1)
