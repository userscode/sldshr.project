import streamlit as st
import hashlib
from datetime import datetime
import json
import base64
import threading
import uuid
import io
from huggingface_hub import HfApi, hf_hub_download

st.set_page_config(page_title="Мессенджер", page_icon=":material/forum:", layout="wide", initial_sidebar_state="expanded")

st.markdown("""
<style>
    /* Скрываем стандартное верхнее меню и футер Streamlit */
    #MainMenu {visibility: hidden;}
    header {visibility: hidden;}
    footer {visibility: hidden;}
    
    /* Сброс лишних отступов в главном контейнере */
    .block-container {
        padding-top: 1rem !important;
        padding-bottom: 1rem !important;
        max-width: 1400px;
    }
    
    /* Круглые аватарки везде */
    [data-testid="stImage"] img {
        border-radius: 50% !important;
        object-fit: cover !important;
    }
    
    /* Улучшение визуального стиля для чата */
    [data-testid="stChatMessage"] {
        padding: 0.5rem 1rem;
        border-radius: 8px;
    }
    
    /* Уменьшение отступов у кнопок действий внутри сообщений */
    .stButton button {
        min-height: 2rem !important;
        padding-top: 0 !important;
        padding-bottom: 0 !important;
    }
    
    /* ИСПРАВЛЕНИЕ ДЛЯ КНОПОК: Запрещаем тексту внутри кнопок переноситься на новую строку */
    div[data-testid="stButton"] button div[data-testid="stMarkdownContainer"] p {
        white-space: nowrap !important;
        overflow: hidden !important;
        text-overflow: ellipsis !important;
    }
    
    /* Адаптация под мобильные устройства */
    @media (max-width: 768px) {
        .block-container {
            padding-top: 3rem !important;
            padding-left: 0.5rem !important;
            padding-right: 0.5rem !important;
        }
        [data-testid="stChatMessage"] {
            padding: 0.5rem;
        }
    }
</style>
""", unsafe_allow_html=True)

db_lock = threading.Lock()

@st.cache_resource
def get_database():
    try:
        repo_id = st.secrets["HF_REPO_ID"]
        token = st.secrets["HF_TOKEN"]
        file_path = hf_hub_download(repo_id=repo_id, filename="database.json", repo_type="dataset", token=token)
        with open(file_path, "r", encoding="utf-8") as f:
            db = json.load(f)
    except Exception as e:
        db = {
            "users": {},      
            "messages": {}
        }
        
    # Миграция старых данных
    for u, data in db["users"].items():
        if isinstance(data, str): 
            db["users"][u] = {"password": data, "bio": "", "avatar": None}
            
    for c_id, msgs in db["messages"].items():
        for m in msgs:
            if "id" not in m: m["id"] = str(uuid.uuid4())
            if "reply_to" not in m: m["reply_to"] = None
            if "edited" not in m: m["edited"] = False
            if "type" not in m: m["type"] = "text" # На всякий случай для старых сообщений
                
    return db

db = get_database()

def save_db():
    try:
        repo_id = st.secrets.get("HF_REPO_ID")
        token = st.secrets.get("HF_TOKEN")
        if not repo_id or not token: return
    except Exception: return

    def upload():
        with db_lock:
            try:
                api = HfApi(token=token)
                with open("temp_db.json", "w", encoding="utf-8") as f:
                    json.dump(db, f, ensure_ascii=False)
                api.upload_file(
                    path_or_fileobj="temp_db.json",
                    path_in_repo="database.json",
                    repo_id=repo_id,
                    repo_type="dataset",
                    commit_message="Auto-update database"
                )
            except Exception as e:
                pass
                
    threading.Thread(target=upload).start()

def make_hash(password):
    return hashlib.sha256(str.encode(password)).hexdigest()

def get_dm_id(user1, user2):
    users = sorted([user1, user2])
    return f"dm_{users[0]}_{users[1]}"

def set_action(action, msg_id):
    if action == "reply":
        st.session_state.replying_to = msg_id
        st.session_state.editing_msg = None
    elif action == "edit":
        st.session_state.editing_msg = msg_id
        st.session_state.replying_to = None

