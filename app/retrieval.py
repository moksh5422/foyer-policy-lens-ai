import re
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from .models import DocumentChunk, Evidence

class HybridRetriever:
    """Local retrieval combining lexical overlap and TF-IDF cosine similarity."""
    def __init__(self, chunks: list[DocumentChunk]):
        self.chunks = chunks
        self.vectorizer = None
        self.matrix = None
        texts = [c.text for c in chunks]
        if any(t.strip() for t in texts):
            self.vectorizer = TfidfVectorizer(ngram_range=(1, 2), stop_words="english")
            self.matrix = self.vectorizer.fit_transform(texts)

    @staticmethod
    def _terms(text: str) -> set[str]:
        stop = {"the", "and", "is", "are", "was", "were", "for", "with", "this", "that", "covered", "coverage", "policy", "claim"}
        return set(re.findall(r"[a-z0-9]+", text.lower())) - stop

    def search(self, query: str, top_k: int = 5) -> list[Evidence]:
        if not self.chunks or not query.strip() or self.matrix is None:
            return []
        qterms = self._terms(query)
        qvec = self.vectorizer.transform([query])
        semantic = cosine_similarity(qvec, self.matrix).ravel().tolist()
        scored = []
        for i, chunk in enumerate(self.chunks):
            chunk_terms = self._terms(chunk.text)
            lexical = len(qterms & chunk_terms) / max(1, len(qterms))
            score = 0.58 * lexical + 0.42 * semantic[i]
            if score > 0:
                scored.append((score, chunk))
        scored.sort(key=lambda x: x[0], reverse=True)
        return [Evidence(text=chunk.text, source=chunk.source, score=round(score, 4), page=chunk.page, section=chunk.section, chunk_id=f"{chunk.document_id}:chunk-{idx+1}") for idx, (score, chunk) in enumerate(scored[:max(1, top_k)])]
