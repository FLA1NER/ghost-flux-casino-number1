from flask import Flask, request, jsonify
from flask_cors import CORS
import sqlite3
import random
import logging
from datetime import datetime, timedelta
import json

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = Flask(__name__)
CORS(app)

# Конфигурация игры
ROULETTE_ITEMS = [
    {"name": "Мишка", "value": 15, "chance": 35, "emoji": "🧸"},
    {"name": "Сердечко", "value": 15, "chance": 35, "emoji": "💖"},
    {"name": "Ракета", "value": 50, "chance": 10, "emoji": "🚀"},
    {"name": "Торт", "value": 50, "chance": 10, "emoji": "🎂"},
    {"name": "Кубок", "value": 100, "chance": 5, "emoji": "🏆"},
    {"name": "Кольцо", "value": 100, "chance": 5, "emoji": "💍"}
]

DAILY_BONUS = [
    {"stars": 5, "chance": 70},
    {"stars": 10, "chance": 15},
    {"stars": 25, "chance": 10},
    {"stars": 50, "chance": 5}
]

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
                description TEXT,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Игровые статистики
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS game_stats (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                spins_count INTEGER DEFAULT 0,
                total_won INTEGER DEFAULT 0,
                last_spin DATETIME,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        self.conn.commit()
        logger.info("Database tables created successfully")
    
    def get_user(self, user_id):
        cursor = self.conn.cursor()
        cursor.execute('SELECT * FROM users WHERE user_id = ?', (user_id,))
        user = cursor.fetchone()
        if user:
            return {
                'user_id': user[0],
                'username': user[1],
                'balance': user[2],
                'last_daily_bonus': user[3],
                'created_at': user[4]
            }
        return None
    
    def create_user(self, user_id, username):
        cursor = self.conn.cursor()
        try:
            cursor.execute(
                'INSERT OR IGNORE INTO users (user_id, username) VALUES (?, ?)',
                (user_id, username)
            )
            self.conn.commit()
            logger.info(f"User created: {user_id} - {username}")
            return True
        except Exception as e:
            logger.error(f"Error creating user: {e}")
            return False
    
    def update_balance(self, user_id, amount):
        cursor = self.conn.cursor()
        try:
            cursor.execute(
                'UPDATE users SET balance = balance + ? WHERE user_id = ?',
                (amount, user_id)
            )
            self.conn.commit()
            return True
        except Exception as e:
            logger.error(f"Error updating balance: {e}")
            return False
    
    def add_transaction(self, user_id, type_, amount, description=""):
        cursor = self.conn.cursor()
        try:
            cursor.execute(
                'INSERT INTO transactions (user_id, type, amount, description) VALUES (?, ?, ?, ?)',
                (user_id, type_, amount, description)
            )
            self.conn.commit()
            return True
        except Exception as e:
            logger.error(f"Error adding transaction: {e}")
            return False
    
    def add_to_inventory(self, user_id, item_name, item_value):
        cursor = self.conn.cursor()
        try:
            cursor.execute(
                'INSERT INTO inventory (user_id, item_name, item_value) VALUES (?, ?, ?)',
                (user_id, item_name, item_value)
            )
            self.conn.commit()
            return True
        except Exception as e:
            logger.error(f"Error adding to inventory: {e}")
            return False
    
    def get_inventory(self, user_id):
        cursor = self.conn.cursor()
        try:
            cursor.execute(
                'SELECT * FROM inventory WHERE user_id = ? ORDER BY created_at DESC',
                (user_id,)
            )
            return cursor.fetchall()
        except Exception as e:
            logger.error(f"Error getting inventory: {e}")
            return []
    
    def create_withdrawal(self, user_id, username, item_name, item_value):
        cursor = self.conn.cursor()
        try:
            cursor.execute(
                'INSERT INTO withdrawals (user_id, username, item_name, item_value) VALUES (?, ?, ?, ?)',
                (user_id, username, item_name, item_value)
            )
            self.conn.commit()
            withdrawal_id = cursor.lastrowid
            logger.info(f"Withdrawal created: ID {withdrawal_id} - User {username} - {item_name}")
            return withdrawal_id
        except Exception as e:
            logger.error(f"Error creating withdrawal: {e}")
            return None
    
    def get_pending_withdrawals(self):
        cursor = self.conn.cursor()
        try:
            cursor.execute('SELECT * FROM withdrawals WHERE status = "pending" ORDER BY created_at DESC')
            return cursor.fetchall()
        except Exception as e:
            logger.error(f"Error getting withdrawals: {e}")
            return []
    
    def update_withdrawal_status(self, withdrawal_id, status):
        cursor = self.conn.cursor()
        try:
            cursor.execute(
                'UPDATE withdrawals SET status = ? WHERE id = ?',
                (status, withdrawal_id)
            )
            self.conn.commit()
            return True
        except Exception as e:
            logger.error(f"Error updating withdrawal status: {e}")
            return False
    
    def update_game_stats(self, user_id, won_amount=0):
        cursor = self.conn.cursor()
        try:
            # Проверяем существующую запись
            cursor.execute('SELECT * FROM game_stats WHERE user_id = ?', (user_id,))
            existing = cursor.fetchone()
            
            if existing:
                cursor.execute(
                    'UPDATE game_stats SET spins_count = spins_count + 1, total_won = total_won + ?, last_spin = ? WHERE user_id = ?',
                    (won_amount, datetime.now().isoformat(), user_id)
                )
            else:
                cursor.execute(
                    'INSERT INTO game_stats (user_id, spins_count, total_won, last_spin) VALUES (?, 1, ?, ?)',
                    (user_id, won_amount, datetime.now().isoformat())
                )
            
            self.conn.commit()
            return True
        except Exception as e:
            logger.error(f"Error updating game stats: {e}")
            return False
    
    def get_user_stats(self, user_id):
        cursor = self.conn.cursor()
        try:
            cursor.execute('SELECT * FROM game_stats WHERE user_id = ?', (user_id,))
            stats = cursor.fetchone()
            if stats:
                return {
                    'spins_count': stats[2],
                    'total_won': stats[3],
                    'last_spin': stats[4]
                }
            return {'spins_count': 0, 'total_won': 0, 'last_spin': None}
        except Exception as e:
            logger.error(f"Error getting user stats: {e}")
            return {'spins_count': 0, 'total_won': 0, 'last_spin': None}
    
    def get_all_users_count(self):
        cursor = self.conn.cursor()
        try:
            cursor.execute('SELECT COUNT(*) FROM users')
            return cursor.fetchone()[0]
        except Exception as e:
            logger.error(f"Error getting users count: {e}")
            return 0
    
    def get_total_withdrawals_count(self):
        cursor = self.conn.cursor()
        try:
            cursor.execute('SELECT COUNT(*) FROM withdrawals')
            return cursor.fetchone()[0]
        except Exception as e:
            logger.error(f"Error getting withdrawals count: {e}")
            return 0

# Инициализация базы данных
db = Database()

@app.route('/')
def home():
    return jsonify({
        "status": "online",
        "message": "Ghost FluX Casino API",
        "version": "1.0.0"
    })

@app.route('/api/health', methods=['GET'])
def health_check():
    return jsonify({"status": "healthy", "timestamp": datetime.now().isoformat()})

@app.route('/api/user/<int:user_id>', methods=['GET'])
def get_user(user_id):
    try:
        user = db.get_user(user_id)
        if not user:
            return jsonify({"error": "User not found"}), 404
        
        # Получаем статистику игрока
        stats = db.get_user_stats(user_id)
        user['stats'] = stats
        
        return jsonify(user)
    except Exception as e:
        logger.error(f"Error in get_user: {e}")
        return jsonify({"error": "Internal server error"}), 500

@app.route('/api/register', methods=['POST'])
def register_user():
    try:
        data = request.json
        if not data:
            return jsonify({"error": "No data provided"}), 400
        
        user_id = data.get('user_id')
        username = data.get('username', 'Unknown')
        
        if not user_id:
            return jsonify({"error": "User ID is required"}), 400
        
        success = db.create_user(user_id, username)
        if success:
            return jsonify({"status": "success", "message": "User registered"})
        else:
            return jsonify({"error": "Failed to register user"}), 500
            
    except Exception as e:
        logger.error(f"Error in register_user: {e}")
        return jsonify({"error": "Internal server error"}), 500

@app.route('/api/daily-bonus', methods=['POST'])
def daily_bonus():
    try:
        data = request.json
        if not data:
            return jsonify({"error": "No data provided"}), 400
        
        user_id = data.get('user_id')
        if not user_id:
            return jsonify({"error": "User ID is required"}), 400
        
        user = db.get_user(user_id)
        if not user:
            return jsonify({"error": "User not found"}), 404
        
        now = datetime.now()
        last_bonus = user.get('last_daily_bonus')
        
        # Проверяем, можно ли получить бонус
        if last_bonus:
            try:
                last_bonus = datetime.fromisoformat(last_bonus)
                if now - last_bonus < timedelta(hours=24):
                    time_left = timedelta(hours=24) - (now - last_bonus)
                    hours_left = int(time_left.total_seconds() // 3600)
                    minutes_left = int((time_left.total_seconds() % 3600) // 60)
                    return jsonify({
                        "error": f"Bonus already claimed. Next available in {hours_left}h {minutes_left}m"
                    }), 400
            except ValueError as e:
                logger.warning(f"Error parsing last_bonus date: {e}")
        
        # Выдаем бонус
        bonus = random.choices(
            [b['stars'] for b in DAILY_BONUS],
            weights=[b['chance'] for b in DAILY_BONUS]
        )[0]
        
        # Обновляем баланс и время получения бонуса
        success = db.update_balance(user_id, bonus)
        if not success:
            return jsonify({"error": "Failed to update balance"}), 500
        
        cursor = db.conn.cursor()
        cursor.execute(
            'UPDATE users SET last_daily_bonus = ? WHERE user_id = ?',
            (now.isoformat(), user_id)
        )
        db.conn.commit()
        
        # Добавляем транзакцию
        db.add_transaction(user_id, "daily_bonus", bonus, "Ежедневный бонус")
        
        new_balance = db.get_user(user_id)['balance']
        
        logger.info(f"Daily bonus given: User {user_id} - {bonus} stars")
        
        return jsonify({
            "bonus": bonus, 
            "new_balance": new_balance,
            "message": f"🎁 Вы получили {bonus} звёзд!"
        })
        
    except Exception as e:
        logger.error(f"Error in daily_bonus: {e}")
        return jsonify({"error": "Internal server error"}), 500

@app.route('/api/spin-roulette', methods=['POST'])
def spin_roulette():
    try:
        data = request.json
        if not data:
            return jsonify({"error": "No data provided"}), 400
        
        user_id = data.get('user_id')
        if not user_id:
            return jsonify({"error": "User ID is required"}), 400
        
        cost = 25
        
        user = db.get_user(user_id)
        if not user:
            return jsonify({"error": "User not found"}), 404
        
        if user['balance'] < cost:
            return jsonify({"error": "Insufficient balance"}), 400
        
        # Спин рулетки
        item = random.choices(
            ROULETTE_ITEMS,
            weights=[i['chance'] for i in ROULETTE_ITEMS]
        )[0]
        
        # Обновляем баланс
        success = db.update_balance(user_id, -cost)
        if not success:
            return jsonify({"error": "Failed to update balance"}), 500
        
        # Добавляем предмет в инвентарь
        success = db.add_to_inventory(user_id, item['name'], item['value'])
        if not success:
            return jsonify({"error": "Failed to add item to inventory"}), 500
        
        # Обновляем статистику
        db.update_game_stats(user_id, item['value'])
        
        # Добавляем транзакции
        db.add_transaction(user_id, "roulette_spin", -cost, "Спин рулетки")
        db.add_transaction(user_id, "item_won", item['value'], f"Выигрыш: {item['name']}")
        
        new_balance = db.get_user(user_id)['balance']
        
        logger.info(f"Roulette spin: User {user_id} - Won {item['name']} ({item['value']} stars)")
        
        return jsonify({
            "won_item": item,
            "new_balance": new_balance,
            "cost": cost,
            "message": f"🎉 Поздравляем! Вы выиграли {item['name']} ({item['value']}⭐)"
        })
        
    except Exception as e:
        logger.error(f"Error in spin_roulette: {e}")
        return jsonify({"error": "Internal server error"}), 500

@app.route('/api/inventory/<int:user_id>', methods=['GET'])
def get_user_inventory(user_id):
    try:
        inventory = db.get_inventory(user_id)
        
        # Форматируем результат
        formatted_inventory = []
        for item in inventory:
            formatted_inventory.append({
                "id": item[0],
                "user_id": item[1],
                "item_name": item[2],
                "item_value": item[3],
                "created_at": item[4]
            })
        
        return jsonify(formatted_inventory)
        
    except Exception as e:
        logger.error(f"Error in get_user_inventory: {e}")
        return jsonify({"error": "Internal server error"}), 500

@app.route('/api/withdraw', methods=['POST'])
def withdraw_item():
    try:
        data = request.json
        if not data:
            return jsonify({"error": "No data provided"}), 400
        
        user_id = data.get('user_id')
        item_name = data.get('item_name')
        item_value = data.get('item_value')
        username = data.get('username', 'Unknown')
        
        if not all([user_id, item_name, item_value]):
            return jsonify({"error": "Missing required fields"}), 400
        
        # Проверяем существование пользователя
        user = db.get_user(user_id)
        if not user:
            return jsonify({"error": "User not found"}), 404
        
        # Проверяем наличие предмета в инвентаре
        inventory = db.get_inventory(user_id)
        item_exists = any(item[2] == item_name for item in inventory)
        
        if not item_exists:
            return jsonify({"error": "Item not found in inventory"}), 400
        
        # Создаем заявку на вывод
        withdrawal_id = db.create_withdrawal(user_id, username, item_name, item_value)
        if not withdrawal_id:
            return jsonify({"error": "Failed to create withdrawal"}), 500
        
        # Удаляем предмет из инвентаря
        cursor = db.conn.cursor()
        cursor.execute(
            'DELETE FROM inventory WHERE user_id = ? AND item_name = ? LIMIT 1',
            (user_id, item_name)
        )
        db.conn.commit()
        
        # Добавляем транзакцию
        db.add_transaction(user_id, "withdrawal", -item_value, f"Вывод: {item_name}")
        
        logger.info(f"Withdrawal created: User {user_id} (@{username}) - {item_name} ({item_value} stars)")
        
        return jsonify({
            "status": "withdrawal_created", 
            "id": withdrawal_id,
            "message": "Заявка на вывод создана! Администратор свяжется с вами."
        })
        
    except Exception as e:
        logger.error(f"Error in withdraw_item: {e}")
        return jsonify({"error": "Internal server error"}), 500

@app.route('/api/admin/withdrawals', methods=['GET'])
def get_withdrawals():
    try:
        withdrawals = db.get_pending_withdrawals()
        
        # Форматируем результат
        formatted_withdrawals = []
        for w in withdrawals:
            formatted_withdrawals.append({
                "id": w[0],
                "user_id": w[1],
                "username": w[2],
                "item_name": w[3],
                "item_value": w[4],
                "status": w[5],
                "created_at": w[6]
            })
        
        return jsonify(formatted_withdrawals)
        
    except Exception as e:
        logger.error(f"Error in get_withdrawals: {e}")
        return jsonify({"error": "Internal server error"}), 500

@app.route('/api/admin/add-stars', methods=['POST'])
def add_stars():
    try:
        data = request.json
        if not data:
            return jsonify({"error": "No data provided"}), 400
        
        user_id = data.get('user_id')
        amount = data.get('amount')
        
        if not all([user_id, amount]):
            return jsonify({"error": "User ID and amount are required"}), 400
        
        # Проверяем существование пользователя
        user = db.get_user(user_id)
        if not user:
            return jsonify({"error": "User not found"}), 404
        
        # Обновляем баланс
        success = db.update_balance(user_id, amount)
        if not success:
            return jsonify({"error": "Failed to update balance"}), 500
        
        # Добавляем транзакцию
        db.add_transaction(user_id, "admin_add", amount, "Пополнение администратором")
        
        new_balance = db.get_user(user_id)['balance']
        
        logger.info(f"Stars added by admin: User {user_id} - {amount} stars")
        
        return jsonify({
            "status": "success",
            "new_balance": new_balance,
            "message": f"Added {amount} stars to user {user_id}"
        })
        
    except Exception as e:
        logger.error(f"Error in add_stars: {e}")
        return jsonify({"error": "Internal server error"}), 500

@app.route('/api/admin/stats', methods=['GET'])
def get_admin_stats():
    try:
        total_users = db.get_all_users_count()
        total_withdrawals = db.get_total_withdrawals_count()
        
        return jsonify({
            "total_users": total_users,
            "total_withdrawals": total_withdrawals,
            "server_time": datetime.now().isoformat()
        })
        
    except Exception as e:
        logger.error(f"Error in get_admin_stats: {e}")
        return jsonify({"error": "Internal server error"}), 500

@app.route('/api/admin/complete-withdrawal/<int:withdrawal_id>', methods=['POST'])
def complete_withdrawal(withdrawal_id):
    try:
        success = db.update_withdrawal_status(withdrawal_id, "completed")
        if success:
            logger.info(f"Withdrawal {withdrawal_id} marked as completed")
            return jsonify({"status": "success", "message": "Withdrawal completed"})
        else:
            return jsonify({"error": "Failed to update withdrawal"}), 500
            
    except Exception as e:
        logger.error(f"Error in complete_withdrawal: {e}")
        return jsonify({"error": "Internal server error"}), 500

@app.route('/api/user/stats/<int:user_id>', methods=['GET'])
def get_user_game_stats(user_id):
    try:
        stats = db.get_user_stats(user_id)
        return jsonify(stats)
    except Exception as e:
        logger.error(f"Error in get_user_game_stats: {e}")
        return jsonify({"error": "Internal server error"}), 500

# Обработка ошибок
@app.errorhandler(404)
def not_found(error):
    return jsonify({"error": "Endpoint not found"}), 404

@app.errorhandler(500)
def internal_error(error):
    return jsonify({"error": "Internal server error"}), 500

@app.errorhandler(405)
def method_not_allowed(error):
    return jsonify({"error": "Method not allowed"}), 405

if __name__ == '__main__':
    logger.info("Starting Ghost FluX Casino API server...")
    app.run(host='0.0.0.0', port=5000, debug=True)