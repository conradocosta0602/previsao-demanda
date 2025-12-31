"""
Processador de Fluxos de Reabastecimento
Versão 3.0 - Abas separadas por tipo de fluxo
"""

import pandas as pd
import numpy as np
from typing import Dict, Tuple
from core.replenishment_calculator import ReplenishmentCalculator
from core.demand_calculator import processar_demandas_dataframe


# Ciclos padrão por tipo de fluxo (origem, destino)
CICLOS_PADRAO = {
    ('FORNECEDOR', 'CD'): 30,      # Mensal
    ('FORNECEDOR', 'LOJA'): 14,    # Quinzenal
    ('CD', 'LOJA'): 2,             # 2-3x semana
    ('LOJA', 'LOJA'): 1            # Diário (transferência)
}


def obter_ciclo_padrao(tipo_origem: str, tipo_destino: str) -> int:
    """
    Obtém ciclo de revisão padrão baseado em origem e destino

    Args:
        tipo_origem: FORNECEDOR, CD, ou LOJA
        tipo_destino: CD ou LOJA

    Returns:
        Ciclo em dias
    """
    tipo_origem = str(tipo_origem).upper().strip()
    tipo_destino = str(tipo_destino).upper().strip()

    chave = (tipo_origem, tipo_destino)
    return CICLOS_PADRAO.get(chave, 7)  # Fallback: 7 dias


def ajustar_para_consolidacao(
    quantidade: float,
    lote_minimo: int = 1,
    multiplo_palete: int = 0,
    multiplo_carreta: int = 0
) -> Tuple[int, Dict]:
    """
    Ajusta quantidade para múltiplos de consolidação

    Args:
        quantidade: Quantidade base calculada
        lote_minimo: Unidades por caixa
        multiplo_palete: Unidades por palete (0 = não usar)
        multiplo_carreta: Unidades por carreta (0 = não usar)

    Returns:
        (quantidade_ajustada, detalhes)
    """
    quantidade_original = quantidade
    detalhes = {
        'quantidade_original': quantidade_original,
        'ajustado_caixa': False,
        'ajustado_palete': False,
        'ajustado_carreta': False,
        'numero_caixas': 0,
        'numero_paletes': 0,
        'numero_carretas': 0
    }

    # 1. Ajustar para caixa
    if lote_minimo > 0 and quantidade > 0:
        if quantidade % lote_minimo != 0:
            quantidade = np.ceil(quantidade / lote_minimo) * lote_minimo
            detalhes['ajustado_caixa'] = True
        detalhes['numero_caixas'] = int(quantidade / lote_minimo)

    # 2. Ajustar para palete (apenas se informado)
    if multiplo_palete > 0 and quantidade > 0:
        if quantidade % multiplo_palete != 0:
            quantidade = np.ceil(quantidade / multiplo_palete) * multiplo_palete
            detalhes['ajustado_palete'] = True
        detalhes['numero_paletes'] = int(quantidade / multiplo_palete)

    # 3. Ajustar para carreta (apenas se informado)
    if multiplo_carreta > 0 and quantidade > 0:
        if quantidade % multiplo_carreta != 0:
            quantidade = np.ceil(quantidade / multiplo_carreta) * multiplo_carreta
            detalhes['ajustado_carreta'] = True
        detalhes['numero_carretas'] = int(quantidade / multiplo_carreta)

    detalhes['quantidade_final'] = int(quantidade)
    detalhes['diferenca'] = int(quantidade - quantidade_original)

    return int(quantidade), detalhes


def calcular_nivel_servico_automatico(demanda_media_mensal: float) -> float:
    """
    Define nível de serviço automaticamente baseado em classificação por demanda

    Classificação ABC:
    - Classe A (>500 unid/mês): 98% de nível de serviço
    - Classe B (100-500 unid/mês): 95% de nível de serviço
    - Classe C (<100 unid/mês): 90% de nível de serviço

    Args:
        demanda_media_mensal: Demanda média mensal

    Returns:
        Nível de serviço entre 0.90 e 0.98
    """
    if demanda_media_mensal >= 500:
        return 0.98  # Classe A - alto giro
    elif demanda_media_mensal >= 100:
        return 0.95  # Classe B - médio giro
    else:
        return 0.90  # Classe C - baixo giro


