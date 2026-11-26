from decimal import Decimal
from unittest import mock

from django.contrib.auth.models import User
from django.core import mail
from django.test import TestCase, override_settings
from django.urls import reverse

from app import supabase_client as sb
from app.models import Armeiro, Categoria, Contato, Pedido, Produto, Servico
from login.models import Perfil


def criar_usuario(nome, tipo='cliente', **extra):
    user = User.objects.create_user(nome, f'{nome}@x.com', 'SenhaForte#123', **extra)
    Perfil.objects.update_or_create(usuario=user, defaults={'tipo_usuario': tipo})
    return user


class BaseTeste(TestCase):
    def setUp(self):
        self.cliente = criar_usuario('cli')
        self.func = criar_usuario('func', 'funcionario')
        self.admin = criar_usuario('adm', 'administrador')
        self.produto = Produto.objects.create(nome='Katana', tipo='katana', finalidade='corte',
                                              preco=Decimal('100'), estoque=2)
        cat = Categoria.objects.create(nome='Manutenção')
        Servico.objects.create(nome='Afiação', preco=Decimal('100'), categoria=cat)
        Servico.objects.create(nome='Restauro', preco=Decimal('500'), categoria=cat, ativo=False)


class PaginasPublicas(BaseTeste):
    def test_home_produtos_contato_publicos(self):
        for nome in ['index', 'produtos', 'contato', 'login', 'cadastro', 'password_reset']:
            self.assertEqual(self.client.get(reverse(nome)).status_code, 200, nome)

    @mock.patch('app.supabase_client.listar_integrantes', return_value=[{'id': 1, 'nome': 'Ana', 'cargo': 'Forja', 'biografia': 'x'}])
    def test_quem_somos_usa_supabase(self, _):
        resp = self.client.get(reverse('quem_somos'))
        self.assertContains(resp, 'Ana')

    @mock.patch('app.supabase_client.listar_integrantes', side_effect=sb.ErroSupabase('fora'))
    def test_quem_somos_nao_quebra_sem_supabase(self, _):
        self.assertEqual(self.client.get(reverse('quem_somos')).status_code, 200)

    def test_contato_sem_login(self):
        resp = self.client.post(reverse('contato'), {'nome': 'A', 'email': 'a@a.com', 'mensagem': 'Oi'})
        self.assertRedirects(resp, reverse('contato'))
        self.assertEqual(Contato.objects.count(), 1)

    @mock.patch('app.views.buscar_armas_externas', return_value=([{'nome': 'Longsword', 'dano': '1d8', 'peso': '3', 'custo': '15', 'fonte': 'SRD'}], True))
    def test_produtos_mostra_api_externa(self, _):
        self.assertContains(self.client.get(reverse('produtos')), 'Longsword')


