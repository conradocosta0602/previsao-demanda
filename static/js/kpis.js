// KPIs Dashboard - JavaScript
// Controla filtros, gráficos e visualizações

// Estado Global
let currentView = 'mensal';
let filtros = {
    loja: '',
    produto: '',
    categoria: '',
    fornecedor: ''
};

let charts = {}; // Armazena instâncias dos gráficos

// ===== INICIALIZAÇÃO =====
document.addEventListener('DOMContentLoaded', function() {
    console.log('Inicializando Dashboard de KPIs...');

    // Carregar filtros
    carregarFiltros();

    // Carregar dados iniciais
    carregarDados();
});

// ===== FUNÇÕES DE FILTROS =====
function carregarFiltros() {
    // Buscar opções de filtros do backend
    fetch('/api/kpis/filtros')
        .then(response => response.json())
        .then(data => {
            preencherSelect('filter-loja', data.lojas || []);
            preencherSelect('filter-produto', data.produtos || []);
            preencherSelect('filter-categoria', data.categorias || []);
            preencherSelect('filter-fornecedor', data.fornecedores || []);
        })
        .catch(error => {
            console.error('Erro ao carregar filtros:', error);
        });
}

function preencherSelect(selectId, opcoes) {
    const select = document.getElementById(selectId);
    const optionDefault = select.querySelector('option[value=""]');

    // Limpar opções anteriores (mantendo a primeira)
    select.innerHTML = '';
    select.appendChild(optionDefault);

    // Adicionar novas opções
    opcoes.forEach(opcao => {
        const option = document.createElement('option');
        option.value = opcao.id || opcao.codigo;
        option.textContent = opcao.nome || opcao.descricao || opcao;
        select.appendChild(option);
    });
}

function aplicarFiltros() {
    filtros = {
        loja: document.getElementById('filter-loja').value,
        produto: document.getElementById('filter-produto').value,
        categoria: document.getElementById('filter-categoria').value,
        fornecedor: document.getElementById('filter-fornecedor').value
    };

    console.log('Aplicando filtros:', filtros);
    carregarDados();
}

function limparFiltros() {
    document.getElementById('filter-loja').value = '';
    document.getElementById('filter-produto').value = '';
    document.getElementById('filter-categoria').value = '';
    document.getElementById('filter-fornecedor').value = '';

    filtros = { loja: '', produto: '', categoria: '', fornecedor: '' };
    carregarDados();
}

// ===== MUDANÇA DE VISÃO =====
function mudarVisao(visao) {
    currentView = visao;

    // Atualizar tabs
    document.querySelectorAll('.view-tab').forEach(tab => {
        tab.classList.remove('active');
    });
    event.target.classList.add('active');

    // Atualizar conteúdo
    document.querySelectorAll('.view-content').forEach(content => {
        content.classList.remove('active');
    });

    document.getElementById(`demanda-${visao}`).classList.add('active');
    document.getElementById(`reabastecimento-${visao}`).classList.add('active');

    // Recarregar dados
    carregarDados();
}

// ===== CARREGAMENTO DE DADOS =====
function carregarDados() {
    const params = new URLSearchParams({
        visao: currentView,
        ...filtros
    });

    mostrarLoading(true);

    fetch(`/api/kpis/dados?${params}`)
        .then(response => response.json())
        .then(data => {
            atualizarMetricas(data.metricas_atuais);
            atualizarGraficos(data.series_temporais);
            atualizarTabelaPerformers(data.performers);
            mostrarLoading(false);
        })
        .catch(error => {
            console.error('Erro ao carregar dados:', error);
            mostrarLoading(false);
        });
}

