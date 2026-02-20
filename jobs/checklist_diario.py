"""
Checklist Diario de Conformidade
================================
Job agendado para executar as 06:00 diariamente.
Valida se o sistema de previsao segue a metodologia documentada.

Modos de Operacao:
==================

1. EXECUCAO MANUAL (para testes):
   python jobs/checklist_diario.py --manual

2. SCHEDULER PYTHON (recomendado para desenvolvimento):
   python jobs/checklist_diario.py

3. SERVICO WINDOWS (recomendado para producao):
   # Instalar como servico:
   python jobs/checklist_diario.py --install

   # Iniciar servico:
   net start ChecklistConformidade

   # Parar servico:
   net stop ChecklistConformidade

   # Remover servico:
   python jobs/checklist_diario.py --remove

4. WINDOWS TASK SCHEDULER (alternativa simples):
   schtasks /create /tn "ChecklistDemanda" /tr "python C:\\...\\jobs\\checklist_diario.py --manual" /sc daily /st 06:00

5. TESTE DE EMAIL:
   python jobs/checklist_diario.py --teste-email

Autor: Valter Lino / Claude (Anthropic)
Data: Fevereiro 2026
"""

import sys
import os
import argparse
import smtplib
import logging
import json
import numpy as np
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime
from pathlib import Path


class NumpyEncoder(json.JSONEncoder):
    """Encoder JSON que converte tipos NumPy para tipos nativos Python."""
    def default(self, obj):
        if isinstance(obj, np.bool_):
            return bool(obj)
        if isinstance(obj, np.integer):
            return int(obj)
        if isinstance(obj, np.floating):
            return float(obj)
        if isinstance(obj, np.ndarray):
            return obj.tolist()
        return super().default(obj)

# Adicionar pasta raiz ao path para imports
ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT_DIR)

