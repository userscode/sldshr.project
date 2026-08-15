import streamlit as st
import requests
import pandas as pd
import datetime
import uuid
import os
from io import StringIO

# Page configuration for mobile responsiveness and clean look
st.set_page_config(
    page_title="HuggingChat Mobile Messenger",
    page_icon="💬",
    layout="centered",
    initial_sidebar_state="collapsed"
)

# Custom CSS for mobile-friendly UI, chat bubbles, modern styling, and touch targets
st.markdown("""
<style>
    .stApp {
        max-width: 100%;
        padding: 0px;
    }
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    
    .chat-bubble-user {
        background: linear-gradient(135deg, #0084ff 0%, #00c6ff 100%);
        color: white;
        padding: 12px 16px;
        border-radius: 18px 18px 2px 18px;
        margin: 6px 0;
        max-width: 80%;
        float: right;
        clear: both;
        word-break: break-word;
        box-shadow: 0 2px 5px rgba(0,0,0,0.1);
        font-size: 15px;
    }
    
    .chat-bubble-other {
        background: #f1f0f0;
        color: #111;
        padding: 12px 16px;
        border-radius: 18px 18px 18px 2px;
        margin: 6px 0;
        max-width: 80%;
        float: left;
        clear: both;
        word-break: break-word;
        box-shadow: 0 2px 5px rgba(0,0,0,0.05);
        font-size: 15px;
    }
    
    .chat-container {
        display: flex;
        flex-direction: column;
        margin-bottom: 70px;
    }
    
    .timestamp {
        font-size: 10px;
        color: #888;
        margin-top: 2px;
        text-align: right;
    }

    div.stButton > button {
        border-radius: 12px;
        height: 48px;
        font-weight: 600;
        width: 100%;
    }
</style>
""", unsafe_allow_html=True)

USERS_REPO = "p1rs2/messenger.storage"
MESSAGES_REPO = "p1rs2/messenger.messages"

hf_token = st.secrets.get("HF_TOKEN", os.environ.get("HF_TOKEN", None))

def get_headers():
    headers = {"Content-Type": "application/json"}
    if hf_token and hf_token != "slds":
        headers["Authorization"] = f"Bearer {hf_token}"
    return headers

@st.cache_data(ttl=2)
def load_hf_csv(repo_id, columns):
    url = f"https://huggingface.co/datasets/{repo_id}/raw/main/data.csv"
    try:
        resp = requests.get(url, headers=get_headers(), timeout=5)
        if resp.status_code == 200:
            df = pd.read_csv(StringIO(resp.text))
            for col in columns:
                if col not in df.columns:
                    df[col] = ""
            return df
    except Exception:
        pass
    return pd.DataFrame(columns=columns)

def save_hf_csv(repo_id, df, columns):
    try:
        if not hf_token or hf_token == "slds":
            return False, "Укажите действительный рабочий токен HF_TOKEN (с правами Write) в секретах Streamlit."
        
        from huggingface_hub import HfApi, create_repo
        api = HfApi(token=hf_token)
        
        try:
            create_repo(repo_id=repo_id, repo_type="dataset", exist_ok=True, private=False)
        except Exception:
            pass
            
        csv_data = df.to_csv(index=False)
        import tempfile
        with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".csv") as f:
            f.write(csv_data)
            tmp_path = f.name
            
        api.upload_file(
            path_or_fileobj=tmp_path,
            path_in_repo="data.csv",
            repo_id=repo_id,
            repo_type="dataset",
            commit_message="Update data via Streamlit Messenger"
        )
        try:
            os.unlink(tmp_path)
        except:
            pass
        st.cache_data.clear()
        return True, "Успешно!"
    except Exception as e:
        return False, str(e)

if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
if "username" not in st.session_state:
    st.session_state.username = ""
if "active_chat" not in st.session_state:
    st.session_state.active_chat = "Global Lobby"
