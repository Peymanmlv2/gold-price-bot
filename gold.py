from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
    CallbackContext,  # این خط اضافه شد
    JobQueue,
)
import requests
from bs4 import BeautifulSoup
import sqlite3
import datetime
import logging

# تنظیمات لاگ
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

TOKEN = "7964020615:AAEq0io72Uhz8lwsqmc_n9Gz5z2GYD06WFo"  # جایگزین کنید
DB_NAME = "gold_users.db"

# ---- 1. مدیریت دیتابیس ----
def init_db():
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
        conn.close()

# ---- 2. دریافت قیمت ----
def fetch_gold_price():
    try:
        url = "https://www.tgju.org/profile/geram18"
        headers = {"User-Agent": "Mozilla/5.0"}
        
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.text, "html.parser")
        price = soup.find("span", class_="value").get_text(strip=True)
        change = soup.find("span", class_="change").get_text(strip=True)
        
        return (
            f"🏅 قیمت طلای 18 عیار\n"
            f"🕒 ساعت {datetime.datetime.now().strftime('%H:%M')}\n"
            f"💰 قیمت: {price} تومان\n"
            f"📊 تغییرات: {change}"
        )
    except Exception as e:
        logger.error(f"خطا در دریافت قیمت: {e}")
        return "⚠️ خطا در دریافت قیمت. لطفاً بعداً تلاش کنید."

# ---- 3. دستورات ربات ----
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        user = update.effective_user
        conn = sqlite3.connect(DB_NAME)
        c = conn.cursor()
        
        c.execute(
            "INSERT OR REPLACE INTO users VALUES (?, ?, ?)",
            (user.id, user.username, datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
        )
        conn.commit()
        
        await update.message.reply_text(
            "✅ عضو شدید!\n"
            "قیمت طلا هر ساعت برای شما ارسال می‌شود.\n"
            "برای لغو عضویت /unsubscribe ارسال کنید."
        )
    except Exception as e:
        logger.error(f"خطا در ثبت کاربر: {e}")
        await update.message.reply_text("⚠️ خطا در ثبت عضویت")
    finally:
        conn.close()

async def unsubscribe(update: Update, context: ContextTypes.DEFAULT_TYPE):
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
        conn.close()

# ---- 4. ارسال خودکار ----
async def send_updates(context: CallbackContext):  # اصلاح نوع پارامتر
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
        conn.close()

# ---- 5. راه‌اندازی ----
def main():
    init_db()
    
    application = Application.builder().token(TOKEN).build()
    
    # اضافه کردن دستورات
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("unsubscribe", unsubscribe))
    
    # تنظیم JobQueue
    job_queue = application.job_queue
    job_queue.run_repeating(
        callback=send_updates,
        interval=600 ,  # هر 1 ساعت
        first=10        # شروع پس از 10 ثانیه
    )
    
    logger.info("ربات قیمت طلا فعال شد")
    application.run_polling()

if __name__ == "__main__":
    main()