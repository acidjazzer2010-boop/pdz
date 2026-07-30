import io
import requests
import os

def fetch_latest_report_from_nas():
    cache_filename = "last_downloaded_report.xlsx"
    
    # Прямая ссылка на файл (убедитесь, что файл лежит в папке web на NAS)
    direct_url = "http://45.130.190.72:6783/ПДЗ.xlsx"
    
    try:
        response = requests.get(direct_url, timeout=20)
        
        # Проверка: статус 200 И первые символы файла соответствуют ZIP/XLSX архиву (b'PK\x03\x04')
        if response.status_code == 200 and response.content.startswith(b'PK'):
            with open(cache_filename, "wb") as f:
                f.write(response.content)
            return io.BytesIO(response.content), "✅ Отчет успешно загружен с Synology NAS!"
        else:
            # Если вернулся HTML (404 или страница входа), пытаемся взять старый кэш
            if os.path.exists(cache_filename):
                with open(cache_filename, "rb") as f:
                    content = f.read()
                if content.startswith(b'PK'):
                    return io.BytesIO(content), "⚠️ Файл на NAS недоступен/не найден. Использован предыдущий отчет из кэша."
            
            return None, f"Ошибка: Сервер вернул код {response.status_code} или невалидный файл (не Excel)."
            
    except Exception as e:
        if os.path.exists(cache_filename):
            with open(cache_filename, "rb") as f:
                content = f.read()
            if content.startswith(b'PK'):
                return io.BytesIO(content), f"⚠️ Ошибка сети ({e}). Использован кэш."
        return None, f"Ошибка подключения к NAS: {e}"
