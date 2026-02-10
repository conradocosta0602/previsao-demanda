// KPIs Dashboard - JavaScript Reformulado
// Controla filtros, gráficos e visualizações
// Versão 2.0 - Fevereiro 2026

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

let charts = {};  // Armazena instâncias dos gráficos
let filtrosData = {};  // Dados dos filtros carregados

// Cores padrão para os gráficos
const CORES = {
    ruptura: '#ef4444',
    cobertura: '#10b981',
    wmape: '#3b82f6',
    bias: '#f59e0b',
    melhorHistorico: '#9ca3af'
};

// Faixas de alerta
const FAIXAS = {
    ruptura: {
        verde: 5,      // < 5%
        amarelo: 10    // 5-10%, > 10% = vermelho
    },
    wmape: {
        azul: 20,      // < 20%
        verde: 50      // 20-50%, >= 50% = vermelho
    },
    cobertura: {
        meta: 30       // Meta de 30 dias de cobertura
    }
};

// ========================================
// INICIALIZAÇÃO
// ========================================
document.addEventListener('DOMContentLoaded', function() {
    console.log('Inicializando Dashboard de KPIs v2.0...');

    // Inicializar event listeners
    inicializarEventListeners();

    // Carregar filtros do servidor
    carregarFiltros();

    // Carregar dados iniciais
    carregarDados();
});

