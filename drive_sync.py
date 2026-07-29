import io
import requests
import os
import streamlit as st

def fetch_latest_report_from_gdrive():
    """
    Загружает актуальный отчет с Synology NAS (http://45.130.190.72:6783/) 
    с поддержкой парольного доступа и локального кэширования.
    """
    cache_filename = "last_downloaded_report.xlsx"
    
    # Получаем параметры подключения к вашему NAS из st.secrets
    nas_url = st.secrets.get("NAS_URL", "")
    nas_user = st.secrets.get("NAS_USER", "")
    nas_pass = st.secrets.get("NAS_PASSWORD", "")
    
    if not nas_url:
        if os.path.exists(cache_filename):
            return open(cache_filename, "rb"), "⚠️ NAS_URL не задан. Использован локальный кэш."
        return None, "Не задан параметр NAS_URL в настройках st.secrets."

    try:
        # Запрос к Synology NAS с авторизацией (если требуется)
        auth = (nas_user, nas_pass) if nas_user and nas_pass else None
        response = requests.get(nas_url, auth=auth, timeout=15)
        
        # Проверяем успешность загрузки (статус 200 и файл больше 1 КБ)
        if response.status_code == 200 and len(response.content) > 1000:
            with open(cache_filename, "wb") as f:
                f.write(response.content)
            return io.BytesIO(response.content), "✅ Отчет успешно загружен с Synology NAS!"
        else:
            if os.path.exists(cache_filename):
                return open(cache_filename, "rb"), "⚠️ NAS недоступен или неверный статус. Использован предыдущий отчет (кэш)."
            return None, f"Ошибка загрузки с NAS: HTTP статус {response.status_code}"
            
    except Exception as e:
        if os.path.exists(cache_filename):
            return open(cache_filename, "rb"), f"⚠️ Ошибка сети с NAS ({e}). Использован кэш."
        return None, f"Ошибка подключения к NAS: {e}"
