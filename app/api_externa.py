"""API externa exibida em Produtos: armas medievais do Open5e (https://open5e.com).

A URL pode ser trocada com API_ARMAS_URL no .env. Se a API estiver fora do ar a página continua funcionando.
"""
import requests
from django.conf import settings
from django.core.cache import cache

CHAVE_CACHE = "armas_externas_v1"


def _texto(valor):
    if isinstance(valor, dict):
        return str(valor.get("name") or valor.get("title") or "")
    if valor in (None, ""):
        return ""
    return str(valor)


def buscar_armas_externas(limite=9):
    """Devolve (lista_de_armas, ok). Resultado fica em cache por 1h."""
    armas = cache.get(CHAVE_CACHE)
    if armas is not None:
        return armas, True
    try:
        resp = requests.get(settings.API_ARMAS_URL, params={"limit": limite}, timeout=6)
        resp.raise_for_status()
        corpo = resp.json()
    except (requests.RequestException, ValueError):
        return [], False

    itens = corpo.get("results", []) if isinstance(corpo, dict) else corpo
    armas = []
    for a in itens[:limite]:
        armas.append({
            "nome": _texto(a.get("name")),
            "dano": " ".join(filter(None, [_texto(a.get("damage_dice")), _texto(a.get("damage_type"))])),
            "peso": _texto(a.get("weight")),
            "custo": _texto(a.get("cost")),
            "fonte": _texto(a.get("document")) or "Open5e",
        })
    armas = [a for a in armas if a["nome"]]
    cache.set(CHAVE_CACHE, armas, 3600)
    return armas, True
