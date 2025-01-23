import sqlite3
from datetime import datetime

class NoteDatabase:
    def __init__(self, db_name='notes.db'):
        self.conn = sqlite3.connect(db_name)
        self._create_table()

    def _create_table(self):
        self.conn.execute('''
            CREATE TABLE IF NOT EXISTS notes
            (id INTEGER PRIMARY KEY, 
             chat_id INTEGER, 
             content TEXT,
             created_at DATETIME)
        ''')
        self.conn.commit()

    async def add_note(self, chat_id, content):
        self.conn.execute(
            'INSERT INTO notes (chat_id, content, created_at) VALUES (?, ?, ?)',
            (chat_id, content, datetime.now())
        )
        self.conn.commit()

    async def get_notes(self, chat_id, limit=10):
        cursor = self.conn.execute(
            '''SELECT content, created_at 
               FROM notes 
               WHERE chat_id = ? 
               ORDER BY created_at DESC 
               LIMIT ?''',
            (chat_id, limit)
        )
        return cursor.fetchall()

    def close(self):
        self.conn.close()