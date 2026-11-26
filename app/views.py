import json
from decimal import Decimal

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.db.models import Avg, Count, F, Max, Min, Q, Sum
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import BasePermission, SAFE_METHODS
from rest_framework.response import Response

from login.permissoes import pode, permissao_required

from . import supabase_client as sb
from .api_externa import buscar_armas_externas
from .forms import FormContato, FormServico
from .models import Categoria, Contato, ItemPedido, Pedido, Produto, Servico
from .serializers import CategoriaSerializer

# Faixas de preço dos serviços (usadas no filtro e nos relatórios)
FAIXA_BAIXO = Decimal('150')
FAIXA_ALTO = Decimal('400')


# ------------------------------------------------------------------ páginas públicas
def index(request):
    destaques = Produto.objects.filter(ativo=True, estoque__gt=0)[:3]
    return render(request, "app/index.html", {"destaques": destaques})


def quem_somos(request):
    try:
        integrantes = sb.listar_integrantes()
    except sb.ErroSupabase:
        integrantes = []
        messages.warning(request, "Não foi possível carregar a equipe agora. Tente novamente em instantes.")
    return render(request, "app/quem_somos.html", {"integrantes": integrantes})


def produtos(request):
    locais = Produto.objects.filter(ativo=True).select_related('armeiro')
    tipo = request.GET.get('tipo')
    if tipo:
        locais = locais.filter(tipo=tipo)
    externos, api_ok = buscar_armas_externas()
    return render(request, "app/produtos.html", {
        "produtos": locais,
        "tipos": Produto.Tipo.choices,
        "tipo": tipo,
        "externos": externos,
        "api_ok": api_ok,
    })


def contato(request):
    form = FormContato(request.POST or None)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Mensagem enviada! Responderemos em breve.")
        return redirect("contato")
    return render(request, "app/contato.html", {"form": form})


# ------------------------------------------------------------------ pedidos (cliente logado)
@login_required
@require_POST
def comprar(request, id_produto):
    produto = get_object_or_404(Produto, pk=id_produto, ativo=True)
    with transaction.atomic():
        pedido, _ = Pedido.objects.get_or_create(usuario=request.user, status=Pedido.Status.CARRINHO)
        item, criado = ItemPedido.objects.get_or_create(
            pedido=pedido, produto=produto, defaults={"preco_unitario": produto.preco, "quantidade": 0})
        if item.quantidade + 1 > produto.estoque:
            if criado:
                item.delete()
            messages.error(request, f"Estoque insuficiente de {produto.nome}.")
            return redirect("produtos")
        item.quantidade += 1
        item.preco_unitario = produto.preco
        item.save()
    messages.success(request, f"{produto.nome} adicionada ao seu pedido.")
    return redirect("meus_pedidos")


@login_required
def meus_pedidos(request):
    carrinho = (Pedido.objects.filter(usuario=request.user, status=Pedido.Status.CARRINHO)
                .prefetch_related('itens__produto').first())
    historico = (Pedido.objects.filter(usuario=request.user, status=Pedido.Status.FINALIZADO)
                 .prefetch_related('itens__produto'))
    return render(request, "app/painel_pedidos.html", {"carrinho": carrinho, "historico": historico})


@login_required
@require_POST
def remover_item(request, id_item):
    item = get_object_or_404(ItemPedido, pk=id_item, pedido__usuario=request.user,
                             pedido__status=Pedido.Status.CARRINHO)
    item.delete()
    messages.success(request, "Item removido do pedido.")
    return redirect("meus_pedidos")


@login_required
@require_POST
def finalizar_pedido(request):
    with transaction.atomic():
        pedido = (Pedido.objects.select_for_update()
                  .filter(usuario=request.user, status=Pedido.Status.CARRINHO).first())
        if not pedido or not pedido.itens.exists():
            messages.error(request, "Seu carrinho está vazio.")
            return redirect("meus_pedidos")
        itens = list(pedido.itens.select_related('produto'))
        for item in itens:
            if item.quantidade > item.produto.estoque:
                messages.error(request, f"Estoque insuficiente de {item.produto.nome}. Ajuste o pedido.")
                return redirect("meus_pedidos")
        for item in itens:
            Produto.objects.filter(pk=item.produto_id).update(estoque=F('estoque') - item.quantidade)
            item.preco_unitario = item.produto.preco
            item.save(update_fields=['preco_unitario'])
        pedido.finalizar()
    messages.success(request, "Pedido finalizado! A forja já está trabalhando nele.")
    return redirect("meus_pedidos")


# ------------------------------------------------------------------ painel: contatos
@permissao_required('contatos')
def painel_contatos(request):
    return render(request, "app/painel_contatos.html", {"contatos": Contato.objects.all()})


@permissao_required('contatos')
@require_POST
def del_contato(request, id_contato):
    get_object_or_404(Contato, pk=id_contato).delete()
    messages.success(request, "Mensagem excluída.")
    return redirect("painel_contatos")


