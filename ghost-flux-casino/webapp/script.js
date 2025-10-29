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
            this.tg.BackButton.show();
            this.tg.BackButton.onClick(() => {
                this.closeModals();
            });
            
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

    async makeRequest(endpoint, options = {}) {
        try {
            const url = `${this.API_BASE_URL}/${endpoint}`;
            const response = await fetch(url, {
                headers: {
                    'Content-Type': 'application/json',
                    ...options.headers
                },
                ...options
            });
            
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            
            return await response.json();
        } catch (error) {
            console.error(`API request failed (${endpoint}):`, error);
            throw error;
        }
    }

    async loadUserData() {
        try {
            const userData = await this.makeRequest(`user/${this.user.id}`);
            
            if (userData.error) {
                // Регистрируем пользователя
                await this.makeRequest('register', {
                    method: 'POST',
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
            this.showError("Ошибка загрузки данных пользователя");
        }
    }

    async loadInventory() {
        try {
            this.inventory = await this.makeRequest(`inventory/${this.user.id}`);
            this.renderInventory();
        } catch (error) {
            this.showError("Ошибка загрузки инвентаря");
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
                this.closeModals();
            });
        });
    }

    closeModals() {
        document.querySelectorAll('.modal').forEach(modal => {
            modal.classList.add('hidden');
        });
        this.tg.BackButton.hide();
    }

    async spinRoulette() {
        if (this.balance < 25) {
            this.showError('Недостаточно звёзд для спина!');
            return;
        }

        const spinBtn = document.getElementById('spin-btn');
        const originalText = spinBtn.textContent;
        spinBtn.disabled = true;
        spinBtn.textContent = '🌀 Крутим...';

        try {
            const result = await this.makeRequest('spin-roulette', {
                method: 'POST',
                body: JSON.stringify({ user_id: this.user.id })
            });

            if (result.error) {
                this.showError(result.error);
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
            this.showError('Ошибка при вращении рулетки');
        } finally {
            spinBtn.disabled = false;
            spinBtn.textContent = originalText;
        }
    }

    async animateRoulette(winningItem) {
        const roulette = document.getElementById('roulette');
        const items = roulette.querySelectorAll('.roulette-item');
        
        // Сбрасываем подсветку
        items.forEach(item => item.classList.remove('highlight'));
        
        // Анимация вращения
        roulette.classList.add('spinning');
        
        // Ждем завершения анимации
        await new Promise(resolve => setTimeout(resolve, 3000));
        
        // Убираем анимацию
        roulette.classList.remove('spinning');
        
        // Подсвечиваем выигранный предмет
        items.forEach(item => {
            if (item.textContent.includes(winningItem.emoji)) {
                item.classList.add('highlight');
                
                // Дополнительная анимация для выигранного предмета
                item.style.animation = 'pulse 0.5s infinite alternate';
                setTimeout(() => {
                    item.style.animation = '';
                }, 2000);
            }
        });
    }

    async claimDailyBonus() {
        const bonusBtn = document.getElementById('daily-bonus-btn');
        bonusBtn.disabled = true;

        try {
            const result = await this.makeRequest('daily-bonus', {
                method: 'POST',
                body: JSON.stringify({ user_id: this.user.id })
            });

            if (result.error) {
                this.showError(result.error);
            } else {
                this.balance = result.new_balance;
                this.updateBalanceDisplay();
                this.showSuccess(`🎁 Вы получили ${result.bonus} звёзд!`);
                
                // Обновляем кнопку бонуса
                bonusBtn.textContent = '🎁 Бонус получен';
                bonusBtn.style.opacity = '0.7';
            }

        } catch (error) {
            this.showError('Ошибка при получении бонуса');
        }

        bonusBtn.disabled = false;
    }

    async showInventory() {
        this.tg.BackButton.show();
        await this.loadInventory();
        document.getElementById('inventory-modal').classList.remove('hidden');
    }

    renderInventory() {
        const inventoryList = document.getElementById('inventory-list');
        
        if (!this.inventory || this.inventory.length === 0) {
            inventoryList.innerHTML = '<p style="text-align: center; padding: 20px;">🎒 Инвентарь пуст</p>';
            return;
        }

        inventoryList.innerHTML = this.inventory.map(item => `
            <div class="inventory-item">
                <div class="item-info">
                    <span class="item-emoji">${this.getItemEmoji(item[2])}</span>
                    <div class="item-details">
                        <strong>${item[2]}</strong>
                        <small>${item[3]} звёзд</small>
                    </div>
                </div>
                <button class="withdraw-btn" onclick="app.withdrawItem('${item[2]}', ${item[3]})">
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
        if (!confirm(`Вывести ${itemName} (${itemValue} звёзд)?\n\nАдминистратор свяжется с вами для отправки приза.`)) {
            return;
        }

        try {
            const result = await this.makeRequest('withdraw', {
                method: 'POST',
                body: JSON.stringify({
                    user_id: this.user.id,
                    username: this.user.username,
                    item_name: itemName,
                    item_value: itemValue
                })
            });

            if (result.status === 'withdrawal_created') {
                this.showSuccess('✅ Заявка на вывод создана! Администратор свяжется с вами.');
                this.closeModals();
                await this.loadInventory(); // Обновляем инвентарь
            } else {
                this.showError('Ошибка при создании заявки');
            }

        } catch (error) {
            this.showError('Ошибка при выводе предмета');
        }
    }

    showWinModal(item) {
        this.tg.BackButton.show();
        const winItem = document.getElementById('win-item');
        winItem.innerHTML = `
            <div class="win-emoji">${item.emoji}</div>
            <h3>${item.name}</h3>
            <p class="win-value">${item.value} звёзд</p>
        `;
        
        document.getElementById('win-modal').classList.remove('hidden');
    }

    updateBalanceDisplay() {
        document.getElementById('balance').textContent = this.balance;
    }

    showError(message) {
        alert(`❌ ${message}`);
    }

    showSuccess(message) {
        alert(`✅ ${message}`);
    }
}

// Инициализация приложения
let app;
document.addEventListener('DOMContentLoaded', () => {
    app = new GhostFluxApp();
});