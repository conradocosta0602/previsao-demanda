// Acuracia Dashboard - JavaScript
// Compara previsao vs realizado: WMAPE, BIAS, MAE
// V49 - Marco 2026

// ========================================
// ESTADO GLOBAL
// ========================================
let state = {
    meses: 6,
    agregacao: 'fornecedor',
    filtros: {
        fornecedores: [],
        categorias: [],
        linhas3: [],
        filiais: [],
        curvas: []
    },
    ranking: {
        pagina: 1,
        porPagina: 20,
        ordenarPor: 'wmape',
        ordem: 'desc'
    }
};

let charts = {};
let filtrosData = {};

// Cores
const CORES = {
    wmape: '#3b82f6',
    bias: '#f59e0b',
    fva: '#10b981',
    meta20: '#10b981',
    zero: '#9ca3af'
};

// Faixas WMAPE
const FAIXAS_WMAPE = {
    excelente: { max: 10, cor: '#10b981', label: 'Excelente' },
    boa: { max: 20, cor: '#3b82f6', label: 'Boa' },
    aceitavel: { max: 30, cor: '#f59e0b', label: 'Aceitavel' },
    fraca: { max: 50, cor: '#f97316', label: 'Fraca' },
    muito_fraca: { max: Infinity, cor: '#ef4444', label: 'Muito Fraca' }
};

// ========================================
// INICIALIZACAO
// ========================================
document.addEventListener('DOMContentLoaded', function() {
    console.log('Inicializando Dashboard de Acuracia v1.0...');
    inicializarEventListeners();
    carregarFiltros();
    carregarDados();
});

