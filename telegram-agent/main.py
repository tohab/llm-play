import os
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from openai import AsyncOpenAI

# Load environment variables
load_dotenv()

# Initialize DeepSeek client
client = AsyncOpenAI(
    api_key=os.getenv("DEEPSEEK_API_KEY"),
    base_url="https://api.deepseek.com"
)

SYSTEM_MESSAGE = {
    "role": "system",
    "content": """You are a helpful AI assistant. Your tasks include:
1. Respond helpfully to user messages
2. Interpret natural language commands and map them to available commands
3. Suggest appropriate commands when user intent matches available commands
4. Always respond in less than 50 words

Available commands:
- /start: Initialize new conversation
- /reset: Reset conversation history
- /help: List available commands

When user input matches a command's purpose, suggest the command and ask for confirmation."""
}

# Store conversations per chat
conversations = {}

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Initialize a new conversation"""
    chat_id = update.effective_chat.id
    conversations[chat_id] = [SYSTEM_MESSAGE]
    await update.message.reply_text("Hello! I'm your AI assistant. How can I help you today?")

async def reset(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Reset conversation history"""
    chat_id = update.effective_chat.id
    conversations[chat_id] = [SYSTEM_MESSAGE]
    await update.message.reply_text("Conversation reset. How can I assist you?")

async def help(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show available commands"""
    help_text = """
Available commands:
/start - Initialize new conversation
/reset - Reset conversation history
/help - List all available commands
"""
    await update.message.reply_text(help_text)

async def interpret_command(user_input: str) -> str | None:
    """Use LLM to interpret natural language and suggest commands"""
    prompt = f"""Analyze this user input and suggest the most appropriate command:
User Input: {user_input}

Available Commands:
- /start: Initialize new conversation
- /reset: Reset conversation history
- /help: List available commands

Respond ONLY with the command name if a match is found (e.g. "/reset"), or "None" if no match."""
    
    completion = await client.chat.completions.create(
        model="deepseek-chat",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.2
    )
    
    response = completion.choices[0].message.content.strip()
    return response if response in ["/start", "/reset", "/help"] else None

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    user_input = update.message.text

    # Initialize conversation if new
    if chat_id not in conversations:
        conversations[chat_id] = [SYSTEM_MESSAGE]

    # First check if message matches any commands
    suggested_command = await interpret_command(user_input)
    if suggested_command:
        # Store pending command in context
        context.user_data["pending_command"] = suggested_command
        await update.message.reply_text(f"Do you want to run {suggested_command}? (yes/no)")
        return

    # Add user message to history
    conversations[chat_id].append({"role": "user", "content": user_input})

    try:
        # Show typing indicator
        await context.bot.send_chat_action(chat_id=chat_id, action="typing")

        # Get complete response
        completion = await client.chat.completions.create(
            model="deepseek-chat",
            messages=conversations[chat_id]
        )

        full_response = completion.choices[0].message.content

        # Split long responses into multiple messages
        max_length = 4000
        response_parts = [full_response[i:i+max_length] for i in range(0, len(full_response), max_length)]

        # Send each part as a separate message
        for part in response_parts:
            await update.message.reply_text(part)
            # Add slight delay between messages
            await asyncio.sleep(0.5)

        # Save final response to history
        conversations[chat_id].append({"role": "assistant", "content": full_response})

    except Exception as e:
        await update.message.reply_text(f"🚨 Error: {str(e)}")

async def handle_confirmation(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle yes/no responses for command confirmation"""
    chat_id = update.effective_chat.id
    user_input = update.message.text.lower()
    
    if "pending_command" not in context.user_data:
        await update.message.reply_text("No pending command to confirm")
        return
        
    if user_input in ["yes", "y"]:
        command = context.user_data["pending_command"]
        # Clear pending command
        del context.user_data["pending_command"]
        
        # Execute the command
        if command == "/start":
            await start(update, context)
        elif command == "/reset":
            await reset(update, context)
        elif command == "/help":
            await help(update, context)
    else:
        await update.message.reply_text("Command cancelled")
        del context.user_data["pending_command"]

def main():
    # Create bot application
    application = Application.builder().token(os.getenv("TELEGRAM_TOKEN")).build()

    # Add handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("reset", reset))
    application.add_handler(CommandHandler("help", help))
    application.add_handler(MessageHandler(
        filters.TEXT & ~filters.COMMAND,
        lambda update, context: (
            handle_confirmation(update, context) 
            if "pending_command" in context.user_data
            else handle_message(update, context)
        )
    ))

    # Start polling
    application.run_polling()

if __name__ == "__main__":
    import asyncio
    main()
