import asyncio
import re
import logging
from database import NoteDatabase

logger = logging.getLogger(__name__)

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

async def handle_message(update, context):
    """Handle incoming messages and route to appropriate handler"""
    chat_id = update.effective_chat.id
    user_input = update.message.text

    if 'conversation' not in context.chat_data:
        context.chat_data['conversation'] = [context.bot_data['system_message']]

    # Database connection check
    db = context.bot_data['db']
    if not db.verify_connection():
        await update.message.reply_text("⚠️ Database connection issue, trying to reconnect...")
        context.bot_data['db'] = NoteDatabase()
        if not db.verify_connection():
            await update.message.reply_text("❌ Failed to reconnect to database")
            return

    # Try to interpret as command first
    command_executed = await context.bot_data['interpreter'](user_input, update, context)
    if command_executed:
        return

    # Automatic note detection with regex
    if re.search(r'\b(remember|note)\b', user_input.lower()):
        note_text = re.sub(r'\b(remember|note:?)\b', '', user_input, flags=re.IGNORECASE).strip()
        if note_text:
            try:
                # Save note and get its ID
                note_id = await db.add_note(chat_id, note_text)
                if note_id:
                    # Automatically categorize the note
                    categories = await categorize_note(context.bot_data['client'], note_text)
                    if categories:
                        await db.categorize_note(note_id, categories)
                        await update.message.reply_text(f"📝 I've saved this note under categories: {', '.join(categories)}")
                    else:
                        await update.message.reply_text("📝 I've saved this note but couldn't determine categories")
                else:
                    await update.message.reply_text("⚠️ Failed to save note automatically")
            except Exception as e:
                logger.error(f"Error auto-saving note: {e}")
                await update.message.reply_text("🚨 Error saving note automatically")

    context.chat_data['conversation'].append({"role": "user", "content": user_input})
    try:
        await context.bot.send_chat_action(chat_id=chat_id, action="typing")
        client = context.bot_data['client']
        completion = await client.chat.completions.create(
            model="deepseek-chat",
            messages=context.chat_data['conversation']
        )
        full_response = completion.choices[0].message.content

        response_parts = [full_response[i:i+4000] for i in range(0, len(full_response), 4000)]
        for part in response_parts:
            await update.message.reply_text(part)
            await asyncio.sleep(0.5)

        context.chat_data['conversation'].append({"role": "assistant", "content": full_response})
    except Exception as e:
        logger.error(f"Error in handle_message: {e}")
        await update.message.reply_text("🚨 Error processing your request")

async def handle_confirmation(update, context):
    """Handle command confirmation responses"""
    chat_id = update.effective_chat.id
    user_input = update.message.text.lower()
    
    if "pending_command" not in context.user_data:
        await update.message.reply_text("No pending command to confirm")
        return
        
    if user_input in ["yes", "y"]:
        command = context.user_data["pending_command"]
        del context.user_data["pending_command"]
        await context.bot_data['commands'][command[1:]](update, context)
    else:
        await update.message.reply_text("Command cancelled")
        del context.user_data["pending_command"]

async def find_related_notes(client, topic, notes):
    """Use LLM to find notes related to a specific topic"""
    try:
        note_list = "\n".join([f"- {content}" for _, content in notes])
        prompt = f"""Analyze these notes and return ONLY the IDs of notes related to '{topic}':
{note_list}

Return ONLY a comma-separated list of IDs, nothing else. If no notes are related, return 'none'."""
        
        completion = await client.chat.completions.create(
            model="deepseek-chat",
        return [int(id.strip()) for id in result.split(",")]
    except Exception as e:
        logger.error(f"Error finding related notes: {e}")
        return []

async def categorize_note(client, note_content):
    """Use LLM to generate categories for a note"""
    try:
        prompt = f"""Analyze this note and suggest 1-3 relevant categories. 
Return ONLY a comma-separated list of category names, nothing else.

Note content:
{note_content}

Categories:"""
        
        completion = await client.chat.completions.create(
            model="deepseek-chat",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.2
        )
        
        result = completion.choices[0].message.content.strip()
        return [cat.strip().lower() for cat in result.split(",")]
    except Exception as e:
        logger.error(f"Error categorizing note: {e}")
        return []