def delete_msg(c_id, msg_id):
    db["messages"][c_id] = [m for m in db["messages"][c_id] if m["id"] != msg_id]
    st.session_state.replying_to = None
    st.session_state.editing_msg = None
    save_db()

@st.dialog("Очистка чата")
def clear_chat_dialog(c_id):
    st.warning("Вы уверены, что хотите удалить всю историю переписки с этим пользователем? Это действие необратимо и удалит сообщения для вас обоих.")
    if st.button("🗑️ Удалить всё", type="primary", use_container_width=True):
        db["messages"][c_id] = []
        save_db()
        st.session_state.replying_to = None
        st.session_state.editing_msg = None
        st.rerun()

if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
    st.session_state.username = ""
    st.session_state.current_chat_id = None
    st.session_state.current_chat_name = None
    st.session_state.replying_to = None
    st.session_state.editing_msg = None
    st.session_state.last_chat_id = None

# Сброс действий при смене чата
if st.session_state.current_chat_id != st.session_state.last_chat_id:
    st.session_state.replying_to = None
    st.session_state.editing_msg = None
    st.session_state.last_chat_id = st.session_state.current_chat_id

@st.dialog("Настройки профиля")
def profile_dialog():
    user_data = db["users"][st.session_state.username]
    new_bio = st.text_input("О себе (статус)", value=user_data.get("bio", ""))
    new_avatar = st.file_uploader("Загрузить аватарку (до 2МБ)", type=["png", "jpg", "jpeg"])
    
    if st.button("Сохранить изменения", type="primary", use_container_width=True):
        user_data["bio"] = new_bio
        if new_avatar:
            user_data["avatar"] = base64.b64encode(new_avatar.read()).decode('utf-8')
        save_db()
        st.rerun()

@st.dialog("Профиль пользователя")
def view_profile_dialog(username):
    user_info = db["users"].get(username, {})
    col1, col2 = st.columns([1, 2])
    with col1:
        if user_info.get("avatar"):
            try:
                st.image(io.BytesIO(base64.b64decode(user_info["avatar"])), use_container_width=True)
            except Exception:
                st.markdown("<h1 style='text-align:center;'>👤</h1>", unsafe_allow_html=True)
        else:
            st.markdown("<h1 style='text-align:center;'>👤</h1>", unsafe_allow_html=True)
    with col2:
        st.markdown(f"### {username}")
        if user_info.get("bio"):
            st.info(user_info["bio"])
        else:
            st.caption("Пользователь не указал информацию о себе.")

