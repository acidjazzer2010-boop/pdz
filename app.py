import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
import os
import datetime
import html
import hmac
import hashlib
from io import BytesIO

# Попытка импорта библиотеки для безопасного хеширования паролей
try:
    from werkzeug.security import check_password_hash
except ImportError:
    # Запасной вариант безопасного сравнения, если werkzeug не установлен
    def check_password_hash(stored_hash, password):
        # Ожидается хэш sha256
        computed_hash = hashlib.sha256(password.encode('utf-8')).hexdigest()
        return hmac.compare_digest(stored_hash, computed_hash)

# --- ИМПОРТ ВНЕШНИХ МОДУЛЕЙ ---
try:
    from drive_sync import fetch_latest_report_from_nas
except ImportError:
    fetch_latest_report_from_nas = None

try:
    from exporter import generate_html_report_bytes, send_report_to_email, send_report_via_email
except ImportError:
    generate_html_report_bytes = None
    send_report_to_email = None
    send_report_via_email = None

# --- 1. НАСТРОЙКА СТРАНИЦЫ И ТЕМЫ ---
st.set_page_config(
    page_title="Личный кабинет KRAYVIN",
    page_icon="🍷",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown("""
    <style>
    .main { background-color: #F8F9FA; }
    .stMetric {
        background-color: #FFFFFF;
        padding: 15px;
        border-radius: 8px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.05);
        border-left: 4px solid #642A38;
    }
    h1, h2, h3 { color: #642A38; }
    </style>
""", unsafe_allow_html=True)

# --- 2. СКРЫТЫЕ ФУНКЦИИ БЕЗОПАСНОСТИ И ЛОГИРОВАНИЯ ---

def get_client_ip():
    """Скрыто получает IP-адрес с базовой очисткой."""
    try:
        headers = st.context.headers
        if "X-Forwarded-For" in headers:
            # Берем первый IP и фильтруем от невалидных символов
            raw_ip = headers["X-Forwarded-For"].split(",")[0].strip()
            return html.escape(raw_ip[:45])  # Ограничение длины IPv6
        elif "Remote-Addr" in headers:
            return html.escape(headers["Remote-Addr"][:45])
    except Exception:
        pass
    return "127.0.0.1 (Local/Unknown)"

def log_access_event_silent(username, status, role="—"):
    """Фоново записывает событие входа с обработкой ошибок доступа к файлу."""
    try:
        log_file = "access_log.csv"
        now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        ip_address = get_client_ip()
        
        # Экранируем имя пользователя для защиты CSV от инъекций
        safe_username = html.escape(username[:50])
        
        new_entry = pd.DataFrame([{
            "Timestamp": now,
            "Username": safe_username,
            "Status": status,
            "IP_Address": ip_address,
            "Role": role
        }])
        
        if os.path.exists(log_file):
            new_entry.to_csv(log_file, mode='a', header=False, index=False, encoding='utf-8-sig')
        else:
            new_entry.to_csv(log_file, mode='w', header=True, index=False, encoding='utf-8-sig')
    except Exception as e:
        print(f"[LOG ERROR] Не удалось записать лог: {e}")

def send_security_alert_silent(attempted_username, ip_address, is_success, role="—"):
    """Скрыто отправляет почтовое уведомление о входе с экранированием HTML-инъекций."""
    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    target_email = (
        st.secrets.get("ALERT_EMAIL") 
        or st.secrets.get("security", {}).get("alert_email", "e.hasanov@kraivin.ru")
    )
    
    # Экранирование ввода пользователя от HTML/Header Injection
    safe_username = html.escape(str(attempted_username)[:50]).replace('\n', '').replace('\r', '')
    safe_ip = html.escape(str(ip_address)[:45])
    safe_role = html.escape(str(role)[:30])
    
    if is_success:
        subject_icon = "✅"
        status_text = "Успешная авторизация"
        color = "#28a745"
    else:
        subject_icon = "⚠️"
        status_text = "ОШИБКА АВТОРИЗАЦИИ (Неверный пароль)"
        color = "#dc3545"

    subject_line = f"{subject_icon} Безопасность: Вход '{safe_username}' [{status_text}]"

    alert_html = f"""
    <!DOCTYPE html>
    <html lang="ru">
    <head>
        <meta charset="utf-8">
        <style>
            body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif; color: #1d1d1f; line-height: 1.5; background-color: #f5f5f7; padding: 20px; }}
            .card {{ background: #ffffff; border-radius: 12px; padding: 24px; max-width: 550px; margin: 0 auto; box-shadow: 0 4px 12px rgba(0,0,0,0.08); border-left: 6px solid {color}; }}
            h3 {{ color: #642A38; margin-top: 0; }}
            .status {{ color: {color}; font-weight: 700; display: inline-block; padding: 4px 8px; background: rgba(0,0,0,0.04); border-radius: 6px; }}
            hr {{ border: none; border-top: 1px solid #e5e5ea; margin: 20px 0; }}
            .footer {{ font-size: 12px; color: #8e8e93; text-align: center; }}
        </style>
    </head>
    <body>
        <div class="card">
            <h3>{subject_icon} Служебное уведомление безопасности</h3>
            <p><b>Статус попытки:</b> <span class="status">{status_text}</span></p>
            <p><b>Дата и время:</b> {now}</p>
            <p><b>Введенный логин:</b> {safe_username}</p>
            <p><b>Назначенная роль:</b> {safe_role}</p>
            <p><b>IP-адрес пользователя:</b> {safe_ip}</p>
            <hr>
            <p class="footer">Система мониторинга доступа KRAYVIN</p>
        </div>
    </body>
    </html>
    """
    
    if send_report_via_email:
        try:
            send_report_via_email(
                html_content=alert_html, 
                recipient_email=target_email, 
                subject=subject_line, 
                as_attachment=False
            )
        except Exception as e:
            print(f"[SECURITY ALERT EXCEPTION]: {e}")

# --- 3. ЕДИНАЯ АВТОРИЗАЦИЯ И СЕССИЯ ---
if "authenticated" not in st.session_state:
    st.session_state.authenticated = False
    st.session_state.username = None
    st.session_state.role = None
    st.session_state.name = None

def verify_credentials(username, password):
    users_dict = st.secrets.get("users", {})
    ip_addr = get_client_ip()
    
    if username in users_dict:
        user_data = users_dict[username]
        stored_password = user_data.get("password")
        stored_hash = user_data.get("password_hash")
        
        is_valid = False
        
        # 1. Проверка по хешу (Рекомендуется)
        if stored_hash:
            is_valid = check_password_hash(stored_hash, password)
        # 2. Обратная совместимость с открытым паролем через защищенное сравнение hmac
        elif stored_password:
            is_valid = hmac.compare_digest(stored_password, password)

        if is_valid:
            role = user_data.get("role", "Сотрудник")
            name = user_data.get("name", username)
            
            log_access_event_silent(username, "SUCCESS", role)
            send_security_alert_silent(username, ip_addr, is_success=True, role=role)
            return True, role, name

    # Если логин не найден или пароль неверный
    log_access_event_silent(username, "FAILED_LOGIN", "—")
    send_security_alert_silent(username, ip_addr, is_success=False, role="—")
    return False, None, None

# Экран входа
if not st.session_state.authenticated:
    st.markdown("<h2 style='text-align: center; color: #642A38;'>🔐 Личный кабинет KRAYVIN</h2>", unsafe_allow_html=True)
    col1, col2, col3 = st.columns([1, 1.2, 1])
    with col2:
        with st.form("login_form"):
            username_input = st.text_input("Логин", key="login_username_input")
            password_input = st.text_input("Пароль", type="password", key="login_password_input")
            submit_button = st.form_submit_button("Войти в систему", use_container_width=True)
            
            if submit_button:
                is_valid, role, name = verify_credentials(username_input, password_input)
                if is_valid:
                    st.session_state.authenticated = True
                    st.session_state.username = username_input
                    st.session_state.role = role
                    st.session_state.name = name
                    st.rerun()
                else:
                    st.error("❌ Неверный логин или пароль.")
    st.stop()

# --- 4. БОКОВАЯ ПАНЕЛЬ И НАВИГАЦИЯ ---
logo_path = "КРАЙВИН лого винный квадрат.png"
if os.path.exists(logo_path):
    st.sidebar.image(logo_path, use_container_width=True)

st.sidebar.markdown(f"👤 **{html.escape(st.session_state.name)}**")
st.sidebar.markdown(f"🔑 Роль: {html.escape(st.session_state.role)}")

if st.sidebar.button("🚪 Выйти из системы", key="logout_btn"):
    st.session_state.authenticated = False
    st.session_state.username = None
    st.session_state.role = None
    st.session_state.name = None
    st.rerun()

st.sidebar.markdown("---")

active_module = st.sidebar.radio(
    "📌 Выберите сервис:",
    ["🧮 Анализ денежных потоков", "📈 Управление дебиторской задолженностью"],
    key="main_active_module_radio"
)

st.sidebar.markdown("---")

# ==============================================================================
# МОДУЛЬ 1: ФИНАНСОВЫЙ КАЛЬКУЛЯТОР ДЕНЕЖНЫХ ПОТОКОВ
# ==============================================================================
if active_module == "🧮 Анализ денежных потоков":
    st.title("Анализ денежных потоков и рентабельности")
    st.markdown("Интерактивная финансовая модель для сценарного анализа кассовых разрывов.")

    st.sidebar.header("Параметры финансовой модели")
    ru_months_full = ['Январь', 'Февраль', 'Март', 'Апрель', 'Май', 'Июнь', 'Июль', 'Август', 'Сентябрь', 'Октябрь', 'Ноябрь', 'Декабрь']
    col_m, col_y = st.sidebar.columns(2)
    start_month_idx = col_m.selectbox("Месяц старта", range(12), format_func=lambda x: ru_months_full[x], key="cf_start_month")
    start_year = col_y.selectbox("Год старта", [2026, 2027], key="cf_start_year")

    margin_pct = st.sidebar.slider("Маржинальность (%)", min_value=10, max_value=50, value=20, step=1, key="cf_margin")
    period = st.sidebar.selectbox("Горизонт планирования (мес)", [6, 12, 18, 24], key="cf_period")

    st.sidebar.subheader("Стартовый капитал и закупки")
    initial_purchase = st.sidebar.number_input("Первоначальная закупка товара (руб)", value=5_000_000, step=500_000, key="cf_init_purchase")
    initial_cash_buffer = st.sidebar.number_input("Стартовый денежный буфер (на счете)", value=2_000_000, step=500_000, key="cf_init_buffer")

    st.sidebar.subheader("Динамика продаж")
    aov = st.sidebar.number_input("Средняя сумма заказа (руб)", value=150_000, step=10_000, key="cf_aov")
    start_orders = st.sidebar.number_input("Заказов в 1-й месяц (шт)", value=40, step=1, key="cf_start_orders")
    orders_growth = st.sidebar.slider("Ежемесячный прирост заказов (%)", 0, 100, 15, step=1, key="cf_orders_growth")
    scale_factor = st.sidebar.slider("Коэффициент масштабирования продаж", 0.5, 3.0, 1.0, 0.1, key="cf_scale_factor")

    st.sidebar.subheader("Команда и расходы")
    monthly_fot = st.sidebar.number_input("ФОТ в месяц (руб)", value=500_000, step=50_000, key="cf_monthly_fot")

    st.sidebar.subheader("Работа с поставщиками")
    prepayment_pct = st.sidebar.slider("Предоплата поставщикам (%)", 0, 100, 50, step=10, key="cf_prepayment")
    delay_days = st.sidebar.slider("Отсрочка на остаток (дней)", 0, 90, 40, step=5, key="cf_delay_days")

    st.sidebar.subheader("Факторинг")
    factoring_share = st.sidebar.slider("Доля выручки в факторинге (%)", 0, 100, 50, step=10, key="cf_fact_share")
    factoring_advance = st.sidebar.slider("Аванс от фактора (%)", 50, 100, 80, step=5, key="cf_fact_advance")

    st.sidebar.subheader("Условия с покупателями")
    customer_delay_days = st.sidebar.slider("Отсрочка платежа покупателям (дней)", 0, 120, 70, step=5, key="cf_cust_delay")

    # Расчеты
    ru_months_short = ['Янв', 'Фев', 'Мар', 'Апр', 'Май', 'Июн', 'Июл', 'Авг', 'Сен', 'Окт', 'Ноя', 'Дек']
    x_labels = [f"{ru_months_short[(start_month_idx + i) % 12]} {start_year + ((start_month_idx + i) // 12)}" for i in range(period)]

    orders = np.zeros(period)
    rev = np.zeros(period)
    for i in range(period):
        orders[i] = start_orders * scale_factor if i == 0 else orders[i-1] * (1 + (orders_growth / 100))
        rev[i] = orders[i] * aov

    cogs_vat = (rev * (1 - margin_pct / 100)) * 1.2
    delay_months_suppliers = max(1, int(round(delay_days / 30))) if delay_days > 0 else 0
    cogs_payments = np.zeros(period)

    for i in range(period):
        cogs_payments[i] += cogs_vat[i] * (prepayment_pct / 100)
        if i + delay_months_suppliers < period:
            cogs_payments[i + delay_months_suppliers] += cogs_vat[i] * ((100 - prepayment_pct) / 100)

    cogs_payments[0] += initial_purchase * (prepayment_pct / 100)
    if delay_months_suppliers < period:
        cogs_payments[delay_months_suppliers] += initial_purchase * ((100 - prepayment_pct) / 100)

    customer_delay_months = max(0, int(round(customer_delay_days / 30)))
    inflows = np.zeros(period)
    for i in range(period):
        inflows[i] += rev[i] * 1.2 * (factoring_share / 100) * (factoring_advance / 100)
        target_month = i + customer_delay_months
        if target_month < period:
            inflows[target_month] += rev[i] * 1.2 * ((100 - factoring_share) / 100)
            inflows[target_month] += rev[i] * 1.2 * (factoring_share / 100) * ((100 - factoring_advance) / 100)

    base_other_opex = 150_000
    opex = np.full(period, base_other_opex + monthly_fot)
    for i in range(6, period):
        opex[i] = (base_other_opex * 1.2) + monthly_fot

    taxes_and_commissions = rev * 0.05
    outflows = cogs_payments + opex + taxes_and_commissions
    net_cf = inflows - outflows
    cum_cf = np.cumsum(net_cf)
    cash_balance = cum_cf + initial_cash_buffer

    max_deficit = float(min(min(cum_cf), 0))
    net_profit = float(sum(rev * (margin_pct / 100)) - sum(opex) - sum(taxes_and_commissions) - (initial_purchase * 0.15))
    roi = (net_profit / sum(rev)) * 100 if sum(rev) > 0 else 0.0

    def format_rub(val):
        return f"{val:,.0f}".replace(",", " ") + " руб."

    col1, col2, col3, col4 = st.columns(4)
    col1.metric(f"Выручка (за {period} мес)", format_rub(sum(rev)))
    col2.metric("Макс. кассовый разрыв", format_rub(max_deficit))
    col3.metric("Чистая прибыль", format_rub(net_profit))
    col4.metric("Рентабельность по ЧП", f"{roi:.1f}%")

    st.divider()

    tab1, tab2, tab3 = st.tabs(["💰 Ликвидность и Денежный поток", "📈 Рентабельность и Источники", "📉 Накопленный итог и Расходы"])

    with tab1:
        st.markdown("### Динамика ликвидности и остаток средств")
        fig1 = go.Figure()
        fig1.add_trace(go.Scatter(x=x_labels, y=cash_balance, mode='lines+markers+text', name='Остаток ДС', text=[f"{v:,.0f}" for v in cash_balance], line=dict(color='#642A38', width=3), fill='tozeroy'))
        fig1.add_hline(y=0, line_dash="dash", line_color="red")
        st.plotly_chart(fig1, use_container_width=True, key="cf_chart_liquidity")

    with tab2:
        st.markdown("### Динамика маржинальности и EBITDA")
        fig3 = go.Figure()
        ebitda_vals = rev - opex - taxes_and_commissions
        fig3.add_trace(go.Bar(x=x_labels, y=ebitda_vals, name='EBITDA', marker_color='#642A38'))
        st.plotly_chart(fig3, use_container_width=True, key="cf_chart_ebitda")

    with tab3:
        st.markdown("### Накопленный денежный поток")
        fig5 = go.Figure()
        fig5.add_trace(go.Scatter(x=x_labels, y=cum_cf + initial_cash_buffer, mode='lines+markers', name='Накопленный ДС', line=dict(color='#642A38', width=3)))
        st.plotly_chart(fig5, use_container_width=True, key="cf_chart_cum_cf")

    # --- ПАНЕЛЬ ЭКСПОРТА ---
    st.divider()
    st.subheader("📤 Экспорт финансовой модели")
    
    cf_df = pd.DataFrame({
        "Месяц": x_labels,
        "Выручка (₽)": [f"{v:,.0f}".replace(",", " ") for v in rev],
        "Поступления (₽)": [f"{v:,.0f}".replace(",", " ") for v in inflows],
        "Выплаты (₽)": [f"{v:,.0f}".replace(",", " ") for v in outflows],
        "Чистый ДП (₽)": [f"{v:,.0f}".replace(",", " ") for v in net_cf],
        "Остаток ДС (₽)": [f"{v:,.0f}".replace(",", " ") for v in cash_balance]
    })

    html_cf_report = f"""
    <!DOCTYPE html>
    <html lang="ru">
    <head>
        <meta charset="utf-8">
        <style>
            body {{ font-family: -apple-system, BlinkMacSystemFont, "SF Pro Display", "Segoe UI", Roboto, Helvetica, Arial, sans-serif; color: #1d1d1f; background-color: #f5f5f7; margin: 0; padding: 40px 20px; }}
            .container {{ max-width: 960px; margin: 0 auto; background: #ffffff; border-radius: 16px; padding: 32px; box-shadow: 0 4px 20px rgba(0,0,0,0.06); }}
            .header {{ border-bottom: 2px solid #642A38; padding-bottom: 16px; margin-bottom: 24px; display: flex; justify-content: space-between; align-items: center; }}
            h1 {{ color: #642A38; margin: 0; font-size: 24px; font-weight: 700; }}
            .date {{ color: #8e8e93; font-size: 14px; }}
            .metrics-grid {{ display: grid; grid-template-columns: repeat(4, 1fr); gap: 16px; margin-bottom: 28px; }}
            .metric-card {{ background: #fafafa; border: 1px solid #e5e5ea; border-radius: 12px; padding: 16px; border-left: 4px solid #642A38; }}
            .metric-label {{ font-size: 12px; color: #8e8e93; text-transform: uppercase; letter-spacing: 0.5px; font-weight: 600; margin-bottom: 4px; }}
            .metric-value {{ font-size: 18px; font-weight: 700; color: #1d1d1f; }}
            table {{ width: 100%; border-collapse: separate; border-spacing: 0; margin-top: 16px; border-radius: 8px; overflow: hidden; border: 1px solid #e5e5ea; }}
            th {{ background-color: #642A38; color: #ffffff; text-align: left; padding: 12px 16px; font-size: 13px; font-weight: 600; }}
            td {{ padding: 12px 16px; border-bottom: 1px solid #e5e5ea; font-size: 13px; color: #3a3a3c; }}
            tr:nth-child(even) {{ background-color: #fbfbfd; }}
            tr:last-child td {{ border-bottom: none; }}
            .footer {{ margin-top: 32px; text-align: center; color: #8e8e93; font-size: 12px; }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>📊 Финансовая модель денежных потоков</h1>
                <div class="date">{datetime.datetime.now().strftime('%d.%m.%Y %H:%M')}</div>
            </div>
            
            <div class="metrics-grid">
                <div class="metric-card">
                    <div class="metric-label">Выручка ({period} мес)</div>
                    <div class="metric-value">{format_rub(sum(rev))}</div>
                </div>
                <div class="metric-card">
                    <div class="metric-label">Макс. Кассовый разрыв</div>
                    <div class="metric-value" style="color: #d70015;">{format_rub(max_deficit)}</div>
                </div>
                <div class="metric-card">
                    <div class="metric-label">Чистая прибыль</div>
                    <div class="metric-value">{format_rub(net_profit)}</div>
                </div>
                <div class="metric-card">
                    <div class="metric-label">Рентабельность</div>
                    <div class="metric-value">{roi:.1f}%</div>
                </div>
            </div>

            {cf_df.to_html(index=False, border=0)}

            <div class="footer">
                Конфиденциально
            </div>
        </div>
    </body>
    </html>
    """

    exp_col1, exp_col2 = st.columns(2)
    with exp_col1:
        st.download_button(
            label="📥 Скачать финансовую модель (HTML)",
            data=html_cf_report,
            file_name=f"cashflow_model_{datetime.datetime.now().strftime('%Y%m%d')}.html",
            mime="text/html",
            use_container_width=True,
            key="dl_cf_html"
        )

    with exp_col2:
        target_email_input = st.text_input("Email для отправки модели:", value=st.secrets.get("ALERT_EMAIL", ""), key="email_cf")
        if st.button("📧 Отправить отчет по Email", use_container_width=True, key="send_cf_email"):
            if send_report_via_email and target_email_input:
                ok, msg = send_report_via_email(
                    html_content=html_cf_report,
                    recipient_email=target_email_input,
                    subject="📊 Финансовая модель денежных потоков",
                    as_attachment=True
                )
                if ok:
                    st.success("✅ Финансовый отчет успешно отправлен!")
                else:
                    st.error(f"❌ Ошибка отправки: {msg}")
            else:
                st.warning("Введите корректный E-mail или проверьте модуль отправки.")


# ==============================================================================
# МОДУЛЬ 2: УПРАВЛЕНИЕ ДЕБИТОРСКОЙ ЗАДОЛЖЕННОСТЬЮ
# ==============================================================================
elif active_module == "📈 Управление дебиторской задолженностью":
    st.title("📈 Управление дебиторской задолженностью")

    @st.cache_data
    def load_hierarchy_data(file_bytes):
        df_raw = pd.read_excel(file_bytes, header=None)
        
        def safe_float(val):
            try:
                val_str = str(val).replace(',', '.').replace(' ', '').strip()
                return float(val_str)
            except:
                return 0.0

        hierarchy = []
        for idx in range(8, len(df_raw)):
            row = df_raw.iloc[idx]
            client_name = str(row.iloc[0]).strip() if pd.notna(row.iloc[0]) else ""
            if not client_name or client_name in ["nan", "None", "Итого", "Всего"]:
                continue
            total_debt = safe_float(row.iloc[4])
            overdue_debt = safe_float(row.iloc[6])
            hierarchy.append({
                'Клиент': client_name,
                'Общий долг': total_debt,
                'Просрочено': overdue_debt,
                'Не просрочено': max(0.0, total_debt - overdue_debt),
                'Просрочено (%)': (overdue_debt / total_debt * 100) if total_debt > 0 else 0.0,
                'Комментарий': ''
            })

        return pd.DataFrame(), hierarchy

    if fetch_latest_report_from_nas is not None:
        target_file, fetch_message = fetch_latest_report_from_nas()
    else:
        target_file, fetch_message = None, "Модуль drive_sync не загружен."

    if target_file is not None:
        _, hierarchy = load_hierarchy_data(target_file)
        clients_df = pd.DataFrame(hierarchy)
        
        if not clients_df.empty:
            total_portfolio = clients_df['Общий долг'].sum()
            total_overdue = clients_df['Просрочено'].sum()
            
            c1, c2, c3 = st.columns(3)
            c1.metric("Общий портфель долга", f"{total_portfolio:,.2f} ₽")
            c2.metric("Просрочено (ПДЗ)", f"{total_overdue:,.2f} ₽", delta_color="inverse")
            c3.metric("Контрагентов", len(clients_df))
            
            st.dataframe(clients_df[['Клиент', 'Общий долг', 'Просрочено', 'Не просрочено']], use_container_width=True)

            # --- ПАНЕЛЬ ЭКСПОРТА ---
            st.divider()
            st.subheader("📤 Экспорт отчета по ПДЗ")

            export_df = clients_df.copy()
            export_df['Общий долг (₽)'] = export_df['Общий долг'].apply(lambda x: f"{x:,.2f}".replace(",", " "))
            export_df['Просрочено (₽)'] = export_df['Просрочено'].apply(lambda x: f"{x:,.2f}".replace(",", " "))
            export_df['Не просрочено (₽)'] = export_df['Не просрочено'].apply(lambda x: f"{x:,.2f}".replace(",", " "))
            export_df['Просрочено (%)'] = export_df['Просрочено (%)'].apply(lambda x: f"{x:.1f}%")

            total_portfolio_fmt = f"{total_portfolio:,.2f}".replace(",", " ")
            total_overdue_fmt = f"{total_overdue:,.2f}".replace(",", " ")

            html_pdz_report = f"""
            <!DOCTYPE html>
            <html lang="ru">
            <head>
                <meta charset="utf-8">
                <style>
                    body {{ font-family: -apple-system, BlinkMacSystemFont, "SF Pro Display", "Segoe UI", Roboto, Helvetica, Arial, sans-serif; color: #1d1d1f; background-color: #f5f5f7; margin: 0; padding: 40px 20px; }}
                    .container {{ max-width: 980px; margin: 0 auto; background: #ffffff; border-radius: 16px; padding: 32px; box-shadow: 0 4px 20px rgba(0,0,0,0.06); }}
                    .header {{ border-bottom: 2px solid #642A38; padding-bottom: 16px; margin-bottom: 24px; display: flex; justify-content: space-between; align-items: center; }}
                    h1 {{ color: #642A38; margin: 0; font-size: 24px; font-weight: 700; }}
                    .date {{ color: #8e8e93; font-size: 14px; }}
                    .metrics-grid {{ display: grid; grid-template-columns: repeat(3, 1fr); gap: 16px; margin-bottom: 28px; }}
                    .metric-card {{ background: #fafafa; border: 1px solid #e5e5ea; border-radius: 12px; padding: 16px; border-left: 4px solid #642A38; }}
                    .metric-label {{ font-size: 12px; color: #8e8e93; text-transform: uppercase; letter-spacing: 0.5px; font-weight: 600; margin-bottom: 4px; }}
                    .metric-value {{ font-size: 20px; font-weight: 700; color: #1d1d1f; }}
                    table {{ width: 100%; border-collapse: separate; border-spacing: 0; margin-top: 16px; border-radius: 8px; overflow: hidden; border: 1px solid #e5e5ea; }}
                    th {{ background-color: #642A38; color: #ffffff; text-align: left; padding: 12px 16px; font-size: 13px; font-weight: 600; }}
                    td {{ padding: 12px 16px; border-bottom: 1px solid #e5e5ea; font-size: 13px; color: #3a3a3c; }}
                    tr:nth-child(even) {{ background-color: #fbfbfd; }}
                    tr:last-child td {{ border-bottom: none; }}
                    .overdue {{ color: #d70015; font-weight: 600; }}
                    .footer {{ margin-top: 32px; text-align: center; color: #8e8e93; font-size: 12px; }}
                </style>
            </head>
            <body>
                <div class="container">
                    <div class="header">
                        <h1>📈 Отчет по дебиторской задолженности</h1>
                        <div class="date">{datetime.datetime.now().strftime('%d.%m.%Y %H:%M')}</div>
                    </div>
                    
                    <div class="metrics-grid">
                        <div class="metric-card">
                            <div class="metric-label">Общий портфель долга</div>
                            <div class="metric-value">{total_portfolio_fmt} ₽</div>
                        </div>
                        <div class="metric-card">
                            <div class="metric-label">Просрочено (ПДЗ)</div>
                            <div class="metric-value overdue">{total_overdue_fmt} ₽</div>
                        </div>
                        <div class="metric-card">
                            <div class="metric-label">Всего контрагентов</div>
                            <div class="metric-value">{len(clients_df)}</div>
                        </div>
                    </div>

                    {export_df[['Клиент', 'Общий долг (₽)', 'Просрочено (₽)', 'Не просрочено (₽)', 'Просрочено (%)']].to_html(index=False, border=0)}

                    <div class="footer">
                        Конфиденциально
                    </div>
                </div>
            </body>
            </html>
            """

            exp_col1, exp_col2 = st.columns(2)
            with exp_col1:
                st.download_button(
                    label="📥 Скачать отчет ПДЗ (HTML)",
                    data=html_pdz_report,
                    file_name=f"pdz_report_{datetime.datetime.now().strftime('%Y%m%d')}.html",
                    mime="text/html",
                    use_container_width=True,
                    key="dl_pdz_html"
                )

            with exp_col2:
                target_email_pdz = st.text_input("Email для отправки отчета:", value=st.secrets.get("ALERT_EMAIL", ""), key="email_pdz")
                if st.button("📧 Отправить отчет по Email", use_container_width=True, key="send_pdz_email"):
                    if send_report_via_email and target_email_pdz:
                        ok, msg = send_report_via_email(
                            html_content=html_pdz_report,
                            recipient_email=target_email_pdz,
                            subject="📈 Сводный отчет по дебиторской задолженности",
                            as_attachment=True
                        )
                        if ok:
                            st.success("✅ Отчет по ПДЗ успешно отправлен!")
                        else:
                            st.error(f"❌ Ошибка отправки: {msg}")
                    else:
                        st.warning("Введите корректный E-mail или проверьте модуль отправки.")
    else:
        st.error(f"❌ {fetch_message}")
