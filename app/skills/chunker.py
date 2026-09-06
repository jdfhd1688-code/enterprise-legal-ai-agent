"""Structure-aware chunker that preserves source, page and section metadata."""

from __future__ import annotations

import re

from app.schemas.document import DocumentChunk, ParsedDocument

_SECTION_MARKER = re.compile(
    r"(?m)^\s*(第\s*[0-9一二三四五六七八九十百千]+\s*[条款章]|"
    r"[一二三四五六七八九十]+[、.．]\s*[^\n]{0,30}|"
    r"\d{1,2}[、.．]\s*[^\n]{0,30})"
)
_SENTENCE_BOUNDARY = re.compile(r"(?<=[。！？；;])\s*|\n+")


class ChunkerSkill:
    """Splits parsed pages into sections / clauses for RAG and evidence links."""

    max_chunk_chars = 900

    def chunk(self, parsed: ParsedDocument) -> list[DocumentChunk]:
        chunks: list[DocumentChunk] = []
        for page in parsed.pages:
            page_text = page.text.strip()
            if not page_text:
                continue
            sections = self._sections(page_text)
            for section_index, (title, body) in enumerate(sections, start=1):
                body = (title + "\n" + body).strip()
                for piece_index, piece in enumerate(self._split_long(body), start=1):
                    if not piece.strip():
                        continue
                    chunk_id = f"C{page.page_no:02d}-{section_index:02d}{piece_index:02d}"
                    chunks.append(
                        DocumentChunk(
                            chunk_id=chunk_id,
                            source=parsed.source,
                            page_no=page.page_no,
                            section=title or f"第{section_index}段",
                            text=piece.strip(),
                        )
                    )
        return chunks

    def _sections(self, text: str) -> list[tuple[str, str]]:
        matches = list(_SECTION_MARKER.finditer(text))
        if len(matches) <= 1:
            paragraphs = [p.strip() for p in re.split(r"\n\s*\n", text) if p.strip()]
            if not paragraphs:
                return [("正文", text)]
            return [("正文", paragraph) for paragraph in paragraphs]
        sections: list[tuple[str, str]] = []
        for pos, match in enumerate(matches):
            start = match.start()
            end = matches[pos + 1].start() if pos + 1 < len(matches) else len(text)
            section_title = text[start : match.end()].strip()
            sections.append((section_title, text[start:end].strip()))
        return sections

    def _split_long(self, text: str) -> list[str]:
        if len(text) <= self.max_chunk_chars:
            return [text]
        pieces: list[str] = []
        buffer = ""
        for sentence in _SENTENCE_BOUNDARY.split(text):
            candidate = f"{buffer}{sentence}"
            if len(candidate) > self.max_chunk_chars and buffer:
                pieces.append(buffer.strip())
                buffer = sentence
            else:
                buffer = candidate
        if buffer.strip():
            pieces.append(buffer.strip())
        if not pieces:
            pieces = [text]
        return pieces
