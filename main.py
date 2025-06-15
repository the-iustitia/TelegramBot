from generate_profile import generate_profile
from aiogram.types import InputFile, ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
import asyncio
import json
import random
import os
from aiogram import Bot, Dispatcher, F
from aiogram.types import Message, CallbackQuery
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

BOT_TOKEN = "7335965093:AAGg4AFZNtvBvxjQxD6qGwTyOtZ1HfpOYHQ"
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(storage=MemoryStorage())

QUESTIONS_PATH = os.path.join("json", "questions", "questions.json")
STATS_PATH = os.path.join("json", "stats.json")

with open(QUESTIONS_PATH, "r", encoding="utf-8") as f:
    questions = json.load(f)

class QuizStates(StatesGroup):
    waiting_for_answer = State()
    choosing_difficulty = State()

def load_stats():
    try:
        with open(STATS_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        return {}

def save_stats(data):
    with open(STATS_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

def get_accuracy(correct, wrong):
    total = correct + wrong
    return round(correct / total * 100, 1) if total else 0

def generate_leaderboard(stats, limit=10):
    sorted_users = sorted(stats.items(), key=lambda item: item[1].get("correct", 0), reverse=True)
    lines = ["🏆 <b>Топ 10 игроков викторины</b>:"]
    medals = ["🥇", "🥈", "🥉"]
    for i, (user_id, data) in enumerate(sorted_users[:limit]):
        medal = medals[i] if i < 3 else f"{i+1}."
        username = data.get("username", f"ID:{user_id}")
        correct = data.get("correct", 0)
        wrong = data.get("wrong", 0)
        acc = get_accuracy(correct, wrong)
        lines.append(f"{medal} <b>{username}</b> — ✅ {correct} | ❌ {wrong} | 🎯 {acc}%")
    return "\n".join(lines)

main_menu = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="🎮 Играть")],
        [KeyboardButton(text="⚙️ Сложность"), KeyboardButton(text="🏆 Топ")],
        [KeyboardButton(text="👤 Профиль"), KeyboardButton(text="🔁 Сброс")]
    ],
    resize_keyboard=True
)

@dp.message(F.text == "/start")
async def start_handler(message: Message, state: FSMContext):
    user_id = str(message.from_user.id)
    stats = load_stats()
    stats.setdefault(user_id, {
        "correct": 0, "wrong": 0, "username": message.from_user.username or f"ID:{user_id}",
        "xp": 0, "recent_correct_ids": [], "avatar": avatat_choice
    })
    save_stats(stats)
    await state.clear()
    await message.answer("Привет! 👋 Добро пожаловать в викторину.\nВыбери действие ниже ⬇️", reply_markup=main_menu)

@dp.message(F.text == "🎮 Играть")
async def game_start(message: Message, state: FSMContext):
    state_data = await state.get_data()
    difficulty = state_data.get("difficulty")
    if not difficulty:
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🟢 Лёгкий", callback_data="difficulty_easy")],
            [InlineKeyboardButton(text="🔴 Сложный", callback_data="difficulty_hard")]
        ])
        await state.set_state(QuizStates.choosing_difficulty)
        await message.answer("Выбери уровень сложности:", reply_markup=keyboard)
        return

    await send_question(message.from_user.id, state)

@dp.message(F.text == "⚙️ Сложность")
async def choose_difficulty_command(message: Message, state: FSMContext):
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🟢 Лёгкий", callback_data="difficulty_easy")],
        [InlineKeyboardButton(text="🔴 Сложный", callback_data="difficulty_hard")]
    ])
    await state.set_state(QuizStates.choosing_difficulty)
    await message.answer("Выбери уровень сложности:", reply_markup=keyboard)

@dp.callback_query(QuizStates.choosing_difficulty)
async def difficulty_selected(callback: CallbackQuery, state: FSMContext):
    data = callback.data
    difficulty_map = {
        "difficulty_easy": "easy",
        "difficulty_hard": "hard"
    }

    difficulty = difficulty_map.get(data)
    if not difficulty:
        await callback.answer("Ошибка выбора.", show_alert=True)
        return

    await state.update_data(difficulty=difficulty)
    await callback.answer(f"Сложность выбрана: {difficulty.capitalize()}")
    await callback.message.edit_text(
        f"✅ Установлен уровень сложности: <b>{'Лёгкий' if difficulty == 'easy' else 'Сложный'}</b>",
        parse_mode=ParseMode.HTML
    )
    await send_question(callback.from_user.id, state)

