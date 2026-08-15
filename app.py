import streamlit as st
import hashlib
import random
import string
from datetime import datetime
import json
import base64
import threading
import uuid
import io
from huggingface_hub import HfApi, hf_hub_download

st.set_page_config(page_title="Мессенджер", page_icon="💬", layout="wide")

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
        print(f"База не найдена или ошибка загрузки ({e}). Создана новая пустая БД.")
        db = {
            "users": {},      
            "messages": {},   
            "groups": {},
            "sessions": {}
        }
        
    # МИГРАЦИИ (обновление старых данных под новый формат)
    if "sessions" not in db:
        db["sessions"] = {}
        
    # Обновляем профили пользователей
    for u, data in db["users"].items():
        if isinstance(data, str): # Если это старый формат (просто строка пароля)
            db["users"][u] = {"password": data, "bio": "", "avatar": None}
            
    # Обновляем сообщения
    for c_id, msgs in db["messages"].items():
        for m in msgs:
            if "id" not in m:
                m["id"] = str(uuid.uuid4())
                m["reply_to"] = None
                m["edited"] = False
                
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
                print(f"Ошибка выгрузки: {e}")
                
    threading.Thread(target=upload).start()

def make_hash(password):
    return hashlib.sha256(str.encode(password)).hexdigest()

def generate_group_code():
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))

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
    elif action == "cancel":
        st.session_state.replying_to = None
        st.session_state.editing_msg = None

def delete_msg(c_id, msg_id):
    db["messages"][c_id] = [m for m in db["messages"][c_id] if m["id"] != msg_id]
    st.session_state.replying_to = None
    st.session_state.editing_msg = None
    save_db()

if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
    st.session_state.username = ""
    st.session_state.current_chat_id = None
    st.session_state.current_chat_name = None
    st.session_state.replying_to = None
    st.session_state.editing_msg = None
    st.session_state.last_chat_id = None

# Проверка токена сессии в URL (для автоматического входа)
if not st.session_state.logged_in:
    url_token = st.query_params.get("session")
    if url_token and url_token in db.get("sessions", {}):
        st.session_state.logged_in = True
        st.session_state.username = db["sessions"][url_token]

# Очистка состояний ответа/редактирования при смене чата
if st.session_state.current_chat_id != st.session_state.last_chat_id:
    st.session_state.replying_to = None
    st.session_state.editing_msg = None
    st.session_state.last_chat_id = st.session_state.current_chat_id

@st.dialog("⚙️ Настройки профиля")
def profile_dialog():
    user_data = db["users"][st.session_state.username]
    new_bio = st.text_input("О себе (статус)", value=user_data.get("bio", ""))
    new_avatar = st.file_uploader("Загрузить аватарку (до 2МБ)", type=["png", "jpg", "jpeg"])
    
    if st.button("Сохранить изменения", use_container_width=True):
        user_data["bio"] = new_bio
        if new_avatar:
            user_data["avatar"] = base64.b64encode(new_avatar.read()).decode('utf-8')
        save_db()
        st.rerun()

if not st.session_state.logged_in:
    col1, col2, col3 = st.columns([1, 1, 1])
    with col2:
        st.title("💬 Мессенджер")
        tab1, tab2 = st.tabs(["Вход", "Регистрация"])
        
        with tab1:
            l_user = st.text_input("Никнейм", key="l_user")
            l_pass = st.text_input("Пароль", type="password", key="l_pass")
            if st.button("Войти", use_container_width=True):
                if l_user in db["users"] and db["users"][l_user]["password"] == make_hash(l_pass):
                    # Создаем токен сессии и сохраняем его
                    session_token = uuid.uuid4().hex
                    db["sessions"][session_token] = l_user
                    st.query_params["session"] = session_token
                    save_db()
                    
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
                    st.error("Никнейм уже занят")
                else:
                    db["users"][r_user] = {"password": make_hash(r_pass), "bio": "", "avatar": None}
                    save_db()
                    st.success("Аккаунт создан! Теперь выполните вход.")

