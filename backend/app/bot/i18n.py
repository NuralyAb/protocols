"""Minimal i18n catalogue for the Telegram bot."""
from __future__ import annotations

from typing import Literal

Lang = Literal["ru", "kk", "en"]

_CATALOG: dict[str, dict[Lang, str]] = {
    "welcome": {
        "ru": (
            "Привет! Я бот AI-Протоколист.\n"
            "Я умею присылать протоколы заседаний и отвечать на вопросы по стенограмме.\n\n"
            "Сначала войдите: /login email пароль\n"
            "Справка: /help"
        ),
        "kk": (
            "Сәлем! Мен AI-Хаттамашы ботымын.\n"
            "Жиналыс хаттамаларын жіберіп, стенограмма бойынша сұрақтарға жауап беремін.\n\n"
            "Алдымен кіріңіз: /login email құпия_сөз\n"
            "Анықтама: /help"
        ),
        "en": (
            "Hi! I'm the AI Meeting Protocolist bot.\n"
            "I send meeting protocols and answer questions about the transcript.\n\n"
            "Sign in first: /login email password\n"
            "Help: /help"
        ),
    },
    "help": {
        "ru": (
            "Команды:\n"
            "/login email пароль — войти\n"
            "/logout — выйти\n"
            "/lang ru|kk|en — язык ответов\n"
            "/last — последние сессии\n"
            "/use DDMMYYYY-HHMM — выбрать сессию\n"
            "/protocol — сгенерировать формальный протокол (PDF)\n"
            "/report — то же, что /protocol\n"
            "/insights — анализ встречи (для неформальных разговоров)\n"
            "/change — сменить сессию (повторный ввод ID)\n"
            "/help — эта справка\n\n"
            "После /use пришлите любой вопрос обычным сообщением — я отвечу по транскрипту."
        ),
        "kk": (
            "Командалар:\n"
            "/login email құпия_сөз — кіру\n"
            "/logout — шығу\n"
            "/lang ru|kk|en — жауап тілі\n"
            "/last — соңғы сессиялар\n"
            "/use DDMMYYYY-HHMM — сессия таңдау\n"
            "/protocol — ресми хаттама (PDF)\n"
            "/report — /protocol-пен бірдей\n"
            "/insights — жиналыс талдауы (еркін әңгіме үшін)\n"
            "/change — сессияны өзгерту\n"
            "/help — осы анықтама\n\n"
            "/use-тан кейін кез-келген сұрақ жіберіңіз — стенограмма бойынша жауап беремін."
        ),
        "en": (
            "Commands:\n"
            "/login email password — sign in\n"
            "/logout — sign out\n"
            "/lang ru|kk|en — answer language\n"
            "/last — recent sessions\n"
            "/use DDMMYYYY-HHMM — pick a session\n"
            "/protocol — formal protocol (PDF)\n"
            "/report — same as /protocol\n"
            "/insights — meeting analysis (for casual talks)\n"
            "/change — switch session\n"
            "/help — this help\n\n"
            "After /use, send any question — I'll answer from the transcript."
        ),
    },
    "login_usage": {
        "ru": "Использование: /login email пароль",
        "kk": "Қолдану: /login email құпия_сөз",
        "en": "Usage: /login email password",
    },
    "login_ok": {
        "ru": "Вход выполнен ✅. Теперь /last чтобы увидеть сессии или /use DDMMYYYY-HHMM.",
        "kk": "Кіру сәтті ✅. Енді /last немесе /use DDMMYYYY-HHMM.",
        "en": "Signed in ✅. Try /last to see sessions or /use DDMMYYYY-HHMM.",
    },
    "login_fail": {
        "ru": "Не удалось войти: {error}",
        "kk": "Кіру сәтсіз: {error}",
        "en": "Sign in failed: {error}",
    },
    "not_authed": {
        "ru": "Сначала войдите: /login email пароль",
        "kk": "Алдымен кіріңіз: /login email құпия_сөз",
        "en": "Sign in first: /login email password",
    },
    "logged_out": {
        "ru": "Вы вышли из аккаунта.",
        "kk": "Аккаунттан шықтыңыз.",
        "en": "Signed out.",
    },
    "lang_usage": {
        "ru": "Использование: /lang ru|kk|en",
        "kk": "Қолдану: /lang ru|kk|en",
        "en": "Usage: /lang ru|kk|en",
    },
    "lang_set": {
        "ru": "Язык ответов: RU",
        "kk": "Жауап тілі: KK",
        "en": "Answer language: EN",
    },
    "use_usage": {
        "ru": "Использование: /use DDMMYYYY-HHMM (код сессии)",
        "kk": "Қолдану: /use DDMMYYYY-HHMM (сессия коды)",
        "en": "Usage: /use DDMMYYYY-HHMM (session code)",
    },
    "use_ok": {
        "ru": "Сессия выбрана: *{title}* (код `{fid}`). Задавайте вопросы — отвечу по транскрипту.",
        "kk": "Сессия таңдалды: *{title}* (код `{fid}`). Сұрақтарыңызды қойыңыз.",
        "en": "Session selected: *{title}* (code `{fid}`). Ask anything — I'll answer from the transcript.",
    },
    "not_found": {
        "ru": "Сессия не найдена. Проверьте код (DDMMYYYY-HHMM).",
        "kk": "Сессия табылмады. Кодты тексеріңіз (DDMMYYYY-HHMM).",
        "en": "Session not found. Check the code (DDMMYYYY-HHMM).",
    },
    "no_session": {
        "ru": "Сначала выберите сессию: /use DDMMYYYY-HHMM",
        "kk": "Алдымен сессияны таңдаңыз: /use DDMMYYYY-HHMM",
        "en": "Pick a session first: /use DDMMYYYY-HHMM",
    },
    "last_empty": {
        "ru": "У вас пока нет сессий.",
        "kk": "Сізде әзірге сессиялар жоқ.",
        "en": "You have no sessions yet.",
    },
    "last_header": {
        "ru": "Последние сессии:",
        "kk": "Соңғы сессиялар:",
        "en": "Recent sessions:",
    },
    "no_template": {
        "ru": "В системе нет шаблонов протокола.",
        "kk": "Хаттама үлгілері жоқ.",
        "en": "No protocol templates available.",
    },
    "protocol_generating": {
        "ru": "Генерирую протокол… ~20 сек.",
        "kk": "Хаттама жасалуда… ~20 сек.",
        "en": "Generating protocol… ~20 s.",
    },
    "protocol_fail": {
        "ru": "Не удалось сгенерировать: {error}",
        "kk": "Жасалмады: {error}",
        "en": "Generation failed: {error}",
    },
    "qa_thinking": {
        "ru": "Думаю…",
        "kk": "Ойланудамын…",
        "en": "Thinking…",
    },
    "qa_fail": {
        "ru": "Ошибка: {error}",
        "kk": "Қате: {error}",
        "en": "Error: {error}",
    },
    "insights_header": {
        "ru": "📊 Анализ встречи",
        "kk": "📊 Жиналыс талдауы",
        "en": "📊 Meeting insights",
    },
    "insights_speakers": {
        "ru": "*Спикеры:*",
        "kk": "*Спикерлер:*",
        "en": "*Speakers:*",
    },
    "insights_top_words": {
        "ru": "*Ключевые слова:*",
        "kk": "*Кілт сөздер:*",
        "en": "*Top words:*",
    },
    "insights_moments": {
        "ru": "*Ключевые моменты:*",
        "kk": "*Негізгі сәттер:*",
        "en": "*Key moments:*",
    },
    "insights_empty": {
        "ru": "В транскрипте пока недостаточно данных для анализа.",
        "kk": "Талдау үшін деректер жеткіліксіз.",
        "en": "Not enough transcript data for insights yet.",
    },
    "change_prompt": {
        "ru": "Отправьте /use DDMMYYYY-HHMM чтобы выбрать другую сессию, или /last для списка.",
        "kk": "Басқа сессия үшін /use DDMMYYYY-HHMM немесе /last жіберіңіз.",
        "en": "Send /use DDMMYYYY-HHMM for another session or /last to list.",
    },
}


def t(key: str, lang: Lang, **kw) -> str:
    entry = _CATALOG.get(key)
    if not entry:
        return key
    msg = entry.get(lang) or entry.get("ru") or key
    try:
        return msg.format(**kw) if kw else msg
    except KeyError:
        return msg
