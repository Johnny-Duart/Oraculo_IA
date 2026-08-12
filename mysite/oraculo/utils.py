from datetime import datetime, timedelta

from django.conf import settings
from django.core.cache import cache

try:
    import requests
except Exception:
    requests = None

try:
    from bs4 import BeautifulSoup
except Exception:
    BeautifulSoup = None

try:
    from langchain.docstore.document import Document
except Exception:
    Document = None

try:
    from langchain_community.document_loaders import PyPDFLoader
except Exception:
    PyPDFLoader = None

try:
    from apscheduler.schedulers.background import BackgroundScheduler
except Exception:
    BackgroundScheduler = None

try:
    from langchain_ollama import ChatOllama, OllamaEmbeddings
except ImportError:
    try:
        from langchain_community.chat_models import ChatOllama
        from langchain_community.embeddings import OllamaEmbeddings
    except Exception:
        ChatOllama = None
        OllamaEmbeddings = None

try:
    from langchain_community.vectorstores import FAISS
except Exception:
    FAISS = None

try:
    from .wrapper_evolutionapi import SendMessage
except Exception:
    SendMessage = None

FAISS_PATH = str(settings.BASE_DIR / "banco_faiss")

if BackgroundScheduler is not None:
    scheduler = BackgroundScheduler()
    try:
        scheduler.start()
    except Exception:
        scheduler = None
else:
    scheduler = None


SYSTEM_PROMPT = """
Você é um assistente virtual.
Responda apenas utilizando as informações presentes no contexto.
Nunca invente respostas.
Sempre responda em português.
Contexto:
{context}
"""

_llm = None
_vectordb = None
_embeddings = None


def get_embeddings():
    global _embeddings

    if _embeddings is None:
        _embeddings = OllamaEmbeddings(model="nomic-embed-text")

    return _embeddings


def get_llm():
    global _llm

    if _llm is None:
        _llm = ChatOllama(model="llama3")

    return _llm


def get_vectordb():
    global _vectordb

    if _vectordb is None:
        embeddings = get_embeddings()
        _vectordb = FAISS.load_local(
            FAISS_PATH,
            embeddings,
            allow_dangerous_deserialization=True,
        )

    return _vectordb


def html_para_texto_rag(html_str: str) -> str:
    if BeautifulSoup is None:
        return html_str
    soup = BeautifulSoup(html_str, "html.parser")
    texto_final = []
    for tag in soup.find_all(["h1", "h2", "h3", "p", "li"]):
        texto = tag.get_text(strip=True)
        if not texto:
            continue
        if tag.name in ["h1", "h2", "h3"]:
            texto_final.append(f"\n\n### {texto.upper()}")
        elif tag.name == "li":
            texto_final.append(f" - {texto}")
        else:
            texto_final.append(texto)
    return "\n".join(texto_final).strip()


def _make_doc(text, arquivo):
    if Document is not None:
        doc = Document(page_content=text)
        doc.metadata["arquivo"] = arquivo
        return doc

    class SimpleDoc:
        def __init__(self, t):
            self.page_content = t
            self.metadata = {}

    doc = SimpleDoc(text)
    doc.metadata["arquivo"] = arquivo
    return doc


def gerar_documentos(instance):
    documentos = []

    if instance.documento and PyPDFLoader is not None:
        try:
            if instance.documento.name.split(".")[-1].lower() == "pdf":
                loader = PyPDFLoader(instance.documento.path)
                for doc in loader.load():
                    doc.metadata["arquivo"] = instance.documento.url
                    documentos.append(doc)
        except Exception as e:
            print("Erro ao carregar PDF:", e)

    if instance.conteudo:
        documentos.append(_make_doc(instance.conteudo, "Conteúdo digitado"))

    if instance.site and requests is not None:
        try:
            url = (
                instance.site
                if instance.site.startswith("https://")
                else f"https://{instance.site}"
            )
            resp = requests.get(url, timeout=10)
            resp.raise_for_status()
            content = html_para_texto_rag(resp.text)
            documentos.append(_make_doc(content, instance.site))
        except Exception:
            pass

    return documentos


def send_message_response(remote_jid, phone):
    buffer = cache.get(f"wa_buffer_{phone}", [])
    if not buffer:
        return

    if OllamaEmbeddings is None or FAISS is None or ChatOllama is None:
        print("ERRO: dependências LangChain não disponíveis.")
        cache.delete(f"wa_buffer_{phone}")
        cache.delete(f"wa_timer_{phone}")
        return

    question = "\n".join(buffer)
    print("3 - Pergunta:", question)

    try:
        vectordb = get_vectordb()
    except Exception as e:
        print("ERRO ao carregar FAISS:", e)
        return

    try:
        docs = vectordb.max_marginal_relevance_search(
            question,
            k=5,
            fetch_k=20,
        )
    except Exception as e:
        print(e)
        return

    context = "\n\n".join([doc.page_content for doc in docs])
    llm_messages = [
        {"role": "system", "content": SYSTEM_PROMPT.format(context=context)},
        {"role": "user", "content": question},
    ]

    llm = get_llm()
    resposta = llm.invoke(llm_messages).content
    print("RESPOSTA GERADA:", resposta)

    if SendMessage is None:
        print("AVISO: SendMessage não disponível.")
        cache.delete(f"wa_buffer_{phone}")
        cache.delete(f"wa_timer_{phone}")
        return

    try:
        resp = SendMessage().send_message(
            instance="oraculo", remote_jid=remote_jid, text=resposta
        )
        print("STATUS:", resp.status_code)
        print("RESPOSTA:", resp.text)
        if resp.status_code in [200, 201]:
            cache.delete(f"wa_buffer_{phone}")
            cache.delete(f"wa_timer_{phone}")
        else:
            print("ERRO AO ENVIAR:", resp.text)
    except Exception as e:
        print("EXCEÇÃO AO ENVIAR:", e)


def sched_message_response(remote_jid, phone):
    if scheduler is None:
        send_message_response(remote_jid, phone)
        return

    if not cache.get(f"wa_timer_{phone}"):
        scheduler.add_job(
            send_message_response,
            "date",
            run_date=datetime.now() + timedelta(seconds=15),
            kwargs={"remote_jid": remote_jid, "phone": phone},
            misfire_grace_time=60,
        )
        cache.set(f"wa_timer_{phone}", True, timeout=60)
