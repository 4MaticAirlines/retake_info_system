"""
Репозиторий пересдач.

Отвечает за сохранение и чтение таблицы пересдач.
"""

from sqlalchemy.orm import Session

from app.models.retake_record import RetakeRecord


class RetakeRepository:
    """
    Репозиторий для работы с таблицей пересдач.
    """

    @staticmethod
    def clear_all(db: Session) -> None:
        """
        Полностью очищает таблицу пересдач.
        """
        db.query(RetakeRecord).delete()
        db.commit()

    @staticmethod
    def save_many(db: Session, records: list[dict]) -> int:
        """
        Сохраняет список пересдач в БД.
        """
        objects = [
            RetakeRecord(
                source_file=record.get("source_file", ""),
                sheet_name=record.get("sheet_name", ""),
                retake_type=record.get("retake_type", ""),
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
        """
        Возвращает количество записей пересдач.
        """
        return db.query(RetakeRecord).count()

    @staticmethod
    def get_all(db: Session) -> list[RetakeRecord]:
        """
        Возвращает все пересдачи.
        """
        return db.query(RetakeRecord).all()