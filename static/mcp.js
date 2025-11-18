/**
 * MCP Tools - интерфейс для работы с Model Context Protocol
 * День 10: Интеграция MCP в веб-интерфейс
 */

// Глобальное хранилище инструментов
let mcpTools = [];
let currentTool = null;
let currentServer = 'github'; // по умолчанию GitHub

// Иконки для инструментов
const toolIcons = {
    'calculator': '🧮',
    'get_current_time': '⏰',
    'text_analyzer': '📊',
    'json_formatter': '📋',
    'weather_info': '🌤️',
    // GitHub tools
    'create_or_update_file': '📝',
    'push_files': '⬆️',
    'create_repository': '📦',
    'get_file_contents': '📄',
    'create_issue': '🐛',
    'create_pull_request': '🔀',
    'fork_repository': '🍴',
    'create_branch': '🌿',
    'list_commits': '📜',
    'search_repositories': '🔍',
    'search_code': '🔎',
    'search_issues': '🔍',
    'search_users': '👤',
    'get_issue': '📋',
    'update_issue': '✏️',
    'add_issue_comment': '💬',
    'default': '🔧'
};

// Получить иконку для инструмента
function getToolIcon(toolName) {
    return toolIcons[toolName] || toolIcons['default'];
}

// Загрузить список инструментов
async function loadMcpTools() {
    const loadBtn = document.getElementById('loadMcpTools');
    const toolsGrid = document.getElementById('mcpToolsGrid');
    const toolsCount = document.getElementById('mcpToolsCount');
    const serverSelect = document.getElementById('mcpServerType');

    currentServer = serverSelect.value;

    loadBtn.disabled = true;
    loadBtn.textContent = '⏳ Загрузка...';

    try {
        // Выбираем endpoint в зависимости от сервера
        const endpoint = currentServer === 'github' ? '/mcp/github/tools' : '/mcp/tools';
        const response = await fetch(endpoint);
        const data = await response.json();

        if (data.status === 'ok') {
            mcpTools = data.tools;
            displayMcpTools(mcpTools);
            toolsCount.textContent = `${data.count} инструментов (${data.server === 'github' ? 'GitHub' : 'Local'})`;
        } else {
            throw new Error(data.error || 'Ошибка загрузки инструментов');
        }
    } catch (error) {
        console.error('Ошибка загрузки MCP инструментов:', error);
        toolsGrid.innerHTML = `
            <div class="mcp-placeholder">
                <p style="color: #dc3545;">❌ Ошибка загрузки: ${error.message}</p>
                <p>Убедитесь, что MCP сервер запущен и доступен</p>
                ${currentServer === 'github' ? '<p>Проверьте, что GitHub токен действителен</p>' : ''}
            </div>
        `;
    } finally {
        loadBtn.disabled = false;
        loadBtn.textContent = '🔄 Загрузить инструменты';
    }
}

// Отобразить инструменты
function displayMcpTools(tools) {
    const toolsGrid = document.getElementById('mcpToolsGrid');

    if (tools.length === 0) {
        toolsGrid.innerHTML = `
            <div class="mcp-placeholder">
                <p>Инструменты не найдены</p>
            </div>
        `;
        return;
    }

    toolsGrid.innerHTML = tools.map(tool => {
        const params = tool.inputSchema?.properties || {};
        const required = tool.inputSchema?.required || [];
        const paramCount = Object.keys(params).length;
        const requiredCount = required.length;

        return `
            <div class="mcp-tool-card" onclick="openToolModal('${tool.name}')">
                <div class="mcp-tool-header">
                    <div class="mcp-tool-name">
                        <span class="mcp-tool-icon">${getToolIcon(tool.name)}</span>
                        ${tool.name}
                    </div>
                </div>
                <div class="mcp-tool-description">${tool.description}</div>
                <div class="mcp-tool-schema">
                    <div class="mcp-schema-summary">
                        Параметры: ${paramCount}
                    </div>
                    <div class="mcp-schema-params">
                        ${requiredCount > 0 ? `Обязательных: ${requiredCount}` : 'Все опциональные'}
                    </div>
                </div>
            </div>
        `;
    }).join('');
}

