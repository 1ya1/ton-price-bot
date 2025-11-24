import os
import telebot
from telebot import types
import requests
import time
import threading
import json
import hashlib
from datetime import datetime
from flask import Flask, render_template_string
import sqlite3

# ================== НАСТРОЙКИ ==================
BOT_TOKEN = os.environ.get('BOT_TOKEN', '8455345722:AAFJ_DqCuv-fWRQZJ6XlQm0DBPOUz3v9MO0')
bot = telebot.TeleBot(BOT_TOKEN)


# ================== БАЗА ДАННЫХ ==================
def init_db():
    """Инициализация базы данных"""
    conn = sqlite3.connect('bot_data.db', check_same_thread=False)
    c = conn.cursor()

    # Таблица пользователей
    c.execute('''CREATE TABLE IF NOT EXISTS users
                 (user_id INTEGER PRIMARY KEY, settings TEXT, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')

    # Таблица для предыдущей цены
    c.execute('''CREATE TABLE IF NOT EXISTS price_data
                 (id INTEGER PRIMARY KEY, previous_price REAL, updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')

    conn.commit()
    conn.close()
    print("✅ База данных инициализирована")


def save_user_settings(user_id, settings):
    """Сохранение настроек пользователя"""
    try:
        conn = sqlite3.connect('bot_data.db', check_same_thread=False)
        c = conn.cursor()
        c.execute("REPLACE INTO users (user_id, settings) VALUES (?, ?)",
                  (user_id, json.dumps(settings)))
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"❌ Ошибка сохранения настроек: {e}")


def load_user_settings(user_id):
    """Загрузка настроек пользователя"""
    try:
        conn = sqlite3.connect('bot_data.db', check_same_thread=False)
        c = conn.cursor()
        c.execute("SELECT settings FROM users WHERE user_id = ?", (user_id,))
        result = c.fetchone()
        conn.close()

        if result:
            return json.loads(result[0])
        return None
    except Exception as e:
        print(f"❌ Ошибка загрузки настроек: {e}")
        return None


def load_all_settings():
    """Загрузка всех настроек"""
    try:
        conn = sqlite3.connect('bot_data.db', check_same_thread=False)
        c = conn.cursor()
        c.execute("SELECT user_id, settings FROM users")
        rows = c.fetchall()
        conn.close()

        settings = {}
        for user_id, settings_json in rows:
            settings[user_id] = json.loads(settings_json)
        return settings
    except Exception as e:
        print(f"❌ Ошибка загрузки всех настроек: {e}")
        return {}


def save_previous_price(price):
    """Сохранение предыдущей цены"""
    try:
        conn = sqlite3.connect('bot_data.db', check_same_thread=False)
        c = conn.cursor()
        c.execute("REPLACE INTO price_data (id, previous_price) VALUES (1, ?)", (price,))
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"❌ Ошибка сохранения цены: {e}")


def load_previous_price():
    """Загрузка предыдущей цены"""
    try:
        conn = sqlite3.connect('bot_data.db', check_same_thread=False)
        c = conn.cursor()
        c.execute("SELECT previous_price FROM price_data WHERE id = 1")
        result = c.fetchone()
        conn.close()

        return result[0] if result else None
    except Exception as e:
        print(f"❌ Ошибка загрузки цены: {e}")
        return None


# ================== ИНИЦИАЛИЗАЦИЯ ==================
init_db()
user_settings = load_all_settings()
previous_price = load_previous_price()

# ================== ВЕБ-СЕРВЕР ДЛЯ RENDER ==================
app = Flask(__name__)


