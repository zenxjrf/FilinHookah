const tg = window.Telegram.WebApp;
tg.ready();

let currentDate = new Date().toISOString().split('T')[0];
let allGuests = [];
let ws = null;

// Инициализация
document.addEventListener('DOMContentLoaded', () => {
    document.getElementById('calendar-date').value = currentDate;
    loadDashboard();
    loadTables();
    loadCalendar();
    loadEvents();
    loadGuests();
    connectWebSocket();
});

// WebSocket подключение для реального времени
function connectWebSocket() {
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const wsUrl = `${protocol}//${window.location.host}/ws/admin`;
    
    ws = new WebSocket(wsUrl);
    
    ws.onopen = () => {
        console.log('WebSocket connected');
        // Отправляем ping для поддержания соединения
        setInterval(() => {
            if (ws.readyState === WebSocket.OPEN) {
                ws.send(JSON.stringify({ type: 'ping' }));
            }
        }, 30000);
    };
    
    ws.onmessage = (event) => {
        try {
            const message = JSON.parse(event.data);
            console.log('WebSocket message:', message);
            
            if (message.type === 'booking_update') {
                // Обновляем данные при изменении брони
                loadTables();
                loadCalendar();
                loadDashboard();
                
                // Показываем уведомление
                showNotification(`Бронь #${message.booking_id}: ${message.action}`, message.status);
            }
        } catch (e) {
            console.error('Error processing WebSocket message:', e);
        }
    };
    
    ws.onclose = () => {
        console.log('WebSocket disconnected. Reconnecting in 5s...');
        setTimeout(connectWebSocket, 5000);
    };
    
    ws.onerror = (error) => {
        console.error('WebSocket error:', error);
    };
}

function showNotification(title, status) {
    // Визуальное уведомление
    const notification = document.createElement('div');
    notification.className = 'notification';
    notification.innerHTML = `<strong>${title}</strong>`;
    notification.style.cssText = `
        position: fixed;
        top: 80px;
        right: 20px;
        padding: 16px 24px;
        background: ${status === 'confirmed' ? 'var(--success)' : status === 'canceled' ? 'var(--danger)' : 'var(--gold)'};
        color: white;
        border-radius: 12px;
        z-index: 10000;
        animation: slideIn 0.3s ease;
        box-shadow: 0 4px 20px rgba(0,0,0,0.3);
    `;
    document.body.appendChild(notification);
    setTimeout(() => notification.remove(), 3000);
}

// Загрузка дашборда
async function loadDashboard() {
    try {
        const response = await fetch('/api/admin/stats');
        const stats = await response.json();
        
        document.getElementById('stat-total').textContent = stats.total_bookings || 0;
        document.getElementById('stat-now').textContent = stats.now_in_restaurant || 0;
        document.getElementById('stat-expecting').textContent = stats.expecting || 0;
        document.getElementById('stat-free').textContent = stats.free_tables || 8;
    } catch (error) {
        console.error('Error loading dashboard:', error);
    }
}

// Загрузка таблицы столов
async function loadTables() {
    try {
        const response = await fetch(`/api/admin/tables?date=${currentDate}`);
        const data = await response.json();
        
        const grid = document.getElementById('tables-grid');
        grid.innerHTML = '';
        
        for (let tableNo = 1; tableNo <= 8; tableNo++) {
            const tableData = data.tables[tableNo] || [];
            const status = getTableStatus(tableData);
            
            const card = document.createElement('div');
            card.className = `table-card ${status}`;
            card.onclick = () => showTableDetails(tableNo, tableData);
            
            card.innerHTML = `
                <div class="table-number">Стол ${tableNo}</div>
                <div class="table-status">${getStatusText(status)}</div>
            `;
            
            grid.appendChild(card);
        }
    } catch (error) {
        console.error('Error loading tables:', error);
    }
}

function getTableStatus(bookings) {
    if (bookings.some(b => b.is_blocked)) return 'blocked';
    if (bookings.some(b => b.is_occupied)) return 'occupied';
    // Показываем booked только для активных броней (не completed и не canceled)
    if (bookings.some(b => b.status === 'pending' || b.status === 'confirmed')) return 'booked';
    return 'free';
}

function getStatusText(status) {
    const texts = {
        free: 'Свободен',
        booked: 'Бронь',
        occupied: 'Занят',
        blocked: 'Заблокирован'
    };
    return texts[status] || status;
}

