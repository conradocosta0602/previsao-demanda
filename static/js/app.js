// Sistema de Previsão de Demanda - JavaScript

// =====================================================
// FUNÇÃO AUXILIAR PARA CORRIGIR PARSING DE DATAS
// =====================================================
// JavaScript interpreta "YYYY-MM-DD" como UTC midnight,
// o que em fusos horários negativos (ex: Brasil GMT-3)
// mostra o dia anterior. Esta função corrige isso.
// Também suporta formato semanal YYYY-SWW (ex: 2026-S05)
function parseLocalDate(dateStr) {
    if (!dateStr) return null;
    // Se já é um objeto Date, retornar
    if (dateStr instanceof Date) return dateStr;

    // Verificar se é formato semanal YYYY-SWW (ex: 2026-S05)
    const semanalMatch = dateStr.match(/^(\d{4})-S(\d{2})$/);
    if (semanalMatch) {
        const ano = parseInt(semanalMatch[1]);
        const semana = parseInt(semanalMatch[2]);
        // Calcular a data da segunda-feira da semana ISO
        // Fórmula: encontrar 4 de janeiro (sempre na semana 1) e ajustar
        const jan4 = new Date(ano, 0, 4);
        const diaSemanaJan4 = jan4.getDay() || 7; // Domingo = 7
        // Segunda-feira da semana 1
        const seg1 = new Date(jan4);
        seg1.setDate(jan4.getDate() - diaSemanaJan4 + 1);
        // Segunda-feira da semana desejada
        const resultado = new Date(seg1);
        resultado.setDate(seg1.getDate() + (semana - 1) * 7);
        return resultado;
    }

    // Parsear manualmente formato YYYY-MM-DD para evitar problema de timezone
    const parts = dateStr.split('-');
    if (parts.length === 3) {
        // new Date(year, monthIndex, day) usa timezone LOCAL
        return new Date(parseInt(parts[0]), parseInt(parts[1]) - 1, parseInt(parts[2]));
    }
    // Fallback: adicionar T00:00:00 para forçar interpretação local
    return new Date(dateStr + 'T00:00:00');
}

// Upload de arquivo removido - agora apenas consulta ao banco de dados

function mostrarResultados(data) {
    // Esconder progresso
    document.getElementById('progress').style.display = 'none';

    // Mostrar resultados
    document.getElementById('results').style.display = 'block';

    // Preencher resumo - Layout executivo
    const resumo = data.resumo;

    // Calcular WMAPE e BIAS médios das previsões
    // IMPORTANTE: Exclui WMAPEs = 999.9 (produtos muito esparsos sem dados suficientes)
    let wmapeMedia = 0;
    let biasMedia = 0;
    let countMetrics = 0;
    let countBias = 0;

    if (data.grafico_data && data.grafico_data.previsoes_lojas) {
        data.grafico_data.previsoes_lojas.forEach(p => {
            // Incluir apenas WMAPEs válidos (< 999.9)
            // 999.9 indica produto muito esparso, sem períodos suficientes para cálculo
            if (p.WMAPE !== null && p.WMAPE !== undefined && p.WMAPE < 999.9) {
                wmapeMedia += p.WMAPE;
                countMetrics++;
            }
            if (p.BIAS !== null && p.BIAS !== undefined) {
                biasMedia += p.BIAS;
                countBias++;
            }
        });
        if (countMetrics > 0) {
            wmapeMedia = (wmapeMedia / countMetrics).toFixed(1);
        } else {
            wmapeMedia = 'N/A';  // Nenhum WMAPE calculável
        }
        if (countBias > 0) {
            biasMedia = (biasMedia / countBias).toFixed(1);
        } else {
            biasMedia = 'N/A';
        }
    }

    // Função para determinar cor do WMAPE baseado nos critérios
    function getWmapeColor(wmape) {
        if (wmape === 'N/A') return '#6c757d';  // Cinza - Não aplicável
        const value = parseFloat(wmape);
        if (isNaN(value)) return '#6c757d';
        if (value < 10) return '#059669';  // Verde - Excelente
        if (value <= 20) return '#3b82f6'; // Azul - Bom
        if (value <= 30) return '#f59e0b'; // Laranja - Aceitável
        if (value <= 50) return '#dc2626'; // Vermelho - Fraca
        return '#991b1b';                  // Vermelho escuro - Muito Fraca
    }

    // Função para determinar cor do BIAS baseado nos critérios
    function getBiasColor(bias) {
        if (bias === 'N/A') return '#6c757d';  // Cinza - Não aplicável
        const value = Math.abs(parseFloat(bias));
        if (isNaN(value)) return '#6c757d';
        if (value <= 20) return '#059669';  // Verde - Normal
        if (value <= 50) return '#3b82f6';  // Azul - Atenção
        if (value <= 100) return '#f59e0b'; // Amarelo - Alerta
        return '#dc2626';                   // Vermelho - Crítico
    }

    const wmapeColor = getWmapeColor(wmapeMedia);
    const biasColor = getBiasColor(biasMedia);

    document.getElementById('resumo').innerHTML = `
        <div class="resumo-card-compact">
            <h4>SKUs</h4>
            <p class="big-number-compact">${resumo.total_skus}</p>
        </div>
        <div class="resumo-card-compact">
            <h4>Meses Previsão</h4>
            <p class="big-number-compact">${resumo.meses_previsao}</p>
        </div>
        <div class="resumo-card-compact">
            <h4>WMAPE Médio</h4>
            <p class="big-number-compact" style="color: ${wmapeColor};">${wmapeMedia === 'N/A' ? wmapeMedia : wmapeMedia + '%'}</p>
            <p style="font-size: 0.7em; color: #666; margin-top: 4px;">Acurácia${wmapeMedia !== 'N/A' ? '' : ' (SKUs válidos)'}</p>
        </div>
        <div class="resumo-card-compact">
            <h4>BIAS Médio</h4>
            <p class="big-number-compact" style="color: ${biasColor};">${biasMedia === 'N/A' ? biasMedia : (biasMedia > 0 ? '+' : '') + biasMedia + '%'}</p>
            <p style="font-size: 0.7em; color: #666; margin-top: 4px;">Tendência</p>
        </div>
    `;

    // Mostrar alertas
    const alertasContainer = document.getElementById('alertas');
    if (data.alertas && data.alertas.length > 0) {
        const alertasHtml = data.alertas.map(a => {
            const tipo = a.tipo || 'info';
            const mensagem = a.mensagem || a;
            return `<div class="alerta ${tipo}">${mensagem}</div>`;
        }).join('');
        alertasContainer.innerHTML = alertasHtml;
    } else {
        alertasContainer.innerHTML = '<div class="alerta info">Processamento concluido sem alertas.</div>';
    }

    // Configurar download
    document.getElementById('downloadBtn').href = `/download/${data.arquivo_saida}`;

    // Configurar dados e tabelas
    if (data.grafico_data) {
        configurarGraficoYoY(data.grafico_data);  // Gráfico de comparação YoY mensal
        exibirTabelaFornecedorItem(data.grafico_data, data.smart_alerts);  // Tabela fornecedor/item
    }
}

function mostrarErro(mensagem) {
    document.getElementById('progress').style.display = 'none';
    document.getElementById('results').style.display = 'none';
    document.getElementById('error').style.display = 'block';
    document.getElementById('errorMessage').textContent = mensagem;
}

function formatNumber(num) {
    if (num === undefined || num === null) return '0';
    return Math.round(num).toLocaleString('pt-BR');
}

// ===== GRÁFICO DE DEMANDA =====
let demandaChart = null;
let graficoDados = null;

function configurarGrafico(dados) {
    graficoDados = dados;

    // Preencher filtros
    const filtroLoja = document.getElementById('filtroLoja');
    const filtroSKU = document.getElementById('filtroSKU');

    filtroLoja.innerHTML = dados.lojas.map(l => `<option value="${l}">${l}</option>`).join('');
    filtroSKU.innerHTML = dados.skus.map(s => `<option value="${s}">${s}</option>`).join('');

    // Adicionar event listeners
    document.getElementById('tipoVisao').addEventListener('change', atualizarGrafico);
    document.getElementById('filtroLoja').addEventListener('change', atualizarGrafico);
    document.getElementById('filtroSKU').addEventListener('change', atualizarGrafico);

    // Mostrar/esconder filtros baseado no tipo de visão
    document.getElementById('tipoVisao').addEventListener('change', (e) => {
        const tipo = e.target.value;
        document.getElementById('filtroLoja').style.display = tipo === 'loja' ? 'inline-block' : 'none';
        document.getElementById('filtroSKU').style.display = tipo === 'sku' ? 'inline-block' : 'none';
    });

    // Renderizar gráfico inicial
    atualizarGrafico();
}

function atualizarGrafico() {
    const tipoVisao = document.getElementById('tipoVisao').value;
    const lojaFiltro = document.getElementById('filtroLoja').value;
    const skuFiltro = document.getElementById('filtroSKU').value;

    let dadosHistoricos = [];
    let dadosPrevisao = [];

    if (tipoVisao === 'agregada') {
        // Visão total agregada
        dadosHistoricos = graficoDados.historico_total;

        // Agregar previsões
        const previsoesAgregadas = {};
        graficoDados.previsoes_lojas.forEach(p => {
            const mes = p.Mes_Previsao;
            if (!previsoesAgregadas[mes]) {
                previsoesAgregadas[mes] = 0;
            }
            previsoesAgregadas[mes] += p.Previsao;
        });

        dadosPrevisao = Object.keys(previsoesAgregadas).sort().map(mes => ({
            Mes: mes,
            Vendas_Corrigidas: previsoesAgregadas[mes]
        }));

    } else if (tipoVisao === 'loja') {
        // Visão por loja (agregado todos SKUs da loja)
        dadosHistoricos = graficoDados.historico_lojas
            .filter(h => h.Loja === lojaFiltro)
            .reduce((acc, item) => {
                const mes = item.Mes;
                const idx = acc.findIndex(a => a.Mes === mes);
                if (idx >= 0) {
                    acc[idx].Vendas_Corrigidas += item.Vendas_Corrigidas;
                } else {
                    acc.push({ Mes: mes, Vendas_Corrigidas: item.Vendas_Corrigidas });
                }
                return acc;
            }, []);

        // Agregar previsões da loja
        const previsoesLoja = {};
        graficoDados.previsoes_lojas
            .filter(p => p.Loja === lojaFiltro)
            .forEach(p => {
                const mes = p.Mes_Previsao;
                if (!previsoesLoja[mes]) {
                    previsoesLoja[mes] = 0;
                }
                previsoesLoja[mes] += p.Previsao;
            });

        dadosPrevisao = Object.keys(previsoesLoja).sort().map(mes => ({
            Mes: mes,
            Vendas_Corrigidas: previsoesLoja[mes]
        }));

    } else if (tipoVisao === 'sku') {
        // Visão por SKU (agregado todas lojas)
        dadosHistoricos = graficoDados.historico_sku
            .filter(h => h.SKU === skuFiltro)
            .reduce((acc, item) => {
                const mes = item.Mes;
                const idx = acc.findIndex(a => a.Mes === mes);
                if (idx >= 0) {
                    acc[idx].Vendas_Corrigidas += item.Vendas_Corrigidas;
                } else {
                    acc.push({ Mes: mes, Vendas_Corrigidas: item.Vendas_Corrigidas });
                }
                return acc;
            }, []);

        // Agregar previsões do SKU
        const previsoesSKU = {};
        graficoDados.previsoes_lojas
            .filter(p => p.SKU === skuFiltro)
            .forEach(p => {
                const mes = p.Mes_Previsao;
                if (!previsoesSKU[mes]) {
                    previsoesSKU[mes] = 0;
                }
                previsoesSKU[mes] += p.Previsao;
            });

        dadosPrevisao = Object.keys(previsoesSKU).sort().map(mes => ({
            Mes: mes,
            Vendas_Corrigidas: previsoesSKU[mes]
        }));
    }

    // Ordenar dados históricos
    dadosHistoricos.sort((a, b) => a.Mes.localeCompare(b.Mes));

    // Criar labels (meses)
    const mesesHistoricos = dadosHistoricos.map(d => d.Mes);
    const mesesPrevisao = dadosPrevisao.map(d => d.Mes);
    const todosOsMeses = [...mesesHistoricos, ...mesesPrevisao];

    // Criar datasets - conectar histórico com previsão
    const valoresHistoricos = dadosHistoricos.map(d => d.Vendas_Corrigidas);

    // Para previsão: repetir último valor histórico no início para conectar as linhas
    const ultimoValorHistorico = valoresHistoricos[valoresHistoricos.length - 1];
    const valoresPrevisao = new Array(mesesHistoricos.length - 1).fill(null)
        .concat([ultimoValorHistorico])  // Conecta com o último ponto histórico
        .concat(dadosPrevisao.map(d => d.Vendas_Corrigidas));

    renderizarGrafico(todosOsMeses, valoresHistoricos, valoresPrevisao, tipoVisao, lojaFiltro, skuFiltro);
}

function renderizarGrafico(labels, historico, previsao, tipo, loja, sku) {
    const ctx = document.getElementById('demandaChart').getContext('2d');

    // Destruir gráfico anterior se existir
    if (demandaChart) {
        demandaChart.destroy();
    }

    // Título do gráfico
    let titulo = 'Demanda Total Agregada';
    if (tipo === 'loja') {
        titulo = `Demanda da Loja ${loja}`;
    } else if (tipo === 'sku') {
        titulo = `Demanda do SKU ${sku}`;
    }

    // Calcular escala dinâmica do eixo Y
    const todosValores = [
        ...historico.filter(v => v !== null && v !== undefined),
        ...previsao.filter(v => v !== null && v !== undefined)
    ];

    const valorMinimo = Math.min(...todosValores);
    const valorMaximo = Math.max(...todosValores);
    const amplitude = valorMaximo - valorMinimo;

    // Adicionar margem de 10% acima e abaixo para melhor visualização
    const margemInferior = valorMinimo - (amplitude * 0.10);
    const margemSuperior = valorMaximo + (amplitude * 0.10);

    // Garantir que não fique negativo se todos valores forem positivos
    const yMin = Math.max(0, margemInferior);
    const yMax = margemSuperior;

    demandaChart = new Chart(ctx, {
        type: 'line',
        data: {
            labels: labels,
            datasets: [
                {
                    label: 'Histórico',
                    data: historico,
                    borderColor: '#11998e',
                    backgroundColor: 'rgba(17, 153, 142, 0.1)',
                    borderWidth: 3,
                    tension: 0.4,
                    fill: true,
                    pointRadius: 4,
                    pointHoverRadius: 6
                },
                {
                    label: 'Previsão',
                    data: previsao,
                    borderColor: '#38ef7d',
                    backgroundColor: 'rgba(56, 239, 125, 0.1)',
                    borderWidth: 3,
                    borderDash: [10, 5],
                    tension: 0.4,
                    fill: true,
                    pointRadius: 4,
                    pointHoverRadius: 6
                }
            ]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                title: {
                    display: true,
                    text: titulo,
                    font: {
                        size: 16,
                        weight: 'bold'
                    },
                    color: '#333'
                },
                legend: {
                    display: true,
                    position: 'top',
                    labels: {
                        usePointStyle: true,
                        padding: 15,
                        font: {
                            size: 13
                        }
                    }
                },
                tooltip: {
                    mode: 'index',
                    intersect: false,
                    callbacks: {
                        label: function(context) {
                            let label = context.dataset.label || '';
                            if (label) {
                                label += ': ';
                            }
                            if (context.parsed.y !== null) {
                                label += formatNumber(context.parsed.y) + ' unidades';
                            }
                            return label;
                        }
                    }
                }
            },
            scales: {
                x: {
                    grid: {
                        display: false
                    },
                    ticks: {
                        maxRotation: 45,
                        minRotation: 45
                    }
                },
                y: {
                    min: yMin,
                    max: yMax,
                    grid: {
                        color: 'rgba(0, 0, 0, 0.05)'
                    },
                    ticks: {
                        callback: function(value) {
                            return formatNumber(value);
                        }
                    }
                }
            },
            interaction: {
                mode: 'nearest',
                axis: 'x',
                intersect: false
            }
        }
    });
}