@app.route('/')
def home():
    """Главная страница статуса"""
    users_count = len(user_settings)
    active_users = sum(1 for settings in user_settings.values() if settings.get('active', True))

    html_template = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>TON Price Bot</title>
        <meta charset="utf-8">
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <style>
            body { 
                font-family: 'Arial', sans-serif; 
                margin: 0; 
                padding: 20px; 
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                color: white;
                min-height: 100vh;
            }
            .container { 
                max-width: 800px; 
                margin: 0 auto; 
                background: rgba(255,255,255,0.1);
                padding: 30px;
                border-radius: 15px;
                backdrop-filter: blur(10px);
            }
            .status { 
                color: #4CAF50; 
                font-weight: bold; 
                font-size: 1.2em;
            }
            .info { 
                background: rgba(255,255,255,0.2); 
                padding: 20px; 
                border-radius: 10px; 
                margin: 15px 0;
            }
            .stats {
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
                gap: 15px;
                margin: 20px 0;
            }
            .stat-card {
                background: rgba(255,255,255,0.15);
                padding: 15px;
                border-radius: 10px;
                text-align: center;
            }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>🤖 TON Price Bot</h1>
            <div class="info">
                <p class="status">✅ Бот работает нормально</p>
                <p>📍 Режим: Cloud Deployment (Render.com)</p>
                <p>🕐 Время сервера: {{ current_time }}</p>
            </div>

            <div class="stats">
                <div class="stat-card">
                    <h3>👥 Пользователей</h3>
                    <p style="font-size: 2em; margin: 10px 0;">{{ users_count }}</p>
                </div>
                <div class="stat-card">
                    <h3>🔔 Активных уведомлений</h3>
                    <p style="font-size: 2em; margin: 10px 0;">{{ active_users }}</p>
                </div>
                <div class="stat-card">
                    <h3>💰 Последняя цена</h3>
                    <p style="font-size: 2em; margin: 10px 0;">
                        {% if previous_price %}${{ "%.4f"|format(previous_price) }}{% else %}N/A{% endif %}
                    </p>
                </div>
            </div>

            <div class="info">
                <h3>📊 Статистика системы</h3>
                <p>🔄 Мониторинг цен: Активен</p>
                <p>💾 База данных: SQLite</p>
                <p>🌐 Хостинг: Render.com (Бесплатный)</p>
                <p>⏰ Аптайм: 24/7</p>
            </div>
        </div>
    </body>
    </html>
    """

    return render_template_string(html_template,
                                  users_count=users_count,
                                  active_users=active_users,
                                  previous_price=previous_price,
                                  current_time=datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC')
                                  )


@app.route('/health')
def health():
    """Простая проверка здоровья для UptimeRobot"""
    return "OK", 200


def run_flask():
    """Запуск Flask сервера"""
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port, debug=False)


# ================== ОСНОВНОЙ КОД БОТА ==================
# Инициализация бота
bot = telebot.TeleBot('8455345722:AAFJ_DqCuv-fWRQZJ6XlQm0DBPOUz3v9MO0')

# Хранилище пользовательских настроек
user_settings = {}
previous_price = None

# Кэш для данных
cache = {
    'price': {
        'data': None,
        'timestamp': None,
        'ttl': 30  # 30 секунд
    }
}

# Защита от перегрузки
rate_limits = {}
REQUEST_LIMIT = 25  # Максимум 25 запросов в минуту на пользователя
REQUEST_WINDOW = 20  # Окно в секундах

# API для получения курса TON
API_URLS = [
    "https://api.coingecko.com/api/v3/simple/price?ids=the-open-network&vs_currencies=usd,rub&include_24hr_change=true",
    "https://api.coingecko.com/api/v3/simple/price?ids=toncoin&vs_currencies=usd,rub&include_24hr_change=true"
]

# Файл для сохранения данных
DATA_FILE = "bot_data.json"

# Тексты на разных языках
TEXTS = {
    'ru': {
        'main_menu': "🤖 Бот для отслеживания курса Toncoin\n\nЯ буду уведомлять вас о значительных изменениях курса TON в реальном времени.\nТакже вы можете быстро открыть официальный кошелек TON.",
        'settings': "⚙️ **Настройки уведомлений**\n\n",
        'current_price': "💰 **Toncoin (TON)**\n",
        'wallet': "👛 **Официальный TON кошелек**\n\n",
        'wallet_info': "ℹ️ **О кошельке TON**\n\n",
        'buy_ton': "💳 **Покупка TON**\n\n",
        'stats': "📊 **Статистика мониторинга**\n\n",
        'calculator': "🧮 **Калькулятор TON**\n\n",
        'notifications_on': "🔔 Уведомления ВКЛ",
        'notifications_off': "🔕 Уведомления ВЫКЛ",
        'set_threshold_up': "📈 Введите порог для уведомления о росте (в %):\n\nПример: 2.5 (для 2.5% роста)",
        'set_threshold_down': "📉 Введите порог для уведомления о падении (в %):\n\nПример: 2.5 (для 2.5% падения)",
        'threshold_set': "✅ Порог установлен: {}%",
        'error_number': "❌ Пожалуйста, введите число:",
        'error_positive': "❌ Значение должно быть больше 0",
        'error_general': "❌ Произошла ошибка, попробуйте снова",
        'price_updated': "✅ Курс актуален",
        'rate_limit': "⏰ Слишком много запросов. Подождите немного.",
        'api_error': "🔧 Временные проблемы с API. Используем кэшированные данные.",
        'currency_usd': "🇺🇸 Доллары (USD)",
        'currency_rub': "🇷🇺 Рубли (RUB)",
        'language_ru': "🇷🇺 Русский",
        'language_en': "🇺🇸 English",
        'menu_settings': "⚙️ Настройки",
        'menu_price': "💰 Курс",
        'menu_wallet': "👛 Кошелек",
        'menu_stats': "📊 Статистика",
        'menu_calculator': "🧮 Калькулятор",
        'menu_toggle': "🔔 Вкл/Выкл",
        'menu_language': "🌐 Язык",
        'menu_currency': "💵 Валюта",
        'settings_threshold_up': "📈 Порог роста",
        'settings_threshold_down': "📉 Порог падения",
        'settings_language': "🌐 Язык",
        'settings_currency': "💵 Валюта",
        'back': "🔙 Назад",
        'refresh': "🔄 Обновить",
        'calculate_sell': "💰 Продать TON",
        'enter_ton_amount': "💎 Введите количество TON для продажи:",
        'calculation_result': "💰 **Результат расчета**\n\n",
        'wallet_features': "✅ **Безопасное хранение**\n✅ **Мгновенные переводы**\n✅ **Покупка TON через карту**\n✅ **Низкие комиссии**\n✅ **Интеграция с Telegram**",
        'buy_features': "✅ **Банковские карты** (Visa/Mastercard)\n✅ **Быстрое пополнение**\n✅ **Лучший курс**\n✅ **Без скрытых комиссий**",
        'wallet_security': "🔒 **Безопасность**\n• Ключи хранятся на вашем устройстве\n• Шифрование на уровне Telegram\n• Резервные копии в облаке",
        'wallet_convenience': "⚡ **Удобство**\n• Мгновенные транзакции\n• Покупка TON через карту\n• Низкие комиссии сети\n• Интеграция с dApps",
        'wallet_functions': "💎 **Функции**\n• Отправка/получение ТОН\n• Стейкинг\n• NFT коллекции\n• Jetton токены"
    },
    'en': {
        'main_menu': "🤖 Bot for tracking Toncoin price\n\nI will notify you about significant TON price changes in real time.\nYou can also quickly open the official TON wallet.",
        'settings': "⚙️ **Notification Settings**\n\n",
        'current_price': "💰 **Toncoin (TON)**\n",
        'wallet': "👛 **Official TON Wallet**\n\n",
        'wallet_info': "ℹ️ **About TON Wallet**\n\n",
        'buy_ton': "💳 **Buy TON**\n\n",
        'stats': "📊 **Monitoring Statistics**\n\n",
        'calculator': "🧮 **TON Calculator**\n\n",
        'notifications_on': "🔔 Notifications ON",
        'notifications_off': "🔕 Notifications OFF",
        'set_threshold_up': "📈 Enter threshold for growth notification (in %):\n\nExample: 2.5 (for 2.5% growth)",
        'set_threshold_down': "📉 Enter threshold for drop notification (in %):\n\nExample: 2.5 (for 2.5% drop)",
        'threshold_set': "✅ Threshold set: {}%",
        'error_number': "❌ Please enter a number:",
        'error_positive': "❌ Value must be greater than 0",
        'error_general': "❌ An error occurred, please try again",
        'price_updated': "✅ Price is up to date",
        'rate_limit': "⏰ Too many requests. Please wait a bit.",
        'api_error': "🔧 Temporary API issues. Using cached data.",
        'currency_usd': "🇺🇸 Dollars (USD)",
        'currency_rub': "🇷🇺 Rubles (RUB)",
        'language_ru': "🇷🇺 Russian",
        'language_en': "🇺🇸 English",
        'menu_settings': "⚙️ Settings",
        'menu_price': "💰 Price",
        'menu_wallet': "👛 Wallet",
        'menu_stats': "📊 Stats",
        'menu_calculator': "🧮 Calculator",
        'menu_toggle': "🔔 Toggle",
        'menu_language': "🌐 Language",
        'menu_currency': "💵 Currency",
        'settings_threshold_up': "📈 Growth threshold",
        'settings_threshold_down': "📉 Drop threshold",
        'settings_language': "🌐 Language",
        'settings_currency': "💵 Currency",
        'back': "🔙 Back",
        'refresh': "🔄 Refresh",
        'calculate_sell': "💰 Sell TON",
        'enter_ton_amount': "💎 Enter TON amount to sell:",
        'calculation_result': "💰 **Calculation Result**\n\n",
        'wallet_features': "✅ **Secure storage**\n✅ **Instant transfers**\n✅ **Buy TON with card**\n✅ **Low fees**\n✅ **Telegram integration**",
        'buy_features': "✅ **Bank cards** (Visa/Mastercard)\n✅ **Fast top-up**\n✅ **Best rate**\n✅ **No hidden fees**",
        'wallet_security': "🔒 **Security**\n• Keys stored on your device\n• Telegram-level encryption\n• Cloud backups",
        'wallet_convenience': "⚡ **Convenience**\n• Instant transactions\n• Buy TON with card\n• Low network fees\n• dApps integration",
        'wallet_functions': "💎 **Functions**\n• Send/receive TON\n• Staking\n• NFT collections\n• Jetton tokens"
    }
}


def get_text(user_id, key):
    """Получить текст на нужном языке"""
    lang = user_settings.get(user_id, {}).get('language', 'ru')
    return TEXTS[lang].get(key, key)


def save_data():
    """Сохранение данных в файл"""
    try:
        data = {
            'user_settings': user_settings,
            'previous_price': previous_price
        }
        with open(DATA_FILE, 'w') as f:
            json.dump(data, f)
    except Exception as e:
        print(f"Ошибка сохранения данных: {e}")


def load_data():
    """Загрузка данных из файла"""
    global user_settings, previous_price
    try:
        if os.path.exists(DATA_FILE):
            with open(DATA_FILE, 'r') as f:
                data = json.load(f)
                user_settings = data.get('user_settings', {})
                previous_price = data.get('previous_price', None)
                print("Данные загружены успешно")
    except Exception as e:
        print(f"Ошибка загрузки данных: {e}")


def check_rate_limit(user_id):
    """Проверка ограничения запросов"""
    now = time.time()
    user_hash = hashlib.md5(str(user_id).encode()).hexdigest()  # Анонимизируем ID

    if user_hash not in rate_limits:
        rate_limits[user_hash] = []

    # Удаляем старые запросы
    rate_limits[user_hash] = [req_time for req_time in rate_limits[user_hash]
                              if now - req_time < REQUEST_WINDOW]

    # Проверяем лимит
    if len(rate_limits[user_hash]) >= REQUEST_LIMIT:
        return False

    # Добавляем текущий запрос
    rate_limits[user_hash].append(now)
    return True


def get_ton_price():
    """Получение текущего курса TON с кэшированием"""
    # Проверяем кэш
    if (cache['price']['data'] and
            cache['price']['timestamp'] and
            (time.time() - cache['price']['timestamp']) < cache['price']['ttl']):
        print("Используем кэшированные данные курса")
        return cache['price']['data']

    # Если кэш устарел, делаем новый запрос
    for api_url in API_URLS:
        try:
            print(f"Запрос курса с API: {api_url}")
            response = requests.get(api_url, timeout=10)
            data = response.json()

            # Пробуем разные ключи
            ton_data = None
            for key in ['the-open-network', 'toncoin', 'ton']:
                if key in data:
                    ton_data = data[key]
                    break

            if ton_data and 'usd' in ton_data:
                price_usd = ton_data['usd']
                price_rub = ton_data.get('rub', price_usd * 90)
                change_24h = ton_data.get('usd_24h_change', 0)

                result = (price_usd, price_rub, change_24h)

                # Сохраняем в кэш
                cache['price']['data'] = result
                cache['price']['timestamp'] = time.time()

                print(f"Курс получен: ${price_usd:.4f}")
                return result

        except Exception as e:
            print(f"Ошибка API {api_url}: {e}")
            continue

    # Если все API не сработали, используем кэш или заглушку
    if cache['price']['data']:
        print("Используем кэш из-за ошибок API")
        return cache['price']['data']

    print("Используем заглушку")
    return 1.50, 135.0, 0.0


def calculate_sell_value(ton_amount, currency='usd'):
    """Расчет стоимости продажи TON"""
    try:
        price_usd, price_rub, change_24h = get_ton_price()

        if currency == 'usd':
            price = price_usd
            currency_symbol = '$'
        else:
            price = price_rub
            currency_symbol = '₽'

        # Рассчитываем общую стоимость
        total_value = ton_amount * price

        # Рассчитываем комиссию (примерно 0.5-1%)
        fee_percentage = 0.007  # 0.7% комиссия
        fee_amount = total_value * fee_percentage
        net_value = total_value - fee_amount

        return {
            'total_value': total_value,
            'net_value': net_value,
            'fee_amount': fee_amount,
            'price': price,
            'currency_symbol': currency_symbol,
            'fee_percentage': fee_percentage * 100
        }
    except Exception as e:
        print(f"Ошибка расчета: {e}")
        return None


@bot.message_handler(commands=['start'])
def start(message):
    """Обработчик команды /start"""
    user_id = message.from_user.id

    # Проверяем ограничение запросов
    if not check_rate_limit(user_id):
        bot.send_message(message.chat.id, get_text(user_id, 'rate_limit'))
        return

    if user_id not in user_settings:
        user_settings[user_id] = {
            'threshold_up': 3.0,
            'threshold_down': 3.0,
            'active': True,
            'language': 'ru',
            'currency': 'usd'
        }
        save_data()

    keyboard = types.InlineKeyboardMarkup()
    keyboard.row(
        types.InlineKeyboardButton(get_text(user_id, 'menu_settings'), callback_data="settings"),
        types.InlineKeyboardButton(get_text(user_id, 'menu_price'), callback_data="current_price")
    )
    keyboard.row(
        types.InlineKeyboardButton(get_text(user_id, 'menu_wallet'), callback_data="open_wallet"),
        types.InlineKeyboardButton(get_text(user_id, 'menu_calculator'), callback_data="calculator")
    )
    keyboard.row(types.InlineKeyboardButton(get_text(user_id, 'menu_toggle'), callback_data="toggle"))

    bot.send_message(
        message.chat.id,
        get_text(user_id, 'main_menu'),
        reply_markup=keyboard
    )


@bot.callback_query_handler(func=lambda call: True)
def callback_handler(call):
    """Обработчик нажатий на кнопки"""
    user_id = call.from_user.id

    # Проверяем ограничение запросов
    if not check_rate_limit(user_id):
        bot.answer_callback_query(call.id, get_text(user_id, 'rate_limit'))
        return

    try:
        if call.data == "current_price":
            show_current_price(call)
        elif call.data == "settings":
            show_settings(call)
        elif call.data == "toggle":
            toggle_notifications(call)
        elif call.data == "main_menu":
            show_main_menu(call)
        elif call.data == "calculator":
            show_calculator_menu(call)
        elif call.data == "calculate_sell":
            start_sell_calculation(call)
        elif call.data == "set_up":
            set_threshold(call, 'up')
        elif call.data == "set_down":
            set_threshold(call, 'down')
        elif call.data == "open_wallet":
            open_wallet(call)
        elif call.data == "wallet_info":
            show_wallet_info(call)
        elif call.data == "buy_ton":
            buy_ton(call)
        elif call.data == "stats":
            show_stats(call)
        elif call.data == "language_settings":
            show_language_settings(call)
        elif call.data == "currency_settings":
            show_currency_settings(call)
        elif call.data.startswith("set_lang_"):
            set_language(call)
        elif call.data.startswith("set_curr_"):
            set_currency(call)
    except Exception as e:
        print(f"Ошибка в callback_handler: {e}")
        try:
            bot.answer_callback_query(call.id, get_text(user_id, 'error_general'))
        except:
            pass


def show_calculator_menu(call):
    """Меню калькулятора"""
    user_id = call.from_user.id

    try:
        keyboard = types.InlineKeyboardMarkup()
        keyboard.row(types.InlineKeyboardButton(get_text(user_id, 'calculate_sell'), callback_data="calculate_sell"))
        keyboard.row(types.InlineKeyboardButton(get_text(user_id, 'back'), callback_data="main_menu"))

        message = (
            f"{get_text(user_id, 'calculator')}"
            f"🧮 **Калькулятор стоимости TON**\n\n"
            f"С помощью этого калькулятора вы можете:\n\n"
            f"• 📊 Рассчитать стоимость ваших TON\n"
            f"• 💰 Узнать сумму после комиссий\n"
            f"• 📈 Оценить прибыль от продажи\n\n"
            f"Нажмите кнопку ниже чтобы начать расчет:"
        )

        bot.edit_message_text(
            message,
            call.message.chat.id,
            call.message.message_id,
            reply_markup=keyboard,
            parse_mode='Markdown'
        )
    except Exception as e:
        print(f"Ошибка в show_calculator_menu: {e}")
        bot.answer_callback_query(call.id, get_text(user_id, 'error_general'))


def start_sell_calculation(call):
    """Начало расчета продажи"""
    user_id = call.from_user.id

    try:
        if user_id not in user_settings:
            user_settings[user_id] = {}

        user_settings[user_id]['awaiting_calculation'] = True
        save_data()

        # Получаем текущий курс для справки
        price_usd, price_rub, change_24h = get_ton_price()
        currency = user_settings[user_id].get('currency', 'usd')
        current_price = price_usd if currency == 'usd' else price_rub
        currency_symbol = '$' if currency == 'usd' else '₽'

        message = (
            f"{get_text(user_id, 'enter_ton_amount')}\n\n"
            f"💡 *Текущий курс:* {currency_symbol}{current_price:.4f}\n"
            f"📊 *Примеры:*\n"
            f"• 10 TON = {currency_symbol}{10 * current_price:.2f}\n"
            f"• 100 TON = {currency_symbol}{100 * current_price:.2f}\n"
            f"• 1000 TON = {currency_symbol}{1000 * current_price:.2f}\n\n"
            f"Введите количество TON:"
        )

        bot.edit_message_text(
            message,
            call.message.chat.id,
            call.message.message_id,
            parse_mode='Markdown'
        )
    except Exception as e:
        print(f"Ошибка в start_sell_calculation: {e}")
        bot.answer_callback_query(call.id, get_text(user_id, 'error_general'))


def calculate_and_show_result(user_id, chat_id, ton_amount):
    """Расчет и показ результата"""
    try:
        currency = user_settings.get(user_id, {}).get('currency', 'usd')
        calculation = calculate_sell_value(ton_amount, currency)

        if not calculation:
            bot.send_message(chat_id, get_text(user_id, 'error_general'))
            return

        currency_symbol = calculation['currency_symbol']

        message = (
            f"{get_text(user_id, 'calculation_result')}"
            f"💎 **Количество TON:** {ton_amount:.2f}\n"
            f"💰 **Текущая цена:** {currency_symbol}{calculation['price']:.4f}\n\n"
            f"📊 **Общая стоимость:** {currency_symbol}{calculation['total_value']:.2f}\n"
            f"📉 **Комиссия ({calculation['fee_percentage']:.1f}%):** {currency_symbol}{calculation['fee_amount']:.2f}\n"
            f"💵 **К получению:** {currency_symbol}{calculation['net_value']:.2f}\n\n"
            f"💡 *Расчет включает примерную комиссию сети*"
        )

        keyboard = types.InlineKeyboardMarkup()
        keyboard.row(types.InlineKeyboardButton(get_text(user_id, 'calculate_sell'), callback_data="calculate_sell"))
        keyboard.row(types.InlineKeyboardButton(get_text(user_id, 'menu_price'), callback_data="current_price"))
        keyboard.row(types.InlineKeyboardButton(get_text(user_id, 'back'), callback_data="main_menu"))

        bot.send_message(
            chat_id,
            message,
            reply_markup=keyboard,
            parse_mode='Markdown'
        )

    except Exception as e:
        print(f"Ошибка показа результата: {e}")
        bot.send_message(chat_id, get_text(user_id, 'error_general'))


def show_current_price(call):
    """Показать текущий курс"""
    user_id = call.from_user.id

    try:
        price_usd, price_rub, change_24h = get_ton_price()

        currency = user_settings.get(user_id, {}).get('currency', 'usd')
        price = price_usd if currency == 'usd' else price_rub
        currency_symbol = '$' if currency == 'usd' else '₽'

        change_emoji = "📈" if change_24h > 0 else "📉"
        current_time = datetime.now().strftime("%H:%M:%S")

        # Проверяем, используем ли мы кэшированные данные
        cache_info = ""
        if cache['price']['timestamp']:
            cache_age = time.time() - cache['price']['timestamp']
            if cache_age > 60:  # Если данные старше 1 минуты
                cache_info = "\n🔧 *Используются кэшированные данные*"

        message = (
            f"{get_text(user_id, 'current_price')}"
            f"💵 {('Цена' if get_text(user_id, 'language') == 'ru' else 'Price')}: {currency_symbol}{price:.4f}\n"
            f"{change_emoji} {('Изменение за 24ч' if get_text(user_id, 'language') == 'ru' else '24h change')}: {change_24h:.2f}%\n"
            f"🕐 {('Обновлено' if get_text(user_id, 'language') == 'ru' else 'Updated')}: {current_time}"
            f"{cache_info}\n\n"
            f"🧮 {('Используйте калькулятор для расчета стоимости' if get_text(user_id, 'language') == 'ru' else 'Use calculator to calculate value')}"
        )

        keyboard = types.InlineKeyboardMarkup()
        keyboard.row(types.InlineKeyboardButton(get_text(user_id, 'refresh'), callback_data="current_price"))
        keyboard.row(types.InlineKeyboardButton(get_text(user_id, 'menu_calculator'), callback_data="calculator"))
        keyboard.row(types.InlineKeyboardButton(get_text(user_id, 'menu_wallet'), callback_data="open_wallet"))
        keyboard.row(types.InlineKeyboardButton(get_text(user_id, 'back'), callback_data="main_menu"))

        try:
            bot.edit_message_text(
                message,
                call.message.chat.id,
                call.message.message_id,
                reply_markup=keyboard,
                parse_mode='Markdown'
            )
        except Exception as edit_error:
            if "message is not modified" in str(edit_error):
                bot.answer_callback_query(call.id, get_text(user_id, 'price_updated'))
            else:
                bot.send_message(
                    call.message.chat.id,
                    message,
                    reply_markup=keyboard,
                    parse_mode='Markdown'
                )
    except Exception as e:
        print(f"Ошибка в show_current_price: {e}")
        bot.answer_callback_query(call.id, get_text(user_id, 'error_general'))


def show_settings(call):
    """Настройки уведомлений"""
    user_id = call.from_user.id

    try:
        settings = user_settings.get(user_id, {})

        keyboard = types.InlineKeyboardMarkup()
        keyboard.row(
            types.InlineKeyboardButton(get_text(user_id, 'settings_threshold_up'), callback_data="set_up"),
            types.InlineKeyboardButton(get_text(user_id, 'settings_threshold_down'), callback_data="set_down")
        )
        keyboard.row(
            types.InlineKeyboardButton(get_text(user_id, 'settings_language'), callback_data="language_settings"),
            types.InlineKeyboardButton(get_text(user_id, 'settings_currency'), callback_data="currency_settings")
        )
        keyboard.row(types.InlineKeyboardButton(get_text(user_id, 'back'), callback_data="main_menu"))

        message = (
            f"{get_text(user_id, 'settings')}"
            f"📈 {('Уведомлять при росте' if get_text(user_id, 'language') == 'ru' else 'Notify on growth')}: {settings.get('threshold_up', 3.0)}%\n"
            f"📉 {('Уведомлять при падении' if get_text(user_id, 'language') == 'ru' else 'Notify on drop')}: {settings.get('threshold_down', 3.0)}%\n"
            f"🔔 {('Статус' if get_text(user_id, 'language') == 'ru' else 'Status')}: {('ВКЛ' if settings.get('active', True) else 'ВЫКЛ') if get_text(user_id, 'language') == 'ru' else ('ON' if settings.get('active', True) else 'OFF')}\n"
            f"🌐 {('Язык' if get_text(user_id, 'language') == 'ru' else 'Language')}: {'Русский' if settings.get('language', 'ru') == 'ru' else 'English'}\n"
            f"💵 {('Валюта' if get_text(user_id, 'language') == 'ru' else 'Currency')}: {'USD' if settings.get('currency', 'usd') == 'usd' else 'RUB'}\n\n"
            f"{'💡 Бот отслеживает изменения цены в реальном времени' if get_text(user_id, 'language') == 'ru' else '💡 Bot tracks price changes in real time'}"
        )

        bot.edit_message_text(
            message,
            call.message.chat.id,
            call.message.message_id,
            reply_markup=keyboard,
            parse_mode='Markdown'
        )
    except Exception as e:
        print(f"Ошибка в show_settings: {e}")
        bot.answer_callback_query(call.id, get_text(user_id, 'error_general'))


def set_threshold(call, threshold_type):
    """Запрос на установку порога"""
    user_id = call.from_user.id

    try:
        if user_id not in user_settings:
            user_settings[user_id] = {}

        user_settings[user_id]['awaiting_input'] = threshold_type

        if threshold_type == 'up':
            message = get_text(user_id, 'set_threshold_up')
        else:
            message = get_text(user_id, 'set_threshold_down')

        bot.edit_message_text(
            message,
            call.message.chat.id,
            call.message.message_id
        )
    except Exception as e:
        print(f"Ошибка в set_threshold: {e}")
        bot.answer_callback_query(call.id, get_text(user_id, 'error_general'))


def toggle_notifications(call):
    """Включение/выключение уведомлений"""
    user_id = call.from_user.id

    try:
        if user_id not in user_settings:
            user_settings[user_id] = {'active': True}

        user_settings[user_id]['active'] = not user_settings[user_id].get('active', True)
        status = get_text(user_id, 'notifications_on') if user_settings[user_id]['active'] else get_text(user_id,
                                                                                                         'notifications_off')

        save_data()

        bot.answer_callback_query(call.id, status)
        show_settings(call)
    except Exception as e:
        print(f"Ошибка в toggle_notifications: {e}")
        bot.answer_callback_query(call.id, get_text(user_id, 'error_general'))


def show_main_menu(call):
    """Показать главное меню"""
    user_id = call.from_user.id

    try:
        keyboard = types.InlineKeyboardMarkup()
        keyboard.row(
            types.InlineKeyboardButton(get_text(user_id, 'menu_settings'), callback_data="settings"),
            types.InlineKeyboardButton(get_text(user_id, 'menu_price'), callback_data="current_price")
        )
        keyboard.row(
            types.InlineKeyboardButton(get_text(user_id, 'menu_wallet'), callback_data="open_wallet"),
            types.InlineKeyboardButton(get_text(user_id, 'menu_calculator'), callback_data="calculator")
        )
        keyboard.row(types.InlineKeyboardButton(get_text(user_id, 'menu_toggle'), callback_data="toggle"))

        bot.edit_message_text(
            get_text(user_id, 'main_menu'),
            call.message.chat.id,
            call.message.message_id,
            reply_markup=keyboard
        )
    except Exception as e:
        print(f"Ошибка в show_main_menu: {e}")
        bot.answer_callback_query(call.id, get_text(user_id, 'error_general'))


def open_wallet(call):
    """Открыть меню кошелька"""
    user_id = call.from_user.id

    try:
        keyboard = types.InlineKeyboardMarkup()

        # Пробуем разные варианты ссылок для открытия кошелька
        keyboard.row(
            types.InlineKeyboardButton("📱 Открыть кошелек", url="https://t.me/wallet?startattach=wallet"),
            types.InlineKeyboardButton("ℹ️ О кошельке", callback_data="wallet_info")
        )
        keyboard.row(
            types.InlineKeyboardButton("💳 Купить TON", url="https://t.me/wallet?startattach=wallet&startapp=buy"),
            types.InlineKeyboardButton("📊 Статистика", callback_data="stats")
        )
        keyboard.row(types.InlineKeyboardButton(get_text(user_id, 'back'), callback_data="main_menu"))

        message = (
            f"{get_text(user_id, 'wallet')}"
            f"{get_text(user_id, 'wallet_features')}\n\n"
            f"💡 *Как открыть кошелек:*\n"
            f"1. Нажмите кнопку '📱 Открыть кошелек'\n"
            f"2. В открывшемся чате нажмите 'Open Wallet'\n"
            f"3. Или установите официальное приложение TON Wallet\n\n"
            f"📲 *Альтернативные способы:*\n"
            f"• Скачайте @wallet бота\n"
            f"• Используйте приложение Tonkeeper\n"
            f"• Установите Trust Wallet"
        )

        bot.edit_message_text(
            message,
            call.message.chat.id,
            call.message.message_id,
            reply_markup=keyboard,
            parse_mode='Markdown'
        )
    except Exception as e:
        print(f"Ошибка в open_wallet: {e}")
        bot.answer_callback_query(call.id, get_text(user_id, 'error_general'))


def show_wallet_info(call):
    """Информация о кошельке"""
    user_id = call.from_user.id

    try:
        keyboard = types.InlineKeyboardMarkup()

        # Предлагаем несколько вариантов кошельков
        keyboard.row(
            types.InlineKeyboardButton("📱 Telegram Wallet", url="https://t.me/wallet"),
            types.InlineKeyboardButton("🔵 Tonkeeper", url="https://tonkeeper.com")
        )
        keyboard.row(
            types.InlineKeyboardButton("🟢 Trust Wallet", url="https://trustwallet.com"),
            types.InlineKeyboardButton("🟠 MyTonWallet", url="https://mytonwallet.io")
        )
        keyboard.row(types.InlineKeyboardButton(get_text(user_id, 'back'), callback_data="open_wallet"))

        message = (
            f"{get_text(user_id, 'wallet_info')}"
            f"🎯 **Рекомендуемые кошельки:**\n\n"
            f"🤖 **Telegram Wallet** (встроенный)\n"
            f"• Интегрирован в Telegram\n"
            f"• Простой и удобный\n"
            f"• Покупка TON через карту\n\n"
            f"🔵 **Tonkeeper**\n"
            f"• Официальный кошелек TON\n"
            f"• Поддержка NFT и dApps\n"
            f"• Высокая безопасность\n\n"
            f"🟢 **Trust Wallet**\n"
            f"• Мульти-чейн кошелек\n"
            f"• Поддержка многих сетей\n"
            f"• Децентрализованный\n\n"
            f"💡 *Выберите кошелек который вам больше подходит*"
        )

        bot.edit_message_text(
            message,
            call.message.chat.id,
            call.message.message_id,
            reply_markup=keyboard,
            parse_mode='Markdown'
        )
    except Exception as e:
        print(f"Ошибка в show_wallet_info: {e}")
        bot.answer_callback_query(call.id, get_text(user_id, 'error_general'))


def buy_ton(call):
    """Покупка TON"""
    user_id = call.from_user.id

    try:
        keyboard = types.InlineKeyboardMarkup()

        # Предлагаем разные способы покупки
        keyboard.row(
            types.InlineKeyboardButton("🤖 Telegram Wallet", url="https://t.me/wallet"),
            types.InlineKeyboardButton("🔵 Tonkeeper", url="https://tonkeeper.com")
        )
        keyboard.row(
            types.InlineKeyboardButton("📈 Binance", url="https://www.binance.com"),
            types.InlineKeyboardButton("🚀 Bybit", url="https://www.bybit.com")
        )
        keyboard.row(
            types.InlineKeyboardButton("💎 OKX", url="https://www.okx.com"),
            types.InlineKeyboardButton("🔄 Купить P2P", url="https://p2p.binance.com")
        )
        keyboard.row(types.InlineKeyboardButton(get_text(user_id, 'back'), callback_data="open_wallet"))

        message = (
            f"{get_text(user_id, 'buy_ton')}"
            f"💳 **Способы покупки TON:**\n\n"
            f"🤖 **Через Telegram Wallet**\n"
            f"• Прямо в приложении Telegram\n"
            f"• Банковские карты Visa/Mastercard\n"
            f"• Быстро и удобно\n\n"
            f"🔵 **Через Tonkeeper**\n"
            f"• Встроенная покупка\n"
            f"• Поддержка карт\n"
            f"• Хороший курс\n\n"
            f"📈 **На биржах:**\n"
            f"• Binance - крупнейшая биржа\n"
            f"• Bybit - хорошие условия\n"
            f"• OKX - много пар\n\n"
            f"🔄 **P2P платформы:**\n"
            f"• Прямые сделки\n"
            f"• Разные способы оплаты\n"
            f"• Конкурентные цены\n\n"
            f"💡 *Выберите удобный для вас способ*"
        )

        bot.edit_message_text(
            message,
            call.message.chat.id,
            call.message.message_id,
            reply_markup=keyboard,
            parse_mode='Markdown'
        )
    except Exception as e:
        print(f"Ошибка в buy_ton: {e}")
        bot.answer_callback_query(call.id, get_text(user_id, 'error_general'))


@bot.message_handler(commands=['wallet'])
def wallet_command(message):
    """Команда для открытия кошелька"""
    user_id = message.from_user.id

    try:
        # Пытаемся отправить прямое сообщение с кнопкой
        keyboard = types.InlineKeyboardMarkup()
        keyboard.row(types.InlineKeyboardButton("🚀 Открыть TON кошелек", url="https://t.me/wallet"))

        bot.send_message(
            message.chat.id,
            "💎 **TON Кошелек**\n\n"
            "Нажмите кнопку ниже чтобы открыть официальный TON кошелек в Telegram.\n\n"
            "Если кнопка не работает:\n"
            "1. Откройте @wallet бота\n"
            "2. Нажмите 'Start'\n"
            "3. Следуйте инструкциям",
            reply_markup=keyboard,
            parse_mode='Markdown'
        )
    except Exception as e:
        print(f"Ошибка в wallet_command: {e}")
        bot.send_message(message.chat.id, "❌ Не удалось открыть кошелек. Попробуйте открыть @wallet бота вручную.")


def show_stats(call):
    """Статистика мониторинга"""
    user_id = call.from_user.id

    try:
        price_usd, price_rub, change_24h = get_ton_price()
        total_users = len(user_settings)
        active_users = sum(1 for settings in user_settings.values() if settings.get('active', True))

        keyboard = types.InlineKeyboardMarkup()
        keyboard.row(types.InlineKeyboardButton(get_text(user_id, 'refresh'), callback_data="stats"))
        keyboard.row(types.InlineKeyboardButton(get_text(user_id, 'back'), callback_data="open_wallet"))

        message = (
            f"{get_text(user_id, 'stats')}"
            f"👥 Всего пользователей: {total_users}\n"
            f"🔔 Активные уведомления: {active_users}\n"
            f"💰 Текущая цена TON: ${price_usd:.4f}\n"
            f"📈 Изменение за 24ч: {change_24h:.2f}%\n"
            f"🕐 Последнее обновление: {datetime.now().strftime('%H:%M:%S')}\n\n"
            f"💡 *Система работает стабильно*"
        )

        bot.edit_message_text(
            message,
            call.message.chat.id,
            call.message.message_id,
            reply_markup=keyboard,
            parse_mode='Markdown'
        )
    except Exception as e:
        print(f"Ошибка в show_stats: {e}")
        bot.answer_callback_query(call.id, get_text(user_id, 'error_general'))


def show_language_settings(call):
    """Настройки языка"""
    user_id = call.from_user.id

    try:
        keyboard = types.InlineKeyboardMarkup()
        keyboard.row(
            types.InlineKeyboardButton(get_text(user_id, 'language_ru'), callback_data="set_lang_ru"),
            types.InlineKeyboardButton(get_text(user_id, 'language_en'), callback_data="set_lang_en")
        )
        keyboard.row(types.InlineKeyboardButton(get_text(user_id, 'back'), callback_data="settings"))

        message = f"🌐 **Выберите язык / Choose language**"

        bot.edit_message_text(
            message,
            call.message.chat.id,
            call.message.message_id,
            reply_markup=keyboard
        )
    except Exception as e:
        print(f"Ошибка в show_language_settings: {e}")
        bot.answer_callback_query(call.id, get_text(user_id, 'error_general'))


def show_currency_settings(call):
    """Настройки валюты"""
    user_id = call.from_user.id

    try:
        keyboard = types.InlineKeyboardMarkup()
        keyboard.row(
            types.InlineKeyboardButton(get_text(user_id, 'currency_usd'), callback_data="set_curr_usd"),
            types.InlineKeyboardButton(get_text(user_id, 'currency_rub'), callback_data="set_curr_rub")
        )
        keyboard.row(types.InlineKeyboardButton(get_text(user_id, 'back'), callback_data="settings"))

        message = f"💵 **Выберите валюту / Choose currency**"

        bot.edit_message_text(
            message,
            call.message.chat.id,
            call.message.message_id,
            reply_markup=keyboard
        )
    except Exception as e:
        print(f"Ошибка в show_currency_settings: {e}")
        bot.answer_callback_query(call.id, get_text(user_id, 'error_general'))


def set_language(call):
    """Установка языка"""
    user_id = call.from_user.id

    try:
        language = call.data.replace("set_lang_", "")
        if user_id not in user_settings:
            user_settings[user_id] = {}

        user_settings[user_id]['language'] = language
        save_data()

        bot.answer_callback_query(call.id, f"✅ Язык установлен / Language set: {language}")
        show_settings(call)
    except Exception as e:
        print(f"Ошибка в set_language: {e}")
        bot.answer_callback_query(call.id, get_text(user_id, 'error_general'))


def set_currency(call):
    """Установка валюты"""
    user_id = call.from_user.id

    try:
        currency = call.data.replace("set_curr_", "")
        if user_id not in user_settings:
            user_settings[user_id] = {}

        user_settings[user_id]['currency'] = currency
        save_data()

        currency_name = "USD" if currency == 'usd' else "RUB"
        bot.answer_callback_query(call.id, f"✅ Валюта установлена / Currency set: {currency_name}")
        show_settings(call)
    except Exception as e:
        print(f"Ошибка в set_currency: {e}")
        bot.answer_callback_query(call.id, get_text(user_id, 'error_general'))


@bot.message_handler(func=lambda message: True)
def handle_messages(message):
    """Обработка текстовых сообщений"""
    user_id = message.from_user.id

    # Проверяем ограничение запросов
    if not check_rate_limit(user_id):
        bot.send_message(message.chat.id, get_text(user_id, 'rate_limit'))
        return

    try:
        # Проверяем, ожидаем ли мы ввод количества TON для расчета
        if user_id in user_settings and user_settings[user_id].get('awaiting_calculation'):
            try:
                ton_amount = float(message.text.replace(',', '.'))
                if ton_amount <= 0:
                    bot.send_message(message.chat.id, get_text(user_id, 'error_positive'))
                    return

                # Убираем флаг ожидания
                user_settings[user_id]['awaiting_calculation'] = False
                save_data()

                # Показываем результат расчета
                calculate_and_show_result(user_id, message.chat.id, ton_amount)

            except ValueError:
                bot.send_message(message.chat.id, get_text(user_id, 'error_number'))

        # Проверяем, ожидаем ли мы ввод порога уведомлений
        elif user_id in user_settings and 'awaiting_input' in user_settings[user_id]:
            threshold_type = user_settings[user_id]['awaiting_input']

            try:
                value = float(message.text)
                if value <= 0:
                    bot.send_message(message.chat.id, get_text(user_id, 'error_positive'))
                    return

                if threshold_type == 'up':
                    user_settings[user_id]['threshold_up'] = value
                    setting_name = "порог роста" if get_text(user_id, 'language') == 'ru' else "growth threshold"
                else:
                    user_settings[user_id]['threshold_down'] = value
                    setting_name = "порог падения" if get_text(user_id, 'language') == 'ru' else "drop threshold"

                del user_settings[user_id]['awaiting_input']
                save_data()

                keyboard = types.InlineKeyboardMarkup()
                keyboard.row(types.InlineKeyboardButton(get_text(user_id, 'menu_settings'), callback_data="settings"))

                bot.send_message(
                    message.chat.id,
                    get_text(user_id, 'threshold_set').format(value),
                    reply_markup=keyboard
                )

            except ValueError:
                bot.send_message(message.chat.id, get_text(user_id, 'error_number'))
        else:
            start(message)
    except Exception as e:
        print(f"Ошибка в handle_messages: {e}")
        bot.send_message(message.chat.id, get_text(user_id, 'error_general'))


def check_price_changes():
    """Проверка изменений цены в реальном времени"""
    global previous_price

    print("Запущен мониторинг цен TON...")

    while True:
        try:
            current_price_usd, current_price_rub, change_24h = get_ton_price()
            current_price = current_price_usd

            if previous_price is None:
                previous_price = current_price
                print(f"Первая проверка: ${current_price:.4f}")
                time.sleep(60)
                continue

            price_change = ((current_price - previous_price) / previous_price) * 100

            print(f"Цена: ${current_price:.4f}, Изменение: {price_change:.2f}%")

            for user_id, settings in user_settings.items():
                if not settings.get('active', True):
                    continue

                threshold_up = settings.get('threshold_up', 3.0)
                threshold_down = settings.get('threshold_down', 3.0)

                if price_change > threshold_up:
                    currency = settings.get('currency', 'usd')
                    price = current_price_usd if currency == 'usd' else current_price_rub
                    currency_symbol = '$' if currency == 'usd' else '₽'

                    if settings.get('language', 'ru') == 'ru':
                        message = (
                            f"🚀 **TON вырос на {price_change:.2f}%!**\n"
                            f"💵 Цена: {currency_symbol}{price:.4f}\n"
                            f"📈 Изменение за 24ч: {change_24h:.2f}%"
                        )
                    else:
                        message = (
                            f"🚀 **TON grew by {price_change:.2f}%!**\n"
                            f"💵 Price: {currency_symbol}{price:.4f}\n"
                            f"📈 24h change: {change_24h:.2f}%"
                        )

                    try:
                        bot.send_message(user_id, message, parse_mode='Markdown')
                        print(f"Отправлено уведомление о росте пользователю {user_id}")
                    except Exception as e:
                        print(f"Не удалось отправить сообщение пользователю {user_id}: {e}")

                elif price_change < -threshold_down:
                    currency = settings.get('currency', 'usd')
                    price = current_price_usd if currency == 'usd' else current_price_rub
                    currency_symbol = '$' if currency == 'usd' else '₽'

                    if settings.get('language', 'ru') == 'ru':
                        message = (
                            f"🔻 **TON упал на {abs(price_change):.2f}%!**\n"
                            f"💵 Цена: {currency_symbol}{price:.4f}\n"
                            f"📉 Изменение за 24ч: {change_24h:.2f}%"
                        )
                    else:
                        message = (
                            f"🔻 **TON dropped by {abs(price_change):.2f}%!**\n"
                            f"💵 Price: {currency_symbol}{price:.4f}\n"
                            f"📉 24h change: {change_24h:.2f}%"
                        )

                    try:
                        bot.send_message(user_id, message, parse_mode='Markdown')
                        print(f"Отправлено уведомление о падении пользователю {user_id}")
                    except Exception as e:
                        print(f"Не удалось отправить сообщение пользователю {user_id}: {e}")

            previous_price = current_price
            time.sleep(60)

        except Exception as e:
            print(f"Ошибка в мониторинге: {e}")
            time.sleep(60)


def run_monitoring():
    """Запуск мониторинга в отдельном потоке"""
    monitoring_thread = threading.Thread(target=check_price_changes)
    monitoring_thread.daemon = True
    monitoring_thread.start()


def cleanup_old_rates():
    """Очистка старых записей ограничений"""
    while True:
        try:
            now = time.time()
            expired_users = []

            for user_hash, requests in rate_limits.items():
                # Удаляем пользователей без активных запросов
                if not any(now - req_time < REQUEST_WINDOW * 2 for req_time in requests):
                    expired_users.append(user_hash)

            for user_hash in expired_users:
                rate_limits.pop(user_hash, None)

            time.sleep(300)  # Проверяем каждые 5 минут

        except Exception as e:
            print(f"Ошибка очистки rate limits: {e}")
            time.sleep(300)


if __name__ == "__main__":
    load_data()

    print("Бот запущен...")
    print("Отслеживание изменений цены TON в реальном времени")
    print("Многоязычная поддержка: русский/английский")
    print("Поддержка валют: USD/RUB")
    print("Калькулятор продажи: включен")
    print("Кэширование: включено (30 сек)")
    print("Защита от перегрузки: включена (25 запросов/20 сек)")

    run_monitoring()

    # Запускаем очистку старых rate limits
    cleanup_thread = threading.Thread(target=cleanup_old_rates)
    cleanup_thread.daemon = True
    cleanup_thread.start()

    # Добавьте в конец файла перед bot.polling()
    from flask import Flask
    from threading import Thread

    app = Flask('')


    @app.route('/')
    def home():
        return "Bot is alive!"


    def run():
        app.run(host='0.0.0.0', port=8080)


    def keep_alive():
        t = Thread(target=run)
        t.start()


    keep_alive()

    bot.polling(none_stop=True)

# ОБНОВИТЕ ФУНКЦИИ СОХРАНЕНИЯ:
def save_data():
    """Обновленная функция сохранения"""
    save_previous_price(previous_price)
    print("💾 Данные сохранены в базу")


def load_data():
    """Обновленная функция загрузки"""
    global user_settings, previous_price
    user_settings = load_all_settings()
    previous_price = load_previous_price()
    print("💾 Данные загружены из базы")


# ================== ЗАПУСК ==================
if __name__ == "__main__":
    load_data()

    print("🤖 TON Price Bot запускается...")
    print("📍 Режим: Cloud Deployment (Render.com)")
    print("💾 Хранилище: SQLite Database")
    print("🔔 Мониторинг: Активен 24/7")
    print("🌐 Веб-интерфейс: Включен")

    # Запуск мониторинга цен
    run_monitoring()

    # Запуск очистки rate limits
    cleanup_thread = threading.Thread(target=cleanup_old_rates)
    cleanup_thread.daemon = True
    cleanup_thread.start()

    # Запуск Flask в отдельном потоке
    flask_thread = threading.Thread(target=run_flask)
    flask_thread.daemon = True
    flask_thread.start()

    # Основной цикл бота
    while True:
        try:
            print("🔄 Запуск Telegram Bot...")
            bot.polling(none_stop=True, interval=1, timeout=30)
        except Exception as e:
            print(f"❌ Ошибка бота: {e}")
            print("♻️ Перезапуск через 15 секунд...")
            time.sleep(15)
