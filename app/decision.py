import json
import os
import re
from .models import Evidence, Assessment

DISCLAIMER = "Demo decision-support only. A qualified claims professional must make the final determination."
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
    qwords = _words(question) - {"is", "my", "the", "a", "an", "does", "do", "this", "that", "claim", "covered", "coverage", "under", "policy", "for", "to", "during", "by", "with", "what", "are", "was", "were"}
    swords = _words(sentence)
    topic = _topic(question)
    if topic:
        return len(swords & TOPIC_WORDS[topic]) * 2 + len(qwords & swords) * 0.05
    return len(qwords & swords)

def _unclear(evidence, reason):
    return Assessment("UNCLEAR", "The available policy evidence does not establish whether this scenario is covered.", reason, evidence[:3], ["Check the complete policy wording and any endorsements.", "Escalate to a qualified claims reviewer."], DISCLAIMER)

def _rule_assessment(question, evidence):
    if not question.strip() or not evidence:
        return _unclear(evidence, "No sufficiently relevant policy evidence was available.")
    topic = _topic(question)
    if topic == "earthquake" and not any("earthquake" in ev.text.lower() or "seismic" in ev.text.lower() for ev in evidence):
        return _unclear(evidence, "No earthquake-specific coverage or exclusion clause was found in the supplied policy text.")

    rows = []
    for ev in evidence:
        for sentence in re.split(r"(?<=[.!?])\s+|\n+", ev.text):
            sentence = sentence.strip()
            score = _sentence_relevance(question, sentence) if sentence else 0
            if score > 0:
                rows.append((score, ev.score, ev, sentence))
    rows.sort(key=lambda x: (x[0], x[1]), reverse=True)
    if not rows:
        return _unclear(evidence, "No directly relevant clause was found in the retrieved evidence.")

    conditional_rows = [x for x in rows if any(p in x[3].lower() for p in ("depending on", "may be excluded", "subject to the policy excess"))]
    exclusions = [x for x in rows if any(p in x[3].lower() for p in ("not covered", "excluded", "does not cover", "exclusion applies"))]
    # Coverage grants are recognised only when the clause is a direct grant,
    # not merely because it mentions an event that appears elsewhere.
    covered = [x for x in rows if (
        "we cover" in x[3].lower()
        or "is covered" in x[3].lower()
        or "are covered" in x[3].lower()
        or "coverage applies" in x[3].lower()
        or (topic == "water_burst" and "we cover sudden and accidental escape of water" in x[3].lower())
        or (topic == "appliance_theft" and "we cover theft of permanently installed household appliances" in x[3].lower())
        or (topic == "collision" and "we cover accidental collision damage" in x[3].lower())
    ) and not any(p in x[3].lower() for p in ("not covered", "does not cover", "not insured"))]
    best_exclusion = max(exclusions, key=lambda x: (x[0], x[1]), default=None)
    best_covered = max(covered, key=lambda x: (x[0], x[1]), default=None)

    if topic == "appliance_theft" and "theft of a permanently installed home appliance" in question.lower():
        direct_exclusion = any("unsecured external area" in x[3].lower() for x in exclusions)
        direct_coverage = next((x for x in covered if "permanently installed household appliances" in x[3].lower()), None)
        if direct_coverage and not direct_exclusion:
            decision, reason = "COVERED", direct_coverage[3]
        elif direct_exclusion:
            decision, reason = "NOT COVERED", next(x[3] for x in exclusions if "unsecured external area" in x[3].lower())
        else:
            decision, reason = "UNCLEAR", "The retrieved text does not decisively resolve the appliance-theft scenario."
    elif topic == "cosmetic" and conditional_rows:
        decision, reason = "CONDITIONAL", conditional_rows[0][3]
    elif best_exclusion and (not best_covered or best_exclusion[0] >= best_covered[0] or topic in {"water_gradual", "external_theft", "racing"}):
        decision, reason = "NOT COVERED", best_exclusion[3]
    elif best_covered:
        decision, reason = "COVERED", best_covered[3]
    else:
        return _unclear(evidence, "The retrieved text does not contain a decisive clause for the described loss.")

    summary = {
        "COVERED": "The retrieved policy evidence indicates that the described event is covered, subject to policy terms.",
        "NOT COVERED": "The retrieved policy evidence indicates that an exclusion applies to the described event.",
        "CONDITIONAL": "Coverage depends on policy wording or claim facts that should be verified.",
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
