// Variáveis globais
let transacoes = [];

// Inicialização
document.addEventListener('DOMContentLoaded', function() {
    if (document.getElementById('form-transacao')) {
        configurarFormulario();
    }
    if (document.getElementById('form-relatorio')) {
        configurarFormularioRelatorio();
    }
    
    // Carrega os dados principais, presentes no dashboard
    if (document.getElementById('total-receitas')) {
        carregarDados();
        // Atualizar dados a cada 30 segundos
        setInterval(carregarDados, 30000);
    }
});

function carregarDados() {
    carregarTransacoes();
    carregarSaldo();
    carregarGraficos();
}

// Configurar formulário
function configurarFormulario() {
    const form = document.getElementById('form-transacao');
    const dataInput = document.getElementById('data');
    
    // Definir data atual como padrão
    const hoje = new Date().toISOString().split('T')[0];
    dataInput.value = hoje;
    
    form.addEventListener('submit', function(e) {
        e.preventDefault();
        adicionarTransacao();
    });
}

// API Calls
async function carregarTransacoes() {
    try {
        let url = '/api/transacoes';
        // Se estiver na página inicial, limita para 5 transações
        if (window.location.pathname === '/') {
            url += '?limit=5';
        }
        
        const response = await fetch(url);
        transacoes = await response.json();
        exibirTransacoes();
    } catch (error) {
        console.error('Erro ao carregar transações:', error);
    }
}

async function carregarSaldo() {
    try {
        const response = await fetch('/api/relatorios/saldo');
        const saldo = await response.json();
        
        document.getElementById('total-receitas').textContent = 
            formatarMoeda(saldo.geral.receitas);
        document.getElementById('total-despesas').textContent = 
            formatarMoeda(saldo.geral.despesas);
        document.getElementById('saldo-total').textContent = 
            formatarMoeda(saldo.geral.saldo);
            
        // CORREÇÃO APLICADA AQUI
        const cardSaldo = document.querySelector('.card-saldo');
        if (saldo.geral.saldo >= 0) {
            cardSaldo.classList.remove('negative-saldo');
            cardSaldo.classList.add('positive-saldo');
        } else {
            cardSaldo.classList.remove('positive-saldo');
            cardSaldo.classList.add('negative-saldo');
        }
            
    } catch (error) {
        console.error('Erro ao carregar saldo:', error);
    }
}

async function carregarGraficos() {
    await carregarGraficoMensal();
    await carregarGraficoCategorias();
}

async function carregarGraficoMensal() {
    try {
        const response = await fetch('/api/relatorios/mensal');
        const dados = await response.json();
        
        const meses = dados.map(item => formatarMes(item.mes));
        const receitas = dados.map(item => item.receitas);
        const despesas = dados.map(item => item.despesas);
        const saldos = dados.map(item => item.saldo);
        
        const trace1 = {
            x: meses,
            y: receitas,
            name: 'Receitas',
            type: 'bar',
            marker: { color: '#27ae60' }
        };
        
        const trace2 = {
            x: meses,
            y: despesas,
            name: 'Despesas',
            type: 'bar',
            marker: { color: '#e74c3c' }
        };
        
        const trace3 = {
            x: meses,
            y: saldos,
            name: 'Saldo',
            type: 'line',
            marker: { color: '#3498db' },
            line: { width: 4 }
        };
        
        const layout = {
            barmode: 'group',
            showlegend: true,
            legend: { orientation: 'h' },
            margin: { t: 0, r: 0, b: 30, l: 40 },
            paper_bgcolor: 'rgba(0,0,0,0)',
            plot_bgcolor: 'rgba(0,0,0,0)'
        };
        
        Plotly.newPlot('grafico-mensal', [trace1, trace2, trace3], layout, {
            responsive: true,
            displayModeBar: false
        });
        
    } catch (error) {
        console.error('Erro ao carregar gráfico mensal:', error);
    }
}

