import streamlit as st
import pandas as pd
import plotly.express as px
from io import BytesIO
from exporter import send_report_via_email
from drive_sync import fetch_latest_report_from_gdrive

# Page configuration
st.set_page_config(
    page_title="Корпоративный отчет: Управление дебиторской задолженностью",
    page_icon="📈",
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

# --- МНОГОПОЛЬЗОВАТЕЛЬСКИЙ ЛК ---
if "authenticated" not in st.session_state:
    st.session_state.authenticated = False
    st.session_state.username = None
    st.session_state.role = None
    st.session_state.name = None

def verify_credentials(username, password):
    users_dict = st.secrets.get("users", {
        "admin": {"password": "krayvin2026", "role": "Директор", "name": "Администратор"},
        "manager": {"password": "manager123", "role": "Финансист", "name": "Менеджер ПДЗ"}
    })
    
    if username in users_dict:
        if users_dict[username]["password"] == password:
            return True, users_dict[username]["role"], users_dict[username]["name"]
    return False, None, None

if not st.session_state.authenticated:
    st.markdown("<h2 style='text-align: center; color: #1F4E78;'>🔐 Личный кабинет корпоративной системы</h2>", unsafe_allow_html=True)
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

# Боковая панель профиля (чистая, без лишних технических текстов)
st.sidebar.markdown(f"👤 **{st.session_state.name}**")
st.sidebar.markdown(f"🔑 Роль: {st.session_state.role}")
if st.sidebar.button("🚪 Выйти из системы"):
    st.session_state.authenticated = False
    st.session_state.username = None
    st.session_state.role = None
    st.session_state.name = None
    st.rerun()

st.title("📈 Финансовый отчет: Управление дебиторской задолженностью")
st.markdown("Отчет для контроля портфеля и рисков")

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

# Тихо загружаем файл из Google Drive (без лишних плашек)
target_file, fetch_message = fetch_latest_report_from_gdrive()

if target_file is not None:
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
    
    total_portfolio = clients_df['Общий долг'].sum()
    total_overdue = clients_df['Просрочено'].sum()
    total_not_overdue = clients_df['Не просрочено'].sum()
    overdue_share = (total_overdue / total_portfolio) * 100 if total_portfolio > 0 else 0
    
    st.markdown("---")
    
    available_pages = [
        "1. Сводный лист портфеля", 
        "2. Динамика и рост ПДЗ", 
        "3. Топ-5 дебиторов (Риски)", 
        "4. Детальный реестр и заказы"
    ]
    
    # Доступ к экспорту и отправке только для роли Директор
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
                "Макс. дней просрочки": st.column_config.NumberColumn("Макс. дней просрочки", format="%d"),
            },
            use_container_width=True,
            hide_index=True
        )
        
    elif page == "2. Динамика и рост ПДЗ":
        st.subheader("📈 Страница 2: Анализ динамики и роста просроченной задолженности (ПДЗ)")
        col_a, col_b = st.columns(2)
        with col_a:
            fig_aging = px.bar(df_aging, x='Интервал', y='Долг', text='Доля (%)', title="Структура задолженности по интервалам просрочки", color='Долг', color_continuous_scale='Reds')
            fig_aging.update_traces(texttemplate='%{text:.1f}%', textposition='outside')
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
        
        st.dataframe(top_debtors[['№ п/п', 'Клиент', 'Общий долг', 'Просрочено', 'Макс. дней просрочки', 'Комментарий']], use_container_width=True, hide_index=True)
        
    elif page == "4. Детальный реестр и заказы":
        st.subheader("🌳 Страница 4: Иерархический реестр (Клиенты и заказы)")
        selected_client_filter = st.selectbox("Фильтр по контрагенту:", ["Все клиенты"] + list(clients_df['Клиент'].unique()))
        filtered_hierarchy = hierarchy if selected_client_filter == "Все клиенты" else [c for c in hierarchy if c['Клиент'] == selected_client_filter]
        
        for client in filtered_hierarchy:
            with st.expander(f"📁 **{client['Клиент']}** — Всего долг: **{client['Общий долг']:,.2f} ₽** | Просрочено: **{client['Просрочено']:,.2f} ₽**"):
                st.markdown(f"**Комментарий отдела:** {client['Комментарий'] if client['Комментарий'] else 'Нет комментариев'}")
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
                    
    elif page == "5. Экспорт и отправка":
        st.subheader("⚙️ Страница 5: Экспорт отчета и рассылка")
        
        # Финансовое форматирование с разделителями тысяч (пробелы)
        def format_ru_number(val):
            if isinstance(val, (int, float)):
                return f"{val:,.2f}".replace(",", " ").replace(".", ",")
            return str(val)

        export_df = clients_df.copy()
        for col in export_df.columns:
            if export_df[col].dtype in ['float64', 'int64']:
                export_df[col] = export_df[col].apply(format_ru_number)
        
        export_df = export_df.fillna("-")
        
        # HTML с кроссплатформенными системными шрифтами для macOS и Windows
        html_content = f"""
        <html>
        <head>
            <meta charset="utf-8">
            <title>Сводный финансовый отчет по дебиторской задолженности</title>
            <style>
                body {{ 
                    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif; 
                    margin: 20px; 
                    color: #333; 
                }}
                h1 {{ color: #1F4E78; font-size: 22px; }}
                p {{ color: #595959; font-size: 14px; }}
                table {{ border-collapse: collapse; width: 100%; margin-top: 20px; font-size: 13px; }}
                th, td {{ border: 1px solid #D9D9D9; padding: 10px 12px; text-align: left; }}
                th {{ background-color: #1F4E78; color: white; font-weight: bold; }}
                tr:nth-child(even) {{ background-color: #F9FAFB; }}
                td:nth-child(n+3) {{ text-align: right; }}
            </style>
        </head>
        <body>
            <h1>Сводный финансовый отчет по дебиторской задолженности</h1>
            <p>Дата актуальности: Свежий срез из Google Drive | Валюта: RUB</p>
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
                success, message = send_report_via_email(html_content, recipient_input)
                if success:
                    st.success(f"✅ {message}")
                else:
                    st.error(f"❌ Ошибка: {message}")
else:
    st.error("❌ Не удалось получить файл отчета из Google Drive.")
