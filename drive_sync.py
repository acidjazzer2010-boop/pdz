import io
import requests
import os
import streamlit as st

def fetch_latest_report_from_nas():
    """
    Загружает отчет по прямой публичной ссылке шаринга Synology NAS.
    """
    cache_filename = "last_downloaded_report.xlsx"
    
    # Прямая ссылка на ваш файл по шарингу
    sharing_url = "http://45.130.190.72:6783/sharing/i4LaNSCbE"
    
    try:
        # Загружаем файл напрямую по ссылке
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        }
        response = requests.get(sharing_url, headers=headers, timeout=20, allow_redirects=True)
        
        # Проверяем, что это действительно файл, а не страница ошибки (код 200 и размер > 1 КБ)
        if response.status_code == 200 and len(response.content) > 1000 and b"<html>" not in response.content[:100]:
            with open(cache_filename, "wb") as f:
                f.write(response.content)
            return io.BytesIO(response.content), "✅ Отчет успешно загружен с Synology NAS!"
        else:
            if os.path.exists(cache_filename):
                return open(cache_filename, "rb"), "⚠️ Ссылка шаринга недоступна. Использован кэш."
            return None, "Ошибка: По ссылке шаринга отдается не файл. Проверьте права ссылки в File Station."
            
    except Exception as e:
        if os.path.exists(cache_filename):
            return open(cache_filename, "rb"), f"⚠️ Ошибка сети ({e}). Использован кэш."
        return None, f"Ошибка подключения к NAS: {e}"
