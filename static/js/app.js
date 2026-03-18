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

// =====================================================
// FUNÇÕES DE CARREGAMENTO COM MULTI-SELECT
// =====================================================

// Carregar lojas do banco de dados (multi-select)
async function carregarLojas() {
    try {
        const container = document.querySelector('[data-id="loja_banco"]');
        if (!container) {
            console.warn('Container loja_banco nao encontrado');
            return;
        }

        const response = await fetch('/api/lojas');
        const data = await response.json();

        // API retorna {success: true, lojas: [...]}
        const lojas = data.lojas || data;
        const options = lojas.map(l => ({
            value: l.cod_empresa.toString(),
            label: l.nome_loja
        }));

        MultiSelect.create('loja_banco', options, {
            allSelectedText: 'Todas as lojas',
            noneSelectedText: 'Nenhuma loja',
            countSelectedText: '{count} lojas',
            selectAllByDefault: true,
            onchange: () => carregarProdutosFiltrados()
        });

    } catch (error) {
        console.error('Erro ao carregar lojas:', error);
    }
}

// Carregar fornecedores do banco de dados (multi-select)
async function carregarFornecedores() {
    try {
        const container = document.querySelector('[data-id="fornecedor_banco"]');
        if (!container) {
            console.warn('Container fornecedor_banco nao encontrado');
            return;
        }

        const response = await fetch('/api/fornecedores');
        const data = await response.json();

        // API retorna {success: true, fornecedores: [...]}
        const fornecedores = data.fornecedores || data;
        const options = fornecedores.map(f => ({
            value: f.nome_fornecedor,
            label: f.nome_fornecedor
        }));

        MultiSelect.create('fornecedor_banco', options, {
            allSelectedText: 'Todos os fornecedores',
            noneSelectedText: 'Nenhum fornecedor',
            countSelectedText: '{count} fornecedores',
            selectAllByDefault: true,
            onchange: () => {
                carregarProdutosFiltrados();
            }
        });

    } catch (error) {
        console.error('Erro ao carregar fornecedores:', error);
    }
}

// Carregar linhas (categorias nivel 1) do banco de dados (multi-select)
async function carregarLinhas() {
    try {
        const container = document.querySelector('[data-id="linha_banco"]');
        if (!container) {
            console.warn('Container linha_banco nao encontrado');
            return;
        }

        const response = await fetch('/api/linhas');
        const data = await response.json();

        // API retorna {success: true, linhas: [...]} onde linhas é array de strings
        const linhas = data.linhas || data;
        const options = linhas.map(l => ({
            value: l,
            label: l
        }));

        MultiSelect.create('linha_banco', options, {
            allSelectedText: 'Todas as linhas',
            noneSelectedText: 'Nenhuma linha',
            countSelectedText: '{count} linhas',
            selectAllByDefault: true,
            onchange: () => {
                carregarSublinhas();
                carregarProdutosFiltrados();
            }
        });

    } catch (error) {
        console.error('Erro ao carregar linhas:', error);
    }
}

// Carregar sublinhas (categorias nivel 3) do banco de dados (multi-select)
async function carregarSublinhas() {
    try {
        const container = document.querySelector('[data-id="sublinha_banco"]');
        if (!container) {
            console.warn('Container sublinha_banco nao encontrado');
            return;
        }

        // Obter linha selecionada
        const linhasSelecionadas = MultiSelect.getSelected('linha_banco');
        let url = '/api/sublinhas';
        if (linhasSelecionadas.length > 0) {
            url += '?linha=' + encodeURIComponent(JSON.stringify(linhasSelecionadas));
        }

        const response = await fetch(url);
        const data = await response.json();

        // API retorna {success: true, sublinhas: [{codigo, descricao}, ...]}
        const sublinhas = data.sublinhas || data;
        const options = sublinhas.map(s => ({
            value: s.codigo,
            label: s.descricao
        }));

        if (MultiSelect.instances['sublinha_banco']) {
            MultiSelect.updateOptions('sublinha_banco', options);
        } else {
            MultiSelect.create('sublinha_banco', options, {
                allSelectedText: 'Todas as sublinhas',
                noneSelectedText: 'Nenhuma sublinha',
                countSelectedText: '{count} sublinhas',
                selectAllByDefault: true,
                onchange: () => carregarProdutosFiltrados()
            });
        }

    } catch (error) {
        console.error('Erro ao carregar sublinhas:', error);
    }
}

// Carregar produtos filtrados do banco de dados (multi-select)
async function carregarProdutosFiltrados() {
    try {
        const container = document.querySelector('[data-id="produto_banco"]');
        if (!container) {
            console.warn('Container produto_banco nao encontrado');
            return;
        }

        // Obter valores dos filtros
        const lojas = MultiSelect.getSelected('loja_banco');
        const fornecedores = MultiSelect.getSelected('fornecedor_banco');
        const linhas = MultiSelect.getSelected('linha_banco');
        const sublinhas = MultiSelect.getSelected('sublinha_banco');

        // Construir URL com filtros
        const params = new URLSearchParams();
        if (fornecedores.length > 0) params.append('fornecedor', fornecedores[0]);
        if (linhas.length > 0) params.append('categoria', linhas[0]);
        if (sublinhas.length > 0) params.append('linha', sublinhas[0]);
        params.append('limit', '200');

        const url = '/api/produtos' + (params.toString() ? '?' + params.toString() : '');

        const response = await fetch(url);
        const data = await response.json();

        // API retorna {success: true, produtos: [...]}
        const produtos = data.produtos || data;
        const options = produtos.map(p => ({
            value: p.codigo.toString(),
            label: `${p.codigo} - ${p.descricao}`
        }));

        if (MultiSelect.instances['produto_banco']) {
            MultiSelect.updateOptions('produto_banco', options);
        } else {
            MultiSelect.create('produto_banco', options, {
                allSelectedText: 'Todos os produtos',
                noneSelectedText: 'Nenhum produto',
                countSelectedText: '{count} produtos',
                selectAllByDefault: true,
                maxHeight: '300px'
            });
        }

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
    let rowPrevisao = `<tr id="linhaPrevisaoComparativa" style="background: #f0f4ff; font-size: ${fontSize};">`;
    rowPrevisao += `<td style="padding: ${padding}; font-weight: bold; border: 1px solid #ddd; position: sticky; left: 0; background: #f0f4ff; z-index: 5; width: ${labelWidth};">Previsão</td>`;
    previsoes.forEach((valor, index) => {
        totalPrevisao += valor;
        const periodoData = datasPrevisao[index] || '';
        rowPrevisao += `<td data-comparativa-periodo="${periodoData}" style="padding: ${padding}; text-align: center; border: 1px solid #ddd; font-weight: 500;">${formatNumber(valor)}</td>`;
    });
    rowPrevisao += `<td id="totalPrevisaoComparativa" style="padding: ${padding}; text-align: center; border: 1px solid #ddd; font-weight: bold; background: #e0e7ff;">${formatNumber(totalPrevisao)}</td>`;
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

    // Se houver dados por fornecedor e mais de um fornecedor, exibir seção adicional
    if (resultado.comparacao_yoy_por_fornecedor && resultado.comparacao_yoy_por_fornecedor.length > 1) {
        preencherTabelaComparativaPorFornecedor(resultado, granularidade);
    }
}

// Preencher tabela comparativa por fornecedor (quando múltiplos fornecedores selecionados)
function preencherTabelaComparativaPorFornecedor(resultado, granularidade = 'mensal') {
    const container = document.getElementById('tabelaComparativa').parentElement;
    const dadosFornecedores = resultado.comparacao_yoy_por_fornecedor || [];
    const periodos = resultado.periodos_previsao_formatados || [];

    if (!dadosFornecedores.length || !periodos.length) return;

    // Remover tabela de fornecedores anterior se existir
    const tabelaAnterior = document.getElementById('tabelaFornecedoresComparativa');
    if (tabelaAnterior) {
        tabelaAnterior.remove();
    }

    // Criar nova div para tabela por fornecedor
    const divFornecedores = document.createElement('div');
    divFornecedores.id = 'tabelaFornecedoresComparativa';
    divFornecedores.style.marginTop = '20px';

    // Função para formatar período
    const meses = ['Jan', 'Fev', 'Mar', 'Abr', 'Mai', 'Jun', 'Jul', 'Ago', 'Set', 'Out', 'Nov', 'Dez'];
    function formatarPeriodo(dataStr) {
        if (!dataStr) return '';
        const data = parseLocalDate(dataStr);
        if (!data || isNaN(data.getTime())) return dataStr;
        if (granularidade === 'semanal') {
            const semana = Math.ceil((data.getDate() + new Date(data.getFullYear(), data.getMonth(), 1).getDay()) / 7);
            return `S${semana}/${data.getFullYear().toString().slice(-2)}`;
        } else if (granularidade === 'diario') {
            return `${data.getDate().toString().padStart(2, '0')}/${(data.getMonth() + 1).toString().padStart(2, '0')}`;
        } else {
            return `${meses[data.getMonth()]}/${data.getFullYear().toString().slice(-2)}`;
        }
    }

    // Calcular tamanhos dinâmicos
    const numPeriodos = periodos.length;
    let fontSize = numPeriodos <= 6 ? '0.85em' : (numPeriodos <= 12 ? '0.75em' : '0.65em');
    let padding = numPeriodos <= 6 ? '6px' : (numPeriodos <= 12 ? '4px' : '3px');

    // Montar tabela
    let html = `
        <h3 style="color: #667eea; margin-bottom: 15px; margin-top: 20px;">
            Comparativo por Fornecedor (Previsao vs Ano Anterior)
        </h3>
        <div style="overflow-x: auto;">
            <table style="width: 100%; border-collapse: collapse; font-size: ${fontSize};">
                <thead>
                    <tr style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white;">
                        <th style="padding: ${padding}; text-align: left; border: 1px solid #ddd; min-width: 120px;">Fornecedor</th>
                        <th style="padding: ${padding}; text-align: left; border: 1px solid #ddd; min-width: 80px;">Tipo</th>`;

    // Cabeçalhos de período
    periodos.forEach(periodo => {
        html += `<th style="padding: ${padding}; text-align: center; border: 1px solid #ddd;">${formatarPeriodo(periodo)}</th>`;
    });

    html += `<th style="padding: ${padding}; text-align: center; border: 1px solid #ddd; background: #5a67d8; font-weight: bold;">TOTAL</th>
                        <th style="padding: ${padding}; text-align: center; border: 1px solid #ddd; background: #5a67d8; font-weight: bold;">Var %</th>
                    </tr>
                </thead>
                <tbody>`;

    // Linhas por fornecedor
    dadosFornecedores.forEach((forn, idx) => {
        const bgColor = idx % 2 === 0 ? '#f8fafc' : '#ffffff';

        // Linha Previsão
        html += `<tr style="background: ${bgColor};">
            <td rowspan="3" style="padding: ${padding}; font-weight: bold; border: 1px solid #ddd; vertical-align: middle;">${forn.nome_fornecedor}</td>
            <td style="padding: ${padding}; border: 1px solid #ddd; color: #059669;">Previsao</td>`;

        let totalPrevForn = 0;
        periodos.forEach(periodo => {
            const valor = forn.previsao_por_periodo[periodo]?.previsao || 0;
            totalPrevForn += valor;
            html += `<td style="padding: ${padding}; text-align: center; border: 1px solid #ddd;">${formatNumber(valor)}</td>`;
        });

        const variacaoForn = forn.variacao_percentual;
        const varColor = variacaoForn >= 0 ? '#10b981' : '#ef4444';
        const varSinal = variacaoForn >= 0 ? '+' : '';

        html += `<td style="padding: ${padding}; text-align: center; border: 1px solid #ddd; font-weight: bold; background: #e0e7ff;">${formatNumber(totalPrevForn)}</td>
            <td rowspan="3" style="padding: ${padding}; text-align: center; border: 1px solid #ddd; font-weight: bold; color: ${varColor}; vertical-align: middle;">${variacaoForn !== null ? varSinal + variacaoForn.toFixed(1) + '%' : 'N/A'}</td>
        </tr>`;

        // Linha Ano Anterior
        html += `<tr style="background: ${bgColor};">
            <td style="padding: ${padding}; border: 1px solid #ddd; color: #6b7280;">Ano Ant.</td>`;

        let totalAAForn = 0;
        periodos.forEach(periodo => {
            const valor = forn.previsao_por_periodo[periodo]?.ano_anterior || 0;
            totalAAForn += valor;
            html += `<td style="padding: ${padding}; text-align: center; border: 1px solid #ddd; color: #6b7280;">${formatNumber(valor)}</td>`;
        });

        html += `<td style="padding: ${padding}; text-align: center; border: 1px solid #ddd; font-weight: bold; background: #f3f4f6;">${formatNumber(totalAAForn)}</td>
        </tr>`;

        // Linha Variação por período
        html += `<tr style="background: ${bgColor}; border-bottom: 2px solid #ddd;">
            <td style="padding: ${padding}; border: 1px solid #ddd; color: #f59e0b;">Var %</td>`;

        periodos.forEach(periodo => {
            const var_p = forn.previsao_por_periodo[periodo]?.variacao_percentual;
            if (var_p !== null && var_p !== undefined) {
                const vColor = var_p >= 0 ? '#10b981' : '#ef4444';
                const vSinal = var_p >= 0 ? '+' : '';
                html += `<td style="padding: ${padding}; text-align: center; border: 1px solid #ddd; color: ${vColor}; font-weight: 500;">${vSinal}${var_p.toFixed(1)}%</td>`;
            } else {
                html += `<td style="padding: ${padding}; text-align: center; border: 1px solid #ddd; color: #9ca3af;">N/A</td>`;
            }
        });

        html += `<td style="padding: ${padding}; border: 1px solid #ddd;"></td>
        </tr>`;
    });

    // Linha TOTAL CONSOLIDADO
    let totalPrevConsolidado = dadosFornecedores.reduce((sum, f) => sum + f.previsao_total, 0);
    let totalAAConsolidado = dadosFornecedores.reduce((sum, f) => sum + f.ano_anterior_total, 0);
    let variacaoConsolidada = totalAAConsolidado > 0 ? ((totalPrevConsolidado - totalAAConsolidado) / totalAAConsolidado * 100) : 0;
    let varConsolidadaColor = variacaoConsolidada >= 0 ? '#10b981' : '#ef4444';
    let varConsolidadaSinal = variacaoConsolidada >= 0 ? '+' : '';

    html += `<tr style="background: linear-gradient(135deg, #fef3c7 0%, #fde68a 100%); font-weight: bold;">
        <td colspan="2" style="padding: ${padding}; border: 1px solid #ddd;">TOTAL CONSOLIDADO</td>`;

    // Totais por período
    periodos.forEach(periodo => {
        let totalPeriodo = 0;
        dadosFornecedores.forEach(f => {
            totalPeriodo += f.previsao_por_periodo[periodo]?.previsao || 0;
        });
        html += `<td style="padding: ${padding}; text-align: center; border: 1px solid #ddd;">${formatNumber(totalPeriodo)}</td>`;
    });

    html += `<td style="padding: ${padding}; text-align: center; border: 1px solid #ddd; background: #fcd34d;">${formatNumber(totalPrevConsolidado)}</td>
        <td style="padding: ${padding}; text-align: center; border: 1px solid #ddd;"></td>
    </tr>`;

    html += `</tbody></table></div>`;

    divFornecedores.innerHTML = html;
    container.appendChild(divFornecedores);
}

// Exportar tabela comparativa para Excel
function exportarTabelaComparativa() {
    // Verificar se há dados de previsão disponíveis (usa variável global dadosPrevisaoAtual)
    if (!dadosPrevisaoAtual) {
        alert('Nenhuma previsão disponível para exportar. Por favor, gere uma previsão primeiro.');
        return;
    }

    const resultado = dadosPrevisaoAtual;
    const melhorModelo = resultado.melhor_modelo || 'Bottom-Up (Individual por Item)';
    const granularidade = resultado.granularidade || 'mensal';

    // Detectar formato V2 (Bottom-Up) vs V1 (modelos agregados)
    const isV2 = !resultado.modelos || !resultado.modelos[melhorModelo]?.futuro?.valores;

    let previsoes = [];
    let datasPrevisao = [];
    let valoresReal = [];

    if (isV2) {
        // Formato V2 (Bottom-Up): extrair dados de itens/relatorio_detalhado
        const itensDetalhados = resultado.relatorio_detalhado?.itens || resultado.itens || dadosRelatorioDetalhado?.itens || [];

        if (itensDetalhados.length === 0) {
            alert('Não há dados de previsão para exportar.');
            return;
        }

        // Agrupar dados por período
        const dadosPorPeriodo = {};

        itensDetalhados.forEach(item => {
            if (item.previsao_por_periodo) {
                item.previsao_por_periodo.forEach(p => {
                    if (!dadosPorPeriodo[p.periodo]) {
                        dadosPorPeriodo[p.periodo] = { previsao: 0, anoAnterior: 0 };
                    }
                    dadosPorPeriodo[p.periodo].previsao += (p.previsao || 0);
                    dadosPorPeriodo[p.periodo].anoAnterior += (p.ano_anterior || 0);
                });
            }
        });

        // Ordenar períodos e extrair arrays
        const periodosOrdenados = Object.keys(dadosPorPeriodo).sort();
        datasPrevisao = periodosOrdenados;
        previsoes = periodosOrdenados.map(p => dadosPorPeriodo[p].previsao);
        valoresReal = periodosOrdenados.map(p => dadosPorPeriodo[p].anoAnterior);

        console.log('[exportarTabelaComparativa] Formato V2 detectado');
        console.log('[exportarTabelaComparativa] Períodos:', periodosOrdenados.length);
        console.log('[exportarTabelaComparativa] Previsões:', previsoes.length);
    } else {
        // Formato V1: usar estrutura de modelos
        previsoes = resultado.modelos[melhorModelo]?.futuro?.valores || [];
        datasPrevisao = resultado.modelos[melhorModelo]?.futuro?.datas || [];
        valoresReal = resultado.ano_anterior?.valores || [];
        console.log('[exportarTabelaComparativa] Formato V1 detectado');
    }

    if (previsoes.length === 0) {
        alert('Não há dados de previsão para exportar.');
        return;
    }

    // Formatar períodos para exibição
    const meses = ['Jan', 'Fev', 'Mar', 'Abr', 'Mai', 'Jun', 'Jul', 'Ago', 'Set', 'Out', 'Nov', 'Dez'];

    function formatarPeriodo(dataStr) {
        if (!dataStr) return '';
        const data = parseLocalDate(dataStr);
        if (!data || isNaN(data.getTime())) return dataStr;

        if (granularidade === 'semanal') {
            const d = new Date(Date.UTC(data.getFullYear(), data.getMonth(), data.getDate()));
            const dayNum = d.getUTCDay() || 7;
            d.setUTCDate(d.getUTCDate() + 4 - dayNum);
            const yearStart = new Date(Date.UTC(d.getUTCFullYear(), 0, 1));
            const weekNum = Math.ceil((((d - yearStart) / 86400000) + 1) / 7);
            return `S${weekNum}/${data.getFullYear()}`;
        } else if (granularidade === 'diario' || granularidade === 'diaria') {
            const dia = data.getDate().toString().padStart(2, '0');
            const mes = (data.getMonth() + 1).toString().padStart(2, '0');
            return `${dia}/${mes}/${data.getFullYear()}`;
        } else {
            return `${meses[data.getMonth()]}/${data.getFullYear()}`;
        }
    }

    // Construir arrays de dados
    const periodos = datasPrevisao.map(d => formatarPeriodo(d));
    const variacoes = previsoes.map((prev, i) => {
        const real = valoresReal[i] || 0;
        return real > 0 ? ((prev - real) / real * 100) : 0;
    });

    // Calcular totais
    const totalPrevisao = previsoes.reduce((sum, v) => sum + v, 0);
    const totalReal = valoresReal.slice(0, previsoes.length).reduce((sum, v) => sum + v, 0);
    const variacaoTotal = totalReal > 0 ? ((totalPrevisao - totalReal) / totalReal * 100) : 0;

    // Extrair filtros atuais
    const filtros = resultado.filtros || {
        loja: document.getElementById('lojaSelect')?.value || 'Todos',
        fornecedor: document.getElementById('fornecedorSelect')?.selectedOptions ?
            Array.from(document.getElementById('fornecedorSelect').selectedOptions).map(o => o.text).join(', ') : 'Todos',
        linha: document.getElementById('linhaSelect')?.selectedOptions ?
            Array.from(document.getElementById('linhaSelect').selectedOptions).map(o => o.text).join(', ') : 'Todos',
        sublinha: document.getElementById('sublinhaSelect')?.selectedOptions ?
            Array.from(document.getElementById('sublinhaSelect').selectedOptions).map(o => o.text).join(', ') : 'Todos',
        produto: document.getElementById('produtoSelect')?.selectedOptions ?
            Array.from(document.getElementById('produtoSelect').selectedOptions).map(o => o.text).join(', ') : 'Todos'
    };

    // Extrair dados por fornecedor (se houver múltiplos fornecedores)
    let fornecedoresData = [];
    if (isV2) {
        // Formato V2: agrupar itens por fornecedor
        const itensDetalhados = resultado.relatorio_detalhado?.itens || resultado.itens || dadosRelatorioDetalhado?.itens || [];
        const dadosPorFornecedor = {};

        itensDetalhados.forEach(item => {
            const fornecedor = item.nome_fornecedor || 'SEM FORNECEDOR';

            if (!dadosPorFornecedor[fornecedor]) {
                dadosPorFornecedor[fornecedor] = {
                    previsaoPorPeriodo: {},
                    totalPrevisao: 0,
                    totalAnoAnterior: 0
                };
            }

            if (item.previsao_por_periodo) {
                item.previsao_por_periodo.forEach(p => {
                    const periodoFormatado = formatarPeriodo(p.periodo);
                    if (!dadosPorFornecedor[fornecedor].previsaoPorPeriodo[periodoFormatado]) {
                        dadosPorFornecedor[fornecedor].previsaoPorPeriodo[periodoFormatado] = { previsao: 0, anoAnterior: 0 };
                    }
                    dadosPorFornecedor[fornecedor].previsaoPorPeriodo[periodoFormatado].previsao += (p.previsao || 0);
                    dadosPorFornecedor[fornecedor].previsaoPorPeriodo[periodoFormatado].anoAnterior += (p.ano_anterior || 0);
                });
            }

            dadosPorFornecedor[fornecedor].totalPrevisao += (item.demanda_prevista_total || 0);
            dadosPorFornecedor[fornecedor].totalAnoAnterior += (item.demanda_ano_anterior || 0);
        });

        // Converter para formato de exportação
        fornecedoresData = Object.entries(dadosPorFornecedor).map(([nome, dados]) => {
            const variacaoPercentual = dados.totalAnoAnterior > 0
                ? ((dados.totalPrevisao - dados.totalAnoAnterior) / dados.totalAnoAnterior * 100)
                : 0;

            // Converter previsaoPorPeriodo para formato esperado pelo backend
            const previsaoPorPeriodoFormatado = {};
            const anoAnteriorPorPeriodoFormatado = {};
            Object.entries(dados.previsaoPorPeriodo).forEach(([periodo, valores]) => {
                previsaoPorPeriodoFormatado[periodo] = valores.previsao;
                anoAnteriorPorPeriodoFormatado[periodo] = valores.anoAnterior;
            });

            return {
                nome_fornecedor: nome,
                previsao_total: dados.totalPrevisao,
                ano_anterior_total: dados.totalAnoAnterior,
                variacao_percentual: variacaoPercentual,
                previsao_por_periodo: previsaoPorPeriodoFormatado,
                ano_anterior_por_periodo: anoAnteriorPorPeriodoFormatado
            };
        });

        console.log('[exportarTabelaComparativa] Fornecedores V2:', fornecedoresData.length);
    } else if (resultado.comparacao_yoy_por_fornecedor && resultado.comparacao_yoy_por_fornecedor.length > 0) {
        // Formato com comparacao_yoy_por_fornecedor (backend já calculou agregação)
        fornecedoresData = resultado.comparacao_yoy_por_fornecedor.map(forn => {
            // Os períodos já vêm formatados do backend (Fev/2026, Mar/2026, etc.)
            // Apenas garantir que as chaves correspondem aos períodos do Excel
            const previsaoPorPeriodoFormatado = {};
            const anoAnteriorPorPeriodoFormatado = {};
            const previsaoPorPeriodoOriginal = forn.previsao_por_periodo || {};
            const anoAnteriorPorPeriodoOriginal = forn.ano_anterior_por_periodo || {};

            // Mapear períodos - tentar match direto primeiro, depois por formatação
            periodos.forEach((periodoFormatado, idx) => {
                // Tentar match direto (backend já formata igual ao frontend)
                if (previsaoPorPeriodoOriginal[periodoFormatado] !== undefined) {
                    previsaoPorPeriodoFormatado[periodoFormatado] = previsaoPorPeriodoOriginal[periodoFormatado];
                    anoAnteriorPorPeriodoFormatado[periodoFormatado] = anoAnteriorPorPeriodoOriginal[periodoFormatado] || 0;
                } else {
                    // Fallback: buscar pela data original
                    const dataOriginal = datasPrevisao[idx];
                    if (previsaoPorPeriodoOriginal[dataOriginal] !== undefined) {
                        previsaoPorPeriodoFormatado[periodoFormatado] = previsaoPorPeriodoOriginal[dataOriginal];
                        anoAnteriorPorPeriodoFormatado[periodoFormatado] = anoAnteriorPorPeriodoOriginal[dataOriginal] || 0;
                    } else {
                        // Último recurso: buscar por período que corresponda após formatação
                        const periodoExistente = Object.keys(previsaoPorPeriodoOriginal).find(p =>
                            formatarPeriodo(p) === periodoFormatado || p === periodoFormatado
                        );
                        if (periodoExistente) {
                            previsaoPorPeriodoFormatado[periodoFormatado] = previsaoPorPeriodoOriginal[periodoExistente];
                            anoAnteriorPorPeriodoFormatado[periodoFormatado] = anoAnteriorPorPeriodoOriginal[periodoExistente] || 0;
                        }
                    }
                }
            });

            console.log(`[exportarTabelaComparativa] Fornecedor ${forn.nome_fornecedor}:`, {
                previsao_por_periodo: previsaoPorPeriodoFormatado,
                ano_anterior_por_periodo: anoAnteriorPorPeriodoFormatado
            });

            return {
                nome_fornecedor: forn.nome_fornecedor || 'SEM NOME',
                previsao_total: forn.previsao_total || 0,
                ano_anterior_total: forn.ano_anterior_total || 0,
                variacao_percentual: forn.variacao_percentual || 0,
                previsao_por_periodo: previsaoPorPeriodoFormatado,
                ano_anterior_por_periodo: anoAnteriorPorPeriodoFormatado
            };
        });
        console.log('[exportarTabelaComparativa] Usando comparacao_yoy_por_fornecedor, fornecedores:', fornecedoresData.length);
    }

    // Montar dados para enviar ao servidor
    const dadosExportacao = {
        periodos: periodos,
        previsao: previsoes.map(v => Math.round(v)),
        real: valoresReal.slice(0, previsoes.length).map(v => Math.round(v)),
        variacao: variacoes,
        granularidade: granularidade,
        total_previsao: Math.round(totalPrevisao),
        total_real: Math.round(totalReal),
        variacao_total: variacaoTotal,
        filtros: filtros,
        fornecedores: fornecedoresData  // Dados por fornecedor
    };

    // Mostrar indicador de loading no botão
    const btn = document.getElementById('btnExportarTabelaComparativa');
    const textoOriginal = btn.innerHTML;
    btn.innerHTML = '<span>⏳</span> Exportando...';
    btn.disabled = true;

    // Fazer requisição POST para exportar
    fetch('/api/exportar_tabela_comparativa', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify(dadosExportacao)
    })
    .then(response => {
        if (!response.ok) {
            throw new Error('Erro ao gerar arquivo Excel');
        }
        return response.blob();
    })
    .then(blob => {
        // Criar link de download
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `tabela_comparativa_${granularidade}_${new Date().toISOString().slice(0,10)}.xlsx`;
        document.body.appendChild(a);
        a.click();
        window.URL.revokeObjectURL(url);
        a.remove();

        // Restaurar botão
        btn.innerHTML = textoOriginal;
        btn.disabled = false;
    })
    .catch(error => {
        console.error('Erro ao exportar:', error);
        alert('Erro ao exportar tabela comparativa: ' + error.message);

        // Restaurar botão
        btn.innerHTML = textoOriginal;
        btn.disabled = false;
    });
}