function showTableDetails(tableNo, bookings) {
    const currentStatus = getTableStatus(bookings);
    
    const message = `Стол ${tableNo}\n\nТекущий статус: ${getStatusText(currentStatus)}\nБроней: ${bookings.length}\n\nВыберите действие:`;
    
    // Создаём кастомное модальное окно с кнопками
    const modal = document.createElement('div');
    modal.className = 'modal show';
    modal.innerHTML = `
        <div class="modal-content">
            <h3>🪑 Стол ${tableNo}</h3>
            <p style="color: var(--text-secondary); margin-bottom: 20px;">${message}</p>
            <div style="display: flex; flex-direction: column; gap: 12px;">
                <button class="primary" onclick="bookTable(${tableNo})" style="padding: 14px; background: linear-gradient(135deg, var(--amber), var(--gold)); color: #0a0510; border: none; border-radius: 12px; cursor: pointer; font-weight: 700; font-size: 14px;">
                    📅 Забронировать (гости придут)
                </button>
                <button onclick="markTableOccupied(${tableNo})" style="padding: 14px; background: rgba(239, 68, 68, 0.2); color: var(--danger); border: 1px solid var(--danger); border-radius: 12px; cursor: pointer; font-weight: 700; font-size: 14px;">
                    🔴 Занят (гости без брони)
                </button>
                <button onclick="freeTable(${tableNo})" style="padding: 14px; background: rgba(16, 185, 129, 0.2); color: var(--success); border: 1px solid var(--success); border-radius: 12px; cursor: pointer; font-weight: 700; font-size: 14px;">
                    🟢 Освободить (гости ушли)
                </button>
                <button onclick="closeModal()" style="padding: 12px; background: transparent; color: var(--text-muted); border: 1px solid var(--border); border-radius: 12px; cursor: pointer; font-size: 14px;">
                    Отмена
                </button>
            </div>
        </div>
    `;
    document.body.appendChild(modal);
    
    modal.addEventListener('click', (e) => {
        if (e.target === modal) closeModal();
    });
}

function closeModal() {
    document.querySelectorAll('.modal').forEach(m => {
        if (!m.querySelector('#event-modal') && !m.querySelector('#notes-modal')) {
            m.remove();
        }
    });
}

async function bookTable(tableNo) {
    closeModal();
    const datetime = prompt("Введите дату и время брони (YYYY-MM-DD HH:MM):", new Date().toISOString().slice(0, 16).replace('T', ' '));
    if (!datetime) return;
    
    const guests = prompt("Количество гостей:", "2");
    
    try {
        await fetch('/api/admin/tables/book', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ 
                table_no: tableNo, 
                datetime: datetime,
                guests: parseInt(guests) || 2
            })
        });
        loadTables();
        loadCalendar();
        alert(`✅ Стол ${tableNo} забронирован на ${datetime}`);
    } catch (error) {
        alert('Ошибка при бронировании стола');
    }
}

async function markTableOccupied(tableNo) {
    closeModal();
    if (!confirm(`Отметить стол ${tableNo} как занятый (гости без брони)?`)) return;
    
    try {
        await fetch('/api/admin/tables/occupy', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ table_no: tableNo })
        });
        loadTables();
        loadCalendar();
        alert(`🔴 Стол ${tableNo} отмечен как занятый`);
    } catch (error) {
        alert('Ошибка при отметке стола');
    }
}

async function freeTable(tableNo) {
    closeModal();
    
    const action = confirm(`Освободить стол ${tableNo}?\n\nOK - Гости ушли (закрыть брони)\nОтмена - Отменить будущие брони`);
    
    try {
        await fetch(`/api/admin/tables/${tableNo}/free`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ close_all: action })
        });
        loadTables();
        loadCalendar();
        alert(`🟢 Стол ${tableNo} освобождён`);
    } catch (error) {
        alert('Ошибка при освобождении стола');
    }
}

// Календарь
function changeDate(delta) {
    const date = new Date(currentDate);
    date.setDate(date.getDate() + delta);
    currentDate = date.toISOString().split('T')[0];
    document.getElementById('calendar-date').value = currentDate;
    loadCalendar();
    loadTables();
}

