# ملف: bot.py

import nest_asyncio
nest_asyncio.apply()

import httpx
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
import os # سنستخدم هذه المكتبة لقراءة التوكن بأمان

# --- قراءة التوكن من متغيرات البيئة (أكثر أماناً) ---
# سنقوم بتعيين هذا المتغير في لوحة تحكم Render لاحقاً
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")

PISTON_API_URL = "https://emkc.org/api/v2/piston/execute"
user_code_sessions = {}

# ... (جميع دوال البوت: start_command, reset_command, run_command, etc. تبقى كما هي تماماً) ...
async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    user_code_sessions[user_id] = ""
    welcome_message = """
    أهلاً بك في بوت محرر بايثون! 🐍 (يعمل 24/7)

    **الجديد:** الآن أعمل بشكل دائم!

    **كيفية الاستخدام:**
    1.  أرسل لي كود بايثون.
    2.  أرسل الأمر `/run` لتنفيذه.

    **الأوامر:** `/run`, `/reset`, `/help`
    """
    await update.message.reply_text(welcome_message)

async def reset_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    user_code_sessions[user_id] = ""
    await update.message.reply_text("✅ تم إعادة تعيين الجلسة.")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    text = update.message.text
    if user_id not in user_code_sessions:
        user_code_sessions[user_id] = ""
    user_code_sessions[user_id] += text + "\n"
    await update.message.reply_text("📝 تم استلام الكود. نفّذ باستخدام /run.")

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await start_command(update, context)

async def run_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    code_to_run = user_code_sessions.get(user_id, "")

    if not code_to_run.strip():
        await update.message.reply_text("لم ترسل أي كود بعد!")
        return

    await update.message.reply_text("⏳ جاري تنفيذ الكود...")

    try:
        payload = { "language": "python", "version": "3.10.0", "files": [{"content": code_to_run}] }
        async with httpx.AsyncClient() as client:
            response = await client.post(PISTON_API_URL, json=payload, timeout=20.0)
            result = response.json()

        if "run" in result and result["run"] is not None:
            output = result["run"]["stdout"]
            stderr = result["run"]["stderr"]
            final_output = ""
            if output: final_output += f"--- ✅ المخرجات ---\n{output}\n"
            if stderr: final_output += f"--- ❌ خطأ ---\n{stderr}\n"
            if not final_output: final_output = "✅ تم تنفيذ الكود بنجاح بدون أي مخرجات."
        else:
            final_output = f"حدث خطأ: {result.get('message', 'خطأ غير معروف')}"

        await update.message.reply_text(final_output)

    except httpx.ReadTimeout:
        await update.message.reply_text("❌ خطأ: استغرق الكود وقتاً طويلاً للتنفيذ.")
    except Exception as e:
        await update.message.reply_text(f"❌ حدث خطأ غير متوقع: {e}")

# --- الدالة الرئيسية لتشغيل البوت ---
def main():
    if not TELEGRAM_TOKEN:
        print("❌ خطأ: لم يتم العثور على توكن تليجرام. يرجى تعيينه في متغيرات البيئة.")
        return

    print("🚀 البوت قيد التشغيل (الإصدار الدائم)...")
    app = Application.builder().token(TELEGRAM_TOKEN).build()

    # إضافة المعالجات
    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(CommandHandler("reset", reset_command))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("run", run_command))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    print("📡 البوت يستمع الآن للرسائل...")
    app.run_polling()

if __name__ == '__main__':
    main()