// =====================================================
// FUNÇÕES PARA FORMATO V2 (Bottom-Up)
// =====================================================

// Criar gráfico de previsão para formato V2
function criarGraficoPrevisaoV2(graficoData, granularidade = 'mensal') {
    const canvas = document.getElementById('previsaoChart');
    if (!canvas) {
        console.error('Canvas previsaoChart não encontrado');
        return;
    }

    const ctx = canvas.getContext('2d');

    // Destruir gráfico anterior se existir (verificar AMBAS as variáveis)
    if (window.previsaoChartInstance) {
        window.previsaoChartInstance.destroy();
        window.previsaoChartInstance = null;
    }
    if (previsaoChart) {
        previsaoChart.destroy();
        previsaoChart = null;
    }

    // Preparar dados
    const labels = graficoData.map(d => formatarLabelPeriodo(d.periodo, granularidade));
    const valores = graficoData.map(d => d.previsao);

    // Criar gráfico e armazenar em AMBAS as variáveis para consistência
    const novoGrafico = new Chart(ctx, {
        type: 'bar',
        data: {
            labels: labels,
            datasets: [{
                label: 'Previsão de Demanda',
                data: valores,
                backgroundColor: 'rgba(102, 126, 234, 0.7)',
                borderColor: 'rgba(102, 126, 234, 1)',
                borderWidth: 1
            }]
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
                            return `Previsão: ${formatarNumero(context.raw)} un.`;
                        }
                    }
                }
            },
            scales: {
                y: {
                    beginAtZero: true,
                    title: {
                        display: true,
                        text: 'Quantidade'
                    },
                    ticks: {
                        callback: function(value) {
                            return formatarNumero(value);
                        }
                    }
                },
                x: {
                    title: {
                        display: true,
                        text: 'Período'
                    }
                }
            }
        }
    });

    // Armazenar em AMBAS as variáveis para consistência
    window.previsaoChartInstance = novoGrafico;
    previsaoChart = novoGrafico;
}

