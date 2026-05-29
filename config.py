import os

BOT_TOKEN = os.getenv("BOT_TOKEN", "8823952328:AAFYbYfryNcwI1kkIT1ynpv7XP4IpocLyHs")  # ВСТАВЬ СВОЙ ТОКЕН
ADMIN_IDS = [716644144]  # Админ ID

SUPPORT_LINK = "@Gid_Guarantor"
MANAGER_LINK = "@Gid_Guarantor"

# FIX: абсолютный путь к фото
import pathlib
PHOTO_PATH = str(pathlib.Path(__file__).parent / "photo.jpg")
