// pedido_cd.js - Processamento de Pedidos CD → Lojas

document.getElementById('uploadForm').addEventListener('submit', async (e) => {
    e.preventDefault();

    const formData = new FormData();
    const fileInput = document.getElementById('file');

    formData.append('file', fileInput.files[0]);

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
                    `Processando pedidos... ${progress}%`;
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

        // Verificar se há resultados para PEDIDOS_CD
        if (!data.resultados || !data.resultados.PEDIDOS_CD) {
            throw new Error('Nenhum resultado encontrado. Verifique se o arquivo possui a aba PEDIDOS_CD e HISTORICO_VENDAS.');
        }

        const resultado = data.resultados.PEDIDOS_CD;

        // Exibir resultados
        setTimeout(() => {
            document.getElementById('progress').style.display = 'none';
            document.getElementById('results').style.display = 'block';

            exibirResumo(resultado.resumo);
            exibirAlertas(resultado.resumo, resultado.dados_tabela);
            exibirResultados(resultado.dados_tabela);

            // Configurar download
            const arquivoCD = data.arquivos_gerados.find(a =>
                a.toLowerCase().includes('cd')
            );
            if (arquivoCD) {
                document.getElementById('downloadBtn').href = `/download/${arquivoCD}`;
            }
        }, 500);

    } catch (error) {
        document.getElementById('progress').style.display = 'none';
        document.getElementById('error').style.display = 'block';
        document.getElementById('errorMessage').textContent = error.message;
    }
});

function exibirResumo(resumo) {
    const html = `
        <div class="resumo-card-compact">
            <h4>Total de Itens</h4>
            <p class="big-number-compact">${resumo.total_itens || 0}</p>
        </div>
        <div class="resumo-card-compact">
            <h4>Itens a Distribuir</h4>
            <p class="big-number-compact">${resumo.total_a_pedir || 0}</p>
        </div>
        <div class="resumo-card-compact">
            <h4>Valor Total Estimado</h4>
            <p class="big-number-compact">R$ ${(resumo.valor_total || 0).toLocaleString('pt-BR', {minimumFractionDigits: 2})}</p>
        </div>
    `;
    document.getElementById('resumo').innerHTML = html;
}

function exibirAlertas(resumo, dados) {
    const alertasHtml = [];

    // Verificar alertas de falta no CD
    const semEstoqueCD = dados.filter(item =>
        item.Alerta && item.Alerta.includes('CD sem estoque')
    ).length;

    if (semEstoqueCD > 0) {
        alertasHtml.push(`
            <div class="alerta error">
                <strong>⚠️ Atenção:</strong> ${semEstoqueCD} itens sem estoque suficiente no CD!
            </div>
        `);
    }

    if (resumo.total_em_risco > 0) {
        alertasHtml.push(`
            <div class="alerta warning">
                <strong>📦 Urgente:</strong> ${resumo.total_em_risco} lojas com risco de ruptura.
            </div>
        `);
    }

    if (resumo.total_a_pedir > 0) {
        alertasHtml.push(`
            <div class="alerta info">
                <strong>✓ Ação:</strong> ${resumo.total_a_pedir} itens prontos para distribuição.
            </div>
        `);
    }

    if (alertasHtml.length === 0) {
        alertasHtml.push(`
            <div class="alerta info">
                <strong>✅ Tudo OK:</strong> Lojas com estoque adequado.
            </div>
        `);
    }

    document.getElementById('alertas').innerHTML = alertasHtml.join('');
}

