/**
 * Simulador de Cenários - JavaScript
 *
 * Gerencia a interface interativa do simulador:
 * - Carregamento de dados da previsão
 * - Aplicação de cenários (predefinidos e personalizados)
 * - Visualização de impacto
 * - Gráficos comparativos
 * - Exportação para Excel
 */

// Estado global
let dadosOriginais = null;
let dadosSimulados = null;
let graficoComparacao = null;

// ===========================
// INICIALIZAÇÃO
// ===========================

document.addEventListener('DOMContentLoaded', function() {
    console.log('🎯 Simulador de Cenários carregado');

    // Configurar sliders
    setupSliders();

    // Carregar dados
    carregarDados();
});

function setupSliders() {
    // Slider global
    const globalSlider = document.getElementById('globalSlider');
    const globalValue = document.getElementById('globalValue');

    globalSlider.addEventListener('input', function() {
        globalValue.textContent = `${this.value}%`;
    });

    // Slider por loja
    const lojaSlider = document.getElementById('lojaSlider');
    const lojaValue = document.getElementById('lojaValue');

    lojaSlider.addEventListener('input', function() {
        lojaValue.textContent = `${this.value}%`;
    });

    // Slider por SKU
    const skuSlider = document.getElementById('skuSlider');
    const skuValue = document.getElementById('skuValue');

    skuSlider.addEventListener('input', function() {
        skuValue.textContent = `${this.value}%`;
    });
}

// ===========================
// CARREGAMENTO DE DADOS
// ===========================

async function carregarDados() {
    console.log('📥 Carregando dados da previsão...');

    try {
        const response = await fetch('/simulador/dados');
        const result = await response.json();

        if (!result.success) {
            mostrarSemDados();
            return;
        }

        dadosOriginais = result.dados;
        dadosSimulados = JSON.parse(JSON.stringify(dadosOriginais)); // Deep copy

        console.log('✅ Dados carregados:', dadosOriginais);

        // Mostrar interface
        document.getElementById('loadingSim').style.display = 'none';
        document.getElementById('noDataAlert').style.display = 'none';
        document.getElementById('simulatorGrid').style.display = 'grid';

        // Popular dropdowns
        popularDropdowns();

        // Renderizar estado inicial
        renderizarEstado();

    } catch (erro) {
        console.error('❌ Erro ao carregar dados:', erro);
        mostrarSemDados();
    }
}

function mostrarSemDados() {
    document.getElementById('loadingSim').style.display = 'none';
    document.getElementById('simulatorGrid').style.display = 'none';
    document.getElementById('noDataAlert').style.display = 'block';
}

function popularDropdowns() {
    // Extrair lojas únicas
    const lojas = [...new Set(dadosOriginais.previsoes.map(p => p.loja))].sort();
    const lojaSelect = document.getElementById('lojaSelect');
    lojaSelect.innerHTML = lojas.map(loja =>
        `<option value="${loja}">${loja}</option>`
    ).join('');

    // Extrair SKUs únicos
    const skus = [...new Set(dadosOriginais.previsoes.map(p => p.sku))].sort();
    const skuSelect = document.getElementById('skuSelect');
    skuSelect.innerHTML = skus.map(sku =>
        `<option value="${sku}">${sku}</option>`
    ).join('');
}

// ===========================
// APLICAÇÃO DE CENÁRIOS
// ===========================

