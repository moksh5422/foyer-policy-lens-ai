# Policy Lens AI — Insurance Claim Coverage Assistant

A Foyer-inspired portfolio project demonstrating an end-to-end AI workflow for insurance policy analysis. It ingests synthetic policy documents, retrieves relevant evidence, assesses a question against that evidence, cites the clauses used, and explicitly handles uncertainty.

> **Demo only.** Uses synthetic policies and is not insurance, legal, or claims advice.

## Features

- Multi-format ingestion: PDF, Word, Excel, PowerPoint, TXT and Markdown.
- Local lexical + TF-IDF retrieval (hybrid-style retrieval baseline).
- Bounded outcomes: `COVERED`, `NOT COVERED`, `CONDITIONAL`, `UNCLEAR`.
- Evidence snippets and source identifiers.
- Streamlit UI and FastAPI endpoint.
- Optional OpenAI structured-reasoning path with a deterministic local fallback.
- Evaluation cases, unit tests, Docker Compose and GitHub Actions CI.

## Run locally

```bash
python -m venv .venv
# Windows: .venv\\Scripts\\activate
# macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
streamlit run app.py
```

Run the API in another terminal:

```bash
uvicorn api:app --reload --port 8000
```

- UI: http://localhost:8501
- API health: http://localhost:8000/health
- API docs: http://localhost:8000/docs

## Optional OpenAI reasoning

Copy `.env.example` to `.env`, set `OPENAI_API_KEY`, and start the app from an environment where these variables are loaded. Never commit secrets. The local assessment remains available without an API key.

## Docker Compose

```bash
docker compose up --build
```

## Tests and evaluation

```bash
pytest -q
python run_evaluation.py
```

The included benchmark contains eight synthetic cases and is a smoke test only. Its accuracy is not a claim about real-world insurance performance. Production usage would require a broader, human-labelled evaluation set and expert review.

## Architecture

1. Extract text from policy files and preserve source metadata.
2. Split document text into retrievable chunks.
3. Retrieve relevant evidence using lexical overlap and TF-IDF cosine similarity.
4. Assess only against retrieved evidence.
5. Return a bounded decision, reasoning, evidence references, and review steps.

See [architecture](docs/architecture.md) and [evaluation](docs/evaluation.md).

## Production evolution

A production version could use managed hybrid search (for example Azure AI Search), document-level authorization, policy version/effective-date filtering, PII controls, audit and tracing, expert-labelled evaluation, monitoring, and human-in-the-loop review for unclear or high-impact decisions.

No Foyer confidential or internal data is included; the example policies are synthetic.

## Portfolio positioning

This project demonstrates an end-to-end path from a practical business problem to a modular AI application: ingestion, retrieval, evidence selection, reasoning, structured output, evaluation, UI, API, and deployment scaffolding. See [Portfolio Demonstration Notes](docs/portfolio-notes.md) for design decisions and limitations.
