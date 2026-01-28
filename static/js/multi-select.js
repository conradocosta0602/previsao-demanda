/**
 * Componente Multi-Select com Checkboxes
 *
 * Uso:
 * 1. No HTML, adicione um container com a classe 'multi-select-wrapper' e data-attributes:
 *    <div class="multi-select-wrapper"
 *         data-id="meuFiltro"
 *         data-placeholder="Selecione..."
 *         data-all-selected-text="Todos selecionados"
 *         data-none-selected-text="Nenhum selecionado">
 *    </div>
 *
 * 2. No JavaScript, inicialize com:
 *    MultiSelect.create('meuFiltro', opcoes, { onchange: callback });
 *
 * 3. Para obter valores selecionados:
 *    MultiSelect.getSelected('meuFiltro');
 *
 * 4. Para definir valores:
 *    MultiSelect.setSelected('meuFiltro', ['valor1', 'valor2']);
 */

const MultiSelect = {
    instances: {},

    /**
     * Cria um novo componente multi-select
     * @param {string} id - ID único do componente
     * @param {Array} options - Array de opções [{value: '', label: ''}, ...] ou ['item1', 'item2']
     * @param {Object} config - Configurações opcionais
     */
    create: function(id, options, config = {}) {
        const container = document.querySelector(`[data-id="${id}"]`) || document.getElementById(`${id}MultiSelect`);
        if (!container) {
            console.warn(`MultiSelect: Container para '${id}' não encontrado`);
            return null;
        }

        // Configurações padrão
        const settings = {
            placeholder: config.placeholder || container.dataset.placeholder || 'Selecione...',
            allSelectedText: config.allSelectedText || container.dataset.allSelectedText || 'Todos selecionados',
            noneSelectedText: config.noneSelectedText || container.dataset.noneSelectedText || 'Nenhum selecionado',
            countSelectedText: config.countSelectedText || '{count} selecionados',
            selectAllText: config.selectAllText || 'Marcar Todos',
            deselectAllText: config.deselectAllText || 'Desmarcar Todos',
            selectAllByDefault: config.selectAllByDefault !== false, // true por padrão
            showSelectAll: config.showSelectAll !== false, // true por padrão
            onchange: config.onchange || null,
            maxHeight: config.maxHeight || '250px'
        };

        // Normalizar opções
        const normalizedOptions = options.map((opt, idx) => {
            if (typeof opt === 'string') {
                return { value: opt, label: opt };
            }
            return { value: opt.value || opt.codigo || opt.id, label: opt.label || opt.nome || opt.descricao || opt.value };
        });

        // Armazenar instância
        this.instances[id] = {
            options: normalizedOptions,
            selected: settings.selectAllByDefault ? normalizedOptions.map(o => o.value) : [],
            settings: settings,
            container: container
        };

        // Renderizar HTML
        this._render(id);

        // Configurar eventos
        this._setupEvents(id);

        return this.instances[id];
    },

    /**
     * Renderiza o componente
     */
    _render: function(id) {
        const instance = this.instances[id];
        const { options, settings, container } = instance;

        container.className = 'multi-select-container';
        container.innerHTML = `
            <div class="multi-select-header" id="${id}Header">
                <span class="multi-select-text" id="${id}Text">${settings.placeholder}</span>
                <span class="multi-select-arrow">▼</span>
            </div>
            <div class="multi-select-dropdown" id="${id}Dropdown" style="display: none;">
                ${settings.showSelectAll ? `
                <div class="multi-select-actions">
                    <button type="button" class="ms-btn-select-all" data-action="selectAll">${settings.selectAllText}</button>
                    <button type="button" class="ms-btn-deselect-all" data-action="deselectAll">${settings.deselectAllText}</button>
                </div>
                ` : ''}
                <div class="multi-select-options" id="${id}Options" style="max-height: ${settings.maxHeight};">
                    ${options.map((opt, idx) => `
                        <div class="multi-select-option" data-value="${opt.value}">
                            <input type="checkbox" id="${id}_opt_${idx}" value="${opt.value}" ${instance.selected.includes(opt.value) ? 'checked' : ''}>
                            <label for="${id}_opt_${idx}">${opt.label}</label>
                        </div>
                    `).join('')}
                </div>
            </div>
            <input type="hidden" id="${id}" name="${id}" value="">
        `;

        // Atualizar texto e hidden input
        this._updateDisplay(id);
    },

    /**
     * Configura eventos do componente
     */
    _setupEvents: function(id) {
        const instance = this.instances[id];
        const container = instance.container;

        // Toggle dropdown
        const header = container.querySelector(`#${id}Header`);
        header.addEventListener('click', (e) => {
            e.stopPropagation();
            this.toggle(id);
        });

        // Botões Marcar/Desmarcar Todos
        const actions = container.querySelectorAll('.multi-select-actions button');
        actions.forEach(btn => {
            btn.addEventListener('click', (e) => {
                e.stopPropagation();
                if (btn.dataset.action === 'selectAll') {
                    this.selectAll(id);
                } else {
                    this.deselectAll(id);
                }
            });
        });

        // Checkboxes
        const optionsContainer = container.querySelector(`#${id}Options`);
        optionsContainer.addEventListener('change', (e) => {
            if (e.target.type === 'checkbox') {
                this._handleCheckboxChange(id, e.target.value, e.target.checked);
            }
        });

        // Clique na opção (não apenas no checkbox)
        optionsContainer.addEventListener('click', (e) => {
            const option = e.target.closest('.multi-select-option');
            if (option && e.target.tagName !== 'INPUT') {
                const checkbox = option.querySelector('input[type="checkbox"]');
                checkbox.checked = !checkbox.checked;
                this._handleCheckboxChange(id, checkbox.value, checkbox.checked);
            }
        });

        // Fechar ao clicar fora
        document.addEventListener('click', (e) => {
            if (!container.contains(e.target)) {
                this.close(id);
            }
        });
    },

    /**
     * Manipula mudança de checkbox
     */
    _handleCheckboxChange: function(id, value, checked) {
        const instance = this.instances[id];

        if (checked) {
            if (!instance.selected.includes(value)) {
                instance.selected.push(value);
            }
        } else {
            instance.selected = instance.selected.filter(v => v !== value);
        }

        this._updateDisplay(id);

        // Callback
        if (instance.settings.onchange) {
            instance.settings.onchange(instance.selected, id);
        }
    },

    /**
     * Atualiza texto exibido e hidden input
     */
    _updateDisplay: function(id) {
        const instance = this.instances[id];
        const { selected, options, settings, container } = instance;

        const textEl = container.querySelector(`#${id}Text`);
        const hiddenInput = container.querySelector(`#${id}`);

        // Atualizar texto
        if (selected.length === 0) {
            textEl.textContent = settings.noneSelectedText;
        } else if (selected.length === options.length) {
            textEl.textContent = settings.allSelectedText;
        } else if (selected.length === 1) {
            const opt = options.find(o => o.value === selected[0]);
            textEl.textContent = opt ? opt.label : selected[0];
        } else {
            textEl.textContent = settings.countSelectedText.replace('{count}', selected.length);
        }

        // Atualizar hidden input (JSON se múltiplos, vazio se todos)
        if (selected.length === options.length || selected.length === 0) {
            hiddenInput.value = '';
        } else {
            hiddenInput.value = JSON.stringify(selected);
        }
    },

    /**
     * Abre/fecha o dropdown
     */
    toggle: function(id) {
        const dropdown = document.getElementById(`${id}Dropdown`);
        const container = this.instances[id].container;

        if (dropdown.style.display === 'none') {
            // Fechar outros dropdowns abertos
            Object.keys(this.instances).forEach(otherId => {
                if (otherId !== id) this.close(otherId);
            });
            dropdown.style.display = 'block';
            container.classList.add('open');
        } else {
            dropdown.style.display = 'none';
            container.classList.remove('open');
        }
    },

    /**
     * Fecha o dropdown
     */
    close: function(id) {
        const instance = this.instances[id];
        if (!instance) return;

        const dropdown = document.getElementById(`${id}Dropdown`);
        if (dropdown) {
            dropdown.style.display = 'none';
            instance.container.classList.remove('open');
        }
    },

    /**
     * Seleciona todos
     */
    selectAll: function(id) {
        const instance = this.instances[id];
        instance.selected = instance.options.map(o => o.value);

        // Atualizar checkboxes
        const checkboxes = instance.container.querySelectorAll(`#${id}Options input[type="checkbox"]`);
        checkboxes.forEach(cb => cb.checked = true);

        this._updateDisplay(id);

        if (instance.settings.onchange) {
            instance.settings.onchange(instance.selected, id);
        }
    },

    /**
     * Desmarca todos
     */
    deselectAll: function(id) {
        const instance = this.instances[id];
        instance.selected = [];

        // Atualizar checkboxes
        const checkboxes = instance.container.querySelectorAll(`#${id}Options input[type="checkbox"]`);
        checkboxes.forEach(cb => cb.checked = false);

        this._updateDisplay(id);

        if (instance.settings.onchange) {
            instance.settings.onchange(instance.selected, id);
        }
    },

    /**
     * Obtém valores selecionados
     */
    getSelected: function(id) {
        const instance = this.instances[id];
        if (!instance) return [];

        // Se todos estão selecionados, retorna array vazio (significa "TODOS")
        if (instance.selected.length === instance.options.length) {
            return [];
        }
        return [...instance.selected];
    },

    /**
     * Obtém valores selecionados (sempre retorna array, mesmo se todos)
     */
    getSelectedAll: function(id) {
        const instance = this.instances[id];
        return instance ? [...instance.selected] : [];
    },

    /**
     * Define valores selecionados
     */
    setSelected: function(id, values) {
        const instance = this.instances[id];
        if (!instance) return;

        instance.selected = Array.isArray(values) ? values : [values];

        // Atualizar checkboxes
        const checkboxes = instance.container.querySelectorAll(`#${id}Options input[type="checkbox"]`);
        checkboxes.forEach(cb => {
            cb.checked = instance.selected.includes(cb.value);
        });

        this._updateDisplay(id);
    },

    /**
     * Atualiza opções do componente
     */
    updateOptions: function(id, options, keepSelection = true) {
        const instance = this.instances[id];
        if (!instance) return;

        const previousSelected = keepSelection ? [...instance.selected] : [];

        // Normalizar opções
        instance.options = options.map((opt) => {
            if (typeof opt === 'string') {
                return { value: opt, label: opt };
            }
            return { value: opt.value || opt.codigo || opt.id, label: opt.label || opt.nome || opt.descricao || opt.value };
        });

        // Manter seleção anterior se possível
        if (keepSelection) {
            instance.selected = previousSelected.filter(v => instance.options.some(o => o.value === v));
            if (instance.selected.length === 0 && instance.settings.selectAllByDefault) {
                instance.selected = instance.options.map(o => o.value);
            }
        } else {
            instance.selected = instance.settings.selectAllByDefault ? instance.options.map(o => o.value) : [];
        }

        this._render(id);
        this._setupEvents(id);
    },

    /**
     * Destrói o componente
     */
    destroy: function(id) {
        const instance = this.instances[id];
        if (instance) {
            instance.container.innerHTML = '';
            delete this.instances[id];
        }
    }
};

// Exportar para uso global
window.MultiSelect = MultiSelect;
