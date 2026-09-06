"""PDF text extraction tool.

PyMuPDF is preferred; pypdf is a fallback so the repo can still boot on a
minimal Python install. The caller receives per-page text, never fabricated
content.
"""

from __future__ import annotations

import io
from dataclasses import dataclass


class PDFParseError(RuntimeError):
    pass


@dataclass
class PDFPageText:
    page_no: int
    text: str


def _normalize(text: str) -> str:
    return "\n".join(line.rstrip() for line in text.replace("\x00", "").splitlines()).strip()


def _extract_with_pymupdf(data: bytes) -> list[PDFPageText]:
    try:
        import pymupdf as fitz  # type: ignore
    except ImportError as exc:  # pragma: no cover - depends on install
        raise PDFParseError("PyMuPDF 未安装，无法使用首选 PDF 解析器。") from exc

    try:
        document = fitz.open(stream=data, filetype="pdf")
        pages: list[PDFPageText] = []
        for page_no in range(document.page_count):
            page = document.load_page(page_no)
            text = _normalize(page.get_text("text"))
            pages.append(PDFPageText(page_no=page_no + 1, text=text))
        document.close()
        return pages
    except Exception as exc:  # noqa: BLE001 - surface every PDF failure clearly
        raise PDFParseError(f"PDF 解析失败：{exc}") from exc


def _extract_with_pypdf(data: bytes) -> list[PDFPageText]:
    try:
        from pypdf import PdfReader  # type: ignore
    except ImportError as exc:
        raise PDFParseError("环境中没有可用 PDF 解析器（需要 PyMuPDF 或 pypdf）。") from exc

    try:
        reader = PdfReader(io.BytesIO(data))
        if reader.is_encrypted:
            try:
                reader.decrypt("")
            except Exception as exc:  # noqa: BLE001
                raise PDFParseError("PDF 已加密，请先移除密码后再上传。") from exc
        pages = [
            PDFPageText(page_no=idx + 1, text=_normalize(page.extract_text() or ""))
            for idx, page in enumerate(reader.pages)
        ]
        return pages
    except Exception as exc:  # noqa: BLE001
        raise PDFParseError(f"PDF 解析失败：{exc}") from exc


class PdfTool:
    """Tool that extracts real text from uploaded PDF bytes."""

    @staticmethod
    def extract(data: bytes) -> list[PDFPageText]:
        if not data:
            raise PDFParseError("上传文件为空，无法解析。")
        try:
            pages = _extract_with_pymupdf(data)
        except ImportError:
            pages = _extract_with_pypdf(data)
        except PDFParseError:
            # pypdf is independent and may still handle the same file.
            pages = _extract_with_pypdf(data)
        if not pages:
            raise PDFParseError("PDF 没有可提取页面。")
        if all(not page.text for page in pages):
            raise PDFParseError("PDF 中没有可提取文本（可能是扫描件）。MVP 暂不提供 OCR。")
        return pages
