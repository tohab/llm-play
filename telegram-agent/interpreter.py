import re
import logging
from database import NoteDatabase

logger = logging.getLogger(__name__)

async def interpret_command(user_input: str, update, context) -> bool:
    """Interpret natural language commands and execute matching commands"""
    prompt = f"""Analyze this user input and determine if it matches any command purpose.
User Input: "{user_input}"

Available Commands (with examples):
- /start: ("start", "begin chat", "hello", "hi")
- /reset: ("reset", "clear", "start over")
- /help: ("help", "commands", "what can you do?")
- /save: ("save note", "remember to...", "note this...", "please save this...")
- /notes: ("show me my notes", "what notes do I have?", "retrieve my notes", "list notes")
- /remove_notes: ("delete notes about...", "remove all... notes", "clear notes related to...")
- /edit_notes: ("change notes about...", "update... notes to...", "modify notes related to...")

If the input is semantically similar to these examples, respond "True". Otherwise "False"."""
    
    try:
        client = context.bot_data['client']
        completion = await client.chat.completions.create(
            model="deepseek-chat",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.2
        )

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
- /remove_notes
- /edit_notes

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
                    db = context.bot_data['db']
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
                "/start": context.bot_data['commands']['start'],
                "/reset": context.bot_data['commands']['reset'],
                "/help": context.bot_data['commands']['help'],
                "/notes": context.bot_data['commands']['show_notes'],
                "/remove_notes": context.bot_data['commands']['remove_notes'],
                "/edit_notes": context.bot_data['commands']['edit_notes']
            }
            
            if cmd_str in handlers:
                await handlers[cmd_str](update, context)
                return True
            
        return False
    except Exception as e:
        logger.error(f"Error in interpret_command: {e}")
        return False
