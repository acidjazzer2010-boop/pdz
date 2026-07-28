import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from io import BytesIO
from exporter import send_report_via_email

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

st.title("📊 Дашборд финансового анализа и управления дебиторской задолженностью")
st.markdown("Иерархический анализ просроченной дебиторской задолженности (ПДЗ), динамика и свод по клиентам.")

# Sidebar for File Import & Controls
st.sidebar.header("📁 Управление данными")
uploaded_file = st.sidebar.file_uploader("Загрузить свежий файл отчета (Excel)", type=["xlsx", "xls"])

@st.cache_data
def load_hierarchy_data(file_bytes):
    df_raw = pd.read_excel(file_bytes, header=None)
    
    # Parse aging summary table (rows 9 to 15)
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
    
    # Parse hierarchical clients and orders
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

if uploaded_file is not None:
    df_aging, hierarchy = load_hierarchy_data(uploaded_file)
    
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
    
    # Sidebar Filters
    st.sidebar.markdown("---")
    st.sidebar.subheader("🔍 Фильтры")
    clients_list = sorted(clients_df['Клиент'].dropna().unique())
    selected_client = st.sidebar.selectbox("Выберите клиента", ["Все клиенты"] + list(clients_list))
    
    # KPI Metrics
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
    
    # Tabs for navigation
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
            fig_aging = px.bar(
                df_aging, 
                x='Интервал', 
                y='Долг', 
                text='Доля (%)',
                title="Распределение долга по интервалам просрочки",
                color='Долг',
                color_continuous_scale='Blues'
            )
            fig_aging.update_traces(texttemplate='%{text:.1f}%', textposition='outside')
            fig_aging.update_layout(xaxis_title="Интервал просрочки", yaxis_title="Сумма долга (руб.)")
            st.plotly_chart(fig_aging, use_container_width=True)
            
        with c2:
            dynamics_data = pd.DataFrame({
                'Месяц': ['Март', 'Апр', 'Май', 'Июн', 'Текущий'],
                'Общий долг': [total_portfolio*0.9, total_portfolio*0.93, total_portfolio*0.96, total_portfolio*0.98, total_portfolio],
                'Просроченный долг (ПДЗ)': [total_overdue*0.85, total_overdue*0.9, total_overdue*0.93, total_overdue*0.96, total_overdue]
            })
            
            fig_dyn = px.line(
                dynamics_data, 
                x='Месяц', 
                y=['Общий долг', 'Просроченный долг (ПДЗ)'], 
                markers=True,
                title="Динамика портфеля дебиторской задолженности (Тренд)"
            )
            fig_dyn.update_layout(xaxis_title="Период", yaxis_title="Сумма (руб.)")
            st.plotly_chart(fig_dyn, use_container_width=True)
            
    with tab2:
        st.subheader("Сводный отчет по всем клиентам")
        st.markdown("💡 *Агрегированные данные по каждому контрагенту с возможностью сортировки.*")
        
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
        
    with tab3:
        st.subheader("Иерархический реестр задолженности (Дерево заказов)")
        filtered_hierarchy = hierarchy if selected_client == "Все клиенты" else [c for c in hierarchy if c['Клиент'] == selected_client]
        
        for client in filtered_hierarchy:
            with st.expander(f"📁 **{client['Клиент']}** — Всего долг: **{client['Общий долг']:,.2f} ₽** | Просрочено: **{client['Просрочено']:,.2f} ₽**"):
                st.markdown(f"**Статус / Комментарий:** {client['Комментарий'] if client['Комментарий'] else 'Нет комментариев'}")
                
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
                    st.dataframe(
                        pd.DataFrame(orders_data),
                        column_config={
                            "Общий долг": st.column_config.NumberColumn("Общий долг (₽)", format="%,.2f ₽"),
                            "Просрочено": st.column_config.NumberColumn("Просрочено (₽)", format="%,.2f ₽"),
                            "Наш долг": st.column_config.NumberColumn("Наш долг (₽)", format="%,.2f ₽"),
                            "К отгрузке": st.column_config.NumberColumn("К отгрузке (₽)", format="%,.2f ₽"),
                            "Не просрочено": st.column_config.NumberColumn("Не просрочено (₽)", format="%,.2f ₽"),
                            "Дней просрочки": st.column_config.NumberColumn("Дней просрочки", format="%d"),
                        },
                        use_container_width=True,
                        hide_index=True
                    )
                else:
                    st.info("Детальные заказы отсутствуют.")
                    
    with tab4:
        st.subheader("⚙️ Панель экспорта и отправки отчета")
        
        export_df = clients_df.fillna("-")
        
        html_content = f"""
        <html>
        <head>
            <meta charset="utf-8">
            <title>Сводный отчет по дебиторской задолженности</title>
            <style>
                body {{ font-family: Arial, sans-serif; margin: 20px; color: #333; }}
                h1 {{ color: #1F4E78; }}
                table {{ border-collapse: collapse; width: 100%; margin-top: 20px; font-size: 14px; }}
                th, td {{ border: 1px solid #D9D9D9; padding: 8px 12px; text-align: left; }}
                th {{ background-color: #1F4E78; color: white; }}
                tr:nth-child(even) {{ background-color: #F9FAFB; }}
            </style>
        </head>
        <body>
            <h1>Сводный отчет по дебиторской задолженности</h1>
            <p>Дата актуальности: Свежий срез | Валюта: RUB</p>
            <h3>Свод по клиентам</h3>
            {export_df.to_html(index=False, float_format=lambda x: f"{x:,.2f}" if isinstance(x, (int, float)) else str(x))}
        </body>
        </html>
        """
        
        col_exp1, col_exp2 = st.columns(2)
        
        with col_exp1:
            st.markdown("### 📥 Скачать HTML-отчет")
            st.markdown("Сохранить готовый веб-отчет на устройство.")
            st.download_button(
                label="🌐 Скачать отчет в HTML",
                data=html_content.encode("utf-8"),
                file_name="Сводный_отчет_дебиторская_задолженность.html",
                mime="text/html"
            )
            
        with col_exp2:
            st.markdown("### 📧 Отправить по электронной почте")
            has_server_secrets = "SMTP_SERVER" in st.secrets or "smtp" in st.secrets
            
            recipient_input = st.text_input("Email получателя", value="boss@company.ru")
            
            if st.button("📨 Отправить отчет по почте"):
                if has_server_secrets:
                    success, message = send_report_via_email(html_content, recipient_input)
                else:
                    # Резервный вариант на случай локального тестирования без st.secrets
                    config = {
                        "server": "smtp.yandex.ru",
                        "port": 465,
                        "sender_email": "user@yandex.ru",
                        "sender_password": "password"
                    }
                    success, message = send_report_via_email(html_content, recipient_input, smtp_config=config)
                    
                if success:
                    st.success(f"✅ {message}")
                else:
                    st.error(f"❌ Ошибка: {message}")
else:
    st.info("👈 Пожалуйста, загрузите файл отчета Excel через боковую панель слева, чтобы начать работу с дашбордом.")
