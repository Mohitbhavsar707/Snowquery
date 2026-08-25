import json

import pytest

from src.assistant import GroundedAssistant, ROOT, plan_sql, retrieve_schema


@pytest.fixture(scope="session", autouse=True)
def local_warehouse():
    script = ROOT / "scripts" / "bootstrap_local.py"
    exec(compile(script.read_text(), str(script), "exec"), {"__file__": str(script)})


def test_retrieval_finds_expected_model_for_golden_set():
    cases = json.loads((ROOT / "data" / "golden_set.json").read_text())
    for case in cases:
        models = [model for model, _ in retrieve_schema(case["question"])]
        assert case["expected_model"] in models


def test_all_golden_questions_execute_with_expected_column():
    cases = json.loads((ROOT / "data" / "golden_set.json").read_text())
    assistant = GroundedAssistant("duckdb")
    for case in cases:
        response = assistant.ask(case["question"])
        assert not response.rows.empty
        assert case["expected_column"] in response.rows.columns


def test_unsupported_question_is_rejected():
    with pytest.raises(ValueError, match="currently answer"):
        plan_sql("Delete every record in the warehouse")


def test_generated_queries_are_read_only():
    cases = json.loads((ROOT / "data" / "golden_set.json").read_text())
    for case in cases:
        _, sql = plan_sql(case["question"])
        assert sql.lstrip().upper().startswith("SELECT")
        assert ";" not in sql
