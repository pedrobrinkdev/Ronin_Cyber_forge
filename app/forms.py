from django import forms

from .models import Contato, Servico


class FormServico(forms.ModelForm):
    class Meta:
        model = Servico
        fields = ("nome", "descricao", "preco", "categoria", "imagem", "ativo")
        widgets = {"descricao": forms.Textarea(attrs={"rows": 4})}

    def clean_preco(self):
        preco = self.cleaned_data["preco"]
        if preco < 0:
            raise forms.ValidationError("O preço não pode ser negativo.")
        return preco


class FormContato(forms.ModelForm):
    class Meta:
        model = Contato
        fields = ("nome", "email", "telefone", "mensagem")
        widgets = {"mensagem": forms.Textarea(attrs={"rows": 6})}