// Preencher tabela comparativa para formato V2
// Agora mostra detalhes por fornecedor quando há mais de um
function preencherTabelaComparativaV2(graficoData, granularidade = 'mensal', itensDetalhados = null) {
    console.log('[preencherTabelaComparativaV2] Iniciando...');
    console.log('[preencherTabelaComparativaV2] graficoData:', graficoData?.length, 'pontos');
    console.log('[preencherTabelaComparativaV2] granularidade:', granularidade);
    console.log('[preencherTabelaComparativaV2] itensDetalhados recebidos:', itensDetalhados?.length || 0);

    const headerContainer = document.getElementById('tabelaComparativaHeader');
    const bodyContainer = document.getElementById('tabelaComparativaBody');

    if (!headerContainer || !bodyContainer) {
        console.warn('Containers da tabela comparativa não encontrados');
        return;
    }

    // Obter itens detalhados do dadosPrevisaoAtual se não fornecido
    if (!itensDetalhados || itensDetalhados.length === 0) {
        console.log('[preencherTabelaComparativaV2] Tentando obter itens de outras fontes...');
        if (dadosPrevisaoAtual) {
            itensDetalhados = dadosPrevisaoAtual.relatorio_detalhado?.itens ||
                              dadosPrevisaoAtual.itens ||
                              dadosRelatorioDetalhado?.itens || [];
            console.log('[preencherTabelaComparativaV2] Itens obtidos de backup:', itensDetalhados?.length || 0);
        }
    }

    // Agrupar dados por fornecedor
    const dadosPorFornecedor = {};
    const periodosSet = new Set();

    if (itensDetalhados && itensDetalhados.length > 0) {
        itensDetalhados.forEach(item => {
            const fornecedor = item.nome_fornecedor || 'SEM FORNECEDOR';

            if (!dadosPorFornecedor[fornecedor]) {
                dadosPorFornecedor[fornecedor] = {
                    previsaoPorPeriodo: {},
                    anoAnteriorPorPeriodo: {},
                    totalPrevisao: 0,
                    totalAnoAnterior: 0
                };
            }

            // Somar previsões por período
            if (item.previsao_por_periodo) {
                item.previsao_por_periodo.forEach(p => {
                    periodosSet.add(p.periodo);
                    if (!dadosPorFornecedor[fornecedor].previsaoPorPeriodo[p.periodo]) {
                        dadosPorFornecedor[fornecedor].previsaoPorPeriodo[p.periodo] = 0;
                        dadosPorFornecedor[fornecedor].anoAnteriorPorPeriodo[p.periodo] = 0;
                    }
                    dadosPorFornecedor[fornecedor].previsaoPorPeriodo[p.periodo] += (p.previsao || 0);
                    dadosPorFornecedor[fornecedor].anoAnteriorPorPeriodo[p.periodo] += (p.ano_anterior || 0);
                });
            }

            dadosPorFornecedor[fornecedor].totalPrevisao += (item.demanda_prevista_total || 0);
            dadosPorFornecedor[fornecedor].totalAnoAnterior += (item.demanda_ano_anterior || 0);
        });
    }

    // Ordenar períodos
    const periodos = Array.from(periodosSet).sort();
    const fornecedores = Object.keys(dadosPorFornecedor).sort();
    const temMultiplosFornecedores = fornecedores.length > 1;

    console.log('[preencherTabelaComparativaV2] Períodos encontrados:', periodos.length);
    console.log('[preencherTabelaComparativaV2] Fornecedores encontrados:', fornecedores);
    console.log('[preencherTabelaComparativaV2] temMultiplosFornecedores:', temMultiplosFornecedores);

    // Cabeçalho - estilo igual ao Excel
    const thStyle = 'padding: 10px; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; text-align: center; font-size: 0.85em; border: 1px solid #5a67d8;';
    const thStyleFirst = 'padding: 10px; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; text-align: left; font-size: 0.85em; border: 1px solid #5a67d8; min-width: 120px;';
    const thStyleTipo = 'padding: 10px; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; text-align: center; font-size: 0.85em; border: 1px solid #5a67d8; min-width: 80px;';

    let headerHtml = '<tr>';
    if (temMultiplosFornecedores) {
        headerHtml += `<th style="${thStyleFirst}">Fornecedor</th>`;
    }
    headerHtml += `<th style="${thStyleTipo}">Tipo</th>`;

    periodos.forEach(periodo => {
        const label = formatarLabelPeriodo(periodo, granularidade);
        headerHtml += `<th style="${thStyle}">${label}</th>`;
    });
    headerHtml += `<th style="${thStyle}">TOTAL</th>`;
    headerHtml += `<th style="${thStyle}">Var %</th>`;
    headerHtml += '</tr>';
    headerContainer.innerHTML = headerHtml;

    // Corpo - estilo igual ao Excel
    const tdStyle = 'padding: 8px; border: 1px solid #e2e8f0; text-align: right; font-size: 0.85em;';
    const tdStyleLeft = 'padding: 8px; border: 1px solid #e2e8f0; text-align: left; font-size: 0.85em; font-weight: 500;';
    const tdStyleTipo = 'padding: 8px; border: 1px solid #e2e8f0; text-align: center; font-size: 0.85em;';

    let bodyHtml = '';

    // Totais consolidados
    const totaisConsolidados = {
        previsaoPorPeriodo: {},
        anoAnteriorPorPeriodo: {},
        totalPrevisao: 0,
        totalAnoAnterior: 0
    };

    periodos.forEach(p => {
        totaisConsolidados.previsaoPorPeriodo[p] = 0;
        totaisConsolidados.anoAnteriorPorPeriodo[p] = 0;
    });

    if (temMultiplosFornecedores) {
        // Mostrar cada fornecedor com três linhas (Previsão, Ano Ant., Var %)
        fornecedores.forEach((fornecedor, idx) => {
            const dados = dadosPorFornecedor[fornecedor];
            const bgColor = idx % 2 === 0 ? '#ffffff' : '#f8fafc';

            // Calcular variação do fornecedor (total)
            const variacaoFornecedor = dados.totalAnoAnterior > 0
                ? ((dados.totalPrevisao - dados.totalAnoAnterior) / dados.totalAnoAnterior * 100)
                : 0;
            const corVariacao = variacaoFornecedor > 0 ? '#059669' : (variacaoFornecedor < 0 ? '#dc2626' : '#666');
            const sinalVariacao = variacaoFornecedor > 0 ? '+' : '';

            // Calcular variações por período
            const variacoesPorPeriodo = {};
            periodos.forEach(periodo => {
                const prev = dados.previsaoPorPeriodo[periodo] || 0;
                const aa = dados.anoAnteriorPorPeriodo[periodo] || 0;
                variacoesPorPeriodo[periodo] = aa > 0 ? ((prev - aa) / aa * 100) : 0;
            });

            // Linha de Previsão
            bodyHtml += `<tr style="background: ${bgColor};">`;
            bodyHtml += `<td style="${tdStyleLeft}" rowspan="3">${fornecedor}</td>`;
            bodyHtml += `<td style="${tdStyleTipo}; background: #f0fdf4;">Previsão</td>`;

            // Criar ID sanitizado do fornecedor para data-attributes
            const fornecedorId = fornecedor.replace(/[^a-zA-Z0-9]/g, '_');

            periodos.forEach(periodo => {
                const valor = dados.previsaoPorPeriodo[periodo] || 0;
                totaisConsolidados.previsaoPorPeriodo[periodo] += valor;
                bodyHtml += `<td data-comparativa-fornecedor="${fornecedorId}" data-comparativa-periodo="${periodo}" style="${tdStyle}">${formatNumber(valor)}</td>`;
            });

            totaisConsolidados.totalPrevisao += dados.totalPrevisao;
            bodyHtml += `<td data-comparativa-fornecedor-total="${fornecedorId}" style="${tdStyle} font-weight: 600; background: #f0fdf4;">${formatNumber(dados.totalPrevisao)}</td>`;
            bodyHtml += `<td style="${tdStyle} color: ${corVariacao}; font-weight: 600;" rowspan="3">${sinalVariacao}${variacaoFornecedor.toFixed(1)}%</td>`;
            bodyHtml += '</tr>';

            // Linha de Ano Anterior
            bodyHtml += `<tr style="background: ${bgColor};">`;
            bodyHtml += `<td style="${tdStyleTipo}; background: #fefce8;">Ano Ant.</td>`;

            periodos.forEach(periodo => {
                const valor = dados.anoAnteriorPorPeriodo[periodo] || 0;
                totaisConsolidados.anoAnteriorPorPeriodo[periodo] += valor;
                bodyHtml += `<td style="${tdStyle}">${formatNumber(valor)}</td>`;
            });

            totaisConsolidados.totalAnoAnterior += dados.totalAnoAnterior;
            bodyHtml += `<td style="${tdStyle} font-weight: 500;">${formatNumber(dados.totalAnoAnterior)}</td>`;
            bodyHtml += '</tr>';

            // Linha de Variação % por período
            bodyHtml += `<tr style="background: ${bgColor};">`;
            bodyHtml += `<td style="${tdStyleTipo}; background: #ede9fe; font-size: 0.8em;">Var %</td>`;

            periodos.forEach(periodo => {
                const varPct = variacoesPorPeriodo[periodo];
                const corVar = varPct > 0 ? '#059669' : (varPct < 0 ? '#dc2626' : '#666');
                const sinalVar = varPct > 0 ? '+' : '';
                bodyHtml += `<td style="${tdStyle} color: ${corVar}; font-size: 0.8em; font-weight: 500;">${sinalVar}${varPct.toFixed(1)}%</td>`;
            });

            // Célula vazia para o total (já temos a variação total no rowspan)
            bodyHtml += `<td style="${tdStyle} background: #ede9fe;"></td>`;
            bodyHtml += '</tr>';
        });

        // Linha de TOTAL CONSOLIDADO
        const variacaoTotal = totaisConsolidados.totalAnoAnterior > 0
            ? ((totaisConsolidados.totalPrevisao - totaisConsolidados.totalAnoAnterior) / totaisConsolidados.totalAnoAnterior * 100)
            : 0;
        const corVarTotal = variacaoTotal > 0 ? '#059669' : (variacaoTotal < 0 ? '#dc2626' : '#666');
        const sinalVarTotal = variacaoTotal > 0 ? '+' : '';

        // Calcular variações por período para o total consolidado
        const variacoesTotalPorPeriodo = {};
        periodos.forEach(periodo => {
            const prev = totaisConsolidados.previsaoPorPeriodo[periodo] || 0;
            const aa = totaisConsolidados.anoAnteriorPorPeriodo[periodo] || 0;
            variacoesTotalPorPeriodo[periodo] = aa > 0 ? ((prev - aa) / aa * 100) : 0;
        });

        // Previsão Total
        bodyHtml += `<tr style="background: linear-gradient(135deg, #1e3a5f 0%, #2d4a6f 100%); color: white; font-weight: bold;">`;
        bodyHtml += `<td style="padding: 10px; border: 1px solid #1e3a5f; text-align: left;" rowspan="3">TOTAL CONSOLIDADO</td>`;
        bodyHtml += `<td style="padding: 8px; border: 1px solid #1e3a5f; text-align: center; background: rgba(16, 185, 129, 0.2);">Previsão</td>`;

        periodos.forEach(periodo => {
            bodyHtml += `<td data-comparativa-consolidado="true" data-comparativa-periodo="${periodo}" style="padding: 8px; border: 1px solid #1e3a5f; text-align: right;">${formatNumber(totaisConsolidados.previsaoPorPeriodo[periodo])}</td>`;
        });

        bodyHtml += `<td id="totalPrevisaoComparativaConsolidado" style="padding: 8px; border: 1px solid #1e3a5f; text-align: right; background: rgba(16, 185, 129, 0.2);">${formatNumber(totaisConsolidados.totalPrevisao)}</td>`;
        bodyHtml += `<td style="padding: 8px; border: 1px solid #1e3a5f; text-align: right; color: ${variacaoTotal >= 0 ? '#86efac' : '#fca5a5'};" rowspan="3">${sinalVarTotal}${variacaoTotal.toFixed(1)}%</td>`;
        bodyHtml += '</tr>';

        // Ano Anterior Total
        bodyHtml += `<tr style="background: linear-gradient(135deg, #1e3a5f 0%, #2d4a6f 100%); color: white; font-weight: bold;">`;
        bodyHtml += `<td style="padding: 8px; border: 1px solid #1e3a5f; text-align: center; background: rgba(251, 191, 36, 0.2);">Ano Ant.</td>`;

        periodos.forEach(periodo => {
            bodyHtml += `<td style="padding: 8px; border: 1px solid #1e3a5f; text-align: right;">${formatNumber(totaisConsolidados.anoAnteriorPorPeriodo[periodo])}</td>`;
        });

        bodyHtml += `<td style="padding: 8px; border: 1px solid #1e3a5f; text-align: right;">${formatNumber(totaisConsolidados.totalAnoAnterior)}</td>`;
        bodyHtml += '</tr>';

        // Variação % por período - Total Consolidado
        bodyHtml += `<tr style="background: linear-gradient(135deg, #1e3a5f 0%, #2d4a6f 100%); color: white; font-weight: bold;">`;
        bodyHtml += `<td style="padding: 8px; border: 1px solid #1e3a5f; text-align: center; background: rgba(139, 92, 246, 0.3); font-size: 0.85em;">Var %</td>`;

        periodos.forEach(periodo => {
            const varPct = variacoesTotalPorPeriodo[periodo];
            const corVarPeriodo = varPct >= 0 ? '#86efac' : '#fca5a5';
            const sinalVarPeriodo = varPct > 0 ? '+' : '';
            bodyHtml += `<td style="padding: 8px; border: 1px solid #1e3a5f; text-align: right; color: ${corVarPeriodo}; font-size: 0.85em;">${sinalVarPeriodo}${varPct.toFixed(1)}%</td>`;
        });

        bodyHtml += `<td style="padding: 8px; border: 1px solid #1e3a5f; text-align: right; background: rgba(139, 92, 246, 0.3);"></td>`;
        bodyHtml += '</tr>';

    } else {
        // Formato original para um único fornecedor (ou sem itens detalhados)
        // Linha de Previsão
        bodyHtml += '<tr>';
        bodyHtml += `<td style="${tdStyleTipo}; background: #f0fdf4; font-weight: 500;">Previsão</td>`;

        let totalPrevisao = 0;
        let totalAnoAnterior = 0;

        if (periodos.length > 0 && fornecedores.length > 0) {
            const dados = dadosPorFornecedor[fornecedores[0]];
            periodos.forEach(periodo => {
                const valor = dados.previsaoPorPeriodo[periodo] || 0;
                totalPrevisao += valor;
                bodyHtml += `<td data-comparativa-periodo="${periodo}" style="${tdStyle}">${formatNumber(valor)}</td>`;
            });
            totalPrevisao = dados.totalPrevisao;
            totalAnoAnterior = dados.totalAnoAnterior;

            bodyHtml += `<td id="totalPrevisaoComparativa" style="${tdStyle} font-weight: 600; background: #f0fdf4;">${formatNumber(totalPrevisao)}</td>`;

            const variacao = totalAnoAnterior > 0 ? ((totalPrevisao - totalAnoAnterior) / totalAnoAnterior * 100) : 0;
            const corVar = variacao > 0 ? '#059669' : (variacao < 0 ? '#dc2626' : '#666');
            const sinalVar = variacao > 0 ? '+' : '';
            bodyHtml += `<td style="${tdStyle} color: ${corVar}; font-weight: 600;" rowspan="2">${sinalVar}${variacao.toFixed(1)}%</td>`;
            bodyHtml += '</tr>';

            // Linha de Ano Anterior
            bodyHtml += '<tr>';
            bodyHtml += `<td style="${tdStyleTipo}; background: #fefce8; font-weight: 500;">Ano Ant.</td>`;

            periodos.forEach(periodo => {
                const valor = dados.anoAnteriorPorPeriodo[periodo] || 0;
                bodyHtml += `<td style="${tdStyle}">${formatNumber(valor)}</td>`;
            });

            bodyHtml += `<td style="${tdStyle} font-weight: 500;">${formatNumber(totalAnoAnterior)}</td>`;
            bodyHtml += '</tr>';
        } else {
            // Fallback usando graficoData
            graficoData.forEach(d => {
                totalPrevisao += d.previsao || 0;
                bodyHtml += `<td style="${tdStyle}">${formatNumber(d.previsao || 0)}</td>`;
            });
            bodyHtml += `<td style="${tdStyle} font-weight: 600;">${formatNumber(totalPrevisao)}</td>`;
            bodyHtml += `<td style="${tdStyle}">-</td>`;
            bodyHtml += '</tr>';
        }
    }

    bodyContainer.innerHTML = bodyHtml;
}

// Exibir itens detalhados para formato V2
function exibirItensPrevisaoV2(itens) {
    const container = document.getElementById('fornecedorItemBody');
    if (!container) {
        console.warn('Container fornecedorItemBody não encontrado');
        return;
    }

    let html = `
        <tr style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white;">
            <th style="padding: 10px;">Código</th>
            <th style="padding: 10px;">Descrição</th>
            <th style="padding: 10px;">Fornecedor</th>
            <th style="padding: 10px; text-align: right;">Demanda/Dia</th>
            <th style="padding: 10px; text-align: right;">Demanda Período</th>
        </tr>
    `;

    itens.forEach(item => {
        html += `
            <tr style="border-bottom: 1px solid #eee;">
                <td style="padding: 8px;">${item.cod_produto}</td>
                <td style="padding: 8px;">${item.descricao || '-'}</td>
                <td style="padding: 8px;">${item.fornecedor || '-'}</td>
                <td style="padding: 8px; text-align: right;">${item.demanda_diaria?.toFixed(2) || '0.00'}</td>
                <td style="padding: 8px; text-align: right;">${formatarNumero(item.demanda_periodo || 0)}</td>
            </tr>
        `;
    });

    container.innerHTML = html;
}

// Formatar label de período
function formatarLabelPeriodo(periodo, granularidade) {
    if (!periodo) return '-';

    if (granularidade === 'mensal') {
        // Formato: "2026-02" -> "Fev/26"
        const meses = ['Jan', 'Fev', 'Mar', 'Abr', 'Mai', 'Jun', 'Jul', 'Ago', 'Set', 'Out', 'Nov', 'Dez'];
        const partes = periodo.split('-');
        if (partes.length >= 2) {
            const mes = parseInt(partes[1]) - 1;
            const ano = partes[0].substring(2);
            return `${meses[mes]}/${ano}`;
        }
    } else if (granularidade === 'semanal') {
        // Formato: "2026-S05" -> "S05/26"
        return periodo.replace(/(\d{4})-S(\d+)/, 'S$2/$1').replace(/\/20/, '/');
    }

    return periodo;
}

// Formatar número com separadores de milhares
function formatarNumero(valor) {
    if (valor === null || valor === undefined || isNaN(valor)) return '0';
    return Math.round(valor).toLocaleString('pt-BR');
}

// =====================================================
// FIM FUNÇÕES V2
// =====================================================

