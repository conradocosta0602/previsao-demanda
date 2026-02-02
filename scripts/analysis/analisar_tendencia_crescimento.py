import pandas as pd
import numpy as np

df = pd.read_excel('dados_teste_integrado.xlsx')
df['Mes'] = pd.to_datetime(df['Mes'])
df_agg = df.groupby('Mes', as_index=False).agg({'Vendas': 'sum'})
vendas = df_agg['Vendas'].tolist()

print('='*80)
print('ANALISE: Ha tendencia de crescimento nos dados?')
print('='*80)

print('\nComparacao YoY (mesmos meses entre 2023 e 2024):')
print('-'*80)
print(f'{"Mes":<15} {"2023":<15} {"2024":<15} {"Crescimento"}')
print('-'*80)

crescimentos = []
for mes in range(1, 7):
    v2023 = vendas[mes-1]
    v2024 = vendas[12+mes-1]
    crescimento = ((v2024/v2023)-1)*100
    crescimentos.append(crescimento)
    mes_nome = pd.Timestamp(year=2023, month=mes, day=1).strftime('%B')
    print(f'{mes_nome:<15} {v2023:>14,.0f} {v2024:>14,.0f} {crescimento:+14.1f}%')

print('-'*80)
print(f'{"MEDIA":<15} {"":>14} {"":>14} {np.mean(crescimentos):+14.1f}%')

print(f'\n{"="*80}')
print('CONCLUSAO:')
print('='*80)

media_cresc = np.mean(crescimentos)
if media_cresc > 5:
    print(f'[INFO] Ha tendencia de CRESCIMENTO de {media_cresc:.1f}% ao ano')
    print(f'\nO modelo sazonal deveria aplicar:')
    print(f'  1. Padrão sazonal (índices mensais)')
    print(f'  2. Tendência de crescimento de ~{media_cresc:.1f}% ao ano')
    print(f'\nSe as previsoes mostram -0.7%, o modelo esta IGNORANDO a tendencia!')
elif media_cresc < -5:
    print(f'[INFO] Ha tendencia de QUEDA de {abs(media_cresc):.1f}% ao ano')
else:
    print(f'[INFO] Nao ha tendencia significativa ({media_cresc:.1f}%)')
    print(f'As previsoes de -0.7% estao coerentes com dados estaveis')
