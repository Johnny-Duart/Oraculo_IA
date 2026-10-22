import os
import warnings

from django.conf import settings
from django.db.models.signals import post_save
from django.dispatch import receiver
from django_q.tasks import async_task

try:
    from langchain_text_splitters import RecursiveCharacterTextSplitter
except ImportError:
    try:
        from langchain.text_splitter import RecursiveCharacterTextSplitter
    except ImportError:
        RecursiveCharacterTextSplitter = None

try:
    from langchain_ollama import OllamaEmbeddings
except ImportError as e:
    print(
        f"AVISO: langchain_ollama indisponível ({e}), tentando langchain_community..."
    )
    try:
        from langchain_community.embeddings import OllamaEmbeddings
    except Exception as e2:
        print(f"ERRO: OllamaEmbeddings indisponível: {e2}")
        OllamaEmbeddings = None

try:
    from langchain_community.vectorstores import FAISS
except Exception as e:
    print(f"ERRO: FAISS indisponível: {e}")
    FAISS = None

from .models import Treinamento
from .utils import gerar_documentos

warnings.filterwarnings("ignore", category=DeprecationWarning)


@receiver(post_save, sender=Treinamento)
def signals_treinamento_ia(sender, instance, created, **kwargs):
    if created:
        async_task(task_treinar_ia, instance.id)


def task_treinar_ia(instance_id):
    if RecursiveCharacterTextSplitter is None:
        print("ERRO: RecursiveCharacterTextSplitter indisponível.")
        return
    if OllamaEmbeddings is None:
        print(
            "ERRO: OllamaEmbeddings indisponível (verifique se langchain-ollama está instalado)."
        )
        return
    if FAISS is None:
        print("ERRO: FAISS indisponível.")
        return

    treinamento = Treinamento.objects.get(id=instance_id)
    documentos = gerar_documentos(treinamento)

    if not documentos:
        print(f"[RAG] Treinamento #{instance_id}: nenhum documento gerado ou falha na extração.")
        return

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=500, chunk_overlap=100
    )
    chunks = splitter.split_documents(documentos)
    print(f"[RAG] Gerando embeddings para {len(chunks)} chunks do Treinamento #{instance_id}...")

    embeddings = OllamaEmbeddings(model="nomic-embed-text")

    db_path = settings.BASE_DIR / "banco_faiss"
    index_file = os.path.join(db_path, "index.faiss")
    pkl_file = os.path.join(db_path, "index.pkl")

    vectordb = None
    if os.path.exists(index_file) and os.path.exists(pkl_file):
        try:
            vectordb = FAISS.load_local(
                str(db_path), embeddings, allow_dangerous_deserialization=True
            )
            vectordb.add_documents(chunks)
        except Exception as e:
            print(f"[RAG] Aviso ao carregar índice existente ({e}). Criando nova base do zero...")
            vectordb = None

    if vectordb is None:
        vectordb = FAISS.from_documents(chunks, embeddings)

    vectordb.save_local(str(db_path))
    print(f"[RAG] Treinamento #{instance_id} indexado e salvo com sucesso no banco_faiss!")
