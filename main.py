from generate_profile import generate_profile
from aiogram.types import InputFile
import time
import traceback
import asyncio
import json
import random
import os
from aiogram import Bot, Dispatcher, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.filters import Command

BOT_TOKEN = "7335965093:AAGg4AFZNtvBvxjQxD6qGwTyOtZ1HfpOYHQ"
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(storage=MemoryStorage())

QUESTIONS_PATH = os.path.join("json", "questions", "questions.json")
STATS_PATH = os.path.join("json", "stats.json")

with open(QUESTIONS_PATH, "r", encoding="utf-8") as f:
    questions = json.load(f)

class QuizStates(StatesGroup):
    waiting_for_answer = State()

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

def get_user_rank(user_id, stats):
    sorted_users = sorted(stats.items(), key=lambda x: x[1].get("correct", 0), reverse=True)
    for index, (uid, _) in enumerate(sorted_users):
        if uid == user_id:
            return index + 1
    return len(sorted_users)

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

@dp.message(Command("start"))
async def start_handler(message: Message, state: FSMContext):
    await message.answer("Привет! Добро пожаловать в викторину 🎓. Готов?")
    await send_question(message.from_user.id, state)

@dp.message(Command("leaderboard"))
async def leaderboard_handler(message: Message):
    stats = load_stats()
    text = generate_leaderboard(stats)
    await message.answer(text, parse_mode=ParseMode.HTML)

@dp.message(Command("profile"))
async def send_profile(message: Message):
    from aiogram.types.input_file import FSInputFile

    user = message.from_user
    user_id = str(user.id)
    user_name = user.full_name

    profile_path = generate_profile(user_id)

    if profile_path and os.path.exists(profile_path):
        photo = FSInputFile(profile_path)
        await message.reply_photo(photo)
    else:
        await message.reply("❌ Не удалось создать профиль.")


async def send_question(user_id, state: FSMContext):
    q = random.choice(questions)
    question_text = q["question"]
    answers = q["answers"]
    correct_answer = q["correct_answer"]
    correct_index = answers.index(correct_answer)

    await state.set_state(QuizStates.waiting_for_answer)
    await state.update_data(
        correct_index=correct_index,
        answers=answers,
        correct_answer=correct_answer
    )

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=ans, callback_data=str(i))]
        for i, ans in enumerate(answers)
    ])

    await bot.send_message(user_id, f"❓ {question_text}", reply_markup=keyboard)

@dp.callback_query(QuizStates.waiting_for_answer)
async def answer_handler(callback: CallbackQuery, state: FSMContext):
    user_id = str(callback.from_user.id)
    stats = load_stats()
    stats.setdefault(user_id, {
        "correct": 0,
        "wrong": 0,
        "username": callback.from_user.username or f"ID:{user_id}",
        "xp": 0
    })

    data = await state.get_data()
    correct_index = data.get("correct_index")
    correct_answer = data.get("correct_answer")

    try:
        chosen_index = int(callback.data)
    except ValueError:
        await callback.answer("Ошибка кнопки!", show_alert=True)
        return

    if chosen_index == correct_index:
        stats[user_id]["correct"] += 1
        stats[user_id]["xp"] += 5
        await callback.answer("✅ Верно! +5 XP")
    else:
        stats[user_id]["wrong"] += 1
        stats[user_id]["xp"] = max(0, stats[user_id]["xp"] - 7)
        await callback.answer(f"❌ Неверно. -7 XP\nПравильный ответ: {correct_answer}", show_alert=True)

    save_stats(stats)
    await send_question(callback.from_user.id, state)

async def main():
    await dp.start_polling(bot)



if __name__ == "__main__":
    asyncio.run(main())
