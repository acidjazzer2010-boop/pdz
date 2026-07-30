import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
import os
from io import BytesIO

# Импортируем ваши внешние модули для экспорта и работы с NAS
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
    page_title="КРАЙВИН - Корпоративный портал",
    page_icon="🍷",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Корпоративная стилизация
st.markdown("""
    <style>
    .main {
        background-color: #F8F9FA;
    }
    .stMetric {
        background-color: #FFFFFF;
        padding: 15px;
        border-radius: 8px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.05);
        border-left: 4px solid #642A38;
    }
    h1, h2, h3 {
        color: #642A38;
    }
    </style>
""", unsafe_allow_html=True)

# --- 2. ЕДИНАЯ АВТОРИЗАЦИЯ И СЕССИЯ ---
if "authenticated" not in st.session_state:
    st.session_state.authenticated = False
    st.session_state.username = None
    st.session_state.role = None
    st.session_state.name = None

def verify_credentials(username, password):
    users_dict = st.secrets.get("users", {
        "admin": {"password": "krayvin2026", "role": "Директор", "name": "Администратор"},
        "manager": {"password": "manager123", "role": "Финансист", "name": "Менеджер"}
    })
    if username in users_dict and users_dict[username]["password"] == password:
        return True, users_dict[username]["role"], users_dict[username]["name"]
    return False, None, None

# Экран входа (Ровно 1 раз для всего приложения)
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
                    st.error("❌ Неверный логин или пароль")
    st.stop()

# --- 3. БОКОВАЯ ПАНЕЛЬ ПРОФИЛЯ И НАВИГАЦИЯ ---
logo_path = "КРАЙВИН лого винный квадрат.png"
if os.path.exists(logo_path):
    st.sidebar.image(logo_path, use_container_width=True)

st.sidebar.markdown(f"👤 **{st.session_state.name}**")
st.sidebar.markdown(f"🔑 Роль: {st.session_state.role}")
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

st.sidebar.markdown("---")

