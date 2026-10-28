# Evaluation

The evaluation set contains eight synthetic questions spanning clear coverage, explicit exclusions, conditional clauses, and unseen policy topics.

Run:

```bash
python run_evaluation.py
pytest -q
```

The deterministic local path is used by default so contributors can reproduce results without an API key. The optional LLM path should be evaluated separately against a substantially larger, human-reviewed benchmark before any real claims workflow. Measure not just decision accuracy but evidence citation validity, abstention quality, retrieval recall, latency, and reviewer override rate.
