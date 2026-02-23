const tg = window.Telegram.WebApp;
tg.ready();
tg.expand();

const user = tg.initDataUnsafe?.user;
const telegramId = user?.id || 0;

// Установка аватара и имени пользователя
function setupProfile() {
    if (user) {
        const avatarUrl = user.photo_url || 'https://via.placeholder.com/56/7c3aed/f5f3ff?text=👤';
        const fullName = [user.first_name, user.last_name].filter(Boolean).join(' ') || 'Гость';
        
        // Маленький аватар в шапке
        document.getElementById('profile-avatar').src = avatarUrl;
        document.getElementById('profile-name').textContent = user.first_name || 'Профиль';
        
        // Большой аватар в профиле
        document.getElementById('profile-avatar-large').src = avatarUrl;
        document.getElementById('profile-name-large').textContent = fullName;
    }
}

// Переключение профиля
function toggleProfile() {
    const dropdown = document.getElementById('profile-dropdown');
    dropdown.classList.toggle('show');
    
    // Закрыть при клике вне
    document.addEventListener('click', function closeProfile(e) {
        if (!dropdown.contains(e.target) && !e.target.closest('.profile-btn')) {
            dropdown.classList.remove('show');
            document.removeEventListener('click', closeProfile);
        }
    });
}

// Навигация по страницам
function initNavigation() {
    const navButtons = document.querySelectorAll('.nav-btn');
    const pages = document.querySelectorAll('.page');
    
    navButtons.forEach(btn => {
        btn.addEventListener('click', function() {
            const targetPage = this.dataset.page;
            
            navButtons.forEach(b => b.classList.remove('active'));
            pages.forEach(p => p.classList.remove('active'));
            
            this.classList.add('active');
            const targetElement = document.getElementById(targetPage);
            if (targetElement) {
                targetElement.classList.add('active');
            }
            
            if (tg.HapticFeedback && tg.HapticFeedback.impactOccurred) {
                tg.HapticFeedback.impactOccurred('light');
            }
            
            // Закрыть профиль если открыт
            document.getElementById('profile-dropdown').classList.remove('show');
            
            // Загрузить данные для страницы
            loadPageData(targetPage);
        });
    });
}

// Переход на страницу
function showPage(pageId) {
    const navButtons = document.querySelectorAll('.nav-btn');
    const pages = document.querySelectorAll('.page');
    
    navButtons.forEach(b => b.classList.remove('active'));
    pages.forEach(p => p.classList.remove('active'));
    
    const targetBtn = document.querySelector(`.nav-btn[data-page="${pageId}"]`);
    if (targetBtn) targetBtn.classList.add('active');
    
    const targetElement = document.getElementById(pageId);
    if (targetElement) {
        targetElement.classList.add('active');
    }
    
    document.getElementById('profile-dropdown').classList.remove('show');
    loadPageData(pageId);
}

function loadPageData(pageId) {
    switch(pageId) {
        case 'home-page':
            loadHome();
            break;
        case 'promotions-page':
            loadPromotions();
            break;
        case 'contacts-page':
            loadContacts();
            break;
        case 'menu-page':
            loadMenu();
            break;
        case 'bookings-page':
            loadBookings();
            break;
    }
}

// Устанавливаем текущую дату и время для формы бронирования
function setCurrentDateTime() {
    const dateTimeInput = document.getElementById("date_time");
    if (dateTimeInput) {
        const now = new Date();
        const year = now.getFullYear();
        const month = String(now.getMonth() + 1).padStart(2, '0');
        const day = String(now.getDate()).padStart(2, '0');
        const hours = String(now.getHours()).padStart(2, '0');
        const minutes = String(now.getMinutes()).padStart(2, '0');
        dateTimeInput.value = `${year}-${month}-${day}T${hours}:${minutes}`;
        dateTimeInput.min = `${year}-${month}-${day}T${hours}:${minutes}`;
    }
}

function esc(v) {
    return String(v ?? "").replace(/[&<>\"]/g, (m) => ({"&":"&amp;","<":"&lt;",">":"&gt;","\"":"&quot;"}[m]));
}