async function loadCalendar() {
    try {
        const response = await fetch(`/api/admin/bookings?date=${currentDate}`);
        const bookings = await response.json();
        
        const list = document.getElementById('calendar-bookings');
        
        if (bookings.length === 0) {
            list.innerHTML = '<div style="text-align: center; color: var(--text-muted); padding: 20px;">Нет броней на этот день</div>';
            return;
        }
        
        list.innerHTML = bookings.map(b => {
            const statusColors = {
                'pending': 'rgba(245, 158, 11, 0.2)',
                'confirmed': 'rgba(16, 185, 129, 0.2)',
                'completed': 'rgba(124, 58, 237, 0.2)',
                'canceled': 'rgba(239, 68, 68, 0.2)'
            };
            
            return `
            <div class="booking-item" style="background: ${statusColors[b.status] || 'transparent'};">
                <div class="booking-info">
                    <div class="booking-time">🕐 ${formatTime(b.booking_at)}</div>
                    <div class="booking-details">
                        Стол ${b.table_no} | ${b.guests} гостей | ${b.client_name || 'Гость'}
                        <span style="color: var(--gold); margin-left: 8px;">(${b.status === 'completed' ? 'Закрыта' : b.status === 'confirmed' ? 'Подтверждена' : b.status === 'canceled' ? 'Отменена' : 'Ожидает'})</span>
                    </div>
                </div>
                <div class="booking-actions">
                    ${b.status === 'pending' ? `<button class="btn-sm btn-confirm" onclick="updateBookingStatus(${b.id}, 'confirmed')">✅</button>` : ''}
                    <button class="btn-sm btn-cancel" onclick="updateBookingStatus(${b.id}, 'canceled')">❌</button>
                    ${b.status === 'confirmed' ? `<button class="btn-sm btn-close" onclick="updateBookingStatus(${b.id}, 'completed')">🟢</button>` : ''}
                    ${b.status === 'completed' ? `<button class="btn-sm" style="background: #6d5a9e; color: white;" onclick="updateBookingStatus(${b.id}, 'pending')">🔄</button>` : ''}
                </div>
            </div>
        `}).join('');
    } catch (error) {
        console.error('Error loading calendar:', error);
    }
}

async function updateBookingStatus(bookingId, status) {
    if (!confirm(`Изменить статус брони на ${status}?`)) return;
    
    try {
        await fetch(`/api/admin/bookings/${bookingId}/status`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ status })
        });
        
        loadCalendar();
        loadTables();
        loadDashboard();
        
        if (status === 'completed') {
            showConfetti();
        }
    } catch (error) {
        alert('Ошибка при обновлении статуса');
    }
}

function exportToCSV() {
    const bookings = document.querySelectorAll('.booking-item');
    if (bookings.length === 0) {
        alert('Нет данных для экспорта');
        return;
    }
    
    let csv = 'ID;Время;Стол;Гостей;Клиент;Статус\n';
    bookings.forEach(item => {
        const time = item.querySelector('.booking-time')?.textContent || '';
        const details = item.querySelector('.booking-details')?.textContent || '';
        csv += `${time};${details};-\n`;
    });
    
    const blob = new Blob(['\ufeff' + csv], { type: 'text/csv;charset=utf-8;' });
    const link = document.createElement('a');
    link.href = URL.createObjectURL(blob);
    link.download = `bookings_${currentDate}.csv`;
    link.click();
}

// События
async function loadEvents() {
    try {
        const response = await fetch('/api/admin/events');
        const events = await response.json();
        
        const list = document.getElementById('events-list');
        
        if (events.length === 0) {
            list.innerHTML = '<div style="text-align: center; color: var(--text-muted); padding: 20px;">Нет событий</div>';
            return;
        }
        
        list.innerHTML = events.map(e => `
            <div class="event-item">
                <div class="event-title">🎉 ${e.title}</div>
                <div class="event-datetime">📅 ${formatDateTime(e.datetime)}</div>
                <div class="event-description">${e.description || ''}</div>
                <div class="event-actions" style="display: flex; gap: 8px; margin-top: 12px;">
                    <button class="btn-sm" onclick="editEvent(${e.id}, '${e.title}', '${e.description || ''}', '${e.datetime}')" style="background: var(--purple); color: white;">✏️</button>
                    <button class="btn-sm" onclick="deleteEvent(${e.id})" style="background: var(--danger); color: white;">🗑️</button>
                </div>
            </div>
        `).join('');
    } catch (error) {
        console.error('Error loading events:', error);
    }
}

function showAddEventForm() {
    document.getElementById('event-modal').classList.add('show');
}

function closeModal() {
    document.querySelectorAll('.modal').forEach(m => m.classList.remove('show'));
}

document.getElementById('event-form')?.addEventListener('submit', async (e) => {
    e.preventDefault();
    
    const eventData = {
        title: document.getElementById('event-title').value,
        datetime: document.getElementById('event-datetime').value,
        description: document.getElementById('event-description').value
    };
    
    const eventId = document.getElementById('event-id')?.value;
    
    try {
        if (eventId) {
            // Редактирование
            await fetch(`/api/admin/events/${eventId}`, {
                method: 'PUT',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(eventData)
            });
        } else {
            // Создание
            await fetch('/api/admin/events', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(eventData)
            });
        }
        
        closeModal();
        loadEvents();
        showConfetti();
    } catch (error) {
        alert('Ошибка при сохранении события');
    }
});

