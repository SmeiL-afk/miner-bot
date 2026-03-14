import asyncio
import os
import random
import json
import aiosqlite
from datetime import datetime, timedelta
from aiogram import Bot, Dispatcher, types, F
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton, FSInputFile


# ===================== ФУНКЦИЯ ДЛЯ ФОТО =====================
async def send_drill_photo(message: types.Message, drill_level: int, text: str, keyboard=None):
    """Отправляет фото бура, если файл есть в папке images/"""
    image_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "images", f"drill_{drill_level}.jpg")
    if os.path.exists(image_path):
        photo = FSInputFile(image_path)
        await message.answer_photo(photo=photo, caption=text, reply_markup=keyboard, parse_mode=ParseMode.HTML)
    else:
        await message.answer(text, reply_markup=keyboard)


# ===================== КОНФИГ =====================
BOT_TOKEN = "8778377938:AAHgOQwI8mCtQmCDhJ5Dgl-liEFnL2zcdsI"
CREATOR_ID = 5002614559
ADMIN_USERNAMES = ["твой_юзернейм"]

bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
storage = MemoryStorage()
dp = Dispatcher(storage=storage)


# ===================== СОСТОЯНИЯ =====================
class MiningStates(StatesGroup):
    in_progress = State()


class DrillNavStates(StatesGroup):
    category = State()
    index = State()


# 👑 АДМИНСКИЕ СОСТОЯНИЯ
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
    1: {"name": "🛠 Дрель-новичка", "bonus": 0, "price": 0, "rarity": "🟢 Обычный", "desc": "С неё начинается путь"},
    2: {"name": "⚙️ Усиленный бур", "bonus": 5, "price": 1000, "rarity": "🟢 Обычный", "desc": "Металлический корпус"},
    3: {"name": "🏭 Промышленный бур", "bonus": 10, "price": 5000, "rarity": "🔵 Необычный",
        "desc": "Гидравлический привод"},
    4: {"name": "💎 Алмазный бур", "bonus": 15, "price": 20000, "rarity": "🔵 Необычный", "desc": "Алмазное напыление"},
    5: {"name": "🔬 Квантовый бур", "bonus": 25, "price": 50000, "rarity": "🟣 Редкий", "desc": "Субатомный уровень"},
    6: {"name": "☢️ Ядерный бур", "bonus": 35, "price": 100000, "rarity": "🟣 Редкий", "desc": "Микро-реактор"},
    7: {"name": "☀️ Солнечный бур", "bonus": 50, "price": 200000, "rarity": "🟣 Редкий", "desc": "Солнечный свет"},
    8: {"name": "🔥 Пустынный бур", "bonus": 60, "price": 0, "rarity": "🟡 Эпический", "desc": "Термостойкий",
        "loc": "Пустыня"},
    9: {"name": "❄️ Снежный бур", "bonus": 60, "price": 0, "rarity": "🟡 Эпический", "desc": "Криогенный",
        "loc": "Ледяные копи"},
    10: {"name": "🌿 Лесной бур", "bonus": 60, "price": 0, "rarity": "🟡 Эпический", "desc": "Опутан лианами",
         "loc": "Небесные копи"},
    11: {"name": "🌋 Вулканический бур", "bonus": 70, "price": 0, "rarity": "🟡 Эпический", "desc": "Работает в магме",
         "loc": "Вулкан"},
    12: {"name": "💧 Океанический бур", "bonus": 70, "price": 0, "rarity": "🟡 Эпический", "desc": "Гидроизоляция",
         "loc": "Космос"},
    13: {"name": "⚡ Грозовой бур", "bonus": 80, "price": 0, "rarity": "🟤 Легендарный", "desc": "Питается от молний"},
    14: {"name": "🌈 Кристальный бур", "bonus": 90, "price": 0, "rarity": "🟤 Легендарный",
         "desc": "Магический кристалл"},
    15: {"name": "🕯️ Теневой бур", "bonus": 90, "price": 0, "rarity": "🟤 Легендарный", "desc": "Поглощает свет"},
    16: {"name": "🌌 Космический бур", "bonus": 100, "price": 0, "rarity": "👑 Мифический", "desc": "Метеоритное железо"},
    17: {"name": "🌙 Лунный бур", "bonus": 100, "price": 0, "rarity": "👑 Мифический", "desc": "Лунный свет"},
    18: {"name": "⭐ Звёздный бур", "bonus": 100, "price": 0, "rarity": "👑 Мифический", "desc": "Шлейф из искр"}
}

# ===================== БАЗА ДАННЫХ =====================
DB_PATH = "miner_bot.db"


