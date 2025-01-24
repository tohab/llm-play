import os
import logging
from dotenv import load_dotenv
from openai import OpenAI
from database import NoteDatabase
from commands import start, reset, help, save_note, show_notes, remove_notes, execute_remove_notes, edit_notes, execute_edit_notes
from interpreter import interpret_command as interpret_command_fn
from llm_handler import handle_message as handle_message_fn, handle_confirmation, SYSTEM_MESSAGE

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

class CLIApp:
    def __init__(self):
        # Load environment variables
        load_dotenv()

        # Initialize services
        self.db = NoteDatabase()
        self.client = OpenAI(
            api_key=os.getenv("DEEPSEEK_API_KEY"),
            base_url="https://api.deepseek.com"
        )

        # Store shared resources
        self.commands = {
            'start': start,
            'reset': reset,
            'help': help,
            'save': save_note,
            'notes': show_notes,
            'remove_notes': remove_notes,
            'execute_remove_notes': execute_remove_notes,
            'edit_notes': edit_notes,
            'execute_edit_notes': execute_edit_notes
        }
        self.system_message = SYSTEM_MESSAGE
        self.conversation = [SYSTEM_MESSAGE]
        self.pending_command = None

    def interpret_command(self, user_input: str) -> bool:
        """Interpret natural language commands and execute matching commands"""
        return interpret_command_fn(user_input, self)

    def handle_message(self, user_input: str):
        """Handle regular message input"""
        return handle_message_fn(user_input, self)

    def handle_confirmation(self, user_input: str):
        """Handle command confirmation input"""
        return handle_confirmation(user_input, self)

    def run(self):
        print("CLI Note Assistant - Type 'help' for commands")
        while True:
            try:
                user_input = input("> ").strip()
                if not user_input:
                    continue

                # Handle pending command confirmation
                if self.pending_command:
                    self.handle_confirmation(user_input)
                    continue

                # Try to interpret as command first
                if self.interpret_command(user_input):
                    continue

                # Handle regular message
                self.handle_message(user_input)

            except KeyboardInterrupt:
                print("\nExiting...")
                break
            except Exception as e:
                logger.error(f"Error: {e}")
                print("An error occurred, please try again")

if __name__ == "__main__":
    app = CLIApp()
    app.run()