const chatMessages = document.getElementById('chatMessages');
const messageInput = document.getElementById('messageInput');
const sendBtn = document.getElementById('sendBtn');
const clearBtn = document.getElementById('clearBtn');
const infoModeBtn = document.getElementById('infoModeBtn');
const recommendModeBtn = document.getElementById('recommendModeBtn');
const reasoningModeBtn = document.getElementById('reasoningModeBtn');
const temperatureModeBtn = document.getElementById('temperatureModeBtn');
const comparisonModeBtn = document.getElementById('comparisonModeBtn');
const tokensModeBtn = document.getElementById('tokensModeBtn');
const compressionModeBtn = document.getElementById('compressionModeBtn');
const reasoningContainer = document.getElementById('reasoningContainer');
const temperatureContainer = document.getElementById('temperatureContainer');
const comparisonContainer = document.getElementById('comparisonContainer');
const tokensContainer = document.getElementById('tokensContainer');
const compressionDialogContainer = document.getElementById('compressionDialogContainer');
const chatInputContainer = document.getElementById('chatInputContainer');
const taskInput = document.getElementById('taskInput');
const reasoningResults = document.getElementById('reasoningResults');
const temperaturePrompt = document.getElementById('temperaturePrompt');
const temperatureResults = document.getElementById('temperatureResults');
const runTemperatureBtn = document.getElementById('runTemperatureBtn');
const comparisonPrompt = document.getElementById('comparisonPrompt');
const comparisonResults = document.getElementById('comparisonResults');
const runComparisonBtn = document.getElementById('runComparisonBtn');

// Элементы режима сжатия
const compressionMessages = document.getElementById('compressionMessages');
const compressionMessageInput = document.getElementById('compressionMessageInput');
const compressionSendBtn = document.getElementById('compressionSendBtn');
const compressionCompareBtn = document.getElementById('compressionCompareBtn');
const compressionStatsBtn = document.getElementById('compressionStatsBtn');
const compressionClearBtn = document.getElementById('compressionClearBtn');
const compressionComparisonResults = document.getElementById('compressionComparisonResults');

// Текущий режим работы: 'info', 'recommend', 'reasoning', 'temperature', 'comparison', 'tokens' или 'compression'
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

    // Температура 0.5
    html += '<div class="temperature-card temp-medium">';
    html += '<div class="temp-header">';
    html += '<div class="temp-value">🌤️ Температура: 0.5</div>';
    html += '<div class="temp-label">Сбалансированный</div>';
    html += '</div>';
    html += '<div class="temp-description">';
    html += `<p>${escapeHtml(data.temperatures['0.5'].description)}</p>`;
    html += '</div>';
    html += '<div class="temp-response">';
    html += `<pre>${escapeHtml(data.temperatures['0.5'].response)}</pre>`;
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
    html += '<h4>🌤️ Температура 0.5</h4>';
    html += `<p>${escapeHtml(data.recommendations['0.5'])}</p>`;
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
    html += '<li><strong>Баланс:</strong> Температура 0.5 обеспечивает хороший баланс между точностью и креативностью, подходит для большинства задач.</li>';
    html += '<li><strong>Разнообразие:</strong> Чем выше температура (в диапазоне 0.0-1.0), тем больше вариативность ответов при повторных запросах.</li>';
    html += '</ul>';
    html += '</div>';

    temperatureResults.innerHTML = html;
}

async function runModelComparison() {
    const prompt = comparisonPrompt.value.trim();
    if (!prompt) {
        alert('Пожалуйста, введите запрос для тестирования');
        return;
    }

    // Получаем выбранные модели
    const checkboxes = document.querySelectorAll('.model-checkbox:checked');
    const selectedModels = Array.from(checkboxes).map(cb => cb.value);

    if (selectedModels.length < 2) {
        alert('Пожалуйста, выберите минимум 2 модели для сравнения');
        return;
    }

    // Отключаем кнопку и показываем загрузку
    runComparisonBtn.disabled = true;
    comparisonPrompt.disabled = true;
    checkboxes.forEach(cb => cb.disabled = true);
    comparisonResults.innerHTML = '<div class="loading-comparison">⏳ Запускаю сравнение моделей...<br>Это может занять некоторое время, так как запрашиваются разные модели HuggingFace API</div>';

    try {
        const response = await fetch('/model_comparison', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                prompt: prompt,
                models: selectedModels
            })
        });

        const data = await response.json();

        if (response.ok) {
            displayComparisonResults(data);
        } else {
            comparisonResults.innerHTML = `<div class="error">Ошибка: ${data.error || 'Неизвестная ошибка'}</div>`;
        }
    } catch (error) {
        comparisonResults.innerHTML = `<div class="error">Ошибка подключения: ${error.message}</div>`;
    } finally {
        runComparisonBtn.disabled = false;
        comparisonPrompt.disabled = false;
        checkboxes.forEach(cb => cb.disabled = false);
    }
}

