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

# --- Logging --------------------------------------------------
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# --- Bot config ------------------------------------------------
TOKEN = "8072365620:AAHnRlzDCIydHDv6GnCPJFyFtdk39M23_Xc"
YOUR_CHAT_ID = 987632568  # integer, not string

# --- Conversation states --------------------------------------
NAME, MATERIAL_TYPE, SUBJECT, SEMESTER, FILE = range(5)

# --- Options --------------------------------------------------
MATERIAL_TYPES = ["Notes", "Exam Papers", "Presentation", "Other"]
SEMESTER_OPTIONS = ["1st", "2nd", "3rd", "4th", "5th", "6th"]
ALLOWED_EXTENSIONS = ['.pdf', '.pptx']


# --- Handlers -------------------------------------------------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Clear all data and force a fresh start
    context.user_data.clear()
    await update.message.reply_text("👋 Hi! What's your name?")
    return NAME

async def get_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    name = update.message.text.strip()
    context.user_data['name'] = name

    kb = [MATERIAL_TYPES[i:i+2] for i in range(0, len(MATERIAL_TYPES), 2)]
    await update.message.reply_text(
        f"📝 {name}, what kind of material would you like to share?",
        reply_markup=ReplyKeyboardMarkup(kb, one_time_keyboard=True, resize_keyboard=True)
    )
    return MATERIAL_TYPE

async def get_material_type(update: Update, context: ContextTypes.DEFAULT_TYPE):
    choice = update.message.text
    if choice not in MATERIAL_TYPES:
        # Re-send buttons if input is invalid
        kb = [MATERIAL_TYPES[i:i+2] for i in range(0, len(MATERIAL_TYPES), 2)]
        await update.message.reply_text(
            "❗ Please choose a valid material type using the buttons below:",
            reply_markup=ReplyKeyboardMarkup(kb, one_time_keyboard=True, resize_keyboard=True)
        )
        return MATERIAL_TYPE  # Stay in the same state

    # Valid choice → proceed
    context.user_data['material_type'] = choice
    await update.message.reply_text(
        "📚 Okay, and this is for which subject exactly?",
        reply_markup=ReplyKeyboardRemove()  # Remove keyboard for free-text input
    )
    return SUBJECT

async def get_subject(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['subject'] = update.message.text.strip()

    sem_kb = [SEMESTER_OPTIONS[i:i+3] for i in range(0, len(SEMESTER_OPTIONS), 3)]
    await update.message.reply_text(
        "🎓 And this would come under which semester?",
        reply_markup=ReplyKeyboardMarkup(sem_kb, one_time_keyboard=True, resize_keyboard=True)
    )
    return SEMESTER


async def get_semester(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handles semester selection and asks for file."""
    semester = update.message.text

    # Validate the semester selection
    if semester not in SEMESTER_OPTIONS:
        await update.message.reply_text(
            "❌ Please select a valid semester from the buttons."
        )
        return SEMESTER

    context.user_data['semester'] = semester

    # Remove the keyboard once the semester is selected
    await update.message.reply_text(
        "📤 Now please upload the file (PDF or PPTX only).",
        reply_markup=ReplyKeyboardRemove()
    )
    return FILE


async def get_file(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle uploads: only PDF for Notes/Exam/Other, only PPTX for Presentations."""
    doc = update.message.document

    # 1) If it's not a document at all:
    if not doc:
        await update.message.reply_text(
            "❌ Unsupported file format!\n"
            "Only PDF (.pdf) or PowerPoint (.pptx) files are accepted.\n"
            "Please try again."
        )
        return FILE

    # 2) Check extension vs. material type
    file_name = doc.file_name or ""
    ext = "." + file_name.rsplit(".", 1)[-1].lower() if "." in file_name else ""
    material = context.user_data.get("material_type", "").lower()

    if material == "presentation":
        allowed_exts = [".pptx"]
        err_msg = "❌ Only PPTX files are allowed for Presentations.\nPlease upload a `.pptx` file."
    else:
        allowed_exts = [".pdf"]
        err_msg = "❌ Only PDF files are allowed for this material.\nPlease upload a `.pdf` file."

    if ext not in allowed_exts:
        await update.message.reply_text(err_msg)
        return FILE

    # 3) If we get here, it's a valid file—process it
    try:
        # Confirmation #1
        await update.message.reply_text(
            "✅ File format accepted! Processing your submission..."
        )

        # Forward the document to your chat
        await context.bot.forward_message(
            chat_id=YOUR_CHAT_ID,
            from_chat_id=update.message.chat_id,
            message_id=update.message.message_id
        )

        # Send the details to your chat
        data = context.user_data
        await context.bot.send_message(
            chat_id=YOUR_CHAT_ID,
            text=(
                f"📝 New {data['material_type']} submission\n"
                f"👤 Name: {data['name']}\n"
                f"📘 Subject: {data['subject']}\n"
                f"📅 Semester: {data['semester']}\n"
                f"📂 File: {file_name}"
            )
        )

        # Confirmation #2 (separate message)
        await update.message.reply_text(
            "🎉 File successfully submitted!\n"
            "Thank you for your contribution!"
        )
        await update.message.reply_text(
            "🔁 Want to share more? Just type /start again to make another contribution!"
        )

    except Exception as e:
        logger.error(f"Error in get_file: {e}")
        await update.message.reply_text(
            "❌ Oops, something went wrong while processing your file.\n"
            "Please try again or /cancel to start over."
        )
    finally:
        context.user_data.clear()
        return ConversationHandler.END


async def invalid_file(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Catch all non-document messages in FILE state."""
    await update.message.reply_text(
        "❌ Unsupported file format!\n"
        "Only .pdf or .pptx files are accepted.\n"
        "Please send a valid document."
    )
    return FILE

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🚫 Operation cancelled. Use /start to try again.")
    context.user_data.clear()
    return ConversationHandler.END

async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logger.error(f"Update {update} caused error {context.error}")
    if update.message:
        await update.message.reply_text("⚠️ An error occurred. Please /cancel and try again.")


def main():
    app = Application.builder().token(TOKEN).build()

    conv = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            NAME: [ MessageHandler(filters.TEXT & ~filters.COMMAND, get_name) ],
            MATERIAL_TYPE: [ MessageHandler(filters.TEXT & ~filters.COMMAND, get_material_type) ],
            SUBJECT: [ MessageHandler(filters.TEXT & ~filters.COMMAND, get_subject) ],
            SEMESTER: [ MessageHandler(filters.TEXT & ~filters.COMMAND, get_semester) ],
            FILE: [
                # 1) valid docs → get_file
                MessageHandler(filters.Document.ALL & ~filters.COMMAND, get_file),
                # 2) everything else → invalid_file
                MessageHandler(~filters.Document.ALL & ~filters.COMMAND, invalid_file),
            ],
        },
        fallbacks=[ CommandHandler("cancel", cancel) ],
        per_user=True,
        per_chat=True,
    )

    app.add_handler(conv)
    app.add_error_handler(error_handler)

    print("Bot is up and running...")
    app.run_polling()


if __name__ == "__main__":
    main()
