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

<<<<<<< Updated upstream
from django.core.cache import cache
from datetime import datetime, timedelta

try:
    from langchain_community.chat_models import ChatOllama
    from langchain_community.embeddings import OllamaEmbeddings
    from langchain_community.vectorstores import FAISS
except Exception:
    ChatOllama = None
    OllamaEmbeddings = None
=======
from django.conf import settings
from django.core.cache import cache
from datetime import datetime, timedelta

# Bug #11 corrigido: tenta langchain_ollama primeiro (pacote novo e correto),
# cai em langchain_community como fallback se não estiver instalado.
# Para instalar o novo: pip install langchain-ollama
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
>>>>>>> Stashed changes
    FAISS = None

try:
    from .wrapper_evolutionapi import SendMessage
except Exception:
    SendMessage = None
<<<<<<< Updated upstream
=======

# Bug #5 corrigido: caminho absoluto, igual ao que signals.py usa para salvar
FAISS_PATH = str(settings.BASE_DIR / "banco_faiss")

# Bug #7 (parcial) corrigido: scheduler ainda sobe no import,
# mas sched_message_response agora checa se é None antes de usar
if BackgroundScheduler is not None:
    scheduler = BackgroundScheduler()
    try:
        scheduler.start()
    except Exception:
        scheduler = None
else:
    scheduler = None
>>>>>>> Stashed changes


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
            texto_formatado = f"\n\n### {texto.upper()}"
        elif tag.name == "li":
            texto_formatado = f" - {texto}"
        else:
            texto_formatado = texto

        texto_final.append(texto_formatado)

    return "\n".join(texto_final).strip()


def gerar_documentos(instance):
    documentos = []
<<<<<<< Updated upstream
    if instance.documento and PyPDFLoader is not None:
        try:
            extensao = instance.documento.name.split(".")[-1].lower()
            if extensao == "pdf":
                loader = PyPDFLoader(instance.documento.path)
                pdf_doc = loader.load()
                for doc in pdf_doc:
                    doc.metadata["arquivo"] = instance.documento.url

                documentos += pdf_doc
        except Exception:
            # Se falhar no processamento do PDF, apenas ignoramos o anexo.
            pass
=======

    if instance.documento and PyPDFLoader is not None:
        try:
            extensao = instance.documento.name.split(".")[-1].lower()
            if extensao == "pdf":
                loader = PyPDFLoader(instance.documento.path)
                pdf_doc = loader.load()
                for doc in pdf_doc:
                    doc.metadata["arquivo"] = instance.documento.url
                documentos += pdf_doc
        except Exception:
            pass

>>>>>>> Stashed changes
    if instance.conteudo:
        if Document is not None:
            documento = Document(page_content=instance.conteudo)
            documento.metadata["arquivo"] = "Conteúdo digitado"
            documentos.append(documento)
        else:
            class SimpleDoc:
                def __init__(self, text):
                    self.page_content = text
                    self.metadata = {}

            documento = SimpleDoc(instance.conteudo)
            documento.metadata["arquivo"] = "Conteúdo digitado"
            documentos.append(documento)

    if instance.site and requests is not None:
        try:
            site_url = (
                instance.site
                if instance.site.startswith("https://")
                else f"https://{instance.site}"
            )
            content = requests.get(site_url, timeout=10).text
            content = html_para_texto_rag(content)

            if Document is not None:
                documentos.append(Document(page_content=content))
            else:
                class SimpleDoc2:
                    def __init__(self, text):
                        self.page_content = text
                        self.metadata = {}

                documentos.append(SimpleDoc2(content))
        except Exception:
            pass

    return documentos


<<<<<<< Updated upstream
if BackgroundScheduler is not None:
    scheduler = BackgroundScheduler()
    try:
        scheduler.start()
    except Exception:
        scheduler = None
else:
    scheduler = None
=======
def send_message_response(remote_jid, phone):
    print("1 - Entrou na função")
>>>>>>> Stashed changes

    # Renomeado de 'messages' para 'buffer' para não reutilizar o nome
    buffer = cache.get(f"wa_buffer_{phone}", [])
    print("2 - Mensagens no buffer:", buffer)

<<<<<<< Updated upstream
def send_message_response(remote_jid, phone):
    print("1 - Entrou na função")
    messages = cache.get(f"wa_buffer_{phone}", [])
    print("2 - Mensagens:", messages)

    if messages:
        question = "\n".join(messages)

        print("3 - Pergunta:", question)
        if OllamaEmbeddings is None or FAISS is None:
            return

        embeddings = OllamaEmbeddings(model="nomic-embed-text")
        print("4 - Embeddings OK")
