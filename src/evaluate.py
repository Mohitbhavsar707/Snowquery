import json
from pathlib import Path

from src.assistant import GroundedAssistant, ROOT


def main() -> None:
    cases = json.loads((ROOT / "data" / "golden_set.json").read_text())
    assistant = GroundedAssistant("duckdb")
    retrieval_hits = 0
    execution_hits = 0
    for case in cases:
        try:
            result = assistant.ask(case["question"])
            retrieval_ok = case["expected_model"] in result.retrieved_models
            execution_ok = not result.rows.empty and case["expected_column"] in result.rows.columns
        except Exception:
            retrieval_ok = execution_ok = False
        retrieval_hits += retrieval_ok
        execution_hits += execution_ok
        print(f"{'PASS' if retrieval_ok and execution_ok else 'FAIL'}  {case['question']}")
    total = len(cases)
    print(f"\nretrieval_hit@2: {retrieval_hits / total:.0%} ({retrieval_hits}/{total})")
    print(f"execution_accuracy: {execution_hits / total:.0%} ({execution_hits}/{total})")


if __name__ == "__main__":
    main()