// ===== ATUALIZAÇÃO DE MÉTRICAS =====
function atualizarMetricas(metricas) {
    // KPIs de Demanda
    document.getElementById('wmape-atual').textContent =
        metricas.wmape ? metricas.wmape.toFixed(1) + '%' : '-';
    document.getElementById('bias-atual').textContent =
        metricas.bias !== undefined ? (metricas.bias > 0 ? '+' : '') + metricas.bias.toFixed(2) : '-';
    document.getElementById('previsoes-excelentes').textContent =
        metricas.previsoes_excelentes || '-';
    document.getElementById('total-skus').textContent =
        metricas.total_skus || '-';

    // Tendências - Demanda
    atualizarTendencia('wmape-trend', metricas.wmape_tendencia);
    atualizarTendencia('bias-trend', metricas.bias_tendencia);
    atualizarTendencia('excelentes-trend', metricas.excelentes_tendencia);

    // KPIs de Reabastecimento
    document.getElementById('taxa-ruptura').textContent =
        metricas.taxa_ruptura ? metricas.taxa_ruptura.toFixed(1) + '%' : '-';
    document.getElementById('cobertura-media').textContent =
        metricas.cobertura_media ? metricas.cobertura_media.toFixed(1) + ' dias' : '-';
    document.getElementById('nivel-servico').textContent =
        metricas.nivel_servico ? metricas.nivel_servico.toFixed(1) + '%' : '-';
    document.getElementById('skus-criticos').textContent =
        metricas.skus_criticos || '-';

    // Tendências - Reabastecimento
    atualizarTendencia('ruptura-trend', metricas.ruptura_tendencia);
    atualizarTendencia('cobertura-trend', metricas.cobertura_tendencia);
    atualizarTendencia('servico-trend', metricas.servico_tendencia);
    atualizarTendencia('criticos-trend', metricas.criticos_tendencia);
}

function atualizarTendencia(elementId, tendencia) {
    const element = document.getElementById(elementId);
    if (!tendencia) return;

    element.className = 'metric-trend';

    if (tendencia.tipo === 'up') {
        element.classList.add('trend-up');
        element.textContent = `↑ ${tendencia.valor}`;
    } else if (tendencia.tipo === 'down') {
        element.classList.add('trend-down');
        element.textContent = `↓ ${tendencia.valor}`;
    } else {
        element.classList.add('trend-stable');
        element.textContent = `→ ${tendencia.valor}`;
    }
}

// ===== ATUALIZAÇÃO DE GRÁFICOS =====
function atualizarGraficos(series) {
    if (currentView === 'mensal') {
        criarGraficoWMAPEMensal(series.wmape_mensal || []);
        criarGraficoBIASMensal(series.bias_mensal || []);
        criarGraficoClassificacao(series.classificacao || []);
        criarGraficoRupturaMensal(series.ruptura_mensal || []);
        criarGraficoCoberturaMensal(series.cobertura_mensal || []);
        criarGraficoServicoMensal(series.servico_mensal || []);
    } else {
        criarGraficoWMAPESemanal(series.wmape_semanal || []);
        criarGraficoBIASSemanal(series.bias_semanal || []);
        criarGraficoRupturaSemanal(series.ruptura_semanal || []);
        criarGraficoCoberturaSemanal(series.cobertura_semanal || []);
    }
}

function criarGraficoWMAPEMensal(dados) {
    const ctx = document.getElementById('chart-wmape-mensal');
    if (!ctx) return;

    if (charts['wmape-mensal']) {
        charts['wmape-mensal'].destroy();
    }

    charts['wmape-mensal'] = new Chart(ctx, {
        type: 'line',
        data: {
            labels: dados.map(d => d.mes),
            datasets: [{
                label: 'WMAPE (%)',
                data: dados.map(d => d.wmape),
                borderColor: '#667eea',
                backgroundColor: 'rgba(102, 126, 234, 0.1)',
                borderWidth: 3,
                tension: 0.4,
                fill: true
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    display: false
                },
                tooltip: {
                    callbacks: {
                        label: function(context) {
                            return 'WMAPE: ' + context.parsed.y.toFixed(2) + '%';
                        }
                    }
                }
            },
            scales: {
                y: {
                    beginAtZero: true,
                    title: {
                        display: true,
                        text: 'WMAPE (%)'
                    },
                    grid: {
                        color: 'rgba(0, 0, 0, 0.05)'
                    }
                },
                x: {
                    grid: {
                        display: false
                    }
                }
            }
        }
    });
}

