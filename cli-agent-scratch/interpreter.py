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
                formatted_content TEXT NOT NULL,
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
        # Handle confirmation responses first
        if user_input.lower() in ('yes', 'no'):
            if hasattr(self, '_pending_delete_ids'):
                if user_input.lower() == 'yes':
                    result = self._confirm_delete(self._pending_delete_ids)
                    del self._pending_delete_ids
                    return result
                else:
                    del self._pending_delete_ids
                    return "Delete cancelled"
        
        # Check for commands first
        if user_input.startswith('/'):
            if user_input.startswith('/save'):
                return self._save_note(user_input)
            elif user_input.startswith('/list'):
                return self._list_notes()
            elif user_input.startswith('/help'):
                return "Available commands:\n/save [note] - Save a note\n/list - List all notes\n/categories - List all categories\n/delete [query] - Delete notes matching query"
            elif user_input.startswith('/categories'):
                return self._list_categories()
            elif user_input.startswith('/delete'):
                return self._delete_notes(user_input)
            else:
                return "Unknown command. Type /help for available commands"
            
        # Check for natural language note commands
        intent = self._classify_intent(user_input)
        if intent == "save_note":
            return self._save_note(f"/save {user_input}")
        elif intent == "list_notes":
            return self._list_notes()
        elif intent == "delete_notes":
            return self._delete_notes(f"/delete {self._extract_delete_query(user_input)}")
            
        # Only use LLM for non-note related inputs
        return self._generate_response(user_input)

    def _extract_delete_query(self, user_input: str) -> str:
        """Extract the query portion from natural language delete requests"""
        handler = llm_handler.LLMHandler()
        prompt = f"""Extract the query portion from this delete request:
        Input: {user_input}
        
        Examples:
        - "delete notes about cats" → "cats"
        - "get rid of all work-related notes" → "work"
        - "remove notes containing meeting notes" → "meeting notes"
        
        Return only the extracted query:"""
        return handler.generate_response(prompt).strip()

    def _classify_intent(self, user_input: str) -> str:
        """Classify user intent using LLM"""
        handler = llm_handler.LLMHandler()
        prompt = f"""Classify the user's intent from their input:
        Input: {user_input}
        
        Possible intents:
        - save_note: User wants to save a note (phrases like: remember this, save this, make a note, jot this down)
        - list_notes: User wants to list all notes (phrases like: show notes, show me what you remember, what have we discussed, list my notes)
        - delete_notes: User wants to delete notes (phrases like: delete X note, get rid of notes about X, remove notes containing Y, clear all notes about Z)
        - other: General conversation
        
        Return only the intent name (save_note, list_notes, delete_notes, or other)"""
        
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

    def _format_note(self, note_content: str) -> str:
        """Format note content to improve grammar, spelling and cohesion"""
        handler = llm_handler.LLMHandler()
        prompt = f"""Please format this note to improve its grammar, spelling and cohesion:
        {note_content}
        
        Rules:
        - Fix any spelling and grammar errors
        - Make sentences more clear and concise
        - Maintain the original meaning
        - Keep the same overall structure
        - Return only the formatted note"""
        return handler.generate_response(prompt).strip()

    def _save_note(self, input_text: str) -> str:
        """Save note to database with automatic categorization"""
        note_content = input_text[len("/save"):].strip()
        if not note_content:
            return "Error: No content provided after /save"

        # Store note as plain text without formatting
        processed_note = note_content.strip()
        
        # Get category and save note
        category = self._get_category_for_note(processed_note)
        cursor = self.conn.cursor()
        
        # Format note
        formatted_note = self._format_note(processed_note)
        
        # Save note with both raw and formatted content
        cursor.execute("""
            INSERT INTO notes (content, formatted_content) 
            VALUES (?, ?)
        """, (processed_note, formatted_note))
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
        """List all notes sorted by category"""
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT c.name, n.content
            FROM notes n
            JOIN note_category nc ON n.id = nc.note_id
            JOIN categories c ON nc.category_id = c.id
            ORDER BY c.name ASC, n.created_at DESC
        """)
        notes = cursor.fetchall()
        
        if not notes:
            return "No notes found"
            
        # Group notes by category
        categorized_notes = {}
        for category, content in notes:
            if category not in categorized_notes:
                categorized_notes[category] = []
            categorized_notes[category].append(content)
            
        # Format output with category headings
        output = []
        for category, contents in sorted(categorized_notes.items()):
            output.append(f"[{category}]")
            output.extend(f"- {content}" for content in contents)
            output.append("")  # Add blank line between categories
            
        return "\n".join(output)

    def _generate_response(self, input_text: str) -> str:
        """Generate response using LLM"""
        handler = llm_handler.LLMHandler()
        return handler.generate_response(input_text)

    def _delete_notes(self, input_text: str) -> str:
        """Delete notes matching the given query after confirmation"""
        query = input_text[len("/delete"):].strip()
        if not query:
            return "Error: No query provided after /delete"

        # Find matching notes
        cursor = self.conn.cursor()
        cursor.execute("SELECT id, content FROM notes")
        all_notes = cursor.fetchall()
        
        # Use LLM to find relevant notes
        handler = llm_handler.LLMHandler()
        prompt = f"""Given these notes and a query, return only the IDs of notes that should be deleted:
        Query: {query}
        Notes:
        {all_notes}
        
        Return only a comma-separated list of IDs to delete, or 'none' if no matches found"""
        
        response = handler.generate_response(prompt).strip()
        if response.lower() == 'none':
            return "No matching notes found"
            
        try:
            self._pending_delete_ids = [int(id_str) for id_str in response.split(',')]
        except ValueError:
            return "Error: Invalid response from LLM"
            
        # Get note contents for confirmation
        cursor.execute("SELECT id, content FROM notes WHERE id IN ({})".format(
            ','.join('?' for _ in self._pending_delete_ids)), self._pending_delete_ids)
        matching_notes = cursor.fetchall()
        
        if not matching_notes:
            return "No matching notes found"
            
        # Show confirmation prompt
        notes_list = "\n".join(f"- {content}" for _, content in matching_notes)
        return f"Do you want to delete these notes?\n{notes_list}\n\nType 'yes' to confirm or 'no' to cancel"

    def _confirm_delete(self, note_ids: list[int]) -> str:
        """Actually delete the notes after confirmation"""
        cursor = self.conn.cursor()
        cursor.execute("DELETE FROM notes WHERE id IN ({})".format(
            ','.join('?' for _ in note_ids)), note_ids)
        cursor.execute("DELETE FROM note_category WHERE note_id IN ({})".format(
            ','.join('?' for _ in note_ids)), note_ids)
        self.conn.commit()
        return f"Deleted {len(note_ids)} notes"

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