def processar_pedidos_fornecedor(
    df_fornecedor: pd.DataFrame,
    df_historico: pd.DataFrame
) -> Dict:
    """
    Processa aba PEDIDOS_FORNECEDOR

    Compras de fornecedores (para CD ou Lojas)

    Args:
        df_fornecedor: DataFrame com pedidos de fornecedor
        df_historico: DataFrame com histórico de vendas

    Returns:
        Dicionário com resultados e estatísticas
    """
    print("[INFO] Processando PEDIDOS_FORNECEDOR...")

    # 1. Calcular demandas a partir do histórico
    df_demandas = processar_demandas_dataframe(df_historico, metodo='auto')

    resultados = []

    for idx, row in df_fornecedor.iterrows():
        try:
            # 2. Obter tipo de destino e ciclo adequado
            tipo_destino = str(row.get('Tipo_Destino', 'CD')).upper().strip()
            ciclo_informado = row.get('Ciclo_Pedido_Dias')

            if pd.notna(ciclo_informado):
                ciclo_dias = int(ciclo_informado)
            else:
                ciclo_dias = obter_ciclo_padrao('FORNECEDOR', tipo_destino)

            # 3. Buscar demanda calculada
            destino = row['Destino']
            sku = row['SKU']

            # Se destino é CD, agregar demanda de todas as lojas
            if tipo_destino == 'CD':
                demanda_filtro = df_demandas[df_demandas['SKU'] == sku]

                if demanda_filtro.empty:
                    print(f"[AVISO] Sem histórico para SKU {sku}, pulando...")
                    continue

                # Agregar demanda de todas as lojas para este SKU
                demanda_total = demanda_filtro['Demanda_Media_Mensal'].sum()
                desvio_total = (demanda_filtro['Desvio_Padrao_Mensal'] ** 2).sum() ** 0.5

                # Criar info agregada
                demanda_info = {
                    'Demanda_Media_Mensal': demanda_total,
                    'Desvio_Padrao_Mensal': desvio_total,
                    'Metodo_Usado': demanda_filtro.iloc[0]['Metodo_Usado'] if len(demanda_filtro) > 0 else 'N/A'
                }
            else:
                # Se destino é LOJA, buscar demanda específica daquela loja
                demanda_filtro = df_demandas[
                    (df_demandas['Loja'] == destino) &
                    (df_demandas['SKU'] == sku)
                ]

                if demanda_filtro.empty:
                    print(f"[AVISO] Sem histórico para {destino}/{sku}, pulando...")
                    continue

                demanda_info = demanda_filtro.iloc[0]

            # 4. Calcular nível de serviço automaticamente baseado na demanda
            # Acessar demanda para determinar classificação ABC
            if isinstance(demanda_info, dict):
                demanda_para_ns = demanda_info['Demanda_Media_Mensal']
            else:
                demanda_para_ns = demanda_info['Demanda_Media_Mensal']

            nivel_servico = calcular_nivel_servico_automatico(demanda_para_ns)

            calc = ReplenishmentCalculator(nivel_servico)

            # Acessar dados de demanda (pode ser dict ou Series do pandas)
            if isinstance(demanda_info, dict):
                demanda_media = demanda_info['Demanda_Media_Mensal']
                desvio_padrao = demanda_info['Desvio_Padrao_Mensal']
            else:
                demanda_media = demanda_info['Demanda_Media_Mensal']
                desvio_padrao = demanda_info['Desvio_Padrao_Mensal']

            resultado = calc.analisar_item(
                loja=destino,
                sku=sku,
                demanda_media_mensal=demanda_media,
                desvio_padrao_mensal=desvio_padrao,
                lead_time_dias=int(row['Lead_Time_Dias']),
                estoque_disponivel=float(row.get('Estoque_Disponivel', 0)),
                estoque_transito=float(row.get('Estoque_Transito', 0)),
                pedidos_abertos=float(row.get('Pedidos_Abertos', 0)),
                lote_minimo=int(row.get('Lote_Minimo', 1)),
                revisao_dias=ciclo_dias
            )

            # 5. Ajustar para consolidação (palete/carreta)
            quantidade_base = resultado['Quantidade_Pedido']

            if tipo_destino == 'CD':
                # CD pode usar palete/carreta
                multiplo_palete = int(row.get('Multiplo_Palete', 0))
                multiplo_carreta = int(row.get('Multiplo_Carreta', 0))
            else:
                # Loja não usa palete/carreta
                multiplo_palete = 0
                multiplo_carreta = 0

            quantidade_final, detalhes_consolidacao = ajustar_para_consolidacao(
                quantidade_base,
                int(row.get('Lote_Minimo', 1)),
                multiplo_palete,
                multiplo_carreta
            )

            # 6. Calcular custos (se informados)
            custo_unitario = row.get('Custo_Unitario', 0)
            custo_frete = row.get('Custo_Frete', 0)

            if pd.notna(custo_unitario) and pd.notna(custo_frete):
                custo_total = (quantidade_final * custo_unitario) + custo_frete
                custo_unitario_final = custo_total / quantidade_final if quantidade_final > 0 else 0
            else:
                custo_total = None
                custo_unitario_final = None

            # 7. Montar resultado
            resultado_item = {
                'Fornecedor': row['Fornecedor'],
                'SKU': sku,
                'Destino': destino,
                'Tipo_Destino': tipo_destino,
                'Lead_Time_Dias': int(row['Lead_Time_Dias']),
                'Ciclo_Pedido_Dias': ciclo_dias,
                'Demanda_Media_Mensal': demanda_media,
                'Desvio_Padrao_Mensal': desvio_padrao,
                'Nivel_Servico': nivel_servico,  # Nível de serviço automático
                'Metodo_Usado': demanda_info.get('Metodo_Usado', 'N/A') if isinstance(demanda_info, dict) else demanda_info.get('Metodo_Usado', 'N/A'),
                'Estoque_Disponivel': float(row['Estoque_Disponivel']),
                'Estoque_Transito': float(row.get('Estoque_Transito', 0)),
                'Pedidos_Abertos': float(row.get('Pedidos_Abertos', 0)),
                'Estoque_Efetivo': resultado['Estoque_Efetivo'],
                'Ponto_Pedido': resultado['Ponto_Pedido'],
                'Estoque_Seguranca': resultado['Estoque_Seguranca'],
                'Quantidade_Base': quantidade_base,
                'Quantidade_Final': quantidade_final,
                'Numero_Caixas': detalhes_consolidacao['numero_caixas'],
                'Numero_Paletes': detalhes_consolidacao['numero_paletes'],
                'Numero_Carretas': detalhes_consolidacao['numero_carretas'],
                'Foi_Consolidado': quantidade_final > quantidade_base,
                'Diferenca_Consolidacao': detalhes_consolidacao['diferenca'],
                'Cobertura_Dias_Atual': resultado['Cobertura_Atual_Dias'],
                'Cobertura_Dias_Apos_Pedido': resultado['Cobertura_Com_Pedido_Dias'],
                'Custo_Unitario': float(custo_unitario) if pd.notna(custo_unitario) else 0,
                'Custo_Total': custo_total,
                'Custo_Unitario_Final': custo_unitario_final,
                'Deve_Pedir': resultado['Deve_Pedir'],
                'Risco_Ruptura': resultado['Risco_Ruptura']
            }

            resultados.append(resultado_item)

        except Exception as e:
            print(f"[ERRO] Erro ao processar {row.get('Fornecedor')}/{row.get('SKU')}: {e}")
            continue

    df_resultado = pd.DataFrame(resultados)

    # Calcular consolidação por fornecedor
    consolidacao = calcular_consolidacao_fornecedor(df_resultado)

    print(f"[OK] Processados {len(df_resultado)} itens de PEDIDOS_FORNECEDOR")

    return {
        'pedidos': df_resultado,
        'consolidacao': consolidacao,
        'total_itens': len(df_resultado),
        'total_unidades': df_resultado['Quantidade_Final'].sum() if len(df_resultado) > 0 else 0,
        'total_caixas': df_resultado['Numero_Caixas'].sum() if len(df_resultado) > 0 else 0,
        'total_paletes': df_resultado['Numero_Paletes'].sum() if len(df_resultado) > 0 else 0,
        'total_carretas': df_resultado['Numero_Carretas'].sum() if len(df_resultado) > 0 else 0
    }


