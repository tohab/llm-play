import sqlite3
from typing import Optional
import llm_handler

class Interpreter:
    def __init__(self, db_path: str = "notes.db"):
        self.conn = sqlite3.connect(db_path)
        self._init_db()

    def _init_db(self):
        """Initialize database with notes and categories tables if they don't exist"""
        cursor = self.conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS notes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                content TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS categories (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE
            )
        """)
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS note_category (
                note_id INTEGER NOT NULL,
                category_id INTEGER NOT NULL,
                PRIMARY KEY (note_id, category_id),
                FOREIGN KEY (note_id) REFERENCES notes(id),
                FOREIGN KEY (category_id) REFERENCES categories(id)
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
                return "Available commands:\n/save [note] - Save a note\n/list - List all notes\n/categories - List all categories"
            elif user_input.startswith('/categories'):
                return self._list_categories()
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

    def _get_category_for_note(self, note_content: str) -> str:
        """Determine the most relevant category for a note using LLM"""
        handler = llm_handler.LLMHandler()
        prompt = f"""Analyze this note and determine the single most relevant category:
        {note_content}
        
        Choose from these general categories or suggest a new specific one:
        - Work
        - Personal
        - Ideas
        - Reminders
        - Research
        - Code
        - Documentation
        
        Return only the category name:"""
        return handler.generate_response(prompt).strip()

    def _save_note(self, input_text: str) -> str:
        """Save note to database with automatic categorization"""
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
        
        # Get category and save note
        category = self._get_category_for_note(processed_note)
        cursor = self.conn.cursor()
        
        # Save note
        cursor.execute("INSERT INTO notes (content) VALUES (?)", (processed_note,))
        note_id = cursor.lastrowid
        
        # Save category
        cursor.execute("INSERT OR IGNORE INTO categories (name) VALUES (?)", (category,))
        cursor.execute("SELECT id FROM categories WHERE name = ?", (category,))
        category_id = cursor.fetchone()[0]
        
        # Link note to category
        cursor.execute("INSERT INTO note_category (note_id, category_id) VALUES (?, ?)", 
                      (note_id, category_id))
        
        self.conn.commit()
        return f"Note saved in category '{category}': {processed_note}"

    def _list_notes(self) -> str:
        """List all notes with their categories"""
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT n.content, c.name 
            FROM notes n
            JOIN note_category nc ON n.id = nc.note_id
            JOIN categories c ON nc.category_id = c.id
            ORDER BY n.created_at DESC
        """)
        notes = cursor.fetchall()
        
        if not notes:
            return "No notes found"
            
        return "\n".join(f"- [{category}] {content}" 
                        for content, category in notes)

    def _generate_response(self, input_text: str) -> str:
        """Generate response using LLM"""
        handler = llm_handler.LLMHandler()
        return handler.generate_response(input_text)

    def _list_categories(self) -> str:
        """List all categories and their note counts"""
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT c.name, COUNT(nc.note_id) as note_count
            FROM categories c
            LEFT JOIN note_category nc ON c.id = nc.category_id
            GROUP BY c.name
            ORDER BY note_count DESC
        """)
        categories = cursor.fetchall()
        
        if not categories:
            return "No categories found"
            
        return "\n".join(f"- {name} ({count} notes)" 
                        for name, count in categories)

    def __del__(self):
        self.conn.close()
