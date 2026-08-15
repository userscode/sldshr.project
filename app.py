import streamlit as st
from datetime import datetime

# Настраиваем страницу (должно быть первым вызовом)
st.set_page_config(page_title="Общий чат", page_icon="💬", layout="centered")

# Используем @st.cache_resource, чтобы этот список был один на ВСЕХ пользователей (глобальная переменная).
# В отличие от session_state, который хранит данные только для одной вкладки браузера.
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

chat_store = get_chat_store()

st.title("💬 Открытый мессенджер")
st.markdown("Написано на **Streamlit**. Сообщения появляются у всех пользователей в реальном времени.")

# Сохраняем никнейм в локальную сессию конкретного пользователя
if "username" not in st.session_state:
    st.session_state.username = "Гость"

# Поле для ввода никнейма
username_input = st.text_input("Ваш никнейм:", value=st.session_state.username, max_chars=20)
st.session_state.username = username_input

# Декоратор @st.fragment(run_every="2s") заставляет обновляться ТОЛЬКО эту функцию каждые 2 секунды.
# Это позволяет нам подгружать новые сообщения от других людей, не перезагружая всю страницу.
@st.fragment(run_every="2s")
def display_chat():
    # Создаем контейнер фиксированной высоты с прокруткой
    chat_container = st.container(height=500)
    
    with chat_container:
        for msg in chat_store:
            # Выбираем иконку/роль в зависимости от того, кто пишет
            role = "assistant" if msg["name"] == "Система" else "user"
            
            with st.chat_message(role):
                if msg["name"] == "Система":
                    st.markdown(msg["content"])
                else:
                    st.markdown(f"**{msg['name']}** *(в {msg['time']})*:\n\n{msg['content']}")

# Запускаем отрисовку чата
display_chat()

# Компонент chat_input всегда прикреплен к низу экрана
if prompt := st.chat_input("Напишите сообщение..."):
    # Проверка на пустой никнейм
    current_user = st.session_state.username.strip()
    if not current_user:
        current_user = "Аноним"
        
    timestamp = datetime.now().strftime("%H:%M:%S")
    
    # Добавляем сообщение в глобальную память
    chat_store.append({
        "role": "user",
        "name": current_user,
        "time": timestamp,
        "content": prompt
    })
    
    # Принудительно перезагружаем страницу пользователя, чтобы его сообщение появилось моментально,
    # не дожидаясь срабатывания таймера из фрагмента.
    st.rerun()
