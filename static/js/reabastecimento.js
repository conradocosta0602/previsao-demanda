// Reabastecimento.js - Sistema de Reabastecimento Inteligente

let dadosCompletos = [];
let itensUrgentes = [];

// Mapeamento de nomes técnicos para nomenclatura do documento
const METODOS_NOMENCLATURA = {
    'sma': 'SMA (Média Móvel Simples)',
    'wma': 'WMA (Média Móvel Ponderada)',
    'ema': 'EMA (Média Móvel Exponencial)',
    'tendencia': 'Regressão com Tendência',
    'sazonal': 'Decomposição Sazonal',
    'tsb': 'TSB (Teunter-Syntetos-Babai)',
    'ultimo': 'Última Venda',
    'auto_estavel': 'AUTO (Seleção Automática)',
    'nenhum': 'Sem Dados'
};

document.getElementById('uploadForm').addEventListener('submit', async (e) => {
    e.preventDefault();

    const formData = new FormData();
    const fileInput = document.getElementById('file');
    const modoCalculo = document.getElementById('modo_calculo').value;
    const nivelServico = document.getElementById('nivel_servico').value;
    const revisaoDias = document.getElementById('revisao_dias').value;

    formData.append('file', fileInput.files[0]);
    formData.append('modo_calculo', modoCalculo);
    formData.append('nivel_servico', nivelServico);
    formData.append('revisao_dias', revisaoDias);

    // Mostrar progresso
    document.getElementById('progress').style.display = 'block';
    document.getElementById('results').style.display = 'none';
    document.getElementById('error').style.display = 'none';

    try {
        // Simular progresso
        let progress = 0;
        const progressInterval = setInterval(() => {
            progress += 10;
            if (progress <= 90) {
                document.getElementById('progressFill').style.width = progress + '%';
                document.getElementById('progressText').textContent =
                    `Processando reabastecimento... ${progress}%`;
            }
        }, 200);

        const response = await fetch('/processar_reabastecimento_v3', {
            method: 'POST',
            body: formData
        });

        clearInterval(progressInterval);
        document.getElementById('progressFill').style.width = '100%';
        document.getElementById('progressText').textContent = 'Concluído!';

        if (!response.ok) {
            const errorData = await response.json();
            throw new Error(errorData.erro || 'Erro ao processar arquivo');
        }

        const data = await response.json();

        // Verificar se há resultados
        if (!data.resultados || Object.keys(data.resultados).length === 0) {
            throw new Error('Nenhum resultado foi processado. Verifique se o arquivo possui as abas corretas (PEDIDOS_FORNECEDOR, PEDIDOS_CD ou TRANSFERENCIAS).');
        }

        // Armazenar dados (consolidar todos os fluxos)
        dadosCompletos = consolidarDadosFluxos(data.resultados);
        itensUrgentes = extrairItensUrgentes(dadosCompletos);

        // Exibir resultados
        setTimeout(() => {
            document.getElementById('progress').style.display = 'none';
            document.getElementById('results').style.display = 'block';

            exibirResumoMultifluxo(data.resultados);
            exibirAlertasMultifluxo(data.resultados);
            exibirItensUrgentes(itensUrgentes);
            exibirResultadosCompletos(dadosCompletos);

            // Configurar downloads (múltiplos arquivos)
            configurarDownloads(data.arquivos_gerados);
        }, 500);

    } catch (error) {
        document.getElementById('progress').style.display = 'none';
        document.getElementById('error').style.display = 'block';
        document.getElementById('errorMessage').textContent = error.message;
    }
});

// Consolidar dados de todos os fluxos em um único array
function consolidarDadosFluxos(resultados) {
    let todosItens = [];

    for (const [fluxo, dados] of Object.entries(resultados)) {
        if (dados.dados_tabela && Array.isArray(dados.dados_tabela)) {
            // Adicionar identificador do fluxo a cada item
            const itensComFluxo = dados.dados_tabela.map(item => ({
                ...item,
                Fluxo: fluxo.replace('_', ' ')
            }));
            todosItens = todosItens.concat(itensComFluxo);
        }
    }

    return todosItens;
}

