import json
from pathlib import Path

def run_evaluation(pipeline, cases_path: str) -> dict:
    cases = json.loads(Path(cases_path).read_text(encoding="utf-8"))
    results = []
    for case in cases:
        result = pipeline.answer(case["question"])
        expected = case["expected_decision"]
        results.append({"id": case["id"], "question": case["question"], "predicted": result.decision, "expected": expected, "correct": result.decision == expected})
    correct = sum(row["correct"] for row in results)
    return {"total": len(results), "correct": correct, "accuracy": correct / len(results) if results else 0.0, "cases": results}