function displayComparisonResults(data) {
    let html = '<div class="comparison-results-header">';
    html += `<h3>📊 Результаты сравнения моделей</h3>`;
    html += `<p class="comparison-prompt"><strong>Запрос:</strong> ${escapeHtml(data.prompt)}</p>`;
    html += `<p class="comparison-stats"><strong>Сравнено моделей:</strong> ${data.models_compared} | <strong>Успешных вызовов:</strong> ${data.successful_calls}</p>`;
    html += '</div>';

    // Общий анализ (если есть)
    if (data.analysis) {
        html += '<div class="comparison-analysis">';
        html += '<h3>📈 Общий анализ</h3>';
        html += '<div class="analysis-grid">';

        html += '<div class="analysis-card">';
        html += '<h4>⚡ Самая быстрая</h4>';
        html += `<p><strong>${escapeHtml(data.analysis.fastest_model)}</strong></p>`;
        html += `<p class="metric">${data.analysis.fastest_time} сек</p>`;
        html += '</div>';

        html += '<div class="analysis-card">';
        html += '<h4>🐌 Самая медленная</h4>';
        html += `<p><strong>${escapeHtml(data.analysis.slowest_model)}</strong></p>`;
        html += `<p class="metric">${data.analysis.slowest_time} сек</p>`;
        html += '</div>';

        html += '<div class="analysis-card">';
        html += '<h4>📝 Самый краткий ответ</h4>';
        html += `<p><strong>${escapeHtml(data.analysis.most_concise_model)}</strong></p>`;
        html += `<p class="metric">${data.analysis.most_concise_tokens} токенов</p>`;
        html += '</div>';

        html += '<div class="analysis-card">';
        html += '<h4>📚 Самый подробный ответ</h4>';
        html += `<p><strong>${escapeHtml(data.analysis.most_verbose_model)}</strong></p>`;
        html += `<p class="metric">${data.analysis.most_verbose_tokens} токенов</p>`;
        html += '</div>';

        html += '<div class="analysis-card">';
        html += '<h4>💰 Самая дешевая</h4>';
        html += `<p><strong>${escapeHtml(data.analysis.cheapest_model)}</strong></p>`;
        html += `<p class="metric">${data.analysis.cheapest_cost} ₽</p>`;
        html += '</div>';

        html += '<div class="analysis-card">';
        html += '<h4>💸 Самая дорогая</h4>';
        html += `<p><strong>${escapeHtml(data.analysis.most_expensive_model)}</strong></p>`;
        html += `<p class="metric">${data.analysis.most_expensive_cost} ₽</p>`;
        html += '</div>';

        html += '<div class="analysis-card">';
        html += '<h4>⏱️ Среднее время</h4>';
        html += `<p class="metric">${data.analysis.avg_response_time} сек</p>`;
        html += '</div>';

        html += '<div class="analysis-card">';
        html += '<h4>💬 Средний размер ответа</h4>';
        html += `<p class="metric">${data.analysis.avg_output_tokens} токенов</p>`;
        html += '</div>';

        html += '<div class="analysis-card">';
        html += '<h4>💵 Средняя стоимость</h4>';
        html += `<p class="metric">${data.analysis.avg_cost} ₽</p>`;
        html += '</div>';

        html += '</div>';
        html += '</div>';
    }

    // Результаты каждой модели
    html += '<div class="model-results-container">';

    data.results.forEach((result, index) => {
        const statusClass = result.success ? 'model-success' : 'model-error';
        html += `<div class="model-result-card ${statusClass}">`;
        html += `<div class="model-header">`;
        const modelTitle = result.model_name ? `${result.model_name} (${result.model})` : result.model;
        html += `<h4>${index + 1}. ${escapeHtml(modelTitle)}</h4>`;
        html += result.success ? '<span class="status-badge success">✅ Успех</span>' : '<span class="status-badge error">❌ Ошибка</span>';
        html += `</div>`;

        if (result.success) {
            // Метрики
            html += '<div class="model-metrics">';
            html += `<div class="metric-item"><span class="metric-label">⏱️ Время:</span> <span class="metric-value">${result.metrics.response_time} сек</span></div>`;
            html += `<div class="metric-item"><span class="metric-label">📥 Входных токенов:</span> <span class="metric-value">${result.metrics.input_tokens}</span></div>`;
            html += `<div class="metric-item"><span class="metric-label">📤 Выходных токенов:</span> <span class="metric-value">${result.metrics.output_tokens}</span></div>`;
            html += `<div class="metric-item"><span class="metric-label">📊 Всего токенов:</span> <span class="metric-value">${result.metrics.total_tokens}</span></div>`;
            html += `<div class="metric-item"><span class="metric-label">💰 Стоимость:</span> <span class="metric-value">${result.metrics.cost_rub} ₽</span></div>`;
            html += '</div>';

            // Ответ модели
            html += '<div class="model-response">';
            html += '<h5>💬 Ответ модели:</h5>';
            html += `<pre>${escapeHtml(result.response)}</pre>`;
            html += '</div>';
        } else {
            // Ошибка
            html += '<div class="model-error-message">';
            html += `<p><strong>Ошибка:</strong> ${escapeHtml(result.error)}</p>`;
            html += `<p><strong>Время до ошибки:</strong> ${result.metrics.response_time} сек</p>`;
            html += '</div>';
        }

        html += '</div>';
    });

    html += '</div>';

    // Выводы
    html += '<div class="comparison-conclusions">';
    html += '<h3>📝 Выводы</h3>';
    html += '<ul>';
    html += '<li><strong>Скорость:</strong> YandexGPT Lite обычно быстрее стандартной модели, но YandexGPT 32K может работать дольше из-за расширенного контекста.</li>';
    html += '<li><strong>Качество:</strong> Стандартная модель YandexGPT обеспечивает хороший баланс качества и скорости, YandexGPT 32K лучше работает с большими контекстами.</li>';
    html += '<li><strong>Токены:</strong> Разные модели генерируют разное количество токенов. Больше токенов не всегда означает лучше - важна содержательность.</li>';
    html += '<li><strong>Стоимость:</strong> YandexGPT Lite самая экономичная (0.2₽/1K входных токенов), YandexGPT 32K самая дорогая (0.8₽/1K входных токенов).</li>';
    html += '<li><strong>Специализация:</strong> Модель Summarization специализируется на суммаризации текстов, остальные - универсальные языковые модели.</li>';
    html += '</ul>';
    html += '</div>';

    comparisonResults.innerHTML = html;
}

