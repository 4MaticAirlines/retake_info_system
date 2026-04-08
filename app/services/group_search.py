"""
Сервис поиска пересдач по группе.

Здесь реализована отдельная логика поиска по группе, чтобы она не зависела
от поиска по выписке и не ломалась из-за него.
"""


class GroupSearch:
    """
    Поиск записей пересдач по названию группы.
    """

    @staticmethod
    def _normalize(value: str) -> str:
        """
        Приводит строку к единому виду:
        - убирает пробелы по краям
        - переводит в верхний регистр
        """
        return str(value).strip().upper()

    @staticmethod
    def _is_exact_group_query(query: str) -> bool:
        """
        Определяет, является ли запрос точным.

        Примеры:
        - БИВТ-24-1 -> точный запрос
        - БИВТ-24   -> общий запрос
        - БИВТ      -> общий запрос
        """
        return query.count("-") >= 2

    @staticmethod
    def _group_matches(query: str, candidate: str) -> bool:
        """
        Проверяет, подходит ли группа из записи под запрос пользователя.

        Логика:
        - если запрос точный -> только полное совпадение;
        - если запрос общий -> совпадение по префиксу.
        """
        query = GroupSearch._normalize(query)
        candidate = GroupSearch._normalize(candidate)

        if not query or not candidate:
            return False

        # Для точного запроса требуем полное совпадение.
        if GroupSearch._is_exact_group_query(query):
            return query == candidate

        # Для общего запроса разрешаем совпадение по началу строки.
        return candidate == query or candidate.startswith(query + "-")

    @staticmethod
    def find_by_group(records: list[dict], group_name: str) -> list[dict]:
        """
        Возвращает список записей пересдач, подходящих под запрос группы.
        """
        query = GroupSearch._normalize(group_name)
        result = []
        seen = set()

        for record in records:
            groups_list = [GroupSearch._normalize(group) for group in record.get("groups_list", [])]

            matched = any(GroupSearch._group_matches(query, group) for group in groups_list)
            if not matched:
                continue

            # Убираем дубли, чтобы одна и та же запись не повторялась.
            key = (
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

            if key in seen:
                continue

            seen.add(key)
            result.append(record)

        return result