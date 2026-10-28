from dataclasses import asdict, dataclass
from typing import Optional

@dataclass
class DocumentChunk:
    text: str
    source: str
    document_id: str
    page: Optional[int] = None
    section: Optional[str] = None

@dataclass
class Evidence:
    text: str
    source: str
    score: float
    page: Optional[int] = None
    section: Optional[str] = None
    chunk_id: str = ""

@dataclass
class Assessment:
    decision: str
    summary: str
    reasoning: str
    evidence: list[Evidence]
    questions_for_claimant: list[str]
    disclaimer: str = "Demo decision-support only. A qualified claims professional must make the final determination."
    conditions: Optional[list[str]] = None
    exclusions: Optional[list[str]] = None

    def __post_init__(self):
        self.conditions = self.conditions or []
        self.exclusions = self.exclusions or []

    def to_dict(self):
        return {
            "decision": self.decision,
            "summary": self.summary,
            "reasoning": self.reasoning,
            "evidence": [asdict(item) for item in self.evidence],
            "questions_for_claimant": self.questions_for_claimant,
            "conditions": self.conditions,
            "exclusions": self.exclusions,
            "disclaimer": self.disclaimer,
        }