async function runTokenTest(testType) {
    const promptMap = {
        'short': document.getElementById('shortPrompt').value,
        'long': document.getElementById('longPrompt').value,
        'extreme': document.getElementById('extremePrompt').value
    };

    const resultMap = {
        'short': document.getElementById('shortResult'),
        'long': document.getElementById('longResult'),
        'extreme': document.getElementById('extremeResult')
    };

    const prompt = promptMap[testType];
    const resultDiv = resultMap[testType];
    const btn = document.querySelector(`[data-type="${testType}"]`);

    if (!prompt || !resultDiv) return;

    // Отключаем кнопку и показываем загрузку
    btn.disabled = true;
    resultDiv.innerHTML = '<div class="token-loading">⏳ Тестируем...</div>';
    resultDiv.classList.add('visible');

    try {
        const response = await fetch('/token_test', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                prompt: prompt,
                test_type: testType
            })
        });

        const data = await response.json();

        if (response.ok) {
            displayTokenResult(data, resultDiv, testType);
            updateTokenConclusions();
        } else {
            resultDiv.innerHTML = `<div class="token-error">❌ Ошибка: ${data.error || 'Неизвестная ошибка'}</div>`;
        }
    } catch (error) {
        resultDiv.innerHTML = `<div class="token-error">❌ Ошибка подключения: ${error.message}</div>`;
    } finally {
        btn.disabled = false;
    }
}