// Открыть модальное окно вызова инструмента
function openToolModal(toolName) {
    console.log('🪟 openToolModal вызвана с toolName:', toolName);

    const tool = mcpTools.find(t => t.name === toolName);
    console.log('🔧 Найден инструмент:', tool);

    if (!tool) {
        console.error('❌ Инструмент не найден!');
        return;
    }

    currentTool = tool;
    console.log('✅ currentTool установлен:', currentTool.name);

    const modal = document.getElementById('mcpModal');
    const modalTitle = document.getElementById('mcpModalTitle');
    const toolInfo = document.getElementById('mcpToolInfo');
    const toolForm = document.getElementById('mcpToolForm');

    modalTitle.textContent = `${getToolIcon(tool.name)} ${tool.name}`;
    toolInfo.innerHTML = `
        <h4>${tool.description}</h4>
    `;

    // Создаем форму для параметров
    const params = tool.inputSchema?.properties || {};
    const required = tool.inputSchema?.required || [];

    console.log('📋 Параметры инструмента:', Object.keys(params));

    toolForm.innerHTML = Object.keys(params).map(paramName => {
        const param = params[paramName];
        const isRequired = required.includes(paramName);

        return createFormField(paramName, param, isRequired);
    }).join('');

    modal.style.display = 'flex';
    console.log('✅ Модальное окно открыто');
}

// Создать поле формы
function createFormField(name, schema, isRequired) {
    const label = `
        <label class="mcp-form-label">
            ${name}
            ${isRequired ? '<span class="required">*</span>' : ''}
        </label>
    `;

    const hint = schema.description ? `
        <div class="mcp-form-hint">${schema.description}</div>
    ` : '';

    let input = '';

    if (schema.enum) {
        // Поле select для enum
        const options = schema.enum.map(value =>
            `<option value="${value}">${value}</option>`
        ).join('');
        input = `
            <select class="mcp-form-select" name="${name}" ${isRequired ? 'required' : ''}>
                <option value="">-- Выберите --</option>
                ${options}
            </select>
        `;
    } else if (schema.type === 'number' || schema.type === 'integer') {
        // Поле для чисел
        input = `
            <input
                type="number"
                class="mcp-form-input"
                name="${name}"
                placeholder="${schema.default || ''}"
                ${isRequired ? 'required' : ''}
            />
        `;
    } else if (schema.type === 'boolean') {
        // Checkbox для boolean
        input = `
            <select class="mcp-form-select" name="${name}">
                <option value="">-- Выберите --</option>
                <option value="true">true</option>
                <option value="false">false</option>
            </select>
        `;
    } else {
        // Textarea для длинных текстов, input для коротких
        if (name.includes('text') || name.includes('json') || name.includes('string')) {
            input = `
                <textarea
                    class="mcp-form-textarea"
                    name="${name}"
                    placeholder="${schema.default || ''}"
                    ${isRequired ? 'required' : ''}
                ></textarea>
            `;
        } else {
            input = `
                <input
                    type="text"
                    class="mcp-form-input"
                    name="${name}"
                    placeholder="${schema.default || ''}"
                    ${isRequired ? 'required' : ''}
                />
            `;
        }
    }

    return `
        <div class="mcp-form-group">
            ${label}
            ${input}
            ${hint}
        </div>
    `;
}

// Закрыть модальное окно
function closeToolModal() {
    const modal = document.getElementById('mcpModal');
    modal.style.display = 'none';
    currentTool = null;
}

// Делаем функцию глобально доступной для onclick
window.openToolModal = openToolModal;

