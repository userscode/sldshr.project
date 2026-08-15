import streamlit as st
import os
import json
import uuid
import tempfile
import hashlib
from datetime import datetime
from huggingface_hub import HfApi, hf_hub_download
from huggingface_hub.utils import EntryNotFoundError

# --- НАСТРОЙКИ STREAMLIT И ЛИМИТОВ (до 200 МБ) ---
def setup_streamlit_config():
    config_dir = ".streamlit"
    config_file = f"{config_dir}/config.toml"
    if not os.path.exists(config_dir):
        os.makedirs(config_dir)
    if not os.path.exists(config_file):
        with open(config_file, "w") as f:
            f.write("[server]\nmaxUploadSize = 200\n")
            
setup_streamlit_config()

st.set_page_config(page_title="CloudChat", page_icon="💬", layout="centered")

# --- СТИЛИ ДЛЯ ИДЕАЛЬНОГО UI ---
# Эти стили исправляют баги с огромными видео/фото и делают интерфейс "мессенджером"
st.markdown("""
<style>
    #MainMenu {visibility: hidden;}
    header {visibility: hidden;}
    footer {visibility: hidden;}
    
    /* Ограничение размеров медиа в чате, чтобы не ломался UI */
    [data-testid="stChatMessage"] img, 
    [data-testid="stChatMessage"] video {
        max-height: 300px !important;
        max-width: 100% !important;
        width: auto !important;
        border-radius: 12px;
        object-fit: cover;
        margin-top: 8px;
        box-shadow: 0 4px 12px rgba(0,0,0,0.1);
    }
    
    /* Красивые контейнеры комнат */
    .room-card {
        padding: 16px;
        border-radius: 16px;
        border: 1px solid #e2e8f0;
        background: #f8fafc;
        margin-bottom: 12px;
        transition: transform 0.2s;
    }
    [data-theme="dark"] .room-card {
        background: #1e293b;
        border-color: #334155;
    }
    
    /* Скрытие дефолтной кнопки загрузки файлов, если хотим кастомный UI */
    .stFileUploader > div > div > button {
        border-radius: 12px;
    }
</style>
""", unsafe_allow_html=True)

# --- ИНИЦИАЛИЗАЦИЯ HUGGING FACE ---
HF_TOKEN = st.secrets.get("HF_TOKEN", None)
HF_REPO_ID = st.secrets.get("HF_REPO_ID", None)

if not HF_TOKEN or not HF_REPO_ID:
    st.error("⚠️ Настройте HF_TOKEN и HF_REPO_ID в Secrets.")
    st.stop()

api = HfApi(token=HF_TOKEN)

# --- БАЗА ДАННЫХ И ХЭШИРОВАНИЕ ---
def hash_key(key: str) -> str:
    """Хэширует ключ доступа для безопасного хранения (SHA-256)"""
    return hashlib.sha256(key.encode('utf-8')).hexdigest()

