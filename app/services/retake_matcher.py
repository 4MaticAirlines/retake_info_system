"""
Сервис сопоставления дисциплин из выписки с пересдачами из Excel.

Главная логика:
1. Для каждой дисциплины из выписки ищем все совпадения по названию.
2. Если среди них есть записи с нужной группой из выписки:
   - показываем только записи этой группы;
   - другие группы не показываем вообще.
3. Если нужной группы нет:
   - показываем все записи, совпавшие по названию дисциплины.
"""

import re


class RetakeMatcher:
    """
    Сервис сопоставления записей выписки с пересдачами.
    """

    @staticmethod
    def _normalize(text: str) -> str:
        """
        Нормализует строку для сравнения:
        - нижний регистр;
        - убираем лишние символы;
        - нормализуем пробелы.
        """
        text = str(text).lower().strip()
        text = re.sub(r"[^a-zа-яё0-9\s-]", " ", text)
        text = re.sub(r"\s+", " ", text)
        return text

    @staticmethod
    def _token_similarity(left: str, right: str) -> float:
        """
        Считает похожесть двух названий по пересечению слов.
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
        Проверяет, совпадает ли дисциплина из файла пересдач
        с дисциплиной из выписки.
        """
        left = RetakeMatcher._normalize(record_discipline)
        right = RetakeMatcher._normalize(statement_discipline)

        if not left or not right:
            return False

        # Полное совпадение
        if left == right:
            return True

        # Одна строка содержится в другой
        if left in right or right in left:
            return True

        # Мягкое совпадение по словам
        return RetakeMatcher._token_similarity(left, right) >= 0.45

    @staticmethod
    def _extract_groups(record: dict) -> list[str]:
        """
        Возвращает список групп из записи пересдачи.
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
        Проверяет, есть ли нужная группа в записи пересдачи.
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

        Нужен для удаления дублей.
        Преподаватель оставлен в ключе специально:
        если у одной дисциплины и группы разные преподаватели,
        это разные строки и их надо различать.
        """
        return (
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
        Удаляет полные дубли из списка записей.
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
    def build_statement_results(
        records: list[dict],
        debts: list[dict],
        group: str = "",
    ) -> list[dict]:
        """
        Формирует результат поиска по выписке.

        Логика:
        - сначала ищем все совпадения по названию дисциплины;
        - если среди них есть записи с нужной группой, показываем только их;
        - если группы нет, показываем все совпадения по дисциплине.
        """
        result = []

        for debt in debts:
            discipline = debt["discipline"]
            debt_type = debt["debt_type"]
            status = debt["status"]

            # Все совпадения по названию дисциплины
            discipline_matches = []

            for record in records:
                record_discipline = record.get("discipline", "")

                if not RetakeMatcher._discipline_matches(record_discipline, discipline):
                    continue

                discipline_matches.append(record)

            # Убираем полные дубли
            discipline_matches = RetakeMatcher._deduplicate_records(discipline_matches)

            # Среди совпадений по дисциплине ищем строки с нужной группой
            group_matches = [
                record
                for record in discipline_matches
                if RetakeMatcher._group_matches(record, group)
            ]

            # Если нашли нужную группу — показываем только её
            # Если не нашли — показываем всё, что совпало по дисциплине
            final_matches = group_matches if group_matches else discipline_matches

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