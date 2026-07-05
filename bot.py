#!/usr/bin/env python3
"""
bot.py — Telegram frontend for shazaming

A single-user bot: paste a SoundCloud or YouTube URL, get a tracklist back.

Dependencies:
    uv sync  (adds python-telegram-bot, python-dotenv)

Config (.env, not committed):
    TELEGRAM_BOT_TOKEN=...
    TELEGRAM_OWNER_ID=...
"""

import asyncio
import logging
import os
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv
from telegram import Update
from telegram.ext import Application, ContextTypes, MessageHandler, filters

from main import slug_from_url
from mix_shazam import format_tracklist
from mix_shazam import main as shazam_main

load_dotenv()

BOT_TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]
OWNER_ID = int(os.environ["TELEGRAM_OWNER_ID"])

TELEGRAM_MSG_LIMIT = 4096

logger = logging.getLogger(__name__)
job_lock = asyncio.Lock()


ALLOWED_HOSTS = ("soundcloud.com", "youtube.com", "youtu.be")


def is_probably_url(text: str) -> bool:
    text = text.strip().lower()
    return text.startswith(("http://", "https://")) and any(h in text for h in ALLOWED_HOSTS)


async def send_long_message(chat_id: int, text: str, context: ContextTypes.DEFAULT_TYPE):
    """Split text into <=4096-char chunks on line boundaries and send each."""
    lines = text.split("\n")
    chunk = ""
    for line in lines:
        candidate = f"{chunk}\n{line}" if chunk else line
        if len(candidate) > TELEGRAM_MSG_LIMIT - 100:
            await context.bot.send_message(chat_id=chat_id, text=chunk)
            chunk = line
        else:
            chunk = candidate
    if chunk:
        await context.bot.send_message(chat_id=chat_id, text=chunk)


async def run_job(url: str, update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    slug = slug_from_url(url)
    timestamp = datetime.now().strftime("%Y-%m-%dT%H-%M-%S")
    out_dir = Path("runs") / f"{timestamp}_{slug}"
    out_dir.mkdir(parents=True, exist_ok=True)

    log_file = out_dir / "shazaming.log"
    output = out_dir / "tracklist.json"
    mp3_path = str(out_dir / "mix.mp3")

    file_handler = logging.FileHandler(log_file, mode="w")
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(
        logging.Formatter("%(asctime)s %(levelname)s %(message)s", datefmt="%H:%M:%S")
    )
    root_logger = logging.getLogger()
    root_logger.addHandler(file_handler)

    await update.message.reply_text(f"Started: {url}\nOutput: {out_dir}")

    try:
        results = await shazam_main(
            url,
            interval=1,
            duration=20,
            output=str(output),
            mp3_path=mp3_path,
        )
    except Exception as e:
        logger.exception("Job failed")
        await update.message.reply_text(f"Job failed: {e}")
        return
    finally:
        root_logger.removeHandler(file_handler)
        file_handler.close()

    await send_long_message(chat_id, format_tracklist(results), context)
    await update.message.reply_text(f"Done. Saved to {out_dir}")


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user is None or update.effective_user.id != OWNER_ID:
        logger.warning(f"Ignored message from unauthorized user {update.effective_user}")
        return

    url = (update.message.text or "").strip()
    if not is_probably_url(url):
        await update.message.reply_text(
            "Send me a SoundCloud or YouTube mix URL and I'll identify the tracks."
        )
        return

    if job_lock.locked():
        await update.message.reply_text(
            "Already working on a mix — please wait for it to finish before sending another."
        )
        return

    async with job_lock:
        await run_job(url, update, context)


def main():
    logging.basicConfig(level=logging.INFO)
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.run_polling()


if __name__ == "__main__":
    main()
