import io
import requests
import os
import streamlit as st
import datetime

def fetch_latest_report_from_gdrive():
    """
    Загружает актуальный отчет из Google Drive.
    Ищет файл по ID из st.secrets. Если актуального на сегодня нет, 
    пытается использовать сохраненный локально кэш (предыдущий файл).
    """
    cache_filename = "last_downloaded_report.xlsx"
    
    # Получаем ID файла или папки из секретов Streamlit
    file_id = st.secrets.get("GDRIVE_FILE_ID", "")
    
    if not file_id:
        # Если ID не задан в секретах, проверяем локальный кэш
        if os.path.exists(cache_filename):
            return open(cache_filename, "rb"), "Использован предыдущий сохраненный файл (GDRIVE_FILE_ID не настроен в secrets)."
        return None, "Не задан GDRIVE_FILE_ID в st.secrets и нет сохраненного локального файла."

    try:
        download_url = f"https://drive.google.com/uc?export=download&id={file_id}"
        response = requests.get(download_url, timeout=10)
        
        if response.status_code == 200 and len(response.content) > 1000:
            # Сохраняем свежий файл как резервный (предыдущий)
            with open(cache_filename, "wb") as f:
                f.write(response.content)
            return io.BytesIO(response.content), "Файл успешно загружен из Google Drive!"
        else:
            # Если не удалось скачать свежий, используем предыдущий сохраненный кэш
            if os.path.exists(cache_filename):
                return open(cache_filename, "rb"), "⚠️ Свежий файл на Google Drive недоступен. Использован предыдущий отчет (кэш)."
            return None, "Не удалось скачать файл из Google Drive, и нет предыдущей копии."
            
    except Exception as e:
        # В случае сбоя сети или ошибки берем предыдущий файл
        if os.path.exists(cache_filename):
            return open(cache_filename, "rb"), f"⚠️ Ошибка сети ({e}). Использован предыдущий отчет."
        return None, f"Ошибка загрузки: {e}"
