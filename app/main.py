from fastapi import FastAPI
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles

from app.core.config import BASE_DIR
from app.storage.database import Base, engine

# Импорт моделей обязателен до create_all
from app.models.uploaded_file import UploadedFile  # noqa: F401
from app.models.retake_record import RetakeRecord  # noqa: F401
from app.api.routes_files import router as files_router


Base.metadata.create_all(bind=engine)

app = FastAPI(title="Retake Info System")

app.include_router(files_router)
app.mount("/static", StaticFiles(directory=str(BASE_DIR / "app" / "static")), name="static")


@app.get("/", include_in_schema=False)
def root():
    return RedirectResponse(url="/files/")