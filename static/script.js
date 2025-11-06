const chatMessages = document.getElementById('chatMessages');
const messageInput = document.getElementById('messageInput');
const sendBtn = document.getElementById('sendBtn');
const clearBtn = document.getElementById('clearBtn');

function addMessage(text, isUser) {
    const messageDiv = document.createElement('div');
    messageDiv.className = `message ${isUser ? 'user' : 'assistant'}`;
    
    const contentDiv = document.createElement('div');
    contentDiv.className = 'message-content';
    
    if (isUser) {
        contentDiv.textContent = text;
    } else {
        // Пытаемся распарсить JSON
        try {
            const jsonData = JSON.parse(text);
            contentDiv.innerHTML = formatJSONResponse(jsonData, text);
        } catch (e) {
            // Если не JSON - выводим как обычный текст
            contentDiv.textContent = text;
        }
    }
    
    messageDiv.appendChild(contentDiv);
    chatMessages.appendChild(messageDiv);
    
    // Прокрутка вниз
    chatMessages.scrollTop = chatMessages.scrollHeight;
    
    // Инициализация спойлеров после добавления сообщения
    initSpoilers();
}

function formatJSONResponse(data, rawJSON) {
    let html = '<div class="json-response">';
    
    // Если есть ошибка
    if (data.error) {
        html += `<div class="json-error">⚠️ ${escapeHtml(data.error)}</div>`;
    } else {
        // Красивое отображение данных
        html += '<div class="json-data">';
        
        if (data.title) {
            html += `<div class="json-field"><span class="json-label">🎬 Фильм:</span> <span class="json-value">${escapeHtml(data.title)}</span></div>`;
        }
        
        if (data.release) {
            html += `<div class="json-field"><span class="json-label">📅 Год:</span> <span class="json-value">${escapeHtml(data.release)}</span></div>`;
        }
        
        if (data.rating) {
            html += `<div class="json-field"><span class="json-label">⭐ Рейтинг:</span> <span class="json-value">${escapeHtml(data.rating)}</span></div>`;
        }
        
        if (data.producer) {
            html += `<div class="json-field"><span class="json-label">🎭 Режиссёр:</span> <span class="json-value">${escapeHtml(data.producer)}</span></div>`;
        }
        
        if (data.actors && Array.isArray(data.actors) && data.actors.length > 0) {
            html += '<div class="json-field"><span class="json-label">👥 Актёры:</span> <span class="json-value">';
            const actorsList = data.actors.map(actor => {
                const name = actor.firstName && actor.lastName 
                    ? `${escapeHtml(actor.firstName)} ${escapeHtml(actor.lastName)}`
                    : (actor.firstName || actor.lastName || '');
                return name;
            }).filter(Boolean);
            html += actorsList.join(', ') || '-';
            html += '</span></div>';
        }
        
        if (data.description) {
            html += `<div class="json-field json-description"><span class="json-label">📝 Описание:</span> <span class="json-value">${escapeHtml(data.description)}</span></div>`;
        }
        
        html += '</div>';
    }
    
    // Спойлер с JSON
    html += `
        <details class="json-spoiler">
            <summary class="json-spoiler-toggle">📄 Показать JSON</summary>
            <pre class="json-raw">${escapeHtml(rawJSON)}</pre>
        </details>
    `;
    
    html += '</div>';
    return html;
}

function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

function initSpoilers() {
    // Добавляем обработчики для спойлеров
    const spoilers = document.querySelectorAll('.json-spoiler');
    spoilers.forEach(spoiler => {
        const summary = spoiler.querySelector('summary');
        if (summary && !summary.dataset.listenerAdded) {
            summary.dataset.listenerAdded = 'true';
            summary.addEventListener('click', function() {
                setTimeout(() => {
                    chatMessages.scrollTop = chatMessages.scrollHeight;
                }, 100);
            });
        }
    });
}

function showLoading() {
    const messageDiv = document.createElement('div');
    messageDiv.className = 'message assistant';
    messageDiv.id = 'loadingMessage';
    
    const contentDiv = document.createElement('div');
    contentDiv.className = 'message-content';
    contentDiv.innerHTML = '<div class="loading"></div>';
    
    messageDiv.appendChild(contentDiv);
    chatMessages.appendChild(messageDiv);
    chatMessages.scrollTop = chatMessages.scrollHeight;
}

function removeLoading() {
    const loadingMessage = document.getElementById('loadingMessage');
    if (loadingMessage) {
        loadingMessage.remove();
    }
}

async function sendMessage() {
    const message = messageInput.value.trim();
    if (!message) return;
    
    // Добавляем сообщение пользователя
    addMessage(message, true);
    messageInput.value = '';
    sendBtn.disabled = true;
    
    // Показываем индикатор загрузки
    showLoading();
    
    try {
        const response = await fetch('/chat', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ message: message })
        });
        
        const data = await response.json();
        
        removeLoading();
        
        if (response.ok) {
            addMessage(data.response, false);
        } else {
            addMessage(`Ошибка: ${data.error || 'Неизвестная ошибка'}`, false);
        }
    } catch (error) {
        removeLoading();
        addMessage(`Ошибка подключения: ${error.message}`, false);
    } finally {
        sendBtn.disabled = false;
        messageInput.focus();
    }
}

async function clearHistory() {
    if (!confirm('Очистить историю чата?')) return;
    
    try {
        await fetch('/clear', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            }
        });
        
        chatMessages.innerHTML = `
            <div class="message assistant">
                <div class="message-content">Привет! Я агент Смит, твой личный справочник по фильмам. По какому хочешь получить информацию?</div>
                </div>
        `;
    } catch (error) {
        console.error('Ошибка при очистке:', error);
    }
}

// Обработчики событий
sendBtn.addEventListener('click', sendMessage);
clearBtn.addEventListener('click', clearHistory);

messageInput.addEventListener('keypress', (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault();
        sendMessage();
    }
});

// Фокус на поле ввода при загрузке
messageInput.focus();

