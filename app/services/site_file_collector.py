"""
Сервис автоматической загрузки Excel-файлов с сайта МИСИС.

Что делает:
1. Загружает HTML страницы с пересдачами.
2. Ищет ссылки на Excel-файлы только в нужных вкладках.
3. Скачивает найденные файлы.

Почему нужен retry:
- сайт может отвечать медленно;
- отдельный запрос может зависнуть;
- одна неудачная попытка не должна ломать всю автозагрузку.
"""

from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry


class SiteFileCollector:
    """
    Загружает Excel-файлы только из указанных вкладок страницы МИСИС.
    """

    # Вкладки, из которых нужно собирать файлы.
    TARGET_TAB_IDS = ("tab-1-1", "tab-1-3")

    def __init__(self, page_url: str):
        """
        Инициализация сервиса.

        Убираем hash-часть URL, потому что сервер её не обрабатывает.
        """
        self.page_url = page_url.split("#")[0].strip()
        self.session = self._build_session()

    @staticmethod
    def _build_session() -> requests.Session:
        """
        Создаёт requests.Session с повторными попытками.

        Это нужно, чтобы:
        - переживать временные ошибки сети;
        - не падать от первого таймаута;
        - стабильнее работать с сайтом.
        """
        session = requests.Session()

        retry_strategy = Retry(
            total=3,                  # всего 3 повторные попытки
            backoff_factor=1.5,       # пауза между попытками растёт постепенно
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["GET"],
        )

        adapter = HTTPAdapter(max_retries=retry_strategy)
        session.mount("https://", adapter)
        session.mount("http://", adapter)

        # Небольшой заголовок, чтобы запрос выглядел как обычный браузерный.
        session.headers.update(
            {
                "User-Agent": (
                    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/124.0 Safari/537.36"
                )
            }
        )

        return session

    def _get_page_html(self) -> str:
        """
        Загружает HTML страницы с пересдачами.

        Важно:
        - увеличен timeout;
        - используется session с retry.
        """
        response = self.session.get(self.page_url, timeout=60)
        response.raise_for_status()
        return response.text

    @staticmethod
    def _is_excel_link(href: str) -> bool:
        """
        Проверяет, ведёт ли ссылка на Excel-файл.
        """
        href = href.lower()
        return ".xls" in href or ".xlsx" in href

    def _collect_links_from_tab(self, soup: BeautifulSoup, tab_id: str) -> list[str]:
        """
        Собирает Excel-ссылки только из одной конкретной вкладки.
        """
        tab_block = soup.find(id=tab_id)
        if not tab_block:
            return []

        links = []
        for tag in tab_block.find_all("a", href=True):
            href = tag["href"].strip()
            if self._is_excel_link(href):
                links.append(urljoin(self.page_url, href))

        return links

    def collect_excel_links(self) -> list[str]:
        """
        Собирает все уникальные Excel-ссылки из нужных вкладок.
        """
        html = self._get_page_html()
        soup = BeautifulSoup(html, "html.parser")

        links = []

        for tab_id in self.TARGET_TAB_IDS:
            links.extend(self._collect_links_from_tab(soup, tab_id))

        # Убираем дубликаты, сохраняя порядок.
        unique_links = list(dict.fromkeys(links))
        return unique_links

    def download_file(self, file_url: str) -> tuple[str, bytes]:
        """
        Скачивает один файл по ссылке.

        Timeout тоже увеличен, потому что некоторые файлы могут открываться медленно.
        """
        response = self.session.get(file_url, timeout=90)
        response.raise_for_status()

        file_name = file_url.split("/")[-1]
        return file_name, response.content