import streamlit as st
import pandas as pd
import plotly.express as px
from io import BytesIO
import os

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
st.markdown("Иерархический анализ просроченной дебиторской задолженности (ПДЗ) по клиентам и заказам.")

# Sidebar for File Import & Controls
st.sidebar.header("📁 Управление данными")
uploaded_file = st.sidebar.file_uploader("Загрузить файл отчета (Excel)", type=["xlsx", "xls"])

default_file = "Отчет по дебиторской задолженности 27.07.2026.xlsx"
target_file = uploaded_file if uploaded_file is not None else (default_file if os.path.exists(default_file) else None)

@st.cache_data
def load_hierarchy_data(file):
    df_raw = pd.read_excel(file, header=None)
    
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
    current_client = None
    current_client_data = None
    
    for idx, row in df_raw.iterrows():
        if idx < 21:
            continue
        if idx == 93:
            break
        
        col_0 = row.iloc[0]
        col_2 = row.iloc[2]
        
        def safe_float(val):
            try:
                return float(val)
            except:
                return 0.0

        if pd.notna(col_0) and isinstance(col_0, (int, float)) and not (isinstance(col_2, str) and col_2.startswith('Заказ')):
            if current_client_data:
                hierarchy.append(current_client_data)
                
            current_client = str(col_2).strip()
            current_client_data = {
                'Клиент': current_client,
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

if target_file is not None:
    df_aging, hierarchy = load_hierarchy_data(target_file)
    
    # Flatten clients summary for charts & metrics
    clients_df = pd.DataFrame([{
        'Клиент': c['Клиент'],
        'Общий долг': c['Общий долг'],
        'Просрочено': c['Просрочено'],
        'Доля долга (%)': c['Доля долга (%)'],
        'Дней просрочки': c['Дней просрочки'],
        'Комментарий': c['Комментарий']
    } for c in hierarchy])
    
    # Sidebar Filters
    st.sidebar.markdown("---")
    st.sidebar.subheader("🔍 Фильтры")
    
    clients_list = sorted(clients_df['Клиент'].dropna().unique())
    selected_client = st.sidebar.selectbox("Выберите клиента", ["Все клиенты"] + list(clients_list))
    
    # KPI Metrics
    total_portfolio = clients_df['Общий долг'].sum()
    total_overdue = clients_df['Просрочено'].sum()
    total_not_overdue = total_portfolio - total_overdue
    overdue_share = (total_overdue / total_portfolio) * 100 if total_portfolio > 0 else 0
    
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Общий портфель долга", f"{total_portfolio:,.2f}".replace(",", " ") + " ₽")
    col2.metric("Не просрочено", f"{total_not_overdue:,.2f}".replace(",", " ") + " ₽", f"{100 - overdue_share:.1f}%")
    col3.metric("Просрочено (ПДЗ)", f"{total_overdue:,.2f}".replace(",", " ") + " ₽", f"{overdue_share:.1f}%", delta_color="inverse")
    col4.metric("Активных клиентов", len(clients_list))
    
    st.markdown("---")
    
    # Tabs for navigation
    tab1, tab2, tab3 = st.tabs(["📈 Аналитика и Графики", "🌳 Иерархический реестр (Дерево)", "⚙️ Экспорт данных"])
    
    with tab1:
        st.subheader("Структура и динамика просроченной задолженности")
        
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
            top_clients = clients_df.sort_values(by='Общий долг', ascending=False).head(10)
            fig_clients = px.bar(
                top_clients,
                x='Общий долг',
                y='Клиент',
                orientation='h',
                title="ТОП-10 клиентов по общей сумме долга",
                color='Общий долг',
                color_continuous_scale='Reds'
            )
            fig_clients.update_layout(yaxis={'categoryorder':'total ascending'}, xaxis_title="Сумма долга (руб.)", yaxis_title="")
            st.plotly_chart(fig_clients, use_container_width=True)
            
    with tab2:
        st.subheader("Иерархический реестр задолженности (Клиенты и Заказы)")
        st.markdown("💡 *Каждый клиент представлен итоговой строкой. Разверните блок клиента, чтобы просмотреть детальные заказы.*")
        
        filtered_hierarchy = hierarchy if selected_client == "Все клиенты" else [c for c in hierarchy if c['Клиент'] == selected_client]
        
        for client in filtered_hierarchy:
            with st.expander(f"📁 **{client['Клиент']}** — Всего долг: **{client['Общий долг']:,.2f} ₽** | Просрочено: **{client['Просрочено']:,.2f} ₽**"):
                st.markdown(f"**Статус / Комментарий:** {client['Комментарий'] if client['Комментарий'] else 'Нет комментариев'}")
                
                orders_data = []
                for order in client['Заказы']:
                    orders_data.append({
                        'Объект расчетов': order['Объект расчетов'],
                        'Общий долг': order['Общий долг'],
                        'Просрочено': order['Просрочено'],
                        'Дней просрочки': order['Дней просрочки'],
                        'Наш долг': order['Наш долг'],
                        'К отгрузке': order['К отгрузке'],
                        'Не просрочено': order['Не просрочено'],
                        'Комментарий': order['Комментарий']
                    })
                
                if orders_data:
                    df_orders = pd.DataFrame(orders_data)
                    st.dataframe(
                        df_orders,
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
                    
    with tab3:
        st.subheader("Экспорт отчета")
        st.markdown("Вы можете выгрузить агрегированный и детализированный отчет.")
        
        output = BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            clients_df.to_excel(writer, index=False, sheet_name='Клиенты (Итоги)')
            df_aging.to_excel(writer, index=False, sheet_name='Интервалы просрочки')
        excel_data = output.getvalue()
        
        st.download_button(
            label="📥 Скачать сводный отчет по клиентам в Excel",
            data=excel_data,
            file_name="Сводный_отчет_клиенты.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
else:
    st.info("Пожалуйста, загрузите Excel-файл с отчетом через боковую панель слева, чтобы начать работу.")