if "chat_type" not in st.session_state:
    st.session_state.chat_type = "group"

def load_users():
    return load_hf_csv(USERS_REPO, ["username", "password", "created_at"])

def load_messages():
    return load_hf_csv(MESSAGES_REPO, ["id", "sender", "recipient", "content", "timestamp", "is_group"])

def save_user(username, password):
    df = load_users()
    if not df.empty and username in df['username'].astype(str).values:
        return False, "Пользователь уже существует!"
    
    new_row = pd.DataFrame([{"username": username, "password": password, "created_at": str(datetime.datetime.now())}])
    updated_df = pd.concat([df, new_row], ignore_index=True)
    return save_hf_csv(USERS_REPO, updated_df, ["username", "password", "created_at"])

def save_message(sender, recipient, content, is_group):
    df = load_messages()
    msg_id = str(uuid.uuid4())
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    new_row = pd.DataFrame([{
        "id": msg_id,
        "sender": sender,
        "recipient": recipient,
        "content": content,
        "timestamp": timestamp,
        "is_group": str(is_group)
    }])
    
    updated_df = pd.concat([df, new_row], ignore_index=True)
    return save_message_to_hf(MESSAGES_REPO, updated_df, ["id", "sender", "recipient", "content", "timestamp", "is_group"])

def save_message_to_hf(repo_id, df, columns):
    success, err = save_hf_csv(repo_id, df, columns)
    return success, err

if not st.session_state.logged_in:
    st.markdown("<h2 style='text-align: center;'>💬 HuggingChat Messenger</h2>", unsafe_allow_html=True)
    st.markdown("<p style='text-align: center; color: gray;'>Мобильный чат на Hugging Face Datasets</p>", unsafe_allow_html=True)
    
    if not hf_token or hf_token == "slds":
        st.warning("⚠️ Внимание: Установите реальный HF_TOKEN с правами Write в секретах Streamlit.")

    tab_login, tab_register = st.tabs(["🔑 Вход", "📝 Регистрация"])
    
    with tab_login:
        with st.form("login_form"):
            login_user = st.text_input("Логин")
            login_pass = st.text_input("Пароль", type="password")
            submit_login = st.form_submit_button("Войти")
            
            if submit_login:
                if not login_user or not login_pass:
                    st.error("Заполните все поля!")
                else:
                    users_df = load_users()
                    if users_df.empty:
                        st.error("База пользователей пуста или недоступна.")
                    else:
                        match = users_df[(users_df['username'].astype(str) == login_user) & (users_df['password'].astype(str) == login_pass)]
                        if not match.empty:
                            st.session_state.logged_in = True
                            st.session_state.username = login_user
                            st.success("Успешный вход!")
                            st.rerun()
                        else:
                            st.error("Неверный логин или пароль.")

    with tab_register:
        with st.form("register_form"):
            reg_user = st.text_input("Придумайте логин")
            reg_pass = st.text_input("Придумайте пароль", type="password")
            submit_reg = st.form_submit_button("Зарегистрироваться")
            
            if submit_reg:
                if not reg_user or not reg_pass:
                    st.error("Заполните все поля!")
                elif len(reg_user) < 3:
                    st.error("Логин должен быть не короче 3 символов.")
                else:
                    success, msg = save_user(reg_user, reg_pass)
                    if success:
                        st.success("Успешная регистрация! Перейдите во вкладку 'Вход'.")
                    else:
                        st.error(f"Ошибка: {msg}")

