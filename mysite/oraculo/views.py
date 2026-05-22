from pathlib import Path

from django.conf import settings
from django.http import HttpResponse, JsonResponse, StreamingHttpResponse
from django.shortcuts import redirect, render
from django.views.decorators.csrf import csrf_exempt
from django_q.models import Task
from langchain_community.chat_models import ChatOllama
from langchain_community.embeddings import OllamaEmbeddings
from langchain_community.vectorstores import FAISS

from .models import DataTreinamento, Pergunta, Treinamento


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


@csrf_exempt
def chat(request):
    if request.method == "GET":
        return render(request, "chat.html")
    elif request.method == "POST":
        pergunta_user = request.POST.get("pergunta")
        pergunta = Pergunta(pergunta=pergunta_user)
        pergunta.save()
        return JsonResponse({"id": pergunta.id})


@csrf_exempt
def stream_response(request):
    id_pergunta = request.POST.get("id_pergunta") or request.GET.get(
        "id_pergunta"
    )
    pergunta = Pergunta.objects.get(id=id_pergunta)

    def stream_generator():
        embeddings = OllamaEmbeddings(model="nomic-embed-text")
        vectordb = FAISS.load_local(
            "banco_faiss", embeddings, allow_dangerous_deserialization=True
        )

        docs = vectordb.max_marginal_relevance_search(
            pergunta.pergunta, k=5, fetch_k=20
        )
        docs_unicos = []
        vistos = set()

        for doc in docs:
            if doc.page_content not in vistos:
                vistos.add(doc.page_content)
                docs_unicos.append(doc)

        for doc in docs_unicos:
            dt = DataTreinamento(
                metadata=doc.metadata,
                texto=doc.page_content,
            )

            dt.save()
            pergunta.data_treinamento.add(dt)
        contexto = ""

        for i, doc in enumerate(docs_unicos, start=1):
            contexto += f"\n[CONTEXTO {i}]\n{doc.page_content}\n"
        messages = [
            {
                "role": "system",
                "content": f"Voce é um assistente virtual e deve responder com precisão as perguntas sobre o pdf, sem inventar nada. Lembre-se sempre de responder em portugues \n\n{contexto}",
            },
            {
                "role": "user",
                "content": f"{pergunta.pergunta}",
            },
        ]
        llm = ChatOllama(model="llama3")

        for chunk in llm.stream(messages):
            if hasattr(chunk, "content"):
                yield chunk.content
            else:
                yield str(chunk)

    return StreamingHttpResponse(
        stream_generator(), content_type="text/plain; charset=utf-8"
    )


def ver_fontes(request, id):
    pergunta = Pergunta.objects.get(id=id)
    for i in pergunta.data_treinamento.all():
        print(i.metadata)
        print(i.texto)
        print("---")
    print(pergunta.pergunta)
    return render(request, "ver_fontes.html", {"pergunta": pergunta})