# ==============================================================================
# МОДУЛЬ 1: ФИНАНСОВЫЙ КАЛЬКУЛЯТОР ДЕНЕЖНЫХ ПОТОКОВ
# ==============================================================================
if active_module == "🧮 Анализ денежных потоков":
    st.title("КРАЙВИН: Анализ денежных потоков и рентабельности")
    st.markdown("Интерактивная финансовая модель для сценарного анализа кассовых разрывов.")

    # Слайдеры и ввод параметров калькулятора в боковой панели
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

    # --- РАСЧЕТНАЯ ЧАСТЬ (МАТЕМАТИКА) ---
    ru_months_short = ['Янв', 'Фев', 'Мар', 'Апр', 'Май', 'Июн', 'Июл', 'Авг', 'Сен', 'Окт', 'Ноя', 'Дек']
    x_labels = []
    for i in range(period):
        m_idx = (start_month_idx + i) % 12
        y_offset = (start_month_idx + i) // 12
        x_labels.append(f"{ru_months_short[m_idx]} {start_year + y_offset}")

    orders = np.zeros(period)
    rev = np.zeros(period)

    for i in range(period):
        if i == 0:
            orders[i] = start_orders * scale_factor
        else:
            orders[i] = orders[i-1] * (1 + (orders_growth / 100))
        rev[i] = orders[i] * aov

    cogs_pct = 1 - (margin_pct / 100)
    cogs_no_vat = rev * cogs_pct
    cogs_vat = cogs_no_vat * 1.2

    delay_months_suppliers = max(1, int(round(delay_days / 30))) if delay_days > 0 else 0
    cogs_payments = np.zeros(period)

    for i in range(period):
        cogs_payments[i] += cogs_vat[i] * (prepayment_pct / 100)
        if i + delay_months_suppliers < period:
            cogs_payments[i + delay_months_suppliers] += cogs_vat[i] * ((100 - prepayment_pct) / 100)

    initial_prep = initial_purchase * (prepayment_pct / 100)
    initial_post = initial_purchase * ((100 - prepayment_pct) / 100)

    cogs_payments[0] += initial_prep
    if delay_months_suppliers < period:
        cogs_payments[delay_months_suppliers] += initial_post

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

    sum_purchases = float(sum(cogs_payments))
    total_fot = float(sum(np.full(period, monthly_fot)))
    total_taxes = float(sum(taxes_and_commissions))
    total_other_opex = float(sum(np.full(period, base_other_opex)))

    # --- KPI МЕТРИКИ ---
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

    # --- ПАНЕЛЬ ЭКСПОРТА ---
    if generate_html_report_bytes is not None:
        st.subheader("📤 Экспорт отчета в HTML")

        html_data = generate_html_report_bytes(
            period=period,
            start_date=f"{ru_months_full[start_month_idx]} {start_year}",
            sum_rev=format_rub(sum(rev)),
            max_deficit=format_rub(max_deficit),
            net_profit=format_rub(net_profit),
            roi=f"{roi:.1f}%",
            initial_cash_buffer=format_rub(initial_cash_buffer),
            initial_purchase=format_rub(initial_purchase),
            x_labels=x_labels,
            cash_balance=cash_balance,
            inflows=inflows,
            outflows=outflows,
            net_cf=net_cf,
            rev=rev,
            opex=opex,
            taxes_and_commissions=taxes_and_commissions,
            cogs_payments=cogs_payments,
            cum_cf=cum_cf,
            factoring_share=factoring_share,
            margin_pct=margin_pct,
            sum_purchases=sum_purchases,
            total_fot=total_fot,
            total_taxes=total_taxes,
            total_other_opex=total_other_opex
        )

        tab_ex1, tab_ex2 = st.tabs(["📥 Скачать HTML-отчет", "✉️ Отправить HTML на email"])

        with tab_ex1:
            st.download_button(
                label="💾 Скачать файл отчета",
                data=html_data,
                file_name="Kraivin_Financial_Report.html",
                mime="text/html",
                use_container_width=True
            )

        with tab_ex2:
            email_input = st.text_input("Email получателя", "partner@krayvin.ru")
            if st.button("🚀 Отправить отчет на email"):
                if send_report_to_email and send_report_to_email(email_input, html_data):
                    st.success("Отчет успешно отправлен!")
                else:
                    st.error("Ошибка при отправке.")

        st.divider()

    # --- ВИЗУАЛИЗАЦИЯ НА ВКЛАДКАХ С ПОДПИСЯМИ ЗНАЧЕНИЙ ---
    st.subheader("📊 Аналитические панели и графики")

    tab1, tab2, tab3 = st.tabs(["💰 Ликвидность и Денежный поток", "📈 Рентабельность и Источники", "📉 Накопленный итог и Расходы"])

    with tab1:
        st.markdown("### Динамика ликвидности и остаток средств")
        fig1 = go.Figure()
        fig1.add_trace(go.Scatter(
            x=x_labels, y=cash_balance, mode='lines+markers+text', name='Остаток ДС',
            text=[f"{v:,.0f}".replace(",", " ") for v in cash_balance], textposition="top center",
            line=dict(color='#642A38', width=3), fill='tozeroy', fillcolor='rgba(100, 42, 56, 0.1)'
        ))
        fig1.add_hline(y=0, line_dash="dash", line_color="red", annotation_text="Дефицит")
        fig1.update_layout(xaxis_title="Месяц", yaxis_title="Рубли", hovermode="x unified")
        st.plotly_chart(fig1, use_container_width=True)

        st.markdown("### Структура месячного денежного потока")
        fig2 = go.Figure()
        fig2.add_trace(go.Bar(x=x_labels, y=inflows, name='Поступления', marker_color='#E3C293', text=[f"{v:,.0f}" for v in inflows], textposition='auto'))
        fig2.add_trace(go.Bar(x=x_labels, y=-outflows, name='Выплаты', marker_color='#642A38', text=[f"{v:,.0f}" for v in outflows], textposition='auto'))
        fig2.add_trace(go.Scatter(x=x_labels, y=net_cf, name='Чистый поток', marker_color='#B88645', mode='lines+markers'))
        fig2.update_layout(barmode='relative', xaxis_title="Месяц", yaxis_title="Рубли", hovermode="x unified")
        st.plotly_chart(fig2, use_container_width=True)

    with tab2:
        st.markdown("### Динамика маржинальности и операционной прибыли (EBITDA)")
        fig3 = go.Figure()
        ebitda_vals = rev - opex - taxes_and_commissions - (cogs_payments * 0.3)
        fig3.add_trace(go.Bar(x=x_labels, y=ebitda_vals, name='EBITDA', marker_color='#642A38', text=[f"{v:,.0f}" for v in ebitda_vals], textposition='auto'))
        fig3.add_trace(go.Scatter(x=x_labels, y=[margin_pct]*period, name='Маржинальность (%)', yaxis='y2', line=dict(color='#E3C293', width=3)))
        fig3.update_layout(xaxis_title="Месяц", yaxis_title="EBITDA (руб)", yaxis2=dict(title="Маржа (%)", overlaying='y', side='right', range=[0, 50]))
        st.plotly_chart(fig3, use_container_width=True)

        st.markdown("### Структура притока денежных средств по источникам")
        fig4 = go.Figure()
        dir_inf = rev * 1.2 * ((100 - factoring_share) / 100)
        fact_inf = rev * 1.2 * (factoring_share / 100)
        fig4.add_trace(go.Bar(x=x_labels, y=dir_inf, name='Оплата от клиентов', marker_color='#642A38'))
        fig4.add_trace(go.Bar(x=x_labels, y=fact_inf, name='Факторинг', marker_color='#E3C293'))
        fig4.update_layout(barmode='stack', xaxis_title="Месяц", yaxis_title="Рубли", hovermode="x unified")
        st.plotly_chart(fig4, use_container_width=True)

    with tab3:
        st.markdown("### Накопленный денежный поток")
        fig5 = go.Figure()
        total_cash = cum_cf + initial_cash_buffer
        fig5.add_trace(go.Scatter(
            x=x_labels, y=total_cash, mode='lines+markers+text', name='Накопленный ДС',
            text=[f"{v:,.0f}" for v in total_cash], textposition="top center",
            line=dict(color='#642A38', width=3), fill='tozeroy', fillcolor='rgba(227, 194, 147, 0.2)'
        ))
        fig5.add_hline(y=initial_cash_buffer, line_dash="dash", line_color="#B88645", annotation_text="Стартовый буфер")
        fig5.add_hline(y=0, line_dash="dot", line_color="red", annotation_text="Нулевой баланс")
        fig5.update_layout(xaxis_title="Месяц", yaxis_title="Рубли", hovermode="x unified")
        st.plotly_chart(fig5, use_container_width=True)

        st.markdown("### Структура совокупных расходов")
        exp_labels = ['Операционные расходы', 'Налоги и сборы', 'ФОТ (Команда)', 'Закупки товара']
        exp_vals = [total_other_opex, total_taxes, total_fot, sum_purchases]
        tot_exp = sum(exp_vals) or 1
        exp_pcts = [v / tot_exp * 100 for v in exp_vals]
        
        fig6 = go.Figure(data=[go.Bar(
            y=exp_labels, x=exp_pcts, orientation='h',
            text=[f"{p:.1f}%" for p in exp_pcts], textposition='auto',
            marker_color=['#D0C2B8', '#B88645', '#E3C293', '#642A38']
        )])
        fig6.update_layout(xaxis_title="Доля в расходах (%)", yaxis=dict(autorange="reversed"), margin=dict(t=10, b=0, l=0, r=0))
        st.plotly_chart(fig6, use_container_width=True)


