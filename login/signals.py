from django.contrib.auth.models import User
from django.db.models.signals import post_save
from django.dispatch import receiver

from .models import Perfil


@receiver(post_save, sender=User)
def criar_perfil(sender, instance, created, **kwargs):
    """Todo usuário novo (cadastro, createsuperuser ou admin) ganha um Perfil."""
    if created:
        tipo = 'administrador' if instance.is_superuser else 'cliente'
        Perfil.objects.get_or_create(usuario=instance, defaults={'tipo_usuario': tipo})
