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

# --- Logging Setup ---
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# --- Bot Config ---
TOKEN = "8072365620:AAHnRlzDCIydHDv6GnCPJFyFtdk39M23_Xc"
YOUR_CHAT_ID = 987632568

# --- Conversation States ---
NAME, MATERIAL_TYPE, SUBJECT, SEMESTER, FILE = range(5)

# --- Options ---
MATERIAL_TYPES = ["Notes", "Exam Papers", "Presentation", "Other"]
SEMESTER_OPTIONS = ["1st", "2nd", "3rd", "4th", "5th", "6th"]

# --- Handlers ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Starts the conversation and clears any existing data"""
    context.user_data.clear()
    await update.message.reply_text(
        "👋 Hi! What's your name?",
        reply_markup=ReplyKeyboardRemove()
    )
    return NAME

async def get_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Stores the name and asks for material type"""
    name = update.message.text.strip()
    if not name:
        await update.message.reply_text("❌ Please enter a valid name.")
        return NAME

    context.user_data['name'] = name
    
    # Create keyboard buttons (2 columns)
    keyboard = [
        MATERIAL_TYPES[i:i+2] 
        for i in range(0, len(MATERIAL_TYPES), 2)
    ]
    
    await update.message.reply_text(
        f"📝 {name}, what material would you like to share?",
        reply_markup=ReplyKeyboardMarkup(
            keyboard,
            one_time_keyboard=True,
            resize_keyboard=True
        )
    )
    return MATERIAL_TYPE

async def get_material_type(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Stores material type and asks for subject"""
    choice = update.message.text
    if choice not in MATERIAL_TYPES:
        # Re-send keyboard if invalid choice
        keyboard = [
            MATERIAL_TYPES[i:i+2] 
            for i in range(0, len(MATERIAL_TYPES), 2)
        ]
        await update.message.reply_text(
            "❗ Please choose from the buttons below:",
            reply_markup=ReplyKeyboardMarkup(
                keyboard,
                one_time_keyboard=True,
                resize_keyboard=True
            )
        )
        return MATERIAL_TYPE

    context.user_data['material_type'] = choice
    await update.message.reply_text(
        "📚 What subject is this for?",
        reply_markup=ReplyKeyboardRemove()
    )
    return SUBJECT

async def get_subject(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Stores subject and asks for semester"""
    context.user_data['subject'] = update.message.text.strip()
    
    # Create semester keyboard (3 columns)
    keyboard = [
        SEMESTER_OPTIONS[i:i+3] 
        for i in range(0, len(SEMESTER_OPTIONS), 3)
    ]
    
    await update.message.reply_text(
        "🎓 Which semester is this for?",
        reply_markup=ReplyKeyboardMarkup(
            keyboard,
            one_time_keyboard=True,
            resize_keyboard=True
        )
    )
    return SEMESTER

async def get_semester(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Stores semester and asks for file"""
    semester = update.message.text
    if semester not in SEMESTER_OPTIONS:
        await update.message.reply_text("❌ Please select from the buttons.")
        return SEMESTER

    context.user_data['semester'] = semester
    await update.message.reply_text(
        "📤 Please upload your file (PDF or PPTX):",
        reply_markup=ReplyKeyboardRemove()
    )
    return FILE

async def get_file(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handles the file upload"""
    if not update.message.document:
        await update.message.reply_text("❌ Please send a file.")
        return FILE

    file = update.message.document
    file_name = file.file_name
    file_ext = file_name.split('.')[-1].lower() if '.' in file_name else ""

    # Validate file type
    material_type = context.user_data.get('material_type', '').lower()
    if material_type == 'presentation' and file_ext != 'pptx':
        await update.message.reply_text("❌ Only PPTX files for presentations.")
        return FILE
    elif file_ext != 'pdf':
        await update.message.reply_text("❌ Only PDF files accepted.")
        return FILE

    # Process valid file
    try:
        await update.message.reply_text("✅ File received! Processing...")
        
        # Forward to admin
        await context.bot.forward_message(
            chat_id=YOUR_CHAT_ID,
            from_chat_id=update.message.chat_id,
            message_id=update.message.message_id
        )
        
        # Send details to admin
        data = context.user_data
        await context.bot.send_message(
            chat_id=YOUR_CHAT_ID,
            text=f"""📝 New {data['material_type']} submission
👤 Name: {data['name']}
📘 Subject: {data['subject']}
📅 Semester: {data['semester']}
📂 File: {file_name}"""
        )
        
        await update.message.reply_text(
            "🎉 Thank you for your submission!\n"
            "Type /start to share more materials."
        )
    except Exception as e:
        logger.error(f"File processing error: {e}")
        await update.message.reply_text("❌ Error processing file. Please try again.")
    finally:
        context.user_data.clear()
        return ConversationHandler.END

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Cancels the conversation"""
    await update.message.reply_text(
        "🚫 Operation cancelled. Use /start to begin again.",
        reply_markup=ReplyKeyboardRemove()
    )
    context.user_data.clear()
    return ConversationHandler.END

def main():
    """Run the bot"""
    application = Application.builder().token(TOKEN).build()

    # Add global /start handler
    application.add_handler(CommandHandler("start", start))

    # Conversation handler
    conv_handler = ConversationHandler(
        entry_points=[],
        states={
            NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_name)],
            MATERIAL_TYPE: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_material_type)],
            SUBJECT: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_subject)],
            SEMESTER: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_semester)],
            FILE: [
                MessageHandler(filters.Document.ALL & ~filters.COMMAND, get_file),
                MessageHandler(~filters.Document.ALL & ~filters.COMMAND, 
                             lambda u,c: u.message.reply_text("❌ Please send a file."))
            ],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
        per_user=True,
        per_chat=True,
    )
    application.add_handler(conv_handler)

    # Start the bot
    print("Bot is running...")
    application.run_polling()

if __name__ == "__main__":
    main()
