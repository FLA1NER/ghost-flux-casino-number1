import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes
import requests
import json
from config import BOT_TOKEN, ADMIN_ID, ADMIN_USERNAME, CHANNEL_USERNAME, WEBAPP_URL

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Базовый URL API
API_BASE_URL = "http://localhost:5000/api"

def make_api_request(endpoint, method='GET', data=None):
    """Универсальная функция для API запросов с обработкой ошибок"""
    try:
        url = f"{API_BASE_URL}/{endpoint}"
        logger.info(f"Making API request to: {url}")
        
        if method == 'GET':
            response = requests.get(url, timeout=10)
        elif method == 'POST':
            response = requests.post(url, json=data, timeout=10)
        
        logger.info(f"API response status: {response.status_code}")
        
        if response.status_code == 200:
            return response.json()
        else:
            logger.error(f"API Error: {response.status_code} - {response.text}")
            return None
    except requests.exceptions.RequestException as e:
        logger.error(f"Request failed: {e}")
        return None
    except json.JSONDecodeError as e:
        logger.error(f"JSON decode error: {e}")
        return None

def escape_markdown(text):
    """Экранирование специальных символов для MarkdownV2"""
    if not text:
        return ""
    escape_chars = r'_*[]()~`>#+-=|{}.!'
    return ''.join(['\\' + char if char in escape_chars else char for char in str(text)])

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        user = update.effective_user
        user_id = user.id
        username = user.username or "Unknown"
        
        logger.info(f"Start command from user {user_id} (@{username})")
        
        # Регистрируем пользователя (но не блокируем если сервер недоступен)
        try:
            result = make_api_request('register', 'POST', {
                'user_id': user_id,
                'username': username
            })
            
            if result is None:
                logger.warning(f"Failed to register user {user_id}, but continuing...")
            else:
                logger.info(f"User {user_id} registered successfully")
        except Exception as e:
            logger.warning(f"Registration failed but continuing: {e}")
        
        # Создаем клавиатуру
        keyboard = [
            [InlineKeyboardButton("🎮 Открыть Ghost FluX Casino", web_app={'url': WEBAPP_URL})],
            [InlineKeyboardButton("📢 Наш канал", url=f"https://t.me/{CHANNEL_USERNAME}")],
            [InlineKeyboardButton("💬 Купить звёзды", url=ADMIN_USERNAME)]
        ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        # Текст без Markdown для надежности
        welcome_text = f"""👻 Добро пожаловать в Ghost FluX Casino!

🎰 Игровые режимы:
• 🎡 Рулетка (25 звёзд)
• 🎁 Ежедневный бонус

💫 Пополнение баланса:
50 звёзд = 85 руб
100 звёзд = 160 руб
250 звёзд = 400 руб

💌 Связь: {ADMIN_USERNAME}

Нажмите кнопку ниже чтобы открыть казино! 🎮"""
        
        await update.message.reply_text(
            welcome_text,
            reply_markup=reply_markup
            # Убрал parse_mode для избежания ошибок
        )
        
        logger.info(f"Start message sent to user {user_id}")
        
    except Exception as e:
        logger.error(f"Error in start command: {e}")
        await update.message.reply_text(
            "❌ Произошла ошибка при запуске. Пожалуйста, попробуйте позже."
        )

async def admin_panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        user_id = update.effective_user.id
        if user_id != ADMIN_ID:
            await update.message.reply_text("❌ Доступ запрещен")
            return
        
        keyboard = [
            [InlineKeyboardButton("📊 Статистика", callback_data="admin_stats")],
            [InlineKeyboardButton("📤 Заявки на вывод", callback_data="admin_withdrawals")],
            [InlineKeyboardButton("⭐ Добавить звёзды", callback_data="admin_add_stars")],
            [InlineKeyboardButton("🔄 Обновить", callback_data="admin_refresh")]
        ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text("👑 Панель администратора", reply_markup=reply_markup)
        
    except Exception as e:
        logger.error(f"Error in admin_panel: {e}")
        await update.message.reply_text("❌ Ошибка при открытии админ панели")

async def handle_admin_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        query = update.callback_query
        user_id = query.from_user.id
        
        if user_id != ADMIN_ID:
            await query.answer("❌ Доступ запрещен")
            return
        
        await query.answer()
        data = query.data
        
        if data == "admin_withdrawals":
            withdrawals = make_api_request('admin/withdrawals')
            
            if not withdrawals:
                text = "📭 Нет pending заявок на вывод"
            else:
                text = "📤 Заявки на вывод:\n\n"
                for w in withdrawals:
                    text += f"ID: {w['id']}\n"
                    text += f"Пользователь: @{w['username']} (ID: {w['user_id']})\n"
                    text += f"Предмет: {w['item_name']} ({w['item_value']} звёзд)\n"
                    text += f"Время: {w['created_at'][:19]}\n"
                    text += "⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯\n"
            
            keyboard = [
                [InlineKeyboardButton("🔄 Обновить", callback_data="admin_withdrawals")],
                [InlineKeyboardButton("📋 Главное меню", callback_data="admin_back")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await query.edit_message_text(text, reply_markup=reply_markup)
        
        elif data == "admin_stats":
            stats = make_api_request('admin/stats')
            
            if stats:
                users_count = stats.get('total_users', 'N/A')
                total_withdrawals = stats.get('total_withdrawals', 'N/A')
            else:
                users_count = "N/A"
                total_withdrawals = "N/A"
            
            text = (
                f"📊 Статистика Ghost FluX\n\n"
                f"👥 Пользователи: {users_count}\n"
                f"📤 Всего выводов: {total_withdrawals}\n"
                f"👑 Админ: {ADMIN_USERNAME}"
            )
            
            keyboard = [
                [InlineKeyboardButton("🔄 Обновить", callback_data="admin_stats")],
                [InlineKeyboardButton("📋 Главное меню", callback_data="admin_back")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await query.edit_message_text(text, reply_markup=reply_markup)
        
        elif data == "admin_add_stars":
            text = (
                "⭐ Добавление звёзд\n\n"
                "Используйте команду:\n"
                "/addstars user_id amount\n\n"
                "Пример:\n"
                "/addstars 123456789 100"
            )
            
            keyboard = [
                [InlineKeyboardButton("📋 Главное меню", callback_data="admin_back")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await query.edit_message_text(text, reply_markup=reply_markup)
        
        elif data == "admin_back" or data == "admin_refresh":
            await admin_panel(update, context)
            
    except Exception as e:
        logger.error(f"Error in handle_admin_callback: {e}")
        await query.edit_message_text("❌ Ошибка при обработке запроса")

async def add_stars_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        user_id = update.effective_user.id
        if user_id != ADMIN_ID:
            await update.message.reply_text("❌ Доступ запрещен")
            return
        
        if len(context.args) != 2:
            await update.message.reply_text(
                "❌ Неправильный формат команды\n\n"
                "Используйте: /addstars user_id amount\n"
                "Пример: /addstars 123456789 100"
            )
            return
        
        target_user_id = int(context.args[0])
        amount = int(context.args[1])
        
        result = make_api_request('admin/add-stars', 'POST', {
            'user_id': target_user_id,
            'amount': amount
        })
        
        if result:
            await update.message.reply_text(
                f"✅ Успешно добавлено {amount}⭐ пользователю {target_user_id}"
            )
            
            # Пытаемся отправить уведомление пользователю
            try:
                await context.bot.send_message(
                    chat_id=target_user_id,
                    text=f"🎉 Вам начислено {amount}⭐ на баланс!\n\n💫 Новый баланс можно проверить в Mini App"
                )
            except Exception as e:
                logger.warning(f"Could not notify user {target_user_id}: {e}")
                
        else:
            await update.message.reply_text("❌ Ошибка при добавлении звёзд")
            
    except ValueError:
        await update.message.reply_text("❌ Неверный формат ID или количества звёзд")
    except Exception as e:
        logger.error(f"Error in add_stars_command: {e}")
        await update.message.reply_text("❌ Ошибка при выполнении команды")

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда помощи"""
    help_text = """
🤖 Команды бота Ghost FluX:

/start - Начать работу
/help - Показать эту справку
/stats - Моя статистика

👑 Команды администратора:
/admin - Панель управления
/addstars user_id amount - Добавить звёзды
/complete withdrawal_id - Завершить вывод

💫 Пополнение баланса:
50⭐ = 85 руб | 100⭐ = 160 руб | 250⭐ = 400 руб
Связь: @KXKXKXKXKXKXKXKXKXKXK
    """
    await update.message.reply_text(help_text)

async def user_stats_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда для просмотра статистики пользователя"""
    try:
        user_id = update.effective_user.id
        
        # Определяем ID пользователя для статистики
        if len(context.args) == 1 and update.effective_user.id == ADMIN_ID:
            try:
                target_user_id = int(context.args[0])
            except ValueError:
                target_user_id = user_id
        else:
            target_user_id = user_id
        
        stats = make_api_request(f'user/stats/{target_user_id}')
        user_data = make_api_request(f'user/{target_user_id}')
        
        if stats and user_data:
            username = user_data.get('username', 'Unknown')
            balance = user_data.get('balance', 0)
            
            text = (
                f"📊 Статистика пользователя @{username}\n\n"
                f"🆔 ID: {target_user_id}\n"
                f"⭐ Баланс: {balance}\n"
                f"🎡 Спинов: {stats.get('spins_count', 0)}\n"
                f"🏆 Всего выиграно: {stats.get('total_won', 0)}⭐\n"
            )
            
            if stats.get('last_spin'):
                text += f"⏰ Последний спин: {stats['last_spin'][:19]}"
            
            await update.message.reply_text(text)
        else:
            await update.message.reply_text("❌ Ошибка при получении статистики")
            
    except Exception as e:
        logger.error(f"Error in user_stats_command: {e}")
        await update.message.reply_text("❌ Ошибка при получении статистики")

async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик ошибок"""
    try:
        logger.error(f"Exception while handling an update: {context.error}", exc_info=context.error)
        
        # Более информативное сообщение об ошибке
        error_message = f"""
❌ Произошла техническая ошибка.

Возможные причины:
• Сервер временно недоступен
• Проблемы с подключением
• Технические работы

Пожалуйста, попробуйте позже или свяжитесь с администратором: {ADMIN_USERNAME}
        """
        
        if update and update.effective_message:
            await update.effective_message.reply_text(error_message)
    except Exception as e:
        logger.error(f"Error in error handler: {e}")

def main():
    try:
        logger.info("Starting Ghost FluX Casino Bot...")
        logger.info(f"Admin ID: {ADMIN_ID}")
        logger.info(f"WebApp URL: {WEBAPP_URL}")
        
        # Создаем приложение
        application = Application.builder().token(BOT_TOKEN).build()
        
        # Обработчики команд
        application.add_handler(CommandHandler("start", start))
        application.add_handler(CommandHandler("help", help_command))
        application.add_handler(CommandHandler("admin", admin_panel))
        application.add_handler(CommandHandler("addstars", add_stars_command))
        application.add_handler(CommandHandler("stats", user_stats_command))
        
        # Обработчики callback запросов
        application.add_handler(CallbackQueryHandler(handle_admin_callback, pattern="^admin_"))
        
        # Обработчик ошибок
        application.add_error_handler(error_handler)
        
        logger.info("Bot started successfully!")
        application.run_polling()
        
    except Exception as e:
        logger.error(f"Failed to start bot: {e}")

if __name__ == '__main__':
    main()