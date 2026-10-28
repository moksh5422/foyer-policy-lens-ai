import json, os, re
from .models import Evidence, Assessment

DISCLAIMER = "Demo decision-support only. A qualified claims professional must make the final determination."

def _terms(text):
    return set(re.findall(r"[a-z0-9]+", text.lower()))

def _rule_assessment(question, evidence):
    q = question.lower()
    qterms = _terms(q)
    relevant = []
    for ev in evidence:
        for sentence in re.split(r"(?<=[.!?])\s+|\n+", ev.text):
            sentence = sentence.strip()
            if not sentence:
                continue
            terms = _terms(sentence)
            overlap = len((qterms - {"is","my","the","a","an","does","do","this","that","claim","covered","coverage","under","policy","for","to"}) & terms)
            if overlap:
                relevant.append((overlap, ev.score, ev, sentence))
    relevant.sort(key=lambda row: (row[0], row[1]), reverse=True)
    if not relevant:
        return Assessment("UNCLEAR", "The available policy text does not establish whether this scenario is covered.", "No sufficiently relevant policy clause was retrieved. A reviewer should check the full wording and any endorsements.", evidence[:3], ["Confirm the policy version and effective date.", "Ask a claims reviewer to inspect the complete policy and endorsements."], DISCLAIMER)

    topic = qterms
    candidates = [x for x in relevant if x[0] >= max(1, min(2, len(topic)))] or relevant
    exclusion_words = ("not covered", "excluded", "does not cover", "exclusion applies", "not insured")
    coverage_words = ("we cover", "is covered", "are covered", "coverage applies", "insured against", "covers sudden")
    exclusions = [x for x in candidates if any(w in x[3].lower() for w in exclusion_words)]
    covered = [x for x in candidates if any(w in x[3].lower() for w in coverage_words) and not any(w in x[3].lower() for w in exclusion_words)]
    conditional = [x for x in candidates if any(w in x[3].lower() for w in ("depending on", "subject to", "may be excluded", "provided that"))]

    best_excl = max(exclusions, key=lambda x: (x[0], x[1]), default=None)
    best_cov = max(covered, key=lambda x: (x[0], x[1]), default=None)
    if best_excl and (not best_cov or best_excl[0] >= best_cov[0]):
        decision, reason = "NOT COVERED", best_excl[3]
    elif conditional and (not best_cov or conditional[0][0] >= best_cov[0]):
        decision, reason = "CONDITIONAL", conditional[0][3]
    elif best_cov:
        decision, reason = "COVERED", best_cov[3]
    else:
        decision, reason = "UNCLEAR", "The retrieved text does not contain a decisive clause for the described loss."

    conditions = [x[3] for x in conditional[:3]]
    exclusion_text = [x[3] for x in exclusions[:3]] if decision == "NOT COVERED" else []
    summary = {
        "COVERED": "The retrieved policy evidence indicates that the described event is covered, subject to policy terms.",
        "NOT COVERED": "The retrieved policy evidence indicates that an exclusion applies to the described event.",
        "CONDITIONAL": "Coverage depends on additional policy wording or claim facts that should be verified.",
        "UNCLEAR": "The retrieved evidence is insufficient to determine coverage reliably."
    }[decision]
    return Assessment(decision, summary, reason, [x[2] for x in candidates[:5]], ["Verify policy number, policy version and date of loss.", "Confirm relevant facts, limits, deductibles and endorsements.", "Escalate conditional or unclear outcomes to a claims professional."], DISCLAIMER, conditions, exclusion_text)

def assess(question: str, evidence: list[Evidence], use_llm: bool = False, model: str = "gpt-4o-mini") -> Assessment:
    if use_llm and os.getenv("OPENAI_API_KEY") and evidence:
        try:
            from openai import OpenAI
            client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
            prompt = {
                "question": question,
                "evidence": [{"source": e.source, "chunk_id": e.chunk_id, "text": e.text} for e in evidence],
                "instructions": "Assess only from supplied evidence. Never invent policy terms. Use exactly COVERED, NOT COVERED, CONDITIONAL or UNCLEAR. If evidence conflicts or is insufficient, return UNCLEAR or CONDITIONAL. Cite only provided source and chunk IDs. Return JSON with decision, summary, reasoning, cited_chunk_ids, conditions, exclusions, questions_for_claimant."
            }
            response = client.chat.completions.create(
                model=model,
                temperature=0,
                response_format={"type": "json_object"},
                messages=[{"role": "system", "content": "You are a cautious insurance-policy evidence assistant. You do not make binding claims decisions."}, {"role": "user", "content": json.dumps(prompt)}]
            )
            data = json.loads(response.choices[0].message.content or "{}")
            decision = data.get("decision", "UNCLEAR")
            if decision not in {"COVERED", "NOT COVERED", "CONDITIONAL", "UNCLEAR"}:
                decision = "UNCLEAR"
            ids = set(data.get("cited_chunk_ids", []))
            cited = [e for e in evidence if e.chunk_id in ids]
            # Fail safely if the model provides no valid evidence references.
            if not cited:
                return _rule_assessment(question, evidence)
            return Assessment(decision, str(data.get("summary", "")), str(data.get("reasoning", "")), cited, list(data.get("questions_for_claimant", [])), DISCLAIMER, list(data.get("conditions", [])), list(data.get("exclusions", [])))
        except Exception:
            # Keep the demo usable when the external model cannot be reached.
            pass
    return _rule_assessment(question, evidence)