function aplicarCenarioPredefinido(tipo) {
    console.log(`🎯 Aplicando cenário: ${tipo}`);

    // Resetar para original
    dadosSimulados = JSON.parse(JSON.stringify(dadosOriginais));

    // Aplicar ajuste baseado no tipo
    switch(tipo) {
        case 'otimista':
            aplicarAjusteGlobalInterno(20);
            break;
        case 'pessimista':
            aplicarAjusteGlobalInterno(-20);
            break;
        case 'conservador':
            aplicarAjusteGlobalInterno(-10);
            break;
        case 'black_friday':
            aplicarAjustePorMesInterno(11, 50); // Novembro
            aplicarAjustePorMesInterno(12, 30); // Dezembro
            break;
        case 'verao':
            aplicarAjustePorMesInterno(1, 25);  // Janeiro
            aplicarAjustePorMesInterno(2, 25);  // Fevereiro
            break;
    }

    // Destacar botão ativo
    document.querySelectorAll('.scenario-btn').forEach(btn => {
        btn.classList.remove('active');
    });
    event.target.classList.add('active');

    // Resetar sliders
    resetarSliders();

    // Renderizar
    renderizarEstado();
}

function aplicarAjusteGlobal() {
    const percentual = parseFloat(document.getElementById('globalSlider').value);

    console.log(`🌐 Aplicando ajuste global: ${percentual}%`);

    // Resetar e aplicar
    dadosSimulados = JSON.parse(JSON.stringify(dadosOriginais));
    aplicarAjusteGlobalInterno(percentual);

    // Desmarcar cenários predefinidos
    document.querySelectorAll('.scenario-btn').forEach(btn => {
        btn.classList.remove('active');
    });

    renderizarEstado();
}

function aplicarAjustePorLoja() {
    const loja = document.getElementById('lojaSelect').value;
    const percentual = parseFloat(document.getElementById('lojaSlider').value);

    console.log(`🏪 Aplicando ajuste na loja ${loja}: ${percentual}%`);

    aplicarAjustePorLojaInterno(loja, percentual);
    renderizarEstado();
}

function aplicarAjustePorSKU() {
    const sku = document.getElementById('skuSelect').value;
    const percentual = parseFloat(document.getElementById('skuSlider').value);

    console.log(`📦 Aplicando ajuste no SKU ${sku}: ${percentual}%`);

    aplicarAjustePorSKUInterno(sku, percentual);
    renderizarEstado();
}

// ===========================
// FUNÇÕES INTERNAS DE AJUSTE
// ===========================

function aplicarAjusteGlobalInterno(percentual) {
    const fator = 1 + (percentual / 100);

    dadosSimulados.previsoes = dadosSimulados.previsoes.map(p => ({
        ...p,
        previsao: p.previsao * fator
    }));
}

function aplicarAjustePorLojaInterno(loja, percentual) {
    const fator = 1 + (percentual / 100);

    dadosSimulados.previsoes = dadosSimulados.previsoes.map(p => {
        if (p.loja === loja) {
            // Aplicar sobre o valor ORIGINAL, não o simulado atual
            const original = dadosOriginais.previsoes.find(
                orig => orig.loja === p.loja && orig.sku === p.sku && orig.mes === p.mes
            );
            return {
                ...p,
                previsao: original.previsao * fator
            };
        }
        return p;
    });
}

function aplicarAjustePorSKUInterno(sku, percentual) {
    const fator = 1 + (percentual / 100);

    dadosSimulados.previsoes = dadosSimulados.previsoes.map(p => {
        if (p.sku === sku) {
            const original = dadosOriginais.previsoes.find(
                orig => orig.loja === p.loja && orig.sku === p.sku && orig.mes === p.mes
            );
            return {
                ...p,
                previsao: original.previsao * fator
            };
        }
        return p;
    });
}

function aplicarAjustePorMesInterno(mesNumero, percentual) {
    const fator = 1 + (percentual / 100);

    dadosSimulados.previsoes = dadosSimulados.previsoes.map(p => {
        const mes = new Date(p.mes).getMonth() + 1; // 1-12

        if (mes === mesNumero) {
            return {
                ...p,
                previsao: p.previsao * fator
            };
        }
        return p;
    });
}

// ===========================
// RENDERIZAÇÃO
// ===========================

