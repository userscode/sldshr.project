import streamlit as st
import os
import json
import uuid
import tempfile
from datetime import datetime
from huggingface_hub import HfApi, hf_hub_download
from huggingface_hub.utils import EntryNotFoundError

# Настройки страницы
st.set_page_config(page_title="Видеохостинг", page_icon=":material/movie:", layout="wide")

# CSS для улучшения внешнего вида
st.markdown("""
<style>
    #MainMenu {visibility: hidden;}
    header {visibility: hidden;}
    footer {visibility: hidden;}
    .block-container {
        padding-top: 2rem !important;
        max-width: 1000px;
    }
    .video-card {
        background-color: #f0f2f6;
        border-radius: 10px;
        padding: 15px;
        margin-bottom: 20px;
    }
    [data-theme="dark"] .video-card {
        background-color: #1e1e27;
    }
</style>
""", unsafe_allow_html=True)

ADMIN_PASSWORD = "SuperSecret_Admin_Password_2026!#$"

# Получаем секреты для доступа к Hugging Face
HF_TOKEN = st.secrets.get("HF_TOKEN", None)
HF_REPO_ID = st.secrets.get("HF_REPO_ID", None)

# Проверка, настроены ли секреты
if not HF_TOKEN or not HF_REPO_ID:
    st.error("⚠️ Внимание: Не настроены HF_TOKEN и HF_REPO_ID в Secrets. Приложение не сможет сохранять данные.")
    st.stop()

# Инициализируем API Hugging Face
api = HfApi(token=HF_TOKEN)

