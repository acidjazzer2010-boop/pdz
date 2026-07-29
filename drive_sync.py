import io
import requests
import os

def fetch_latest_report_from_nas():
    """
    Загружает свежий отчет по прямой HTTP-ссылке из веб-папки Synology NAS.
    """
    cache_filename = "last_downloaded_report.xlsx"
    
    # Укажите здесь вашу прямую ссылку на файл в папке web на NAS
    direct_url = "direct_url = "http://45.130.190.72:6783/ПДЗ.xlsx""
    
    try:
        response = requests.get(direct_url, timeout=20)
        
        # Проверяем, что скачался именно Excel-файл (статус 200 и размер > 1 КБ)
        if response.status_code == 200 and len(response.content) > 1000 and b"<html>" not in response.content[:100]:
            with open(cache_filename, "wb") as f:
                f.write(response.content)
            return io.BytesIO(response.content), "✅ Отчет успешно загружен с Synology NAS!"
        else:
            if os.path.exists(cache_filename):
                return open(cache_filename, "rb"), "⚠️ Файл на NAS недоступен. Использован предыдущий отчет (кэш)."
            return None, f"Ошибка: NAS вернул код {response.status_code}. Проверьте путь к файлу."
            
    except Exception as e:
        if os.path.exists(cache_filename):
            return open(cache_filename, "rb"), f"⚠️ Ошибка сети ({e}). Использован кэш."
        return None, f"Ошибка подключения к NAS: {e}"