function inicializarEventListeners() {
    // Visão temporal
    document.querySelectorAll('input[name="visao-temporal"]').forEach(radio => {
        radio.addEventListener('change', (e) => {
            state.visaoTemporal = e.target.value;
            carregarDados();
        });
    });

    // Agregação
    document.querySelectorAll('input[name="agregacao"]').forEach(radio => {
        radio.addEventListener('change', (e) => {
            state.agregacao = e.target.value;
            atualizarVisibilidadeGraficos();
            carregarDados();
        });
    });

    // Ordenação da tabela
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

            // Criar multi-select para Fornecedor
            if (data.fornecedores && data.fornecedores.length > 0) {
                const fornecedoresOptions = data.fornecedores.map(f => ({
                    value: f,
                    label: f
                }));
                MultiSelect.create('filter-fornecedor', fornecedoresOptions, {
                    allSelectedText: 'Todos os fornecedores',
                    selectAllByDefault: true,
                    onchange: () => {}
                });
            }

            // Criar multi-select para Categoria (Linha1)
            if (data.categorias && data.categorias.length > 0) {
                const categoriasOptions = data.categorias.map(c => ({
                    value: c,
                    label: c
                }));
                MultiSelect.create('filter-categoria', categoriasOptions, {
                    allSelectedText: 'Todas as categorias',
                    selectAllByDefault: true,
                    onchange: () => atualizarLinhas3()
                });
            }

            // Criar multi-select para Linha3 (dependente de Categoria)
            atualizarLinhas3();

            // Criar multi-select para Filial
            if (data.filiais && data.filiais.length > 0) {
                const filiaisOptions = data.filiais.map(f => ({
                    value: f.codigo.toString(),
                    label: `${f.codigo} - ${f.nome}`
                }));
                MultiSelect.create('filter-filial', filiaisOptions, {
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
    // Pegar categorias selecionadas
    const categoriasSelecionadas = MultiSelect.getSelected('filter-categoria') || [];

    // Filtrar linhas3 pelas categorias selecionadas
    let linhas3Filtradas = [];

    if (filtrosData.linhas3_por_categoria) {
        if (categoriasSelecionadas.length === 0) {
            // Se nenhuma categoria selecionada, mostrar todas as linhas3
            Object.values(filtrosData.linhas3_por_categoria).forEach(linhas => {
                linhas3Filtradas = linhas3Filtradas.concat(linhas);
            });
        } else {
            // Filtrar pelas categorias selecionadas
            categoriasSelecionadas.forEach(cat => {
                if (filtrosData.linhas3_por_categoria[cat]) {
                    linhas3Filtradas = linhas3Filtradas.concat(filtrosData.linhas3_por_categoria[cat]);
                }
            });
        }
    }

    // Remover duplicatas
    linhas3Filtradas = [...new Set(linhas3Filtradas)];

    // Recriar multi-select de Linha3
    const linhas3Options = linhas3Filtradas.map(l => ({
        value: l.codigo,
        label: `${l.codigo} - ${l.descricao}`
    }));

    MultiSelect.create('filter-linha3', linhas3Options, {
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

    state.ranking.pagina = 1;  // Reset paginação

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

    // Carregar resumo, evolução e ranking em paralelo
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

    if (state.filtros.fornecedores.length > 0) {
        params.append('fornecedores', JSON.stringify(state.filtros.fornecedores));
    }
    if (state.filtros.categorias.length > 0) {
        params.append('categorias', JSON.stringify(state.filtros.categorias));
    }
    if (state.filtros.linhas3.length > 0) {
        params.append('linhas3', JSON.stringify(state.filtros.linhas3));
    }
    if (state.filtros.filiais.length > 0) {
        params.append('filiais', JSON.stringify(state.filtros.filiais));
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
// ATUALIZAÇÃO DOS CARDS KPI
// ========================================
function atualizarCardsKPI(data) {
    // Ruptura
    atualizarCardKPI('ruptura', data.ruptura, '%', getCorRuptura);

    // Cobertura
    atualizarCardKPI('cobertura', data.cobertura, ' dias', getCorCobertura);

    // WMAPE
    atualizarCardKPI('wmape', data.wmape, '%', getCorWMAPE);

    // BIAS
    atualizarCardKPI('bias', data.bias, '%', getCorBIAS);
}

function atualizarCardKPI(id, dados, sufixo, getCorFunc) {
    if (!dados) return;

    const valorEl = document.getElementById(`kpi-${id}-valor`);
    const tendenciaEl = document.getElementById(`kpi-${id}-tendencia`);
    const badgeEl = document.getElementById(`kpi-${id}-badge`);

    if (valorEl) {
        const valorFormatado = dados.valor !== null && dados.valor !== undefined
            ? dados.valor.toFixed(1) + sufixo
            : '-';
        valorEl.textContent = valorFormatado;
    }

    if (tendenciaEl) {
        // Mostrar periodo de referencia e variacao
        let textoTendencia = '';

        if (dados.periodo) {
            textoTendencia = dados.periodo;
        }

        if (dados.variacao !== undefined && dados.variacao !== 0) {
            const variacao = dados.variacao;
            const sinal = variacao > 0 ? '+' : '';
            textoTendencia += ` | ${sinal}${variacao.toFixed(1)}% vs anterior`;
        }

        tendenciaEl.textContent = textoTendencia;
        tendenciaEl.className = 'kpi-tendencia';

        // Para ruptura e WMAPE, diminuir é bom
        // Para cobertura, aumentar é bom
        if (dados.variacao !== undefined && dados.variacao !== 0) {
            if (id === 'ruptura' || id === 'wmape') {
                tendenciaEl.classList.add(dados.variacao <= 0 ? 'tendencia-positiva' : 'tendencia-negativa');
            } else if (id === 'cobertura') {
                tendenciaEl.classList.add(dados.variacao >= 0 ? 'tendencia-positiva' : 'tendencia-negativa');
            } else {
                // BIAS - quanto mais próximo de 0, melhor
                tendenciaEl.classList.add(Math.abs(dados.variacao) <= 5 ? 'tendencia-positiva' : 'tendencia-negativa');
            }
        }
    }

    if (badgeEl && getCorFunc) {
        const cor = getCorFunc(dados.valor);
        badgeEl.className = `kpi-badge badge-${cor}`;
        badgeEl.textContent = getTextoStatus(cor);
    }
}

function getCorRuptura(valor) {
    if (valor === null || valor === undefined) return 'cinza';
    if (valor < FAIXAS.ruptura.verde) return 'verde';
    if (valor <= FAIXAS.ruptura.amarelo) return 'amarelo';
    return 'vermelho';
}

function getCorCobertura(valor) {
    if (valor === null || valor === undefined) return 'cinza';
    if (valor >= FAIXAS.cobertura.meta) return 'verde';
    if (valor >= FAIXAS.cobertura.meta * 0.7) return 'amarelo';
    return 'vermelho';
}

function getCorWMAPE(valor) {
    if (valor === null || valor === undefined) return 'cinza';
    if (valor < FAIXAS.wmape.azul) return 'azul';
    if (valor < FAIXAS.wmape.verde) return 'verde';
    return 'vermelho';
}

function getCorBIAS(valor) {
    if (valor === null || valor === undefined) return 'cinza';
    const absValor = Math.abs(valor);
    if (absValor < 10) return 'verde';
    if (absValor < 25) return 'amarelo';
    return 'vermelho';
}

function getTextoStatus(cor) {
    const textos = {
        'verde': 'Bom',
        'amarelo': 'Atenção',
        'vermelho': 'Crítico',
        'azul': 'Excelente',
        'cinza': '-'
    };
    return textos[cor] || '-';
}

// ========================================
// ATUALIZAÇÃO DOS GRÁFICOS
// ========================================
function atualizarVisibilidadeGraficos() {
    const containerGraficos = document.getElementById('graficos-container');
    const containerItem = document.getElementById('graficos-item-container');

    if (state.agregacao === 'item') {
        // Para nível item, mostrar gráficos também (como solicitado)
        if (containerGraficos) containerGraficos.style.display = 'grid';
        if (containerItem) containerItem.style.display = 'block';
    } else {
        if (containerGraficos) containerGraficos.style.display = 'grid';
        if (containerItem) containerItem.style.display = 'none';
    }
}

function atualizarGraficos(data) {
    if (!data) return;

    // Destruir gráficos existentes
    Object.keys(charts).forEach(key => {
        if (charts[key]) {
            charts[key].destroy();
        }
    });
    charts = {};

    // Criar novos gráficos
    criarGraficoRuptura(data.ruptura || []);
    criarGraficoCobertura(data.cobertura || []);
    criarGraficoWMAPE(data.wmape || []);
    criarGraficoBIAS(data.bias || []);
}

function criarGraficoRuptura(dados) {
    const ctx = document.getElementById('chart-ruptura');
    if (!ctx || !dados.length) return;

    const labels = dados.map(d => d.periodo);
    const valores = dados.map(d => d.valor);
    const melhorHistorico = dados.map(d => d.melhor_historico);

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
                    label: 'Melhor Histórico',
                    data: melhorHistorico,
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
    const melhorHistorico = dados.map(d => d.melhor_historico);

    // Adicionar linha de meta
    const meta = dados.map(() => FAIXAS.cobertura.meta);

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
                    label: 'Meta (30 dias)',
                    data: meta,
                    borderColor: '#6366f1',
                    borderWidth: 2,
                    borderDash: [10, 5],
                    tension: 0,
                    fill: false,
                    pointRadius: 0
                },
                {
                    label: 'Melhor Histórico',
                    data: melhorHistorico,
                    borderColor: CORES.melhorHistorico,
                    borderWidth: 2,
                    borderDash: [5, 5],
                    tension: 0.4,
                    fill: false,
                    pointRadius: 0
                }
            ]
        },
        options: getOptionsGrafico('Cobertura (dias)', true)
    });
}

function criarGraficoWMAPE(dados) {
    const ctx = document.getElementById('chart-wmape');
    if (!ctx || !dados.length) return;

    const labels = dados.map(d => d.periodo);
    const valores = dados.map(d => d.valor);
    const melhorHistorico = dados.map(d => d.melhor_historico);

    charts['wmape'] = new Chart(ctx, {
        type: 'line',
        data: {
            labels: labels,
            datasets: [
                {
                    label: 'WMAPE (%)',
                    data: valores,
                    borderColor: CORES.wmape,
                    backgroundColor: hexToRgba(CORES.wmape, 0.1),
                    borderWidth: 3,
                    tension: 0.4,
                    fill: true,
                    pointRadius: 4,
                    pointHoverRadius: 6
                },
                {
                    label: 'Melhor Histórico',
                    data: melhorHistorico,
                    borderColor: CORES.melhorHistorico,
                    borderWidth: 2,
                    borderDash: [5, 5],
                    tension: 0.4,
                    fill: false,
                    pointRadius: 0
                }
            ]
        },
        options: getOptionsGrafico('WMAPE (%)', true)
    });
}

function criarGraficoBIAS(dados) {
    const ctx = document.getElementById('chart-bias');
    if (!ctx || !dados.length) return;

    const labels = dados.map(d => d.periodo);
    const valores = dados.map(d => d.valor);

    // Linha de referência no zero
    const zeroLine = dados.map(() => 0);

    charts['bias'] = new Chart(ctx, {
        type: 'line',
        data: {
            labels: labels,
            datasets: [
                {
                    label: 'BIAS (%)',
                    data: valores,
                    borderColor: CORES.bias,
                    backgroundColor: hexToRgba(CORES.bias, 0.1),
                    borderWidth: 3,
                    tension: 0.4,
                    fill: true,
                    pointRadius: 4,
                    pointHoverRadius: 6
                },
                {
                    label: 'Referência (0)',
                    data: zeroLine,
                    borderColor: CORES.melhorHistorico,
                    borderWidth: 2,
                    borderDash: [5, 5],
                    tension: 0,
                    fill: false,
                    pointRadius: 0
                }
            ]
        },
        options: getOptionsGrafico('BIAS (%)', false)
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
                    font: {
                        size: 11
                    }
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
                grid: {
                    color: 'rgba(0, 0, 0, 0.05)'
                }
            },
            x: {
                grid: {
                    display: false
                },
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
                <td colspan="8" class="text-center text-muted py-4">
                    Nenhum dado encontrado para os filtros selecionados
                </td>
            </tr>
        `;
        if (paginacaoInfo) paginacaoInfo.textContent = '';
        return;
    }

    tbody.innerHTML = '';

    data.itens.forEach((item, index) => {
        const tr = document.createElement('tr');

        // Determinar status baseado nos valores
        const statusRuptura = getCorRuptura(item.ruptura);
        const statusWMAPE = getCorWMAPE(item.wmape);

        tr.innerHTML = `
            <td class="fw-medium">${item.identificador || '-'}</td>
            <td>${item.descricao || '-'}</td>
            <td>
                <span class="badge badge-${statusRuptura}">${item.ruptura !== null ? item.ruptura.toFixed(1) + '%' : '-'}</span>
            </td>
            <td>${item.cobertura !== null ? item.cobertura.toFixed(1) : '-'}</td>
            <td>
                <span class="badge badge-${statusWMAPE}">${item.wmape !== null ? item.wmape.toFixed(1) + '%' : '-'}</span>
            </td>
            <td>${item.bias !== null ? (item.bias > 0 ? '+' : '') + item.bias.toFixed(1) + '%' : '-'}</td>
            <td>${item.total_skus || '-'}</td>
            <td>${item.skus_ruptura || '-'}</td>
        `;

        tbody.appendChild(tr);
    });

    // Atualizar informações de paginação
    if (paginacaoInfo) {
        const inicio = (data.pagina - 1) * data.por_pagina + 1;
        const fim = Math.min(data.pagina * data.por_pagina, data.total);
        paginacaoInfo.textContent = `Mostrando ${inicio}-${fim} de ${data.total}`;
    }

    // Atualizar botões de paginação
    atualizarBotoesPaginacao(data);
}

function atualizarBotoesPaginacao(data) {
    const btnAnterior = document.getElementById('btn-pagina-anterior');
    const btnProxima = document.getElementById('btn-pagina-proxima');

    if (btnAnterior) {
        btnAnterior.disabled = data.pagina <= 1;
    }

    if (btnProxima) {
        btnProxima.disabled = data.pagina >= data.total_paginas;
    }
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
                icone.textContent = state.ranking.ordem === 'asc' ? '↑' : '↓';
                icone.style.opacity = '1';
            } else {
                icone.textContent = '↕';
                icone.style.opacity = '0.3';
            }
        }
    });
}

// ========================================
// UTILITÁRIOS
// ========================================
function hexToRgba(hex, alpha) {
    const r = parseInt(hex.slice(1, 3), 16);
    const g = parseInt(hex.slice(3, 5), 16);
    const b = parseInt(hex.slice(5, 7), 16);
    return `rgba(${r}, ${g}, ${b}, ${alpha})`;
}

function mostrarLoading(show) {
    const overlay = document.getElementById('loading-overlay');
    if (overlay) {
        overlay.style.display = show ? 'flex' : 'none';
    }
}

function formatarNumero(valor, decimais = 1) {
    if (valor === null || valor === undefined) return '-';
    return valor.toLocaleString('pt-BR', {
        minimumFractionDigits: decimais,
        maximumFractionDigits: decimais
    });
}

// ========================================
// EXPORTAÇÃO
// ========================================
function exportarDados(formato) {
    const params = buildQueryParams();
    params.append('formato', formato);

    window.location.href = `/api/kpis/exportar?${params}`;
}

// Expor funções globalmente para uso no HTML
window.aplicarFiltros = aplicarFiltros;
window.limparFiltros = limparFiltros;
window.paginaAnterior = paginaAnterior;
window.proximaPagina = proximaPagina;
window.exportarDados = exportarDados;
