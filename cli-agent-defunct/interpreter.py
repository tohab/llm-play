from dataclasses import dataclass
from typing import Optional
import logging
import json

logger = logging.getLogger(__name__)

@dataclass
class CommandDecision:
    """Represents the interpreter's decision about how to handle user input"""
    should_execute_command: bool
    command_name: Optional[str] = None
    command_args: Optional[list] = None
    chat_response: Optional[str] = None

def interpret_command(user_input: str, app) -> CommandDecision:
    """
    Analyze user input and decide whether to execute a command or provide a chat response.
    Returns a CommandDecision object with the interpreter's decision.
    """
    decision_prompt = f"""Analyze this user input and decide how to handle it:
User Input: "{user_input}"

Available Commands:
- start: Initialize new conversation
- reset: Reset conversation history
- help: List available commands
- save: Save a new note to memory
- notes: Retrieve and display saved notes
- remove_notes: Delete specific notes
- edit_notes: Modify existing notes

Decision Rules:
1. If the input clearly matches a command's purpose, choose to execute that command
2. If the input is ambiguous but could be a command, ask for clarification
3. If the input is clearly a general message, provide a chat response

Respond in JSON format with:
- should_execute_command: boolean
- command_name: string or null
- command_args: array or null
- chat_response: string or null"""

    try:
        completion = app.client.chat.completions.create(
            model="deepseek-chat",
            messages=[{"role": "user", "content": decision_prompt}],
            response_format={"type": "json_object"},
            temperature=0.2
        )

        decision_data = completion.choices[0].message.content
        try:
            decision_dict = json.loads(decision_data)
            return CommandDecision(**decision_dict)
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON response: {decision_data}")
            return CommandDecision(
                should_execute_command=False,
                chat_response="Sorry, I had trouble understanding your request."
            )

    except Exception as e:
        logger.error(f"Error in interpret_command: {e}")
        return CommandDecision(
            should_execute_command=False,
            chat_response="Sorry, I encountered an error processing your request."
        )

def execute_command(decision: CommandDecision, app) -> bool:
    """Execute the command specified in the CommandDecision"""
    if not decision.should_execute_command or not decision.command_name:
        return False

    handlers = {
        "start": app.commands['start'],
        "reset": app.commands['reset'],
        "help": app.commands['help'],
        "save": lambda app: app.commands['save'](app, *decision.command_args),
        "notes": app.commands['notes'],
        "remove_notes": lambda app: app.commands['remove_notes'](app, *decision.command_args),
        "edit_notes": lambda app: app.commands['edit_notes'](app, *decision.command_args)
    }

    if decision.command_name in handlers:
        try:
            handlers[decision.command_name](app)
            return True
        except Exception as e:
            logger.error(f"Error executing command {decision.command_name}: {e}")
            return False

    return False