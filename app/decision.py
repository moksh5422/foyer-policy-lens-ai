import json
import os
import re
from typing import List, Optional

from .models import Evidence, Assessment

COVERAGE_CUES = (
    "we cover", "the policy covers", "covers", "is covered", "are covered",
    "coverage applies", "insured against", "benefit is payable",
)
EXCLUSION_CUES = (
    "not covered", "not be covered", "does not cover", "do not cover",
    "excluded", "exclusion applies", "no cover for",
)
CONDITIONAL_CUES = (
    "depending on", "subject to", "provided that", "only if", "unless",
    "may be excluded", "may not be covered",
)
GENERIC_TERMS = {
    "damage", "loss", "vehicle", "property", "insured", "incident", "claim",
    "policy", "coverage", "event", "caused", "used", "accidental", "sudden",
    "ordinary", "personal",
}
STOP_WORDS = {
    "what", "is", "are", "was", "were", "my", "the", "a", "an", "does", "do",
    "i", "this", "that", "claim", "covered", "cover", "coverage", "under", "policy",
    "can", "by", "for", "during", "with", "and", "or", "of", "to", "in", "on", "be",
}


def _tokens(text: str):
    return set(re.findall(r"[a-z0-9]+", text.lower()))


def _sentences(text: str):
    return [s.strip() for s in re.split(r"(?<=[.!?])\s+|\n+", text) if s.strip()]


def _question_terms(question: str):
    return _tokens(question) - STOP_WORDS


def _relevance(question: str, sentence: str) -> float:
    q = _question_terms(question)
    s = _tokens(sentence)
    if not q or not s:
        return 0.0
    overlap = len(q & s)
    q_words = re.findall(r"[a-z0-9]+", question.lower())
    s_words = re.findall(r"[a-z0-9]+", sentence.lower())
    q_bigrams = set(zip(q_words, q_words[1:]))
    s_bigrams = set(zip(s_words, s_words[1:]))
    phrase_bonus = min(1.5, 0.75 * len(q_bigrams & s_bigrams))
    return float(overlap) + phrase_bonus


def _cue_score(sentence: str, cues) -> float:
    s = sentence.lower()
    return sum(1.0 for cue in cues if cue in s)


def _term_cue_proximity(question: str, sentence: str, cues) -> float:
    qterms = _question_terms(question)
    words = re.findall(r"[a-z0-9]+", sentence.lower())
    if not qterms or not words:
        return 0.0
    cue_positions = []
    for cue in cues:
        cue_words = cue.split()
        for i in range(len(words) - len(cue_words) + 1):
            if words[i:i + len(cue_words)] == cue_words:
                cue_positions.extend(range(i, i + len(cue_words)))
    if not cue_positions:
        return 0.0
    best = min(
        abs(i - j)
        for i, word in enumerate(words) if word in qterms
        for j in cue_positions
    )
    return 1.0 if best <= 10 else 0.0


def _unclear(evidence: List[Evidence], reason: str) -> Assessment:
    return Assessment(
        decision="UNCLEAR",
        confidence=0.25,
        explanation="The available policy evidence does not establish whether this scenario is covered.",
        evidence=evidence[:3],
        next_steps=[
            "Check the complete policy wording and applicable endorsements.",
            "Escalate to a qualified claims reviewer if the evidence remains insufficient.",
        ],
        trace={"method": "deterministic_evidence_reasoner", "reason": reason, "retrieved_chunks": len(evidence)},
    )