function displayTokenResult(data, resultDiv, testType) {
    let html = '';

    // Информация о тесте
    html += '<div class="token-metrics">';
    html += '<h5>📊 Метрики запроса</h5>';
    html += '<div class="token-metrics-grid">';

    html += '<div class="token-metric-item">';
    html += '<div class="token-metric-label">Длина промпта</div>';
    html += `<div class="token-metric-value">${data.prompt_length} символов</div>`;
    html += '</div>';

    html += '<div class="token-metric-item">';
    html += '<div class="token-metric-label">Оценка токенов</div>';
    html += `<div class="token-metric-value">${data.estimated_input_tokens}</div>`;
    html += '</div>';

    html += '</div>';
    html += '</div>';

    // Режим сравнения для экстремального теста
    if (data.comparison_mode) {
        html += '<h5 style="margin-top: 20px; color: #ff9800;">🔬 Сравнение моделей</h5>';

        // Базовая модель
        html += '<div style="border: 2px solid #ff5722; border-radius: 10px; padding: 15px; margin-top: 15px;">';
        html += `<h5 style="color: #ff5722;">❌ ${escapeHtml(data.base_model.model_name)} (лимит: ${data.base_model.model_limit})</h5>`;

        if (data.base_model.result.success) {
            const metrics = data.base_model.result.metrics;
            html += '<div class="token-metrics-grid">';

            html += '<div class="token-metric-item">';
            html += '<div class="token-metric-label">⏱️ Время</div>';
            html += `<div class="token-metric-value">${metrics.response_time} сек</div>`;
            html += '</div>';

            html += '<div class="token-metric-item">';
            html += '<div class="token-metric-label">📥 Входные токены</div>';
            html += `<div class="token-metric-value">${metrics.input_tokens}</div>`;
            html += '</div>';

            html += '<div class="token-metric-item">';
            html += '<div class="token-metric-label">📤 Выходные токены</div>';
            html += `<div class="token-metric-value">${metrics.output_tokens}</div>`;
            html += '</div>';

            html += '<div class="token-metric-item">';
            html += '<div class="token-metric-label">💰 Стоимость</div>';
            html += `<div class="token-metric-value">${metrics.cost_rub} ₽</div>`;
            html += '</div>';

            html += '</div>';

            const limitPercent = (metrics.input_tokens / data.base_model.model_limit) * 100;
            const limitClass = limitPercent > 90 ? 'danger' : (limitPercent > 70 ? 'warning' : '');
            // Минимальная ширина 8% для видимости, но показываем реальный процент
            const displayWidth = Math.max(8, Math.min(limitPercent, 100));

            html += '<div class="token-progress-bar" style="margin-top: 10px;">';
            html += `<div class="token-progress-fill ${limitClass}" style="width: ${displayWidth}%">`;
            html += `${limitPercent.toFixed(1)}% лимита`;
            html += '</div>';
            html += '</div>';

            const previewText = data.base_model.result.response.substring(0, 300) + '...';
            html += `<p style="margin-top: 10px; font-size: 12px; color: #666;">${escapeHtml(previewText)}</p>`;
        } else {
            html += `<p style="color: #d32f2f; font-weight: bold;">⚠️ Ошибка: ${escapeHtml(data.base_model.result.error)}</p>`;
            html += '<p style="font-size: 12px; color: #666;">Запрос слишком велик для этой модели!</p>';
        }

        html += '</div>';

        // 32K модель
        html += '<div style="border: 2px solid #4caf50; border-radius: 10px; padding: 15px; margin-top: 15px;">';
        html += `<h5 style="color: #4caf50;">✅ ${escapeHtml(data.extended_model.model_name)} (лимит: ${data.extended_model.model_limit})</h5>`;

        if (data.extended_model.result.success) {
            const metrics = data.extended_model.result.metrics;
            html += '<div class="token-metrics-grid">';

            html += '<div class="token-metric-item">';
            html += '<div class="token-metric-label">⏱️ Время</div>';
            html += `<div class="token-metric-value">${metrics.response_time} сек</div>`;
            html += '</div>';

            html += '<div class="token-metric-item">';
            html += '<div class="token-metric-label">📥 Входные токены</div>';
            html += `<div class="token-metric-value">${metrics.input_tokens}</div>`;
            html += '</div>';

            html += '<div class="token-metric-item">';
            html += '<div class="token-metric-label">📤 Выходные токены</div>';
            html += `<div class="token-metric-value">${metrics.output_tokens}</div>`;
            html += '</div>';

            html += '<div class="token-metric-item">';
            html += '<div class="token-metric-label">💰 Стоимость</div>';
            html += `<div class="token-metric-value">${metrics.cost_rub} ₽</div>`;
            html += '</div>';

            html += '</div>';

            const limitPercent = (metrics.input_tokens / data.extended_model.model_limit) * 100;
            const limitClass = limitPercent > 90 ? 'danger' : (limitPercent > 70 ? 'warning' : '');
            // Минимальная ширина 8% для видимости, но показываем реальный процент
            const displayWidth = Math.max(8, Math.min(limitPercent, 100));

            html += '<div class="token-progress-bar" style="margin-top: 10px;">';
            html += `<div class="token-progress-fill ${limitClass}" style="width: ${displayWidth}%">`;
            html += `${limitPercent.toFixed(1)}% лимита`;
            html += '</div>';
            html += '</div>';

            const previewText = data.extended_model.result.response.substring(0, 300) + '...';
            html += `<p style="margin-top: 10px; font-size: 12px; color: #666;">${escapeHtml(previewText)}</p>`;
        } else {
            html += `<p style="color: #d32f2f; font-weight: bold;">⚠️ Ошибка: ${escapeHtml(data.extended_model.result.error)}</p>`;
        }

        html += '</div>';

        // Вывод
        html += '<div style="background: #fff3cd; border-radius: 10px; padding: 15px; margin-top: 15px;">';
        html += '<h5 style="color: #856404;">💡 Вывод</h5>';
        if (data.base_model.result.success && data.extended_model.result.success) {
            html += '<p>Обе модели справились с запросом. Базовая модель достаточна для этого размера.</p>';
        } else if (!data.base_model.result.success && data.extended_model.result.success) {
            html += '<p><strong>Базовая модель не справилась</strong> (превышен лимит 8000 токенов), но <strong>YandexGPT 32K успешно обработала запрос</strong>. Это демонстрирует необходимость использования модели с расширенным контекстом для больших запросов.</p>';
        } else {
            html += '<p>Обе модели вернули ошибки. Возможно проблема с API или запрос некорректен.</p>';
        }
        html += '</div>';

    } else {
        // Обычный режим (для коротких и длинных запросов)
        if (data.result.success) {
            const metrics = data.result.metrics;

            html += '<div class="token-metrics">';
            html += '<h5>✅ Результаты обработки</h5>';
            html += '<div class="token-metrics-grid">';

            html += '<div class="token-metric-item">';
            html += '<div class="token-metric-label">⏱️ Время ответа</div>';
            html += `<div class="token-metric-value success">${metrics.response_time} сек</div>`;
            html += '</div>';

            html += '<div class="token-metric-item">';
            html += '<div class="token-metric-label">📥 Входные токены</div>';
            html += `<div class="token-metric-value">${metrics.input_tokens}</div>`;
            html += '</div>';

            html += '<div class="token-metric-item">';
            html += '<div class="token-metric-label">📤 Выходные токены</div>';
            html += `<div class="token-metric-value">${metrics.output_tokens}</div>`;
            html += '</div>';

            html += '<div class="token-metric-item">';
            html += '<div class="token-metric-label">📊 Всего токенов</div>';
            html += `<div class="token-metric-value">${metrics.total_tokens}</div>`;
            html += '</div>';

            html += '<div class="token-metric-item">';
            html += '<div class="token-metric-label">💰 Стоимость</div>';
            html += `<div class="token-metric-value">${metrics.cost_rub} ₽</div>`;
            html += '</div>';

            html += '</div>';

            // Прогресс-бар использования лимита
            const limitPercent = (metrics.input_tokens / data.model_limit) * 100;
            const limitClass = limitPercent > 80 ? 'danger' : (limitPercent > 50 ? 'warning' : '');
            // Минимальная ширина 8% для видимости, но показываем реальный процент
            const displayWidth = Math.max(8, Math.min(limitPercent, 100));

            html += '<div class="token-progress-bar">';
            html += `<div class="token-progress-fill ${limitClass}" style="width: ${displayWidth}%">`;
            html += `${limitPercent.toFixed(1)}% лимита`;
            html += '</div>';
            html += '</div>';

            html += '</div>';

            // Предпросмотр ответа
            html += '<div class="token-response-preview">';
            html += '<h5>💬 Превью ответа</h5>';
            const previewText = data.result.response.substring(0, 500) + (data.result.response.length > 500 ? '...' : '');
            html += `<div class="token-response-text">${escapeHtml(previewText)}</div>`;
            html += '</div>';

        } else {
            // Ошибка
            html += '<div class="token-error">';
            html += '<h5>❌ Ошибка обработки</h5>';
            html += `<p>${escapeHtml(data.result.error)}</p>`;
            html += '</div>';
        }
    }

    resultDiv.innerHTML = html;
}

