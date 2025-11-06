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
        // Универсальное отображение данных
        html += '<div class="json-data">';
        html += formatJSONValue(data, '');
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

function formatJSONValue(value, key = '') {
    if (value === null) {
        return `<div class="json-field"><span class="json-label">${formatKey(key)}:</span> <span class="json-value json-null">null</span></div>`;
    }
    
    if (Array.isArray(value)) {
        if (value.length === 0) {
            return `<div class="json-field"><span class="json-label">${formatKey(key)}:</span> <span class="json-value json-empty">(пусто)</span></div>`;
        }
        let html = `<div class="json-field json-array"><span class="json-label">${formatKey(key)}:</span> <div class="json-array-items">`;
        value.forEach((item, index) => {
            html += `<div class="json-array-item">`;
            if (typeof item === 'object' && item !== null) {
                // Для объектов в массиве не показываем ключ, только содержимое
                const objKeys = Object.keys(item);
                if (objKeys.length === 0) {
                    html += `<span class="json-value json-empty">(пусто)</span>`;
                } else {
                    objKeys.forEach(k => {
                        html += formatJSONValue(item[k], k);
                    });
                }
            } else {
                html += `<span class="json-value">${escapeHtml(String(item))}</span>`;
            }
            html += `</div>`;
        });
        html += '</div></div>';
        return html;
    }
    
    if (typeof value === 'object') {
        const keys = Object.keys(value);
        if (keys.length === 0) {
            return `<div class="json-field"><span class="json-label">${formatKey(key)}:</span> <span class="json-value json-empty">(пусто)</span></div>`;
        }
        let html = key ? `<div class="json-object"><div class="json-object-label">${formatKey(key)}:</div><div class="json-object-content">` : '';
        keys.forEach(k => {
            html += formatJSONValue(value[k], k);
        });
        html += key ? '</div></div>' : '';
        return html;
    }
    
    // Простые типы
    const displayValue = typeof value === 'boolean' 
        ? (value ? '✓ Да' : '✗ Нет')
        : escapeHtml(String(value));
    
    return `<div class="json-field"><span class="json-label">${formatKey(key)}:</span> <span class="json-value">${displayValue}</span></div>`;
}

function formatKey(key) {
    if (!key) return '';
    
    // Эмодзи для известных полей
    const emojiMap = {
        'title': '🎬',
        'release': '📅',
        'rating': '⭐',
        'producer': '🎭',
        'director': '🎭',
        'actors': '👥',
        'description': '📝',
        'error': '⚠️',
        'name': '👤',
        'year': '📅',
        'genre': '🎞️',
        'duration': '⏱️',
        'country': '🌍',
        'language': '🗣️'
    };
    
    const emoji = emojiMap[key.toLowerCase()] || '';
    const formattedKey = key.charAt(0).toUpperCase() + key.slice(1);
    return emoji ? `${emoji} ${formattedKey}` : formattedKey;
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