if not st.session_state.logged_in:
    st.markdown("<h1 style='text-align: center; margin-bottom: 0;'>💬 Мессенджер</h1>", unsafe_allow_html=True)
    st.markdown("<p style='text-align: center; color: gray; margin-bottom: 2rem;'>Войдите или зарегистрируйтесь для начала общения</p>", unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns([1, 1.2, 1])
    with col2:
        tab1, tab2 = st.tabs(["🔑 Вход", "📝 Регистрация"])
        
        with tab1:
            l_user = st.text_input("Никнейм", key="l_user")
            l_pass = st.text_input("Пароль", type="password", key="l_pass")
            if st.button("Войти", type="primary", use_container_width=True):
                if l_user in db["users"] and db["users"][l_user]["password"] == make_hash(l_pass):
                    st.session_state.logged_in = True
                    st.session_state.username = l_user
                    st.rerun()
                else:
                    st.error("Неверный логин или пароль")
                    
        with tab2:
            r_user = st.text_input("Никнейм", key="r_user")
            r_pass = st.text_input("Пароль", type="password", key="r_pass")
            if st.button("Создать аккаунт", type="primary", use_container_width=True):
                if not r_user or not r_pass:
                    st.warning("Заполните все поля")
                elif r_user in db["users"]:
                    st.error("Никнейм уже занят")
                else:
                    db["users"][r_user] = {"password": make_hash(r_pass), "bio": "", "avatar": None}
                    save_db()
                    st.success("Аккаунт создан! Теперь выполните вход.")

else:
    current_user = st.session_state.username
    user_info = db["users"][current_user]
    
    # ИСПОЛЬЗУЕМ SIDEBAR: Идеальная адаптация для ПК (слева) и Мобильных (сворачивается)
    with st.sidebar:
        # Профиль пользователя
        prof_col1, prof_col2 = st.columns([1, 3], vertical_alignment="center")
        with prof_col1:
            if user_info.get("avatar"):
                try:
                    st.image(io.BytesIO(base64.b64decode(user_info["avatar"])), use_container_width=True)
                except Exception:
                    st.markdown("<h2 style='margin:0; text-align:center;'>👤</h2>", unsafe_allow_html=True)
            else:
                st.markdown("<h2 style='margin:0; text-align:center;'>👤</h2>", unsafe_allow_html=True)
        with prof_col2:
            st.markdown(f"**{current_user}**")
            
        act1, act2 = st.columns(2)
        with act1:
            if st.button("Настройки", icon=":material/settings:", use_container_width=True):
                profile_dialog()
        with act2:
            if st.button("Выйти", icon=":material/logout:", use_container_width=True):
                st.session_state.logged_in = False
                st.session_state.username = ""
                st.session_state.current_chat_id = None
                st.rerun()
            
        st.divider()
        
        # Личные сообщения
        st.markdown("#### :material/forum: Чаты")
        other_users = [u for u in db["users"].keys() if u != current_user]
        
        if not other_users:
            st.caption("Пока никто кроме вас не зарегистрировался.")
        else:
            for user in other_users:
                if st.button(f"{user}", icon=":material/account_circle:", type="tertiary", use_container_width=True, key=f"btn_user_{user}"):
                    st.session_state.current_chat_id = get_dm_id(current_user, user)
                    st.session_state.current_chat_name = user
                    # На мобилках sidebar закроется автоматически при смене страницы (или нажатии кнопки, если добавить логику, но Streamlit делает это сам)
                    st.rerun()

    # ОСНОВНОЙ КОНТЕЙНЕР (Чат)
    chat_id = st.session_state.current_chat_id
    
    if not chat_id:
        st.info("👈 Выберите пользователя в меню слева (на мобильном телефоне откройте боковую панель в левом верхнем углу), чтобы начать диалог.")
    else:
        # Шапка чата с новыми кнопками
        head_col1, head_col2, head_col3 = st.columns([6, 2, 2], vertical_alignment="center")
        with head_col1:
            st.subheader(f"Чат с {st.session_state.current_chat_name}")
        with head_col2:
            if st.button("Профиль", icon=":material/person:", use_container_width=True):
                view_profile_dialog(st.session_state.current_chat_name)
        with head_col3:
            if st.button("Очистить", icon=":material/delete:", use_container_width=True):
                clear_chat_dialog(chat_id)
        
        @st.fragment(run_every="2s")
        def show_messages(c_id):
            messages = db["messages"].get(c_id, [])
            if not messages:
                st.caption("Здесь пока нет сообщений. Напишите что-нибудь!")
                return
                
            for msg in messages:
                avatar_data = db["users"].get(msg["author"], {}).get("avatar")
                
                # Обработка ошибки битой аватарки в чате
                avatar_img = None
                if avatar_data:
                    try:
                        avatar_img = io.BytesIO(base64.b64decode(avatar_data))
                    except Exception:
                        pass
                
                with st.chat_message(msg["author"], avatar=avatar_img):
                    if msg.get("reply_to"):
                        parent = next((m for m in messages if m["id"] == msg["reply_to"]), None)
                        if parent:
                            st.caption(f":material/reply: В ответ **{parent['author']}**: _{parent['content'][:40] if parent['type'] == 'text' else '[Медиафайл]'}..._")
                    
                    time_text = f"**{msg['author']}** • {msg['time']}"
                    if msg.get("edited"): time_text += " *(изменено)*"
                    st.caption(time_text)
                    
                    # Рендер контента в зависимости от типа
                    if msg.get("type", "text") == "text":
                        st.write(msg["content"])
                    else:
                        try:
                            media_bytes = base64.b64decode(msg["content"])
                            if msg["type"] == "image":
                                st.image(io.BytesIO(media_bytes), width=300, border=True)
                            elif msg["type"] == "video":
                                st.video(io.BytesIO(media_bytes))
                            elif msg["type"] == "audio":
                                st.audio(io.BytesIO(media_bytes))
                        except Exception:
                            st.error("Ошибка загрузки медиафайла")
                            
                    # Кнопки действий
                    act_col1, act_col2, act_col3, _ = st.columns([1, 1, 1, 15])
                    with act_col1:
                        st.button("", icon=":material/reply:", type="tertiary", help="Ответить", key=f"r_{msg['id']}", on_click=set_action, args=("reply", msg["id"]))
                    if msg["author"] == current_user:
                        if msg.get("type", "text") == "text":
                            with act_col2:
                                st.button("", icon=":material/edit:", type="tertiary", help="Редактировать", key=f"e_{msg['id']}", on_click=set_action, args=("edit", msg["id"]))
                        with act_col3:
                            st.button("", icon=":material/delete:", type="tertiary", help="Удалить", key=f"d_{msg['id']}", on_click=delete_msg, args=(c_id, msg["id"]))

        # Контейнер для сообщений
        with st.container(height=500, border=True):
            show_messages(chat_id)
        
        editing_id = st.session_state.editing_msg
        replying_id = st.session_state.replying_to
        
        if editing_id:
            msg_to_edit = next((m for m in db["messages"].get(chat_id, []) if m["id"] == editing_id), None)
            if msg_to_edit:
                st.info(":material/edit: **Редактирование сообщения**")
                edit_col1, edit_col2, edit_col3 = st.columns([6, 1, 1])
                with edit_col1:
                    new_text = st.text_input("Новый текст", value=msg_to_edit["content"], label_visibility="collapsed")
                with edit_col2:
                    if st.button("Сохранить", type="primary", use_container_width=True):
                        msg_to_edit["content"] = new_text
                        msg_to_edit["edited"] = True
                        st.session_state.editing_msg = None
                        save_db()
                        st.rerun()
                with edit_col3:
                    if st.button("Отмена", use_container_width=True):
                        st.session_state.editing_msg = None
                        st.rerun()
        else:
            if replying_id:
                parent = next((m for m in db["messages"].get(chat_id, []) if m["id"] == replying_id), None)
                if parent:
                    preview = parent['content'][:50] if parent.get('type','text') == 'text' else '[Медиафайл]'
                    st.info(f":material/reply: Ответ для **{parent['author']}**: _{preview}_")
                    if st.button("Отменить", icon=":material/close:", key="btn_cancel_reply", type="tertiary"):
                        st.session_state.replying_to = None
                        st.rerun()
            
            inp_col1, inp_col2 = st.columns([1, 12], vertical_alignment="bottom")
            with inp_col1:
                with st.popover("📎", help="Прикрепить файл (фото, видео, аудио)"):
                    media_file = st.file_uploader("Загрузить файл", type=["png", "jpg", "jpeg", "mp4", "mp3", "wav"], label_visibility="collapsed")
                    if media_file and st.button("Отправить", icon=":material/send:", type="primary", use_container_width=True):
                        if chat_id not in db["messages"]: db["messages"][chat_id] = []
                        
                        # Определяем тип файла по расширению
                        ext = media_file.name.split('.')[-1].lower()
                        if ext in ['png', 'jpg', 'jpeg']: m_type = "image"
                        elif ext in ['mp4']: m_type = "video"
                        elif ext in ['mp3', 'wav']: m_type = "audio"
                        else: m_type = "image"
                        
                        b64_data = base64.b64encode(media_file.read()).decode('utf-8')
                        db["messages"][chat_id].append({
                            "id": str(uuid.uuid4()),
                            "author": current_user,
                            "type": m_type,
                            "content": b64_data,
                            "time": datetime.now().strftime("%H:%M"),
                            "reply_to": replying_id,
                            "edited": False
                        })
                        st.session_state.replying_to = None
                        save_db()
                        st.rerun()
                        
            with inp_col2:
                text_input = st.chat_input("Напишите сообщение...")
                if text_input:
                    if chat_id not in db["messages"]: db["messages"][chat_id] = []
                    db["messages"][chat_id].append({
                        "id": str(uuid.uuid4()),
                        "author": current_user,
                        "type": "text",
                        "content": text_input,
                        "time": datetime.now().strftime("%H:%M"),
                        "reply_to": replying_id,
                        "edited": False
                    })
                    st.session_state.replying_to = None
                    save_db()
                    st.rerun()