else:
    col_menu, col_chat = st.columns([1, 3])
    current_user = st.session_state.username
    user_info = db["users"][current_user]
    
    with col_menu:
        # Отображение профиля
        prof_col1, prof_col2 = st.columns([1, 3])
        with prof_col1:
            if user_info.get("avatar"):
                st.image(io.BytesIO(base64.b64decode(user_info["avatar"])), use_column_width=True)
            else:
                st.markdown("<h1>👤</h1>", unsafe_allow_html=True)
        with prof_col2:
            st.subheader(f"{current_user}")
            if user_info.get("bio"):
                st.caption(f"_{user_info['bio']}_")
                
        if st.button("⚙️ Настроить профиль", use_container_width=True):
            profile_dialog()
            
        if st.button("🚪 Выйти", use_container_width=True):
            # Удаляем сессию
            token = st.query_params.get("session")
            if token in db["sessions"]:
                del db["sessions"][token]
                save_db()
            st.query_params.clear()
            st.session_state.logged_in = False
            st.session_state.username = ""
            st.session_state.current_chat_id = None
            st.rerun()
            
        st.divider()
        
        # Секция "Группы"
        st.markdown("### 👥 Мои группы")
        with st.expander("➕ Создать секретную группу"):
            new_group_name = st.text_input("Название группы")
            if st.button("Создать"):
                if new_group_name:
                    code = generate_group_code()
                    db["groups"][code] = {"name": new_group_name, "members": [current_user]}
                    save_db()
                    st.success(f"Создано! Код: `{code}`")
                
        with st.expander("🔑 Войти по коду"):
            join_code = st.text_input("8-значный код").upper()
            if st.button("Присоединиться"):
                if join_code in db["groups"]:
                    if current_user not in db["groups"][join_code]["members"]:
                        db["groups"][join_code]["members"].append(current_user)
                        save_db()
                    st.success("Вы добавлены в группу!")
                    st.rerun()
                else:
                    st.error("Группа не найдена")

        # Список групп
        has_groups = False
        for code, group_data in db["groups"].items():
            if current_user in group_data["members"]:
                has_groups = True
                if st.button(f"🛡 {group_data['name']}", key=f"btn_grp_{code}", use_container_width=True):
                    st.session_state.current_chat_id = f"group_{code}"
                    st.session_state.current_chat_name = group_data['name']
                    st.rerun()
        if not has_groups:
            st.caption("Нет групп")

        st.divider()

        # Секция "Личные сообщения"
        st.markdown("### 💬 Пользователи")
        other_users = [u for u in db["users"].keys() if u != current_user]
        
        if not other_users:
            st.caption("Пока никто кроме вас не зарегистрировался.")
        else:
            for user in other_users:
                if st.button(f"👤 {user}", key=f"btn_user_{user}", use_container_width=True):
                    st.session_state.current_chat_id = get_dm_id(current_user, user)
                    st.session_state.current_chat_name = user
                    st.rerun()

    with col_chat:
        chat_id = st.session_state.current_chat_id
        
        if not chat_id:
            st.info("👈 Выберите чат в меню слева или создайте группу.")
        else:
            is_group = chat_id.startswith("group_")
            header_text = f"Чат с: {st.session_state.current_chat_name}"
            if is_group:
                code = chat_id.split("_")[1]
                header_text = f"Группа: {st.session_state.current_chat_name} (Код: `{code}`)"
            
            st.subheader(header_text)
            
            @st.fragment(run_every="2s")
            def show_messages(c_id):
                messages = db["messages"].get(c_id, [])
                for msg in messages:
                    # Подготовка аватарки
                    avatar_data = db["users"].get(msg["author"], {}).get("avatar")
                    avatar_img = io.BytesIO(base64.b64decode(avatar_data)) if avatar_data else "👤"
                    
                    with st.chat_message(msg["author"], avatar=avatar_img):
                        # Если это ответ на сообщение
                        if msg.get("reply_to"):
                            parent = next((m for m in messages if m["id"] == msg["reply_to"]), None)
                            if parent:
                                st.caption(f"↪ В ответ на **{parent['author']}**: _{parent['content'][:40]}..._")
                        
                        # Информация и текст
                        time_text = f"**{msg['author']}** • {msg['time']}"
                        if msg.get("edited"):
                            time_text += " *(изменено)*"
                        st.caption(time_text)
                        
                        if msg["type"] == "text":
                            st.write(msg["content"])
                        elif msg["type"] == "image":
                            try:
                                img_bytes = base64.b64decode(msg["content"])
                                st.image(img_bytes, width=300)
                            except Exception:
                                st.error("Ошибка картинки")
                                
                        # Кнопки взаимодействия (Ответить, Изменить, Удалить)
                        act_col1, act_col2, act_col3, _ = st.columns([1, 1, 1, 10])
                        with act_col1:
                            st.button("↩️", key=f"r_{msg['id']}", help="Ответить", on_click=set_action, args=("reply", msg["id"]))
                        if msg["author"] == current_user:
                            if msg["type"] == "text": # Редактируем только текст
                                with act_col2:
                                    st.button("✏️", key=f"e_{msg['id']}", help="Редактировать", on_click=set_action, args=("edit", msg["id"]))
                            with act_col3:
                                st.button("🗑", key=f"d_{msg['id']}", help="Удалить", on_click=delete_msg, args=(c_id, msg["id"]))

            # Контейнер для сообщений
            with st.container(height=500):
                show_messages(chat_id)
            
            editing_id = st.session_state.editing_msg
            replying_id = st.session_state.replying_to
            
            if editing_id:
                # Режим редактирования
                msg_to_edit = next((m for m in db["messages"].get(chat_id, []) if m["id"] == editing_id), None)
                if msg_to_edit:
                    st.info("✏️ **Редактирование сообщения**")
                    edit_col1, edit_col2, edit_col3 = st.columns([6, 1, 1])
                    with edit_col1:
                        new_text = st.text_input("Новый текст", value=msg_to_edit["content"], label_visibility="collapsed")
                    with edit_col2:
                        if st.button("Сохранить", use_container_width=True):
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
                # Режим ответа или обычный ввод
                if replying_id:
                    parent = next((m for m in db["messages"].get(chat_id, []) if m["id"] == replying_id), None)
                    if parent:
                        st.info(f"↩️ Ответ для **{parent['author']}**: _{parent['content'][:50]}_")
                        if st.button("❌ Отменить ответ", key="btn_cancel_reply"):
                            st.session_state.replying_to = None
                            st.rerun()
                
                # Стандартная форма отправки
                inp_col1, inp_col2 = st.columns([1, 8])
                with inp_col1:
                    with st.popover("📎 Фото"):
                        img_file = st.file_uploader("Загрузить", type=["png", "jpg", "jpeg"], label_visibility="collapsed")
                        if img_file and st.button("Отправить фото"):
                            if chat_id not in db["messages"]: db["messages"][chat_id] = []
                            b64_img = base64.b64encode(img_file.read()).decode('utf-8')
                            db["messages"][chat_id].append({
                                "id": str(uuid.uuid4()),
                                "author": current_user,
                                "type": "image",
                                "content": b64_img,
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
