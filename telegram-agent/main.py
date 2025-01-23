import os
import asyncio
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from openai import AsyncOpenAI
from database import NoteDatabase

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
- /save: Save a note to memory
- /notes: Show recent notes

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
    
    await db.add_note(chat_id, note_text)
    await update.message.reply_text("📝 Note saved successfully!")

async def show_notes(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    notes = await db.get_notes(chat_id)
    
    if not notes:
        await update.message.reply_text("No notes found. Start saving with /save")
        return
    
    response = "📒 Your Recent Notes:\n\n"
    for i, (content, timestamp) in enumerate(notes, 1):
        response += f"{i}. {content}\n   ({timestamp})\n\n"
    
    await update.message.reply_text(response)

async def interpret_command(user_input: str, update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    prompt = f"""Analyze this user input and determine if it matches any command purpose:
User Input: {user_input}

Available Commands:
- /start: Initialize new conversation
- /reset: Reset conversation history
- /help: List available commands
- /save: Save a note to memory
- /notes: Show recent notes

Respond with "True" if the input matches a command's purpose, otherwise "False"."""
    
    completion = await client.chat.completions.create(
        model="deepseek-chat",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.2
    )
    
    if completion.choices[0].message.content.strip().lower() == "true":
        # Determine which command to execute
        command_prompt = f"""Which command should be executed for this input?
User Input: {user_input}

Available Commands:
- /start: Initialize new conversation
- /reset: Reset conversation history
- /help: List available commands
- /save: Save a note to memory
- /notes: Show recent notes

Respond ONLY with the command name (e.g. "/save")"""
        
        command_completion = await client.chat.completions.create(
            model="deepseek-chat",
            messages=[{"role": "user", "content": command_prompt}],
            temperature=0.2
        )
        
        command = command_completion.choices[0].message.content.strip()
        
        if command == "/start":
            await start(update, context)
        elif command == "/reset":
            await reset(update, context)
        elif command == "/help":
            await help(update, context)
        elif command == "/save":
            await save_note(update, context)
        elif command == "/notes":
            await show_notes(update, context)
        
        return True
    
    return False

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    user_input = update.message.text

    if chat_id not in conversations:
        conversations[chat_id] = [SYSTEM_MESSAGE]

    # Check if input matches a command's purpose
    command_executed = await interpret_command(user_input, update, context)
    if command_executed:
        return

    conversations[chat_id].append({"role": "user", "content": user_input})

    try:
        await context.bot.send_chat_action(chat_id=chat_id, action="typing")
        completion = await client.chat.completions.create(
            model="deepseek-chat",
            messages=conversations[chat_id]
        )
        full_response = completion.choices[0].message.content

        max_length = 4000
        response_parts = [full_response[i:i+max_length] for i in range(0, len(full_response), max_length)]

        for part in response_parts:
            await update.message.reply_text(part)
            await asyncio.sleep(0.5)

        conversations[chat_id].append({"role": "assistant", "content": full_response})

    except Exception as e:
        await update.message.reply_text(f"🚨 Error: {str(e)}")

async def handle_confirmation(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    user_input = update.message.text.lower()
    
    if "pending_command" not in context.user_data:
        await update.message.reply_text("No pending command to confirm")
        return
        
    if user_input in ["yes", "y"]:
        command = context.user_data["pending_command"]
        del context.user_data["pending_command"]
        
        if command == "/start":
            await start(update, context)
        elif command == "/reset":
            await reset(update, context)
        elif command == "/help":
            await help(update, context)
        elif command == "/save":
            await update.message.reply_text("Please send your note after the command\nExample: /save Important reminder")
        elif command == "/notes":
            await show_notes(update, context)
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
