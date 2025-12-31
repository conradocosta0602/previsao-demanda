// Pedido Manual - Planilha Interativa

let dadosCarregados = [];
let linhaCounter = 0;

// Adicionar nova linha vazia
function adicionarLinha() {
    linhaCounter++;
    const tbody = document.getElementById('spreadsheetBody');

    const tr = document.createElement('tr');
    tr.id = `row-${linhaCounter}`;
    tr.innerHTML = `
        <td style="text-align: center; color: #999;">${linhaCounter}</td>
        <td><input type="text" class="cell-input" data-field="loja" placeholder="LOJA_01"></td>
        <td><input type="text" class="cell-input" data-field="sku" placeholder="SKU_001"></td>
        <td><input type="number" class="cell-input" data-field="quantidade" placeholder="0" min="0"></td>
        <td><input type="number" class="cell-input" data-field="demanda_diaria" placeholder="0" min="0" step="0.1"></td>
        <td><input type="number" class="cell-input" data-field="estoque_atual" placeholder="0" min="0"></td>
        <td><div class="cell-readonly" data-result="cobertura_atual">-</div></td>
        <td><div class="cell-readonly" data-result="estoque_apos">-</div></td>
        <td><div class="cell-readonly" data-result="cobertura_apos">-</div></td>
        <td><div class="cell-readonly" data-result="status">-</div></td>
        <td style="text-align: center;">
            <button class="btn-delete" onclick="removerLinha('row-${linhaCounter}')">✕</button>
        </td>
    `;

    tbody.appendChild(tr);

    // Esconder empty state
    document.getElementById('emptyState').style.display = 'none';
}

// Remover linha
function removerLinha(rowId) {
    const row = document.getElementById(rowId);
    if (row) {
        row.remove();
    }

    // Verificar se ficou vazio
    const tbody = document.getElementById('spreadsheetBody');
    if (tbody.children.length === 0) {
        document.getElementById('emptyState').style.display = 'block';
        document.getElementById('summarySection').style.display = 'none';
        linhaCounter = 0;
    }
}

// Limpar todos os dados
function limparTodos() {
    if (confirm('Tem certeza que deseja limpar todos os dados?')) {
        document.getElementById('spreadsheetBody').innerHTML = '';
        document.getElementById('emptyState').style.display = 'block';
        document.getElementById('summarySection').style.display = 'none';
        dadosCarregados = [];
        linhaCounter = 0;
    }
}

// Carregar arquivo Excel
async function carregarArquivo() {
    const fileInput = document.getElementById('fileUpload');

    if (!fileInput.files || fileInput.files.length === 0) {
        alert('Selecione um arquivo Excel');
        return;
    }

    const formData = new FormData();
    formData.append('file', fileInput.files[0]);

    try {
        const response = await fetch('/api/carregar_dados_pedido', {
            method: 'POST',
            body: formData
        });

        if (!response.ok) {
            const error = await response.json();
            alert(error.erro || 'Erro ao carregar arquivo');
            return;
        }

        const data = await response.json();
        dadosCarregados = data.dados;

        // Limpar linhas existentes
        document.getElementById('spreadsheetBody').innerHTML = '';
        linhaCounter = 0;

        // Adicionar linhas com os dados carregados
        dadosCarregados.forEach(item => {
            adicionarLinhaComDados(item);
        });

        alert(`${dadosCarregados.length} itens carregados com sucesso!`);

    } catch (error) {
        alert('Erro ao carregar arquivo: ' + error.message);
    }
}

