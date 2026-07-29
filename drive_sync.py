import io
import requests
import os
import streamlit as st

def fetch_latest_report_from_nas():
    """
    Загружает актуальный отчет с Synology NAS с базовой или расширенной авторизацией.
    """
    cache_filename = "last_downloaded_report.xlsx"
    
    nas_url = st.secrets.get("NAS_URL", "")
    nas_user = st.secrets.get("NAS_USER", "")
    nas_pass = st.secrets.get("NAS_PASSWORD", "")
    
    if not nas_url:
        if os.path.exists(cache_filename):
            return open(cache_filename, "rb"), "⚠️ NAS_URL не задан. Использован локальный кэш."
        return None, "Не задан параметр NAS_URL в настройках st.secrets."

    try:
        # Передаем логин и пароль для доступа к закрытому NAS
        auth = (nas_user, nas_pass) if nas_user and nas_pass else None
        
        # allow_redirects=True позволяет корректно отрабатывать ссылки-перенаправления
        response = requests.get(nas_url, auth=auth, timeout=20, allow_redirects=True)
        
        # Проверяем, что скачался именно Excel-файл (а не HTML-страница авторизации NAS)
        if response.status_code == 200 and len(response.content) > 1000 and b"<html>" not in response.content[:100]:
            with open(cache_filename, "wb") as f:
                f.write(response.content)
            return io.BytesIO(response.content), "✅ Отчет успешно загружен с Synology NAS!"
        else:
            if os.path.exists(cache_filename):
                return open(cache_filename, "rb"), "⚠️ NAS вернул не файл (или нет доступа). Использован кэш."
            return None, f"Ошибка: NAS отдал некорректный ответ (статус {response.status_code}). Проверьте прямую ссылку на файл."
            
    except Exception as e:
        if os.path.exists(cache_filename):
            return open(cache_filename, "rb"), f"⚠️ Ошибка сети с NAS ({e}). Использован кэш."
        return None, f"Ошибка подключения к NAS: {e}"
