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
        union = left_tokens | right_tokens

        if not union:
            return 0.0

        return len(intersection) / len(union)

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

        return RetakeMatcher._token_score(left, right) >= 0.45

    @staticmethod
    def build_statement_results(
        records: list[dict],
        disciplines: list[str],
    ) -> list[dict]:
        result = []

        for discipline in disciplines:
            matched_records = []
            seen = set()

            for record in records:
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