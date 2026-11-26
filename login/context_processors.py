from .permissoes import SECOES, obter_tipo


def permissoes(request):
    tipo = obter_tipo(request.user)
    return {
        'tipo_usuario': tipo,
        'perm': {secao: (tipo in grupos) for secao, grupos in SECOES.items()} if tipo else {},
    }
