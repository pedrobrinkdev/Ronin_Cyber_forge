"""Bateria extra: segurança, dados inválidos, fluxos completos e robustez."""
import re
from decimal import Decimal
from io import StringIO
from unittest import mock

from django.contrib.auth.models import User
from django.core import mail
from django.core.management import call_command
from django.test import Client, TestCase, override_settings
from django.urls import reverse

from app import supabase_client as sb
from app.models import Categoria, Contato, Pedido, Produto, Servico
from login.models import Perfil

RAPIDO = override_settings(PASSWORD_HASHERS=['django.contrib.auth.hashers.MD5PasswordHasher'])
SENHA = 'SenhaForte#123'


def usuario(nome, tipo='cliente'):
    u = User.objects.create_user(nome, f'{nome}@x.com', SENHA)
    Perfil.objects.update_or_create(usuario=u, defaults={'tipo_usuario': tipo})
    return u


@RAPIDO
class Base(TestCase):
    def setUp(self):
        self.cli, self.cli2 = usuario('cli'), usuario('cli2')
        self.func, self.adm = usuario('func', 'funcionario'), usuario('adm', 'administrador')
        self.cat = Categoria.objects.create(nome='Manutenção')
        self.serv = Servico.objects.create(nome='Afiação', preco=Decimal('100'), categoria=self.cat)
        self.prod = Produto.objects.create(nome='Katana', tipo='katana', finalidade='corte', preco=Decimal('100'), estoque=3)


class Cadastro(Base):
    DADOS = {'username': 'novo', 'first_name': 'Novo', 'email': 'novo@x.com', 'password1': SENHA, 'password2': SENHA}

    def test_nao_da_para_se_autopromover_no_cadastro(self):
        self.client.post(reverse('cadastro'), {**self.DADOS, 'tipo_usuario': 'administrador', 'is_staff': 'on', 'is_superuser': 'on'})
        u = User.objects.get(username='novo')
        self.assertEqual(u.perfil.tipo_usuario, 'cliente')
        self.assertFalse(u.is_staff or u.is_superuser)

    def test_email_duplicado_recusado(self):
        r = self.client.post(reverse('cadastro'), {**self.DADOS, 'email': 'CLI@x.com'})
        self.assertEqual(r.status_code, 200); self.assertFalse(User.objects.filter(username='novo').exists())

    def test_senha_fraca_e_diferente_recusadas(self):
        for senha, conf in [('123', '123'), ('12345678', '12345678'), (SENHA, 'outra')]:
            self.client.post(reverse('cadastro'), {**self.DADOS, 'password1': senha, 'password2': conf})
        self.assertFalse(User.objects.filter(username='novo').exists())

    def test_campos_vazios_recusados(self):
        self.assertEqual(self.client.post(reverse('cadastro'), {}).status_code, 200)

    def test_logado_nao_ve_cadastro(self):
        self.client.force_login(self.cli)
        self.assertRedirects(self.client.get(reverse('cadastro')), reverse('dashboard'))


class Login(Base):
    def test_senha_errada_nao_loga(self):
        r = self.client.post(reverse('login'), {'username': 'cli', 'password': 'errada'})
        self.assertEqual(r.status_code, 200); self.assertNotIn('_auth_user_id', self.client.session)

    def test_open_redirect_bloqueado(self):
        r = self.client.post(reverse('login') + '?next=https://evil.com/', {'username': 'cli', 'password': SENHA})
        self.assertEqual(r.url, reverse('dashboard'))

    def test_next_interno_funciona(self):
        r = self.client.post(reverse('login') + '?next=/produtos/', {'username': 'cli', 'password': SENHA})
        self.assertEqual(r.url, '/produtos/')

    def test_admin_ignora_next_e_vai_pro_admin(self):
        r = self.client.post(reverse('login') + '?next=/produtos/', {'username': 'adm', 'password': SENHA})
        self.assertEqual(r.url, '/admin/')

    def test_logout_so_por_post(self):
        self.client.force_login(self.cli)
        self.assertEqual(self.client.get(reverse('logout')).status_code, 405)
        self.client.post(reverse('logout'))
        self.assertNotIn('_auth_user_id', self.client.session)

    def test_cliente_nao_entra_no_admin(self):
        self.client.force_login(self.cli)
        self.assertEqual(self.client.get('/admin/').status_code, 302)

    def test_perfil_administrador_vira_staff(self):
        self.assertTrue(User.objects.get(username='adm').is_staff)
        self.client.force_login(self.adm)
        self.assertEqual(self.client.get('/admin/').status_code, 200)