function renderizarEstado() {
    console.log('🎨 Renderizando estado atual...');

    // Calcular impacto
    const impacto = calcularImpacto();

    // Atualizar card de impacto
    atualizarCardImpacto(impacto);

    // Atualizar gráfico
    atualizarGrafico(impacto.por_mes);

    // Atualizar tabela
    atualizarTabela(impacto.por_mes);
}

function calcularImpacto() {
    // Total base
    const totalBase = dadosOriginais.previsoes.reduce((sum, p) => sum + p.previsao, 0);
    const totalSimulado = dadosSimulados.previsoes.reduce((sum, p) => sum + p.previsao, 0);

    const diferencaAbsoluta = totalSimulado - totalBase;
    const diferencaPercentual = totalBase > 0 ? ((totalSimulado / totalBase) - 1) * 100 : 0;

    // Por mês
    const mesesUnicos = [...new Set(dadosOriginais.previsoes.map(p => p.mes))].sort();

    const porMes = mesesUnicos.map(mes => {
        const baseM = dadosOriginais.previsoes
            .filter(p => p.mes === mes)
            .reduce((sum, p) => sum + p.previsao, 0);

        const simM = dadosSimulados.previsoes
            .filter(p => p.mes === mes)
            .reduce((sum, p) => sum + p.previsao, 0);

        return {
            mes: mes,
            base: baseM,
            simulado: simM,
            diferenca: simM - baseM,
            percentual: baseM > 0 ? ((simM / baseM) - 1) * 100 : 0
        };
    });

    return {
        total: {
            base: totalBase,
            simulado: totalSimulado,
            diferenca_absoluta: diferencaAbsoluta,
            diferenca_percentual: diferencaPercentual
        },
        por_mes: porMes
    };
}

function atualizarCardImpacto(impacto) {
    const card = document.getElementById('impactoCard');
    card.style.display = 'block';

    const { total } = impacto;

    // Título com percentual
    document.getElementById('impactoPercentual').textContent =
        `${total.diferenca_percentual >= 0 ? '+' : ''}${total.diferenca_percentual.toFixed(1)}%`;

    // Descrição
    let descricao = 'Cenário Personalizado';
    const activeBtn = document.querySelector('.scenario-btn.active');
    if (activeBtn) {
        descricao = activeBtn.textContent.trim();
    }
    document.getElementById('impactoDescricao').textContent = descricao;

    // Valores
    document.getElementById('totalBase').textContent = Math.round(total.base).toLocaleString('pt-BR');
    document.getElementById('totalSimulado').textContent = Math.round(total.simulado).toLocaleString('pt-BR');
    document.getElementById('diferencaAbsoluta').textContent =
        `${total.diferenca_absoluta >= 0 ? '+' : ''}${Math.round(total.diferenca_absoluta).toLocaleString('pt-BR')}`;

    const percElem = document.getElementById('diferencaPercentual');
    percElem.textContent = `${total.diferenca_percentual >= 0 ? '+' : ''}${total.diferenca_percentual.toFixed(1)}%`;
    percElem.className = total.diferenca_percentual >= 0 ? 'value positive' : 'value negative';
}

