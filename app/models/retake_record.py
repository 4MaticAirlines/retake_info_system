from sqlalchemy import Column, Integer, String

from app.storage.database import Base


class RetakeRecord(Base):
    __tablename__ = "retake_records"

    id = Column(Integer, primary_key=True, index=True)
    source_file = Column(String, nullable=True)
    sheet_name = Column(String, nullable=True)

    discipline = Column(String, nullable=False, index=True)
    teacher = Column(String, nullable=True)
    groups_raw = Column(String, nullable=True)
    groups_normalized = Column(String, nullable=True, index=True)

    date_raw = Column(String, nullable=True)
    time_raw = Column(String, nullable=True)
    room = Column(String, nullable=True)

    consultation_date_raw = Column(String, nullable=True)
    consultation_time_raw = Column(String, nullable=True)
    consultation_room = Column(String, nullable=True)