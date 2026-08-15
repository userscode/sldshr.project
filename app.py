import streamlit as st
import hashlib
import random
import string
from datetime import datetime
import json
import base64
import threading
from huggingface_hub import HfApi, hf_hub_download

# Включаем широкий экран для ПК-интерфейса
st.set_page_config(page_title="Мессенджер", page_icon="💬", layout="wide")

# Настройки для базы данных
db_lock = threading.Lock()

# Имитация базы данных
@st.cache_resource
def get_database():
    try:
        # Попытка скачать существующую базу из датасета
        repo_id = st.secrets["HF_REPO_ID"]
        token = st.secrets["HF_TOKEN"]
        file_path = hf_hub_download(repo_id=repo_id, filename="database.json", repo_type="dataset", token=token)
        with open(file_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        print(f"База не найдена или ошибка загрузки ({e}). Создана новая пустая БД.")
        return {
            "users": {},      # {"никнейм": "хэш_пароля"}
            "messages": {},   # {"id_чата": [{"author": "ник", "type": "text/image", "content": "...", "time": "..."}]}
            "groups": {}      # {"8значный_код": {"name": "Название", "members": ["ник1", "ник2"]}}
        }

db = get_database()

def save_db():
    """Фоновое сохранение базы данных в HF Dataset (чтобы не тормозить интерфейс)"""
    try:
        repo_id = st.secrets.get("HF_REPO_ID")
        token = st.secrets.get("HF_TOKEN")
        if not repo_id or not token:
            return
    except Exception:
        return

    def upload():
        with db_lock:
            try:
                api = HfApi(token=token)
                # Сохраняем во временный файл
                with open("temp_db.json", "w", encoding="utf-8") as f:
                    json.dump(db, f, ensure_ascii=False)
                # Отправляем в Dataset
                api.upload_file(
                    path_or_fileobj="temp_db.json",
                    path_in_repo="database.json",
                    repo_id=repo_id,
                    repo_type="dataset",
                    commit_message="Auto-update database"
                )
            except Exception as e:
                print(f"Ошибка выгрузки в HF: {e}")
                
    threading.Thread(target=upload).start()

# Вспомогательные функции
def make_hash(password):
    return hashlib.sha256(str.encode(password)).hexdigest()

def generate_group_code():
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))

def get_dm_id(user1, user2):
    # Создаем уникальный ID для личной переписки (сортируем имена, чтобы A+B было тем же чатом, что и B+A)
    users = sorted([user1, user2])
    return f"dm_{users[0]}_{users[1]}"

# Инициализация сессии
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
    st.session_state.username = ""
    st.session_state.current_chat_id = None
    st.session_state.current_chat_name = None

# --- ЭКРАН АВТОРИЗАЦИИ ---
if not st.session_state.logged_in:
    col1, col2, col3 = st.columns([1, 1, 1])
    with col2:
        st.title("💬 Мессенджер")
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
                    st.error("Никнейм уже занят")
                else:
                    db["users"][r_user] = make_hash(r_pass)
                    save_db()
                    st.success("Аккаунт создан! Теперь выполните вход.")