def _rule_based(question: str, evidence: List[Evidence]) -> Assessment:
    if not question.strip() or not evidence:
        return _unclear(evidence, "No sufficiently relevant policy evidence was retrieved.")

    rows = []
    for ev in evidence:
        for sent in _sentences(ev.text):
            relevance = _relevance(question, sent)
            if relevance > 0:
                rows.append({
                    "relevance": relevance,
                    "source_score": ev.score,
                    "evidence": ev,
                    "sentence": sent,
                    "coverage": _cue_score(sent, COVERAGE_CUES),
                    "exclusion": _cue_score(sent, EXCLUSION_CUES),
                    "conditional": _cue_score(sent, CONDITIONAL_CUES),
                })

    query_specific_terms = _question_terms(question) - GENERIC_TERMS
    has_specific_match = any(query_specific_terms & _tokens(r["sentence"]) for r in rows)
    if not rows or max(r["relevance"] for r in rows) < 2 or (query_specific_terms and not has_specific_match):
        return _unclear(evidence, "No sufficiently specific clause matched the loss described in the question.")

    for row in rows:
        row["coverage_score"] = row["relevance"] + 1.5 * row["coverage"] + _term_cue_proximity(question, row["sentence"], COVERAGE_CUES)
        row["exclusion_score"] = row["relevance"] + 1.5 * row["exclusion"] + _term_cue_proximity(question, row["sentence"], EXCLUSION_CUES)
        row["conditional_score"] = row["relevance"] + 1.5 * row["conditional"]

    coverage = sorted([r for r in rows if r["coverage"]], key=lambda r: (r["coverage_score"], r["source_score"]), reverse=True)
    exclusions = sorted([r for r in rows if r["exclusion"]], key=lambda r: (r["exclusion_score"], r["source_score"]), reverse=True)
    conditionals = sorted([r for r in rows if r["conditional"]], key=lambda r: (r["conditional_score"], r["source_score"]), reverse=True)

    best_cov = coverage[0] if coverage else None
    best_excl = exclusions[0] if exclusions else None
    best_cond = conditionals[0] if conditionals else None

    if best_cond and (
        (not best_cov or best_cond["conditional_score"] >= best_cov["coverage_score"] + 0.5)
        and (not best_excl or best_cond["conditional_score"] >= best_excl["exclusion_score"] + 0.5)
    ):
        decision = "CONDITIONAL"
        confidence = 0.75
        reason = best_cond["sentence"]
    elif best_cov and best_excl:
        qterms = _question_terms(question)
        cov_terms = _tokens(best_cov["sentence"])
        excl_terms = _tokens(best_excl["sentence"])
        exclusion_only_terms = len((excl_terms & qterms) - cov_terms)
        coverage_only_terms = len((cov_terms & qterms) - excl_terms)
        gap = best_cov["coverage_score"] - best_excl["exclusion_score"]

        if exclusion_only_terms > 0 and best_excl["exclusion_score"] >= best_cov["coverage_score"] - 1.5:
            decision = "NOT COVERED"
            confidence = 0.90
            reason = best_excl["sentence"]
        elif coverage_only_terms > 0 and best_cov["coverage_score"] > best_excl["exclusion_score"] + 1.5:
            decision = "COVERED"
            confidence = 0.88
            reason = best_cov["sentence"]
        elif abs(gap) < 1.0:
            decision = "CONDITIONAL"
            confidence = 0.72
            reason = "The retrieved evidence contains both coverage and exclusion language; the applicable policy conditions need to be verified."
        elif gap > 0:
            decision = "COVERED"
            confidence = min(0.95, 0.72 + 0.05 * gap)
            reason = best_cov["sentence"]
        else:
            decision = "NOT COVERED"
            confidence = min(0.95, 0.72 + 0.05 * (-gap))
            reason = best_excl["sentence"]
    elif best_excl:
        if best_cond and best_cond["conditional_score"] >= best_excl["exclusion_score"] - 1.0:
            decision = "CONDITIONAL"
            confidence = 0.75
            reason = best_cond["sentence"]
        else:
            decision = "NOT COVERED"
            confidence = min(0.94, 0.76 + 0.04 * best_excl["exclusion_score"])
            reason = best_excl["sentence"]
    elif best_cov:
        decision = "COVERED"
        confidence = min(0.94, 0.76 + 0.04 * best_cov["coverage_score"])
        reason = best_cov["sentence"]
    else:
        decision = "UNCLEAR"
        confidence = 0.35
        reason = "The retrieved evidence does not contain a decisive coverage grant, exclusion, or condition for the described loss."

    conditions = [r["sentence"] for r in conditionals[:3]]
    exclusion_text = [r["sentence"] for r in exclusions[:3]] if decision in {"NOT COVERED", "CONDITIONAL"} else []
    return Assessment(
        decision=decision,
        confidence=confidence,
        explanation=reason,
        evidence=evidence,
        conditions=conditions,
        exclusions=exclusion_text,
        next_steps=[
            "Verify the policy number, policy version and date of loss.",
            "Confirm the facts, limits, deductibles and endorsements relevant to the claim.",
            "Use the cited policy evidence as the basis for final human claims review.",
        ],
        trace={
            "method": "deterministic_evidence_reasoner",
            "retrieved_chunks": len(evidence),
            "relevant_sentences": len(rows),
            "coverage_candidates": len(coverage),
            "exclusion_candidates": len(exclusions),
            "conditional_candidates": len(conditionals),
        },
    )


def _openai_decision(question: str, evidence: List[Evidence], model: str) -> Optional[Assessment]:
    key = os.getenv("OPENAI_API_KEY")
    if not key:
        return None
    try:
        from openai import OpenAI
        client = OpenAI(api_key=key)
        context = "\n\n".join(f"[{i + 1}] {e.source} / {e.chunk_id}\n{e.text}" for i, e in enumerate(evidence))
        prompt = f"""
You are an insurance policy evidence assistant. Answer only from the supplied policy evidence.
Question: {question}

Policy evidence:
{context}

Return JSON with:
decision: one of COVERED, NOT COVERED, CONDITIONAL, UNCLEAR
confidence: number 0 to 1
explanation: concise business explanation
conditions: array of strings
exclusions: array of strings
next_steps: array of strings
Do not invent policy terms. If evidence is insufficient or ambiguous, choose UNCLEAR or CONDITIONAL.
"""
        response = client.chat.completions.create(
            model=model,
            temperature=0,
            response_format={"type": "json_object"},
            messages=[{"role": "user", "content": prompt}],
        )
        data = json.loads(response.choices[0].message.content or "{}")
        decision = data.get("decision", "UNCLEAR")
        if decision not in {"COVERED", "NOT COVERED", "CONDITIONAL", "UNCLEAR"}:
            return None
        return Assessment(
            decision=decision,
            confidence=max(0.0, min(1.0, float(data.get("confidence", 0.5)))),
            explanation=str(data.get("explanation", "")),
            evidence=evidence,
            conditions=list(data.get("conditions", [])),
            exclusions=list(data.get("exclusions", [])),
            next_steps=list(data.get("next_steps", [])),
            trace={"method": "openai_structured_reasoning", "model": model},
        )
    except Exception:
        return None


def assess(question: str, evidence: List[Evidence], use_llm: bool = False, model: str = "gpt-4o-mini") -> Assessment:
    if use_llm:
        result = _openai_decision(question, evidence, model)
        if result:
            return result
    return _rule_based(question, evidence)
