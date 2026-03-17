// KPIs Dashboard - JavaScript
// Controla filtros, graficos e visualizacoes
// Versao 3.0 - Marco 2026 (Ruptura + Cobertura + Excesso)

// ========================================
// ESTADO GLOBAL
// ========================================
let state = {
    visaoTemporal: 'mensal',      // mensal, semanal, diario
    agregacao: 'geral',            // geral, fornecedor, linha, filial, item
    filtros: {
        fornecedores: [],
        categorias: [],
        linhas3: [],
        filiais: []
    },
    ranking: {
        pagina: 1,
        porPagina: 20,
        ordenarPor: 'ruptura',
        ordem: 'desc'
    }
};

let charts = {};
let filtrosData = {};

// Cores padrao
const CORES = {
    ruptura: '#ef4444',
    cobertura: '#3b82f6',
    excesso: '#f59e0b',
    melhorHistorico: '#9ca3af',
    meta90: '#10b981'
};

// Faixas de alerta
const FAIXAS = {
    ruptura: { verde: 5, amarelo: 10 },           // < 5% verde, 5-10% amarelo, >10% vermelho
    cobertura: { vermelhoBaixo: 30, verde: 90, amarelo: 120 },  // <30 vermelho, 30-90 verde, 90-120 amarelo, >120 vermelho
    excesso: { verde: 10, amarelo: 20 }            // < 10% verde, 10-20% amarelo, >20% vermelho
};

// ========================================
// INICIALIZACAO
// ========================================
document.addEventListener('DOMContentLoaded', function() {
    console.log('Inicializando Dashboard de KPIs v3.0...');
    inicializarEventListeners();
    carregarFiltros();
    carregarDados();
});

function inicializarEventListeners() {
    document.querySelectorAll('input[name="visao-temporal"]').forEach(radio => {
        radio.addEventListener('change', (e) => {
            state.visaoTemporal = e.target.value;
            carregarDados();
        });
    });

    document.querySelectorAll('input[name="agregacao"]').forEach(radio => {
        radio.addEventListener('change', (e) => {
            state.agregacao = e.target.value;
            carregarDados();
        });
    });

    document.querySelectorAll('.sortable').forEach(th => {
        th.addEventListener('click', () => {
            const campo = th.dataset.sort;
            if (state.ranking.ordenarPor === campo) {
                state.ranking.ordem = state.ranking.ordem === 'asc' ? 'desc' : 'asc';
            } else {
                state.ranking.ordenarPor = campo;
                state.ranking.ordem = 'desc';
            }
            atualizarIconesOrdenacao();
            carregarRanking();
        });
    });
}

// ========================================
// FILTROS
// ========================================
function carregarFiltros() {
    fetch('/api/kpis/filtros')
        .then(response => response.json())
        .then(data => {
            filtrosData = data;

            if (data.fornecedores && data.fornecedores.length > 0) {
                MultiSelect.create('filter-fornecedor', data.fornecedores.map(f => ({
                    value: f, label: f
                })), {
                    allSelectedText: 'Todos os fornecedores',
                    selectAllByDefault: true,
                    onchange: () => {}
                });
            }

            if (data.categorias && data.categorias.length > 0) {
                MultiSelect.create('filter-categoria', data.categorias.map(c => ({
                    value: c, label: c
                })), {
                    allSelectedText: 'Todas as categorias',
                    selectAllByDefault: true,
                    onchange: () => atualizarLinhas3()
                });
            }

            atualizarLinhas3();

            if (data.filiais && data.filiais.length > 0) {
                MultiSelect.create('filter-filial', data.filiais.map(f => ({
                    value: f.codigo.toString(),
                    label: `${f.codigo} - ${f.nome}`
                })), {
                    allSelectedText: 'Todas as filiais',
                    selectAllByDefault: true,
                    onchange: () => {}
                });
            }
        })
        .catch(error => {
            console.error('Erro ao carregar filtros:', error);
        });
}

