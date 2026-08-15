import streamlit as st
from datasets import load_dataset, Dataset
from huggingface_hub import HfApi
import pandas as pd
import datetime
import uuid
import os

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
    /* Global mobile optimization */
    .stApp {
        max-width: 100%;
        padding: 0px;
    }
    
    /* Hide default streamlit elements for clean app feel */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    
    /* Custom chat bubble styling */
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

    /* Mobile friendly buttons and inputs */
    div.stButton > button {
        border-radius: 12px;
        height: 48px;
        font-weight: 600;
        width: 100%;
    }
    
    /* Sticky footer styling for message input */
    .fixed-footer {
        position: fixed;
        bottom: 0;
        left: 0;
        width: 100%;
        background-color: white;
        padding: 10px;
        z-index: 100;
        border-top: 1px solid #ddd;
    }
</style>
""", unsafe_allow_html=True)

USERS_DATASET = "p1rs2/messenger.storage"
MESSAGES_DATASET = "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"  # Note: usually HF dataset repo IDs require username/dataset, but we handle safe loading/pushing

# Token input or secrets check for Hugging Face write access
# In Streamlit Cloud, set HF_TOKEN in secrets.toml
hf_token = st.secrets.get("HF_TOKEN", os.environ.get("HF_TOKEN", None))

@st.cache_resource
def get_hf_api():
    if hf_token:
        return HfApi(token=hf_token)
    return None

if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
if "username" not in st.session_state:
    st.session_state.username = ""
if "active_chat" not in st.session_state:
    st.session_state.active_chat = "Global Lobby"  # Can be username for DM or group name
if "chat_type" not in st.session_state:
    st.session_state.chat_type = "group"  # 'group' or 'dm'

@st.cache_data(ttl=5)
def load_users():
    try:
        ds = load_dataset(USERS_DATASET, token=hf_token, split="train")
        return pd.DataFrame(ds)
    except Exception as e:
        # Fallback empty dataframe if dataset is empty or unreachable
        return pd.DataFrame(columns=["username", "password", "created_at"])

@st.cache_data(ttl=3)
def load_messages():
    try:
        ds = load_dataset(MESSAGES_DATASET, token=hf_token, split="train")
        return pd.DataFrame(ds)
    except Exception as e:
        return pd.DataFrame(columns=["id", "sender", "recipient", "content", "timestamp", "is_group"])

def save_user_to_hf(username, password):
    try:
        df = load_users()
        if not df.empty and username in df['username'].values:
            return False, "Пользователь уже существует!"
        
        new_row = pd.DataFrame([{"username": username, "password": password, "created_at": str(datetime.datetime.now())}])
        updated_df = pd.concat([df, new_row], ignore_index=True)
        
        dataset = Dataset.from_pandas(updated_df)
        dataset.push_to_hub(USERS_DATASET, token=hf_token, private=True)
        st.cache_data.clear()
        return True, "Успешная регистрация!"
    except Exception as e:
        return False, f"Ошибка сохранения: {str(e)}"

def save_message_to_hf(sender, recipient, content, is_group):
    try:
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
        dataset = Dataset.from_pandas(updated_df)
        dataset.push_to_hub(MESSAGES_DATASET, token=hf_token, private=True)
        st.cache_data.clear()
        return True
    except Exception as e:
        st.error(f"Не удалось отправить сообщение: {str(e)}")
        return False

if not st.session_state.logged_in:
    st.markdown("<h2 style='text-align: center;'>💬 HuggingChat Messenger</h2>", unsafe_allow_html=True)
    st.markdown("<p style='text-align: center; color: gray;'>Мобильный мессенджер на базе Hugging Face Datasets</p>", unsafe_allow_html=True)
    
    if not hf_token:
        st.warning("⚠️ Внимание: Токен Hugging Face (HF_TOKEN) не обнаружен в secrets. Запись в датасеты может быть недоступна без токена с правами WRITE.")

    tab_login, tab_register = st.tabs(["🔑 Вход", "📝 Регистрация"])
    
    with tab_login:
        with st.form("login_form"):
            login_user = st.text_input("Имя пользователя (Логин)")
            login_pass = st.text_input("Пароль", type="password")
            submit_login = st.form_submit_button("Войти в систему")
            
            if submit_login:
                if not login_user or not login_pass:
                    st.error("Заполните все поля!")
                else:
                    users_df = load_users()
                    if users_df.empty:
                        st.error("Пользователи не найдены. Сначала зарегистрируйтесь.")
                    else:
                        match = users_df[(users_df['username'] == login_user) & (users_df['password'] == login_pass)]
                        if not match.empty:
                            st.session_state.logged_in = True
                            st.session_state.username = login_user
                            st.success("Успешный вход! Загрузка мессенджера...")
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
                    success, msg = save_user_to_hf(reg_user, reg_pass)
                    if success:
                        st.success(f"{msg} Теперь вы можете войти во вкладке 'Вход'.")
                    else:
                        st.error(msg)

else:
    # Top Mobile Navigation / Header Bar
    col_top1, col_top2 = st.columns([3, 1])
    with col_top1:
        st.markdown(f"### 👋 Привет, **{st.session_state.username}**!")
    with col_top2:
        if st.button("Выйти", use_container_width=True):
            st.session_state.logged_in = False
            st.session_state.username = ""
            st.rerun()

    st.markdown("---")

    # Sidebar for selecting chats (Groups & Users) optimized for mobile drawers
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

        st.markdown("#### 👤 Личные сообщения (ЛС)")
        users_df = load_users()
        if not users_df.empty:
            other_users = users_df[users_df['username'] != st.session_state.username]['username'].tolist()
            if not other_users:
                st.info("Пока нет других пользователей.")
            for u in other_users:
                if st.button(f"👤 {u}", use_container_width=True):
                    st.session_state.active_chat = u
                    st.session_state.chat_type = "dm"
                    st.rerun()
        
        st.markdown("---")
        if st.button("🔄 Обновить чаты", use_container_width=True):
            st.cache_data.clear()
            st.rerun()

    chat_title = f"Чат с: {st.session_state.active_chat}" if st.session_state.chat_type == "dm" else f"Группа: {st.session_state.active_chat}"
    st.markdown(f"#### 📌 {chat_title}")

    # Load messages
    messages_df = load_messages()

    # Filter messages based on active chat type
    if not messages_df.empty:
        # Convert columns to string safely
        messages_df['is_group'] = messages_df['is_group'].astype(str)
        
        if st.session_state.chat_type == "group":
            active_msgs = messages_df[
                (messages_df['is_group'].isin(['True', 'true', '1'])) & 
                (messages_df['recipient'] == st.session_state.active_chat)
            ]
        else:
            # DM logic: messages between current user and target user
            curr = st.session_state.username
            target = st.session_state.active_chat
            active_msgs = messages_df[
                ((messages_df['sender'] == curr) & (messages_df['recipient'] == target)) |
                ((messages_df['sender'] == target) & (messages_df['recipient'] == curr))
            ]
        
        # Sort by timestamp
        if not active_msgs.empty and 'timestamp' in active_msgs.columns:
            active_msgs = active_msgs.sort_values(by='timestamp', ascending=True)

        # Render chat history container
        st.markdown('<div class="chat-container">', unsafe_allow_html=True)
        for _, row in active_msgs.iterrows():
            sender = row.get('sender', 'Unknown')
            content = row.get('content', '')
            timestamp = row.get('timestamp', '')
            
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

    # Spacer to prevent content overlap with fixed footer input
    st.markdown("<br><br><br>", unsafe_allow_html=True)

    with st.form(key="message_form", clear_on_submit=True):
        col_input, col_send = st.columns([4, 1])
        with col_input:
            msg_text = st.text_input("Сообщение...", placeholder="Введите сообщение...", label_visibility="collapsed")
        with col_send:
            send_btn = st.form_submit_button("➤")
            
        if send_btn and msg_text.strip():
            is_grp = True if st.session_state.chat_type == "group" else False
            success = save_message_to_hf(
                sender=st.session_state.username,
                recipient=st.session_state.active_chat,
                content=msg_text.strip(),
                is_group=is_grp
            )
            if success:
                st.rerun()
