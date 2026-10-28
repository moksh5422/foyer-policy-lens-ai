from pathlib import Path
from app.pipeline import PolicyLensPipeline

def build_pipeline():
    policies = sorted(str(p) for p in Path("data/policies").iterdir() if p.is_file())
    return PolicyLensPipeline.from_paths(policies)

def test_coverage_and_exclusion():
    pipeline = build_pipeline()
    assert pipeline.answer("Is accidental water damage caused by a burst pipe covered?").decision == "COVERED"
    assert pipeline.answer("Is damage caused by gradual seepage covered?").decision == "NOT COVERED"
    assert pipeline.answer("Is a vehicle used in racing covered for collision damage?").decision == "NOT COVERED"
    assert pipeline.answer("Is damage caused by an earthquake covered?").decision == "UNCLEAR"

def test_conditional_cosmetic_clause():
    pipeline = build_pipeline()
    assert pipeline.answer("Is minor cosmetic damage automatically covered?").decision == "CONDITIONAL"

def test_empty_question_is_unclear():
    pipeline = build_pipeline()
    assert build_pipeline().answer("").decision == "UNCLEAR"
