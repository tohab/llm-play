import logging
from database import NoteDatabase

logger = logging.getLogger(__name__)

async def start(update, context):
    chat_id = update.effective_chat.id
    context.chat_data['conversation'] = [context.bot_data['system_message']]
    await update.message.reply_text("Hello! I'm your AI assistant. How can I help you today?")

async def reset(update, context):
    chat_id = update.effective_chat.id
    context.chat_data['conversation'] = [context.bot_data['system_message']]
    await update.message.reply_text("Conversation reset. How can I assist you?")

async def help(update, context):
    help_text = """
Available commands:
/start - Initialize new conversation
/reset - Reset conversation history
/save <note> - Save a new note
/notes - Show recent notes
/remove_notes <topic> - Remove notes related to a topic
/edit_notes <topic> <new_content> - Edit notes related to a topic
/help - List all available commands
"""
    await update.message.reply_text(help_text)

async def save_note(update, context):
    chat_id = update.effective_chat.id
    note_text = ' '.join(context.args)
    
    if not note_text:
        await update.message.reply_text("Please provide a note after the command\nExample: /save Buy milk tomorrow")
        return
    
    try:
        db = context.bot_data['db']
        success = await db.add_note(chat_id, note_text)
        if success:
            await update.message.reply_text("📝 Note saved successfully!")
        else:
            await update.message.reply_text("⚠️ Failed to save note, please try again")
    except Exception as e:
        logger.error(f"Error saving note: {e}")
        await update.message.reply_text("🚨 Error saving note, please try again")

async def show_notes(update, context):
    chat_id = update.effective_chat.id
    try:
        db = context.bot_data['db']
        notes = await db.get_notes(chat_id)
        if not notes:
            await update.message.reply_text("No notes found. Start saving with /save")
            return
        
        response = "📒 Your Recent Notes:\n\n"
        for content, timestamp in notes:
            response += f"• {content}\n  ({timestamp})\n\n"
        
        await update.message.reply_text(response)
    except Exception as e:
        logger.error(f"Error retrieving notes: {e}")
        await update.message.reply_text("🚨 Error retrieving notes, please try again")

async def remove_notes(update, context):
    """Remove notes related to a specific topic"""
    chat_id = update.effective_chat.id
    topic = ' '.join(context.args)
    
    if not topic:
        await update.message.reply_text("Please specify a topic to remove notes about\nExample: /remove_notes coffee")
        return
    
    try:
        db = context.bot_data['db']
        client = context.bot_data['client']
        
        # Get all notes and find related ones
        all_notes = await db.get_all_notes(chat_id)
        note_ids = await context.bot_data['llm_handler'].find_related_notes(client, topic, all_notes)
        
        if not note_ids:
            await update.message.reply_text(f"No notes found related to '{topic}'")
            return
            
        # Show confirmation
        context.user_data['pending_command'] = ('/remove_notes', topic, note_ids)
        await update.message.reply_text(
            f"⚠️ Found {len(note_ids)} notes related to '{topic}'. "
            "Are you sure you want to delete them? (yes/no)"
        )
    except Exception as e:
        logger.error(f"Error removing notes: {e}")
        await update.message.reply_text("🚨 Error removing notes, please try again")

async def edit_notes(update, context):
    """Edit notes related to a specific topic"""
    chat_id = update.effective_chat.id
    if len(context.args) < 2:
        await update.message.reply_text(
            "Please specify a topic and new content\n"
            "Example: /edit_notes coffee replace with tea"
        )
        return
    
    topic = context.args[0]
    new_content = ' '.join(context.args[1:])
    
    try:
        db = context.bot_data['db']
        client = context.bot_data['client']
        
        # Get all notes and find related ones
        all_notes = await db.get_all_notes(chat_id)
        note_ids = await context.bot_data['llm_handler'].find_related_notes(client, topic, all_notes)
        
        if not note_ids:
            await update.message.reply_text(f"No notes found related to '{topic}'")
            return
            
        # Show confirmation
        context.user_data['pending_command'] = ('/edit_notes', topic, note_ids, new_content)
        await update.message.reply_text(
            f"⚠️ Found {len(note_ids)} notes related to '{topic}'. "
            f"Are you sure you want to update them to: '{new_content}'? (yes/no)"
        )
    except Exception as e:
        logger.error(f"Error editing notes: {e}")
        await update.message.reply_text("🚨 Error editing notes, please try again")

async def execute_remove_notes(update, context):
    """Execute the removal of notes after confirmation"""
    _, topic, note_ids = context.user_data['pending_command']
    db = context.bot_data['db']
    
    success_count = 0
    for note_id in note_ids:
        if await db.delete_note(note_id):
            success_count += 1
    
    await update.message.reply_text(
        f"✅ Removed {success_count}/{len(note_ids)} notes related to '{topic}'"
    )

async def execute_edit_notes(update, context):
    """Execute the editing of notes after confirmation"""
    _, topic, note_ids, new_content = context.user_data['pending_command']
    db = context.bot_data['db']
    
    success_count = 0
    for note_id in note_ids:
        if await db.update_note(note_id, new_content):
            success_count += 1
    
    await update.message.reply_text(
        f"✅ Updated {success_count}/{len(note_ids)} notes related to '{topic}'"
    )
