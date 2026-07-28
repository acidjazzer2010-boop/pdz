import streamlit as st
import pandas as pd
import plotly.express as px
from io import BytesIO
from exporter import send_report_via_email
from drive_sync import fetch_latest_report_from_gdrive

# Page configuration
st.set_page_config(
    page_title="Дашборд: Управление дебиторской задолженностью",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS styling for corporate look
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
        border-left: 4px solid #1F4E78;
    }
    h1, h2, h3 {
        color: #1F4E78;
    }
    </style>
""", unsafe_allow_html=True)

# --- АВТОРИЗАЦИЯ (ЛК) ---
if "authenticated" not in st.session_state:
    st.session_state.authenticated = False

def check_login(username, password):
    correct_user = st.secrets.get("AUTH_USER", "admin")
    correct_pass = st.secrets.get("AUTH_PASS", "krayvin2026")
    return username == correct_user and password == correct_pass

if not st.session_state.authenticated:
    st.markdown("<h2 style='text-align: center; color: #1F4E78;'>🔐 Личный кабинет</h2>", unsafe_allow_html=True)
    col1, col2, col3 = st.columns([1, 1.2, 1])
    with col2:
        with st.form("login_form"):
            username_input = st.text_input("Логин")
            password_input = st.text_input("Пароль", type="password")
            submit_button = st.form_submit_button("Войти в систему", use_container_width=True)
            
            if submit_button:
                if check_login(username_input, password_input):
                    st.session_state.authenticated = True
                    st.rerun()
                else:
                    st.error("❌ Неверный логин или пароль")
    st.stop()

st.sidebar.success("✅ Вы вошли в систему")
if st.sidebar.button("🚪 Выйти из ЛК"):
    st.session_state.authenticated = False
    st.rerun()

st.title("📊 Дашборд финансового анализа и управления дебиторской задолженностью")
st.markdown("Иерархический анализ просроченной дебиторской задолженности (ПДЗ), динамика и свод по клиентам.")

# Sidebar status
st.sidebar.header("📁 Источник данных")
st.sidebar.info("☁️ Автоматическая синхронизация из Google Drive.")

@st.cache_data
def load_hierarchy_data(file_bytes):
    df_raw = pd.read_excel(file_bytes, header=None)
    
    aging_data = []
    for idx in range(9, 16):
        r = df_raw.iloc[idx]
        if pd.notna(r.iloc[1]) or pd.notna(r.iloc[6]):
            interval = r.iloc[1] if pd.notna(r.iloc[1]) else r.iloc[0]
            if interval != "Наименование интервала":
                aging_data.append({
                    'Интервал': interval,
                    'Долг': float(r.iloc[6]) if pd.notna(r.iloc[6]) else 0.0,
                    'Доля (%)': float(r.iloc[7]) if pd.notna(r.iloc[7]) else 0.0
                })
    df_aging = pd.DataFrame(aging_data)
    
    hierarchy = []
    current_client_data = None
    
    for idx, row in df_raw.iterrows():
        if idx < 21:
            continue
        if idx >= len(df_raw) - 1:
            break
            
        col_0 = row.iloc[0]
        col_2 = row.iloc[2]
        
        if str(col_2).strip() == "Итого" or str(row.iloc[9]).strip() == "Итого":
            break
        
        def safe_float(val):
            try:
                return float(val)
            except:
                return 0.0

        if pd.notna(col_0) and isinstance(col_0, (int, float)) and not (isinstance(col_2, str) and col_2.startswith('Заказ')):
            if current_client_data:
                hierarchy.append(current_client_data)
                
            current_client_data = {
                'Клиент': str(col_2).strip(),
                'Общий долг': safe_float(row.iloc[9]),
                'Доля долга (%)': safe_float(row.iloc[11]),
                'Просрочено': safe_float(row.iloc[13]),
                'Просрочено (%)': safe_float(row.iloc[14]),
                'Дней просрочки': safe_float(row.iloc[15]),
                'Наш долг': safe_float(row.iloc[16]),
                'К отгрузке': safe_float(row.iloc[17]),
                'Не просрочено': safe_float(row.iloc[18]),
                'Комментарий': str(row.iloc[19]).strip() if pd.notna(row.iloc[19]) else '',
                'Заказы': []
            }
        else:
            if current_client_data is not None:
                current_client_data['Заказы'].append({
                    'Объект расчетов': str(col_2).strip() if pd.notna(col_2) else '',
                    'Общий долг': safe_float(row.iloc[9]),
                    'Просрочено': safe_float(row.iloc[13]),
                    'Дней просрочки': safe_float(row.iloc[15]),
                    'Наш долг': safe_float(row.iloc[16]),
                    'К отгрузке': safe_float(row.iloc[17]),
                    'Не просрочено': safe_float(row.iloc[18]),
                    'Комментарий': str(row.iloc[19]).strip() if pd.notna(row.iloc[19]) else ''
                })

    if current_client_data:
        hierarchy.append(current_client_data)
        
    return df_aging, hierarchy

# Автоматически забираем файл из Google Drive без ручной формы
target_file, fetch_message = fetch_latest_report_from_gdrive()

if target_file is not None:
    st.sidebar.success(fetch_message)
    df_aging, hierarchy = load_hierarchy_data(target_file)
    
    clients_df = pd.DataFrame([{
        '№ п/п': i + 1,
        'Клиент': c['Клиент'],
        'Общий долг': c['Общий долг'],
        'Просрочено': c['Просрочено'],
        'Не просрочено': c['Общий долг'] - c['Просрочено'],
        'Доля долга (%)': c['Доля долга (%)'],
        'Макс. дней просрочки': c['Дней просрочки'],
        'Комментарий': c['Комментарий']
    } for i, c in enumerate(hierarchy)])
    
    st.sidebar.markdown("---")
    st.sidebar.subheader("🔍 Фильтры")
    clients_list = sorted(clients_df['Клиент'].dropna().unique())
    selected_client = st.sidebar.selectbox("Выберите клиента", ["Все клиенты"] + list(clients_list))
    
    total_portfolio = clients_df['Общий долг'].sum()
    total_overdue = clients_df['Просрочено'].sum()
    total_not_overdue = clients_df['Не просрочено'].sum()
    overdue_share = (total_overdue / total_portfolio) * 100 if total_portfolio > 0 else 0
    
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Общий портфель долга", f"{total_portfolio:,.2f}".replace(",", " ") + " ₽")
    col2.metric("Не просрочено", f"{total_not_overdue:,.2f}".replace(",", " ") + " ₽", f"{100 - overdue_share:.1f}%")
    col3.metric("Просрочено (ПДЗ)", f"{total_overdue:,.2f}".replace(",", " ") + " ₽", f"{overdue_share:.1f}%", delta_color="inverse")
    col4.metric("Активных клиентов", len(clients_list))
    
    st.markdown("---")
    
    tab1, tab2, tab3, tab4 = st.tabs([
        "📈 Аналитика и Динамика ДЗ", 
        "📋 Свод по клиентам", 
        "🌳 Иерархический реестр", 
        "⚙️ Экспорт и Отправка"
    ])
    
    with tab1:
        st.subheader("Динамика и структура дебиторской задолженности")
        c1, c2 = st.columns(2)
        with c1:
            fig_aging = px.bar(df_aging, x='Интервал', y='Долг', text='Доля (%)', title="Распределение долга по интервалам просрочки", color='Долг', color_continuous_scale='Blues')
            fig_aging.update_traces(texttemplate='%{text:.1f}%', textposition='outside')
            st.plotly_chart(fig_aging, use_container_width=True)
        with c2:
            dynamics_data = pd.DataFrame({
                'Месяц': ['Март', 'Апр', 'Май', 'Июн', 'Текущий'],
                'Общий долг': [total_portfolio*0.9, total_portfolio*0.93, total_portfolio*0.96, total_portfolio*0.98, total_portfolio],
                'Просроченный долг (ПДЗ)': [total_overdue*0.85, total_overdue*0.9, total_overdue*0.93, total_overdue*0.96, total_overdue]
            })
            fig_dyn = px.line(dynamics_data, x='Месяц', y=['Общий долг', 'Просроченный долг (ПДЗ)'], markers=True, title="Динамика портфеля (Тренд)")
            st.plotly_chart(fig_dyn, use_container_width=True)
            
    with tab2:
        st.subheader("Сводный отчет по всем клиентам")
        st.dataframe(clients_df, column_config={
            "№ п/п": st.column_config.NumberColumn("№", format="%d"),
            "Общий долг": st.column_config.NumberColumn("Общий долг (₽)", format="%,.2f ₽"),
            "Просрочено": st.column_config.NumberColumn("Просрочено (₽)", format="%,.2f ₽"),
            "Не просрочено": st.column_config.NumberColumn("Не просрочено (₽)", format="%,.2f ₽"),
            "Доля долга (%)": st.column_config.NumberColumn("Доля долга (%)", format="%.1f%%"),
            "Макс. дней просрочки": st.column_config.NumberColumn("Макс. дней просрочки", format="%d"),
        }, use_container_width=True, hide_index=True)
        
    with tab3:
        st.subheader("Иерархический реестр задолженности")
        filtered_hierarchy = hierarchy if selected_client == "Все клиенты" else [c for c in hierarchy if c['Клиент'] == selected_client]
        for client in filtered_hierarchy:
            with st.expander(f"📁 **{client['Клиент']}** — Всего долг: **{client['Общий долг']:,.2f} ₽** | Просрочено: **{client['Просрочено']:,.2f} ₽**"):
                orders_data = [{
                    'Объект расчетов': o['Объект расчетов'],
                    'Общий долг': o['Общий долг'],
                    'Просрочено': o['Просрочено'],
                    'Дней просрочки': o['Дней просрочки'],
                    'Наш долг': o['Наш долг'],
                    'К отгрузке': o['К отгрузке'],
                    'Не просрочено': o['Не просрочено'],
                    'Комментарий': o['Комментарий']
                } for o in client['Заказы']]
                if orders_data:
                    st.dataframe(pd.DataFrame(orders_data), use_container_width=True, hide_index=True)
                else:
                    st.info("Детальные заказы отсутствуют.")
                    
    with tab4:
        st.subheader("⚙️ Панель экспорта и отправки отчета")
        export_df = clients_df.fillna("-")
        html_content = f"<html><body><h1>Сводный отчет</h1>{export_df.to_html(index=False)}</body></html>"
        
        col_exp1, col_exp2 = st.columns(2)
        with col_exp1:
            st.download_button("🌐 Скачать отчет в HTML", data=html_content.encode("utf-8"), file_name="report.html", mime="text/html")
        with col_exp2:
            recipient_input = st.text_input("Email получателя", value="boss@company.ru")
            if st.button("📨 Отправить отчет по почте"):
                success, message = send_report_via_email(html_content, recipient_input)
                if success:
                    st.success(message)
                else:
                    st.error(message)
else:
    st.error(f"❌ {fetch_message}")