@st.cache_data(ttl=2) # Кратковременный кэш для быстрой работы
def load_db():
    try:
        db_path = hf_hub_download(
            repo_id=HF_REPO_ID, 
            filename="chat_database.json", 
            repo_type="dataset", 
            token=HF_TOKEN
        )
        with open(db_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except EntryNotFoundError:
        return {"users": {}, "rooms": {}, "messages": {}}
    except Exception:
        return {"users": {}, "rooms": {}, "messages": {}}

def save_db(db_data):
    with tempfile.NamedTemporaryFile(mode="w", delete=False, encoding="utf-8") as tmp:
        json.dump(db_data, tmp, ensure_ascii=False, indent=2)
        tmp_path = tmp.name
    
    api.upload_file(
        path_or_fileobj=tmp_path,
        path_in_repo="chat_database.json",
        repo_id=HF_REPO_ID,
        repo_type="dataset"
    )
    os.remove(tmp_path)
    load_db.clear()

def safe_db_update(update_fn):
    """Безопасное обновление БД (стягиваем свежую, обновляем, заливаем)"""
    db = load_db()
    update_fn(db)
    save_db(db)

# --- СЕССИИ И НАВИГАЦИЯ ---
if "user_hash" not in st.session_state:
    st.session_state.user_hash = None
if "user_name" not in st.session_state:
    st.session_state.user_name = None
if "current_room" not in st.session_state:
    st.session_state.current_room = None

# --- ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ---
def get_file_type(filename):
    ext = filename.split('.')[-1].lower()
    if ext in ['jpg', 'jpeg', 'png', 'gif', 'webp']: return 'image'
    if ext in ['mp4', 'mov', 'webm']: return 'video'
    if ext in ['mp3', 'wav', 'ogg']: return 'audio'
    return 'document'

# --- 1. ЭКРАН АВТОРИЗАЦИИ И РЕГИСТРАЦИИ ---
if not st.session_state.user_hash:
    st.title("💬 CloudChat")
    st.markdown("Защищенный мессенджер с облачным хранением файлов.")
    
    tab_login, tab_register = st.tabs(["🔑 Войти по ключу", "📝 Создать аккаунт"])
    
    with tab_register:
        st.subheader("Новый аккаунт")
        new_name = st.text_input("Ваше имя (Никнейм)", placeholder="Например: Алекс")
        if st.button("Сгенерировать ключ доступа", type="primary"):
            if not new_name.strip():
                st.error("Введите имя!")
            else:
                raw_key = f"CC-{uuid.uuid4().hex[:12].upper()}"
                hashed = hash_key(raw_key)
                
                def add_user(db):
                    db["users"][hashed] = {
                        "name": new_name.strip(),
                        "created": datetime.now().strftime("%d.%m.%Y %H:%M")
                    }
                safe_db_update(add_user)
                
                st.success("✅ Аккаунт создан!")
                st.info(f"**Ваш ключ доступа:** `{raw_key}`\n\n⚠️ Скопируйте и сохраните его. Это ваш логин и пароль. Восстановить его невозможно!")
                
    with tab_login:
        st.subheader("Вход в систему")
        login_key = st.text_input("Введите ваш ключ доступа", type="password")
        if st.button("Войти"):
            if not login_key:
                st.error("Введите ключ!")
            else:
                db = load_db()
                hashed = hash_key(login_key.strip())
                if hashed in db["users"]:
                    st.session_state.user_hash = hashed
                    st.session_state.user_name = db["users"][hashed]["name"]
                    st.rerun()
                else:
                    st.error("❌ Неверный ключ доступа. Аккаунт не найден.")
    st.stop()

# --- 2. ГЛАВНОЕ МЕНЮ (СПИСОК КОМНАТ) ---
if not st.session_state.current_room:
    col1, col2 = st.columns([3, 1])
    with col1:
        st.title(f"Привет, {st.session_state.user_name}! 👋")
    with col2:
        if st.button("🚪 Выйти", use_container_width=True):
            st.session_state.user_hash = None
            st.session_state.user_name = None
            st.rerun()
            
    st.divider()
    
    tab_rooms, tab_create, tab_join = st.tabs(["💬 Мои комнаты", "➕ Создать комнату", "🔗 Войти по коду"])
    
    db = load_db()
    
    with tab_rooms:
        my_rooms = {code: data for code, data in db["rooms"].items() if st.session_state.user_name in data.get("participants", [])}
        
        if not my_rooms:
            st.info("Вы пока не состоите ни в одной комнате. Создайте новую или присоединитесь по коду!")
        else:
            for code, room in my_rooms.items():
                st.markdown(f"""
                <div class="room-card">
                    <h3>{room.get('avatar', '📁')} {room['name']}</h3>
                    <p style="color: gray; margin-bottom: 5px;">{room['description']}</p>
                    <p style="font-size: 12px;">Участников: {len(room.get('participants', []))}</p>
                </div>
                """, unsafe_allow_html=True)
                
                cols = st.columns([1, 1, 2])
                if cols[0].button("Войти", key=f"enter_{code}", type="primary"):
                    st.session_state.current_room = code
                    st.rerun()
                cols[1].code(code, language="text")
                st.write("") # Отступ
                
    with tab_create:
        room_name = st.text_input("Название комнаты", max_chars=50)
        room_desc = st.text_area("Описание", max_chars=200)
        room_avatar = st.selectbox("Аватарка", ["📁", "🔥", "🚀", "💡", "🎮", "🎵", "💼", "🍕", "❤️"])
        
        if st.button("Создать комнату", type="primary"):
            if not room_name:
                st.error("Введите название комнаты!")
            else:
                room_code = uuid.uuid4().hex[:10].upper() # 10 символов
                
                def add_room(db_data):
                    db_data["rooms"][room_code] = {
                        "name": room_name,
                        "description": room_desc,
                        "avatar": room_avatar,
                        "owner": st.session_state.user_name,
                        "participants": [st.session_state.user_name]
                    }
                    db_data["messages"][room_code] = []
                
                safe_db_update(add_room)
                st.success(f"Комната создана! Код для приглашения: **{room_code}**")
                
    with tab_join:
        join_code = st.text_input("Введите 10-значный код комнаты").upper().strip()
        if st.button("Присоединиться"):
            if join_code in db["rooms"]:
                if st.session_state.user_name not in db["rooms"][join_code]["participants"]:
                    def join_room(db_data):
                        db_data["rooms"][join_code]["participants"].append(st.session_state.user_name)
                    safe_db_update(join_room)
                
                st.session_state.current_room = join_code
                st.rerun()
            else:
                st.error("❌ Комната с таким кодом не найдена!")
    st.stop()


# --- 3. ЧАТ КОМНАТЫ ---
room_code = st.session_state.current_room
db = load_db()

# Если комната была удалена (защита)
if room_code not in db["rooms"]:
    st.warning("Эта комната больше не существует.")
    if st.button("Вернуться"):
        st.session_state.current_room = None
        st.rerun()
    st.stop()

room_info = db["rooms"][room_code]

# Шапка комнаты
col_back, col_info, col_code = st.columns([1, 6, 2])
with col_back:
    if st.button("⬅ Назад"):
        st.session_state.current_room = None
        st.rerun()
with col_info:
    st.markdown(f"### {room_info.get('avatar', '📁')} {room_info['name']}")
    st.caption(f"{room_info['description']} • Участники: {', '.join(room_info.get('participants', []))}")
with col_code:
    st.code(room_code, language="text")

st.divider()

# ФРАГМЕНТ: Автообновление чата каждые 3 секунды
@st.fragment(run_every="3s")
def render_chat():
    current_db = load_db()
    messages = current_db["messages"].get(room_code, [])
    
    if not messages:
        st.info("В этой комнате пока нет сообщений.")
    
    for msg in messages:
        # Определяем аватар: сам пользователь - другой аватар
        is_me = (msg["author"] == st.session_state.user_name)
        avatar = "👤" if is_me else "💬"
        
        with st.chat_message(msg["author"], avatar=avatar):
            # Шапка сообщения
            st.markdown(f"**{msg['author']}**  •  <span style='font-size:0.8em; color:gray;'>{msg['timestamp']}</span>", unsafe_allow_html=True)
            
            # Текст
            if msg["text"]:
                st.write(msg["text"])
                
            # Файлы (если есть)
            if msg.get("files"):
                images = [f for f in msg["files"] if f["type"] == "image"]
                videos = [f for f in msg["files"] if f["type"] == "video"]
                docs = [f for f in msg["files"] if f["type"] not in ["image", "video"]]
                
                # Изображения (в колонках для компактности)
                if images:
                    img_cols = st.columns(min(len(images), 3))
                    for idx, img in enumerate(images):
                        with img_cols[idx % 3]:
                            try:
                                path = hf_hub_download(repo_id=HF_REPO_ID, filename=f"uploads/{img['filename']}", repo_type="dataset", token=HF_TOKEN)
                                st.image(path)
                            except:
                                st.error("Фото недоступно")
                
                # Видео
                for vid in videos:
                    try:
                        path = hf_hub_download(repo_id=HF_REPO_ID, filename=f"uploads/{vid['filename']}", repo_type="dataset", token=HF_TOKEN)
                        st.video(path)
                    except:
                        st.error("Видео недоступно")
                
                # Документы и аудио
                for doc in docs:
                    try:
                        path = hf_hub_download(repo_id=HF_REPO_ID, filename=f"uploads/{doc['filename']}", repo_type="dataset", token=HF_TOKEN)
                        with open(path, "rb") as f:
                            st.download_button(
                                label=f"📎 {doc['original_name']}",
                                data=f,
                                file_name=doc['original_name'],
                                key=f"dl_{msg['id']}_{doc['filename']}"
                            )
                    except:
                        pass
            
            # Кнопка удаления (только для своих сообщений)
            if is_me:
                if st.button("Удалить 🗑️", key=f"del_{msg['id']}", size="small", help="Удалить сообщение и файлы"):
                    # Логика удаления
                    def delete_msg(db_data):
                        # Находим сообщение
                        target = next((m for m in db_data["messages"][room_code] if m["id"] == msg["id"]), None)
                        if target:
                            # 1. Удаляем файлы с Hugging Face
                            for f_info in target.get("files", []):
                                try:
                                    api.delete_file(
                                        path_in_repo=f"uploads/{f_info['filename']}",
                                        repo_id=HF_REPO_ID,
                                        repo_type="dataset"
                                    )
                                except Exception:
                                    pass # Игнорируем если файла уже нет
                            # 2. Удаляем из массива
                            db_data["messages"][room_code].remove(target)
                    
                    safe_db_update(delete_msg)
                    st.rerun()

# Отрисовываем чат (он будет сам обновляться)
chat_container = st.container(height=500)
with chat_container:
    render_chat()

# --- ФОРМА ОТПРАВКИ СООБЩЕНИЯ (загрузка файлов происходит здесь) ---
st.write("") # Отступ
with st.expander("📎 Написать сообщение и прикрепить файлы (до 200МБ)", expanded=True):
    msg_text = st.text_area("Текст сообщения", height=100, label_visibility="collapsed", placeholder="Напишите сообщение...")
    msg_files = st.file_uploader("Файлы", accept_multiple_files=True, label_visibility="collapsed")
    
    if st.button("✈️ Отправить", type="primary", use_container_width=True):
        if not msg_text.strip() and not msg_files:
            st.error("Сообщение не может быть пустым!")
        else:
            with st.spinner("Отправка..."):
                uploaded_data = []
                
                # Обработка файлов в момент отправки
                if msg_files:
                    for file in msg_files:
                        ext = file.name.split('.')[-1]
                        unique_filename = f"{uuid.uuid4().hex}.{ext}"
                        
                        # Сохраняем временно и грузим в HF
                        with tempfile.NamedTemporaryFile(delete=False, suffix=f".{ext}") as tmp:
                            tmp.write(file.getbuffer())
                            tmp_path = tmp.name
                        
                        api.upload_file(
                            path_or_fileobj=tmp_path,
                            path_in_repo=f"uploads/{unique_filename}",
                            repo_id=HF_REPO_ID,
                            repo_type="dataset"
                        )
                        os.remove(tmp_path)
                        
                        uploaded_data.append({
                            "original_name": file.name,
                            "filename": unique_filename,
                            "type": get_file_type(file.name)
                        })
                
                # Формируем объект сообщения
                new_message = {
                    "id": uuid.uuid4().hex,
                    "author": st.session_state.user_name,
                    "text": msg_text.strip(),
                    "files": uploaded_data,
                    "timestamp": datetime.now().strftime("%H:%M")
                }
                
                # Сохраняем в БД
                def add_msg(db_data):
                    db_data["messages"][room_code].append(new_message)
                
                safe_db_update(add_msg)
                st.rerun() # Перезагрузка для очистки инпутов и обновления чата
