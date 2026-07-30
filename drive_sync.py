import io
import requests
import os
import streamlit as st

def fetch_latest_report_from_nas():
    """
    Автоматически скачивает файл из закрытой папки Synology NAS через WebAPI.
    Параметры берутся из st.secrets["nas"].
    """
    cache_filename = "last_downloaded_report.xlsx"
    
    nas_conf = st.secrets.get("nas", {})
    host = nas_conf.get("host", "http://45.130.190.72:6783")
    username = nas_conf.get("username")
    password = nas_conf.get("password")
    file_path = nas_conf.get("file_path", "/Kraivin/ПДЗ.xlsx")

    # Если в secrets указан прямой URL без авторизации
    direct_url = nas_conf.get("url")
    if direct_url:
        try:
            headers = {"User-Agent": "Mozilla/5.0"}
            res = requests.get(direct_url, headers=headers, timeout=20, allow_redirects=True)
            if res.status_code == 200 and res.content.startswith(b'PK'):
                with open(cache_filename, "wb") as f:
                    f.write(res.content)
                return io.BytesIO(res.content), "✅ Отчет загружен с Synology NAS!"
        except Exception:
            pass

    # Основной сценарий: Авторизация через WebAPI Synology
    if username and password:
        try:
            session = requests.Session()
            
            # 1. Логин в DSM
            auth_url = f"{host}/webapi/auth.cgi"
            auth_params = {
                "api": "SYNO.API.Auth",
                "version": "3",
                "method": "login",
                "account": username,
                "passwd": password,
                "session": "FileStation",
                "format": "cookie"
            }
            
            auth_res = session.get(auth_url, params=auth_params, timeout=10)
            auth_data = auth_res.json()
            
            if auth_data.get("success"):
                sid = auth_data["data"]["sid"]
                
                # 2. Скачивание файла по пути в FileStation
                download_url = f"{host}/webapi/entry.cgi"
                dl_params = {
                    "api": "SYNO.FileStation.Download",
                    "version": "2",
                    "method": "download",
                    "path": file_path,
                    "mode": "download",
                    "_sid": sid
                }
                
                dl_res = session.get(download_url, params=dl_params, timeout=20)
                
                if dl_res.status_code == 200 and dl_res.content.startswith(b'PK'):
                    with open(cache_filename, "wb") as f:
                        f.write(dl_res.content)
                    return io.BytesIO(dl_res.content), "✅ Отчет успешно загружен с Synology NAS через WebAPI!"
                else:
                    preview = dl_res.text[:200].replace("\n", " ").strip()
                    raise Exception(f"API отдал HTTP {dl_res.status_code}, но не файл Excel. Ответ: {preview}")
            else:
                code = auth_data.get("error", {}).get("code", "неизвестно")
                raise Exception(f"Ошибка авторизации Synology (Код: {code}). Проверьте логин и пароль.")

        except Exception as e:
            if os.path.exists(cache_filename):
                with open(cache_filename, "rb") as f:
                    content = f.read()
                if content.startswith(b'PK'):
                    return io.BytesIO(content), f"⚠️ Сбой загрузки с NAS ({e}). Использована локальная копия из кэша."
            return None, f"❌ Ошибка подключения к NAS: {e}"

    # Если ничего не помогло, пробуем хотя бы прочитать кэш
    if os.path.exists(cache_filename):
        with open(cache_filename, "rb") as f:
            content = f.read()
        if content.startswith(b'PK'):
            return io.BytesIO(content), "⚠️ Не удалось получить данные с NAS. Использована копия из кэша."

    return None, "❌ Ошибка: В st.secrets не указаны учётные данные (username/password) или 'url' для NAS."