function updateTokenConclusions() {
    const conclusionsDiv = document.getElementById('tokensConclusions');
    const contentDiv = document.getElementById('tokensConclusionContent');

    if (!conclusionsDiv || !contentDiv) return;

    let html = '';

    html += '<div class="conclusion-item">';
    html += '<h4>🎯 Короткие запросы (5-20 токенов)</h4>';
    html += '<p>Оптимальны для простых вопросов и быстрых команд. Низкая стоимость, быстрый ответ. Модель YandexGPT обрабатывает такие запросы за доли секунды.</p>';
    html += '</div>';

    html += '<div class="conclusion-item">';
    html += '<h4>📝 Длинные запросы (200-500 токенов)</h4>';
    html += '<p>Подходят для детальных инструкций и сложных задач. Стоимость умеренная, время обработки приемлемое. Модель может генерировать более контекстуальные и детальные ответы.</p>';
    html += '</div>';

    html += '<div class="conclusion-item">';
    html += '<h4>⚠️ Экстремальные запросы (>8000 токенов)</h4>';
    html += '<p>Превышают лимит базовых моделей YandexGPT и YandexGPT Lite (8000 токенов). Для таких запросов необходимо использовать YandexGPT 32K с лимитом 32000 токенов. Высокая стоимость, требуют больше времени на обработку.</p>';
    html += '</div>';

    html += '<div class="conclusion-item">';
    html += '<h4>💡 Рекомендации</h4>';
    html += '<ul style="margin-left: 20px; margin-top: 8px;">';
    html += '<li>Используйте YandexGPT Lite для коротких запросов - это экономично</li>';
    html += '<li>YandexGPT подходит для большинства задач средней сложности</li>';
    html += '<li>YandexGPT 32K используйте только для длинных контекстов</li>';
    html += '<li>Оптимизируйте запросы - убирайте лишние слова и повторения</li>';
    html += '<li>Помните: стоимость зависит как от входных, так и от выходных токенов</li>';
    html += '</ul>';
    html += '</div>';

    contentDiv.innerHTML = html;
    conclusionsDiv.style.display = 'block';
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
    if (comparisonModeBtn) {
        comparisonModeBtn.classList.remove('active');
    }
    if (tokensModeBtn) {
        tokensModeBtn.classList.remove('active');
    }
    if (compressionModeBtn) {
        compressionModeBtn.classList.remove('active');
    }

    if (mode === 'info') {
        infoModeBtn.classList.add('active');
    } else if (mode === 'recommend') {
        recommendModeBtn.classList.add('active');
    } else if (mode === 'reasoning' && reasoningModeBtn) {
        reasoningModeBtn.classList.add('active');
    } else if (mode === 'temperature' && temperatureModeBtn) {
        temperatureModeBtn.classList.add('active');
    } else if (mode === 'comparison' && comparisonModeBtn) {
        comparisonModeBtn.classList.add('active');
    } else if (mode === 'tokens' && tokensModeBtn) {
        tokensModeBtn.classList.add('active');
    } else if (mode === 'compression' && compressionModeBtn) {
        compressionModeBtn.classList.add('active');
    }

    // Показываем/скрываем интерфейсы
    if (mode === 'reasoning' && reasoningContainer && chatInputContainer) {
        chatMessages.style.display = 'none';
        chatInputContainer.style.display = 'none';
        reasoningContainer.style.display = 'block';
        if (temperatureContainer) {
            temperatureContainer.style.display = 'none';
        }
        if (comparisonContainer) {
            comparisonContainer.style.display = 'none';
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
        if (comparisonContainer) {
            comparisonContainer.style.display = 'none';
        }
        if (temperatureResults) {
            temperatureResults.innerHTML = '';
        }
        if (temperaturePrompt) {
            temperaturePrompt.value = '';
        }
    } else if (mode === 'comparison' && comparisonContainer && chatInputContainer) {
        chatMessages.style.display = 'none';
        chatInputContainer.style.display = 'none';
        if (reasoningContainer) {
            reasoningContainer.style.display = 'none';
        }
        if (temperatureContainer) {
            temperatureContainer.style.display = 'none';
        }
        comparisonContainer.style.display = 'block';
        if (tokensContainer) {
            tokensContainer.style.display = 'none';
        }
        if (comparisonResults) {
            comparisonResults.innerHTML = '';
        }
        if (comparisonPrompt) {
            comparisonPrompt.value = '';
        }
    } else if (mode === 'tokens' && tokensContainer && chatInputContainer) {
        chatMessages.style.display = 'none';
        chatInputContainer.style.display = 'none';
        if (reasoningContainer) {
            reasoningContainer.style.display = 'none';
        }
        if (temperatureContainer) {
            temperatureContainer.style.display = 'none';
        }
        if (comparisonContainer) {
            comparisonContainer.style.display = 'none';
        }
        tokensContainer.style.display = 'block';
        if (compressionDialogContainer) {
            compressionDialogContainer.style.display = 'none';
        }
    } else if (mode === 'compression' && compressionDialogContainer && chatInputContainer) {
        chatMessages.style.display = 'none';
        chatInputContainer.style.display = 'none';
        if (reasoningContainer) {
            reasoningContainer.style.display = 'none';
        }
        if (temperatureContainer) {
            temperatureContainer.style.display = 'none';
        }
        if (comparisonContainer) {
            comparisonContainer.style.display = 'none';
        }
        if (tokensContainer) {
            tokensContainer.style.display = 'none';
        }
        compressionDialogContainer.style.display = 'block';
        // Обновляем статистику при открытии
        updateCompressionStats();
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
        if (comparisonContainer) {
            comparisonContainer.style.display = 'none';
        }
        if (tokensContainer) {
            tokensContainer.style.display = 'none';
        }
        if (compressionDialogContainer) {
            compressionDialogContainer.style.display = 'none';
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
if (comparisonModeBtn) {
    comparisonModeBtn.addEventListener('click', () => switchMode('comparison'));
}
if (runTemperatureBtn) {
    runTemperatureBtn.addEventListener('click', runTemperatureExperiment);
}
if (runComparisonBtn) {
    runComparisonBtn.addEventListener('click', runModelComparison);
}
if (tokensModeBtn) {
    tokensModeBtn.addEventListener('click', () => switchMode('tokens'));
}
if (compressionModeBtn) {
    compressionModeBtn.addEventListener('click', () => switchMode('compression'));
}

// Обработчики для кнопок режима сжатия
if (compressionSendBtn) {
    compressionSendBtn.addEventListener('click', () => sendCompressionMessage('send'));
}
if (compressionCompareBtn) {
    compressionCompareBtn.addEventListener('click', () => sendCompressionMessage('compare'));
}
const compressionTestBtn = document.getElementById('compressionTestBtn');
if (compressionTestBtn) {
    compressionTestBtn.addEventListener('click', runCompressionTest);
}
if (compressionStatsBtn) {
    compressionStatsBtn.addEventListener('click', updateCompressionStats);
}
if (compressionClearBtn) {
    compressionClearBtn.addEventListener('click', clearCompressionHistory);
}
if (compressionMessageInput) {
    compressionMessageInput.addEventListener('keypress', (e) => {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            sendCompressionMessage('send');
        }
    });
}

// Обработчики для кнопок тестирования токенов
document.addEventListener('click', (e) => {
    if (e.target.classList.contains('token-test-btn')) {
        const testType = e.target.dataset.type;
        runTokenTest(testType);
    }
});

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

// ============= Функции для режима сжатия диалога =============

function addCompressionMessage(text, isUser) {
    const messageDiv = document.createElement('div');
    messageDiv.className = `message ${isUser ? 'user' : 'assistant'}`;

    const contentDiv = document.createElement('div');
    contentDiv.className = 'message-content';
    contentDiv.textContent = text;

    messageDiv.appendChild(contentDiv);
    compressionMessages.appendChild(messageDiv);

    // Прокрутка вниз
    compressionMessages.scrollTop = compressionMessages.scrollHeight;
}

async function sendCompressionMessage(action) {
    const message = compressionMessageInput.value.trim();

    if (!message) {
        alert('Пожалуйста, введите сообщение');
        return;
    }

    // Добавляем сообщение пользователя
    addCompressionMessage(message, true);

    // Очищаем поле ввода
    compressionMessageInput.value = '';

    // Отключаем кнопки
    compressionSendBtn.disabled = true;
    compressionCompareBtn.disabled = true;

    // Показываем индикатор загрузки
    const loadingDiv = document.createElement('div');
    loadingDiv.className = 'message assistant loading-message';
    loadingDiv.innerHTML = '<div class="message-content">⏳ Обрабатываю запрос...</div>';
    compressionMessages.appendChild(loadingDiv);
    compressionMessages.scrollTop = compressionMessages.scrollHeight;

    try {
        const response = await fetch('/compression_test', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ message, action })
        });

        const data = await response.json();

        // Удаляем индикатор загрузки
        loadingDiv.remove();

        if (!response.ok) {
            addCompressionMessage(`❌ Ошибка: ${data.error || 'Неизвестная ошибка'}`, false);
            return;
        }

        if (action === 'send') {
            // Обычная отправка

            // Показываем индикатор компрессии, если она произошла
            if (data.compression_triggered) {
                const compressionNotice = document.createElement('div');
                compressionNotice.className = 'message assistant compression-notice';
                compressionNotice.innerHTML = '<div class="message-content">🗜️ ВЫПОЛНЕНА КОМПРЕССИЯ ИСТОРИИ! Старые сообщения сжаты в краткое резюме.</div>';
                compressionMessages.appendChild(compressionNotice);
                compressionMessages.scrollTop = compressionMessages.scrollHeight;
            }

            addCompressionMessage(data.response, false);

            // Обновляем статистику
            if (data.compression_stats) {
                updateCompressionStatsDisplay(data.compression_stats);
            }

            // Показываем метрики
            const metricsText = `📊 Метрики: ${data.metrics.input_tokens} вх + ${data.metrics.output_tokens} вых = ${data.metrics.total_tokens} токенов | ⏱️ ${data.metrics.response_time}s | 💰 ${data.metrics.cost_rub}₽`;
            addCompressionMessage(metricsText, false);

        } else if (action === 'compare') {
            // Сравнение
            const comparison = data.comparison;

            // Показываем результаты сравнения
            compressionComparisonResults.style.display = 'block';

            // С компрессией
            document.getElementById('withCompressionResult').innerHTML = `
                <div class="compression-result-item">
                    <p><strong>Ответ:</strong> ${escapeHtml(comparison.with_compression.response.substring(0, 200))}...</p>
                    <div class="metrics">
                        <div>📊 Входные токены: ${comparison.with_compression.metrics.input_tokens}</div>
                        <div>📊 Выходные токены: ${comparison.with_compression.metrics.output_tokens}</div>
                        <div>📊 Всего токенов: ${comparison.with_compression.metrics.total_tokens}</div>
                        <div>💰 Стоимость: ${comparison.with_compression.metrics.cost_rub}₽</div>
                        <div>⏱️ Время: ${comparison.with_compression.metrics.response_time}s</div>
                        <div>📝 Сообщений в истории: ${comparison.with_compression.metrics.history_messages}</div>
                    </div>
                </div>
            `;

            // Без компрессии
            document.getElementById('withoutCompressionResult').innerHTML = `
                <div class="compression-result-item">
                    <p><strong>Ответ:</strong> ${escapeHtml(comparison.without_compression.response.substring(0, 200))}...</p>
                    <div class="metrics">
                        <div>📊 Входные токены: ${comparison.without_compression.metrics.input_tokens}</div>
                        <div>📊 Выходные токены: ${comparison.without_compression.metrics.output_tokens}</div>
                        <div>📊 Всего токенов: ${comparison.without_compression.metrics.total_tokens}</div>
                        <div>💰 Стоимость: ${comparison.without_compression.metrics.cost_rub}₽</div>
                        <div>⏱️ Время: ${comparison.without_compression.metrics.response_time}s</div>
                        <div>📝 Сообщений в истории: ${comparison.without_compression.metrics.history_messages}</div>
                    </div>
                </div>
            `;

            // Экономия
            document.getElementById('savingsContent').innerHTML = `
                <div class="savings-metrics">
                    <div class="savings-item highlight">
                        <strong>📊 Сэкономлено токенов:</strong> ${comparison.savings.tokens_saved} (${comparison.savings.tokens_saved_percent}%)
                    </div>
                    <div class="savings-item highlight">
                        <strong>💰 Сэкономлено денег:</strong> ${comparison.savings.cost_saved}₽ (${comparison.savings.cost_saved_percent}%)
                    </div>
                    <div class="savings-item">
                        <strong>⏱️ Разница во времени:</strong> ${comparison.savings.time_difference}s
                    </div>
                </div>
            `;

            // Обновляем статистику
            if (comparison.compression_stats) {
                updateCompressionStatsDisplay(comparison.compression_stats);
            }

            // Добавляем сообщение в чат
            addCompressionMessage(comparison.with_compression.response, false);
            addCompressionMessage(`✅ Сравнение завершено! Экономия: ${comparison.savings.tokens_saved} токенов (${comparison.savings.tokens_saved_percent}%)`, false);
        }

    } catch (error) {
        loadingDiv.remove();
        addCompressionMessage(`❌ Ошибка подключения: ${error.message}`, false);
    } finally {
        // Включаем кнопки
        compressionSendBtn.disabled = false;
        compressionCompareBtn.disabled = false;
        compressionMessageInput.focus();
    }
}

