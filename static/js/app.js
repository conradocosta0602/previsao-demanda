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

    // Preencher resumo
    const resumo = data.resumo;
    document.getElementById('resumo').innerHTML = `
        <div class="resumo-card">
            <h3>SKUs Processados</h3>
            <p class="big-number">${resumo.total_skus}</p>
        </div>
        <div class="resumo-card">
            <h3>Combinacoes Loja+SKU</h3>
            <p class="big-number">${resumo.total_combinacoes}</p>
        </div>
        <div class="resumo-card">
            <h3>Meses de Previsao</h3>
            <p class="big-number">${resumo.meses_previsao}</p>
        </div>
        <div class="resumo-card">
            <h3>Vendas Perdidas Est.</h3>
            <p class="big-number">${formatNumber(resumo.vendas_perdidas)}</p>
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