def processar_pedidos_cd(
    df_cd: pd.DataFrame,
    df_historico: pd.DataFrame
) -> Dict:
    """
    Processa aba PEDIDOS_CD

    Distribuição CD → Loja (com parâmetros de exposição)

    Args:
        df_cd: DataFrame com pedidos de CD para lojas
        df_historico: DataFrame com histórico de vendas

    Returns:
        Dicionário com resultados e alertas
    """
    print("[INFO] Processando PEDIDOS_CD...")

    # 1. Calcular demandas
    df_demandas = processar_demandas_dataframe(df_historico, metodo='auto')

    resultados = []
    alertas_cd = []

    for idx, row in df_cd.iterrows():
        try:
            # 2. Obter ciclo (padrão: 2 dias para CD→Loja)
            ciclo_informado = row.get('Ciclo_Pedido_Dias')
            if pd.notna(ciclo_informado):
                ciclo_dias = int(ciclo_informado)
            else:
                ciclo_dias = obter_ciclo_padrao('CD', 'LOJA')

            # 3. Buscar demanda
            loja_destino = row['Loja_Destino']
            sku = row['SKU']

            demanda_filtro = df_demandas[
                (df_demandas['Loja'] == loja_destino) &
                (df_demandas['SKU'] == sku)
            ]

            if demanda_filtro.empty:
                print(f"[AVISO] Sem histórico para {loja_destino}/{sku}, pulando...")
                continue

            demanda_info = demanda_filtro.iloc[0]

            # 4. Calcular nível de serviço automaticamente
            nivel_servico = calcular_nivel_servico_automatico(demanda_info['Demanda_Media_Mensal'])

            calc = ReplenishmentCalculator(nivel_servico)

            resultado = calc.analisar_item(
                loja=loja_destino,
                sku=sku,
                demanda_media_mensal=demanda_info['Demanda_Media_Mensal'],
                desvio_padrao_mensal=demanda_info['Desvio_Padrao_Mensal'],
                lead_time_dias=int(row['Lead_Time_Dias']),
                estoque_disponivel=float(row.get('Estoque_Disponivel_Loja', 0)),
                estoque_transito=float(row.get('Estoque_Transito', 0)),
                pedidos_abertos=float(row.get('Pedidos_Abertos', 0)),
                lote_minimo=int(row.get('Lote_Minimo', 1)),
                revisao_dias=ciclo_dias
            )

            # 5. Validar parâmetros de exposição (gôndola)
            estoque_min_gondola = int(row.get('Estoque_Min_Gondola', 0))
            numero_frentes = int(row.get('Numero_Frentes', 1))

            if estoque_min_gondola > 0 and numero_frentes > 0:
                estoque_minimo_exposicao = estoque_min_gondola * numero_frentes
                ponto_pedido_original = resultado['Ponto_Pedido']
                ponto_pedido_ajustado = max(ponto_pedido_original, estoque_minimo_exposicao)

                # Recalcular quantidade se ponto de pedido mudou
                if ponto_pedido_ajustado > ponto_pedido_original:
                    demanda_diaria = demanda_info['Demanda_Media_Mensal'] / 30
                    demanda_revisao = demanda_diaria * ciclo_dias
                    estoque_efetivo = resultado['Estoque_Efetivo']

                    quantidade_necessaria = ponto_pedido_ajustado + demanda_revisao - estoque_efetivo

                    if quantidade_necessaria > 0:
                        lote_minimo = int(row.get('Lote_Minimo', 1))
                        quantidade_pedido = int(np.ceil(quantidade_necessaria / lote_minimo) * lote_minimo)
                    else:
                        quantidade_pedido = 0

                    resultado['Ponto_Pedido'] = ponto_pedido_ajustado
                    resultado['Quantidade_Pedido'] = quantidade_pedido
                    resultado['Deve_Pedir'] = 'Sim' if quantidade_pedido > 0 else 'Não'
                    resultado['ajustado_exposicao'] = True
                else:
                    resultado['ajustado_exposicao'] = False

                frentes_cobertas = (resultado['Estoque_Efetivo'] + resultado['Quantidade_Pedido']) / estoque_min_gondola if estoque_min_gondola > 0 else 0
            else:
                resultado['ajustado_exposicao'] = False
                estoque_minimo_exposicao = 0
                frentes_cobertas = 0

            # 6. Validar disponibilidade no CD (se informado)
            estoque_cd = row.get('Estoque_CD')
            if pd.notna(estoque_cd) and estoque_cd > 0:
                if resultado['Quantidade_Pedido'] > estoque_cd:
                    alertas_cd.append({
                        'CD_Origem': row['CD_Origem'],
                        'Loja_Destino': loja_destino,
                        'SKU': sku,
                        'Quantidade_Solicitada': resultado['Quantidade_Pedido'],
                        'Estoque_CD': estoque_cd,
                        'Diferenca': resultado['Quantidade_Pedido'] - estoque_cd,
                        'Alerta': 'CD_INSUFICIENTE'
                    })

            # 7. Obter custo unitário (se disponível)
            custo_unitario = float(row.get('Custo_Unitario', 0))

            # 8. Montar resultado
            resultado_item = {
                'CD_Origem': row['CD_Origem'],
                'Loja_Destino': loja_destino,
                'SKU': sku,
                'Lead_Time_Dias': int(row['Lead_Time_Dias']),
                'Ciclo_Pedido_Dias': ciclo_dias,
                'Demanda_Media_Mensal': demanda_info['Demanda_Media_Mensal'],
                'Nivel_Servico': nivel_servico,  # Nível de serviço automático
                'Metodo_Usado': demanda_info.get('Metodo_Usado', 'N/A'),
                'Estoque_Loja': float(row.get('Estoque_Disponivel_Loja', 0)),
                'Estoque_CD': float(estoque_cd) if pd.notna(estoque_cd) else None,
                'Estoque_Transito': float(row.get('Estoque_Transito', 0)),
                'Estoque_Efetivo': resultado['Estoque_Efetivo'],
                'Ponto_Pedido': resultado['Ponto_Pedido'],
                'Estoque_Seguranca': resultado['Estoque_Seguranca'],
                'Estoque_Min_Gondola': estoque_min_gondola,
                'Numero_Frentes': numero_frentes,
                'Estoque_Min_Exposicao': estoque_minimo_exposicao,
                'Ajustado_Exposicao': resultado.get('ajustado_exposicao', False),
                'Quantidade_Pedido': resultado['Quantidade_Pedido'],
                'Numero_Caixas': int(resultado['Quantidade_Pedido'] / int(row.get('Lote_Minimo', 1))) if int(row.get('Lote_Minimo', 1)) > 0 else 0,
                'Frentes_Cobertas': round(frentes_cobertas, 1),
                'Cobertura_Dias_Atual': resultado['Cobertura_Atual_Dias'],
                'Cobertura_Dias_Apos_Pedido': resultado['Cobertura_Com_Pedido_Dias'],
                'Custo_Unitario': custo_unitario,
                'Deve_Pedir': resultado['Deve_Pedir'],
                'Risco_Ruptura': resultado['Risco_Ruptura'],
                'Alerta': 'CD_INSUFICIENTE' if any(a['SKU'] == sku and a['Loja_Destino'] == loja_destino for a in alertas_cd) else None
            }

            resultados.append(resultado_item)

        except Exception as e:
            print(f"[ERRO] Erro ao processar {row.get('CD_Origem')}/{row.get('Loja_Destino')}/{row.get('SKU')}: {e}")
            continue

    df_resultado = pd.DataFrame(resultados)
    df_alertas = pd.DataFrame(alertas_cd)

    print(f"[OK] Processados {len(df_resultado)} itens de PEDIDOS_CD")
    if len(df_alertas) > 0:
        print(f"[AVISO] {len(df_alertas)} alertas de CD insuficiente")

    return {
        'pedidos': df_resultado,
        'alertas_cd': df_alertas,
        'total_itens': len(df_resultado),
        'total_unidades': df_resultado['Quantidade_Pedido'].sum() if len(df_resultado) > 0 else 0,
        'alertas_count': len(df_alertas)
    }


