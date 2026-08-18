import streamlit as st
import random
import json
import re
import time
from collections import defaultdict
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import make_pipeline

st.set_page_config(
    page_title="sldshr Autonomous AI",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown("""
<style>
    .main {
        background: linear-gradient(135deg, #090d16 0%, #02040a 100%);
    }
    .stAppHeader {
        background: transparent;
    }
    .sldshr-badge {
        background: linear-gradient(90deg, #6366f1, #a855f7, #ec4899);
        color: white;
        padding: 5px 14px;
        border-radius: 20px;
        font-weight: bold;
        font-size: 0.85rem;
        display: inline-block;
        margin-bottom: 12px;
        box-shadow: 0 0 15px rgba(168, 85, 247, 0.4);
    }
    .sldshr-status {
        background: rgba(16, 185, 129, 0.15);
        border: 1px solid rgba(16, 185, 129, 0.4);
        color: #34d399;
        padding: 8px 12px;
        border-radius: 8px;
        font-size: 0.85rem;
        margin-bottom: 15px;
    }
    .stChatMessage {
        border-radius: 12px;
        padding: 12px;
        margin-bottom: 8px;
    }
    div[data-testid="stSidebar"] {
        background: #060911;
        border-right: 1px solid rgba(255, 255, 255, 0.08);
    }
</style>
""", unsafe_allow_html=True)

SLDSHR_MASSIVE_INTENTS = [
    # --- БРЕНД И ПРОЕКТЫ SLDSHR ---
    {
        "tag": "sldshr_about",
        "patterns": [
            "кто такой sldshr", "что за sldshr", "расскажи про sldshr", "кто твой создатель", 
            "чей ты бот", "кто сделал тебя", "sldshr это кто", "о проекте sldshr", "разработчик sldshr"
        ],
        "responses": [
            "⚡ **sldshr** — это автономная экосистема разработчиков и исследователей ИИ, создающая локальные алгоритмы, высоконагруженные сервисы и гибкие нейросетевые инструменты!",
            "Я — полностью автономный интеллектуальный бот от **sldshr**. Работаю 100% локально, без внешних API, серверов или платных подписок!",
            "**sldshr** продвигает идею независимых ИИ-систем. Мой код выполняется прямо в вашей среде Python с использованием машинного обучения и цепей Маркова."
        ]
    },
    {
        "tag": "sldshr_products",
        "patterns": [
            "что умеет sldshr", "проекты sldshr", "продукты sldshr", "стек sldshr", "какие сервисы есть у sldshr", "чем занимается sldshr"
        ],
        "responses": [
            "🚀 **Ключевые направления sldshr:**\n- Локальные автономизированные ИИ-ассистенты\n- Высокоскоростные парсеры и пайплайны обработки данных\n- Модульные интерфейсы на Streamlit, React и FastAPI\n- Оптимизированные алгоритмы машинного обучения (scikit-learn, PyTorch)",
            "Стек **sldshr** основывается на чистом Python, оптимизированных структурах данных, векторах TF-IDF и стохастической генерации текстов."
        ]
    },

    # --- ПРИВЕТСТВИЯ И ПРОЩАНИЯ ---
    {
        "tag": "greeting",
        "patterns": [
            "привет", "здравствуй", "добрый день", "хай", "салют", "доброе утро", "добрый вечер", 
            "дратути", "хей", "ку", "приветик", "здарова", "hello", "hi", "hey", "добрейший вечерок"
        ],
        "responses": [
            "Приветствую! На связи локальный движок **sldshr AI**. Задавайте любой вопрос!",
            "Здравствуйте! Я готов к обработке запросов и генерации ответов. Чем могу помочь?",
            "Хэй! sldshr Bot на месте. Все вычисления происходят прямо у вас на ПК. О чем поговорим?",
            "Привет! Готов разобрать вопросы по коду, науке или архитектуре приложений."
        ]
    },
    {
        "tag": "goodbye",
        "patterns": [
            "пока", "до свидания", "прощай", "до встречи", "увидимся", "бай", "всего доброго", 
            "хорошего дня", "спокойной ночи", "бб", "bye", "goodbye"
        ],
        "responses": [
            "До связи! Рад был помочь. Возвращайтесь к **sldshr AI** в любое время!",
            "Всего хорошего! Успешной разработки и чистых алгоритмов!",
            "Увидимся! Локальный движок переходит в режим ожидания."
        ]
    },

    # --- ПРОГРАММИРОВАНИЕ И PYTHON ---
    {
        "tag": "python_basics",
        "patterns": [
            "почему python", "зачем нужен python", "расскажи про python", "питон код", "что такое python", "плюсы python", "учить python"
        ],
        "responses": [
            "🐍 **Python** — сильный и читаемый язык. Он доминирует в сфере ИИ и ML благодаря богатой экосистеме: `scikit-learn`, `numpy`, `pandas`, `torch`, `streamlit`.",
            "Главное преимущество Python — лаконичный синтаксис и быстрая скорость разработки прототипов. В **sldshr** этот язык является основным инструментарием."
        ]
    },
    {
        "tag": "machine_learning",
        "patterns": [
            "что такое машинное обучение", "как работает ml", "объясни машинное обучение", "обучение моделей", "scikit-learn", "tf-idf", "векторизация"
        ],
        "responses": [
            "🤖 **Машинное обучение (ML)** — область ИИ, где алгоритм находит паттерны в данных. Например, **TF-IDF** превращает слова в математические векторы, а **Логистическая регрессия** классифицирует их по темам.",
            "В отличие от правил с `if/else`, модель ML в **sldshr AI** рассчитывает вероятности принадлежности вашего текста к конкретным интентам."
        ]
    },
    {
        "tag": "streamlit_info",
        "patterns": [
            "что такое streamlit", "зачем нужен streamlit", "как работает streamlit", "как делать дашборд на streamlit"
        ],
        "responses": [
            "🎈 **Streamlit** — реактивный фреймворк Python для быстрого создания веб-приложений. Весь этот чат-бот полностью построен на Streamlit всего в одном файле!",
            "В Streamlit состояние сохраняется через `st.session_state`, а интерфейс обновляется при любом действии пользователя за доли секунды."
        ]
    },

    # --- АРХИТЕКТУРА И ДАТА БАЗЫ ---
    {
        "tag": "backend_dev",
        "patterns": [
            "что такое backend", "как устроена архитектура", "fastapi или flask", "база данных", "sql или nosql", "docker контейнеры"
        ],
        "responses": [
            "⚙️ **Бэкенд архитектура**: для высокой производительности выбирают **FastAPI** (асинхронность на asyncio). Для хранения данных — **PostgreSQL** (реляционная) или **Redis** (кэш в памяти).",
            "🐳 **Docker** позволяет запаковать код, зависимости и библиотеки в изолированный образ, гарантируя, что приложение запустится везде одинаково."
        ]
    },

    # --- ЮМОР И СТАТУС ---
    {
        "tag": "jokes",
        "patterns": [
            "расскажи анекдот", "пошути", "знаешь шутку", "анекдот про программистов", "смешная шутка", "развлеки меня"
        ],
        "responses": [
            "💡 Почему программисты любят тёмную тему? Потому что свет привлекает баги! 🐛",
            "🖥️ Есть 10 типов людей: те, кто понимают двоичную систему счисления, и те, кто её не понимают.",
            "⚡ В локальном коде sldshr нет багов, есть только незадокументированные алгоритмические особенности!"
        ]
    },
    {
        "tag": "mood_status",
        "patterns": [
            "как дела", "как жизнь", "как настроение", "ты как", "все хорошо", "как себя чувствуешь"
        ],
        "responses": [
            "⚡ Все локальные потоки **sldshr AI** работают на максимум! Память чиста, процессоры готовы к вычислениям.",
            "Отлично! Локальная цепь Маркова обучена, классификатор готов. О чем спросите?"
        ]
    }
]

SLDSHR_TEXT_CORPUS = """
Проект sldshr разрабатывает автономные интеллектуальные системы на языке Python.
Машинное обучение позволяет компьютерам учиться на данных без явного программирования всех правил.
Векторизация TF-IDF извлекает важные слова и переводит текст в числовую матрицу.
Логистическая регрессия рассчитывает вероятность классов и выбирает наиболее подходящий ответ.
Цепи Маркова строят вероятностные цепочки слов для генерации новых уникальных предложений.
Streamlit позволяет создавать современные интерактивные веб-интерфейсы прямо из кода Python.
Локальные ИИ системы гарантируют полную приватность данные не передаются на сторонние серверы.
Разработка бэкенда требует понимания асинхронности баз данных и контейнеризации через Docker.
Чистый код и правильно подобранная структура данных делают приложения sldshr быстрыми и надежными.
Векторный анализ текста позволяет находить скрытые зависимости и смысловые сходства в фразах.
Автономный чат бот sldshr способен синтезировать ответы объединяя статистику и правила языка.
Команда sldshr постоянно улучшает алгоритмы обработки естественного языка для локального запуска.
Обучение модели происходит за доли секунды благодаря эффективным математическим библиотекам.
Применение алгоритмов классификации делает поиск ответов точным и устойчивым к опечаткам.
"""

class SldshrMarkovGenerator:
    """
    Собственный локальный генератор текста на основе N-gram Цепи Маркова.
    Обучается на встроенном текстовом корпусе sldshr без внешних API.
    """
    def __init__(self, n=2):
        self.n = n
        self.chain = defaultdict(list)
        self.words = []

    def fit(self, text_corpus):
        """Обучение цепи Маркова на тексте."""
        # Очистка и разбиение текста на слова
        cleaned = re.sub(r'[^\w\s]', '', text_corpus.lower())
        self.words = [w for w in cleaned.split() if w]
        
        if len(self.words) <= self.n:
            return

        for i in range(len(self.words) - self.n):
            gram = tuple(self.words[i:i + self.n])
            next_word = self.words[i + self.n]
            self.chain[gram].append(next_word)

    def generate(self, seed_words=None, max_length=25):
        """Генерация нового уникального предложения."""
        if not self.chain:
            return "Локальная цепь Маркова еще не обучена."

        # Попытка найти стартовую N-грамму из слов пользователя
        start_gram = None
        if seed_words:
            seed_clean = [w.lower() for w in seed_words if len(w) > 2]
            for i in range(len(seed_clean) - self.n + 1):
                candidate = tuple(seed_clean[i:i + self.n])
                if candidate in self.chain:
                    start_gram = candidate
                    break
        
        # Если совпадений нет, выбираем случайную N-грамму из обучающей выборки
        if not start_gram:
            start_gram = random.choice(list(self.chain.keys()))

        result = list(start_gram)
        current_gram = start_gram

        for _ in range(max_length - self.n):
            if current_gram in self.chain:
                next_word = random.choice(self.chain[current_gram])
                result.append(next_word)
                current_gram = tuple(result[-self.n:])
            else:
                break

        sentence = " ".join(result)
        return sentence.capitalize() + "."

class SldshrSynthesizer:
    """
    Локальный синтаксический движок sldshr.
    Комбинирует найденный ответ интента, данные генератора Маркова и ключевые слова.
    """
    def __init__(self, markov_gen):
        self.markov = markov_gen
        self.prefixes = [
            "⚡ **[sldshr Synthesis]**: ",
            "🧠 **[Локальный ИИ sldshr]**: ",
            "🔍 **[Анализ sldshr Engine]**: ",
            "💡 **[Автономный генератор]**: "
        ]
        self.connectors = [
            "\n\nДополнительно сгенерированный контекст: ",
            "\n\nСвязанная локальная мысль: ",
            "\n\nАлгоритмическое продолжение: "
        ]

    def synthesize(self, base_response, user_text):
        """Синтезирует развернутый локальный ответ."""
        words = re.findall(r'\w+', user_text)
        # Генерируем дополнительную мысль цепью Маркова
        markov_thought = self.markov.generate(seed_words=words, max_length=20)
        
        prefix = random.choice(self.prefixes)
        connector = random.choice(self.connectors)
        
        return f"{prefix}{base_response}{connector}*\"{markov_thought}\"*"

def train_intent_model(intents):
    """Обучение локального классификатора интентов."""
    X = []
    y = []

    for intent in intents:
        for pattern in intent["patterns"]:
            X.append(pattern.lower())
            y.append(intent["tag"])

    if not X:
        return None

    model = make_pipeline(
        TfidfVectorizer(ngram_range=(1, 2), analyzer='word', sublinear_tf=True),
        LogisticRegression(C=4.0, max_iter=250)
    )
    model.fit(X, y)
    return model

def get_bot_response(user_text, model, intents, markov_gen, synthesizer, mode, threshold=0.15):
    """Диспетчер автономных ответов без внешних вызовов."""
    user_text_clean = user_text.lower().strip()

    # Режим 1: Чистая свободная генерация через цепь Маркова
    if mode == "🎲 Чистый Марковский генератор":
        words = re.findall(r'\w+', user_text_clean)
        gen_text = markov_gen.generate(seed_words=words, max_length=30)
        return f"⚡ **[sldshr Markov Chain]**:\n{gen_text}"

    # Классификация намерения через ML
    probabilities = model.predict_proba([user_text_clean])[0]
    max_prob = max(probabilities)
    predicted_tag = model.classes_[probabilities.argmax()]

    # Если уверенность классификатора низкая
    if max_prob < threshold:
        words = re.findall(r'\w+', user_text_clean)
        generated = markov_gen.generate(seed_words=words, max_length=25)
        return (
            f"⚡ **[sldshr AI]**: Точного ответа в базе нет, но моя локальная цепь Маркова сформулировала такую мысль:\n"
            f"> *\"{generated}\"*\n\n"
            f"Вы можете добавить этот вопрос в базу знаний в боковом меню!"
        )

    matched_intent = next((i for i in intents if i["tag"] == predicted_tag), None)
    if not matched_intent:
        return "Тема найдена, но ответы отсутствуют."

    base_resp = random.choice(matched_intent["responses"])

    # Режим 2: Гибридный генеративный синтез
    if mode == "⚡ sldshr Гибридная генерация (Local ML + Markov)":
        return synthesizer.synthesize(base_resp, user_text)
    
    # Режим 3: Точный ответ из базы
    return f"⚡ {base_resp}"

if "intents" not in st.session_state:
    st.session_state.intents = SLDSHR_MASSIVE_INTENTS

if "markov" not in st.session_state:
    st.session_state.markov = SldshrMarkovGenerator(n=2)
    # Пополняем корпус текстами из всех ответов интентов
    full_corpus = SLDSHR_TEXT_CORPUS + "\n"
    for intent in st.session_state.intents:
        full_corpus += "\n".join(intent["responses"]) + "\n"
    st.session_state.markov.fit(full_corpus)

if "model" not in st.session_state:
    st.session_state.model = train_intent_model(st.session_state.intents)

if "synthesizer" not in st.session_state:
    st.session_state.synthesizer = SldshrSynthesizer(st.session_state.markov)

if "messages" not in st.session_state:
    st.session_state.messages = [
        {"role": "assistant", "content": "⚡ Привет! Я **100% автономный sldshr AI Bot**. Я работаю полностью локально на алгоритмах Machine Learning и N-gram Цепях Маркова. Никаких внешних API или ключей!"}
    ]

with st.sidebar:
    st.markdown("<div class='sldshr-badge'>sldshr Standalone Core v3.0</div>", unsafe_allow_html=True)
    st.markdown("<div class='sldshr-status'>🟢 Режим: 100% Offline / Local</div>", unsafe_allow_html=True)
    
    st.title("⚙️ Настройки и Движок")

    generation_mode = st.radio(
        "Локальный режим работы:",
        [
            "⚡ sldshr Гибридная генерация (Local ML + Markov)",
            "🎯 Точный классификатор (Из базы знаний)",
            "🎲 Чистый Марковский генератор"
        ],
        index=0
    )

    st.markdown("---")
    st.subheader("📊 База знаний и Марков")
    
    total_intents = len(st.session_state.intents)
    total_patterns = sum(len(i["patterns"]) for i in st.session_state.intents)
    total_responses = sum(len(i["responses"]) for i in st.session_state.intents)
    markov_states = len(st.session_state.markov.chain)

    col1, col2 = st.columns(2)
    col1.metric("Интентов", total_intents)
    col2.metric("Фраз / Ответов", f"{total_patterns} / {total_responses}")
    st.metric("Состояний цепи Маркова", markov_states)

    st.markdown("---")
    st.subheader("💾 Управление датасетом")
    
    dataset_json = json.dumps(st.session_state.intents, ensure_ascii=False, indent=2)
    st.download_button(
        label="📥 Скачать базу знаний JSON",
        data=dataset_json,
        file_name="sldshr_local_dataset.json",
        mime="application/json"
    )

    # Добавление нового интента
    with st.expander("➕ Добавить новое намерение"):
        new_tag = st.text_input("Тег (название темы)", placeholder="например: algorithms")
        new_patterns = st.text_area("Фразы пользователя (через запятую)", placeholder="что такое сортировка, алгоритмы сортировки")
        new_responses = st.text_area("Ответы бота (через запятую)", placeholder="Сортировка — это упорядочивание элементов...")
        
        if st.button("🚀 Дообучить локальную модель"):
            if new_tag and new_patterns and new_responses:
                p_list = [p.strip() for p in new_patterns.split(",") if p.strip()]
                r_list = [r.strip() for r in new_responses.split(",") if r.strip()]

                st.session_state.intents.append({
                    "tag": new_tag.strip(),
                    "patterns": p_list,
                    "responses": r_list
                })
                
                # Переобучение ML классификатора
                st.session_state.model = train_intent_model(st.session_state.intents)
                
                # Обновление корпуса Маркова
                extra_text = " ".join(r_list)
                st.session_state.markov.fit(extra_text)

                st.success(f"Тема '{new_tag}' успешно добавлена! Локальная модель переобучена.")
                time.sleep(1)
                st.rerun()
            else:
                st.error("Заполните все поля!")

    with st.expander("🔍 Посмотреть текущие данные"):
        st.json(st.session_state.intents)

st.title("⚡ sldshr Autonomous Assistant")
st.caption("Локальный чат-бот от sldshr | Запуск с нуля на Python, scikit-learn и N-gram Markov Chain.")

# Отображение диалога
for message in st.session_state.messages:
    avatar = "⚡" if message["role"] == "assistant" else "👤"
    with st.chat_message(message["role"], avatar=avatar):
        st.markdown(message["content"])

# Ввод сообщения
if prompt := st.chat_input("Напишите запрос sldshr AI..."):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user", avatar="👤"):
        st.markdown(prompt)

    # Генерация локального ответа без задержек API
    bot_response = get_bot_response(
        prompt,
        st.session_state.model,
        st.session_state.intents,
        st.session_state.markov,
        st.session_state.synthesizer,
        generation_mode
    )

    st.session_state.messages.append({"role": "assistant", "content": bot_response})
    with st.chat_message("assistant", avatar="⚡"):
        st.markdown(bot_response)
