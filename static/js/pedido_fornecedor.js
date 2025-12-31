// pedido_fornecedor.js - Processamento de Pedidos ao Fornecedor

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

        // Verificar se há resultados para PEDIDOS_FORNECEDOR
        if (!data.resultados || !data.resultados.PEDIDOS_FORNECEDOR) {
            throw new Error('Nenhum resultado encontrado. Verifique se o arquivo possui a aba PEDIDOS_FORNECEDOR e HISTORICO_VENDAS.');
        }

        const resultado = data.resultados.PEDIDOS_FORNECEDOR;

        // Exibir resultados
        setTimeout(() => {
            document.getElementById('progress').style.display = 'none';
            document.getElementById('results').style.display = 'block';

            exibirResumo(resultado.resumo);
            exibirAlertas(resultado.resumo);
            exibirResultados(resultado.dados_tabela);

            // Configurar download
            const arquivoFornecedor = data.arquivos_gerados.find(a =>
                a.toLowerCase().includes('fornecedor')
            );
            if (arquivoFornecedor) {
                document.getElementById('downloadBtn').href = `/download/${arquivoFornecedor}`;
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
            <h4>Itens a Pedir</h4>
            <p class="big-number-compact">${resumo.total_a_pedir || 0}</p>
        </div>
        <div class="resumo-card-compact">
            <h4>Custo Total Estimado</h4>
            <p class="big-number-compact">R$ ${(resumo.custo_total || 0).toLocaleString('pt-BR', {minimumFractionDigits: 2})}</p>
        </div>
    `;
    document.getElementById('resumo').innerHTML = html;
}

function exibirAlertas(resumo) {
    const alertasHtml = [];

    if (resumo.total_a_pedir > 0) {
        alertasHtml.push(`
            <div class="alerta warning">
                <strong>📦 Pedido Necessário:</strong> ${resumo.total_a_pedir} itens precisam ser pedidos ao fornecedor.
            </div>
        `);
    } else {
        alertasHtml.push(`
            <div class="alerta info">
                <strong>✅ Estoque OK:</strong> Não há necessidade de novos pedidos no momento.
            </div>
        `);
    }

    document.getElementById('alertas').innerHTML = alertasHtml.join('');
}

function exibirResultados(dados) {
    const tbody = document.getElementById('resultadosBody');

    if (!dados || dados.length === 0) {
        tbody.innerHTML = '<tr><td colspan="13" style="text-align: center; padding: 20px;">Nenhum pedido necessário</td></tr>';
        return;
    }

    // Agrupar dados por fornecedor
    const porFornecedor = {};
    dados.forEach(item => {
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
        let valorTotalEstoque = 0;
        let valorTotalPedido = 0;

        itensFornecedor.forEach(item => {
            const custoUnitario = item.Custo_Unitario || 0;
            // Valor do estoque: TODOS os itens com estoque no destino
            valorTotalEstoque += (item.Estoque_Disponivel || 0) * custoUnitario;
            // Valor do pedido: APENAS itens que devem ser pedidos
            if (item.Deve_Pedir === 'Sim') {
                valorTotalPedido += (item.Quantidade_Final || 0) * custoUnitario;
            }
        });

        const itensAPedir = itensFornecedor.filter(item => item.Deve_Pedir === 'Sim').length;

        // Cobertura atual ponderada
        let coberturaAtualTotal = 0;
        let coberturaProjetadaTotal = 0;
        let rupturaAtual = 0;
        let pesoTotal = 0;

        itensFornecedor.forEach(item => {
            const demanda = item.Demanda_Media_Mensal || 0;
            if (demanda > 0) {
                coberturaAtualTotal += (item.Cobertura_Dias_Atual || 0) * demanda;
                coberturaProjetadaTotal += (item.Cobertura_Dias_Apos_Pedido || 0) * demanda;
                pesoTotal += demanda;
            }
            if (item.Risco_Ruptura === 'Sim') {
                rupturaAtual++;
            }
        });

        const coberturaAtual = pesoTotal > 0 ? coberturaAtualTotal / pesoTotal : 0;
        const coberturaProjetada = pesoTotal > 0 ? coberturaProjetadaTotal / pesoTotal : 0;

        // Linha de cabeçalho do fornecedor com totalizadores
        html += `
            <tr style="background: linear-gradient(135deg, #0070f3 0%, #00d4ff 100%); color: white;">
                <td colspan="13" style="padding: 12px; font-weight: bold; font-size: 1.1em;">
                    📦 ${fornecedor}
                    <div style="display: grid; grid-template-columns: repeat(6, 1fr); gap: 10px; margin-top: 8px; font-size: 0.85em; font-weight: normal;">
                        <div>
                            <div style="opacity: 0.8; font-size: 0.9em;">Valor Estoque</div>
                            <div style="font-weight: bold;">R$ ${valorTotalEstoque.toLocaleString('pt-BR', {minimumFractionDigits: 2})}</div>
                        </div>
                        <div>
                            <div style="opacity: 0.8; font-size: 0.9em;">Valor Pedido</div>
                            <div style="font-weight: bold;">R$ ${valorTotalPedido.toLocaleString('pt-BR', {minimumFractionDigits: 2})}</div>
                        </div>
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
                            <div style="font-weight: bold;">${itensAPedir} de ${itensFornecedor.length}</div>
                        </div>
                        <div>
                            <div style="opacity: 0.8; font-size: 0.9em;">Ruptura Atual</div>
                            <div style="font-weight: bold; color: ${rupturaAtual > 0 ? '#ffeb3b' : '#4caf50'};">${rupturaAtual} itens</div>
                        </div>
                    </div>
                </td>
            </tr>
        `;

        // Cabeçalho da tabela repetido para cada fornecedor
        html += `
            <tr style="background: #e3f2fd; color: #0070f3; font-weight: bold; font-size: 0.85em;">
                <th style="padding: 8px; text-align: left; border-bottom: 2px solid #0070f3;">SKU</th>
                <th style="padding: 8px; text-align: left; border-bottom: 2px solid #0070f3;">Destino</th>
                <th style="padding: 8px; text-align: right; border-bottom: 2px solid #0070f3;">Demanda Média</th>
                <th style="padding: 8px; text-align: right; border-bottom: 2px solid #0070f3;">Estoque Atual</th>
                <th style="padding: 8px; text-align: right; border-bottom: 2px solid #0070f3;">Em Trânsito</th>
                <th style="padding: 8px; text-align: right; border-bottom: 2px solid #0070f3;">Pedidos Abertos</th>
                <th style="padding: 8px; text-align: center; border-bottom: 2px solid #0070f3;">Nível Serviço</th>
                <th style="padding: 8px; text-align: right; border-bottom: 2px solid #0070f3;">Cob. Atual (dias)</th>
                <th style="padding: 8px; text-align: right; border-bottom: 2px solid #0070f3;">Cob. Projetada (dias)</th>
                <th style="padding: 8px; text-align: right; border-bottom: 2px solid #0070f3;">Qtd. Pedido</th>
                <th style="padding: 8px; text-align: right; border-bottom: 2px solid #0070f3;">Custo</th>
                <th style="padding: 8px; text-align: center; border-bottom: 2px solid #0070f3;">Método</th>
                <th style="padding: 8px; text-align: center; border-bottom: 2px solid #0070f3;">Pedir?</th>
            </tr>
        `;

        // Linhas de itens do fornecedor
        itensFornecedor.forEach(item => {
            const devePedir = item.Deve_Pedir === 'Sim';
            const temRisco = item.Risco_Ruptura === 'Sim';
            const rowClass = temRisco ? 'background-color: #fff3e0;' : (devePedir ? 'background-color: #e3f2fd;' : '');

            // Mostrar sempre custo unitário (mesmo sem pedido)
            const custoUnitario = item.Custo_Unitario || 0;
            const quantidadePedido = item.Quantidade_Final || 0;
            const custoLabel = custoUnitario > 0 ? `R$ ${custoUnitario.toFixed(2)}` : '-';

            html += `
                <tr style="${rowClass}">
                    <td style="padding: 6px;">${item.SKU || 'N/A'}</td>
                    <td style="padding: 6px;">${item.Destino || 'N/A'}</td>
                    <td style="padding: 6px; text-align: right;">${(item.Demanda_Media_Mensal || 0).toFixed(1)}</td>
                    <td style="padding: 6px; text-align: right;">${item.Estoque_Disponivel || 0}</td>
                    <td style="padding: 6px; text-align: right;">${item.Estoque_Transito || 0}</td>
                    <td style="padding: 6px; text-align: right;">${item.Pedidos_Abertos || 0}</td>
                    <td style="padding: 6px; text-align: center;">${((item.Nivel_Servico || 0) * 100).toFixed(0)}%</td>
                    <td style="padding: 6px; text-align: right; color: ${(item.Cobertura_Dias_Atual || 0) < 7 ? '#dc3545' : '#11998e'};">${(item.Cobertura_Dias_Atual || 0).toFixed(1)}</td>
                    <td style="padding: 6px; text-align: right;">${(item.Cobertura_Dias_Apos_Pedido || 0).toFixed(1)}</td>
                    <td style="padding: 6px; text-align: right; font-weight: bold; color: ${devePedir ? '#0070f3' : '#666'};">${quantidadePedido}</td>
                    <td style="padding: 6px; text-align: right;">${custoLabel}</td>
                    <td style="padding: 6px; font-size: 0.75em;">${item.Metodo_Usado || 'N/A'}</td>
                    <td style="padding: 6px; text-align: center;">
                        ${devePedir ? '<span style="color: #0070f3; font-weight: bold;">✓</span>' : '-'}
                    </td>
                </tr>
            `;
        });

        // Linha de separação entre fornecedores
        html += `
            <tr>
                <td colspan="13" style="padding: 10px; background: #f5f5f5;"></td>
            </tr>
        `;
    });

    tbody.innerHTML = html;
}