function criarGraficoBIASMensal(dados) {
    const ctx = document.getElementById('chart-bias-mensal');
    if (!ctx) return;

    if (charts['bias-mensal']) {
        charts['bias-mensal'].destroy();
    }

    charts['bias-mensal'] = new Chart(ctx, {
        type: 'line',
        data: {
            labels: dados.map(d => d.mes),
            datasets: [{
                label: 'BIAS',
                data: dados.map(d => d.bias),
                borderColor: '#f59e0b',
                backgroundColor: 'rgba(245, 158, 11, 0.1)',
                borderWidth: 3,
                tension: 0.4,
                fill: true
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    display: false
                },
                tooltip: {
                    callbacks: {
                        label: function(context) {
                            const valor = context.parsed.y;
                            return 'BIAS: ' + (valor > 0 ? '+' : '') + valor.toFixed(2);
                        }
                    }
                }
            },
            scales: {
                y: {
                    title: {
                        display: true,
                        text: 'BIAS'
                    },
                    grid: {
                        color: 'rgba(0, 0, 0, 0.05)'
                    }
                },
                x: {
                    grid: {
                        display: false
                    }
                }
            }
        }
    });
}

function criarGraficoClassificacao(dados) {
    const ctx = document.getElementById('chart-classificacao-wmape');
    if (!ctx) return;

    if (charts['classificacao']) {
        charts['classificacao'].destroy();
    }

    charts['classificacao'] = new Chart(ctx, {
        type: 'bar',
        data: {
            labels: dados.map(d => d.mes),
            datasets: [
                {
                    label: 'Excelente (<10%)',
                    data: dados.map(d => d.excelente),
                    backgroundColor: '#10b981',
                    stack: 'stack1'
                },
                {
                    label: 'Bom (10-20%)',
                    data: dados.map(d => d.bom),
                    backgroundColor: '#3b82f6',
                    stack: 'stack1'
                },
                {
                    label: 'Aceitável (20-30%)',
                    data: dados.map(d => d.aceitavel),
                    backgroundColor: '#f59e0b',
                    stack: 'stack1'
                },
                {
                    label: 'Fraca (>30%)',
                    data: dados.map(d => d.fraca),
                    backgroundColor: '#ef4444',
                    stack: 'stack1'
                }
            ]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    position: 'top'
                },
                tooltip: {
                    callbacks: {
                        label: function(context) {
                            return context.dataset.label + ': ' + context.parsed.y + ' SKUs';
                        }
                    }
                }
            },
            scales: {
                y: {
                    stacked: true,
                    title: {
                        display: true,
                        text: 'Quantidade de SKUs'
                    },
                    grid: {
                        color: 'rgba(0, 0, 0, 0.05)'
                    }
                },
                x: {
                    stacked: true,
                    grid: {
                        display: false
                    }
                }
            }
        }
    });
}

function criarGraficoRupturaMensal(dados) {
    const ctx = document.getElementById('chart-ruptura-mensal');
    if (!ctx) return;

    if (charts['ruptura-mensal']) {
        charts['ruptura-mensal'].destroy();
    }

    charts['ruptura-mensal'] = new Chart(ctx, {
        type: 'line',
        data: {
            labels: dados.map(d => d.mes),
            datasets: [{
                label: 'Taxa de Ruptura (%)',
                data: dados.map(d => d.taxa_ruptura),
                borderColor: '#ef4444',
                backgroundColor: 'rgba(239, 68, 68, 0.1)',
                borderWidth: 3,
                tension: 0.4,
                fill: true
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    display: false
                }
            },
            scales: {
                y: {
                    beginAtZero: true,
                    title: {
                        display: true,
                        text: 'Taxa de Ruptura (%)'
                    },
                    grid: {
                        color: 'rgba(0, 0, 0, 0.05)'
                    }
                },
                x: {
                    grid: {
                        display: false
                    }
                }
            }
        }
    });
}