function atualizarLinhas3() {
    const categoriasSelecionadas = MultiSelect.getSelected('filter-categoria') || [];
    let linhas3Filtradas = [];

    if (filtrosData.linhas3_por_categoria) {
        if (categoriasSelecionadas.length === 0) {
            Object.values(filtrosData.linhas3_por_categoria).forEach(linhas => {
                linhas3Filtradas = linhas3Filtradas.concat(linhas);
            });
        } else {
            categoriasSelecionadas.forEach(cat => {
                if (filtrosData.linhas3_por_categoria[cat]) {
                    linhas3Filtradas = linhas3Filtradas.concat(filtrosData.linhas3_por_categoria[cat]);
                }
            });
        }
    }

    linhas3Filtradas = [...new Set(linhas3Filtradas)];

    MultiSelect.create('filter-linha3', linhas3Filtradas.map(l => ({
        value: l.codigo,
        label: `${l.codigo} - ${l.descricao}`
    })), {
        allSelectedText: 'Todas as linhas',
        selectAllByDefault: true,
        onchange: () => {}
    });
}

function aplicarFiltros() {
    state.filtros = {
        fornecedores: MultiSelect.getSelected('filter-fornecedor') || [],
        categorias: MultiSelect.getSelected('filter-categoria') || [],
        linhas3: MultiSelect.getSelected('filter-linha3') || [],
        filiais: MultiSelect.getSelected('filter-filial') || []
    };
    state.ranking.pagina = 1;
    console.log('Aplicando filtros:', state.filtros);
    carregarDados();
}

function limparFiltros() {
    MultiSelect.selectAll('filter-fornecedor');
    MultiSelect.selectAll('filter-categoria');
    MultiSelect.selectAll('filter-linha3');
    MultiSelect.selectAll('filter-filial');

    state.filtros = {
        fornecedores: [],
        categorias: [],
        linhas3: [],
        filiais: []
    };
    state.ranking.pagina = 1;
    carregarDados();
}

// ========================================
// CARREGAMENTO DE DADOS
// ========================================
function carregarDados() {
    mostrarLoading(true);

    Promise.all([
        carregarResumo(),
        carregarEvolucao(),
        carregarRanking()
    ]).then(() => {
        mostrarLoading(false);
    }).catch(error => {
        console.error('Erro ao carregar dados:', error);
        mostrarLoading(false);
    });
}

function buildQueryParams() {
    const params = new URLSearchParams();
    params.append('visao', state.visaoTemporal);
    params.append('agregacao', state.agregacao);

    // Dias baseado na visao temporal
    const diasMap = { mensal: 365, semanal: 180, diario: 30 };
    params.append('dias', diasMap[state.visaoTemporal] || 365);

    // Enviar filtros como valores individuais (formato getlist)
    if (state.filtros.fornecedores.length > 0) {
        state.filtros.fornecedores.forEach(v => params.append('fornecedor', v));
    }
    if (state.filtros.categorias.length > 0) {
        state.filtros.categorias.forEach(v => params.append('categoria', v));
    }
    if (state.filtros.linhas3.length > 0) {
        state.filtros.linhas3.forEach(v => params.append('codigo_linha', v));
    }
    if (state.filtros.filiais.length > 0) {
        state.filtros.filiais.forEach(v => params.append('cod_empresa', v));
    }

    return params;
}

function carregarResumo() {
    const params = buildQueryParams();
    return fetch(`/api/kpis/resumo?${params}`)
        .then(response => response.json())
        .then(data => {
            atualizarCardsKPI(data);
        });
}

function carregarEvolucao() {
    const params = buildQueryParams();
    return fetch(`/api/kpis/evolucao?${params}`)
        .then(response => response.json())
        .then(data => {
            atualizarGraficos(data);
        });
}

function carregarRanking() {
    const params = buildQueryParams();
    params.append('pagina', state.ranking.pagina);
    params.append('por_pagina', state.ranking.porPagina);
    params.append('ordenar_por', state.ranking.ordenarPor);
    params.append('ordem', state.ranking.ordem);

    return fetch(`/api/kpis/ranking?${params}`)
        .then(response => response.json())
        .then(data => {
            atualizarTabelaRanking(data);
        });
}

// ========================================
// ATUALIZACAO DOS CARDS KPI
// ========================================
function atualizarCardsKPI(data) {
    // Ruptura
    atualizarCardKPI('ruptura', data.ruptura, '%', getCorRuptura, true);

    // Cobertura
    atualizarCardKPI('cobertura', data.cobertura, ' dias', getCorCobertura, false);

    // Excesso
    atualizarCardKPI('excesso', data.excesso, '%', getCorExcesso, true);

    // Faixas de excesso
    atualizarFaixasExcesso(data.excesso);
}

