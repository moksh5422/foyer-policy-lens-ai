# Portfolio Demonstration Notes

## Problem
Insurance policy language is distributed across long documents, and exclusions can change a claim outcome. A user needs a clear, traceable first-pass answer without the system inventing policy clauses.

## Solution
Policy Lens AI accepts multiple policy files, extracts text, splits it into chunks, retrieves relevant evidence with lexical and TF-IDF similarity, and returns a bounded coverage outcome with source references and follow-up steps. A Streamlit interface and FastAPI endpoint expose the same pipeline.

## Engineering choices
- Modules separate ingestion, retrieval, assessment and interface code.
- Synthetic policies keep private insurer and customer information out of the repository.
- The default local path works without an API key.
- Optional structured LLM assessment is constrained to provided evidence and falls back locally on errors or invalid citations.
- An evaluation set and automated tests make sample behaviours inspectable.

## Limitations and next steps
- Local TF-IDF retrieval is a baseline, not a production vector-search platform.
- The eight-case synthetic benchmark is a smoke test; its score should not be generalized to real claims.
- Production requires policy versioning, access control, PII minimisation, audit trails, human review, and a larger expert-labelled benchmark.
- A future iteration could use Azure AI Search, policy metadata filters, citation validation, and reviewer feedback.
