from pathlib import Path
from app.pipeline import PolicyLensPipeline
from app.evaluation import run_evaluation

policies = sorted(str(p) for p in Path("data/policies").iterdir() if p.is_file())
pipeline = PolicyLensPipeline.from_paths(policies)
result = run_evaluation(pipeline, "data/evaluation/questions.json")
print(f"Accuracy: {result['accuracy']:.1%} ({result['correct']}/{result['total']})")
for row in result["cases"]:
    status = "OK" if row["correct"] else "FAIL"
    print(f"{row['id']}: {row['predicted']} | expected={row['expected']} | {status}")