// Criar gráfico de previsão simplificado com 3 linhas + ano anterior
function criarGraficoPrevisao(historicoBase, historicoTeste, modelos, melhorModelo, granularidade = 'mensal', anoAnterior = null) {
    const canvas = document.getElementById('previsaoChart');
    if (!canvas) {
        console.error('Canvas previsaoChart não encontrado');
        return;
    }

    const ctx = canvas.getContext('2d');

    // Destruir gráfico anterior se existir (verificar AMBAS as variáveis)
    if (window.previsaoChartInstance) {
        window.previsaoChartInstance.destroy();
        window.previsaoChartInstance = null;
    }
    if (previsaoChart) {
        previsaoChart.destroy();
        previsaoChart = null;
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
        label: 'Base Histórica (75%)',
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

    // Armazenar também em window.previsaoChartInstance para consistência
    window.previsaoChartInstance = previsaoChart;
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

        // Obter valores dos multi-selects (retorna array vazio se todos selecionados)
        const lojas = MultiSelect.getSelected('loja_banco');
        const fornecedores = MultiSelect.getSelected('fornecedor_banco');
        const linhas = MultiSelect.getSelected('linha_banco');
        const sublinhas = MultiSelect.getSelected('sublinha_banco');
        const produtos = MultiSelect.getSelected('produto_banco');

        const dados = {
            loja: lojas.length > 0 ? lojas : 'TODAS',
            fornecedor: fornecedores.length > 0 ? fornecedores : 'TODOS',
            linha: linhas.length > 0 ? linhas : 'TODAS',
            sublinha: sublinhas.length > 0 ? sublinhas : 'TODAS',
            produto: produtos.length > 0 ? produtos : 'TODOS',
            granularidade: document.getElementById('granularidade_banco').value,
            ...dadosPeriodo  // Inclui os dados de período específicos
        };

        console.log('=== DADOS ENVIADOS ===');
        console.log('Granularidade:', dados.granularidade);
        console.log('Tipo período:', dados.tipo_periodo);
        console.log('Lojas:', dados.loja);
        console.log('Fornecedores:', dados.fornecedor);
        console.log('Linhas:', dados.linha);
        console.log('Sublinhas:', dados.sublinha);
        console.log('Produtos:', dados.produto);
        console.log('Dados completos:', JSON.stringify(dados, null, 2));

        // Enviar requisição (Bottom-Up com sazonalidade, tendência e limitadores)
        // Timeout de 10 minutos para permitir processamento de grandes volumes
        const controller = new AbortController();
        const timeoutId = setTimeout(() => controller.abort(), 600000); // 10 minutos

        let response;
        try {
            response = await fetch('/api/gerar_previsao_banco', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify(dados),
                signal: controller.signal
            });
        } catch (fetchError) {
            clearTimeout(timeoutId);
            if (fetchError.name === 'AbortError') {
                throw new Error('Tempo limite excedido (10 min). Tente filtrar menos itens.');
            }
            throw fetchError;
        }
        clearTimeout(timeoutId);

        const resultado = await response.json();

        clearInterval(progressInterval);
        progressFill.style.width = '100%';
        progressText.textContent = 'Concluído!';

        setTimeout(() => {
            document.getElementById('progress').style.display = 'none';
        }, 500);

        if (response.status === 200 && (resultado.success || resultado.sucesso || resultado.resultado?.success || resultado.resultado?.sucesso)) {
            console.log('Resultado recebido:', resultado);

            // Mostrar resultados
            document.getElementById('results').style.display = 'block';

            // Detectar formato da resposta (V2 Bottom-Up ou V1 legado)
            // V2 usa grafico_data direto (formato simplificado com barras)
            // V1 usa modelos com historico_base, historico_teste, futuro (gráfico de linhas com WMAPE/BIAS)
            const isV2Format = resultado.grafico_data || resultado.resultado?.grafico_data;

            console.log('=== DEBUG FORMATO ===');
            console.log('isV2Format:', isV2Format);
            console.log('resultado.grafico_data:', resultado.grafico_data);
            console.log('resultado.modelos:', resultado.modelos ? 'presente' : 'ausente');

            if (isV2Format) {
                // ========== FORMATO V2 (Bottom-Up com grafico_data) ==========
                const dados = resultado.resultado || resultado;
                const graficoData = dados.grafico_data || [];
                const totalItens = dados.total_itens || 0;
                const demandaTotal = dados.demanda_total || 0;
                const granularidade = dados.granularidade || 'mensal';

                console.log('V2 - graficoData:', graficoData);

                // KPIs para V2
                document.getElementById('kpi_wmape').textContent = `${totalItens} itens`;
                document.getElementById('kpi_bias').textContent = '-';
                document.getElementById('kpi_variacao').textContent = formatarNumero(demandaTotal);

                // Criar gráfico simples para V2
                criarGraficoPrevisaoV2(graficoData, granularidade);

                // Obter itens detalhados para tabela comparativa
                const itensDetalhados = dados.relatorio_detalhado?.itens || dados.itens || [];

                // Preencher tabela comparativa V2
                preencherTabelaComparativaV2(graficoData, granularidade, itensDetalhados);

                // Exibir itens detalhados se disponível
                if (itensDetalhados.length > 0) {
                    exibirItensPrevisaoV2(itensDetalhados);
                }

                // Desabilitar download temporariamente
                const downloadBtn = document.getElementById('downloadBtn');
                if (downloadBtn) {
                    downloadBtn.disabled = true;
                    downloadBtn.style.opacity = '0.5';
                    downloadBtn.style.pointerEvents = 'none';
                    downloadBtn.style.cursor = 'not-allowed';
                }

                armazenarDadosPrevisao(dados);

            } else {
                // ========== FORMATO V1 (Legado) ==========
                // Obter métricas do melhor modelo
                const melhorModelo = resultado.melhor_modelo;

                // V2 tem métricas dentro de modelos[modelo].metricas, V1 tem em resultado.metricas[modelo]
                const modeloData = resultado.modelos?.[melhorModelo] || {};
                const metricasMelhor = modeloData.metricas || resultado.metricas?.[melhorModelo] || {};

                // Usar variação calculada no backend (consistente com tabela comparativa)
                const variacaoDemanda = resultado.variacao_demanda_pct ?? 0;

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

                // Preencher tabela comparativa (usar V2 com detalhes por fornecedor se disponível)
                const itensDetalhados = resultado.relatorio_detalhado?.itens || [];
                const granularidade = resultado.granularidade || 'mensal';

                // Construir grafico_data para a tabela comparativa V2
                const datasPrevisao = modeloData?.futuro?.datas || [];
                const valoresPrevisao = modeloData?.futuro?.valores || [];
                const valoresAnoAnt = resultado.ano_anterior?.valores || [];
                const graficoDataParaTabela = datasPrevisao.map((d, i) => ({
                    periodo: d,
                    previsao: valoresPrevisao[i] || 0,
                    ano_anterior: valoresAnoAnt[i] || 0
                }));

                // Usar a função V2 que suporta detalhes por fornecedor
                preencherTabelaComparativaV2(graficoDataParaTabela, granularidade, itensDetalhados);

                // Exibir relatório detalhado por fornecedor/item (se houver dados)
                if (resultado.relatorio_detalhado) {
                    console.log('[Debug] relatorio_detalhado encontrado com', resultado.relatorio_detalhado.itens?.length || 0, 'itens');
                    exibirRelatorioDetalhado(resultado.relatorio_detalhado);
                } else {
                    console.log('[Debug] relatorio_detalhado NAO encontrado no resultado');
                }

                // Armazenar dados para validação de demanda (v6.0)
                armazenarDadosPrevisao(resultado);

                // Configurar botão de download Excel
                const downloadBtn = document.getElementById('downloadBtn');
                if (downloadBtn && resultado.relatorio_detalhado && resultado.relatorio_detalhado.itens && resultado.relatorio_detalhado.itens.length > 0) {
                    // Habilitar botão de download (agora usa onclick para exportar via API)
                    downloadBtn.disabled = false;
                    downloadBtn.style.opacity = '1';
                    downloadBtn.style.pointerEvents = 'auto';
                    downloadBtn.style.cursor = 'pointer';
                    downloadBtn.title = 'Clique para exportar o relatório detalhado de itens';
                } else if (downloadBtn) {
                    // Se não houver itens, desabilitar o botão visualmente
                    downloadBtn.disabled = true;
                    downloadBtn.style.opacity = '0.5';
                    downloadBtn.style.pointerEvents = 'none';
                    downloadBtn.style.cursor = 'not-allowed';
                    downloadBtn.title = 'Gere uma previsão para habilitar o download';
                }

                // Configurar botão de salvar demanda pré-calculada (v5.7)
                atualizarBotaoSalvarDemanda();
            }

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
        document.getElementById('relatorioCustoSection').style.display = 'none';
        return;
    }

    // Armazenar dados globalmente para filtros
    dadosRelatorioDetalhado = dados;

    // Mostrar seções
    document.getElementById('relatorioDetalhadoSection').style.display = 'block';
    document.getElementById('relatorioCustoSection').style.display = 'block';

    // Popular filtro de fornecedores
    popularFiltroFornecedores(dados.itens);

    // Renderizar tabelas
    renderizarTabelaRelatorioDetalhado(dados.itens, dados.periodos_previsao, dados.granularidade);
    renderizarTabelaRelatorioCusto(dados.itens, dados.periodos_previsao, dados.granularidade);

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

    // Criar cabeçalho - Código e Descrição congelados
    let headerHtml = '<tr style="background: linear-gradient(135deg, #10b981 0%, #059669 100%); color: white; font-size: 0.8em;">';
    headerHtml += '<th style="padding: 8px; text-align: left; border: 1px solid #ddd; position: sticky; left: 0; background: linear-gradient(135deg, #10b981 0%, #059669 100%); z-index: 12; min-width: 70px; width: 70px;">Código</th>';
    headerHtml += '<th style="padding: 8px; text-align: left; border: 1px solid #ddd; position: sticky; left: 70px; background: linear-gradient(135deg, #10b981 0%, #059669 100%); z-index: 12; min-width: 220px; width: 220px;">Descrição</th>';

    // Colunas de períodos
    periodos.forEach(periodo => {
        const nomePeriodo = formatarPeriodoHeader(periodo);
        headerHtml += `<th style="padding: 6px; text-align: center; border: 1px solid #ddd; min-width: 60px;">${nomePeriodo}</th>`;
    });

    headerHtml += '<th style="padding: 8px; text-align: center; border: 1px solid #ddd; background: #047857; min-width: 70px;">Total Prev.</th>';
    headerHtml += '<th style="padding: 8px; text-align: center; border: 1px solid #ddd; min-width: 70px;">Ano Ant.</th>';
    headerHtml += '<th style="padding: 8px; text-align: center; border: 1px solid #ddd; min-width: 60px;">Var. %</th>';
    headerHtml += '<th style="padding: 8px; text-align: center; border: 1px solid #ddd; min-width: 50px;">Alerta</th>';
    headerHtml += '<th style="padding: 8px; text-align: center; border: 1px solid #ddd; min-width: 70px;">Situação</th>';
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
        // Array para armazenar os labels de período (string) dos itens
        let periodosStringPorIdx = new Array(numColunasPeriodos).fill(null);

        itensFornecedor.forEach(item => {
            totalPrevFornecedor += item.demanda_prevista_total || 0;
            totalAnoAntFornecedor += item.demanda_ano_anterior || 0;

            // Somar previsões por período
            if (item.previsao_por_periodo) {
                item.previsao_por_periodo.forEach((p, idx) => {
                    if (idx < numColunasPeriodos) {
                        totaisPorPeriodo[idx] += p.previsao || 0;
                        // Capturar o período string do item (mesmo formato usado nas células dos itens)
                        if (!periodosStringPorIdx[idx] && p.periodo) {
                            periodosStringPorIdx[idx] = p.periodo;
                        }
                    }
                });
            }
        });

        const variacaoFornecedor = totalAnoAntFornecedor > 0
            ? ((totalPrevFornecedor - totalAnoAntFornecedor) / totalAnoAntFornecedor * 100)
            : 0;

        // Criar ID seguro para o fornecedor (remover caracteres especiais)
        const fornecedorId = fornecedor.replace(/[^a-zA-Z0-9]/g, '_');

        // Linha do fornecedor (cabeçalho do grupo - colapsável) - duas colunas congeladas
        bodyHtml += `<tr class="linha-fornecedor" data-fornecedor="${fornecedorId}" onclick="toggleFornecedor('${fornecedorId}')" style="background: #e0f2f1; cursor: pointer; font-weight: bold;">`;
        bodyHtml += `<td style="padding: 10px; border: 1px solid #ddd; position: sticky; left: 0; background: #e0f2f1; z-index: 6; width: 70px;">`;
        bodyHtml += `<span class="toggle-icon" id="toggle-${fornecedorId}">▼</span>`;
        bodyHtml += `</td>`;
        bodyHtml += `<td style="padding: 10px; border: 1px solid #ddd; position: sticky; left: 70px; background: #e0f2f1; z-index: 6; width: 220px;">`;
        bodyHtml += `${fornecedor} (${itensFornecedor.length} itens)`;
        bodyHtml += `</td>`;

        // Totais por período do fornecedor
        // Usar o período string capturado dos itens para manter consistência com as células dos itens
        totaisPorPeriodo.forEach((total, idx) => {
            const periodoLabel = periodosStringPorIdx[idx] || (periodos && periodos[idx] ? periodos[idx].periodo : `periodo_${idx}`);
            bodyHtml += `<td data-fornecedor-total="${fornecedorId}" data-periodo="${periodoLabel}" style="padding: 6px; text-align: center; border: 1px solid #ddd; background: #e0f2f1; font-weight: bold;">${formatNumber(total)}</td>`;
        });

        bodyHtml += `<td data-fornecedor-total-geral="${fornecedorId}" style="padding: 8px; text-align: center; border: 1px solid #ddd; background: #b2dfdb; font-weight: bold;">${formatNumber(totalPrevFornecedor)}</td>`;
        bodyHtml += `<td style="padding: 8px; text-align: center; border: 1px solid #ddd; background: #e0f2f1;">${formatNumber(totalAnoAntFornecedor)}</td>`;

        const corVariacao = variacaoFornecedor > 0 ? '#059669' : (variacaoFornecedor < 0 ? '#dc2626' : '#666');
        const sinalVariacao = variacaoFornecedor > 0 ? '+' : '';
        bodyHtml += `<td style="padding: 8px; text-align: center; border: 1px solid #ddd; background: #e0f2f1; color: ${corVariacao}; font-weight: bold;">${sinalVariacao}${variacaoFornecedor.toFixed(1)}%</td>`;

        bodyHtml += `<td style="padding: 8px; text-align: center; border: 1px solid #ddd; background: #e0f2f1;">-</td>`;
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

        // Função para verificar se item é Fora de Linha ou Encomenda
        function isSitCompraExcluido(sitCompra) {
            return sitCompra === 'FL' || sitCompra === 'EN';
        }

        // Ordenar itens por código decrescente (maior para menor)
        const itensOrdenados = [...itensFornecedor].sort((a, b) => {
            const codA = parseInt(a.cod_produto) || 0;
            const codB = parseInt(b.cod_produto) || 0;
            return codB - codA;
        });

        // Linhas dos itens (inicialmente visíveis) - com onclick para drill-down
        itensOrdenados.forEach(item => {
            // Escapar aspas na descrição para evitar problemas no onclick
            const descricaoEscapada = (item.descricao || '').replace(/'/g, "\\'").replace(/"/g, '&quot;');
            const fornecedorEscapado = (item.nome_fornecedor || '').replace(/'/g, "\\'").replace(/"/g, '&quot;');

            bodyHtml += `<tr class="linha-item" data-fornecedor="${fornecedorId}" data-cod-produto="${item.cod_produto}" onclick="selecionarItemDrillDown('${item.cod_produto}', '${descricaoEscapada}', '${fornecedorEscapado}')" style="background: white;" title="Clique para analisar e ajustar este item">`;
            bodyHtml += `<td style="padding: 6px 8px; border: 1px solid #ddd; position: sticky; left: 0; background: white; z-index: 5; font-size: 0.85em; min-width: 70px; width: 70px;">${item.cod_produto}</td>`;
            bodyHtml += `<td style="padding: 6px 8px; border: 1px solid #ddd; position: sticky; left: 70px; background: white; z-index: 5; font-size: 0.85em; min-width: 220px; width: 220px; max-width: 220px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;" title="${item.descricao}">${item.descricao}</td>`;

            // Valores por período
            if (item.previsao_por_periodo && item.previsao_por_periodo.length > 0) {
                item.previsao_por_periodo.forEach((p, idx) => {
                    if (idx < numColunasPeriodos) {
                        const bgAjuste = p.ajuste_manual ? 'background: #fef3c7;' : '';
                        const titleAjuste = p.ajuste_manual ? ` title="Ajuste manual salvo"` : '';
                        bodyHtml += `<td data-cod-produto="${item.cod_produto}" data-periodo="${p.periodo}"${titleAjuste} style="padding: 6px; text-align: center; border: 1px solid #ddd; font-size: 0.85em; ${bgAjuste}">${formatNumber(p.previsao || 0)}</td>`;
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
            bodyHtml += `<td data-item-total="${item.cod_produto}" style="padding: 6px; text-align: center; border: 1px solid #ddd; font-weight: 500; background: #f0fdf4;">${formatNumber(item.demanda_prevista_total || 0)}</td>`;

            // Ano anterior
            bodyHtml += `<td style="padding: 6px; text-align: center; border: 1px solid #ddd;">${formatNumber(item.demanda_ano_anterior || 0)}</td>`;

            // Variação
            const varItem = item.variacao_percentual || 0;
            const corVarItem = varItem > 0 ? '#059669' : (varItem < 0 ? '#dc2626' : '#666');
            const sinalVarItem = varItem > 0 ? '+' : '';
            bodyHtml += `<td style="padding: 6px; text-align: center; border: 1px solid #ddd; color: ${corVarItem}; font-weight: 500;">${sinalVarItem}${varItem.toFixed(1)}%</td>`;

            // Alerta (V50: baseado em CV - Coeficiente de Variação)
            const cvPct = item.cv ? (item.cv * 100).toFixed(1) : '-';
            const cvTooltip = item.cv ? `CV: ${cvPct}% | Desvio mensal: ${formatNumber(item.desvio_padrao || 0)} un` : 'Sem dados';
            bodyHtml += `<td title="${cvTooltip}" style="padding: 6px; text-align: center; border: 1px solid #ddd; font-size: 1.2em; cursor: help;">${item.sinal_emoji || '⚪'}</td>`;

            // Situação de Compra
            const sitCompra = item.sit_compra || '';
            const sitCompraDesc = item.sit_compra_descricao || '';
            let sitCompraHtml = '-';
            let sitCompraBg = '';

            if (sitCompra) {
                // Cores por situação
                const coresSitCompra = {
                    'FL': { bg: '#ffebee', color: '#c62828', label: 'Fora de Linha' },
                    'EN': { bg: '#fff8e1', color: '#f57f17', label: 'Encomenda' },
                    'NC': { bg: '#ffebee', color: '#c62828', label: 'Não Comprar' },
                    'CO': { bg: '#e3f2fd', color: '#1565c0', label: 'Compra Oport.' },
                    'FF': { bg: '#f5f5f5', color: '#616161', label: 'Falta Fornec.' }
                };
                const config = coresSitCompra[sitCompra] || { bg: '#f5f5f5', color: '#666', label: sitCompraDesc || sitCompra };
                sitCompraHtml = `<span style="background: ${config.bg}; color: ${config.color}; padding: 2px 6px; border-radius: 4px; font-size: 0.75em; font-weight: 500;" title="${sitCompraDesc}">${sitCompra}</span>`;
                sitCompraBg = sitCompra === 'FL' || sitCompra === 'EN' ? 'background: #fafafa;' : '';
            }
            bodyHtml += `<td style="padding: 6px; text-align: center; border: 1px solid #ddd; ${sitCompraBg}">${sitCompraHtml}</td>`;

            // Método
            bodyHtml += `<td style="padding: 6px; text-align: center; border: 1px solid #ddd; font-size: 0.8em;">${item.metodo_estatistico || '-'}</td>`;

            bodyHtml += `</tr>`;
        });
    });

    tbody.innerHTML = bodyHtml;
}

// Formatar valor como moeda BRL
function formatCurrency(valor) {
    if (valor === 0 || valor === null || valor === undefined) return 'R$ 0,00';
    return valor.toLocaleString('pt-BR', { style: 'currency', currency: 'BRL', minimumFractionDigits: 2, maximumFractionDigits: 2 });
}

// Renderizar tabela espelhada de custo (CUE)
function renderizarTabelaRelatorioCusto(itens, periodos, granularidade) {
    const thead = document.getElementById('relatorioCustoHeader');
    const tbody = document.getElementById('relatorioCustoBody');

    if (!thead || !tbody) return;

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
            const mesIdx = periodo.mes - 1;
            return `${mesesNomes[mesIdx]}/${periodo.ano}`;
        }
    }

    // Cabecalho azul
    let headerHtml = '<tr style="background: linear-gradient(135deg, #3b82f6 0%, #1d4ed8 100%); color: white; font-size: 0.8em;">';
    headerHtml += '<th style="padding: 8px; text-align: left; border: 1px solid #93c5fd; position: sticky; left: 0; background: linear-gradient(135deg, #3b82f6 0%, #1d4ed8 100%); z-index: 12; min-width: 70px; width: 70px;">Código</th>';
    headerHtml += '<th style="padding: 8px; text-align: left; border: 1px solid #93c5fd; position: sticky; left: 70px; background: linear-gradient(135deg, #3b82f6 0%, #1d4ed8 100%); z-index: 12; min-width: 220px; width: 220px;">Descrição</th>';

    periodos.forEach(periodo => {
        const nomePeriodo = formatarPeriodoHeader(periodo);
        headerHtml += `<th style="padding: 6px; text-align: center; border: 1px solid #93c5fd; min-width: 90px;">${nomePeriodo}</th>`;
    });

    headerHtml += '<th style="padding: 8px; text-align: center; border: 1px solid #93c5fd; background: #1e40af; min-width: 100px;">Total Prev. R$</th>';
    headerHtml += '<th style="padding: 8px; text-align: center; border: 1px solid #93c5fd; min-width: 80px;">CUE Unit.</th>';
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

    const fornecedoresOrdenados = Object.keys(itensPorFornecedor).sort();
    const numColunasPeriodos = periodos.length;

    let bodyHtml = '';
    let custoTotalGeral = 0;
    let custoAnoAntGeral = 0;

    fornecedoresOrdenados.forEach(fornecedor => {
        const itensFornecedor = itensPorFornecedor[fornecedor];
        const fornecedorId = fornecedor.replace(/[^a-zA-Z0-9]/g, '_');

        let custoTotalFornecedor = 0;
        let totaisCustoPorPeriodo = new Array(numColunasPeriodos).fill(0);

        itensFornecedor.forEach(item => {
            const cue = item.cue || 0;
            custoTotalFornecedor += (item.demanda_prevista_total || 0) * cue;

            if (item.previsao_por_periodo) {
                item.previsao_por_periodo.forEach((p, idx) => {
                    if (idx < numColunasPeriodos) {
                        totaisCustoPorPeriodo[idx] += (p.previsao || 0) * cue;
                    }
                });
            }
        });

        custoTotalGeral += custoTotalFornecedor;

        // Linha do fornecedor
        bodyHtml += `<tr class="linha-fornecedor-custo" data-fornecedor-custo="${fornecedorId}" onclick="toggleFornecedorCusto('${fornecedorId}')" style="background: #dbeafe; cursor: pointer; font-weight: bold;">`;
        bodyHtml += `<td style="padding: 10px; border: 1px solid #93c5fd; position: sticky; left: 0; background: #dbeafe; z-index: 6; width: 70px;">`;
        bodyHtml += `<span class="toggle-icon-custo" id="toggle-custo-${fornecedorId}">▼</span>`;
        bodyHtml += `</td>`;
        bodyHtml += `<td style="padding: 10px; border: 1px solid #93c5fd; position: sticky; left: 70px; background: #dbeafe; z-index: 6; width: 220px;">`;
        bodyHtml += `${fornecedor} (${itensFornecedor.length} itens)`;
        bodyHtml += `</td>`;

        totaisCustoPorPeriodo.forEach((total, idx) => {
            bodyHtml += `<td data-custo-fornecedor-total="${fornecedorId}" data-custo-periodo-idx="${idx}" style="padding: 6px; text-align: center; border: 1px solid #93c5fd; background: #dbeafe; font-weight: bold; font-size: 0.85em;">${formatCurrency(total)}</td>`;
        });

        bodyHtml += `<td data-custo-fornecedor-total-geral="${fornecedorId}" style="padding: 8px; text-align: center; border: 1px solid #93c5fd; background: #bfdbfe; font-weight: bold;">${formatCurrency(custoTotalFornecedor)}</td>`;
        bodyHtml += `<td style="padding: 8px; text-align: center; border: 1px solid #93c5fd; background: #dbeafe;">-</td>`;
        bodyHtml += `</tr>`;

        // Itens do fornecedor - ordenados por código decrescente (mesma ordem da tabela de quantidade)
        const itensOrdenadosCusto = [...itensFornecedor].sort((a, b) => {
            const codA = parseInt(a.cod_produto) || 0;
            const codB = parseInt(b.cod_produto) || 0;
            return codB - codA;
        });

        itensOrdenadosCusto.forEach(item => {
            const cue = item.cue || 0;
            const custoTotalItem = (item.demanda_prevista_total || 0) * cue;

            bodyHtml += `<tr class="linha-item-custo" data-fornecedor-custo="${fornecedorId}" style="background: white;">`;
            bodyHtml += `<td style="padding: 6px 8px; border: 1px solid #ddd; position: sticky; left: 0; background: white; z-index: 5; font-size: 0.85em; min-width: 70px; width: 70px;">${item.cod_produto}</td>`;
            bodyHtml += `<td style="padding: 6px 8px; border: 1px solid #ddd; position: sticky; left: 70px; background: white; z-index: 5; font-size: 0.85em; min-width: 220px; width: 220px; max-width: 220px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;" title="${item.descricao}">${item.descricao}</td>`;

            if (item.previsao_por_periodo && item.previsao_por_periodo.length > 0) {
                item.previsao_por_periodo.forEach((p, idx) => {
                    if (idx < numColunasPeriodos) {
                        const valorCusto = (p.previsao || 0) * cue;
                        const bgCustoAjuste = p.ajuste_manual ? 'background: #fef3c7;' : '';
                        bodyHtml += `<td data-custo-cod-produto="${item.cod_produto}" data-custo-periodo="${p.periodo}" style="padding: 6px; text-align: center; border: 1px solid #ddd; font-size: 0.85em; ${bgCustoAjuste}">${cue > 0 ? formatCurrency(valorCusto) : '-'}</td>`;
                    }
                });
                for (let i = item.previsao_por_periodo.length; i < numColunasPeriodos; i++) {
                    bodyHtml += `<td style="padding: 6px; text-align: center; border: 1px solid #ddd; color: #999;">-</td>`;
                }
            } else {
                for (let i = 0; i < numColunasPeriodos; i++) {
                    bodyHtml += `<td style="padding: 6px; text-align: center; border: 1px solid #ddd; color: #999;">-</td>`;
                }
            }

            // Total previsto em R$
            bodyHtml += `<td data-custo-item-total="${item.cod_produto}" style="padding: 6px; text-align: center; border: 1px solid #ddd; font-weight: 500; background: #eff6ff;">${cue > 0 ? formatCurrency(custoTotalItem) : '-'}</td>`;

            // CUE unitario
            bodyHtml += `<td style="padding: 6px; text-align: center; border: 1px solid #ddd; font-size: 0.8em; color: #6b7280;">${cue > 0 ? formatCurrency(cue) : '-'}</td>`;

            bodyHtml += `</tr>`;
        });
    });

    tbody.innerHTML = bodyHtml;

    // Atualizar resumo
    const resumoSection = document.getElementById('resumoRelatorioCusto');
    if (resumoSection) {
        resumoSection.style.display = 'block';
        document.getElementById('resumoCustoTotal').textContent = formatCurrency(custoTotalGeral);
    }
}

