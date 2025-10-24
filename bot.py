# ملف: bot.py (الإصدار 3.1 - تحسين رسالة الترحيب والدعم)

import nest_asyncio
nest_asyncio.apply()

import httpx
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
import os

# --- إعدادات ---
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
PISTON_API_URL = "https://emkc.org/api/v2/piston/execute"

# --- جلسات المستخدمين ---
user_code_sessions = {}
user_packages_sessions = {}

# --- الدوال ---

# === تم تحديث هذه الدالة بالكامل ===
async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    user_name = update.message.from_user.first_name # لنرحب بالمستخدم باسمه
    
    # إعادة تعيين الجلسة لضمان بداية نظيفة
    user_code_sessions[user_id] = ""
    user_packages_sessions[user_id] = []
    
    welcome_message = f"""
    أهلاً بك يا {user_name} في **منصة بايثون المتكاملة**! 🐍

    أنا لست مجرد بوت، أنا بيئة تطوير مصغرة بين يديك، مصممة لمساعدتك على تجربة وتشغيل أكواد بايثون بسرعة وسهولة، مباشرة من تليجرام.

    ---
    ### 🚀 **دليل البدء السريع**

    **الهدف:** تشغيل كود بايثون يستخدم مكتبة خارجية (مثل `requests`).

    **الخطوة 1: تثبيت المكتبات**
    أخبرني ما هي المكتبات التي تحتاجها باستخدام أمر `/install`.
    *(مثال: لتثبيت مكتبة `requests`)*
    `/install requests`

    **الخطوة 2: كتابة الكود**
    أرسل لي كود بايثون الذي تريد تشغيله كرسالة نصية عادية.
    *(مثال: كود لجلب عنوان IP)*
    `import requests`
    `response = requests.get("https://api.ipify.org?format=json")`
    `print(response.json()["ip"])`

    **الخطوة 3: التشغيل!**
    عندما تكون جاهزاً، أرسل الأمر `/run` لتنفيذ كل شيء.

    ---
    ### 📖 **قائمة الأوامر الكاملة**

    - `/run`
      لتنفيذ الكود الذي أرسلته مع المكتبات التي حددتها.

    - `/install <مكتبة1> <مكتبة2> ...`
      لتحديد المكتبات المطلوبة. سيتم تثبيتها عند استخدام `/run`.

    - `/reset`
      لمسح كل شيء: الكود الذي كتبته وقائمة المكتبات المحددة، والبدء من جديد بجلسة نظيفة.

    - `/help`
      لعرض هذه الرسالة التعليمية مرة أخرى في أي وقت.

    ---
    ### 💡 **نصائح وحيل**

    *   **كود متعدد الأسطر:** يمكنك إرسال الكود في رسالة واحدة طويلة أو عدة رسائل قصيرة، سأقوم بتجميعها لك.
    *   **بدون مكتبات:** إذا كان الكود لا يحتاج لمكتبات خارجية، يمكنك تخطي أمر `/install` والذهاب مباشرة إلى كتابة الكود ثم `/run`.
    *   **الأخطاء صديقتك:** إذا كان هناك خطأ في الكود أو في اسم المكتبة، سأرسل لك سجل الأخطاء لمساعدتك في تصحيحه.

    **جاهز لتبدأ رحلتك في البرمجة؟ جرب المثال في دليل البدء السريع!**
    """
    await update.message.reply_text(welcome_message, parse_mode='Markdown')

async def reset_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    user_code_sessions[user_id] = ""
    user_packages_sessions[user_id] = []
    await update.message.reply_text("✅ **جلسة جديدة!** تم مسح الكود والمكتبات. يمكنك البدء من الصفر.")