async function loadBootstrap() {
    if (!telegramId) {
        return;
    }

    const username = encodeURIComponent(user?.username || "");
    const fullName = encodeURIComponent([user?.first_name, user?.last_name].filter(Boolean).join(" "));
    
    try {
        const response = await fetch(`/api/bootstrap?telegram_id=${telegramId}&username=${username}&full_name=${fullName}`);
        if (!response.ok) return;
        
        const data = await response.json();
        
        // Сохраняем данные для использования
        window.bootstrapData = data;
        
        // Обновляем профиль
        updateProfile(data);
        
        // Загружаем данные для текущей активной страницы
        const activePage = document.querySelector('.page.active');
        if (activePage) {
            loadPageData(activePage.id);
        }
    } catch (error) {
        console.error('Error loading bootstrap:', error);
    }
}

function updateProfile(data) {
    const visits = data.visits || 0;
    
    // Обновляем счетчики на главной
    document.getElementById('home-visits').textContent = visits;
    
    // До следующего бонуса
    const nextBonus = visits < 5 ? 5 : 10;
    const untilBonus = nextBonus - visits;
    document.getElementById('home-next-bonus').textContent = Math.max(0, untilBonus);
    
    // Обновляем профиль - прогресс
    document.getElementById('profile-visits').textContent = `${visits} ${visits === 1 ? 'визит' : visits < 5 ? 'визита' : 'визитов'}`;
    
    // Прогресс лояльности
    const progressPercent = Math.min(100, (visits / 10) * 100);
    document.getElementById('profile-progress-fill').style.width = `${progressPercent}%`;
    document.getElementById('profile-progress-text').textContent = `${visits}/10 до бесплатного кальяна`;
    
    // Личная скидка (из notes)
    const personalDiscountEl = document.getElementById('profile-personal-discount');
    let personalDiscount = 0;
    
    // Проверяем notes на наличие personal_discount
    if (data.notes) {
        try {
            const notesData = typeof data.notes === 'string' ? JSON.parse(data.notes) : data.notes;
            personalDiscount = notesData.personal_discount || 0;
        } catch (e) {
            personalDiscount = 0;
        }
    }
    
    if (personalDiscount > 0) {
        personalDiscountEl.textContent = `🏷️ ${personalDiscount} ₽ на счёт`;
        personalDiscountEl.style.background = 'rgba(16, 185, 129, 0.2)';
    } else {
        personalDiscountEl.textContent = 'Нет личной скидки';
        personalDiscountEl.style.background = 'rgba(255, 149, 0, 0.1)';
    }
    
    // График на главной
    document.getElementById('home-schedule').textContent = data.schedule || 'Ежедневно с 14:00 до 2:00';
    
    // Показываем админ-панель только админам
    const adminIds = [1698158035, 987654321]; // Замени на свои ADMIN_IDS из .env
    if (adminIds.includes(telegramId)) {
        document.querySelector('.admin-only').style.display = 'flex';
    }
}

function loadHome() {
    const data = window.bootstrapData;
    if (!data) return;
    
    updateProfile(data);
}

function loadPromotions() {
    const data = window.bootstrapData;
    const container = document.getElementById("promotions-list");
    if (!container || !data) return;
    
    const promotions = data.promotions || [];
    container.innerHTML = promotions.length
        ? promotions.map((p) => `
            <div class='card'>
                <div style='font-size: 16px; font-weight: 700; color: var(--gold); margin-bottom: 6px;'>${esc(p.title)}</div>
                <div style='color: var(--text-secondary); line-height: 1.5;'>${esc(p.description)}</div>
            </div>`).join("")
        : "<div class='card' style='text-align: center; padding: 40px 20px;'>🎉 Акций пока нет</div>";
}

