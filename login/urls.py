from django.contrib.auth import views as auth_views
from django.urls import path, reverse_lazy

from . import views

urlpatterns = [
    path("", views.EntrarView.as_view(), name="login"),
    path("logout/", views.SairView.as_view(), name="logout"),
    path("cadastro/", views.cadastro, name="cadastro"),
    path("dashboard/", views.dashboard, name="dashboard"),
    path("perfil/", views.perfil, name="perfil"),
    path("alterar-senha/", views.AlterarSenhaView.as_view(), name="alterar_senha"),

    # Recuperação de senha (mecanismo nativo do Django)
    path("esqueci-senha/", auth_views.PasswordResetView.as_view(
        template_name="login/recuperar_senha.html",
        email_template_name="login/emails/recuperar_senha.txt",
        subject_template_name="login/emails/recuperar_senha_assunto.txt",
        success_url=reverse_lazy("password_reset_done"),
    ), name="password_reset"),
    path("esqueci-senha/enviado/", auth_views.PasswordResetDoneView.as_view(
        template_name="login/recuperar_senha_enviada.html"), name="password_reset_done"),
    path("redefinir/<uidb64>/<token>/", auth_views.PasswordResetConfirmView.as_view(
        template_name="login/redefinir_senha.html",
        success_url=reverse_lazy("password_reset_complete"),
    ), name="password_reset_confirm"),
    path("redefinir/concluido/", auth_views.PasswordResetCompleteView.as_view(
        template_name="login/redefinir_senha_concluida.html"), name="password_reset_complete"),
]
