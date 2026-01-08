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

// ===================================================================
// FUNCIONALIDADE DO BANCO DE DADOS
// ===================================================================

// Variável global para armazenar o gráfico de previsão
let previsaoChart = null;

// Trocar entre tabs (Upload vs Banco)
function trocarTab(tipo) {
    const tabBanco = document.getElementById('tabBanco');
    const tabUpload = document.getElementById('tabUpload');
    const formBanco = document.getElementById('formBanco');
    const formUpload = document.getElementById('formUpload');

    if (tipo === 'banco') {
        tabBanco.style.background = 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)';
        tabBanco.style.color = 'white';
        tabUpload.style.background = '#e0e0e0';
        tabUpload.style.color = '#666';
        formBanco.style.display = 'block';
        formUpload.style.display = 'none';
    } else {
        tabUpload.style.background = 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)';
        tabUpload.style.color = 'white';
        tabBanco.style.background = '#e0e0e0';
        tabBanco.style.color = '#666';
        formUpload.style.display = 'block';
        formBanco.style.display = 'none';
    }
}

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
        const response = await fetch('/api/lojas');
        const lojas = await response.json();
        const select = document.getElementById('loja_banco');

        select.innerHTML = '';
        lojas.forEach(loja => {
            const option = document.createElement('option');
            option.value = loja.nome_loja;  // Usar nome_loja como value
            option.textContent = loja.nome_loja;
            select.appendChild(option);
        });
    } catch (error) {
        console.error('Erro ao carregar lojas:', error);
    }
}

// Carregar categorias do banco de dados
async function carregarCategorias() {
    try {
        const response = await fetch('/api/categorias');
        const categorias = await response.json();
        const select = document.getElementById('categoria_banco');

        select.innerHTML = '';
        categorias.forEach(cat => {
            const option = document.createElement('option');
            option.value = cat;  // cat já é uma string
            option.textContent = cat;
            select.appendChild(option);
        });
    } catch (error) {
        console.error('Erro ao carregar categorias:', error);
    }
}