async function carregarGraficoCategorias() {
    try {
        const response = await fetch('/api/relatorios/categorias');
        const dados = await response.json();
        
        const categoriasReceita = dados.receitas.map(item => item.categoria);
        const valoresReceita = dados.receitas.map(item => item.total);
        
        const categoriasDespesa = dados.despesas.map(item => item.categoria);
        const valoresDespesa = dados.despesas.map(item => item.total);
        
        const trace1 = {
            labels: categoriasReceita,
            values: valoresReceita,
            name: 'Receitas',
            type: 'pie',
            hole: 0.4,
            domain: { row: 0, column: 0 },
            marker: { colors: ['#27ae60', '#2ecc71', '#1abc9c', '#16a085'] }
        };
        
        const trace2 = {
            labels: categoriasDespesa,
            values: valoresDespesa,
            name: 'Despesas',
            type: 'pie',
            hole: 0.4,
            domain: { row: 0, column: 1 },
            marker: { colors: ['#e74c3c', '#c0392b', '#d35400', '#e67e22'] }
        };
        
        const layout = {
            grid: { rows: 1, columns: 2 },
            showlegend: true,
            paper_bgcolor: 'rgba(0,0,0,0)',
            plot_bgcolor: 'rgba(0,0,0,0)'
        };
        
        Plotly.newPlot('grafico-categorias', [trace1, trace2], layout, {
            responsive: true,
            displayModeBar: false
        });
        
    } catch (error) {
        console.error('Erro ao carregar gráfico de categorias:', error);
    }
}

// Funções de transações
async function adicionarTransacao() {
    const form = document.getElementById('form-transacao');
    
    const transacao = {
        descricao: document.getElementById('descricao').value,
        valor: parseFloat(document.getElementById('valor').value),
        tipo: document.getElementById('tipo').value,
        categoria: document.getElementById('categoria').value,
        data: document.getElementById('data').value
    };
    
    try {
        const response = await fetch('/api/transacoes', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify(transacao)
        });
        
        const result = await response.json();
        
        if (result.success) {
            form.reset();
            document.getElementById('data').value = new Date().toISOString().split('T')[0];
            mostrarMensagem('Transação adicionada com sucesso!', 'success');
            // Redireciona para o dashboard para ver a transação
            setTimeout(() => {
                window.location.href = '/';
            }, 1000);
        } else {
            throw new Error(result.error);
        }
    } catch (error) {
        console.error('Erro ao adicionar transação:', error);
        mostrarMensagem('Erro ao adicionar transação!', 'danger');
    }
}

async function excluirTransacao(id) {
    if (!confirm('Tem certeza que deseja excluir esta transação?')) {
        return;
    }
    
    try {
        const response = await fetch(`/api/transacoes/${id}`, {
            method: 'DELETE'
        });
        
        const result = await response.json();
        
        if (result.success) {
            carregarDados();
            mostrarMensagem('Transação excluída com sucesso!', 'success');
        } else {
            throw new Error(result.error);
        }
    } catch (error) {
        console.error('Erro ao excluir transação:', error);
        mostrarMensagem('Erro ao excluir transação!', 'danger');
    }
}

function exibirTransacoes() {
    const container = document.getElementById('lista-transacoes');
    if (!container) return;

    if (transacoes.length === 0) {
        container.innerHTML = `
            <div class="text-center text-muted py-4">
                <i class="fas fa-receipt fa-3x mb-3"></i>
                <p>Nenhuma transação cadastrada</p>
            </div>
        `;
        return;
    }
    
    container.innerHTML = transacoes.map(transacao => `
        <div class="transacao-item fade-in ${transacao.tipo === 'receita' ? 'transacao-receita' : 'transacao-despesa'}">
            <div class="d-flex justify-content-between align-items-center">
                <div class="flex-grow-1">
                    <h6 class="mb-1">${transacao.descricao}</h6>
                    <small class="text-muted">
                        ${transacao.categoria} • ${formatarData(transacao.data)}
                    </small>
                </div>
                <div class="text-end">
                    <div class="fw-bold ${transacao.tipo === 'receita' ? 'text-success' : 'text-danger'}">
                        ${transacao.tipo === 'receita' ? '+' : '-'} ${formatarMoeda(transacao.valor)}
                    </div>
                    <div class="mt-1">
                        <button class="btn btn-sm btn-outline-danger btn-action" 
                                onclick="excluirTransacao(${transacao.id})"
                                title="Excluir">
                            <i class="fas fa-trash"></i>
                        </button>
                    </div>
                </div>
            </div>
        </div>
    `).join('');
}

// Utilitários
function formatarMoeda(valor) {
    return new Intl.NumberFormat('pt-BR', {
        style: 'currency',
        currency: 'BRL'
    }).format(valor);
}

