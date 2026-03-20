import asyncio
import os
import random
import json
import aiomysql
import pytz
from datetime import datetime, timedelta
from typing import Optional, List
from aiogram import Bot, Dispatcher, types, F
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton, FSInputFile
from aiogram.types import LabeledPrice, PreCheckoutQuery
from aiogram.types.message import ContentType
from datetime import datetime, timedelta, timezone
MOSCOW_TZ = pytz.timezone('Europe/Moscow')

# ==================== МОСКОВСКОЕ ВРЕМЯ ===============
def now_moscow():
    """Возвращает текущее время в Москве"""
    return datetime.now(MOSCOW_TZ)

def is_happy_hours() -> bool:
    """Проверяет, активны ли сейчас счастливые часы в Москве"""
    now = now_moscow().time()
    start = datetime.strptime("12:00", "%H:%M").time()
    end = datetime.strptime("14:00", "%H:%M").time()
    return start <= now <= end

# ================ ЗАЩИТА =======================
import sys
print(f"Python version: {sys.version}")
print(f"Running file: {__file__}")

# ================= ИМПОРТ MySQL ======================
print("🔍 Проверка переменных MySQL:")
print(f"HOST: {os.environ.get('MYSQLHOST')}")
print(f"PORT: {os.environ.get('MYSQLPORT')}")
print(f"USER: {os.environ.get('MYSQLUSER')}")
print(f"DATABASE: {os.environ.get('MYSQLDATABASE')}")
print(f"PASSWORD: {'*' * 8 if os.environ.get('MYSQL_ROOT_PASSWORD') else 'None'}")

# ===================== КОНФИГУРАЦИЯ =====================
BOT_TOKEN = "8778377938:AAHgOQwI8mCtQmCDhJ5Dgl-liEFnL2zcdsI"
PROVIDER_TOKEN = ""  # Сюда потом вставишь токен ЮKassa
CREATOR_ID = 5002614559
CREATOR_USERNAME = "AlexanderSmeiL"
ADMIN_USERNAMES = ["AlexanderSmeiL"]

# ===================== ПОДКЛЮЧЕНИЕ К MYSQL =====================
MYSQL_CONFIG = {
    "host": os.environ.get("MYSQLHOST"),
    "port": int(os.environ.get("MYSQLPORT", 3306)),
    "user": os.environ.get("MYSQLUSER"),
    "password": os.environ.get("MYSQL_ROOT_PASSWORD"),
    "db": os.environ.get("MYSQLDATABASE") or "railway"
}

pool = None


async def get_pool():
    global pool
    if pool is None:
        # Проверяем, что все переменные есть
        db_name = MYSQL_CONFIG["db"] or "railway"
        print(f"📦 Подключаюсь к БД: {db_name}")
        print(f"📦 Хост: {MYSQL_CONFIG['host']}")
        print(f"📦 Порт: {MYSQL_CONFIG['port']}")
        print(f"📦 Пользователь: {MYSQL_CONFIG['user']}")

        pool = await aiomysql.create_pool(
            host=MYSQL_CONFIG["host"],
            port=MYSQL_CONFIG["port"],
            user=MYSQL_CONFIG["user"],
            password=MYSQL_CONFIG["password"],
            db=db_name,
            autocommit=True
        )
    return pool

# ===================== СОСТОЯНИЯ FSM =====================
class MiningStates(StatesGroup):
    in_progress = State()

class PromoStates(StatesGroup):
    waiting_for_promo = State()

class AdminStates(StatesGroup):
    waiting_for_user_id = State()
    waiting_for_amount = State()
    waiting_for_promo_code = State()
    waiting_for_promo_type = State()
    waiting_for_promo_value = State()
    waiting_for_promo_uses = State()
    waiting_for_promo_delete = State()
    waiting_for_broadcast = State()
    waiting_for_maintenance = State()
    waiting_for_currency_amount = State()
    waiting_for_drill_user_id = State()
    waiting_for_drill_level = State()

class CasinoStates(StatesGroup):
    playing = State()

# ===================== СИСТЕМА ТОПЛИВА =====================
FUEL_CONFIG = {
    "base_max": 100,
    "vip_bonus_max": 20,
    "elite_bonus_max": 30,
    "regen_rate_base": 5,
    "regen_rate_vip": 7,
    "regen_interval": 10,
    "regen_notify": True
}

# ===================== ЛОКАЦИИ =====================
LOCATIONS = {
    1: {"name": "⛏ Шахта 1", "min_level": 1, "entry_fee": 0, "vip": False, "image": "location_1.jpg",
        "chances": {"common": 70, "rare": 20, "epic": 9, "legendary": 0.99, "mythic": 0.01}},
    2: {"name": "🏜️ Пустыня", "min_level": 11, "entry_fee": 10000, "vip": False, "image": "location_2.jpg",
        "chances": {"common": 60, "rare": 25, "epic": 12, "legendary": 2.5, "mythic": 0.5}},
    3: {"name": "❄️ Ледяные копи", "min_level": 21, "entry_fee": 50000, "vip": False, "image": "location_3.jpg",
        "chances": {"common": 55, "rare": 25, "epic": 15, "legendary": 3.5, "mythic": 1.5}},
    4: {"name": "🌋 Вулкан", "min_level": 31, "entry_fee": 200000, "vip": False, "image": "location_4.jpg",
        "chances": {"common": 45, "rare": 25, "epic": 20, "legendary": 6, "mythic": 4}},
    5: {"name": "🏔️ Небесные копи", "min_level": 41, "entry_fee": 500000, "vip": True, "image": "location_5.jpg",
        "chances": {"common": 35, "rare": 25, "epic": 22, "legendary": 10, "mythic": 8}},
    6: {"name": "🌌 Космос", "min_level": 51, "entry_fee": 1000000, "vip": True, "image": "location_6.jpg",
        "chances": {"common": 25, "rare": 25, "epic": 25, "legendary": 15, "mythic": 10}}
}

RARITIES = {
    "common": {"name": "🪨 Обычный", "emoji": "🪨", "min": 1, "max": 3},
    "rare": {"name": "📀 Необычный", "emoji": "📀", "min": 1, "max": 2},
    "epic": {"name": "🌟 Эпический", "emoji": "🌟", "min": 1, "max": 1},
    "legendary": {"name": "👑 Легендарный", "emoji": "👑", "min": 1, "max": 1},
    "mythic": {"name": "🌀 Мифический", "emoji": "🌀", "min": 1, "max": 1}
}

# ===================== БУРЫ =====================
DRILL_LEVELS = {
    1: {"name": "🛠️ Дрель-новичка", "bonus": 0, "price_coins": 0, "price_rub": 0, "rarity": "🟢 Обычный", "desc": "С неё начинается путь", "obtain": "start", "image": "drill_1.jpg"},
    2: {"name": "⚙️ Усиленный бур", "bonus": 5, "price_coins": 1000, "price_rub": 0, "rarity": "🟢 Обычный", "desc": "Металлический корпус", "obtain": "shop", "image": "drill_2.jpg"},
    3: {"name": "🏭 Промышленный бур", "bonus": 10, "price_coins": 5000, "price_rub": 0, "rarity": "🔵 Необычный", "desc": "Гидравлический привод", "obtain": "shop", "image": "drill_3.jpg"},
    4: {"name": "💎 Алмазный бур", "bonus": 15, "price_coins": 20000, "price_rub": 0, "rarity": "🔵 Необычный", "desc": "Алмазное напыление", "obtain": "shop", "image": "drill_4.jpg"},
    5: {"name": "🔬 Квантовый бур", "bonus": 25, "price_coins": 50000, "price_rub": 100, "rarity": "🟣 Редкий", "desc": "Субатомный уровень", "obtain": "shop_rub", "image": "drill_5.jpg"},
    6: {"name": "☢️ Ядерный бур", "bonus": 35, "price_coins": 100000, "price_rub": 200, "rarity": "🟣 Редкий", "desc": "Микро-реактор", "obtain": "shop_rub", "image": "drill_6.jpg"},
    7: {"name": "☀️ Солнечный бур", "bonus": 50, "price_coins": 200000, "price_rub": 400, "rarity": "🟣 Редкий", "desc": "Солнечный свет", "obtain": "shop_rub", "image": "drill_7.jpg"},
    8: {"name": "🔥 Пустынный бур", "bonus": 60, "price_coins": 0, "price_rub": 0, "rarity": "🟡 Эпический", "desc": "Термостойкий", "loc": "Пустыня", "obtain": "location", "image": "drill_8.jpg"},
    9: {"name": "❄️ Снежный бур", "bonus": 60, "price_coins": 0, "price_rub": 0, "rarity": "🟡 Эпический", "desc": "Криогенный", "loc": "Ледяные копи", "obtain": "location", "image": "drill_9.jpg"},
    10: {"name": "🌿 Лесной бур", "bonus": 60, "price_coins": 0, "price_rub": 0, "rarity": "🟡 Эпический", "desc": "Опутан лианами", "loc": "Небесные копи", "obtain": "location", "image": "drill_10.jpg"},
    11: {"name": "🌋 Вулканический бур", "bonus": 70, "price_coins": 0, "price_rub": 0, "rarity": "🟡 Эпический", "desc": "Работает в магме", "loc": "Вулкан", "obtain": "location", "image": "drill_11.jpg"},
    12: {"name": "💧 Океанический бур", "bonus": 70, "price_coins": 0, "price_rub": 0, "rarity": "🟡 Эпический", "desc": "Гидроизоляция", "loc": "Космос", "obtain": "location", "image": "drill_12.jpg"},
    13: {"name": "⚡ Грозовой бур", "bonus": 80, "price_coins": 0, "price_rub": 1000, "rarity": "🟤 Легендарный", "desc": "Питается от молний", "obtain": "donate", "image": "drill_13.jpg"},
    14: {"name": "🌈 Кристальный бур", "bonus": 90, "price_coins": 0, "price_rub": 1500, "rarity": "🟤 Легендарный", "desc": "Магический кристалл", "obtain": "donate", "image": "drill_14.jpg"},
    15: {"name": "🕯️ Теневой бур", "bonus": 90, "price_coins": 0, "price_rub": 1500, "rarity": "🟤 Легендарный", "desc": "Поглощает свет", "obtain": "donate", "image": "drill_15.jpg"},
    16: {"name": "🌌 Космический бур", "bonus": 100, "price_coins": 0, "price_rub": 0, "rarity": "👑 Мифический", "desc": "Метеоритное железо", "obtain": "top1", "image": "drill_16.jpg"},
    17: {"name": "🌙 Лунный бур", "bonus": 100, "price_coins": 0, "price_rub": 0, "rarity": "👑 Мифический", "desc": "Лунный свет", "obtain": "top3", "image": "drill_17.jpg"},
    18: {"name": "⭐ Звёздный бур", "bonus": 100, "price_coins": 0, "price_rub": 0, "rarity": "👑 Мифический", "desc": "Шлейф из искр", "obtain": "event", "image": "drill_18.jpg"},
}

# ===================== VIP СТАТУСЫ =====================
VIP_TYPES = {
    "vip_month": {"name": "VIP на месяц", "price": 299, "days": 30},
    "vip_3months": {"name": "VIP на 3 месяца", "price": 699, "days": 90},
    "vip_6months": {"name": "VIP на 6 месяцев", "price": 1199, "days": 180},
    "vip_year": {"name": "VIP на год", "price": 1499, "days": 365},
}

# ===================== БУСТЫ =====================
BOOSTS = {
    "boost_2h": {"name": "⚡️ x2 (2ч)", "price": 49, "hours": 2, "multiplier": 2.0},
    "boost_12h": {"name": "⚡️ x2 (12ч)", "price": 199, "hours": 12, "multiplier": 2.0},
    "boost_24h": {"name": "⚡️ x2 (24ч)", "price": 299, "hours": 24, "multiplier": 2.0},
    "boost_x3": {"name": "🔥 x3 (1ч)", "price": 499, "hours": 1, "multiplier": 3.0},
}

# ===================== ТОВАРЫ ДЛЯ МАГАЗИНА =====================
SHOP_FUEL = {
    "small": {"name": "⛽ Малая канистра", "fuel": 10, "price_coins": 500},
    "medium": {"name": "⛽⛽ Средняя канистра", "fuel": 25, "price_coins": 1000},
    "large": {"name": "⛽⛽⛽ Большая канистра", "fuel": 50, "price_coins": 2000},
}

DONATE_FUEL = {
    "small": {"name": "⛽ Топливо 50 ед.", "fuel": 50, "price_rub": 99},
    "medium": {"name": "⛽⛽ Топливо 150 ед.", "fuel": 150, "price_rub": 249},
    "large": {"name": "⛽⛽⛽ Топливо 300 ед.", "fuel": 300, "price_rub": 499},
}

# ===================== РЕФЕРАЛЫ =====================
REFERRAL_BONUSES = {"inviter": 200, "invited": 100, "vip_percent": 15}

# ===================== ПРОМОКОДЫ =====================
PROMO_CODES = {
    "START100": {"type": "balance", "value": 100, "uses": 1000, "used_by": []},
    "VIPWEEK": {"type": "vip", "value": 7, "uses": 50, "used_by": []},
    "BOOST24": {"type": "boost", "value": 24, "uses": 100, "used_by": []},
    "DRILL2": {"type": "drill", "value": 2, "uses": 10, "used_by": []},
    "STARTVIP": {
    "type": "combo",
    "value": {
        "vip": 7,
        "drill": 5,
        "balance": 500
    },
    "uses": 1000,
    "used_by": []
},

}

# ===================== КАТЕГОРИИ ТОПА =====================
TOP_CATEGORIES = {
    "balance": {"name": "💰 По балансу", "key": "balance"},
    "mined": {"name": "⛏ По добыче", "key": "total_mined"},
    "referrals": {"name": "👥 По рефералам", "key": "referral_count"},
    "donations": {"name": "💎 По донатам", "key": "total_donated"},
    "drill": {"name": "🛠 По буру", "key": "drill_level"},
    "daily": {"name": "📆 По серии", "key": "daily_streak"}
}

# ===================== ИНИЦИАЛИЗАЦИЯ БОТА =====================
bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
storage = MemoryStorage()
dp = Dispatcher(storage=storage)


