# 🤖 Oráculo IA — Chatbot com RAG (em desenvolvimento)

Sistema web desenvolvido com **Django** que permite treinar uma IA personalizada a partir de **sites, textos e documentos**, utilizando técnicas de **RAG (Retrieval-Augmented Generation)**.

> 🚧 Projeto em desenvolvimento — novas funcionalidades estão sendo implementadas continuamente.

---

## 🚀 Sobre o projeto

O **Oráculo IA** é uma aplicação que permite:

- Upload de dados para treinamento (URLs, textos e arquivos)
- Processamento assíncrono de dados
- Criação de base vetorial para consultas inteligentes
- Interface web para interação com chatbot

A proposta é simular um sistema real de IA corporativa, onde usuários podem treinar e consultar uma base de conhecimento personalizada.

---

## 🧠 Funcionalidades atuais

- ✅ Cadastro e login de usuários  
- ✅ Sistema de permissões (usuário / gerente)  
- ✅ Upload de dados para treinamento:
  - Sites (web scraping)
  - Texto manual
  - Arquivos (PDF)
- ✅ Processamento assíncrono com filas  
- ✅ Geração de embeddings  
- ✅ Armazenamento vetorial com FAISS  
- ✅ Interface web para treinamento e chat  
- 🚧 Sistema de chat (em desenvolvimento)  

---

## ⚙️ Tecnologias utilizadas

- **Backend:** Django  
- **IA / RAG:** LangChain  
- **Embeddings:** Ollama  
- **Banco vetorial:** FAISS  
- **Processamento assíncrono:** Django Q  
- **Web scraping:** BeautifulSoup  
- **Frontend:** HTML + TailwindCSS  

---

## 🏗️ Arquitetura

O projeto segue uma estrutura modular:

- `usuarios/` → autenticação e permissões  
- `oraculo/` → lógica da IA e treinamento  
- `core/` → configurações globais  

### 🔄 Fluxo de treinamento

1. Usuário envia dados (site, texto ou arquivo)  
2. Sistema processa conteúdo  
3. Texto é dividido em chunks  
4. Embeddings são gerados  
5. Dados são armazenados no FAISS  
6. Base fica pronta para consultas futuras  

---

## 🔄 Processamento assíncrono

O treinamento da IA ocorre em background utilizando:

- `django_q`  
- Signals do Django (`post_save`)  

Isso evita travamentos e melhora a experiência do usuário.

---

## 🔐 Controle de acesso

O sistema possui controle de permissões com:

- Usuários comuns  
- Gerentes (podem treinar a IA)  

Gerenciado com a biblioteca **django-role-permissions**.

---

## ▶️ Como rodar o projeto

```bash
# Clonar o repositório
git clone https://github.com/Johnny-Duart/Oraculo_IA.git

# Entrar na pasta
cd Oraculo_IA

# Criar ambiente virtual
python -m venv venv

# Ativar ambiente (Windows)
venv\Scripts\activate

# Instalar dependências
pip install -r requirements.txt

# Rodar migrações
python manage.py migrate

# Iniciar servidor
python manage.py runserver
```

## 💡 Diferenciais do projeto
Aplicação prática de RAG
Uso de processamento assíncrono
Integração com múltiplas fontes de dados
Estrutura próxima de sistemas reais de IA

---

## 👨‍💻 Autor

Desenvolvido por Jonathan Duarte

---

⚠️ Observação

Este projeto está em desenvolvimento e pode sofrer alterações frequentes.

---

