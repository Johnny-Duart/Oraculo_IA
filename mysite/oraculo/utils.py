import re
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
Você é a Iazete, uma assistente virtual inteligente, prestativa e cordial.
Responda diretamente à pergunta utilizando exclusivamente as informações da base de conhecimento abaixo.
Nunca use termos ou expressões como "de acordo com o contexto", "no contexto 1", "segundo as informações fornecidas". Responda de forma natural, direta e profissional em português.
Se a informação necessária não estiver na base, informe educadamente que não possui essa informação cadastrada.

Base de conhecimento:
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

    # 1. Remover scripts, estilos, navegações, rodapés e formulários que poluem o RAG
    for tag in soup(["script", "style", "nav", "footer", "header", "aside", "noscript", "svg", "form", "button"]):
        tag.decompose()

    # 2. Remover elementos de navegação e edição específicos (ex.: Wikipedia)
    for noise in soup.find_all(class_=re.compile(r"mw-editsection|reference|catlinks|mw-jump-link|navbox|sidebar|portal")):
        noise.decompose()

    # 3. Focar no container principal do conteúdo se existir
    content_root = (
        soup.find("div", id="mw-content-text")
        or soup.find("main")
        or soup.find("article")
        or soup.find("div", id="content")
        or soup.find("div", class_=re.compile(r"content|post|article|body", re.I))
        or soup.body
        or soup
    )

    texto_final = []
    for tag in content_root.find_all(["h1", "h2", "h3", "h4", "p", "li"]):
        texto = tag.get_text(separator=" ", strip=True)
        if not texto:
            continue

        # Limpar referências tipo [1], [2], [editar], etc.
        texto = re.sub(r"\[\d+\]", "", texto)
        texto = re.sub(r"\[editar.*?\]", "", texto)
        texto = re.sub(r"\s+([.,;:!?])", r"\1", texto)
        texto = re.sub(r"\s+", " ", texto).strip()

        if not texto or len(texto) < 3:
            continue

        if tag.name in ["h1", "h2", "h3", "h4"]:
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
            print("[RAG] Erro ao carregar PDF:", e)

    if instance.conteudo and instance.conteudo.strip():
        documentos.append(_make_doc(instance.conteudo.strip(), "Conteúdo digitado"))

    if instance.site and requests is not None:
        raw_site = instance.site.strip()
        if raw_site:
            url = raw_site if (raw_site.startswith("http://") or raw_site.startswith("https://")) else f"https://{raw_site}"
            try:
                headers = {
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
                    "Accept-Language": "pt-BR,pt;q=0.9,en-US;q=0.8,en;q=0.7",
                    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                }
                resp = requests.get(url, headers=headers, timeout=15)
                resp.raise_for_status()

                # Garantir encoding correto (UTF-8) para caracteres em português
                if resp.encoding is None or resp.encoding.lower() == "iso-8859-1":
                    resp.encoding = resp.apparent_encoding or "utf-8"

                content = html_para_texto_rag(resp.text)
                if content:
                    documentos.append(_make_doc(content, url))
                    print(f"[RAG] Sucesso ao extrair {len(content)} caracteres do site: {url}")
                else:
                    print(f"[RAG] Aviso: Nenhum texto aproveitável extraído do site: {url}")
            except Exception as e:
                print(f"[RAG] Erro ao extrair conteúdo do site {url}: {e}")

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