function atualizarGrafico(dadosPorMes) {
    const ctx = document.getElementById('comparisonChart').getContext('2d');

    // Destruir gráfico anterior se existir
    if (graficoComparacao) {
        graficoComparacao.destroy();
    }

    const labels = dadosPorMes.map(d => {
        const data = new Date(d.mes);
        return data.toLocaleDateString('pt-BR', { month: 'short', year: 'numeric' });
    });

    const datasetsBase = dadosPorMes.map(d => d.base);
    const datasetsSimulado = dadosPorMes.map(d => d.simulado);

    graficoComparacao = new Chart(ctx, {
        type: 'line',
        data: {
            labels: labels,
            datasets: [
                {
                    label: 'Previsão Base',
                    data: datasetsBase,
                    borderColor: '#6c757d',
                    backgroundColor: 'rgba(108, 117, 125, 0.1)',
                    borderWidth: 2,
                    pointRadius: 4,
                    pointHoverRadius: 6,
                    borderDash: [5, 5]
                },
                {
                    label: 'Previsão Simulada',
                    data: datasetsSimulado,
                    borderColor: '#667eea',
                    backgroundColor: 'rgba(102, 126, 234, 0.1)',
                    borderWidth: 3,
                    pointRadius: 5,
                    pointHoverRadius: 7,
                    fill: true
                }
            ]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            interaction: {
                mode: 'index',
                intersect: false
            },
            plugins: {
                legend: {
                    display: true,
                    position: 'top'
                },
                tooltip: {
                    callbacks: {
                        label: function(context) {
                            return `${context.dataset.label}: ${Math.round(context.parsed.y).toLocaleString('pt-BR')}`;
                        }
                    }
                }
            },
            scales: {
                y: {
                    beginAtZero: true,
                    ticks: {
                        callback: function(value) {
                            return value.toLocaleString('pt-BR');
                        }
                    }
                }
            }
        }
    });
}

function atualizarTabela(dadosPorMes) {
    const tbody = document.getElementById('comparisonTableBody');

    tbody.innerHTML = dadosPorMes.map(d => {
        const mesFormatado = new Date(d.mes).toLocaleDateString('pt-BR', {
            month: 'short',
            year: 'numeric'
        });

        const classeDif = d.diferenca >= 0 ? 'positive' : 'negative';
        const sinalDif = d.diferenca >= 0 ? '+' : '';
        const sinalPerc = d.percentual >= 0 ? '+' : '';

        return `
            <tr>
                <td><strong>${mesFormatado}</strong></td>
                <td>${Math.round(d.base).toLocaleString('pt-BR')}</td>
                <td>${Math.round(d.simulado).toLocaleString('pt-BR')}</td>
                <td class="${classeDif}">${sinalDif}${Math.round(d.diferenca).toLocaleString('pt-BR')}</td>
                <td class="${classeDif}">${sinalPerc}${d.percentual.toFixed(1)}%</td>
            </tr>
        `;
    }).join('');
}

// ===========================
// AÇÕES
// ===========================

function resetarCenario() {
    console.log('🔄 Resetando para cenário original...');

    // Resetar dados
    dadosSimulados = JSON.parse(JSON.stringify(dadosOriginais));

    // Resetar sliders
    resetarSliders();

    // Desmarcar cenários
    document.querySelectorAll('.scenario-btn').forEach(btn => {
        btn.classList.remove('active');
    });

    // Renderizar
    renderizarEstado();
}

function resetarSliders() {
    document.getElementById('globalSlider').value = 0;
    document.getElementById('globalValue').textContent = '0%';

    document.getElementById('lojaSlider').value = 0;
    document.getElementById('lojaValue').textContent = '0%';

    document.getElementById('skuSlider').value = 0;
    document.getElementById('skuValue').textContent = '0%';
}

async function exportarCenario() {
    console.log('💾 Exportando cenário para Excel...');

    try {
        const response = await fetch('/simulador/exportar', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                previsoes_simuladas: dadosSimulados.previsoes
            })
        });

        if (response.ok) {
            // Download do arquivo
            const blob = await response.blob();
            const url = window.URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = `cenario_simulado_${new Date().toISOString().slice(0,10)}.xlsx`;
            document.body.appendChild(a);
            a.click();
            a.remove();
            window.URL.revokeObjectURL(url);

            console.log('✅ Arquivo exportado com sucesso');
        } else {
            const error = await response.json();
            console.error('❌ Erro ao exportar:', error);
            alert('Erro ao exportar cenário. Veja o console para detalhes.');
        }

    } catch (erro) {
        console.error('❌ Erro ao exportar:', erro);
        alert('Erro ao exportar cenário. Veja o console para detalhes.');
    }
}