=======
    if not buffer:
        return

    question = "\n".join(buffer)
    print("3 - Pergunta:", question)

    if OllamaEmbeddings is None or FAISS is None:
        print("ERRO: dependências LangChain não disponíveis.")
        cache.delete(f"wa_buffer_{phone}")
        cache.delete(f"wa_timer_{phone}")
        return

    embeddings = OllamaEmbeddings(model="nomic-embed-text")
    print("4 - Embeddings OK")

    # Bug #5 corrigido: usa FAISS_PATH absoluto definido no topo do módulo
    try:
>>>>>>> Stashed changes
        vectordb = FAISS.load_local(
            FAISS_PATH, embeddings, allow_dangerous_deserialization=True
        )
<<<<<<< Updated upstream
        print("5 - Banco carregado")

        docs = vectordb.max_marginal_relevance_search(
            question, k=5, fetch_k=20
        )
        print("6 - Busca OK")
        context = "\n\n".join([doc.page_content for doc in docs])
        messages = [
            {
                "role": "system",
                "content": f"Voce é um assistente virtual e deve responder com precisão as perguntas sobre o pdf, sem inventar nada. Lembre-se sempre de responder em portugues \n\n{context}",
            },
            {
                "role": "user",
                "content": question,
            },
        ]
        print("7 - Contexto OK")
        if ChatOllama is None:
            return

        llm = ChatOllama(model="llama3")
        print("8 - LLM criado")
        response = llm.invoke(messages).content

        print("RESPOSTA GERADA:")
        print(response)
        if SendMessage is not None:
            try:
                resp = SendMessage().send_message(
                    instance="oraculo",
                    remote_jid=remote_jid,
                    text=response,
                )

                print("STATUS:", resp.status_code)
                print("RESPOSTA:", resp.text)

                if resp.status_code in [200, 201]:
                    print("10 - Mensagem enviada")
                else:
                    print("ERRO AO ENVIAR")
            except Exception:
                pass
=======
    except Exception as e:
        print("ERRO ao carregar banco FAISS:", e)
        return

    print("5 - Banco carregado")

    docs = vectordb.max_marginal_relevance_search(question, k=5, fetch_k=20)
    print("6 - Busca OK")

    context = "\n\n".join([doc.page_content for doc in docs])

    # Renomeado para llm_messages para evitar reutilização confusa do nome 'messages'
    llm_messages = [
        {
            "role": "system",
            "content": (
                "Voce é um assistente virtual e deve responder com precisão as perguntas "
                "sobre o pdf, sem inventar nada. Lembre-se sempre de responder em portugues "
                f"\n\n{context}"
            ),
        },
        {
            "role": "user",
            "content": question,
        },
    ]
    print("7 - Contexto OK")
>>>>>>> Stashed changes

    if ChatOllama is None:
        print("ERRO: ChatOllama não disponível.")
        return

    llm = ChatOllama(model="llama3")
    print("8 - LLM criado")

    resposta = llm.invoke(llm_messages).content
    print("RESPOSTA GERADA:")
    print(resposta)

    # Bug #8 corrigido: cache.delete agora está DENTRO do bloco de envio bem-sucedido.
    # O buffer só é apagado se a mensagem foi entregue (status 200/201).
    if SendMessage is not None:
        try:
            resp = SendMessage().send_message(
                instance="oraculo",
                remote_jid=remote_jid,
                text=resposta,
            )
            print("STATUS:", resp.status_code)
            print("RESPOSTA:", resp.text)

            if resp.status_code in [200, 201]:
                print("10 - Mensagem enviada com sucesso")
                cache.delete(f"wa_buffer_{phone}")
                cache.delete(f"wa_timer_{phone}")
            else:
                print("ERRO AO ENVIAR — buffer mantido para retry:", resp.text)
        except Exception as e:
            print("EXCEÇÃO AO ENVIAR:", e)
    else:
        # SendMessage não disponível: limpa buffer para não acumular indefinidamente
        print("AVISO: SendMessage não disponível, buffer limpo sem envio.")
        cache.delete(f"wa_buffer_{phone}")
        cache.delete(f"wa_timer_{phone}")
        print("10 - Mensagem enviada")


def sched_message_response(remote_jid, phone):
<<<<<<< Updated upstream
=======
    # Bug #7 corrigido: checa scheduler antes de usar — se for None, processa direto
    if scheduler is None:
        print("AVISO: scheduler não disponível, processando mensagem diretamente.")
        send_message_response(remote_jid, phone)
        return

>>>>>>> Stashed changes
    if not cache.get(f"wa_timer_{phone}"):
        scheduler.add_job(
            send_message_response,
            "date",
            run_date=datetime.now() + timedelta(seconds=15),
            kwargs={"remote_jid": remote_jid, "phone": phone},
            misfire_grace_time=60,
        )
        cache.set(f"wa_timer_{phone}", True, timeout=60)