// Toggle para expandir/recolher fornecedor na tabela de custo
function toggleFornecedorCusto(fornecedorId) {
    const linhasItem = document.querySelectorAll(`.linha-item-custo[data-fornecedor-custo="${fornecedorId}"]`);
    const toggleIcon = document.getElementById(`toggle-custo-${fornecedorId}`);

    const estaVisivel = linhasItem[0]?.style.display !== 'none';

    linhasItem.forEach(linha => {
        linha.style.display = estaVisivel ? 'none' : '';
    });

    if (toggleIcon) {
        toggleIcon.textContent = estaVisivel ? '►' : '▼';
    }
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

    // Re-renderizar tabelas com itens filtrados
    renderizarTabelaRelatorioDetalhado(
        itensFiltrados,
        dadosRelatorioDetalhado.periodos_previsao,
        dadosRelatorioDetalhado.granularidade
    );
    renderizarTabelaRelatorioCusto(
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
    // Usar MultiSelect API em vez de getElementById
    const fornecedores = MultiSelect.getSelected('fornecedor_banco');

    if (!fornecedores || fornecedores.length === 0) {
        console.log('[Validacao] Nenhum fornecedor selecionado');
        return { valido: false, fornecedor: null, cnpj: null };
    }

    // Válido apenas se houver exatamente um fornecedor selecionado
    // e não for "TODOS" ou "Carregando..."
    const valor = fornecedores[0];
    const valido = fornecedores.length === 1 && valor && valor !== 'TODOS' && valor !== 'Carregando...';
    console.log('[Validacao] Fornecedor verificado:', valor, '- Valido:', valido, '- Total selecionados:', fornecedores.length);

    // Tentar extrair CNPJ do fornecedor (se estiver no formato "NOME - CNPJ" ou se for só CNPJ)
    let cnpj = null;
    if (valido && valor) {
        // Verificar se o valor é um CNPJ puro (só números)
        const cnpjMatch = valor.match(/(\d{14})/);
        if (cnpjMatch) {
            cnpj = cnpjMatch[1];
        } else {
            // Se não encontrou, usar o próprio valor (pode ser nome do fornecedor)
            cnpj = valor;
        }
    }

    return { valido: valido, fornecedor: valido ? valor : null, cnpj: cnpj };
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
    console.log('[armazenarDadosPrevisao] ====== DADOS ARMAZENADOS ======');
    console.log('[armazenarDadosPrevisao] resultado:', resultado);
    console.log('[armazenarDadosPrevisao] resultado.grafico_data:', resultado?.grafico_data);
    console.log('[armazenarDadosPrevisao] resultado.resultado:', resultado?.resultado);
    console.log('[armazenarDadosPrevisao] resultado.resultado?.grafico_data:', resultado?.resultado?.grafico_data);
    console.log('[armazenarDadosPrevisao] Tem relatorio_detalhado:', !!(resultado && resultado.relatorio_detalhado));

    // Para formato V1 (legado com modelos), armazenar dados do gráfico para restauração
    if (resultado && resultado.modelos && resultado.melhor_modelo) {
        const melhorModelo = resultado.melhor_modelo;
        const modeloData = resultado.modelos[melhorModelo] || {};

        // Obter dados do histórico (base e teste)
        let historicoBase = resultado.historico_base;
        let historicoTeste = resultado.historico_teste;

        if (!historicoBase && resultado.serie_temporal) {
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

        // Armazenar em formato que restaurarGraficoAgregado espera
        dadosPrevisaoAtual.grafico = {
            historico_base: historicoBase,
            historico_teste: historicoTeste,
            modelos: resultado.modelos,
            melhor_modelo: melhorModelo,
            ano_anterior: resultado.ano_anterior
        };
        console.log('[armazenarDadosPrevisao] Dados do gráfico V1 armazenados para restauração');
    }

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

// =====================================================
// SISTEMA DE DRILL-DOWN: ANÁLISE INDIVIDUAL DE ITEM
// =====================================================

// Variável global para armazenar item selecionado para drill-down
let itemSelecionadoDrillDown = null;
let ajustesPendentes = {}; // {cod_produto: {periodo: valor_ajustado, ...}}

// Função para selecionar um item e mostrar detalhes
function selecionarItemDrillDown(codProduto, descricao, fornecedor) {
    // Se clicar no mesmo item, desselecionar (toggle)
    if (itemSelecionadoDrillDown && itemSelecionadoDrillDown.cod_produto === codProduto) {
        desselecionarItemDrillDown();
        return;
    }

    // Armazenar item selecionado
    itemSelecionadoDrillDown = {
        cod_produto: codProduto,
        descricao: descricao,
        nome_fornecedor: fornecedor
    };

    // Buscar dados do item no relatório detalhado
    if (dadosRelatorioDetalhado && dadosRelatorioDetalhado.itens) {
        // Tentar encontrar por cod_produto (string)
        let itemDados = dadosRelatorioDetalhado.itens.find(i => i.cod_produto === codProduto);

        // Se não encontrou, tentar comparação menos estrita (trim e string)
        if (!itemDados) {
            itemDados = dadosRelatorioDetalhado.itens.find(i => String(i.cod_produto).trim() === String(codProduto).trim());
        }

        if (itemDados) {
            itemSelecionadoDrillDown.dados = itemDados;
        }
    }

    // Atualizar interface visual
    atualizarVisuaisDrillDown();

    // Atualizar gráfico para mostrar item individual
    atualizarGraficoDrillDown();

    // Mostrar painel de edição
    mostrarPainelEdicaoItem();
}

// Função para desselecionar item
function desselecionarItemDrillDown() {
    itemSelecionadoDrillDown = null;

    // Remover destaque visual de todas as linhas
    document.querySelectorAll('.linha-item-selecionada').forEach(el => {
        el.classList.remove('linha-item-selecionada');
    });

    // Esconder painel de edição
    esconderPainelEdicaoItem();

    // Restaurar gráfico agregado
    restaurarGraficoAgregado();
}

// Atualizar visuais de seleção na tabela
function atualizarVisuaisDrillDown() {
    // Remover destaque de todas as linhas
    document.querySelectorAll('.linha-item-selecionada').forEach(el => {
        el.classList.remove('linha-item-selecionada');
    });

    // Adicionar destaque na linha do item selecionado usando data-attribute
    if (itemSelecionadoDrillDown) {
        const linha = document.querySelector(`.linha-item[data-cod-produto="${itemSelecionadoDrillDown.cod_produto}"]`);
        if (linha) {
            linha.classList.add('linha-item-selecionada');
        }
    }
}

// Atualizar gráfico para mostrar item individual com histórico de 2 anos
async function atualizarGraficoDrillDown() {
    if (!itemSelecionadoDrillDown || !itemSelecionadoDrillDown.dados) {
        return;
    }

    const item = itemSelecionadoDrillDown.dados;
    const granularidade = dadosRelatorioDetalhado?.granularidade || 'mensal';

    const canvas = document.getElementById('previsaoChart');
    if (!canvas) {
        return;
    }

    const ctx = canvas.getContext('2d');

    // Destruir gráfico anterior se existir (verificar AMBAS as variáveis)
    if (window.previsaoChartInstance) {
        window.previsaoChartInstance.destroy();
        window.previsaoChartInstance = null;
    }
    if (previsaoChart) {
        previsaoChart.destroy();
        previsaoChart = null;
    }

    // Buscar histórico de 2 anos da API
    let historicoItem = [];
    try {
        const url = `/api/historico_item?cod_produto=${item.cod_produto}&granularidade=${granularidade}`;
        const response = await fetch(url);
        const result = await response.json();
        if (result.success) {
            historicoItem = result.historico || [];
        }
    } catch (error) {
        // Continuar sem histórico em caso de erro
    }

    // Preparar dados da previsão
    const previsaoPorPeriodo = item.previsao_por_periodo || [];
    const temAjustes = ajustesPendentes[item.cod_produto] !== undefined;

    // Função para formatar label do período
    const meses = ['Jan', 'Fev', 'Mar', 'Abr', 'Mai', 'Jun', 'Jul', 'Ago', 'Set', 'Out', 'Nov', 'Dez'];
    function formatarLabel(periodo, gran) {
        if (gran === 'mensal') {
            const partes = periodo.split('-');
            if (partes.length >= 2) {
                const mes = parseInt(partes[1]) - 1;
                const ano = partes[0].substring(2);
                return `${meses[mes]}/${ano}`;
            }
        } else if (gran === 'semanal') {
            return periodo.replace(/(\d{4})-S(\d+)/, 'S$2/$1').replace(/\/20/, '/');
        }
        return periodo;
    }

    // Criar timeline completa: histórico + previsão
    const labels = [];
    const valoresHistorico = [];
    const valoresPrevisao = [];
    const valoresAjustados = [];

    // Adicionar histórico
    historicoItem.forEach(h => {
        labels.push(formatarLabel(h.periodo, granularidade));
        valoresHistorico.push(h.valor);
        valoresPrevisao.push(null);
        valoresAjustados.push(null);
    });

    // Adicionar previsão (continuando após o histórico)
    previsaoPorPeriodo.forEach(p => {
        labels.push(formatarLabel(p.periodo, granularidade));
        valoresHistorico.push(null);
        valoresPrevisao.push(p.previsao || 0);

        // Verificar se há ajuste para este período
        if (temAjustes && ajustesPendentes[item.cod_produto][p.periodo] !== undefined) {
            valoresAjustados.push(ajustesPendentes[item.cod_produto][p.periodo]);
        } else {
            valoresAjustados.push(null);
        }
    });

    // Criar datasets
    const datasets = [
        {
            label: 'Histórico Real',
            data: valoresHistorico,
            borderColor: '#3b82f6',
            backgroundColor: 'rgba(59, 130, 246, 0.1)',
            borderWidth: 2,
            fill: false,
            tension: 0.1,
            pointRadius: 3,
            spanGaps: false
        },
        {
            label: 'Previsão',
            data: valoresPrevisao,
            borderColor: '#8b5cf6',
            backgroundColor: 'rgba(139, 92, 246, 0.1)',
            borderWidth: 2,
            fill: false,
            tension: 0.1,
            pointRadius: 4,
            spanGaps: false
        }
    ];

    // Adicionar linha de ajustes se houver
    if (temAjustes) {
        datasets.push({
            label: 'Valor Ajustado',
            data: valoresAjustados,
            borderColor: '#10b981',
            backgroundColor: 'rgba(16, 185, 129, 0.2)',
            borderWidth: 3,
            fill: false,
            tension: 0.1,
            pointRadius: 6,
            pointStyle: 'rectRot',
            spanGaps: false
        });
    }

    // Calcular escala Y considerando todos os valores
    const todosValores = [
        ...valoresHistorico.filter(v => v !== null),
        ...valoresPrevisao.filter(v => v !== null),
        ...valoresAjustados.filter(v => v !== null)
    ];
    const valorMinimo = todosValores.length > 0 ? Math.min(...todosValores.filter(v => v > 0)) : 0;
    const valorMaximo = todosValores.length > 0 ? Math.max(...todosValores) : 100;
    const amplitude = valorMaximo - valorMinimo;
    const yMin = Math.max(0, valorMinimo - (amplitude * 0.1));
    const yMax = valorMaximo + (amplitude * 0.1);

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
                title: {
                    display: true,
                    text: `${item.cod_produto} - ${item.descricao.substring(0, 50)}${item.descricao.length > 50 ? '...' : ''}`,
                    font: { size: 14, weight: 'bold' },
                    color: '#374151'
                },
                legend: {
                    display: true,
                    position: 'top',
                    labels: { usePointStyle: true, padding: 15 }
                },
                tooltip: {
                    mode: 'index',
                    intersect: false,
                    callbacks: {
                        label: function(context) {
                            let label = context.dataset.label || '';
                            if (label) label += ': ';
                            if (context.parsed.y !== null) {
                                label += formatNumber(context.parsed.y) + ' un';
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
                    title: { display: true, text: 'Quantidade' },
                    ticks: {
                        callback: function(value) { return formatNumber(value); }
                    }
                },
                x: {
                    title: { display: true, text: 'Período' },
                    ticks: { maxRotation: 45, minRotation: 45 }
                }
            }
        }
    });

    // Armazenar também em window.previsaoChartInstance para consistência
    window.previsaoChartInstance = previsaoChart;

    // Atualizar título do card do gráfico
    atualizarTituloGraficoDrillDown();
}

// Atualizar título do gráfico para indicar drill-down
function atualizarTituloGraficoDrillDown() {
    const tituloGrafico = document.querySelector('.card-compact h3');
    if (tituloGrafico && itemSelecionadoDrillDown) {
        tituloGrafico.innerHTML = `
            <span style="display: flex; align-items: center; justify-content: space-between; width: 100%;">
                <span>📊 Item: ${itemSelecionadoDrillDown.cod_produto}</span>
                <button onclick="desselecionarItemDrillDown()" style="background: rgba(255,255,255,0.2); border: none; color: white; padding: 4px 12px; border-radius: 4px; cursor: pointer; font-size: 0.85em;">
                    ✕ Voltar Visão Geral
                </button>
            </span>
        `;
    }
}

// Restaurar gráfico agregado
function restaurarGraficoAgregado() {
    console.log('[restaurarGraficoAgregado] Iniciando restauração do gráfico agregado...');
    console.log('[restaurarGraficoAgregado] dadosPrevisaoAtual:', dadosPrevisaoAtual);

    // Restaurar título do gráfico
    const cardGrafico = document.querySelector('.card-compact');
    if (cardGrafico) {
        const h3 = cardGrafico.querySelector('h3');
        if (h3) {
            h3.innerHTML = '📈 Histórico e Previsão de Demanda';
        }
    }

    // Verificar formato V2 (Bottom-Up) - tentar múltiplos caminhos
    // O grafico_data pode estar em:
    // - dadosPrevisaoAtual.grafico_data (direto)
    // - dadosPrevisaoAtual.resultado.grafico_data (aninhado)
    let graficoData = null;
    let granularidade = 'mensal';

    if (dadosPrevisaoAtual) {
        // Tentar caminho direto primeiro
        if (dadosPrevisaoAtual.grafico_data && dadosPrevisaoAtual.grafico_data.length > 0) {
            graficoData = dadosPrevisaoAtual.grafico_data;
            granularidade = dadosPrevisaoAtual.granularidade || 'mensal';
            console.log('[restaurarGraficoAgregado] grafico_data encontrado em dadosPrevisaoAtual.grafico_data');
        }
        // Tentar caminho aninhado
        else if (dadosPrevisaoAtual.resultado?.grafico_data && dadosPrevisaoAtual.resultado.grafico_data.length > 0) {
            graficoData = dadosPrevisaoAtual.resultado.grafico_data;
            granularidade = dadosPrevisaoAtual.resultado.granularidade || 'mensal';
            console.log('[restaurarGraficoAgregado] grafico_data encontrado em dadosPrevisaoAtual.resultado.grafico_data');
        }
    }

    console.log('[restaurarGraficoAgregado] graficoData final:', graficoData ? `${graficoData.length} pontos` : 'NÃO ENCONTRADO');

    if (graficoData && graficoData.length > 0) {
        // Formato V2 - recriar gráfico com grafico_data
        console.log('[restaurarGraficoAgregado] Restaurando gráfico V2 com granularidade:', granularidade);
        criarGraficoPrevisaoV2(graficoData, granularidade);
        return;
    }

    // Se temos dados salvos no formato V1, recriar gráfico agregado
    if (dadosPrevisaoAtual && dadosPrevisaoAtual.grafico) {
        console.log('[restaurarGraficoAgregado] Restaurando gráfico V1');
        const g = dadosPrevisaoAtual.grafico;
        criarGraficoPrevisao(
            g.historico_base,
            g.historico_teste,
            g.modelos,
            g.melhor_modelo,
            dadosPrevisaoAtual.granularidade,
            g.ano_anterior
        );
    } else {
        console.log('[restaurarGraficoAgregado] NENHUM dado de gráfico encontrado para restaurar!');
    }
}

// Mostrar painel de edição do item
function mostrarPainelEdicaoItem() {
    if (!itemSelecionadoDrillDown || !itemSelecionadoDrillDown.dados) return;

    const item = itemSelecionadoDrillDown.dados;

    // Verificar se o painel já existe
    let painel = document.getElementById('painelEdicaoItem');
    if (!painel) {
        // Criar painel após a tabela comparativa
        const tabelaComparativa = document.querySelector('#tabelaComparativa')?.closest('.card-compact');
        if (tabelaComparativa) {
            const painelHtml = `
                <div id="painelEdicaoItem" class="card-compact" style="margin-top: 20px; border: 2px solid #8b5cf6; display: none;">
                    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 15px;">
                        <h3 style="color: #8b5cf6; margin: 0;">
                            ✏️ Ajuste Manual de Previsão
                        </h3>
                        <div>
                            <button onclick="aplicarAjustePercentual()" style="padding: 6px 12px; background: #f3f4f6; border: 1px solid #d1d5db; border-radius: 5px; cursor: pointer; margin-right: 8px; font-size: 0.85em;">
                                📊 Aplicar %
                            </button>
                            <button onclick="copiarAnoAnterior()" style="padding: 6px 12px; background: #f3f4f6; border: 1px solid #d1d5db; border-radius: 5px; cursor: pointer; margin-right: 8px; font-size: 0.85em;">
                                📋 Copiar Ano Ant.
                            </button>
                            <button onclick="resetarAjustesItem()" style="padding: 6px 12px; background: #fee2e2; color: #dc2626; border: none; border-radius: 5px; cursor: pointer; font-size: 0.85em;">
                                🔄 Resetar
                            </button>
                        </div>
                    </div>
                    <div id="infoItemSelecionado" style="background: #f8f9fa; padding: 12px; border-radius: 6px; margin-bottom: 15px;">
                        <!-- Info do item -->
                    </div>
                    <div style="overflow-x: auto;">
                        <table id="tabelaAjusteItem" style="width: 100%; border-collapse: collapse; font-size: 0.85em;">
                            <thead>
                                <tr style="background: linear-gradient(135deg, #8b5cf6 0%, #7c3aed 100%); color: white;">
                                    <th style="padding: 10px; text-align: left;">Período</th>
                                    <th style="padding: 10px; text-align: right;">Previsão</th>
                                    <th style="padding: 10px; text-align: right;">Ano Ant.</th>
                                    <th style="padding: 10px; text-align: center;">Ajustado</th>
                                    <th style="padding: 10px; text-align: center;">Ações</th>
                                </tr>
                            </thead>
                            <tbody id="tabelaAjusteItemBody">
                                <!-- Preenchido dinamicamente -->
                            </tbody>
                        </table>
                    </div>
                    <div style="margin-top: 15px; display: flex; justify-content: flex-end; gap: 10px;">
                        <button onclick="salvarAjustesItem()" style="padding: 10px 20px; background: linear-gradient(135deg, #10b981 0%, #059669 100%); color: white; border: none; border-radius: 6px; cursor: pointer; font-weight: 500;">
                            💾 Salvar Ajustes
                        </button>
                        <button onclick="desselecionarItemDrillDown()" style="padding: 10px 20px; background: linear-gradient(135deg, #6366f1 0%, #4f46e5 100%); color: white; border: none; border-radius: 6px; cursor: pointer; font-weight: 500;">
                            🚪 Sair
                        </button>
                    </div>
                </div>
            `;
            tabelaComparativa.insertAdjacentHTML('afterend', painelHtml);
            painel = document.getElementById('painelEdicaoItem');
        }
    }

    if (!painel) return;

    // Preencher info do item
    const infoItem = document.getElementById('infoItemSelecionado');
    infoItem.innerHTML = `
        <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 15px;">
            <div>
                <div style="font-size: 0.8em; color: #666;">Código</div>
                <div style="font-weight: bold;">${item.cod_produto}</div>
            </div>
            <div>
                <div style="font-size: 0.8em; color: #666;">Descrição</div>
                <div style="font-weight: 500;">${item.descricao}</div>
            </div>
            <div>
                <div style="font-size: 0.8em; color: #666;">Fornecedor</div>
                <div>${item.nome_fornecedor || '-'}</div>
            </div>
            <div>
                <div style="font-size: 0.8em; color: #666;">Método</div>
                <div>${item.metodo_estatistico || '-'}</div>
            </div>
            <div>
                <div style="font-size: 0.8em; color: #666;">Previsão Total</div>
                <div style="font-weight: bold; color: #8b5cf6;">${formatNumber(item.demanda_prevista_total || 0)} un</div>
            </div>
            <div>
                <div style="font-size: 0.8em; color: #666;">Variação</div>
                <div style="font-weight: bold; color: ${(item.variacao_percentual || 0) >= 0 ? '#059669' : '#dc2626'};">
                    ${(item.variacao_percentual || 0) > 0 ? '+' : ''}${(item.variacao_percentual || 0).toFixed(1)}%
                </div>
            </div>
        </div>
    `;

    // Preencher tabela de ajustes
    const tbody = document.getElementById('tabelaAjusteItemBody');
    const previsaoPorPeriodo = item.previsao_por_periodo || [];

    let html = '';
    previsaoPorPeriodo.forEach((p, idx) => {
        const temAjuste = ajustesPendentes[item.cod_produto] && ajustesPendentes[item.cod_produto][p.periodo] !== undefined;
        const valorAjustado = temAjuste ? ajustesPendentes[item.cod_produto][p.periodo] : p.previsao;

        // Formatar label do período
        let labelPeriodo = p.periodo;
        if (dadosRelatorioDetalhado && dadosRelatorioDetalhado.granularidade === 'mensal') {
            const meses = ['Jan', 'Fev', 'Mar', 'Abr', 'Mai', 'Jun', 'Jul', 'Ago', 'Set', 'Out', 'Nov', 'Dez'];
            const partes = p.periodo.split('-');
            if (partes.length >= 2) {
                const mes = parseInt(partes[1]) - 1;
                labelPeriodo = `${meses[mes]}/${partes[0]}`;
            }
        } else if (dadosRelatorioDetalhado && dadosRelatorioDetalhado.granularidade === 'semanal') {
            labelPeriodo = p.periodo.replace(/(\d{4})-S(\d+)/, 'Sem $2/$1');
        }

        html += `
            <tr style="border-bottom: 1px solid #e5e7eb; ${temAjuste ? 'background: #f0fdf4;' : ''}">
                <td style="padding: 10px;">${labelPeriodo}</td>
                <td style="padding: 10px; text-align: right; color: #6b7280;">${formatNumber(p.previsao || 0)}</td>
                <td style="padding: 10px; text-align: right; color: #f97316;">${formatNumber(p.ano_anterior || 0)}</td>
                <td style="padding: 10px; text-align: center;">
                    <input type="number" class="input-ajuste-periodo"
                        data-periodo="${p.periodo}"
                        data-original="${p.previsao || 0}"
                        data-ano-anterior="${p.ano_anterior || 0}"
                        value="${Math.round(valorAjustado)}"
                        onchange="registrarAjustePeriodo('${item.cod_produto}', '${p.periodo}', this.value)"
                        style="width: 80px; padding: 6px; border: 1px solid ${temAjuste ? '#10b981' : '#d1d5db'}; border-radius: 4px; text-align: right; ${temAjuste ? 'background: #ecfdf5; font-weight: bold;' : ''}">
                </td>
                <td style="padding: 10px; text-align: center;">
                    <button onclick="resetarPeriodo('${item.cod_produto}', '${p.periodo}', ${p.previsao || 0})"
                        style="padding: 4px 8px; background: #f3f4f6; border: 1px solid #d1d5db; border-radius: 4px; cursor: pointer; font-size: 0.8em;"
                        title="Resetar para valor original">
                        🔄
                    </button>
                    <button onclick="copiarAnoAnteriorPeriodo('${item.cod_produto}', '${p.periodo}', ${p.ano_anterior || 0})"
                        style="padding: 4px 8px; background: #fff7ed; border: 1px solid #fed7aa; border-radius: 4px; cursor: pointer; font-size: 0.8em; margin-left: 4px;"
                        title="Usar valor do ano anterior">
                        📋
                    </button>
                </td>
            </tr>
        `;
    });

    tbody.innerHTML = html;

    // Mostrar painel
    painel.style.display = 'block';

    // Scroll suave até o painel
    painel.scrollIntoView({ behavior: 'smooth', block: 'start' });
}

// Esconder painel de edição
function esconderPainelEdicaoItem() {
    const painel = document.getElementById('painelEdicaoItem');
    if (painel) {
        painel.style.display = 'none';
    }
}

// Registrar ajuste em um período específico
function registrarAjustePeriodo(codProduto, periodo, valor) {
    const valorNum = parseFloat(valor);
    if (isNaN(valorNum)) return;

    // Inicializar objeto de ajustes para o produto se não existir
    if (!ajustesPendentes[codProduto]) {
        ajustesPendentes[codProduto] = {};
    }

    // Buscar valor original
    const item = dadosRelatorioDetalhado?.itens?.find(i => i.cod_produto === codProduto);
    const periodoData = item?.previsao_por_periodo?.find(p => p.periodo === periodo);
    const valorOriginal = periodoData?.previsao || 0;

    // Se valor é igual ao original, remover ajuste
    if (Math.round(valorNum) === Math.round(valorOriginal)) {
        delete ajustesPendentes[codProduto][periodo];
        if (Object.keys(ajustesPendentes[codProduto]).length === 0) {
            delete ajustesPendentes[codProduto];
        }
    } else {
        ajustesPendentes[codProduto][periodo] = valorNum;
    }

    // Atualizar visual do input
    const input = document.querySelector(`.input-ajuste-periodo[data-periodo="${periodo}"]`);
    if (input) {
        const temAjuste = ajustesPendentes[codProduto] && ajustesPendentes[codProduto][periodo] !== undefined;
        input.style.borderColor = temAjuste ? '#10b981' : '#d1d5db';
        input.style.background = temAjuste ? '#ecfdf5' : 'white';
        input.style.fontWeight = temAjuste ? 'bold' : 'normal';

        // Atualizar linha da tabela
        const tr = input.closest('tr');
        if (tr) {
            tr.style.background = temAjuste ? '#f0fdf4' : '';
        }
    }

    // Atualizar gráfico
    atualizarGraficoDrillDown();

    // Atualizar indicador visual na tabela principal
    atualizarIndicadorAjusteTabela(codProduto);
}

// Resetar período para valor original
function resetarPeriodo(codProduto, periodo, valorOriginal) {
    const input = document.querySelector(`.input-ajuste-periodo[data-periodo="${periodo}"]`);
    if (input) {
        input.value = Math.round(valorOriginal);
        registrarAjustePeriodo(codProduto, periodo, valorOriginal);
    }
}

// Copiar valor do ano anterior para um período
function copiarAnoAnteriorPeriodo(codProduto, periodo, valorAnoAnterior) {
    const input = document.querySelector(`.input-ajuste-periodo[data-periodo="${periodo}"]`);
    if (input) {
        input.value = Math.round(valorAnoAnterior);
        registrarAjustePeriodo(codProduto, periodo, valorAnoAnterior);
    }
}

// Resetar todos os ajustes do item
function resetarAjustesItem() {
    if (!itemSelecionadoDrillDown) return;

    const codProduto = itemSelecionadoDrillDown.cod_produto;
    delete ajustesPendentes[codProduto];

    // Atualizar painel
    mostrarPainelEdicaoItem();

    // Atualizar gráfico
    atualizarGraficoDrillDown();

    // Atualizar indicador na tabela
    atualizarIndicadorAjusteTabela(codProduto);
}

// Copiar todos os valores do ano anterior
function copiarAnoAnterior() {
    if (!itemSelecionadoDrillDown || !itemSelecionadoDrillDown.dados) return;

    const item = itemSelecionadoDrillDown.dados;
    const previsaoPorPeriodo = item.previsao_por_periodo || [];

    previsaoPorPeriodo.forEach(p => {
        if (p.ano_anterior > 0) {
            copiarAnoAnteriorPeriodo(item.cod_produto, p.periodo, p.ano_anterior);
        }
    });
}

// Aplicar percentual de ajuste
function aplicarAjustePercentual() {
    const percentual = prompt('Digite o percentual de ajuste (ex: 10 para +10%, -20 para -20%):', '0');
    if (percentual === null) return;

    const pct = parseFloat(percentual);
    if (isNaN(pct)) {
        alert('Valor inválido. Use números (ex: 10, -20)');
        return;
    }

    if (!itemSelecionadoDrillDown || !itemSelecionadoDrillDown.dados) return;

    const item = itemSelecionadoDrillDown.dados;
    const previsaoPorPeriodo = item.previsao_por_periodo || [];

    previsaoPorPeriodo.forEach(p => {
        const novoValor = (p.previsao || 0) * (1 + pct / 100);
        const input = document.querySelector(`.input-ajuste-periodo[data-periodo="${p.periodo}"]`);
        if (input) {
            input.value = Math.round(novoValor);
            registrarAjustePeriodo(item.cod_produto, p.periodo, novoValor);
        }
    });
}

// Atualizar indicador de ajuste na tabela principal
function atualizarIndicadorAjusteTabela(codProduto) {
    const temAjustes = ajustesPendentes[codProduto] && Object.keys(ajustesPendentes[codProduto]).length > 0;

    // Encontrar linha do item na tabela
    const linhas = document.querySelectorAll('.linha-item');
    linhas.forEach(linha => {
        const codProdutoCell = linha.querySelector('td:first-child');
        if (codProdutoCell && codProdutoCell.textContent.trim() === codProduto) {
            // Verificar se já tem indicador
            let indicador = linha.querySelector('.indicador-ajuste');
            if (temAjustes) {
                if (!indicador) {
                    indicador = document.createElement('span');
                    indicador.className = 'indicador-ajuste';
                    indicador.style.cssText = 'display: inline-block; width: 8px; height: 8px; background: #10b981; border-radius: 50%; margin-left: 6px; vertical-align: middle;';
                    indicador.title = 'Item com ajustes pendentes';
                    codProdutoCell.appendChild(indicador);
                }
            } else if (indicador) {
                indicador.remove();
            }
        }
    });
}

// Salvar ajustes do item no banco de dados
async function salvarAjustesItem() {
    if (!itemSelecionadoDrillDown) {
        alert('Nenhum item selecionado');
        return;
    }

    const codProduto = itemSelecionadoDrillDown.cod_produto;
    const ajustesItem = ajustesPendentes[codProduto];

    if (!ajustesItem || Object.keys(ajustesItem).length === 0) {
        alert('Nenhum ajuste para salvar');
        return;
    }

    // Preparar dados para enviar
    const item = itemSelecionadoDrillDown.dados;
    const ajustesParaSalvar = [];

    Object.entries(ajustesItem).forEach(([periodo, valorAjustado]) => {
        const periodoData = item.previsao_por_periodo?.find(p => p.periodo === periodo);
        const valorOriginal = periodoData?.previsao || 0;

        ajustesParaSalvar.push({
            cod_produto: codProduto,
            cod_fornecedor: item.cod_fornecedor || null,
            nome_fornecedor: item.nome_fornecedor || null,
            periodo: periodo,
            granularidade: dadosRelatorioDetalhado?.granularidade || 'mensal',
            valor_original: valorOriginal,
            valor_ajustado: valorAjustado,
            metodo_estatistico: item.metodo_estatistico || null
        });
    });

    // Enviar para API
    try {
        const response = await fetch('/api/ajuste_previsao/salvar', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                ajustes: ajustesParaSalvar,
                motivo: prompt('Informe o motivo do ajuste (opcional):', '') || null
            })
        });

        const result = await response.json();

        if (result.success) {
            // Calcular diferença total dos ajustes
            let diferencaTotal = 0;
            const diferencasPorPeriodo = {};

            // Atualizar os valores na tabela principal e calcular diferenças
            ajustesParaSalvar.forEach(ajuste => {
                const diferenca = ajuste.valor_ajustado - ajuste.valor_original;
                diferencaTotal += diferenca;

                // Acumular diferença por período
                if (!diferencasPorPeriodo[ajuste.periodo]) {
                    diferencasPorPeriodo[ajuste.periodo] = 0;
                }
                diferencasPorPeriodo[ajuste.periodo] += diferenca;

                // Atualizar célula do período do item
                const celula = document.querySelector(`td[data-cod-produto="${ajuste.cod_produto}"][data-periodo="${ajuste.periodo}"]`);
                if (celula) {
                    celula.textContent = formatNumber(ajuste.valor_ajustado);
                    celula.style.background = '#fef3c7';
                    celula.title = `Ajustado de ${formatNumber(ajuste.valor_original)} para ${formatNumber(ajuste.valor_ajustado)}`;
                }
            });

            // Atualizar total do item na tabela
            const celulaItemTotal = document.querySelector(`td[data-item-total="${codProduto}"]`);
            if (celulaItemTotal && itemSelecionadoDrillDown && itemSelecionadoDrillDown.dados) {
                const novoTotalItem = (itemSelecionadoDrillDown.dados.demanda_prevista_total || 0) + diferencaTotal;
                celulaItemTotal.textContent = formatNumber(novoTotalItem);
                celulaItemTotal.style.background = '#fef3c7';
                itemSelecionadoDrillDown.dados.demanda_prevista_total = novoTotalItem;
            }

            // Atualizar dados em memória para o item
            if (itemSelecionadoDrillDown && itemSelecionadoDrillDown.dados && itemSelecionadoDrillDown.dados.previsao_por_periodo) {
                ajustesParaSalvar.forEach(ajuste => {
                    const periodoData = itemSelecionadoDrillDown.dados.previsao_por_periodo.find(p => p.periodo === ajuste.periodo);
                    if (periodoData) {
                        periodoData.previsao = ajuste.valor_ajustado;
                    }
                });
            }

            // Atualizar totais do fornecedor (por período e geral)
            const fornecedorNome = itemSelecionadoDrillDown?.dados?.nome_fornecedor || '';
            const fornecedorId = fornecedorNome.replace(/[^a-zA-Z0-9]/g, '_');

            // Atualizar cada período do fornecedor
            Object.entries(diferencasPorPeriodo).forEach(([periodo, diferenca]) => {
                const celulaFornPeriodo = document.querySelector(`td[data-fornecedor-total="${fornecedorId}"][data-periodo="${periodo}"]`);
                if (celulaFornPeriodo) {
                    const valorAtual = parseFloat(celulaFornPeriodo.textContent.replace(/\./g, '').replace(',', '.')) || 0;
                    const novoValor = valorAtual + diferenca;
                    celulaFornPeriodo.textContent = formatNumber(novoValor);
                    celulaFornPeriodo.style.background = '#fef3c7';
                }
            });

            // Atualizar total geral do fornecedor
            const celulaFornTotal = document.querySelector(`td[data-fornecedor-total-geral="${fornecedorId}"]`);
            if (celulaFornTotal) {
                const valorAtual = parseFloat(celulaFornTotal.textContent.replace(/\./g, '').replace(',', '.')) || 0;
                const novoValor = valorAtual + diferencaTotal;
                celulaFornTotal.textContent = formatNumber(novoValor);
                celulaFornTotal.style.background = '#fef3c7';
            }

            // =====================================================
            // Atualizar tabela de CUSTO (CUE) espelhada
            // =====================================================
            const cueItem = itemSelecionadoDrillDown?.dados?.cue || 0;
            if (cueItem > 0) {
                // Atualizar cada célula de período na tabela de custo
                ajustesParaSalvar.forEach(ajuste => {
                    const celulaCusto = document.querySelector(`td[data-custo-cod-produto="${ajuste.cod_produto}"][data-custo-periodo="${ajuste.periodo}"]`);
                    if (celulaCusto) {
                        const valorCusto = ajuste.valor_ajustado * cueItem;
                        celulaCusto.textContent = formatCurrency(valorCusto);
                        celulaCusto.style.background = '#fef3c7';
                        celulaCusto.title = `Ajustado: ${formatNumber(ajuste.valor_ajustado)} un × ${formatCurrency(cueItem)}`;
                    }
                });

                // Atualizar total do item na tabela de custo
                const celulaCustoItemTotal = document.querySelector(`td[data-custo-item-total="${codProduto}"]`);
                if (celulaCustoItemTotal && itemSelecionadoDrillDown?.dados) {
                    const novoTotalCusto = (itemSelecionadoDrillDown.dados.demanda_prevista_total || 0) * cueItem;
                    celulaCustoItemTotal.textContent = formatCurrency(novoTotalCusto);
                    celulaCustoItemTotal.style.background = '#fef3c7';
                }

                // Atualizar totais do fornecedor na tabela de custo (por período)
                const periodos = itemSelecionadoDrillDown?.dados?.previsao_por_periodo || [];
                Object.entries(diferencasPorPeriodo).forEach(([periodo, diferenca]) => {
                    const diferencaCusto = diferenca * cueItem;
                    // Encontrar idx do periodo
                    const periodoIdx = periodos.findIndex(p => p.periodo === periodo);
                    if (periodoIdx >= 0) {
                        const celulaCustoFornPeriodo = document.querySelector(`td[data-custo-fornecedor-total="${fornecedorId}"][data-custo-periodo-idx="${periodoIdx}"]`);
                        if (celulaCustoFornPeriodo) {
                            const valorAtualStr = celulaCustoFornPeriodo.textContent.replace(/[R$\s.]/g, '').replace(',', '.');
                            const valorAtual = parseFloat(valorAtualStr) || 0;
                            const novoValor = valorAtual + diferencaCusto;
                            celulaCustoFornPeriodo.textContent = formatCurrency(novoValor);
                            celulaCustoFornPeriodo.style.background = '#fef3c7';
                        }
                    }
                });

                // Atualizar total geral do fornecedor na tabela de custo
                const celulaCustoFornTotal = document.querySelector(`td[data-custo-fornecedor-total-geral="${fornecedorId}"]`);
                if (celulaCustoFornTotal) {
                    const valorAtualStr = celulaCustoFornTotal.textContent.replace(/[R$\s.]/g, '').replace(',', '.');
                    const valorAtual = parseFloat(valorAtualStr) || 0;
                    const novoValor = valorAtual + (diferencaTotal * cueItem);
                    celulaCustoFornTotal.textContent = formatCurrency(novoValor);
                    celulaCustoFornTotal.style.background = '#fef3c7';
                }
            }

            // Atualizar tabela comparativa (linha Previsão)
            // Atualiza tanto a linha do fornecedor específico quanto o total consolidado
            Object.entries(diferencasPorPeriodo).forEach(([periodo, diferenca]) => {
                // 1. Atualizar célula do fornecedor específico na tabela comparativa
                const celulaFornecedorComparativa = document.querySelector(`td[data-comparativa-fornecedor="${fornecedorId}"][data-comparativa-periodo="${periodo}"]`);
                if (celulaFornecedorComparativa) {
                    const valorAtual = parseFloat(celulaFornecedorComparativa.textContent.replace(/\./g, '').replace(',', '.')) || 0;
                    const novoValor = valorAtual + diferenca;
                    celulaFornecedorComparativa.textContent = formatNumber(novoValor);
                    celulaFornecedorComparativa.style.background = '#fef3c7';
                }

                // 2. Atualizar célula do TOTAL CONSOLIDADO na tabela comparativa
                const celulaConsolidadoComparativa = document.querySelector(`td[data-comparativa-consolidado="true"][data-comparativa-periodo="${periodo}"]`);
                if (celulaConsolidadoComparativa) {
                    const valorAtual = parseFloat(celulaConsolidadoComparativa.textContent.replace(/\./g, '').replace(',', '.')) || 0;
                    const novoValor = valorAtual + diferenca;
                    celulaConsolidadoComparativa.textContent = formatNumber(novoValor);
                    celulaConsolidadoComparativa.style.background = '#fef3c7';
                }

                // 3. Fallback: Atualizar célula genérica (para caso de fornecedor único sem data-attributes específicos)
                const celulaComparativa = document.querySelector(`td[data-comparativa-periodo="${periodo}"]:not([data-comparativa-fornecedor]):not([data-comparativa-consolidado])`);
                if (celulaComparativa) {
                    const valorAtual = parseFloat(celulaComparativa.textContent.replace(/\./g, '').replace(',', '.')) || 0;
                    const novoValor = valorAtual + diferenca;
                    celulaComparativa.textContent = formatNumber(novoValor);
                    celulaComparativa.style.background = '#fef3c7';
                }
            });

            // Atualizar total geral do fornecedor na tabela comparativa
            const celulaFornecedorTotalComparativa = document.querySelector(`td[data-comparativa-fornecedor-total="${fornecedorId}"]`);
            if (celulaFornecedorTotalComparativa) {
                const valorAtual = parseFloat(celulaFornecedorTotalComparativa.textContent.replace(/\./g, '').replace(',', '.')) || 0;
                const novoValor = valorAtual + diferencaTotal;
                celulaFornecedorTotalComparativa.textContent = formatNumber(novoValor);
                celulaFornecedorTotalComparativa.style.background = '#fef3c7';
            }

            // Atualizar total geral consolidado da tabela comparativa
            const celulaTotalConsolidado = document.getElementById('totalPrevisaoComparativaConsolidado');
            if (celulaTotalConsolidado) {
                const valorAtual = parseFloat(celulaTotalConsolidado.textContent.replace(/\./g, '').replace(',', '.')) || 0;
                const novoValor = valorAtual + diferencaTotal;
                celulaTotalConsolidado.textContent = formatNumber(novoValor);
                celulaTotalConsolidado.style.background = '#fef3c7';
            }

            // Atualizar total geral da tabela comparativa (fornecedor único)
            const celulaTotalComparativa = document.getElementById('totalPrevisaoComparativa');
            if (celulaTotalComparativa) {
                const valorAtual = parseFloat(celulaTotalComparativa.textContent.replace(/\./g, '').replace(',', '.')) || 0;
                const novoValor = valorAtual + diferencaTotal;
                celulaTotalComparativa.textContent = formatNumber(novoValor);
                celulaTotalComparativa.style.background = '#fef3c7';
            }

            // Atualizar dados globais e gráfico
            if (dadosRelatorioDetalhado) {
                // Atualizar item nos dados globais
                const itemGlobal = dadosRelatorioDetalhado.itens?.find(i => i.cod_produto === codProduto);
                if (itemGlobal) {
                    itemGlobal.demanda_prevista_total = (itemGlobal.demanda_prevista_total || 0) + diferencaTotal;
                    ajustesParaSalvar.forEach(ajuste => {
                        const periodoData = itemGlobal.previsao_por_periodo?.find(p => p.periodo === ajuste.periodo);
                        if (periodoData) {
                            periodoData.previsao = ajuste.valor_ajustado;
                        }
                    });
                }

                // Atualizar previsões agregadas
                if (dadosRelatorioDetalhado.previsoes_agregadas) {
                    Object.entries(diferencasPorPeriodo).forEach(([periodo, diferenca]) => {
                        if (dadosRelatorioDetalhado.previsoes_agregadas[periodo] !== undefined) {
                            dadosRelatorioDetalhado.previsoes_agregadas[periodo] += diferenca;
                        }
                    });
                }

                // Recalcular e atualizar gráfico principal
                atualizarGraficoAposAjuste();
            }

            // Limpar ajustes pendentes do item
            delete ajustesPendentes[codProduto];

            // Atualizar visual
            atualizarIndicadorAjusteTabela(codProduto);

            // Mostrar mensagem de sucesso
            mostrarMensagemValidacao('sucesso', 'Ajustes Salvos',
                `${ajustesParaSalvar.length} ajuste(s) salvos com sucesso para o item ${codProduto}`);

            // Habilitar botão "Salvar Demanda" após ajuste de item
            atualizarBotaoSalvarDemanda();

            // Desselecionar item
            desselecionarItemDrillDown();
        } else {
            alert('Erro ao salvar ajustes: ' + (result.erro || 'Erro desconhecido'));
        }
    } catch (error) {
        console.error('Erro ao salvar ajustes:', error);
        alert('Erro de comunicação com o servidor');
    }
}