@dp.message(F.text == "🏆 Топ")
async def leaderboard_button(message: Message):
    stats = load_stats()
    await message.answer(generate_leaderboard(stats), parse_mode=ParseMode.HTML)

@dp.message(F.text == "👤 Профиль")
async def profile_button(message: Message):
    await send_profile(message)

@dp.message(F.text == "🔁 Сброс")
async def reset_button(message: Message):
    await reset_progress(message)

@dp.message()
async def unknown_message(message: Message):
    await message.answer("❌ Пожалуйста, пользуйся кнопками внизу ⬇️", reply_markup=main_menu)

async def send_question(user_id, state: FSMContext):
    stats = load_stats()
    user_stats = stats.get(str(user_id), {})
    recent_ids = user_stats.get("recent_correct_ids", [])
    state_data = await state.get_data()
    difficulty = state_data.get("difficulty", "easy")

    filtered_questions = [
        q for q in questions
        if q["id"] not in recent_ids and q.get("difficulty", "easy") == difficulty
    ]

    if not filtered_questions:
        await bot.send_message(user_id, f"🎉 Все вопросы на уровне сложности '{difficulty}' завершены!\nНапиши 🔁 Сброс или выбери другой уровень сложности ⚙️.")
        return

    q = random.choice(filtered_questions)
    question_text = q["question"]
    answers = q["answers"]
    correct_answer = q["correct_answer"]
    correct_index = answers.index(correct_answer)

    await state.set_state(QuizStates.waiting_for_answer)
    await state.update_data(
        correct_index=correct_index,
        answers=answers,
        correct_answer=correct_answer,
        question_id=q["id"]
    )

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=ans, callback_data=str(i))]
        for i, ans in enumerate(answers)
    ])

    await bot.send_message(
        user_id,
        f"❓ <b>{question_text}</b>\n\n🧠 Сложность: <b>{'Лёгкий' if difficulty == 'easy' else 'Сложный'}</b>",
        reply_markup=keyboard,
        parse_mode=ParseMode.HTML
    )

@dp.callback_query(QuizStates.waiting_for_answer)
async def answer_handler(callback: CallbackQuery, state: FSMContext):
    user_id = str(callback.from_user.id)
    stats = load_stats()
    stats.setdefault(user_id, {
        "correct": 0,
        "wrong": 0,
        "username": callback.from_user.username or f"ID:{user_id}",
        "xp": 0,
        "recent_correct_ids": []
    })

    data = await state.get_data()
    correct_index = data.get("correct_index")
    correct_answer = data.get("correct_answer")
    question_id = data.get("question_id")

    try:
        chosen_index = int(callback.data)
    except ValueError:
        await callback.answer("Ошибка кнопки!", show_alert=True)
        return

    if chosen_index == correct_index:
        stats[user_id]["correct"] += 1
        stats[user_id]["xp"] += 5
        await callback.answer("✅ Верно! +5 XP")

        stats[user_id].setdefault("recent_correct_ids", [])
        stats[user_id]["recent_correct_ids"].append(question_id)
        if len(stats[user_id]["recent_correct_ids"]) > 100:
            stats[user_id]["recent_correct_ids"].pop(0)

    else:
        stats[user_id]["wrong"] += 1
        stats[user_id]["xp"] = max(0, stats[user_id]["xp"] - 7)
        await callback.answer(f"❌ Неверно. -7 XP\nПравильный ответ: {correct_answer}", show_alert=True)

    save_stats(stats)
    await send_question(callback.from_user.id, state)


async def send_profile(message: Message):
    from aiogram.types.input_file import FSInputFile

    user_id = message.from_user.id
    profile_path = await generate_profile(bot, user_id)

    if profile_path and os.path.exists(profile_path):
        photo = FSInputFile(profile_path)
        await message.reply_photo(photo, reply_markup=main_menu)
        try:
            os.remove(profile_path)
        except Exception as e:
            print(f"Ошибка при удалении файла: {e}")
    else:
        await message.reply("❌ Не удалось создать профиль.", reply_markup=main_menu)

async def reset_progress(message: Message):
    user_id = str(message.from_user.id)
    stats = load_stats()
    if user_id in stats:
        stats[user_id]["recent_correct_ids"] = []
        save_stats(stats)
        await message.answer("🔄 История вопросов сброшена!", reply_markup=main_menu)
    else:
        await message.answer("Нет данных для сброса.", reply_markup=main_menu)

async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
