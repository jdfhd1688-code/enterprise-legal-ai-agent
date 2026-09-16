"""Document-level Pydantic models shared by parser, chunker and storage."""

from __future__ import annotations

from pydantic import BaseModel, Field


class DocumentAnchor(BaseModel):
    document_id: str
    paragraph_index: int
    clause_id: str
    heading: str = ""
    text: str
    anchor_type: str = "paragraph"
    table_index: int | None = None
    row_index: int | None = None
    cell_index: int | None = None
    source_span: tuple[int, int] | None = None


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
    anchors: list[DocumentAnchor] = Field(default_factory=list)


class DocumentChunk(BaseModel):
    chunk_id: str
    source: str
    page_no: int | None = None
    section: str
    text: str
    anchor: DocumentAnchor | None = None

    @property
    def evidence_label(self) -> str:
        if self.page_no:
            return f"{self.source} 第{self.page_no}页 {self.section}"
        return f"{self.source} {self.section}"