async def init_db():
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute('''
                         CREATE TABLE IF NOT EXISTS users
                         (
                             user_id
                             INTEGER
                             PRIMARY
                             KEY,
                             balance
                             INTEGER
                             DEFAULT
                             100,
                             fuel
                             INTEGER
                             DEFAULT
                             10,
                             max_fuel
                             INTEGER
                             DEFAULT
                             10,
                             last_fuel_reset
                             TEXT,
                             drill_level
                             INTEGER
                             DEFAULT
                             1,
                             vip_until
                             TEXT,
                             boost_until
                             TEXT,
                             boost_multiplier
                             REAL
                             DEFAULT
                             1.0,
                             inventory
                             TEXT
                             DEFAULT
                             '{}',
                             total_mined
                             INTEGER
                             DEFAULT
                             0,
                             register_date
                             TEXT,
                             referrer
                             INTEGER,
                             referral_count
                             INTEGER
                             DEFAULT
                             0,
                             referral_earnings
                             INTEGER
                             DEFAULT
                             0,
                             used_promos
                             TEXT
                             DEFAULT
                             '[]',
                             last_daily
                             TEXT,
                             daily_streak
                             INTEGER
                             DEFAULT
                             0,
                             daily_task
                             TEXT,
                             daily_progress
                             INTEGER
                             DEFAULT
                             0,
                             daily_completed
                             INTEGER
                             DEFAULT
                             0,
                             username
                             TEXT,
                             first_name
                             TEXT,
                             current_location
                             INTEGER
                             DEFAULT
                             1,
                             unlocked_locations
                             TEXT
                             DEFAULT
                             '[1]',
                             rarest_find
                             TEXT
                             DEFAULT
                             'common'
                         )
                         ''')
        await db.commit()


async def get_user(user_id, first_name=None, username=None):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute('SELECT * FROM users WHERE user_id = ?', (user_id,))
        user = await cursor.fetchone()
        if not user:
            register_date = datetime.now().strftime("%d.%m.%Y")
            await db.execute('''
                             INSERT INTO users (user_id, balance, fuel, max_fuel, last_fuel_reset, drill_level,
                                                vip_until, boost_until, boost_multiplier, inventory, total_mined,
                                                register_date, referrer, referral_count, referral_earnings,
                                                used_promos, last_daily, daily_streak, username, first_name,
                                                current_location, unlocked_locations)
                             VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                             ''', (user_id, 100, 10, 10, None, 1, None, None, 1.0,
                                   json.dumps({r: 0 for r in RARITIES.keys()}), 0,
                                   register_date, None, 0, 0, json.dumps([]), None, 0, username, first_name, 1,
                                   json.dumps([1])))
            await db.commit()
            cursor = await db.execute('SELECT * FROM users WHERE user_id = ?', (user_id,))
            user = await cursor.fetchone()
        return dict(user)


async def update_user(user_id, **kwargs):
    async with aiosqlite.connect(DB_PATH) as db:
        for key, value in kwargs.items():
            if isinstance(value, (dict, list)):
                value = json.dumps(value)
            await db.execute(f'UPDATE users SET {key} = ? WHERE user_id = ?', (value, user_id))
        await db.commit()


async def get_all_users():
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute('SELECT * FROM users')
        rows = await cursor.fetchall()
        return [dict(row) for row in rows]


# ===================== ФУНКЦИИ =====================
def get_fuel_emoji(fuel, max_fuel):
    percent = fuel / max_fuel if max_fuel > 0 else 0
    return "🟢" if percent >= 0.7 else "🟡" if percent >= 0.3 else "🔴"


def get_display_name(user_id, user_data):
    """Возвращает имя пользователя с особым стилем для создателя"""
    if user_id == CREATOR_ID:
        return "<b><i>👑 Создатель</i></b>"
    if user_data.get('first_name'):
        name = user_data['first_name'][:15]
        return f"👤 {name}"
    if user_data.get('username'):
        return f"👤 @{user_data['username']}"
    return f"👤 Игрок {user_id}"


def mine_resources(user):
    loc = LOCATIONS[user['current_location']]
    chances = loc['chances']
    drill = DRILL_LEVELS[user['drill_level']]
    multiplier = 1 + drill['bonus'] / 100
    if user.get('vip_until') and datetime.now() < datetime.fromisoformat(user['vip_until']):
        multiplier *= 2
    if user.get('boost_until') and datetime.now() < datetime.fromisoformat(user['boost_until']):
        multiplier *= user['boost_multiplier']
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


async def check_fuel_reset(user):
    """Проверяет, не наступил ли новый день, и обновляет топливо если надо"""
    try:
        today = datetime.now().date()
        last_reset = None
        if user.get('last_fuel_reset'):
            last_reset = datetime.fromisoformat(user['last_fuel_reset']).date()
        if last_reset != today:
            vip_active = False
            if user.get('vip_until'):
                try:
                    if datetime.now() < datetime.fromisoformat(user['vip_until']):
                        vip_active = True
                except:
                    pass
            if user['drill_level'] >= 16:
                new_max = 20
            elif vip_active:
                new_max = 15
            else:
                new_max = 10
            user['fuel'] = new_max
            user['max_fuel'] = new_max
            user['last_fuel_reset'] = datetime.now().isoformat()
    except Exception as e:
        print(f"❌ Ошибка в check_fuel_reset: {e}")
    return user


# ===================== КЛАВИАТУРЫ =====================
def main_keyboard(user_id=None):
    kb = [
        [KeyboardButton(text="⛏ Добывать"), KeyboardButton(text="📦 Инвентарь")],
        [KeyboardButton(text="🛠 Буры"), KeyboardButton(text="🗺️ Локации")],
        [KeyboardButton(text="🏪 Магазин"), KeyboardButton(text="📊 Топ")],
        [KeyboardButton(text="👤 Профиль"), KeyboardButton(text="👥 Рефералы")],
        [KeyboardButton(text="💎 Донат"), KeyboardButton(text="🎁 Бонус")],
        [KeyboardButton(text="❓ Помощь")]
    ]

    # Добавляем админку только для создателя
    if user_id == CREATOR_ID:
        kb.append([KeyboardButton(text="👑 Админка")])

    return ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True)


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