# ===================== ФУНКЦИИ БАЗЫ ДАННЫХ MYSQL =====================
async def init_db():
    p = await get_pool()
    async with p.acquire() as conn:
        async with conn.cursor() as cur:
            # === НОВЫЙ КОД: создаём базу данных ===
            db_name = MYSQL_CONFIG["db"] or "railway"
            await cur.execute(f"CREATE DATABASE IF NOT EXISTS {db_name}")
            await cur.execute(f"USE {db_name}")
            print(f"✅ База данных {db_name} готова")
            # =======================================

            # Дальше идёт твой старый код создания таблиц
            await cur.execute('''
                              CREATE TABLE IF NOT EXISTS users
                              (
                                  user_id
                                  BIGINT
                                  PRIMARY
                                  KEY,
                                  balance
                                  INT
                                  DEFAULT
                                  100,
                                  fuel
                                  INT
                                  DEFAULT
                                  100,
                                  max_fuel
                                  INT
                                  DEFAULT
                                  100,
                                  last_fuel_reset
                                  DATETIME,
                                  drill_level
                                  INT
                                  DEFAULT
                                  1,
                                  vip_until
                                  DATETIME,
                                  boost_until
                                  DATETIME,
                                  boost_multiplier
                                  FLOAT
                                  DEFAULT
                                  1.0,
                                  inventory
                                  TEXT,
                                  total_mined
                                  INT
                                  DEFAULT
                                  0,
                                  total_earned
                                  INT
                                  DEFAULT
                                  0,
                                  register_date
                                  VARCHAR
                              (
                                  20
                              ),
                                  referrer BIGINT,
                                  referral_count INT DEFAULT 0,
                                  referral_earnings INT DEFAULT 0,
                                  used_promos TEXT,
                                  last_daily DATETIME,
                                  daily_streak INT DEFAULT 0,
                                  username VARCHAR
                              (
                                  255
                              ),
                                  first_name VARCHAR
                              (
                                  255
                              ),
                                  current_location INT DEFAULT 1,
                                  unlocked_locations TEXT,
                                  rarest_find VARCHAR
                              (
                                  50
                              ) DEFAULT 'common',
                                  total_donated INT DEFAULT 0
                                  )
                              ''')
            # === ДОБАВЛЯЕМ НЕДОСТАЮЩИЕ ПОЛЯ ===
            try:
                await cur.execute("ALTER TABLE users ADD COLUMN last_daily DATETIME")
                print("✅ Поле last_daily добавлено")
            except:
                print("⚠️ Поле last_daily уже существует")

            try:
                await cur.execute("ALTER TABLE users ADD COLUMN daily_streak INT DEFAULT 0")
                print("✅ Поле daily_streak добавлено")
            except:
                print("⚠️ Поле daily_streak уже существует")
            await cur.execute('''
                              CREATE TABLE IF NOT EXISTS promo_codes
                              (
                                  code
                                  VARCHAR
                              (
                                  50
                              ) PRIMARY KEY,
                                  type VARCHAR
                              (
                                  20
                              ),
                                  value TEXT,
                                  uses INT,
                                  used_by TEXT
                                  )
                              ''')
            await conn.commit()
            print("✅ Таблицы созданы")


async def get_user(user_id, first_name=None, username=None, referrer=None):
    p = await get_pool()
    async with p.acquire() as conn:
        async with conn.cursor() as cur:
            await cur.execute('SELECT * FROM users WHERE user_id = %s', (user_id,))
            result = await cur.fetchone()

            if not result:
                register_date = datetime.now().strftime("%d.%m.%Y")

                starter_balance = 100
                if referrer and referrer != user_id:
                    await cur.execute('SELECT user_id FROM users WHERE user_id = %s', (referrer,))
                    ref_result = await cur.fetchone()
                    if ref_result:
                        await cur.execute(
                            'UPDATE users SET balance = balance + 200, referral_count = referral_count + 1 WHERE user_id = %s',
                            (referrer,))
                        starter_balance = 200
                    else:
                        referrer = None
                else:
                    referrer = None

                await cur.execute('''
                                  INSERT INTO users (user_id, balance, fuel, max_fuel, last_fuel_reset, drill_level,
                                                     vip_until, boost_until, boost_multiplier, inventory, total_mined,
                                                     total_earned,
                                                     register_date, referrer, referral_count, referral_earnings,
                                                     used_promos, last_daily, daily_streak, username, first_name,
                                                     current_location, unlocked_locations, total_donated)
                                  VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
                                          %s, %s, %s, %s, %s)
                                  ''', (
                                      user_id, starter_balance, 100, 100, None, 1, None, None, 1.0,
                                      json.dumps({r: 0 for r in RARITIES.keys()}), 0, 0,
                                      register_date, referrer, 0, 0, json.dumps([]), None, 0, username, first_name,
                                      1, json.dumps([1]), 0
                                  ))
                await conn.commit()

                await cur.execute('SELECT * FROM users WHERE user_id = %s', (user_id,))
                result = await cur.fetchone()

            columns = [desc[0] for desc in cur.description]
            return dict(zip(columns, result))


async def update_user(user_id, **kwargs):
    p = await get_pool()
    async with p.acquire() as conn:
        async with conn.cursor() as cur:
            for key, value in kwargs.items():
                if isinstance(value, (dict, list)):
                    value = json.dumps(value)
                await cur.execute(f'UPDATE users SET {key} = %s WHERE user_id = %s', (value, user_id))
            await conn.commit()


async def get_all_users():
    p = await get_pool()
    async with p.acquire() as conn:
        async with conn.cursor() as cur:
            await cur.execute('SELECT * FROM users')
            result = await cur.fetchall()
            columns = [desc[0] for desc in cur.description]
            return [dict(zip(columns, row)) for row in result]


async def get_promo_codes_db():
    p = await get_pool()
    async with p.acquire() as conn:
        async with conn.cursor() as cur:
            await cur.execute('SELECT * FROM promo_codes')
            result = await cur.fetchall()
            columns = [desc[0] for desc in cur.description]
            promos = {}
            for row in result:
                data = dict(zip(columns, row))
                data['value'] = json.loads(data['value'])
                data['used_by'] = json.loads(data['used_by'])
                promos[data['code']] = data
            return promos


async def update_promo_db(code, **kwargs):
    p = await get_pool()
    async with p.acquire() as conn:
        async with conn.cursor() as cur:
            for key, value in kwargs.items():
                if isinstance(value, (dict, list)):
                    value = json.dumps(value)
                await cur.execute(f'UPDATE promo_codes SET {key} = %s WHERE code = %s', (value, code))
            await conn.commit()


async def delete_promo_db(code):
    p = await get_pool()
    async with p.acquire() as conn:
        async with conn.cursor() as cur:
            await cur.execute('DELETE FROM promo_codes WHERE code = %s', (code,))
            await conn.commit()


# ===================== СИСТЕМА УВЕДОМЛЕНИЙ =====================
class AdminNotifier:
    def __init__(self, bot: Bot, admin_id: int):
        self.bot = bot
        self.admin_id = admin_id

    async def send_to_admin(self, text: str, keyboard: Optional[InlineKeyboardMarkup] = None):
        try:
            await self.bot.send_message(
                chat_id=self.admin_id,
                text=text,
                parse_mode="HTML",
                reply_markup=keyboard
            )
        except Exception as e:
            print(f"Ошибка уведомления админу: {e}")

    async def send_to_user(self, user_id: int, text: str, keyboard: Optional[InlineKeyboardMarkup] = None):
        try:
            await self.bot.send_message(
                chat_id=user_id,
                text=text,
                parse_mode="HTML",
                reply_markup=keyboard
            )
        except Exception as e:
            print(f"Ошибка уведомления игроку {user_id}: {e}")

    async def broadcast(self, user_ids: List[int], text: str):
        sent = 0
        for uid in user_ids:
            try:
                await self.bot.send_message(uid, text, parse_mode="HTML")
                sent += 1
                await asyncio.sleep(0.05)
            except:
                pass
        return sent

    async def fuel_refilled(self, user_id: int, fuel: int, max_fuel: int, regen_rate: int = 5):
        text = (
            f"⛽ <b>ТОПЛИВО ПОЛНОСТЬЮ ВОССТАНОВЛЕНО!</b>\n\n"
            f"Теперь у тебя <b>{fuel}/{max_fuel}</b> единиц топлива.\n"
            f"⚡️ Скорость твоего восстановления: <b>+{regen_rate}</b> каждые 10 мин\n\n"
            f"⛏ Не дай ему простаивать — начинай добычу!"
        )
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="⛏ Добывать", callback_data="mine_now")]
        ])
        await self.send_to_user(user_id, text, kb)

    async def promo_created(self, promo_code: str, promo_type: str, promo_value: int, uses: int):
        text = (
            f"🎫 <b>НОВЫЙ ПРОМОКОД</b>\n\n"
            f"🔑 Код: <b>{promo_code}</b>\n"
            f"📦 Тип: {promo_type}\n"
            f"🎁 Значение: {promo_value}\n"
            f"📊 Использований: {uses}"
        )
        await self.send_to_admin(text)

    async def error_alert(self, error_msg: str, location: str):
        text = (
            f"❌ <b>ОШИБКА В БОТЕ</b>\n\n"
            f"📍 Место: {location}\n"
            f"📝 Сообщение: <code>{error_msg[:200]}</code>"
        )
        await self.send_to_admin(text)

    async def new_user(self, user_id: int, username: str, first_name: str, referrer: Optional[int] = None):
        name_display = first_name or username or f"ID {user_id}"
        ref_text = f"👥 Реферер: <code>{referrer}</code>" if referrer else "👥 Реферер: прямой заход"
        text = (
            f"🎯 <b>НОВЫЙ ИГРОК</b>\n\n"
            f"🆔 ID: <code>{user_id}</code>\n"
            f"👤 Имя: {name_display}\n"
            f"{ref_text}\n"
            f"📅 {datetime.now().strftime('%d.%m.%Y %H:%M')}"
        )
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="👤 Профиль", callback_data=f"admin_user_{user_id}")]
        ])
        await self.send_to_admin(text, kb)

    async def happy_hours_start(self):
        """Уведомление о начале счастливых часов"""
        text = (
            "🎁 <b>СЧАСТЛИВЫЕ ЧАСЫ НАЧАЛИСЬ!</b>\n\n"
            "⏰ С 12:00 до 14:00 действует <b>УДВОЕННАЯ ДОБЫЧА</b>!\n"
            "⛏ Каждая добыча приносит в 2 раза больше ресурсов!\n\n"
            "🔥 Успей воспользоваться!"
        )
        users = await get_all_users()
        for u in users:
            try:
                await self.bot.send_message(u['user_id'], text, parse_mode=ParseMode.HTML)
                await asyncio.sleep(0.05)
            except:
                pass


# Инициализация нотификатора
notifier = AdminNotifier(bot, CREATOR_ID)
bot.notifier = notifier


# ===================== ФУНКЦИИ ТОПЛИВА =====================
def get_max_fuel(user) -> int:
    """Определяет максимальный запас топлива для пользователя"""
    base = FUEL_CONFIG["base_max"]  # 100

    if user.get('vip_until'):
        try:
            if datetime.now() < datetime.fromisoformat(user['vip_until']):
                base += FUEL_CONFIG["vip_bonus_max"]  # +20
        except:
            pass

    if user.get('drill_level', 0) >= 16:
        base += FUEL_CONFIG["elite_bonus_max"]  # +30

    return base


def get_regen_rate(user) -> int:
    """Определяет скорость восстановления топлива (только VIP влияет)"""
    base_rate = FUEL_CONFIG["regen_rate_base"]  # 5

    if user.get('vip_until'):
        try:
            if datetime.now() < datetime.fromisoformat(user['vip_until']):
                return FUEL_CONFIG["regen_rate_vip"]  # 7
        except:
            pass

    return base_rate


def get_fuel_bar(fuel: int, max_fuel: int) -> str:
    """Возвращает прогресс-бар топлива"""
    percent = fuel / max_fuel
    filled = int(percent * 10)
    empty = 10 - filled
    return "🟩" * filled + "⬜" * empty


# ===================== ФУНКЦИИ ДЛЯ ФОТО =====================
async def send_photo(message: types.Message, text: str, image_name: str, keyboard=None):
    if not image_name:
        await message.answer(text, reply_markup=keyboard)
        return
    image_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "images", image_name)
    try:
        if os.path.exists(image_path):
            photo = FSInputFile(image_path)
            await message.answer_photo(photo=photo, caption=text, reply_markup=keyboard, parse_mode=ParseMode.HTML)
        else:
            await message.answer(text, reply_markup=keyboard)
    except:
        await message.answer(text, reply_markup=keyboard)


async def send_drill_photo(message: types.Message, drill_level: int, text: str, keyboard=None):
    await send_photo(message, text, f"drill_{drill_level}.jpg", keyboard)


async def edit_photo(callback: types.CallbackQuery, text: str, image_name: str, keyboard=None):
    if not image_name:
        await callback.message.edit_text(text, reply_markup=keyboard)
        return
    image_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "images", image_name)
    try:
        if os.path.exists(image_path):
            photo = FSInputFile(image_path)
            await callback.message.delete()
            await callback.message.answer_photo(photo=photo, caption=text, reply_markup=keyboard,
                                                parse_mode=ParseMode.HTML)
        else:
            await callback.message.edit_text(text, reply_markup=keyboard)
    except:
        await callback.message.edit_text(text, reply_markup=keyboard)


# ===================== ИГРОВЫЕ ФУНКЦИИ =====================
def get_display_name(user_id, user_data):
    """Возвращает имя пользователя без ID, только юзернейм или имя"""
    if user_id == CREATOR_ID:
        return "👑 Создатель"

    if user_data.get('first_name'):
        return f"👤 {user_data['first_name'][:15]}"

    if user_data.get('username'):
        return f"👤 @{user_data['username']}"

    return "👤 Игрок"  # без ID


def mine_resources(user):
    loc = LOCATIONS[user['current_location']]
    chances = loc['chances']
    drill = DRILL_LEVELS[user['drill_level']]

    multiplier = 1 + drill['bonus'] / 100

    if user.get('vip_until') and datetime.now() < datetime.fromisoformat(user['vip_until']):
        multiplier *= 2

    if user.get('boost_until') and datetime.now() < datetime.fromisoformat(user['boost_until']):
        multiplier *= user['boost_multiplier']

    # Счастливые часы по московскому времени
    if is_happy_hours():
        multiplier *= 2
        print("🎉 Счастливые часы активны! x2")

    total = int(5 * multiplier)
    inventory = json.loads(user['inventory'])
    mined = []

    for _ in range(total):
        roll = random.random() * 100
        cum = 0
        for key, chance in chances.items():
            cum += chance
            if roll <= cum and key in RARITIES:
                amount = random.randint(RARITIES[key]['min'], RARITIES[key]['max'])
                mined.append((key, amount))
                inventory[key] = inventory.get(key, 0) + amount
                user['total_mined'] += amount
                break

    user['inventory'] = inventory
    return mined


