import sqlite3
import json
from datetime import datetime, timedelta

class Database:
    def __init__(self):
        self.conn = sqlite3.connect('ghost_flux.db', check_same_thread=False)
        self.create_tables()
    
    def create_tables(self):
        cursor = self.conn.cursor()
        
        # Пользователи
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                username TEXT,
                balance INTEGER DEFAULT 0,
                last_daily_bonus DATETIME,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Инвентарь
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS inventory (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                item_name TEXT,
                item_value INTEGER,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Выводы
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS withdrawals (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                username TEXT,
                item_name TEXT,
                item_value INTEGER,
                status TEXT DEFAULT 'pending',
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Транзакции
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS transactions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                type TEXT,
                amount INTEGER,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        self.conn.commit()
    
    def get_user(self, user_id):
        cursor = self.conn.cursor()
        cursor.execute('SELECT * FROM users WHERE user_id = ?', (user_id,))
        user = cursor.fetchone()
        if user:
            return {
                'user_id': user[0],
                'username': user[1],
                'balance': user[2],
                'last_daily_bonus': user[3]
            }
        return None
    
    def create_user(self, user_id, username):
        cursor = self.conn.cursor()
        cursor.execute(
            'INSERT OR IGNORE INTO users (user_id, username) VALUES (?, ?)',
            (user_id, username)
        )
        self.conn.commit()
    
    def update_balance(self, user_id, amount):
        cursor = self.conn.cursor()
        cursor.execute(
            'UPDATE users SET balance = balance + ? WHERE user_id = ?',
            (amount, user_id)
        )
        self.conn.commit()
    
    def add_to_inventory(self, user_id, item_name, item_value):
        cursor = self.conn.cursor()
        cursor.execute(
            'INSERT INTO inventory (user_id, item_name, item_value) VALUES (?, ?, ?)',
            (user_id, item_name, item_value)
        )
        self.conn.commit()
    
    def get_inventory(self, user_id):
        cursor = self.conn.cursor()
        cursor.execute(
            'SELECT * FROM inventory WHERE user_id = ? ORDER BY created_at DESC',
            (user_id,)
        )
        return cursor.fetchall()
    
    def create_withdrawal(self, user_id, username, item_name, item_value):
        cursor = self.conn.cursor()
        cursor.execute(
            'INSERT INTO withdrawals (user_id, username, item_name, item_value) VALUES (?, ?, ?, ?)',
            (user_id, username, item_name, item_value)
        )
        self.conn.commit()
        return cursor.lastrowid
    
    def get_pending_withdrawals(self):
        cursor = self.conn.cursor()
        cursor.execute('SELECT * FROM withdrawals WHERE status = "pending" ORDER BY created_at DESC')
        return cursor.fetchall()
    
    def update_withdrawal_status(self, withdrawal_id, status):
        cursor = self.conn.cursor()
        cursor.execute(
            'UPDATE withdrawals SET status = ? WHERE id = ?',
            (status, withdrawal_id)
        )
        self.conn.commit()