function editEvent(id, title, description, datetime) {
    document.getElementById('event-id').value = id;
    document.getElementById('event-title').value = title;
    document.getElementById('event-description').value = description;
    document.getElementById('event-datetime').value = datetime.replace(' ', 'T');
    document.getElementById('event-modal').classList.add('show');
}

function deleteEvent(id) {
    if (!confirm('Удалить это событие?')) return;
    
    fetch(`/api/admin/events/${id}`, {
        method: 'DELETE'
    }).then(() => {
        loadEvents();
    }).catch(() => {
        alert('Ошибка при удалении события');
    });
}

// Гости
async function loadGuests() {
    try {
        const response = await fetch('/api/admin/guests');
        allGuests = await response.json();
        renderGuests(allGuests);
    } catch (error) {
        console.error('Error loading guests:', error);
    }
}

function setGuestDiscount(clientId, clientName, currentDiscount) {
    const discount = prompt(`Установить личную скидку для ${clientName}:\n\nТекущая: ${currentDiscount} ₽\n\nВведите новую сумму в рублях:`, currentDiscount);
    if (discount === null) return;
    
    const amount = parseInt(discount) || 0;
    
    fetch(`/api/admin/guests/${clientId}/discount`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ discount: amount })
    }).then(() => {
        loadGuests();
        alert(`Скидка ${amount} ₽ установлена для ${clientName}`);
    }).catch(() => {
        alert('Ошибка при установке скидки');
    });
}

function searchGuests() {
    const query = document.getElementById('guest-search').value.toLowerCase();
    
    const filtered = allGuests.filter(g => 
        g.name?.toLowerCase().includes(query) ||
        g.phone?.includes(query)
    );
    
    renderGuests(filtered);
}

function renderGuests(guests) {
    const list = document.getElementById('guests-list');
    
    if (guests.length === 0) {
        list.innerHTML = '<div style="text-align: center; color: var(--text-muted); padding: 20px;">Гости не найдены</div>';
        return;
    }
    
    list.innerHTML = guests.map(g => `
        <div class="guest-item">
            <div class="guest-info">
                <div class="guest-name">${g.name || 'Гость'}</div>
                <div class="guest-details">📞 ${g.phone || '—'} | 💎 ${g.visits || 0} визитов</div>
            </div>
            <div class="guest-actions">
                <button class="btn-sm" onclick="showGuestNotes(${g.id}, '${g.name || 'Гость'}')">📝</button>
                <button class="btn-sm btn-discount" onclick="setGuestDiscount(${g.id}, '${g.name || 'Гость'}', ${g.personal_discount || 0})">🏷️</button>
            </div>
        </div>
    `).join('');
}

function showGuestNotes(clientId, clientName) {
    document.getElementById('notes-client-id').value = clientId;
    document.getElementById('notes-modal').classList.add('show');
}

document.getElementById('notes-form')?.addEventListener('submit', async (e) => {
    e.preventDefault();
    
    const clientId = document.getElementById('notes-client-id').value;
    const notes = document.getElementById('notes-text').value;
    
    try {
        await fetch(`/api/admin/guests/${clientId}/notes`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ notes })
        });
        
        closeModal();
        loadGuests();
        alert('Заметка сохранена!');
    } catch (error) {
        alert('Ошибка при сохранении заметки');
    }
});

// Конфетти
function showConfetti() {
    const colors = ['#fbbf24', '#ff9500', '#7c3aed', '#10b981', '#ef4444'];
    
    for (let i = 0; i < 50; i++) {
        setTimeout(() => {
            const confetti = document.createElement('div');
            confetti.className = 'confetti';
            confetti.style.left = Math.random() * 100 + 'vw';
            confetti.style.background = colors[Math.floor(Math.random() * colors.length)];
            confetti.style.animationDuration = (Math.random() * 2 + 2) + 's';
            document.body.appendChild(confetti);
            
            setTimeout(() => confetti.remove(), 4000);
        }, i * 50);
    }
}

// Утилиты
function formatTime(isoString) {
    const date = new Date(isoString);
    return date.toLocaleTimeString('ru-RU', { hour: '2-digit', minute: '2-digit' });
}

function formatDateTime(isoString) {
    const date = new Date(isoString);
    return date.toLocaleString('ru-RU', { day: '2-digit', month: '2-digit', hour: '2-digit', minute: '2-digit' });
}

function closeAdmin() {
    tg.close();
}

// Закрытие модальных окон по клику вне
document.querySelectorAll('.modal').forEach(modal => {
    modal.addEventListener('click', (e) => {
        if (e.target === modal) closeModal();
    });
});
