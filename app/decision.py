import json
import os
import re
from .models import Evidence, Assessment

DISCLAIMER = "Demo decision-support only. A qualified claims professional must make the final determination."
STOP = {"is", "my", "the", "a", "an", "does", "do", "this", "that", "claim", "covered", "coverage", "under", "policy", "for", "to", "during", "by", "with", "what", "are", "was", "were"}
TOPICS = {
    "water_burst": ["burst pipe", "burst", "sudden plumbing", "escape of water"],
    "water_gradual": ["gradual seepage", "gradual", "repeated leakage", "long-term deterioration", "lack of maintenance"],
    "appliance_theft": ["permanently installed", "household appliance", "appliance theft"],
    "external_theft": ["unsecured external", "external area", "property left outside"],
    "collision": ["collision", "vehicle collision"],
    "racing": ["racing", "track event", "timed competition", "competitive driving"],
    "cosmetic": ["cosmetic damage", "minor cosmetic"],
    "earthquake": ["earthquake"],
}
TOPIC_WORDS = {
    "water_burst": {"burst", "pipe", "sudden", "plumbing", "water", "escape"},
    "water_gradual": {"gradual", "seepage", "leakage", "maintenance", "deterioration"},
    "appliance_theft": {"appliance", "installed", "theft", "forcible"},
    "external_theft": {"external", "unsecured", "theft", "property"},
    "collision": {"collision", "vehicle", "transportation"},
    "racing": {"racing", "competition", "track", "driving", "vehicle"},
    "cosmetic": {"cosmetic", "damage", "repair", "collision"},
    "earthquake": {"earthquake", "seismic"},
}

def _words(text):
    return set(re.findall(r"[a-z0-9]+", text.lower()))

def _topic(question):
    q = question.lower()
    matches = [topic for topic, phrases in TOPICS.items() if any(phrase in q for phrase in phrases)]
    return matches[0] if len(matches) == 1 else None

def _sentence_relevance(question, sentence):
    qwords = _words(question) - STOP
    swords = _words(sentence)
    overlap = len(qwords & swords)
    topic = _topic(question)
    if topic:
        return len(swords & TOPIC_WORDS[topic]) * 2 + overlap * 0.05
    return overlap

