from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes, CallbackContext
import requests
from bs4 import BeautifulSoup
import sqlite3
import datetime
import pytz
import logging

# تنظیمات پایه
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)  # اینجا از __name__ استفاده می‌کنیم نه name

TOKEN = "7964020615:AAEq0io72Uhz8lwsqmc_n9Gz5z2GYD06WFo"  # توکن ربات خود را اینجا قرار دهید
DB_NAME = "gold_users.db"
TEHRAN_TZ = pytz.timezone('Asia/Tehran')

def init_db():
    conn = None
    try:
        conn = sqlite3.connect(DB_NAME)
        c = conn.cursor()
        c.execute("""
            CREATE TABLE IF NOT EXISTS users (
                chat_id INTEGER PRIMARY KEY,
                username TEXT,
                register_date TEXT
            )
        """)
        conn.commit()
    except Exception as e:
        logger.error(f"خطا در ایجاد دیتابیس: {e}")
    finally:
        if conn:
            conn.close()

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        user = update.effective_user
        conn = sqlite3.connect(DB_NAME)
        c = conn.cursor()
        
        c.execute(
            "INSERT OR REPLACE INTO users VALUES (?, ?, ?)",
            (user.id, user.username, datetime.datetime.now(TEHRAN_TZ).strftime("%Y-%m-%d %H:%M:%S"))
        )
        conn.commit()
        
        await update.message.reply_text(
            "✅ عضو شدید!\nقیمت طلا هر دقیقه برای شما ارسال می‌شود.\n"
            "برای لغو عضویت /unsubscribe ارسال کنید."
        )
    except Exception as e:
        logger.error(f"خطا در ثبت کاربر: {e}")
        await update.message.reply_text("⚠️ خطا در ثبت عضویت")
    finally:
        if conn:
            conn.close()

async def unsubscribe(update: Update, context: ContextTypes.DEFAULT_TYPE):
    conn = None
    try:
        conn = sqlite3.connect(DB_NAME)
        c = conn.cursor()
        c.execute("DELETE FROM users WHERE chat_id=?", (update.effective_user.id,))
        conn.commit()
        await update.message.reply_text("✅ عضویت شما لغو شد.")
    except Exception as e:
        logger.error(f"خطا در لغو عضویت: {e}")
        await update.message.reply_text("⚠️ خطا در لغو عضویت")
    finally:
        if conn:
            conn.close()

async def send_updates(context: CallbackContext):
    conn = None
    try:
        price = fetch_gold_price()
        conn = sqlite3.connect(DB_NAME)
        c = conn.cursor()
        c.execute("SELECT chat_id FROM users")
        
        for (chat_id,) in c.fetchall():
            try:
                await context.bot.send_message(chat_id=chat_id, text=price)
            except Exception as e:
                logger.warning(f"ارسال به کاربر {chat_id} ناموفق: {e}")
                c.execute("DELETE FROM users WHERE chat_id=?", (chat_id,))
                conn.commit()
    except Exception as e:
        logger.error(f"خطا در ارسال خودکار: {e}")
    finally:
        if conn:
            conn.close()

def fetch_gold_price():
    try:
        url = "https://www.tgju.org/profile/geram18"
        headers = {"User-Agent": "Mozilla/5.0"}
        
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.text, "html.parser")
        price = soup.find("span", class_="value").get_text(strip=True)
        change = soup.find("span", class_="change").get_text(strip=True)
        current_time = datetime.datetime.now(TEHRAN_TZ).strftime('%H:%M:%S')
        
        return (
            f"🏅 قیمت طلای 18 عیار\n"
            f"🕒 ساعت {current_time}\n"
            f"💰 قیمت: {price} تومان\n"
            f"📊 تغییرات: {change}"
        )
    except Exception as e:
        logger.error(f"خطا در دریافت قیمت: {e}")
        return "⚠️ خطا در دریافت قیمت. لطفاً بعداً تلاش کنید."

def main():
    init_db()
    app = Application.builder().token(TOKEN).build()
    
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("unsubscribe", unsubscribe))
    
    job_queue = app.job_queue
    if job_queue:
        job_queue.run_repeating(
            callback=send_updates,
            interval=60.0,
            first=10.0
        )
        logger.info("JobQueue با موفقیت تنظیم شد")
    else:
        logger.error("JobQueue در دسترس نیست!")
    
    logger.info("ربات در حال اجراست...")
    app.run_polling()

if __name__ == "__main__":
    main()