function atualizarCardKPI(id, dados, sufixo, getCorFunc, menorMelhor) {
    if (!dados) return;

    const valorEl = document.getElementById(`kpi-${id}-valor`);
    const tendenciaEl = document.getElementById(`kpi-${id}-tendencia`);
    const badgeEl = document.getElementById(`kpi-${id}-badge`);

    if (valorEl) {
        const valor = dados.valor;
        if (valor !== null && valor !== undefined) {
            valorEl.textContent = (id === 'cobertura' ? Math.round(valor) : valor.toFixed(1)) + sufixo;
        } else {
            valorEl.textContent = '-';
        }
    }

    if (tendenciaEl) {
        let texto = dados.periodo || '';

        if (dados.variacao !== undefined && dados.variacao !== 0) {
            const sinal = dados.variacao > 0 ? '+' : '';
            const unidade = id === 'cobertura' ? 'd' : '%';
            texto += ` | ${sinal}${dados.variacao.toFixed(1)}${unidade} vs anterior`;
        }

        tendenciaEl.textContent = texto;
        tendenciaEl.className = 'kpi-tendencia';

        if (dados.variacao !== undefined && dados.variacao !== 0) {
            if (menorMelhor) {
                // Para ruptura e excesso: diminuir e bom
                tendenciaEl.classList.add(dados.variacao <= 0 ? 'tendencia-positiva' : 'tendencia-negativa');
            } else {
                // Para cobertura: depende da faixa
                // Se cobertura < 90 e subiu, e bom. Se cobertura > 90 e subiu, pode ser ruim
                const cobAtual = dados.valor || 0;
                if (cobAtual <= 90) {
                    tendenciaEl.classList.add(dados.variacao >= 0 ? 'tendencia-positiva' : 'tendencia-negativa');
                } else {
                    tendenciaEl.classList.add(dados.variacao <= 0 ? 'tendencia-positiva' : 'tendencia-negativa');
                }
            }
        }
    }

    if (badgeEl && getCorFunc) {
        const cor = getCorFunc(dados.valor);
        badgeEl.className = `kpi-badge badge-${cor}`;
        badgeEl.textContent = getTextoStatus(cor);
    }
}

function atualizarFaixasExcesso(dados) {
    if (!dados) return;

    const container = document.getElementById('excesso-faixas');
    if (!container) return;

    const total = dados.total_itens || 1;
    const faixas = [
        { label: '> 180 dias', valor: dados.faixa_acima_180 || 0, cor: '#dc2626' },
        { label: '120-180 dias', valor: dados.faixa_120_180 || 0, cor: '#f59e0b' },
        { label: '90-120 dias', valor: dados.faixa_90_120 || 0, cor: '#fbbf24' }
    ];

    container.innerHTML = faixas.map(f => {
        const pct = total > 0 ? ((f.valor / total) * 100).toFixed(1) : 0;
        const barWidth = Math.min(pct * 2, 100); // Escala visual
        return `
            <div class="faixa-item">
                <div class="faixa-label">${f.label}</div>
                <div class="faixa-bar-container">
                    <div class="faixa-bar" style="width: ${barWidth}%; background: ${f.cor};"></div>
                </div>
                <div class="faixa-valor">${f.valor} <span class="faixa-pct">(${pct}%)</span></div>
            </div>
        `;
    }).join('');
}

function getCorRuptura(valor) {
    if (valor === null || valor === undefined) return 'cinza';
    if (valor < FAIXAS.ruptura.verde) return 'verde';
    if (valor <= FAIXAS.ruptura.amarelo) return 'amarelo';
    return 'vermelho';
}

function getCorCobertura(valor) {
    if (valor === null || valor === undefined) return 'cinza';
    if (valor < FAIXAS.cobertura.vermelhoBaixo) return 'vermelho';
    if (valor <= FAIXAS.cobertura.verde) return 'verde';
    if (valor <= FAIXAS.cobertura.amarelo) return 'amarelo';
    return 'vermelho';
}

function getCorExcesso(valor) {
    if (valor === null || valor === undefined) return 'cinza';
    if (valor < FAIXAS.excesso.verde) return 'verde';
    if (valor <= FAIXAS.excesso.amarelo) return 'amarelo';
    return 'vermelho';
}

function getTextoStatus(cor) {
    const textos = {
        'verde': 'Bom',
        'amarelo': 'Atencao',
        'vermelho': 'Critico',
        'azul': 'Excelente',
        'cinza': '-'
    };
    return textos[cor] || '-';
}

