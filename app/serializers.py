from rest_framework import serializers

from .models import Categoria


class CategoriaSerializer(serializers.ModelSerializer):
    class Meta:
        model = Categoria
        fields = '__all__'
        extra_kwargs = {'nome': {'required': True, 'allow_blank': False}}
