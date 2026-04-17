from django.shortcuts import redirect, render
from django_q.models import Task

from .models import Treinamento


def treinar_ia(request):
    if request.method == "GET":
        tasks = Task.objects.all()
        return render(request, "treinar_ia.html", {"tasks": tasks})
    elif request.method == "POST":
        site = request.POST.get("site")
        conteudo = request.POST.get("conteudo")
        documento = request.FILES.get("documento")

        treinamento = Treinamento(
            site=site, conteudo=conteudo, documento=documento
        )
        treinamento.save()
        return redirect("treinar_ia")


def chat(request):
    if request.method == "GET":
        return render(request, "chat.html")
    elif request.method == "POST":
        ...
