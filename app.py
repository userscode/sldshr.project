import streamlit as st
import random
import json
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import make_pipeline

# -----------------------------------------------------------------------------
# 1. УЧЕБНЫЕ МАТЕРИАЛЫ (Датасет интентов / намерений)
# -----------------------------------------------------------------------------
DEFAULT_INTENTS = [
    {
        "tag": "greeting",
        "patterns": ["привет", "здравствуй", "добрый день", "хай", "салют", "доброе утро", "добрый вечер"],
        "responses": ["Привет! Чем могу помочь?", "Здравствуйте! Рад общению.", "Приветствую! О чем поговорим?"]
    },
    {
        "tag": "goodbye",
        "patterns": ["пока", "до свидания", "прощай", "до встречи", "увидимся", "бай"],
        "responses": ["До свидания! Хорошего дня!", "Пока! Обращайтесь еще.", "Всего доброго!"]
    },
    {
        "tag": "thanks",
        "patterns": ["спасибо", "благодарю", "большое спасибо", "выручил", "спас"],
        "responses": ["Пожалуйста! Рад помочь.", "Не за что!", "Всегда к вашим услугам!"]
    },
    {
        "tag": "about_bot",
        "patterns": ["кто ты", "что ты умеешь", "расскажи о себе", "как тебя зовут", "ты кто"],
        "responses": [
            "Я чат-бот, обученный с нуля с помощью TF-IDF и Logistic Regression!",
            "Я локальный бот на Streamlit. Обучаюсь на текстовых шаблонах прямо здесь.",
            "Меня создали без внешних API — моя логика работает прямо в вашем коде!"
        ]
    },
    {
        "tag": "capabilities",
        "patterns": ["что делать", "помощь", "хелп", "как пользоваться", "инструкция"],
        "responses": [
            "Вы можете задавать мне вопросы, приветствовать или обучать новым фразам в боковом меню!",
            "Напишите мне сообщение, и я попытаюсь определить ваше намерение."
        ]
    },
    {
        "tag": "mood",
        "patterns": ["как дела", "как жизнь", "как настроение", "все хорошо"],
        "responses": ["Отлично! Готов к обучению и ответам.", "Всё супер, спасибо за проявленный интерес!"]
    }
]

# -----------------------------------------------------------------------------
# 2. ФУНКЦИИ ДЛЯ ОБУЧЕНИЯ И ПРЕДСКАЗАНИЯ
# -----------------------------------------------------------------------------
def train_model(intents):
    """
    Извлекает тексты и метки из датасета и обучает
    Пайплайн: TF-IDF Vectorizer + Logistic Regression.
    """
    X = []
    y = []

    for intent in intents:
        for pattern in intent["patterns"]:
            X.append(pattern.lower())
            y.append(intent["tag"])

    if not X:
        return None

    # Создаем конвейер из векторизатора и классификатора
    model = make_pipeline(
        TfidfVectorizer(ngram_range=(1, 2), analyzer='word'),
        LogisticRegression(C=10.0, max_iter=200)
    )
    model.fit(X, y)
    return model

def get_bot_response(user_text, model, intents, threshold=0.25):
    """
    Определяет намерение пользователя с помощью обученной модели.
    Если уверенность ниже порога, возвращает шаблонный ответ нераспознанной фразы.
    """
    user_text_clean = user_text.lower().strip()
    
    # Предсказание вероятностей классов
    probabilities = model.predict_proba([user_text_clean])[0]
    max_prob = max(probabilities)
    predicted_tag = model.classes_[probabilities.argmax()]

    if max_prob < threshold:
        return "Извините, я пока не понял ваш вопрос. Попробуйте сформулировать иначе или добавьте эту фразу в обучающие данные!"

    # Находим ответ для предсказанного тега
    for intent in intents:
        if intent["tag"] == predicted_tag:
            return random.choice(intent["responses"])

    return "Интересный вопрос! Но у меня нет подходящего ответа."

# -----------------------------------------------------------------------------
# 3. STREAMLIT ИНТЕРФЕЙС И СОСТОЯНИЕ
# -----------------------------------------------------------------------------
st.set_page_config(page_title="Чат-бот с нуля", page_icon="🤖", layout="wide")

st.title("🤖 Чат-бот на Streamlit (Обучение с нуля)")
st.caption("Бот использует модель TF-IDF + LogisticRegression и не зависит от внешних API.")

# Инициализация состояния
if "intents" not in st.session_state:
    st.session_state.intents = DEFAULT_INTENTS

if "model" not in st.session_state:
    st.session_state.model = train_model(st.session_state.intents)

if "messages" not in st.session_state:
    st.session_state.messages = [
        {"role": "assistant", "content": "Привет! Я бот, обученный с нуля. Напиши мне что-нибудь!"}
    ]

# -----------------------------------------------------------------------------
# 4. БОКОВАЯ ПАНЕЛЬ: Управление обучающими данными
# -----------------------------------------------------------------------------
with st.sidebar:
    st.header("⚙️ Обучение модели")
    st.markdown("Вы можете переобучить бота, добавив новые намерения и варианты фраз.")

    with st.expander("➕ Добавить новое намерение (Intent)"):
        new_tag = st.text_input("Тег (уникальный ID)", placeholder="например: weather")
        new_patterns = st.text_area("Шаблоны фраз (через запятую)", placeholder="какая погода, идет ли дождь, сколько градусов")
        new_responses = st.text_area("Ответы бота (через запятую)", placeholder="Погода отличная!, Возьмите зонт.")
        
        if st.button("Добавить и Переобучить"):
            if new_tag and new_patterns and new_responses:
                patterns_list = [p.strip() for p in new_patterns.split(",") if p.strip()]
                responses_list = [r.strip() for r in new_responses.split(",") if r.strip()]

                # Добавляем в датасет
                st.session_state.intents.append({
                    "tag": new_tag.strip(),
                    "patterns": patterns_list,
                    "responses": responses_list
                })
                
                # Переобучаем модель
                st.session_state.model = train_model(st.session_state.intents)
                st.success(f"Тег '{new_tag}' успешно добавлен! Модель переобучена.")
            else:
                st.error("Пожалуйста, заполните все поля!")

    st.subheader("📚 Текущий датасет")
    st.json(st.session_state.intents)

# -----------------------------------------------------------------------------
# 5. ДИАЛОГОВЫЙ ИНТЕРФЕЙС
# -----------------------------------------------------------------------------
# Отображение истории сообщений
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# Поле ввода сообщения
if prompt := st.chat_input("Напишите сообщение..."):
    # Добавляем сообщение пользователя
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    # Генерация ответа модели
    response = get_bot_response(
        prompt, 
        st.session_state.model, 
        st.session_state.intents
    )

    # Добавляем ответ бота
    st.session_state.messages.append({"role": "assistant", "content": response})
    with st.chat_message("assistant"):
        st.markdown(response)