# --- ОСНОВНОЙ ЭКРАН (ПК ИНТЕРФЕЙС) ---
else:
    # Разделяем экран на 2 части: меню слева (1 часть) и сам чат справа (3 части)
    col_menu, col_chat = st.columns([1, 3])
    
    current_user = st.session_state.username
    
    # ------------------ ЛЕВОЕ МЕНЮ ------------------
    with col_menu:
        st.subheader(f"👤 {current_user}")
        if st.button("Выйти", use_container_width=True, size="small"):
            st.session_state.logged_in = False
            st.session_state.username = ""
            st.session_state.current_chat_id = None
            st.rerun()
            
        st.divider()
        
        # Секция "Группы"
        st.markdown("### 👥 Мои группы")
        
        # Кнопки для управления группами (спрятаны в "аккордеоны")
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

        # Вывод списка групп пользователя
        has_groups = False
        for code, group_data in db["groups"].items():
            if current_user in group_data["members"]:
                has_groups = True
                if st.button(f"🛡 {group_data['name']}", key=f"btn_grp_{code}", use_container_width=True):
                    st.session_state.current_chat_id = f"group_{code}"
                    st.session_state.current_chat_name = group_data['name']
                    st.rerun()
        
        if not has_groups:
            st.caption("Вы не состоите в группах")

        st.divider()

        # Секция "Личные сообщения"
        st.markdown("### 💬 Чаты (Пользователи)")
        other_users = [u for u in db["users"].keys() if u != current_user]
        
        if not other_users:
            st.caption("Пока никто кроме вас не зарегистрировался.")
        else:
            for user in other_users:
                if st.button(f"👤 {user}", key=f"btn_user_{user}", use_container_width=True):
                    st.session_state.current_chat_id = get_dm_id(current_user, user)
                    st.session_state.current_chat_name = user
                    st.rerun()

    # ------------------ ПРАВЫЙ БЛОК (ЧАТ) ------------------
    with col_chat:
        chat_id = st.session_state.current_chat_id
        
        if not chat_id:
            st.info("👈 Выберите чат в меню слева или создайте группу.")
        else:
            # Если это группа, показываем её код в заголовке, чтобы можно было поделиться
            is_group = chat_id.startswith("group_")
            header_text = f"Чат с: {st.session_state.current_chat_name}"
            if is_group:
                code = chat_id.split("_")[1]
                header_text = f"Группа: {st.session_state.current_chat_name} (Код: `{code}`)"
            
            st.subheader(header_text)
            
            # Функция для отрисовки сообщений (обновляется каждые 2 секунды)
            @st.fragment(run_every="2s")
            def show_messages(c_id):
                messages = db["messages"].get(c_id, [])
                for msg in messages:
                    with st.chat_message(msg["author"]):
                        st.caption(f"**{msg['author']}** • {msg['time']}")
                        if msg["type"] == "text":
                            st.write(msg["content"])
                        elif msg["type"] == "image":
                            # Декодируем картинку из Base64 формата
                            try:
                                img_bytes = base64.b64decode(msg["content"])
                                st.image(img_bytes, width=300)
                            except Exception:
                                st.error("Ошибка загрузки изображения")

            # Контейнер для сообщений с фиксированной высотой и прокруткой
            with st.container(height=500):
                show_messages(chat_id)
            
            # Форма отправки сообщения
            # Используем колонки, чтобы поместить кнопку загрузки картинки рядом с полем ввода
            inp_col1, inp_col2 = st.columns([1, 8])
            
            with inp_col1:
                # Всплывающее меню для отправки картинки
                with st.popover("📎 Фото"):
                    img_file = st.file_uploader("Загрузить", type=["png", "jpg", "jpeg"], label_visibility="collapsed")
                    if img_file and st.button("Отправить фото"):
                        if chat_id not in db["messages"]:
                            db["messages"][chat_id] = []
                        
                        # Кодируем байты в Base64 для сохранения в JSON
                        b64_img = base64.b64encode(img_file.read()).decode('utf-8')
                        db["messages"][chat_id].append({
                            "author": current_user,
                            "type": "image",
                            "content": b64_img,
                            "time": datetime.now().strftime("%H:%M")
                        })
                        save_db()
                        st.rerun()
                        
            with inp_col2:
                # Поле для ввода текста
                text_input = st.chat_input("Напишите сообщение...")
                if text_input:
                    if chat_id not in db["messages"]:
                        db["messages"][chat_id] = []
                    db["messages"][chat_id].append({
                        "author": current_user,
                        "type": "text",
                        "content": text_input,
                        "time": datetime.now().strftime("%H:%M")
                    })
                    save_db()
                    st.rerun()