# ------------------------------------------------------------------ painel: serviços
def _filtrar_servicos(request):
    qs = Servico.objects.select_related('categoria')
    busca = request.GET.get('busca', '').strip()
    categoria = request.GET.get('categoria', '')
    preco = request.GET.get('preco', '')
    situacao = request.GET.get('situacao', '')
    ordem = request.GET.get('ordem', 'nome')

    if busca:
        qs = qs.filter(Q(nome__icontains=busca) | Q(descricao__icontains=busca))
    if categoria.isdigit():
        qs = qs.filter(categoria_id=categoria)
    if preco == 'baixo':
        qs = qs.filter(preco__lte=FAIXA_BAIXO)
    elif preco == 'medio':
        qs = qs.filter(preco__gt=FAIXA_BAIXO, preco__lte=FAIXA_ALTO)
    elif preco == 'alto':
        qs = qs.filter(preco__gt=FAIXA_ALTO)
    if situacao == 'ativos':
        qs = qs.filter(ativo=True)
    elif situacao == 'inativos':
        qs = qs.filter(ativo=False)

    qs = qs.order_by({'menor': 'preco', 'maior': '-preco', 'recentes': '-criado_em'}.get(ordem, 'nome'))
    filtros = {'busca': busca, 'categoria': categoria, 'preco': preco, 'situacao': situacao, 'ordem': ordem}
    return qs, filtros


@permissao_required('servicos')
def painel_servicos(request):
    servicos, filtros = _filtrar_servicos(request)
    stats = servicos.aggregate(total=Count('id'), media=Avg('preco'), menor=Min('preco'), maior=Max('preco'),
                               ativos=Count('id', filter=Q(ativo=True)))
    return render(request, "app/painel_servicos.html", {
        "servicos": servicos,
        "stats": stats,
        "categorias": Categoria.objects.filter(ativo=True),
        "filtros": filtros,
        "pode_editar": pode(request.user, 'servicos_editar'),
    })


@permissao_required('servicos_editar')
def add_servico(request):
    form = FormServico(request.POST or None, request.FILES or None)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Serviço cadastrado.")
        return redirect("painel_servicos")
    return render(request, "app/painel_servico_form.html", {"form": form, "titulo": "Novo Serviço"})


@permissao_required('servicos_editar')
def edit_servico(request, id_servico):
    servico = get_object_or_404(Servico, pk=id_servico)
    form = FormServico(request.POST or None, request.FILES or None, instance=servico)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Serviço atualizado.")
        return redirect("painel_servicos")
    return render(request, "app/painel_servico_form.html", {"form": form, "titulo": "Editar Serviço"})


@permissao_required('servicos_editar')
@require_POST
def del_servico(request, id_servico):
    get_object_or_404(Servico, pk=id_servico).delete()
    messages.success(request, "Serviço excluído.")
    return redirect("painel_servicos")


# ------------------------------------------------------------------ painel: equipe (Supabase)
def _dados_integrante(request):
    return {
        "nome": request.POST.get("nome", "").strip(),
        "cargo": request.POST.get("cargo", "").strip(),
        "biografia": request.POST.get("biografia", "").strip(),
        "foto_url": request.POST.get("foto_url", "").strip() or None,
    }


@permissao_required('equipe')
def painel_equipe(request):
    try:
        integrantes = sb.listar_integrantes()
    except sb.ErroSupabase as exc:
        integrantes = []
        messages.error(request, str(exc))
    return render(request, "app/painel_equipe.html", {"integrantes": integrantes})


@permissao_required('equipe')
def add_integrante(request):
    if request.method == "POST":
        dados = _dados_integrante(request)
        if not dados["nome"] or not dados["cargo"]:
            messages.error(request, "Informe nome e cargo.")
        else:
            try:
                sb.criar_integrante(dados)
                messages.success(request, "Integrante adicionado.")
                return redirect("painel_equipe")
            except sb.ErroSupabase as exc:
                messages.error(request, str(exc))
        return render(request, "app/painel_equipe_form.html", {"titulo": "Novo Integrante", "integrante": dados})
    return render(request, "app/painel_equipe_form.html", {"titulo": "Novo Integrante", "integrante": {}})


@permissao_required('equipe')
def edit_integrante(request, id_integrante):
    try:
        integrante = sb.obter_integrante(id_integrante)
    except sb.ErroSupabase as exc:
        messages.error(request, str(exc))
        return redirect("painel_equipe")
    if not integrante:
        messages.error(request, "Integrante não encontrado.")
        return redirect("painel_equipe")

    if request.method == "POST":
        dados = _dados_integrante(request)
        if not dados["nome"] or not dados["cargo"]:
            messages.error(request, "Informe nome e cargo.")
            integrante = {**integrante, **dados}
        else:
            try:
                sb.atualizar_integrante(id_integrante, dados)
                messages.success(request, "Integrante atualizado.")
                return redirect("painel_equipe")
            except sb.ErroSupabase as exc:
                messages.error(request, str(exc))
                integrante = {**integrante, **dados}
    return render(request, "app/painel_equipe_form.html", {"titulo": "Editar Integrante", "integrante": integrante})