# ===================== СТАРТ =====================
@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    user_id = message.from_user.id
    first_name = message.from_user.first_name
    username = message.from_user.username
    user = await get_user(user_id, first_name, username)
    await message.answer(
        f"👋 Добро пожаловать!\n💰 {user['balance']} монет\n⛽ {user['fuel']}/10",
        reply_markup=main_keyboard(user_id))


# ===================== ДОБЫЧА =====================
@dp.message(F.text == "⛏ Добывать", StateFilter(None))
async def mine_command(message: types.Message, state: FSMContext):
    await state.set_state(MiningStates.in_progress)
    try:
        user_id = message.from_user.id
        user = await get_user(user_id)
        user = await check_fuel_reset(user)
        await update_user(user_id, fuel=user['fuel'], max_fuel=user['max_fuel'],
                          last_fuel_reset=user['last_fuel_reset'])

        if user['fuel'] <= 0:
            await message.answer("⛽ Нет топлива!", reply_markup=main_keyboard(user_id))
            await state.clear()
            return

        user['fuel'] -= 1
        mined = mine_resources(user)
        await update_user(user_id, fuel=user['fuel'], inventory=user['inventory'], total_mined=user['total_mined'])

        result = {}
        for r, a in mined:
            result[r] = result.get(r, 0) + a

        fuel_emoji = get_fuel_emoji(user['fuel'], user['max_fuel'])
        loc_name = LOCATIONS[user['current_location']]['name']

        text = f"⛏ Добыча в {loc_name}\n\n"
        for r, a in result.items():
            text += f"{RARITIES[r]['emoji']} {RARITIES[r]['name']}: +{a}\n"
        text += f"\n⛽ Осталось: {fuel_emoji} {user['fuel']}/{user['max_fuel']}"

        await message.answer(text, reply_markup=main_keyboard(user_id))
    except Exception as e:
        print(f"❌ Ошибка добычи: {e}")
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
    text = f"🛠 <b>ТВОЙ БУР</b>\n\n<b>{drill['name']}</b>\n⚡️ Бонус: +{drill['bonus']}%\n"
    if user['drill_level'] < len(DRILL_LEVELS):
        next_drill = DRILL_LEVELS[user['drill_level'] + 1]
        text += f"\n➡️ Следующий: {next_drill['name']}\n💰 Цена: {next_drill.get('price', 0)} монет"
    await send_drill_photo(message, user['drill_level'], text, main_keyboard(user_id))


# ===================== ЛОКАЦИИ =====================
@dp.message(F.text == "🗺️ Локации")
async def locations_menu(message: types.Message):
    user_id = message.from_user.id
    user = await get_user(user_id)
    await message.answer("🗺️ Локации", reply_markup=get_locations_keyboard(user))


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
        await callback.message.answer(f"🗺️ Ты в {LOCATIONS[loc_id]['name']}", reply_markup=main_keyboard(user_id))
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
    await callback.message.answer(f"🗺️ Открыта: {loc['name']}!", reply_markup=main_keyboard(user_id))


# ===================== МАГАЗИН =====================
@dp.message(F.text == "🏪 Магазин")
async def shop_menu(message: types.Message):
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🛠 Купить бур", callback_data="shop_drills")],
        [InlineKeyboardButton(text="💰 Продать руду", callback_data="shop_sell")],
        [InlineKeyboardButton(text="◀️ Назад", callback_data="back_main")]
    ])
    await message.answer("🏪 <b>МАГАЗИН</b>\n\nВыбери категорию:", reply_markup=kb, parse_mode=ParseMode.HTML)

# ===================== ДОНАТ =========================
@dp.message(F.text == "💎 Донат")
async def donate_menu(message: types.Message):
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="👑 VIP СТАТУСЫ", callback_data="donate_vip_menu")],
        [InlineKeyboardButton(text="⚡️ БУСТЫ", callback_data="donate_boost_menu")],
        [InlineKeyboardButton(text="🛠 ЛЕГЕНДАРНЫЕ БУРЫ", callback_data="donate_drills_menu")],
        [InlineKeyboardButton(text="❓ Помощь по донату", callback_data="donate_help")]
    ])

    text = (
        "💎 <b>ПОДДЕРЖКА ПРОЕКТА</b>\n\n"
        "Выбери категорию доната:\n\n"
        "👑 <b>VIP статусы</b> — больше топлива и бонусов\n"
        "⚡️ <b>Бусты</b> — временное ускорение добычи\n"
        "🛠 <b>Легендарные буры</b> — мощные инструменты"
    )

    await message.answer(text, reply_markup=kb, parse_mode=ParseMode.HTML)


