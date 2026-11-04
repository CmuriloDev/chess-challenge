import re
import sys
import urllib.request
import zipfile
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BOOK_DIR = ROOT / "data" / "book"
SYZYGY_DIR = ROOT / "data" / "syzygy"
BOOK_URL = "https://github.com/ChrisWhittington/polyglot-books/releases/latest/download/komodo.zip"
SYZYGY_INDEXES = (
    "https://tablebase.lichess.ovh/tables/standard/3-4-5-wdl/",
    "https://tablebase.lichess.ovh/tables/standard/3-4-5-dtz/",
)
WORKERS = 4
HEADERS = {"User-Agent": "chess-challenge-fetch"}


def open_url(url: str):
    return urllib.request.urlopen(urllib.request.Request(url, headers=HEADERS), timeout=60)


def download(url: str, target: Path) -> str:
    with open_url(url) as response:
        expected = int(response.headers.get("Content-Length", 0))
        if target.exists() and expected and target.stat().st_size == expected:
            return "ok"
        partial = target.with_suffix(target.suffix + ".part")
        with partial.open("wb") as handle:
            while chunk := response.read(1 << 20):
                handle.write(chunk)
        if expected and partial.stat().st_size != expected:
            partial.unlink()
            raise IOError(f"download incompleto: {url}")
        partial.replace(target)
    return "baixado"


def fetch_book() -> None:
    BOOK_DIR.mkdir(parents=True, exist_ok=True)
    target = BOOK_DIR / "komodo.bin"
    if target.exists():
        print(f"livro ja existe: {target}")
        return
    archive = BOOK_DIR / "komodo.zip"
    download(BOOK_URL, archive)
    with zipfile.ZipFile(archive) as bundle:
        bundle.extractall(BOOK_DIR)
    archive.unlink()
    print(f"livro instalado: {target}")


def list_tablebases(index: str) -> list[str]:
    with open_url(index) as response:
        page = response.read().decode("utf-8", "replace")
    names = sorted(set(re.findall(r'href="([^"/]+\.rtb[wz])"', page)))
    return [index + name for name in names]


def fetch_syzygy() -> None:
    SYZYGY_DIR.mkdir(parents=True, exist_ok=True)
    urls = [url for index in SYZYGY_INDEXES for url in list_tablebases(index)]
    print(f"tablebases: {len(urls)} arquivos")
    done = 0

    def job(url: str) -> str:
        return download(url, SYZYGY_DIR / url.rsplit("/", 1)[1])

    with ThreadPoolExecutor(max_workers=WORKERS) as pool:
        for status in pool.map(job, urls):
            done += 1
            if done % 20 == 0 or done == len(urls):
                print(f"  {done}/{len(urls)} ({status})", flush=True)
    print(f"tablebases instaladas em {SYZYGY_DIR}")


def main() -> int:
    fetch_book()
    fetch_syzygy()
    return 0


if __name__ == "__main__":
    sys.exit(main())
