const chatMessages = document.getElementById('chatMessages');
const messageInput = document.getElementById('messageInput');
const sendBtn = document.getElementById('sendBtn');
const clearBtn = document.getElementById('clearBtn');
const infoModeBtn = document.getElementById('infoModeBtn');
const recommendModeBtn = document.getElementById('recommendModeBtn');
const reasoningModeBtn = document.getElementById('reasoningModeBtn');
const temperatureModeBtn = document.getElementById('temperatureModeBtn');
const reasoningContainer = document.getElementById('reasoningContainer');
const temperatureContainer = document.getElementById('temperatureContainer');
const chatInputContainer = document.getElementById('chatInputContainer');
const taskInput = document.getElementById('taskInput');
const reasoningResults = document.getElementById('reasoningResults');
const temperaturePrompt = document.getElementById('temperaturePrompt');
const temperatureResults = document.getElementById('temperatureResults');
const runTemperatureBtn = document.getElementById('runTemperatureBtn');

// Текущий режим работы: 'info', 'recommend', 'reasoning' или 'temperature'
let currentMode = 'info';

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

            // Проверяем, является ли это выбором фильмов
            if (jsonData.type === 'movie_selection' && jsonData.movies) {
                contentDiv.innerHTML = formatMovieSelection(jsonData);
            } else {
                contentDiv.innerHTML = formatJSONResponse(jsonData, text);
            }
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

function formatMovieSelection(data) {
    let html = '<div class="movie-selection">';

    // Сообщение
    if (data.message) {
        html += `<p class="selection-message">${escapeHtml(data.message)}</p>`;
    }

    // Счетчик выбранных фильмов
    html += '<div class="selection-counter">Выбрано: <span id="selectedCount">0</span> / 4</div>';

    // Кнопки с фильмами
    html += '<div class="movie-buttons">';
    data.movies.forEach((movie, index) => {
        html += `<button class="movie-btn" data-movie="${escapeHtml(movie)}" data-index="${index}">
            ${escapeHtml(movie)}
        </button>`;
    });
    html += '</div>';

    // Кнопка подтверждения выбора
    html += '<button class="confirm-selection-btn" id="confirmSelection" disabled>Подтвердить выбор</button>';

    html += '</div>';

    // Добавляем обработчики после рендера
    setTimeout(() => {
        initMovieSelection();
    }, 100);

    return html;
}

function initMovieSelection() {
    const movieButtons = document.querySelectorAll('.movie-btn');
    const confirmBtn = document.getElementById('confirmSelection');
    const counterSpan = document.getElementById('selectedCount');
    let selectedMovies = [];

    movieButtons.forEach(btn => {
        btn.addEventListener('click', function() {
            const movieName = this.dataset.movie;

            if (this.classList.contains('selected')) {
                // Убираем выбор
                this.classList.remove('selected');
                selectedMovies = selectedMovies.filter(m => m !== movieName);
            } else {
                // Добавляем выбор, но не больше 4
                if (selectedMovies.length < 4) {
                    this.classList.add('selected');
                    selectedMovies.push(movieName);
                }
            }

            // Обновляем счетчик
            counterSpan.textContent = selectedMovies.length;

            // Активируем кнопку подтверждения, если выбрано ровно 4
            if (selectedMovies.length === 4) {
                confirmBtn.disabled = false;
            } else {
                confirmBtn.disabled = true;
            }
        });
    });

    if (confirmBtn && !confirmBtn.dataset.listenerAdded) {
        confirmBtn.dataset.listenerAdded = 'true';
        confirmBtn.addEventListener('click', async function() {
            // Отключаем все кнопки
            movieButtons.forEach(btn => btn.disabled = true);
            confirmBtn.disabled = true;

            // Формируем сообщение с выбранными фильмами
            const message = `Я выбрал: ${selectedMovies.join(', ')}`;

            // Добавляем сообщение пользователя
            addMessage(message, true);

            // Отправляем выбранные фильмы агенту
            sendBtn.disabled = true;
            showLoading();

            try {
                const response = await fetch('/recommend', {
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
            }
        });
    }
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

async function solveTask(method) {
    const task = taskInput.value.trim();
    if (!task) {
        alert('Пожалуйста, введите задачу для решения');
        return;
    }

    // Отключаем кнопки и показываем загрузку
    const methodButtons = document.querySelectorAll('.method-btn');
    methodButtons.forEach(btn => btn.disabled = true);
    taskInput.disabled = true;

    reasoningResults.innerHTML = '<div class="loading-reasoning">⏳ Решаю задачу, это может занять некоторое время...</div>';

    try {
        const response = await fetch('/reasoning', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ task: task, method: method })
        });

        const data = await response.json();

        if (response.ok) {
            displayReasoningResults(data);
        } else {
            reasoningResults.innerHTML = `<div class="error">Ошибка: ${data.error || 'Неизвестная ошибка'}</div>`;
        }
    } catch (error) {
        reasoningResults.innerHTML = `<div class="error">Ошибка подключения: ${error.message}</div>`;
    } finally {
        methodButtons.forEach(btn => btn.disabled = false);
        taskInput.disabled = false;
    }
}

