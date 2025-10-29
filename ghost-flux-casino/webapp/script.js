class GhostFluxApp {
    constructor() {
        this.tg = window.Telegram.WebApp;
        this.user = null;
        this.balance = 100; // Начальный баланс для теста
        this.inventory = [];
        
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
                this.showMainUI();
            } else {
                // Тестовый режим если нет данных пользователя
                this.user = { id: 123456789, username: 'test_user' };
                this.showMainUI();
            }
        } catch (error) {
            console.error('Initialization error:', error);
            // Все равно показываем интерфейс
            this.user = { id: 123456789, username: 'test_user' };
            this.showMainUI();
        }
    }

    showMainUI() {
        document.getElementById('loader').classList.add('hidden');
        document.getElementById('main-ui').classList.remove('hidden');
        this.updateBalanceDisplay();
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
            // Имитация запроса к серверу
            const wonItem = this.getRandomItem();
            
            // Анимация рулетки
            await this.animateRoulette(wonItem);
            
            // Обновляем баланс
            this.balance -= 25; // Стоимость спина
            this.balance += wonItem.value; // Выигрыш
            
            // Добавляем в инвентарь
            this.inventory.push(wonItem);
            
            this.updateBalanceDisplay();
            
            // Показываем выигрыш
            this.showWinModal(wonItem);

        } catch (error) {
            console.error('Error spinning roulette:', error);
            alert('Ошибка при вращении рулетки');
        }

        spinBtn.disabled = false;
    }

    getRandomItem() {
        const items = [
            {"name": "Мишка", "value": 15, "chance": 35, "emoji": "🧸"},
            {"name": "Сердечко", "value": 15, "chance": 35, "emoji": "💖"},
            {"name": "Ракета", "value": 50, "chance": 10, "emoji": "🚀"},
            {"name": "Торт", "value": 50, "chance": 10, "emoji": "🎂"},
            {"name": "Кубок", "value": 100, "chance": 5, "emoji": "🏆"},
            {"name": "Кольцо", "value": 100, "chance": 5, "emoji": "💍"}
        ];

        // Простая реализация случайного выбора
        const random = Math.random() * 100;
        let currentChance = 0;

        for (const item of items) {
            currentChance += item.chance;
            if (random <= currentChance) {
                return item;
            }
        }

        return items[0]; // fallback
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
            // Имитация ежедневного бонуса
            const bonuses = [
                {"stars": 5, "chance": 70},
                {"stars": 10, "chance": 15},
                {"stars": 25, "chance": 10},
                {"stars": 50, "chance": 5}
            ];

            const random = Math.random() * 100;
            let currentChance = 0;
            let bonus = 5;

            for (const b of bonuses) {
                currentChance += b.chance;
                if (random <= currentChance) {
                    bonus = b.stars;
                    break;
                }
            }

            this.balance += bonus;
            this.updateBalanceDisplay();
            
            alert(`🎁 Вы получили ${bonus} звёзд!`);

        } catch (error) {
            console.error('Error claiming bonus:', error);
            alert('Ошибка при получении бонуса');
        }

        bonusBtn.disabled = false;
    }

    async showInventory() {
        this.renderInventory();
        document.getElementById('inventory-modal').classList.remove('hidden');
    }

    renderInventory() {
        const inventoryList = document.getElementById('inventory-list');
        
        if (this.inventory.length === 0) {
            inventoryList.innerHTML = '<p style="text-align: center; padding: 20px;">🎒 Инвентарь пуст</p>';
            return;
        }

        inventoryList.innerHTML = this.inventory.map((item, index) => `
            <div class="inventory-item">
                <div>
                    <strong>${item.emoji} ${item.name}</strong>
                    <br>
                    <small>${item.value} звёзд</small>
                </div>
                <button class="withdraw-btn" onclick="app.withdrawItem(${index})">
                    Вывести
                </button>
            </div>
        `).join('');
    }

    withdrawItem(index) {
        const item = this.inventory[index];
        if (!confirm(`Вывести ${item.name} (${item.value} звёзд)?\n\nАдминистратор @KXKXKXKXKXKXKXKXKXKXK свяжется с вами.`)) {
            return;
        }

        // Удаляем из инвентаря
        this.inventory.splice(index, 1);
        this.renderInventory();
        
        alert('✅ Заявка на вывод создана! Администратор свяжется с вами в Telegram.');
    }

    showWinModal(item) {
        const winItem = document.getElementById('win-item');
        winItem.innerHTML = `
            <div style="font-size: 48px;">${item.emoji}</div>
            <h3>${item.name}</h3>
            <p>${item.value} звёзд</p>
        `;
        
        document.getElementById('win-modal').classList.remove('hidden');
    }

    updateBalanceDisplay() {
        document.getElementById('balance').textContent = this.balance;
    }
}

// Инициализация приложения
let app;
document.addEventListener('DOMContentLoaded', () => {
    app = new GhostFluxApp();
});