function criarGraficoCoberturaMensal(dados) {
    const ctx = document.getElementById('chart-cobertura-mensal');
    if (!ctx) return;

    if (charts['cobertura-mensal']) {
        charts['cobertura-mensal'].destroy();
    }

    charts['cobertura-mensal'] = new Chart(ctx, {
        type: 'line',
        data: {
            labels: dados.map(d => d.mes),
            datasets: [{
                label: 'Cobertura Média (dias)',
                data: dados.map(d => d.cobertura_media),
                borderColor: '#10b981',
                backgroundColor: 'rgba(16, 185, 129, 0.1)',
                borderWidth: 3,
                tension: 0.4,
                fill: true
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    display: false
                }
            },
            scales: {
                y: {
                    beginAtZero: true,
                    title: {
                        display: true,
                        text: 'Dias de Cobertura'
                    },
                    grid: {
                        color: 'rgba(0, 0, 0, 0.05)'
                    }
                },
                x: {
                    grid: {
                        display: false
                    }
                }
            }
        }
    });
}

function criarGraficoServicoMensal(dados) {
    const ctx = document.getElementById('chart-servico-mensal');
    if (!ctx) return;

    if (charts['servico-mensal']) {
        charts['servico-mensal'].destroy();
    }

    charts['servico-mensal'] = new Chart(ctx, {
        type: 'line',
        data: {
            labels: dados.map(d => d.mes),
            datasets: [{
                label: 'Nível de Serviço (%)',
                data: dados.map(d => d.nivel_servico),
                borderColor: '#3b82f6',
                backgroundColor: 'rgba(59, 130, 246, 0.1)',
                borderWidth: 3,
                tension: 0.4,
                fill: true
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    display: false
                }
            },
            scales: {
                y: {
                    min: 80,
                    max: 100,
                    title: {
                        display: true,
                        text: 'Nível de Serviço (%)'
                    },
                    grid: {
                        color: 'rgba(0, 0, 0, 0.05)'
                    }
                },
                x: {
                    grid: {
                        display: false
                    }
                }
            }
        }
    });
}

// Gráficos Semanais (similares aos mensais, mas com dados semanais)
function criarGraficoWMAPESemanal(dados) {
    const ctx = document.getElementById('chart-wmape-semanal');
    if (!ctx) return;

    if (charts['wmape-semanal']) {
        charts['wmape-semanal'].destroy();
    }

    charts['wmape-semanal'] = new Chart(ctx, {
        type: 'line',
        data: {
            labels: dados.map(d => d.semana),
            datasets: [{
                label: 'WMAPE (%)',
                data: dados.map(d => d.wmape),
                borderColor: '#667eea',
                backgroundColor: 'rgba(102, 126, 234, 0.1)',
                borderWidth: 2,
                tension: 0.4,
                fill: true,
                pointRadius: 2
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    display: false
                }
            },
            scales: {
                y: {
                    beginAtZero: true,
                    title: {
                        display: true,
                        text: 'WMAPE (%)'
                    }
                },
                x: {
                    grid: {
                        display: false
                    }
                }
            }
        }
    });
}

function criarGraficoBIASSemanal(dados) {
    const ctx = document.getElementById('chart-bias-semanal');
    if (!ctx) return;

    if (charts['bias-semanal']) {
        charts['bias-semanal'].destroy();
    }

    charts['bias-semanal'] = new Chart(ctx, {
        type: 'line',
        data: {
            labels: dados.map(d => d.semana),
            datasets: [{
                label: 'BIAS',
                data: dados.map(d => d.bias),
                borderColor: '#f59e0b',
                backgroundColor: 'rgba(245, 158, 11, 0.1)',
                borderWidth: 2,
                tension: 0.4,
                fill: true,
                pointRadius: 2
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    display: false
                }
            },
            scales: {
                y: {
                    title: {
                        display: true,
                        text: 'BIAS'
                    }
                },
                x: {
                    grid: {
                        display: false
                    }
                }
            }
        }
    });
}

