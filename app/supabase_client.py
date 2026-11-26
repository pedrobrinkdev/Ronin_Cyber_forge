"""Banco REMOTO: Supabase (tabela `integrantes`).

Colunas esperadas: id (int, PK), nome (text), cargo (text), biografia (text), foto_url (text).
O cliente é criado só no primeiro uso, assim o site não cai se o Supabase estiver fora/sem chave.
"""
import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent.parent / ".env")

TABELA = "integrantes"
_client = None


class ErroSupabase(Exception):
    """Falha ao falar com o Supabase (sem configuração, rede ou permissão)."""


def _cliente():
    global _client
    if _client is None:
        url, chave = os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_KEY")
        if not url or not chave:
            raise ErroSupabase("Configure SUPABASE_URL e SUPABASE_KEY no arquivo .env")
        try:
            from supabase import create_client
            _client = create_client(url, chave)
        except Exception as exc:  # noqa: BLE001
            raise ErroSupabase(f"Não foi possível conectar ao Supabase: {exc}") from exc
    return _client


def _executar(consulta):
    try:
        return consulta.execute().data
    except ErroSupabase:
        raise
    except Exception as exc:  # noqa: BLE001
        raise ErroSupabase(f"Erro na consulta ao Supabase: {exc}") from exc


def listar_integrantes():
    return _executar(_cliente().table(TABELA).select("*").order("id")) or []


def obter_integrante(id_integrante):
    dados = _executar(_cliente().table(TABELA).select("*").eq("id", id_integrante)) or []
    return dados[0] if dados else None


def criar_integrante(dados):
    return _executar(_cliente().table(TABELA).insert(dados))


def atualizar_integrante(id_integrante, dados):
    return _executar(_cliente().table(TABELA).update(dados).eq("id", id_integrante))


def excluir_integrante(id_integrante):
    return _executar(_cliente().table(TABELA).delete().eq("id", id_integrante))
