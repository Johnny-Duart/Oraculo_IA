from django.db import models


class Treinamento(models.Model):
    # Bug #12 corrigido: campos agora são opcionais (blank=True / null=True).
    # O usuário preenche apenas UM dos três ao treinar (site, texto ou PDF),
    # então todos precisam aceitar vazio. Sem isso, salvar com só um campo
    # preenchido causava erro de integridade no banco.
    site = models.URLField(blank=True, default="")
    conteudo = models.TextField(blank=True, default="")
    documento = models.FileField(upload_to="documentos", blank=True, null=True)

    def __str__(self):
        # __str__ corrigido: o original retornava self.site, que agora pode ser vazio
        if self.site:
            return self.site
        if self.conteudo:
            return self.conteudo[:50]
        if self.documento:
            return str(self.documento.name)
        return f"Treinamento #{self.pk}"


class DataTreinamento(models.Model):
    metadata = models.JSONField(null=True, blank=True)
    texto = models.TextField()


class Pergunta(models.Model):
    data_treinamento = models.ManyToManyField(DataTreinamento)
    pergunta = models.TextField()

    def __str__(self):
        return self.pergunta