def processar_transferencias(
    df_transf: pd.DataFrame,
    df_historico: pd.DataFrame
) -> Dict:
    """
    Processa aba TRANSFERENCIAS

    Identifica oportunidades de transferência Loja → Loja

    Args:
        df_transf: DataFrame com transferências possíveis
        df_historico: DataFrame com histórico de vendas

    Returns:
        Dicionário com sugestões de transferências
    """
    print("[INFO] Processando TRANSFERENCIAS...")

    resultados = []

    for idx, row in df_transf.iterrows():
        try:
            loja_origem = row['Loja_Origem']
            loja_destino = row['Loja_Destino']
            sku = row['SKU']

            estoque_origem = float(row['Estoque_Origem'])
            estoque_destino = float(row['Estoque_Destino'])
            demanda_diaria_origem = float(row['Demanda_Diaria_Origem'])
            demanda_diaria_destino = float(row['Demanda_Diaria_Destino'])

            # Calcular coberturas
            cobertura_origem = estoque_origem / demanda_diaria_origem if demanda_diaria_origem > 0 else 999
            cobertura_destino = estoque_destino / demanda_diaria_destino if demanda_diaria_destino > 0 else 999

            # Calcular excesso na origem
            ponto_pedido_origem = demanda_diaria_origem * 14  # 2 semanas de segurança
            excesso_origem = max(0, estoque_origem - ponto_pedido_origem)

            # Calcular necessidade no destino
            ponto_pedido_destino = demanda_diaria_destino * 14
            necessidade_destino = max(0, ponto_pedido_destino - estoque_destino)

            # Quantidade a transferir: mínimo entre excesso e necessidade
            quantidade_transferir = min(excesso_origem, necessidade_destino)

            if quantidade_transferir > 0:
                # Calcular valor do estoque transferido
                custo_unitario = float(row.get('Custo_Unitario_Produto', 0))
                valor_estoque_transferido = quantidade_transferir * custo_unitario

                # Calcular custo operacional da transferência
                custo_transferencia = float(row.get('Custo_Transferencia', 0))
                custo_total_transferencia = quantidade_transferir * custo_transferencia

                # Determinar prioridade
                if cobertura_destino < 3:
                    prioridade = 'ALTA'
                elif cobertura_destino < 7:
                    prioridade = 'MEDIA'
                else:
                    prioridade = 'BAIXA'

                # Coberturas após transferência
                estoque_origem_apos = estoque_origem - quantidade_transferir
                estoque_destino_apos = estoque_destino + quantidade_transferir

                cobertura_origem_apos = estoque_origem_apos / demanda_diaria_origem if demanda_diaria_origem > 0 else 999
                cobertura_destino_apos = estoque_destino_apos / demanda_diaria_destino if demanda_diaria_destino > 0 else 999

                resultado_item = {
                    'Loja_Origem': loja_origem,
                    'Loja_Destino': loja_destino,
                    'SKU': sku,
                    'Estoque_Origem_Antes': estoque_origem,
                    'Estoque_Destino_Antes': estoque_destino,
                    'Cobertura_Origem_Antes': round(cobertura_origem, 1),
                    'Cobertura_Destino_Antes': round(cobertura_destino, 1),
                    'Quantidade_Transferir': int(quantidade_transferir),
                    'Estoque_Origem_Apos': estoque_origem_apos,
                    'Estoque_Destino_Apos': estoque_destino_apos,
                    'Cobertura_Origem_Apos': round(cobertura_origem_apos, 1),
                    'Cobertura_Destino_Apos': round(cobertura_destino_apos, 1),
                    'Custo_Unitario': round(custo_unitario, 2),
                    'Valor_Estoque_Transferido': round(valor_estoque_transferido, 2),
                    'Custo_Operacional_Transferencia': round(custo_total_transferencia, 2),
                    'Prioridade': prioridade,
                    'Lead_Time_Dias': int(row.get('Lead_Time_Dias', 1)),
                    'Distancia_Km': float(row.get('Distancia_Km', 0))
                }

                resultados.append(resultado_item)

        except Exception as e:
            print(f"[ERRO] Erro ao processar transferência {row.get('Loja_Origem')}->{row.get('Loja_Destino')}/{row.get('SKU')}: {e}")
            continue

    df_resultado = pd.DataFrame(resultados)

    # Ordenar por prioridade e valor do estoque transferido
    if len(df_resultado) > 0:
        prioridade_ordem = {'ALTA': 1, 'MEDIA': 2, 'BAIXA': 3}
        df_resultado['_ordem'] = df_resultado['Prioridade'].map(prioridade_ordem)
        df_resultado = df_resultado.sort_values(['_ordem', 'Valor_Estoque_Transferido'], ascending=[True, False])
        df_resultado = df_resultado.drop('_ordem', axis=1)

    print(f"[OK] Identificadas {len(df_resultado)} oportunidades de transferência")

    return {
        'transferencias': df_resultado,
        'total_transferencias': len(df_resultado),
        'total_unidades': df_resultado['Quantidade_Transferir'].sum() if len(df_resultado) > 0 else 0,
        'valor_total_estoque': df_resultado['Valor_Estoque_Transferido'].sum() if len(df_resultado) > 0 else 0,
        'custo_operacional_total': df_resultado['Custo_Operacional_Transferencia'].sum() if len(df_resultado) > 0 else 0,
        'alta_prioridade': len(df_resultado[df_resultado['Prioridade'] == 'ALTA']) if len(df_resultado) > 0 else 0
    }


