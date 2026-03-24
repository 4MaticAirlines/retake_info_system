from pathlib import Path

from docx import Document
from pypdf import PdfReader


class StatementParser:
    @staticmethod
    def parse_statement(file_path: Path) -> str:
        suffix = file_path.suffix.lower()

        if suffix == ".txt":
            return file_path.read_text(encoding="utf-8", errors="ignore")

        if suffix == ".docx":
            document = Document(file_path)
            paragraphs = [paragraph.text for paragraph in document.paragraphs]
            return "\n".join(paragraphs)

        if suffix == ".pdf":
            reader = PdfReader(str(file_path))
            pages_text: list[str] = []

            for page in reader.pages:
                page_text = page.extract_text() or ""
                pages_text.append(page_text)

            return "\n".join(pages_text)

        raise ValueError("Поддерживаются только файлы .txt, .docx и .pdf")