def apply_promo_reward(user, promo_data):
    if promo_data['type'] == "balance":
        user['balance'] += promo_data['value']
        return f"💰 +{promo_data['value']} монет"

    elif promo_data['type'] == "vip":
        user['vip_until'] = (datetime.now() + timedelta(days=promo_data['value'])).isoformat()
        return f"👑 VIP на {promo_data['value']} дней"

    elif promo_data['type'] == "boost":
        user['boost_until'] = (datetime.now() + timedelta(hours=promo_data['value'])).isoformat()
        user['boost_multiplier'] = 2.0
        return f"⚡️ Буст x2 на {promo_data['value']} часов"

    elif promo_data['type'] == "drill":
        user['drill_level'] = promo_data['value']
        return f"🛠 Бур {DRILL_LEVELS[promo_data['value']]['name']}"

    elif promo_data['type'] == "combo":
        rewards = []
        if 'vip' in promo_data['value']:
            user['vip_until'] = (datetime.now() + timedelta(days=promo_data['value']['vip'])).isoformat()
            rewards.append(f"👑 VIP на {promo_data['value']['vip']} дней")
        if 'boost' in promo_data['value']:
            user['boost_until'] = (datetime.now() + timedelta(hours=promo_data['value']['boost'])).isoformat()
            user['boost_multiplier'] = 2.0
            rewards.append(f"⚡️ Буст x2 на {promo_data['value']['boost']} часов")
        if 'drill' in promo_data['value']:
            user['drill_level'] = promo_data['value']['drill']
            rewards.append(f"🛠 {DRILL_LEVELS[promo_data['value']['drill']]['name']}")
        if 'balance' in promo_data['value']:
            user['balance'] += promo_data['value']['balance']
            rewards.append(f"💰 {promo_data['value']['balance']} монет")
        return " + ".join(rewards)

    return ""


# ===================== КЛАВИАТУРЫ =====================
def main_keyboard(user_id=None):
    kb = [
        [KeyboardButton(text="⛏ Добывать"), KeyboardButton(text="📦 Инвентарь")],
        [KeyboardButton(text="🛠 Буры"), KeyboardButton(text="🗺️ Локации")],
        [KeyboardButton(text="🏪 Магазин"), KeyboardButton(text="📊 Топ")],
        [KeyboardButton(text="👤 Профиль"), KeyboardButton(text="👥 Рефералы")],
        [KeyboardButton(text="⛽ Статус топлива"), KeyboardButton(text="💎 Донат")],
        [KeyboardButton(text="🎁 Счастливые часы"), KeyboardButton(text="❓ Помощь")]
    ]
    if user_id == CREATOR_ID:
        kb.append([KeyboardButton(text="👑 Админка")])
    return ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True)


def get_shop_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🛠 Купить бур", callback_data="shop_drills")],
        [InlineKeyboardButton(text="⛽ Купить топливо", callback_data="shop_fuel")],
        [InlineKeyboardButton(text="💰 Продать руду", callback_data="shop_sell")],
        [InlineKeyboardButton(text="◀️ Назад", callback_data="back_main")]
    ])


def get_locations_keyboard(user):
    unlocked = json.loads(user['unlocked_locations'])
    kb = []
    for loc_id, loc in LOCATIONS.items():
        if loc_id in unlocked:
            mark = "✅" if loc_id == user['current_location'] else "🔓"
            kb.append([InlineKeyboardButton(text=f"{mark} {loc['name']}", callback_data=f"loc_{loc_id}")])
        elif loc_id - 1 in unlocked and user['drill_level'] >= loc['min_level']:
            price = f"{loc['entry_fee']}💰" + (" + VIP" if loc['vip'] else "")
            kb.append([InlineKeyboardButton(text=f"🔒 {loc['name']} - {price}", callback_data=f"buy_loc_{loc_id}")])
    kb.append([InlineKeyboardButton(text="◀️ Назад", callback_data="back_main")])
    return InlineKeyboardMarkup(inline_keyboard=kb)


def get_admin_keyboard():
    return ReplyKeyboardMarkup(keyboard=[
        [KeyboardButton(text="📊 Статистика"), KeyboardButton(text="👥 Все игроки")],
        [KeyboardButton(text="💰 Выдать монеты"), KeyboardButton(text="🎫 Промокоды")],
        [KeyboardButton(text="📢 Рассылка"), KeyboardButton(text="💎 Валюта")],
        [KeyboardButton(text="🛠 Управление бурами"), KeyboardButton(text="🔧 Техработы")],
        [KeyboardButton(text="◀️ Выйти")]
    ], resize_keyboard=True)


# ===================== СТАРТ =====================
@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    user_id = message.from_user.id
    first_name = message.from_user.first_name
    username = message.from_user.username

    # Проверяем реферала
    args = message.text.split()
    referrer = int(args[1]) if len(args) > 1 else None

    user = await get_user(user_id, first_name, username, referrer)

    # Приветственный текст
    welcome_text = (
        f"👋 <b>Добро пожаловать в Miner Game, {first_name or 'шахтёр'}!</b>\n\n"
        f"⛏ <b>ЧТО ТУТ ДЕЛАТЬ:</b>\n"
        f"• Добывай ресурсы в разных локациях\n"
        f"• Продавай руду и улучшай бур\n"
        f"• Открывай новые локации\n"
        f"• Приглашай друзей и получай бонусы\n\n"

        f"📊 <b>ТВОИ ДАННЫЕ:</b>\n"
        f"💰 Баланс: {user['balance']} монет\n"
        f"⛽ Топливо: {user['fuel']}/{user['max_fuel']}\n"
        f"🛠 Бур: {DRILL_LEVELS[user['drill_level']]['name']}\n"
        f"🗺️ Локация: {LOCATIONS[user['current_location']]['name']}\n\n"

        f"🎁 <b>СОВЕТ:</b>\n"
        f"• Заходи каждый день за бонусом\n"
        f"• С 12:00 до 14:00 — удвоенная добыча!\n"
        f"• Введи промокод <b>STARTVIP</b> для подарка"
    )

    # Кнопки для быстрого старта
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⛏ Начать добычу", callback_data="mine_now")],
        [InlineKeyboardButton(text="🎁 Ввести STARTVIP", callback_data="enter_startvip")],
        [InlineKeyboardButton(text="📋 Правила игры", callback_data="game_rules")]
    ])

    await send_photo(message, welcome_text, "welcome.jpg", kb)

    # Уведомление админу о новом игроке
    if referrer and user_id != referrer:
        await bot.notifier.new_user(user_id, username, first_name, referrer)


@dp.callback_query(F.data == "game_rules")
async def game_rules(callback: types.CallbackQuery):
    """Подробные правила игры"""
    text = (
        "📋 <b>ПРАВИЛА ИГРЫ MINER GAME</b>\n\n"

        "⛏ <b>ДОБЫЧА:</b>\n"
        "• Каждое нажатие тратит 1 топливо\n"
        "• Топливо восстанавливается автоматически: +5 каждые 10 мин\n"
        "• VIP восстанавливает +7 каждые 10 мин\n"
        "• В разных локациях разный шанс на редкую руду\n\n"

        "🛠 <b>БУРЫ:</b>\n"
        "• Чем выше уровень бура, тем больше добыча\n"
        "• Улучшай бур за монеты в магазине\n"
        "• Легендарные буры дают огромный бонус\n\n"

        "🗺️ <b>ЛОКАЦИИ:</b>\n"
        "• Шахта 1 — бесплатно, для новичков\n"
        "• Пустыня — 10 000 монет, +шанс на редкую\n"
        "• Ледяные копи — 50 000 монет, +шанс на эпическую\n"
        "• Вулкан — 200 000 монет, +шанс на легендарную\n"
        "• Небесные копи — 500 000 монет + VIP\n"
        "• Космос — 1 000 000 монет + VIP\n\n"

        "👥 <b>РЕФЕРАЛЫ:</b>\n"
        "• За друга: +200 монет\n"
        "• Другу: +100 монет\n"
        "• 15% от донатов друзей\n\n"

        "🎁 <b>БОНУСЫ И ИВЕНТЫ:</b>\n"
        "• Ежедневный бонус — заходи каждый день\n"
        "• Счастливые часы — с 12:00 до 14:00 x2 добыча\n"
        "• Промокоды — вводи и получай подарки\n\n"

        "💎 <b>ДОНАТ:</b>\n"
        "• Покупка топлива, VIP, бустов\n"
        "• Легендарные буры за рубли\n"
        "• Поддержи проект и получай преимущества"
    )

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="◀️ Назад", callback_data="back_to_start")]
    ])

    await callback.message.edit_text(text, reply_markup=kb, parse_mode=ParseMode.HTML)
    await callback.answer()

@dp.callback_query(F.data == "back_to_start")
async def back_to_start(callback: types.CallbackQuery):
    """Возврат в главное меню"""
    await cmd_start(callback.message)
    await callback.answer()

# ===================== ДОБЫЧА =====================
@dp.message(F.text == "⛏ Добывать", StateFilter(None))
async def mine_command(message: types.Message, state: FSMContext):
    await state.set_state(MiningStates.in_progress)
    try:
        user_id = message.from_user.id
        user = await get_user(user_id)

        if user['fuel'] <= 0:
            await message.answer("⛽ Нет топлива! Подожди восстановления или купи в магазине.",
                                 reply_markup=main_keyboard(user_id))
            await state.clear()
            return

        user['fuel'] -= 1
        mined = mine_resources(user)

        await update_user(user_id, fuel=user['fuel'], inventory=user['inventory'], total_mined=user['total_mined'])

        result = {}
        for r, a in mined:
            result[r] = result.get(r, 0) + a

        fuel_emoji = get_fuel_bar(user['fuel'], user['max_fuel'])
        loc_name = LOCATIONS[user['current_location']]['name']

        text = f"⛏ Добыча в {loc_name}\n\n"
        for r, a in result.items():
            text += f"{RARITIES[r]['emoji']} {RARITIES[r]['name']}: +{a}\n"
        text += f"\n⛽ {fuel_emoji} {user['fuel']}/{user['max_fuel']}"

        await message.answer(text, reply_markup=main_keyboard(user_id))

    except Exception as e:
        print(f"❌ Ошибка добычи: {e}")
        if hasattr(bot, 'notifier'):
            await bot.notifier.error_alert(str(e), "mine_command")
        await message.answer("❌ Произошла ошибка при добыче")
    finally:
        await state.clear()


# ===================== ИНВЕНТАРЬ =====================
@dp.message(F.text == "📦 Инвентарь")
async def inventory(message: types.Message):
    user_id = message.from_user.id
    user = await get_user(user_id)
    inv = json.loads(user['inventory'])
    text = "📦 ИНВЕНТАРЬ\n\n"
    for r, data in RARITIES.items():
        if inv.get(r, 0) > 0:
            text += f"{data['emoji']} {data['name']}: {inv[r]} шт.\n"
    await message.answer(text, reply_markup=main_keyboard(user_id))


# ===================== БУРЫ =====================
@dp.message(F.text == "🛠 Буры")
async def drills_menu(message: types.Message):
    user_id = message.from_user.id
    user = await get_user(user_id)
    drill = DRILL_LEVELS[user['drill_level']]

    text = f"🛠 <b>ТВОЙ БУР</b>\n\n"
    text += f"<b>{drill['name']}</b>\n"
    text += f"Редкость: {drill['rarity']}\n"
    text += f"⚡️ Бонус: +{drill['bonus']}%\n"
    text += f"📝 {drill['desc']}\n\n"

    if user['drill_level'] < len(DRILL_LEVELS):
        next_drill = DRILL_LEVELS[user['drill_level'] + 1]
        text += f"➡️ Следующий: {next_drill['name']}\n"
        if next_drill.get('price_coins', 0) > 0:
            text += f"💰 Цена: {next_drill['price_coins']} монет"
        elif next_drill.get('price_rub', 0) > 0:
            text += f"💎 Цена: {next_drill['price_rub']}₽"

    await send_drill_photo(message, user['drill_level'], text, main_keyboard(user_id))


# ===================== ЛОКАЦИИ =====================
@dp.message(F.text == "🗺️ Локации")
async def locations_menu(message: types.Message):
    user_id = message.from_user.id
    user = await get_user(user_id)
    await message.answer("🗺️ ЛОКАЦИИ\n\nВыбери локацию:", reply_markup=get_locations_keyboard(user))


@dp.callback_query(F.data.startswith("loc_"))
async def select_loc(callback: types.CallbackQuery):
    loc_id = int(callback.data.split("_")[1])
    user_id = callback.from_user.id
    user = await get_user(user_id)
    unlocked = json.loads(user['unlocked_locations'])

    if loc_id in unlocked:
        await update_user(user_id, current_location=loc_id)
        await callback.answer(f"✅ Теперь ты в {LOCATIONS[loc_id]['name']}")
        await callback.message.delete()
        await send_photo(callback.message, f"🗺️ Ты в {LOCATIONS[loc_id]['name']}", LOCATIONS[loc_id]['image'],
                         main_keyboard(user_id))
    else:
        await callback.answer("❌ Локация недоступна", show_alert=True)


@dp.callback_query(F.data.startswith("buy_loc_"))
async def buy_loc(callback: types.CallbackQuery):
    loc_id = int(callback.data.split("_")[2])
    user_id = callback.from_user.id
    user = await get_user(user_id)
    loc = LOCATIONS[loc_id]

    if loc['vip'] and (not user['vip_until'] or datetime.now() >= datetime.fromisoformat(user['vip_until'])):
        await callback.answer("❌ Нужен VIP", show_alert=True)
        return

    if user['balance'] < loc['entry_fee']:
        await callback.answer(f"❌ Нужно {loc['entry_fee']}💰", show_alert=True)
        return

    user['balance'] -= loc['entry_fee']
    unlocked = json.loads(user['unlocked_locations'])
    unlocked.append(loc_id)
    await update_user(user_id, balance=user['balance'], unlocked_locations=unlocked)
    await callback.answer(f"✅ Локация открыта!")
    await callback.message.delete()
    await send_photo(callback.message, f"🗺️ Открыта: {loc['name']}!", loc['image'], main_keyboard(user_id))


# ===================== МАГАЗИН =====================
@dp.message(F.text == "🏪 Магазин")
async def shop_menu(message: types.Message):
    await message.answer("🏪 <b>МАГАЗИН</b>\n\nВыбери категорию:", reply_markup=get_shop_keyboard(),
                         parse_mode=ParseMode.HTML)