def calcular_consolidacao_fornecedor(df_pedidos: pd.DataFrame) -> pd.DataFrame:
    """
    Calcula consolidação de pedidos por fornecedor e destino

    Args:
        df_pedidos: DataFrame com pedidos processados

    Returns:
        DataFrame com consolidação
    """
    if df_pedidos.empty:
        return pd.DataFrame()

    # Agrupar por fornecedor e destino
    consolidacao = df_pedidos.groupby(['Fornecedor', 'Destino', 'Tipo_Destino']).agg({
        'Quantidade_Final': 'sum',
        'Numero_Caixas': 'sum',
        'Numero_Paletes': 'sum',
        'Numero_Carretas': 'sum',
        'Custo_Total': 'sum',
        'SKU': 'count'
    }).reset_index()

    consolidacao = consolidacao.rename(columns={'SKU': 'Total_Itens'})

    return consolidacao


def gerar_relatorio_pedido_fornecedor(resultado: Dict, caminho_saida: str):
    """
    Gera arquivo Excel com relatório de pedidos para fornecedor

    Args:
        resultado: Resultado do processamento
        caminho_saida: Caminho do arquivo de saída
    """
    with pd.ExcelWriter(caminho_saida, engine='openpyxl') as writer:
        # Aba 1: Pedidos
        resultado['pedidos'].to_excel(writer, sheet_name='PEDIDOS', index=False)

        # Aba 2: Consolidação
        if not resultado['consolidacao'].empty:
            resultado['consolidacao'].to_excel(writer, sheet_name='CONSOLIDACAO', index=False)

    print(f"[OK] Relatório gerado: {caminho_saida}")


