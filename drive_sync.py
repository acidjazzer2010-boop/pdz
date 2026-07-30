import io
import requests
import os
import streamlit as st

def fetch_latest_report_from_nas():
    """
    Автоматически загружает свежий отчет с Synology NAS.
    Ссылка забирается из st.secrets["nas"]["url"].
    """
    cache_filename = "last_downloaded_report.xlsx"
    
    # 1. Чтение URL из секретов
    try:
        direct_url = st.secrets["nas"]["url"]
    except Exception:
        return None, "❌ Ошибка: В st.secrets не найдена секция [nas] или ключ 'url'."

    try:
        # Передаем стандартный User-Agent, чтобы NAS не блокировал запрос
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        }
        
        response = requests.get(direct_url, headers=headers, timeout=20, allow_redirects=True)
        
        # 2. Проверка бинарной сигнатуры XLSX (любой zip/xlsx начинается с b'PK')
        if response.status_code == 200 and response.content.startswith(b'PK'):
            with open(cache_filename, "wb") as f:
                f.write(response.content)
            return io.BytesIO(response.content), "✅ Отчет успешно автоматически загружен с Synology NAS!"
        
        # 3. Если NAS вернул HTML/текст вместо бинарного файла
        else:
            # Получаем превью ответа для быстрой диагностики
            preview = response.text[:200].replace("\n", " ").strip()
            
            # Попытка отдачи из локального кэша
            if os.path.exists(cache_filename):
                with open(cache_filename, "rb") as f:
                    content = f.read()
                if content.startswith(b'PK'):
                    return (
                        io.BytesIO(content), 
                        f"⚠️ NAS вернул HTTP {response.status_code} (не Excel). Использован кэш.\nОтвет NAS: {preview}"
                    )
            
            return None, f"❌ NAS вернул HTTP {response.status_code}, но это не Excel. Ответ сервера: {preview}"

    except Exception as e:
        # 4. Обработка ошибок сети с fallback на кэш
        if os.path.exists(cache_filename):
            with open(cache_filename, "rb") as f:
                content = f.read()
            if content.startswith(b'PK'):
                return io.BytesIO(content), f"⚠️ Сбой сети при обращении к NAS ({e}). Использована локальная копия из кэша."
        
        return None, f"❌ Ошибка подключения к NAS: {e}"
