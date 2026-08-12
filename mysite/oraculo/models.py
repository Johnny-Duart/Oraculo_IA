from django.db import models


gclass Treinamento(models.Model):
    site = models.URLField(blank=True, default="")
    conteudo = models.TextField(blank=True, default="")
    documento = models.FileField(upload_to="documentos", blank=True, null=True)

    def __str__(self):
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