@dp.callback_query(F.data == "donate_vip_menu")
async def donate_vip_menu(callback: types.CallbackQuery):
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="👑 VIP на месяц — 299₽", callback_data="buy_vip_month")],
        [InlineKeyboardButton(text="👑 VIP на 3 месяца — 699₽", callback_data="buy_vip_3months")],
        [InlineKeyboardButton(text="👑 VIP на полгода — 1199₽", callback_data="buy_vip_6months")],
        [InlineKeyboardButton(text="👑 VIP на год — 1499₽", callback_data="buy_vip_year")],
        [InlineKeyboardButton(text="◀️ Назад", callback_data="back_to_donate")]
    ])

    text = (
        "👑 <b>VIP СТАТУСЫ</b>\n\n"
        "✨ <b>Преимущества VIP:</b>\n"
        "• ⛽ +5 топлива каждый день (15 вместо 10)\n"
        "• 💰 Удвоенный доход от добычи\n"
        "• 🔓 Доступ к VIP-локациям\n"
        "• 🎁 Еженедельные бонусы\n\n"
        "👇 Выбери срок:"
    )

    await callback.message.edit_text(text, reply_markup=kb, parse_mode=ParseMode.HTML)
    await callback.answer()


@dp.callback_query(F.data == "donate_boost_menu")
async def donate_boost_menu(callback: types.CallbackQuery):
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⚡️ x2 на 2 часа — 49₽", callback_data="buy_boost_2h")],
        [InlineKeyboardButton(text="⚡️⚡️ x2 на 12 часов — 199₽", callback_data="buy_boost_12h")],
        [InlineKeyboardButton(text="⚡️⚡️⚡️ x2 на 24 часа — 299₽", callback_data="buy_boost_24h")],
        [InlineKeyboardButton(text="🔥 x3 на 1 час — 499₽", callback_data="buy_boost_x3")],
        [InlineKeyboardButton(text="◀️ Назад", callback_data="back_to_donate")]
    ])

    text = (
        "⚡️ <b>БУСТЫ</b>\n\n"
        "✨ <b>Как работают:</b>\n"
        "• Временно увеличивают добычу\n"
        "• Складываются с VIP-бонусом\n"
        "• Активны 24/7 после покупки\n\n"
        "👇 Выбери буст:"
    )

    await callback.message.edit_text(text, reply_markup=kb, parse_mode=ParseMode.HTML)
    await callback.answer()


@dp.callback_query(F.data == "donate_drills_menu")
async def donate_drills_menu(callback: types.CallbackQuery):
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⚡ Грозовой бур — 1000₽", callback_data="buy_drill_13")],
        [InlineKeyboardButton(text="🌈 Кристальный бур — 1500₽", callback_data="buy_drill_14")],
        [InlineKeyboardButton(text="🕯️ Теневой бур — 1500₽", callback_data="buy_drill_15")],
        [InlineKeyboardButton(text="◀️ Назад", callback_data="back_to_donate")]
    ])

    text = (
        "🛠 <b>ЛЕГЕНДАРНЫЕ БУРЫ</b>\n\n"
        "⚡ <b>Грозовой бур</b> — +80% к добыче\n"
        "🌈 <b>Кристальный бур</b> — +90% к добыче\n"
        "🕯️ <b>Теневой бур</b> — +90% к добыче\n\n"
        "💎 Покупаются <b>навсегда</b> и не теряются!\n\n"
        "👇 Выбери бур:"
    )

    await callback.message.edit_text(text, reply_markup=kb, parse_mode=ParseMode.HTML)
    await callback.answer()


@dp.callback_query(F.data == "donate_help")
async def donate_help(callback: types.CallbackQuery):
    text = (
        "❓ <b>ПОМОЩЬ ПО ДОНАТУ</b>\n\n"
        "💳 <b>Как оплатить?</b>\n"
        "• После нажатия на кнопку откроется окно оплаты\n"
        "• Поддерживаются карты РФ, ЮMoney, SberPay\n\n"
        "🎁 <b>Что происходит после оплаты?</b>\n"
        "• Бонус начисляется автоматически\n"
        "• Вы получите уведомление в боте\n\n"
        "🆘 <b>Проблемы с оплатой?</b>\n"
        "• Напиши в поддержку @admin\n"
        "• Приложи скриншот оплаты"
    )

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="◀️ Назад", callback_data="back_to_donate")]
    ])

    await callback.message.edit_text(text, reply_markup=kb, parse_mode=ParseMode.HTML)
    await callback.answer()

@dp.callback_query(F.data == "back_to_donate")
async def back_to_donate(callback: types.CallbackQuery):
    await donate_menu(callback.message)
    await callback.answer()

# ===================== МАГАЗИН БУРОВ =====================
@dp.callback_query(F.data == "shop_drills")
async def shop_drills_menu(callback: types.CallbackQuery):
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🟢 Обычные", callback_data="drills_cat_common")],
        [InlineKeyboardButton(text="🔵 Необычные", callback_data="drills_cat_uncommon")],
        [InlineKeyboardButton(text="🟣 Редкие", callback_data="drills_cat_rare")],
        [InlineKeyboardButton(text="🟡 Эпические", callback_data="drills_cat_epic")],
        [InlineKeyboardButton(text="🟤 Легендарные", callback_data="drills_cat_legendary")],
        [InlineKeyboardButton(text="👑 Мифические", callback_data="drills_cat_mythic")],
        [InlineKeyboardButton(text="◀️ Назад в магазин", callback_data="back_to_shop")]
    ])

    # Пытаемся отредактировать, если не получается — удаляем и создаём новое
    try:
        await callback.message.edit_text(
            "🛠 <b>МАГАЗИН БУРОВ</b>\n\nВыбери категорию:",
            reply_markup=kb,
            parse_mode=ParseMode.HTML
        )
    except Exception as e:
        # Если не получилось отредактировать (нет текста), удаляем и отправляем новое
        await callback.message.delete()
        await callback.message.answer(
            "🛠 <b>МАГАЗИН БУРОВ</b>\n\nВыбери категорию:",
            reply_markup=kb,
            parse_mode=ParseMode.HTML
        )
    await callback.answer()


