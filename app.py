import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
import os
import datetime
from io import BytesIO

# Импорт ваших модулей
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
    page_title="Личный кабинет",
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

# --- 2. ВСПАМОГАТЕЛЬНЫЕ ФУНКЦИИ БЕЗОПАСНОСТИ И ЛОГИРОВАНИЯ ---

def get_client_ip():
    """Получает публичный IP-адрес клиента из заголовков Streamlit."""
    try:
        headers = st.context.headers
        if "X-Forwarded-For" in headers:
            return headers["X-Forwarded-For"].split(",")[0].strip()
        elif "Remote-Addr" in headers:
            return headers["Remote-Addr"]
    except Exception:
        pass
    return "127.0.0.1 (Local/Unknown)"

def log_access_event(username, status, role="—"):
    """Записывает событие входа в локальный файл access_log.csv."""
    log_file = "access_log.csv"
    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    ip_address = get_client_ip()
    
    new_entry = pd.DataFrame([{
        "Timestamp": now,
        "Username": username,
        "Status": status,
        "IP_Address": ip_address,
        "Role": role
    }])
    
    if os.path.exists(log_file):
        new_entry.to_csv(log_file, mode='a', header=False, index=False, encoding='utf-8-sig')
    else:
        new_entry.to_csv(log_file, mode='w', header=True, index=False, encoding='utf-8-sig')

def send_security_alert(attempted_username, ip_address):
    """Отправляет уведомление о неудачной попытке входа."""
    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    alert_html = f"""
    <h3>⚠️ Внимание: Неудачная попытка входа в систему KRAYVIN!</h3>
    <p><b>Дата и время:</b> {now}</p>
    <p><b>Попытка входа под логином:</b> {attempted_username}</p>
    <p><b>IP-адрес источника:</b> {ip_address}</p>
    <hr>
    <p><i>Если это были не вы, рекомендуем проверить настройки безопасности.</i></p>
    """
    
    # 1. Отправка на Email (если подключен модуль exporter)
    admin_email = st.secrets.get("security", {}).get("alert_email", "security@krayvin.ru")
    if send_report_via_email:
        send_report_via_email(alert_html, admin_email)

# --- 3. ЕДИНАЯ АВТОРИЗАЦИЯ И СЕССИЯ ---
if "authenticated" not in st.session_state:
    st.session_state.authenticated = False
    st.session_state.username = None
    st.session_state.role = None
    st.session_state.name = None

def verify_credentials(username, password):
    users_dict = st.secrets.get("users", {
        "admin": {"password": "password", "role": "Директор", "name": "Администратор"},
        "manager": {"password": "password", "role": "Финансист", "name": "Менеджер"}
    })
    
    ip_addr = get_client_ip()
    
    if username in users_dict and users_dict[username]["password"] == password:
        role = users_dict[username]["role"]
        name = users_dict[username]["name"]
        log_access_event(username, "SUCCESS", role)
        return True, role, name
    else:
        log_access_event(username, "FAILED_LOGIN", "—")
        send_security_alert(username, ip_addr)
        return False, None, None

# Экран входа
if not st.session_state.authenticated:
    st.markdown("<h2 style='text-align: center; color: #642A38;'>🔐 Корпоративный портал KRAYVIN</h2>", unsafe_allow_html=True)
    col1, col2, col3 = st.columns([1, 1.2, 1])
    with col2:
        with st.form("login_form"):
            username_input = st.text_input("Логин")
            password_input = st.text_input("Пароль", type="password")
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
                    st.error("❌ Неверный логин или пароль. Информация об инциденте записана.")
    st.stop()

# --- 4. БОКОВАЯ ПАНЕЛЬ И НАВИГАЦИЯ ---
logo_path = "КРАЙВИН лого винный квадрат.png"
if os.path.exists(logo_path):
    st.sidebar.image(logo_path, use_container_width=True)

st.sidebar.markdown(f"👤 **{st.session_state.name}**")
st.sidebar.markdown(f"🔑 Роль: {st.session_state.role}")
st.sidebar.caption(f"🌐 IP: `{get_client_ip()}`")

if st.sidebar.button("🚪 Выйти из системы"):
    st.session_state.authenticated = False
    st.session_state.username = None
    st.session_state.role = None
    st.session_state.name = None
    st.rerun()

st.sidebar.markdown("---")

# Переключатель сервисов
active_module = st.sidebar.radio(
    "📌 Выберите сервис:",
    ["🧮 Анализ денежных потоков", "📈 Управление дебиторской задолженностью"]
)

# Просмотр журнала посещений (Только для роли "Директор")
if st.session_state.role == "Директор":
    st.sidebar.markdown("---")
    if st.sidebar.checkbox("📜 Журнал посещений (Log)"):
        active_module = "📜 Журнал посещений"

st.sidebar.markdown("---")