// ===== GRÁFICO DE COMPARAÇÃO YoY =====
let yoyChart = null;

function configurarGraficoYoY(dados) {
    if (!dados.comparacao_yoy || dados.comparacao_yoy.length === 0) {
        return;
    }

    const ctx = document.getElementById('yoyChart').getContext('2d');

    // Destruir gráfico anterior se existir
    if (yoyChart) {
        yoyChart.destroy();
    }

    // Preparar dados
    const labels = dados.comparacao_yoy.map(d => d.mes_nome);
    const demandaAnoAnterior = dados.comparacao_yoy.map(d => d.demanda_ano_anterior || 0);
    const previsaoAtual = dados.comparacao_yoy.map(d => d.previsao_atual || 0);
    const variacoes = dados.comparacao_yoy.map(d => d.variacao_percentual);

    // Calcular escala dinâmica do eixo Y
    const todosValores = [...demandaAnoAnterior, ...previsaoAtual];
    const valorMinimo = Math.min(...todosValores);
    const valorMaximo = Math.max(...todosValores);
    const amplitude = valorMaximo - valorMinimo;

    // Adicionar margem de 10% acima e abaixo para melhor visualização
    const margemInferior = valorMinimo - (amplitude * 0.10);
    const margemSuperior = valorMaximo + (amplitude * 0.10);

    // Garantir que não fique negativo se todos valores forem positivos
    const yMin = Math.max(0, margemInferior);
    const yMax = margemSuperior;

    yoyChart = new Chart(ctx, {
        type: 'bar',
        data: {
            labels: labels,
            datasets: [
                {
                    label: 'Mesmo Mês Ano Anterior',
                    data: demandaAnoAnterior,
                    backgroundColor: 'rgba(17, 153, 142, 0.7)',
                    borderColor: '#11998e',
                    borderWidth: 2
                },
                {
                    label: 'Previsão Atual',
                    data: previsaoAtual,
                    backgroundColor: 'rgba(56, 239, 125, 0.7)',
                    borderColor: '#38ef7d',
                    borderWidth: 2
                }
            ]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                title: {
                    display: true,
                    text: 'Comparação: Previsão vs Mesmo Período Ano Anterior',
                    font: {
                        size: 14,
                        weight: 'bold'
                    },
                    color: '#333'
                },
                legend: {
                    display: true,
                    position: 'top',
                    labels: {
                        usePointStyle: true,
                        padding: 10,
                        font: {
                            size: 11
                        }
                    }
                },
                tooltip: {
                    callbacks: {
                        label: function(context) {
                            let label = context.dataset.label || '';
                            if (label) {
                                label += ': ';
                            }
                            label += formatNumber(context.parsed.y) + ' unidades';
                            return label;
                        },
                        afterLabel: function(context) {
                            const index = context.dataIndex;
                            const variacao = variacoes[index];
                            if (variacao !== null && variacao !== undefined) {
                                const sinal = variacao > 0 ? '+' : '';
                                return `Variação YoY: ${sinal}${variacao}%`;
                            }
                            return '';
                        }
                    }
                }
            },
            scales: {
                x: {
                    grid: {
                        display: false
                    }
                },
                y: {
                    min: yMin,
                    max: yMax,
                    grid: {
                        color: 'rgba(0, 0, 0, 0.05)'
                    },
                    ticks: {
                        callback: function(value) {
                            return formatNumber(value);
                        }
                    }
                }
            }
        },
        plugins: [{
            id: 'customLabels',
            afterDatasetsDraw: function(chart) {
                const ctx = chart.ctx;
                chart.data.datasets.forEach((dataset, datasetIndex) => {
                    const meta = chart.getDatasetMeta(datasetIndex);
                    if (!meta.hidden && datasetIndex === 1) { // Apenas para previsão (segundo dataset)
                        meta.data.forEach((bar, index) => {
                            const variacao = variacoes[index];
                            if (variacao !== null && variacao !== undefined) {
                                const sinal = variacao > 0 ? '+' : '';
                                const cor = variacao > 0 ? '#059669' : '#dc2626';

                                ctx.fillStyle = cor;
                                ctx.font = 'bold 11px Arial';
                                ctx.textAlign = 'center';
                                ctx.textBaseline = 'bottom';

                                const text = `${sinal}${variacao}%`;
                                ctx.fillText(text, bar.x, bar.y - 5);
                            }
                        });
                    }
                });
            }
        }]
    });

    // Preencher tabela comparativa
    preencherTabelaYoY(dados.comparacao_yoy);
}

// ===== TABELA COMPARATIVA YoY =====
function preencherTabelaYoY(comparacao_yoy) {
    if (!comparacao_yoy || comparacao_yoy.length === 0) {
        return;
    }

    const thead = document.getElementById('yoyComparisonHeader');
    const tbody = document.getElementById('yoyComparisonBody');

    // Limpar conteúdo anterior
    thead.innerHTML = '';
    tbody.innerHTML = '';

    // Criar cabeçalho completo - Compacto e sem scroll
    const mesesNomes = comparacao_yoy.map(d => d.mes_nome);
    let headerRow = '<tr style="background-color: #f5f5f5; border-bottom: 2px solid #6C757D; font-size: 0.85em;">';
    headerRow += '<th style="padding: 6px 8px; text-align: left; border-right: 1px solid #ddd; white-space: nowrap;">Período</th>';

    mesesNomes.forEach(mes => {
        headerRow += `<th style="padding: 6px 4px; border-left: 1px solid #e5e5e5; white-space: nowrap; font-size: 0.85em;">${mes}</th>`;
    });

    headerRow += '<th style="padding: 6px 8px; border-left: 2px solid #6C757D; background-color: #F8F9FA; font-weight: bold; white-space: nowrap;">Total</th>';
    headerRow += '</tr>';
    thead.innerHTML = headerRow;

    // Calcular totais
    let totalPrevisao = 0;
    let totalAnterior = 0;

    comparacao_yoy.forEach(d => {
        totalPrevisao += (d.previsao_atual || 0);
        totalAnterior += (d.demanda_ano_anterior || 0);
    });

    // Linha 1: Previsão (período atual) - Compacto
    let rowPrevisao = '<tr style="background-color: rgba(56, 239, 125, 0.1);">';
    rowPrevisao += '<td style="padding: 6px 8px; font-weight: bold; text-align: left; border-right: 1px solid #ddd; white-space: nowrap;">Previsão</td>';
    comparacao_yoy.forEach(d => {
        const valor = d.previsao_atual || 0;
        rowPrevisao += `<td style="padding: 6px 4px; border-left: 1px solid #e5e5e5; font-weight: 500; font-size: 0.9em;">${formatNumber(valor)}</td>`;
    });
    rowPrevisao += `<td style="padding: 6px 8px; border-left: 2px solid #6C757D; background-color: #F8F9FA; font-weight: bold;">${formatNumber(totalPrevisao)}</td>`;
    rowPrevisao += '</tr>';

    // Linha 2: Ano Anterior (período passado) - Compacto
    let rowAnterior = '<tr style="background-color: rgba(17, 153, 142, 0.1);">';
    rowAnterior += '<td style="padding: 6px 8px; font-weight: bold; text-align: left; border-right: 1px solid #ddd; white-space: nowrap;">Ano Anterior</td>';
    comparacao_yoy.forEach(d => {
        const valor = d.demanda_ano_anterior || 0;
        rowAnterior += `<td style="padding: 6px 4px; border-left: 1px solid #e5e5e5; font-weight: 500; font-size: 0.9em;">${formatNumber(valor)}</td>`;
    });
    rowAnterior += `<td style="padding: 6px 8px; border-left: 2px solid #6C757D; background-color: #F8F9FA; font-weight: bold;">${formatNumber(totalAnterior)}</td>`;
    rowAnterior += '</tr>';

    // Linha 3: Variação % - Compacto
    let rowVariacao = '<tr style="border-top: 2px solid #ddd;">';
    rowVariacao += '<td style="padding: 6px 8px; font-weight: bold; text-align: left; border-right: 1px solid #ddd; white-space: nowrap;">Variação %</td>';
    comparacao_yoy.forEach(d => {
        const variacao = d.variacao_percentual;
        if (variacao !== null && variacao !== undefined) {
            const sinal = variacao > 0 ? '+' : '';
            const cor = variacao > 0 ? '#059669' : (variacao < 0 ? '#dc2626' : '#666');
            rowVariacao += `<td style="padding: 6px 4px; border-left: 1px solid #e5e5e5; font-weight: bold; color: ${cor}; font-size: 0.9em;">${sinal}${variacao.toFixed(1)}%</td>`;
        } else {
            rowVariacao += `<td style="padding: 6px 4px; border-left: 1px solid #e5e5e5; color: #999; font-size: 0.9em;">N/A</td>`;
        }
    });

    // Variação total
    const variacaoTotal = totalAnterior > 0 ? ((totalPrevisao - totalAnterior) / totalAnterior) * 100 : 0;
    const sinalTotal = variacaoTotal > 0 ? '+' : '';
    const corTotal = variacaoTotal > 0 ? '#059669' : (variacaoTotal < 0 ? '#dc2626' : '#666');
    rowVariacao += `<td style="padding: 6px 8px; border-left: 2px solid #6C757D; background-color: #F8F9FA; font-weight: bold; color: ${corTotal};">${sinalTotal}${variacaoTotal.toFixed(1)}%</td>`;
    rowVariacao += '</tr>';

    // Adicionar as linhas ao tbody
    tbody.innerHTML = rowPrevisao + rowAnterior + rowVariacao;
}

// ===== MÉTRICAS DE ACURÁCIA (WMAPE + BIAS) =====
function exibirMetricasAcuracia(dados) {
    if (!dados.previsoes_lojas || dados.previsoes_lojas.length === 0) {
        return;
    }

    // Calcular métricas agregadas
    const previsoes_com_metricas = dados.previsoes_lojas.filter(p => p.WMAPE !== null && p.BIAS !== null);

    if (previsoes_com_metricas.length === 0) {
        return; // Não há métricas calculadas
    }

    // Calcular médias por loja/SKU (pegar apenas primeira previsão de cada combinação)
    const metricas_unicas = {};
    dados.previsoes_lojas.forEach(p => {
        const key = `${p.Loja}_${p.SKU}`;
        if (!metricas_unicas[key] && p.WMAPE !== null) {
            metricas_unicas[key] = {
                loja: p.Loja,
                sku: p.SKU,
                wmape: p.WMAPE,
                bias: p.BIAS,
                metodo: p.Metodo
            };
        }
    });

    const metricas_array = Object.values(metricas_unicas);

    // Calcular médias gerais
    const wmape_medio = metricas_array.reduce((sum, m) => sum + m.wmape, 0) / metricas_array.length;
    const bias_medio = metricas_array.reduce((sum, m) => sum + m.bias, 0) / metricas_array.length;

    // Interpretar WMAPE
    let wmape_classificacao = '';
    let wmape_cor = '';
    if (wmape_medio < 10) {
        wmape_classificacao = 'Excelente';
        wmape_cor = '#28a745'; // Verde
    } else if (wmape_medio < 20) {
        wmape_classificacao = 'Boa';
        wmape_cor = '#5cb85c';
    } else if (wmape_medio < 30) {
        wmape_classificacao = 'Aceitável';
        wmape_cor = '#f0ad4e'; // Laranja
    } else if (wmape_medio < 50) {
        wmape_classificacao = 'Fraca';
        wmape_cor = '#ff8c00';
    } else {
        wmape_classificacao = 'Muito fraca';
        wmape_cor = '#d9534f'; // Vermelho
    }

    // Interpretar BIAS
    let bias_interpretacao = '';
    let bias_acao = '';
    let bias_cor = '';
    const bias_abs = Math.abs(bias_medio);

    if (bias_abs < 5) {
        bias_interpretacao = 'Sem viés significativo';
        bias_acao = 'Modelo equilibrado, não requer ajuste';
        bias_cor = '#28a745';
    } else if (bias_medio > 0) {
        bias_interpretacao = `Superestimando em ${bias_abs.toFixed(1)} unidades`;
        bias_acao = 'Reduzir previsão para evitar excesso de estoque';
        bias_cor = '#ff8c00';
    } else {
        bias_interpretacao = `Subestimando em ${bias_abs.toFixed(1)} unidades`;
        bias_acao = 'Aumentar previsão para evitar rupturas';
        bias_cor = '#d9534f';
    }

    // Montar HTML
    const html = `
        <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap: 15px; margin-bottom: 15px;">
            <!-- Card WMAPE -->
            <div style="background: #f8f9fa; border-left: 4px solid ${wmape_cor}; padding: 15px; border-radius: 4px;">
                <div style="font-weight: bold; color: #495057; margin-bottom: 8px;">
                    📊 WMAPE (Erro Percentual Ponderado)
                </div>
                <div style="font-size: 1.8em; font-weight: bold; color: ${wmape_cor}; margin-bottom: 5px;">
                    ${wmape_medio.toFixed(1)}%
                </div>
                <div style="color: #6c757d; font-size: 0.9em; margin-bottom: 8px;">
                    Classificação: <span style="font-weight: bold; color: ${wmape_cor};">${wmape_classificacao}</span>
                </div>
                <div style="color: #6c757d; font-size: 0.85em;">
                    Erro ponderado por volume: ${wmape_medio.toFixed(1)}%
                </div>
            </div>

            <!-- Card BIAS -->
            <div style="background: #f8f9fa; border-left: 4px solid ${bias_cor}; padding: 15px; border-radius: 4px;">
                <div style="font-weight: bold; color: #495057; margin-bottom: 8px;">
                    🎯 BIAS (Viés Direcional)
                </div>
                <div style="font-size: 1.8em; font-weight: bold; color: ${bias_cor}; margin-bottom: 5px;">
                    ${bias_medio >= 0 ? '+' : ''}${bias_medio.toFixed(2)} un
                </div>
                <div style="color: #6c757d; font-size: 0.9em; margin-bottom: 8px;">
                    ${bias_interpretacao}
                </div>
                <div style="color: #6c757d; font-size: 0.85em;">
                    <strong>Ação:</strong> ${bias_acao}
                </div>
            </div>
        </div>

        <div style="background: #e9ecef; padding: 10px; border-radius: 4px; font-size: 0.85em; color: #495057;">
            <strong>ℹ️ O que significam essas métricas?</strong><br>
            • <strong>WMAPE:</strong> Erro ponderado pelo volume de vendas (produtos alto volume têm peso proporcional)<br>
            • <strong>BIAS:</strong> Indica se há tendência sistemática de superestimar (positivo) ou subestimar (negativo)<br>
            • Calculado via validação cruzada em ${metricas_array.length} combinações Loja/SKU
        </div>
    `;

    document.getElementById('accuracyMetricsContent').innerHTML = html;
    document.getElementById('accuracyMetricsCard').style.display = 'block';
}

