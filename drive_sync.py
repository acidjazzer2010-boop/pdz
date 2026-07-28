import io
import requests
import os
import streamlit as st

def fetch_latest_report_from_gdrive():
    """
    Автоматически забирает файл из Google Drive по ID или полной ссылке,
    с сохранением локального кэша (предыдущего файла) при сбое.
    """
    cache_filename = "last_downloaded_report.xlsx"
    gdrive_input = st.secrets.get("GDRIVE_FILE_ID", "")
    
    if not gdrive_input:
        if os.path.exists(cache_filename):
            return open(cache_filename, "rb"), "⚠️ GDRIVE_FILE_ID не задан в secrets. Использован предыдущий кэш."
        return None, "Не задан GDRIVE_FILE_ID в настройках st.secrets."

    # Извлекаем ID из любой ссылки Google Drive или оставляем как есть, если это чистый ID
    file_id = gdrive_input.strip()
    if "drive.google.com" in file_id or "docs.google.com" in file_id:
        if "/d/" in file_id:
            try:
                file_id = file_id.split("/d/")[1].split("/")[0]
            except:
                pass

    try:
        # Прямая ссылка на экспорт/скачивание файла Google Drive
        download_url = f"https://drive.google.com/uc?export=download&id={file_id}"
        response = requests.get(download_url, timeout=10)
        
        # Проверяем, что файл скачался (размер больше 1 КБ и это не страница авторизации Google)
        if response.status_code == 200 and len(response.content) > 1000 and b"<html>" not in response.content[:100]:
            with open(cache_filename, "wb") as f:
                f.write(response.content)
            return io.BytesIO(response.content), "✅ Отчет успешно загружен из Google Drive!"
        else:
            # Если файл не отдал данные (например, закрыт доступ), берем кэш
            if os.path.exists(cache_filename):
                return open(cache_filename, "rb"), "⚠️ Google Drive недоступен или нет прав 'Всем по ссылке'. Использован предыдущий отчет (кэш)."
            return None, "Ошибка доступа к Google Drive. Проверьте права доступа файла ('Всем, у кого есть ссылка')."
            
    except Exception as e:
        if os.path.exists(cache_filename):
            return open(cache_filename, "rb"), f"⚠️ Ошибка сети ({e}). Использован предыдущий отчет (кэш)."
        return None, f"Ошибка загрузки: {e}"
