import logging
from database import NoteDatabase

logger = logging.getLogger(__name__)

def start(app):
    app.conversation = [app.system_message]
    print("Hello! I'm your AI assistant. How can I help you today?")

def reset(app):
    app.conversation = [app.system_message]
    print("Conversation reset. How can I assist you?")

def help(app):
    help_text = """
Available commands:
start - Initialize new conversation
reset - Reset conversation history
help - List available commands
save <note> - Save a new note
notes - Show recent notes
remove_notes <topic> - Remove notes related to a topic
edit_notes <topic> <new_content> - Edit notes related to a topic
"""
    print(help_text)

def save_note(app, note_text=None):
    if not note_text:
        print("Please provide a note after the command\nExample: save Buy milk tomorrow")
        return
    
    try:
        success = app.db.add_note(0, note_text)  # Using 0 as default chat_id
        if success:
            print("📝 Note saved successfully!")
        else:
            print("⚠️ Failed to save note, please try again")
    except Exception as e:
        logger.error(f"Error saving note: {e}")
        print("🚨 Error saving note, please try again")

def show_notes(app):
    try:
        notes = app.db.get_notes(0)  # Using 0 as default chat_id
        if not notes:
            print("No notes found. Start saving with 'save'")
            return
        
        print("📒 Your Recent Notes:\n")
        for content, timestamp in notes:
            print(f"• {content}")
            print(f"  ({timestamp})\n")
    except Exception as e:
        logger.error(f"Error retrieving notes: {e}")
        print("🚨 Error retrieving notes, please try again")

def remove_notes(app, topic=None):
    """Remove notes related to a specific topic"""
    if not topic:
        print("Please specify a topic to remove notes about\nExample: remove_notes coffee")
        return
    
    try:
        # Get all notes and find related ones
        all_notes = app.db.get_all_notes(0)
        note_ids = find_related_notes(app.client, topic, all_notes)
        
        if not note_ids:
            print(f"No notes found related to '{topic}'")
            return
            
        # Show confirmation
        app.pending_command = ('execute_remove_notes', topic, note_ids)
        print(
            f"⚠️ Found {len(note_ids)} notes related to '{topic}'.\n"
            "Are you sure you want to delete them? (yes/no)"
        )
    except Exception as e:
        logger.error(f"Error removing notes: {e}")
        print("🚨 Error removing notes, please try again")

def edit_notes(app, args=None):
    """Edit notes related to a specific topic"""
    if not args or len(args) < 2:
        print(
            "Please specify a topic and new content\n"
            "Example: edit_notes coffee replace with tea"
        )
        return
    
    topic = args[0]
    new_content = ' '.join(args[1:])
    
    try:
        # Get all notes and find related ones
        all_notes = app.db.get_all_notes(0)
        note_ids = find_related_notes(app.client, topic, all_notes)
        
        if not note_ids:
            print(f"No notes found related to '{topic}'")
            return
            
        # Show confirmation
        app.pending_command = ('execute_edit_notes', topic, note_ids, new_content)
        print(
            f"⚠️ Found {len(note_ids)} notes related to '{topic}'.\n"
            f"Are you sure you want to update them to: '{new_content}'? (yes/no)"
        )
    except Exception as e:
        logger.error(f"Error editing notes: {e}")
        print("🚨 Error editing notes, please try again")

def execute_remove_notes(app, topic, note_ids):
    """Execute the removal of notes after confirmation"""
    success_count = 0
    for note_id in note_ids:
        if app.db.delete_note(note_id):
            success_count += 1
    
    print(f"✅ Removed {success_count}/{len(note_ids)} notes related to '{topic}'")

def execute_edit_notes(app, topic, note_ids, new_content):
    """Execute the editing of notes after confirmation"""
    success_count = 0
    for note_id in note_ids:
        if app.db.update_note(note_id, new_content):
            success_count += 1
    
    print(f"✅ Updated {success_count}/{len(note_ids)} notes related to '{topic}'")