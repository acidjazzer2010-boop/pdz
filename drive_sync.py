import io
import requests
import os

def fetch_latest_report_from_nas():
    """
    Загружает свежий отчет по ссылке общего доступа Synology NAS.
    """
    cache_filename = "last_downloaded_report.xlsx"
    
    # Ваша ссылка общего доступа из Synology
    direct_url = "http://45.130.190.72:6783/sharing/i4LaNSCbE"
    
    try:
        response = requests.get(direct_url, timeout=20)
        
        # Если ссылка ведет на страницу загрузки Synology, скрипт попытается вытащить файл 
        # или сохранить то, что отдает сервер.
        if response.status_code == 200:
            # Проверяем, не пустой ли ответ
            if len(response.content) > 1000:
                with open(cache_filename, "wb") as f:
                    f.write(response.content)
                return io.BytesIO(response.content), "✅ Отчет успешно загружен с Synology NAS!"
                
        if os.path.exists(cache_filename):
            return open(cache_filename, "rb"), "⚠️ Файл по ссылке недоступен. Использован предыдущий отчет (кэш)."
        return None, f"Ошибка: сервер вернул код {response.status_code}."
            
    except Exception as e:
        if os.path.exists(cache_filename):
            return open(cache_filename, "rb"), f"⚠️ Ошибка сети ({e}). Использован кэш."
        return None, f"Ошибка подключения к NAS: {e}"
