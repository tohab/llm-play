import sqlite3
from datetime import datetime
from contextlib import contextmanager
import logging

logger = logging.getLogger(__name__)

class NoteDatabase:
    def __init__(self, db_name='notes.db'):
        self.db_name = db_name
        self._create_table()
        
    @contextmanager
    def _get_connection(self):
        """Context manager for database connections"""
        conn = sqlite3.connect(self.db_name)
        conn.execute("PRAGMA journal_mode=WAL")
        try:
            yield conn
            conn.commit()
        except sqlite3.Error as e:
            logger.error(f"Database error: {e}")
            conn.rollback()
            raise
        finally:
            conn.close()

    def _create_table(self):
        """Create notes and categories tables if they don't exist"""
        with self._get_connection() as conn:
            # Create notes table
            conn.execute('''
                CREATE TABLE IF NOT EXISTS notes
                (id INTEGER PRIMARY KEY, 
                 chat_id INTEGER, 
                 content TEXT,
                 created_at DATETIME)
            ''')
            
            # Create categories table
            conn.execute('''
                CREATE TABLE IF NOT EXISTS categories
                (id INTEGER PRIMARY KEY,
                 name TEXT UNIQUE)
            ''')
            
            # Create note_category join table
            conn.execute('''
                CREATE TABLE IF NOT EXISTS note_category
                (note_id INTEGER,
                 category_id INTEGER,
                 PRIMARY KEY (note_id, category_id),
                 FOREIGN KEY (note_id) REFERENCES notes(id),
                 FOREIGN KEY (category_id) REFERENCES categories(id))
            ''')

    async def add_note(self, chat_id, content):
        """Add a new note with automatic retry on failure"""
        max_retries = 3
        for attempt in range(max_retries):
            try:
                with self._get_connection() as conn:
                    conn.execute(
                        'INSERT INTO notes (chat_id, content, created_at) VALUES (?, ?, ?)',
                        (chat_id, content.strip(), datetime.now())
                    )
                    return True
            except sqlite3.Error as e:
                logger.warning(f"Failed to add note (attempt {attempt + 1}): {e}")
                if attempt == max_retries - 1:
                    raise
        return False

    async def get_notes(self, chat_id, limit=10):
        """Get notes with connection pooling and error handling"""
        try:
            with self._get_connection() as conn:
                cursor = conn.execute(
                    '''SELECT content, created_at 
                       FROM notes 
                       WHERE chat_id = ? 
                       ORDER BY created_at DESC 
                       LIMIT ?''',
                    (chat_id, limit)
                )
                return cursor.fetchall()
        except sqlite3.Error as e:
            logger.error(f"Error getting notes: {e}")
            return []

    def verify_connection(self):
        """Verify database connection is working"""
        try:
            with self._get_connection() as conn:
                conn.execute("SELECT 1")
            return True
        except sqlite3.Error:
            return False

    async def get_all_notes(self, chat_id):
        """Get all notes for a chat"""
        try:
            with self._get_connection() as conn:
                cursor = conn.execute(
                    '''SELECT id, content 
                       FROM notes 
                       WHERE chat_id = ? 
                       ORDER BY created_at DESC''',
                    (chat_id,)
                )
                return cursor.fetchall()
        except sqlite3.Error as e:
            logger.error(f"Error getting all notes: {e}")
            return []

    async def delete_note(self, note_id):
        """Delete a note by ID"""
        try:
            with self._get_connection() as conn:
                conn.execute(
                    'DELETE FROM notes WHERE id = ?',
                    (note_id,)
                )
                return True
        except sqlite3.Error as e:
            logger.error(f"Error deleting note: {e}")
            return False

    async def update_note(self, note_id, new_content):
        """Update a note's content"""
        try:
            with self._get_connection() as conn:
                conn.execute(
                    'UPDATE notes SET content = ? WHERE id = ?',
                    (new_content.strip(), note_id)
                )
                return True
        except sqlite3.Error as e:
            logger.error(f"Error updating note: {e}")
            return False

    async def get_or_create_category(self, name):
        """Get or create a category by name"""
        try:
            with self._get_connection() as conn:
                # Try to get existing category
                cursor = conn.execute(
                    'SELECT id FROM categories WHERE name = ?',
                    (name.lower(),)
                )
                result = cursor.fetchone()
                
                if result:
                    return result[0]
                
                # Create new category
                cursor = conn.execute(
                    'INSERT INTO categories (name) VALUES (?)',
                    (name.lower(),)
                )
                return cursor.lastrowid
        except sqlite3.Error as e:
            logger.error(f"Error getting/creating category: {e}")
            return None

    async def categorize_note(self, note_id, category_names):
        """Categorize a note with given categories"""
        try:
            with self._get_connection() as conn:
                # Remove existing categories for this note
                conn.execute(
                    'DELETE FROM note_category WHERE note_id = ?',
                    (note_id,)
                )
                
                # Add new categories
                for category_name in category_names:
                    category_id = await self.get_or_create_category(category_name)
                    if category_id:
                        conn.execute(
                            'INSERT INTO note_category (note_id, category_id) VALUES (?, ?)',
                            (note_id, category_id)
                        )
                return True
        except sqlite3.Error as e:
            logger.error(f"Error categorizing note: {e}")
            return False

    async def get_notes_by_category(self, chat_id, category_name):
        """Get notes belonging to a specific category"""
        try:
            with self._get_connection() as conn:
                cursor = conn.execute('''
                    SELECT n.id, n.content 
                    FROM notes n
                    JOIN note_category nc ON n.id = nc.note_id
                    JOIN categories c ON nc.category_id = c.id
                    WHERE n.chat_id = ? AND c.name = ?
                    ORDER BY n.created_at DESC
                ''', (chat_id, category_name.lower()))
                return cursor.fetchall()
        except sqlite3.Error as e:
            logger.error(f"Error getting notes by category: {e}")
            return []

    async def get_all_categories(self, chat_id):
        """Get all categories used by a chat"""
        try:
            with self._get_connection() as conn:
                cursor = conn.execute('''
                    SELECT DISTINCT c.name 
                    FROM categories c
                    JOIN note_category nc ON c.id = nc.category_id
                    JOIN notes n ON nc.note_id = n.id
                    WHERE n.chat_id = ?
                    ORDER BY c.name
                ''', (chat_id,))
                return [row[0] for row in cursor.fetchall()]
        except sqlite3.Error as e:
            logger.error(f"Error getting categories: {e}")
            return []
