from telegram import Update, ReplyKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    ConversationHandler,
    filters
)
import logging
import asyncio

# --- Logging ---
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# --- Config ---
TOKEN = "8072365620:AAHnRlzDCIydHDv6GnCPJFyFtdk39M23_Xc"
YOUR_CHAT_ID = 987632568

# --- States ---
NAME, MATERIAL_TYPE, SUBJECT, SEMESTER, FILE = range(5)

# --- Options ---
MATERIAL_TYPES = ["Notes", "Exam Papers", "Presentation", "Other"]
SEMESTER_OPTIONS = ["1st", "2nd", "3rd", "4th", "5th", "6th"]

# =============================================
# CHANGED: Added proper error handling and state reset
# =============================================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Force reset everything when /start is called"""
    context.user_data.clear()  # Clear all stored data
    await update.message.reply_text(
        "👋 Hi! What's your name?",
        reply_markup=ReplyKeyboardRemove()  # Remove any lingering keyboards
    )
    return NAME

async def get_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle name input with validation"""
    name = update.message.text.strip()
    if not name:
        await update.message.reply_text("❌ Please enter a valid name.")
        return NAME

    context.user_data['name'] = name
    
    # =============================================
    # CHANGED: Added delay to ensure buttons render properly
    # =============================================
    kb = [MATERIAL_TYPES[i:i+2] for i in range(0, len(MATERIAL_TYPES), 2)]
    await update.message.reply_text(
        f"📝 {name}, choose material type:",
        reply_markup=ReplyKeyboardMarkup(kb, one_time_keyboard=True, resize_keyboard=True)
    )
    await asyncio.sleep(0.5)  # Small delay for UI consistency
    return MATERIAL_TYPE

async def get_material_type(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle material type with button re-send if invalid"""
    choice = update.message.text
    if choice not in MATERIAL_TYPES:
        # =============================================
        # CHANGED: Re-send buttons if invalid input
        # =============================================
        kb = [MATERIAL_TYPES[i:i+2] for i in range(0, len(MATERIAL_TYPES), 2)]
        await update.message.reply_text(
            "❗ Please use the buttons below:",
            reply_markup=ReplyKeyboardMarkup(kb, one_time_keyboard=True, resize_keyboard=True)
        )
        await asyncio.sleep(0.5)
        return MATERIAL_TYPE

    context.user_data['material_type'] = choice
    await update.message.reply_text(
        "📚 Enter the subject name:",
        reply_markup=ReplyKeyboardRemove()  # Clear before free-text input
    )
    return SUBJECT

async def get_subject(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle subject input"""
    context.user_data['subject'] = update.message.text.strip()
    
    # =============================================
    # CHANGED: Clear previous keyboard before showing new one
    # =============================================
    await update.message.reply_text(
        "Clearing previous options...",
        reply_markup=ReplyKeyboardRemove()
    )
    
    sem_kb = [SEMESTER_OPTIONS[i:i+3] for i in range(0, len(SEMESTER_OPTIONS), 3)]
    await update.message.reply_text(
        "🎓 Select semester:",
        reply_markup=ReplyKeyboardMarkup(sem_kb, one_time_keyboard=True, resize_keyboard=True)
    )
    await asyncio.sleep(0.5)
    return SEMESTER

async def get_semester(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle semester selection"""
    semester = update.message.text
    if semester not in SEMESTER_OPTIONS:
        await update.message.reply_text("❌ Please select from the buttons.")
        return SEMESTER

    context.user_data['semester'] = semester
    await update.message.reply_text(
        "📤 Now upload the file (PDF or PPTX):",
        reply_markup=ReplyKeyboardRemove()
    )
    return FILE

async def get_file(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle file uploads"""
    doc = update.message.document
    if not doc:
        await update.message.reply_text("❌ Please send a valid file.")
        return FILE

    file_name = doc.file_name or ""
    ext = "." + file_name.rsplit(".", 1)[-1].lower() if "." in file_name else ""
    
    if context.user_data.get("material_type", "").lower() == "presentation":
        if ext != ".pptx":
            await update.message.reply_text("❌ Only PPTX files for Presentations.")
            return FILE
    elif ext != ".pdf":
        await update.message.reply_text("❌ Only PDF files allowed.")
        return FILE

    try:
        await update.message.reply_text("✅ Processing...")
        await context.bot.forward_message(
            chat_id=YOUR_CHAT_ID,
            from_chat_id=update.message.chat_id,
            message_id=update.message.message_id
        )
        
        data = context.user_data
        await context.bot.send_message(
            chat_id=YOUR_CHAT_ID,
            text=f"""📝 New {data['material_type']} submission
👤 Name: {data['name']}
📘 Subject: {data['subject']}
📅 Semester: {data['semester']}
📂 File: {file_name}"""
        )
        
        await update.message.reply_text("🎉 Submitted! Thank you!")
    except Exception as e:
        logger.error(f"Error: {e}")
        await update.message.reply_text("❌ Failed to process. Try again.")
    finally:
        context.user_data.clear()
        return ConversationHandler.END

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Cancel conversation"""
    await update.message.reply_text(
        "🚫 Cancelled. Use /start to begin again.",
        reply_markup=ReplyKeyboardRemove()
    )
    context.user_data.clear()
    return ConversationHandler.END

def main():
    app = Application.builder().token(TOKEN).build()
    
    # =============================================
    # CHANGED: Made /start a global handler
    # =============================================
    app.add_handler(CommandHandler("start", start))

    conv = ConversationHandler(
        entry_points=[],  # Empty because /start is now global
        states={
            NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_name)],
            MATERIAL_TYPE: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_material_type)],
            SUBJECT: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_subject)],
            SEMESTER: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_semester)],
            FILE: [
                MessageHandler(filters.Document.ALL & ~filters.COMMAND, get_file),
                MessageHandler(~filters.Document.ALL & ~filters.COMMAND, 
                             lambda u,c: u.message.reply_text("❌ Only PDF/PPTX files!"))
            ],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
        per_user=True,
        per_chat=True,
    )
    app.add_handler(conv)
    
    print("Bot is running...")
    app.run_polling()

if __name__ == "__main__":
    main()
