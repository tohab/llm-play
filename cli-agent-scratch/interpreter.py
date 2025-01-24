import sqlite3
from typing import Optional
import llm_handler

class Interpreter:
    def __init__(self, db_path: str = "notes.db"):
        self.conn = sqlite3.connect(db_path)
        self._init_db()

    def _init_db(self):
        """Initialize database with notes table if it doesn't exist"""
        cursor = self.conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS notes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                content TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        self.conn.commit()

    def handle_input(self, user_input: str) -> str:
        """Process user input and return appropriate response"""
        # Check for commands first
        if user_input.startswith('/'):
            if user_input.startswith('/save'):
                return self._save_note(user_input)
            elif user_input.startswith('/list'):
                return self._list_notes()
            elif user_input.startswith('/help'):
                return "Available commands:\n/save [note] - Save a note\n/list - List all notes"
            else:
                return "Unknown command. Type /help for available commands"
            
        # Check for natural language note commands
        intent = self._classify_intent(user_input)
        if intent == "save_note":
            return self._save_note(f"/save {user_input}")
        elif intent == "list_notes":
            return self._list_notes()
            
        # Only use LLM for non-note related inputs
        return self._generate_response(user_input)

    def _classify_intent(self, user_input: str) -> str:
        """Classify user intent using LLM"""
        handler = llm_handler.LLMHandler()
        prompt = f"""Classify the user's intent from their input:
        Input: {user_input}
        
        Possible intents:
        - save_note: User wants to save a note (phrases like: remember this, save this, make a note, jot this down)
        - list_notes: User wants to list all notes (phrases like: show notes, show me what you remember, what have we discussed, list my notes)
        - other: General conversation
        
        Return only the intent name (save_note, list_notes, or other)"""
        
        response = handler.generate_response(prompt)
        return response.strip().lower()

    def _save_note(self, input_text: str) -> str:
        """Save note to database"""
        note_content = input_text[len("/save"):].strip()
        if not note_content:
            return "Error: No content provided after /save"

        # Use LLM to process and clean up the note
        handler = llm_handler.LLMHandler()
        prompt = f"""Please process this note to make it more coherent and organized:
        - Remove unnecessary filler words
        - Fix grammar and punctuation
        - Make it concise but preserve meaning
        - Format lists and bullet points consistently
        
        Original note: {note_content}
        
        Return only the cleaned up note content:"""
        
        processed_note = handler.generate_response(prompt).strip()
        
        cursor = self.conn.cursor()
        cursor.execute("INSERT INTO notes (content) VALUES (?)", (processed_note,))
        self.conn.commit()
        return f"Note saved: {processed_note}"

    def _list_notes(self) -> str:
        """List all notes from database"""
        cursor = self.conn.cursor()
        cursor.execute("SELECT content FROM notes ORDER BY created_at DESC")
        notes = cursor.fetchall()
        
        if not notes:
            return "No notes found"
            
        return "\n- " + "\n- ".join(note[0] for note in notes)

    def _generate_response(self, input_text: str) -> str:
        """Generate response using LLM"""
        handler = llm_handler.LLMHandler()
        return handler.generate_response(input_text)

    def __del__(self):
        self.conn.close()
