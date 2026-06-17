from pathlib import Path

from django.core.cache import cache
from django.http import HttpResponse, JsonResponse, StreamingHttpResponse
from django.shortcuts import redirect, render
from django.views.decorators.csrf import csrf_exempt
from django_q.models import Task

from .models import DataTreinamento, Pergunta, Treinamento
from .utils import send_message_response

try:
    from langchain_community.chat_models import ChatOllama
    from langchain_community.embeddings import OllamaEmbeddings
    from langchain_community.vectorstores import FAISS

    LANGCHAIN_AVAILABLE = True
except Exception:
    ChatOllama = None
    OllamaEmbeddings = None
    FAISS = None
    LANGCHAIN_AVAILABLE = False
import json

sched_message_response = None
send_message_response = None

try:
    from .utils import (
        sched_message_response,
        send_message_response,
    )
except Exception:
    pass


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
        if not LANGCHAIN_AVAILABLE:
            yield "Funcionalidade indisponível: dependências LangChain/faiss não estão instaladas.\n"
            return

        # Verifica se as dependências de embeddings/FAISS estão disponíveis
        if OllamaEmbeddings is None or FAISS is None:
            yield "Funcionalidade indisponível: dependências LangChain/faiss não estão instaladas.\n"
            return

        embeddings = OllamaEmbeddings(model="nomic-embed-text")
        try:
            vectordb = FAISS.load_local(
                "banco_faiss", embeddings, allow_dangerous_deserialization=True
            )
        except Exception:
            # Se o índice local não existir ou houver erro no FAISS, avisamos o usuário
            yield (
                "Base de busca (FAISS) não encontrada ou erro ao carregar. Execute o treinamento em 'Treinar IA' antes de perguntar.\n"
            )
            return

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


@csrf_exempt
def webhook_whatsapp(request):
    print("Webhook recebeu uma requisição:", request.method)
    print(request.method)
    print(request.path)
    print(request.method)
    print(request.body)
    if request.method == "GET":
        return HttpResponse("Webhook funcionando!")
    if request.method != "POST":
        return HttpResponse("Apenas POST")

    try:
        data = json.loads(request.body)
    except Exception:
        return HttpResponse("JSON inválido", status=400)

    key_data = data.get("data", {}).get("key", {})

    from_me = key_data.get("fromMe", False)

    if from_me:
        print("Mensagem enviada pelo próprio bot (fromMe=True). Ignorando.")
        return HttpResponse("Ignorado: Mensagem do próprio bot")

    remote_jid = key_data.get("remoteJid", "")

    if not remote_jid or remote_jid == "status@broadcast":
        return HttpResponse("JID inválido ou broadcast ignorado", status=400)

    actual_sender = data.get("data", {}).get("participant")
    if actual_sender and "@s.whatsapp.net" in actual_sender:
        remote_jid = actual_sender

    phone = remote_jid.split("@")[0]

    print("REMOTE JID ORIGINAL:", remote_jid)
    print("PHONE LIMPO:", phone)
    message_text = ""
    print(json.dumps(data, indent=2))
    msg_data = data.get("data", {}).get("message", {})

    if "conversation" in msg_data:
        message_text = msg_data.get("conversation")
    elif "extendedTextMessage" in msg_data:

        message_text = msg_data.get("extendedTextMessage", {}).get("text")
    elif "imageMessage" in msg_data:

        message_text = msg_data.get("imageMessage", {}).get("caption")

    if not message_text:
        print(
            "Mensagem sem texto ou tipo não suportado (ex: áudio/figurinha sem transcrição)."
        )
        return HttpResponse("Mensagem sem texto ignorada")
    print(f"MENSAGEM RECEBIDA DE {phone}: {message_text}")

    buffer = cache.get(f"wa_buffer_{phone}", [])
    buffer.append(message_text)

    cache.set(f"wa_buffer_{phone}", buffer, timeout=60)

    if sched_message_response:
        sched_message_response(remote_jid, phone)
    else:
        send_message_response(remote_jid, phone)
    return HttpResponse("Sucesso")
