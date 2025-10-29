class GhostFluxApp {
    constructor() {
        this.tg = window.Telegram.WebApp;
        this.user = null;
        this.balance = 0;
        this.inventory = [];
        this.API_BASE_URL = "http://localhost:5000/api";
        
        this.init();
    }

    async init() {
        try {
            // Инициализация Telegram WebApp
            this.tg.expand();
            this.tg.enableClosingConfirmation();
            
            // Получаем данные пользователя
            this.user = this.tg.initDataUnsafe.user;
            
            if (this.user) {
                await this.loadUserData();
                this.showMainUI();
            } else {
                this.showError("Ошибка загрузки данных пользователя");
            }
        } catch (error) {
            console.error('Initialization error:', error);
            this.showError("Ошибка инициализации приложения");
        }
    }

    async loadUserData() {
        try {
            const response = await fetch(`${this.API_BASE_URL}/user/${this.user.id}`);
            const userData = await response.json();
            
            if (userData.error) {
                // Регистрируем пользователя
                await fetch(`${this.API_BASE_URL}/register`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        user_id: this.user.id,
                        username: this.user.username
                    })
                });
                
                // Повторно загружаем данные
                await this.loadUserData();
                return;
            }
            
            this.balance = userData.balance;
            this.updateBalanceDisplay();
            
        } catch (error) {
            console.error('Error loading user data:', error);
            this.showError("Ошибка загрузки данных пользователя");
        }
    }

    showMainUI() {
        document.getElementById('loader').classList.add('hidden');
        document.getElementById('main-ui').classList.remove('hidden');
        
        this.setupEventListeners();
    }

    setupEventListeners() {
        // Кнопка спина рулетки
        document.getElementById('spin-btn').addEventListener('click', () => {
            this.spinRoulette();
        });

        // Ежедневный бонус
        document.getElementById('daily-bonus-btn').addEventListener('click', () => {
            this.claimDailyBonus();
        });

        // Инвентарь
        document.getElementById('inventory-btn').addEventListener('click', () => {
            this.showInventory();
        });

        // Закрытие модальных окон
        document.querySelectorAll('.close-btn').forEach(btn => {
            btn.addEventListener('click', (e) => {
                e.target.closest('.modal').classList.add('hidden');
            });
        });
    }

    async spinRoulette() {
        if (this.balance < 25) {
            alert('Недостаточно звёзд для спина!');
            return;
        }

        const spinBtn = document.getElementById('spin-btn');
        spinBtn.disabled = true;

        try {
            const response = await fetch(`${this.API_BASE_URL}/spin-roulette`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ user_id: this.user.id })
            });

            const result = await response.json();

            if (result.error) {
                alert(result.error);
                spinBtn.disabled = false;
                return;
            }

            // Анимация рулетки
            await this.animateRoulette(result.won_item);
            
            // Обновляем баланс
            this.balance = result.new_balance;
            this.updateBalanceDisplay();
            
            // Показываем выигрыш
            this.showWinModal(result.won_item);

        } catch (error) {
            console.error('Error spinning roulette:', error);
            alert('Ошибка при вращении рулетки');
        }

        spinBtn.disabled = false;
    }

    async animateRoulette(winningItem) {
        const roulette = document.getElementById('roulette');
        const items = roulette.querySelectorAll('.roulette-item');
        
        // Добавляем класс анимации
        roulette.classList.add('spinning');
        
        // Ждем завершения анимации
        await new Promise(resolve => setTimeout(resolve, 3000));
        
        // Убираем анимацию
        roulette.classList.remove('spinning');
        
        // Подсвечиваем выигранный предмет
        items.forEach(item => {
            item.classList.remove('highlight');
            if (item.textContent.includes(winningItem.emoji)) {
                item.classList.add('highlight');
            }
        });
    }

    async claimDailyBonus() {
        const bonusBtn = document.getElementById('daily-bonus-btn');
        bonusBtn.disabled = true;

        try {
            const response = await fetch(`${this.API_BASE_URL}/daily-bonus`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ user_id: this.user.id })
            });

            const result = await response.json();

            if (result.error) {
                alert(result.error);
            } else {
                this.balance = result.new_balance;
                this.updateBalanceDisplay();
                alert(`🎁 Вы получили ${result.bonus} звёзд!`);
            }

        } catch (error) {
            console.error('Error claiming bonus:', error);
            alert('Ошибка при получении бонуса');
        }

        bonusBtn.disabled = false;
    }

    async showInventory() {
        try {
            const response = await fetch(`${this.API_BASE_URL}/inventory/${this.user.id}`);
            this.inventory = await response.json();
            this.renderInventory();
        } catch (error) {
            console.error('Error loading inventory:', error);
        }
        
        document.getElementById('inventory-modal').classList.remove('hidden');
    }

    renderInventory() {
        const inventoryList = document.getElementById('inventory-list');
        
        if (this.inventory.length === 0) {
            inventoryList.innerHTML = '<p>Инвентарь пуст</p>';
            return;
        }

        inventoryList.innerHTML = this.inventory.map(item => `
            <div class="inventory-item">
                <div>
                    <strong>${this.getItemEmoji(item.item_name)} ${item.item_name}</strong>
                    <br>
                    <small>${item.item_value} звёзд</small>
                </div>
                <button class="withdraw-btn" onclick="app.withdrawItem('${item.item_name}', ${item.item_value})">
                    Вывести
                </button>
            </div>
        `).join('');
    }

    getItemEmoji(itemName) {
        const emojis = {
            'Мишка': '🧸',
            'Сердечко': '💖',
            'Ракета': '🚀',
            'Торт': '🎂',
            'Кубок': '🏆',
            'Кольцо': '💍'
        };
        return emojis[itemName] || '🎁';
    }

    async withdrawItem(itemName, itemValue) {
        if (!confirm(`Вывести ${itemName} (${itemValue} звёзд)?`)) {
            return;
        }

        try {
            const response = await fetch(`${this.API_BASE_URL}/withdraw`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    user_id: this.user.id,
                    username: this.user.username,
                    item_name: itemName,
                    item_value: itemValue
                })
            });

            const result = await response.json();

            if (result.status === 'withdrawal_created') {
                alert('Заявка на вывод создана! Администратор свяжется с вами.');
                this.showInventory(); // Обновляем инвентарь
            } else {
                alert('Ошибка при создании заявки');
            }

        } catch (error) {
            console.error('Error withdrawing item:', error);
            alert('Ошибка при выводе предмета');
        }
    }

    showWinModal(item) {
        const winItem = document.getElementById('win-item');
        winItem.innerHTML = `
            <div>${item.emoji}</div>
            <h3>${item.name}</h3>
            <p>${item.value} звёзд</p>
        `;
        
        document.getElementById('win-modal').classList.remove('hidden');
    }

    updateBalanceDisplay() {
        document.getElementById('balance').textContent = this.balance;
    }

    showError(message) {
        alert(`❌ ${message}`);
    }
}

// Инициализация приложения
let app;
document.addEventListener('DOMContentLoaded', () => {
    app = new GhostFluxApp();
});