@permissao_required('equipe')
@require_POST
def del_integrante(request, id_integrante):
    try:
        sb.excluir_integrante(id_integrante)
        messages.success(request, "Integrante excluído.")
    except sb.ErroSupabase as exc:
        messages.error(request, str(exc))
    return redirect("painel_equipe")


# ------------------------------------------------------------------ painel: relatórios
GRAFICOS = [
    ('categoria', 'Serviços por categoria'),
    ('faixas', 'Faixas de preço'),
    ('media', 'Preço médio por categoria'),
    ('situacao', 'Ativos x inativos'),
]


@permissao_required('relatorios')
def painel_relatorios(request):
    todas = list(Categoria.objects.all())
    opcoes = [(str(c.id), c.nome) for c in todas]
    if Servico.objects.filter(categoria__isnull=True).exists():
        opcoes.append(('sem', 'Sem categoria'))
    validas = {v for v, _ in opcoes}
    chaves_graficos = {k for k, _ in GRAFICOS}

    enviado = request.GET.get('enviado') == '1'
    if enviado:  # o usuário usou o filtro: respeita exatamente o que marcou (inclusive "nenhuma")
        cats = [c for c in request.GET.getlist('cats') if c in validas]
        graficos = [g for g in request.GET.getlist('graficos') if g in chaves_graficos]
    else:        # primeira visita: tudo marcado
        cats = [v for v, _ in opcoes]
        graficos = [k for k, _ in GRAFICOS]

    filtro = Q(categoria_id__in=[int(c) for c in cats if c != 'sem'])
    if 'sem' in cats:
        filtro |= Q(categoria__isnull=True)
    servicos = Servico.objects.filter(filtro) if cats else Servico.objects.none()

    kpis = servicos.aggregate(total=Count('id'), ativos=Count('id', filter=Q(ativo=True)),
                              media=Avg('preco'), maior=Max('preco'), menor=Min('preco'), soma=Sum('preco'))
    kpis['inativos'] = (kpis['total'] or 0) - (kpis['ativos'] or 0)

    agreg = {l['categoria_id']: l for l in servicos.values('categoria_id').annotate(qtd=Count('id'), media=Avg('preco'))}
    linhas = []
    for c in todas:
        if str(c.id) in cats:
            l = agreg.get(c.id)
            linhas.append({'nome': c.nome, 'qtd': l['qtd'] if l else 0, 'media': float(l['media']) if l and l['media'] is not None else 0.0})
    if 'sem' in cats:
        l = agreg.get(None)
        linhas.append({'nome': 'Sem categoria', 'qtd': l['qtd'] if l else 0, 'media': float(l['media']) if l and l['media'] is not None else 0.0})

    faixas = [
        ('Até R$ 150', servicos.filter(preco__lte=FAIXA_BAIXO).count()),
        ('R$ 150 a R$ 400', servicos.filter(preco__gt=FAIXA_BAIXO, preco__lte=FAIXA_ALTO).count()),
        ('Acima de R$ 400', servicos.filter(preco__gt=FAIXA_ALTO).count()),
    ]
    dados = {
        'categorias': [l['nome'] for l in linhas],
        'qtd_categoria': [l['qtd'] for l in linhas],
        'media_categoria': [round(l['media'], 2) for l in linhas],
        'faixas_nomes': [f[0] for f in faixas],
        'faixas_valores': [f[1] for f in faixas],
        'situacao': [kpis['ativos'] or 0, kpis['inativos']],
    }
    return render(request, "app/painel_relatorios.html", {
        "kpis": kpis, "linhas": linhas, "dados": dados,   # dict: o template converte com json_script
        "opcoes": [{'valor': v, 'nome': n, 'marcada': v in cats} for v, n in opcoes],
        "graficos_opcoes": [{'chave': k, 'nome': n, 'marcado': k in graficos} for k, n in GRAFICOS],
        "mostrar": {k: (k in graficos) for k, _ in GRAFICOS},
        "sem_categoria_marcada": not cats,
        "sem_grafico_marcado": not graficos,
        "enviado": enviado,
    })


# ------------------------------------------------------------------ API REST (categorias)
class SomenteAdminEscreve(BasePermission):
    def has_permission(self, request, view):
        return request.method in SAFE_METHODS or bool(request.user and request.user.is_staff)


@api_view(['GET', 'POST'])
@permission_classes([SomenteAdminEscreve])
def categorias_api(request):
    if request.method == 'GET':
        return Response(CategoriaSerializer(Categoria.objects.all(), many=True).data)
    serializer = CategoriaSerializer(data=request.data)
    if serializer.is_valid():
        serializer.save()
        return Response(serializer.data, status=status.HTTP_201_CREATED)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET', 'PUT', 'DELETE'])
@permission_classes([SomenteAdminEscreve])
def categoria_api(request, id_categoria):
    categoria = get_object_or_404(Categoria, pk=id_categoria)
    if request.method == 'GET':
        return Response(CategoriaSerializer(categoria).data)
    if request.method == 'DELETE':
        categoria.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
    serializer = CategoriaSerializer(categoria, data=request.data)
    if serializer.is_valid():
        serializer.save()
        return Response(serializer.data)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
