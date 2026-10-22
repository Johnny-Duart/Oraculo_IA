import json

from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.core.cache import cache
from django.http import (
    Http404,
    HttpResponse,
    JsonResponse,
    StreamingHttpResponse,
)
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


sched_message_response = None
send_message_response = None

try:
    from .utils import (
        sched_message_response,
        send_message_response,
    )
except Exception:
    pass


@login_required
def treinar_ia(request):
    if request.method == "GET":
        tasks = Task.objects.all()
        return render(request, "treinar_ia.html", {"tasks": tasks})
    elif request.method == "POST":
        site = request.POST.get("site") or ""
        conteudo = request.POST.get("conteudo") or ""
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


@login_required
@csrf_exempt
def stream_response(request):
    id_pergunta = request.POST.get("id_pergunta") or request.GET.get(
        "id_pergunta"
    )

    try:
        pergunta = Pergunta.objects.get(id=id_pergunta)
    except (Pergunta.DoesNotExist, ValueError, TypeError):
        return HttpResponse("Pergunta não encontrada.", status=404)

    def stream_generator():
        if not LANGCHAIN_AVAILABLE:
            yield "Funcionalidade indisponível: dependências LangChain/faiss não estão instaladas.\n"
            return

        if OllamaEmbeddings is None or FAISS is None:
            yield "Funcionalidade indisponível: dependências LangChain/faiss não estão instaladas.\n"
            return

        embeddings = OllamaEmbeddings(model="nomic-embed-text")
        try:
            vectordb = FAISS.load_local(
                "banco_faiss", embeddings, allow_dangerous_deserialization=True
            )
        except Exception:
            yield (
                "Ainda não aprendi nada! Minha memória está completamente vazia no momento. "
                "Por favor, acesse a aba 'Treinar IA' e envie sites, textos ou documentos para que eu possa aprender!"
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

        trechos_contexto = [doc.page_content.strip() for doc in docs_unicos if doc.page_content.strip()]
        contexto_formatado = "\n\n---\n\n".join(trechos_contexto)

        llm_messages = [
            {
                "role": "system",
                "content": (
                    "Você é a Iazete, uma assistente virtual inteligente, prestativa e amigável.\n"
                    "Diretrizes obrigatórias:\n"
                    "1. Responda à pergunta do usuário utilizando exclusivamente as informações presentes na base de conhecimento abaixo.\n"
                    "2. NUNCA cite termos como 'contexto 1', 'segundo o contexto', 'de acordo com o texto fornecido' ou metadados internos. Fale naturalmente com o usuário em português, como uma assistente oficial bem informada.\n"
                    "3. Se a informação solicitada não estiver na base de conhecimento, diga educadamente que ainda não possui essa informação.\n"
                    "4. Não invente ou presuma informações além do que consta na base.\n\n"
                    f"Base de Conhecimento:\n{contexto_formatado}"
                ),
            },
            {
                "role": "user",
                "content": pergunta.pergunta,
            },
        ]

        llm = ChatOllama(model="llama3")
        for chunk in llm.stream(llm_messages):
            if hasattr(chunk, "content"):
                yield chunk.content
            else:
                yield str(chunk)

    return StreamingHttpResponse(
        stream_generator(), content_type="text/plain; charset=utf-8"
    )


@login_required
def ver_fontes(request, id):
    try:
        pergunta = Pergunta.objects.get(id=id)
    except Pergunta.DoesNotExist:
        raise Http404("Pergunta não encontrada.")

    return render(request, "ver_fontes.html", {"pergunta": pergunta})


@csrf_exempt
def webhook_whatsapp(request):
    if request.method == "GET":
        return HttpResponse("Webhook funcionando!")
    if request.method != "POST":
        return HttpResponse("Apenas POST")

    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return HttpResponse("JSON inválido", status=400)

    if data.get("apikey") != settings.EVOLUTION_WEBHOOK_APIKEY:
        return HttpResponse("Não autorizado", status=401)

    evento = data.get("event")

    if evento != "messages.upsert":
        return JsonResponse({"status": "ignorado"})

    key_data = data.get("data", {}).get("key", {})

    from_me = key_data.get("fromMe", False)

    if from_me:
        return HttpResponse("Ignorado: Mensagem do próprio bot")

    remote_jid = key_data.get("remoteJid", "")

    if not remote_jid or remote_jid == "status@broadcast":
        return HttpResponse("JID inválido ou broadcast ignorado", status=400)

    actual_sender = data.get("data", {}).get("participant")
    if actual_sender and "@s.whatsapp.net" in actual_sender:
        remote_jid = actual_sender

    phone = remote_jid.split("@")[0]
    message_text = ""
    msg_data = data.get("data", {}).get("message", {})
    message_text = ""

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

    buffer = cache.get(f"wa_buffer_{phone}", [])
    buffer.append(message_text)
    cache.set(f"wa_buffer_{phone}", buffer, timeout=60)

    if sched_message_response:
        sched_message_response(remote_jid, phone)
    else:
        send_message_response(remote_jid, phone)
    return HttpResponse("Sucesso")
