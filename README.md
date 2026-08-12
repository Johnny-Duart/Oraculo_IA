# 🤖 Oráculo IA — Chatbot com RAG + Integração WhatsApp

Sistema web desenvolvido com **Django** que permite treinar uma IA personalizada a partir de **sites, textos e documentos**, utilizando técnicas de **RAG (Retrieval-Augmented Generation)** — com respostas disponíveis tanto por uma interface web quanto diretamente pelo **WhatsApp**.

---

## 🚀 Sobre o projeto

O **Oráculo IA** é uma aplicação que permite:

- Upload de dados para treinamento (URLs, textos e arquivos PDF)
- Processamento assíncrono de dados em background
- Criação de base vetorial (FAISS) para consultas inteligentes
- Interface web para interação com o chatbot
- **Atendimento automatizado via WhatsApp**, usando a Evolution API

A proposta é simular um sistema real de IA corporativa, onde usuários treinam uma base de conhecimento e podem consultá-la tanto internamente (painel web) quanto externamente (WhatsApp de clientes/usuários finais).

---

## 🧠 Funcionalidades atuais

- ✅ Cadastro e login de usuários
- ✅ Sistema de permissões (usuário / gerente)
- ✅ Upload de dados para treinamento:
  - Sites (web scraping)
  - Texto manual
  - Arquivos (PDF)
- ✅ Processamento assíncrono com filas (Django Q)
- ✅ Geração de embeddings (Ollama)
- ✅ Armazenamento vetorial com FAISS
- ✅ Interface web para treinamento e chat (com streaming de resposta)
- ✅ **Integração com WhatsApp via Evolution API** — recebe perguntas e responde automaticamente com base no conhecimento treinado
- ✅ Buffer de mensagens (agrupa múltiplas mensagens do usuário antes de responder)
- ✅ Autenticação de webhook (validação de apikey)

---

## ⚙️ Tecnologias utilizadas

- **Backend:** Django, Django Q (filas assíncronas)
- **IA / RAG:** LangChain
- **Embeddings e LLM:** Ollama (`nomic-embed-text`, `llama3`)
- **Banco vetorial:** FAISS
- **Integração WhatsApp:** Evolution API (Docker) + webhook
- **Infraestrutura de dev:** Docker (Evolution API, PostgreSQL, Redis), ngrok (túnel HTTPS)
- **Web scraping:** BeautifulSoup
- **Frontend:** HTML + TailwindCSS

---

## 🏗️ Arquitetura

- `usuarios/` → autenticação e permissões
- `oraculo/` → lógica da IA, treinamento e integração com WhatsApp
- `core/` → configurações globais do Django

### 🔄 Fluxo de treinamento

1. Usuário envia dados (site, texto ou arquivo) pelo painel web
2. Um signal `post_save` dispara uma task assíncrona (Django Q)
3. O conteúdo é extraído e dividido em chunks
4. Embeddings são gerados via Ollama
5. Os vetores são armazenados/atualizados no índice FAISS (`banco_faiss/`)

### 💬 Fluxo de conversa (WhatsApp)

1. Evolution API recebe uma mensagem no WhatsApp conectado
2. Envia um webhook (`POST /oraculo/webhook_whatsapp/`) para o Django
3. A mensagem é validada (apikey, remetente, tipo) e armazenada em um buffer (cache)
4. Após um pequeno delay (agrupando possíveis mensagens seguidas), o sistema:
   - Busca os trechos mais relevantes no FAISS
   - Monta um prompt com o contexto encontrado
   - Gera a resposta via LLM (Ollama)
   - Envia a resposta de volta ao usuário via Evolution API

### 🔄 Processamento assíncrono

O treinamento roda em background via `django_q` + signals do Django (`post_save`), evitando travar a interface enquanto o índice é atualizado.

---

## 🔐 Controle de acesso

- Autenticação de usuários (login obrigatório nas rotas internas)
- Permissões por papel (usuário comum / gerente), via `django-role-permissions`
- Webhook do WhatsApp protegido por validação de apikey

---

## ▶️ Como rodar o projeto

### Pré-requisitos

- Python 3.13
- [Ollama](https://ollama.com) instalado, com os modelos baixados:
  ```bash
  ollama pull nomic-embed-text
  ollama pull llama3
  ```
- Docker (para rodar a Evolution API, usada na integração com WhatsApp)
- [ngrok](https://ngrok.com) (para expor o webhook publicamente em ambiente de desenvolvimento)

### Setup

```bash
# Clonar o repositório
git clone https://github.com/Johnny-Duart/Oraculo_IA.git
cd Oraculo_IA/mysite

# Copiar e configurar as variáveis de ambiente
cp .env.example .env
# edite o .env com sua SECRET_KEY, chaves da Evolution API, etc.

# Opção A: usando Poetry (recomendado)
poetry install
poetry run python manage.py migrate

# Opção B: usando pip
python -m venv .venv
.venv\Scripts\activate  # Windows
pip install -r requirements.txt
python manage.py migrate
```

### Subindo a Evolution API (WhatsApp)

Suba os containers da Evolution API, PostgreSQL e Redis (configuração no seu `docker-compose.yml`), depois crie e conecte a instância:

```bash
python oraculo/create_instance.py
python oraculo/connect.py   # gera um QR code — escaneie com o WhatsApp
```

### Rodando o projeto (3 processos em paralelo)

```bash
# Terminal 1 — servidor Django
python manage.py runserver 8001

# Terminal 2 — worker de tarefas assíncronas (treinamento da IA)
python manage.py qcluster

# Terminal 3 — túnel público para o webhook (dev)
ngrok http 8001
```

Depois, registre a URL gerada pelo ngrok como webhook na Evolution API (`.../oraculo/webhook_whatsapp/`).

---

## 💡 Diferenciais do projeto

- Aplicação prática de RAG ponta a ponta
- Integração real com WhatsApp (não é só um chat web)
- Processamento assíncrono e resiliente a falhas de dependências (fallbacks explícitos)
- Estrutura próxima de sistemas reais de atendimento automatizado

---

## ⚠️ Observações

- Projeto em desenvolvimento — pode sofrer alterações frequentes.
- Configurado para ambiente de desenvolvimento local (SQLite, `DEBUG=True`, servidor de desenvolvimento do Django). Para produção, seriam necessários ajustes de segurança e infraestrutura.

---

## 👨‍💻 Equipe e contribuições

**Jonathan Duarte** — Backend, IA e integrações
- Arquitetura do projeto (Django, modelagem de dados, apps `usuarios` e `oraculo`)
- Pipeline de RAG completo: extração de conteúdo (sites/texto/PDF), chunking, geração de embeddings e indexação no FAISS
- Integração com LLM (Ollama) para geração de respostas
- Chatbot web (interface de chat com streaming de resposta)
- Integração com WhatsApp via Evolution API (webhook, buffer de mensagens, envio de respostas)
- Sistema de autenticação, permissões (usuário/gerente) e proteção das rotas

**Ramon Nogueira** — Estilização e front-end
- Refinamento visual das telas (HTML/TailwindCSS) a partir da base inicial do projeto

**Matheus** — Integração com Evolution API
- Identificação de uma versão estável da Evolution API (a base inicial usava uma versão antiga com o envio de mensagens quebrado)
- Correções pontuais na integração para o envio de mensagens funcionar corretamente

---

## 👨‍💻 Autor

Desenvolvido por Jonathan Duarte, com colaboração de Ramon Nogueira e Matheus