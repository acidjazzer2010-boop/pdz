import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import streamlit as st

def send_report_via_email(html_content, recipient_email, smtp_config=None, subject="Сводный отчет по дебиторской задолженности"):
    """
    Отправляет HTML-отчет на электронную почту.
    Сначала проверяет st.secrets на сервере, если их нет — использует переданные настройки.
    """
    try:
        # Проверяем секреты на сервере Streamlit
        if "smtp" in st.secrets:
            smtp_server = st.secrets["smtp"]["server"]
            smtp_port = int(st.secrets["smtp"]["port"])
            sender_email = st.secrets["smtp"]["sender_email"]
            sender_password = st.secrets["smtp"]["sender_password"]
        elif smtp_config:
            # Используем данные из формы ручного ввода
            smtp_server = smtp_config["server"]
            smtp_port = int(smtp_config["port"])
            sender_email = smtp_config["sender_email"]
            sender_password = smtp_config["sender_password"]
        else:
            return False, "Не заданы настройки SMTP (проверьте st.secrets или поля ввода)."

        msg = MIMEMultipart()
        msg['From'] = sender_email
        msg['To'] = recipient_email
        msg['Subject'] = subject
        
        msg.attach(MIMEText("Здравствуйте!\n\nВо вложении находится актуальный сводный отчет по управлению дебиторской задолженностью.\n\nС уважением,\nФинансовый отдел", 'plain'))
        
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
