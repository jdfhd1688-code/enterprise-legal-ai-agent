"""Document-level Pydantic models shared by parser, chunker and storage."""

from __future__ import annotations

from pydantic import BaseModel, Field


class DocumentPage(BaseModel):
    source: str
    page_no: int
    text: str
    section: str = "main"


class ParsedDocument(BaseModel):
    source: str
    title: str
    pages: list[DocumentPage]
    file_size: int
    content_type: str
    parse_warnings: list[str] = Field(default_factory=list)
    num_pages: int = 0
    text_length: int = 0


class DocumentChunk(BaseModel):
    chunk_id: str
    source: str
    page_no: int | None = None
    section: str
    text: str

    @property
    def evidence_label(self) -> str:
        if self.page_no:
            return f"{self.source} 第{self.page_no}页 {self.section}"
        return f"{self.source} {self.section}"
