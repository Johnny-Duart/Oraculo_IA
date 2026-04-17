import os
import warnings

from django.conf import settings
from django.db.models.signals import post_save
from django.dispatch import receiver
from django_q.tasks import async_task
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.embeddings import OllamaEmbeddings
from langchain_community.vectorstores import FAISS

from .models import Treinamento
from .utils import gerar_documentos

warnings.filterwarnings("ignore", category=DeprecationWarning)


@receiver(post_save, sender=Treinamento)
def signals_treinamento_ia(sender, instance, created, **kwargs):
    if created:
        async_task(task_treinar_ia, instance.id)


def task_treinar_ia(instance_id):
    treinamento = Treinamento.objects.get(id=instance_id)
    documentos = gerar_documentos(treinamento)

    if not documentos:
        return

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=500, chunk_overlap=100
    )
    chunks = splitter.split_documents(documentos)

    embeddings = OllamaEmbeddings(model="nomic-embed-text")

    db_path = settings.BASE_DIR / "banco_faiss"
    if os.path.exists(db_path):
        vectordb = FAISS.load_local(
            db_path, embeddings, allow_dangerous_deserialization=True
        )
        vectordb.add_documents(chunks)
    else:
        vectordb = FAISS.from_documents(chunks, embeddings)
    vectordb.save_local(db_path)