function exibirResultados(dados) {
    const tbody = document.getElementById('resultadosBody');

    if (!dados || dados.length === 0) {
        tbody.innerHTML = '<tr><td colspan="13" style="text-align: center; padding: 20px;">Nenhuma distribuição necessária</td></tr>';
        return;
    }

    // Agrupar dados por loja
    const porLoja = {};
    dados.forEach(item => {
        const loja = item.Loja_Destino || item.Destino || 'N/A';
        if (!porLoja[loja]) {
            porLoja[loja] = [];
        }
        porLoja[loja].push(item);
    });

    let html = '';

    // Para cada loja
    Object.keys(porLoja).sort().forEach(loja => {
        const itensLoja = porLoja[loja];

        // Calcular totalizadores da loja
        let valorTotalEstoque = 0;
        let valorTotalPedido = 0;
        let temCustoInformado = itensLoja.some(item => (item.Custo_Unitario || 0) > 0);

        itensLoja.forEach(item => {
            const custo = item.Custo_Unitario || 0;
            // Valor do estoque: TODOS os itens com estoque no destino
            valorTotalEstoque += (item.Estoque_Loja || 0) * custo;
            // Valor do pedido: APENAS itens que devem ser pedidos
            if (item.Deve_Pedir === 'Sim') {
                valorTotalPedido += (item.Quantidade_Pedido || 0) * custo;
            }
        });

        const itensAPedir = itensLoja.filter(item => item.Deve_Pedir === 'Sim').length;

        // Cobertura atual ponderada
        let coberturaAtualTotal = 0;
        let coberturaProjetadaTotal = 0;
        let rupturaAtual = 0;
        let pesoTotal = 0;

        itensLoja.forEach(item => {
            // Backend envia demanda mensal, converter para diária
            const demandaMensal = item.Demanda_Media_Mensal || 0;
            const demandaDiaria = demandaMensal / 30;
            if (demandaDiaria > 0) {
                coberturaAtualTotal += (item.Cobertura_Dias_Atual || 0) * demandaDiaria;
                coberturaProjetadaTotal += (item.Cobertura_Dias_Apos_Pedido || 0) * demandaDiaria;
                pesoTotal += demandaDiaria;
            }
            if (item.Risco_Ruptura === 'Sim') {
                rupturaAtual++;
            }
        });

        const coberturaAtual = pesoTotal > 0 ? coberturaAtualTotal / pesoTotal : 0;
        const coberturaProjetada = pesoTotal > 0 ? coberturaProjetadaTotal / pesoTotal : 0;

        // Linha de cabeçalho da loja com totalizadores
        html += `
            <tr style="background: linear-gradient(135deg, #6C757D 0%, #495057 100%); color: white;">
                <td colspan="13" style="padding: 12px; font-weight: bold; font-size: 1.1em;">
                    🏢 ${loja}
                    <div style="display: grid; grid-template-columns: ${temCustoInformado ? 'repeat(5, 1fr)' : 'repeat(4, 1fr)'}; gap: 10px; margin-top: 8px; font-size: 0.85em; font-weight: normal;">
                        ${temCustoInformado ? `
                        <div>
                            <div style="opacity: 0.8; font-size: 0.9em;">Valor Estoque</div>
                            <div style="font-weight: bold;">R$ ${valorTotalEstoque.toLocaleString('pt-BR', {minimumFractionDigits: 2})}</div>
                        </div>
                        <div>
                            <div style="opacity: 0.8; font-size: 0.9em;">Valor Pedido</div>
                            <div style="font-weight: bold;">R$ ${valorTotalPedido.toLocaleString('pt-BR', {minimumFractionDigits: 2})}</div>
                        </div>
                        ` : ''}
                        <div>
                            <div style="opacity: 0.8; font-size: 0.9em;">Cobertura Atual</div>
                            <div style="font-weight: bold;">${coberturaAtual.toFixed(1)} dias</div>
                        </div>
                        <div>
                            <div style="opacity: 0.8; font-size: 0.9em;">Cobertura Projetada</div>
                            <div style="font-weight: bold;">${coberturaProjetada.toFixed(1)} dias</div>
                        </div>
                        <div>
                            <div style="opacity: 0.8; font-size: 0.9em;">Itens a Pedir</div>
                            <div style="font-weight: bold;">${itensAPedir} de ${itensLoja.length}</div>
                        </div>
                        <div>
                            <div style="opacity: 0.8; font-size: 0.9em;">Ruptura Atual</div>
                            <div style="font-weight: bold; color: ${rupturaAtual > 0 ? '#ffeb3b' : '#4caf50'};">${rupturaAtual} itens</div>
                        </div>
                    </div>
                </td>
            </tr>
        `;

        // Cabeçalho da tabela repetido para cada loja
        html += `
            <tr style="background: #F8F9FA; color: #6C757D; font-weight: bold; font-size: 0.85em;">
                <th style="padding: 8px; text-align: left; border-bottom: 2px solid #6C757D;">CD Origem</th>
                <th style="padding: 8px; text-align: left; border-bottom: 2px solid #6C757D;">SKU</th>
                <th style="padding: 8px; text-align: right; border-bottom: 2px solid #6C757D;">Demanda Diária</th>
                <th style="padding: 8px; text-align: right; border-bottom: 2px solid #6C757D;">Estoque Loja</th>
                <th style="padding: 8px; text-align: right; border-bottom: 2px solid #6C757D;">Estoque CD</th>
                <th style="padding: 8px; text-align: right; border-bottom: 2px solid #6C757D;">Em Trânsito</th>
                <th style="padding: 8px; text-align: center; border-bottom: 2px solid #6C757D;">Nível Serviço</th>
                <th style="padding: 8px; text-align: right; border-bottom: 2px solid #6C757D;">Cob. Atual (dias)</th>
                <th style="padding: 8px; text-align: right; border-bottom: 2px solid #6C757D;">Cob. Projetada (dias)</th>
                <th style="padding: 8px; text-align: right; border-bottom: 2px solid #6C757D;">Qtd. Pedido</th>
                <th style="padding: 8px; text-align: right; border-bottom: 2px solid #6C757D;">Custo</th>
                <th style="padding: 8px; text-align: center; border-bottom: 2px solid #6C757D;">Método</th>
                <th style="padding: 8px; text-align: center; border-bottom: 2px solid #6C757D;">Pedir?</th>
            </tr>
        `;

        // Linhas de itens da loja
        itensLoja.forEach(item => {
            const devePedir = item.Deve_Pedir === 'Sim';
            const temRisco = item.Risco_Ruptura === 'Sim';
            const temAlerta = item.Alerta && item.Alerta.includes('CD sem estoque');

            let rowClass = '';
            if (temAlerta) {
                rowClass = 'background-color: #f8d7da;'; // Vermelho claro para alerta
            } else if (temRisco) {
                rowClass = 'background-color: #fff3e0;'; // Laranja para risco
            } else if (devePedir) {
                rowClass = 'background-color: #f3e5f5;'; // Roxo claro para deve pedir
            }

            const custoUnitario = item.Custo_Unitario || 0;
            const quantidadePedido = item.Quantidade_Pedido || 0;

            // Mostrar sempre custo unitário (mesmo sem pedido)
            const custoLabel = custoUnitario > 0 ? `R$ ${custoUnitario.toFixed(2)}` : '-';

            // Converter demanda mensal para diária
            const demandaDiaria = (item.Demanda_Media_Mensal || 0) / 30;

            html += `
                <tr style="${rowClass}">
                    <td style="padding: 6px;">${item.CD_Origem || item.Origem || 'N/A'}</td>
                    <td style="padding: 6px;">${item.SKU || 'N/A'}</td>
                    <td style="padding: 6px; text-align: right;">${demandaDiaria.toFixed(1)}</td>
                    <td style="padding: 6px; text-align: right;">${item.Estoque_Loja || 0}</td>
                    <td style="padding: 6px; text-align: right;">${item.Estoque_CD !== null && item.Estoque_CD !== undefined ? item.Estoque_CD : '-'}</td>
                    <td style="padding: 6px; text-align: right;">${item.Estoque_Transito || 0}</td>
                    <td style="padding: 6px; text-align: center;">${((item.Nivel_Servico || 0) * 100).toFixed(0)}%</td>
                    <td style="padding: 6px; text-align: right; color: ${(item.Cobertura_Dias_Atual || 0) < 3 ? '#dc3545' : '#6C757D'};">${(item.Cobertura_Dias_Atual || 0).toFixed(1)}</td>
                    <td style="padding: 6px; text-align: right;">${(item.Cobertura_Dias_Apos_Pedido || 0).toFixed(1)}</td>
                    <td style="padding: 6px; text-align: right; font-weight: bold; color: ${devePedir ? '#6C757D' : '#666'};">${quantidadePedido}</td>
                    <td style="padding: 6px; text-align: right;">${custoLabel}</td>
                    <td style="padding: 6px; font-size: 0.75em;">${item.Metodo_Usado || 'N/A'}</td>
                    <td style="padding: 6px; text-align: center;">
                        ${temAlerta ? '<span style="color: #dc3545;">⚠️</span>' :
                          devePedir ? '<span style="color: #6C757D; font-weight: bold;">✓</span>' : '-'}
                    </td>
                </tr>
            `;
        });

        // Linha de separação entre lojas
        html += `
            <tr>
                <td colspan="13" style="padding: 10px; background: #f5f5f5;"></td>
            </tr>
        `;
    });

    tbody.innerHTML = html;
}
