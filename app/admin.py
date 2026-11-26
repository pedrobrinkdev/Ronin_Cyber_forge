from django.contrib import admin

from .models import Armeiro, Categoria, Contato, ItemPedido, Pedido, Produto, Servico

admin.site.register(Categoria)
admin.site.register(Armeiro)


@admin.register(Servico)
class ServicoAdmin(admin.ModelAdmin):
    list_display = ["nome", "preco", "categoria", "ativo"]
    list_filter = ["categoria", "ativo"]
    search_fields = ["nome", "descricao"]
    ordering = ["nome"]
    list_per_page = 25


@admin.register(Produto)
class ProdutoAdmin(admin.ModelAdmin):
    list_display = ["nome", "tipo", "finalidade", "preco", "estoque", "armeiro", "ativo"]
    list_filter = ["tipo", "finalidade", "ativo", "armeiro"]
    search_fields = ["nome", "descricao"]
    list_editable = ["estoque", "ativo"]


@admin.register(Contato)
class ContatoAdmin(admin.ModelAdmin):
    list_display = ["nome", "email", "criado_em"]
    search_fields = ["nome", "email", "mensagem"]


class ItemInline(admin.TabularInline):
    model = ItemPedido
    extra = 0


@admin.register(Pedido)
class PedidoAdmin(admin.ModelAdmin):
    list_display = ["id", "usuario", "status", "criado_em"]
    list_filter = ["status"]
    inlines = [ItemInline]