def _rule_assessment(question, evidence):
    if not question.strip() or not evidence:
        return Assessment("UNCLEAR", "The available policy text does not establish whether this scenario is covered.", "No sufficiently relevant policy evidence was available. A claims reviewer should check the complete policy wording and endorsements.", evidence[:3], ["Confirm the policy number, version and date of loss.", "Ask a claims reviewer to inspect the complete policy and endorsements."], DISCLAIMER)
    if _topic(question) == "earthquake":
        directly_relevant = [ev for ev in evidence if "earthquake" in ev.text.lower() or "seismic" in ev.text.lower()]
        if not directly_relevant:
            return Assessment("UNCLEAR", "The supplied policy documents do not establish whether earthquake damage is covered.", "No earthquake-specific coverage or exclusion clause was found in the supplied policy text. The absence of a clause in this demo corpus is not proof of coverage or non-coverage.", evidence[:3], ["Check the complete policy wording and any endorsements for earthquake or earth-movement provisions.", "Escalate to a claims reviewer."], DISCLAIMER)
    topic = _topic(question)
    if topic == "earthquake":
        directly_relevant = [ev for ev in evidence if "earthquake" in ev.text.lower() or "seismic" in ev.text.lower()]
        if not directly_relevant:
            return Assessment("UNCLEAR", "The supplied policy documents do not establish whether earthquake damage is covered.", "No earthquake-specific coverage or exclusion clause was found in the supplied policy text. The absence of a clause in this demo corpus is not proof of coverage or non-coverage.", evidence[:3], ["Check the complete policy wording and any endorsements for earthquake or earth-movement provisions.", "Escalate to a claims reviewer."], DISCLAIMER)

    rows = []
    for ev in evidence:
        for sentence in re.split(r"(?<=[.!?])\s+|\n+", ev.text):
            sentence = sentence.strip()
            if not sentence:
                continue
            relevance = _sentence_relevance(question, sentence)
            if relevance > 0:
                rows.append((relevance, ev.score, ev, sentence))
    rows.sort(key=lambda x: (x[0], x[1]), reverse=True)
    if not rows:
        return Assessment("UNCLEAR", "The available policy text does not establish whether this scenario is covered.", "No directly relevant clause was found in the retrieved evidence.", evidence[:3], ["Confirm the policy version and effective dates.", "Escalate the question for human review."], DISCLAIMER)

    specific_exclusion_topics = {"water_gradual", "external_theft", "racing"}
    conditional_rows = [x for x in rows if any(p in x[3].lower() for p in ("depending on", "may be excluded", "subject to the policy excess"))]
    exclusions = [x for x in rows if any(p in x[3].lower() for p in ("not covered", "excluded", "does not cover", "exclusion applies"))]
    covered = [x for x in rows if any(p in x[3].lower() for p in ("we cover", "is covered", "are covered", "coverage applies", "covers sudden")) and not any(p in x[3].lower() for p in ("not covered", "does not cover", "not insured"))]
    best_exclusion = max(exclusions, key=lambda x: (x[0], x[1]), default=None)
    best_covered = max(covered, key=lambda x: (x[0], x[1]), default=None)

    if topic == "cosmetic" and conditional_rows:
        decision, reason = "CONDITIONAL", conditional_rows[0][3]
    elif best_exclusion and (not best_covered or best_exclusion[0] >= best_covered[0] or topic in specific_exclusion_topics):
        decision, reason = "NOT COVERED", best_exclusion[3]
    elif best_covered:
        decision, reason = "COVERED", best_covered[3]
    else:
        decision, reason = "UNCLEAR", "The retrieved text does not contain a decisive clause for the described loss."

    summary = {
        "COVERED": "The retrieved policy evidence indicates that the described event is covered, subject to policy terms.",
        "NOT COVERED": "The retrieved policy evidence indicates that an exclusion applies to the described event.",
        "CONDITIONAL": "Coverage depends on policy wording or claim facts that should be verified.",
        "UNCLEAR": "The retrieved evidence is insufficient to determine coverage reliably.",
    }[decision]
    conditions = [x[3] for x in conditional_rows[:3]]
    exclusion_text = [x[3] for x in exclusions[:3]] if decision == "NOT COVERED" else []
    return Assessment(decision, summary, reason, [x[2] for x in rows[:5]], ["Verify policy number, policy version and date of loss.", "Confirm relevant facts, limits, deductibles and endorsements.", "Escalate conditional or unclear outcomes to a claims professional."], DISCLAIMER, conditions, exclusion_text)

def assess(question: str, evidence: list[Evidence], use_llm: bool = False, model: str = "gpt-4o-mini") -> Assessment:
    if use_llm and os.getenv("OPENAI_API_KEY") and evidence:
        try:
            from openai import OpenAI
            client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
            payload = {"question": question, "evidence": [{"source": e.source, "chunk_id": e.chunk_id, "text": e.text} for e in evidence], "instructions": "Use only supplied evidence. Never invent policy terms. Return JSON keys decision, summary, reasoning, cited_chunk_ids, conditions, exclusions, questions_for_claimant. Decision must be COVERED, NOT COVERED, CONDITIONAL or UNCLEAR. If insufficient or conflicting, use UNCLEAR or CONDITIONAL."}
            response = client.chat.completions.create(model=model, temperature=0, response_format={"type": "json_object"}, messages=[{"role": "system", "content": "You are a cautious insurance-policy evidence assistant, not a binding claims decision-maker."}, {"role": "user", "content": json.dumps(payload)}])
            data = json.loads(response.choices[0].message.content or "{}")
            decision = data.get("decision", "UNCLEAR")
            if decision not in {"COVERED", "NOT COVERED", "CONDITIONAL", "UNCLEAR"}:
                return _rule_assessment(question, evidence)
            cited_ids = set(data.get("cited_chunk_ids", []))
            cited = [ev for ev in evidence if ev.chunk_id in cited_ids]
            if not cited:
                return _rule_assessment(question, evidence)
            return Assessment(decision, str(data.get("summary", "")), str(data.get("reasoning", "")), cited, list(data.get("questions_for_claimant", [])), DISCLAIMER, list(data.get("conditions", [])), list(data.get("exclusions", [])))
        except Exception:
            pass
    return _rule_assessment(question, evidence)