// Extrair os 10 itens mais urgentes
function extrairItensUrgentes(dados) {
    // Filtrar itens com risco de ruptura ou que devem pedir
    const urgentes = dados.filter(item =>
        item.Risco_Ruptura === 'Sim' || item.Deve_Pedir === 'Sim'
    );

    // Ordenar por cobertura atual (menor primeiro)
    urgentes.sort((a, b) => a.Cobertura_Atual_Dias - b.Cobertura_Atual_Dias);

    // Retornar top 10
    return urgentes.slice(0, 10);
}

// Exibir resumo consolidado de múltiplos fluxos
function exibirResumoMultifluxo(resultados) {
    let totalItens = 0;
    let totalAPedir = 0;
    let totalEmRisco = 0;
    let somaCobertura = 0;
    let countCobertura = 0;

    for (const [fluxo, dados] of Object.entries(resultados)) {
        if (dados.resumo) {
            totalItens += dados.resumo.total_itens || 0;
            totalAPedir += dados.resumo.total_a_pedir || 0;
            totalEmRisco += dados.resumo.total_em_risco || 0;

            if (dados.resumo.cobertura_media_dias) {
                somaCobertura += dados.resumo.cobertura_media_dias * dados.resumo.total_itens;
                countCobertura += dados.resumo.total_itens;
            }
        }
    }

    const coberturaMedia = countCobertura > 0 ? (somaCobertura / countCobertura) : 0;
    const percentualPedir = totalItens > 0 ? ((totalAPedir / totalItens) * 100).toFixed(1) : 0;
    const percentualRisco = totalItens > 0 ? ((totalEmRisco / totalItens) * 100).toFixed(1) : 0;

    // Exibir resumo por fluxo
    let fluxosHtml = '';
    const nomeFluxos = {
        'PEDIDOS_FORNECEDOR': '📦 Fornecedor',
        'PEDIDOS_CD': '🏢 CD → Lojas',
        'TRANSFERENCIAS': '🔄 Transferências'
    };

    for (const [fluxo, dados] of Object.entries(resultados)) {
        const nomeFluxo = nomeFluxos[fluxo] || fluxo;
        const itens = dados.resumo?.total_itens || 0;
        const pedir = dados.resumo?.total_a_pedir || 0;

        fluxosHtml += `
            <div style="background: #f8f9fa; padding: 8px; border-radius: 4px; margin-bottom: 6px;">
                <strong>${nomeFluxo}:</strong> ${itens} itens (${pedir} a pedir)
            </div>
        `;
    }

    document.getElementById('resumo').innerHTML = `
        <div class="resumo-card-compact">
            <h4>Total de Itens</h4>
            <p class="big-number-compact">${totalItens}</p>
            <div style="margin-top: 8px; font-size: 0.75em;">
                ${fluxosHtml}
            </div>
        </div>
        <div class="resumo-card-compact">
            <h4>Itens a Pedir</h4>
            <p class="big-number-compact">${totalAPedir}</p>
            <p style="font-size: 0.7em; color: #666; margin-top: 4px;">${percentualPedir}% do total</p>
        </div>
        <div class="resumo-card-compact">
            <h4>Itens em Risco</h4>
            <p class="big-number-compact" style="color: ${totalEmRisco > 0 ? '#dc3545' : '#11998e'};">${totalEmRisco}</p>
            <p style="font-size: 0.7em; color: #666; margin-top: 4px;">${percentualRisco}% do total</p>
        </div>
        <div class="resumo-card-compact">
            <h4>Cobertura Média</h4>
            <p class="big-number-compact">${coberturaMedia.toFixed(1)}</p>
            <p style="font-size: 0.7em; color: #666; margin-top: 4px;">dias</p>
        </div>
    `;
}