# ==============================================================================
# МОДУЛЬ: ЖУРНАЛ ПОСЕЩЕНИЙ (ТОЛЬКО ДЛЯ АДМИНИСТРАТОРА)
# ==============================================================================
if active_module == "📜 Журнал посещений":
    st.title("📜 Журнал безопасности и посещений системы")
    st.markdown("Мониторинг подключений, IP-адресов и попыток несанкционированного доступа.")

    if os.path.exists("access_log.csv"):
        log_df = pd.read_csv("access_log.csv")
        
        c1, c2, c3 = st.columns(3)
        c1.metric("Всего подключений", len(log_df))
        c2.metric("Успешных входов", len(log_df[log_df["Status"] == "SUCCESS"]))
        c3.metric("Подозрительных попыток", len(log_df[log_df["Status"] == "FAILED_LOGIN"]), delta_color="inverse")

        st.subheader("Таблица активности")
        st.dataframe(
            log_df.sort_values(by="Timestamp", ascending=False),
            column_config={
                "Timestamp": "Время",
                "Username": "Логин",
                "Status": "Статус",
                "IP_Address": "IP-Адрес",
                "Role": "Роль"
            },
            use_container_width=True,
            hide_index=True
        )

        csv_bytes = log_df.to_csv(index=False, encoding='utf-8-sig').encode('utf-8-sig')
        st.download_button("📥 Скачать журнал (CSV)", data=csv_bytes, file_name="access_log.csv", mime="text/csv")
    else:
        st.info("Журнал посещений пока пуст.")


# ==============================================================================
# МОДУЛЬ 1: ФИНАНСОВЫЙ КАЛЬКУЛЯТОР ДЕНЕЖНЫХ ПОТОКОВ
# ==============================================================================
elif active_module == "🧮 Анализ денежных потоков":
    st.title("КРАЙВИН: Анализ денежных потоков и рентабельности")
    st.markdown("Интерактивная финансовая модель для сценарного анализа кассовых разрывов.")

    st.sidebar.header("Параметры финансовой модели")
    ru_months_full = ['Январь', 'Февраль', 'Март', 'Апрель', 'Май', 'Июнь', 'Июль', 'Август', 'Сентябрь', 'Октябрь', 'Ноябрь', 'Декабрь']
    col_m, col_y = st.sidebar.columns(2)
    start_month_idx = col_m.selectbox("Месяц старта", range(12), format_func=lambda x: ru_months_full[x])
    start_year = col_y.selectbox("Год старта", [2026, 2027])

    margin_pct = st.sidebar.slider("Маржинальность (%)", min_value=10, max_value=50, value=20, step=1)
    period = st.sidebar.selectbox("Горизонт планирования (мес)", [6, 12, 18, 24])

    st.sidebar.subheader("Стартовый капитал и закупки")
    initial_purchase = st.sidebar.number_input("Первоначальная закупка товара (руб)", value=5_000_000, step=500_000)
    initial_cash_buffer = st.sidebar.number_input("Стартовый денежный буфер (на счете)", value=2_000_000, step=500_000)

    st.sidebar.subheader("Динамика продаж")
    aov = st.sidebar.number_input("Средняя сумма заказа (руб)", value=150_000, step=10_000)
    start_orders = st.sidebar.number_input("Заказов в 1-й месяц (шт)", value=40, step=1)
    orders_growth = st.sidebar.slider("Ежемесячный прирост заказов (%)", 0, 100, 15, step=1)
    scale_factor = st.sidebar.slider("Коэффициент масштабирования продаж", 0.5, 3.0, 1.0, 0.1)

    st.sidebar.subheader("Команда и расходы")
    monthly_fot = st.sidebar.number_input("ФОТ в месяц (руб)", value=500_000, step=50_000)

    st.sidebar.subheader("Работа с поставщиками")
    prepayment_pct = st.sidebar.slider("Предоплата поставщикам (%)", 0, 100, 50, step=10)
    delay_days = st.sidebar.slider("Отсрочка на остаток (дней)", 0, 90, 40, step=5)

    st.sidebar.subheader("Факторинг")
    factoring_share = st.sidebar.slider("Доля выручки в факторинге (%)", 0, 100, 50, step=10)
    factoring_advance = st.sidebar.slider("Аванс от фактора (%)", 50, 100, 80, step=5)

    st.sidebar.subheader("Условия с покупателями")
    customer_delay_days = st.sidebar.slider("Отсрочка платежа покупателям (дней)", 0, 120, 70, step=5)

    # Математические расчеты
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
        st.plotly_chart(fig1, use_container_width=True)

    with tab2:
        st.markdown("### Динамика маржинальности и EBITDA")
        fig3 = go.Figure()
        ebitda_vals = rev - opex - taxes_and_commissions
        fig3.add_trace(go.Bar(x=x_labels, y=ebitda_vals, name='EBITDA', marker_color='#642A38'))
        st.plotly_chart(fig3, use_container_width=True)

    with tab3:
        st.markdown("### Накопленный денежный поток")
        fig5 = go.Figure()
        fig5.add_trace(go.Scatter(x=x_labels, y=cum_cf + initial_cash_buffer, mode='lines+markers', name='Накопленный ДС', line=dict(color='#642A38', width=3)))
        st.plotly_chart(fig5, use_container_width=True)


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
    else:
        st.error(f"❌ {fetch_message}")