# ===================== КАТЕГОРИИ БУРОВ =====================
@dp.callback_query(F.data.startswith("drills_cat_"))
async def show_drill_category(callback: types.CallbackQuery, state: FSMContext):
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

    # Удаляем сообщение с меню категорий
    await callback.message.delete()
    # Показываем первый бур
    await show_drill(callback.message, user, category, 0, state)
    await callback.answer()


async def show_drill(message: types.Message, user: dict, category: str, index: int, state: FSMContext):
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

    # Формируем красивый текст
    text = f"✨ <b>{drill['name']}</b>\n\n"
    text += f"🎁 <b>Редкость:</b> {drill['rarity']}\n"
    text += f"⚡️ <b>Бонус:</b> +{drill['bonus']}% к добыче\n"
    text += f"📝 <b>Описание:</b> {drill['desc']}\n\n"

    if level > user['drill_level']:
        if drill.get('price', 0) > 0:
            text += f"💰 <b>Цена:</b> {drill['price']} монет"
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

    if level > user['drill_level'] and drill.get('price', 0) > 0:
        kb.append([InlineKeyboardButton(text="💰 Купить", callback_data=f"buy_drill_{level}")])

    kb.append([InlineKeyboardButton(text="◀️ Назад к категориям", callback_data="shop_drills")])

    # Отправляем фото, если есть
    image_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "images", f"drill_{level}.jpg")
    if os.path.exists(image_path):
        photo = FSInputFile(image_path)
        await message.answer_photo(
            photo=photo,
            caption=text,
            reply_markup=InlineKeyboardMarkup(inline_keyboard=kb),
            parse_mode=ParseMode.HTML
        )
    else:
        await message.edit_text(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=kb), parse_mode=ParseMode.HTML)


# ===================== НАВИГАЦИЯ ПО БУРАМ =====================
@dp.callback_query(F.data.startswith("drill_nav_"))
async def drill_navigation(callback: types.CallbackQuery, state: FSMContext):
    parts = callback.data.split("_")
    category = parts[2]
    index = int(parts[3])
    user_id = callback.from_user.id
    user = await get_user(user_id)
    await show_drill(callback.message, user, category, index, state)
    await callback.answer()


# ===================== ПОКУПКА БУРА =====================
@dp.callback_query(F.data.startswith("buy_drill_"))
async def buy_drill(callback: types.CallbackQuery):
    level = int(callback.data.split("_")[2])
    user_id = callback.from_user.id
    user = await get_user(user_id)
    drill = DRILL_LEVELS[level]

    if user['balance'] < drill['price']:
        await callback.answer(f"❌ Не хватает {drill['price'] - user['balance']}💰", show_alert=True)
        return

    user['balance'] -= drill['price']
    user['drill_level'] = level
    await update_user(user_id, balance=user['balance'], drill_level=level)

    text = (f"✅ <b>Поздравляем с покупкой!</b>\n\n"
            f"<b>{drill['name']}</b>\n"
            f"Редкость: {drill['rarity']}\n"
            f"⚡️ Бонус: +{drill['bonus']}%\n"
            f"📝 {drill['desc']}\n\n"
            f"💰 Остаток: {user['balance']} монет")

    await callback.message.delete()
    await send_drill_photo(callback.message, level, text, main_keyboard(user_id))
    await callback.answer()
    await callback.message.delete()
    await show_drill(callback.message, user, category, index, state)
    await callback.answer()


# ===================== БУСТЫ =====================
@dp.callback_query(F.data == "shop_boosts")
async def shop_boosts(callback: types.CallbackQuery):
    text = "⚡️ <b>БУСТЫ</b>\n\n"
    text += "• x2 на 2 часа — 49₽\n"
    text += "• x2 на 12 часов — 199₽\n"
    text += "• x2 на 24 часа — 299₽\n"
    text += "• x3 на 1 час — 499₽\n\n"
    text += "💎 Скоро появится возможность покупки"
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="◀️ Назад", callback_data="back_to_shop")]
    ])
    await callback.message.edit_text(text, reply_markup=kb, parse_mode=ParseMode.HTML)
    await callback.answer()


# ===================== VIP =====================
@dp.callback_query(F.data == "shop_vip")
async def shop_vip(callback: types.CallbackQuery):
    text = "👑 <b>VIP СТАТУСЫ</b>\n\n"
    text += "• VIP на месяц — 299₽\n"
    text += "• VIP на 3 месяца — 699₽\n"
    text += "• VIP на полгода — 1199₽\n"
    text += "• VIP на год — 1499₽\n\n"
    text += "💎 Скоро появится возможность покупки"
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="◀️ Назад", callback_data="back_to_shop")]
    ])
    await callback.message.edit_text(text, reply_markup=kb, parse_mode=ParseMode.HTML)
    await callback.answer()


# ===================== ПРОДАЖА =====================
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