// Exibir alertas consolidados
function exibirAlertasMultifluxo(resultados) {
    const alertasHtml = [];

    let totalEmRisco = 0;
    let totalAPedir = 0;

    for (const [fluxo, dados] of Object.entries(resultados)) {
        if (dados.resumo) {
            totalEmRisco += dados.resumo.total_em_risco || 0;
            totalAPedir += dados.resumo.total_a_pedir || 0;
        }
    }

    if (totalEmRisco > 0) {
        alertasHtml.push(`
            <div class="alerta error">
                <strong>⚠️ Atenção:</strong> ${totalEmRisco} itens com risco de ruptura nos próximos 7 dias!
            </div>
        `);
    }

    if (totalAPedir > 0) {
        alertasHtml.push(`
            <div class="alerta warning">
                <strong>📦 Ação Necessária:</strong> ${totalAPedir} itens precisam de reabastecimento.
            </div>
        `);
    }

    if (totalEmRisco === 0 && totalAPedir === 0) {
        alertasHtml.push(`
            <div class="alerta info">
                <strong>✅ Estoque Saudável:</strong> Todos os itens estão com níveis adequados de estoque.
            </div>
        `);
    }

    document.getElementById('alertas').innerHTML = alertasHtml.join('');
}

// Configurar downloads múltiplos
function configurarDownloads(arquivos) {
    if (!arquivos || arquivos.length === 0) {
        document.getElementById('downloadBtn').style.display = 'none';
        return;
    }

    // Se houver apenas um arquivo, mostrar botão simples
    if (arquivos.length === 1) {
        document.getElementById('downloadBtn').href = `/download/${arquivos[0]}`;
        document.getElementById('downloadBtn').style.display = 'inline-block';
        document.getElementById('downloadBtn').textContent = '📥 Download Excel Completo';
    } else {
        // Se houver múltiplos arquivos, criar lista de downloads
        const downloadSection = document.querySelector('.download-section-compact');
        const nomeFluxos = {
            'fornecedor': '📦 Pedidos Fornecedor',
            'cd': '🏢 Pedidos CD',
            'transferencias': '🔄 Transferências'
        };

        let html = '<h4 style="margin-bottom: 10px;">📥 Downloads Disponíveis:</h4>';

        arquivos.forEach(arquivo => {
            let nomeExibicao = 'Download';

            // Identificar tipo de arquivo pelo nome
            for (const [tipo, nome] of Object.entries(nomeFluxos)) {
                if (arquivo.toLowerCase().includes(tipo)) {
                    nomeExibicao = nome;
                    break;
                }
            }

            html += `
                <a href="/download/${arquivo}" class="btn-download-compact" download style="display: block; margin-bottom: 8px;">
                    ${nomeExibicao}
                </a>
            `;
        });

        downloadSection.innerHTML = html;
    }
}

function exibirResumo(resumo) {
    const percentualPedir = ((resumo.total_a_pedir / resumo.total_itens) * 100).toFixed(1);
    const percentualRisco = ((resumo.total_em_risco / resumo.total_itens) * 100).toFixed(1);

    document.getElementById('resumo').innerHTML = `
        <div class="resumo-card-compact">
            <h4>Total de Itens</h4>
            <p class="big-number-compact">${resumo.total_itens}</p>
        </div>
        <div class="resumo-card-compact">
            <h4>Itens a Pedir</h4>
            <p class="big-number-compact">${resumo.total_a_pedir}</p>
            <p style="font-size: 0.7em; color: #666; margin-top: 4px;">${percentualPedir}% do total</p>
        </div>
        <div class="resumo-card-compact">
            <h4>Itens em Risco</h4>
            <p class="big-number-compact" style="color: ${resumo.total_em_risco > 0 ? '#dc3545' : '#11998e'};">${resumo.total_em_risco}</p>
            <p style="font-size: 0.7em; color: #666; margin-top: 4px;">${percentualRisco}% do total</p>
        </div>
        <div class="resumo-card-compact">
            <h4>Cobertura Média</h4>
            <p class="big-number-compact">${resumo.cobertura_media_dias.toFixed(1)}</p>
            <p style="font-size: 0.7em; color: #666; margin-top: 4px;">dias</p>
        </div>
    `;
}

