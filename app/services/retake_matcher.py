import re


class RetakeMatcher:
    @staticmethod
    def _normalize(text: str) -> str:
        text = str(text).lower().strip()
        text = re.sub(r"[^a-zа-яё0-9\s-]", " ", text)
        text = re.sub(r"\s+", " ", text)
        return text

    @staticmethod
    def _token_score(left: str, right: str) -> float:
        left_tokens = set(RetakeMatcher._normalize(left).split())
        right_tokens = set(RetakeMatcher._normalize(right).split())

        if not left_tokens or not right_tokens:
            return 0.0

        intersection = left_tokens & right_tokens
        return len(intersection) / min(len(left_tokens), len(right_tokens))

    @staticmethod
    def _discipline_matches(record_discipline: str, statement_discipline: str) -> bool:
        left = RetakeMatcher._normalize(record_discipline)
        right = RetakeMatcher._normalize(statement_discipline)

        if not left or not right:
            return False

        if left == right:
            return True

        if left in right or right in left:
            return True

        return RetakeMatcher._token_score(left, right) >= 0.5

    @staticmethod
    def _group_matches(record: dict, group: str) -> bool:
        if not group:
            return True

        group = group.strip().upper()
        groups_raw = str(record.get("groups", "")).upper()
        groups_normalized = str(record.get("groups_normalized", "")).upper()

        return group in groups_raw or group in groups_normalized

    @staticmethod
    def build_statement_results(
        records: list[dict],
        disciplines: list[str],
        group: str = "",
    ) -> list[dict]:
        """
        Возвращает список вида:
        [
            {
                "discipline": "Алгоритмы дискретной математики",
                "matches": [ ...пересдачи... ]
            },
            ...
        ]
        """
        result = []

        for discipline in disciplines:
            matched_records = []
            seen = set()

            for record in records:
                if not RetakeMatcher._group_matches(record, group):
                    continue

                record_discipline = record.get("discipline", "")

                if not RetakeMatcher._discipline_matches(record_discipline, discipline):
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
                matched_records.append(record)

            result.append(
                {
                    "discipline": discipline,
                    "matches": matched_records,
                }
            )

        return result