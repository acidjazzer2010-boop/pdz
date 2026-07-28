import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import streamlit as st

def send_report_via_email(html_content, recipient_email, smtp_config=None, subject="Сводный отчет по дебиторской задолженности"):
    """
    Отправляет HTML-отчет на электронную почту с поддержкой st.secrets (как flat, так и nested) или ручного ввода.
    """
    try:
        smtp_server = None
        smtp_port = None
        sender_email = None
        sender_password = None

        # 1. Проверяем flat секреты (как ввел пользователь: SMTP_SERVER, etc.)
        if "SMTP_SERVER" in st.secrets:
            smtp_server = st.secrets["SMTP_SERVER"]
            smtp_port = int(st.secrets.get("SMTP_PORT", 465))
            sender_email = st.secrets.get("SMTP_USER", "")
            sender_password = st.secrets.get("SMTP_PASSWORD", "")
        # 2. Проверяем вложенные секреты [smtp]
        elif "smtp" in st.secrets:
            smtp_server = st.secrets["smtp"].get("server")
            smtp_port = int(st.secrets["smtp"].get("port", 465))
            sender_email = st.secrets["smtp"].get("sender_email") or st.secrets["smtp"].get("user")
            sender_password = st.secrets["smtp"].get("sender_password") or st.secrets["smtp"].get("password")
        # 3. Используем ручной ввод из формы
        elif smtp_config:
            smtp_server = smtp_config["server"]
            smtp_port = int(smtp_config["port"])
            sender_email = smtp_config["sender_email"]
            sender_password = smtp_config["sender_password"]

        if not smtp_server or not sender_email or not sender_password:
            return False, "Не удалось найти параметры SMTP. Проверьте st.secrets или поля ввода."

        msg = MIMEMultipart()
        msg['From'] = sender_email
        msg['To'] = recipient_email
        msg['Subject'] = subject
        
        msg.attach(MIMEText("Здравствуйте!

Во вложении находится актуальный сводный отчет по управлению дебиторской задолженностью.

С уважением,
Финансовый отдел", 'plain'))
        
        html_attachment = MIMEText(html_content, 'html', 'utf-8')
        html_attachment.add_header('Content-Disposition', 'attachment', filename='debt_report.html')
        msg.attach(html_attachment)
        
        server = smtplib.SMTP_SSL(smtp_server, smtp_port)
        server.login(sender_email, sender_password)
        server.sendmail(sender_email, recipient_email, msg.as_string())
        server.quit()
        
        return True, "Отчет успешно отправлен!"
    except Exception as e:
        return False, str(e)