@dp.callback_query(F.data == "back_to_shop")
async def back_to_shop(callback: types.CallbackQuery):
    await shop_menu(callback.message)
    await callback.answer()


# ===================== МАГАЗИН - ТОПЛИВО =====================
@dp.callback_query(F.data == "shop_fuel")
async def shop_fuel_menu(callback: types.CallbackQuery):
    text = "⛽ <b>ТОПЛИВО В МАГАЗИНЕ</b>\n\n"
    text += "Покупай топливо за монеты:\n\n"

    for key, fuel in SHOP_FUEL.items():
        text += f"• {fuel['name']} — {fuel['fuel']} топлива\n"
        text += f"  💰 Цена: {fuel['price_coins']} монет\n\n"

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⛽ Малая (10) - 500💰", callback_data="buy_fuel_small_coins")],
        [InlineKeyboardButton(text="⛽⛽ Средняя (25) - 1000💰", callback_data="buy_fuel_medium_coins")],
        [InlineKeyboardButton(text="⛽⛽⛽ Большая (50) - 2000💰", callback_data="buy_fuel_large_coins")],
        [InlineKeyboardButton(text="◀️ Назад", callback_data="back_to_shop")]
    ])

    await callback.message.edit_text(text, reply_markup=kb, parse_mode=ParseMode.HTML)
    await callback.answer()


@dp.callback_query(F.data.startswith("buy_fuel_"))
async def buy_fuel_coins(callback: types.CallbackQuery):
    parts = callback.data.split("_")
    size = parts[2]  # small, medium, large
    fuel_item = SHOP_FUEL[size]

    user_id = callback.from_user.id
    user = await get_user(user_id)

    if user['balance'] < fuel_item['price_coins']:
        await callback.answer(f"❌ Не хватает {fuel_item['price_coins'] - user['balance']}💰", show_alert=True)
        return

    user['balance'] -= fuel_item['price_coins']
    user['fuel'] = min(user['fuel'] + fuel_item['fuel'], user['max_fuel'])

    await update_user(user_id, balance=user['balance'], fuel=user['fuel'])

    await callback.message.edit_text(
        f"✅ <b>Покупка успешна!</b>\n\n"
        f"⛽ Ты получил {fuel_item['fuel']} топлива\n"
        f"💰 Остаток: {user['balance']} монет\n"
        f"⛽ Текущее топливо: {user['fuel']}/{user['max_fuel']}",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="◀️ Назад в магазин", callback_data="back_to_shop")]
        ]),
        parse_mode=ParseMode.HTML
    )
    await callback.answer()


# ===================== МАГАЗИН - ПРОДАЖА =====================
@dp.callback_query(F.data == "shop_sell")
async def shop_sell(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    user = await get_user(user_id)
    inv = json.loads(user['inventory'])

    text = "💰 <b>ПРОДАЖА РУДЫ</b>\n\n"
    total = 0
    kb = []

    for r, data in RARITIES.items():
        count = inv.get(r, 0)
        if count > 0:
            price = (data['min'] + data['max']) // 2
            total_value = count * price
            text += f"{data['emoji']} {data['name']}: {count} шт. × {price} = {total_value}💰\n"
            total += total_value
            kb.append([InlineKeyboardButton(text=f"Продать {data['name']}", callback_data=f"sell_{r}")])

    if total == 0:
        text += "У тебя нет руды для продажи"
    else:
        text += f"\n💰 <b>Всего можно получить: {total} монет</b>"
        kb.append([InlineKeyboardButton(text="💰 Продать всё", callback_data="sell_all")])

    kb.append([InlineKeyboardButton(text="◀️ Назад", callback_data="back_to_shop")])
    await callback.message.edit_text(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=kb),
                                     parse_mode=ParseMode.HTML)
    await callback.answer()


@dp.callback_query(F.data.startswith("sell_"))
async def process_sell(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    user = await get_user(user_id)
    inv = json.loads(user['inventory'])

    if callback.data == "sell_all":
        total = 0
        for r in RARITIES:
            count = inv.get(r, 0)
            if count > 0:
                price = (RARITIES[r]['min'] + RARITIES[r]['max']) // 2
                total += count * price
                inv[r] = 0
        user['balance'] += total
        user['total_earned'] += total
        await update_user(user_id, balance=user['balance'], inventory=inv, total_earned=user['total_earned'])
        await callback.message.edit_text(f"✅ Продано всё! Получено: {total}💰")
    else:
        r = callback.data.split("_")[1]
        count = inv.get(r, 0)
        if count > 0:
            price = (RARITIES[r]['min'] + RARITIES[r]['max']) // 2
            total = count * price
            user['balance'] += total
            user['total_earned'] += total
            inv[r] = 0
            await update_user(user_id, balance=user['balance'], inventory=inv, total_earned=user['total_earned'])
            await callback.message.edit_text(f"✅ Продано {RARITIES[r]['name']}! Получено: {total}💰")

    await callback.answer()


# ===================== СТАТУС ТОПЛИВА =====================
@dp.message(F.text == "⛽ Статус топлива")
async def fuel_status(message: types.Message):
    user_id = message.from_user.id
    user = await get_user(user_id)

    max_fuel = get_max_fuel(user)
    regen_rate = get_regen_rate(user)
    next_regen = FUEL_CONFIG["regen_interval"]

    bar = get_fuel_bar(user['fuel'], max_fuel)

    vip_status = ""
    if regen_rate > FUEL_CONFIG["regen_rate_base"]:
        vip_status = "👑 VIP (ускоренное восстановление)"

    if user['fuel'] < max_fuel:
        needed = max_fuel - user['fuel']
        cycles_needed = (needed + regen_rate - 1) // regen_rate
        minutes_to_full = cycles_needed * next_regen
        hours = minutes_to_full // 60
        minutes = minutes_to_full % 60

        text = (
            f"⛽ <b>СТАТУС ТОПЛИВА</b>\n\n"
            f"{bar} {user['fuel']}/{max_fuel}\n"
            f"{vip_status}\n"
            f"⚡️ Восстановление: <b>+{regen_rate}</b> каждые {next_regen} мин\n"
            f"⏳ До полного бака: {hours}ч {minutes}м\n\n"
            f"💎 Купить топливо можно в магазине или донате!"
        )
    else:
        text = (
            f"⛽ <b>СТАТУС ТОПЛИВА</b>\n\n"
            f"{bar} {user['fuel']}/{max_fuel}\n"
            f"{vip_status}\n"
            f"⚡️ Восстановление: <b>+{regen_rate}</b> каждые {next_regen} мин\n"
            f"✅ Бак полный! Иди добывать! ⛏"
        )

    await message.answer(text, reply_markup=main_keyboard(user_id))


# ===================== ПРОФИЛЬ =====================
@dp.message(F.text == "👤 Профиль")
async def profile(message: types.Message):
    user_id = message.from_user.id
    user = await get_user(user_id)

    name = get_display_name(user_id, user)

    vip_status = "Нет"
    if user.get('vip_until'):
        try:
            vip_until = datetime.fromisoformat(user['vip_until'])
            if datetime.now() < vip_until:
                vip_status = f"✅ до {vip_until.strftime('%d.%m.%Y')}"
        except:
            pass

    boost_status = "Нет"
    if user.get('boost_until'):
        try:
            boost_until = datetime.fromisoformat(user['boost_until'])
            if datetime.now() < boost_until:
                boost_status = f"⚡️ x{user['boost_multiplier']}"
        except:
            pass

    used_promos = json.loads(user['used_promos']) if isinstance(user['used_promos'], str) else user['used_promos']

    fuel_bar = get_fuel_bar(user['fuel'], user['max_fuel'])

    text = (
        f"👤 <b>ПРОФИЛЬ</b>\n\n"
        f"{name}\n"
        f"🆔 <code>{user_id}</code>\n"
        f"📅 {user['register_date']}\n\n"
        f"💰 <b>Баланс:</b> {user['balance']} монет\n"
        f"⛽ <b>Топливо:</b> {fuel_bar} {user['fuel']}/{user['max_fuel']}\n"
        f"🛠 <b>Бур:</b> {DRILL_LEVELS[user['drill_level']]['name']}\n"
        f"🗺️ <b>Локация:</b> {LOCATIONS[user['current_location']]['name']}\n\n"
        f"👑 <b>VIP:</b> {vip_status}\n"
        f"⚡️ <b>Буст:</b> {boost_status}\n"
        f"⛏ <b>Добыто:</b> {user['total_mined']} ед.\n"
        f"👥 <b>Рефералов:</b> {user['referral_count']}\n"
        f"💎 <b>Донатов:</b> {user['total_donated']} ₽\n"
        f"🎁 <b>Промокодов:</b> {len(used_promos)}"
    )

    await message.answer(text, reply_markup=main_keyboard(user_id), parse_mode=ParseMode.HTML)


# ===================== РЕФЕРАЛЫ =====================
@dp.message(F.text == "👥 Рефералы")
async def referrals(message: types.Message):
    user_id = message.from_user.id
    user = await get_user(user_id)
    bot_username = (await bot.me()).username
    link = f"https://t.me/{bot_username}?start={user_id}"

    text = (
        f"👥 <b>РЕФЕРАЛЬНАЯ СИСТЕМА</b>\n\n"
        f"🔗 <b>Твоя ссылка:</b>\n"
        f"<code>{link}</code>\n\n"
        f"👥 <b>Приглашено:</b> {user['referral_count']}\n"
        f"💰 <b>Заработано:</b> {user['referral_earnings']} монет\n\n"
        f"🎁 <b>Бонусы за приглашение:</b>\n"
        f"• За друга: <b>+200 монет</b>\n"
        f"• Другу: <b>+100 монет</b>\n"
        f"• 15% от донатов рефералов"
    )

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📋 Копировать ссылку", callback_data="copy_ref")],
        [InlineKeyboardButton(text="📤 Поделиться",
                              url=f"https://t.me/share/url?url={link}&text=🔥 Играй со мной в Miner Bot!")],
        [InlineKeyboardButton(text="◀️ Назад", callback_data="back_main")]
    ])

    await message.answer(text, reply_markup=kb, parse_mode=ParseMode.HTML)


@dp.callback_query(F.data == "copy_ref")
async def copy_ref(callback: types.CallbackQuery):
    await callback.answer("🔗 Ссылка скопирована!", show_alert=True)


