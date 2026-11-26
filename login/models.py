from django.contrib.auth.models import User
from django.db import models


class Perfil(models.Model):
    TIPOS_USUARIO = [
        ('administrador', 'Administrador'),
        ('funcionario', 'Funcionário'),
        ('cliente', 'Cliente'),
    ]

    usuario = models.OneToOneField(User, on_delete=models.CASCADE, related_name='perfil')
    tipo_usuario = models.CharField(max_length=20, choices=TIPOS_USUARIO, default='cliente')

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        # Administrador precisa conseguir entrar no painel /admin/
        if self.tipo_usuario == 'administrador' and not (self.usuario.is_staff and self.usuario.is_superuser):
            self.usuario.is_staff = True
            self.usuario.is_superuser = True
            self.usuario.save(update_fields=['is_staff', 'is_superuser'])

    def __str__(self):
        return f'{self.usuario.username} - {self.get_tipo_usuario_display()}'