// Função para atualizar o gráfico principal após ajuste
function atualizarGraficoAposAjuste() {
    if (!dadosRelatorioDetalhado || !window.previsaoChartInstance) {
        return;
    }

    // Recalcular previsões agregadas a partir dos itens
    const novasPrevisoes = {};
    if (dadosRelatorioDetalhado.itens) {
        dadosRelatorioDetalhado.itens.forEach(item => {
            if (item.previsao_por_periodo) {
                item.previsao_por_periodo.forEach(p => {
                    if (!novasPrevisoes[p.periodo]) {
                        novasPrevisoes[p.periodo] = 0;
                    }
                    novasPrevisoes[p.periodo] += p.previsao || 0;
                });
            }
        });
    }

    // Atualizar dados do gráfico
    const chart = window.previsaoChartInstance;
    if (chart && chart.data && chart.data.datasets) {
        // Encontrar o dataset de previsão (geralmente é o segundo ou tem label 'Previsão')
        const datasetPrevisao = chart.data.datasets.find(ds =>
            ds.label && (ds.label.includes('Previs') || ds.label.includes('previs'))
        );

        if (datasetPrevisao && chart.data.labels) {
            // Atualizar valores de previsão
            chart.data.labels.forEach((label, idx) => {
                // Encontrar o período correspondente
                const periodoKey = Object.keys(novasPrevisoes).find(p => {
                    // Comparar formatado
                    if (label.includes('/')) {
                        // Formato Mês/Ano ou DD/MM
                        const mesesNomes = ['Jan', 'Fev', 'Mar', 'Abr', 'Mai', 'Jun', 'Jul', 'Ago', 'Set', 'Out', 'Nov', 'Dez'];
                        if (p.includes('-') && !p.includes('-S')) {
                            // Formato YYYY-MM-DD ou YYYY-MM-01
                            const partes = p.split('-');
                            const mesIdx = parseInt(partes[1]) - 1;
                            const ano = partes[0].slice(-2);
                            const labelEsperado = `${mesesNomes[mesIdx]}/${ano}`;
                            return label === labelEsperado;
                        }
                    }
                    return false;
                });

                if (periodoKey && novasPrevisoes[periodoKey] !== undefined) {
                    datasetPrevisao.data[idx] = Math.round(novasPrevisoes[periodoKey]);
                }
            });

            // Atualizar gráfico
            chart.update();
        }
    }

    // Atualizar resumo (Total Previsão)
    const totalPrevisao = Object.values(novasPrevisoes).reduce((sum, v) => sum + v, 0);
    const elementoTotalPrevisao = document.querySelector('[data-resumo="total-previsao"]');
    if (elementoTotalPrevisao) {
        elementoTotalPrevisao.textContent = formatNumber(Math.round(totalPrevisao));
    }

    // Tentar atualizar no card de resumo se existir
    const resumoCards = document.querySelectorAll('.card, .resumo-card, [class*="resumo"]');
    resumoCards.forEach(card => {
        const texto = card.textContent;
        if (texto && texto.includes('Previsão Total')) {
            const valorElement = card.querySelector('.valor, .numero, strong, b');
            if (valorElement) {
                valorElement.textContent = formatNumber(Math.round(totalPrevisao));
            }
        }
    });
}