# ===================== ЕЖЕДНЕВНЫЙ БОНУС =====================
@dp.message(F.text == "🎁 Бонус")
async def daily_bonus(message: types.Message):
    user_id = message.from_user.id
    user = await get_user(user_id)
    print(f"🔍 last_daily в базе: {user.get('last_daily')}")
    print(f"🔍 daily_streak: {user.get('daily_streak')}")
    today = datetime.now().date()

    # Получаем дату последнего бонуса
    last_bonus = user.get('last_daily')

    # Если есть last_bonus и он не None
    if last_bonus and last_bonus != "None" and last_bonus != "null":
        try:
            last_date = datetime.fromisoformat(last_bonus).date()
            if last_date == today:
                # Считаем время до следующего бонуса
                next_bonus = datetime.combine(today + timedelta(days=1), datetime.min.time())
                time_left = next_bonus - datetime.now()
                hours = int(time_left.total_seconds() // 3600)
                minutes = int((time_left.total_seconds() % 3600) // 60)

                await message.answer(
                    f"⏳ Ты уже получал бонус сегодня!\n"
                    f"Следующий бонус через: {hours}ч {minutes}м"
                )
                return
        except (ValueError, TypeError):
            # Если дата кривая — выдаём бонус
            pass

    # Выдаём бонус
    bonus = 50
    user['balance'] += bonus
    user['daily_streak'] = user.get('daily_streak', 0) + 1
    user['last_daily'] = datetime.now().isoformat()
    print(f"✅ Сохраняю last_daily: {user['last_daily']}")
    print(f"✅ Сохраняю daily_streak: {user['daily_streak']}")

    await update_user(user_id,
                      balance=user['balance'],
                      daily_streak=user['daily_streak'],
                      last_daily=user['last_daily'])

    text = f"🎁 <b>ЕЖЕДНЕВНЫЙ БОНУС</b>\n\n💰 +{bonus} монет\n📆 Серия: {user['daily_streak']} дней"

    if user['daily_streak'] % 7 == 0:
        extra = 100
        user['balance'] += extra
        await update_user(user_id, balance=user['balance'])
        text += f"\n\n🎉 <b>Бонус за неделю!</b> +{extra} монет"

    await message.answer(text, parse_mode=ParseMode.HTML)


@dp.callback_query(F.data == "enter_startvip")
async def enter_startvip(callback: types.CallbackQuery, state: FSMContext):
    """Автоматическая активация промокода STARTVIP"""
    await callback.message.delete()
    await callback.message.answer("⏳ Активирую промокод STARTVIP...")

    # Создаём искусственное сообщение с кодом
    class FakeMessage:
        def __init__(self, text, from_user):
            self.text = text
            self.from_user = from_user

    fake_msg = FakeMessage("STARTVIP", callback.from_user)
    await process_promo(fake_msg, state)
    await callback.answer()


@dp.message(PromoStates.waiting_for_promo)
async def process_promo(message: types.Message, state: FSMContext):
    """Обработка ввода промокода"""
    user_id = message.from_user.id
    user = await get_user(user_id)
    promo_code = message.text.strip().upper()
    promos = await get_promo_codes_db()

    if promo_code not in promos:
        await message.answer("❌ Промокод не найден", reply_markup=main_keyboard(user_id))
        await state.clear()
        return

    promo = promos[promo_code]
    used_promos = json.loads(user['used_promos']) if isinstance(user['used_promos'], str) else user['used_promos']

    if user_id in promo['used_by']:
        await message.answer("❌ Ты уже использовал этот промокод", reply_markup=main_keyboard(user_id))
        await state.clear()
        return

    if len(promo['used_by']) >= promo['uses']:
        await message.answer("❌ Промокод закончился", reply_markup=main_keyboard(user_id))
        await state.clear()
        return

    reward_text = apply_promo_reward(user, promo)
    promo['used_by'].append(user_id)
    used_promos.append(promo_code)

    await update_user(user_id,
                      balance=user['balance'],
                      vip_until=user['vip_until'],
                      boost_until=user['boost_until'],
                      drill_level=user['drill_level'],
                      used_promos=used_promos)

    await update_promo_db(promo_code, used_by=promo['used_by'])

    await message.answer(
        f"✅ Промокод активирован!\n\nТы получил:\n{reward_text}",
        reply_markup=main_keyboard(user_id)
    )
    await state.clear()


def apply_promo_reward(user, promo_data):
    """Применяет награду за промокод"""
    if promo_data['type'] == "balance":
        user['balance'] += promo_data['value']
        return f"💰 +{promo_data['value']} монет"

    elif promo_data['type'] == "vip":
        user['vip_until'] = (datetime.now() + timedelta(days=promo_data['value'])).isoformat()
        return f"👑 VIP на {promo_data['value']} дней"

    elif promo_data['type'] == "boost":
        user['boost_until'] = (datetime.now() + timedelta(hours=promo_data['value'])).isoformat()
        user['boost_multiplier'] = 2.0
        return f"⚡️ Буст x2 на {promo_data['value']} часов"

    elif promo_data['type'] == "drill":
        user['drill_level'] = promo_data['value']
        return f"🛠 Бур {DRILL_LEVELS[promo_data['value']]['name']}"

    elif promo_data['type'] == "combo":
        rewards = []
        if 'vip' in promo_data['value']:
            user['vip_until'] = (datetime.now() + timedelta(days=promo_data['value']['vip'])).isoformat()
            rewards.append(f"👑 VIP на {promo_data['value']['vip']} дней")
        if 'boost' in promo_data['value']:
            user['boost_until'] = (datetime.now() + timedelta(hours=promo_data['value']['boost'])).isoformat()
            user['boost_multiplier'] = 2.0
            rewards.append(f"⚡️ Буст x2 на {promo_data['value']['boost']} часов")
        if 'drill' in promo_data['value']:
            user['drill_level'] = promo_data['value']['drill']
            rewards.append(f"🛠 {DRILL_LEVELS[promo_data['value']['drill']]['name']}")
        if 'balance' in promo_data['value']:
            user['balance'] += promo_data['value']['balance']
            rewards.append(f"💰 {promo_data['value']['balance']} монет")
        return " + ".join(rewards)

    return ""

@dp.callback_query(F.data == "enter_startvip")
async def enter_startvip_simple(callback: types.CallbackQuery):
    """Простая активация STARTVIP без FSM"""
    user_id = callback.from_user.id
    user = await get_user(user_id)

    # Проверяем, использовал ли уже
    used = json.loads(user.get('used_promos', '[]'))
    if 'STARTVIP' in used:
        await callback.message.edit_text("❌ Ты уже активировал этот промокод!")
        await callback.answer()
        return

    # Начисляем бонус
    user['balance'] += 500
    user['vip_until'] = (datetime.now() + timedelta(days=7)).isoformat()
    user['drill_level'] = 5
    used.append('STARTVIP')

    await update_user(user_id,
                      balance=user['balance'],
                      vip_until=user['vip_until'],
                      drill_level=5,
                      used_promos=json.dumps(used))

    await callback.message.edit_text(
        "✅ <b>Промокод активирован!</b>\n\n"
        "Ты получил:\n"
        "💰 500 монет\n"
        "👑 VIP на 7 дней\n"
        "🛠 Элитный бур (5 уровень)\n\n"
        "Возвращайся в главное меню!",
        parse_mode=ParseMode.HTML
    )
    await callback.answer()

# ===================== ПОМОЩЬ =====================
@dp.message(F.text == "❓ Помощь")
async def help_cmd(message: types.Message):
    text = (
        "❓ <b>ПОМОЩЬ</b>\n\n"
        "⛏ <b>Добыча:</b> тратит топливо, даёт руду\n"
        "📦 <b>Инвентарь:</b> хранение ресурсов\n"
        "🛠 <b>Буры:</b> улучшай для бонусов\n"
        "🗺️ <b>Локации:</b> разные шансы на руду\n"
        "🏪 <b>Магазин:</b> покупай топливо, продавай руду\n"
        "📊 <b>Топ:</b> лучшие игроки\n"
        "👥 <b>Рефералы:</b> приглашай друзей\n"
        "⛽ <b>Статус топлива:</b> сколько осталось\n"
        "💎 <b>Донат:</b> поддержка проекта\n"
        "🎁 <b>Бонус:</b> ежедневная награда"
    )
    await message.answer(text, reply_markup=main_keyboard(message.from_user.id), parse_mode=ParseMode.HTML)


# ===================== ВОЗВРАТ =====================
@dp.callback_query(F.data == "back_main")
async def back_main(callback: types.CallbackQuery):
    await callback.message.delete()
    await callback.message.answer("Главное меню", reply_markup=main_keyboard(callback.from_user.id))
    await callback.answer()


# ===================== АДМИНКА =====================
@dp.message(F.text == "👑 Админка")
async def admin_panel(message: types.Message):
    if message.from_user.id != CREATOR_ID:
        return
    await message.answer("👑 <b>АДМИН-ПАНЕЛЬ</b>\n\nВыбери действие:", reply_markup=get_admin_keyboard(),
                         parse_mode=ParseMode.HTML)


@dp.message(F.text == "📊 Статистика")
async def admin_stats(message: types.Message):
    if message.from_user.id != CREATOR_ID:
        return
    users = await get_all_users()
    total_balance = sum(u['balance'] for u in users)
    total_donations = sum(u['total_donated'] for u in users)
    total_mined = sum(u['total_mined'] for u in users)
    vip_count = sum(1 for u in users if u.get('vip_until') and datetime.now() < datetime.fromisoformat(u['vip_until']))

    text = (
        f"📊 <b>СТАТИСТИКА</b>\n\n"
        f"👥 Всего игроков: <b>{len(users)}</b>\n"
        f"💰 Общий баланс: <b>{total_balance}</b> монет\n"
        f"💎 Всего донатов: <b>{total_donations}</b> ₽\n"
        f"⛏ Всего добыто: <b>{total_mined}</b> ед.\n"
        f"👑 VIP игроков: <b>{vip_count}</b>"
    )
    await message.answer(text, parse_mode=ParseMode.HTML)


@dp.message(F.text == "👥 Все игроки")
async def admin_players(message: types.Message):
    if message.from_user.id != CREATOR_ID:
        return
    users = await get_all_users()
    text = "👥 <b>СПИСОК ИГРОКОВ</b>\n\n"
    for i, u in enumerate(users[:10], 1):
        name = u['first_name'] or f"ID {u['user_id']}"
        text += f"{i}. {name[:20]} — {u['balance']}💰 | {u['fuel']}/{u['max_fuel']}⛽\n"
    if len(users) > 10:
        text += f"\n... и ещё {len(users) - 10} игроков"
    await message.answer(text, parse_mode=ParseMode.HTML)


@dp.message(F.text == "💰 Выдать монеты")
async def admin_give_money(message: types.Message, state: FSMContext):
    if message.from_user.id != CREATOR_ID:
        return
    await message.answer("Введи ID пользователя:")
    await state.set_state(AdminStates.waiting_for_user_id)


@dp.message(AdminStates.waiting_for_user_id)
async def admin_process_uid(message: types.Message, state: FSMContext):
    try:
        uid = int(message.text)
        user = await get_user(uid)
        await state.update_data(target_uid=uid)
        await message.answer("Введи сумму монет:")
        await state.set_state(AdminStates.waiting_for_amount)
    except:
        await message.answer("❌ Неверный ID")
        await state.clear()


@dp.message(AdminStates.waiting_for_amount)
async def admin_process_amount(message: types.Message, state: FSMContext):
    try:
        amount = int(message.text)
        data = await state.get_data()
        uid = data['target_uid']
        user = await get_user(uid)
        await update_user(uid, balance=user['balance'] + amount)
        await message.answer(f"✅ Выдано {amount} монет пользователю {uid}")
        await state.clear()
    except:
        await message.answer("❌ Неверная сумма")
        await state.clear()

@dp.callback_query(F.data == "admin_list_drills")
async def admin_list_drills(callback: types.CallbackQuery):
    text = "🛠 <b>СПИСОК ВСЕХ БУРОВ</b>\n\n"
    for level, drill in DRILL_LEVELS.items():
        text += f"{level}. {drill['name']} — +{drill['bonus']}%\n"
        text += f"   Редкость: {drill['rarity']}\n"
        if drill.get('price_coins', 0) > 0:
            text += f"   💰 {drill['price_coins']} монет\n"
        elif drill.get('price_rub', 0) > 0:
            text += f"   💎 {drill['price_rub']}₽\n"
        text += "\n"

    await callback.message.edit_text(text, parse_mode=ParseMode.HTML)
    await callback.answer()

# ===================== УПРАВЛЕНИЕ ПРОМОКОДАМИ =====================
@dp.message(F.text == "🎫 Промокоды")
async def admin_promo_menu(message: types.Message):
    if message.from_user.id != CREATOR_ID:
        return
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="➕ Создать промокод", callback_data="admin_create_promo")],
        [InlineKeyboardButton(text="📋 Список промокодов", callback_data="admin_list_promos")],
        [InlineKeyboardButton(text="❌ Удалить промокод", callback_data="admin_delete_promo")],
        [InlineKeyboardButton(text="◀️ Назад", callback_data="back_to_admin")]
    ])
    await message.answer("🎫 <b>УПРАВЛЕНИЕ ПРОМОКОДАМИ</b>", reply_markup=kb, parse_mode=ParseMode.HTML)


@dp.callback_query(F.data == "admin_create_promo")
async def admin_create_promo(callback: types.CallbackQuery, state: FSMContext):
    await callback.message.edit_text("Введи название промокода (например: SUMMER100):")
    await state.set_state(AdminStates.waiting_for_promo_code)
    await callback.answer()


@dp.message(AdminStates.waiting_for_promo_code)
async def admin_process_promo_code(message: types.Message, state: FSMContext):
    code = message.text.upper()
    await state.update_data(promo_code=code)

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💰 Монеты", callback_data="promo_type_balance")],
        [InlineKeyboardButton(text="👑 VIP", callback_data="promo_type_vip")],
        [InlineKeyboardButton(text="⚡️ Буст", callback_data="promo_type_boost")],
        [InlineKeyboardButton(text="🛠 Бур", callback_data="promo_type_drill")],
        [InlineKeyboardButton(text="🎁 Комбо", callback_data="promo_type_combo")]
    ])

    await message.answer("Выбери тип награды:", reply_markup=kb)
    await state.set_state(AdminStates.waiting_for_promo_type)


@dp.callback_query(AdminStates.waiting_for_promo_type, F.data.startswith("promo_type_"))
async def admin_process_type(callback: types.CallbackQuery, state: FSMContext):
    ptype = callback.data.replace("promo_type_", "")
    await state.update_data(promo_type=ptype)

    if ptype == "combo":
        await callback.message.edit_text(
            "Введи значение в формате: vip=дни,boost=часы,drill=уровень,balance=монеты\nНапример: vip=7,boost=24,drill=5,balance=500")
    else:
        await callback.message.edit_text("Введи значение награды:")
    await callback.answer()
    await state.set_state(AdminStates.waiting_for_promo_value)


@dp.message(AdminStates.waiting_for_promo_value)
async def admin_process_value(message: types.Message, state: FSMContext):
    data = await state.get_data()
    ptype = data['promo_type']

    if ptype == "combo":
        try:
            parts = message.text.strip().split(',')
            combo_value = {}
            for part in parts:
                key, val = part.strip().split('=')
                combo_value[key] = int(val)
            await state.update_data(promo_value=combo_value)
        except:
            await message.answer("❌ Неверный формат")
            return
    else:
        try:
            val = int(message.text)
            await state.update_data(promo_value=val)
        except:
            await message.answer("❌ Введи число")
            return

    await message.answer("Введи количество использований:")
    await state.set_state(AdminStates.waiting_for_promo_uses)


@dp.message(AdminStates.waiting_for_promo_uses)
async def admin_process_uses(message: types.Message, state: FSMContext):
    try:
        uses = int(message.text)
        data = await state.get_data()

        p = await get_pool()
        async with p.acquire() as conn:
            async with conn.cursor() as cur:
                await cur.execute('''
                                  INSERT INTO promo_codes (code, type, value, uses, used_by)
                                  VALUES (%s, %s, %s, %s, %s)
                                  ''', (data['promo_code'], data['promo_type'], json.dumps(data['promo_value']), uses,
                                        json.dumps([])))
                await conn.commit()

        await bot.notifier.promo_created(data['promo_code'], data['promo_type'], str(data['promo_value']), uses)

        if uses > 1 and data['promo_type'] != "combo":
            users = await get_all_users()
            user_ids = [u['user_id'] for u in users if u['user_id'] != CREATOR_ID]
            await bot.notifier.broadcast(
                user_ids,
                f"🎫 <b>НОВЫЙ ПРОМОКОД!</b>\n\n"
                f"🔑 Код: <b>{data['promo_code']}</b>\n"
                f"🎁 Тип: {data['promo_type']}\n"
                f"📦 Значение: {data['promo_value']}\n\n"
                f"🏃 Успей активировать!"
            )

        await message.answer(f"✅ Промокод {data['promo_code']} создан!")
        await state.clear()
    except Exception as e:
        await message.answer(f"❌ Ошибка: {e}")
        await state.clear()


@dp.callback_query(F.data == "admin_list_promos")
async def admin_list_promos(callback: types.CallbackQuery):
    promos = await get_promo_codes_db()

    if not promos:
        await callback.message.edit_text(
            "📭 Нет активных промокодов",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="◀️ Назад", callback_data="back_to_promo_admin")]
            ])
        )
        await callback.answer()
        return

    text = "📋 <b>АКТИВНЫЕ ПРОМОКОДЫ</b>\n\n"
    for code, data in promos.items():
        used = len(data['used_by'])
        text += f"• <b>{code}</b> — {data['type']} = {data['value']}\n"
        text += f"  Использовано: {used}/{data['uses']}\n\n"

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔄 Обновить", callback_data="admin_list_promos")],
        [InlineKeyboardButton(text="◀️ Назад", callback_data="back_to_promo_admin")]
    ])

    await callback.message.edit_text(text, reply_markup=kb, parse_mode=ParseMode.HTML)
    await callback.answer()


@dp.callback_query(F.data == "admin_delete_promo")
async def admin_delete_promo(callback: types.CallbackQuery, state: FSMContext):
    await callback.message.edit_text("Введи название промокода для удаления:")
    await state.set_state(AdminStates.waiting_for_promo_delete)
    await callback.answer()


@dp.message(AdminStates.waiting_for_promo_delete)
async def admin_process_delete(message: types.Message, state: FSMContext):
    code = message.text.upper()
    await delete_promo_db(code)
    await message.answer(f"✅ Промокод {code} удалён!")
    await state.clear()


