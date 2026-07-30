import streamlit as st
import streamlit.components.v1 as components

# Настройка страницы
st.set_page_config(
    page_title="Корпоративный портал KRAYVIN",
    page_icon="💼",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Стилизация портала
st.markdown("""
    <style>
    .main {
        background-color: #F8F9FA;
    }
    h1, h2, h3 {
        color: #1F4E78;
    }
    div.stTabs [data-baseweb="tab-panel"] {
        padding-top: 10px;
    }
    </style>
""", unsafe_allow_html=True)

# --- ЕДИНАЯ АВТОРИЗАЦИЯ НА ПОРТАЛЕ ---
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
    
    if username in users_dict:
        if users_dict[username]["password"] == password:
            return True, users_dict[username]["role"], users_dict[username]["name"]
    return False, None, None

if not st.session_state.authenticated:
    st.markdown("<h2 style='text-align: center; color: #1F4E78;'>🔐 Корпоративный портал KRAYVIN</h2>", unsafe_allow_html=True)
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

# --- БОКОВАЯ ПАНЕЛЬ ПРОФИЛЯ ---
st.sidebar.markdown(f"👤 **{st.session_state.name}**")
st.sidebar.markdown(f"🔑 Роль: {st.session_state.role}")
if st.sidebar.button("🚪 Выйти из системы"):
    st.session_state.authenticated = False
    st.session_state.username = None
    st.session_state.role = None
    st.session_state.name = None
    st.rerun()

# --- ВКЛАДКИ СЕРВИСОВ (СВЕТЛАЯ ТЕМА) ---
tab1, tab2 = st.tabs(["🧮 КРАЙВИН: Анализ денежных потоков", "📈 Управление дебиторской задолженностью"])

with tab1:
    components.iframe(
        "https://kraivin-dashboard-cpmnvlfyd78y4kyfgryypb.streamlit.app/?embed=true&theme.base=light",
        height=950,
        scrolling=True
    )

with tab2:
    components.iframe(
        "https://ompavtzjtpjclke8fqjmkp.streamlit.app/?embed=true&theme.base=light",
        height=950,
        scrolling=True
    )