@dp.callback_query(F.data == "back_to_shop")
async def back_to_shop(callback: types.CallbackQuery):
    await shop_menu(callback.message)
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
        await update_user(user_id, balance=user['balance'], inventory=inv)
        await callback.message.edit_text(f"✅ Продано всё! Получено: {total}💰")
    else:
        r = callback.data.split("_")[1]
        count = inv.get(r, 0)
        if count > 0:
            price = (RARITIES[r]['min'] + RARITIES[r]['max']) // 2
            total = count * price
            user['balance'] += total
            inv[r] = 0
            await update_user(user_id, balance=user['balance'], inventory=inv)
            await callback.message.edit_text(f"✅ Продано {RARITIES[r]['name']}! Получено: {total}💰")
    await callback.answer()


# ===================== ТОП =====================
@dp.message(F.text == "📊 Топ")
async def top_menu(message: types.Message):
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💰 По монетам", callback_data="top_balance")],
        [InlineKeyboardButton(text="👥 По рефералам", callback_data="top_referrals")],
        [InlineKeyboardButton(text="🗺️ По локациям", callback_data="top_locations")],
        [InlineKeyboardButton(text="❌ Закрыть", callback_data="close")]
    ])
    await message.answer("📊 <b>ВЫБЕРИ КАТЕГОРИЮ ТОПА</b>", reply_markup=kb, parse_mode=ParseMode.HTML)


@dp.callback_query(F.data.startswith("top_"))
async def top_categories(callback: types.CallbackQuery):
    users = await get_all_users()
    if callback.data == "top_balance":
        sorted_users = sorted(users, key=lambda x: x['balance'], reverse=True)[:10]
        title = "💰 ТОП ПО МОНЕТАМ"
    elif callback.data == "top_referrals":
        sorted_users = sorted(users, key=lambda x: x['referral_count'], reverse=True)[:10]
        title = "👥 ТОП ПО РЕФЕРАЛАМ"
    elif callback.data == "top_locations":
        sorted_users = sorted(users, key=lambda x: x['current_location'], reverse=True)[:10]
        title = "🗺️ ТОП ПО ЛОКАЦИЯМ"
    else:
        await callback.message.delete()
        return

    text = f"<b>{title}</b>\n\n"
    medals = ["🥇", "🥈", "🥉"]
    for i, u in enumerate(sorted_users, 1):
        medal = medals[i - 1] if i <= 3 else f"{i}."
        name = get_display_name(u['user_id'], u)
        if callback.data == "top_balance":
            value = f"{u['balance']}💰"
        elif callback.data == "top_referrals":
            value = f"{u['referral_count']}👥"
        else:
            value = f"{LOCATIONS[u['current_location']]['name']}"
        text += f"{medal} {name} — {value}\n"

    await callback.message.edit_text(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="◀️ Назад", callback_data="back_to_top")],
        [InlineKeyboardButton(text="❌ Закрыть", callback_data="close")]
    ]), parse_mode=ParseMode.HTML)
    await callback.answer()


@dp.callback_query(F.data == "back_to_top")
async def back_to_top(callback: types.CallbackQuery):
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💰 По монетам", callback_data="top_balance")],
        [InlineKeyboardButton(text="👥 По рефералам", callback_data="top_referrals")],
        [InlineKeyboardButton(text="🗺️ По локациям", callback_data="top_locations")],
        [InlineKeyboardButton(text="❌ Закрыть", callback_data="close")]
    ])
    await callback.message.edit_text("📊 <b>ВЫБЕРИ КАТЕГОРИЮ ТОПА</b>", reply_markup=kb, parse_mode=ParseMode.HTML)
    await callback.answer()


# ===================== ПРОФИЛЬ =====================
@dp.message(F.text == "👤 Профиль")
async def profile(message: types.Message):
    user_id = message.from_user.id
    user = await get_user(user_id)
    user = await check_fuel_reset(user)
    name = get_display_name(user_id, user)
    vip = "Нет"
    if user['vip_until'] and datetime.now() < datetime.fromisoformat(user['vip_until']):
        vip = f"✅ до {datetime.fromisoformat(user['vip_until']).strftime('%d.%m.%Y')}"
    boost = "Нет"
    if user['boost_until'] and datetime.now() < datetime.fromisoformat(user['boost_until']):
        boost = f"⚡️ x{user['boost_multiplier']}"
    used = json.loads(user['used_promos'])
    text = (f"👤 ПРОФИЛЬ\n\n{name}\n🆔 {user_id}\n📅 {user['register_date']}\n\n"
            f"💰 {user['balance']} монет\n⛽ {get_fuel_emoji(user['fuel'], user['max_fuel'])} {user['fuel']}/{user['max_fuel']}\n"
            f"🛠 {DRILL_LEVELS[user['drill_level']]['name']}\n🗺️ {LOCATIONS[user['current_location']]['name']}\n\n"
            f"👑 VIP: {vip}\n⚡️ Буст: {boost}\n⛏ Добыто: {user['total_mined']}\n"
            f"👥 Рефералов: {user['referral_count']}\n🎁 Промокодов: {len(used)}")
    await update_user(user_id, fuel=user['fuel'], max_fuel=user['max_fuel'])
    await message.answer(text, reply_markup=main_keyboard(user_id))


