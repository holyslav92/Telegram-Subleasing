"""
Модуль загрузки медиафайлов по FTP на веб-сервер сайта «Добрый дом Тюмень».
Позволяет загружать логотипы, референсы Pexels и сгенерированные изображения
в медиа-папку сайта, чтобы передавать их прямыми публичными URL в Image-to-Image модели.
"""

import ftplib
import os
from pathlib import Path
from urllib.parse import urljoin

def upload_file_to_ftp(local_path: str, remote_filename: str = None) -> str:
    """
    Загружает локальный файл на FTP-сервер сайта.
    Параметры берутся из переменных окружения:
      - FTP_HOST (например, добрыйдом-72.рф или IP)
      - FTP_USER
      - FTP_PASSWORD
      - FTP_DIR (например, /public_html/uploads или /media)
      - FTP_BASE_URL (например, https://добрыйдом-72.рф/uploads/)
    Возвращает публичный URL загруженного файла или None при отсутствии конфигурации/ошибке.
    """
    host = os.environ.get("FTP_HOST", "").strip()
    user = os.environ.get("FTP_USER", "").strip()
    passwd = os.environ.get("FTP_PASSWORD", "").strip()
    remote_dir = os.environ.get("FTP_DIR", "/public_html/uploads").strip()
    base_url = os.environ.get("FTP_BASE_URL", "https://xn---72-9cdob8azaodt6k.xn--p1ai/uploads/").strip()

    if not host or not user or not passwd:
        return ""

    file_path = Path(local_path)
    if not file_path.exists():
        return ""

    filename = remote_filename or file_path.name

    try:
        with ftplib.FTP(host, timeout=30) as ftp:
            ftp.login(user=user, passwd=passwd)
            if remote_dir:
                try:
                    ftp.cwd(remote_dir)
                except Exception:
                    # Попытка создать директорию если не существует
                    parts = remote_dir.strip("/").split("/")
                    for part in parts:
                        try:
                            ftp.cwd(part)
                        except Exception:
                            ftp.mkd(part)
                            ftp.cwd(part)

            with open(file_path, "rb") as f:
                ftp.storbinary(f"STOR {filename}", f)

        if not base_url.endswith("/"):
            base_url += "/"
        return f"{base_url}{filename}"
    except Exception as e:
        print(f"Ошибка загрузки по FTP: {e}")
        return ""