class Senha(Base):
    @override_settings(EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend')
    def test_fluxo_completo_de_recuperacao(self):
        self.client.post(reverse('password_reset'), {'email': 'cli@x.com'})
        link = re.search(r'https?://\S+(/login/redefinir/\S+)', mail.outbox[0].body).group(1)
        r = self.client.get(link, follow=True)
        self.assertEqual(r.status_code, 200)
        url_final = r.redirect_chain[-1][0]
        r = self.client.post(url_final, {'new_password1': 'NovaSenha#456', 'new_password2': 'NovaSenha#456'})
        self.assertRedirects(r, reverse('password_reset_complete'))
        self.assertTrue(Client().login(username='cli', password='NovaSenha#456'))
        self.assertContains(self.client.get(link, follow=True), 'Link inválido')  # token já usado

    @override_settings(EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend')
    def test_email_inexistente_nao_vaza_e_nao_envia(self):
        r = self.client.post(reverse('password_reset'), {'email': 'ninguem@x.com'})
        self.assertRedirects(r, reverse('password_reset_done')); self.assertEqual(len(mail.outbox), 0)

    def test_token_invalido(self):
        self.assertContains(self.client.get('/login/redefinir/abc/xyz-123/', follow=True), 'Link inválido')

    def test_alterar_senha(self):
        self.client.force_login(self.cli)
        r = self.client.post(reverse('alterar_senha'), {'old_password': 'errada', 'new_password1': 'NovaSenha#456', 'new_password2': 'NovaSenha#456'})
        self.assertEqual(r.status_code, 200)
        r = self.client.post(reverse('alterar_senha'), {'old_password': SENHA, 'new_password1': 'NovaSenha#456', 'new_password2': 'NovaSenha#456'})
        self.assertRedirects(r, reverse('perfil'))
        self.assertTrue(Client().login(username='cli', password='NovaSenha#456'))

    def test_perfil_nao_permite_trocar_username_nem_privilegios(self):
        self.client.force_login(self.cli)
        self.client.post(reverse('perfil'), {'first_name': 'A', 'last_name': 'B', 'email': 'cli@x.com',
                                             'username': 'hacker', 'is_staff': 'on', 'is_superuser': 'on'})
        self.cli.refresh_from_db()
        self.assertEqual(self.cli.username, 'cli'); self.assertFalse(self.cli.is_staff or self.cli.is_superuser)

    def test_perfil_email_de_outro_recusado(self):
        self.client.force_login(self.cli)
        self.client.post(reverse('perfil'), {'first_name': 'A', 'last_name': 'B', 'email': 'cli2@x.com'})
        self.cli.refresh_from_db(); self.assertEqual(self.cli.email, 'cli@x.com')


class Autorizacao(Base):
    def test_anonimo_nao_altera_nada_via_post(self):
        c = Contato.objects.create(nome='z', email='z@z.com', mensagem='m')
        for nome, args in [('del_servico', [self.serv.id]), ('del_contato', [c.id]), ('del_integrante', [1]),
                           ('finalizar_pedido', []), ('comprar', [self.prod.id])]:
            r = self.client.post(reverse(nome, args=args))
            self.assertEqual(r.status_code, 302, nome); self.assertIn('/login/', r.url, nome)
        self.assertTrue(Servico.objects.exists() and Contato.objects.exists())

    def test_cliente_nao_consegue_alterar_dados_da_equipe(self):
        c = Contato.objects.create(nome='z', email='z@z.com', mensagem='m')
        self.client.force_login(self.cli)
        self.client.post(reverse('del_servico', args=[self.serv.id]))
        self.client.post(reverse('del_contato', args=[c.id]))
        self.client.post(reverse('add_servico'), {'nome': 'X', 'preco': '1', 'categoria': self.cat.id})
        with mock.patch('app.supabase_client.excluir_integrante') as ex, mock.patch('app.supabase_client.criar_integrante') as cr:
            self.client.post(reverse('del_integrante', args=[1])); self.client.post(reverse('add_integrante'), {'nome': 'a', 'cargo': 'b'})
            ex.assert_not_called(); cr.assert_not_called()
        self.assertEqual(Servico.objects.count(), 1); self.assertEqual(Contato.objects.count(), 1)

    def test_csrf_obrigatorio(self):
        c = Client(enforce_csrf_checks=True); c.force_login(self.cli)
        self.assertEqual(c.post(reverse('comprar', args=[self.prod.id])).status_code, 403)
        self.assertEqual(c.post(reverse('finalizar_pedido')).status_code, 403)

    def test_api_categorias(self):
        self.assertEqual(self.client.get('/categoria-api/').status_code, 200)
        for metodo, url in [('post', '/categoria-api/'), ('put', f'/categoria-api/{self.cat.id}/'), ('delete', f'/categoria-api/{self.cat.id}/')]:
            self.assertIn(getattr(self.client, metodo)(url, content_type='application/json', data='{"nome":"x"}').status_code, (401, 403), metodo)
        self.assertTrue(Categoria.objects.filter(pk=self.cat.id).exists())
        self.client.force_login(self.adm)
        r = self.client.post('/categoria-api/', {'nome': 'Nova'}, content_type='application/json')
        self.assertEqual(r.status_code, 201)
        self.assertEqual(self.client.post('/categoria-api/', {}, content_type='application/json').status_code, 400)


class Pedidos(Base):
    def test_pedidos_isolados_por_usuario(self):
        self.client.force_login(self.cli); self.client.post(reverse('comprar', args=[self.prod.id]))
        self.client.post(reverse('finalizar_pedido'))
        self.client.force_login(self.cli2)
        self.assertContains(self.client.get(reverse('meus_pedidos')), 'ainda não finalizou')
        self.assertNotContains(self.client.get(reverse('meus_pedidos')), 'Katana')

    def test_finalizar_carrinho_vazio_e_sem_pedido(self):
        self.client.force_login(self.cli)
        self.assertEqual(self.client.post(reverse('finalizar_pedido'), follow=True).status_code, 200)
        self.assertEqual(Pedido.objects.count(), 0)

    def test_produto_inativo_ou_inexistente(self):
        self.client.force_login(self.cli)
        Produto.objects.filter(pk=self.prod.id).update(ativo=False)
        self.assertEqual(self.client.post(reverse('comprar', args=[self.prod.id])).status_code, 404)
        self.assertEqual(self.client.post(reverse('comprar', args=[9999])).status_code, 404)

    def test_estoque_zerado_depois_de_outro_comprar(self):
        a, b = self.cli, self.cli2
        for u in (a, b):
            self.client.force_login(u)
            for _ in range(3): self.client.post(reverse('comprar', args=[self.prod.id]))
        self.client.force_login(a); self.client.post(reverse('finalizar_pedido'))
        self.client.force_login(b); r = self.client.post(reverse('finalizar_pedido'), follow=True)
        self.assertContains(r, 'Estoque insuficiente')
        self.prod.refresh_from_db(); self.assertEqual(self.prod.estoque, 0)
        self.assertEqual(Pedido.objects.filter(status='finalizado').count(), 1)

    def test_preco_congelado_no_pedido_finalizado(self):
        self.client.force_login(self.cli); self.client.post(reverse('comprar', args=[self.prod.id]))
        self.client.post(reverse('finalizar_pedido'))
        Produto.objects.filter(pk=self.prod.id).update(preco=Decimal('999'))
        self.assertEqual(Pedido.objects.get().total, Decimal('100'))


class Validacao(Base):
    def test_servico_preco_negativo_e_invalido(self):
        self.client.force_login(self.func)
        for preco in ['-5', 'abc', '']:
            self.client.post(reverse('add_servico'), {'nome': 'Ruim', 'preco': preco, 'categoria': self.cat.id})
        self.assertFalse(Servico.objects.filter(nome='Ruim').exists())

    def test_servico_inexistente_da_404_e_nao_500(self):
        self.client.force_login(self.func)
        self.assertEqual(self.client.get(reverse('edit_servico', args=[9999])).status_code, 404)
        self.assertEqual(self.client.post(reverse('del_servico', args=[9999])).status_code, 404)

    def test_contato_invalido(self):
        for d in [{'nome': 'A', 'email': 'nao-e-email', 'mensagem': 'x'}, {'nome': '', 'email': 'a@a.com', 'mensagem': 'x'}, {'nome': 'A', 'email': 'a@a.com', 'mensagem': ''}]:
            self.assertEqual(self.client.post(reverse('contato'), d).status_code, 200)
        self.assertEqual(Contato.objects.count(), 0)

    def test_filtros_com_lixo_nao_quebram(self):
        self.client.force_login(self.func)
        r = self.client.get(reverse('painel_servicos'), {'categoria': "1;DROP TABLE", 'preco': "'--", 'ordem': 'xxx', 'busca': "' OR 1=1"})
        self.assertEqual(r.status_code, 200)

    def test_equipe_valida_nome_e_cargo(self):
        self.client.force_login(self.func)
        with mock.patch('app.supabase_client.criar_integrante') as cr:
            self.client.post(reverse('add_integrante'), {'nome': '', 'cargo': ''}); cr.assert_not_called()

    def test_equipe_erro_do_supabase_nao_derruba(self):
        self.client.force_login(self.func)
        with mock.patch('app.supabase_client.listar_integrantes', side_effect=sb.ErroSupabase('sem rede')):
            self.assertContains(self.client.get(reverse('painel_equipe')), 'sem rede')
        with mock.patch('app.supabase_client.criar_integrante', side_effect=sb.ErroSupabase('negado')):
            self.assertContains(self.client.post(reverse('add_integrante'), {'nome': 'a', 'cargo': 'b'}), 'negado')
        with mock.patch('app.supabase_client.obter_integrante', return_value=None):
            self.assertRedirects(self.client.get(reverse('edit_integrante', args=[5])), reverse('painel_equipe'))

    def test_sem_variaveis_supabase_da_erro_amigavel(self):
        sb._client = None
        with mock.patch.dict('os.environ', {'SUPABASE_URL': '', 'SUPABASE_KEY': ''}):
            with self.assertRaises(sb.ErroSupabase): sb.listar_integrantes()

    def test_api_externa_resiliente(self):
        import requests
        from django.core.cache import cache
        from app.api_externa import buscar_armas_externas
        cache.clear()
        with mock.patch('requests.get', side_effect=requests.ConnectionError()):
            self.assertEqual(buscar_armas_externas(), ([], False))
        resp = mock.Mock(); resp.raise_for_status.return_value = None
        resp.json.return_value = {'results': [{'name': 'Longsword', 'damage_dice': '1d8', 'damage_type': {'name': 'slashing'}, 'document': {'name': 'SRD'}}, {'sem_nome': 1}]}
        with mock.patch('requests.get', return_value=resp):
            armas, ok = buscar_armas_externas()
        self.assertTrue(ok); self.assertEqual(len(armas), 1); self.assertIn('slashing', armas[0]['dano'])
        cache.clear()
        resp.json.side_effect = ValueError()
        with mock.patch('requests.get', return_value=resp):
            self.assertEqual(buscar_armas_externas(), ([], False))


class XSS(Base):
    def test_mensagem_de_contato_escapada(self):
        Contato.objects.create(nome='<b>x</b>', email='z@z.com', mensagem='<script>alert(1)</script>')
        self.client.force_login(self.func)
        html = self.client.get(reverse('painel_contatos')).content.decode()
        self.assertNotIn('<script>alert(1)</script>', html); self.assertIn('&lt;script&gt;', html)

    @mock.patch('app.supabase_client.listar_integrantes', return_value=[{'id': 1, 'nome': '<img src=x onerror=alert(1)>', 'cargo': 'c', 'biografia': '<script>x</script>'}])
    def test_integrante_do_supabase_escapado(self, _):
        html = self.client.get(reverse('quem_somos')).content.decode()
        self.assertNotIn('<img src=x', html); self.assertNotIn('<script>x</script>', html)

    def test_nome_de_produto_escapado_e_busca_refletida(self):
        Produto.objects.create(nome='<script>p</script>', tipo='katana', finalidade='corte', preco=1, estoque=1)
        self.assertNotIn('<script>p</script>', self.client.get(reverse('produtos')).content.decode())
        self.client.force_login(self.func)
        self.assertNotIn('<script>q</script>', self.client.get(reverse('painel_servicos'), {'busca': '<script>q</script>'}).content.decode())


class Robustez(Base):
    def test_seed_idempotente(self):
        call_command('seed', stdout=StringIO()); n = (Produto.objects.count(), Servico.objects.count(), User.objects.count())
        call_command('seed', stdout=StringIO())
        self.assertEqual(n, (Produto.objects.count(), Servico.objects.count(), User.objects.count()))

    def test_sem_migrations_pendentes(self):
        call_command('makemigrations', '--check', '--dry-run', stdout=StringIO())

    def test_funcionario_abre_todas_as_telas_do_painel(self):
        call_command('seed', stdout=StringIO())
        self.client.force_login(self.func)
        with mock.patch('app.supabase_client.listar_integrantes', return_value=[]):
            for nome in ['dashboard', 'perfil', 'alterar_senha', 'meus_pedidos', 'painel_servicos', 'add_servico', 'painel_contatos', 'painel_equipe', 'add_integrante', 'painel_relatorios']:
                self.assertEqual(self.client.get(reverse(nome)).status_code, 200, nome)
        self.assertEqual(self.client.get(reverse('edit_servico', args=[Servico.objects.first().id])).status_code, 200)

    def test_relatorios_sem_nenhum_servico(self):
        Servico.objects.all().delete(); self.client.force_login(self.func)
        self.assertEqual(self.client.get(reverse('painel_relatorios')).status_code, 200)
        self.assertEqual(self.client.get(reverse('painel_servicos')).status_code, 200)

    def test_staff_sem_perfil_nao_quebra(self):
        u = User.objects.create_user('semperfil', password=SENHA); Perfil.objects.filter(usuario=u).delete()
        self.client.force_login(u); self.assertEqual(self.client.get(reverse('dashboard')).status_code, 200)

    def test_pagina_404_e_metodo_errado(self):
        self.assertEqual(self.client.get('/nao-existe/').status_code, 404)
        self.client.force_login(self.cli)
        self.assertEqual(self.client.get(reverse('finalizar_pedido')).status_code, 405)


class VoltarAoSite(Base):
    def test_todo_logado_tem_botao_de_voltar_ao_site(self):
        for u in (self.cli, self.func):
            self.client.force_login(u)
            for nome in ['dashboard', 'perfil', 'meus_pedidos', 'painel_servicos']:
                html = self.client.get(reverse(nome)).content.decode()
                self.assertIn('Voltar ao site', html, nome)
                self.assertIn('href="/"', html, nome)


import json as _json


def _dados_relatorio(resp):
    m = re.search(r'<script id="dados-relatorio" type="application/json">(.*?)</script>', resp.content.decode(), re.S)
    return _json.loads(m.group(1))


class RelatoriosFiltros(Base):
    def setUp(self):
        super().setUp()
        self.cat2 = Categoria.objects.create(nome='Personalização')
        self.cat3 = Categoria.objects.create(nome='Consultoria')  # sem serviços
        Servico.objects.create(nome='Gravação', preco=Decimal('200'), categoria=self.cat2)
        Servico.objects.create(nome='Tsuba', preco=Decimal('900'), categoria=self.cat2, ativo=False)
        Servico.objects.create(nome='Solto', preco=Decimal('50'))  # sem categoria
        self.client.force_login(self.func)
        self.url = reverse('painel_relatorios')

    def test_dados_chegam_como_objeto_e_nao_como_texto(self):
        d = _dados_relatorio(self.client.get(self.url))
        self.assertIsInstance(d, dict)  # bug antigo: vinha duplamente codificado (str) e nenhum gráfico desenhava
        for chave in ['categorias', 'qtd_categoria', 'media_categoria', 'faixas_nomes', 'faixas_valores', 'situacao']:
            self.assertIn(chave, d)

    def test_padrao_mostra_tudo(self):
        r = self.client.get(self.url)
        for canvas in ['gCategoria', 'gFaixas', 'gMedia', 'gSituacao']:
            self.assertContains(r, f'id="{canvas}"')
        d = _dados_relatorio(r)
        self.assertEqual(sum(d['qtd_categoria']), 4)
        self.assertIn('Sem categoria', d['categorias'])

    def test_uma_categoria(self):
        d = _dados_relatorio(self.client.get(self.url, {'enviado': '1', 'cats': [self.cat2.id], 'graficos': ['categoria']}))
        self.assertEqual(d['categorias'], ['Personalização']); self.assertEqual(d['qtd_categoria'], [2])
        self.assertEqual(d['media_categoria'], [550.0]); self.assertEqual(d['situacao'], [1, 1])

    def test_duas_categorias_inclui_categoria_vazia_com_zero(self):
        d = _dados_relatorio(self.client.get(self.url, {'enviado': '1', 'cats': [self.cat.id, self.cat3.id], 'graficos': ['categoria']}))
        self.assertEqual(dict(zip(d['categorias'], d['qtd_categoria'])), {'Manutenção': 1, 'Consultoria': 0})

    def test_nenhuma_categoria(self):
        r = self.client.get(self.url, {'enviado': '1', 'graficos': ['categoria']})
        self.assertContains(r, 'Nenhuma categoria selecionada'); self.assertNotContains(r, 'id="gCategoria"')

    def test_escolher_quais_graficos(self):
        r = self.client.get(self.url, {'enviado': '1', 'cats': [self.cat.id], 'graficos': ['faixas', 'situacao']})
        self.assertContains(r, 'id="gFaixas"'); self.assertContains(r, 'id="gSituacao"')
        self.assertNotContains(r, 'id="gCategoria"'); self.assertNotContains(r, 'id="gMedia"')

    def test_nenhum_grafico(self):
        r = self.client.get(self.url, {'enviado': '1', 'cats': [self.cat.id]})
        self.assertContains(r, 'Nenhum gráfico selecionado')

    def test_faixas_de_preco_respeitam_filtro(self):
        d = _dados_relatorio(self.client.get(self.url, {'enviado': '1', 'cats': [self.cat2.id], 'graficos': ['faixas']}))
        self.assertEqual(d['faixas_valores'], [0, 1, 1])  # 200 -> médio, 900 -> alto

    def test_parametros_invalidos_nao_quebram(self):
        r = self.client.get(self.url, {'enviado': '1', 'cats': ['abc', '9999', "1;DROP"], 'graficos': ['xx']})
        self.assertEqual(r.status_code, 200)

    def test_chartjs_local_existe(self):
        self.assertContains(self.client.get(self.url), 'chart.umd.min.js')
        from django.contrib.staticfiles import finders
        self.assertIsNotNone(finders.find('js/chart.umd.min.js'))


class AvisosEUsuario(Base):
    def test_avisos_de_login(self):
        r = self.client.post(reverse('login'), {'username': 'cli', 'password': 'errada'})
        self.assertContains(r, 'usuário ou senha incorretos')
        r = self.client.post(reverse('login'), {'username': 'cli', 'password': SENHA}, follow=True)
        self.assertContains(r, 'Login realizado com sucesso')

    def test_aviso_de_logout(self):
        self.client.force_login(self.cli)
        self.assertContains(self.client.post(reverse('logout'), follow=True), 'Você saiu da sua conta')

    def test_avisos_de_cadastro(self):
        self.assertContains(self.client.post(reverse('cadastro'), {'username': 'a'}), 'Não foi possível criar a conta')
        r = self.client.post(reverse('cadastro'), {'username': 'novo2', 'first_name': 'N', 'email': 'n2@x.com',
                                                   'password1': SENHA, 'password2': SENHA}, follow=True)
        self.assertContains(r, 'Conta criada com sucesso')

    def test_avisos_de_senha_e_perfil(self):
        self.client.force_login(self.cli)
        self.assertContains(self.client.post(reverse('alterar_senha'), {'old_password': 'x', 'new_password1': 'a', 'new_password2': 'b'}), 'Não foi possível alterar a senha')
        r = self.client.post(reverse('alterar_senha'), {'old_password': SENHA, 'new_password1': 'NovaSenha#456', 'new_password2': 'NovaSenha#456'}, follow=True)
        self.assertContains(r, 'Senha alterada com sucesso')
        self.assertContains(self.client.post(reverse('perfil'), {'first_name': 'A', 'last_name': 'B', 'email': 'cli2@x.com'}), 'Não foi possível salvar o perfil')
        self.assertContains(self.client.post(reverse('perfil'), {'first_name': 'A', 'last_name': 'B', 'email': 'ok@x.com'}, follow=True), 'Perfil atualizado com sucesso')

    def test_usuario_logado_aparece_no_topo_do_site_e_do_painel(self):
        self.assertNotContains(self.client.get(reverse('index')), 'chip-usuario')
        self.client.force_login(self.cli)
        for nome in ['index', 'produtos', 'contato', 'dashboard', 'meus_pedidos']:
            html = self.client.get(reverse(nome)).content.decode()
            self.assertIn('chip-usuario', html, nome); self.assertIn('Cli', html, nome); self.assertIn('Cliente', html, nome)
