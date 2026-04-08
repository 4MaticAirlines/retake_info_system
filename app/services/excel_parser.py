"""
Парсер Excel-файлов с пересдачами.

Почему нужен отдельный парсер:
- кафедры оформляют Excel по-разному;
- заголовки часто содержат переносы строк;
- merged cells дают пустые ячейки в середине таблицы.

Задача этого файла:
1. Открыть все Excel-файлы.
2. Найти строку заголовков.
3. Прочитать таблицу построчно.
"""

import re
import warnings
from pathlib import Path

import pandas as pd

from app.core.config import INPUT_DIR


class ExcelParser:
    """
    Парсер Excel-файлов кафедр.
    """

    def __init__(self, input_dir: Path = INPUT_DIR):
        self.input_dir = input_dir

    def get_excel_files(self) -> list[Path]:
        """
        Возвращает все Excel-файлы из папки input.

        Важно:
        - не делим файлы на manual/site;
        - берём все .xls и .xlsx.
        """
        if not self.input_dir.exists():
            return []

        files = []
        for file_path in self.input_dir.iterdir():
            if not file_path.is_file():
                continue

            if file_path.name.startswith("."):
                continue

            if file_path.suffix.lower() not in {".xls", ".xlsx"}:
                continue

            files.append(file_path)

        return sorted(files)

    @staticmethod
    def _resolve_engine(file_path: Path) -> str | None:
        """
        Выбирает движок чтения Excel по расширению файла.
        """
        if file_path.suffix.lower() == ".xls":
            return "xlrd"
        if file_path.suffix.lower() == ".xlsx":
            return "openpyxl"
        return None

    @staticmethod
    def _clean_cell(value) -> str:
        """
        Нормализует значение ячейки:
        - убирает NaN;
        - заменяет переводы строк пробелами;
        - схлопывает лишние пробелы.
        """
        if pd.isna(value):
            return ""

        text = str(value)
        text = text.replace("\r", " ").replace("\n", " ")
        text = re.sub(r"\s+", " ", text).strip()
        return text

    @staticmethod
    def _normalize_header(value: str) -> str:
        """
        Нормализует заголовок таблицы для сравнения.

        Пример:
        'Дата  проведения\\n  пересдачи'
        -> 'дата проведения пересдачи'
        """
        value = ExcelParser._clean_cell(value).lower()
        return value

    @staticmethod
    def _is_header_row(values: list[str]) -> bool:
        """
        Проверяет, является ли строка строкой заголовков.

        Мы не требуем идеального совпадения, потому что в Excel
        заголовки могут быть длинными, с переносами строк и пробелами.
        """
        normalized_values = {ExcelParser._normalize_header(value) for value in values if value.strip()}

        required_patterns = [
            "дисциплина",
            "преподаватель",
            "группы",
            "дата проведения пересдачи",
            "время проведения пересдачи",
            "аудитория",
        ]

        for pattern in required_patterns:
            if not any(pattern in cell for cell in normalized_values):
                return False

        return True

    def _find_header_rows(self, df_raw: pd.DataFrame) -> list[int]:
        """
        Ищет строки, похожие на строку заголовков таблицы.
        """
        header_rows = []

        for index, row in df_raw.iterrows():
            values = [self._clean_cell(value) for value in row.tolist()]
            if self._is_header_row(values):
                header_rows.append(index)

        return header_rows

    def _parse_sheet(self, file_path: Path, sheet_name: str, df_raw: pd.DataFrame) -> list[dict]:
        """
        Разбирает один лист Excel в список словарей.
        """
        parsed_rows: list[dict] = []

        header_rows = self._find_header_rows(df_raw)
        if not header_rows:
            return parsed_rows

        for position, header_row_index in enumerate(header_rows):
            header_values = [
                self._clean_cell(value) if self._clean_cell(value) else f"Unnamed: {idx}"
                for idx, value in enumerate(df_raw.iloc[header_row_index].tolist())
            ]

            next_header_index = header_rows[position + 1] if position + 1 < len(header_rows) else len(df_raw)

            body_df = df_raw.iloc[header_row_index + 1:next_header_index].copy()
            if body_df.empty:
                continue

            body_df.columns = header_values
            body_df = body_df.dropna(how="all")

            # Протягиваем merged cells вниз.
            body_df = body_df.ffill().fillna("")

            for _, row in body_df.iterrows():
                row_dict = {
                    column_name: self._clean_cell(value)
                    for column_name, value in row.to_dict().items()
                }

                parsed_rows.append(
                    {
                        "source_file": file_path.name,
                        "sheet_name": sheet_name,
                        "row_data": row_dict,
                    }
                )

        return parsed_rows

    def parse_file(self, file_path: Path) -> list[dict]:
        """
        Разбирает один Excel-файл.
        """
        parsed_rows: list[dict] = []
        engine = self._resolve_engine(file_path)

        try:
            with warnings.catch_warnings():
                warnings.simplefilter("ignore", UserWarning)
                excel_file = pd.ExcelFile(file_path, engine=engine)

            for sheet_name in excel_file.sheet_names:
                with warnings.catch_warnings():
                    warnings.simplefilter("ignore", UserWarning)
                    df_raw = pd.read_excel(
                        file_path,
                        sheet_name=sheet_name,
                        engine=engine,
                        header=None,
                        dtype=object,
                    )

                df_raw = df_raw.dropna(how="all")
                parsed_rows.extend(self._parse_sheet(file_path, sheet_name, df_raw))

        except Exception as error:
            parsed_rows.append(
                {
                    "source_file": file_path.name,
                    "sheet_name": None,
                    "row_data": {"error": str(error)},
                }
            )

        return parsed_rows

    def parse_all_files(self) -> list[dict]:
        """
        Разбирает все Excel-файлы из папки input.
        """
        all_rows: list[dict] = []

        for file_path in self.get_excel_files():
            all_rows.extend(self.parse_file(file_path))

        return all_rows