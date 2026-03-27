import re
from typing import Any

from app.core.constants import (
    CONSULTATION_DATE_COLUMN_ALIASES,
    CONSULTATION_ROOM_COLUMN_ALIASES,
    CONSULTATION_TIME_COLUMN_ALIASES,
    DATE_COLUMN_ALIASES,
    DISCIPLINE_COLUMN_ALIASES,
    GROUP_COLUMN_ALIASES,
    HEADER_SKIP_VALUES,
    ROOM_COLUMN_ALIASES,
    TEACHER_COLUMN_ALIASES,
    TIME_COLUMN_ALIASES,
)


class DataNormalizer:
    @staticmethod
    def _clean_text(value: Any) -> str:
        if value is None:
            return ""

        text = str(value).replace("\r", " ").replace("\n", " ").strip()
        text = re.sub(r"\s+", " ", text)
        return text

    @staticmethod
    def _normalize_date(value: Any) -> str:
        text = DataNormalizer._clean_text(value)
        if not text:
            return ""

        text = text.replace("T00:00:00", "")
        text = text.replace(" 00:00:00", "")
        text = text.replace("/", ".")
        text = re.sub(r"\s+", " ", text)
        return text.strip()

    @staticmethod
    def _normalize_time(value: Any) -> str:
        text = DataNormalizer._clean_text(value)
        if not text:
            return ""
        return text.replace(" ", "")

    @staticmethod
    def _normalize_group_token(token: str) -> str:
        token = token.strip().upper()
        token = token.replace("–", "-").replace("—", "-")
        token = re.sub(r"\s+", "", token)
        token = token.strip(" ,;")
        return token

    @staticmethod
    def _extract_groups_from_text(groups_text: str) -> list[str]:
        """
        Более агрессивное извлечение групп из строки.
        Поддерживает:
        - разделение запятыми, точками с запятой, переводами строк
        - строки вида: БЭК-22-ФК-1, БЭК-22-ФК-2
        - одиночные группы внутри большого текста
        """
        if not groups_text:
            return []

        text = str(groups_text)
        text = text.replace("\r", "\n")
        text = text.replace("–", "-").replace("—", "-")

        # сначала пробуем выделить группы регуляркой
        # достаточно гибкая для MISIS-форматов
        pattern = r"[A-Za-zА-Яа-яЁё0-9]+(?:-[A-Za-zА-Яа-яЁё0-9]+){1,6}"
        regex_groups = re.findall(pattern, text)

        groups = [DataNormalizer._normalize_group_token(item) for item in regex_groups if item.strip()]

        # если регулярка ничего не дала, пробуем обычное разбиение
        if not groups:
            prepared = text.replace(";", ",").replace("\n", ",")
            parts = [part for part in prepared.split(",") if part.strip()]
            groups = [DataNormalizer._normalize_group_token(part) for part in parts if part.strip()]

        # убираем пустые и дубли
        groups = [group for group in groups if group]
        groups = list(dict.fromkeys(groups))

        return groups

    @staticmethod
    def _get_value(data: dict, aliases: list[str]) -> str:
        for alias in aliases:
            if alias in data:
                raw_value = data.get(alias)
                cleaned = DataNormalizer._clean_text(raw_value)
                if cleaned:
                    return cleaned
        return ""

    @staticmethod
    def normalize_rows(rows: list[dict]) -> list[dict]:
        normalized: list[dict] = []

        current_teacher = ""
        current_groups = ""
        current_date = ""
        current_time = ""
        current_room = ""
        current_consultation_date = ""
        current_consultation_time = ""
        current_consultation_room = ""

        for row in rows:
            data = row.get("row_data", {})
            if "error" in data:
                continue

            teacher = DataNormalizer._get_value(data, TEACHER_COLUMN_ALIASES)
            discipline = DataNormalizer._get_value(data, DISCIPLINE_COLUMN_ALIASES)
            groups = DataNormalizer._get_value(data, GROUP_COLUMN_ALIASES)

            date = DataNormalizer._normalize_date(DataNormalizer._get_value(data, DATE_COLUMN_ALIASES))
            time = DataNormalizer._normalize_time(DataNormalizer._get_value(data, TIME_COLUMN_ALIASES))
            room = DataNormalizer._get_value(data, ROOM_COLUMN_ALIASES)

            consultation_date = DataNormalizer._normalize_date(
                DataNormalizer._get_value(data, CONSULTATION_DATE_COLUMN_ALIASES)
            )
            consultation_time = DataNormalizer._normalize_time(
                DataNormalizer._get_value(data, CONSULTATION_TIME_COLUMN_ALIASES)
            )
            consultation_room = DataNormalizer._get_value(data, CONSULTATION_ROOM_COLUMN_ALIASES)

            if teacher:
                current_teacher = teacher
            else:
                teacher = current_teacher

            # очень важно: группы тоже могут идти "продолжением" строки
            if groups:
                current_groups = groups
            else:
                groups = current_groups

            if date:
                current_date = date
            else:
                date = current_date

            if time:
                current_time = time
            else:
                time = current_time

            if room:
                current_room = room
            else:
                room = current_room

            if consultation_date:
                current_consultation_date = consultation_date
            else:
                consultation_date = current_consultation_date

            if consultation_time:
                current_consultation_time = consultation_time
            else:
                consultation_time = current_consultation_time

            if consultation_room:
                current_consultation_room = consultation_room
            else:
                consultation_room = current_consultation_room

            if not discipline:
                continue

            if discipline.strip().lower() in HEADER_SKIP_VALUES:
                continue

            groups_list = DataNormalizer._extract_groups_from_text(groups)
            groups_normalized = ",".join(groups_list)

            normalized.append(
                {
                    "source_file": row.get("source_file", ""),
                    "sheet_name": row.get("sheet_name", ""),
                    "discipline": discipline,
                    "teacher": teacher,
                    "groups": groups,
                    "groups_list": groups_list,
                    "groups_normalized": groups_normalized,
                    "date": date,
                    "time": time,
                    "room": room,
                    "consultation_date": consultation_date,
                    "consultation_time": consultation_time,
                    "consultation_room": consultation_room,
                }
            )

        return DataNormalizer._deduplicate_records(normalized)

    @staticmethod
    def _deduplicate_records(records: list[dict]) -> list[dict]:
        unique: list[dict] = []
        seen: set[tuple] = set()

        for record in records:
            key = (
                record.get("discipline", "").lower(),
                record.get("teacher", "").lower(),
                record.get("groups_normalized", "").lower(),
                record.get("date", "").lower(),
                record.get("time", "").lower(),
                record.get("room", "").lower(),
                record.get("consultation_date", "").lower(),
                record.get("consultation_time", "").lower(),
                record.get("consultation_room", "").lower(),
            )

            if key in seen:
                continue

            seen.add(key)
            unique.append(record)

        return unique