async function updateCompressionStats() {
    try {
        const response = await fetch('/compression_test', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ action: 'stats' })
        });

        const data = await response.json();

        if (response.ok && data.stats) {
            updateCompressionStatsDisplay(data.stats);
            addCompressionMessage('📊 Статистика обновлена', false);
        }
    } catch (error) {
        console.error('Ошибка при обновлении статистики:', error);
    }
}

function updateCompressionStatsDisplay(stats) {
    document.getElementById('statTotalMessages').textContent = stats.total_messages || 0;
    document.getElementById('statCompressedMessages').textContent = stats.compressed_messages || 0;
    document.getElementById('statCompressionCount').textContent = stats.compression_count || 0;
    document.getElementById('statTokensSaved').textContent = stats.total_tokens_saved || 0;
    document.getElementById('statCurrentFullTokens').textContent = stats.current_full_tokens || 0;
    document.getElementById('statCurrentCompressedTokens').textContent = stats.current_compressed_tokens || 0;
    document.getElementById('statCompressionRatio').textContent = (stats.compression_ratio || 0) + '%';
}

async function clearCompressionHistory() {
    if (!confirm('Очистить историю диалога и статистику?')) return;

    try {
        const response = await fetch('/compression_test', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ action: 'clear' })
        });

        const data = await response.json();

        if (response.ok) {
            // Очищаем чат
            compressionMessages.innerHTML = `
                <div class="message assistant">
                    <div class="message-content">
                        Привет! Я готов к диалогу с автоматическим сжатием истории.
                        При достижении 10 сообщений старые сообщения будут автоматически
                        сжаты в краткое резюме. Давай начнем!
                    </div>
                </div>
            `;

            // Скрываем результаты сравнения
            compressionComparisonResults.style.display = 'none';

            // Обновляем статистику
            updateCompressionStatsDisplay({
                total_messages: 0,
                compressed_messages: 0,
                compression_count: 0,
                total_tokens_saved: 0,
                current_full_tokens: 0,
                current_compressed_tokens: 0,
                compression_ratio: 0
            });

            addCompressionMessage('✅ История очищена', false);
        }
    } catch (error) {
        addCompressionMessage(`❌ Ошибка при очистке: ${error.message}`, false);
    }
}

