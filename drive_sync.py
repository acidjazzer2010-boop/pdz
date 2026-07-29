import io
import requests
import os
import streamlit as st

def fetch_latest_report_from_nas():
    """
    Загружает файл через Synology File Station API с авторизацией.
    """
    cache_filename = "last_downloaded_report.xlsx"
    
    nas_base = "http://45.130.190.72:6783"
    nas_user = st.secrets.get("NAS_USER", "")
    nas_pass = st.secrets.get("NAS_PASSWORD", "")
    sharing_id = "i4LaNSCbE" # ID из вашей ссылки /sharing/i4LaNSCbE
    
    try:
        session = requests.Session()
        
        # 1. Авторизуемся в Synology DSM API
        login_url = f"{nas_base}/webapi/auth.cgi"
        login_params = {
            "api": "SYNO.API.Auth",
            "version": "3",
            "method": "login",
            "account": nas_user,
            "passwd": nas_pass,
            "session": "FileStation"
        }
        login_resp = session.get(login_url, params=login_params, timeout=10).json()
        
        if not login_resp.get("success"):
            if os.path.exists(cache_filename):
                return open(cache_filename, "rb"), "⚠️ Ошибка авторизации на NAS. Использован кэш."
            return None, "Ошибка входа на Synology NAS: проверьте логин и пароль в st.secrets."
            
        syno_token = login_resp["data"]["sid"]
        
        # 2. Получаем прямую ссылку на скачивание файла по шарингу
        # Либо запрашиваем файл напрямую через File Station API
        download_url = f"{nas_base}/webapi/entry.cgi"
        download_params = {
            "api": "SYNO.FileStation.Sharing",
            "version": "1",
            "method": "get",
            "id": sharing_id,
            "_sid": syno_token
        }
        
        # Скачиваем файл
        response = session.get(download_url, params=download_params, timeout=20)
        
        if response.status_code == 200 and len(response.content) > 1000 and b"<html>" not in response.content[:100]:
            with open(cache_filename, "wb") as f:
                f.write(response.content)
            return io.BytesIO(response.content), "✅ Отчет успешно загружен с Synology NAS!"
        else:
            if os.path.exists(cache_filename):
                return open(cache_filename, "rb"), "⚠️ Не удалось получить файл по шарингу. Использован кэш."
            return None, "Ошибка: NAS вернул пустой или некорректный файл по ссылке шаринга."
            
    except Exception as e:
        if os.path.exists(cache_filename):
            return open(cache_filename, "rb"), f"⚠️ Ошибка сети ({e}). Использован кэш."
        return None, f"Ошибка подключения к NAS: {e}"