function displayReasoningResults(data) {
    let html = '<div class="results-header">';
    html += `<h3>Задача: ${escapeHtml(data.task)}</h3>`;
    html += '</div>';

    html += '<div class="results-container">';

    const methodNames = {
        'direct': '1️⃣ Прямой ответ',
        'step_by_step': '2️⃣ Пошаговое решение',
        'prompt_generator': '3️⃣ С промптом от ИИ',
        'expert_panel': '4️⃣ Группа экспертов (🔬 Физик, 👵 Бабушка, 👦 Ребёнок, 🤖 Робот)'
    };

    for (const [method, result] of Object.entries(data.results)) {
        html += '<div class="result-card">';
        html += `<h4>${methodNames[method] || method}</h4>`;
        html += '<div class="result-content">';
        html += `<pre>${escapeHtml(result)}</pre>`;
        html += '</div>';
        html += '</div>';
    }

    html += '</div>';

    reasoningResults.innerHTML = html;
}

async function runTemperatureExperiment() {
    const prompt = temperaturePrompt.value.trim();
    if (!prompt) {
        alert('Пожалуйста, введите запрос для тестирования');
        return;
    }

    // Отключаем кнопку и показываем загрузку
    runTemperatureBtn.disabled = true;
    temperaturePrompt.disabled = true;
    temperatureResults.innerHTML = '<div class="loading-temperature">⏳ Запускаю эксперимент с разными температурами...<br>Это может занять некоторое время, так как делается 3 запроса к API</div>';

    try {
        const response = await fetch('/temperature_experiment', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ prompt: prompt })
        });

        const data = await response.json();

        if (response.ok) {
            displayTemperatureResults(data);
        } else {
            temperatureResults.innerHTML = `<div class="error">Ошибка: ${data.error || 'Неизвестная ошибка'}</div>`;
        }
    } catch (error) {
        temperatureResults.innerHTML = `<div class="error">Ошибка подключения: ${error.message}</div>`;
    } finally {
        runTemperatureBtn.disabled = false;
        temperaturePrompt.disabled = false;
    }
}

