from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import LoginView, LogoutView, PasswordChangeView
from django.contrib.messages.views import SuccessMessageMixin
from django.shortcuts import redirect, render
from django.urls import reverse, reverse_lazy

from .forms import CadastroForm, PerfilForm
from .permissoes import obter_tipo, pode


class EntrarView(LoginView):
    template_name = 'login/login.html'
    redirect_authenticated_user = True

    def get_success_url(self):
        # Administrador vai direto para o painel do Django; os demais para o dashboard
        if obter_tipo(self.request.user) == 'administrador':
            return '/admin/'
        return self.get_redirect_url() or reverse('dashboard')

    def form_valid(self, form):
        resposta = super().form_valid(form)
        nome = self.request.user.get_full_name() or self.request.user.username
        messages.success(self.request, f"Login realizado com sucesso! Bem-vindo(a), {nome}.")
        return resposta

    def form_invalid(self, form):
        messages.error(self.request, "Não foi possível entrar: usuário ou senha incorretos.")
        return super().form_invalid(form)


class SairView(LogoutView):
    def post(self, request, *args, **kwargs):
        resposta = super().post(request, *args, **kwargs)
        messages.success(request, "Você saiu da sua conta. Até logo!")
        return resposta


class AlterarSenhaView(SuccessMessageMixin, PasswordChangeView):
    template_name = 'login/alterar_senha.html'
    success_url = reverse_lazy('perfil')
    success_message = "Senha alterada com sucesso!"

    def form_invalid(self, form):
        messages.error(self.request, "Não foi possível alterar a senha. Confira os campos abaixo.")
        return super().form_invalid(form)


@login_required
def dashboard(request):
    if obter_tipo(request.user) == 'administrador':
        return redirect('/admin/')

    secoes = [
        ('perfil', 'Editar Perfil', 'Seus dados cadastrais e senha.', reverse('perfil'), '👤'),
        ('contatos', 'Contatos', 'Mensagens recebidas pelo site.', reverse('painel_contatos'), '✉️'),
        ('servicos', 'Serviços', 'Catálogo de serviços da forja.', reverse('painel_servicos'), '🛠️'),
        ('equipe', 'Equipe', 'Integrantes da forja (Supabase).', reverse('painel_equipe'), '🥷'),
        ('pedidos', 'Meus Pedidos', 'Carrinho e histórico de compras.', reverse('meus_pedidos'), '🗡️'),
        ('relatorios', 'Relatórios', 'Gráficos e indicadores dos serviços.', reverse('painel_relatorios'), '📊'),
    ]
    disponiveis = [
        {'titulo': t, 'descricao': d, 'url': u, 'icone': i}
        for chave, t, d, u, i in secoes if pode(request.user, chave)
    ]
    return render(request, 'login/dashboard.html', {'secoes': disponiveis})


@login_required
def perfil(request):
    form = PerfilForm(request.POST or None, instance=request.user)
    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request, "Perfil atualizado com sucesso!")
        return redirect('perfil')
    if request.method == 'POST':
        messages.error(request, "Não foi possível salvar o perfil. Confira os campos abaixo.")
    return render(request, 'login/perfil.html', {'form': form})


def cadastro(request):
    if request.user.is_authenticated:
        return redirect('dashboard')
    form = CadastroForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        form.save()  # o Perfil (cliente) é criado pelo signal
        messages.success(request, "Conta criada com sucesso! Agora é só entrar.")
        return redirect('login')
    if request.method == 'POST':
        messages.error(request, "Não foi possível criar a conta. Corrija os campos destacados.")
    return render(request, 'login/cadastro.html', {'form': form})
