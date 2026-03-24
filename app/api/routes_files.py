from datetime import datetime
from pathlib import Path

from fastapi import APIRouter, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from app.core.config import BASE_DIR, INPUT_DIR, STATEMENT_DIR, UNIVERSITY_RETAKES_URL
from app.services.data_normalizer import DataNormalizer
from app.services.debt_extractor import DebtExtractor
from app.services.excel_parser import ExcelParser
from app.services.retake_matcher import RetakeMatcher
from app.services.site_file_collector import SiteFileCollector
from app.services.statement_parser import StatementParser
from app.storage.database import SessionLocal
from app.storage.file_repository import UploadedFileRepository
from app.storage.retake_repository import RetakeRepository
from app.utils.file_loader import (
    calculate_file_hash,
    find_existing_file_by_hash,
    save_binary_file,
)

router = APIRouter(prefix="/files", tags=["files"])
templates = Jinja2Templates(directory=str(BASE_DIR / "app" / "templates"))


def retake_to_dict(record) -> dict:
    return {
        "id": record.id,
        "discipline": record.discipline,
        "teacher": record.teacher,
        "groups": record.groups_raw or "",
        "groups_normalized": record.groups_normalized or "",
        "date": record.date_raw or "",
        "time": record.time_raw or "",
        "room": record.room or "",
        "consultation_date": record.consultation_date_raw or "",
        "consultation_time": record.consultation_time_raw or "",
        "consultation_room": record.consultation_room or "",
        "source_file": record.source_file or "",
        "sheet_name": record.sheet_name or "",
    }


def build_file_list(db) -> list[dict]:
    db_files = UploadedFileRepository.list_all(db)
    meta_by_stored = {item.stored_name: item for item in db_files}

    files: list[dict] = []
    for file_path in sorted(INPUT_DIR.iterdir(), key=lambda item: item.stat().st_mtime, reverse=True):
        if not file_path.is_file():
            continue
        if file_path.name.startswith("."):
            continue

        meta = meta_by_stored.get(file_path.name)
        files.append(
            {
                "stored_name": file_path.name,
                "display_name": meta.original_name if meta else file_path.name,
                "source": meta.source if meta else "unknown",
                "size_kb": round(file_path.stat().st_size / 1024, 2),
                "updated_at": datetime.fromtimestamp(file_path.stat().st_mtime).strftime("%d.%m.%Y %H:%M"),
            }
        )

    return files


def render_page(request: Request, template_name: str, **context):
    return templates.TemplateResponse(
        request=request,
        name=template_name,
        context=context,
    )


def sync_retakes_from_files(db) -> int:
    parser = ExcelParser()
    rows = parser.parse_all_files()
    normalized = DataNormalizer.normalize_rows(rows)

    RetakeRepository.clear_all(db)
    return RetakeRepository.save_many(db, normalized)


def ensure_retakes_loaded(db) -> None:
    if RetakeRepository.count(db) == 0 and any(INPUT_DIR.iterdir()):
        sync_retakes_from_files(db)


def has_consultation_info(records: list[dict]) -> bool:
    return any(
        record.get("consultation_date")
        or record.get("consultation_time")
        or record.get("consultation_room")
        for record in records
    )


@router.get("/", response_class=HTMLResponse)
def home_page(request: Request):
    return render_page(
        request,
        "index.html",
        message="",
        message_type="info",
    )


@router.get("/search", response_class=HTMLResponse)
def search_page(request: Request):
    return render_page(request, "search.html")


@router.get("/manage", response_class=HTMLResponse)
def manage_page(request: Request):
    db = SessionLocal()
    try:
        return render_page(
            request,
            "manage.html",
            files=build_file_list(db),
            message="",
            message_type="info",
        )
    finally:
        db.close()


@router.post("/fetch-from-site", response_class=HTMLResponse)
def fetch_from_site(request: Request):
    db = SessionLocal()
    try:
        if not UNIVERSITY_RETAKES_URL:
            return render_page(
                request,
                "manage.html",
                files=build_file_list(db),
                message="URL страницы с пересдачами не задан в .env",
                message_type="error",
            )

        collector = SiteFileCollector(UNIVERSITY_RETAKES_URL)
        links = collector.collect_excel_links()

        if not links:
            return render_page(
                request,
                "manage.html",
                files=build_file_list(db),
                message="Excel-файлы на странице не найдены",
                message_type="error",
            )

        saved_count = 0
        duplicate_count = 0

        for file_url in links:
            original_name, file_bytes = collector.download_file(file_url)
            file_hash = calculate_file_hash(file_bytes)

            if UploadedFileRepository.find_by_hash(db, file_hash) or find_existing_file_by_hash(INPUT_DIR, file_hash):
                duplicate_count += 1
                continue

            stored_name, file_path = save_binary_file(INPUT_DIR, original_name, file_bytes)
            UploadedFileRepository.create(
                db,
                original_name=original_name,
                stored_name=stored_name,
                file_hash=file_hash,
                source="site",
                file_type="excel",
                file_path=str(file_path),
            )
            saved_count += 1

        if saved_count > 0:
            sync_retakes_from_files(db)

        return render_page(
            request,
            "manage.html",
            files=build_file_list(db),
            message=f"Автозагрузка завершена: новых файлов — {saved_count}, дубликатов — {duplicate_count}",
            message_type="success",
        )
    except Exception as error:
        return render_page(
            request,
            "manage.html",
            files=build_file_list(db),
            message=f"Ошибка автозагрузки: {error}",
            message_type="error",
        )
    finally:
        db.close()


