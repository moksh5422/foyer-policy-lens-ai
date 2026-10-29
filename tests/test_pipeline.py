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


def test_installed_appliance_theft():
    pipeline = build_pipeline()
    assert pipeline.answer("Is theft of a permanently installed home appliance covered?").decision == "COVERED"


def test_empty_question_is_unclear():
    pipeline = build_pipeline()
    assert pipeline.answer("").decision == "UNCLEAR"


def test_reasoner_is_not_hardcoded_to_demo_topics(tmp_path):
    policy = tmp_path / "new_policy.txt"
    policy.write_text(
        "GLASS COVER\n"
        "The policy covers accidental breakage of fixed glass panels in the insured premises.\n\n"
        "GLASS EXCLUSION\n"
        "Intentional breakage of glass is not covered.\n",
        encoding="utf-8",
    )

    pipeline = PolicyLensPipeline.from_paths([str(policy)])
    assert pipeline.answer("Is accidental breakage of a fixed glass panel covered?").decision == "COVERED"
    assert pipeline.answer("Is intentional breakage of a glass panel covered?").decision == "NOT COVERED"


def test_unknown_scenario_returns_unclear(tmp_path):
    policy = tmp_path / "limited_policy.txt"
    policy.write_text(
        "The policy covers accidental damage to the insured property.\n",
        encoding="utf-8",
    )
    pipeline = PolicyLensPipeline.from_paths([str(policy)])
    assert pipeline.answer("Is volcanic eruption damage covered?").decision == "UNCLEAR"
