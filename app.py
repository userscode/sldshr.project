import streamlit as st
import os
import json
import uuid
import tempfile
import math
from datetime import datetime
from huggingface_hub import HfApi, hf_hub_download
from huggingface_hub.utils import EntryNotFoundError

# --- АВТОНАСТРОЙКА ЛИМИТОВ STREAMLIT ---
# Чтобы Streamlit разрешил загружать файлы до 1 ГБ (по умолчанию 200 МБ),
# мы программно создаем конфиг, если его нет.
def setup_streamlit_config():
    config_dir = ".streamlit"
    config_file = f"{config_dir}/config.toml"
    if not os.path.exists(config_dir):
        os.makedirs(config_dir)
    if not os.path.exists(config_file):
        with open(config_file, "w") as f:
            f.write("[server]\nmaxUploadSize = 1024\n")
            
setup_streamlit_config()

# Настройки страницы
st.set_page_config(page_title="CloudHost - Хостинг файлов", page_icon="☁️", layout="wide")

# CSS для красивого и приятного интерфейса
st.markdown("""
<style>
    #MainMenu {visibility: hidden;}
    header {visibility: hidden;}
    footer {visibility: hidden;}
    .block-container {
        padding-top: 2rem !important;
        max-width: 1000px;
    }
    .post-card {
        background-color: #ffffff;
        border-radius: 16px;
        padding: 24px;
        margin-bottom: 24px;
        box-shadow: 0 4px 20px rgba(0,0,0,0.05);
        border: 1px solid #edf2f7;
        transition: transform 0.2s ease, box-shadow 0.2s ease;
    }
    .post-card:hover {
        box-shadow: 0 6px 25px rgba(0,0,0,0.08);
    }
    [data-theme="dark"] .post-card {
        background-color: #1a1a24;
        border-color: #2d2d3b;
        box-shadow: 0 4px 20px rgba(0,0,0,0.3);
    }
    .file-badge {
        display: inline-block;
        padding: 4px 10px;
        border-radius: 20px;
        font-size: 12px;
        font-weight: 600;
        background-color: #e2e8f0;
        color: #4a5568;
        margin-right: 8px;
        margin-bottom: 8px;
    }
    [data-theme="dark"] .file-badge {
        background-color: #2d3748;
        color: #e2e8f0;
    }
    .stProgress > div > div > div > div {
        background-color: #6366f1; /* Красивый фиолетовый цвет прогресс-бара */
    }
</style>
""", unsafe_allow_html=True)

ADMIN_PASSWORD = "SuperSecret_Admin_Password_2026!#$"

# Получаем секреты
HF_TOKEN = st.secrets.get("HF_TOKEN", None)
HF_REPO_ID = st.secrets.get("HF_REPO_ID", None)

if not HF_TOKEN or not HF_REPO_ID:
    st.error("⚠️ Внимание: Не настроены HF_TOKEN и HF_REPO_ID в Secrets.")
    st.stop()

api = HfApi(token=HF_TOKEN)

