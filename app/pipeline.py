from pathlib import Path
from .ingestion import ingest_file, chunk_document
from .retrieval import HybridRetriever
from .decision import assess
from .models import Assessment

class PolicyLensPipeline:
    def __init__(self, chunks):
        self.chunks = chunks
        self.retriever = HybridRetriever(chunks)

    @classmethod
    def from_paths(cls, paths):
        documents = []
        for path in paths:
            documents.extend(ingest_file(path))
        return cls(chunk_document(documents))

    def answer(self, question: str, top_k: int = 5, use_llm: bool = False, model: str = "gpt-4o-mini") -> Assessment:
        evidence = self.retriever.search(question, top_k=top_k)
        return assess(question, evidence, use_llm=use_llm, model=model)
