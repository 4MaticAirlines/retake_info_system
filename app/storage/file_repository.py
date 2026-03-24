from sqlalchemy.orm import Session

from app.models.uploaded_file import UploadedFile


class UploadedFileRepository:
    @staticmethod
    def find_by_hash(db: Session, file_hash: str) -> UploadedFile | None:
        return db.query(UploadedFile).filter(UploadedFile.file_hash == file_hash).first()

    @staticmethod
    def get_by_stored_name(db: Session, stored_name: str) -> UploadedFile | None:
        return db.query(UploadedFile).filter(UploadedFile.stored_name == stored_name).first()

    @staticmethod
    def list_all(db: Session) -> list[UploadedFile]:
        return db.query(UploadedFile).order_by(UploadedFile.created_at.desc()).all()

    @staticmethod
    def create(
        db: Session,
        *,
        original_name: str,
        stored_name: str,
        file_hash: str,
        source: str,
        file_type: str,
        file_path: str,
    ) -> UploadedFile:
        obj = UploadedFile(
            original_name=original_name,
            stored_name=stored_name,
            file_hash=file_hash,
            source=source,
            file_type=file_type,
            file_path=file_path,
        )
        db.add(obj)
        db.commit()
        db.refresh(obj)
        return obj

    @staticmethod
    def delete_by_stored_name(db: Session, stored_name: str) -> None:
        obj = UploadedFileRepository.get_by_stored_name(db, stored_name)
        if obj:
            db.delete(obj)
            db.commit()

    @staticmethod
    def clear_all(db: Session) -> None:
        db.query(UploadedFile).delete()
        db.commit()