@st.cache_data(ttl=10) # Кэшируем на 10 секунд, чтобы не спамить запросами к HF
def load_db():
    try:
        # Скачиваем файл metadata.json из репозитория
        db_path = hf_hub_download(
            repo_id=HF_REPO_ID, 
            filename="metadata.json", 
            repo_type="dataset", 
            token=HF_TOKEN
        )
        with open(db_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except EntryNotFoundError:
        # Если файла еще нет, возвращаем пустую базу
        return {"videos": []}
    except Exception as e:
        st.error(f"Ошибка при загрузке БД: {e}")
        return {"videos": []}

def save_db(db):
    # Сохраняем локально во временный файл и отправляем на HF
    with tempfile.NamedTemporaryFile(mode="w", delete=False, encoding="utf-8") as tmp:
        json.dump(db, tmp, ensure_ascii=False, indent=4)
        tmp_path = tmp.name
    
    api.upload_file(
        path_or_fileobj=tmp_path,
        path_in_repo="metadata.json",
        repo_id=HF_REPO_ID,
        repo_type="dataset"
    )
    # Очищаем временный файл
    os.remove(tmp_path)
    # Сбрасываем кэш, чтобы загрузить свежие данные
    load_db.clear()

db = load_db()

with st.sidebar:
    st.markdown("## 📺 Навигация")
    page = st.radio("Меню", ["🏠 Главная", "📤 Загрузить видео", "🛡️ Админ-панель"], label_visibility="collapsed")
    st.divider()
    st.caption("Без регистрации. Все видео хранятся в Hugging Face Datasets!")

# -----------------------------------------
# ГЛАВНАЯ СТРАНИЦА (Лента видео)
# -----------------------------------------
if page == "🏠 Главная":
    st.title("🎥 Новые видео")
    
    if not db.get("videos"):
        st.info("Пока нет загруженных видео. Станьте первым, кто загрузит ролик!")
    else:
        for video in reversed(db["videos"]):
            with st.container(border=True):
                st.subheader(video["title"])
                st.caption(f"👤 Автор: **{video['author']}** • 🕒 {video['timestamp']}")
                
                # Пытаемся скачать/найти видеофайл из HF Datasets
                try:
                    video_path = hf_hub_download(
                        repo_id=HF_REPO_ID,
                        filename=f"videos/{video['filename']}",
                        repo_type="dataset",
                        token=HF_TOKEN
                    )
                    st.video(video_path)
                except Exception as e:
                    st.error(f"Не удалось загрузить видеофайл с облака. (Возможно, он был удален)")
                
                if video["description"]:
                    st.markdown(video["description"])

# -----------------------------------------
# СТРАНИЦА ЗАГРУЗКИ ВИДЕО
# -----------------------------------------
elif page == "📤 Загрузить видео":
    st.title("📤 Опубликовать видео")
    st.markdown("Файл будет напрямую отправлен в Hugging Face Dataset. (Макс. размер по умолчанию 3 ГБ)")
    
    with st.form("upload_form"):
        v_author = st.text_input("Ваше имя или никнейм", max_chars=50)
        v_title = st.text_input("Название видео", max_chars=100)
        v_desc = st.text_area("Описание видео (о чем оно?)", max_chars=500)
        
        v_file = st.file_uploader("Выберите видеофайл", type=["mp4", "mov", "avi", "mkv"])
        
        submitted = st.form_submit_button("Опубликовать", type="primary", use_container_width=True)
        
        if submitted:
            if not v_author or not v_title or not v_file:
                st.error("Пожалуйста, заполните имя, название и выберите файл!")
            else:
                with st.spinner("Загрузка видео в облако Hugging Face... (Большие файлы грузятся долго)"):
                    try:
                        file_ext = v_file.name.split('.')[-1]
                        unique_filename = f"{uuid.uuid4().hex}.{file_ext}"
                        
                        # Сохраняем загруженный файл во временную директорию
                        with tempfile.NamedTemporaryFile(delete=False, suffix=f".{file_ext}") as tmp_video:
                            tmp_video.write(v_file.getbuffer())
                            tmp_video_path = tmp_video.name
                        
                        # Загружаем файл напрямую в датасет в папку videos/
                        api.upload_file(
                            path_or_fileobj=tmp_video_path,
                            path_in_repo=f"videos/{unique_filename}",
                            repo_id=HF_REPO_ID,
                            repo_type="dataset"
                        )
                        os.remove(tmp_video_path) # Удаляем временный файл
                        
                        # Обновляем базу данных
                        new_video = {
                            "id": str(uuid.uuid4()),
                            "author": v_author,
                            "title": v_title,
                            "description": v_desc,
                            "filename": unique_filename,
                            "timestamp": datetime.now().strftime("%d.%m.%Y %H:%M")
                        }
                        db["videos"].append(new_video)
                        save_db(db)
                        
                        st.success("🎉 Видео успешно опубликовано! Перейдите на Главную.")
                    except Exception as e:
                        st.error(f"❌ Ошибка при загрузке: {e}")

# -----------------------------------------
# АДМИН-ПАНЕЛЬ
# -----------------------------------------
elif page == "🛡️ Админ-панель":
    st.title("🛡️ Панель администратора")
    
    if "admin_auth" not in st.session_state:
        st.session_state.admin_auth = False
        
    if not st.session_state.admin_auth:
        st.warning("Доступ только для администраторов.")
        pwd = st.text_input("Введите пароль доступа:", type="password")
        if st.button("Войти"):
            if pwd == ADMIN_PASSWORD:
                st.session_state.admin_auth = True
                st.rerun()
            else:
                st.error("❌ Неверный пароль!")
    else:
        st.success("✅ Вы вошли как Администратор.")
        if st.button("Выйти из админ-панели"):
            st.session_state.admin_auth = False
            st.rerun()
            
        st.divider()
        st.subheader("Управление видео (в облаке)")
        
        if not db.get("videos"):
            st.info("База видео пуста.")
        else:
            for video in reversed(db["videos"]):
                with st.container(border=True):
                    col1, col2 = st.columns([4, 1], vertical_alignment="center")
                    with col1:
                        st.markdown(f"**{video['title']}** (Автор: {video['author']})")
                        st.caption(f"ID: {video['id']} | Файл: {video['filename']}")
                    with col2:
                        if st.button("🗑️ Удалить", key=f"del_{video['id']}", type="primary"):
                            try:
                                # Удаляем файл из HF Dataset
                                api.delete_file(
                                    path_in_repo=f"videos/{video['filename']}",
                                    repo_id=HF_REPO_ID,
                                    repo_type="dataset"
                                )
                            except Exception as e:
                                st.warning(f"Файл видео не найден в облаке или ошибка: {e}")
                            
                            # Удаляем из базы и сохраняем
                            db["videos"] = [v for v in db["videos"] if v["id"] != video["id"]]
                            save_db(db)
                            st.rerun()
