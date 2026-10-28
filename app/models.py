from dataclasses import dataclass, asdict
from typing import Optional

@dataclass
class DocumentChunk:
    text: str
    source: str
    document_id: str
    page: Optional[int] = None
    section: Optional[str] = None

    def to_dict(self):
        return asdict(self)

@dataclass
class ClaimInput:
    description: str
    amount: Optional[float] = None
    policy_number: Optional[str] = None

@dataclass
class Evidence:
    text: str
    source: str
    score: float
    page: Optional[int] = None
    section: Optional[str] = None

@dataclass
class Assessment:
    outcome: str
    summary: str
    reasoning: str
    evidence: list[Evidence]
    questions_for_claimant: list[str]
    disclaimer: str = "Demo assessment only; a qualified claims professional must make the final decision."