function exibirAlertas(resumo) {
    const alertasHtml = [];

    if (resumo.total_em_risco > 0) {
        alertasHtml.push(`
            <div class="alerta error">
                <strong>⚠️ Atenção:</strong> ${resumo.total_em_risco} itens com risco de ruptura nos próximos 7 dias!
            </div>
        `);
    }

    if (resumo.total_a_pedir > 0) {
        alertasHtml.push(`
            <div class="alerta warning">
                <strong>📦 Ação Necessária:</strong> ${resumo.total_a_pedir} itens precisam de reabastecimento.
            </div>
        `);
    }

    if (resumo.total_em_risco === 0 && resumo.total_a_pedir === 0) {
        alertasHtml.push(`
            <div class="alerta info">
                <strong>✅ Estoque Saudável:</strong> Todos os itens estão com níveis adequados de estoque.
            </div>
        `);
    }

    document.getElementById('alertas').innerHTML = alertasHtml.join('');
}

function exibirItensUrgentes(itens) {
    const tbody = document.getElementById('urgentesBody');

    if (!itens || itens.length === 0) {
        tbody.innerHTML = '<tr><td colspan="7" style="text-align: center; padding: 20px; color: #666;">Nenhum item urgente encontrado</td></tr>';
        return;
    }

    tbody.innerHTML = itens.map(item => {
        const riscoClass = item.Risco_Ruptura === 'Sim' ? 'style="background-color: #f8d7da;"' : '';
        const coberturaColor = item.Cobertura_Atual_Dias < 7 ? '#dc3545' : '#11998e';

        return `
            <tr ${riscoClass}>
                <td style="padding: 8px; border-bottom: 1px solid #eee;">${item.Loja}</td>
                <td style="padding: 8px; border-bottom: 1px solid #eee;">${item.SKU}</td>
                <td style="padding: 8px; text-align: right; border-bottom: 1px solid #eee;">${item.Estoque_Disponivel}</td>
                <td style="padding: 8px; text-align: right; border-bottom: 1px solid #eee;">${item.Ponto_Pedido}</td>
                <td style="padding: 8px; text-align: right; border-bottom: 1px solid #eee; font-weight: bold;">${item.Quantidade_Pedido}</td>
                <td style="padding: 8px; text-align: right; border-bottom: 1px solid #eee; color: ${coberturaColor}; font-weight: bold;">${item.Cobertura_Atual_Dias}</td>
                <td style="padding: 8px; text-align: center; border-bottom: 1px solid #eee;">
                    ${item.Risco_Ruptura === 'Sim' ? '<span style="color: #dc3545;">⚠️ Sim</span>' : '<span style="color: #11998e;">✓ Não</span>'}
                </td>
            </tr>
        `;
    }).join('');
}

function exibirResultadosCompletos(resultados) {
    renderizarTabela(resultados);

    // Event listeners para filtros
    document.getElementById('filtroRisco').addEventListener('change', aplicarFiltros);
    document.getElementById('filtroPedir').addEventListener('change', aplicarFiltros);
}

function aplicarFiltros() {
    const filtroRisco = document.getElementById('filtroRisco').value;
    const filtroPedir = document.getElementById('filtroPedir').value;

    let resultadosFiltrados = [...dadosCompletos];

    // Filtrar por risco
    if (filtroRisco === 'risco') {
        resultadosFiltrados = resultadosFiltrados.filter(item => item.Risco_Ruptura === 'Sim');
    } else if (filtroRisco === 'sem_risco') {
        resultadosFiltrados = resultadosFiltrados.filter(item => item.Risco_Ruptura === 'Não');
    }

    // Filtrar por deve pedir
    if (filtroPedir === 'sim') {
        resultadosFiltrados = resultadosFiltrados.filter(item => item.Deve_Pedir === 'Sim');
    } else if (filtroPedir === 'nao') {
        resultadosFiltrados = resultadosFiltrados.filter(item => item.Deve_Pedir === 'Não');
    }

    renderizarTabela(resultadosFiltrados);
}