async def install_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    packages = context.args
    if not packages:
        await update.message.reply_text("⚠️ **خطأ في الاستخدام!**\nالرجاء تحديد أسماء المكتبات بعد الأمر.\n*مثال: `/install requests pandas`*", parse_mode='Markdown')
        return
    
    user_packages_sessions[user_id] = packages
    packages_str = ", ".join([f"`{p}`" for p in packages])
    await update.message.reply_text(f"✅ **تم تحديد المكتبات.**\n سيتم تثبيت: {packages_str} عند التشغيل القادم.", parse_mode='Markdown')

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    text = update.message.text
    if user_id not in user_code_sessions:
        user_code_sessions[user_id] = ""
    user_code_sessions[user_id] += text + "\n"
    await update.message.reply_text("📝 تم استلام الكود. أرسل المزيد، أو نفّذ باستخدام `/run`.")

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # أمر المساعدة يعرض نفس الرسالة الترحيبية الشاملة
    await start_command(update, context)

async def run_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    code_to_run = user_code_sessions.get(user_id, "")
    packages_to_install = user_packages_sessions.get(user_id, [])

    if not code_to_run.strip():
        await update.message.reply_text("لم ترسل أي كود بعد! أرسل لي بعض الكود أولاً.")
        return

    tasks_message = "⏳ **جاري التنفيذ...**\n"
    if packages_to_install:
        tasks_message += f"1. تثبيت المكتبات: `{', '.join(packages_to_install)}`\n"
        tasks_message += "2. تشغيل السكربت."
    else:
        tasks_message += "1. تشغيل السكربت."
        
    await update.message.reply_text(tasks_message, parse_mode='Markdown')

    try:
        payload = {
            "language": "python", "version": "3.10.0",
            "packages": packages_to_install,
            "files": [{"content": code_to_run}]
        }
        async with httpx.AsyncClient() as client:
            response = await client.post(PISTON_API_URL, json=payload, timeout=60.0)
            result = response.json()

        compile_stage = result.get("compile", {})
        run_stage = result.get("run", {})
        final_output = ""

        if compile_stage and (compile_stage.get("stdout") or compile_stage.get("stderr")):
            final_output += "--- ⚙️ **سجل التثبيت** ---\n"
            if compile_stage.get("stdout"):
                final_output += "```\n" + compile_stage.get("stdout")[:1000] + "\n```\n"
            if compile_stage.get("stderr"):
                final_output += "--- ⚠️ **تحذيرات/أخطاء التثبيت** ---\n"
                final_output += "```\n" + compile_stage.get("stderr")[:1000] + "\n```\n"
        
        if run_stage and (run_stage.get("stdout") or run_stage.get("stderr")):
            if run_stage.get("stdout"):
                final_output += f"--- ✅ **مخرجات الكود** ---\n"
                final_output += "```\n" + run_stage.get('stdout')[:1000] + "\n```\n"
            if run_stage.get("stderr"):
                final_output += f"--- ❌ **أخطاء الكود** ---\n"
                final_output += "```\n" + run_stage.get('stderr')[:1000] + "\n```\n"
        
        if not final_output:
            final_output = "✅ **اكتمل التنفيذ بنجاح** (بدون أي مخرجات)."

        await update.message.reply_text(final_output, parse_mode='Markdown')

    except httpx.ReadTimeout:
        await update.message.reply_text("❌ **خطأ: انتهت مهلة الانتظار.**\nاستغرقت العملية (التثبيت أو التشغيل) وقتاً طويلاً جداً.")
    except Exception as e:
        await update.message.reply_text(f"❌ **حدث خطأ غير متوقع:**\n`{e}`")

# --- الدالة الرئيسية (تبقى كما هي) ---
def main():
    if not TELEGRAM_TOKEN:
        print("❌ خطأ: لم يتم العثور على توكن تليجرام.")
        return

    print("🚀 البوت قيد التشغيل (الإصدار 3.1)...")
    app = Application.builder().token(TELEGRAM_TOKEN).build()

    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(CommandHandler("reset", reset_command))
    app.add_handler(CommandHandler("install", install_command))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("run", run_command))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    print("📡 البوت يستمع الآن للرسائل...")
    app.run_polling()

if __name__ == '__main__':
    main()
