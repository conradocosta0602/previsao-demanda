# -*- coding: utf-8 -*-
"""
Script para testar senha do PostgreSQL
"""
import sys
import psycopg2

def testar_senha(senha):
    """Testa conexão com PostgreSQL"""
    try:
        conn = psycopg2.connect(
            host='localhost',
            database='postgres',  # banco padrão
            user='postgres',
            password=senha,
            port=5432
        )
        print(f"✅ SENHA CORRETA! Conexão bem-sucedida!")

        # Verificar versão
        cursor = conn.cursor()
        cursor.execute("SELECT version();")
        version = cursor.fetchone()[0]
        print(f"📌 {version}")

        cursor.close()
        conn.close()
        return True

    except psycopg2.OperationalError as e:
        if "authentication failed" in str(e).lower() or "password" in str(e).lower():
            print(f"❌ SENHA INCORRETA")
        else:
            print(f"❌ Erro de conexão: {e}")
        return False
    except Exception as e:
        print(f"❌ Erro: {e}")
        return False

if __name__ == '__main__':
    print("=" * 60)
    print("   TESTE DE SENHA DO POSTGRESQL")
    print("=" * 60)
    print()

    # Senhas comuns para testar
    senhas_comuns = [
        'postgres',
        'postgres123',
        'admin',
        'root',
        '123456',
        'password',
        '1234',
        ''  # senha vazia
    ]

    senha_digitada = input("Digite a senha que você lembra (ou Enter para testar senhas comuns): ").strip()

    if senha_digitada:
        print(f"\n🔍 Testando senha informada...")
        if testar_senha(senha_digitada):
            print(f"\n🎉 Perfeito! Use esta senha: '{senha_digitada}'")
            print(f"\n📝 Atualize o arquivo database/importar_csvs.py:")
            print(f"   Linha 26: 'password': '{senha_digitada}',")
        else:
            print(f"\n💡 Senha incorreta. Quer tentar senhas comuns? (s/n)")
            resposta = input().strip().lower()
            if resposta == 's':
                print("\n🔍 Testando senhas comuns...")
                for senha in senhas_comuns:
                    print(f"  Tentando: '{senha if senha else '(vazia)'}'... ", end='')
                    if testar_senha(senha):
                        print(f"\n\n🎉 Senha encontrada: '{senha if senha else '(vazia)'}'")
                        break
    else:
        print(f"\n🔍 Testando senhas comuns...")
        for senha in senhas_comuns:
            descricao = senha if senha else '(vazia)'
            print(f"\n  Tentando: '{descricao}'... ", end='')
            if testar_senha(senha):
                print(f"\n\n🎉 Senha encontrada: '{descricao}'")
                print(f"\n📝 Atualize o arquivo database/importar_csvs.py:")
                print(f"   Linha 26: 'password': '{senha}',")
                break
        else:
            print(f"\n\n❌ Nenhuma senha comum funcionou.")
            print(f"\n💡 Opções:")
            print(f"  1. Resetar senha (ver RESETAR_SENHA_POSTGRES.md)")
            print(f"  2. Reinstalar PostgreSQL")
            print(f"  3. Usar SQLite (sem senha)")
