import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from io import BytesIO
import os

# Page configuration
st.set_page_config(
    page_title="Дашборд: Управление дебиторской задолженностью",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS styling for corporate look (КРАЙВИН style)
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
st.markdown("Инструмент контроля просроченной дебиторской задолженности (ПДЗ), анализа клиентов и претензионной работы.")

# Sidebar for File Import & Controls
st.sidebar.header("📁 Управление данными")
uploaded_file = st.sidebar.file_uploader("Загрузить файл отчета (Excel)", type=["xlsx", "xls"])

# Default fallback file if available in local workspace
default_file = "Отчет по дебиторской задолженности 27.07.2026.xlsx"
target_file = uploaded_file if uploaded_file is not None else (default_file if os.path.exists(default_file) else None)

@st.cache_data
def load_data(file):
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
    
    # Parse detailed register (from row 21 onwards)
    data_rows = []
    current_client = None
    
    for idx, row in df_raw.iterrows():
        if idx < 21:
            continue
        if idx == 92: # Итого
            break
        
        col_0 = row.iloc[0]
        col_2 = row.iloc[2]
        col_9 = row.iloc[9]
        col_11 = row.iloc[11]
        col_13 = row.iloc[13]
        col_14 = row.iloc[14]
        col_15 = row.iloc[15]
        col_16 = row.iloc[16]
        col_17 = row.iloc[17]
        col_18 = row.iloc[18]
        col_19 = row.iloc[19]
        
        if pd.notna(col_0) and isinstance(col_0, (int, float)) and not (isinstance(col_2, str) and col_2.startswith('Заказ')):
            current_client = str(col_2).strip()
            is_client = True
        else:
            is_client = False
            
        def safe_float(val):
            try:
                return float(val)
            except:
                return 0.0

        data_rows.append({
            'row_idx': idx,
            'is_client': is_client,
            'Клиент': current_client,
            'Объект расчетов': str(col_2).strip() if pd.notna(col_2) else '',
            'Общий долг': safe_float(col_9),
            'Доля долга (%)': safe_float(col_11),
            'Просрочено': safe_float(col_13),
            'Просрочено (%)': safe_float(col_14),
            'Дней просрочки': safe_float(col_15),
            'Наш долг': safe_float(col_16),
            'К отгрузке': safe_float(col_17),
            'Не просрочено': safe_float(col_18),
            'Комментарий': str(col_19).strip() if pd.notna(col_19) else ''
        })
        
    df_register = pd.DataFrame(data_rows)
    return df_aging, df_register

if target_file is not None:
    df_aging, df_register = load_data(target_file)
    
    # Sidebar Filters
    st.sidebar.markdown("---")
    st.sidebar.subheader("🔍 Фильтры")
    
    clients_list = sorted(df_register[df_register['is_client']]['Клиент'].dropna().unique())
    selected_client = st.sidebar.selectbox("Выберите клиента", ["Все клиенты"] + list(clients_list))
    
    min_days = st.sidebar.slider("Минимум дней просрочки", 0, int(df_register['Дней просрочки'].max()), 0)
    
    # Filter data
    filtered_df = df_register.copy()
    if selected_client != "Все клиенты":
        client_rows = filtered_df[filtered_df['Клиент'] == selected_client]
        filtered_df = client_rows
        
    filtered_df = filtered_df[filtered_df['Дней просрочки'] >= min_days]
    
    # KPI Metrics
    total_portfolio = df_register[df_register['is_client']]['Общий долг'].sum()
    total_overdue = df_register[df_register['is_client']]['Просрочено'].sum()
    total_not_overdue = df_register[df_register['is_client']]['Не просрочено'].sum()
    overdue_share = (total_overdue / total_portfolio) * 100 if total_portfolio > 0 else 0
    
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Общий портфель долга", f"{total_portfolio:,.2f} ₽")
    col2.metric("Не просрочено", f"{total_not_overdue:,.2f} ₽", f"{100 - overdue_share:.1f}%")
    col3.metric("Просрочено (ПДЗ)", f"{total_overdue:,.2f} ₽", f"{overdue_share:.1f}%", delta_color="inverse")
    col4.metric("Активных клиентов", len(clients_list))
    
    st.markdown("---")
    
    # Tabs for navigation
    tab1, tab2, tab3 = st.tabs(["📈 Аналитика и Графики", "📋 Реестр задолженности", "⚙️ Экспорт данных"])
    
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
            clients_summary = df_register[df_register['is_client']].sort_values(by='Общий долг', ascending=False).head(10)
            fig_clients = px.bar(
                clients_summary,
                x='Общий долг',
                y='Клиент',
                orientation='h',
                title="ТОП-10 должников по общей сумме долга",
                color='Общий долг',
                color_continuous_scale='Reds'
            )
            fig_clients.update_layout(yaxis={'categoryorder':'total ascending'}, xaxis_title="Сумма долга (руб.)", yaxis_title="")
            st.plotly_chart(fig_clients, use_container_width=True)
            
    with tab2:
        st.subheader("Детальный реестр дебиторской задолженности")
        st.dataframe(filtered_df[['Клиент', 'Объект расчетов', 'Общий долг', 'Доля долга (%)', 'Просрочено', 'Дней просрочки', 'Наш долг', 'К отгрузке', 'Не просрочено', 'Комментарий']], use_container_width=True)
        
    with tab3:
        st.subheader("Экспорт отчета")
        st.markdown("Вы можете выгрузить актуальные и отфильтрованные данные в формате Excel или CSV.")
        
        output = BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df_register.to_excel(writer, index=False, sheet_name='Реестр задолженности')
            df_aging.to_excel(writer, index=False, sheet_name='Интервалы просрочки')
        processed_data = output.getvalue()
        
        st.download_button(
            label="📥 Скачать полный отчет в Excel",
            data=processed_data,
            file_name="Дебиторская_задолженность_анализ.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
        
else:
    st.info("Пожалуйста, загрузите Excel-файл с отчетом через боковую панель слева, чтобы начать работу.")
