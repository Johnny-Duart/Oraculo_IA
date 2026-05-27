import requests
from bs4 import BeautifulSoup
from langchain.docstore.document import Document
from langchain_community.document_loaders import PyPDFLoader
from apscheduler.schedulers.background import BackgroundScheduler
from django.core.cache import cache
from datetime import datetime, timedelta
from langchain_community.chat_models import ChatOllama
from langchain_community.embeddings import OllamaEmbeddings
from langchain_community.vectorstores import FAISS
from .wrapper_evolutionapi import SendMessage


def html_para_texto_rag(html_str: str) -> str:

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
    if instance.documento:
        extensao = instance.documento.name.split(".")[-1].lower()
        if extensao == "pdf":
            loader = PyPDFLoader(instance.documento.path)
            pdf_doc = loader.load()
            for doc in pdf_doc:
                doc.metadata["arquivo"] = instance.documento.url

            documentos += pdf_doc
    if instance.conteudo:
        documento = Document(page_content=instance.conteudo)
        documento.metadata["arquivo"] = "Conteúdo digitado"
        documentos.append(documento)

    if instance.site:
        site_url = (
            instance.site
            if instance.site.startswith("https://")
            else f"https://{instance.site}"
        )
        content = requests.get(site_url, timeout=10).text
        content = html_para_texto_rag(content)

        documentos.append(Document(page_content=content))

    return documentos


scheduler = BackgroundScheduler()
scheduler.start()


def send_message_response(phone):

    messages = cache.get(f"wa_buffer_{phone}", [])
    if messages:
        question = "\n".join(messages)

        print(question)

        embeddings = OllamaEmbeddings(model="nomic-embed-text")

        vectordb = FAISS.load_local(
            "banco_faiss", embeddings, allow_dangerous_deserialization=True
        )

        docs = vectordb.max_marginal_relevance_search(
            question, k=5, fetch_k=20
        )
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

        llm = ChatOllama(model="llama3")

        response = llm.invoke(messages).content

        SendMessage().send_message(
            instance="oraculo",
            number=phone,
            text=response,
        )

        cache.delete(f"wa_buffer_{phone}")
        cache.delete(f"wa_timer_{phone}")


def sched_message_response(phone):
    if not cache.get(f"wa_timer_{phone}"):
        scheduler.add_job(
            send_message_response,
            "date",
            run_date=datetime.now() + timedelta(seconds=15),
            kwargs={"phone": phone},
            misfire_grace_time=60,
        )
        cache.set(f"wa_timer_{phone}", True, timeout=60)
