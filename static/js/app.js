// Sistema de Previsão de Demanda - JavaScript

document.getElementById('uploadForm').addEventListener('submit', async (e) => {
    e.preventDefault();

    // Esconder seções
    document.getElementById('results').style.display = 'none';
    document.getElementById('error').style.display = 'none';

    // Mostrar progresso
    document.getElementById('progress').style.display = 'block';

    const formData = new FormData(e.target);
    const progressFill = document.getElementById('progressFill');
    const progressText = document.getElementById('progressText');

    // Simular progresso
    let progress = 0;
    const progressInterval = setInterval(() => {
        progress += 2;
        if (progress <= 90) {
            progressFill.style.width = progress + '%';

            // Atualizar texto de progresso
            if (progress < 20) {
                progressText.textContent = 'Carregando arquivo...';
            } else if (progress < 40) {
                progressText.textContent = 'Validando dados...';
            } else if (progress < 60) {
                progressText.textContent = 'Tratando rupturas de estoque...';
            } else if (progress < 80) {
                progressText.textContent = 'Gerando previsoes...';
            } else {
                progressText.textContent = 'Compilando relatorio...';
            }
        }
    }, 200);

    try {
        // Enviar para backend
        const response = await fetch('/upload', {
            method: 'POST',
            body: formData
        });

        const data = await response.json();

        clearInterval(progressInterval);
        progressFill.style.width = '100%';
        progressText.textContent = 'Concluido!';

        // Pequeno delay para mostrar 100%
        await new Promise(resolve => setTimeout(resolve, 500));

        if (data.success) {
            mostrarResultados(data);
        } else {
            mostrarErro(data.erro);
        }

    } catch (error) {
        clearInterval(progressInterval);
        mostrarErro('Erro de conexao com o servidor: ' + error.message);
    }
});

function mostrarResultados(data) {
    // Esconder progresso
    document.getElementById('progress').style.display = 'none';

    // Mostrar resultados
    document.getElementById('results').style.display = 'block';

    // Preencher resumo - Layout executivo
    const resumo = data.resumo;

    // Calcular MAPE e BIAS médios das previsões
    let mapeMedia = 0;
    let biasMedia = 0;
    let countMetrics = 0;

    if (data.grafico_data && data.grafico_data.previsoes_lojas) {
        data.grafico_data.previsoes_lojas.forEach(p => {
            if (p.MAPE !== null && p.MAPE !== undefined) {
                mapeMedia += p.MAPE;
                countMetrics++;
            }
            if (p.BIAS !== null && p.BIAS !== undefined) {
                biasMedia += p.BIAS;
            }
        });
        if (countMetrics > 0) {
            mapeMedia = (mapeMedia / countMetrics).toFixed(1);
            biasMedia = (biasMedia / countMetrics).toFixed(1);
        }
    }

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
            <h4>MAPE Médio</h4>
            <p class="big-number-compact">${mapeMedia}%</p>
            <p style="font-size: 0.7em; color: #666; margin-top: 4px;">Acurácia</p>
        </div>
        <div class="resumo-card-compact">
            <h4>BIAS Médio</h4>
            <p class="big-number-compact">${biasMedia > 0 ? '+' : ''}${biasMedia}%</p>
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
        exibirTabelaFornecedorItem(data.grafico_data);  // Tabela fornecedor/item
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
                    beginAtZero: true,
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
                    beginAtZero: true,
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
    let headerRow = '<tr style="background-color: #f5f5f5; border-bottom: 2px solid #0070f3; font-size: 0.85em;">';
    headerRow += '<th style="padding: 6px 8px; text-align: left; border-right: 1px solid #ddd; white-space: nowrap;">Período</th>';

    mesesNomes.forEach(mes => {
        headerRow += `<th style="padding: 6px 4px; border-left: 1px solid #e5e5e5; white-space: nowrap; font-size: 0.85em;">${mes}</th>`;
    });

    headerRow += '<th style="padding: 6px 8px; border-left: 2px solid #0070f3; background-color: #e6f3ff; font-weight: bold; white-space: nowrap;">Total</th>';
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
    rowPrevisao += `<td style="padding: 6px 8px; border-left: 2px solid #0070f3; background-color: #e6f3ff; font-weight: bold;">${formatNumber(totalPrevisao)}</td>`;
    rowPrevisao += '</tr>';

    // Linha 2: Ano Anterior (período passado) - Compacto
    let rowAnterior = '<tr style="background-color: rgba(17, 153, 142, 0.1);">';
    rowAnterior += '<td style="padding: 6px 8px; font-weight: bold; text-align: left; border-right: 1px solid #ddd; white-space: nowrap;">Ano Anterior</td>';
    comparacao_yoy.forEach(d => {
        const valor = d.demanda_ano_anterior || 0;
        rowAnterior += `<td style="padding: 6px 4px; border-left: 1px solid #e5e5e5; font-weight: 500; font-size: 0.9em;">${formatNumber(valor)}</td>`;
    });
    rowAnterior += `<td style="padding: 6px 8px; border-left: 2px solid #0070f3; background-color: #e6f3ff; font-weight: bold;">${formatNumber(totalAnterior)}</td>`;
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
    rowVariacao += `<td style="padding: 6px 8px; border-left: 2px solid #0070f3; background-color: #e6f3ff; font-weight: bold; color: ${corTotal};">${sinalTotal}${variacaoTotal.toFixed(1)}%</td>`;
    rowVariacao += '</tr>';

    // Adicionar as linhas ao tbody
    tbody.innerHTML = rowPrevisao + rowAnterior + rowVariacao;
}