async function runCompressionTest() {
    if (!confirm('Запустить автоматический тест? Это отправит серию сообщений для проверки механизма сжатия.')) return;

    // Очищаем историю перед тестом
    addCompressionMessage('🧪 Запуск автоматического теста...', false);
    addCompressionMessage('📋 Очистка истории...', false);

    try {
        await fetch('/compression_test', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ action: 'clear' })
        });

        addCompressionMessage('✅ История очищена', false);

        // Отключаем кнопки
        compressionSendBtn.disabled = true;
        compressionCompareBtn.disabled = true;
        compressionTestBtn.disabled = true;
        compressionStatsBtn.disabled = true;
        compressionClearBtn.disabled = true;

        // Запускаем тест
        const response = await fetch('/compression_test', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ action: 'run_test' })
        });

        const data = await response.json();

        if (!response.ok) {
            addCompressionMessage(`❌ Ошибка теста: ${data.error || 'Неизвестная ошибка'}`, false);
            return;
        }

        // Показываем результаты теста
        addCompressionMessage('✅ Тест завершен!', false);
        addCompressionMessage('', false);
        addCompressionMessage('📊 РЕЗУЛЬТАТЫ ТЕСТА:', false);
        addCompressionMessage(`📝 Отправлено сообщений: ${data.messages_sent}`, false);
        addCompressionMessage(`⏱️ Общее время: ${data.total_time}s`, false);
        addCompressionMessage(`📊 Всего использовано токенов: ${data.total_tokens}`, false);
        addCompressionMessage(`💰 Общая стоимость: ${data.total_cost}₽`, false);
        addCompressionMessage('', false);

        if (data.final_stats) {
            const stats = data.final_stats;
            addCompressionMessage('📈 СТАТИСТИКА СЖАТИЯ:', false);
            addCompressionMessage(`🗜️ Компрессий выполнено: ${stats.compression_count}`, false);
            addCompressionMessage(`💾 Сэкономлено токенов: ${stats.total_tokens_saved}`, false);
            addCompressionMessage(`📉 Степень сжатия: ${stats.compression_ratio}%`, false);

            // Обновляем отображение статистики
            updateCompressionStatsDisplay(stats);
        }

        if (data.comparison) {
            addCompressionMessage('', false);
            addCompressionMessage('⚖️ СРАВНЕНИЕ (последний запрос):', false);
            addCompressionMessage(`✅ С компрессией: ${data.comparison.with_compression.metrics.total_tokens} токенов, ${data.comparison.with_compression.metrics.cost_rub}₽`, false);
            addCompressionMessage(`❌ Без компрессии: ${data.comparison.without_compression.metrics.total_tokens} токенов, ${data.comparison.without_compression.metrics.cost_rub}₽`, false);
            addCompressionMessage(`💡 Экономия: ${data.comparison.savings.tokens_saved} токенов (${data.comparison.savings.tokens_saved_percent}%)`, false);
        }

    } catch (error) {
        addCompressionMessage(`❌ Ошибка: ${error.message}`, false);
    } finally {
        // Включаем кнопки
        compressionSendBtn.disabled = false;
        compressionCompareBtn.disabled = false;
        compressionTestBtn.disabled = false;
        compressionStatsBtn.disabled = false;
        compressionClearBtn.disabled = false;
    }
}