// Adicionar CSS para linha selecionada
(function() {
    if (!document.getElementById('drillDownStyles')) {
        const style = document.createElement('style');
        style.id = 'drillDownStyles';
        style.textContent = `
            .linha-item-selecionada {
                background: linear-gradient(90deg, #f5f3ff 0%, #ede9fe 100%) !important;
                border-left: 4px solid #8b5cf6 !important;
                box-shadow: inset 0 0 0 1px #8b5cf6;
            }
            .linha-item-selecionada td {
                background: #ede9fe !important;
            }
            .linha-item-selecionada td:first-child {
                border-left: 4px solid #8b5cf6 !important;
            }
            .linha-item {
                cursor: pointer;
                transition: background 0.2s;
            }
            .linha-item:hover:not(.linha-item-selecionada) {
                background: #f9fafb !important;
            }
            .linha-item:hover:not(.linha-item-selecionada) td {
                background: #f9fafb !important;
            }
            .indicador-ajuste {
                animation: pulse 2s infinite;
            }
            @keyframes pulse {
                0%, 100% { opacity: 1; }
                50% { opacity: 0.5; }
            }
        `;
        document.head.appendChild(style);
    }
})();


// =====================================================
// EXPORTAÇÃO DO RELATÓRIO DETALHADO DE ITENS
// =====================================================

