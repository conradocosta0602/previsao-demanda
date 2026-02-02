# -*- coding: utf-8 -*-
"""
Módulo de cache para otimização de consultas frequentes.

Implementa cache em memória usando functools.lru_cache.
Para cache distribuído (Redis), descomentar seção apropriada.
"""

from functools import lru_cache, wraps
from datetime import datetime, timedelta
import hashlib
import json


# ============================================
# CACHE EM MEMÓRIA (LRU Cache)
# ============================================

# Tempo de expiração do cache (em segundos)
CACHE_TTL = {
    'fornecedores': 3600,      # 1 hora
    'empresas': 3600,          # 1 hora
    'categorias': 3600,        # 1 hora
    'produtos': 1800,          # 30 minutos
    'parametros': 900,         # 15 minutos
    'abc': 3600,               # 1 hora
}


def timed_lru_cache(seconds: int, maxsize: int = 128):
    """
    Decorator que combina LRU cache com expiração por tempo.

    Args:
        seconds: Tempo de vida do cache em segundos
        maxsize: Número máximo de itens no cache

    Usage:
        @timed_lru_cache(seconds=3600, maxsize=100)
        def get_fornecedores():
            return query_database()
    """
    def decorator(func):
        func = lru_cache(maxsize=maxsize)(func)
        func.lifetime = timedelta(seconds=seconds)
        func.expiration = datetime.utcnow() + func.lifetime

        @wraps(func)
        def wrapped(*args, **kwargs):
            if datetime.utcnow() >= func.expiration:
                func.cache_clear()
                func.expiration = datetime.utcnow() + func.lifetime
            return func(*args, **kwargs)

        wrapped.cache_clear = func.cache_clear
        wrapped.cache_info = func.cache_info

        return wrapped

    return decorator


def make_cache_key(*args, **kwargs):
    """
    Gera chave única para cache baseada nos argumentos.
    """
    key_data = json.dumps({'args': args, 'kwargs': kwargs}, sort_keys=True, default=str)
    return hashlib.md5(key_data.encode()).hexdigest()


# ============================================
# FUNÇÕES DE CACHE ESPECÍFICAS
# ============================================

@timed_lru_cache(seconds=3600, maxsize=10)
def get_fornecedores_cached():
    """
    Retorna lista de fornecedores do banco (cacheado por 1 hora).
    """
    from app.utils.db_connection import get_db_connection
    from psycopg2.extras import RealDictCursor

    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)

    cur.execute("""
        SELECT DISTINCT cnpj, nome_fantasia
        FROM cadastro_fornecedores
        WHERE cnpj IS NOT NULL
        ORDER BY nome_fantasia
    """)

    fornecedores = cur.fetchall()

    cur.close()
    conn.close()

    return [dict(f) for f in fornecedores]


@timed_lru_cache(seconds=3600, maxsize=10)
def get_empresas_cached():
    """
    Retorna lista de empresas/lojas do banco (cacheado por 1 hora).
    """
    from app.utils.db_connection import get_db_connection
    from psycopg2.extras import RealDictCursor

    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)

    cur.execute("""
        SELECT DISTINCT cod_empresa, nome_empresa
        FROM cadastro_empresas
        ORDER BY cod_empresa
    """)

    empresas = cur.fetchall()

    cur.close()
    conn.close()

    return [dict(e) for e in empresas]


@timed_lru_cache(seconds=3600, maxsize=10)
def get_categorias_cached():
    """
    Retorna lista de categorias (Linha 1) do banco (cacheado por 1 hora).
    """
    from app.utils.db_connection import get_db_connection
    from psycopg2.extras import RealDictCursor

    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)

    cur.execute("""
        SELECT DISTINCT linha1
        FROM cadastro_produtos_completo
        WHERE linha1 IS NOT NULL
        ORDER BY linha1
    """)

    categorias = cur.fetchall()

    cur.close()
    conn.close()

    return [c['linha1'] for c in categorias]


@timed_lru_cache(seconds=3600, maxsize=100)
def get_classificacao_abc_cached(cnpj_fornecedor: str = None):
    """
    Retorna classificação ABC dos produtos (cacheado por 1 hora).
    """
    from app.utils.db_connection import get_db_connection
    from psycopg2.extras import RealDictCursor

    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)

    query = """
        SELECT codigo, classificacao_abc
        FROM classificacao_abc
        WHERE classificacao_abc IS NOT NULL
    """

    if cnpj_fornecedor:
        query += " AND cnpj_fornecedor = %s"
        cur.execute(query, (cnpj_fornecedor,))
    else:
        cur.execute(query)

    abc = cur.fetchall()

    cur.close()
    conn.close()

    return {item['codigo']: item['classificacao_abc'] for item in abc}


# ============================================
# GERENCIAMENTO DE CACHE
# ============================================

def clear_all_caches():
    """
    Limpa todos os caches do sistema.
    """
    get_fornecedores_cached.cache_clear()
    get_empresas_cached.cache_clear()
    get_categorias_cached.cache_clear()
    get_classificacao_abc_cached.cache_clear()


def get_cache_stats():
    """
    Retorna estatísticas de uso dos caches.
    """
    return {
        'fornecedores': get_fornecedores_cached.cache_info()._asdict(),
        'empresas': get_empresas_cached.cache_info()._asdict(),
        'categorias': get_categorias_cached.cache_info()._asdict(),
        'abc': get_classificacao_abc_cached.cache_info()._asdict(),
    }


# ============================================
# CACHE COM REDIS (para produção)
# ============================================
"""
Para habilitar cache Redis em produção:

1. Instalar: pip install redis

2. Descomentar código abaixo:

import redis
import pickle

redis_client = redis.Redis(
    host=os.environ.get('REDIS_HOST', 'localhost'),
    port=int(os.environ.get('REDIS_PORT', 6379)),
    db=0
)

def cache_with_redis(key_prefix: str, ttl: int = 3600):
    def decorator(func):
        @wraps(func)
        def wrapped(*args, **kwargs):
            cache_key = f"{key_prefix}:{make_cache_key(*args, **kwargs)}"

            # Tentar obter do cache
            cached = redis_client.get(cache_key)
            if cached:
                return pickle.loads(cached)

            # Executar função e cachear resultado
            result = func(*args, **kwargs)
            redis_client.setex(cache_key, ttl, pickle.dumps(result))

            return result

        return wrapped
    return decorator

def clear_redis_cache(pattern: str = "*"):
    for key in redis_client.scan_iter(pattern):
        redis_client.delete(key)
"""