function inicializarEventListeners() {
    document.querySelectorAll('input[name="periodo"]').forEach(radio => {
        radio.addEventListener('change', (e) => {
            state.meses = parseInt(e.target.value);
            carregarDados();
        });
    });

    document.querySelectorAll('input[name="agregacao"]').forEach(radio => {
        radio.addEventListener('change', (e) => {
            state.agregacao = e.target.value;
            state.ranking.pagina = 1;
            carregarRanking();
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
    fetch('/api/acuracia/filtros')
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

            if (data.curvas && data.curvas.length > 0) {
                MultiSelect.create('filter-curva', data.curvas.map(c => ({
                    value: c, label: `Curva ${c}`
                })), {
                    allSelectedText: 'Todas as curvas',
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
        filiais: MultiSelect.getSelected('filter-filial') || [],
        curvas: MultiSelect.getSelected('filter-curva') || []
    };
    state.ranking.pagina = 1;
    carregarDados();
}

function limparFiltros() {
    MultiSelect.selectAll('filter-fornecedor');
    MultiSelect.selectAll('filter-categoria');
    MultiSelect.selectAll('filter-linha3');
    MultiSelect.selectAll('filter-filial');
    MultiSelect.selectAll('filter-curva');

    state.filtros = {
        fornecedores: [],
        categorias: [],
        linhas3: [],
        filiais: [],
        curvas: []
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
    params.append('meses', state.meses);

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
    if (state.filtros.curvas.length > 0) {
        state.filtros.curvas.forEach(v => params.append('curva_abc', v));
    }

    return params;
}

function carregarResumo() {
    const params = buildQueryParams();
    return fetch(`/api/acuracia/resumo?${params}`)
        .then(response => response.json())
        .then(data => {
            if (data.erro) {
                console.error('Erro no resumo:', data.erro);
                return;
            }
            atualizarCardsKPI(data);
        });
}

function carregarEvolucao() {
    const params = buildQueryParams();
    params.set('meses', Math.max(state.meses, 6)); // Minimo 6 meses no grafico
    return fetch(`/api/acuracia/evolucao?${params}`)
        .then(response => response.json())
        .then(data => {
            if (data.erro) {
                console.error('Erro na evolucao:', data.erro);
                return;
            }
            atualizarGraficoEvolucao(data.evolucao || []);
        });
}

function carregarRanking() {
    const params = buildQueryParams();
    params.append('agregacao', state.agregacao);
    params.append('pagina', state.ranking.pagina);
    params.append('por_pagina', state.ranking.porPagina);
    params.append('ordenar_por', state.ranking.ordenarPor);
    params.append('ordem', state.ranking.ordem);

    return fetch(`/api/acuracia/ranking?${params}`)
        .then(response => response.json())
        .then(data => {
            if (data.erro) {
                console.error('Erro no ranking:', data.erro);
                return;
            }
            atualizarTabelaRanking(data);
        });
}

// ========================================
// ATUALIZACAO DOS CARDS
// ========================================
function atualizarCardsKPI(data) {
    // WMAPE
    const wmape = data.wmape || {};
    const wmapeVal = wmape.valor || 0;
    document.getElementById('kpi-wmape-valor').textContent = wmapeVal.toFixed(1) + '%';

    const badgeWmape = document.getElementById('kpi-wmape-badge');
    const corWmape = getCorWmape(wmapeVal);
    badgeWmape.className = `kpi-badge badge-${corWmape.badge}`;
    badgeWmape.textContent = wmape.classificacao || '-';

    const tendWmape = document.getElementById('kpi-wmape-tendencia');
    let textoWmape = wmape.periodo || '';
    if (wmape.variacao && wmape.variacao !== 0) {
        const sinal = wmape.variacao > 0 ? '+' : '';
        textoWmape += ` | ${sinal}${wmape.variacao.toFixed(1)}% vs anterior`;
    }
    tendWmape.textContent = textoWmape;
    tendWmape.className = 'kpi-tendencia';
    if (wmape.variacao && wmape.variacao !== 0) {
        // Para WMAPE: diminuir e bom
        tendWmape.classList.add(wmape.variacao <= 0 ? 'tendencia-positiva' : 'tendencia-negativa');
    }

    // BIAS
    const bias = data.bias || {};
    const biasVal = bias.valor || 0;
    const sinalBias = biasVal > 0 ? '+' : '';
    document.getElementById('kpi-bias-valor').textContent = sinalBias + biasVal.toFixed(1) + '%';

    const badgeBias = document.getElementById('kpi-bias-badge');
    const corBias = getCorBias(biasVal);
    badgeBias.className = `kpi-badge badge-${corBias.badge}`;
    const direcaoTexto = bias.direcao === 'superestimando' ? 'Superestimando'
        : bias.direcao === 'subestimando' ? 'Subestimando' : 'Equilibrado';
    badgeBias.textContent = direcaoTexto;

    const tendBias = document.getElementById('kpi-bias-tendencia');
    let textoBias = bias.periodo || '';
    if (bias.variacao && bias.variacao !== 0) {
        const sinalV = bias.variacao > 0 ? '+' : '';
        textoBias += ` | ${sinalV}${bias.variacao.toFixed(1)}% vs anterior`;
    }
    tendBias.textContent = textoBias;
    tendBias.className = 'kpi-tendencia';
    if (bias.variacao && bias.variacao !== 0) {
        // Para BIAS: diminuir valor absoluto e bom
        tendBias.classList.add(Math.abs(biasVal) < Math.abs(biasVal - bias.variacao)
            ? 'tendencia-positiva' : 'tendencia-negativa');
    }

    // FVA
    const fva = data.fva || {};
    const fvaVal = fva.valor;
    const fvaElem = document.getElementById('kpi-fva-valor');
    const badgeFva = document.getElementById('kpi-fva-badge');
    const tendFva = document.getElementById('kpi-fva-tendencia');

    if (fvaElem) {
        if (fvaVal !== null && fvaVal !== undefined) {
            const sinalFva = fvaVal > 0 ? '+' : '';
            fvaElem.textContent = sinalFva + fvaVal.toFixed(1) + '%';

            const corFva = getCorFva(fvaVal);
            if (badgeFva) {
                badgeFva.className = `kpi-badge badge-${corFva.badge}`;
                badgeFva.textContent = corFva.texto;
            }
            if (tendFva) {
                tendFva.textContent = fva.interpretacao || '';
                tendFva.className = 'kpi-tendencia';
            }
        } else {
            fvaElem.textContent = 'N/D';
            if (badgeFva) {
                badgeFva.className = 'kpi-badge badge-cinza';
                badgeFva.textContent = 'Sem dados';
            }
            if (tendFva) tendFva.textContent = 'Sem vendas do ano anterior';
        }
    }

    // Total itens badge
    document.getElementById('kpi-total-itens').textContent =
        (data.total_itens || 0) + ' itens';

    // Donut distribuicao
    atualizarDonut(data.distribuicao_wmape || {});
}

function atualizarDonut(dist) {
    if (charts.distribuicao) charts.distribuicao.destroy();

    const ctx = document.getElementById('chart-distribuicao');
    if (!ctx) return;

    const valores = [
        dist.excelente || 0,
        dist.boa || 0,
        dist.aceitavel || 0,
        dist.fraca || 0,
        dist.muito_fraca || 0
    ];

    const total = valores.reduce((a, b) => a + b, 0);
    if (total === 0) return;

    charts.distribuicao = new Chart(ctx, {
        type: 'doughnut',
        data: {
            labels: ['Excelente (<10%)', 'Boa (10-20%)', 'Aceitavel (20-30%)', 'Fraca (30-50%)', 'Muito Fraca (>50%)'],
            datasets: [{
                data: valores,
                backgroundColor: [
                    FAIXAS_WMAPE.excelente.cor,
                    FAIXAS_WMAPE.boa.cor,
                    FAIXAS_WMAPE.aceitavel.cor,
                    FAIXAS_WMAPE.fraca.cor,
                    FAIXAS_WMAPE.muito_fraca.cor
                ],
                borderWidth: 2,
                borderColor: '#fff'
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            cutout: '60%',
            plugins: {
                legend: {
                    display: true,
                    position: 'right',
                    labels: {
                        usePointStyle: true,
                        padding: 8,
                        font: { size: 10 },
                        generateLabels: function(chart) {
                            const data = chart.data;
                            return data.labels.map((label, i) => {
                                const val = data.datasets[0].data[i];
                                const pct = total > 0 ? ((val / total) * 100).toFixed(0) : 0;
                                return {
                                    text: `${label.split('(')[0].trim()} (${pct}%)`,
                                    fillStyle: data.datasets[0].backgroundColor[i],
                                    strokeStyle: '#fff',
                                    lineWidth: 1,
                                    pointStyle: 'circle',
                                    index: i
                                };
                            });
                        }
                    }
                },
                tooltip: {
                    callbacks: {
                        label: function(context) {
                            const val = context.raw;
                            const pct = total > 0 ? ((val / total) * 100).toFixed(1) : 0;
                            return ` ${val} itens (${pct}%)`;
                        }
                    }
                }
            }
        }
    });
}

// ========================================
// GRAFICO EVOLUCAO
// ========================================
function atualizarGraficoEvolucao(dados) {
    if (charts.evolucao) charts.evolucao.destroy();

    const ctx = document.getElementById('chart-evolucao');
    if (!ctx || !dados.length) return;

    const labels = dados.map(d => d.periodo_label);
    const wmapeVals = dados.map(d => d.wmape);
    const biasVals = dados.map(d => d.bias_pct);
    const fvaVals = dados.map(d => d.fva);

    charts.evolucao = new Chart(ctx, {
        type: 'line',
        data: {
            labels: labels,
            datasets: [
                {
                    label: 'WMAPE (%)',
                    data: wmapeVals,
                    borderColor: CORES.wmape,
                    backgroundColor: hexToRgba(CORES.wmape, 0.1),
                    borderWidth: 3,
                    tension: 0.4,
                    fill: true,
                    pointRadius: 4,
                    pointHoverRadius: 6,
                    yAxisID: 'y'
                },
                {
                    label: 'BIAS (%)',
                    data: biasVals,
                    borderColor: CORES.bias,
                    backgroundColor: hexToRgba(CORES.bias, 0.1),
                    borderWidth: 2,
                    tension: 0.4,
                    fill: false,
                    pointRadius: 4,
                    pointHoverRadius: 6,
                    yAxisID: 'y1'
                },
                {
                    label: 'Meta WMAPE (20%)',
                    data: dados.map(() => 20),
                    borderColor: CORES.meta20,
                    borderWidth: 2,
                    borderDash: [5, 5],
                    tension: 0,
                    fill: false,
                    pointRadius: 0,
                    yAxisID: 'y'
                },
                {
                    label: 'FVA (%)',
                    data: fvaVals,
                    borderColor: CORES.fva,
                    backgroundColor: hexToRgba(CORES.fva, 0.1),
                    borderWidth: 2,
                    tension: 0.4,
                    fill: false,
                    pointRadius: 4,
                    pointHoverRadius: 6,
                    yAxisID: 'y1'
                },
                {
                    label: 'BIAS ideal (0%)',
                    data: dados.map(() => 0),
                    borderColor: CORES.zero,
                    borderWidth: 1,
                    borderDash: [3, 3],
                    tension: 0,
                    fill: false,
                    pointRadius: 0,
                    yAxisID: 'y1'
                }
            ]
        },
        options: {
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
                    cornerRadius: 8,
                    callbacks: {
                        label: function(context) {
                            const val = context.raw;
                            if (context.dataset.label.includes('Meta') || context.dataset.label.includes('ideal')) {
                                return null;
                            }
                            if (val === null || val === undefined) return null;
                            const sinal = val > 0 && (context.dataset.label.includes('BIAS') || context.dataset.label.includes('FVA')) ? '+' : '';
                            return ` ${context.dataset.label}: ${sinal}${val.toFixed(1)}%`;
                        }
                    }
                }
            },
            scales: {
                y: {
                    type: 'linear',
                    display: true,
                    position: 'left',
                    beginAtZero: true,
                    title: {
                        display: true,
                        text: 'WMAPE (%)',
                        font: { size: 12, weight: 'bold' },
                        color: CORES.wmape
                    },
                    grid: { color: 'rgba(0, 0, 0, 0.05)' },
                    ticks: { color: CORES.wmape }
                },
                y1: {
                    type: 'linear',
                    display: true,
                    position: 'right',
                    title: {
                        display: true,
                        text: 'BIAS (%)',
                        font: { size: 12, weight: 'bold' },
                        color: CORES.bias
                    },
                    grid: { drawOnChartArea: false },
                    ticks: { color: CORES.bias }
                },
                x: {
                    grid: { display: false },
                    ticks: {
                        maxRotation: 45,
                        minRotation: 0
                    }
                }
            }
        }
    });
}

// ========================================
// TABELA DE RANKING
// ========================================
function atualizarTabelaRanking(data) {
    const tbody = document.getElementById('ranking-tbody');
    const paginacaoInfo = document.getElementById('paginacao-info');
    const thMetodo = document.getElementById('th-metodo');

    if (!tbody) return;

    // Mostrar coluna Metodo apenas para agregacao por item
    if (thMetodo) {
        thMetodo.style.display = state.agregacao === 'item' ? '' : 'none';
    }

    const numCols = state.agregacao === 'item' ? 8 : 7;

    if (!data || !data.itens || data.itens.length === 0) {
        tbody.innerHTML = `
            <tr>
                <td colspan="${numCols}" class="text-center text-muted py-4">
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

        const wmapeVal = item.wmape || 0;
        const biasVal = item.bias_pct || 0;
        const maeVal = item.mae || 0;

        const corW = getCorWmape(wmapeVal);
        const corB = getCorBias(biasVal);

        const sinalBias = biasVal > 0 ? '+' : '';

        let identificador = item.identificador || '-';
        let descExtra = '';
        if (state.agregacao === 'item' && item.descricao) {
            descExtra = `<br><small style="color: #6c757d;">${item.descricao}</small>`;
        }
        if (state.agregacao === 'item' && item.fornecedor) {
            descExtra += `<br><small style="color: #9ca3af;">${item.fornecedor}</small>`;
        }

        const totalRealizado = item.total_realizado || 0;
        const totalFormatado = totalRealizado >= 1000
            ? (totalRealizado / 1000).toFixed(1) + 'k'
            : totalRealizado.toFixed(0);

        const colMetodo = state.agregacao === 'item'
            ? `<td><small>${item.metodo_predominante || '-'}</small></td>`
            : '';

        // FVA
        const fvaItemVal = item.fva;
        let fvaCell = '';
        if (fvaItemVal !== null && fvaItemVal !== undefined) {
            const corF = getCorFva(fvaItemVal);
            const sinalF = fvaItemVal > 0 ? '+' : '';
            fvaCell = `<td><span class="badge badge-${corF.badge}">${sinalF}${fvaItemVal.toFixed(1)}%</span></td>`;
        } else {
            fvaCell = '<td><span class="badge badge-cinza">N/D</span></td>';
        }

        tr.innerHTML = `
            <td class="fw-medium">${identificador}${descExtra}</td>
            <td><span class="badge badge-${corW.badge}">${wmapeVal.toFixed(1)}%</span></td>
            <td><span class="badge badge-${corB.badge}">${sinalBias}${biasVal.toFixed(1)}%</span></td>
            <td>${maeVal.toFixed(1)}</td>
            ${fvaCell}
            <td>${item.total_itens || '-'}</td>
            <td>${totalFormatado}</td>
            ${colMetodo}
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
// FUNCOES DE COR
// ========================================
function getCorWmape(valor) {
    if (valor === null || valor === undefined) return { badge: 'cinza', texto: '-' };
    if (valor < 10) return { badge: 'verde', texto: 'Excelente' };
    if (valor < 20) return { badge: 'azul', texto: 'Boa' };
    if (valor < 30) return { badge: 'amarelo', texto: 'Aceitavel' };
    if (valor < 50) return { badge: 'laranja', texto: 'Fraca' };
    return { badge: 'vermelho', texto: 'Muito Fraca' };
}

function getCorBias(valor) {
    if (valor === null || valor === undefined) return { badge: 'cinza', texto: '-' };
    const abs = Math.abs(valor);
    if (abs < 5) return { badge: 'verde', texto: 'OK' };
    if (abs < 10) return { badge: 'amarelo', texto: 'Atencao' };
    return { badge: 'vermelho', texto: 'Critico' };
}

function getCorFva(valor) {
    if (valor === null || valor === undefined) return { badge: 'cinza', texto: 'N/D' };
    if (valor > 10) return { badge: 'verde', texto: 'Agrega valor' };
    if (valor >= 0) return { badge: 'amarelo', texto: 'Neutro' };
    return { badge: 'vermelho', texto: 'Abaixo do naive' };
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
