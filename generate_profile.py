import random
import json
import os
from PIL import Image, ImageDraw, ImageFont, ImageFilter
from aiogram import Bot
import aiohttp

async def generate_profile(bot: Bot, user_id: int):
    stats_path = os.path.join("json", "stats.json")
    if not os.path.exists(stats_path):
        print("❌ stats.json не найден")
        return None

    with open(stats_path, "r", encoding="utf-8") as f:
        stats = json.load(f)

    data = stats.get(str(user_id))
    if not data:
        return None

    avatar_path = None
    temp_avatar = None
    avatar_from_telegram = False

    try:
        user_photos = await bot.get_user_profile_photos(user_id, limit=1)
        if user_photos.total_count > 0:
            file_id = user_photos.photos[0][0].file_id
            file = await bot.get_file(file_id)
            file_path = file.file_path
            url = f"https://api.telegram.org/file/bot{bot.token}/{file_path}"

            async with aiohttp.ClientSession() as session:
                async with session.get(url) as resp:
                    if resp.status == 200:
                        avatar_data = await resp.read()
                        temp_avatar = f"temp_avatar_{user_id}.png"
                        with open(temp_avatar, "wb") as f:
                            f.write(avatar_data)
                        avatar_path = temp_avatar
                        avatar_from_telegram = True
                        data["avatar"] = avatar_path
                        stats[str(user_id)] = data
                        with open(stats_path, "w", encoding="utf-8") as f:
                            json.dump(stats, f, ensure_ascii=False, indent=4)
    except Exception as e:
        print(f"⚠️ Ошибка загрузки Telegram-аватара: {e}")

    if not avatar_path:
        avatar_filename = data.get("avatar")
        valid = False
        if avatar_filename:
            potential_path = os.path.join("Images", avatar_filename)
            if os.path.exists(potential_path) and os.path.isfile(potential_path):
                avatar_path = potential_path
                valid = True

        if not valid:
            avatar_choice = f"{random.randint(1, 10)}.png"
            avatar_path = os.path.join("Images", avatar_choice)
            data["avatar"] = avatar_choice
            stats[str(user_id)] = data
            with open(stats_path, "w", encoding="utf-8") as f:
                json.dump(stats, f, ensure_ascii=False, indent=4)

            if not os.path.exists(avatar_path) or not os.path.isfile(avatar_path):
                print(f"❌ Аватар {avatar_path} не найден")
                return None

    correct = int(data.get("correct", 0))
    wrong = int(data.get("wrong", 0))
    xp = int(data.get("xp", 0))
    username = data.get("username", "Unknown")
    total = correct + wrong
    accuracy = round((correct / total) * 100) if total else 0

    users_sorted = sorted(stats.items(), key=lambda x: int(x[1].get("xp", 0)), reverse=True)
    rank = next((i + 1 for i, (uid, _) in enumerate(users_sorted) if uid == str(user_id)), "??")

    bg_path = os.path.join("Images", "bg.png")
    if not os.path.exists(bg_path):
        print(f"❌ Фон {bg_path} не найден")
        return None
    bg = Image.open(bg_path).convert("RGBA")
    draw = ImageDraw.Draw(bg)
    image_width, image_height = bg.size

    font_path = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
    font_big = ImageFont.truetype(font_path, 52)
    font_stats = ImageFont.truetype(font_path, 50)

    avatar = Image.open(avatar_path).convert("RGBA")
    size = 220
    avatar = avatar.resize((200, 200))

    mask = Image.new("L", (200, 200), 0)
    draw_mask = ImageDraw.Draw(mask)
    draw_mask.ellipse((0, 0, 200, 200), fill=255)

    final_avatar = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw_outline = ImageDraw.Draw(final_avatar)
    draw_outline.ellipse((0, 0, size, size), fill=(0, 255, 0, 255))
    final_avatar.paste(avatar, (10, 10), mask)

    avatar_x = 250
    avatar_y = (image_height - size) // 2
    bg.paste(final_avatar, (avatar_x, avatar_y), final_avatar)

    name_width = draw.textlength(username, font=font_big)
    username_x = avatar_x + size // 2 - name_width // 2
    draw.text((username_x, avatar_y + size + 10), username, font=font_big, fill="black")

    stats_text = [
        f"Ранг: №{rank}",
        f"Правильно: {correct}",
        f"Ошибок: {wrong}",
        f"Точность: {accuracy}%",
        f"Опыт: {xp}"
    ]

    rect_w, rect_h = 900, 900
    rect_x = image_width - rect_w - 100
    rect_y = (image_height - rect_h) // 2

    blur_box = (rect_x, rect_y, rect_x + rect_w, rect_y + rect_h)
    cropped = bg.crop(blur_box)
    blurred = cropped.filter(ImageFilter.GaussianBlur(radius=10))
    bg.paste(blurred, blur_box)

    orange_overlay = Image.new("RGBA", (rect_w, rect_h), (255, 140, 0, 180))
    bg.paste(orange_overlay, (rect_x, rect_y), orange_overlay)

    for i, line in enumerate(stats_text):
        draw.text((rect_x + 40, rect_y + 40 + i * 70), line, font=font_stats, fill="black")

    output_path = f"profile_{user_id}.png"
    bg.save(output_path)

    if avatar_from_telegram:
        try:
            os.remove(temp_avatar)
        except Exception as e:
            print(f"⚠️ Ошибка удаления временного аватара: {e}")
        data.pop("avatar", None)
        stats[str(user_id)] = data
        with open(stats_path, "w", encoding="utf-8") as f:
            json.dump(stats, f, ensure_ascii=False, indent=4)

    return output_path