function formatarData(data) {
    // Adiciona T00:00:00 para evitar problemas de fuso horário
    return new Date(data + 'T00:00:00').toLocaleDateString('pt-BR');
}

function formatarMes(mesAno) {
    const [ano, mes] = mesAno.split('-');
    const meses = [
        'Jan', 'Fev', 'Mar', 'Abr', 'Mai', 'Jun',
        'Jul', 'Ago', 'Set', 'Out', 'Nov', 'Dez'
    ];
    return `${meses[parseInt(mes) - 1]}/${ano}`;
}

function mostrarMensagem(mensagem, tipo) {
    const alerta = document.createElement('div');
    alerta.className = `alert alert-${tipo} alert-dismissible fade show position-fixed`;
    alerta.style.cssText = `
        top: 20px;
        right: 20px;
        z-index: 1050;
        min-width: 300px;
    `;
    alerta.innerHTML = `
        ${mensagem}
        <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
    `;
    
    document.body.appendChild(alerta);
    
    setTimeout(() => {
        if (alerta.parentNode) {
            alerta.parentNode.removeChild(alerta);
        }
    }, 5000);
}

// --- Funções de Relatório ---

let dadosRelatorio = null;

function configurarDatasRelatorio() {
    const hoje = new Date();
    const primeiroDiaMes = new Date(hoje.getFullYear(), hoje.getMonth(), 1);
    
    document.getElementById('data-inicio').value = primeiroDiaMes.toISOString().split('T')[0];
    document.getElementById('data-fim').value = hoje.toISOString().split('T')[0];
}

function configurarFormularioRelatorio() {
    const form = document.getElementById('form-relatorio');
    
    form.addEventListener('submit', function(e) {
        e.preventDefault();
        gerarRelatorio();
    });
    
    configurarDatasRelatorio();
    gerarRelatorio(); // Gera um relatório inicial com as datas padrão
}

async function gerarRelatorio() {
    const dataInicio = document.getElementById('data-inicio').value;
    const dataFim = document.getElementById('data-fim').value;
    const tipo = document.getElementById('tipo-relatorio').value;
    
    if (!dataInicio || !dataFim) {
        mostrarMensagem('Selecione as datas de início e fim!', 'warning');
        return;
    }
    
    const resultadoDiv = document.getElementById('resultado-relatorio');
    resultadoDiv.innerHTML = `
        <div class="text-center py-5">
            <div class="spinner-border text-primary" role="status">
                <span class="visually-hidden">Carregando...</span>
            </div>
        </div>
    `;
    resultadoDiv.style.display = 'block';
    
    try {
        const response = await fetch(`/api/relatorios/detalhado?data_inicio=${dataInicio}&data_fim=${dataFim}&tipo=${tipo}`);
        dadosRelatorio = await response.json();
        
        exibirRelatorio();
        
    } catch (error) {
        console.error('Erro ao gerar relatório:', error);
        mostrarMensagem('Erro ao gerar relatório!', 'danger');
        resultadoDiv.innerHTML = `<div class="alert alert-danger">Erro ao carregar dados.</div>`;
    }
}

