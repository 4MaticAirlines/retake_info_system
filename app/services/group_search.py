class GroupSearch:
    @staticmethod
    def _normalize(group: str) -> str:
        return str(group).strip().upper()

    @staticmethod
    def _group_matches(query: str, candidate: str) -> bool:
        query = GroupSearch._normalize(query)
        candidate = GroupSearch._normalize(candidate)

        if not query or not candidate:
            return False

        # точное совпадение
        if query == candidate:
            return True

        # если запрос общий, например:
        # БИВТ -> БИВТ-24-1
        # БИВТ-24 -> БИВТ-24-1
        if candidate.startswith(query + "-"):
            return True

        return False

    @staticmethod
    def find_by_group(records: list[dict], group_name: str) -> list[dict]:
        query = GroupSearch._normalize(group_name)
        result = []
        seen = set()

        for record in records:
            groups_list = [GroupSearch._normalize(group) for group in record.get("groups_list", [])]

            matched = any(GroupSearch._group_matches(query, group) for group in groups_list)
            if not matched:
                continue

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