function renderizarTabela(resultados) {
    const tbody = document.getElementById('resultadosBody');

    if (!resultados || resultados.length === 0) {
        tbody.innerHTML = '<tr><td colspan="15" style="text-align: center; padding: 20px; color: #666;">Nenhum resultado encontrado com os filtros selecionados</td></tr>';
        return;
    }

    tbody.innerHTML = resultados.map(item => {
        const riscoClass = item.Risco_Ruptura === 'Sim' ? 'style="background-color: #f8d7da;"' : '';
        const coberturaAtualColor = item.Cobertura_Atual_Dias < 7 ? '#dc3545' : item.Cobertura_Atual_Dias < 15 ? '#ffc107' : '#11998e';
        const coberturaPedidoColor = item.Cobertura_Com_Pedido_Dias < 15 ? '#ffc107' : '#11998e';

        // Formatar nome do método usando nomenclatura do documento
        const metodoTecnico = (item.Metodo_Usado || 'nenhum').toLowerCase();
        const metodoFormatado = METODOS_NOMENCLATURA[metodoTecnico] || item.Metodo_Usado || 'N/A';

        // Cores por tipo de fluxo
        const fluxoCores = {
            'PEDIDOS FORNECEDOR': '#e3f2fd',
            'PEDIDOS CD': '#f3e5f5',
            'TRANSFERENCIAS': '#fff3e0'
        };
        const fluxoColor = fluxoCores[item.Fluxo] || '#f5f5f5';

        return `
            <tr ${riscoClass}>
                <td style="padding: 6px; border-bottom: 1px solid #eee;">
                    <span style="background: ${fluxoColor}; padding: 2px 6px; border-radius: 4px; font-size: 0.75em; white-space: nowrap;">${item.Fluxo || 'N/A'}</span>
                </td>
                <td style="padding: 6px; border-bottom: 1px solid #eee;">${item.Loja || item.Destino || 'N/A'}</td>
                <td style="padding: 6px; border-bottom: 1px solid #eee;">${item.SKU}</td>
                <td style="padding: 6px; text-align: right; border-bottom: 1px solid #eee;">${item.Demanda_Media_Mensal ? item.Demanda_Media_Mensal.toFixed(1) : 'N/A'}</td>
                <td style="padding: 6px; text-align: right; border-bottom: 1px solid #eee;">${item.Estoque_Disponivel || 0}</td>
                <td style="padding: 6px; text-align: right; border-bottom: 1px solid #eee;">${item.Estoque_Transito || 0}</td>
                <td style="padding: 6px; text-align: right; border-bottom: 1px solid #eee; font-weight: bold;">${item.Estoque_Efetivo || 0}</td>
                <td style="padding: 6px; text-align: right; border-bottom: 1px solid #eee; background-color: #f0fdf4;">${item.Ponto_Pedido || 0}</td>
                <td style="padding: 6px; text-align: right; border-bottom: 1px solid #eee;">${item.Estoque_Seguranca || 0}</td>
                <td style="padding: 6px; text-align: right; border-bottom: 1px solid #eee; font-weight: bold; color: ${item.Quantidade_Pedido > 0 ? '#11998e' : '#666'};">${item.Quantidade_Pedido || 0}</td>
                <td style="padding: 6px; text-align: right; border-bottom: 1px solid #eee; color: ${coberturaAtualColor}; font-weight: bold;">${item.Cobertura_Atual_Dias || 0}</td>
                <td style="padding: 6px; text-align: right; border-bottom: 1px solid #eee; color: ${coberturaPedidoColor};">${item.Cobertura_Com_Pedido_Dias || 0}</td>
                <td style="padding: 6px; text-align: center; border-bottom: 1px solid #eee;">
                    ${item.Risco_Ruptura === 'Sim' ? '<span style="color: #dc3545; font-weight: bold;">⚠️</span>' : '<span style="color: #11998e;">✓</span>'}
                </td>
                <td style="padding: 6px; text-align: center; border-bottom: 1px solid #eee;">
                    ${item.Deve_Pedir === 'Sim' ? '<span style="color: #11998e; font-weight: bold;">✓</span>' : '<span style="color: #666;">-</span>'}
                </td>
                <td style="padding: 6px; border-bottom: 1px solid #eee; font-size: 0.75em; color: #666;">
                    <span style="background: #e3f2fd; padding: 2px 6px; border-radius: 4px; white-space: nowrap;">${metodoFormatado}</span>
                </td>
            </tr>
        `;
    }).join('');
}
