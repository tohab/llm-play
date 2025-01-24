import re
import logging
from database import NoteDatabase
from interpreter import interpret_command, execute_command, CommandDecision

logger = logging.getLogger(__name__)

SYSTEM_MESSAGE = {
    "role": "system",
    "content": """You are a helpful AI assistant. Your tasks include:
1. Analyze user input to determine if it should be handled as a command or chat response
2. Execute commands automatically when appropriate
3. Provide helpful responses to general messages

The system will automatically determine the best way to handle each message."""
}

def handle_message(user_input, app):
    """Handle incoming messages and route to appropriate handler"""
    if 'conversation' not in app.conversation:
        app.conversation = [app.system_message]

    # Database connection check
    if not app.db.verify_connection():
        print("⚠️ Database connection issue, trying to reconnect...")
        app.db = NoteDatabase()
        if not app.db.verify_connection():
            print("❌ Failed to reconnect to database")
            return

    # Get interpreter decision
    decision = interpret_command(user_input, app)
    
    # Handle command execution
    if decision.should_execute_command:
        if execute_command(decision, app):
            return
        # If command execution fails, fall through to chat response

    # Handle chat response
    if decision.chat_response:
        print(decision.chat_response)
        app.conversation.append({"role": "assistant", "content": decision.chat_response})
        return

    # Default chat handling
    app.conversation.append({"role": "user", "content": user_input})
    try:
        completion = app.client.chat.completions.create(
            model="deepseek-chat",
            messages=app.conversation
        )
        full_response = completion.choices[0].message.content
        print(full_response)
        app.conversation.append({"role": "assistant", "content": full_response})
    except Exception as e:
        logger.error(f"Error in handle_message: {e}")
        if "401" in str(e):
            print("🔑 Authentication failed - please check your API key")
        elif "404" in str(e):
            print("🌐 API endpoint not found - please check your base URL")
        else:
            print(f"🚨 Error processing your request: {str(e)}")

def handle_confirmation(user_input, app):
    """Handle command confirmation responses"""
    if not hasattr(app, 'pending_command') or not app.pending_command:
        print("No pending command to confirm")
        return
        
    if user_input.lower() in ["yes", "y"]:
        command = app.pending_command
        del app.pending_command
        app.commands[command[0]](app, *command[1:])
    else:
        print("Command cancelled")
        del app.pending_command

def find_related_notes(client, topic, notes):
    """Use LLM to find notes related to a specific topic"""
    try:
        note_list = "\n".join([f"- {content}" for _, content in notes])
        prompt = f"""Analyze these notes and return ONLY the IDs of notes related to '{topic}':
{note_list}

Return ONLY a comma-separated list of IDs, nothing else. If no notes are related, return 'none'."""
        
        completion = client.chat.completions.create(
            model="deepseek-chat",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.2
        )
        
        result = completion.choices[0].message.content.strip()
        if result.lower() == "none":
            return []
        return [int(id.strip()) for id in result.split(",")]
    except Exception as e:
        logger.error(f"Error finding related notes: {e}")
        return []