function criarGraficoRupturaSemanal(dados) {
    const ctx = document.getElementById('chart-ruptura-semanal');
    if (!ctx) return;

    if (charts['ruptura-semanal']) {
        charts['ruptura-semanal'].destroy();
    }

    charts['ruptura-semanal'] = new Chart(ctx, {
        type: 'line',
        data: {
            labels: dados.map(d => d.semana),
            datasets: [{
                label: 'Taxa de Ruptura (%)',
                data: dados.map(d => d.taxa_ruptura),
                borderColor: '#ef4444',
                backgroundColor: 'rgba(239, 68, 68, 0.1)',
                borderWidth: 2,
                tension: 0.4,
                fill: true,
                pointRadius: 2
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    display: false
                }
            },
            scales: {
                y: {
                    beginAtZero: true,
                    title: {
                        display: true,
                        text: 'Taxa de Ruptura (%)'
                    }
                },
                x: {
                    grid: {
                        display: false
                    }
                }
            }
        }
    });
}

function criarGraficoCoberturaSemanal(dados) {
    const ctx = document.getElementById('chart-cobertura-semanal');
    if (!ctx) return;

    if (charts['cobertura-semanal']) {
        charts['cobertura-semanal'].destroy();
    }

    charts['cobertura-semanal'] = new Chart(ctx, {
        type: 'line',
        data: {
            labels: dados.map(d => d.semana),
            datasets: [{
                label: 'Cobertura Média (dias)',
                data: dados.map(d => d.cobertura_media),
                borderColor: '#10b981',
                backgroundColor: 'rgba(16, 185, 129, 0.1)',
                borderWidth: 2,
                tension: 0.4,
                fill: true,
                pointRadius: 2
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    display: false
                }
            },
            scales: {
                y: {
                    beginAtZero: true,
                    title: {
                        display: true,
                        text: 'Dias de Cobertura'
                    }
                },
                x: {
                    grid: {
                        display: false
                    }
                }
            }
        }
    });
}

// ===== TABELA DE PERFORMERS =====
function atualizarTabelaPerformers(performers) {
    const tbody = document.getElementById('performers-table');
    if (!performers || performers.length === 0) {
        tbody.innerHTML = '<tr><td colspan="8" style="text-align: center; color: #6c757d;">Nenhum dado disponível</td></tr>';
        return;
    }

    tbody.innerHTML = '';

    performers.forEach(p => {
        const tr = document.createElement('tr');

        // Determinar status
        let statusClass = 'status-good';
        let statusText = 'Bom';

        if (p.wmape < 10 && p.taxa_ruptura < 5) {
            statusClass = 'status-excellent';
            statusText = 'Excelente';
        } else if (p.wmape > 30 || p.taxa_ruptura > 20) {
            statusClass = 'status-critical';
            statusText = 'Crítico';
        } else if (p.wmape > 20 || p.taxa_ruptura > 10) {
            statusClass = 'status-warning';
            statusText = 'Atenção';
        }

        tr.innerHTML = `
            <td><strong>${p.sku}</strong></td>
            <td>${p.descricao}</td>
            <td>${p.loja}</td>
            <td>${p.wmape ? p.wmape.toFixed(1) + '%' : '-'}</td>
            <td>${p.bias !== undefined ? (p.bias > 0 ? '+' : '') + p.bias.toFixed(2) : '-'}</td>
            <td>${p.taxa_ruptura ? p.taxa_ruptura.toFixed(1) + '%' : '-'}</td>
            <td>${p.cobertura ? p.cobertura.toFixed(1) + ' dias' : '-'}</td>
            <td><span class="status-badge ${statusClass}">${statusText}</span></td>
        `;

        tbody.appendChild(tr);
    });
}

// ===== LOADING STATE =====
function mostrarLoading(show) {
    // Implementar indicador de loading se necessário
    console.log('Loading:', show);
}
