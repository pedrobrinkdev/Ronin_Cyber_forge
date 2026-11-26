from django.urls import path

from . import views

urlpatterns = [
    # Públicas
    path("", views.index, name="index"),
    path("quem-somos/", views.quem_somos, name="quem_somos"),
    path("produtos/", views.produtos, name="produtos"),
    path("contato/", views.contato, name="contato"),

    # Compra (somente logado)
    path("comprar/<int:id_produto>/", views.comprar, name="comprar"),
    path("painel/pedidos/", views.meus_pedidos, name="meus_pedidos"),
    path("painel/pedidos/remover/<int:id_item>/", views.remover_item, name="remover_item"),
    path("painel/pedidos/finalizar/", views.finalizar_pedido, name="finalizar_pedido"),

    # Painel
    path("painel/contatos/", views.painel_contatos, name="painel_contatos"),
    path("painel/contatos/<int:id_contato>/excluir/", views.del_contato, name="del_contato"),

    path("painel/servicos/", views.painel_servicos, name="painel_servicos"),
    path("painel/servicos/novo/", views.add_servico, name="add_servico"),
    path("painel/servicos/<int:id_servico>/editar/", views.edit_servico, name="edit_servico"),
    path("painel/servicos/<int:id_servico>/excluir/", views.del_servico, name="del_servico"),

    path("painel/equipe/", views.painel_equipe, name="painel_equipe"),
    path("painel/equipe/novo/", views.add_integrante, name="add_integrante"),
    path("painel/equipe/<int:id_integrante>/editar/", views.edit_integrante, name="edit_integrante"),
    path("painel/equipe/<int:id_integrante>/excluir/", views.del_integrante, name="del_integrante"),

    path("painel/relatorios/", views.painel_relatorios, name="painel_relatorios"),

    # API REST de categorias
    path("categoria-api/", views.categorias_api, name="categorias_api"),
    path("categoria-api/<int:id_categoria>/", views.categoria_api, name="categoria_api"),
]
