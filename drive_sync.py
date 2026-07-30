import io
import requests
import os
import streamlit as st

def fetch_latest_report_from_nas():
    """
    Автоматически скачивает файл из закрытой папки Synology NAS через WebAPI.
    """
    cache_filename = "last_downloaded_report.xlsx"
    
    nas_conf = st.secrets.get("nas", {})
    host = nas_conf.get("host", "http://45.130.190.72:6783")
    username = nas_conf.get("username")
    password = nas_conf.get("password")
    file_path = nas_conf.get("file_path", "/Kraivin/ПДЗ.xlsx")

    if not username or not password:
        return None, "❌ Ошибка: В st.secrets не указаны username и password для NAS."

    try:
        session = requests.Session()
        
        # 1. Авторизация в Synology DSM API
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
            
            # 2. Скачивание файла по пути из FileStation
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
            
            # Проверяем, что вернулся именно файл Excel (начинается с b'PK')
            if dl_res.status_code == 200 and dl_res.content.startswith(b'PK'):
                with open(cache_filename, "wb") as f:
                    f.write(dl_res.content)
                return io.BytesIO(dl_res.content), "✅ Отчет успешно загружен с Synology NAS через WebAPI!"
            else:
                preview = dl_res.text[:200].replace("\n", " ")
                raise Exception(f"API отдал статус {dl_res.status_code}, но не файл Excel. Ответ: {preview}")
        else:
            code = auth_data.get("error", {}).get("code", "unknown")
            raise Exception(f"Ошибка авторизации Synology (Код ошибки: {code}). Проверьте логин/пароль.")

    except Exception as e:
        # Fallback на сохраненный кэш
        if os.path.exists(cache_filename):
            with open(cache_filename, "rb") as f:
                content = f.read()
            if content.startswith(b'PK'):
                return io.BytesIO(content), f"⚠️ Сбой автозагрузки с NAS ({e}). Использована копия из кэша."
        
        return None, f"❌ Ошибка подключения к NAS: {e}"