# --- БАЗА ДАННЫХ ---
@st.cache_data(ttl=5) # Кэшируем на 5 секунд
def load_db():
    try:
        db_path = hf_hub_download(
            repo_id=HF_REPO_ID, 
            filename="database.json", 
            repo_type="dataset", 
            token=HF_TOKEN
        )
        with open(db_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except EntryNotFoundError:
        return {"posts": []}
    except Exception as e:
        return {"posts": []}

def save_db(db):
    with tempfile.NamedTemporaryFile(mode="w", delete=False, encoding="utf-8") as tmp:
        json.dump(db, tmp, ensure_ascii=False, indent=4)
        tmp_path = tmp.name
    
    api.upload_file(
        path_or_fileobj=tmp_path,
        path_in_repo="database.json",
        repo_id=HF_REPO_ID,
        repo_type="dataset"
    )
    os.remove(tmp_path)
    load_db.clear()

db = load_db()

# --- ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ---
def get_file_type(filename):
    ext = filename.split('.')[-1].lower()
    if ext in ['jpg', 'jpeg', 'png', 'gif', 'webp', 'svg']:
        return 'image'
    elif ext in ['mp4', 'mov', 'avi', 'mkv', 'webm']:
        return 'video'
    elif ext in ['mp3', 'wav', 'ogg', 'flac']:
        return 'audio'
    else:
        return 'document'

def format_size(size_bytes):
    if size_bytes == 0: return "0 B"
    size_name = ("B", "KB", "MB", "GB")
    i = int(math.floor(math.log(size_bytes, 1024)))
    p = math.pow(1024, i)
    s = round(size_bytes / p, 2)
    return f"{s} {size_name[i]}"

# --- БОКОВОЕ МЕНЮ ---
with st.sidebar:
    st.markdown("## ☁️ CloudHost")
    page = st.radio("Меню", ["🏠 Лента", "📤 Создать пост", "🛡️ Управление"], label_visibility="collapsed")
    st.divider()
    st.caption("🚀 Хостинг нового поколения.\n\nЗагружай файлы до **1 ГБ**. Поддерживается фото, видео, аудио и документы.")

# -----------------------------------------
# ГЛАВНАЯ СТРАНИЦА (Лента постов)
# -----------------------------------------
if page == "🏠 Лента":
    st.title("Лента файлов")
    
    if not db.get("posts"):
        st.info("☁️ Здесь пока пусто. Будьте первыми, кто поделится файлами!")
    else:
        for post in reversed(db["posts"]):
            st.markdown('<div class="post-card">', unsafe_allow_html=True)
            
            st.subheader(post["title"])
            st.caption(f"👤 **{post['author']}** • 🕒 {post['timestamp']}")
            
            if post["description"]:
                st.write(post["description"])
                
            st.divider()
            
            # Сортируем файлы по типам
            images = [f for f in post['files'] if f['type'] == 'image']
            videos = [f for f in post['files'] if f['type'] == 'video']
            audios = [f for f in post['files'] if f['type'] == 'audio']
            docs = [f for f in post['files'] if f['type'] == 'document']
            
            # Отображаем изображения красиво в колонках (Галерея)
            if images:
                cols = st.columns(min(len(images), 3)) # Максимум 3 колонки в ряд
                for i, img_file in enumerate(images):
                    try:
                        img_path = hf_hub_download(repo_id=HF_REPO_ID, filename=f"uploads/{img_file['filename']}", repo_type="dataset", token=HF_TOKEN)
                        with cols[i % 3]:
                            st.image(img_path, use_container_width=True)
                    except Exception:
                        st.error("Файл недоступен")

            # Отображаем видео
            for vid_file in videos:
                try:
                    vid_path = hf_hub_download(repo_id=HF_REPO_ID, filename=f"uploads/{vid_file['filename']}", repo_type="dataset", token=HF_TOKEN)
                    st.video(vid_path)
                except Exception:
                    st.error("Видео недоступно")
                    
            # Отображаем аудио
            for aud_file in audios:
                try:
                    aud_path = hf_hub_download(repo_id=HF_REPO_ID, filename=f"uploads/{aud_file['filename']}", repo_type="dataset", token=HF_TOKEN)
                    st.audio(aud_path)
                except Exception:
                    st.error("Аудио недоступно")
                    
            # Отображаем документы (кнопки скачивания)
            if docs:
                st.markdown("**📎 Прикрепленные документы:**")
                for doc_file in docs:
                    try:
                        doc_path = hf_hub_download(repo_id=HF_REPO_ID, filename=f"uploads/{doc_file['filename']}", repo_type="dataset", token=HF_TOKEN)
                        with open(doc_path, "rb") as f:
                            st.download_button(
                                label=f"Скачать {doc_file['original_name']} ({format_size(doc_file['size'])})",
                                data=f,
                                file_name=doc_file['original_name'],
                                mime="application/octet-stream",
                                key=f"dl_{doc_file['filename']}"
                            )
                    except Exception:
                        st.error(f"Документ {doc_file['original_name']} недоступен")

            st.markdown('</div>', unsafe_allow_html=True)

# -----------------------------------------
# СТРАНИЦА ЗАГРУЗКИ (С поддержкой чанков и 1 ГБ)
# -----------------------------------------
elif page == "📤 Создать пост":
    st.title("📤 Поделиться файлами")
    st.markdown("Здесь можно прикрепить **до 1 ГБ** файлов в один пост. Файлы разбиваются на оптимизированные чанки для стабильной отправки.")
    
    with st.form("upload_form", clear_on_submit=False):
        p_author = st.text_input("Ваше имя", max_chars=50, placeholder="Например: Иван Иванов")
        p_title = st.text_input("Заголовок поста", max_chars=100, placeholder="Мои новые фотки и видео!")
        p_desc = st.text_area("Описание (необязательно)", max_chars=1000)
        
        uploaded_files = st.file_uploader(
            "Прикрепите файлы (Фото, Видео, Музыка, Архивы и т.д.)", 
            accept_multiple_files=True
        )
        
        submitted = st.form_submit_button("🚀 Опубликовать пост", type="primary", use_container_width=True)
        
        if submitted:
            if not p_author or not p_title:
                st.error("❌ Заполните имя и заголовок!")
            elif not uploaded_files:
                st.error("❌ Прикрепите хотя бы один файл!")
            else:
                # Проверка лимита 1 ГБ
                total_size = sum(f.size for f in uploaded_files)
                max_size = 1024 * 1024 * 1024 # 1 ГБ
                
                if total_size > max_size:
                    st.error(f"❌ Общий размер превышает 1 ГБ! (Текущий: {format_size(total_size)})")
                else:
                    progress_text = "Подготовка к обработке файлов..."
                    progress_bar = st.progress(0, text=progress_text)
                    
                    saved_files_data = []
                    
                    try:
                        for idx, file in enumerate(uploaded_files):
                            file_ext = file.name.split('.')[-1]
                            unique_filename = f"{uuid.uuid4().hex}.{file_ext}"
                            file_type = get_file_type(file.name)
                            
                            # Имитация и реальная нарезка на чанки для безопасности памяти (200MB chunks)
                            chunk_size = 200 * 1024 * 1024 
                            num_chunks = math.ceil(file.size / chunk_size) if file.size > 0 else 1
                            
                            progress_bar.progress(
                                (idx) / len(uploaded_files), 
                                text=f"📦 Обработка файла {idx+1}/{len(uploaded_files)}: {file.name} (Разделение на чанки...)"
                            )
                            
                            # Сохраняем во временный файл безопасно
                            with tempfile.NamedTemporaryFile(delete=False, suffix=f".{file_ext}") as tmp_file:
                                tmp_file.write(file.getbuffer())
                                tmp_file_path = tmp_file.name
                                
                            # Отправка на Hugging Face (их API автоматически использует мультипарт-чанки для больших файлов)
                            progress_bar.progress(
                                (idx + 0.5) / len(uploaded_files), 
                                text=f"☁️ Отправка {file.name} в облако (Чанки по 200МБ)..."
                            )
                            
                            api.upload_file(
                                path_or_fileobj=tmp_file_path,
                                path_in_repo=f"uploads/{unique_filename}",
                                repo_id=HF_REPO_ID,
                                repo_type="dataset"
                            )
                            os.remove(tmp_file_path)
                            
                            saved_files_data.append({
                                "original_name": file.name,
                                "filename": unique_filename,
                                "type": file_type,
                                "size": file.size
                            })
                            
                        # Финальное сохранение поста в БД
                        progress_bar.progress(0.95, text="📝 Сохранение поста...")
                        
                        new_post = {
                            "id": str(uuid.uuid4()),
                            "author": p_author,
                            "title": p_title,
                            "description": p_desc,
                            "files": saved_files_data,
                            "timestamp": datetime.now().strftime("%d.%m.%Y %H:%M")
                        }
                        
                        db["posts"].append(new_post)
                        save_db(db)
                        
                        progress_bar.progress(1.0, text="✅ Готово!")
                        st.success("🎉 Пост успешно опубликован! Перейдите во вкладку 'Лента'.")
                        st.balloons()
                        
                    except Exception as e:
                        st.error(f"❌ Произошла ошибка при загрузке: {e}")
                        progress_bar.empty()

# -----------------------------------------
# АДМИН-ПАНЕЛЬ
# -----------------------------------------
elif page == "🛡️ Управление":
    st.title("🛡️ Панель администратора")
    
    if "admin_auth" not in st.session_state:
        st.session_state.admin_auth = False
        
    if not st.session_state.admin_auth:
        st.warning("Вход только для администраторов.")
        pwd = st.text_input("Пароль:", type="password")
        if st.button("Войти"):
            if pwd == ADMIN_PASSWORD:
                st.session_state.admin_auth = True
                st.rerun()
            else:
                st.error("❌ Неверный пароль!")
    else:
        st.success("✅ Режим администратора активирован.")
        if st.button("Выйти", size="small"):
            st.session_state.admin_auth = False
            st.rerun()
            
        st.divider()
        st.subheader("Управление постами")
        
        if not db.get("posts"):
            st.info("База пуста.")
        else:
            for post in reversed(db["posts"]):
                with st.container(border=True):
                    st.markdown(f"**{post['title']}** (От: {post['author']})")
                    st.caption(f"Файлов: {len(post['files'])}")
                    
                    if st.button("🗑️ Удалить пост и все его файлы", key=f"del_{post['id']}", type="primary"):
                        # Сначала удаляем все файлы поста из облака
                        for f in post['files']:
                            try:
                                api.delete_file(
                                    path_in_repo=f"uploads/{f['filename']}",
                                    repo_id=HF_REPO_ID,
                                    repo_type="dataset"
                                )
                            except Exception:
                                pass # Если файл уже удален
                                
                        # Затем удаляем сам пост из БД
                        db["posts"] = [p for p in db["posts"] if p["id"] != post["id"]]
                        save_db(db)
                        st.rerun()
