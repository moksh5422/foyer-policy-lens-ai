# Architecture

```text
PDF / DOCX / XLSX / PPTX / TXT / Markdown
                 |
                 v
       Ingestion and chunking
   text extraction + source metadata
                 |
                 v
        Hybrid-style retrieval
  lexical overlap + TF-IDF similarity
                 |
                 v
          Evidence selection
                 |
        +--------+--------+
        |                 |
        v                 v
 Local rule reasoning   Optional OpenAI
        |                 |
        +--------+--------+
                 v
 COVERED / NOT COVERED / CONDITIONAL / UNCLEAR
                 |
                 v
 explanation + source citations + next steps
```

The application keeps ingestion, retrieval, assessment, and user experience in separate modules. Local retrieval is intentionally lightweight and reproducible. A production implementation could replace it with Azure AI Search or another managed hybrid-search service without changing the core UI contract.

## Safety and operational boundaries

- Demo policies are synthetic.
- Unsupported or ambiguous cases should be escalated instead of inventing policy wording.
- Real deployments need authentication, document-level authorization, retention controls, PII handling, audit logs, policy version/effective-date filtering, and human review.
- The included benchmark is a smoke test, not evidence of production performance.
