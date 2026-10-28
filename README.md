# Foyer Policy Lens AI

An evidence-grounded insurance policy coverage assistant built as a demonstration project for AI engineering recruitment. It retrieves relevant policy clauses, produces a coverage assessment, cites supporting evidence, and explicitly flags ambiguity rather than inventing certainty.

> Demo only. Uses synthetic policy documents and is not insurance, legal, or claims advice.

## Features

- Ingests PDF, DOCX, XLSX, PPTX, TXT, and Markdown policy documents.
- Hybrid-style local retrieval using lexical matching and TF-IDF cosine similarity.
- Coverage outcomes: `COVERED`, `NOT COVERED`, `CONDITIONAL`, or `UNCLEAR`.
- Evidence snippets with document/page/section metadata where available.
- Streamlit user interface and FastAPI endpoint.
- Evaluation cases, automated tests, Docker Compose, and GitHub Actions CI.
- Optional OpenAI-backed structured assessment; deterministic local fallback.

## Run locally

```bash
python -m venv .venv
# Windows: .venv\\Scripts\\activate
# macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
streamlit run app.py
```

In another terminal, run the API:

```bash
uvicorn api:app --reload --port 8000
```

Optional model configuration: copy `.env.example` to `.env` and configure your OpenAI API key and model. Do not commit secrets.

## Docker

```bash
docker compose up --build
```

## Evaluate and test

```bash
python run_evaluation.py
pytest -q
```

The included evaluation set is deliberately small and synthetic; scores describe only those cases and are not a claim of real-world insurance performance.

## Repository layout

```text
app/                    ingestion, retrieval, decision, pipeline, evaluation
app.py                  Streamlit interface
api.py                  FastAPI service
 data/policies/          synthetic demo policies
data/evaluation/        evaluation questions and expected outcomes
data/demo_claim.json    sample claim
 tests/                  automated tests
docs/                   architecture and evaluation notes
.github/workflows/       CI workflow
```

## Architecture

1. Extract text and metadata from uploaded policy documents.
2. Split content into retrievable chunks while preserving document references.
3. Retrieve relevant clauses with local lexical and TF-IDF matching.
4. Assess the claim against evidence and return a bounded outcome with citations.
5. Ask for human review when evidence is incomplete or conflicting.

See [`docs/architecture.md`](docs/architecture.md) and [`docs/evaluation.md`](docs/evaluation.md).

## Production considerations

For a production setting, replace local retrieval with a managed hybrid search service such as Azure AI Search, add authenticated access and per-policy authorization, enforce PII minimisation/retention, monitor retrieval and answer quality, expand evaluation with expert-labelled cases, and route ambiguous or high-impact decisions to a qualified human reviewer.

## License

This repository is provided for demonstration and learning. Add an explicit license before reuse or redistribution.