else:
    col_top1, col_top2 = st.columns([3, 1])
    with col_top1:
        st.markdown(f"### 👋 **{st.session_state.username}**")
    with col_top2:
        if st.button("Выйти", use_container_width=True):
            st.session_state.logged_in = False
            st.session_state.username = ""
            st.rerun()

    st.markdown("---")

    with st.sidebar:
        st.markdown("### 📱 Меню чатов")
        
        st.markdown("#### 🌐 Общие группы")
        if st.button("💬 Глобальный чат", use_container_width=True):
            st.session_state.active_chat = "Global Lobby"
            st.session_state.chat_type = "group"
            st.rerun()
            
        if st.button("🚀 Разработка и ИИ", use_container_width=True):
            st.session_state.active_chat = "AI & Tech"
            st.session_state.chat_type = "group"
            st.rerun()

        st.markdown("#### 👤 Личные сообщения")
        users_df = load_users()
        if not users_df.empty:
            other_users = users_df[users_df['username'].astype(str) != st.session_state.username]['username'].tolist()
            if not other_users:
                st.info("Пока нет других пользователей.")
            for u in other_users:
                if st.button(f"👤 {u}", use_container_width=True):
                    st.session_state.active_chat = u
                    st.session_state.chat_type = "dm"
                    st.rerun()
        
        st.markdown("---")
        if st.button("🔄 Обновить чат", use_container_width=True):
            st.cache_data.clear()
            st.rerun()

    chat_title = f"ЛС с: {st.session_state.active_chat}" if st.session_state.chat_type == "dm" else f"Группа: {st.session_state.active_chat}"
    st.markdown(f"#### 📌 {chat_title}")

    messages_df = load_messages()

    if not messages_df.empty:
        messages_df['is_group'] = messages_df['is_group'].astype(str)
        
        if st.session_state.chat_type == "group":
            active_msgs = messages_df[
                (messages_df['is_group'].isin(['True', 'true', '1'])) & 
                (messages_df['recipient'].astype(str) == st.session_state.active_chat)
            ]
        else:
            curr = st.session_state.username
            target = st.session_state.active_chat
            active_msgs = messages_df[
                ((messages_df['sender'].astype(str) == curr) & (messages_df['recipient'].astype(str) == target)) |
                ((messages_df['sender'].astype(str) == target) & (messages_df['recipient'].astype(str) == curr))
            ]
        
        if not active_msgs.empty and 'timestamp' in active_msgs.columns:
            active_msgs = active_msgs.sort_values(by='timestamp', ascending=True)

        st.markdown('<div class="chat-container">', unsafe_allow_html=True)
        for _, row in active_msgs.iterrows():
            sender = str(row.get('sender', 'Unknown'))
            content = str(row.get('content', ''))
            timestamp = str(row.get('timestamp', ''))
            
            if sender == st.session_state.username:
                st.markdown(f"""
                <div style="width:100%; float:right;">
                    <div class="chat-bubble-user">
                        <div style="font-size: 11px; font-weight: bold; margin-bottom: 2px; color: #e0f2fe;">Вы</div>
                        {content}
                        <div class="timestamp">{timestamp}</div>
                    </div>
                </div>
                """, unsafe_allow_html=True)
            else:
                st.markdown(f"""
                <div style="width:100%; float:left;">
                    <div class="chat-bubble-other">
                        <div style="font-size: 11px; font-weight: bold; margin-bottom: 2px; color: #0284c7;">{sender}</div>
                        {content}
                        <div class="timestamp">{timestamp}</div>
                    </div>
                </div>
                """, unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)
    else:
        st.info("Пока нет сообщений в этом чате. Напишите первыми!")

    st.markdown("<br><br>", unsafe_allow_html=True)

    with st.form(key="message_form", clear_on_submit=True):
        col_input, col_send = st.columns([4, 1])
        with col_input:
            msg_text = st.text_input("Сообщение...", placeholder="Введите сообщение...", label_visibility="collapsed")
        with col_send:
            send_btn = st.form_submit_button("➤")
            
        if send_btn and msg_text.strip():
            is_grp = True if st.session_state.chat_type == "group" else False
            success, err = save_message(
                sender=st.session_state.username,
                recipient=st.session_state.active_chat,
                content=msg_text.strip(),
                is_group=is_grp
            )
            if success:
                st.rerun()
            else:
                st.error(f"Не удалось отправить: {err}")
```eof