# Configurar logging
LOG_DIR = os.path.join(ROOT_DIR, 'logs')
os.makedirs(LOG_DIR, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler(os.path.join(LOG_DIR, 'checklist_conformidade.log')),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

from jobs.configuracao_jobs import CONFIGURACAO_ALERTAS, CONFIGURACAO_BANCO
from core.validador_conformidade import ValidadorConformidade


def obter_conexao_banco():
    """Obtem conexao com o banco de dados."""
    try:
        import psycopg2
        conn = psycopg2.connect(**CONFIGURACAO_BANCO)
        return conn
    except Exception as e:
        logger.warning(f"Nao foi possivel conectar ao banco: {e}")
        return None


def salvar_resultado_banco(conn, resultado: dict, tipo: str = 'cronjob_diario'):
    """
    Salva resultado do checklist no banco de dados.

    Args:
        conn: Conexao com banco de dados
        resultado: Dict com resultado do checklist
        tipo: Tipo de execucao
    """
    if not conn:
        return

    try:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO auditoria_conformidade (
                data_execucao,
                tipo,
                status,
                total_verificacoes,
                verificacoes_ok,
                verificacoes_falha,
                verificacoes_alerta,
                detalhes,
                tempo_execucao_ms,
                alerta_enviado,
                alerta_destinatarios
            ) VALUES (
                NOW(),
                %s,
                %s,
                %s,
                %s,
                %s,
                %s,
                %s,
                %s,
                %s,
                %s
            )
        """, (
            tipo,
            resultado.get('status', 'erro'),
            resultado.get('total_verificacoes', 0),
            resultado.get('verificacoes_ok', 0),
            resultado.get('verificacoes_falha', 0),
            resultado.get('verificacoes_alerta', 0),
            json.dumps({'verificacoes': resultado.get('verificacoes', [])}, cls=NumpyEncoder),
            resultado.get('tempo_execucao_ms'),
            resultado.get('alerta_enviado', False),
            CONFIGURACAO_ALERTAS['email']['destinatarios'] if resultado.get('alerta_enviado') else None
        ))
        conn.commit()
        logger.info("Resultado salvo no banco de dados")
    except Exception as e:
        logger.error(f"Erro ao salvar resultado no banco: {e}")
        conn.rollback()


def enviar_email_alerta(resultado: dict) -> bool:
    """
    Envia email de alerta quando o checklist falha.

    Args:
        resultado: Dict com resultado do checklist

    Returns:
        True se email enviado com sucesso, False caso contrario
    """
    if not CONFIGURACAO_ALERTAS['email']['habilitado']:
        logger.info("Envio de email desabilitado")
        return False

    config = CONFIGURACAO_ALERTAS['email']

    # Montar corpo do email
    status = resultado['status'].upper()
    data = datetime.now().strftime('%d/%m/%Y %H:%M')

    html = f"""
    <html>
    <head>
        <style>
            body {{ font-family: Arial, sans-serif; }}
            .header {{ background-color: {'#dc3545' if status == 'REPROVADO' else '#ffc107'}; color: white; padding: 20px; }}
            .content {{ padding: 20px; }}
            .ok {{ color: green; }}
            .falha {{ color: red; }}
            .alerta {{ color: orange; }}
            table {{ border-collapse: collapse; width: 100%; }}
            th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
            th {{ background-color: #4a5568; color: white; }}
        </style>
    </head>
    <body>
        <div class="header">
            <h2>[{status}] Checklist de Conformidade - Previsao de Demanda</h2>
            <p>Data: {data}</p>
        </div>
        <div class="content">
            <h3>Resumo</h3>
            <p><strong>Status:</strong> {status}</p>
            <p><strong>Verificacoes OK:</strong> {resultado['verificacoes_ok']}/{resultado['total_verificacoes']}</p>
            <p><strong>Tempo de execucao:</strong> {resultado['tempo_execucao_ms']}ms</p>

            <h3>Detalhes das Verificacoes</h3>
            <table>
                <tr>
                    <th>Codigo</th>
                    <th>Nome</th>
                    <th>Status</th>
                    <th>Mensagem</th>
                </tr>
    """

    for v in resultado.get('verificacoes', []):
        classe = 'ok' if v['status'] == 'ok' else ('falha' if v['status'] == 'falha' else 'alerta')
        icone = '✓' if v['status'] == 'ok' else ('✗' if v['status'] == 'falha' else '!')
        html += f"""
                <tr>
                    <td>{v['codigo']}</td>
                    <td>{v['nome']}</td>
                    <td class="{classe}">{icone} {v['status'].upper()}</td>
                    <td>{v['mensagem']}</td>
                </tr>
        """

    html += """
            </table>

            <h3>Acoes Recomendadas</h3>
            <ul>
                <li>Verificar logs do sistema</li>
                <li>Revisar alteracoes recentes no codigo</li>
                <li>Executar testes unitarios</li>
                <li>Contatar equipe de desenvolvimento se necessario</li>
            </ul>

            <p><em>Este email foi gerado automaticamente pelo sistema de conformidade.</em></p>
        </div>
    </body>
    </html>
    """

    try:
        msg = MIMEMultipart('alternative')
        msg['Subject'] = f"{config['assunto_padrao']} - {status}"
        msg['From'] = config.get('remetente', config['destinatarios'][0])
        msg['To'] = ', '.join(config['destinatarios'])

        msg.attach(MIMEText(html, 'html'))

        # Enviar email
        with smtplib.SMTP(config['smtp_server'], config['smtp_port']) as server:
            server.starttls()
            if config.get('smtp_usuario') and config.get('smtp_senha'):
                server.login(config['smtp_usuario'], config['smtp_senha'])
            server.sendmail(
                config.get('remetente', config['destinatarios'][0]),
                config['destinatarios'],
                msg.as_string()
            )

        logger.info(f"Email de alerta enviado para: {', '.join(config['destinatarios'])}")
        return True

    except Exception as e:
        logger.error(f"Falha ao enviar email: {e}")
        return False


def executar_checklist(tipo: str = 'cronjob_diario'):
    """
    Executa o checklist completo de conformidade.

    Args:
        tipo: Tipo de execucao (cronjob_diario, manual, tempo_real)

    Returns:
        Dict com resultado do checklist
    """
    logger.info("=" * 60)
    logger.info("  CHECKLIST DIARIO DE CONFORMIDADE")
    logger.info(f"  Data: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info(f"  Tipo: {tipo}")
    logger.info("=" * 60)

    # Obter conexao com banco (opcional)
    conn = obter_conexao_banco()

    # Executar validacao
    validador = ValidadorConformidade(conn=conn)
    resultado = validador.executar_checklist_completo()

    # Exibir relatorio
    relatorio = validador.gerar_relatorio_texto()
    for linha in relatorio.split('\n'):
        logger.info(linha)

    # Enviar alerta se nao aprovado
    alerta_enviado = False
    if resultado['status'] != 'aprovado':
        logger.warning("Sistema NAO APROVADO - Enviando alerta...")
        alerta_enviado = enviar_email_alerta(resultado)
    else:
        logger.info("Sistema APROVADO - Nenhum alerta necessario")

    # Adicionar flag de alerta enviado
    resultado['alerta_enviado'] = alerta_enviado

    # Salvar resultado no banco
    salvar_resultado_banco(conn, resultado, tipo)

    # Fechar conexao
    if conn:
        conn.close()

    return resultado


def iniciar_scheduler():
    """Inicia o scheduler para execucao diaria usando APScheduler."""
    try:
        from apscheduler.schedulers.blocking import BlockingScheduler
        from apscheduler.triggers.cron import CronTrigger
    except ImportError:
        logger.error("APScheduler nao instalado. Execute: pip install apscheduler")
        logger.info("Alternativa: Use Windows Task Scheduler para agendar execucao")
        return

    scheduler = BlockingScheduler()

    # Agendar para 06:00 diariamente
    hora = CONFIGURACAO_ALERTAS['horario_execucao'].split(':')
    scheduler.add_job(
        executar_checklist,
        CronTrigger(hour=int(hora[0]), minute=int(hora[1])),
        id='checklist_conformidade',
        name='Checklist Diario de Conformidade',
        misfire_grace_time=3600  # 1 hora de tolerancia se perdeu execucao
    )

    logger.info(f"Scheduler iniciado. Checklist agendado para {CONFIGURACAO_ALERTAS['horario_execucao']} diariamente.")
    logger.info("Pressione Ctrl+C para encerrar.")

    try:
        scheduler.start()
    except (KeyboardInterrupt, SystemExit):
        logger.info("Scheduler encerrado pelo usuario.")


# =============================================================================
# SERVICO WINDOWS (Opcional - para producao)
# =============================================================================

def instalar_servico_windows():
    """Instala o checklist como servico Windows."""
    try:
        import win32serviceutil
        import win32service
    except ImportError:
        logger.error("pywin32 nao instalado. Execute: pip install pywin32")
        return

    try:
        # Criar script de servico
        service_script = os.path.join(ROOT_DIR, 'jobs', 'checklist_service.py')
        with open(service_script, 'w') as f:
            f.write('''"""
Servico Windows para Checklist de Conformidade
"""
import win32serviceutil
import win32service
import win32event
import servicemanager
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from jobs.checklist_diario import executar_checklist, CONFIGURACAO_ALERTAS

class ChecklistService(win32serviceutil.ServiceFramework):
    _svc_name_ = 'ChecklistConformidade'
    _svc_display_name_ = 'Checklist de Conformidade - Previsao Demanda'
    _svc_description_ = 'Executa checklist diario de conformidade da metodologia de previsao'

    def __init__(self, args):
        win32serviceutil.ServiceFramework.__init__(self, args)
        self.stop_event = win32event.CreateEvent(None, 0, 0, None)
        self.running = True

    def SvcStop(self):
        self.ReportServiceStatus(win32service.SERVICE_STOP_PENDING)
        win32event.SetEvent(self.stop_event)
        self.running = False

    def SvcDoRun(self):
        from apscheduler.schedulers.background import BackgroundScheduler
        from apscheduler.triggers.cron import CronTrigger

        scheduler = BackgroundScheduler()
        hora = CONFIGURACAO_ALERTAS['horario_execucao'].split(':')
        scheduler.add_job(
            executar_checklist,
            CronTrigger(hour=int(hora[0]), minute=int(hora[1])),
            id='checklist_conformidade'
        )
        scheduler.start()

        while self.running:
            win32event.WaitForSingleObject(self.stop_event, 5000)

        scheduler.shutdown()

if __name__ == '__main__':
    win32serviceutil.HandleCommandLine(ChecklistService)
''')

        logger.info(f"Script de servico criado: {service_script}")
        logger.info("Para instalar o servico, execute como administrador:")
        logger.info(f"  python {service_script} install")
        logger.info("Para iniciar o servico:")
        logger.info("  net start ChecklistConformidade")

    except Exception as e:
        logger.error(f"Erro ao criar script de servico: {e}")


def main():
    """Funcao principal."""
    parser = argparse.ArgumentParser(
        description='Checklist Diario de Conformidade - Sistema de Previsao de Demanda',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Exemplos:
  python checklist_diario.py --manual       Executa o checklist imediatamente
  python checklist_diario.py                Inicia o scheduler (roda 06:00 diariamente)
  python checklist_diario.py --teste-email  Envia um email de teste
  python checklist_diario.py --install      Gera script para servico Windows
        """
    )
    parser.add_argument('--manual', action='store_true',
                        help='Executa checklist imediatamente (sem scheduler)')
    parser.add_argument('--teste-email', action='store_true',
                        help='Envia email de teste para verificar configuracao')
    parser.add_argument('--install', action='store_true',
                        help='Gera script para instalacao como servico Windows')
    parser.add_argument('--verbose', '-v', action='store_true',
                        help='Modo verboso com mais informacoes de debug')

    args = parser.parse_args()

    # Ajustar nivel de log se verbose
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    if args.teste_email:
        logger.info("Enviando email de teste...")
        resultado_teste = {
            'status': 'alerta',
            'total_verificacoes': 10,
            'verificacoes_ok': 8,
            'verificacoes_falha': 0,
            'verificacoes_alerta': 2,
            'tempo_execucao_ms': 1500,
            'verificacoes': [
                {'codigo': 'V01', 'nome': 'Teste Modulos', 'status': 'ok', 'mensagem': 'Todos os modulos carregaram'},
                {'codigo': 'V04', 'nome': 'Sazonalidade', 'status': 'alerta', 'mensagem': 'Indice sazonal 2.3 acima do limite'},
            ]
        }
        if enviar_email_alerta(resultado_teste):
            logger.info("Email de teste enviado com sucesso!")
        else:
            logger.error("Falha ao enviar email de teste")
        return

    if args.install:
        logger.info("Gerando script de servico Windows...")
        instalar_servico_windows()
        return

    if args.manual:
        resultado = executar_checklist(tipo='manual')
        sys.exit(0 if resultado['status'] == 'aprovado' else 1)
    else:
        iniciar_scheduler()


if __name__ == '__main__':
    main()
