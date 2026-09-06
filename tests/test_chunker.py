from __future__ import annotations

import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

from app.schemas.document import DocumentPage, ParsedDocument
from app.skills.chunker import ChunkerSkill


class ChunkerTests(unittest.TestCase):
    def setUp(self) -> None:
        self.chunker = ChunkerSkill()

    def test_chunks_with_metadata(self) -> None:
        parsed = ParsedDocument(
            source="demo.txt",
            title="demo",
            pages=[
                DocumentPage(
                    source="demo.txt",
                    page_no=1,
                    text="第一条 标的\n甲方提供货物。\n第二条 付款\n甲方逾期付款应支付违约金。",
                )
            ],
            file_size=100,
            content_type="txt",
            num_pages=1,
            text_length=80,
        )
        chunks = self.chunker.chunk(parsed)
        self.assertGreaterEqual(len(chunks), 2)
        self.assertTrue(all(chunk.source == "demo.txt" for chunk in chunks))
        self.assertTrue(all(chunk.page_no == 1 for chunk in chunks))
        self.assertTrue(all(chunk.section for chunk in chunks))

    def test_chunks_long_text(self) -> None:
        text = ("这是一段用于验证长文本切分的合同内容。" * 120)
        parsed = ParsedDocument(
            source="long.txt",
            title="long",
            pages=[DocumentPage(source="long.txt", page_no=1, text=text)],
            file_size=1,
            content_type="txt",
            num_pages=1,
            text_length=len(text),
        )
        chunks = self.chunker.chunk(parsed)
        self.assertGreater(len(chunks), 1)
        self.assertTrue(all(len(chunk.text) <= 1100 for chunk in chunks))


if __name__ == "__main__":
    unittest.main()