// ===== ALERTAS INTELIGENTES =====
function exibirAlertasInteligentes(data) {
    if (!data.smart_alerts || data.smart_alerts.length === 0) {
        document.getElementById('smartAlertsCard').style.display = 'none';
        return;
    }

    const alertas = data.smart_alerts;
    const resumo = data.smart_alerts_summary || {total: 0, critical: 0, warning: 0, info: 0, success: 0};

    // Ordenar por prioridade (críticos primeiro)
    alertas.sort((a, b) => a.prioridade - b.prioridade);

    // Filtrar apenas alertas relevantes (ignorar SUCCESS para não poluir)
    const alertas_visiveis = alertas.filter(a => a.tipo !== 'SUCCESS');

    if (alertas_visiveis.length === 0) {
        // Se só tem alertas SUCCESS, mostrar mensagem positiva
        const html = `
            <div style="padding: 15px; text-align: center; color: #28a745;">
                <div style="font-size: 2em;">✅</div>
                <div style="margin-top: 10px;">
                    <strong>Nenhum alerta crítico detectado</strong><br>
                    <span style="font-size: 0.9em;">Todas as previsões estão dentro dos padrões esperados</span>
                </div>
            </div>
        `;
        document.getElementById('smartAlertsContent').innerHTML = html;
        document.getElementById('smartAlertsCard').style.display = 'block';
        return;
    }

    // Contador de alertas por tipo
    const badge_critico = resumo.critical > 0 ? `<span style="background: #dc3545; color: white; padding: 2px 8px; border-radius: 12px; font-size: 0.85em; margin-left: 8px;">${resumo.critical} 🔴</span>` : '';
    const badge_warning = resumo.warning > 0 ? `<span style="background: #ffc107; color: #000; padding: 2px 8px; border-radius: 12px; font-size: 0.85em; margin-left: 8px;">${resumo.warning} 🟡</span>` : '';
    const badge_info = resumo.info > 0 ? `<span style="background: #17a2b8; color: white; padding: 2px 8px; border-radius: 12px; font-size: 0.85em; margin-left: 8px;">${resumo.info} 🔵</span>` : '';

    // Agrupar alertas por SKU/Loja para mostrar de forma organizada
    const alertas_por_item = {};
    alertas_visiveis.forEach(alerta => {
        const key = `${alerta.loja}_${alerta.sku}`;
        if (!alertas_por_item[key]) {
            alertas_por_item[key] = {
                loja: alerta.loja,
                sku: alerta.sku,
                alertas: []
            };
        }
        alertas_por_item[key].alertas.push(alerta);
    });

    // Renderizar alertas
    let html = `
        <div style="margin-bottom: 15px; padding: 10px; background: #f8f9fa; border-radius: 6px;">
            <div style="display: flex; align-items: center; gap: 5px; flex-wrap: wrap;">
                <strong>Resumo:</strong>
                ${badge_critico}
                ${badge_warning}
                ${badge_info}
            </div>
        </div>
    `;

    // Mostrar apenas os primeiros 10 alertas (limitado para não poluir a tela)
    const max_alertas_expandidos = 5;
    let count = 0;

    for (const key in alertas_por_item) {
        const item = alertas_por_item[key];

        // Para cada SKU/Loja, mostrar os alertas mais críticos
        const alertas_criticos = item.alertas.filter(a => a.tipo === 'CRITICAL');
        const alertas_warning = item.alertas.filter(a => a.tipo === 'WARNING');
        const alertas_info = item.alertas.filter(a => a.tipo === 'INFO');

        // Mostrar críticos primeiro
        [...alertas_criticos, ...alertas_warning, ...alertas_info].forEach(alerta => {
            if (count >= max_alertas_expandidos) return;

            const icon = getTipoIcon(alerta.tipo);
            const cor = getTipoCor(alerta.tipo);
            const borda_cor = getTipoBorda(alerta.tipo);

            html += `
                <div style="margin-bottom: 12px; padding: 12px; border-left: 4px solid ${borda_cor}; background: #fff; border-radius: 4px; box-shadow: 0 1px 3px rgba(0,0,0,0.1);">
                    <div style="display: flex; align-items: flex-start; gap: 10px;">
                        <div style="font-size: 1.5em;">${icon}</div>
                        <div style="flex: 1;">
                            <div style="font-weight: bold; color: ${cor}; margin-bottom: 4px;">
                                ${alerta.titulo}
                            </div>
                            <div style="font-size: 0.9em; color: #666; margin-bottom: 4px;">
                                <strong>SKU:</strong> ${alerta.sku} | <strong>Loja:</strong> ${alerta.loja}
                            </div>
                            <div style="margin-bottom: 6px; font-size: 0.95em;">
                                ${alerta.mensagem}
                            </div>
                            <div style="font-size: 0.9em; color: #495057; padding: 6px; background: #f1f3f5; border-radius: 3px;">
                                <strong>💡 Ação:</strong> ${alerta.acao_recomendada}
                            </div>
                        </div>
                    </div>
                </div>
            `;
            count++;
        });

        if (count >= max_alertas_expandidos) break;
    }

    // Se houver mais alertas, mostrar botão "Ver mais"
    if (alertas_visiveis.length > max_alertas_expandidos) {
        const restantes = alertas_visiveis.length - max_alertas_expandidos;
        html += `
            <div style="text-align: center; padding: 10px; color: #666; font-size: 0.9em;">
                + ${restantes} alerta(s) adicional(is) não exibidos
            </div>
        `;
    }

    document.getElementById('smartAlertsContent').innerHTML = html;
    document.getElementById('smartAlertsCard').style.display = 'block';
}

function getTipoIcon(tipo) {
    const icons = {
        'CRITICAL': '🔴',
        'WARNING': '🟡',
        'INFO': '🔵',
        'SUCCESS': '🟢'
    };
    return icons[tipo] || '⚪';
}

function getTipoCor(tipo) {
    const cores = {
        'CRITICAL': '#dc3545',
        'WARNING': '#f0ad4e',
        'INFO': '#17a2b8',
        'SUCCESS': '#28a745'
    };
    return cores[tipo] || '#6c757d';
}

function getTipoBorda(tipo) {
    return getTipoCor(tipo);
}

// ===== TABELA FORNECEDOR/ITEM =====
function exibirTabelaFornecedorItem(dados, smartAlerts) {
    if (!dados.fornecedor_item || dados.fornecedor_item.length === 0) {
        return;
    }

    const tbody = document.getElementById('fornecedorItemBody');

    // Agrupar dados por fornecedor
    const porFornecedor = {};
    dados.fornecedor_item.forEach(item => {
        const fornecedor = item.Fornecedor || 'N/A';
        if (!porFornecedor[fornecedor]) {
            porFornecedor[fornecedor] = [];
        }
        porFornecedor[fornecedor].push(item);
    });

    let html = '';

    // Função auxiliar para calcular prioridade do alerta de um item
    function calcularPrioridadeAlerta(item, alerts) {
        const variacao = item.Variacao_YoY_Percentual;

        // Verificar se há alertas críticos para este SKU
        if (alerts && alerts.length > 0) {
            const alertasCriticos = alerts.filter(a =>
                a.sku === item.SKU && a.tipo === 'CRITICAL'
            );
            if (alertasCriticos.length > 0) {
                return 1; // 🔴 Crítico - Prioridade máxima
            }

            const alertasWarning = alerts.filter(a =>
                a.sku === item.SKU && a.tipo === 'WARNING'
            );
            if (alertasWarning.length > 0) {
                return 2; // 🟡 Alerta
            }
        }

        // Se não há alerta smart, usar lógica baseada na variação
        if (variacao === null || variacao === undefined) {
            return 5; // ⚪ Sem dados - menor prioridade
        }

        const absVariacao = Math.abs(variacao);
        if (absVariacao > 50) {
            return 2; // 🟡 Alerta (variação > 50%)
        } else if (absVariacao > 20) {
            return 3; // 🔵 Atenção (variação > 20%)
        } else {
            return 4; // 🟢 Normal (variação <= 20%)
        }
    }

    // Para cada fornecedor
    Object.keys(porFornecedor).sort().forEach(fornecedor => {
        let itensFornecedor = porFornecedor[fornecedor];

        // Ordenar itens por criticidade do alerta (mais críticos primeiro)
        itensFornecedor = itensFornecedor.map(item => ({
            ...item,
            _prioridade: calcularPrioridadeAlerta(item, smartAlerts),
            _absVariacao: Math.abs(item.Variacao_YoY_Percentual || 0)
        })).sort((a, b) => {
            // Primeiro por prioridade (menor = mais crítico)
            if (a._prioridade !== b._prioridade) {
                return a._prioridade - b._prioridade;
            }
            // Depois por variação absoluta (maior primeiro)
            return b._absVariacao - a._absVariacao;
        });

        // Calcular totalizadores do fornecedor
        let demandaPrevistaTotal = 0;
        let demandaAnteriorTotal = 0;

        itensFornecedor.forEach(item => {
            demandaPrevistaTotal += item.Demanda_Prevista || 0;
            demandaAnteriorTotal += item.Demanda_Ano_Anterior || 0;
        });

        // Variação YoY do fornecedor
        let variacaoFornecedor = 0;
        if (demandaAnteriorTotal > 0) {
            variacaoFornecedor = ((demandaPrevistaTotal - demandaAnteriorTotal) / demandaAnteriorTotal) * 100;
        }

        // Linha de cabeçalho do fornecedor com totalizadores
        html += `
            <tr style="background: linear-gradient(135deg, #6C757D 0%, #495057 100%); color: white;">
                <td colspan="6" style="padding: 12px; font-weight: bold; font-size: 1.1em;">
                    📦 ${fornecedor}
                    <div style="display: grid; grid-template-columns: repeat(3, 1fr); gap: 10px; margin-top: 8px; font-size: 0.85em; font-weight: normal;">
                        <div>
                            <div style="opacity: 0.8; font-size: 0.9em;">Demanda Prevista</div>
                            <div style="font-weight: bold;">${formatNumber(demandaPrevistaTotal)} un</div>
                        </div>
                        <div>
                            <div style="opacity: 0.8; font-size: 0.9em;">Demanda Ano Anterior</div>
                            <div style="font-weight: bold;">${formatNumber(demandaAnteriorTotal)} un</div>
                        </div>
                        <div>
                            <div style="opacity: 0.8; font-size: 0.9em;">Variação YoY</div>
                            <div style="font-weight: bold; color: ${variacaoFornecedor >= 0 ? '#4caf50' : '#ffeb3b'};">
                                ${variacaoFornecedor > 0 ? '+' : ''}${variacaoFornecedor.toFixed(1)}%
                            </div>
                        </div>
                    </div>
                </td>
            </tr>
        `;

        // Cabeçalho da tabela repetido para cada fornecedor
        html += `
            <tr style="background: #F8F9FA; color: #6C757D; font-weight: bold; font-size: 0.85em;">
                <th style="padding: 8px; text-align: center; border-bottom: 2px solid #6C757D; width: 30px;"></th>
                <th style="padding: 8px; text-align: left; border-bottom: 2px solid #6C757D;">SKU</th>
                <th style="padding: 8px; text-align: right; border-bottom: 2px solid #6C757D;">Demanda Prevista (un)</th>
                <th style="padding: 8px; text-align: right; border-bottom: 2px solid #6C757D;">Demanda Ano Anterior (un)</th>
                <th style="padding: 8px; text-align: right; border-bottom: 2px solid #6C757D;">Variação YoY (%)</th>
                <th style="padding: 8px; text-align: center; border-bottom: 2px solid #6C757D;">Método Estatístico</th>
            </tr>
        `;

        // Linhas de itens do fornecedor
        itensFornecedor.forEach(item => {
            const variacao = item.Variacao_YoY_Percentual;
            const variacaoColor = variacao !== null && variacao !== undefined
                ? (variacao >= 0 ? '#059669' : '#dc2626')
                : '#666';
            const variacaoText = variacao !== null && variacao !== undefined
                ? `${variacao > 0 ? '+' : ''}${variacao.toFixed(1)}%`
                : '-';

            // Determinar ícone de alerta baseado na variação e nos alertas smart
            let alertIcon = '';
            let alertColor = '';
            let alertTitle = '';

            // Verificar se há alertas críticos para este SKU
            if (smartAlerts && smartAlerts.length > 0) {
                const alertasCriticos = smartAlerts.filter(a =>
                    a.sku === item.SKU &&
                    (a.tipo === 'CRITICAL' || a.tipo === 'WARNING')
                );

                if (alertasCriticos.length > 0) {
                    const alerta = alertasCriticos[0];  // Pegar o mais crítico
                    if (alerta.tipo === 'CRITICAL') {
                        alertIcon = '🔴';
                        alertColor = '#dc2626';
                        alertTitle = `CRÍTICO: ${alerta.titulo}`;
                    } else {
                        alertIcon = '🟡';
                        alertColor = '#f59e0b';
                        alertTitle = `ATENÇÃO: ${alerta.titulo}`;
                    }
                }
            }

            // Se não há alerta smart, usar lógica baseada na variação
            if (!alertIcon) {
                if (Math.abs(variacao) > 50) {
                    alertIcon = '🟡';
                    alertColor = '#f59e0b';
                    alertTitle = variacao > 0
                        ? 'ATENÇÃO: Crescimento superior a 50%'
                        : 'ATENÇÃO: Queda superior a 50%';
                } else if (Math.abs(variacao) > 20) {
                    alertIcon = '🔵';
                    alertColor = '#3b82f6';
                    alertTitle = variacao > 0
                        ? 'INFO: Crescimento significativo (>20%)'
                        : 'INFO: Queda significativa (>20%)';
                } else {
                    alertIcon = '🟢';
                    alertColor = '#10b981';
                    alertTitle = 'OK: Variação normal';
                }
            }

            html += `
                <tr style="background-color: ${Math.abs(variacao) > 20 ? '#fff3e0' : 'white'};">
                    <td style="padding: 6px; text-align: center;" title="${alertTitle}">
                        <span style="font-size: 1.2em; cursor: help;">${alertIcon}</span>
                    </td>
                    <td style="padding: 6px;">${item.SKU || 'N/A'}</td>
                    <td style="padding: 6px; text-align: right; font-weight: bold;">${formatNumber(item.Demanda_Prevista)}</td>
                    <td style="padding: 6px; text-align: right;">${formatNumber(item.Demanda_Ano_Anterior)}</td>
                    <td style="padding: 6px; text-align: right; font-weight: bold; color: ${variacaoColor};">${variacaoText}</td>
                    <td style="padding: 6px; text-align: center; font-size: 0.75em;">${item.Metodo_Estatistico || 'N/A'}</td>
                </tr>
            `;
        });

        // Linha de separação entre fornecedores
        html += `
            <tr>
                <td colspan="5" style="padding: 10px; background: #f5f5f5;"></td>
            </tr>
        `;
    });

    tbody.innerHTML = html;
}

// ===================================================================
// FUNCIONALIDADE DO BANCO DE DADOS
// ===================================================================

// Variável global para armazenar o gráfico de previsão
let previsaoChart = null;

// Função trocarTab removida - agora apenas consulta ao banco de dados

// Ajustar limites de previsão baseado na granularidade
function ajustarLimitesPrevisao() {
    const granularidade = document.getElementById('granularidade_banco').value;
    const inputMeses = document.getElementById('meses_previsao_banco');
    const helpText = document.getElementById('help_meses');

    let maxValue, defaultValue, helpMessage;

    switch(granularidade) {
        case 'diario':
            maxValue = 3;
            defaultValue = 3;
            helpMessage = 'Máximo: 3 meses (melhor acurácia para dados diários)';
            break;
        case 'semanal':
            maxValue = 6;
            defaultValue = 6;
            helpMessage = 'Máximo: 6 meses (melhor acurácia para dados semanais)';
            break;
        case 'mensal':
        default:
            maxValue = 24;
            defaultValue = 6;
            helpMessage = 'Máximo: 24 meses (melhor acurácia para dados mensais)';
            break;
    }

    inputMeses.max = maxValue;
    inputMeses.value = Math.min(parseInt(inputMeses.value) || defaultValue, maxValue);
    helpText.textContent = helpMessage;
}

// Carregar lojas do banco de dados
async function carregarLojas() {
    try {
        const select = document.getElementById('loja_banco');
        if (!select) {
            console.warn('Elemento loja_banco nao encontrado');
            return;
        }

        const response = await fetch('/api/lojas');
        const lojas = await response.json();

        select.innerHTML = '';
        lojas.forEach(loja => {
            const option = document.createElement('option');
            option.value = loja.cod_empresa;  // Usar cod_empresa como value
            option.textContent = loja.nome_loja;
            select.appendChild(option);
        });

        // Ao mudar loja, recarregar produtos
        select.addEventListener('change', () => carregarProdutosFiltrados());
    } catch (error) {
        console.error('Erro ao carregar lojas:', error);
    }
}

