/**
 * Gerenciamento de Eventos Sazonais - JavaScript
 *
 * Funções para cadastrar, listar, editar e deletar eventos
 */

// Tipos de eventos com informações
const EVENT_TYPES = {
    'BLACK_FRIDAY': {
        nome: 'Black Friday',
        descricao: 'Última sexta-feira de novembro',
        duracao_dias: 3,
        icone: '🛍️'
    },
    'NATAL': {
        nome: 'Natal',
        descricao: '25 de dezembro',
        duracao_dias: 7,
        icone: '🎄'
    },
    'ANO_NOVO': {
        nome: 'Ano Novo',
        descricao: '31 de dezembro e 1 de janeiro',
        duracao_dias: 2,
        icone: '🎆'
    },
    'DIAS_MAES': {
        nome: 'Dia das Mães',
        descricao: 'Segunda domingo de maio',
        duracao_dias: 7,
        icone: '💐'
    },
    'DIAS_PAIS': {
        nome: 'Dia dos Pais',
        descricao: 'Segunda domingo de agosto',
        duracao_dias: 7,
        icone: '👔'
    },
    'PASCOA': {
        nome: 'Páscoa',
        descricao: 'Data móvel (março/abril)',
        duracao_dias: 7,
        icone: '🐰'
    },
    'VOLTA_AULAS': {
        nome: 'Volta às Aulas',
        descricao: 'Janeiro/Fevereiro',
        duracao_dias: 14,
        icone: '📚'
    },
    'CUSTOM': {
        nome: 'Evento Customizado',
        descricao: 'Evento específico da empresa',
        duracao_dias: 1,
        icone: '📅'
    }
};

// ===========================
// INICIALIZAÇÃO
// ===========================

document.addEventListener('DOMContentLoaded', function() {
    console.log('📅 Gerenciamento de Eventos carregado');

    // Configurar formulário
    setupForm();

    // Carregar eventos
    carregarEventos();
});

function setupForm() {
    const form = document.getElementById('cadastroForm');
    const tipoSelect = document.getElementById('tipoEvento');
    const checkboxManual = document.getElementById('usarMultiplicadorManual');

    // Evento: mudança no tipo de evento
    tipoSelect.addEventListener('change', function() {
        const tipo = this.value;

        if (!tipo) {
            document.getElementById('eventoInfo').style.display = 'none';
            document.getElementById('nomeCustomGroup').style.display = 'none';
            return;
        }

        const info = EVENT_TYPES[tipo];

        // Mostrar informações do evento
        const infoDiv = document.getElementById('eventoInfo');
        infoDiv.innerHTML = `
            <strong>${info.icone} ${info.nome}</strong><br>
            ${info.descricao}<br>
            Duração típica: ${info.duracao_dias} dia(s)
        `;
        infoDiv.style.display = 'block';

        // Preencher duração padrão
        document.getElementById('duracaoDias').value = info.duracao_dias;

        // Mostrar campo de nome customizado se CUSTOM
        if (tipo === 'CUSTOM') {
            document.getElementById('nomeCustomGroup').style.display = 'block';
            document.getElementById('nomeCustom').required = true;
        } else {
            document.getElementById('nomeCustomGroup').style.display = 'none';
            document.getElementById('nomeCustom').required = false;
        }
    });

    // Evento: checkbox de multiplicador manual
    checkboxManual.addEventListener('change', function() {
        const multiplicadorGroup = document.getElementById('multiplicadorGroup');
        if (this.checked) {
            multiplicadorGroup.style.display = 'block';
            document.getElementById('multiplicador').required = true;
        } else {
            multiplicadorGroup.style.display = 'none';
            document.getElementById('multiplicador').required = false;
        }
    });

    // Evento: submit do formulário
    form.addEventListener('submit', async function(e) {
        e.preventDefault();
        await cadastrarEvento();
    });
}

// ===========================
// CADASTRO DE EVENTOS
// ===========================

