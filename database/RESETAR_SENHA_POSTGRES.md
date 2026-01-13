# 🔐 Como Resetar a Senha do PostgreSQL

## Método 1: Resetar Senha (Recomendado)

### Passo 1: Parar o Serviço PostgreSQL

1. Pressione `Windows + R`
2. Digite: `services.msc`
3. Enter
4. Procure por: **postgresql-x64-16**
5. Clique com botão direito → **Parar**

### Passo 2: Editar Arquivo de Configuração

1. Abrir Bloco de Notas **como Administrador**
   - Clique com botão direito no Bloco de Notas
   - "Executar como administrador"

2. Abrir o arquivo:
   ```
   C:\Program Files\PostgreSQL\16\data\pg_hba.conf
   ```

3. Procurar as linhas que começam com:
   ```
   # IPv4 local connections:
   host    all             all             127.0.0.1/32            scram-sha-256
   ```

4. **ALTERAR** `scram-sha-256` para `trust`:
   ```
   host    all             all             127.0.0.1/32            trust
   ```

5. **Salvar** o arquivo

### Passo 3: Reiniciar PostgreSQL

1. Voltar em `services.msc`
2. Clicar com botão direito em **postgresql-x64-16**
3. **Iniciar**

### Passo 4: Alterar a Senha

1. Abrir PowerShell ou CMD

2. Conectar ao PostgreSQL (sem senha agora):
   ```cmd
   "C:\Program Files\PostgreSQL\16\bin\psql.exe" -U postgres
   ```

3. Dentro do PostgreSQL, alterar a senha:
   ```sql
   ALTER USER postgres WITH PASSWORD 'postgres123';
   ```

4. Sair:
   ```
   \q
   ```

### Passo 5: Reverter Configuração de Segurança

1. Abrir novamente (como Administrador):
   ```
   C:\Program Files\PostgreSQL\16\data\pg_hba.conf
   ```

2. **VOLTAR** de `trust` para `scram-sha-256`:
   ```
   host    all             all             127.0.0.1/32            scram-sha-256
   ```

3. **Salvar**

4. Reiniciar o serviço PostgreSQL novamente em `services.msc`

### Passo 6: Testar Nova Senha

```cmd
"C:\Program Files\PostgreSQL\16\bin\psql.exe" -U postgres
```

Quando pedir senha, digite: `postgres123`

---

## Método 2: Senha Simples para Desenvolvimento (Mais Rápido)

Se o Método 1 parecer complicado, podemos usar uma senha simples:

### Opção A: Reinstalar PostgreSQL
- Desinstalar PostgreSQL
- Reinstalar
- Quando pedir senha, usar: `postgres123`
- **Anotar** essa senha!

### Opção B: Criar Novo Usuário

1. Abrir PowerShell como Administrador

2. Se você conseguir entrar no PostgreSQL de alguma forma, criar novo usuário:
   ```sql
   CREATE USER demanda_user WITH PASSWORD 'demanda123' SUPERUSER;
   ```

3. Usar esse usuário no script de importação

---

## ✅ Depois de Resetar a Senha

1. **Anotar** a nova senha (sugestão: `postgres123`)

2. Atualizar o arquivo de importação:
   ```
   database\importar_csvs.py
   ```

   Linha 26, alterar:
   ```python
   'password': 'postgres123',  # Sua nova senha
   ```

3. Prosseguir com a criação do banco!

---

## 🆘 Se Nada Funcionar

Me avise e eu te ajudo com:
- Reinstalação rápida do PostgreSQL
- Criação de banco via outra ferramenta
- Alternativa com SQLite (mais simples, sem senha)

---

**Senha Sugerida:** `postgres123` (fácil de lembrar para desenvolvimento local)
