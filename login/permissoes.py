"""Regras de acesso por perfil (administrador / funcionário / cliente)."""
from functools import wraps

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect

from .models import Perfil

TODOS = {'administrador', 'funcionario', 'cliente'}
EQUIPE = {'administrador', 'funcionario'}

SECOES = {
    'perfil': TODOS,
    'pedidos': TODOS,
    'servicos': TODOS,            # visualizar
    'servicos_editar': EQUIPE,    # adicionar / editar / excluir
    'contatos': EQUIPE,
    'equipe': EQUIPE,
    'relatorios': EQUIPE,
}


def obter_tipo(user):
    if not user.is_authenticated:
        return None
    if user.is_superuser:
        return 'administrador'
    perfil, _ = Perfil.objects.get_or_create(usuario=user)
    return perfil.tipo_usuario


def pode(user, secao):
    return obter_tipo(user) in SECOES.get(secao, set())


def permissao_required(secao):
    """Exige login + permissão para a seção. Sem permissão volta ao dashboard."""
    def decorador(view):
        @wraps(view)
        @login_required
        def interna(request, *args, **kwargs):
            if not pode(request.user, secao):
                messages.error(request, "Você não tem permissão para acessar essa área.")
                return redirect('dashboard')
            return view(request, *args, **kwargs)
        return interna
    return decorador