// Adicionar linha com dados preenchidos
function adicionarLinhaComDados(item) {
    linhaCounter++;
    const tbody = document.getElementById('spreadsheetBody');

    const tr = document.createElement('tr');
    tr.id = `row-${linhaCounter}`;
    tr.innerHTML = `
        <td style="text-align: center; color: #999;">${linhaCounter}</td>
        <td><input type="text" class="cell-input" data-field="loja" value="${item.Loja || ''}"></td>
        <td><input type="text" class="cell-input" data-field="sku" value="${item.SKU || ''}"></td>
        <td><input type="number" class="cell-input" data-field="quantidade" value="0" min="0"></td>
        <td><input type="number" class="cell-input" data-field="demanda_diaria" value="${item.Demanda_Diaria || 0}" min="0" step="0.1"></td>
        <td><input type="number" class="cell-input" data-field="estoque_atual" value="${item.Estoque_Disponivel || 0}" min="0"></td>
        <td><div class="cell-readonly" data-result="cobertura_atual">-</div></td>
        <td><div class="cell-readonly" data-result="estoque_apos">-</div></td>
        <td><div class="cell-readonly" data-result="cobertura_apos">-</div></td>
        <td><div class="cell-readonly" data-result="status">-</div></td>
        <td style="text-align: center;">
            <button class="btn-delete" onclick="removerLinha('row-${linhaCounter}')">✕</button>
        </td>
    `;

    tbody.appendChild(tr);

    // Esconder empty state
    document.getElementById('emptyState').style.display = 'none';
}

// Calcular todas as linhas
function calcularTodos() {
    const tbody = document.getElementById('spreadsheetBody');
    const rows = tbody.getElementsByTagName('tr');

    if (rows.length === 0) {
        alert('Adicione pelo menos uma linha antes de calcular');
        return;
    }

    let totalItens = 0;
    let countSafe = 0;
    let countWarning = 0;
    let countDanger = 0;

    // Processar cada linha
    for (let row of rows) {
        const inputs = row.querySelectorAll('.cell-input');
        const results = row.querySelectorAll('.cell-readonly');

        // Extrair valores
        let loja = '';
        let sku = '';
        let quantidade = 0;
        let demandaDiaria = 0;
        let estoqueAtual = 0;

        inputs.forEach(input => {
            const field = input.getAttribute('data-field');
            const value = input.value;

            if (field === 'loja') loja = value;
            else if (field === 'sku') sku = value;
            else if (field === 'quantidade') quantidade = parseFloat(value) || 0;
            else if (field === 'demanda_diaria') demandaDiaria = parseFloat(value) || 0;
            else if (field === 'estoque_atual') estoqueAtual = parseFloat(value) || 0;
        });

        // Validar dados mínimos
        if (!loja || !sku || demandaDiaria <= 0) {
            // Marcar como inválido
            results.forEach(result => {
                result.textContent = '-';
            });
            continue;
        }

        totalItens++;

        // Calcular métricas
        const coberturaAtual = estoqueAtual / demandaDiaria;
        const estoqueApos = estoqueAtual + quantidade;
        const coberturaApos = estoqueApos / demandaDiaria;

        // Determinar risco
        let status = '';
        let statusClass = '';

        if (coberturaApos < 7) {
            status = '🚨 Risco';
            statusClass = 'risk-danger';
            countDanger++;
        } else if (coberturaApos < 15) {
            status = '⚠️ Atenção';
            statusClass = 'risk-warning';
            countWarning++;
        } else {
            status = '✅ OK';
            statusClass = 'risk-safe';
            countSafe++;
        }

        // Preencher resultados
        results.forEach(result => {
            const field = result.getAttribute('data-result');

            if (field === 'cobertura_atual') {
                result.textContent = coberturaAtual.toFixed(1) + ' dias';
            } else if (field === 'estoque_apos') {
                result.textContent = Math.round(estoqueApos) + ' un';
            } else if (field === 'cobertura_apos') {
                result.textContent = coberturaApos.toFixed(1) + ' dias';
            } else if (field === 'status') {
                result.innerHTML = `<span class="risk-badge ${statusClass}">${status}</span>`;
            }
        });
    }

    // Atualizar resumo
    if (totalItens > 0) {
        document.getElementById('summarySection').style.display = 'grid';
        document.getElementById('summaryTotal').textContent = totalItens;
        document.getElementById('summarySafe').textContent = countSafe;
        document.getElementById('summaryWarning').textContent = countWarning;
        document.getElementById('summaryDanger').textContent = countDanger;
    }
}

// Inicialização
document.addEventListener('DOMContentLoaded', () => {
    // Adicionar uma linha vazia para começar (opcional)
    // adicionarLinha();
});
