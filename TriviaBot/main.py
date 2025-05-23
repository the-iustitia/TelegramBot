import asyncio
import json
import random
from aiogram import Bot, Dispatcher
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.fsm.context import FSMContext
from aiogram.filters import Command

BOT_TOKEN = "TOKEN"
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(storage=MemoryStorage())

with open("questions.json", "r", encoding="utf-8") as f:
    questions = json.load(f)

def load_stats():
    try:
        with open("stats.json", "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        return {}

def save_stats(data):
    with open("stats.json", "w", encoding="utf-8") as f:
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
    await send_question(message.from_user.id)

@dp.message(Command("leaderboard"))
async def leaderboard_handler(message: Message):
    stats = load_stats()
    text = generate_leaderboard(stats)
    await message.answer(text, parse_mode=ParseMode.HTML)

@dp.message(Command("profile"))
async def profile_handler(message: Message):
    user_id = str(message.from_user.id)
    stats = load_stats()
    user = stats.get(user_id)

    if not user:
        await message.answer("У тебя пока нет статистики. Начни игру с /start.")
        return

    correct = user.get("correct", 0)
    wrong = user.get("wrong", 0)
    acc = get_accuracy(correct, wrong)
    rank = get_user_rank(user_id, stats)
    total = correct + wrong

    await message.answer(
        f"<b>👤 Профиль: {user.get('username', 'Без имени')}</b>\n"
        f"✅ Правильных: <b>{correct}</b>\n"
        f"❌ Неправильных: <b>{wrong}</b>\n"
        f"🎯 Точность: <b>{acc}%</b>\n"
        f"🏅 Ранг: <b>{rank}</b> из {len(stats)}\n"
        f"📚 Всего ответов: <b>{total}</b>",
        parse_mode=ParseMode.HTML
    )

async def send_question(user_id):
    q = random.choice(questions)
    question_text = q['question']
    answers = q['answers']
    correct_index = answers.index(q['correct_answer'])

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=ans, callback_data=f"{i}:{correct_index}")]
        for i, ans in enumerate(answers)
    ])

    await bot.send_message(user_id, f"❓ {question_text}", reply_markup=kb)

@dp.callback_query()
async def answer_handler(callback: CallbackQuery):
    user_id = str(callback.from_user.id)
    stats = load_stats()
    stats.setdefault(user_id, {
        "correct": 0,
        "wrong": 0,
        "username": callback.from_user.username or f"ID:{user_id}"
    })

    try:
        chosen_index, correct_index = map(int, callback.data.split(":"))
    except ValueError:
        await callback.answer("Ошибка кнопки!", show_alert=True)
        return

    if chosen_index == correct_index:
        stats[user_id]["correct"] += 1
        await callback.answer("✅ Верно!")
    else:
        stats[user_id]["wrong"] += 1
        correct_answer = questions[0]['answers'][correct_index]
        await callback.answer(f"❌ Неверно. Правильный ответ: {correct_answer}", show_alert=True)

    save_stats(stats)
    await send_question(callback.from_user.id)

async def main():
    await dp.start_polling(bot)

print("Quiz started!!!")

if __name__ == "__main__":
    asyncio.run(main())