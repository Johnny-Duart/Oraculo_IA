# 🤖 Oráculo IA — Chatbot com RAG + Integração WhatsApp

Sistema web desenvolvido com **Django** que permite treinar uma IA personalizada a partir de **sites, textos e documentos**, utilizando técnicas de **RAG (Retrieval-Augmented Generation)** — com respostas disponíveis tanto por uma interface web quanto diretamente pelo **WhatsApp**.
<img width="800" height="500" alt="demo-oraculo" src="https://github.com/user-attachments/assets/832d6687-feef-4b6f-beaf-5ea2d423633f" />

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

- ✅ Cadastro, login e gestão de usuários (com exclusão de colaboradores e travas de segurança)
- ✅ Sistema de controle de acesso baseado em papéis (RBAC: usuário comum / gerente)
- ✅ Pipeline de treinamento da IA (RAG multimodal):
  - Sites (web scraping com bypass anti-bloqueio e sanitização Markdown)
  - Texto digitado manualmente
  - Arquivos e documentos (PDF)
- ✅ Processamento assíncrono em segundo plano (Django Q) com índice vetorial autocicatrizante
- ✅ Geração de embeddings vetoriais (Ollama / `nomic-embed-text`)
- ✅ Armazenamento e busca por similaridade com FAISS
- ✅ Interface web com streaming de respostas em tempo real
- ✅ Rastreabilidade de fontes com suporte total a Unicode e tratamento dinâmico de links e mídias
- ✅ **Integração com WhatsApp via Evolution API** — respostas automatizadas e contextualizadas
- ✅ Buffer inteligente de mensagens (agrupa envios consecutivos antes de processar)
- ✅ **40 testes automatizados** cobrindo autenticação, permissões, RAG, scraping e segurança

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

### Testes Automatizados

A aplicação conta com uma suíte de 40 testes automatizados cobrindo autenticação, permissões, RAG, scraping e segurança:

```bash
# Rodar com Poetry (recomendado)
poetry run python manage.py test

# Ou com ambiente virtual ativo
python manage.py test
```

---

## 🌟 Diferenciais Técnicos e Atualizações Recentes

### 1. 🧠 IA, RAG e Web Scraping Resiliente
* **Web Scraping Anti-Bloqueio:** Cabeçalhos dinâmicos com `User-Agent` de navegador moderno para contornar bloqueios HTTP 403 Forbidden em fontes com proteção anti-bot (como a Wikipedia).
* **Sanitização Semântica:** Limpeza profunda via BeautifulSoup removendo scripts, navegações, rodapés e referências numéricas, convertendo o conteúdo estruturado em Markdown antes de enviar à base vetorial (FAISS).
* **Índice FAISS Autocicatrizante:** Fallback automático no pipeline de indexação caso os arquivos do índice vetorial estejam ausentes ou corrompidos, recriando a base do zero sem quebrar a execução assíncrona.
* **Prompt Engineering Natural:** Respostas humanizadas e diretas, sem marcadores técnicos expositivos (`[CONTEXTO]`, `contexto 1`), capazes de sintetizar múltiplos formatos (sites, PDFs e textos manuais) simultaneamente.

### 2. 🔍 Rastreabilidade e Visualização de Fontes
* **Detecção Inteligente de Origem:** Tratamento dinâmico para evitar erros 404 ao visualizar fontes — diferenciando com precisão textos digitados, URLs externas e documentos PDF originais armazenados no Django Media.
* **Blindagem de Caracteres Especiais:** Configuração de I/O em UTF-8 nativo para suporte resiliente a símbolos científicos, fórmulas matemáticas e alfabetos gregos (ex: $\sigma$, $\alpha$), prevenindo falhas de codificação como `UnicodeEncodeError`.

### 3. 👥 Controle de Acesso e Segurança (RBAC)
* **Gestão Hierárquica:** Acesso diferenciado para Gerentes e Funcionários comuns com validação estrita em rotas sensíveis via `django-role-permissions`.
* **Travas de Segurança:** Regras de integridade que bloqueiam auto-exclusão da própria conta e protegem contas de superusuários contra remoção indevida.
* **Proteção de Rotas Internas:** Configuração de redirecionamento seguro (`LOGIN_URL`) para impedir acessos anônimos a rotas protegidas.

### 4. 🧪 Engenharia de Software e Qualidade (40 Testes Automatizados)
Suíte robusta de testes automatizados garantindo a integridade e regressão zero da aplicação:
* **App `usuarios` (18 testes):** Fluxos de autenticação, força de senhas, login/logout, rotinas de exclusão e controle de permissões.
* **App `oraculo` (22 testes):** Modelos, parser semântico, chunking, sanitização de texto, suporte a caracteres Unicode especiais e validação de segurança no webhook do WhatsApp.

```bash
# Rodar a suíte completa de testes
python manage.py test
```

### 5. 💡 Diferenciais Arquiteturais
- **RAG Ponta a Ponta:** Pipeline completo com ingestão multimodal (sites, PDFs, textos), chunking com overlap, embeddings (`nomic-embed-text`) e busca com Maximal Marginal Relevance (MMR).
- **Integração Real com WhatsApp:** Atendimento corporativo com buffer inteligente de mensagens em cache e webhook autenticado via Evolution API.
- **Processamento Assíncrono com Django Q:** Filas de tarefas desacopladas para treinamento e geração de embeddings sem travar a interface do usuário.

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
