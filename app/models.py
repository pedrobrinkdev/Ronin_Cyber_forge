from decimal import Decimal

from django.conf import settings
from django.db import models
from django.utils import timezone


class Categoria(models.Model):
    nome = models.CharField(max_length=100, default="Geral")
    descricao = models.TextField(blank=True)
    ativo = models.BooleanField(default=True)

    class Meta:
        ordering = ['nome']

    def __str__(self):
        return self.nome


class Servico(models.Model):
    nome = models.CharField(max_length=150)
    descricao = models.TextField(blank=True)
    preco = models.DecimalField(max_digits=10, decimal_places=2)
    imagem = models.ImageField(upload_to='servicos/', blank=True, null=True)
    ativo = models.BooleanField(default=True)
    criado_em = models.DateTimeField(auto_now_add=True)
    atualizado_em = models.DateTimeField(auto_now=True)
    categoria = models.ForeignKey(Categoria, on_delete=models.PROTECT, related_name='servicos', null=True, blank=True)

    def __str__(self):
        return self.nome


class Contato(models.Model):
    nome = models.CharField(max_length=100)
    email = models.EmailField()
    telefone = models.CharField(max_length=20, blank=True)
    mensagem = models.TextField()
    criado_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-criado_em']

    def __str__(self):
        return f"{self.nome} ({self.email})"


class Armeiro(models.Model):
    """Forjador responsável pela espada (veio do projeto loja_espadas)."""
    nome = models.CharField(max_length=100)
    email = models.EmailField(blank=True)
    telefone = models.CharField(max_length=20, blank=True)

    class Meta:
        ordering = ['nome']

    def __str__(self):
        return self.nome


class Produto(models.Model):
    class Tipo(models.TextChoices):
        KATANA = "katana", "Katana (Japão)"
        WAKIZASHI = "wakizashi", "Wakizashi (Japão)"
        JIAN = "jian", "Jian (China)"
        DAO = "dao", "Dao (China)"
        ESPADA_LONGA = "espada_longa", "Espada Longa (Ocidental)"
        RAPIEIRA = "rapieira", "Rapieira (Ocidental)"
        MONTANTE = "montante", "Montante (Ocidental)"

    class Finalidade(models.TextChoices):
        DECORATIVA = "decorativa", "Decorativa / Coleção"
        TREINO = "treino", "Treino / Prática"
        CORTE = "corte", "Corte / Pronta para combate"

    nome = models.CharField(max_length=120)
    descricao = models.TextField(blank=True)
    tipo = models.CharField(max_length=30, choices=Tipo.choices)
    finalidade = models.CharField(max_length=30, choices=Finalidade.choices)
    preco = models.DecimalField(max_digits=10, decimal_places=2)
    estoque = models.PositiveIntegerField(default=1)
    imagem = models.ImageField(upload_to='produtos/', blank=True, null=True)
    armeiro = models.ForeignKey(Armeiro, on_delete=models.SET_NULL, null=True, blank=True, related_name='produtos')
    ativo = models.BooleanField(default=True)
    criado_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-criado_em']

    def __str__(self):
        return self.nome


class Pedido(models.Model):
    class Status(models.TextChoices):
        CARRINHO = "carrinho", "No carrinho"
        FINALIZADO = "finalizado", "Finalizado"

    usuario = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='pedidos')
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.CARRINHO)
    criado_em = models.DateTimeField(auto_now_add=True)
    finalizado_em = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-criado_em']

    @property
    def total(self):
        return sum((i.subtotal for i in self.itens.all()), Decimal('0'))

    def finalizar(self):
        self.status = self.Status.FINALIZADO
        self.finalizado_em = timezone.now()
        self.save(update_fields=['status', 'finalizado_em'])

    def __str__(self):
        return f"Pedido #{self.pk} - {self.usuario}"


class ItemPedido(models.Model):
    pedido = models.ForeignKey(Pedido, on_delete=models.CASCADE, related_name='itens')
    produto = models.ForeignKey(Produto, on_delete=models.PROTECT, related_name='itens')
    quantidade = models.PositiveIntegerField(default=1)
    preco_unitario = models.DecimalField(max_digits=10, decimal_places=2)

    class Meta:
        constraints = [models.UniqueConstraint(fields=['pedido', 'produto'], name='item_unico_por_pedido')]

    @property
    def subtotal(self):
        return self.preco_unitario * self.quantidade

    def __str__(self):
        return f"{self.quantidade}x {self.produto}"