class Autenticacao(BaseTeste):
    def test_areas_logadas_exigem_login(self):
        for nome in ['dashboard', 'perfil', 'meus_pedidos', 'painel_servicos', 'painel_contatos',
                     'painel_equipe', 'painel_relatorios', 'add_servico']:
            resp = self.client.get(reverse(nome))
            self.assertEqual(resp.status_code, 302, nome)
            self.assertIn('/login/', resp.url)

    def test_comprar_exige_login(self):
        resp = self.client.post(reverse('comprar', args=[self.produto.id]))
        self.assertEqual(resp.status_code, 302)
        self.assertEqual(Pedido.objects.count(), 0)

    def test_admin_redireciona_para_admin(self):
        resp = self.client.post(reverse('login'), {'username': 'adm', 'password': 'SenhaForte#123'})
        self.assertEqual(resp.url, '/admin/')

    def test_cliente_redireciona_para_dashboard(self):
        resp = self.client.post(reverse('login'), {'username': 'cli', 'password': 'SenhaForte#123'})
        self.assertEqual(resp.url, reverse('dashboard'))

    def test_superuser_sem_perfil_nao_da_erro(self):
        su = User.objects.create_superuser('root', 'r@r.com', 'SenhaForte#123')
        self.client.force_login(su)
        self.assertEqual(self.client.get(reverse('dashboard')).url, '/admin/')

    def test_cadastro_cria_cliente(self):
        resp = self.client.post(reverse('cadastro'), {
            'username': 'novo', 'first_name': 'Novo', 'email': 'novo@x.com',
            'password1': 'SenhaForte#123', 'password2': 'SenhaForte#123'})
        self.assertRedirects(resp, reverse('login'))
        self.assertEqual(User.objects.get(username='novo').perfil.tipo_usuario, 'cliente')

    def test_cliente_nao_acessa_area_de_equipe(self):
        self.client.force_login(self.cliente)
        for nome in ['painel_contatos', 'painel_equipe', 'painel_relatorios', 'add_servico']:
            self.assertRedirects(self.client.get(reverse(nome)), reverse('dashboard'), msg_prefix=nome)

    def test_dashboard_mostra_secoes_por_perfil(self):
        self.client.force_login(self.cliente)
        html = self.client.get(reverse('dashboard')).content.decode()
        self.assertIn('Meus Pedidos', html)
        self.assertNotIn('Relatórios', html)
        self.client.force_login(self.func)
        html = self.client.get(reverse('dashboard')).content.decode()
        for s in ['Editar Perfil', 'Contatos', 'Serviços', 'Equipe', 'Meus Pedidos', 'Relatórios']:
            self.assertIn(s, html)

    @override_settings(EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend')
    def test_recuperacao_de_senha_envia_email(self):
        self.client.post(reverse('password_reset'), {'email': 'cli@x.com'})
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn('/login/redefinir/', mail.outbox[0].body)

    def test_editar_perfil(self):
        self.client.force_login(self.cliente)
        self.client.post(reverse('perfil'), {'first_name': 'Novo', 'last_name': 'Nome', 'email': 'novo@x.com'})
        self.cliente.refresh_from_db()
        self.assertEqual(self.cliente.first_name, 'Novo')


class Pedidos(BaseTeste):
    def test_comprar_e_finalizar_baixa_estoque(self):
        self.client.force_login(self.cliente)
        self.client.post(reverse('comprar', args=[self.produto.id]))
        self.client.post(reverse('comprar', args=[self.produto.id]))
        pedido = Pedido.objects.get(usuario=self.cliente)
        self.assertEqual(pedido.itens.get().quantidade, 2)
        self.assertEqual(pedido.total, Decimal('200'))
        self.assertContains(self.client.get(reverse('meus_pedidos')), 'Katana')
        self.client.post(reverse('finalizar_pedido'))
        pedido.refresh_from_db(); self.produto.refresh_from_db()
        self.assertEqual(pedido.status, 'finalizado')
        self.assertEqual(self.produto.estoque, 0)

    def test_nao_compra_alem_do_estoque(self):
        self.client.force_login(self.cliente)
        for _ in range(3):
            self.client.post(reverse('comprar', args=[self.produto.id]))
        self.assertEqual(Pedido.objects.get().itens.get().quantidade, 2)

    def test_get_em_comprar_nao_funciona(self):
        self.client.force_login(self.cliente)
        self.assertEqual(self.client.get(reverse('comprar', args=[self.produto.id])).status_code, 405)

    def test_remover_item(self):
        self.client.force_login(self.cliente)
        self.client.post(reverse('comprar', args=[self.produto.id]))
        item = Pedido.objects.get().itens.get()
        self.client.post(reverse('remover_item', args=[item.id]))
        self.assertEqual(Pedido.objects.get().itens.count(), 0)

    def test_nao_remove_item_de_outro_usuario(self):
        self.client.force_login(self.cliente)
        self.client.post(reverse('comprar', args=[self.produto.id]))
        item = Pedido.objects.get().itens.get()
        self.client.force_login(self.func)
        self.assertEqual(self.client.post(reverse('remover_item', args=[item.id])).status_code, 404)


class PainelEquipe(BaseTeste):
    def test_servicos_filtros_combinados(self):
        self.client.force_login(self.func)
        resp = self.client.get(reverse('painel_servicos'), {'situacao': 'ativos', 'preco': 'baixo'})
        self.assertContains(resp, 'Afiação'); self.assertNotContains(resp, 'Restauro')

    def test_cliente_ve_servicos_sem_botoes_de_edicao(self):
        self.client.force_login(self.cliente)
        resp = self.client.get(reverse('painel_servicos'))
        self.assertEqual(resp.status_code, 200)
        self.assertNotContains(resp, 'Novo serviço')

    def test_crud_servico(self):
        self.client.force_login(self.func)
        cat = Categoria.objects.get()
        self.client.post(reverse('add_servico'), {'nome': 'Novo', 'preco': '10', 'categoria': cat.id, 'ativo': 'on'})
        s = Servico.objects.get(nome='Novo')
        self.client.post(reverse('edit_servico', args=[s.id]), {'nome': 'Editado', 'preco': '12', 'categoria': cat.id})
        s.refresh_from_db(); self.assertEqual(s.nome, 'Editado')
        self.assertEqual(self.client.get(reverse('del_servico', args=[s.id])).status_code, 405)
        self.client.post(reverse('del_servico', args=[s.id]))
        self.assertFalse(Servico.objects.filter(pk=s.id).exists())

    def test_contatos_listar_e_excluir(self):
        c = Contato.objects.create(nome='Z', email='z@z.com', mensagem='Olá forja')
        self.client.force_login(self.func)
        self.assertContains(self.client.get(reverse('painel_contatos')), 'Olá forja')
        self.client.post(reverse('del_contato', args=[c.id]))
        self.assertEqual(Contato.objects.count(), 0)

    def test_relatorios(self):
        self.client.force_login(self.func)
        resp = self.client.get(reverse('painel_relatorios'))
        self.assertContains(resp, 'dados-relatorio')

    @mock.patch('app.supabase_client.criar_integrante')
    @mock.patch('app.supabase_client.atualizar_integrante')
    @mock.patch('app.supabase_client.obter_integrante', return_value={'id': 1, 'nome': 'Ana', 'cargo': 'Forja', 'biografia': '', 'foto_url': None})
    @mock.patch('app.supabase_client.excluir_integrante')
    @mock.patch('app.supabase_client.listar_integrantes', return_value=[{'id': 1, 'nome': 'Ana', 'cargo': 'Forja', 'biografia': ''}])
    def test_crud_equipe_supabase(self, listar, excluir, obter, atualizar, criar):
        self.client.force_login(self.func)
        self.assertContains(self.client.get(reverse('painel_equipe')), 'Ana')
        self.client.post(reverse('add_integrante'), {'nome': 'Bia', 'cargo': 'Vendas', 'biografia': '', 'foto_url': ''})
        criar.assert_called_once()
        self.assertEqual(self.client.get(reverse('edit_integrante', args=[1])).status_code, 200)
        self.client.post(reverse('edit_integrante', args=[1]), {'nome': 'Ana 2', 'cargo': 'Forja', 'biografia': '', 'foto_url': ''})
        atualizar.assert_called_once()
        self.client.post(reverse('del_integrante', args=[1]))
        excluir.assert_called_once_with(1)

    def test_api_categorias_escrita_so_staff(self):
        self.assertEqual(self.client.get('/categoria-api/').status_code, 200)
        self.assertIn(self.client.post('/categoria-api/', {'nome': 'X'}).status_code, (401, 403))
