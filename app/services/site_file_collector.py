from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup


class SiteFileCollector:
    """
    Загружает Excel-файлы только из указанных вкладок страницы МИСИС.
    По твоему требованию:
    - tab-1-1
    - tab-1-3
    """

    TARGET_TAB_IDS = ("tab-1-1", "tab-1-3")

    def __init__(self, page_url: str):
        # убираем hash-фрагмент, потому что сервер его не обрабатывает
        self.page_url = page_url.split("#")[0].strip()

    def _get_page_html(self) -> str:
        response = requests.get(self.page_url, timeout=20)
        response.raise_for_status()
        return response.text

    @staticmethod
    def _is_excel_link(href: str) -> bool:
        href = href.lower()
        return ".xls" in href or ".xlsx" in href

    def _collect_links_from_tab(self, soup: BeautifulSoup, tab_id: str) -> list[str]:
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
        html = self._get_page_html()
        soup = BeautifulSoup(html, "html.parser")

        links = []

        # собираем ссылки только из нужных вкладок
        for tab_id in self.TARGET_TAB_IDS:
            links.extend(self._collect_links_from_tab(soup, tab_id))

        # убираем дубликаты, сохраняя порядок
        unique_links = list(dict.fromkeys(links))
        return unique_links

    @staticmethod
    def download_file(file_url: str) -> tuple[str, bytes]:
        response = requests.get(file_url, timeout=30)
        response.raise_for_status()

        file_name = file_url.split("/")[-1]
        return file_name, response.content