// ========================================
// ATUALIZACAO DOS GRAFICOS
// ========================================
function atualizarGraficos(data) {
    if (!data) return;

    Object.keys(charts).forEach(key => {
        if (charts[key]) charts[key].destroy();
    });
    charts = {};

    criarGraficoRuptura(data.ruptura || []);
    criarGraficoCobertura(data.cobertura || []);
    criarGraficoExcesso(data.excesso || []);
}

function criarGraficoRuptura(dados) {
    const ctx = document.getElementById('chart-ruptura');
    if (!ctx || !dados.length) return;

    const labels = dados.map(d => d.periodo);
    const valores = dados.map(d => d.valor);
    const melhor = dados.map(d => d.melhor_historico);

    charts['ruptura'] = new Chart(ctx, {
        type: 'line',
        data: {
            labels: labels,
            datasets: [
                {
                    label: 'Ruptura (%)',
                    data: valores,
                    borderColor: CORES.ruptura,
                    backgroundColor: hexToRgba(CORES.ruptura, 0.1),
                    borderWidth: 3,
                    tension: 0.4,
                    fill: true,
                    pointRadius: 4,
                    pointHoverRadius: 6
                },
                {
                    label: 'Melhor Historico',
                    data: melhor,
                    borderColor: CORES.melhorHistorico,
                    borderWidth: 2,
                    borderDash: [5, 5],
                    tension: 0.4,
                    fill: false,
                    pointRadius: 0
                }
            ]
        },
        options: getOptionsGrafico('Taxa de Ruptura (%)', true)
    });
}

function criarGraficoCobertura(dados) {
    const ctx = document.getElementById('chart-cobertura');
    if (!ctx || !dados.length) return;

    const labels = dados.map(d => d.periodo);
    const valores = dados.map(d => d.valor);
    const meta = dados.map(() => 90);

    charts['cobertura'] = new Chart(ctx, {
        type: 'line',
        data: {
            labels: labels,
            datasets: [
                {
                    label: 'Cobertura (dias)',
                    data: valores,
                    borderColor: CORES.cobertura,
                    backgroundColor: hexToRgba(CORES.cobertura, 0.1),
                    borderWidth: 3,
                    tension: 0.4,
                    fill: true,
                    pointRadius: 4,
                    pointHoverRadius: 6
                },
                {
                    label: 'Meta (90 dias)',
                    data: meta,
                    borderColor: CORES.meta90,
                    borderWidth: 2,
                    borderDash: [5, 5],
                    tension: 0,
                    fill: false,
                    pointRadius: 0
                }
            ]
        },
        options: getOptionsGrafico('Cobertura Media (dias)', true)
    });
}

function criarGraficoExcesso(dados) {
    const ctx = document.getElementById('chart-excesso');
    if (!ctx || !dados.length) return;

    const labels = dados.map(d => d.periodo);
    const valores = dados.map(d => d.valor);
    const melhor = dados.map(d => d.melhor_historico);

    charts['excesso'] = new Chart(ctx, {
        type: 'line',
        data: {
            labels: labels,
            datasets: [
                {
                    label: 'Excesso (%)',
                    data: valores,
                    borderColor: CORES.excesso,
                    backgroundColor: hexToRgba(CORES.excesso, 0.1),
                    borderWidth: 3,
                    tension: 0.4,
                    fill: true,
                    pointRadius: 4,
                    pointHoverRadius: 6
                },
                {
                    label: 'Melhor Historico',
                    data: melhor,
                    borderColor: CORES.melhorHistorico,
                    borderWidth: 2,
                    borderDash: [5, 5],
                    tension: 0.4,
                    fill: false,
                    pointRadius: 0
                }
            ]
        },
        options: getOptionsGrafico('Itens em Excesso (%)', true)
    });
}

function getOptionsGrafico(titulo, beginAtZero = true) {
    return {
        responsive: true,
        maintainAspectRatio: false,
        interaction: {
            intersect: false,
            mode: 'index'
        },
        plugins: {
            legend: {
                display: true,
                position: 'top',
                labels: {
                    usePointStyle: true,
                    padding: 15,
                    font: { size: 11 }
                }
            },
            tooltip: {
                backgroundColor: 'rgba(0, 0, 0, 0.8)',
                titleFont: { size: 13 },
                bodyFont: { size: 12 },
                padding: 12,
                cornerRadius: 8
            }
        },
        scales: {
            y: {
                beginAtZero: beginAtZero,
                title: {
                    display: true,
                    text: titulo,
                    font: { size: 12, weight: 'bold' }
                },
                grid: { color: 'rgba(0, 0, 0, 0.05)' }
            },
            x: {
                grid: { display: false },
                ticks: {
                    maxRotation: 45,
                    minRotation: 0
                }
            }
        }
    };
}

