import io
import requests
import os
import streamlit as st

def fetch_latest_report_from_nas():
    """
    Автоматически загружает свежий отчет с Synology NAS.
    Ссылка и параметры забираются из st.secrets.
    """
    cache_filename = "last_downloaded_report.xlsx"
    
    # Забираем URL из secrets
    try:
        direct_url = st.secrets["nas"]["url"]
    except Exception:
        return None, "❌ Ошибка: В st.secrets не найдена секция [nas] или ключ 'url'."

    try:
        # Выполняем автозагрузку с таймаутом
        response = requests.get(direct_url, timeout=20, allow_redirects=True)
        
        # Проверяем, что запрос успешен И содержимое является файлом XLSX (начинается с PK)
        if response.status_code == 200 and response.content.startswith(b'PK'):
            # Обновляем локальный кеш
            with open(cache_filename, "wb") as f:
                f.write(response.content)
            return io.BytesIO(response.content), "✅ Отчет успешно автоматически загружен с Synology NAS!"
        
        # Если NAS вернул 404, 403 или HTML-страницу входа вместо файла
        else:
            if os.path.exists(cache_filename):
                with open(cache_filename, "rb") as f:
                    content = f.read()
                if content.startswith(b'PK'):
                    return io.BytesIO(content), f"⚠️ NAS вернул код {response.status_code} или HTML. Использована последняя успешная копия из кеша."
            
            return None, f"❌ Ошибка загрузки с NAS (HTTP {response.status_code}). Сервер отдаёт не Excel-файл."

    except Exception as e:
        # При сбое сети fallback на кеш
        if os.path.exists(cache_filename):
            with open(cache_filename, "rb") as f:
                content = f.read()
            if content.startswith(b'PK'):
                return io.BytesIO(content), f"⚠️ Сбой сети при обращении к NAS ({e}). Использована локальная копия из кеша."
        
        return None, f"❌ Ошибка подключения к NAS: {e}"