// Carregar produtos do banco de dados
async function carregarProdutos() {
    try {
        const response = await fetch('/api/produtos');
        const produtos = await response.json();
        const select = document.getElementById('produto_banco');

        select.innerHTML = '';
        produtos.forEach(prod => {
            const option = document.createElement('option');
            option.value = prod.descricao;  // Usar descrição como value
            option.textContent = prod.descricao;
            select.appendChild(option);
        });
    } catch (error) {
        console.error('Erro ao carregar produtos:', error);
    }
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
    const valoresAnoAnterior = resultado.ano_anterior?.valores || [];

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

    // Função auxiliar para calcular número da semana no ano
    function getWeekNumber(date) {
        const d = new Date(Date.UTC(date.getFullYear(), date.getMonth(), date.getDate()));
        const dayNum = d.getUTCDay() || 7;
        d.setUTCDate(d.getUTCDate() + 4 - dayNum);
        const yearStart = new Date(Date.UTC(d.getUTCFullYear(),0,1));
        return Math.ceil((((d - yearStart) / 86400000) + 1)/7);
    }

    // Criar cabeçalho com os períodos (meses, semanas ou dias)
    let headerHtml = `<tr style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; font-size: ${fontSize};">`;
    headerHtml += `<th style="padding: ${padding}; text-align: left; border: 1px solid #ddd; position: sticky; left: 0; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); z-index: 10; width: ${labelWidth};"></th>`;

    const meses = ['Jan', 'Fev', 'Mar', 'Abr', 'Mai', 'Jun', 'Jul', 'Ago', 'Set', 'Out', 'Nov', 'Dez'];

    previsoes.forEach((_, index) => {
        let nomePeriodo = '';
        if (datasPrevisao[index]) {
            const data = new Date(datasPrevisao[index]);
            if (granularidade === 'semanal') {
                // Para semanal, mostrar "SXX" (número da semana no ano)
                const semanaAno = getWeekNumber(data);
                nomePeriodo = `S${semanaAno}`;
            } else if (granularidade === 'diaria') {
                // Para diária, mostrar dia/mês
                nomePeriodo = `${data.getDate()}/${data.getMonth() + 1}`;
            } else {
                // Para mensal, mostrar Mês
                nomePeriodo = meses[data.getMonth()];
            }
        } else {
            nomePeriodo = `P${index + 1}`;
        }
        headerHtml += `<th style="padding: ${padding}; text-align: center; border: 1px solid #ddd;">${nomePeriodo}</th>`;
    });

    // Adicionar coluna TOTAL
    headerHtml += `<th style="padding: ${padding}; text-align: center; border: 1px solid #ddd; background: #5a67d8; font-weight: bold;">TOTAL</th>`;
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

    // Linha Real (Ano Anterior) - Limitar ao número de períodos de previsão
    let rowReal = `<tr style="background: white; font-size: ${fontSize};">`;
    rowReal += `<td style="padding: ${padding}; font-weight: bold; border: 1px solid #ddd; position: sticky; left: 0; background: white; z-index: 5; width: ${labelWidth};">Real</td>`;
    // Mostrar apenas os períodos correspondentes ao número de meses de previsão
    for (let i = 0; i < numPeriodos; i++) {
        const valor = valoresAnoAnterior[i] || 0;
        totalReal += valor;
        rowReal += `<td style="padding: ${padding}; text-align: center; border: 1px solid #ddd;">${formatNumber(valor)}</td>`;
    }
    rowReal += `<td style="padding: ${padding}; text-align: center; border: 1px solid #ddd; font-weight: bold; background: #f3f4f6;">${formatNumber(totalReal)}</td>`;
    rowReal += '</tr>';

    // Linha Variação
    let rowVariacao = `<tr style="background: #fef3c7; font-size: ${fontSize};">`;
    rowVariacao += `<td style="padding: ${padding}; font-weight: bold; border: 1px solid #ddd; position: sticky; left: 0; background: #fef3c7; z-index: 5; width: ${labelWidth};">Variação %</td>`;

    previsoes.forEach((valorPrevisao, index) => {
        const valorAnoAnterior = valoresAnoAnterior[index] || 0;
        const variacao = valorAnoAnterior > 0
            ? ((valorPrevisao - valorAnoAnterior) / valorAnoAnterior * 100)
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

// Criar gráfico de previsão simplificado com 3 linhas
function criarGraficoPrevisao(historicoBase, historicoTeste, modelos, melhorModelo, granularidade = 'mensal') {
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

    // Preparar dados da base histórica (50%)
    const datasBase = historicoBase.datas || [];
    const valoresBase = historicoBase.valores || [];

    // Preparar dados do período de teste (25%)
    const datasTeste = historicoTeste.datas || [];
    const valoresTeste = historicoTeste.valores || [];

    // Preparar dados de previsão do melhor modelo
    const previsaoTeste = modelos[melhorModelo]?.teste?.valores || [];
    const datasPrevisaoTeste = modelos[melhorModelo]?.teste?.datas || [];

    const previsaoFuturo = modelos[melhorModelo]?.futuro?.valores || [];
    const datasPrevisaoFuturo = modelos[melhorModelo]?.futuro?.datas || [];

    // Combinar todas as datas para criar labels
    const todasDatas = [...datasBase, ...datasTeste, ...datasPrevisaoFuturo];
    const meses = ['Jan', 'Fev', 'Mar', 'Abr', 'Mai', 'Jun', 'Jul', 'Ago', 'Set', 'Out', 'Nov', 'Dez'];

    // Formatar labels baseado na granularidade
    const labels = todasDatas.map(dataStr => {
        const data = new Date(dataStr);
        if (granularidade === 'semanal') {
            // Para semanal, mostrar "Sem XX" (número da semana no ano)
            const semanaAno = getWeekNumber(data);
            return `S${semanaAno}/${data.getFullYear().toString().slice(-2)}`;
        } else if (granularidade === 'diaria') {
            // Para diária, mostrar dia/mês
            return `${data.getDate()}/${data.getMonth() + 1}`;
        } else {
            // Para mensal, mostrar Mês/Ano
            return `${meses[data.getMonth()]}/${data.getFullYear().toString().slice(-2)}`;
        }
    });

    // Função auxiliar para calcular número da semana no ano
    function getWeekNumber(date) {
        const d = new Date(Date.UTC(date.getFullYear(), date.getMonth(), date.getDate()));
        const dayNum = d.getUTCDay() || 7;
        d.setUTCDate(d.getUTCDate() + 4 - dayNum);
        const yearStart = new Date(Date.UTC(d.getUTCFullYear(),0,1));
        return Math.ceil((((d - yearStart) / 86400000) + 1)/7);
    }

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

    // Calcular escala dinâmica do eixo Y
    const todosValores = [
        ...valoresBase,
        ...valoresTeste,
        ...previsaoTeste,
        ...previsaoFuturo
    ].filter(v => v !== null && v !== undefined);

    const valorMinimo = Math.min(...todosValores);
    const valorMaximo = Math.max(...todosValores);
    const amplitude = valorMaximo - valorMinimo;

    // Adicionar margem de 10% acima e abaixo para melhor visualização
    const margemInferior = valorMinimo - (amplitude * 0.10);
    const margemSuperior = valorMaximo + (amplitude * 0.10);

    // Garantir que não fique negativo se todos valores forem positivos
    const yMin = Math.max(0, margemInferior);
    const yMax = margemSuperior;

    // Configurar autoSkip baseado no número de períodos
    const totalPeriodos = labels.length;
    const autoSkipLabels = totalPeriodos > 50;  // Auto skip apenas se mais de 50 períodos

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
                        autoSkip: autoSkipLabels,  // Auto skip apenas para muitos períodos
                        maxTicksLimit: autoSkipLabels ? 20 : undefined  // Limitar a 20 se auto skip ativo
                    }
                }
            }
        }
    });
}

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
        const dados = {
            loja: document.getElementById('loja_banco').value,
            categoria: document.getElementById('categoria_banco').value,
            produto: document.getElementById('produto_banco').value,
            meses_previsao: parseInt(document.getElementById('meses_previsao_banco').value),
            granularidade: document.getElementById('granularidade_banco').value
        };

        console.log('Enviando dados:', dados);

        // Enviar requisição
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
            const metricasMelhor = resultado.metricas[melhorModelo] || {};

            // Calcular totais de previsão futura
            const previsaoFuturo = resultado.modelos[melhorModelo]?.futuro?.valores || [];
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

            // Criar gráfico principal com 3 linhas (base, teste, futuro)
            criarGraficoPrevisao(
                resultado.historico_base,
                resultado.historico_teste,
                resultado.modelos,
                melhorModelo,
                resultado.granularidade || 'mensal'  // Passar granularidade para formatação de labels
            );

            // Preencher tabela comparativa
            preencherTabelaComparativa(resultado, melhorModelo, resultado.granularidade || 'mensal');

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
    carregarCategorias();
    carregarProdutos();

    // Configurar listener para ajuste de limites
    const granularidadeSelect = document.getElementById('granularidade_banco');
    if (granularidadeSelect) {
        granularidadeSelect.addEventListener('change', ajustarLimitesPrevisao);
        ajustarLimitesPrevisao(); // Chamar uma vez para configurar valores iniciais
    }
});