function exibirRelatorio() {
    const resultadoDiv = document.getElementById('resultado-relatorio');
    
    if (!dadosRelatorio) {
        resultadoDiv.style.display = 'none';
        return;
    }

    let html = '';

    // Resumo
    const totais = dadosRelatorio.totais;
    const totalReceitas = totais.receita ? totais.receita.total : 0;
    const totalDespesas = totais.despesa ? totais.despesa.total : 0;
    const saldo = totalReceitas - totalDespesas;

    html += `
        <div class="row mb-4" id="resumo-relatorio">
            <div class="col-md-3 mb-3">
                <div class="card card-resumo bg-light">
                    <div class="card-body text-center">
                        <h6 class="card-title text-muted">Transações</h6>
                        <h3 class="text-primary">${dadosRelatorio.transacoes.length}</h3>
                    </div>
                </div>
            </div>
            <div class="col-md-3 mb-3">
                <div class="card card-resumo bg-success bg-opacity-10">
                    <div class="card-body text-center">
                        <h6 class="card-title text-muted">Receitas</h6>
                        <h3 class="text-success">${formatarMoeda(totalReceitas)}</h3>
                    </div>
                </div>
            </div>
            <div class="col-md-3 mb-3">
                <div class="card card-resumo bg-danger bg-opacity-10">
                    <div class="card-body text-center">
                        <h6 class="card-title text-muted">Despesas</h6>
                        <h3 class="text-danger">${formatarMoeda(totalDespesas)}</h3>
                    </div>
                </div>
            </div>
            <div class="col-md-3 mb-3">
                <div class="card card-resumo ${saldo >= 0 ? 'bg-info bg-opacity-10' : 'bg-warning bg-opacity-10'}">
                    <div class="card-body text-center">
                        <h6 class="card-title text-muted">Saldo</h6>
                        <h3 class="${saldo >= 0 ? 'text-info' : 'text-warning'}">${formatarMoeda(saldo)}</h3>
                    </div>
                </div>
            </div>
        </div>
    `;

    // Tabela
    html += `
        <div class="card">
            <div class="card-header d-flex justify-content-between align-items-center">
                <h6 class="mb-0"><i class="fas fa-list-ul me-2"></i>Transações do Período</h6>
                <div>
                    <button class="btn btn-sm btn-outline-secondary" onclick="exportarPDF()">
                        <i class="fas fa-file-pdf me-1"></i>PDF
                    </button>
                    <button class="btn btn-sm btn-outline-secondary" onclick="imprimirRelatorio()">
                        <i class="fas fa-print me-1"></i>Imprimir
                    </button>
                </div>
            </div>
            <div class="card-body p-0">
                <div class="table-responsive">
                    <table class="table table-striped table-hover mb-0" id="tabela-relatorio">
                        <thead class="table-light">
                            <tr>
                                <th>Data</th>
                                <th>Descrição</th>
                                <th>Categoria</th>
                                <th>Tipo</th>
                                <th class="text-end">Valor (R$)</th>
                            </tr>
                        </thead>
                        <tbody>
    `;

    if (dadosRelatorio.transacoes.length === 0) {
        html += `
            <tr>
                <td colspan="5" class="text-center text-muted py-4">
                    Nenhuma transação encontrada para o período selecionado.
                </td>
            </tr>
        `;
    } else {
        dadosRelatorio.transacoes.forEach(transacao => {
            html += `
                <tr>
                    <td>${formatarData(transacao.data)}</td>
                    <td>${transacao.descricao}</td>
                    <td><span class="badge bg-secondary">${transacao.categoria}</span></td>
                    <td>
                        <span class="badge ${transacao.tipo === 'receita' ? 'badge-receita' : 'badge-despesa'}">
                            ${transacao.tipo === 'receita' ? 'Receita' : 'Despesa'}
                        </span>
                    </td>
                    <td class="text-end fw-bold ${transacao.tipo === 'receita' ? 'text-success' : 'text-danger'}">
                        ${transacao.tipo === 'receita' ? '+' : '-'} ${formatarMoeda(transacao.valor)}
                    </td>
                </tr>
            `;
        });
    }

    html += `
                        </tbody>
                        <tfoot class="table-group-divider">
                            <tr>
                                <td colspan="3"></td>
                                <td class="text-end"><strong>Total Receitas:</strong></td>
                                <td class="text-end text-success"><strong>+ ${formatarMoeda(totalReceitas)}</strong></td>
                            </tr>
                            <tr>
                                <td colspan="3"></td>
                                <td class="text-end"><strong>Total Despesas:</strong></td>
                                <td class="text-end text-danger"><strong>- ${formatarMoeda(totalDespesas)}</strong></td>
                            </tr>
                            <tr class="table-active">
                                <td colspan="3"></td>
                                <td class="text-end"><strong>Saldo Final:</strong></td>
                                <td class="text-end ${saldo >= 0 ? 'text-success' : 'text-danger'}">
                                    <strong>${formatarMoeda(saldo)}</strong>
                                </td>
                            </tr>
                        </tfoot>
                    </table>
                </div>
            </div>
        </div>
    `;

    resultadoDiv.innerHTML = html;
}


function exportarPDF() {
    if (!dadosRelatorio) {
        mostrarMensagem('Gere um relatório primeiro!', 'warning');
        return;
    }
    
    const dataInicio = document.getElementById('data-inicio').value;
    const dataFim = document.getElementById('data-fim').value;
    const tipo = document.getElementById('tipo-relatorio').value;
    
    const url = `/relatorio/pdf?data_inicio=${dataInicio}&data_fim=${dataFim}&tipo=${tipo}`;
    window.open(url, '_blank');
}

function imprimirRelatorio() {
    window.print();
}