async function cadastrarEvento() {
    const tipo = document.getElementById('tipoEvento').value;
    const dataEvento = document.getElementById('dataEvento').value;
    const duracaoDias = parseInt(document.getElementById('duracaoDias').value);
    const nomeCustom = document.getElementById('nomeCustom').value;
    const observacoes = document.getElementById('observacoes').value;
    const usarManual = document.getElementById('usarMultiplicadorManual').checked;

    let multiplicador = null;
    if (usarManual) {
        const multiplicadorValue = document.getElementById('multiplicador').value;
        multiplicador = multiplicadorValue ? parseFloat(multiplicadorValue) : null;
    }

    // Validação
    if (!tipo || !dataEvento) {
        mostrarAlerta('Preencha todos os campos obrigatórios', 'error');
        return;
    }

    if (tipo === 'CUSTOM' && !nomeCustom) {
        mostrarAlerta('Nome do evento customizado é obrigatório', 'error');
        return;
    }

    if (usarManual && (!multiplicador || isNaN(multiplicador) || multiplicador <= 0)) {
        mostrarAlerta('Defina um multiplicador válido (número maior que 0)', 'error');
        return;
    }

    // Validar duração
    if (!duracaoDias || duracaoDias < 1) {
        mostrarAlerta('Duração deve ser pelo menos 1 dia', 'error');
        return;
    }

    // Dados para enviar
    const dados = {
        tipo: tipo,
        data_evento: dataEvento,
        duracao_dias: duracaoDias,
        nome_custom: nomeCustom || null,
        multiplicador_manual: multiplicador,
        observacoes: observacoes || null
    };

    console.log('📤 Enviando dados:', dados);

    try {
        const response = await fetch('/eventos/cadastrar', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(dados)
        });

        const result = await response.json();

        console.log('📥 Resposta:', result);

        if (result.success) {
            mostrarAlerta('✅ Evento cadastrado com sucesso!', 'success');
            document.getElementById('cadastroForm').reset();
            document.getElementById('eventoInfo').style.display = 'none';
            document.getElementById('nomeCustomGroup').style.display = 'none';
            document.getElementById('multiplicadorGroup').style.display = 'none';

            // Recarregar lista
            await carregarEventos();
        } else {
            console.error('❌ Erro do servidor:', result.erro);
            mostrarAlerta(`Erro: ${result.erro}`, 'error');
        }

    } catch (erro) {
        console.error('❌ Erro ao cadastrar evento:', erro);
        mostrarAlerta('Erro ao cadastrar evento. Verifique o console do navegador (F12).', 'error');
    }
}

// ===========================
// LISTAGEM DE EVENTOS
// ===========================

async function carregarEventos() {
    document.getElementById('loadingEventos').style.display = 'block';
    document.getElementById('eventosContent').style.display = 'none';
    document.getElementById('emptyState').style.display = 'none';

    try {
        console.log('📥 Carregando eventos...');

        const response = await fetch('/eventos/listar');

        if (!response.ok) {
            throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }

        const result = await response.json();

        console.log('✅ Eventos carregados:', result);

        document.getElementById('loadingEventos').style.display = 'none';

        if (result.success) {
            const eventos = result.eventos;

            if (eventos.length === 0) {
                document.getElementById('emptyState').style.display = 'block';
            } else {
                renderizarEventos(eventos);
                document.getElementById('eventosContent').style.display = 'block';
            }
        } else {
            console.error('❌ Erro do servidor:', result.erro);
            mostrarAlerta(`Erro ao carregar eventos: ${result.erro}`, 'error');
        }

    } catch (erro) {
        console.error('❌ Erro ao carregar eventos:', erro);
        document.getElementById('loadingEventos').style.display = 'none';

        // Mensagem mais específica
        let mensagem = 'Erro ao carregar eventos. ';
        if (erro.message.includes('HTTP')) {
            mensagem += `Servidor retornou: ${erro.message}`;
        } else if (erro.message.includes('JSON')) {
            mensagem += 'Resposta inválida do servidor.';
        } else {
            mensagem += 'Verifique se o servidor Flask está rodando.';
        }

        mostrarAlerta(mensagem, 'error');
    }
}

