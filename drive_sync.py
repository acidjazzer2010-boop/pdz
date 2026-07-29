import io
import requests
import os
import re

def fetch_latest_report_from_nas():
    """
    Загружает отчет напрямую по ссылке шаринга Synology NAS с обходом веб-обертки.
    """
    cache_filename = "last_downloaded_report.xlsx"
    sharing_url = "http://45.130.190.72:6783/sharing/i4LaNSCbE"
    
    try:
        session = requests.Session()
        session.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        })
        
        # 1. Загружаем страницу шаринга, чтобы получить куки и csrf токены
        resp = session.get(sharing_url, timeout=15)
        
        if resp.status_code != 200:
            if os.path.exists(cache_filename):
                return open(cache_filename, "rb"), "⚠️ Ошибка доступа к ссылке. Использован кэш."
            return None, f"Ошибка HTTP: {resp.status_code}"
            
        # Если вдруг по ссылке уже отдается сам файл (например, настроен прямой поток)
        if len(resp.content) > 1000 and b"<html>" not in resp.content[:100]:
            with open(cache_filename, "wb") as f:
                f.write(resp.content)
            return io.BytesIO(resp.content), "✅ Отчет успешно загружен с Synology NAS!"
            
        # 2. Ищем API endpoint для скачивания внутри скриптов страницы шаринга Synology
        # Обычно Synology исполняет запрос к /webapi/entry.cgi для скачивания расшаренного файла
        base_nas = "http://45.130.190.72:6783"
        api_url = f"{base_nas}/webapi/entry.cgi"
        
        # Извлекаем ID шаринга из ссылки
        sharing_id = sharing_url.split("/")[-1]
        
        # Запрос к API File Station Sharing для получения файла
        api_params = {
            "api": "SYNO.FileStation.Sharing",
            "version": "1",
            "method": "download",
            "id": sharing_id
        }
        
        download_resp = session.get(api_url, params=api_params, timeout=20)
        
        if download_resp.status_code == 200 and len(download_resp.content) > 1000 and b"<html>" not in download_resp.content[:100]:
            with open(cache_filename, "wb") as f:
                f.write(download_resp.content)
            return io.BytesIO(download_resp.content), "✅ Отчет успешно загружен с Synology NAS через API!"
        else:
            # Если через API не удалось, пробуем альтернативный метод прямой загрузки через entry.cgi
            alt_params = {
                "api": "SYNO.FileStation.Download",
                "version": "2",
                "method": "download",
                "path": f"/{sharing_id}"
            }
            alt_resp = session.get(api_url, params=alt_params, timeout=20)
            
            if alt_resp.status_code == 200 and len(alt_resp.content) > 1000 and b"<html>" not in alt_resp.content[:100]:
                with open(cache_filename, "wb") as f:
                    f.write(alt_resp.content)
                return io.BytesIO(alt_resp.content), "✅ Отчет успешно загружен с Synology NAS!"
                
            if os.path.exists(cache_filename):
                return open(cache_filename, "rb"), "⚠️ Не удалось обойти веб-обертку NAS. Использован кэш."
            return None, "Ошибка: Ссылка шаринга защищена веб-интерфейсом Synology. Рекомендуется использовать WebDAV или положить файл в общую веб-папку (см. инструкцию выше)."
            
    except Exception as e:
        if os.path.exists(cache_filename):
            return open(cache_filename, "rb"), f"⚠️ Ошибка сети ({e}). Использован кэш."
        return None, f"Ошибка подключения к NAS: {e}"
