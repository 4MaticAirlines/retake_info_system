from sqlalchemy.orm import Session

from app.models.retake_record import RetakeRecord


class RetakeRepository:
    @staticmethod
    def _normalize(group: str) -> str:
        return str(group).strip().upper()

    @staticmethod
    def _group_matches(query: str, candidate: str) -> bool:
        query = RetakeRepository._normalize(query)
        candidate = RetakeRepository._normalize(candidate)

        if not query or not candidate:
            return False

        # точное совпадение
        if query == candidate:
            return True

        # общий запрос:
        # БИВТ -> БИВТ-24-1
        # БИВТ-24 -> БИВТ-24-1
        if candidate.startswith(query + "-"):
            return True

        return False

    @staticmethod
    def clear_all(db: Session) -> None:
        db.query(RetakeRecord).delete()
        db.commit()

    @staticmethod
    def save_many(db: Session, records: list[dict]) -> int:
        objects = [
            RetakeRecord(
                source_file=record.get("source_file", ""),
                sheet_name=record.get("sheet_name", ""),
                discipline=record.get("discipline", ""),
                teacher=record.get("teacher", ""),
                groups_raw=record.get("groups", ""),
                groups_normalized=record.get("groups_normalized", ""),
                date_raw=record.get("date", ""),
                time_raw=record.get("time", ""),
                room=record.get("room", ""),
                consultation_date_raw=record.get("consultation_date", ""),
                consultation_time_raw=record.get("consultation_time", ""),
                consultation_room=record.get("consultation_room", ""),
            )
            for record in records
        ]

        if objects:
            db.add_all(objects)
            db.commit()

        return len(objects)

    @staticmethod
    def count(db: Session) -> int:
        return db.query(RetakeRecord).count()

    @staticmethod
    def get_all(db: Session) -> list[RetakeRecord]:
        return db.query(RetakeRecord).all()

    @staticmethod
    def find_by_group(db: Session, group: str):
        query = RetakeRepository._normalize(group)
        records = db.query(RetakeRecord).all()

        result = []
        for record in records:
            groups_normalized = str(record.groups_normalized or "")
            groups_list = [item.strip().upper() for item in groups_normalized.split(",") if item.strip()]

            if any(RetakeRepository._group_matches(query, item) for item in groups_list):
                result.append(record)

        return result