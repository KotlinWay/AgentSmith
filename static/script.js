const chatMessages = document.getElementById('chatMessages');
const messageInput = document.getElementById('messageInput');
const sendBtn = document.getElementById('sendBtn');
const clearBtn = document.getElementById('clearBtn');

function addMessage(text, isUser) {
    const messageDiv = document.createElement('div');
    messageDiv.className = `message ${isUser ? 'user' : 'assistant'}`;
    
    const contentDiv = document.createElement('div');
    contentDiv.className = 'message-content';
    contentDiv.textContent = text;
    
    messageDiv.appendChild(contentDiv);
    chatMessages.appendChild(messageDiv);
    
    // Прокрутка вниз
    chatMessages.scrollTop = chatMessages.scrollHeight;
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