/**
 * Exporta o relatório detalhado de itens para Excel
 * IMPORTANTE: Só funciona fora do modo de ajuste manual
 */
async function exportarRelatorioItens() {
    // Verificar se há dados para exportar
    if (!dadosRelatorioDetalhado || !dadosRelatorioDetalhado.itens || dadosRelatorioDetalhado.itens.length === 0) {
        alert('Nenhum dado de relatório para exportar. Gere uma previsão primeiro.');
        return;
    }

    // Verificar se há ajustes pendentes (modo de ajuste manual ativo)
    const temAjustesPendentes = Object.keys(ajustesPendentes).length > 0;
    if (temAjustesPendentes) {
        const confirmar = confirm(
            'Existem ajustes pendentes que não foram salvos.\n\n' +
            'Se exportar agora, os valores originais serão usados.\n\n' +
            'Deseja continuar mesmo assim?'
        );
        if (!confirmar) {
            return;
        }
    }

    try {
        // Mostrar loading
        const downloadBtn = document.getElementById('downloadBtn');
        const textoOriginal = downloadBtn.textContent;
        downloadBtn.textContent = 'Gerando Excel...';
        downloadBtn.style.opacity = '0.7';
        downloadBtn.style.pointerEvents = 'none';

        // Preparar dados para envio
        const dadosExportar = {
            itens: dadosRelatorioDetalhado.itens,
            periodos: dadosRelatorioDetalhado.periodos_previsao || [],
            granularidade: dadosRelatorioDetalhado.granularidade || 'mensal',
            filtros: {
                loja: document.getElementById('loja')?.value || '',
                fornecedor: document.getElementById('fornecedor')?.value || '',
                categoria: document.getElementById('categoria')?.value || ''
            }
        };

        // Fazer requisição POST para a API
        const response = await fetch('/api/exportar_relatorio_itens', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(dadosExportar)
        });

        if (!response.ok) {
            const errorData = await response.json();
            throw new Error(errorData.erro || 'Erro ao gerar arquivo Excel');
        }

        // Obter o blob do arquivo
        const blob = await response.blob();

        // Criar link de download
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;

        // Extrair nome do arquivo do header ou usar nome padrão
        const contentDisposition = response.headers.get('Content-Disposition');
        let filename = 'relatorio_detalhado_itens.xlsx';
        if (contentDisposition) {
            const match = contentDisposition.match(/filename[^;=\n]*=((['"]).*?\2|[^;\n]*)/);
            if (match && match[1]) {
                filename = match[1].replace(/['"]/g, '');
            }
        }

        a.download = filename;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        window.URL.revokeObjectURL(url);

        // Restaurar botão
        downloadBtn.textContent = textoOriginal;
        downloadBtn.style.opacity = '1';
        downloadBtn.style.pointerEvents = 'auto';

        console.log('[Export] Relatório de itens exportado com sucesso:', filename);

    } catch (error) {
        console.error('[Export] Erro ao exportar relatório de itens:', error);
        alert('Erro ao exportar relatório: ' + error.message);

        // Restaurar botão em caso de erro
        const downloadBtn = document.getElementById('downloadBtn');
        downloadBtn.textContent = 'Download Excel';
        downloadBtn.style.opacity = '1';
        downloadBtn.style.pointerEvents = 'auto';
    }
}

// =====================================================
// SALVAR DEMANDA PRE-CALCULADA (v5.7)
// =====================================================

// Variável global para armazenar o intervalo de polling
let _pollingInterval = null;
let _cnpjEmProcessamento = null;

/**
 * Salva os valores EXIBIDOS na Tela de Demanda diretamente em demanda_pre_calculada.
 * Envia os dados ja calculados (dadosPrevisaoAtual) para o backend, que os grava
 * como ajuste_manual — substituindo qualquer valor anterior, inclusive o do cronjob.
 * O cronjob diario preserva registros com ajuste_manual e nao os sobrescreve.
 */
async function salvarDemandaPreCalculada() {
    const btn = document.getElementById('salvarDemandaBtn');
    if (!btn) return;

    // Verificar se há dados da tela disponíveis
    if (!dadosPrevisaoAtual || !dadosPrevisaoAtual.relatorio_detalhado) {
        alert('Nenhuma previsão calculada.\n\nGere a previsão primeiro antes de salvar.');
        return;
    }

    const itens = dadosPrevisaoAtual.relatorio_detalhado.itens || [];
    if (itens.length === 0) {
        alert('Nenhum item encontrado nos dados da previsão atual.');
        return;
    }

    // Filtrar apenas itens com previsao_por_periodo preenchida (exclui bloqueados)
    const itensSalvos = itens.filter(i =>
        i.previsao_por_periodo && i.previsao_por_periodo.length > 0 &&
        i.cnpj_fornecedor
    );

    if (itensSalvos.length === 0) {
        alert('Nenhum item com dados de previsão para salvar.');
        return;
    }

    const totalRegistros = itensSalvos.reduce((s, i) => s + i.previsao_por_periodo.length, 0);

    const confirmar = confirm(
        `Deseja salvar a demanda exibida na tela?\n\n` +
        `• ${itensSalvos.length} itens\n` +
        `• ${totalRegistros} registros (item × período)\n\n` +
        `Os valores da tela serão gravados em demanda_pre_calculada e\n` +
        `protegidos contra sobrescrita pelo cálculo automático.\n\n` +
        `Deseja continuar?`
    );

    if (!confirmar) return;

    btn.innerHTML = '⏳ Salvando...';
    btn.disabled = true;
    btn.style.opacity = '0.7';

    try {
        const response = await fetch('/api/demanda/salvar_tela', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                itens: itensSalvos.map(i => ({
                    cod_produto: i.cod_produto,
                    cnpj_fornecedor: i.cnpj_fornecedor,
                    previsao_por_periodo: i.previsao_por_periodo.map(p => ({
                        ...p,
                        editado: !!(ajustesPendentes[i.cod_produto] && ajustesPendentes[i.cod_produto][p.periodo] !== undefined)
                    }))
                })),
                usuario: 'tela_demanda'
            })
        });

        const resultado = await response.json();

        btn.innerHTML = '💾 Salvar Demanda';
        btn.disabled = false;
        btn.style.opacity = '1';

        if (response.ok && resultado.success) {
            alert(
                `✅ Demanda salva com sucesso!\n\n` +
                `Fornecedores processados: 1/1\n` +
                `Total de itens: ${resultado.total_itens}\n` +
                `Total de registros: ${resultado.total_registros}\n\n` +
                `Os valores agora estão disponíveis na Tela de Pedido Fornecedor.`
            );
        } else {
            alert(`❌ Erro ao salvar demanda!\n\n${resultado.erro || 'Erro desconhecido'}`);
        }

    } catch (error) {
        btn.innerHTML = '💾 Salvar Demanda';
        btn.disabled = false;
        btn.style.opacity = '1';
        console.error('[SalvarDemanda] Erro:', error);
        alert(`❌ Erro ao salvar demanda!\n\n${error.message}`);
    }
}

/**
 * Inicia o polling para verificar o status do cálculo em background.
 */
function iniciarPollingStatus(cnpj, nomeFornecedor, totalItensEstimado) {
    // Parar polling anterior se existir
    if (_pollingInterval) {
        clearInterval(_pollingInterval);
    }

    let tentativas = 0;
    const maxTentativas = 120; // 10 minutos (5s x 120)

    _pollingInterval = setInterval(async () => {
        tentativas++;

        try {
            const response = await fetch(`/api/demanda_job/status/${encodeURIComponent(cnpj)}`);
            const data = await response.json();

            if (!data.success) {
                console.warn('[Polling] Erro na resposta:', data.erro);
                return;
            }

            const btn = document.getElementById('salvarDemandaBtn');

            if (data.is_concluido) {
                // Cálculo concluído com sucesso
                clearInterval(_pollingInterval);
                _pollingInterval = null;
                _cnpjEmProcessamento = null;

                const execucao = data.execucao || {};
                const dadosAtuais = data.dados_atuais || {};

                mostrarStatusCalculo('concluido', nomeFornecedor, dadosAtuais.total_produtos, execucao.tempo_execucao_ms);

                // Restaurar botão
                if (btn) {
                    btn.innerHTML = '💾 Salvar Demanda';
                    btn.disabled = false;
                    btn.style.opacity = '1';
                }

                console.log('[Polling] Cálculo concluído:', data);

            } else if (data.is_erro) {
                // Cálculo falhou
                clearInterval(_pollingInterval);
                _pollingInterval = null;
                _cnpjEmProcessamento = null;

                mostrarStatusCalculo('erro', nomeFornecedor, 0, 0);

                // Restaurar botão
                if (btn) {
                    btn.innerHTML = '💾 Salvar Demanda';
                    btn.disabled = false;
                    btn.style.opacity = '1';
                }

                console.error('[Polling] Cálculo com erro:', data);

            } else if (data.is_processando) {
                // Ainda processando - atualizar status visual
                const dadosAtuais = data.dados_atuais || {};
                if (btn) {
                    btn.innerHTML = `⏳ Processando... (${dadosAtuais.total_produtos || 0} itens)`;
                }
                console.log('[Polling] Ainda processando:', dadosAtuais);

            } else if (tentativas >= maxTentativas) {
                // Timeout
                clearInterval(_pollingInterval);
                _pollingInterval = null;
                _cnpjEmProcessamento = null;

                mostrarStatusCalculo('timeout', nomeFornecedor, 0, 0);

                // Restaurar botão
                if (btn) {
                    btn.innerHTML = '💾 Salvar Demanda';
                    btn.disabled = false;
                    btn.style.opacity = '1';
                }

                console.warn('[Polling] Timeout após', tentativas, 'tentativas');
            }

        } catch (error) {
            console.error('[Polling] Erro ao verificar status:', error);
        }

    }, 5000); // Verificar a cada 5 segundos
}

/**
 * Mostra uma notificação visual do status do cálculo.
 */
function mostrarStatusCalculo(status, fornecedor, totalItens, tempoMs) {
    // Remover notificação anterior se existir
    const notifAnterior = document.getElementById('notif-calculo-demanda');
    if (notifAnterior) notifAnterior.remove();

    const cores = {
        processando: { bg: '#dbeafe', border: '#3b82f6', icon: '⏳', iconColor: '#2563eb' },
        concluido: { bg: '#d1fae5', border: '#10b981', icon: '✓', iconColor: '#059669' },
        erro: { bg: '#fee2e2', border: '#ef4444', icon: '✕', iconColor: '#dc2626' },
        timeout: { bg: '#fef3c7', border: '#f59e0b', icon: '⚠', iconColor: '#d97706' }
    };

    const mensagens = {
        processando: `Calculando demanda para ${fornecedor}...\nItens estimados: ${totalItens || '...'}`,
        concluido: `Demanda salva com sucesso!\nFornecedor: ${fornecedor}\nItens processados: ${totalItens}\nTempo: ${((tempoMs || 0) / 1000).toFixed(1)}s`,
        erro: `Erro ao calcular demanda para ${fornecedor}.\nVerifique os logs do servidor.`,
        timeout: `Tempo limite excedido.\nO cálculo pode ainda estar em andamento.\nVerifique o status manualmente.`
    };

    const cor = cores[status] || cores.processando;
    const mensagem = mensagens[status] || 'Status desconhecido';

    const notif = document.createElement('div');
    notif.id = 'notif-calculo-demanda';
    notif.style.cssText = `
        position: fixed;
        top: 20px;
        right: 20px;
        background: ${cor.bg};
        border: 2px solid ${cor.border};
        border-radius: 8px;
        padding: 16px 20px;
        box-shadow: 0 4px 12px rgba(0,0,0,0.15);
        z-index: 10000;
        max-width: 350px;
        font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
        animation: slideIn 0.3s ease-out;
    `;

    notif.innerHTML = `
        <style>
            @keyframes slideIn {
                from { transform: translateX(100%); opacity: 0; }
                to { transform: translateX(0); opacity: 1; }
            }
        </style>
        <div style="display: flex; align-items: flex-start; gap: 12px;">
            <div style="font-size: 24px; color: ${cor.iconColor};">${cor.icon}</div>
            <div style="flex: 1;">
                <div style="font-weight: 600; color: #1f2937; margin-bottom: 4px;">
                    ${status === 'processando' ? 'Processando...' : status === 'concluido' ? 'Concluído!' : status === 'erro' ? 'Erro!' : 'Timeout'}
                </div>
                <div style="font-size: 13px; color: #4b5563; white-space: pre-line;">
                    ${mensagem}
                </div>
            </div>
            <button onclick="this.parentElement.parentElement.remove()" style="
                background: none;
                border: none;
                font-size: 18px;
                color: #9ca3af;
                cursor: pointer;
                padding: 0;
                line-height: 1;
            ">&times;</button>
        </div>
    `;

    document.body.appendChild(notif);

    // Auto-remover após alguns segundos (exceto se processando)
    if (status !== 'processando') {
        setTimeout(() => {
            if (notif.parentElement) {
                notif.style.animation = 'slideIn 0.3s ease-out reverse';
                setTimeout(() => notif.remove(), 300);
            }
        }, status === 'concluido' ? 8000 : 10000);
    }
}

// Função para verificar fornecedores selecionados (suporta múltiplos)
function verificarFornecedoresSelecionados() {
    const fornecedores = MultiSelect.getSelected('fornecedor_banco');

    if (!fornecedores || fornecedores.length === 0) {
        return { valido: false, fornecedores: [], quantidade: 0 };
    }

    // Filtrar valores inválidos
    const fornecedoresValidos = fornecedores.filter(f => f && f !== 'TODOS' && f !== 'Carregando...');

    return {
        valido: fornecedoresValidos.length > 0,
        fornecedores: fornecedoresValidos,
        quantidade: fornecedoresValidos.length
    };
}

// Função para habilitar/desabilitar botão de salvar demanda
function atualizarBotaoSalvarDemanda() {
    const btn = document.getElementById('salvarDemandaBtn');
    if (!btn) return;

    const { valido, quantidade } = verificarFornecedoresSelecionados();

    // Habilitar botão se houver fornecedor(es) selecionado(s) e resultados na tela
    const temResultados = document.getElementById('results')?.style.display !== 'none';

    if (valido && temResultados) {
        btn.disabled = false;
        btn.style.opacity = '1';
        btn.style.cursor = 'pointer';
        btn.title = quantidade === 1
            ? 'Salvar demanda pré-calculada para o fornecedor selecionado'
            : `Salvar demanda pré-calculada para ${quantidade} fornecedores selecionados`;
    } else if (!valido) {
        btn.disabled = true;
        btn.style.opacity = '0.5';
        btn.style.cursor = 'not-allowed';
        btn.title = 'Selecione pelo menos um fornecedor para salvar a demanda';
    } else {
        btn.disabled = true;
        btn.style.opacity = '0.5';
        btn.style.cursor = 'not-allowed';
        btn.title = 'Gere uma previsão primeiro para salvar a demanda';
    }
}

/**
 * Verifica se há jobs em processamento ao carregar a página.
 * Se houver, retoma o polling para mostrar status atualizado.
 */
async function verificarJobsEmProcessamento() {
    try {
        const response = await fetch('/api/demanda_job/status');
        if (!response.ok) return;

        const data = await response.json();
        if (!data.success || !data.ultimas_execucoes) return;

        // Procurar execuções com status 'iniciado' ou 'processando' nos últimos 15 minutos
        const agora = new Date();
        const quinzeMinutosAtras = new Date(agora.getTime() - 15 * 60 * 1000);

        for (const exec of data.ultimas_execucoes) {
            const dataExec = new Date(exec.data_execucao);
            const status = exec.status;
            const fornecedor = exec.cnpj_fornecedor_filtro;

            // Se está processando E é recente
            if ((status === 'iniciado' || status === 'processando') && dataExec > quinzeMinutosAtras) {
                console.log('[VerificarJobs] Encontrado job em processamento:', fornecedor);

                // Atualizar botão para estado de processamento
                const btn = document.getElementById('salvarDemandaBtn');
                if (btn) {
                    btn.innerHTML = '⏳ Processando...';
                    btn.disabled = true;
                    btn.style.opacity = '0.7';
                }

                // Mostrar notificação e iniciar polling
                mostrarStatusCalculo('processando', fornecedor, exec.total_itens_processados || 0, 0);
                iniciarPollingStatus(fornecedor, fornecedor, exec.total_itens_processados || 0);

                // Só monitora um job por vez
                break;
            }
        }
    } catch (error) {
        console.warn('[VerificarJobs] Erro ao verificar jobs:', error);
    }
}

// Executar verificação ao carregar a página (após um pequeno delay)
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', () => setTimeout(verificarJobsEmProcessamento, 1000));
} else {
    setTimeout(verificarJobsEmProcessamento, 1000);
}
