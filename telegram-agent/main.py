import os
import asyncio
import logging
import re
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from openai import AsyncOpenAI
from database import NoteDatabase

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

# Initialize services
db = NoteDatabase()
client = AsyncOpenAI(
    api_key=os.getenv("DEEPSEEK_API_KEY"),
    base_url="https://api.deepseek.com"
)

SYSTEM_MESSAGE = {
    "role": "system",
    "content": """You are a helpful AI assistant. Your tasks include:
1. Respond helpfully to user messages
2. Automatically execute commands when user intent matches their purpose
3. Always respond in less than 50 words

Available commands:
- /start: Initialize new conversation
- /reset: Reset conversation history
- /help: List available commands
- /save <note>: Save a new note to memory (e.g., "Remember to buy milk")
- /notes: Retrieve and display saved notes (e.g., "Show me my notes")

When user input matches a command's purpose, execute it automatically."""
}

conversations = {}

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    conversations[chat_id] = [SYSTEM_MESSAGE]
    await update.message.reply_text("Hello! I'm your AI assistant. How can I help you today?")

async def reset(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    conversations[chat_id] = [SYSTEM_MESSAGE]
    await update.message.reply_text("Conversation reset. How can I assist you?")

async def help(update: Update, context: ContextTypes.DEFAULT_TYPE):
    help_text = """
Available commands:
/start - Initialize new conversation
/reset - Reset conversation history
/save <note> - Save a new note
/notes - Show recent notes
/help - List all available commands
"""
    await update.message.reply_text(help_text)

async def save_note(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    note_text = ' '.join(context.args)
    
    if not note_text:
        await update.message.reply_text("Please provide a note after the command\nExample: /save Buy milk tomorrow")
        return
    
    try:
        success = await db.add_note(chat_id, note_text)
        if success:
            await update.message.reply_text("📝 Note saved successfully!")
        else:
            await update.message.reply_text("⚠️ Failed to save note, please try again")
    except Exception as e:
        logger.error(f"Error saving note: {e}")
        await update.message.reply_text("🚨 Error saving note, please try again")

async def show_notes(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    try:
        notes = await db.get_notes(chat_id)
        if not notes:
            await update.message.reply_text("No notes found. Start saving with /save")
            return
        
        response = "📒 Your Recent Notes:\n\n"
        for i, (content, timestamp) in enumerate(notes, 1):
            response += f"{i}. {content}\n   ({timestamp})\n\n"
        
        await update.message.reply_text(response)
    except Exception as e:
        logger.error(f"Error retrieving notes: {e}")
        await update.message.reply_text("🚨 Error retrieving notes, please try again")

async def interpret_command(user_input: str, update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    prompt = f"""Analyze this user input and determine if it matches any command purpose.
User Input: "{user_input}"

Available Commands (with examples):
- /start: ("start", "begin chat", "hello", "hi")
- /reset: ("reset", "clear", "start over")
- /help: ("help", "commands", "what can you do?")
- /save: ("save note", "remember to...", "note this...", "please save this...")
- /notes: ("show me my notes", "what notes do I have?", "retrieve my notes", "list notes")

If the input is semantically similar to these examples, respond "True". Otherwise "False"."""
    
    try:
        completion = await client.chat.completions.create(
            model="deepseek-chat",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.2
        )

        # Check if the response contains "true" instead of exact match
        result_str = completion.choices[0].message.content.strip().lower()
        if "true" in result_str:
            command_prompt = f"""Which command should be executed for this input?
User Input: "{user_input}"

Available Commands:
- /start
- /reset
- /help
- /save
- /notes

Respond ONLY with the command name (e.g. "/notes")."""
            
            command_completion = await client.chat.completions.create(
                model="deepseek-chat",
                messages=[{"role": "user", "content": command_prompt}],
                temperature=0.2
            )
            
            cmd_str = command_completion.choices[0].message.content.strip().lower()
            if not cmd_str.startswith("/"):
                cmd_str = "/" + cmd_str.lstrip("/")

            chat_id = update.effective_chat.id
            
            if cmd_str == "/save":
                note_text = re.sub(r'\b(remember|note:?)\b', '', user_input, flags=re.IGNORECASE).strip()
                if not note_text:
                    await update.message.reply_text("⚠️ Please provide a note to save")
                    return True
                
                try:
                    success = await db.add_note(chat_id, note_text)
                    if success:
                        await update.message.reply_text("📝 Note saved successfully!")
                    else:
                        await update.message.reply_text("⚠️ Failed to save note, please try again")
                except Exception as e:
                    logger.error(f"Error saving note: {e}")
                    await update.message.reply_text("🚨 Error saving note, please try again")
                return True
            
            handlers = {
                "/start": start,
                "/reset": reset,
                "/help": help,
                "/notes": show_notes
            }
            
            if cmd_str in handlers:
                await handlers[cmd_str](update, context)
                return True
            
        return False
    except Exception as e:
        logger.error(f"Error in interpret_command: {e}")
        return False

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    user_input = update.message.text

    if chat_id not in conversations:
        conversations[chat_id] = [SYSTEM_MESSAGE]

    # Database connection check
    global db
    if not db.verify_connection():
        await update.message.reply_text("⚠️ Database connection issue, trying to reconnect...")
        db = NoteDatabase()
        if not db.verify_connection():
            await update.message.reply_text("❌ Failed to reconnect to database")
            return

    # Try to interpret as command first
    command_executed = await interpret_command(user_input, update, context)
    if command_executed:
        return

    # Automatic note detection with regex
    if re.search(r'\b(remember|note)\b', user_input.lower()):
        note_text = re.sub(r'\b(remember|note:?)\b', '', user_input, flags=re.IGNORECASE).strip()
        if note_text:
            try:
                success = await db.add_note(chat_id, note_text)
                if success:
                    await update.message.reply_text("📝 I've automatically saved this note for you!")
                else:
                    await update.message.reply_text("⚠️ Failed to save note automatically")
            except Exception as e:
                logger.error(f"Error auto-saving note: {e}")
                await update.message.reply_text("🚨 Error saving note automatically")

    conversations[chat_id].append({"role": "user", "content": user_input})
    try:
        await context.bot.send_chat_action(chat_id=chat_id, action="typing")
        completion = await client.chat.completions.create(
            model="deepseek-chat",
            messages=conversations[chat_id]
        )
        full_response = completion.choices[0].message.content

        response_parts = [full_response[i:i+4000] for i in range(0, len(full_response), 4000)]
        for part in response_parts:
            await update.message.reply_text(part)
            await asyncio.sleep(0.5)

        conversations[chat_id].append({"role": "assistant", "content": full_response})
    except Exception as e:
        logger.error(f"Error in handle_message: {e}")
        await update.message.reply_text("🚨 Error processing your request")

async def handle_confirmation(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    user_input = update.message.text.lower()
    
    if "pending_command" not in context.user_data:
        await update.message.reply_text("No pending command to confirm")
        return
        
    if user_input in ["yes", "y"]:
        command = context.user_data["pending_command"]
        del context.user_data["pending_command"]
        await globals()[command[1:]](update, context)
    else:
        await update.message.reply_text("Command cancelled")
        del context.user_data["pending_command"]

def main():
    application = Application.builder().token(os.getenv("TELEGRAM_TOKEN")).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("reset", reset))
    application.add_handler(CommandHandler("help", help))
    application.add_handler(CommandHandler("save", save_note))
    application.add_handler(CommandHandler("notes", show_notes))
    
    application.add_handler(MessageHandler(
        filters.TEXT & ~filters.COMMAND,
        lambda update, context: (
            handle_confirmation(update, context) 
            if "pending_command" in context.user_data
            else handle_message(update, context)
        )
    ))

    application.run_polling()

if __name__ == "__main__":
    main()
