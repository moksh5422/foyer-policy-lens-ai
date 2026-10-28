import re
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from .models import DocumentChunk, Evidence

class HybridRetriever:
    """Local hybrid-style retrieval combining lexical overlap and TF-IDF similarity."""
    def __init__(self, chunks: list[DocumentChunk]):
        self.chunks = chunks
        self.texts = [c.text for c in chunks]
        self.vectorizer = TfidfVectorizer(ngram_range=(1, 2), stop_words="english")
        self.matrix = self.vectorizer.fit_transform(self.texts) if any(t.strip() for t in self.texts) else None

    @staticmethod
    def _terms(text: str) -> set[str]:
        stop = {"the", "and", "is", "are", "was", "were", "for", "with", "this", "that", "covered", "coverage", "policy", "claim"}
        return set(re.findall(r"[a-z0-9]+", text.lower())) - stop

    def search(self, query: str, top_k: int = 5) -> list[Evidence]:
        if not self.chunks or not query.strip():
            return []
        qterms = self._terms(query)
        if self.matrix is not None:
            qvec = self.vectorizer.transform([query])
            semantic = cosine_similarity(qvec, self.matrix).ravel().tolist()
        else:
            semantic = [0.0] * len(self.chunks)
        scored = []
        for i, chunk in enumerate(self.chunks):
            terms = self._terms(chunk.text)
            lexical = len(qterms & terms) / max(1, len(qterms))
            score = 0.58 * lexical + 0.42 * semantic[i]
            if score > 0:
                scored.append((score, chunk))
        scored.sort(key=lambda x: x[0], reverse=True)
        return [Evidence(text=c.text, source=c.source, score=round(s, 4), page=c.page, section=c.section, chunk_id=f"{c.document_id}:{i+1}") for i, (s, c) in enumerate(scored[:max(1, top_k)])]
