"""Page-aware manual ingestion and hybrid retrieval for GridPulse.

The MVP uses a deterministic hashing embedder so retrieval works offline. The
``TextEmbedder`` protocol is intentionally small: a sentence-transformer can
replace it later without changing the index or citation contract.
"""

from __future__ import annotations

import hashlib
import math
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Protocol


TOKEN_PATTERN = re.compile(r"[a-z0-9][a-z0-9_-]*", re.IGNORECASE)
PAGE_PATTERN = re.compile(r"(?m)^##\s+Page\s+(\d+)\s*$")


@dataclass(frozen=True, slots=True)
class DocumentChunk:
    chunk_id: str
    document_id: str
    title: str
    text: str
    source_uri: str
    page: int
    metadata: dict[str, str] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.chunk_id.strip() or not self.document_id.strip():
            raise ValueError("chunk_id and document_id cannot be empty")
        if not self.title.strip() or not self.text.strip():
            raise ValueError("chunk title and text cannot be empty")
        if not self.source_uri.strip():
            raise ValueError("source_uri cannot be empty")
        if self.page < 1:
            raise ValueError("page must be positive")


@dataclass(frozen=True, slots=True)
class RetrievedEvidence:
    chunk: DocumentChunk
    score: float
    lexical_score: float
    vector_score: float

    def citation(self) -> str:
        return f"{self.chunk.title}, p. {self.chunk.page} ({self.chunk.source_uri})"


class TextEmbedder(Protocol):
    def embed(self, text: str) -> tuple[float, ...]: ...


class HashingEmbedder:
    """Deterministic offline vector baseline using hashed token features."""

    def __init__(self, dimensions: int = 256) -> None:
        if dimensions < 16:
            raise ValueError("dimensions must be at least 16")
        self.dimensions = dimensions

    def embed(self, text: str) -> tuple[float, ...]:
        vector = [0.0] * self.dimensions
        tokens = _tokenize(text)
        for token in tokens:
            index = _stable_index(token, self.dimensions)
            vector[index] += 1.0
        for first, second in zip(tokens, tokens[1:]):
            index = _stable_index(f"{first}:{second}", self.dimensions)
            vector[index] += 0.5
        magnitude = math.sqrt(sum(value * value for value in vector))
        if magnitude == 0:
            return tuple(vector)
        return tuple(value / magnitude for value in vector)


class ManualIngestor:
    """Ingest page-marked Markdown or plain text into searchable chunks."""

    def __init__(self, max_chars: int = 900) -> None:
        if max_chars < 100:
            raise ValueError("max_chars must be at least 100")
        self.max_chars = max_chars

    def ingest_path(self, path: str | Path, *, document_id: str | None = None) -> tuple[DocumentChunk, ...]:
        file_path = Path(path)
        text = file_path.read_text(encoding="utf-8")
        return self.ingest_text(
            text,
            document_id=document_id or file_path.stem,
            title=file_path.stem.replace("-", " ").title(),
            source_uri=str(file_path),
        )

    def ingest_text(
        self,
        text: str,
        *,
        document_id: str,
        title: str,
        source_uri: str,
    ) -> tuple[DocumentChunk, ...]:
        pages = _split_pages(text)
        chunks: list[DocumentChunk] = []
        sequence = 0
        for page, page_text in pages:
            for chunk_text in _chunk_paragraphs(page_text, self.max_chars):
                sequence += 1
                chunks.append(
                    DocumentChunk(
                        chunk_id=f"{document_id}-p{page}-c{sequence}",
                        document_id=document_id,
                        title=title,
                        text=chunk_text,
                        source_uri=source_uri,
                        page=page,
                    )
                )
        return tuple(chunks)


class HybridIndex:
    """Small in-memory lexical/vector index with citation-preserving results."""

    def __init__(self, embedder: TextEmbedder | None = None) -> None:
        self.embedder = embedder or HashingEmbedder()
        self._entries: list[tuple[DocumentChunk, tuple[str, ...], tuple[float, ...]]] = []

    def add(self, chunks: tuple[DocumentChunk, ...] | list[DocumentChunk]) -> None:
        for chunk in chunks:
            self._entries.append((chunk, _tokenize(chunk.text), self.embedder.embed(chunk.text)))

    def retrieve(
        self,
        query: str,
        *,
        top_k: int = 5,
        metadata: dict[str, str] | None = None,
    ) -> tuple[RetrievedEvidence, ...]:
        if not query.strip():
            raise ValueError("query cannot be empty")
        if top_k < 1:
            raise ValueError("top_k must be positive")
        query_tokens = set(_tokenize(query))
        query_vector = self.embedder.embed(query)
        scored: list[RetrievedEvidence] = []
        for chunk, tokens, vector in self._entries:
            if metadata and any(chunk.metadata.get(key) != value for key, value in metadata.items()):
                continue
            lexical_score = _lexical_score(query_tokens, tokens)
            vector_score = _cosine(query_vector, vector)
            score = 0.65 * lexical_score + 0.35 * vector_score
            scored.append(RetrievedEvidence(chunk, score, lexical_score, vector_score))
        scored.sort(key=lambda result: (-result.score, result.chunk.chunk_id))
        return tuple(scored[:top_k])

    def context(self, query: str, *, top_k: int = 5) -> str:
        results = self.retrieve(query, top_k=top_k)
        return "\n\n".join(
            f"[{index}] {result.chunk.text}\nSource: {result.citation()}"
            for index, result in enumerate(results, start=1)
        )


def _split_pages(text: str) -> list[tuple[int, str]]:
    matches = list(PAGE_PATTERN.finditer(text))
    if not matches:
        return [(1, text)]
    pages: list[tuple[int, str]] = []
    for index, match in enumerate(matches):
        page = int(match.group(1))
        end = matches[index + 1].start() if index + 1 < len(matches) else len(text)
        page_text = text[match.end() : end].strip()
        if page_text:
            pages.append((page, page_text))
    return pages


def _chunk_paragraphs(text: str, max_chars: int) -> list[str]:
    paragraphs = [paragraph.strip() for paragraph in re.split(r"\n\s*\n", text) if paragraph.strip()]
    chunks: list[str] = []
    current = ""
    for paragraph in paragraphs:
        if len(paragraph) <= max_chars and current and len(current) + len(paragraph) + 2 > max_chars:
            chunks.append(current)
            current = ""
        if len(paragraph) > max_chars:
            if current:
                chunks.append(current)
                current = ""
            chunks.extend(paragraph[start : start + max_chars] for start in range(0, len(paragraph), max_chars))
        else:
            current = f"{current}\n\n{paragraph}".strip()
    if current:
        chunks.append(current)
    return chunks


def _tokenize(text: str) -> tuple[str, ...]:
    return tuple(TOKEN_PATTERN.findall(text.lower()))


def _stable_index(value: str, dimensions: int) -> int:
    digest = hashlib.sha256(value.encode("utf-8")).digest()
    return int.from_bytes(digest[:8], byteorder="big") % dimensions


def _lexical_score(query_tokens: set[str], document_tokens: tuple[str, ...]) -> float:
    if not query_tokens or not document_tokens:
        return 0.0
    document_set = set(document_tokens)
    return len(query_tokens & document_set) / len(query_tokens)


def _cosine(first: tuple[float, ...], second: tuple[float, ...]) -> float:
    if not first or not second:
        return 0.0
    return max(0.0, sum(left * right for left, right in zip(first, second)))