function loadContacts() {
    const data = window.bootstrapData;
    const container = document.getElementById("contacts-text");
    if (!container || !data) return;
    
    container.innerHTML = `
        <div style='font-size: 48px; margin-bottom: 20px;'>📍</div>
        <div style='font-size: 18px; font-weight: 700; color: var(--gold); margin-bottom: 16px;'>
            Филин Lounge Bar
        </div>
        <div style='font-size: 20px; margin-bottom: 8px;'>
            <a href='tel:+79504333434' style='color: var(--amber); text-decoration: none;'>
                📞 7-950-433-34-34
            </a>
        </div>
        <div style='color: var(--text-secondary); margin-top: 16px; font-style: italic; margin-bottom: 24px;'>
            🌙 Твой идеальный вечер
        </div>
        <a href='https://2gis.ru/krasnoyarsk/search/Филин%20центр%20паровых%20коктейлей/firm/70000001042591694/92.798474%2C56.025546?m=92.798522%2C56.025568%2F17.24' target='_blank' class='map-btn' style='
            display: flex;
            align-items: center;
            justify-content: center;
            gap: 10px;
            padding: 16px 24px;
            background: linear-gradient(135deg, var(--amber), var(--gold));
            color: #0a0510;
            text-decoration: none;
            border-radius: 12px;
            font-weight: 700;
            font-size: 14px;
            margin-top: 16px;
            transition: all 0.2s ease;
        '>
            🗺️ Показать на карте
        </a>
    `;
}

function loadMenu() {
    const data = window.bootstrapData;
    const container = document.getElementById("menu-list");
    if (!container || !data) return;
    
    const menu = data.menu || [];
    container.innerHTML = menu.length
        ? menu.map((m) => `
            <div class='card'>
                <div style='font-size: 16px; font-weight: 700; color: var(--gold); margin-bottom: 6px;'>
                    🦉 ${esc(m.title)}
                </div>
                <div style='font-size: 18px; color: var(--amber); font-weight: 600;'>${esc(m.description)}</div>
            </div>`).join("")
        : "<div class='card' style='text-align: center; padding: 40px 20px;'>🦉 Меню загружается...</div>";
}

function loadBookings() {
    const data = window.bootstrapData;
    const container = document.getElementById("bookings-list");
    if (!container || !data) return;
    
    const bookings = data.bookings || [];
    console.log("=== BOOKINGS DEBUG ===");
    console.log("All bookings:", bookings);
    
    container.innerHTML = bookings.length
        ? bookings.map((b) => {
            let statusClass = "status-pending";
            let statusIcon = "⏳";
            let cancelButton = "";
            
            console.log(`Booking #${b.id}: status="${b.status}", booking_at=${b.booking_at}`);
            
            if (b.status === "Бронь подтверждена" || b.status === "confirmed") {
                statusClass = "status-confirmed";
                statusIcon = "✅";
            } else if (b.status === "Выполнена" || b.status === "completed") {
                statusClass = "status-completed";
                statusIcon = "🟢";
            } else if (b.status === "Отменена" || b.status === "canceled") {
                statusClass = "status-canceled";
                statusIcon = "🔴";
            }
            
            const isPending = (b.status === "pending" || b.status === "Ожидает подтверждения");
            const isNotCanceled = (b.status !== "Отменена" && b.status !== "canceled");
            
            console.log(`  isPending=${isPending}, isNotCanceled=${isNotCanceled}`);
            
            if (isPending && isNotCanceled) {
                const bookingTime = new Date(b.booking_at);
                const now = new Date();
                const hoursUntilBooking = (bookingTime - now) / (1000 * 60 * 60);
                
                console.log(`  hoursUntilBooking=${hoursUntilBooking.toFixed(2)}`);
                
                if (hoursUntilBooking > 2) {
                    cancelButton = `
                        <button onclick="cancelBooking(${b.id})" class="cancel-btn">❌ Отменить бронь</button>
                    `;
                    console.log(`  Button added for booking #${b.id}`);
                } else {
                    console.log(`  Button NOT added: less than 2 hours (${hoursUntilBooking.toFixed(2)}h)`);
                }
            }
            
            return `
                <div class='card ${statusClass}'>
                    <div class='booking-header'>#${b.id} | Стол ${b.table_no}</div>
                    <div class='booking-details'>
                        <div>📅 Бронь на: ${new Date(b.booking_at).toLocaleString('ru-RU', {day: '2-digit', month: '2-digit', hour: '2-digit', minute: '2-digit'})}</div>
                        <div>🕐 Создана: ${new Date(b.created_at).toLocaleString('ru-RU', {day: '2-digit', month: '2-digit', hour: '2-digit', minute: '2-digit'})}</div>
                        <div class='booking-status'>${statusIcon} <b>${esc(b.status)}</b></div>
                    </div>
                    ${cancelButton}
                </div>`;
        }).join("")
        : "<div class='card' style='text-align: center; padding: 40px 20px;'>📋 Броней пока нет</div>";
    
    console.log("=== END BOOKINGS DEBUG ===");
}

