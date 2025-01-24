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
        if user_input.startswith("/save"):
            return self._save_note(user_input)
        elif user_input.startswith("/list"):
            return self._list_notes()
        else:
            return self._generate_response(user_input)

    def _save_note(self, input_text: str) -> str:
        """Save note to database"""
        note_content = input_text[len("/save"):].strip()
        if not note_content:
            return "Error: No content provided after /save"

        cursor = self.conn.cursor()
        cursor.execute("INSERT INTO notes (content) VALUES (?)", (note_content,))
        self.conn.commit()
        return f"Note saved: {note_content}"

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
