import os
import warnings
from langchain_community.document_loaders import PyPDFLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_openai import OpenAIEmbeddings, ChatOpenAI
from langchain_community.vectorstores import FAISS
from langchain.chains import RetrievalQA
warnings.filterwarnings("ignore", category=DeprecationWarning)

os.environ["OPENAI_API_KEY"] = "s-7IB7OCMW1HXW9DG3fnsV3dZX0EpHCB45v-Wb3Ej40vbHErPaDiP8NtryL4Tu1eEgog__TvoPi3T3BlbkFJ8pYk-rz1TcOP5M_ayFXEx3iny0QdoZLkDetUttA_OLajh-22q_CYXLKAZYlXL5_a6eG0h0u78A"

caminho_pdf = r"C:\Users\jonat\Desktop\IA Pythonando\Perceptron.pdf"

loader = PyPDFLoader(caminho_pdf)
documentos = loader.load()

splitter = RecursiveCharacterTextSplitter(chunk_size=500, chunk_overlap=100)
chunks = splitter.split_documents(documentos)

embeddings = OpenAIEmbeddings()
db_path = "banco_faiss"
if os.path.exists(db_path):
    vectordb = FAISS.load_local(db_path, embeddings, allow_dangerous_deserialization=True)
    vectordb.add_documents(chunks)
else:
    vectordb = FAISS.from_documents(chunks, embeddings)
    vectordb.save_local(db_path)

retriever = vectordb.as_retriever()
qa = RetrievalQA.from_chain_type(
    llm=ChatOpenAI(model_name="gpt-3.5-turbo"),
    retriever=retriever,
    return_source_documents=True)


pergunta = "O que o PDF fala sobre Sigmoid? explique de uma forma simples"
resposta = qa.invoke(pergunta)

print("Resposta:")
print(resposta["result"])
