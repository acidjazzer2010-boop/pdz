import io
import requests
import pandas as pd
import streamlit as st

def load_report_from_gdrive(file_id_or_url):
    """
    Загружает Excel-файл с Google Drive по ID или публичной ссылке.
    """
    try:
        # Извлекаем file_id из ссылки, если передана полная ссылка вида https://drive.google.com/file/d/FILE_ID/view
        if "drive.google.com" in file_id_or_url:
            if "/d/" in file_id_or_url:
                file_id = file_id_or_url.split("/d/")[1].split("/")[0]
            elif "id=" in file_id_or_url:
                file_id = file_id_or_url.split("id=")[1].split("&")[0]
            else:
                return None, "Не удалось распознать ID файла из ссылки Google Drive."
        else:
            file_id = file_id_or_url.strip()

        # Формируем прямую ссылку на скачивание файла Google Drive
        download_url = f"https://drive.google.com/uc?export=download&id={file_id}"
        
        response = requests.get(download_url)
        if response.status_code == 200:
            return io.BytesIO(response.content), "Файл успешно загружен из Google Drive!"
        else:
            return None, f"Ошибка скачивания: HTTP статус {response.status_code}. Убедитесь, что у файла стоит доступ 'Всем, у кого есть ссылка'."
    except Exception as e:
        return None, str(e)
