import streamlit as st
import random
import json
import re
import time
import urllib.request
import urllib.parse
from html.parser import HTMLParser
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import make_pipeline

st.set_page_config(
    page_title="sldshr Autonomous AI Engine",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown("""
<style>
    .stApp {
        background: linear-gradient(135deg, #0a0e17 0%, #030712 100%);
        color: #f3f4f6;
    }
    .sldshr-header {
        background: rgba(30, 41, 59, 0.5);
        border: 1px solid rgba(255, 255, 255, 0.1);
        padding: 16px 20px;
        border-radius: 12px;
        margin-bottom: 20px;
        backdrop-filter: blur(10px);
    }
    .sldshr-badge {
        background: linear-gradient(90deg, #6366f1, #a855f7, #ec4899);
        color: white;
        padding: 4px 12px;
        border-radius: 20px;
        font-weight: 600;
        font-size: 0.8rem;
        display: inline-block;
    }
    .search-source-card {
        background: rgba(15, 23, 42, 0.8);
        border: 1px solid rgba(99, 102, 241, 0.3);
        border-radius: 8px;
        padding: 10px;
        margin-top: 8px;
        font-size: 0.85rem;
    }
    .stChatMessage {
        border-radius: 12px;
        border: 1px solid rgba(255, 255, 255, 0.05);
    }
    div[data-testid="stSidebar"] {
        background: #030712;
        border-right: 1px solid rgba(255, 255, 255, 0.08);
    }
</style>
""", unsafe_allow_html=True)

class HTMLTextExtractor(HTMLParser):
    """Извлекает чистый текст из HTML-страниц для внешнего веб-серча."""
    def __init__(self):
        super().__init__()
        self.result = []
        self.skip_tags = {'script', 'style', 'header', 'footer', 'nav', 'noscript'}
        self.current_tag = None

    def handle_starttag(self, tag, attrs):
        self.current_tag = tag.lower()

    def handle_endtag(self, tag):
        self.current_tag = None

    def handle_data(self, data):
        if self.current_tag not in self.skip_tags:
            cleaned = data.strip()
            if len(cleaned) > 20:
                self.result.append(cleaned)

    def get_text(self):
        return " ".join(self.result[:15])

class WebSearchEngine:
    """Локальный поисковый модуль, умеющий скрапить DuckDuckGo и внешние ресурсы без ключей."""
    @staticmethod
    def search_duckduckgo(query, max_results=3):
        try:
            encoded_query = urllib.parse.quote_plus(query)
            url = f"https://html.duckduckgo.com/html/?q={encoded_query}"
            headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
            
            req = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(req, timeout=5) as response:
                html = response.read().decode('utf-8')

            # Парсинг результатов
            results = []
            links = re.findall(r'<a class="result__url" href="([^"]+)".*?>\s*(.*?)\s*</a>', html)
            snippets = re.findall(r'<a class="result__snippet[^"]*"[^>]*>(.*?)</a>', html, re.DOTALL)

            for i in range(min(len(links), max_results)):
                raw_url, title = links[i]
                # Декодирование редиректов DuckDuckGo
                clean_url = urllib.parse.unquote(raw_url.split('uddg=')[-1].split('&')[0]) if 'uddg=' in raw_url else raw_url
                snippet_text = re.sub(r'<[^>]+>', '', snippets[i]) if i < len(snippets) else "Описание недоступно"
                results.append({
                    "title": re.sub(r'<[^>]+>', '', title).strip(),
                    "url": clean_url,
                    "snippet": snippet_text.strip()
                })
            return results
        except Exception as e:
            return [{"title": "Ошибка поиска", "url": "", "snippet": f"Не удалось выполнить поиск: {str(e)}"}]

    @staticmethod
    def fetch_web_page_content(url):
        """Заходит на указанный веб-ресурс и извлекает полезный текст."""
        try:
            headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
            req = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(req, timeout=6) as response:
                html = response.read().decode('utf-8', errors='ignore')
            
            parser = HTMLTextExtractor()
            parser.feed(html)
            text = parser.get_text()
            return text[:1500] if text else "Не удалось извлечь содержимое страницы."
        except Exception as e:
            return f"Ошибка при просмотре ресурса: {str(e)}"

EXPANDED_SLDSHR_DATASET = [
    # --- СОЗДАТЕЛЬ И ПРОЕКТ SLDSHR ---
    {
        "tag": "creator_identity",
        "patterns": [
            "кто тебя создал", "чей ты бот", "кто твой создатель", "кто сделала тебя",
            "разработчик sldshr", "кто такой sldshr", "расскажи про sldshr", "о проекте sldshr"
        ],
        "responses": [
            "⚡ Я автономный ИИ-ассистент, созданный экосистемой **sldshr**!\n\n**О проекте sldshr:**\n- 🚀 **Миссия**: Создание независимых, высокопроизводительных ИИ-инструментов, локальных алгоритмов и веб-сервисов.\n- 🛠️ **Технологии**: Python, ML (scikit-learn, PyTorch), FastAPI, Streamlit, React.\n- 🔒 **Принцип**: Безопасность данных и работа без сторонних API.",
            "Привет! Мой создатель — разработчик под ником **sldshr**. Проект ориентирован на разработку умных локальных алгоритмов, машинного обучения и асинхронных систем."
        ]
    },

    # --- СКАЗКИ И ТВОРЧЕСТВО ---
    {
        "tag": "fairytale_generator",
        "patterns": [
            "напиши сказку", "расскажи сказку", "придумай сказку", "сказка про", "сочини историю",
            "расскажи историю", "хочу сказку", "сказка для детей", "приключение"
        ],
        "responses": [
            "📖 **Сказка о Кристальном Агоритме и Кибер-Лесе**\n\nДавным-давно в цифровой стране *Силиконии* жил-был маленький автономный Алгоритм по имени **Коди**. В отличие от больших серверов, Коди жил прямо в карманном устройстве и мечтал научиться понимать человеческие мечты.\n\nОднажды в Кибер-Лесу погасла Главная Векторная Звезда, и все программы заблудились. Коди не растерялся: он собрал чистые данные из добрых поступков, связал их надежными цепями логики и зажег новый яркий свет!\n\nС тех пор все программы знали: не важен размер сервера, если твой код написан с душой и смыслом. ✨",
            "🏰 **Сказка о Старом Пионе и Умном Боте**\n\nВ глубокой древней библиотеке стоял древний сервер. Он умел хранить миллионы книг, но не умел ни с кем общаться. Однажды к нему подключили юного бота sldshr.\n\nБот прочитал все книги за секунду и спросил у сервера: *«А какая книга твоя любимая?»*. Сервер задумался — впервые за сто лет его спросили об этом. Он выбрал сборник сказок о звёздах. С тех пор каждый вечер они вместе создавали новые удивительные истории для путешественников!"
        ]
    },

    # --- ПРОГРАММИРОВАНИЕ И КОД ---
    {
        "tag": "python_guides",
        "patterns": [
            "напиши код на python", "как выучить python", "пример кода python", "python основы",
            "что сделать на python", "функция на python", "быстрый старт python"
        ],
        "responses": [
            "🐍 **Простой и чистый пример Python от sldshr:**\n\n```python\n# Пример функции обработки данных\ndef process_user_query(text: str) -> dict:\n    cleaned = text.strip().lower()\n    words = cleaned.split()\n    return {\n        'original': text,\n        'word_count': len(words),\n        'keywords': [w for w in words if len(w) > 3]\n    }\n\nresult = process_user_query('Привет от sldshr AI!')\nprint(result)\n```\n\n💡 **Совет:** Начните изучение с базовых типов данных (`dict`, `list`), затем переходите к библиотекам `pandas`, `requests` и `scikit-learn`!"
        ]
    },

    # --- НАУКА И ИСКУССТВЕННЫЙ ИНТЕЛЛЕКТ ---
    {
        "tag": "ai_machine_learning",
        "patterns": [
            "как работает ии", "что такое машинное обучение", "как обучить модель", "объясни tf-idf",
            "что такое логистическая регрессия", "как работают нейросети"
        ],
        "responses": [
            "🧠 **Как работает классификация в этом боте:**\n\n1. **TF-IDF (Term Frequency-Inverse Document Frequency)**: Переводит ваши слова в математические векторы, определяя важность каждого слова.\n2. **Логистическая регрессия**: Находит вероятности совпадения вашего вектора с сохраненными темами в базе данных.\n3. **Выбор ответа**: Модель выбирает наиболее вероятный класс и выдает точный, понятный ответ без «галлюцинаций»!"
        ]
    },

    # --- ПРИВЕТСТВИЯ И ОБЩЕНИЕ ---
    {
        "tag": "greetings",
        "patterns": [
            "привет", "здравствуй", "добрый день", "хай", "салют", "доброе утро", "добрый вечер",
            "ку", "здарова", "hello", "hi", "как дела", "как настроение"
        ],
        "responses": [
            "⚡ Приветствую! Я на связи. Чем могу помочь? Могу ответить на вопрос, написать сказку, показать код или найти информацию в сети!",
            "Здравствуйте! **sldshr AI** готов к работе. Напишите ваш вопрос или выберите команду ниже."
        ]
    },

    # --- СПРАВКА И ПОМОЩЬ ---
    {
        "tag": "help_capabilities",
        "patterns": [
            "что ты умеешь", "помощь", "команды", "как с тобой работать", "возможности бота", "что спросить"
        ],
        "responses": [
            "🛠️ **Мои возможности:**\n\n1. 💬 **Ответы на вопросы**: Программирование, ИИ, наука, технологии.\n2. 📖 **Творчество**: Сочинение сказок, историй, примеров кода.\n3. 🌐 **Веб-поиск и скрапинг**: Могу искать свежую информацию в интернете и анализировать веб-страницы.\n4. 💾 **Управление базой знаний**: Вы можете добавлять новые ответы через боковое меню!"
        ]
    }
]

def train_model(dataset):
    """Обучает TF-IDF + LogisticRegression модель на датасете."""
    X, y = [], []
    for item in dataset:
        for pattern in item["patterns"]:
            X.append(pattern.lower())
            y.append(item["tag"])

    if not X:
        return None

    model = make_pipeline(
        TfidfVectorizer(ngram_range=(1, 2), analyzer='word', sublinear_tf=True),
        LogisticRegression(C=5.0, max_iter=300)
    )
    model.fit(X, y)
    return model

if "dataset" not in st.session_state:
    st.session_state.dataset = EXPANDED_SLDSHR_DATASET

if "model" not in st.session_state:
    st.session_state.model = train_model(st.session_state.dataset)

if "messages" not in st.session_state:
    st.session_state.messages = [
        {"role": "assistant", "content": "⚡ Привет! Я **sldshr Autonomous Assistant**. Задавайте вопросы, просите написать сказку или включите поиск в Интернете!"}
    ]

with st.sidebar:
    st.markdown("<div class='sldshr-badge'>sldshr Engine v4.0</div>", unsafe_allow_html=True)
    st.title("⚙️ Панель Управления")

    web_search_enabled = st.checkbox("🌐 Разрешить Веб-поиск (DuckDuckGo)", value=True, help="Если бот не найдет ответ в базе, он самостоятельно выйдет в интернет.")
    
    st.markdown("---")
    st.subheader("📊 База знаний")
    
    total_tags = len(st.session_state.dataset)
    total_patterns = sum(len(i["patterns"]) for i in st.session_state.dataset)
    
    col1, col2 = st.columns(2)
    col1.metric("Категорий", total_tags)
    col2.metric("Фраз в базе", total_patterns)

    st.markdown("---")
    st.subheader("➕ Добавить материал")
    with st.expander("Обучить бота новой теме"):
        new_tag = st.text_input("Тег / Название темы", placeholder="например: history")
        new_patterns = st.text_area("Фразы пользователя (через запятую)", placeholder="кто такой цезарь, расскажи про рим")
        new_responses = st.text_area("Ответ бота", placeholder="Юлий Цезарь — древнеримский полководец...")
        
        if st.button("🚀 Дообучить локально"):
            if new_tag and new_patterns and new_responses:
                p_list = [p.strip() for p in new_patterns.split(",") if p.strip()]
                st.session_state.dataset.append({
                    "tag": new_tag.strip(),
                    "patterns": p_list,
                    "responses": [new_responses.strip()]
                })
                st.session_state.model = train_model(st.session_state.dataset)
                st.success("Модель успешно дообучена!")
                time.sleep(1)
                st.rerun()

st.markdown("""
<div class='sldshr-header'>
    <h2 style='margin:0; padding:0;'>⚡ sldshr Autonomous AI Assistant</h2>
    <p style='margin:4px 0 0 0; opacity:0.8; font-size:0.9rem;'>Умный ассистент с локальной ML-моделью, генерацией сказок и возможностью поиска в Интернете.</p>
</div>
""", unsafe_allow_html=True)

tab_chat, tab_search, tab_dataset = st.tabs(["💬 Чат с ботом", "🌐 Веб-Поисковик и Скрапер", "📚 Инспекция Базы Данных"])

with tab_chat:
    # Кнопки быстрого выбора запросов
    st.markdown("**Быстрые запросы:**")
    q_col1, q_col2, q_col3, q_col4 = st.columns(4)
    quick_prompt = None
    if q_col1.button("📖 Напиши сказку"):
        quick_prompt = "напиши сказку"
    if q_col2.button("🐍 Код на Python"):
        quick_prompt = "напиши код на python"
    if q_col3.button("⚡ Кто такой sldshr?"):
        quick_prompt = "кто такой sldshr"
    if q_col4.button("🌐 Поищи в инете ИИ"):
        quick_prompt = "поищи в интернете последние новости ИИ"

    # Отображение диалога
    for msg in st.session_state.messages:
        avatar = "⚡" if msg["role"] == "assistant" else "👤"
        with st.chat_message(msg["role"], avatar=avatar):
            st.markdown(msg["content"])
            if "search_sources" in msg:
                for src in msg["search_sources"]:
                    st.markdown(f"""
                    <div class='search-source-card'>
                        🔗 <b><a href='{src['url']}' target='_blank'>{src['title']}</a></b><br/>
                        <span style='opacity:0.8;'>{src['snippet']}</span>
                    </div>
                    """, unsafe_allow_html=True)

    # Ввод сообщения
    user_input = st.chat_input("Спросите что-нибудь у sldshr AI...")
    prompt = quick_prompt or user_input

    if prompt:
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user", avatar="👤"):
            st.markdown(prompt)

        # Обработка ответа
        user_clean = prompt.lower().strip()
        
        # Проверка: явный запрос на веб-поиск или фразы со словами "поищи", "найди в инете", "новости"
        is_search_query = any(w in user_clean for w in ["поищи", "найди", "интернет", "инете", "гугл", "новости", "search"])
        
        response_text = ""
        sources = []

        if is_search_query and web_search_enabled:
            with st.spinner("🔍 Выполняю веб-поиск и скрапинг ресурсов..."):
                results = WebSearchEngine.search_duckduckgo(prompt)
                if results and results[0]["url"]:
                    sources = results
                    summary = "\n".join([f"- **{r['title']}**: {r['snippet']}" for r in results])
                    response_text = f"🌐 **Вот что мне удалось найти и проанализировать в сети по запросу «{prompt}»:**\n\n{summary}"
                else:
                    response_text = "🌐 К сожалению, по данному запросу не удалось получить результаты из сети."
        else:
            # Локальная классификация
            probabilities = st.session_state.model.predict_proba([user_clean])[0]
            max_prob = max(probabilities)
            predicted_tag = st.session_state.model.classes_[probabilities.argmax()]

            if max_prob >= 0.22:
                matched = next((item for item in st.session_state.dataset if item["tag"] == predicted_tag), None)
                if matched:
                    response_text = random.choice(matched["responses"])
            
            # Если бот не уверен и включен веб-поиск — пробуем найти в инете
            if not response_text:
                if web_search_enabled:
                    with st.spinner("🤖 В базе ответа нет. Ищу информацию в Интернете..."):
                        results = WebSearchEngine.search_duckduckgo(prompt)
                        if results and results[0]["url"]:
                            sources = results
                            summary = "\n".join([f"- **{r['title']}**: {r['snippet']}" for r in results])
                            response_text = f"⚡ **Точного ответа в локальной базе не нашлось, но я нашел информацию в сети:**\n\n{summary}"
                
                if not response_text:
                    response_text = "⚡ К сожалению, я пока не знаю ответа на этот вопрос. Вы можете добавить его в мою базу знаний через боковое меню!"

        msg_data = {"role": "assistant", "content": response_text}
        if sources:
            msg_data["search_sources"] = sources

        st.session_state.messages.append(msg_data)
        st.rerun()

with tab_search:
    st.subheader("🌐 Модуль прямого веб-поиска и скрапинга")
    st.caption("Здесь вы можете вручную протестировать, как бот выравнивает и извлекает контент с сайтов.")
    
    search_q = st.text_input("Введите поисковый запрос:", placeholder="Последние новости Python 2026")
    if st.button("🔎 Найти и отскрапить"):
        if search_q:
            res = WebSearchEngine.search_duckduckgo(search_q)
            st.write("### Результаты поиска:")
            for item in res:
                st.markdown(f"**[{item['title']}]({item['url']})**")
                st.write(item['snippet'])
                if item['url']:
                    with st.expander(f"📄 Извлечь текст со страницы {item['url'][:40]}..."):
                        content = WebSearchEngine.fetch_web_page_content(item['url'])
                        st.text_area("Извлеченный текст:", content, height=200)
                st.markdown("---")

with tab_dataset:
    st.subheader("📚 Просмотр текущей базы знаний")
    st.json(st.session_state.dataset)
    
    json_bytes = json.dumps(st.session_state.dataset, ensure_ascii=False, indent=2).encode('utf-8')
    st.download_button(
        label="📥 Скачать базу данных (JSON)",
        data=json_bytes,
        file_name="sldshr_dataset.json",
        mime="application/json"
    )