// Функция отмены брони
async function cancelBooking(bookingId) {
    if (!confirm("Вы уверены, что хотите отменить бронь #" + bookingId + "?\n\nБронь будет отменена немедленно.")) return;

    try {
        const response = await fetch(`/api/bookings/${bookingId}/cancel`, {
            method: "POST",
            headers: {"Content-Type": "application/json"},
            body: JSON.stringify({telegram_id: telegramId}),
        });

        const result = await response.json();

        if (response.ok) {
            // Отправляем уведомление боту
            try {
                tg.sendData(JSON.stringify({
                    action: "booking_canceled",
                    booking_id: bookingId
                }));
            } catch (e) {
                console.error("Error sending data to bot:", e);
            }
            
            alert("✅ Бронь отменена!");
            if (tg.HapticFeedback) tg.HapticFeedback.notificationOccurred("success");
            
            // Обновляем данные и закрываем профиль
            setTimeout(() => {
                // Принудительно перезагружаем страницу для обновления данных
                window.location.reload();
            }, 1500);
        } else {
            alert("❌ " + (result.detail || "Ошибка при отмене брони"));
        }
    } catch (error) {
        console.error("Cancel booking error:", error);
        alert("❌ Ошибка сети: " + error.message);
    }
}

// Обработка формы бронирования
const bookingForm = document.getElementById("booking-form");
if (bookingForm) {
    bookingForm.addEventListener("submit", async (event) => {
        event.preventDefault();
        const statusNode = document.getElementById("booking-status");
        statusNode.textContent = "⏳ Создаем бронь...";

        const payload = {
            telegram_id: telegramId,
            username: user?.username || null,
            full_name: [user?.first_name, user?.last_name].filter(Boolean).join(" ") || null,
            phone: document.getElementById("phone").value.trim(),
            date_time: document.getElementById("date_time").value,
            table_no: Number(document.getElementById("table_no").value),
            guests: Number(document.getElementById("guests").value),
            comment: document.getElementById("comment").value || null
        };

        if (!payload.telegram_id) {
            statusNode.textContent = "❌ Ошибка: нужен Telegram";
            return;
        }
        if (!/^\+7\d{10}$/.test(payload.phone)) {
            statusNode.textContent = "❌ Введите телефон: +7XXXXXXXXXX";
            return;
        }

        try {
            const response = await fetch("/api/bookings", {
                method: "POST",
                headers: {"Content-Type": "application/json"},
                body: JSON.stringify(payload),
            });

            if (!response.ok) {
                const err = await response.json();
                statusNode.textContent = "❌ " + (err.detail || "Ошибка при создании брони");
                return;
            }

            const result = await response.json();
            statusNode.textContent = `✅ Бронь #${result.id} создана!`;

            if (tg.HapticFeedback && tg.HapticFeedback.notificationOccurred) {
                tg.HapticFeedback.notificationOccurred("success");
            }

            // Очищаем форму
            bookingForm.reset();
            setCurrentDateTime();

            // Отправляем данные боту для уведомления (закроет Web App)
            setTimeout(() => {
                tg.sendData(JSON.stringify({action: "booking_created", booking_id: result.id}));
            }, 500);
        } catch (error) {
            console.error("Booking error:", error);
            statusNode.textContent = "❌ Ошибка сети";
        }
    });
}

// Делаем функции глобальными
window.toggleProfile = toggleProfile;
window.showPage = showPage;
window.cancelBooking = cancelBooking;
window.openAdmin = openAdmin;

function openAdmin() {
    // Открываем админ-панель в новом окне Telegram WebApp
    const adminUrl = window.location.origin + '/admin';
    tg.openLink(adminUrl);
}

// Инициализация
initNavigation();
setupProfile();
setCurrentDateTime();
loadBootstrap();
