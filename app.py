import streamlit as st
import hashlib
from datetime import datetime

# Настраиваем страницу (должно быть первым вызовом)
st.set_page_config(page_title="Общий чат", page_icon="💬", layout="centered")

# Хранилище сообщений чата
@st.cache_resource
def get_chat_store():
    return [
        {
            "role": "assistant", 
            "name": "Система", 
            "time": "", 
            "content": "🤖 Добро пожаловать! Это общий чат. Все ваши сообщения увидят другие участники."
        }
    ]

# Хранилище пользователей (формат: {"никнейм": "хэш_пароля"})
@st.cache_resource
def get_user_store():
    return {}

chat_store = get_chat_store()
user_store = get_user_store()

# Функция для шифрования паролей
def make_hash(password):
    return hashlib.sha256(str.encode(password)).hexdigest()

# Переменные сессии для конкретного пользователя (открывшего вкладку)
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
if "username" not in st.session_state:
    st.session_state.username = ""

def auth_ui():
    st.title("🔐 Вход в мессенджер")
    
    # Создаем вкладки для входа и регистрации
    tab_login, tab_register = st.tabs(["Вход", "Регистрация"])
    
    with tab_login:
        st.subheader("Войти в аккаунт")
        log_user = st.text_input("Никнейм", key="log_user")
        log_pass = st.text_input("Пароль", type="password", key="log_pass")
        
        if st.button("Войти", type="primary"):
            if not log_user or not log_pass:
                st.warning("Пожалуйста, заполните все поля.")
            elif log_user in user_store and user_store[log_user] == make_hash(log_pass):
                st.session_state.logged_in = True
                st.session_state.username = log_user
                st.rerun() # Перезагружаем страницу, чтобы скрыть форму и показать чат
            else:
                st.error("Неверный никнейм или пароль!")

    with tab_register:
        st.subheader("Создать новый аккаунт")
        reg_user = st.text_input("Придумайте никнейм", key="reg_user")
        reg_pass = st.text_input("Придумайте пароль", type="password", key="reg_pass")
        reg_pass2 = st.text_input("Повторите пароль", type="password", key="reg_pass2")
        
        if st.button("Зарегистрироваться"):
            if not reg_user or not reg_pass:
                st.warning("Пожалуйста, заполните все поля.")
            elif reg_user in user_store:
                st.error("Пользователь с таким никнеймом уже существует!")
            elif reg_pass != reg_pass2:
                st.error("Пароли не совпадают!")
            else:
                # Сохраняем зашифрованный пароль
                user_store[reg_user] = make_hash(reg_pass)
                st.success("Успешная регистрация! Теперь вы можете войти во вкладке 'Вход'.")

# Эта функция обновляется каждые 2 секунды, чтобы подгружать чужие сообщения
@st.fragment(run_every="2s")
def display_chat():
    chat_container = st.container(height=500)
    with chat_container:
        for msg in chat_store:
            # Свои сообщения показываем справа, чужие слева (если поддерживается, иначе просто разделяем роли)
            is_system = msg["name"] == "Система"
            is_me = msg["name"] == st.session_state.username
            
            # Для визуала: системные сообщения - assistant, остальные - user
            role = "assistant" if is_system else "user"
            
            with st.chat_message(role):
                if is_system:
                    st.markdown(msg["content"])
                else:
                    # Выделяем свои сообщения подписью "(Вы)"
                    me_label = " *(Вы)*" if is_me else ""
                    st.markdown(f"**{msg['name']}**{me_label} *(в {msg['time']})*:\n\n{msg['content']}")

# Если пользователь не вошел -> показываем форму входа
if not st.session_state.logged_in:
    auth_ui()
    
# Если вошел -> показываем чат
else:
    # Шапка чата с кнопкой выхода
    col1, col2 = st.columns([8, 2])
    with col1:
        st.title("💬 Открытый мессенджер")
    with col2:
        st.write("") # Отступ для выравнивания
        if st.button("Выйти"):
            st.session_state.logged_in = False
            st.session_state.username = ""
            st.rerun()

    st.markdown(f"Вы вошли как: **{st.session_state.username}**")

    display_chat()

    # Поле ввода (работает только если мы внутри ветки "else" авторизованного пользователя)
    if prompt := st.chat_input("Напишите сообщение..."):
        timestamp = datetime.now().strftime("%H:%M:%S")
        
        # Сохраняем сообщение
        chat_store.append({
            "role": "user",
            "name": st.session_state.username,
            "time": timestamp,
            "content": prompt
        })
        
        # Обновляем страницу для моментального отображения своего сообщения
        st.rerun()
