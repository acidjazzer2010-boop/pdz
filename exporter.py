import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import streamlit as st

def send_report_via_email(html_content, recipient_email, smtp_config=None, subject="Сводный отчет KRAYVIN", as_attachment=False):
    """
    Универсальная отправка HTML-сообщений/отчетов по SMTP.
    """
    try:
        smtp_server = None
        smtp_port = 465
        sender_email = None
        sender_password = None

        # 1. Чтение секретов
        if "SMTP_SERVER" in st.secrets:
            smtp_server = st.secrets["SMTP_SERVER"]
            smtp_port = int(st.secrets.get("SMTP_PORT", 465))
            sender_email = st.secrets.get("SMTP_USER", "")
            sender_password = st.secrets.get("SMTP_PASSWORD", "")
        elif "smtp" in st.secrets:
            smtp_server = st.secrets["smtp"].get("server")
            smtp_port = int(st.secrets["smtp"].get("port", 465))
            sender_email = st.secrets["smtp"].get("sender_email") or st.secrets["smtp"].get("user")
            sender_password = st.secrets["smtp"].get("sender_password") or st.secrets["smtp"].get("password")
        elif smtp_config:
            smtp_server = smtp_config.get("server")
            smtp_port = int(smtp_config.get("port", 465))
            sender_email = smtp_config.get("sender_email")
            sender_password = smtp_config.get("sender_password")

        if not smtp_server or not sender_email or not sender_password:
            error_msg = f"ОШИБКА: Не заполнена конфигурация SMTP в st.secrets! (server={smtp_server}, user={sender_email})"
            print(f"[SMTP ERROR] {error_msg}")
            return False, error_msg

        # 2. Формирование письма
        msg = MIMEMultipart()
        msg['From'] = sender_email
        msg['To'] = recipient_email
        msg['Subject'] = subject

        if as_attachment:
            body_text = "Здравствуйте!\n\nВо вложении находится актуальный сводный отчет.\n\nС уважением,\nФинансовый отдел"
            msg.attach(MIMEText(body_text, 'plain', 'utf-8'))
            
            html_attachment = MIMEText(html_content, 'html', 'utf-8')
            html_attachment.add_header('Content-Disposition', 'attachment', filename='report.html')
            msg.attach(html_attachment)
        else:
            msg.attach(MIMEText(html_content, 'html', 'utf-8'))

        # 3. Подключение и отправка
        if smtp_port == 465:
            server = smtplib.SMTP_SSL(smtp_server, smtp_port, timeout=10)
        else:
            server = smtplib.SMTP(smtp_server, smtp_port, timeout=10)
            server.starttls()

        server.login(sender_email, sender_password)
        server.sendmail(sender_email, recipient_email, msg.as_string())
        server.quit()

        print(f"[SMTP SUCCESS] Письмо успешно отправлено на {recipient_email}")
        return True, "Сообщение успешно отправлено!"

    except smtplib.SMTPAuthenticationError:
        err = "Ошибка авторизации SMTP: неверный логин или пароль приложения."
        print(f"[SMTP ERROR] {err}")
        return False, err
    except Exception as e:
        err = f"Ошибка отправки SMTP: {str(e)}"
        print(f"[SMTP ERROR] {err}")
        return False, err


def generate_html_report_bytes():
    return b""

def send_report_to_email():
    pass