@dp.callback_query(F.data == "back_to_promo_admin")
async def back_to_promo_admin(callback: types.CallbackQuery):
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="➕ Создать промокод", callback_data="admin_create_promo")],
        [InlineKeyboardButton(text="📋 Список промокодов", callback_data="admin_list_promos")],
        [InlineKeyboardButton(text="❌ Удалить промокод", callback_data="admin_delete_promo")],
        [InlineKeyboardButton(text="◀️ Назад", callback_data="back_to_admin")]
    ])
    await callback.message.edit_text("🎫 <b>УПРАВЛЕНИЕ ПРОМОКОДАМИ</b>", reply_markup=kb, parse_mode=ParseMode.HTML)
    await callback.answer()


@dp.callback_query(F.data == "back_to_admin")
async def back_to_admin(callback: types.CallbackQuery):
    await admin_panel(callback.message)
    await callback.answer()


@dp.message(F.text == "📢 Рассылка")
async def admin_broadcast(message: types.Message, state: FSMContext):
    if message.from_user.id != CREATOR_ID:
        return
    await message.answer("Введи текст для рассылки:")
    await state.set_state(AdminStates.waiting_for_broadcast)


@dp.message(AdminStates.waiting_for_broadcast)
async def admin_process_broadcast(message: types.Message, state: FSMContext):
    text = message.text
    users = await get_all_users()
    sent = 0
    failed = 0

    await message.answer("📢 Рассылка началась...")
    for u in users:
        try:
            await bot.send_message(u['user_id'], f"📢 <b>РАССЫЛКА</b>\n\n{text}", parse_mode=ParseMode.HTML)
            sent += 1
            await asyncio.sleep(0.05)
        except:
            failed += 1

    await message.answer(f"✅ Отправлено: {sent}\n❌ Ошибок: {failed}")
    await state.clear()


@dp.message(F.text == "💎 Валюта")
async def admin_currency(message: types.Message):
    if message.from_user.id != CREATOR_ID:
        return
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="➕ Добавить всем", callback_data="currency_add_all")],
        [InlineKeyboardButton(text="📊 Топ балансов", callback_data="top_balance")]
    ])
    await message.answer("💎 <b>УПРАВЛЕНИЕ ВАЛЮТОЙ</b>", reply_markup=kb, parse_mode=ParseMode.HTML)


@dp.message(F.text == "🛠 Управление бурами")
async def admin_drills_menu(message: types.Message):
    if message.from_user.id != CREATOR_ID:
        return
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📋 Список буров", callback_data="admin_list_drills")],
        [InlineKeyboardButton(text="➕ Выдать бур", callback_data="admin_give_drill")],
        [InlineKeyboardButton(text="◀️ Назад", callback_data="back_to_admin")]
    ])
    await message.answer("🛠 <b>УПРАВЛЕНИЕ БУРАМИ</b>", reply_markup=kb, parse_mode=ParseMode.HTML)


@dp.callback_query(F.data == "admin_give_drill")
async def admin_give_drill_start(callback: types.CallbackQuery, state: FSMContext):
    await callback.message.edit_text("Введи ID пользователя:")
    await state.set_state(AdminStates.waiting_for_drill_user_id)
    await callback.answer()


@dp.message(AdminStates.waiting_for_drill_user_id)
async def admin_give_drill_user(message: types.Message, state: FSMContext):
    try:
        uid = int(message.text)
        await state.update_data(target_uid=uid)

        kb = []
        for level, drill in DRILL_LEVELS.items():
            kb.append([InlineKeyboardButton(
                text=f"{drill['name']} (+{drill['bonus']}%)",
                callback_data=f"admin_give_drill_{level}"
            )])

        await message.answer("Выбери бур:", reply_markup=InlineKeyboardMarkup(inline_keyboard=kb))
        await state.set_state(AdminStates.waiting_for_drill_level)
    except:
        await message.answer("❌ Неверный ID")
        await state.clear()


@dp.callback_query(F.data.startswith("admin_give_drill_"))
async def admin_give_drill_level(callback: types.CallbackQuery, state: FSMContext):
    level = int(callback.data.split("_")[3])
    data = await state.get_data()
    uid = data['target_uid']

    user = await get_user(uid)
    await update_user(uid, drill_level=level)

    await callback.message.edit_text(f"✅ Бур {DRILL_LEVELS[level]['name']} выдан пользователю {uid}")
    await state.clear()
    await callback.answer()


@dp.message(F.text == "🔧 Техработы")
async def admin_maintenance(message: types.Message, state: FSMContext):
    if message.from_user.id != CREATOR_ID:
        return
    await message.answer("Введи текст предупреждения о техработах (или /cancel):")
    await state.set_state(AdminStates.waiting_for_maintenance)


@dp.message(AdminStates.waiting_for_maintenance)
async def admin_process_maintenance(message: types.Message, state: FSMContext):
    if message.text == "/cancel":
        await state.clear()
        await message.answer("❌ Отменено")
        return

    users = await get_all_users()
    sent = 0

    warn_text = f"🔧 <b>ТЕХНИЧЕСКИЕ РАБОТЫ</b>\n\n{message.text}\n\n⏳ Бот может временно не работать."

    for u in users:
        try:
            await bot.send_message(u['user_id'], warn_text, parse_mode=ParseMode.HTML)
            sent += 1
        except:
            pass

    await message.answer(f"✅ Предупреждение отправлено {sent} игрокам")
    await state.clear()


@dp.message(F.text == "◀️ Выйти")
async def admin_exit(message: types.Message):
    await message.answer("Выход из админ-панели", reply_markup=main_keyboard(message.from_user.id))


# ===================== ДОНАТ =====================
@dp.message(F.text == "💎 Донат")
async def donate_menu(message: types.Message):
    """Главное меню доната"""
    text = (
        "💎 <b>ПОДДЕРЖКА ПРОЕКТА</b>\n\n"
        "⛽ <b>Топливо:</b>\n"
        "• 50 ед. — 99₽\n"
        "• 150 ед. — 249₽\n"
        "• 300 ед. — 499₽\n\n"
        "👑 <b>VIP статусы:</b>\n"
        "• VIP на месяц — 299₽\n"
        "• VIP на 3 месяца — 699₽\n"
        "• VIP на полгода — 1199₽\n"
        "• VIP на год — 1499₽\n\n"
        "⚡️ <b>Бусты:</b>\n"
        "• x2 на 2 часа — 49₽\n"
        "• x2 на 12 часов — 199₽\n"
        "• x2 на 24 часа — 299₽\n"
        "• x3 на 1 час — 499₽\n\n"
        "🛠 <b>Легендарные буры:</b>\n"
        "• ⚡ Грозовой бур — 1000₽\n"
        "• 🌈 Кристальный бур — 1500₽\n"
        "• 🕯️ Теневой бур — 1500₽\n\n"
        "💳 Оплата временно недоступна. Скоро подключим!"
    )

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⛽ Топливо", callback_data="donate_fuel")],
        [InlineKeyboardButton(text="👑 VIP статусы", callback_data="donate_vip")],
        [InlineKeyboardButton(text="⚡️ Бусты", callback_data="donate_boost")],
        [InlineKeyboardButton(text="🛠 Легендарные буры", callback_data="donate_drills")],
        [InlineKeyboardButton(text="◀️ Назад", callback_data="back_main")]
    ])

    await message.answer(text, reply_markup=kb, parse_mode=ParseMode.HTML)


@dp.callback_query(F.data == "donate_fuel")
async def donate_fuel(callback: types.CallbackQuery):
    """Раздел топлива в донате"""
    await callback.answer("⛽ Покупка топлива за рубли временно недоступна. Скоро будет!", show_alert=True)


@dp.callback_query(F.data == "donate_vip")
async def donate_vip(callback: types.CallbackQuery):
    """Раздел VIP в донате"""
    await callback.answer("👑 Покупка VIP временно недоступна. Скоро будет!", show_alert=True)


@dp.callback_query(F.data == "donate_boost")
async def donate_boost(callback: types.CallbackQuery):
    """Раздел бустов в донате"""
    await callback.answer("⚡️ Покупка бустов временно недоступна. Скоро будет!", show_alert=True)


@dp.callback_query(F.data == "donate_drills")
async def donate_drills(callback: types.CallbackQuery):
    """Раздел легендарных буров в донате"""
    await callback.answer("🛠 Покупка легендарных буров временно недоступна. Скоро будет!", show_alert=True)


# ===================== УСПЕШНЫЙ ПЛАТЕЖ =====================
@dp.pre_checkout_query()
async def pre_checkout_query(pre_checkout_query: PreCheckoutQuery):
    await pre_checkout_query.answer(ok=True)


@dp.message(F.content_type == ContentType.SUCCESSFUL_PAYMENT)
async def successful_payment(message: types.Message):
    payment = message.successful_payment
    payload = payment.invoice_payload

    user_id = message.from_user.id
    user = await get_user(user_id)
    user['total_donated'] += payment.total_amount // 100
    await update_user(user_id, total_donated=user['total_donated'])

    if payload.startswith("fuel_"):
        _, size, fuel_amount = payload.split("_")
        fuel_amount = int(fuel_amount)

        old_fuel = user['fuel']
        user['fuel'] = min(user['fuel'] + fuel_amount, user['max_fuel'])
        await update_user(user_id, fuel=user['fuel'])

        text = f"✅ <b>Спасибо за поддержку!</b>\n\n⛽ Получено {fuel_amount} топлива\n💰 Топливо: {user['fuel']}/{user['max_fuel']}"

    elif payload.startswith("vip_"):
        days = int(payload.split("_")[1])
        user['vip_until'] = (datetime.now() + timedelta(days=days)).isoformat()
        await update_user(user_id, vip_until=user['vip_until'])
        text = f"👑 <b>VIP активирован!</b>\n\n✅ До {datetime.fromisoformat(user['vip_until']).strftime('%d.%m.%Y')}"

    elif payload.startswith("boost_"):
        hours = int(payload.split("_")[1])
        user['boost_until'] = (datetime.now() + timedelta(hours=hours)).isoformat()
        user['boost_multiplier'] = 2.0
        await update_user(user_id, boost_until=user['boost_until'], boost_multiplier=user['boost_multiplier'])
        text = f"⚡️ <b>Буст активирован!</b>\n\n✅ x2 на {hours} часов"

    elif payload.startswith("drill_"):
        level = int(payload.split("_")[1])
        user['drill_level'] = level
        await update_user(user_id, drill_level=level)
        text = f"🛠 <b>Бур получен!</b>\n\n✅ {DRILL_LEVELS[level]['name']}"

    else:
        text = "✅ Спасибо за поддержку!"

    await message.answer(text, reply_markup=main_keyboard(user_id), parse_mode=ParseMode.HTML)


# ===================== ПЛАНИРОВЩИК ТОПЛИВА =====================
async def scheduled_fuel():
    """Плановое восстановление топлива каждые 10 минут"""
    while True:
        await asyncio.sleep(FUEL_CONFIG["regen_interval"] * 60)

        users = await get_all_users()
        regen_count = 0
        full_notify = 0

        for u in users:
            try:
                old_fuel = u['fuel']
                max_fuel = get_max_fuel(u)
                regen_rate = get_regen_rate(u)

                if old_fuel < max_fuel:
                    new_fuel = min(old_fuel + regen_rate, max_fuel)
                    await update_user(u['user_id'], fuel=new_fuel)
                    regen_count += 1

                    if new_fuel == max_fuel and FUEL_CONFIG["regen_notify"]:
                        if 'notifier' in bot:
                            await bot.notifier.fuel_refilled(u['user_id'], new_fuel, max_fuel, regen_rate)
                            full_notify += 1
            except Exception as e:
                print(f"Ошибка регена: {e}")

        now = now_moscow()
        print(f"⛽ {now.strftime('%H:%M')} Реген: {regen_count} игроков, уведомлений: {full_notify}")

# ========================== ТОП ====================
@dp.message(F.text == "📊 Топ")
async def top_menu(message: types.Message):
    """Главное меню топа"""
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💰 По монетам", callback_data="top_balance")],
        [InlineKeyboardButton(text="👥 По рефералам", callback_data="top_referrals")],
        [InlineKeyboardButton(text="🗺️ По локациям", callback_data="top_locations")],
        [InlineKeyboardButton(text="❌ Закрыть", callback_data="close")]
    ])
    await message.answer("📊 <b>ВЫБЕРИ КАТЕГОРИЮ ТОПА</b>", reply_markup=kb, parse_mode=ParseMode.HTML)


@dp.callback_query(F.data == "top_balance")
async def top_balance(callback: types.CallbackQuery):
    """Топ по монетам"""
    users = await get_all_users()
    sorted_users = sorted(users, key=lambda x: x['balance'], reverse=True)[:10]
    text = "💰 <b>ТОП ПО МОНЕТАМ</b>\n\n"

    medals = ["🥇", "🥈", "🥉"]
    for i, u in enumerate(sorted_users, 1):
        medal = medals[i - 1] if i <= 3 else f"{i}."
        name = get_display_name(u['user_id'], u)
        text += f"{medal} {name} — {u['balance']}💰\n"

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="◀️ Назад", callback_data="top_menu")],
        [InlineKeyboardButton(text="❌ Закрыть", callback_data="close")]
    ])
    await callback.message.edit_text(text, reply_markup=kb, parse_mode=ParseMode.HTML)
    await callback.answer()


@dp.callback_query(F.data == "top_referrals")
async def top_referrals(callback: types.CallbackQuery):
    """Топ по рефералам"""
    users = await get_all_users()
    sorted_users = sorted(users, key=lambda x: x['referral_count'], reverse=True)[:10]
    text = "👥 <b>ТОП ПО РЕФЕРАЛАМ</b>\n\n"

    medals = ["🥇", "🥈", "🥉"]
    for i, u in enumerate(sorted_users, 1):
        medal = medals[i - 1] if i <= 3 else f"{i}."
        name = get_display_name(u['user_id'], u)
        text += f"{medal} {name} — {u['referral_count']} 👥\n"

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="◀️ Назад", callback_data="top_menu")],
        [InlineKeyboardButton(text="❌ Закрыть", callback_data="close")]
    ])
    await callback.message.edit_text(text, reply_markup=kb, parse_mode=ParseMode.HTML)
    await callback.answer()