// ========================================
// TABELA DE RANKING
// ========================================
function atualizarTabelaRanking(data) {
    const tbody = document.getElementById('ranking-tbody');
    const paginacaoInfo = document.getElementById('paginacao-info');

    if (!tbody) return;

    if (!data || !data.itens || data.itens.length === 0) {
        tbody.innerHTML = `
            <tr>
                <td colspan="7" class="text-center text-muted py-4">
                    Nenhum dado encontrado para os filtros selecionados
                </td>
            </tr>
        `;
        if (paginacaoInfo) paginacaoInfo.textContent = '';
        return;
    }

    tbody.innerHTML = '';

    data.itens.forEach(item => {
        const tr = document.createElement('tr');

        const badgeRuptura = item.ruptura !== null ? `<span class="badge badge-${getCorRuptura(item.ruptura)}">${item.ruptura.toFixed(1)}%</span>` : '-';
        const badgeCobertura = item.cobertura !== null ? `<span class="badge badge-${getCorCobertura(item.cobertura)}">${Math.round(item.cobertura)}d</span>` : '-';
        const badgeExcesso = item.excesso !== null ? `<span class="badge badge-${getCorExcesso(item.excesso)}">${item.excesso.toFixed(1)}%</span>` : '-';

        tr.innerHTML = `
            <td class="fw-medium">${item.identificador || '-'}</td>
            <td>${item.descricao || '-'}</td>
            <td>${badgeRuptura}</td>
            <td>${badgeCobertura}</td>
            <td>${badgeExcesso}</td>
            <td>${item.total_skus || '-'}</td>
            <td>${item.skus_ruptura || '-'}</td>
        `;

        tbody.appendChild(tr);
    });

    if (paginacaoInfo) {
        const inicio = (data.pagina - 1) * data.por_pagina + 1;
        const fim = Math.min(data.pagina * data.por_pagina, data.total);
        paginacaoInfo.textContent = `Mostrando ${inicio}-${fim} de ${data.total}`;
    }

    atualizarBotoesPaginacao(data);
}

function atualizarBotoesPaginacao(data) {
    const btnAnterior = document.getElementById('btn-pagina-anterior');
    const btnProxima = document.getElementById('btn-pagina-proxima');

    if (btnAnterior) btnAnterior.disabled = data.pagina <= 1;
    if (btnProxima) btnProxima.disabled = data.pagina >= data.total_paginas;
}

function paginaAnterior() {
    if (state.ranking.pagina > 1) {
        state.ranking.pagina--;
        carregarRanking();
    }
}

function proximaPagina() {
    state.ranking.pagina++;
    carregarRanking();
}

function atualizarIconesOrdenacao() {
    document.querySelectorAll('.sortable').forEach(th => {
        const icone = th.querySelector('.sort-icon');
        if (icone) {
            if (th.dataset.sort === state.ranking.ordenarPor) {
                icone.textContent = state.ranking.ordem === 'asc' ? '\u2191' : '\u2193';
                icone.style.opacity = '1';
            } else {
                icone.textContent = '\u2195';
                icone.style.opacity = '0.3';
            }
        }
    });
}

// ========================================
// UTILITARIOS
// ========================================
function hexToRgba(hex, alpha) {
    const r = parseInt(hex.slice(1, 3), 16);
    const g = parseInt(hex.slice(3, 5), 16);
    const b = parseInt(hex.slice(5, 7), 16);
    return `rgba(${r}, ${g}, ${b}, ${alpha})`;
}

function mostrarLoading(show) {
    const overlay = document.getElementById('loading-overlay');
    if (overlay) overlay.style.display = show ? 'flex' : 'none';
}

// Expor funcoes globalmente
window.aplicarFiltros = aplicarFiltros;
window.limparFiltros = limparFiltros;
window.paginaAnterior = paginaAnterior;
window.proximaPagina = proximaPagina;