// ===== MÉTRICAS DE ACURÁCIA (MAPE + BIAS) =====
function exibirMetricasAcuracia(dados) {
    if (!dados.previsoes_lojas || dados.previsoes_lojas.length === 0) {
        return;
    }

    // Calcular métricas agregadas
    const previsoes_com_metricas = dados.previsoes_lojas.filter(p => p.MAPE !== null && p.BIAS !== null);

    if (previsoes_com_metricas.length === 0) {
        return; // Não há métricas calculadas
    }

    // Calcular médias por loja/SKU (pegar apenas primeira previsão de cada combinação)
    const metricas_unicas = {};
    dados.previsoes_lojas.forEach(p => {
        const key = `${p.Loja}_${p.SKU}`;
        if (!metricas_unicas[key] && p.MAPE !== null) {
            metricas_unicas[key] = {
                loja: p.Loja,
                sku: p.SKU,
                mape: p.MAPE,
                bias: p.BIAS,
                metodo: p.Metodo
            };
        }
    });

    const metricas_array = Object.values(metricas_unicas);

    // Calcular médias gerais
    const mape_medio = metricas_array.reduce((sum, m) => sum + m.mape, 0) / metricas_array.length;
    const bias_medio = metricas_array.reduce((sum, m) => sum + m.bias, 0) / metricas_array.length;

    // Interpretar MAPE
    let mape_classificacao = '';
    let mape_cor = '';
    if (mape_medio < 10) {
        mape_classificacao = 'Excelente';
        mape_cor = '#28a745'; // Verde
    } else if (mape_medio < 20) {
        mape_classificacao = 'Boa';
        mape_cor = '#5cb85c';
    } else if (mape_medio < 30) {
        mape_classificacao = 'Aceitável';
        mape_cor = '#f0ad4e'; // Laranja
    } else if (mape_medio < 50) {
        mape_classificacao = 'Fraca';
        mape_cor = '#ff8c00';
    } else {
        mape_classificacao = 'Muito fraca';
        mape_cor = '#d9534f'; // Vermelho
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
            <!-- Card MAPE -->
            <div style="background: #f8f9fa; border-left: 4px solid ${mape_cor}; padding: 15px; border-radius: 4px;">
                <div style="font-weight: bold; color: #495057; margin-bottom: 8px;">
                    📊 MAPE (Erro Percentual Médio)
                </div>
                <div style="font-size: 1.8em; font-weight: bold; color: ${mape_cor}; margin-bottom: 5px;">
                    ${mape_medio.toFixed(1)}%
                </div>
                <div style="color: #6c757d; font-size: 0.9em; margin-bottom: 8px;">
                    Classificação: <span style="font-weight: bold; color: ${mape_cor};">${mape_classificacao}</span>
                </div>
                <div style="color: #6c757d; font-size: 0.85em;">
                    Em média, o erro é ${mape_medio.toFixed(1)}% do valor real
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
            • <strong>MAPE:</strong> Mostra o erro típico das previsões em percentual<br>
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
function exibirTabelaFornecedorItem(dados) {
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

    // Para cada fornecedor
    Object.keys(porFornecedor).sort().forEach(fornecedor => {
        const itensFornecedor = porFornecedor[fornecedor];

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
            <tr style="background: linear-gradient(135deg, #0070f3 0%, #00d4ff 100%); color: white;">
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
            <tr style="background: #e3f2fd; color: #0070f3; font-weight: bold; font-size: 0.85em;">
                <th style="padding: 8px; text-align: center; border-bottom: 2px solid #0070f3; width: 30px;"></th>
                <th style="padding: 8px; text-align: left; border-bottom: 2px solid #0070f3;">SKU</th>
                <th style="padding: 8px; text-align: right; border-bottom: 2px solid #0070f3;">Demanda Prevista (un)</th>
                <th style="padding: 8px; text-align: right; border-bottom: 2px solid #0070f3;">Demanda Ano Anterior (un)</th>
                <th style="padding: 8px; text-align: right; border-bottom: 2px solid #0070f3;">Variação YoY (%)</th>
                <th style="padding: 8px; text-align: center; border-bottom: 2px solid #0070f3;">Método Estatístico</th>
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
            if (dados.smart_alerts) {
                const alertasCriticos = dados.smart_alerts.filter(a =>
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