@dp.callback_query(F.data == "top_locations")
async def top_locations(callback: types.CallbackQuery):
    """Топ по локациям"""
    users = await get_all_users()
    sorted_users = sorted(users, key=lambda x: x['current_location'], reverse=True)[:10]
    text = "🗺️ <b>ТОП ПО ЛОКАЦИЯМ</b>\n\n"

    medals = ["🥇", "🥈", "🥉"]
    for i, u in enumerate(sorted_users, 1):
        medal = medals[i - 1] if i <= 3 else f"{i}."
        name = get_display_name(u['user_id'], u)
        loc_name = LOCATIONS[u['current_location']]['name']
        text += f"{medal} {name} — {loc_name}\n"

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="◀️ Назад", callback_data="top_menu")],
        [InlineKeyboardButton(text="❌ Закрыть", callback_data="close")]
    ])
    await callback.message.edit_text(text, reply_markup=kb, parse_mode=ParseMode.HTML)
    await callback.answer()


@dp.callback_query(F.data == "top_menu")
async def back_to_top_menu(callback: types.CallbackQuery):
    """Возврат в главное меню топа"""
    await top_menu(callback.message)
    await callback.answer()

# ===================== УПРАВЛЕНИЕ ПОКУПКАМИ =================
@dp.callback_query(F.data.startswith("buy_drill_"))
async def buy_drill(callback: types.CallbackQuery):
    level = int(callback.data.split("_")[2])
    user_id = callback.from_user.id
    user = await get_user(user_id)
    drill = DRILL_LEVELS[level]

    # Проверяем, не куплен ли уже
    if user['drill_level'] >= level:
        await callback.answer("❌ У тебя уже есть этот бур или лучше!", show_alert=True)
        return

    # Проверка цены (для монет)
    if drill.get('price_coins', 0) > 0:
        if user['balance'] < drill['price_coins']:
            await callback.answer(f"❌ Не хватает {drill['price_coins'] - user['balance']}💰", show_alert=True)
            return

        user['balance'] -= drill['price_coins']
        user['drill_level'] = level
        await update_user(user_id, balance=user['balance'], drill_level=level)

        await callback.message.edit_text(
            f"✅ <b>Поздравляем с покупкой!</b>\n\n"
            f"Ты купил: {drill['name']}\n"
            f"⚡️ Бонус: +{drill['bonus']}%\n"
            f"💰 Остаток: {user['balance']} монет"
        )

    # Для донатных буров (за рубли)
    elif drill.get('price_rub', 0) > 0:
        await callback.answer("💎 Покупка за рубли временно недоступна", show_alert=True)

    await callback.answer()

# ===================== МАГАЗИН - ВСЕ КНОПКИ =====================
@dp.callback_query(F.data == "shop_drills")
async def shop_drills_callback(callback: types.CallbackQuery):
    """Магазин буров с категориями"""
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🟢 Обычные", callback_data="drills_cat_common")],
        [InlineKeyboardButton(text="🔵 Необычные", callback_data="drills_cat_uncommon")],
        [InlineKeyboardButton(text="🟣 Редкие", callback_data="drills_cat_rare")],
        [InlineKeyboardButton(text="🟡 Эпические", callback_data="drills_cat_epic")],
        [InlineKeyboardButton(text="🟤 Легендарные", callback_data="drills_cat_legendary")],
        [InlineKeyboardButton(text="👑 Мифические", callback_data="drills_cat_mythic")],
        [InlineKeyboardButton(text="◀️ Назад", callback_data="back_to_shop")]
    ])

    await callback.message.edit_text(
        "🛠 <b>МАГАЗИН БУРОВ</b>\n\n"
        "Выбери категорию:",
        reply_markup=kb, parse_mode=ParseMode.HTML
    )
    await callback.answer()

@dp.callback_query(F.data == "drills_cat_common")
async def drills_cat_common(callback: types.CallbackQuery, state: FSMContext):
    """Обычные буры (1-2 ур.)"""
    await show_drill_list(callback, "common", state)

@dp.callback_query(F.data == "drills_cat_uncommon")
async def drills_cat_uncommon(callback: types.CallbackQuery, state: FSMContext):
    """Необычные буры (3-4 ур.)"""
    await show_drill_list(callback, "uncommon", state)

@dp.callback_query(F.data == "drills_cat_rare")
async def drills_cat_rare(callback: types.CallbackQuery, state: FSMContext):
    """Редкие буры (5-7 ур.)"""
    await show_drill_list(callback, "rare", state)

@dp.callback_query(F.data == "drills_cat_epic")
async def drills_cat_epic(callback: types.CallbackQuery, state: FSMContext):
    """Эпические буры (8-12 ур.)"""
    await show_drill_list(callback, "epic", state)

@dp.callback_query(F.data == "drills_cat_legendary")
async def drills_cat_legendary(callback: types.CallbackQuery, state: FSMContext):
    """Легендарные буры (13-15 ур.)"""
    await show_drill_list(callback, "legendary", state)

@dp.callback_query(F.data == "drills_cat_mythic")
async def drills_cat_mythic(callback: types.CallbackQuery, state: FSMContext):
    """Мифические буры (16-18 ур.)"""
    await show_drill_list(callback, "mythic", state)


async def show_drill_list(callback: types.CallbackQuery, category: str, state: FSMContext):
    """Показывает список буров в категории с кнопками (редактирует текущее сообщение)"""
    categories = {
        "common": {"name": "🟢 Обычные", "levels": [1, 2]},
        "uncommon": {"name": "🔵 Необычные", "levels": [3, 4]},
        "rare": {"name": "🟣 Редкие", "levels": [5, 6, 7]},
        "epic": {"name": "🟡 Эпические", "levels": [8, 9, 10, 11, 12]},
        "legendary": {"name": "🟤 Легендарные", "levels": [13, 14, 15]},
        "mythic": {"name": "👑 Мифические", "levels": [16, 17, 18]}
    }

    user_id = callback.from_user.id
    user = await get_user(user_id)

    text = f"<b>{categories[category]['name']}</b>\n\n"
    text += "👇 Нажми на бур, чтобы посмотреть подробнее:\n\n"

    kb = []

    for level in categories[category]["levels"]:
        drill = DRILL_LEVELS[level]

        if level > user['drill_level']:
            if drill.get('price_coins', 0) > 0:
                btn_text = f"🛠 {drill['name']} — {drill['price_coins']}💰"
            else:
                btn_text = f"🗺️ {drill['name']} — {drill.get('loc', 'особое место')}"
        elif level == user['drill_level']:
            btn_text = f"✅ {drill['name']} (твой)"
        else:
            btn_text = f"✅ {drill['name']}"

        kb.append([InlineKeyboardButton(text=btn_text, callback_data=f"view_drill_{level}")])

    kb.append([InlineKeyboardButton(text="◀️ Назад", callback_data="shop_drills")])

    # Редактируем текущее сообщение
    await callback.message.edit_text(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=kb),
                                     parse_mode=ParseMode.HTML)
    await callback.answer()


@dp.callback_query(F.data.startswith("view_drill_"))
async def view_drill(callback: types.CallbackQuery, state: FSMContext):
    """Показывает подробную информацию о буре с фото (редактирует сообщение)"""
    level = int(callback.data.split("_")[2])
    user_id = callback.from_user.id
    user = await get_user(user_id)
    drill = DRILL_LEVELS[level]

    # Формируем текст
    text = f"✨ <b>{drill['name']}</b>\n\n"
    text += f"🎁 <b>Редкость:</b> {drill['rarity']}\n"
    text += f"⚡️ <b>Бонус:</b> +{drill['bonus']}% к добыче\n"
    text += f"📝 <b>Описание:</b> {drill['desc']}\n\n"

    if level > user['drill_level']:
        if drill.get('price_coins', 0) > 0:
            text += f"💰 <b>Цена:</b> {drill['price_coins']} монет"
        elif drill.get('price_rub', 0) > 0:
            text += f"💎 <b>Цена:</b> {drill['price_rub']}₽"
        else:
            text += f"🗺️ <b>Можно найти в:</b> {drill.get('loc', 'особых местах')}"
    else:
        text += f"✅ <b>Уже куплен</b>"

    # Кнопки
    kb = []

    if level > user['drill_level'] and drill.get('price_coins', 0) > 0:
        kb.append([InlineKeyboardButton(text="💰 Купить", callback_data=f"buy_drill_{level}")])

    # Определяем категорию для возврата
    if level in [1, 2]:
        back_cat = "common"
    elif level in [3, 4]:
        back_cat = "uncommon"
    elif level in [5, 6, 7]:
        back_cat = "rare"
    elif level in [8, 9, 10, 11, 12]:
        back_cat = "epic"
    elif level in [13, 14, 15]:
        back_cat = "legendary"
    else:
        back_cat = "mythic"

    kb.append([InlineKeyboardButton(text="◀️ Назад к списку", callback_data=f"back_to_category_{back_cat}")])

    # Фото
    image_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "images", f"drill_{level}.jpg")
    if os.path.exists(image_path):
        photo = FSInputFile(image_path)
        # Редактируем с фото (удаляем старое и отправляем новое с фото)
        await callback.message.delete()
        await callback.message.answer_photo(
            photo=photo,
            caption=text,
            reply_markup=InlineKeyboardMarkup(inline_keyboard=kb),
            parse_mode=ParseMode.HTML
        )
    else:
        # Редактируем текст
        await callback.message.edit_text(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=kb),
                                         parse_mode=ParseMode.HTML)

    await callback.answer()


@dp.callback_query(F.data.startswith("back_to_category_"))
async def back_to_drill_category(callback: types.CallbackQuery, state: FSMContext):
    """Возврат в категорию после просмотра бура (редактирует сообщение)"""
    category = callback.data.replace("back_to_category_", "")

    categories = {
        "common": {"name": "🟢 Обычные", "levels": [1, 2]},
        "uncommon": {"name": "🔵 Необычные", "levels": [3, 4]},
        "rare": {"name": "🟣 Редкие", "levels": [5, 6, 7]},
        "epic": {"name": "🟡 Эпические", "levels": [8, 9, 10, 11, 12]},
        "legendary": {"name": "🟤 Легендарные", "levels": [13, 14, 15]},
        "mythic": {"name": "👑 Мифические", "levels": [16, 17, 18]}
    }

    user_id = callback.from_user.id
    user = await get_user(user_id)

    text = f"<b>{categories[category]['name']}</b>\n\n"
    text += "👇 Нажми на бур, чтобы посмотреть подробнее:\n\n"

    kb = []

    for level in categories[category]["levels"]:
        drill = DRILL_LEVELS[level]

        if level > user['drill_level']:
            if drill.get('price_coins', 0) > 0:
                btn_text = f"🛠 {drill['name']} — {drill['price_coins']}💰"
            else:
                btn_text = f"🗺️ {drill['name']} — {drill.get('loc', 'особое место')}"
        elif level == user['drill_level']:
            btn_text = f"✅ {drill['name']} (твой)"
        else:
            btn_text = f"✅ {drill['name']}"

        kb.append([InlineKeyboardButton(text=btn_text, callback_data=f"view_drill_{level}")])

    kb.append([InlineKeyboardButton(text="◀️ Назад", callback_data="shop_drills")])

    # Редактируем сообщение
    await callback.message.edit_text(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=kb),
                                     parse_mode=ParseMode.HTML)
    await callback.answer()

async def show_drill_list(callback: types.CallbackQuery, category: str, state: FSMContext):
    """Показывает список буров в категории"""
    categories = {
        "common": {"name": "🟢 Обычные", "levels": [1, 2]},
        "uncommon": {"name": "🔵 Необычные", "levels": [3, 4]},
        "rare": {"name": "🟣 Редкие", "levels": [5, 6, 7]},
        "epic": {"name": "🟡 Эпические", "levels": [8, 9, 10, 11, 12]},
        "legendary": {"name": "🟤 Легендарные", "levels": [13, 14, 15]},
        "mythic": {"name": "👑 Мифические", "levels": [16, 17, 18]}
    }

    user_id = callback.from_user.id
    user = await get_user(user_id)

    text = f"<b>{categories[category]['name']}</b>\n\n"
    kb = []

    for level in categories[category]["levels"]:
        drill = DRILL_LEVELS[level]

        if level > user['drill_level']:
            # Бур можно купить
            if drill.get('price_coins', 0) > 0:
                btn_text = f"{drill['name']} — {drill['price_coins']}💰"
                kb.append([InlineKeyboardButton(text=btn_text, callback_data=f"buy_drill_{level}")])
                text += f"• <b>{drill['name']}</b>\n"
                text += f"  ⚡️ +{drill['bonus']}%\n"
                text += f"  💰 {drill['price_coins']} монет\n\n"
            else:
                text += f"• <b>{drill['name']}</b>\n"
                text += f"  ⚡️ +{drill['bonus']}%\n"
                text += f"  🗺️ {drill.get('loc', 'особое место')}\n\n"
        elif level == user['drill_level']:
            # Текущий бур
            text += f"• <b>{drill['name']}</b> ✅ (твой)\n"
            text += f"  ⚡️ +{drill['bonus']}%\n\n"
        else:
            # Бур уже куплен (но не текущий)
            text += f"• <b>{drill['name']}</b> ✅\n"
            text += f"  ⚡️ +{drill['bonus']}%\n\n"

    if not kb and category not in ["epic", "legendary", "mythic"]:
        text += "😕 В этой категории пока нет доступных буров"

    kb.append([InlineKeyboardButton(text="◀️ Назад", callback_data="shop_drills")])

    await callback.message.edit_text(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=kb),
                                     parse_mode=ParseMode.HTML)
    await callback.answer()

@dp.callback_query(F.data.startswith("drills_cat_"))
async def show_drill_category(callback: types.CallbackQuery, state: FSMContext):
    """Показывает первый бур в категории"""
    category = callback.data.replace("drills_cat_", "")
    user_id = callback.from_user.id
    user = await get_user(user_id)

    categories = {
        "common": {"name": "🟢 Обычные", "levels": [1, 2]},
        "uncommon": {"name": "🔵 Необычные", "levels": [3, 4]},
        "rare": {"name": "🟣 Редкие", "levels": [5, 6, 7]},
        "epic": {"name": "🟡 Эпические", "levels": [8, 9, 10, 11, 12]},
        "legendary": {"name": "🟤 Легендарные", "levels": [13, 14, 15]},
        "mythic": {"name": "👑 Мифические", "levels": [16, 17, 18]}
    }

    await state.update_data(category=category, index=0)

    # Удаляем старое сообщение с категориями
    await callback.message.delete()
    # Показываем первый бур
    await show_drill_with_photo(callback.message, user, category, 0, state, is_edit=False)
    await callback.answer()