function displayTemperatureResults(data) {
    let html = '<div class="temperature-results-header">';
    html += `<h3>📊 Результаты эксперимента</h3>`;
    html += `<p class="experiment-prompt"><strong>Запрос:</strong> ${escapeHtml(data.prompt)}</p>`;
    html += '</div>';

    html += '<div class="temperature-cards-container">';

    // Температура 0.0
    html += '<div class="temperature-card temp-cold">';
    html += '<div class="temp-header">';
    html += '<div class="temp-value">🧊 Температура: 0.0</div>';
    html += '<div class="temp-label">Детерминированный</div>';
    html += '</div>';
    html += '<div class="temp-description">';
    html += `<p>${escapeHtml(data.temperatures['0.0'].description)}</p>`;
    html += '</div>';
    html += '<div class="temp-response">';
    html += `<pre>${escapeHtml(data.temperatures['0.0'].response)}</pre>`;
    html += '</div>';
    html += '</div>';

    // Температура 0.7
    html += '<div class="temperature-card temp-medium">';
    html += '<div class="temp-header">';
    html += '<div class="temp-value">🌤️ Температура: 0.7</div>';
    html += '<div class="temp-label">Сбалансированный</div>';
    html += '</div>';
    html += '<div class="temp-description">';
    html += `<p>${escapeHtml(data.temperatures['0.7'].description)}</p>`;
    html += '</div>';
    html += '<div class="temp-response">';
    html += `<pre>${escapeHtml(data.temperatures['0.7'].response)}</pre>`;
    html += '</div>';
    html += '</div>';

    // Температура 1.0
    html += '<div class="temperature-card temp-hot">';
    html += '<div class="temp-header">';
    html += '<div class="temp-value">🔥 Температура: 1.0</div>';
    html += '<div class="temp-label">Креативный</div>';
    html += '</div>';
    html += '<div class="temp-description">';
    html += `<p>${escapeHtml(data.temperatures['1.0'].description)}</p>`;
    html += '</div>';
    html += '<div class="temp-response">';
    html += `<pre>${escapeHtml(data.temperatures['1.0'].response)}</pre>`;
    html += '</div>';
    html += '</div>';

    html += '</div>';

    // Рекомендации
    html += '<div class="temperature-recommendations">';
    html += '<h3>💡 Рекомендации по использованию</h3>';
    html += '<div class="recommendations-grid">';

    html += '<div class="recommendation-card rec-cold">';
    html += '<h4>🧊 Температура 0.0</h4>';
    html += `<p>${escapeHtml(data.recommendations['0.0'])}</p>`;
    html += '</div>';

    html += '<div class="recommendation-card rec-medium">';
    html += '<h4>🌤️ Температура 0.7</h4>';
    html += `<p>${escapeHtml(data.recommendations['0.7'])}</p>`;
    html += '</div>';

    html += '<div class="recommendation-card rec-hot">';
    html += '<h4>🔥 Температура 1.0</h4>';
    html += `<p>${escapeHtml(data.recommendations['1.0'])}</p>`;
    html += '</div>';

    html += '</div>';
    html += '</div>';

    // Выводы
    html += '<div class="temperature-conclusions">';
    html += '<h3>📝 Выводы</h3>';
    html += '<ul>';
    html += '<li><strong>Точность:</strong> При температуре 0.0 модель дает наиболее предсказуемые и точные ответы, идеально для фактических запросов.</li>';
    html += '<li><strong>Креативность:</strong> При температуре 1.0 модель проявляет максимальную креативность и разнообразие, отлично для творческих задач.</li>';
    html += '<li><strong>Баланс:</strong> Температура 0.7 обеспечивает хороший баланс между точностью и креативностью, подходит для большинства задач.</li>';
    html += '<li><strong>Разнообразие:</strong> Чем выше температура (в диапазоне 0.0-1.0), тем больше вариативность ответов при повторных запросах.</li>';
    html += '</ul>';
    html += '</div>';

    temperatureResults.innerHTML = html;
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
        // Выбираем endpoint в зависимости от режима
        const endpoint = currentMode === 'recommend' ? '/recommend' : '/chat';

        const response = await fetch(endpoint, {
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

function switchMode(mode) {
    currentMode = mode;

    // Обновляем активную кнопку
    infoModeBtn.classList.remove('active');
    recommendModeBtn.classList.remove('active');
    if (reasoningModeBtn) {
        reasoningModeBtn.classList.remove('active');
    }
    if (temperatureModeBtn) {
        temperatureModeBtn.classList.remove('active');
    }

    if (mode === 'info') {
        infoModeBtn.classList.add('active');
    } else if (mode === 'recommend') {
        recommendModeBtn.classList.add('active');
    } else if (mode === 'reasoning' && reasoningModeBtn) {
        reasoningModeBtn.classList.add('active');
    } else if (mode === 'temperature' && temperatureModeBtn) {
        temperatureModeBtn.classList.add('active');
    }

    // Показываем/скрываем интерфейсы
    if (mode === 'reasoning' && reasoningContainer && chatInputContainer) {
        chatMessages.style.display = 'none';
        chatInputContainer.style.display = 'none';
        reasoningContainer.style.display = 'block';
        if (temperatureContainer) {
            temperatureContainer.style.display = 'none';
        }
        if (reasoningResults) {
            reasoningResults.innerHTML = '';
        }
        if (taskInput) {
            taskInput.value = '';
        }
    } else if (mode === 'temperature' && temperatureContainer && chatInputContainer) {
        chatMessages.style.display = 'none';
        chatInputContainer.style.display = 'none';
        if (reasoningContainer) {
            reasoningContainer.style.display = 'none';
        }
        temperatureContainer.style.display = 'block';
        if (temperatureResults) {
            temperatureResults.innerHTML = '';
        }
        if (temperaturePrompt) {
            temperaturePrompt.value = '';
        }
    } else {
        chatMessages.style.display = 'flex';
        if (chatInputContainer) {
            chatInputContainer.style.display = 'flex';
        }
        if (reasoningContainer) {
            reasoningContainer.style.display = 'none';
        }
        if (temperatureContainer) {
            temperatureContainer.style.display = 'none';
        }

        // Очищаем чат и показываем приветственное сообщение
        if (mode === 'info') {
            chatMessages.innerHTML = `
                <div class="message assistant">
                    <div class="message-content">Привет! Я агент Смит, твой справочник по фильмам. Введи название фильма.</div>
                </div>
            `;
            // Очищаем историю на сервере
            fetch('/clear', { method: 'POST' }).catch(console.error);
        } else if (mode === 'recommend') {
            chatMessages.innerHTML = `
                <div class="message assistant">
                    <div class="message-content">Привет! Я помогу тебе подобрать идеальный фильм. Расскажи, что тебе нравится, в какой компании будешь смотреть и какое у тебя настроение? 🎬</div>
                </div>
            `;
            // Очищаем историю рекомендаций на сервере
            fetch('/clear_recommendations', { method: 'POST' }).catch(console.error);
        }
    }
}

async function clearHistory() {
    if (!confirm('Очистить историю чата?')) return;

    try {
        const endpoint = currentMode === 'recommend' ? '/clear_recommendations' : '/clear';
        await fetch(endpoint, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            }
        });

        // Показываем приветственное сообщение в зависимости от режима
        if (currentMode === 'info') {
            chatMessages.innerHTML = `
                <div class="message assistant">
                    <div class="message-content">Привет! Я агент Смит, твой справочник по фильмам. Введи название фильма.</div>
                </div>
            `;
        } else {
            chatMessages.innerHTML = `
                <div class="message assistant">
                    <div class="message-content">Привет! Я помогу тебе подобрать идеальный фильм. Расскажи, что тебе нравится, в какой компании будешь смотреть и какое у тебя настроение? 🎬</div>
                </div>
            `;
        }
    } catch (error) {
        console.error('Ошибка при очистке:', error);
    }
}

// Обработчики событий
sendBtn.addEventListener('click', sendMessage);
clearBtn.addEventListener('click', clearHistory);
infoModeBtn.addEventListener('click', () => switchMode('info'));
recommendModeBtn.addEventListener('click', () => switchMode('recommend'));
if (reasoningModeBtn) {
    reasoningModeBtn.addEventListener('click', () => switchMode('reasoning'));
}
if (temperatureModeBtn) {
    temperatureModeBtn.addEventListener('click', () => switchMode('temperature'));
}
if (runTemperatureBtn) {
    runTemperatureBtn.addEventListener('click', runTemperatureExperiment);
}

messageInput.addEventListener('keypress', (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault();
        sendMessage();
    }
});

// Обработчики для кнопок методов рассуждения
document.addEventListener('click', (e) => {
    if (e.target.classList.contains('method-btn')) {
        const method = e.target.dataset.method;
        solveTask(method);
    }
});

// Фокус на поле ввода при загрузке
messageInput.focus();

