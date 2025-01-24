import os
import logging
from dotenv import load_dotenv
from telegram.ext import Application, CommandHandler, MessageHandler, filters
from openai import AsyncOpenAI
from database import NoteDatabase
from commands import start, reset, help, save_note, show_notes, remove_notes, execute_remove_notes, edit_notes, execute_edit_notes
from interpreter import interpret_command
from llm_handler import handle_message, handle_confirmation, SYSTEM_MESSAGE

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

def main():
    # Load environment variables
    load_dotenv()

    # Initialize services
    db = NoteDatabase()
    client = AsyncOpenAI(
        api_key=os.getenv("DEEPSEEK_API_KEY"),
        base_url="https://api.deepseek.com"
    )

    # Create application
    application = Application.builder().token(os.getenv("TELEGRAM_TOKEN")).build()

    # Store shared resources in bot_data
    application.bot_data['db'] = db
    application.bot_data['client'] = client
    application.bot_data['system_message'] = SYSTEM_MESSAGE
    application.bot_data['commands'] = {
        'start': start,
        'reset': reset,
        'help': help,
        'save_note': save_note,
        'show_notes': show_notes,
        'remove_notes': execute_remove_notes,
        'edit_notes': execute_edit_notes
    }
    application.bot_data['interpreter'] = interpret_command

    # Add command handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("reset", reset))
    application.add_handler(CommandHandler("help", help))
    application.add_handler(CommandHandler("save", save_note))
    application.add_handler(CommandHandler("notes", show_notes))
    application.add_handler(CommandHandler("remove_notes", remove_notes))
    application.add_handler(CommandHandler("edit_notes", edit_notes))
    
    # Add message handler
    application.add_handler(MessageHandler(
        filters.TEXT & ~filters.COMMAND,
        lambda update, context: (
            handle_confirmation(update, context) 
            if "pending_command" in context.user_data
            else handle_message(update, context)
        )
    ))

    # Start the bot
    application.run_polling()

if __name__ == "__main__":
    main()