// Carregar fornecedores do banco de dados
async function carregarFornecedores() {
    try {
        const select = document.getElementById('fornecedor_banco');
        if (!select) {
            console.warn('Elemento fornecedor_banco nao encontrado');
            return;
        }

        const response = await fetch('/api/fornecedores');
        const fornecedores = await response.json();

        select.innerHTML = '';
        fornecedores.forEach(forn => {
            const option = document.createElement('option');
            option.value = forn.nome_fornecedor;
            option.textContent = forn.nome_fornecedor;
            select.appendChild(option);
        });

        // Ao mudar fornecedor, recarregar produtos
        select.addEventListener('change', () => carregarProdutosFiltrados());
    } catch (error) {
        console.error('Erro ao carregar fornecedores:', error);
    }
}

// Carregar linhas (categorias nivel 1) do banco de dados
async function carregarLinhas() {
    try {
        const select = document.getElementById('linha_banco');
        if (!select) {
            console.warn('Elemento linha_banco nao encontrado');
            return;
        }

        const response = await fetch('/api/linhas');
        const linhas = await response.json();

        select.innerHTML = '';
        linhas.forEach(item => {
            const option = document.createElement('option');
            option.value = item.linha;
            option.textContent = item.linha;
            select.appendChild(option);
        });

        // Ao mudar linha, recarregar sublinhas e produtos
        select.addEventListener('change', () => {
            carregarSublinhas();
            carregarProdutosFiltrados();
        });
    } catch (error) {
        console.error('Erro ao carregar linhas:', error);
    }
}

// Carregar sublinhas (categorias nivel 3) do banco de dados
async function carregarSublinhas() {
    try {
        const linhaSelect = document.getElementById('linha_banco');
        const select = document.getElementById('sublinha_banco');
        if (!select) {
            console.warn('Elemento sublinha_banco nao encontrado');
            return;
        }

        const linha = linhaSelect ? linhaSelect.value : '';
        const url = linha && linha !== 'TODAS'
            ? `/api/sublinhas?linha=${encodeURIComponent(linha)}`
            : '/api/sublinhas';

        const response = await fetch(url);
        const sublinhas = await response.json();

        select.innerHTML = '';
        sublinhas.forEach(item => {
            const option = document.createElement('option');
            option.value = item.codigo_linha;
            option.textContent = item.descricao_linha;
            select.appendChild(option);
        });

        // Ao mudar sublinha, recarregar produtos
        select.addEventListener('change', () => carregarProdutosFiltrados());
    } catch (error) {
        console.error('Erro ao carregar sublinhas:', error);
    }
}

// Carregar produtos filtrados do banco de dados
async function carregarProdutosFiltrados() {
    try {
        const select = document.getElementById('produto_banco');
        if (!select) {
            console.warn('Elemento produto_banco nao encontrado');
            return;
        }

        const lojaEl = document.getElementById('loja_banco');
        const fornecedorEl = document.getElementById('fornecedor_banco');
        const linhaEl = document.getElementById('linha_banco');
        const sublinhaEl = document.getElementById('sublinha_banco');

        const loja = lojaEl ? lojaEl.value : '';
        const fornecedor = fornecedorEl ? fornecedorEl.value : '';
        const linha = linhaEl ? linhaEl.value : '';
        const sublinha = sublinhaEl ? sublinhaEl.value : '';

        // Construir URL com filtros
        const params = new URLSearchParams();
        if (loja && loja !== 'TODAS') params.append('loja', loja);
        if (fornecedor && fornecedor !== 'TODOS') params.append('fornecedor', fornecedor);
        if (linha && linha !== 'TODAS') params.append('linha', linha);
        if (sublinha && sublinha !== 'TODAS') params.append('sublinha', sublinha);

        const url = '/api/produtos_completo' + (params.toString() ? '?' + params.toString() : '');

        const response = await fetch(url);
        const produtos = await response.json();

        select.innerHTML = '';
        produtos.forEach(prod => {
            const option = document.createElement('option');
            option.value = prod.codigo;
            // Mostrar codigo + descricao para facilitar identificacao
            option.textContent = prod.codigo === 'TODOS'
                ? prod.descricao
                : `${prod.codigo} - ${prod.descricao}`;
            select.appendChild(option);
        });
    } catch (error) {
        console.error('Erro ao carregar produtos:', error);
    }
}

// Carregar categorias do banco de dados (mantido para compatibilidade)
async function carregarCategorias() {
    // Esta funcao foi substituida por carregarLinhas
    // Mantida para compatibilidade com codigo antigo
    carregarLinhas();
}

// Carregar produtos do banco de dados (mantido para compatibilidade)
async function carregarProdutos() {
    // Esta funcao foi substituida por carregarProdutosFiltrados
    // Mantida para compatibilidade com codigo antigo
    carregarProdutosFiltrados();
}

// Formatar número com separadores de milhares
function formatNumber(num) {
    return Math.round(num).toString().replace(/\B(?=(\d{3})+(?!\d))/g, ".");
}

// Preencher tabela comparativa com meses nas colunas
function preencherTabelaComparativa(resultado, melhorModelo, granularidade = 'mensal') {
    const thead = document.getElementById('tabelaComparativaHeader');
    const tbody = document.getElementById('tabelaComparativaBody');
    const previsoes = resultado.modelos[melhorModelo]?.futuro?.valores || [];
    const datasPrevisao = resultado.modelos[melhorModelo]?.futuro?.datas || [];

    // Usar ano_anterior para a linha "Real" (mesmo período do ano passado para comparação correta)
    const valoresReal = resultado.ano_anterior?.valores || [];
    const datasReal = resultado.ano_anterior?.datas || [];

    // Calcular tamanhos dinâmicos baseado no número de períodos
    const numPeriodos = previsoes.length;
    let fontSize, padding, labelWidth;

    if (numPeriodos <= 6) {
        fontSize = '0.9em';
        padding = '8px';
        labelWidth = '90px';
    } else if (numPeriodos <= 9) {
        fontSize = '0.85em';
        padding = '6px';
        labelWidth = '85px';
    } else if (numPeriodos <= 12) {
        fontSize = '0.75em';
        padding = '4px';
        labelWidth = '70px';
    } else {
        fontSize = '0.65em';
        padding = '3px';
        labelWidth = '60px';
    }

    // Função auxiliar para calcular número da semana ISO no ano
    function getWeekNumber(date) {
        const d = new Date(Date.UTC(date.getFullYear(), date.getMonth(), date.getDate()));
        const dayNum = d.getUTCDay() || 7;
        d.setUTCDate(d.getUTCDate() + 4 - dayNum);
        const yearStart = new Date(Date.UTC(d.getUTCFullYear(),0,1));
        return Math.ceil((((d - yearStart) / 86400000) + 1)/7);
    }

    // Função auxiliar para calcular o ANO ISO (pode ser diferente do ano do calendário)
    function getISOWeekYear(date) {
        const d = new Date(Date.UTC(date.getFullYear(), date.getMonth(), date.getDate()));
        const dayNum = d.getUTCDay() || 7;
        d.setUTCDate(d.getUTCDate() + 4 - dayNum);
        return d.getUTCFullYear();
    }

    // Função auxiliar para formatar período
    const meses = ['Jan', 'Fev', 'Mar', 'Abr', 'Mai', 'Jun', 'Jul', 'Ago', 'Set', 'Out', 'Nov', 'Dez'];

    function formatarPeriodo(dataStr, gran, incluirAno = false) {
        if (!dataStr) return '';
        const data = parseLocalDate(dataStr);
        if (!data || isNaN(data.getTime())) return dataStr; // Retornar string original se parsing falhar
        if (gran === 'semanal') {
            const semanaAno = getWeekNumber(data);
            const anoISO = getISOWeekYear(data);
            return `S${semanaAno}/${anoISO.toString().slice(-2)}`;
        } else if (gran === 'diario' || gran === 'diaria') {
            // Formato: DD/MM ou DD/MM/AA se incluirAno=true
            const dia = data.getDate().toString().padStart(2, '0');
            const mes = (data.getMonth() + 1).toString().padStart(2, '0');
            if (incluirAno) {
                const ano = data.getFullYear().toString().slice(-2);
                return `${dia}/${mes}/${ano}`;
            }
            return `${dia}/${mes}`;
        } else {
            return `${meses[data.getMonth()]}/${data.getFullYear()}`;
        }
    }

    // Criar cabeçalho com duas linhas: período previsão e período ano anterior
    let headerHtml = '';

    // Linha 1: Períodos da PREVISÃO
    headerHtml += `<tr style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; font-size: ${fontSize};">`;
    headerHtml += `<th rowspan="2" style="padding: ${padding}; text-align: left; border: 1px solid #ddd; position: sticky; left: 0; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); z-index: 10; width: ${labelWidth}; vertical-align: middle;">Período</th>`;

    previsoes.forEach((_, index) => {
        const nomePeriodo = formatarPeriodo(datasPrevisao[index], granularidade);
        headerHtml += `<th style="padding: ${padding}; text-align: center; border: 1px solid #ddd; font-size: 0.85em;">${nomePeriodo}</th>`;
    });

    // Adicionar coluna TOTAL
    headerHtml += `<th rowspan="2" style="padding: ${padding}; text-align: center; border: 1px solid #ddd; background: #5a67d8; font-weight: bold; vertical-align: middle;">TOTAL</th>`;
    headerHtml += '</tr>';

    // Linha 2: Períodos do REAL (ano anterior - para comparação)
    // Para diário, incluir o ano para deixar claro que é ano anterior com mesmo dia da semana
    const isDiario = granularidade === 'diario' || granularidade === 'diaria';
    headerHtml += `<tr style="background: #8b9dc3; color: white; font-size: ${fontSize};">`;
    previsoes.forEach((_, index) => {
        const nomePeriodoReal = formatarPeriodo(datasReal[index], granularidade, isDiario);
        headerHtml += `<th style="padding: ${padding}; text-align: center; border: 1px solid #ddd; font-size: 0.8em; font-weight: normal;">${nomePeriodoReal || '-'}</th>`;
    });
    headerHtml += '</tr>';

    thead.innerHTML = headerHtml;

    // Criar linhas de dados
    let totalPrevisao = 0;
    let totalReal = 0;

    // Linha Previsão
    let rowPrevisao = `<tr style="background: #f0f4ff; font-size: ${fontSize};">`;
    rowPrevisao += `<td style="padding: ${padding}; font-weight: bold; border: 1px solid #ddd; position: sticky; left: 0; background: #f0f4ff; z-index: 5; width: ${labelWidth};">Previsão</td>`;
    previsoes.forEach((valor) => {
        totalPrevisao += valor;
        rowPrevisao += `<td style="padding: ${padding}; text-align: center; border: 1px solid #ddd; font-weight: 500;">${formatNumber(valor)}</td>`;
    });
    rowPrevisao += `<td style="padding: ${padding}; text-align: center; border: 1px solid #ddd; font-weight: bold; background: #e0e7ff;">${formatNumber(totalPrevisao)}</td>`;
    rowPrevisao += '</tr>';

    // Linha Real (Ano Anterior - para comparação com previsão)
    // Para diário, usar "Ano Ant." para deixar claro que é o mesmo dia da semana do ano anterior
    const labelReal = isDiario ? 'Ano Ant.' : 'Real';
    let rowReal = `<tr style="background: white; font-size: ${fontSize};">`;
    rowReal += `<td style="padding: ${padding}; font-weight: bold; border: 1px solid #ddd; position: sticky; left: 0; background: white; z-index: 5; width: ${labelWidth};">${labelReal}</td>`;

    // Exibir valores nas colunas (limitado ao número de períodos de previsão)
    for (let i = 0; i < numPeriodos; i++) {
        const valor = valoresReal[i] || 0;
        rowReal += `<td style="padding: ${padding}; text-align: center; border: 1px solid #ddd;">${formatNumber(valor)}</td>`;
    }

    // Total Real: somar apenas os valores exibidos (limitado a numPeriodos)
    totalReal = valoresReal.slice(0, numPeriodos).reduce((sum, val) => sum + val, 0);
    rowReal += `<td style="padding: ${padding}; text-align: center; border: 1px solid #ddd; font-weight: bold; background: #f3f4f6;">${formatNumber(totalReal)}</td>`;
    rowReal += '</tr>';

    // Linha Variação
    let rowVariacao = `<tr style="background: #fef3c7; font-size: ${fontSize};">`;
    rowVariacao += `<td style="padding: ${padding}; font-weight: bold; border: 1px solid #ddd; position: sticky; left: 0; background: #fef3c7; z-index: 5; width: ${labelWidth};">Variação %</td>`;

    previsoes.forEach((valorPrevisao, index) => {
        const valorRealPeriodo = valoresReal[index] || 0;
        const variacao = valorRealPeriodo > 0
            ? ((valorPrevisao - valorRealPeriodo) / valorRealPeriodo * 100)
            : 0;

        const variacaoColor = variacao >= 0 ? '#10b981' : '#ef4444';
        const variacaoSinal = variacao >= 0 ? '+' : '';

        rowVariacao += `<td style="padding: ${padding}; text-align: center; border: 1px solid #ddd; font-weight: bold; color: ${variacaoColor};">${variacaoSinal}${variacao.toFixed(1)}%</td>`;
    });

    // Variação total
    const variacaoTotal = totalReal > 0
        ? ((totalPrevisao - totalReal) / totalReal * 100)
        : 0;
    const variacaoTotalColor = variacaoTotal >= 0 ? '#10b981' : '#ef4444';
    const variacaoTotalSinal = variacaoTotal >= 0 ? '+' : '';

    rowVariacao += `<td style="padding: ${padding}; text-align: center; border: 1px solid #ddd; font-weight: bold; color: ${variacaoTotalColor}; background: #fde68a;">${variacaoTotalSinal}${variacaoTotal.toFixed(1)}%</td>`;
    rowVariacao += '</tr>';

    tbody.innerHTML = rowPrevisao + rowReal + rowVariacao;
}