# ===================== РЕФЕРАЛЫ =====================
@dp.message(F.text == "👥 Рефералы")
async def referrals(message: types.Message):
    user_id = message.from_user.id
    user = await get_user(user_id)
    bot_username = (await bot.me()).username
    link = f"https://t.me/{bot_username}?start={user_id}"

    # Красивый текст с эмодзи
    text = (
        f"👥 <b>РЕФЕРАЛЬНАЯ СИСТЕМА</b>\n\n"
        f"🔗 <b>Твоя ссылка:</b>\n"
        f"<code>{link}</code>\n\n"
        f"📊 <b>Статистика:</b>\n"
        f"  👤 Приглашено: <b>{user['referral_count']}</b> чел.\n"
        f"  💰 Заработано: <b>{user['referral_earnings']}</b> монет\n\n"
        f"🎁 <b>Бонусы за приглашение:</b>\n"
        f"  • За каждого друга: <b>+200 монет</b>\n"
        f"  • Другу: <b>+100 монет</b> при регистрации\n"
        f"  • 15% от донатов рефералов\n\n"
        f"📢 <i>Чем больше друзей — тем больше бонусов!</i>"
    )

    # Красивая клавиатура с кнопками
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📋 Копировать ссылку", callback_data=f"copy_ref")],
        [InlineKeyboardButton(text="📤 Поделиться",
                              url=f"https://t.me/share/url?url={link}&text=🔥 Играй со мной в Miner Bot! Зарабатывай монеты и открывай локации!")],
        [InlineKeyboardButton(text="🏆 Топ рефералов", callback_data="top_referrals")],
        [InlineKeyboardButton(text="◀️ Назад", callback_data="back_main")]
    ])

    await message.answer(text, reply_markup=kb, parse_mode=ParseMode.HTML)
# ========================= Копировать ссылку ======================
@dp.callback_query(F.data == "copy_ref")
async def copy_referral_link(callback: types.CallbackQuery):
    await callback.answer("🔗 Ссылка скопирована в буфер!", show_alert=True)

# ===================== БОНУС =====================
@dp.message(F.text == "🎁 Бонус")
async def daily_bonus(message: types.Message):
    user_id = message.from_user.id
    user = await get_user(user_id)
    today = datetime.now().date()
    if user['last_daily']:
        last = datetime.fromisoformat(user['last_daily']).date()
        if last == today:
            await message.answer("⏳ Уже получал сегодня")
            return
    bonus = 50
    user['balance'] += bonus
    user['daily_streak'] += 1
    user['last_daily'] = datetime.now().isoformat()
    await update_user(user_id, balance=user['balance'], daily_streak=user['daily_streak'],
                      last_daily=user['last_daily'])
    text = f"🎁 Бонус: +{bonus}💰\n📆 Серия: {user['daily_streak']} дней"
    await message.answer(text, reply_markup=main_keyboard(user_id))


# ===================== ЗАДАНИЯ =====================
@dp.message(F.text == "📋 Задания")
async def daily_tasks_menu(message: types.Message):
    user_id = message.from_user.id
    user = await get_user(user_id)
    await message.answer("📋 Ежедневные задания (скоро)", reply_markup=main_keyboard(user_id))


# ===================== ПОМОЩЬ =====================
@dp.message(F.text == "❓ Помощь")
async def help_cmd(message: types.Message):
    text = ("❓ ПОМОЩЬ\n\n⛏ Добывай ресурсы\n📦 Инвентарь для хранения\n🛠 Улучшай бур\n"
            "🗺️ Открывай локации\n👥 Приглашай друзей\n🎁 Забирай бонус")
    await message.answer(text, reply_markup=main_keyboard(message.from_user.id))


# ===================== АДМИНКА =====================
@dp.message(F.text == "👑 Админка")
async def admin_panel(message: types.Message):
    if message.from_user.id != CREATOR_ID:
        return

    kb = ReplyKeyboardMarkup(keyboard=[
        [KeyboardButton(text="📊 Статистика"), KeyboardButton(text="👥 Игроки")],
        [KeyboardButton(text="💰 Выдать монеты"), KeyboardButton(text="🎫 Промокоды")],
        [KeyboardButton(text="📢 Рассылка"), KeyboardButton(text="💎 Валюта")],
        [KeyboardButton(text="🔧 Техработы"), KeyboardButton(text="◀️ Выйти")]
    ], resize_keyboard=True)

    await message.answer("👑 <b>АДМИН-ПАНЕЛЬ</b>\n\nВыбери действие:", reply_markup=kb, parse_mode=ParseMode.HTML)


@dp.message(F.text == "📊 Статистика")
async def admin_stats(message: types.Message):
    if message.from_user.id != CREATOR_ID:
        return

    users = await get_all_users()
    total_balance = sum(u['balance'] for u in users)
    total_mined = sum(u['total_mined'] for u in users)
    vip_count = sum(1 for u in users if u.get('vip_until') and datetime.now() < datetime.fromisoformat(u['vip_until']))

    text = (
        f"📊 <b>СТАТИСТИКА</b>\n\n"
        f"👥 Всего игроков: <b>{len(users)}</b>\n"
        f"💰 Общий баланс: <b>{total_balance}</b> монет\n"
        f"⛏ Всего добыто: <b>{total_mined}</b> ед.\n"
        f"👑 VIP игроков: <b>{vip_count}</b>\n"
        f"📅 Активных сегодня: <b>...</b> (будет позже)"
    )

    await message.answer(text, parse_mode=ParseMode.HTML)


@dp.message(F.text == "👥 Игроки")
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


