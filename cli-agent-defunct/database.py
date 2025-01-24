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
        """Create notes table if it doesn't exist"""
        with self._get_connection() as conn:
            conn.execute('''
                CREATE TABLE IF NOT EXISTS notes
                (id INTEGER PRIMARY KEY, 
                 chat_id INTEGER, 
                 content TEXT,
                 created_at DATETIME)
            ''')

    def add_note(self, chat_id, content):
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

    def get_notes(self, chat_id, limit=10):
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

    def get_all_notes(self, chat_id):
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

    def delete_note(self, note_id):
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

    def update_note(self, note_id, new_content):
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