// Criar gráfico de previsão simplificado com 3 linhas + ano anterior
function criarGraficoPrevisao(historicoBase, historicoTeste, modelos, melhorModelo, granularidade = 'mensal', anoAnterior = null) {
    const canvas = document.getElementById('previsaoChart');
    if (!canvas) {
        console.error('Canvas previsaoChart não encontrado');
        return;
    }

    const ctx = canvas.getContext('2d');

    // Destruir gráfico anterior se existir
    if (previsaoChart) {
        previsaoChart.destroy();
    }

    // Preparar dados da base histórica (50%) - tratar caso seja null/undefined
    const datasBase = historicoBase?.datas || [];
    const valoresBase = historicoBase?.valores || [];

    // Preparar dados do período de teste (25%) - tratar caso seja null/undefined
    const datasTeste = historicoTeste?.datas || [];
    const valoresTeste = historicoTeste?.valores || [];

    // Preparar dados de previsão do melhor modelo
    const previsaoTeste = modelos[melhorModelo]?.teste?.valores || [];
    const datasPrevisaoTeste = modelos[melhorModelo]?.teste?.datas || [];

    const previsaoFuturo = modelos[melhorModelo]?.futuro?.valores || [];
    const datasPrevisaoFuturo = modelos[melhorModelo]?.futuro?.datas || [];

    // Combinar todas as datas para criar labels
    const todasDatas = [...datasBase, ...datasTeste, ...datasPrevisaoFuturo];
    const meses = ['Jan', 'Fev', 'Mar', 'Abr', 'Mai', 'Jun', 'Jul', 'Ago', 'Set', 'Out', 'Nov', 'Dez'];

    // Função auxiliar para calcular número da semana ISO no ano
    function getWeekNumber(date) {
        const d = new Date(Date.UTC(date.getFullYear(), date.getMonth(), date.getDate()));
        const dayNum = d.getUTCDay() || 7;
        d.setUTCDate(d.getUTCDate() + 4 - dayNum);
        const yearStart = new Date(Date.UTC(d.getUTCFullYear(),0,1));
        return Math.ceil((((d - yearStart) / 86400000) + 1)/7);
    }

    // Função auxiliar para calcular o ANO ISO (pode ser diferente do ano do calendário)
    function getISOWeekYear(date) {
        const d = new Date(Date.UTC(date.getFullYear(), date.getMonth(), date.getDate()));
        const dayNum = d.getUTCDay() || 7;
        d.setUTCDate(d.getUTCDate() + 4 - dayNum);
        return d.getUTCFullYear();
    }

    // Formatar labels baseado na granularidade
    const labels = todasDatas.map(dataStr => {
        const data = parseLocalDate(dataStr);
        // Verificar se o parsing foi bem sucedido
        if (!data || isNaN(data.getTime())) {
            return dataStr; // Retornar string original se parsing falhar
        }
        if (granularidade === 'semanal') {
            // Para semanal, mostrar "Sem XX" (número da semana no ano) com ano ISO
            const semanaAno = getWeekNumber(data);
            const anoISO = getISOWeekYear(data);
            return `S${semanaAno}/${anoISO.toString().slice(-2)}`;
        } else if (granularidade === 'diario' || granularidade === 'diaria') {
            // Para diária, mostrar DD/MM (com zero à esquerda, igual à tabela)
            const dia = data.getDate().toString().padStart(2, '0');
            const mes = (data.getMonth() + 1).toString().padStart(2, '0');
            return `${dia}/${mes}`;
        } else {
            // Para mensal, mostrar Mês/Ano
            return `${meses[data.getMonth()]}/${data.getFullYear().toString().slice(-2)}`;
        }
    });

    // Criar datasets
    const datasets = [];

    // 1. Dataset Base Histórica (50%) - Linha azul sólida
    const dadosBase = [...valoresBase];
    while (dadosBase.length < todasDatas.length) {
        dadosBase.push(null);
    }

    datasets.push({
        label: 'Base Histórica (50%)',
        data: dadosBase,
        borderColor: '#0070f3',
        backgroundColor: 'rgba(0, 112, 243, 0.1)',
        borderWidth: 2,
        fill: false,
        tension: 0.1,
        pointRadius: 3
    });

    // 2. Dataset Teste - Valores Reais (25%) - Linha verde sólida
    const dadosTesteReal = new Array(valoresBase.length).fill(null);
    dadosTesteReal.push(...valoresTeste);
    while (dadosTesteReal.length < todasDatas.length) {
        dadosTesteReal.push(null);
    }

    datasets.push({
        label: 'Teste - Real (25%)',
        data: dadosTesteReal,
        borderColor: '#10b981',
        backgroundColor: 'rgba(16, 185, 129, 0.1)',
        borderWidth: 2,
        fill: false,
        tension: 0.1,
        pointRadius: 4
    });

    // 3. Dataset Teste - Previsão (25%) - Linha verde tracejada
    // Mostra a previsão do modelo para o período de teste (backtest)
    if (previsaoTeste && previsaoTeste.length > 0) {
        const dadosTestePrevisao = new Array(valoresBase.length).fill(null);
        dadosTestePrevisao.push(...previsaoTeste);
        while (dadosTestePrevisao.length < todasDatas.length) {
            dadosTestePrevisao.push(null);
        }

        datasets.push({
            label: 'Teste - Previsão (25%)',
            data: dadosTestePrevisao,
            borderColor: '#059669',
            backgroundColor: 'rgba(5, 150, 105, 0.1)',
            borderWidth: 2,
            borderDash: [5, 5],
            fill: false,
            tension: 0.1,
            pointRadius: 3
        });
    }

    // 4. Dataset Previsão Futura (25%) - Linha roxa tracejada
    const dadosPrevisaoFuturo = new Array(valoresBase.length + valoresTeste.length).fill(null);
    dadosPrevisaoFuturo.push(...previsaoFuturo);

    datasets.push({
        label: `Previsão Futura (${melhorModelo})`,
        data: dadosPrevisaoFuturo,
        borderColor: '#8b5cf6',
        backgroundColor: 'rgba(139, 92, 246, 0.1)',
        borderWidth: 3,
        borderDash: [8, 4],
        fill: false,
        tension: 0.1,
        pointRadius: 4
    });

    // 5. Dataset Ano Anterior (para comparação com previsão futura) - Linha laranja tracejada
    if (anoAnterior && anoAnterior.valores && anoAnterior.valores.length > 0) {
        // O ano anterior deve aparecer alinhado com a previsão futura para comparação visual
        const dadosAnoAnterior = new Array(valoresBase.length + valoresTeste.length).fill(null);
        dadosAnoAnterior.push(...anoAnterior.valores);

        datasets.push({
            label: 'Ano Anterior (Comparação)',
            data: dadosAnoAnterior,
            borderColor: '#f97316',
            backgroundColor: 'rgba(249, 115, 22, 0.1)',
            borderWidth: 2,
            borderDash: [3, 3],
            fill: false,
            tension: 0.1,
            pointRadius: 3,
            pointStyle: 'triangle'
        });
    }

    // Calcular escala dinâmica do eixo Y
    // CORREÇÃO: Incluir TODOS os valores para garantir que nenhum dado fique fora da área visível
    const todosValores = [
        ...valoresBase,                       // Base histórica (50%)
        ...valoresTeste,                      // Teste real (25%)
        ...previsaoTeste,                     // Teste previsão (25%)
        ...previsaoFuturo,                    // Previsão futura
        ...(anoAnterior?.valores || [])       // Ano anterior (comparação YoY)
    ].filter(v => v !== null && v !== undefined);

    const valorMinimo = Math.min(...todosValores);
    const valorMaximo = Math.max(...todosValores);
    const amplitude = valorMaximo - valorMinimo;

    // Adicionar margem de 3% acima e abaixo para maximizar área útil do gráfico
    const margemInferior = valorMinimo - (amplitude * 0.03);
    const margemSuperior = valorMaximo + (amplitude * 0.03);

    // Garantir que não fique negativo se todos valores forem positivos
    const yMin = Math.max(0, margemInferior);
    const yMax = margemSuperior;

    // Configurar autoSkip baseado no número de períodos e granularidade
    const totalPeriodos = labels.length;
    // Para diário, usar autoSkip mais cedo para manter legibilidade
    const isDiario = granularidade === 'diario' || granularidade === 'diaria';
    const autoSkipLabels = isDiario ? totalPeriodos > 30 : totalPeriodos > 50;

    // Criar gráfico
    previsaoChart = new Chart(ctx, {
        type: 'line',
        data: {
            labels: labels,
            datasets: datasets
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    display: true,
                    position: 'top',
                    labels: {
                        usePointStyle: true,
                        padding: 15
                    }
                },
                tooltip: {
                    mode: 'index',
                    intersect: false,
                    callbacks: {
                        label: function(context) {
                            let label = context.dataset.label || '';
                            if (label) {
                                label += ': ';
                            }
                            if (context.parsed.y !== null) {
                                label += formatNumber(context.parsed.y);
                            }
                            return label;
                        }
                    }
                }
            },
            scales: {
                y: {
                    min: yMin,
                    max: yMax,
                    title: {
                        display: true,
                        text: 'Quantidade'
                    },
                    ticks: {
                        callback: function(value) {
                            return formatNumber(value);
                        }
                    }
                },
                x: {
                    title: {
                        display: true,
                        text: 'Período'
                    },
                    ticks: {
                        maxRotation: 45,
                        minRotation: 45,
                        autoSkip: autoSkipLabels,
                        // Para diário com muitos dias, mostrar ~1 label por semana (elegante e legível)
                        maxTicksLimit: isDiario
                            ? Math.min(Math.ceil(totalPeriodos / 7), 15)
                            : (autoSkipLabels ? 20 : undefined)
                    }
                }
            }
        }
    });
}

// =====================================================
// INTERFACE DINÂMICA DE PERÍODO POR GRANULARIDADE
// =====================================================

// Inicializar selects de ano
function inicializarSelectsAno() {
    const anoAtual = new Date().getFullYear();
    const anos = [anoAtual, anoAtual + 1, anoAtual + 2];

    const selectsAno = [
        'ano_inicio', 'ano_fim',
        'ano_semana_inicio', 'ano_semana_fim'
    ];

    selectsAno.forEach(id => {
        const select = document.getElementById(id);
        if (select) {
            select.innerHTML = '';
            anos.forEach(ano => {
                const option = document.createElement('option');
                option.value = ano;
                option.textContent = ano;
                select.appendChild(option);
            });
        }
    });

    // Definir valores padrão para período mensal
    const mesAtual = new Date().getMonth() + 1;
    document.getElementById('mes_inicio').value = mesAtual;
    document.getElementById('ano_inicio').value = anoAtual;

    // Fim = 3 meses depois
    let mesFim = mesAtual + 2;
    let anoFim = anoAtual;
    if (mesFim > 12) {
        mesFim -= 12;
        anoFim += 1;
    }
    document.getElementById('mes_fim').value = mesFim;
    document.getElementById('ano_fim').value = anoFim;

    // Valores padrão para semanal
    document.getElementById('ano_semana_inicio').value = anoAtual;
    document.getElementById('ano_semana_fim').value = anoAtual;

    // Valores padrão para diário
    const hoje = new Date();
    const dataInicio = new Date(hoje);
    dataInicio.setDate(dataInicio.getDate() + 1);
    const dataFim = new Date(hoje);
    dataFim.setMonth(dataFim.getMonth() + 1);

    document.getElementById('data_inicio').value = dataInicio.toISOString().split('T')[0];
    document.getElementById('data_fim').value = dataFim.toISOString().split('T')[0];
}

// Alternar interface de período baseado na granularidade
function atualizarInterfacePeriodo() {
    const granularidade = document.getElementById('granularidade_banco').value;

    // Esconder todos os períodos
    document.getElementById('periodo_mensal').style.display = 'none';
    document.getElementById('periodo_semanal').style.display = 'none';
    document.getElementById('periodo_diario').style.display = 'none';

    // Mostrar o período correspondente
    if (granularidade === 'mensal') {
        document.getElementById('periodo_mensal').style.display = 'block';
    } else if (granularidade === 'semanal') {
        document.getElementById('periodo_semanal').style.display = 'block';
    } else if (granularidade === 'diario') {
        document.getElementById('periodo_diario').style.display = 'block';
    }
}

// Coletar dados de período baseado na granularidade
function coletarDadosPeriodo() {
    const granularidade = document.getElementById('granularidade_banco').value;

    if (granularidade === 'mensal') {
        return {
            tipo_periodo: 'mensal',
            mes_inicio: parseInt(document.getElementById('mes_inicio').value),
            ano_inicio: parseInt(document.getElementById('ano_inicio').value),
            mes_fim: parseInt(document.getElementById('mes_fim').value),
            ano_fim: parseInt(document.getElementById('ano_fim').value)
        };
    } else if (granularidade === 'semanal') {
        return {
            tipo_periodo: 'semanal',
            semana_inicio: parseInt(document.getElementById('semana_inicio').value),
            ano_semana_inicio: parseInt(document.getElementById('ano_semana_inicio').value),
            semana_fim: parseInt(document.getElementById('semana_fim').value),
            ano_semana_fim: parseInt(document.getElementById('ano_semana_fim').value)
        };
    } else if (granularidade === 'diario') {
        return {
            tipo_periodo: 'diario',
            data_inicio: document.getElementById('data_inicio').value,
            data_fim: document.getElementById('data_fim').value
        };
    }

    return {};
}

// Inicializar ao carregar a página
document.addEventListener('DOMContentLoaded', function() {
    inicializarSelectsAno();
    atualizarInterfacePeriodo();

    // Adicionar listener para mudança de granularidade
    document.getElementById('granularidade_banco').addEventListener('change', atualizarInterfacePeriodo);
});

// Processar formulário do banco
document.getElementById('bancoForm').addEventListener('submit', async (e) => {
    e.preventDefault();

    // Esconder resultados e erros anteriores
    document.getElementById('results').style.display = 'none';
    document.getElementById('error').style.display = 'none';

    // Mostrar progresso
    document.getElementById('progress').style.display = 'block';
    const progressFill = document.getElementById('progressFill');
    const progressText = document.getElementById('progressText');

    // Simular progresso
    let progress = 0;
    const progressInterval = setInterval(() => {
        progress += 5;
        if (progress <= 90) {
            progressFill.style.width = progress + '%';
            if (progress < 30) {
                progressText.textContent = 'Consultando banco de dados...';
            } else if (progress < 60) {
                progressText.textContent = 'Aplicando modelos estatísticos...';
            } else {
                progressText.textContent = 'Gerando previsões...';
            }
        }
    }, 300);

    try {
        // Coletar dados do formulário
        const dadosPeriodo = coletarDadosPeriodo();
        const dados = {
            loja: document.getElementById('loja_banco').value,
            fornecedor: document.getElementById('fornecedor_banco').value,
            linha: document.getElementById('linha_banco').value,
            sublinha: document.getElementById('sublinha_banco').value,
            produto: document.getElementById('produto_banco').value,
            granularidade: document.getElementById('granularidade_banco').value,
            ...dadosPeriodo  // Inclui os dados de período específicos
        };

        console.log('=== DADOS ENVIADOS ===');
        console.log('Granularidade:', dados.granularidade);
        console.log('Tipo período:', dados.tipo_periodo);
        console.log('Dados completos:', JSON.stringify(dados, null, 2));

        // Enviar requisição (Bottom-Up com sazonalidade, tendência e limitadores)
        const response = await fetch('/api/gerar_previsao_banco', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(dados)
        });

        const resultado = await response.json();

        clearInterval(progressInterval);
        progressFill.style.width = '100%';
        progressText.textContent = 'Concluído!';

        setTimeout(() => {
            document.getElementById('progress').style.display = 'none';
        }, 500);

        if (response.status === 200) {
            console.log('Resultado recebido:', resultado);

            // Mostrar resultados
            document.getElementById('results').style.display = 'block';

            // Obter métricas do melhor modelo
            const melhorModelo = resultado.melhor_modelo;

            // V2 tem métricas dentro de modelos[modelo].metricas, V1 tem em resultado.metricas[modelo]
            const modeloData = resultado.modelos[melhorModelo] || {};
            const metricasMelhor = modeloData.metricas || resultado.metricas?.[melhorModelo] || {};

            // Calcular totais de previsão futura
            const previsaoFuturo = modeloData?.futuro?.valores || [];
            const totalPrevisao = previsaoFuturo.reduce((sum, val) => sum + val, 0);

            // Total do ano anterior (apenas os períodos correspondentes à previsão)
            const valoresAnoAnterior = resultado.ano_anterior?.valores || [];
            const numPeriodos = previsaoFuturo.length;
            const totalAnoAnterior = valoresAnoAnterior.slice(0, numPeriodos).reduce((sum, val) => sum + val, 0);

            // Calcular variação de demanda: (total previsão - total ano anterior) / total ano anterior * 100
            const variacaoDemanda = totalAnoAnterior > 0
                ? ((totalPrevisao - totalAnoAnterior) / totalAnoAnterior * 100)
                : 0;

            // Preencher KPIs no topo (métricas do período de teste)
            document.getElementById('kpi_wmape').textContent = `${(metricasMelhor.wmape || 0).toFixed(1)}%`;
            document.getElementById('kpi_bias').textContent = `${(metricasMelhor.bias || 0).toFixed(1)}%`;

            const variacaoSinal = variacaoDemanda >= 0 ? '+' : '';
            document.getElementById('kpi_variacao').textContent = `${variacaoSinal}${variacaoDemanda.toFixed(1)}%`;

            // V2 usa serie_temporal, V1 usa historico_base e historico_teste
            // Para V2, dividimos a série temporal em base e teste
            let historicoBase = resultado.historico_base;
            let historicoTeste = resultado.historico_teste;

            if (!historicoBase && resultado.serie_temporal) {
                // V2: dividir serie_temporal em base e teste (80/20)
                const datas = resultado.serie_temporal.datas || [];
                const valores = resultado.serie_temporal.valores || [];
                const splitIndex = Math.floor(datas.length * 0.8);

                historicoBase = {
                    datas: datas.slice(0, splitIndex),
                    valores: valores.slice(0, splitIndex)
                };
                historicoTeste = {
                    datas: datas.slice(splitIndex),
                    valores: valores.slice(splitIndex)
                };
            }

            // Criar gráfico principal com 3 linhas (base, teste, futuro) + ano anterior
            criarGraficoPrevisao(
                historicoBase,
                historicoTeste,
                resultado.modelos,
                melhorModelo,
                resultado.granularidade || 'mensal',  // Passar granularidade para formatação de labels
                resultado.ano_anterior  // Passar dados do ano anterior para comparação visual
            );

            // Preencher tabela comparativa
            preencherTabelaComparativa(resultado, melhorModelo, resultado.granularidade || 'mensal');

            // Exibir relatório detalhado por fornecedor/item (se houver dados)
            if (resultado.relatorio_detalhado) {
                console.log('[Debug] relatorio_detalhado encontrado com', resultado.relatorio_detalhado.itens?.length || 0, 'itens');
                exibirRelatorioDetalhado(resultado.relatorio_detalhado);
            } else {
                console.log('[Debug] relatorio_detalhado NAO encontrado no resultado');
            }

            // Armazenar dados para validação de demanda (v6.0)
            armazenarDadosPrevisao(resultado);

        } else {
            // Mostrar erro
            let detalhesHtml = '';
            if (resultado.detalhes) {
                detalhesHtml = `
                    <div style="margin-top: 15px; padding: 10px; background: #fff3cd; border: 1px solid #ffc107; border-radius: 4px;">
                        <strong>Detalhes:</strong><br>
                        Períodos encontrados: ${resultado.detalhes.periodos_encontrados}<br>
                        Loja: ${resultado.detalhes.filtros.loja}<br>
                        Categoria: ${resultado.detalhes.filtros.categoria}<br>
                        Produto: ${resultado.detalhes.filtros.produto}<br>
                        Granularidade: ${resultado.detalhes.filtros.granularidade}
                    </div>
                `;
            }

            document.getElementById('error').style.display = 'block';
            document.getElementById('errorMessage').innerHTML = resultado.erro + detalhesHtml;
        }

    } catch (error) {
        clearInterval(progressInterval);
        document.getElementById('progress').style.display = 'none';
        document.getElementById('error').style.display = 'block';
        document.getElementById('errorMessage').textContent = 'Erro ao gerar previsão: ' + error.message;
        console.error('Erro:', error);
    }
});