@dp.message(F.text == "🎫 Промокоды")
async def admin_promo_menu(message: types.Message):
    if message.from_user.id != CREATOR_ID:
        return

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="➕ Создать промокод", callback_data="admin_create_promo")],
        [InlineKeyboardButton(text="📋 Список промокодов", callback_data="admin_list_promos")],
        [InlineKeyboardButton(text="❌ Удалить промокод", callback_data="admin_delete_promo")]
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
    ])

    await message.answer("Выбери тип награды:", reply_markup=kb)
    await state.set_state(AdminStates.waiting_for_promo_type)


@dp.callback_query(AdminStates.waiting_for_promo_type, F.data.startswith("promo_type_"))
async def admin_process_type(callback: types.CallbackQuery, state: FSMContext):
    ptype = callback.data.replace("promo_type_", "")
    await state.update_data(promo_type=ptype)
    await callback.message.edit_text("Введи значение награды:")
    await callback.answer()
    await state.set_state(AdminStates.waiting_for_promo_value)


@dp.message(AdminStates.waiting_for_promo_value)
async def admin_process_value(message: types.Message, state: FSMContext):
    try:
        val = int(message.text)
        await state.update_data(promo_value=val)
        await message.answer("Введи количество использований:")
        await state.set_state(AdminStates.waiting_for_promo_uses)
    except:
        await message.answer("❌ Введи число")


@dp.message(AdminStates.waiting_for_promo_uses)
async def admin_process_uses(message: types.Message, state: FSMContext):
    try:
        uses = int(message.text)
        data = await state.get_data()

        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute('''
                INSERT OR REPLACE INTO promo_codes (code, type, value, uses, used_by)
                VALUES (?, ?, ?, ?, ?)
            ''', (data['promo_code'], data['promo_type'], json.dumps(data['promo_value']), uses, json.dumps([])))
            await db.commit()

        await message.answer(f"✅ Промокод {data['promo_code']} создан!")
        await state.clear()
    except:
        await message.answer("❌ Ошибка")
        await state.clear()


@dp.callback_query(F.data == "admin_list_promos")
async def admin_list_promos(callback: types.CallbackQuery):
    promos = await get_promo_codes_db()

    if not promos:
        await callback.message.edit_text("📭 Нет активных промокодов")
        await callback.answer()
        return

    text = "📋 <b>АКТИВНЫЕ ПРОМОКОДЫ</b>\n\n"
    for code, data in promos.items():
        used = len(data['used_by'])
        text += f"• <b>{code}</b> — {data['type']} = {data['value']}\n"
        text += f"  Использовано: {used}/{data['uses']}\n\n"

    await callback.message.edit_text(text, parse_mode=ParseMode.HTML)
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


@dp.message(F.text == "📢 Рассылка")
async def admin_broadcast(message: types.Message, state: FSMContext):
    if message.from_user.id != CREATOR_ID:
        return
    await message.answer("Введи текст для рассылки всем игрокам:")
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
        [InlineKeyboardButton(text="➖ Забрать у всех", callback_data="currency_remove_all")],
        [InlineKeyboardButton(text="📊 Топ балансов", callback_data="top_balance")]
    ])

    await message.answer("💎 <b>УПРАВЛЕНИЕ ВАЛЮТОЙ</b>", reply_markup=kb, parse_mode=ParseMode.HTML)


@dp.message(F.text == "🔧 Техработы")
async def admin_maintenance(message: types.Message, state: FSMContext):
    if message.from_user.id != CREATOR_ID:
        return
    await message.answer("Введи текст предупреждения о техработax:")
    await state.set_state(AdminStates.waiting_for_maintenance)


@dp.message(AdminStates.waiting_for_maintenance)
async def admin_process_maintenance(message: types.Message, state: FSMContext):
    text = message.text
    users = await get_all_users()
    sent = 0

    warn_text = f"🔧 <b>ТЕХНИЧЕСКИЕ РАБОТЫ</b>\n\n{text}\n\n⏳ Бот может временно не работать."

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

# ===================== НАЗАД =====================
@dp.callback_query(F.data == "back_main")
async def back_main(callback: types.CallbackQuery):
    await callback.message.delete()
    await callback.message.answer("Главное меню", reply_markup=main_keyboard(callback.from_user.id))
    await callback.answer()


@dp.callback_query(F.data == "close")
async def close_message(callback: types.CallbackQuery):
    await callback.message.delete()
    await callback.answer()


@dp.callback_query(F.data == "noop")
async def noop(callback: types.CallbackQuery):
    await callback.answer()


# ===================== ЗАПУСК =====================
async def scheduled_fuel():
    while True:
        now = datetime.now()
        next_day = datetime(now.year, now.month, now.day, 0, 0, 0) + timedelta(days=1)
        await asyncio.sleep((next_day - now).total_seconds())
        users = await get_all_users()
        for u in users:
            try:
                vip = u.get('vip_until') and datetime.now() < datetime.fromisoformat(u['vip_until'])
                max_fuel = 20 if u['drill_level'] >= 16 else 15 if vip else 10
                await update_user(u['user_id'], fuel=max_fuel, max_fuel=max_fuel,
                                  last_fuel_reset=datetime.now().isoformat())
            except:
                pass
        print("🔄 Топливо обновлено")


async def main():
    print("🚀 Бот запускается...")
    await init_db()
    await bot.delete_webhook(drop_pending_updates=True)
    asyncio.create_task(scheduled_fuel())
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())