// Вызвать инструмент
async function callMcpTool() {
    console.log('🔧 callMcpTool вызвана');
    console.log('currentTool:', currentTool);

    if (!currentTool) {
        console.error('❌ currentTool пустой!');
        return;
    }

    const form = document.getElementById('mcpToolForm');
    console.log('📋 Форма найдена:', form);

    const formData = new FormData(form.querySelector('form') || form);
    const arguments = {};

    // Собираем аргументы из формы
    const inputs = form.querySelectorAll('input, select, textarea');
    console.log('📝 Найдено полей:', inputs.length);

    inputs.forEach(input => {
        const name = input.name;
        let value = input.value.trim();
        console.log(`  - ${name}: "${value}"`);

        if (value === '') {
            // Пропускаем пустые необязательные поля
            const schema = currentTool.inputSchema?.properties[name];
            if (schema?.default !== undefined) {
                value = schema.default;
            } else {
                return;
            }
        }

        // Преобразуем тип
        const schema = currentTool.inputSchema?.properties[name];
        if (schema) {
            if (schema.type === 'number' || schema.type === 'integer') {
                arguments[name] = parseFloat(value);
            } else if (schema.type === 'boolean') {
                arguments[name] = value === 'true';
            } else {
                arguments[name] = value;
            }
        } else {
            arguments[name] = value;
        }
    });

    console.log('📦 Аргументы:', arguments);

    // Отправляем запрос
    const callBtn = document.getElementById('mcpCallTool');
    callBtn.disabled = true;
    callBtn.textContent = '⏳ Выполнение...';

    try {
        // Выбираем endpoint в зависимости от сервера
        const endpoint = currentServer === 'github' ? '/mcp/github/call_tool' : '/mcp/call_tool';
        console.log('🌐 Отправка запроса к', endpoint);

        const response = await fetch(endpoint, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                tool_name: currentTool.name,
                arguments: arguments
            })
        });

        console.log('📡 Ответ получен:', response.status);
        const data = await response.json();
        console.log('📊 Данные:', data);

        displayToolResult(data);
        closeToolModal();
    } catch (error) {
        console.error('❌ Ошибка вызова инструмента:', error);
        alert('Ошибка вызова инструмента: ' + error.message);
    } finally {
        callBtn.disabled = false;
        callBtn.textContent = '🚀 Выполнить';
    }
}

// Отобразить результат вызова
function displayToolResult(result) {
    const resultsDiv = document.getElementById('mcpResults');
    const resultsContent = document.getElementById('mcpResultsContent');

    const isSuccess = result.success;
    const statusClass = isSuccess ? 'success' : 'error';
    const statusText = isSuccess ? '✅ Успешно' : '❌ Ошибка';

    let content = '';
    if (isSuccess && result.content) {
        content = result.content.map(c => c.text).join('\n');
    } else if (result.error) {
        content = result.error;
    }

    const resultHtml = `
        <div class="mcp-result-item">
            <div class="mcp-result-header">
                <div class="mcp-result-title">
                    ${getToolIcon(result.tool)} ${result.tool}
                </div>
                <div class="mcp-result-status ${statusClass}">
                    ${statusText}
                </div>
            </div>
            <div class="mcp-result-content">${content}</div>
        </div>
    `;

    resultsContent.insertAdjacentHTML('afterbegin', resultHtml);
    resultsDiv.style.display = 'block';

    // Прокрутить к результатам
    resultsDiv.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
}

// Инициализация при загрузке страницы
document.addEventListener('DOMContentLoaded', () => {
    // Кнопка загрузки инструментов
    const loadBtn = document.getElementById('loadMcpTools');
    if (loadBtn) {
        loadBtn.addEventListener('click', loadMcpTools);
    }

    // Закрытие модального окна
    const closeBtn = document.getElementById('mcpModalClose');
    const cancelBtn = document.getElementById('mcpCancelTool');
    const modal = document.getElementById('mcpModal');

    if (closeBtn) {
        closeBtn.addEventListener('click', closeToolModal);
    }

    if (cancelBtn) {
        cancelBtn.addEventListener('click', closeToolModal);
    }

    if (modal) {
        modal.addEventListener('click', (e) => {
            if (e.target === modal) {
                closeToolModal();
            }
        });
    }

    // Вызов инструмента
    const callBtn = document.getElementById('mcpCallTool');
    console.log('🔍 Поиск кнопки mcpCallTool:', callBtn);
    if (callBtn) {
        callBtn.addEventListener('click', callMcpTool);
        console.log('✅ Обработчик click добавлен для кнопки Выполнить');
    } else {
        console.error('❌ Кнопка mcpCallTool не найдена!');
    }
});