// Inicializar ao carregar a página
document.addEventListener('DOMContentLoaded', function() {
    // Carregar dados dos dropdowns
    carregarLojas();
    carregarFornecedores();
    carregarLinhas();
    carregarSublinhas();
    carregarProdutosFiltrados();

    // Configurar listener para ajuste de limites
    const granularidadeSelect = document.getElementById('granularidade_banco');
    if (granularidadeSelect) {
        granularidadeSelect.addEventListener('change', ajustarLimitesPrevisao);
        ajustarLimitesPrevisao(); // Chamar uma vez para configurar valores iniciais
    }
});

// =====================================================
// RELATÓRIO DETALHADO POR FORNECEDOR/ITEM
// =====================================================

// Variável global para armazenar dados do relatório detalhado
let dadosRelatorioDetalhado = null;

// Função principal para exibir o relatório detalhado
function exibirRelatorioDetalhado(dados) {
    if (!dados || !dados.itens || dados.itens.length === 0) {
        document.getElementById('relatorioDetalhadoSection').style.display = 'none';
        return;
    }

    // Armazenar dados globalmente para filtros
    dadosRelatorioDetalhado = dados;

    // Mostrar seção
    document.getElementById('relatorioDetalhadoSection').style.display = 'block';

    // Popular filtro de fornecedores
    popularFiltroFornecedores(dados.itens);

    // Renderizar tabela
    renderizarTabelaRelatorioDetalhado(dados.itens, dados.periodos_previsao, dados.granularidade);

    // Exibir resumo
    exibirResumoRelatorio(dados.itens);
}

// Popular dropdown de filtro de fornecedores
function popularFiltroFornecedores(itens) {
    const select = document.getElementById('filtroFornecedorRelatorio');
    const fornecedoresUnicos = [...new Set(itens.map(i => i.nome_fornecedor))].sort();

    // Manter opção "Todos"
    select.innerHTML = '<option value="">Todos os Fornecedores</option>';

    fornecedoresUnicos.forEach(fornecedor => {
        const option = document.createElement('option');
        option.value = fornecedor;
        option.textContent = fornecedor;
        select.appendChild(option);
    });
}

// Renderizar tabela do relatório detalhado
function renderizarTabelaRelatorioDetalhado(itens, periodos, granularidade) {
    const thead = document.getElementById('relatorioDetalhadoHeader');
    const tbody = document.getElementById('relatorioDetalhadoBody');

    // Formatar nome do período
    const mesesNomes = ['Jan', 'Fev', 'Mar', 'Abr', 'Mai', 'Jun', 'Jul', 'Ago', 'Set', 'Out', 'Nov', 'Dez'];

    function formatarPeriodoHeader(periodo) {
        if (!periodo) return '-';
        if (granularidade === 'semanal') {
            return `S${periodo.semana}/${periodo.ano}`;
        } else if (granularidade === 'diario' || granularidade === 'diaria') {
            const partes = periodo.split('-');
            if (partes.length === 3) {
                return `${partes[2]}/${partes[1]}`;
            }
            return periodo;
        } else {
            // Mensal
            const mesIdx = periodo.mes - 1;
            return `${mesesNomes[mesIdx]}/${periodo.ano}`;
        }
    }

    // Criar cabeçalho
    let headerHtml = '<tr style="background: linear-gradient(135deg, #10b981 0%, #059669 100%); color: white; font-size: 0.8em;">';
    headerHtml += '<th style="padding: 8px; text-align: left; border: 1px solid #ddd; position: sticky; left: 0; background: linear-gradient(135deg, #10b981 0%, #059669 100%); z-index: 11; min-width: 50px;">Código</th>';
    headerHtml += '<th style="padding: 8px; text-align: left; border: 1px solid #ddd; min-width: 200px;">Descrição</th>';

    // Colunas de períodos
    periodos.forEach(periodo => {
        const nomePeriodo = formatarPeriodoHeader(periodo);
        headerHtml += `<th style="padding: 6px; text-align: center; border: 1px solid #ddd; min-width: 60px;">${nomePeriodo}</th>`;
    });

    headerHtml += '<th style="padding: 8px; text-align: center; border: 1px solid #ddd; background: #047857; min-width: 70px;">Total Prev.</th>';
    headerHtml += '<th style="padding: 8px; text-align: center; border: 1px solid #ddd; min-width: 70px;">Ano Ant.</th>';
    headerHtml += '<th style="padding: 8px; text-align: center; border: 1px solid #ddd; min-width: 60px;">Var. %</th>';
    headerHtml += '<th style="padding: 8px; text-align: center; border: 1px solid #ddd; min-width: 50px;">Alerta</th>';
    headerHtml += '<th style="padding: 8px; text-align: center; border: 1px solid #ddd; min-width: 80px;">Método</th>';
    headerHtml += '</tr>';

    thead.innerHTML = headerHtml;

    // Agrupar itens por fornecedor
    const itensPorFornecedor = {};
    itens.forEach(item => {
        const fornecedor = item.nome_fornecedor || 'SEM FORNECEDOR';
        if (!itensPorFornecedor[fornecedor]) {
            itensPorFornecedor[fornecedor] = [];
        }
        itensPorFornecedor[fornecedor].push(item);
    });

    // Ordenar fornecedores alfabeticamente
    const fornecedoresOrdenados = Object.keys(itensPorFornecedor).sort();

    // Renderizar linhas
    let bodyHtml = '';
    const numColunasPeriodos = periodos.length;

    fornecedoresOrdenados.forEach(fornecedor => {
        const itensFornecedor = itensPorFornecedor[fornecedor];

        // Calcular totais do fornecedor
        let totalPrevFornecedor = 0;
        let totalAnoAntFornecedor = 0;
        let totaisPorPeriodo = new Array(numColunasPeriodos).fill(0);

        itensFornecedor.forEach(item => {
            totalPrevFornecedor += item.demanda_prevista_total || 0;
            totalAnoAntFornecedor += item.demanda_ano_anterior || 0;

            // Somar previsões por período
            if (item.previsao_por_periodo) {
                item.previsao_por_periodo.forEach((p, idx) => {
                    if (idx < numColunasPeriodos) {
                        totaisPorPeriodo[idx] += p.previsao || 0;
                    }
                });
            }
        });

        const variacaoFornecedor = totalAnoAntFornecedor > 0
            ? ((totalPrevFornecedor - totalAnoAntFornecedor) / totalAnoAntFornecedor * 100)
            : 0;

        // Criar ID seguro para o fornecedor (remover caracteres especiais)
        const fornecedorId = fornecedor.replace(/[^a-zA-Z0-9]/g, '_');

        // Linha do fornecedor (cabeçalho do grupo - colapsável)
        bodyHtml += `<tr class="linha-fornecedor" data-fornecedor="${fornecedorId}" onclick="toggleFornecedor('${fornecedorId}')" style="background: #e0f2f1; cursor: pointer; font-weight: bold;">`;
        bodyHtml += `<td colspan="2" style="padding: 10px; border: 1px solid #ddd; position: sticky; left: 0; background: #e0f2f1; z-index: 5;">`;
        bodyHtml += `<span class="toggle-icon" id="toggle-${fornecedorId}">▼</span> ${fornecedor} (${itensFornecedor.length} itens)`;
        bodyHtml += `</td>`;

        // Totais por período do fornecedor
        totaisPorPeriodo.forEach(total => {
            bodyHtml += `<td style="padding: 6px; text-align: center; border: 1px solid #ddd; background: #e0f2f1; font-weight: bold;">${formatNumber(total)}</td>`;
        });

        bodyHtml += `<td style="padding: 8px; text-align: center; border: 1px solid #ddd; background: #b2dfdb; font-weight: bold;">${formatNumber(totalPrevFornecedor)}</td>`;
        bodyHtml += `<td style="padding: 8px; text-align: center; border: 1px solid #ddd; background: #e0f2f1;">${formatNumber(totalAnoAntFornecedor)}</td>`;

        const corVariacao = variacaoFornecedor > 0 ? '#059669' : (variacaoFornecedor < 0 ? '#dc2626' : '#666');
        const sinalVariacao = variacaoFornecedor > 0 ? '+' : '';
        bodyHtml += `<td style="padding: 8px; text-align: center; border: 1px solid #ddd; background: #e0f2f1; color: ${corVariacao}; font-weight: bold;">${sinalVariacao}${variacaoFornecedor.toFixed(1)}%</td>`;

        bodyHtml += `<td style="padding: 8px; text-align: center; border: 1px solid #ddd; background: #e0f2f1;">-</td>`;
        bodyHtml += `<td style="padding: 8px; text-align: center; border: 1px solid #ddd; background: #e0f2f1;">-</td>`;
        bodyHtml += `</tr>`;

        // Função para calcular prioridade do alerta baseado no emoji
        function getPrioridadeAlerta(emoji) {
            const prioridades = {
                '🔴': 1,  // Crítico
                '🟡': 2,  // Alerta
                '🔵': 3,  // Atenção
                '🟢': 4,  // Normal
                '⚪': 5   // Sem dados
            };
            return prioridades[emoji] || 5;
        }

        // Ordenar itens por criticidade do alerta (mais críticos primeiro)
        const itensOrdenados = [...itensFornecedor].sort((a, b) => {
            const prioridadeA = getPrioridadeAlerta(a.sinal_emoji);
            const prioridadeB = getPrioridadeAlerta(b.sinal_emoji);

            // Primeiro por prioridade (menor = mais crítico)
            if (prioridadeA !== prioridadeB) {
                return prioridadeA - prioridadeB;
            }
            // Depois por variação absoluta (maior primeiro)
            return Math.abs(b.variacao_percentual || 0) - Math.abs(a.variacao_percentual || 0);
        });

        // Linhas dos itens (inicialmente visíveis)
        itensOrdenados.forEach(item => {
            bodyHtml += `<tr class="linha-item" data-fornecedor="${fornecedorId}" style="background: white;">`;
            bodyHtml += `<td style="padding: 6px 8px; border: 1px solid #ddd; position: sticky; left: 0; background: white; z-index: 5; font-size: 0.85em;">${item.cod_produto}</td>`;
            bodyHtml += `<td style="padding: 6px 8px; border: 1px solid #ddd; font-size: 0.85em; max-width: 250px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;" title="${item.descricao}">${item.descricao}</td>`;

            // Valores por período
            if (item.previsao_por_periodo && item.previsao_por_periodo.length > 0) {
                item.previsao_por_periodo.forEach((p, idx) => {
                    if (idx < numColunasPeriodos) {
                        bodyHtml += `<td style="padding: 6px; text-align: center; border: 1px solid #ddd; font-size: 0.85em;">${formatNumber(p.previsao || 0)}</td>`;
                    }
                });
                // Preencher colunas faltantes
                for (let i = item.previsao_por_periodo.length; i < numColunasPeriodos; i++) {
                    bodyHtml += `<td style="padding: 6px; text-align: center; border: 1px solid #ddd; color: #999;">0</td>`;
                }
            } else {
                // Item sem previsão - mostrar zeros
                for (let i = 0; i < numColunasPeriodos; i++) {
                    bodyHtml += `<td style="padding: 6px; text-align: center; border: 1px solid #ddd; color: #999;">0</td>`;
                }
            }

            // Total previsto
            bodyHtml += `<td style="padding: 6px; text-align: center; border: 1px solid #ddd; font-weight: 500; background: #f0fdf4;">${formatNumber(item.demanda_prevista_total || 0)}</td>`;

            // Ano anterior
            bodyHtml += `<td style="padding: 6px; text-align: center; border: 1px solid #ddd;">${formatNumber(item.demanda_ano_anterior || 0)}</td>`;

            // Variação
            const varItem = item.variacao_percentual || 0;
            const corVarItem = varItem > 0 ? '#059669' : (varItem < 0 ? '#dc2626' : '#666');
            const sinalVarItem = varItem > 0 ? '+' : '';
            bodyHtml += `<td style="padding: 6px; text-align: center; border: 1px solid #ddd; color: ${corVarItem}; font-weight: 500;">${sinalVarItem}${varItem.toFixed(1)}%</td>`;

            // Alerta
            bodyHtml += `<td style="padding: 6px; text-align: center; border: 1px solid #ddd; font-size: 1.2em;">${item.sinal_emoji || '⚪'}</td>`;

            // Método
            bodyHtml += `<td style="padding: 6px; text-align: center; border: 1px solid #ddd; font-size: 0.8em;">${item.metodo_estatistico || '-'}</td>`;

            bodyHtml += `</tr>`;
        });
    });

    tbody.innerHTML = bodyHtml;
}

// Toggle para expandir/recolher itens de um fornecedor
function toggleFornecedor(fornecedorId) {
    const linhasItem = document.querySelectorAll(`.linha-item[data-fornecedor="${fornecedorId}"]`);
    const toggleIcon = document.getElementById(`toggle-${fornecedorId}`);

    const estaVisivel = linhasItem[0]?.style.display !== 'none';

    linhasItem.forEach(linha => {
        linha.style.display = estaVisivel ? 'none' : '';
    });

    if (toggleIcon) {
        toggleIcon.textContent = estaVisivel ? '▶' : '▼';
    }
}

// Expandir todos os fornecedores
function expandirTodosFornecedores() {
    document.querySelectorAll('.linha-item').forEach(linha => {
        linha.style.display = '';
    });
    document.querySelectorAll('.toggle-icon').forEach(icon => {
        icon.textContent = '▼';
    });
}

