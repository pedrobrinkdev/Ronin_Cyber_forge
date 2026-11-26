"""Popula o banco local com dados de exemplo: python manage.py seed [--senha SENHA]"""
from django.contrib.auth.models import User
from django.core.management.base import BaseCommand

from app.models import Armeiro, Categoria, Produto, Servico
from login.models import Perfil


class Command(BaseCommand):
    help = "Cria categorias, serviços, armeiros, produtos e usuários de demonstração."

    def add_arguments(self, parser):
        parser.add_argument("--senha", default="ronin@2026", help="Senha dos usuários de demonstração")

    def handle(self, *args, **opts):
        senha = opts["senha"]

        cats = {n: Categoria.objects.get_or_create(nome=n, defaults={"descricao": d})[0] for n, d in [
            ("Manutenção", "Afiação, polimento e restauro de lâminas"),
            ("Personalização", "Gravações, bainhas e acabamentos sob medida"),
            ("Consultoria", "Orientação para colecionadores e praticantes"),
        ]}
        servicos = [
            ("Afiação tradicional", "Afiação em pedra d'água, com acabamento espelhado.", 120, "Manutenção"),
            ("Polimento de lâmina", "Polimento completo estilo togishi.", 280, "Manutenção"),
            ("Restauro de lâmina antiga", "Remoção de ferrugem e recuperação do fio.", 650, "Manutenção"),
            ("Gravação a laser", "Nome, kanji ou arte na lâmina.", 180, "Personalização"),
            ("Bainha (saya) sob medida", "Saya em madeira laqueada na cor do seu projeto.", 520, "Personalização"),
            ("Tsuba personalizada", "Guarda forjada com desenho exclusivo neon.", 890, "Personalização"),
            ("Consultoria de coleção", "Avaliação e catalogação do seu acervo.", 150, "Consultoria"),
        ]
        for nome, desc, preco, cat in servicos:
            Servico.objects.get_or_create(nome=nome, defaults={"descricao": desc, "preco": preco, "categoria": cats[cat]})

        mas, _ = Armeiro.objects.get_or_create(nome="Mestre Masamune", defaults={"email": "masamune@forja.com", "telefone": "11999999999"})
        sun, _ = Armeiro.objects.get_or_create(nome="Sun Tzu", defaults={"email": "suntzu@forja.com", "telefone": "11988888888"})

        P = Produto
        produtos = [
            ("Katana Vermelha Shinobi", "Katana de aço carbono com saya vermelho laqueado. Equilíbrio perfeito para corte.", P.Tipo.KATANA, P.Finalidade.CORTE, 3200, 4, mas, "produtos/redkatana.jpg"),
            ("Jian dos Três Reinos", "Jian de dois gumes inspirada na guerra dos Três Reinos. Peça de coleção.", P.Tipo.JIAN, P.Finalidade.DECORATIVA, 1800, 3, sun, "produtos/chinese-jian-0.jpeg"),
            ("Wakizashi Neon Ronin", "Lâmina curta de acabamento escuro com fio em degradê roxo.", P.Tipo.WAKIZASHI, P.Finalidade.DECORATIVA, 2100, 5, mas, None),
            ("Dao de Treino Kage", "Dao balanceada e segura para prática de formas.", P.Tipo.DAO, P.Finalidade.TREINO, 750, 8, sun, None),
            ("Espada Longa Cyber Knight", "Espada longa de duas mãos, guarda cromada e pomo luminoso.", P.Tipo.ESPADA_LONGA, P.Finalidade.DECORATIVA, 2600, 2, sun, None),
            ("Rapieira Crimson", "Rapieira de duelo com guarda trabalhada em vermelho escuro.", P.Tipo.RAPIEIRA, P.Finalidade.TREINO, 980, 6, mas, None),
        ]
        for nome, desc, tipo, fin, preco, est, arm, img in produtos:
            Produto.objects.get_or_create(nome=nome, defaults={
                "descricao": desc, "tipo": tipo, "finalidade": fin, "preco": preco,
                "estoque": est, "armeiro": arm, "imagem": img})

        for username, tipo, extra in [("admin", "administrador", {"is_superuser": True, "is_staff": True}),
                                      ("funcionario", "funcionario", {}), ("cliente", "cliente", {})]:
            user, criado = User.objects.get_or_create(username=username, defaults={
                "email": f"{username}@roninforge.local", "first_name": username.capitalize(), **extra})
            if criado:
                user.set_password(senha)
                user.save()
            Perfil.objects.update_or_create(usuario=user, defaults={"tipo_usuario": tipo})

        self.stdout.write(self.style.SUCCESS(
            f"Seed concluído. Usuários: admin / funcionario / cliente (senha: {senha}). TROQUE as senhas em produção."))
