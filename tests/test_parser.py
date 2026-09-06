from __future__ import annotations

import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

from app.skills.document_parser import DocumentParserError, DocumentParserSkill


class ParserTests(unittest.TestCase):
    def setUp(self) -> None:
        self.parser = DocumentParserSkill()
        self.high_pdf = ROOT / "data" / "contracts" / "sample_contract_high_risk.pdf"

    def test_parses_sample_pdf(self) -> None:
        parsed = self.parser.parse(self.high_pdf.name, self.high_pdf.read_bytes())
        self.assertGreaterEqual(parsed.num_pages, 1)
        self.assertGreater(parsed.text_length, 100)
        self.assertTrue(any("违约金" in page.text for page in parsed.pages))

    def test_rejects_invalid_extension(self) -> None:
        with self.assertRaises(DocumentParserError):
            self.parser.parse("notes.exe", b"not an app file")

    def test_rejects_empty_payload(self) -> None:
        with self.assertRaises(DocumentParserError):
            self.parser.parse("empty.pdf", b"")


if __name__ == "__main__":
    unittest.main()