async def show_drill_with_photo(message: types.Message, user: dict, category: str, index: int, state: FSMContext,
                                is_edit=False):
    """Показывает конкретный бур с фото и кнопками"""
    categories = {
        "common": {"name": "🟢 Обычные", "levels": [1, 2]},
        "uncommon": {"name": "🔵 Необычные", "levels": [3, 4]},
        "rare": {"name": "🟣 Редкие", "levels": [5, 6, 7]},
        "epic": {"name": "🟡 Эпические", "levels": [8, 9, 10, 11, 12]},
        "legendary": {"name": "🟤 Легендарные", "levels": [13, 14, 15]},
        "mythic": {"name": "👑 Мифические", "levels": [16, 17, 18]}
    }

    level = categories[category]["levels"][index]
    drill = DRILL_LEVELS[level]

    # Формируем текст
    text = f"✨ <b>{drill['name']}</b>\n\n"
    text += f"🎁 <b>Редкость:</b> {drill['rarity']}\n"
    text += f"⚡️ <b>Бонус:</b> +{drill['bonus']}% к добыче\n"
    text += f"📝 <b>Описание:</b> {drill['desc']}\n\n"

    if level > user['drill_level']:
        if drill.get('price_coins', 0) > 0:
            text += f"💰 <b>Цена:</b> {drill['price_coins']} монет"
        elif drill.get('price_rub', 0) > 0:
            text += f"💎 <b>Цена:</b> {drill['price_rub']}₽"
        else:
            text += f"🗺️ <b>Можно найти в:</b> {drill.get('loc', 'особых местах')}"
    else:
        text += f"✅ <b>Уже куплен</b>"

    # Клавиатура с листалкой
    kb = []
    nav_buttons = []

    if index > 0:
        nav_buttons.append(InlineKeyboardButton(text="◀️", callback_data=f"drill_nav_{category}_{index - 1}"))
    else:
        nav_buttons.append(InlineKeyboardButton(text="◀️", callback_data="noop"))

    nav_buttons.append(
        InlineKeyboardButton(text=f"{index + 1}/{len(categories[category]['levels'])}", callback_data="noop"))

    if index < len(categories[category]["levels"]) - 1:
        nav_buttons.append(InlineKeyboardButton(text="▶️", callback_data=f"drill_nav_{category}_{index + 1}"))
    else:
        nav_buttons.append(InlineKeyboardButton(text="▶️", callback_data="noop"))

    kb.append(nav_buttons)

    # Кнопка покупки
    if level > user['drill_level'] and drill.get('price_coins', 0) > 0:
        kb.append([InlineKeyboardButton(text="💰 Купить", callback_data=f"buy_drill_{level}")])

    kb.append([InlineKeyboardButton(text="◀️ Назад к категориям", callback_data="shop_drills")])

    image_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "images", f"drill_{level}.jpg")

    if is_edit and os.path.exists(image_path):
        # Редактируем существующее сообщение с фото
        photo = FSInputFile(image_path)
        await message.edit_media(
            media=types.InputMediaPhoto(media=photo, caption=text, parse_mode=ParseMode.HTML),
            reply_markup=InlineKeyboardMarkup(inline_keyboard=kb)
        )
    elif os.path.exists(image_path):
        # Новое сообщение с фото
        photo = FSInputFile(image_path)
        await message.delete()
        await message.answer_photo(
            photo=photo,
            caption=text,
            reply_markup=InlineKeyboardMarkup(inline_keyboard=kb),
            parse_mode=ParseMode.HTML
        )
    else:
        # Если фото нет — просто текст
        if is_edit:
            await message.edit_text(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=kb),
                                    parse_mode=ParseMode.HTML)
        else:
            await message.answer(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=kb), parse_mode=ParseMode.HTML)


@dp.callback_query(F.data.startswith("drill_nav_"))
async def drill_navigation(callback: types.CallbackQuery, state: FSMContext):
    """Листалка буров с редактированием сообщения"""
    parts = callback.data.split("_")
    category = parts[2]
    index = int(parts[3])
    user_id = callback.from_user.id
    user = await get_user(user_id)

    # Редактируем текущее сообщение
    await show_drill_with_photo(callback.message, user, category, index, state, is_edit=True)
    await callback.answer()


@dp.callback_query(F.data.startswith("buy_drill_"))
async def buy_drill(callback: types.CallbackQuery):
    """Покупка бура с возвратом в категорию"""
    level = int(callback.data.split("_")[2])
    user_id = callback.from_user.id
    user = await get_user(user_id)
    drill = DRILL_LEVELS[level]

    if user['drill_level'] >= level:
        await callback.answer("❌ У тебя уже есть этот бур или лучше!", show_alert=True)
        return

    if drill.get('price_coins', 0) > 0:
        if user['balance'] < drill['price_coins']:
            await callback.answer(f"❌ Не хватает {drill['price_coins'] - user['balance']}💰", show_alert=True)
            return

        user['balance'] -= drill['price_coins']
        user['drill_level'] = level
        await update_user(user_id, balance=user['balance'], drill_level=level)

        # После покупки возвращаем в категорию
        text = f"✅ <b>Поздравляем с покупкой!</b>\n\n"
        text += f"🛠 <b>{drill['name']}</b> теперь твой!\n"
        text += f"💰 Остаток: {user['balance']} монет\n\n"
        text += f"⬅️ Нажми «Назад», чтобы продолжить покупки"

        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="◀️ Назад в категорию", callback_data=f"back_to_category_{drill['level']}")]
        ])

        await callback.message.edit_text(text, reply_markup=kb, parse_mode=ParseMode.HTML)
    else:
        await callback.answer("💎 Этот бур нельзя купить за монеты!", show_alert=True)

    await callback.answer()


@dp.callback_query(F.data.startswith("back_to_category_"))
async def back_to_category(callback: types.CallbackQuery, state: FSMContext):
    """Возврат в категорию после покупки"""
    level = int(callback.data.split("_")[3])
    user_id = callback.from_user.id
    user = await get_user(user_id)

    # Определяем категорию по уровню
    if level in [1, 2]:
        category = "common"
    elif level in [3, 4]:
        category = "uncommon"
    elif level in [5, 6, 7]:
        category = "rare"
    elif level in [8, 9, 10, 11, 12]:
        category = "epic"
    elif level in [13, 14, 15]:
        category = "legendary"
    else:
        category = "mythic"

    categories = {
        "common": {"name": "🟢 Обычные", "levels": [1, 2]},
        "uncommon": {"name": "🔵 Необычные", "levels": [3, 4]},
        "rare": {"name": "🟣 Редкие", "levels": [5, 6, 7]},
        "epic": {"name": "🟡 Эпические", "levels": [8, 9, 10, 11, 12]},
        "legendary": {"name": "🟤 Легендарные", "levels": [13, 14, 15]},
        "mythic": {"name": "👑 Мифические", "levels": [16, 17, 18]}
    }

    await state.update_data(category=category, index=0)
    await show_drill_with_photo(callback.message, user, category, 0, state, is_edit=True)
    await callback.answer()

@dp.callback_query(F.data == "shop_sell")
async def shop_sell_callback(callback: types.CallbackQuery):
    """Кнопка 'Продать руду' в магазине"""
    user_id = callback.from_user.id
    user = await get_user(user_id)
    inv = json.loads(user['inventory'])

    text = "💰 <b>ПРОДАЖА РУДЫ</b>\n\n"
    total = 0
    kb = []

    for r, data in RARITIES.items():
        count = inv.get(r, 0)
        if count > 0:
            price = (data['min'] + data['max']) // 2
            total_value = count * price
            text += f"{data['emoji']} {data['name']}: {count} шт. × {price} = {total_value}💰\n"
            total += total_value
            kb.append([InlineKeyboardButton(text=f"Продать {data['name']}", callback_data=f"sell_{r}")])

    if total == 0:
        text += "📦 У тебя нет руды для продажи"
    else:
        text += f"\n💰 <b>Всего можно получить: {total} монет</b>"
        kb.append([InlineKeyboardButton(text="💰 Продать всё", callback_data="sell_all")])

    kb.append([InlineKeyboardButton(text="◀️ Назад в магазин", callback_data="back_to_shop")])
    await callback.message.edit_text(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=kb),
                                     parse_mode=ParseMode.HTML)
    await callback.answer()


@dp.callback_query(F.data.startswith("sell_"))
async def process_sell(callback: types.CallbackQuery):
    """Обработка продажи руды"""
    user_id = callback.from_user.id
    user = await get_user(user_id)
    inv = json.loads(user['inventory'])

    if callback.data == "sell_all":
        total = 0
        for r in RARITIES:
            count = inv.get(r, 0)
            if count > 0:
                price = (RARITIES[r]['min'] + RARITIES[r]['max']) // 2
                total += count * price
                inv[r] = 0
        user['balance'] += total
        user['total_earned'] += total
        await update_user(user_id, balance=user['balance'], inventory=inv, total_earned=user['total_earned'])
        await callback.message.edit_text(f"✅ Продано всё! Получено: {total}💰")
    else:
        r = callback.data.split("_")[1]
        count = inv.get(r, 0)
        if count > 0:
            price = (RARITIES[r]['min'] + RARITIES[r]['max']) // 2
            total = count * price
            user['balance'] += total
            user['total_earned'] += total
            inv[r] = 0
            await update_user(user_id, balance=user['balance'], inventory=inv, total_earned=user['total_earned'])
            await callback.message.edit_text(f"✅ Продано {RARITIES[r]['name']}! Получено: {total}💰")

    await callback.answer()


@dp.callback_query(F.data == "back_to_shop")
async def back_to_shop(callback: types.CallbackQuery):
    """Возврат в главное меню магазина"""
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🛠 Купить бур", callback_data="shop_drills")],
        [InlineKeyboardButton(text="⛽ Купить топливо", callback_data="shop_fuel")],
        [InlineKeyboardButton(text="💰 Продать руду", callback_data="shop_sell")],
        [InlineKeyboardButton(text="◀️ Назад", callback_data="back_main")]
    ])
    await callback.message.edit_text("🏪 <b>МАГАЗИН</b>\n\nВыбери категорию:", reply_markup=kb,
                                     parse_mode=ParseMode.HTML)
    await callback.answer()

@dp.callback_query(F.data == "close")
async def close_message(callback: types.CallbackQuery):
    """Закрывает сообщение с топом"""
    await callback.message.delete()
    await callback.answer()

def is_happy_hours() -> bool:
    """Проверяет, активны ли сейчас счастливые часы"""
    now = datetime.now().time()
    start = datetime.strptime("12:00", "%H:%M").time()
    end = datetime.strptime("14:00", "%H:%M").time()
    return start <= now <= end

@dp.message(F.text == "🎁 Счастливые часы")
async def happy_hours_info(message: types.Message):
    """Информация о счастливых часах"""
    if is_happy_hours():
        time_left = datetime.combine(datetime.today(), datetime.strptime("14:00", "%H:%M").time()) - datetime.now()
        minutes_left = int(time_left.total_seconds() // 60)

        text = (
            "🎁 <b>СЧАСТЛИВЫЕ ЧАСЫ АКТИВНЫ!</b>\n\n"
            f"⏰ Осталось: <b>{minutes_left} минут</b>\n"
            f"⚡️ Множитель добычи: <b>x2</b>\n\n"
            f"⛏ Скорее добывай, пока время не вышло!"
        )
    else:
        text = (
            "🎁 <b>СЧАСТЛИВЫЕ ЧАСЫ</b>\n\n"
            f"⏰ Время проведения: <b>12:00 - 14:00</b>\n"
            f"⚡️ Множитель добычи: <b>x2</b>\n\n"
            f"Приходи в это время, чтобы получать вдвое больше ресурсов!"
        )

    await message.answer(text, parse_mode=ParseMode.HTML)

# ================= ВЕРНУТСЯ НАЗАД ====================
@dp.callback_query(F.data == "back_to_start")
async def back_to_start(callback: types.CallbackQuery):
    """Возврат в главное меню"""
    await callback.message.delete()
    await callback.message.answer("Главное меню", reply_markup=main_keyboard(callback.from_user.id))
    await callback.answer()

    # Пересоздаём приветственное сообщение
    user_id = callback.from_user.id
    first_name = callback.from_user.first_name
    username = callback.from_user.username
    user = await get_user(user_id, first_name, username)

    welcome_text = (
        f"👋 <b>Добро пожаловать в Miner Game, {first_name or 'шахтёр'}!</b>\n\n"
        f"⛏ <b>ЧТО ТУТ ДЕЛАТЬ:</b>\n"
        f"• Добывай ресурсы в разных локациях\n"
        f"• Продавай руду и улучшай бур\n"
        f"• Открывай новые локации\n"
        f"• Приглашай друзей и получай бонусы\n\n"

        f"📊 <b>ТВОИ ДАННЫЕ:</b>\n"
        f"💰 Баланс: {user['balance']} монет\n"
        f"⛽ Топливо: {user['fuel']}/{user['max_fuel']}\n"
        f"🛠 Бур: {DRILL_LEVELS[user['drill_level']]['name']}\n"
        f"🗺️ Локация: {LOCATIONS[user['current_location']]['name']}\n\n"

        f"🎁 <b>СОВЕТ:</b>\n"
        f"• Заходи каждый день за бонусом\n"
        f"• С 12:00 до 14:00 — удвоенная добыча!\n"
        f"• Введи промокод <b>STARTVIP</b> для подарка"
    )

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⛏ Начать добычу", callback_data="mine_now")],
        [InlineKeyboardButton(text="🎁 Ввести STARTVIP", callback_data="enter_startvip")],
        [InlineKeyboardButton(text="📋 Правила игры", callback_data="game_rules")]
    ])

    await send_photo(callback.message, welcome_text, "welcome.jpg", kb)
    await callback.answer()

# ================= ПЛАНИРОВЩИК ИНВЕНТА ==================
async def happy_hours_scheduler():
    """Планировщик счастливых часов"""
    while True:
        now = datetime.now()

        # Проверяем каждую минуту
        if now.hour == 11 and now.minute == 55:  # За 5 минут до начала
            await asyncio.sleep(5 * 60)  # Ждём до 12:00

            # Отправляем уведомление
            if hasattr(bot, 'notifier'):
                await bot.notifier.happy_hours_start()
                print("🎁 Уведомление о счастливых часах отправлено!")

        await asyncio.sleep(60)

# ===================== ЗАПУСК =====================
async def main():
    print("🚀 Бот запускается...")
    print(f"🌍 Часовой пояс: {MOSCOW_TZ}")
    await init_db()
    await bot.delete_webhook(drop_pending_updates=True)
    asyncio.create_task(scheduled_fuel())
    asyncio.create_task(happy_hours_scheduler())
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())