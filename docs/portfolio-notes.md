# Portfolio Demonstration Notes

## Problem
Insurance policy language is distributed across long documents and exclusions can change the outcome. A user needs a clear, traceable first-pass answer without the system inventing policy clauses.

## Solution
Policy Lens AI accepts multiple policy documents, extracts their text, splits the text into chunks, retrieves relevant evidence with lexical and TF-IDF similarity, and returns a bounded coverage outcome with citations and suggested next steps. A Streamlit UI and a FastAPI endpoint expose the same core pipeline.

## Engineering choices
- Modular separation between ingestion, retrieval, assessment and interface.
- Synthetic sample policy documents so the repository contains no private insurer or customer data.
- Local deterministic fallback so the project can be reviewed without an API key.
- Optional structured LLM assessment that only uses provided evidence and fails back to deterministic reasoning when model output is invalid.
- Small test/evaluation suite to make behaviour inspectable.

## Limitations and next improvements
- The current local retrieval baseline is not a production-grade embedding/vector database.
- The sample evaluation dataset is small and synthetic; its score should not be generalized to real claims.
- Production would require policy versioning, access control, PII minimisation, audit trails, human review, and a larger expert-labelled evaluation set.
- Next iteration: add hybrid retrieval backed by Azure AI Search, claim/policy metadata filters, citation validity checks, and a reviewer feedback loop.