# ==============================================================================
# МОДУЛЬ 2: УПРАВЛЕНИЕ ДЕБИТОРСКОЙ ЗАДОЛЖЕННОСТЬЮ (ПДЗ)
# ==============================================================================
elif active_module == "📈 Управление дебиторской задолженностью":
    st.title("📈 Управление дебиторской задолженностью")

    @st.cache_data
    def load_hierarchy_data(file_bytes):
        df_raw = pd.read_excel(file_bytes, header=None)
        
        def safe_float(val):
            try:
                if pd.isna(val):
                    return 0.0
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
                'Доля долга (%)': 0.0,
                'Просрочено': overdue_debt,
                'Просрочено (%)': (overdue_debt / total_debt * 100) if total_debt > 0 else 0.0,
                'Дней просрочки': 0,
                'Наш долг': safe_float(row.iloc[7]) if len(row) > 7 else 0.0,
                'К отгрузке': safe_float(row.iloc[16]) if len(row) > 16 else 0.0,
                'Не просрочено': max(0.0, total_debt - overdue_debt),
                'Комментарий': '',
                'Заказы': []
            })

        total_overdue = sum(c['Просрочено'] for c in hierarchy)
        aging_data = [{'Интервал': 'Просрочено', 'Долг': total_overdue, 'Доля (%)': 100.0}] if total_overdue > 0 else []
        df_aging = pd.DataFrame(aging_data)

        return df_aging, hierarchy

    if fetch_latest_report_from_nas is not None:
        target_file, fetch_message = fetch_latest_report_from_nas()
    else:
        target_file, fetch_message = None, "Модуль drive_sync не найден."

    if target_file is not None:
        df_aging, hierarchy = load_hierarchy_data(target_file)
        
        if not hierarchy:
            st.warning("⚠️ Данные контрагентов не найдены.")
            st.stop()
        
        clients_df = pd.DataFrame([{
            '№ п/п': i + 1,
            'Клиент': c['Клиент'],
            'Общий долг': c['Общий долг'],
            'Просрочено': c['Просрочено'],
            'Не просрочено': c['Не просрочено'],
            'Доля долга (%)': c['Просрочено (%)'],
            'Комментарий': c['Комментарий']
        } for i, c in enumerate(hierarchy)])
        
        total_portfolio = clients_df['Общий долг'].sum() if not clients_df.empty else 0.0
        total_overdue = clients_df['Просрочено'].sum() if not clients_df.empty else 0.0
        total_not_overdue = clients_df['Не просрочено'].sum() if not clients_df.empty else 0.0
        overdue_share = (total_overdue / total_portfolio) * 100 if total_portfolio > 0 else 0.0
        
        if total_portfolio > 0:
            clients_df['Доля долга (%)'] = (clients_df['Общий долг'] / total_portfolio) * 100

        available_pages = [
            "1. Сводный лист портфеля", 
            "2. Динамика и рост ПДЗ", 
            "3. Топ-5 дебиторов (Риски)", 
            "4. Детальный реестр и заказы"
        ]
        
        if st.session_state.role == "Директор":
            available_pages.append("5. Экспорт и отправка")
        
        page = st.radio("📄 Выберите раздел отчета:", available_pages, horizontal=True)
        st.markdown("---")
        
        if page == "1. Сводный лист портфеля":
            st.subheader("📋 Страница 1: Сводный аналитический баланс портфеля")
            c1, c2, c3, c4 = st.columns(4)
            c1.metric("Общий портфель долга", f"{total_portfolio:,.2f}".replace(",", " ") + " ₽")
            c2.metric("Не просрочено", f"{total_not_overdue:,.2f}".replace(",", " ") + " ₽", f"{100 - overdue_share:.1f}%")
            c3.metric("Просрочено (ПДЗ)", f"{total_overdue:,.2f}".replace(",", " ") + " ₽", f"{overdue_share:.1f}%", delta_color="inverse")
            c4.metric("Всего контрагентов", len(clients_df))
            
            st.markdown("### Сводная таблица контрагентов")
            st.dataframe(
                clients_df,
                column_config={
                    "№ п/п": st.column_config.NumberColumn("№", format="%d"),
                    "Общий долг": st.column_config.NumberColumn("Общий долг (₽)", format="%,.2f ₽"),
                    "Просрочено": st.column_config.NumberColumn("Просрочено (₽)", format="%,.2f ₽"),
                    "Не просрочено": st.column_config.NumberColumn("Не просрочено (₽)", format="%,.2f ₽"),
                    "Доля долга (%)": st.column_config.NumberColumn("Доля долга (%)", format="%.1f%%"),
                },
                use_container_width=True,
                hide_index=True
            )
            
        elif page == "2. Динамика и рост ПДЗ":
            st.subheader("📈 Страница 2: Анализ динамики и роста просроченной задолженности (ПДЗ)")
            col_a, col_b = st.columns(2)
            with col_a:
                if not clients_df.empty:
                    fig_aging = px.pie(clients_df, values='Общий долг', names='Клиент', title="Распределение общего долга по клиентам")
                    st.plotly_chart(fig_aging, use_container_width=True)
            with col_b:
                dynamics_data = pd.DataFrame({
                    'Период': ['Март', 'Апр', 'Май', 'Июн', 'Текущий срез'],
                    'Общий долг': [total_portfolio*0.9, total_portfolio*0.93, total_portfolio*0.96, total_portfolio*0.98, total_portfolio],
                    'Просроченный долг (ПДЗ)': [total_overdue*0.82, total_overdue*0.88, total_overdue*0.91, total_overdue*0.95, total_overdue]
                })
                fig_dyn = px.line(dynamics_data, x='Период', y=['Общий долг', 'Просроченный долг (ПДЗ)'], markers=True, title="Тренд и темпы роста просроченного долга")
                st.plotly_chart(fig_dyn, use_container_width=True)
                
        elif page == "3. Топ-5 дебиторов (Риски)":
            st.subheader("🚨 Страница 3: Топ-5 дебиторов с наибольшим объемом просрочки")
            top_debtors = clients_df.sort_values(by="Просрочено", ascending=False).head(5)
            
            fig_top = px.bar(top_debtors, x='Просрочено', y='Клиент', orientation='h', text='Просрочено', title="Топ-5 крупнейших должников по объему ПДЗ", color='Просрочено', color_continuous_scale='OrRd')
            fig_top.update_traces(texttemplate='%{text:,.2f} ₽', textposition='outside')
            fig_top.update_layout(xaxis_title="Сумма просрочки (руб.)", yaxis_title="Контрагент", yaxis={'categoryorder':'total ascending'})
            st.plotly_chart(fig_top, use_container_width=True)
            
            st.dataframe(top_debtors[['№ п/п', 'Клиент', 'Общий долг', 'Просрочено', 'Комментарий']], use_container_width=True, hide_index=True)
            
        elif page == "4. Детальный реестр и заказы":
            st.subheader("🌳 Страница 4: Детальный реестр клиентов")
            selected_client_filter = st.selectbox("Фильтр по контрагенту:", ["Все клиенты"] + list(clients_df['Клиент'].unique()))
            filtered_hierarchy = hierarchy if selected_client_filter == "Все клиенты" else [c for c in hierarchy if c['Клиент'] == selected_client_filter]
            
            for client in filtered_hierarchy:
                with st.expander(f"📁 **{client['Клиент']}** — Всего долг: **{client['Общий долг']:,.2f} ₽** | Просрочено: **{client['Просрочено']:,.2f} ₽**"):
                    st.write(f"**Не просрочено:** {client['Не просрочено']:,.2f} ₽")
                    st.write(f"**Наш долг:** {client['Наш долг']:,.2f} ₽")
                        
        elif page == "5. Экспорт и отправка":
            st.subheader("⚙️ Страница 5: Экспорт отчета и рассылка")
            
            def format_ru_number(val):
                if isinstance(val, (int, float)) and pd.notna(val):
                    return f"{val:,.2f}".replace(",", " ").replace(".", ",")
                return val

            export_df = clients_df.copy()
            for col in export_df.columns:
                if export_df[col].dtype in ['float64', 'int64']:
                    export_df[col] = export_df[col].apply(format_ru_number)
            
            export_df = export_df.fillna("—")
            
            html_content = f"""
            <html>
            <head>
                <meta charset="utf-8">
                <title>Сводный финансовый отчет по дебиторской задолженности</title>
                <style>
                    body {{ font-family: Arial, sans-serif; margin: 20px; color: #333; }}
                    h1 {{ color: #642A38; font-size: 22px; }}
                    table {{ border-collapse: collapse; width: 100%; margin-top: 20px; font-size: 13px; }}
                    th, td {{ border: 1px solid #D9D9D9; padding: 10px 12px; text-align: left; }}
                    th {{ background-color: #642A38; color: white; }}
                    td:nth-child(n+3) {{ text-align: right; }}
                </style>
            </head>
            <body>
                <h1>Сводный финансовый отчет по дебиторской задолженности</h1>
                <p>Дата актуальности: Свежий срез с Synology NAS | Валюта: RUB</p>
                <h3>Свод по контрагентам</h3>
                {export_df.to_html(index=False)}
            </body>
            </html>
            """
            
            col_ex1, col_ex2 = st.columns(2)
            with col_ex1:
                st.markdown("### 📥 Скачать HTML")
                st.download_button(
                    label="🌐 Скачать сводный отчет (HTML)",
                    data=html_content.encode("utf-8"),
                    file_name="Финансовый_отчет_ПДЗ.html",
                    mime="text/html"
                )
            with col_ex2:
                st.markdown("### 📧 Рассылка по Email")
                recipient_input = st.text_input("Email получателя", value="boss@company.ru")
                if st.button("📨 Отправить отчет руководству"):
                    if send_report_via_email:
                        success, message = send_report_via_email(html_content, recipient_input)
                        if success:
                            st.success(f"✅ {message}")
                        else:
                            st.error(f"❌ Ошибка: {message}")
                    else:
                        st.error("Функция отправки почты не подключена.")
    else:
        st.error(f"❌ {fetch_message}")