// Recolher todos os fornecedores
function recolherTodosFornecedores() {
    document.querySelectorAll('.linha-item').forEach(linha => {
        linha.style.display = 'none';
    });
    document.querySelectorAll('.toggle-icon').forEach(icon => {
        icon.textContent = '▶';
    });
}

// Filtrar relatório detalhado
function filtrarRelatorioDetalhado() {
    if (!dadosRelatorioDetalhado) return;

    const filtroFornecedor = document.getElementById('filtroFornecedorRelatorio').value;
    const filtroAlerta = document.getElementById('filtroAlertaRelatorio').value;

    let itensFiltrados = dadosRelatorioDetalhado.itens;

    // Filtrar por fornecedor
    if (filtroFornecedor) {
        itensFiltrados = itensFiltrados.filter(item => item.nome_fornecedor === filtroFornecedor);
    }

    // Filtrar por alerta
    if (filtroAlerta) {
        itensFiltrados = itensFiltrados.filter(item => item.sinal_alerta === filtroAlerta);
    }

    // Re-renderizar tabela com itens filtrados
    renderizarTabelaRelatorioDetalhado(
        itensFiltrados,
        dadosRelatorioDetalhado.periodos_previsao,
        dadosRelatorioDetalhado.granularidade
    );

    // Atualizar resumo
    exibirResumoRelatorio(itensFiltrados);
}

// Exibir resumo do relatório
function exibirResumoRelatorio(itens) {
    const resumoSection = document.getElementById('resumoRelatorioDetalhado');

    if (!itens || itens.length === 0) {
        resumoSection.style.display = 'none';
        return;
    }

    // Calcular estatísticas
    const fornecedoresUnicos = new Set(itens.map(i => i.nome_fornecedor));
    const totalItens = itens.length;
    const criticos = itens.filter(i => i.sinal_alerta === 'vermelho').length;
    const alertas = itens.filter(i => i.sinal_alerta === 'amarelo').length;
    const atencao = itens.filter(i => i.sinal_alerta === 'azul').length;
    const normais = itens.filter(i => i.sinal_alerta === 'verde').length;

    // Preencher valores
    document.getElementById('resumoTotalFornecedores').textContent = fornecedoresUnicos.size;
    document.getElementById('resumoTotalItens').textContent = totalItens;
    document.getElementById('resumoCriticos').textContent = criticos;
    document.getElementById('resumoAlertas').textContent = alertas;
    document.getElementById('resumoAtencao').textContent = atencao;
    document.getElementById('resumoNormais').textContent = normais;

    resumoSection.style.display = 'block';
}

// Função gerarPrevisaoV2 removida - lógica V2 (Bottom-Up) agora é padrão no botão "Gerar Previsão"

// =====================================================
// VALIDAÇÃO DE DEMANDA (v6.0)
// =====================================================

// Variável global para armazenar dados da previsão atual (para validação)
let dadosPrevisaoAtual = null;

// Função para verificar se há um único fornecedor selecionado
function verificarFornecedorUnico() {
    const selectFornecedor = document.getElementById('fornecedor_banco');
    if (!selectFornecedor) {
        console.log('[Validacao] Select fornecedor_banco nao encontrado');
        return { valido: false, fornecedor: null };
    }

    const valor = selectFornecedor.value;
    // Válido apenas se não for vazio, não for "TODOS" e for um único valor
    const valido = valor && valor !== '' && valor !== 'TODOS' && valor !== 'Carregando...';
    console.log('[Validacao] Fornecedor verificado:', valor, '- Valido:', valido);
    return { valido: valido, fornecedor: valido ? valor : null };
}

// Função para verificar se a granularidade permite validação
function verificarGranularidadeValida() {
    const selectGranularidade = document.getElementById('granularidade_banco');
    if (!selectGranularidade) {
        console.log('[Validacao] Select granularidade_banco nao encontrado');
        return { valido: false, granularidade: null };
    }

    const valor = selectGranularidade.value;
    // Válido apenas para semanal ou diário
    const valido = valor === 'semanal' || valor === 'diario';
    console.log('[Validacao] Granularidade verificada:', valor, '- Valido:', valido);
    return { valido: valido, granularidade: valor };
}

// Função para armazenar dados da previsão quando gerada
function armazenarDadosPrevisao(resultado) {
    dadosPrevisaoAtual = resultado;
    console.log('[Validacao] Dados armazenados. Tem relatorio_detalhado:', !!(resultado && resultado.relatorio_detalhado));

    // Habilitar botão de validação APENAS se:
    // 1. Houver dados do relatório detalhado
    // 2. Houver um único fornecedor selecionado
    // 3. Granularidade for semanal ou diário
    const btnValidar = document.getElementById('btnValidarDemanda');
    if (btnValidar) {
        const { valido: fornecedorUnico } = verificarFornecedorUnico();
        const { valido: granularidadeValida, granularidade } = verificarGranularidadeValida();
        const temDados = resultado && resultado.relatorio_detalhado;
        const temItens = temDados && resultado.relatorio_detalhado.itens && resultado.relatorio_detalhado.itens.length > 0;

        console.log('[Validacao] Fornecedor unico:', fornecedorUnico, '- Granularidade valida:', granularidadeValida, '- Tem dados:', temDados, '- Tem itens:', temItens);

        // Botão só ativo se: granularidade (semanal ou diário) + 1 fornecedor + tem itens
        const podeValidar = temItens && fornecedorUnico && granularidadeValida;
        btnValidar.disabled = !podeValidar;

        // Atualizar estilo visual quando desabilitado
        if (btnValidar.disabled) {
            btnValidar.style.opacity = '0.5';
            btnValidar.style.cursor = 'not-allowed';
        } else {
            btnValidar.style.opacity = '1';
            btnValidar.style.cursor = 'pointer';
        }

        // Atualizar tooltip do botão com mensagem específica
        if (!granularidadeValida) {
            btnValidar.title = 'Validação disponível apenas para granularidade Semanal ou Diário';
        } else if (!fornecedorUnico) {
            btnValidar.title = 'Selecione um único fornecedor para validar a demanda';
        } else if (!temItens) {
            btnValidar.title = 'Gere uma previsão com dados detalhados primeiro';
        } else {
            btnValidar.title = 'Validar demanda para período futuro';
        }

        console.log('[Validacao] Botao disabled:', btnValidar.disabled);
    } else {
        console.log('[Validacao] Botao btnValidarDemanda nao encontrado');
    }
}

// Função para abrir modal de validação de demanda
function abrirModalValidacao() {
    console.log('[Validacao] Abrindo modal. dadosPrevisaoAtual:', dadosPrevisaoAtual);

    // Verificar se tem fornecedor único selecionado
    const { valido: fornecedorUnico, fornecedor } = verificarFornecedorUnico();
    if (!fornecedorUnico) {
        mostrarMensagemValidacao('erro', 'Fornecedor não selecionado',
            'Selecione um único fornecedor antes de validar a demanda.\n\nA validação deve ser feita por fornecedor para garantir a rastreabilidade.');
        return;
    }

    if (!dadosPrevisaoAtual || !dadosPrevisaoAtual.relatorio_detalhado) {
        mostrarMensagemValidacao('erro', 'Previsão não gerada',
            'Gere uma previsão primeiro antes de validar a demanda.\n\nCertifique-se de usar os filtros corretos e clicar em "Gerar Previsão".');
        return;
    }

    const modal = document.getElementById('modalValidacaoDemanda');
    if (!modal) {
        criarModalValidacao();
    }

    // Preencher dados no modal
    preencherModalValidacao();

    // Mostrar modal
    document.getElementById('modalValidacaoDemanda').style.display = 'flex';
}

// Função para criar o modal de validação (se não existir)
function criarModalValidacao() {
    const modalHtml = `
        <div id="modalValidacaoDemanda" class="modal-validacao" style="display: none; position: fixed; top: 0; left: 0; width: 100%; height: 100%; background: rgba(0,0,0,0.5); z-index: 1000; justify-content: center; align-items: center;">
            <div class="modal-content" style="background: white; border-radius: 12px; max-width: 900px; width: 95%; max-height: 90vh; overflow: hidden; box-shadow: 0 20px 60px rgba(0,0,0,0.3);">
                <!-- Header -->
                <div style="background: linear-gradient(135deg, #10b981 0%, #059669 100%); color: white; padding: 20px; display: flex; justify-content: space-between; align-items: center;">
                    <h2 style="margin: 0; font-size: 1.2em;">Validar Demanda para Período Futuro</h2>
                    <button onclick="fecharModalValidacao()" style="background: none; border: none; color: white; font-size: 1.5em; cursor: pointer;">&times;</button>
                </div>

                <!-- Body -->
                <div style="padding: 20px; overflow-y: auto; max-height: calc(90vh - 180px);">
                    <!-- Período da Previsão (read-only) -->
                    <div style="background: #f0fdf4; border-radius: 8px; padding: 16px; margin-bottom: 20px;">
                        <h4 style="margin: 0 0 12px 0; color: #065f46;">Período da Previsão</h4>
                        <div style="display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 16px;">
                            <div>
                                <label style="display: block; font-size: 0.85em; color: #374151; margin-bottom: 4px;">Data Início:</label>
                                <div id="validacao_data_inicio_display" style="padding: 10px 12px; background: #e5e7eb; border-radius: 6px; font-weight: 500; color: #374151;">-</div>
                                <input type="hidden" id="validacao_data_inicio">
                            </div>
                            <div>
                                <label style="display: block; font-size: 0.85em; color: #374151; margin-bottom: 4px;">Data Fim:</label>
                                <div id="validacao_data_fim_display" style="padding: 10px 12px; background: #e5e7eb; border-radius: 6px; font-weight: 500; color: #374151;">-</div>
                                <input type="hidden" id="validacao_data_fim">
                            </div>
                            <div>
                                <label style="display: block; font-size: 0.85em; color: #374151; margin-bottom: 4px;">Granularidade:</label>
                                <div id="validacao_granularidade_display" style="padding: 10px 12px; background: #e5e7eb; border-radius: 6px; font-weight: 500; color: #374151;">-</div>
                            </div>
                        </div>
                        <div style="margin-top: 12px;">
                            <label style="display: block; font-size: 0.85em; color: #374151; margin-bottom: 4px;">Observação (opcional):</label>
                            <input type="text" id="validacao_observacao" placeholder="Ex: Validação ajustada conforme reunião S&OP" style="width: 100%; padding: 8px; border: 1px solid #d1fae5; border-radius: 6px; box-sizing: border-box;">
                        </div>
                    </div>

                    <!-- Resumo dos Itens -->
                    <div style="background: #f8fafc; border-radius: 8px; padding: 16px; margin-bottom: 20px;">
                        <h4 style="margin: 0 0 12px 0; color: #374151;">Resumo da Validação</h4>
                        <div id="resumoValidacao" style="display: grid; grid-template-columns: repeat(4, 1fr); gap: 12px; text-align: center;">
                            <div style="background: white; padding: 12px; border-radius: 6px; border: 1px solid #e5e7eb;">
                                <div style="font-size: 0.8em; color: #6b7280;">Itens</div>
                                <div id="validacao_total_itens" style="font-size: 1.5em; font-weight: bold; color: #1f2937;">0</div>
                            </div>
                            <div style="background: white; padding: 12px; border-radius: 6px; border: 1px solid #e5e7eb;">
                                <div style="font-size: 0.8em; color: #6b7280;">Fornecedor</div>
                                <div id="validacao_nome_fornecedor" style="font-size: 1em; font-weight: bold; color: #1f2937; word-break: break-word;">-</div>
                            </div>
                            <div style="background: white; padding: 12px; border-radius: 6px; border: 1px solid #e5e7eb;">
                                <div style="font-size: 0.8em; color: #6b7280;">Demanda Original</div>
                                <div id="validacao_demanda_original" style="font-size: 1.2em; font-weight: bold; color: #6b7280;">0</div>
                            </div>
                            <div style="background: white; padding: 12px; border-radius: 6px; border: 1px solid #e5e7eb;">
                                <div style="font-size: 0.8em; color: #6b7280;">Demanda Ajustada</div>
                                <div id="validacao_demanda_total" style="font-size: 1.5em; font-weight: bold; color: #10b981;">0</div>
                            </div>
                        </div>
                    </div>

                    <!-- Tabela de Itens com campo editável -->
                    <div style="border: 1px solid #e5e7eb; border-radius: 8px; overflow: hidden;">
                        <div style="background: #f8fafc; padding: 12px 16px; border-bottom: 1px solid #e5e7eb; display: flex; justify-content: space-between; align-items: center;">
                            <span style="font-weight: 600; color: #374151;">Itens a Validar (ajuste os valores se necessário)</span>
                            <span id="validacao_itens_selecionados" style="font-size: 0.85em; color: #6b7280;">0 selecionados</span>
                        </div>
                        <div style="max-height: 350px; overflow-y: auto;">
                            <table style="width: 100%; border-collapse: collapse; font-size: 0.85em;">
                                <thead style="position: sticky; top: 0; background: #f8fafc; z-index: 1;">
                                    <tr>
                                        <th style="padding: 8px; text-align: left; border-bottom: 1px solid #e5e7eb; width: 40px;">
                                            <input type="checkbox" id="validacao_selecionar_todos" onchange="toggleSelecionarTodosValidacao()" checked>
                                        </th>
                                        <th style="padding: 8px; text-align: left; border-bottom: 1px solid #e5e7eb;">Produto</th>
                                        <th style="padding: 8px; text-align: right; border-bottom: 1px solid #e5e7eb; width: 120px;">Demanda Prevista</th>
                                        <th style="padding: 8px; text-align: right; border-bottom: 1px solid #e5e7eb; width: 140px;">Demanda Validada</th>
                                    </tr>
                                </thead>
                                <tbody id="validacao_tabela_itens">
                                </tbody>
                            </table>
                        </div>
                    </div>
                </div>

                <!-- Footer -->
                <div style="padding: 16px 20px; border-top: 1px solid #e5e7eb; display: flex; justify-content: space-between; align-items: center;">
                    <button onclick="fecharModalValidacao()" style="padding: 10px 20px; background: #f3f4f6; color: #374151; border: none; border-radius: 6px; cursor: pointer;">
                        Cancelar
                    </button>
                    <button onclick="salvarValidacaoDemanda()" style="padding: 10px 24px; background: linear-gradient(135deg, #10b981 0%, #059669 100%); color: white; border: none; border-radius: 6px; cursor: pointer; font-weight: 600;">
                        Salvar Demanda Validada
                    </button>
                </div>
            </div>
        </div>
    `;

    document.body.insertAdjacentHTML('beforeend', modalHtml);
}

