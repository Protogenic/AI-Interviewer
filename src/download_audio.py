"""
Downloading audio from YouTube videos using yt-dlp
"""
from __future__ import annotations

import argparse
import logging
import subprocess
from pathlib import Path

logger = logging.getLogger("yt_dlp_download")


def configure_console_logging() -> None:
    """
    Configure console logging for.
    """
    level = logging.INFO
    logging.basicConfig(
        level=level,
        format="%(levelname)s | %(name)s | %(message)s",
    )


def read_urls(urls_path: Path) -> list[str]:
    """
    Reads links from the urls file (1 link per line).
    Ignores empty lines and lines starting with "#".
    Parameters
    ----------
    urls_path: Path
        urls file path

    Returns
    -------
    list[str]
        List of url links
    """
    text = urls_path.read_text(encoding="utf-8", errors="replace")
    urls: list[str] = []
    for line in text.splitlines():
        s = line.strip()
        if not s or s.startswith("#"):
            continue
        urls.append(s)
    return urls


def run_yt_dlp(yt_dlp_exe: Path, url: str, out_dir: Path) -> int:
    """
    Launches yt-dlp for a single link.

    Parameters
    ----------
    yt_dlp_exe: Path
        yt-dlp.exe path
    url: str
        url from list
    out_dir: Path
        out directory path

    Returns
    -------
    int
        process code
    """
    out_template = str(out_dir / "%(id)s_%(title)s.%(ext)s")
    cmd = [
        str(yt_dlp_exe),
        "-x",
        "--audio-format",
        "mp3",
        "--audio-quality",
        "7",
        "--output",
        out_template,
        url,
    ]
    return subprocess.run(cmd, check=False).returncode


def main() -> int:
    # Sets the parameters of the desired format for yt-dlp
    parser = argparse.ArgumentParser(
        description="Download MP3 audio from YouTube links using yt-dlp."
    )
    parser.add_argument(
        "--yt-dlp",
        required=True,
        help=r"Путь к yt-dlp.exe (например: C:\tools\yt-dlp\yt-dlp.exe)",
    )
    parser.add_argument(
        "--urls",
        required=True,
        help=r"Путь к urls.txt (1 ссылка на строку)",
    )
    parser.add_argument(
        "--out",
        required=True,
        help=r"Путь к папке, для сохранения mp3 (например: D:\audio)",
    )
    args = parser.parse_args()

    yt_dlp_exe = Path(args.yt_dlp)
    urls_file = Path(args.urls)
    out_dir = Path(args.out)

    configure_console_logging()

    # Check if the yt-dlp URL exists
    if not yt_dlp_exe.exists():
        raise FileNotFoundError(f"yt-dlp.exe не найден по пути: {yt_dlp_exe}")
    if not urls_file.exists():
        raise FileNotFoundError(f"Файл urls.txt не найден: {urls_file}")

    out_dir.mkdir(parents=True, exist_ok=True)
    # Checks if yt-dlp is working
    result = subprocess.run(
        [str(yt_dlp_exe), "--version"],
        capture_output=True,
        text=True,
        check=False,
        encoding="utf-8",
        errors="replace",
    )
    if result.returncode != 0:
        raise RuntimeError(
            "yt-dlp не запускается корректно.\n"
            f"stdout:\n{result.stdout}\n"
            f"stderr:\n{result.stderr}\n"
        )

    urls = read_urls(urls_file)
    if not urls:
        logger.error("В urls.txt нет ссылок.")
        return 2

    ok = 0
    failed = 0
    total = len(urls)

    # Run yt-dlp for each link in the desired format
    for i, url in enumerate(urls, start=1):
        logger.info("[%d/%d] %s", i, total, url)
        code = run_yt_dlp(yt_dlp_exe, url, out_dir)
        if code == 0:
            ok += 1
            logger.info("OK")
        else:
            failed += 1
            logger.warning("yt-dlp завершился с кодом %d для ссылки: %s", code, url)

    logger.info("Готово. Успешно: %d, Ошибки: %d. Папка: %s", ok, failed, out_dir)
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