@router.post("/upload", response_class=HTMLResponse)
async def upload_file(request: Request, file: UploadFile = File(...)):
    db = SessionLocal()
    try:
        if not file.filename:
            return render_page(
                request,
                "manage.html",
                files=build_file_list(db),
                message="Файл не выбран",
                message_type="error",
            )

        if not file.filename.lower().endswith((".xls", ".xlsx")):
            return render_page(
                request,
                "manage.html",
                files=build_file_list(db),
                message="Разрешены только Excel-файлы (.xls, .xlsx)",
                message_type="error",
            )

        file_bytes = await file.read()
        if not file_bytes:
            return render_page(
                request,
                "manage.html",
                files=build_file_list(db),
                message="Файл пустой",
                message_type="error",
            )

        file_hash = calculate_file_hash(file_bytes)

        if UploadedFileRepository.find_by_hash(db, file_hash) or find_existing_file_by_hash(INPUT_DIR, file_hash):
            return render_page(
                request,
                "manage.html",
                files=build_file_list(db),
                message="Такой файл уже был загружен",
                message_type="warning",
            )

        stored_name, file_path = save_binary_file(INPUT_DIR, file.filename, file_bytes)
        UploadedFileRepository.create(
            db,
            original_name=file.filename,
            stored_name=stored_name,
            file_hash=file_hash,
            source="manual",
            file_type="excel",
            file_path=str(file_path),
        )

        sync_retakes_from_files(db)

        return render_page(
            request,
            "manage.html",
            files=build_file_list(db),
            message=f"Файл «{file.filename}» успешно загружен",
            message_type="success",
        )
    finally:
        db.close()


@router.post("/rebuild-db", response_class=HTMLResponse)
def rebuild_db(request: Request):
    db = SessionLocal()
    try:
        saved_count = sync_retakes_from_files(db)
        return render_page(
            request,
            "manage.html",
            files=build_file_list(db),
            message=f"Данные пересдач обновлены. Сохранено записей: {saved_count}",
            message_type="success",
        )
    finally:
        db.close()


@router.post("/delete-one", response_class=HTMLResponse)
def delete_one_file(request: Request, stored_name: str = Form(...)):
    db = SessionLocal()
    try:
        file_path = INPUT_DIR / stored_name
        record = UploadedFileRepository.get_by_stored_name(db, stored_name)

        if not file_path.exists():
            return render_page(
                request,
                "manage.html",
                files=build_file_list(db),
                message="Файл не найден",
                message_type="error",
            )

        if file_path.is_file():
            file_path.unlink()

        if record:
            UploadedFileRepository.delete_by_stored_name(db, stored_name)

        sync_retakes_from_files(db)

        return render_page(
            request,
            "manage.html",
            files=build_file_list(db),
            message="Файл успешно удалён",
            message_type="success",
        )
    finally:
        db.close()


@router.post("/delete-all", response_class=HTMLResponse)
def delete_all_files(request: Request):
    db = SessionLocal()
    try:
        for file_path in INPUT_DIR.iterdir():
            if file_path.is_file() and not file_path.name.startswith("."):
                file_path.unlink()

        UploadedFileRepository.clear_all(db)
        RetakeRepository.clear_all(db)

        return render_page(
            request,
            "manage.html",
            files=[],
            message="Все Excel-файлы и записи о пересдачах удалены",
            message_type="success",
        )
    finally:
        db.close()


@router.get("/parsed")
def show_parsed_files():
    parser = ExcelParser()
    parsed_data = parser.parse_all_files()

    return {
        "message": "Файлы успешно обработаны",
        "total_rows": len(parsed_data),
        "data": parsed_data[:20],
    }


@router.get("/normalized")
def normalized_data():
    parser = ExcelParser()
    rows = parser.parse_all_files()
    normalized = DataNormalizer.normalize_rows(rows)

    return {
        "total_records": len(normalized),
        "data": normalized[:20],
    }


@router.get("/search-by-group", response_class=HTMLResponse)
def search_by_group(request: Request, group: str):
    db = SessionLocal()
    try:
        ensure_retakes_loaded(db)
        records = RetakeRepository.find_by_group(db, group)
        result = [retake_to_dict(record) for record in records]

        return render_page(
            request,
            "results.html",
            search_type="group",
            query=group,
            total_records=len(result),
            records=result,
            disciplines=[],
            statement_group="",
            markers=[],
            show_consultation=has_consultation_info(result),
        )
    finally:
        db.close()


@router.post("/search-by-statement", response_class=HTMLResponse)
async def search_by_statement(request: Request, file: UploadFile = File(...)):
    db = SessionLocal()
    try:
        if not file.filename:
            raise HTTPException(status_code=400, detail="Файл не выбран")

        if not file.filename.lower().endswith((".txt", ".docx", ".pdf")):
            raise HTTPException(status_code=400, detail="Поддерживаются только .txt, .docx и .pdf")

        save_path = STATEMENT_DIR / file.filename
        file_bytes = await file.read()
        save_path.write_bytes(file_bytes)

        statement_text = StatementParser.parse_statement(save_path)
        debts_data = DebtExtractor.extract_debts(statement_text)

        ensure_retakes_loaded(db)
        records = [retake_to_dict(record) for record in RetakeRepository.get_all(db)]

        statement_results = RetakeMatcher.build_statement_results(
            records=records,
            disciplines=debts_data["disciplines"],
            group=debts_data["group"],
        )

        total_matches = sum(len(item["matches"]) for item in statement_results)

        return render_page(
            request,
            "results.html",
            search_type="statement",
            query="выписка о задолженностях",
            total_records=total_matches,
            records=[],
            disciplines=debts_data["disciplines"],
            statement_group=debts_data["group"],
            markers=debts_data["markers"],
            show_consultation=any(
                match.get("consultation_date") or match.get("consultation_time") or match.get("consultation_room")
                for item in statement_results
                for match in item["matches"]
            ),
            statement_results=statement_results,
        )
    finally:
        db.close()