function renderizarEventos(eventos) {
    const tbody = document.getElementById('eventosTableBody');

    tbody.innerHTML = eventos.map(evento => {
        const info = EVENT_TYPES[evento.tipo];
        const icone = info ? info.icone : '📅';

        const dataFormatada = new Date(evento.data_evento + 'T00:00:00').toLocaleDateString('pt-BR');

        const multiplicador = evento.usar_multiplicador_manual && evento.multiplicador_manual
            ? evento.multiplicador_manual
            : evento.multiplicador_calculado || '-';

        const tipoMultiplicador = evento.usar_multiplicador_manual ? 'Manual' : 'Auto';

        const statusBadge = evento.ativo
            ? '<span class="event-badge badge-ativo">Ativo</span>'
            : '<span class="event-badge badge-inativo">Inativo</span>';

        return `
            <tr>
                <td>
                    <span class="event-icon">${icone}</span>
                    <strong>${evento.nome}</strong>
                    ${evento.observacoes ? `<br><small style="color: #6c757d;">${evento.observacoes}</small>` : ''}
                </td>
                <td>${dataFormatada}</td>
                <td>${evento.duracao_dias} dia(s)</td>
                <td>
                    <div class="multiplicador-info">
                        <span class="multiplicador-valor">${typeof multiplicador === 'number' ? multiplicador.toFixed(2) + 'x' : multiplicador}</span>
                        ${typeof multiplicador === 'number' ? `<span class="multiplicador-tipo">${tipoMultiplicador}</span>` : ''}
                    </div>
                </td>
                <td>${statusBadge}</td>
                <td>
                    <div class="acoes-cell">
                        ${evento.ativo
                            ? `<button class="btn-secondary" onclick="editarEvento(${evento.id})">✏️ Editar</button>`
                            : ''}
                        ${evento.ativo
                            ? `<button class="btn-danger" onclick="desativarEvento(${evento.id})">🗑️ Desativar</button>`
                            : `<button class="btn-secondary" onclick="reativarEvento(${evento.id})">✅ Reativar</button>`}
                        <button class="btn-danger" onclick="excluirEvento(${evento.id})" style="background: #dc3545;">❌ Excluir</button>
                    </div>
                </td>
            </tr>
        `;
    }).join('');
}

// ===========================
// EDIÇÃO E EXCLUSÃO
// ===========================

async function editarEvento(id) {
    const novoMultiplicador = prompt('Novo multiplicador (ex: 2.5 para 250%):');

    if (novoMultiplicador === null) {
        return; // Cancelado
    }

    const multiplicador = parseFloat(novoMultiplicador);

    if (isNaN(multiplicador) || multiplicador <= 0) {
        mostrarAlerta('Multiplicador inválido', 'error');
        return;
    }

    try {
        const response = await fetch('/eventos/atualizar', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                evento_id: id,
                multiplicador: multiplicador
            })
        });

        const result = await response.json();

        if (result.success) {
            mostrarAlerta('Multiplicador atualizado!', 'success');
            await carregarEventos();
        } else {
            mostrarAlerta(`Erro: ${result.erro}`, 'error');
        }

    } catch (erro) {
        console.error('Erro ao editar evento:', erro);
        mostrarAlerta('Erro ao editar evento', 'error');
    }
}

async function desativarEvento(id) {
    if (!confirm('Deseja realmente desativar este evento?')) {
        return;
    }

    try {
        const response = await fetch('/eventos/desativar', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                evento_id: id
            })
        });

        const result = await response.json();

        if (result.success) {
            mostrarAlerta('Evento desativado', 'success');
            await carregarEventos();
        } else {
            mostrarAlerta(`Erro: ${result.erro}`, 'error');
        }

    } catch (erro) {
        console.error('Erro ao desativar evento:', erro);
        mostrarAlerta('Erro ao desativar evento', 'error');
    }
}

async function reativarEvento(id) {
    try {
        const response = await fetch('/eventos/reativar', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                evento_id: id
            })
        });

        const result = await response.json();

        if (result.success) {
            mostrarAlerta('Evento reativado', 'success');
            await carregarEventos();
        } else {
            mostrarAlerta(`Erro: ${result.erro}`, 'error');
        }

    } catch (erro) {
        console.error('Erro ao reativar evento:', erro);
        mostrarAlerta('Erro ao reativar evento', 'error');
    }
}

async function excluirEvento(id) {
    if (!confirm('Deseja realmente excluir este evento? Esta ação não pode ser desfeita.')) {
        return;
    }

    try {
        const response = await fetch('/eventos/excluir', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                evento_id: id
            })
        });

        const result = await response.json();

        if (result.success) {
            mostrarAlerta('Evento excluído com sucesso!', 'success');
            await carregarEventos();
        } else {
            mostrarAlerta(`Erro: ${result.erro}`, 'error');
        }

    } catch (erro) {
        console.error('Erro ao excluir evento:', erro);
        mostrarAlerta('Erro ao excluir evento', 'error');
    }
}

// ===========================
// ALERTAS
// ===========================

function mostrarAlerta(mensagem, tipo) {
    const container = document.getElementById('alertContainer');

    const alert = document.createElement('div');
    alert.className = tipo === 'success' ? 'alert alert-success' : 'alert alert-error';
    alert.textContent = mensagem;

    container.appendChild(alert);

    // Remover após 5 segundos
    setTimeout(() => {
        alert.remove();
    }, 5000);
}
