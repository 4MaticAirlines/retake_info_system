import re

from app.core.constants import BAD_DEBT_MARKERS, BROKEN_MARKER_REPLACEMENTS


class DebtExtractor:
    @staticmethod
    def _normalize_text(text: str) -> str:
        text = text.replace("\r", "\n")

        for old_value, new_value in BROKEN_MARKER_REPLACEMENTS.items():
            text = text.replace(old_value, new_value)

        text = re.sub(r"(\w)-\n(\w)", r"\1\2", text)
        text = re.sub(r"[ \t]+", " ", text)
        text = re.sub(r"\n{2,}", "\n", text)

        return text.strip()

    @staticmethod
    def _extract_group(text: str) -> str:
        patterns = [
            r"академическая группа:\s*([A-Za-zА-Яа-яЁё0-9\-]+)",
            r"группа:\s*([A-Za-zА-Яа-яЁё0-9\-]+)",
        ]

        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return match.group(1).strip().upper()

        return ""

    @staticmethod
    def _is_bad_line(line: str) -> bool:
        lowered = line.lower()
        return any(marker in lowered for marker in BAD_DEBT_MARKERS)

    @staticmethod
    def _extract_discipline_from_line(line: str) -> str:
        line = line.strip()
        line = re.sub(r"^\d+\.\s*", "", line)

        split_match = re.split(
            r"\s+(?:Б\d|ФТД|УП)\.[A-ZА-ЯЁ0-9.\-]+",
            line,
            maxsplit=1,
        )

        if split_match:
            discipline = split_match[0].strip()
        else:
            discipline = line.strip()

        discipline = discipline.strip(" -–—")
        discipline = re.sub(r"\s+", " ", discipline)
        return discipline

    @staticmethod
    def _is_valid_discipline(discipline: str) -> bool:
        if not discipline:
            return False

        lowered = discipline.lower().strip()

        if lowered in BAD_DEBT_MARKERS:
            return False

        if len(lowered) < 4:
            return False

        # одиночные обрывки типа "данных" или "неудовлетворительно" отбрасываем
        if " " not in lowered and lowered not in {"математика", "физика", "информатика"}:
            return False

        return True

    @staticmethod
    def extract_debts(statement_text: str) -> dict:
        normalized_text = DebtExtractor._normalize_text(statement_text)
        lines = [line.strip() for line in normalized_text.split("\n") if line.strip()]

        group = DebtExtractor._extract_group(normalized_text)
        disciplines: list[str] = []
        markers: set[str] = set()

        for index, line in enumerate(lines):
            if not DebtExtractor._is_bad_line(line):
                continue

            lowered = line.lower()

            for marker in BAD_DEBT_MARKERS:
                if marker in lowered:
                    markers.add(marker)

            discipline = DebtExtractor._extract_discipline_from_line(line)

            # если строка развалилась и предмет не распознался нормально —
            # пробуем взять предыдущую строку
            if not DebtExtractor._is_valid_discipline(discipline) and index > 0:
                previous_line = lines[index - 1]
                candidate = DebtExtractor._extract_discipline_from_line(previous_line)
                if DebtExtractor._is_valid_discipline(candidate):
                    discipline = candidate

            if DebtExtractor._is_valid_discipline(discipline) and discipline not in disciplines:
                disciplines.append(discipline)

        return {
            "group": group,
            "disciplines": disciplines,
            "markers": sorted(markers),
        }