// Função para preencher dados no modal de validação
function preencherModalValidacao() {
    if (!dadosPrevisaoAtual || !dadosPrevisaoAtual.relatorio_detalhado) return;

    const dados = dadosPrevisaoAtual.relatorio_detalhado;
    const modelos = dadosPrevisaoAtual.modelos || {};

    // Obter granularidade do filtro usado na previsão
    let granularidade = document.getElementById('granularidade_banco')?.value || 'mensal';

    // Obter datas DIRETAMENTE dos campos de filtro (que o usuário usou)
    let dataInicio = '';
    let dataFim = '';

    if (granularidade === 'semanal') {
        // Semanal: usar semana_inicio/ano_semana_inicio e semana_fim/ano_semana_fim
        const semanaInicio = document.getElementById('semana_inicio')?.value;
        const anoSemanaInicio = document.getElementById('ano_semana_inicio')?.value;
        const semanaFim = document.getElementById('semana_fim')?.value;
        const anoSemanaFim = document.getElementById('ano_semana_fim')?.value;

        if (semanaInicio && anoSemanaInicio) {
            const dataInicioSemana = getDateFromWeek(parseInt(anoSemanaInicio), parseInt(semanaInicio));
            dataInicio = dataInicioSemana.toISOString().split('T')[0];
        }
        if (semanaFim && anoSemanaFim) {
            const dataFimSemana = getDateFromWeek(parseInt(anoSemanaFim), parseInt(semanaFim));
            dataFimSemana.setDate(dataFimSemana.getDate() + 6); // Fim da semana
            dataFim = dataFimSemana.toISOString().split('T')[0];
        }
    } else if (granularidade === 'diario') {
        // Diário: usar data_inicio e data_fim diretamente
        dataInicio = document.getElementById('data_inicio')?.value || '';
        dataFim = document.getElementById('data_fim')?.value || '';
    } else {
        // Mensal: usar mes_inicio/ano_inicio e mes_fim/ano_fim
        const mesInicio = document.getElementById('mes_inicio')?.value;
        const anoInicio = document.getElementById('ano_inicio')?.value;
        const mesFim = document.getElementById('mes_fim')?.value;
        const anoFim = document.getElementById('ano_fim')?.value;

        if (mesInicio && anoInicio) {
            dataInicio = `${anoInicio}-${String(mesInicio).padStart(2, '0')}-01`;
        }
        if (mesFim && anoFim) {
            // Último dia do mês
            const ultimoDia = new Date(parseInt(anoFim), parseInt(mesFim), 0).getDate();
            dataFim = `${anoFim}-${String(mesFim).padStart(2, '0')}-${ultimoDia}`;
        }
    }

    // Fallback: tentar obter das datas do modelo se não conseguiu dos filtros
    if ((!dataInicio || !dataFim) && modelos['Bottom-Up'] && modelos['Bottom-Up'].periodos) {
        const periodos = modelos['Bottom-Up'].periodos;
        if (periodos.length > 0) {
            const primeiro = periodos[0];
            const ultimo = periodos[periodos.length - 1];

            if (!dataInicio) {
                if (granularidade === 'semanal' && primeiro.semana && primeiro.ano) {
                    const dt = getDateFromWeek(primeiro.ano, primeiro.semana);
                    dataInicio = dt.toISOString().split('T')[0];
                } else if (primeiro.mes && primeiro.ano) {
                    dataInicio = `${primeiro.ano}-${String(primeiro.mes).padStart(2, '0')}-01`;
                }
            }
            if (!dataFim) {
                if (granularidade === 'semanal' && ultimo.semana && ultimo.ano) {
                    const dt = getDateFromWeek(ultimo.ano, ultimo.semana);
                    dt.setDate(dt.getDate() + 6);
                    dataFim = dt.toISOString().split('T')[0];
                } else if (ultimo.mes && ultimo.ano) {
                    const ultimoDia = new Date(ultimo.ano, ultimo.mes, 0).getDate();
                    dataFim = `${ultimo.ano}-${String(ultimo.mes).padStart(2, '0')}-${ultimoDia}`;
                }
            }
        }
    }

    // Preencher campos read-only de data
    document.getElementById('validacao_data_inicio').value = dataInicio;
    document.getElementById('validacao_data_fim').value = dataFim;
    document.getElementById('validacao_data_inicio_display').textContent = formatarDataBR(dataInicio);
    document.getElementById('validacao_data_fim_display').textContent = formatarDataBR(dataFim);
    document.getElementById('validacao_granularidade_display').textContent =
        granularidade === 'semanal' ? 'Semanal' :
        granularidade === 'diario' ? 'Diário' : 'Mensal';

    // Extrair itens do relatório detalhado
    const itens = dados.itens || [];
    const { fornecedor } = verificarFornecedorUnico();

    // Calcular demanda total
    const demandaTotal = itens.reduce((sum, item) => {
        const demanda = item.demanda_prevista_total || item.previsao_total || item.demanda_prevista || 0;
        return sum + demanda;
    }, 0);

    // Preencher resumo
    document.getElementById('validacao_total_itens').textContent = itens.length;
    document.getElementById('validacao_nome_fornecedor').textContent = fornecedor || '-';
    document.getElementById('validacao_demanda_original').textContent = Math.round(demandaTotal).toLocaleString('pt-BR');
    document.getElementById('validacao_demanda_total').textContent = Math.round(demandaTotal).toLocaleString('pt-BR');

    // Calcular dias do período para demanda diária
    let diasPeriodo = 30; // Fallback
    if (dataInicio && dataFim) {
        const diffTime = new Date(dataFim) - new Date(dataInicio);
        diasPeriodo = Math.ceil(diffTime / (1000 * 60 * 60 * 24)) + 1;
    }

    // Preencher tabela de itens com campo editável
    const tbody = document.getElementById('validacao_tabela_itens');
    tbody.innerHTML = '';

    itens.forEach((item, index) => {
        const demandaTotal = item.demanda_prevista_total || item.previsao_total || item.demanda_prevista || 0;
        const demandaTotalArredondada = Math.round(demandaTotal);

        const tr = document.createElement('tr');
        tr.innerHTML = `
            <td style="padding: 8px; border-bottom: 1px solid #f3f4f6;">
                <input type="checkbox" class="validacao-item-check" data-index="${index}" checked onchange="atualizarContadorValidacao(); atualizarDemandaTotalValidacao();">
            </td>
            <td style="padding: 8px; border-bottom: 1px solid #f3f4f6;">
                <strong>${item.cod_produto || item.codigo}</strong>
                <div style="font-size: 0.85em; color: #6b7280;">${(item.descricao || '').substring(0, 50)}${(item.descricao || '').length > 50 ? '...' : ''}</div>
            </td>
            <td style="padding: 8px; border-bottom: 1px solid #f3f4f6; text-align: right; color: #6b7280;">
                ${demandaTotalArredondada.toLocaleString('pt-BR')}
            </td>
            <td style="padding: 8px; border-bottom: 1px solid #f3f4f6; text-align: right;">
                <input type="number" class="validacao-demanda-input" data-index="${index}"
                    value="${demandaTotalArredondada}"
                    data-original="${demandaTotalArredondada}"
                    onchange="atualizarDemandaTotalValidacao()"
                    oninput="atualizarDemandaTotalValidacao()"
                    style="width: 100px; padding: 6px 8px; border: 1px solid #d1d5db; border-radius: 4px; text-align: right; font-weight: 500;">
            </td>
        `;
        tr.dataset.demandaTotal = demandaTotalArredondada;
        tr.dataset.codProduto = item.cod_produto || item.codigo;
        tr.dataset.nomeFornecedor = item.nome_fornecedor || '';
        tr.dataset.codFornecedor = item.cod_fornecedor || '';
        tbody.appendChild(tr);
    });

    atualizarContadorValidacao();
    atualizarDemandaTotalValidacao();
}

// Função auxiliar para converter semana ISO em data
function getDateFromWeek(year, week) {
    const jan4 = new Date(year, 0, 4);
    const dayOfWeek = jan4.getDay() || 7;
    const firstMonday = new Date(jan4);
    firstMonday.setDate(jan4.getDate() - dayOfWeek + 1);
    const targetDate = new Date(firstMonday);
    targetDate.setDate(firstMonday.getDate() + (week - 1) * 7);
    return targetDate;
}

// Função auxiliar para formatar data em PT-BR
function formatarDataBR(dataStr) {
    if (!dataStr) return '-';
    try {
        const [ano, mes, dia] = dataStr.split('-');
        return `${dia}/${mes}/${ano}`;
    } catch {
        return dataStr;
    }
}

// Função para atualizar demanda total ajustada
function atualizarDemandaTotalValidacao() {
    const inputs = document.querySelectorAll('.validacao-demanda-input');
    const checkboxes = document.querySelectorAll('.validacao-item-check');
    let total = 0;

    inputs.forEach((input, index) => {
        const checkbox = checkboxes[index];
        if (checkbox && checkbox.checked) {
            total += parseFloat(input.value) || 0;
        }
    });

    document.getElementById('validacao_demanda_total').textContent = Math.round(total).toLocaleString('pt-BR');
}

// Função para toggle selecionar todos
function toggleSelecionarTodosValidacao() {
    const checkboxAll = document.getElementById('validacao_selecionar_todos');
    const checkboxes = document.querySelectorAll('.validacao-item-check');
    checkboxes.forEach(cb => cb.checked = checkboxAll.checked);
    atualizarContadorValidacao();
}

// Função para atualizar contador de selecionados
function atualizarContadorValidacao() {
    const checkboxes = document.querySelectorAll('.validacao-item-check:checked');
    document.getElementById('validacao_itens_selecionados').textContent = `${checkboxes.length} selecionados`;
}

// Função para fechar modal
function fecharModalValidacao() {
    const modal = document.getElementById('modalValidacaoDemanda');
    if (modal) {
        modal.style.display = 'none';
    }
}

// Função para salvar validação de demanda
async function salvarValidacaoDemanda() {
    const dataInicio = document.getElementById('validacao_data_inicio').value;
    const dataFim = document.getElementById('validacao_data_fim').value;
    const observacao = document.getElementById('validacao_observacao').value;

    // Validações com mensagens claras
    if (!dataInicio || !dataFim) {
        mostrarMensagemValidacao('erro', 'Período não informado', 'O período de previsão não foi identificado. Gere uma nova previsão.');
        return;
    }

    if (new Date(dataInicio) > new Date(dataFim)) {
        mostrarMensagemValidacao('erro', 'Período inválido', 'A data de início deve ser anterior à data de fim.');
        return;
    }

    // Coletar itens selecionados
    const checkboxes = document.querySelectorAll('.validacao-item-check:checked');
    if (checkboxes.length === 0) {
        mostrarMensagemValidacao('erro', 'Nenhum item selecionado', 'Selecione pelo menos um item para validar.');
        return;
    }

    // Obter loja do formulário (pode ser TODAS para agregado)
    const codLoja = document.getElementById('loja_banco').value;

    // Calcular dias do período
    const diasPeriodo = Math.ceil((new Date(dataFim) - new Date(dataInicio)) / (1000 * 60 * 60 * 24)) + 1;

    // Montar array de itens com valores editados pelo usuário
    const itens = [];
    const inputs = document.querySelectorAll('.validacao-demanda-input');

    checkboxes.forEach(cb => {
        const index = parseInt(cb.dataset.index);
        const tr = cb.closest('tr');
        const input = inputs[index];

        // Usar o valor editado pelo usuário
        const demandaTotalValidada = parseFloat(input?.value) || 0;
        const demandaDiaria = demandaTotalValidada / diasPeriodo;

        itens.push({
            cod_produto: tr.dataset.codProduto,
            cod_loja: codLoja && codLoja !== 'TODAS' ? parseInt(codLoja) : null,
            cod_fornecedor: tr.dataset.codFornecedor ? parseInt(tr.dataset.codFornecedor) : null,
            data_inicio: dataInicio,
            data_fim: dataFim,
            demanda_diaria: demandaDiaria,
            demanda_total_periodo: demandaTotalValidada
        });
    });

    // Mostrar loader
    const btnSalvar = document.querySelector('#modalValidacaoDemanda button[onclick="salvarValidacaoDemanda()"]');
    const textoOriginal = btnSalvar.innerHTML;
    btnSalvar.innerHTML = '<span style="display: inline-block; width: 16px; height: 16px; border: 2px solid #fff; border-top-color: transparent; border-radius: 50%; animation: spin 1s linear infinite;"></span> Salvando...';
    btnSalvar.disabled = true;

    // Adicionar CSS de animação se não existir
    if (!document.getElementById('spinnerStyle')) {
        const style = document.createElement('style');
        style.id = 'spinnerStyle';
        style.textContent = '@keyframes spin { to { transform: rotate(360deg); } }';
        document.head.appendChild(style);
    }

    // Enviar para API
    try {
        const response = await fetch('/api/demanda_validada/salvar', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                itens: itens,
                usuario: 'usuario_sistema', // Pode ser substituído por login real
                observacao: observacao
            })
        });

        const resultado = await response.json();

        // Restaurar botão
        btnSalvar.innerHTML = textoOriginal;
        btnSalvar.disabled = false;

        if (resultado.success) {
            mostrarMensagemValidacao('sucesso', 'Demanda validada com sucesso!',
                `${resultado.itens_salvos} itens salvos para o período de ${formatarDataBR(dataInicio)} a ${formatarDataBR(dataFim)}.`);

            // Fechar modal após 2 segundos
            setTimeout(() => {
                fecharModalValidacao();
            }, 2000);
        } else {
            mostrarMensagemValidacao('erro', 'Erro ao validar demanda', resultado.erro || 'Erro desconhecido. Verifique os logs do servidor.');
        }
    } catch (error) {
        // Restaurar botão
        btnSalvar.innerHTML = textoOriginal;
        btnSalvar.disabled = false;

        console.error('Erro ao salvar validação:', error);
        mostrarMensagemValidacao('erro', 'Erro de conexão', 'Não foi possível conectar ao servidor. Verifique sua conexão e tente novamente.');
    }
}

// Função para mostrar mensagens de feedback no modal de validação
function mostrarMensagemValidacao(tipo, titulo, mensagem) {
    // Remover mensagem anterior se existir
    const msgAnterior = document.getElementById('msgFeedbackValidacao');
    if (msgAnterior) msgAnterior.remove();

    const cores = {
        sucesso: { bg: '#d1fae5', border: '#10b981', icon: '✓', iconColor: '#059669' },
        erro: { bg: '#fee2e2', border: '#ef4444', icon: '✕', iconColor: '#dc2626' },
        aviso: { bg: '#fef3c7', border: '#f59e0b', icon: '!', iconColor: '#d97706' }
    };

    const cor = cores[tipo] || cores.aviso;

    const msgHtml = `
        <div id="msgFeedbackValidacao" style="
            position: fixed;
            top: 50%;
            left: 50%;
            transform: translate(-50%, -50%);
            background: white;
            border-radius: 12px;
            padding: 24px 32px;
            box-shadow: 0 20px 60px rgba(0,0,0,0.3);
            z-index: 1100;
            text-align: center;
            min-width: 320px;
            max-width: 450px;
            animation: fadeInScale 0.3s ease;
        ">
            <div style="
                width: 56px;
                height: 56px;
                border-radius: 50%;
                background: ${cor.bg};
                border: 3px solid ${cor.border};
                display: flex;
                align-items: center;
                justify-content: center;
                margin: 0 auto 16px;
                font-size: 24px;
                font-weight: bold;
                color: ${cor.iconColor};
            ">${cor.icon}</div>
            <h3 style="margin: 0 0 8px; color: #1f2937; font-size: 1.1em;">${titulo}</h3>
            <p style="margin: 0; color: #6b7280; font-size: 0.9em; line-height: 1.5;">${mensagem}</p>
            ${tipo === 'erro' ? `
                <button onclick="document.getElementById('msgFeedbackValidacao').remove(); document.getElementById('overlayFeedbackValidacao').remove();"
                    style="margin-top: 16px; padding: 8px 24px; background: #f3f4f6; color: #374151; border: none; border-radius: 6px; cursor: pointer; font-weight: 500;">
                    Entendi
                </button>
            ` : ''}
        </div>
        <div id="overlayFeedbackValidacao" style="
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            background: rgba(0,0,0,0.3);
            z-index: 1050;
        " onclick="if(document.getElementById('msgFeedbackValidacao')) document.getElementById('msgFeedbackValidacao').remove(); this.remove();"></div>
    `;

    // Adicionar CSS de animação se não existir
    if (!document.getElementById('feedbackAnimStyle')) {
        const style = document.createElement('style');
        style.id = 'feedbackAnimStyle';
        style.textContent = '@keyframes fadeInScale { from { opacity: 0; transform: translate(-50%, -50%) scale(0.9); } to { opacity: 1; transform: translate(-50%, -50%) scale(1); } }';
        document.head.appendChild(style);
    }

    document.body.insertAdjacentHTML('beforeend', msgHtml);

    // Auto-remover mensagem de sucesso após 3 segundos
    if (tipo === 'sucesso') {
        setTimeout(() => {
            const msg = document.getElementById('msgFeedbackValidacao');
            const overlay = document.getElementById('overlayFeedbackValidacao');
            if (msg) msg.remove();
            if (overlay) overlay.remove();
        }, 3000);
    }
}
