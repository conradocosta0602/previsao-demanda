// transferencias.js - Processamento de Transferências entre Lojas

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
                    `Processando transferências... ${progress}%`;
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

        // Verificar se há resultados para TRANSFERENCIAS
        if (!data.resultados || !data.resultados.TRANSFERENCIAS) {
            throw new Error('Nenhum resultado encontrado. Verifique se o arquivo possui a aba TRANSFERENCIAS e HISTORICO_VENDAS.');
        }

        const resultado = data.resultados.TRANSFERENCIAS;

        // Exibir resultados
        setTimeout(() => {
            document.getElementById('progress').style.display = 'none';
            document.getElementById('results').style.display = 'block';

            exibirResumo(resultado.resumo);
            exibirAlertas(resultado.resumo, resultado.dados_tabela);
            exibirResultados(resultado.dados_tabela);

            // Configurar download
            const arquivoTransf = data.arquivos_gerados.find(a =>
                a.toLowerCase().includes('transferencia')
            );
            if (arquivoTransf) {
                document.getElementById('downloadBtn').href = `/download/${arquivoTransf}`;
            }
        }, 500);

    } catch (error) {
        document.getElementById('progress').style.display = 'none';
        document.getElementById('error').style.display = 'block';
        document.getElementById('errorMessage').textContent = error.message;
    }
});

function exibirResumo(resumo) {
    const oportunidades = resumo.total_a_pedir || 0;
    const valorEstoque = resumo.valor_total_estoque || 0;
    const custoOperacional = resumo.custo_operacional_total || 0;

    const html = `
        <div class="resumo-card-compact">
            <h4>Oportunidades</h4>
            <p class="big-number-compact">${oportunidades}</p>
            <p style="font-size: 0.7em; color: #666;">transferências viáveis</p>
        </div>
        <div class="resumo-card-compact">
            <h4>Valor Estoque</h4>
            <p class="big-number-compact">R$ ${valorEstoque.toLocaleString('pt-BR', {minimumFractionDigits: 2})}</p>
            <p style="font-size: 0.7em; color: #666;">movimentado</p>
        </div>
        <div class="resumo-card-compact">
            <h4>Custo Operacional</h4>
            <p class="big-number-compact">R$ ${custoOperacional.toLocaleString('pt-BR', {minimumFractionDigits: 2})}</p>
        </div>
        <div class="resumo-card-compact">
            <h4>Urgência Alta</h4>
            <p class="big-number-compact" style="color: #dc3545;">${resumo.urgencia_alta || 0}</p>
        </div>
    `;
    document.getElementById('resumo').innerHTML = html;
}

function exibirAlertas(resumo, dados) {
    const alertasHtml = [];

    const urgenciaAlta = dados.filter(item =>
        item.Urgencia === 'ALTA' && item.Transferencia_Viavel === 'Sim'
    ).length;

    if (urgenciaAlta > 0) {
        alertasHtml.push(`
            <div class="alerta error">
                <strong>🚨 Urgente:</strong> ${urgenciaAlta} transferências de alta prioridade identificadas!
            </div>
        `);
    }

    if (resumo.total_a_pedir > 0) {
        alertasHtml.push(`
            <div class="alerta warning">
                <strong>🔄 Ação:</strong> ${resumo.total_a_pedir} oportunidades de transferência economicamente viáveis.
            </div>
        `);
    } else {
        alertasHtml.push(`
            <div class="alerta info">
                <strong>✅ Sem Oportunidades:</strong> Não há transferências viáveis no momento.
            </div>
        `);
    }

    document.getElementById('alertas').innerHTML = alertasHtml.join('');
}

function exibirResultados(dados) {
    const tbody = document.getElementById('resultadosBody');

    if (!dados || dados.length === 0) {
        tbody.innerHTML = '<tr><td colspan="7" style="text-align: center; padding: 20px;">Nenhuma oportunidade de transferência identificada</td></tr>';
        return;
    }

    // Ordenar por urgência
    const prioridade = { 'ALTA': 1, 'MEDIA': 2, 'BAIXA': 3 };
    dados.sort((a, b) => (prioridade[a.Urgencia] || 99) - (prioridade[b.Urgencia] || 99));

    tbody.innerHTML = dados.map(item => {
        const viavel = item.Transferencia_Viavel === 'Sim';
        const urgencia = item.Urgencia || 'BAIXA';

        let urgenciaColor = '#28a745'; // Verde (BAIXA)
        if (urgencia === 'ALTA') urgenciaColor = '#dc3545'; // Vermelho
        else if (urgencia === 'MEDIA') urgenciaColor = '#ffc107'; // Amarelo

        const rowClass = viavel && urgencia === 'ALTA' ? 'style="background-color: #fff3e0;"' : '';

        return `
            <tr ${rowClass}>
                <td style="padding: 8px;">${item.Loja_Origem || 'N/A'}</td>
                <td style="padding: 8px;">${item.Loja_Destino || 'N/A'}</td>
                <td style="padding: 8px;">${item.SKU || 'N/A'}</td>
                <td style="padding: 8px; text-align: right; font-weight: bold;">${item.Quantidade_Transferir || 0}</td>
                <td style="padding: 8px; text-align: right; color: #2196F3;">R$ ${(item.Valor_Estoque_Transferido || 0).toFixed(2)}</td>
                <td style="padding: 8px; text-align: center;">
                    <span style="background: ${urgenciaColor}; color: white; padding: 4px 8px; border-radius: 4px; font-size: 0.85em;">
                        ${urgencia}
                    </span>
                </td>
                <td style="padding: 8px; text-align: center;">
                    ${viavel ? '<span style="color: #f093fb; font-weight: bold;">✓ Sim</span>' : '<span style="color: #dc3545;">✗ Não</span>'}
                </td>
            </tr>
        `;
    }).join('');
}
