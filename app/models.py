from dataclasses import asdict, dataclass, field
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
    summary: str = ""
    reasoning: str = ""
    evidence: list[Evidence] = field(default_factory=list)
    questions_for_claimant: list[str] = field(default_factory=list)
    disclaimer: str = "Demo decision-support only. A qualified claims professional must make the final determination."
    conditions: list[str] = field(default_factory=list)
    exclusions: list[str] = field(default_factory=list)
    confidence: Optional[float] = None
    explanation: str = ""
    next_steps: list[str] = field(default_factory=list)
    trace: dict = field(default_factory=dict)

    def __post_init__(self):
        if not self.reasoning and self.explanation:
            self.reasoning = self.explanation
        if not self.questions_for_claimant and self.next_steps:
            self.questions_for_claimant = self.next_steps
        if not self.summary:
            self.summary = f"Coverage assessment: {self.decision}."

    def to_dict(self):
        return {
            "decision": self.decision,
            "summary": self.summary,
            "reasoning": self.reasoning,
            "evidence": [asdict(item) for item in self.evidence],
            "questions_for_claimant": self.questions_for_claimant,
            "conditions": self.conditions,
            "exclusions": self.exclusions,
            "confidence": self.confidence,
            "trace": self.trace,
            "disclaimer": self.disclaimer,
        }
