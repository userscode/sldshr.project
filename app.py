import streamlit as st
import hashlib
from datetime import datetime

st.set_page_config(page_title="Форум", page_icon="📝", layout="centered")

@st.cache_resource
def get_database():
    # Имитация базы данных
    return {
        "users": {}, # {"никнейм": "хэш_пароля"}
        "topics": [
            # Пример стартовой темы
            {"id": 1, "title": "Добро пожаловать на наш новый форум!", "author": "Система", "time": "12:00:00", "views": 0}
        ],
        "posts": {
            # Ключ - ID темы, значение - список сообщений
            1: [{"author": "Система", "content": "Здесь вы можете общаться, создавать темы и обсуждать всё на свете.", "time": "12:00:00"}]
        }
    }

db = get_database()

# Функция для шифрования паролей
def make_hash(password):
    return hashlib.sha256(str.encode(password)).hexdigest()

if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
if "username" not in st.session_state:
    st.session_state.username = ""
if "page" not in st.session_state:
    st.session_state.page = "home" # "home", "topic", "new_topic"
if "current_topic_id" not in st.session_state:
    st.session_state.current_topic_id = None

with st.sidebar:
    if not st.session_state.logged_in:
        st.header("Вход / Регистрация")
        tab1, tab2 = st.tabs(["Вход", "Регистрация"])
        
        with tab1:
            l_user = st.text_input("Никнейм", key="l_user")
            l_pass = st.text_input("Пароль", type="password", key="l_pass")
            if st.button("Войти", use_container_width=True):
                if l_user in db["users"] and db["users"][l_user] == make_hash(l_pass):
                    st.session_state.logged_in = True
                    st.session_state.username = l_user
                    st.rerun()
                else:
                    st.error("Неверный логин или пароль")
                    
        with tab2:
            r_user = st.text_input("Никнейм", key="r_user")
            r_pass = st.text_input("Пароль", type="password", key="r_pass")
            if st.button("Создать аккаунт", use_container_width=True):
                if not r_user or not r_pass:
                    st.warning("Заполните все поля")
                elif r_user in db["users"]:
                    st.error("Никнейм занят")
                else:
                    db["users"][r_user] = make_hash(r_pass)
                    st.success("Аккаунт создан! Теперь войдите.")
    else:
        st.header(f"👤 {st.session_state.username}")
        if st.button("Выйти", use_container_width=True):
            st.session_state.logged_in = False
            st.session_state.username = ""
            st.rerun()
            
    st.divider()
    if st.button("🏠 На главную", use_container_width=True):
        st.session_state.page = "home"
        st.rerun()

def show_home():
    st.title("📝 Главная страница форума")
    
    col1, col2 = st.columns([3, 1])
    with col1:
        st.write("Выберите тему для обсуждения или создайте свою.")
    with col2:
        if st.session_state.logged_in:
            if st.button("➕ Создать тему", type="primary", use_container_width=True):
                st.session_state.page = "new_topic"
                st.rerun()
        else:
            st.info("Войдите, чтобы создавать темы")
            
    st.divider()
    
    # Отображаем список тем (в обратном порядке, чтобы новые были сверху)
    for topic in reversed(db["topics"]):
        t_id = topic["id"]
        replies_count = len(db["posts"].get(t_id, [])) - 1 # Минус 1, так как первое сообщение - это тело темы
        
        c1, c2, c3 = st.columns([5, 2, 2])
        with c1:
            st.markdown(f"### {topic['title']}")
            st.caption(f"Автор: **{topic['author']}** | Создано: {topic['time']}")
        with c2:
            st.write(f"💬 Ответов: {replies_count}")
            st.write(f"👁 Просмотров: {topic['views']}")
        with c3:
            if st.button("Читать", key=f"read_{t_id}", use_container_width=True):
                topic["views"] += 1 # Увеличиваем счетчик просмотров
                st.session_state.current_topic_id = t_id
                st.session_state.page = "topic"
                st.rerun()
        st.markdown("---")

def show_new_topic():
    st.title("➕ Создание новой темы")
    
    if not st.session_state.logged_in:
        st.error("Вам нужно войти в аккаунт, чтобы создать тему.")
        return
        
    title = st.text_input("Заголовок темы")
    content = st.text_area("Текст сообщения", height=150)
    
    col1, col2 = st.columns([1, 1])
    with col1:
        if st.button("Опубликовать", type="primary"):
            if not title or not content:
                st.warning("Заполните заголовок и текст.")
            else:
                # Генерируем новый ID темы
                new_id = len(db["topics"]) + 1
                timestamp = datetime.now().strftime("%H:%M:%S")
                
                # Создаем тему
                db["topics"].append({
                    "id": new_id,
                    "title": title,
                    "author": st.session_state.username,
                    "time": timestamp,
                    "views": 0
                })
                
                # Создаем первый пост в этой теме
                db["posts"][new_id] = [{
                    "author": st.session_state.username,
                    "content": content,
                    "time": timestamp
                }]
                
                st.session_state.current_topic_id = new_id
                st.session_state.page = "topic"
                st.rerun()
    with col2:
        if st.button("Отмена"):
            st.session_state.page = "home"
            st.rerun()

@st.fragment(run_every="3s") # Обновляем тему каждые 3 секунды, чтобы видеть новые ответы
def show_topic():
    t_id = st.session_state.current_topic_id
    
    # Ищем саму тему
    topic = next((t for t in db["topics"] if t["id"] == t_id), None)
    if not topic:
        st.error("Тема не найдена!")
        if st.button("Вернуться"):
            st.session_state.page = "home"
            st.rerun()
        return

    st.title(topic["title"])
    st.caption(f"Создал(а): **{topic['author']}** | Просмотров: {topic['views']}")
    st.divider()
    
    # Отображаем сообщения
    posts = db["posts"].get(t_id, [])
    
    for i, post in enumerate(posts):
        is_topic_starter = i == 0
        
        with st.container(border=True):
            header_col, time_col = st.columns([4, 1])
            with header_col:
                if is_topic_starter:
                    st.markdown(f"🌟 **{post['author']}** (Автор темы)")
                else:
                    st.markdown(f"👤 **{post['author']}**")
            with time_col:
                st.caption(post["time"])
                
            st.markdown(post["content"])
            
    st.write("") # Отступ
    
    # Форма для ответа
    if st.session_state.logged_in:
        reply_content = st.chat_input("Написать ответ...")
        if reply_content:
            timestamp = datetime.now().strftime("%H:%M:%S")
            db["posts"][t_id].append({
                "author": st.session_state.username,
                "content": reply_content,
                "time": timestamp
            })
            st.rerun()
    else:
        st.info("Чтобы оставить комментарий, войдите в аккаунт в боковом меню слева.")

if st.session_state.page == "home":
    show_home()
elif st.session_state.page == "new_topic":
    show_new_topic()
elif st.session_state.page == "topic":
    show_topic()
