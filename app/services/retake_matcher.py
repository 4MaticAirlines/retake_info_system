"""
Сервис сопоставления дисциплин из выписки с пересдачами из Excel.

Логика:
1. Ищем все совпадения по названию дисциплины.
2. Если среди них есть нужная группа — показываем только её.
3. Внутри найденных записей сортируем:
   - сначала первичная,
   - потом вторичная,
   - потом другое.
"""

import re


class RetakeMatcher:
    """
    Сервис сопоставления записей выписки с пересдачами.
    """

    @staticmethod
    def _normalize(text: str) -> str:
        """
        Нормализует строку для сравнения.
        """
        text = str(text).lower().strip()
        text = re.sub(r"[^a-zа-яё0-9\s-]", " ", text)
        text = re.sub(r"\s+", " ", text)
        return text

    @staticmethod
    def _token_similarity(left: str, right: str) -> float:
        """
        Считает похожесть двух названий по словам.
        """
        left_tokens = set(RetakeMatcher._normalize(left).split())
        right_tokens = set(RetakeMatcher._normalize(right).split())

        if not left_tokens or not right_tokens:
            return 0.0

        intersection = left_tokens & right_tokens
        union = left_tokens | right_tokens

        if not union:
            return 0.0

        return len(intersection) / len(union)

    @staticmethod
    def _discipline_matches(record_discipline: str, statement_discipline: str) -> bool:
        """
        Проверяет совпадение дисциплины из пересдачи
        с дисциплиной из выписки.
        """
        left = RetakeMatcher._normalize(record_discipline)
        right = RetakeMatcher._normalize(statement_discipline)

        if not left or not right:
            return False

        if left == right:
            return True

        if left in right or right in left:
            return True

        return RetakeMatcher._token_similarity(left, right) >= 0.45

    @staticmethod
    def _extract_groups(record: dict) -> list[str]:
        """
        Возвращает список групп из записи.
        """
        groups_list = record.get("groups_list", [])
        if groups_list:
            return [str(group).strip().upper() for group in groups_list if str(group).strip()]

        groups_normalized = str(record.get("groups_normalized", ""))
        if groups_normalized:
            return [item.strip().upper() for item in groups_normalized.split(",") if item.strip()]

        groups_raw = str(record.get("groups", ""))
        if groups_raw:
            return [groups_raw.strip().upper()]

        return []

    @staticmethod
    def _group_matches(record: dict, group: str) -> bool:
        """
        Проверяет, есть ли группа из выписки в записи пересдачи.
        """
        if not group:
            return False

        target_group = str(group).strip().upper()
        record_groups = RetakeMatcher._extract_groups(record)

        return target_group in record_groups

    @staticmethod
    def _make_record_key(record: dict) -> tuple:
        """
        Формирует ключ уникальности записи.
        """
        return (
            record.get("retake_type", ""),
            record.get("discipline", ""),
            record.get("teacher", ""),
            record.get("groups", ""),
            record.get("date", ""),
            record.get("time", ""),
            record.get("room", ""),
            record.get("consultation_date", ""),
            record.get("consultation_time", ""),
            record.get("consultation_room", ""),
        )

    @staticmethod
    def _deduplicate_records(records: list[dict]) -> list[dict]:
        """
        Удаляет полные дубли записей.
        """
        unique_records = []
        seen = set()

        for record in records:
            key = RetakeMatcher._make_record_key(record)
            if key in seen:
                continue

            seen.add(key)
            unique_records.append(record)

        return unique_records

    @staticmethod
    def _retake_type_order(record: dict) -> int:
        """
        Определяет порядок сортировки типов пересдачи.

        Порядок:
        0 -> первичная
        1 -> вторичная
        2 -> другое
        """
        retake_type = str(record.get("retake_type", "")).lower()

        if retake_type == "первичная":
            return 0
        if retake_type == "вторичная":
            return 1
        return 2

    @staticmethod
    def _sort_records(records: list[dict]) -> list[dict]:
        """
        Сортирует записи:
        - первичная раньше вторичной;
        - затем по дате, времени и преподавателю.
        """
        return sorted(
            records,
            key=lambda record: (
                RetakeMatcher._retake_type_order(record),
                str(record.get("date", "")),
                str(record.get("time", "")),
                str(record.get("teacher", "")),
            ),
        )

    @staticmethod
    def build_statement_results(
        records: list[dict],
        debts: list[dict],
        group: str = "",
    ) -> list[dict]:
        """
        Формирует результат поиска по выписке.

        Логика:
        - ищем совпадения по дисциплине;
        - если есть записи с нужной группой, оставляем только их;
        - если группы нет, показываем все совпадения по названию;
        - сортируем: первичная -> вторичная -> другое.
        """
        result = []

        for debt in debts:
            discipline = debt["discipline"]
            debt_type = debt["debt_type"]
            status = debt["status"]

            discipline_matches = []

            for record in records:
                record_discipline = record.get("discipline", "")

                if not RetakeMatcher._discipline_matches(record_discipline, discipline):
                    continue

                discipline_matches.append(record)

            discipline_matches = RetakeMatcher._deduplicate_records(discipline_matches)

            group_matches = [
                record
                for record in discipline_matches
                if RetakeMatcher._group_matches(record, group)
            ]

            final_matches = group_matches if group_matches else discipline_matches
            final_matches = RetakeMatcher._sort_records(final_matches)

            result.append(
                {
                    "discipline": discipline,
                    "debt_type": debt_type,
                    "status": status,
                    "matches": final_matches,
                    "used_group_filter": bool(group_matches),
                }
            )

        return result