def gerar_relatorio_pedido_cd(resultado: Dict, caminho_saida: str):
    """
    Gera arquivo Excel com relatório de pedidos CD→Lojas

    Args:
        resultado: Resultado do processamento
        caminho_saida: Caminho do arquivo de saída
    """
    with pd.ExcelWriter(caminho_saida, engine='openpyxl') as writer:
        # Aba 1: Pedidos
        resultado['pedidos'].to_excel(writer, sheet_name='PEDIDOS', index=False)

        # Aba 2: Alertas de CD
        if not resultado['alertas_cd'].empty:
            resultado['alertas_cd'].to_excel(writer, sheet_name='ALERTAS_CD', index=False)

    print(f"[OK] Relatório gerado: {caminho_saida}")


def gerar_relatorio_transferencias(resultado: Dict, caminho_saida: str):
    """
    Gera arquivo Excel com sugestões de transferências

    Args:
        resultado: Resultado do processamento
        caminho_saida: Caminho do arquivo de saída
    """
    if resultado['transferencias'].empty:
        print("[INFO] Nenhuma transferência identificada")
        return

    with pd.ExcelWriter(caminho_saida, engine='openpyxl') as writer:
        # Aba 1: Transferências
        resultado['transferencias'].to_excel(writer, sheet_name='TRANSFERENCIAS', index=False)

    print(f"[OK] Relatório gerado: {caminho_saida}")
