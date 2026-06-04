# README 2.0 — Resumo das alterações e instruções de execução

Este documento explica, de forma didática, todas as alterações que fizemos no projeto para torná-lo executável localmente e modernizar a interface. Inclui: o que foi alterado, por quê, como reproduzir o ambiente, como gerar o índice FAISS (treinamento) e onde encontrar cada arquivo modificado.

---

## 1) Objetivo das mudanças
- Permitir rodar rapidamente a UI (frontend) sem depender imediatamente de todas as dependências pesadas de IA.  
- Tornar o carregamento do projeto resiliente quando bibliotecas opcionais (faiss/langchain, requests, bs4) não estiverem presentes.  
- Modernizar o front-end com um `base.html` novo e assets estáticos (CSS/JS/imagens).  
- Garantir que a raiz (`/`) redirecione para a área principal (`/oraculo/chat/`).

---

## 2) Ambiente reproduzível (passos rápidos)
Estes são os comandos que usei no Windows (PowerShell). Eles criam um venv com Python 3.11, instalam as dependências e iniciam o servidor Django.

1) Instalar Python 3.11 (se necessário):

```powershell
winget install --id=Python.Python.3.11 -e --accept-package-agreements --accept-source-agreements
```

2) Criar e ativar o venv com Python 3.11:

```powershell
cd "C:\Users\val_r\Music\Dev IA\Oraculo_IA"
py -3.11 -m venv venv311
.\venv311\Scripts\Activate.ps1
```

3) Atualizar pip e instalar dependências:

```powershell
python -m pip install --upgrade pip setuptools wheel
python -m pip install -r requirements.txt
```

4) Aplicar migrações e iniciar servidor (em uma aba/terminal):

```powershell
python mysite\manage.py migrate --noinput
python mysite\manage.py runserver 8001
```

5) Para que o processamento assíncrono de treinamento funcione (cria o índice FAISS), abra outro terminal e rode o worker do django-q:

```powershell
python mysite\manage.py qcluster
```

Observações:
- Eu removi um `venv` antigo e deixei `venv311` como o ambiente usado.  
- Em máquinas Windows onde pacotes nativos devem ser compilados (zstandard, algumas versões de numpy, etc.), pode ser necessário instalar o "Microsoft Visual C++ Build Tools" ou usar wheels pré-compiladas. Recomendo usar Python 3.11 para compatibilidade com as wheels disponíveis.

---

## 3) Como gerar o índice FAISS (treinamento)
1. Certifique-se que o `qcluster` está rodando (ver passo 5 acima).  
2. Acesse a interface de treinamento: `http://127.0.0.1:8001/oraculo/treinar_ia/`.  
3. Envie um site / texto / PDF pelo formulário. O `post_save` em `Treinamento` cria uma tarefa assíncrona que:
   - usa `oraculo.utils.gerar_documentos()` para extrair texto;
   - quebra em chunks com `RecursiveCharacterTextSplitter` e gera embeddings (OllamaEmbeddings);
   - salva/atualiza o banco FAISS local em `banco_faiss/`.

Dica: se o index FAISS não existir e você tentar perguntar no chat, a aplicação agora retorna uma mensagem amigável orientando a rodar o treinamento (em vez de 500).

---

## 4) Problemas enfrentados e soluções aplicadas (resumido)
- Erros de import (faiss, langchain, requests, bs4) impediam o `runserver` de iniciar.  
  -> Solução: tornamos imports opcionais (try/except) e adicionamos fallbacks informativos nas views. Arquivo principal: `mysite/oraculo/utils.py` e `mysite/oraculo/views.py`.

- Erro ao carregar índice FAISS inexistente causava 500 ao usar streaming de resposta.  
  -> Solução: capturei a exceção de carregamento do índice e retorno uma mensagem explicando que é necessário treinar antes.

- `base.html` antigo e inconsistências nos templates (uso incorreto de `{% block 'conteudo' %}` com aspas) causavam erros/formatos incorretos.  
  -> Solução: novo `base.html` com layout atualizado e correções em todos os templates para usar `{% block conteudo %}` corretamente.

- O projeto possuía um `runserver` rodando a partir de um venv antigo que travava remoção do diretório.  
  -> Solução: parei os processos antigos e removi o `venv` legado; instalei Python 3.11 e criei `venv311`.

---

## 5) Arquivos alterados / adicionados
Abaixo estão os arquivos que eu criei ou modifiquei durante o trabalho — linkados para facilitar a revisão.

- `mysite/oraculo/utils.py` — tornar imports opcionais, fallbacks `Document` simples, start seguro do scheduler, métodos de geração de documentos resilientes.
- `mysite/oraculo/views.py` — imports condicionais de LangChain, tratamento de exceção ao carregar índice FAISS, mensagens amigáveis quando dependências faltam, proteção do webhook/ agendamento.
- `mysite/oraculo/urls.py` — mapeamento direto para `views.*` (antes foram strings que causavam import issues em tempo de carga).
- `mysite/oraculo/apps.py` — `ready()` protegido com try/except para `oraculo.signals`.
- `mysite/oraculo/templates/chat.html` — UI do chat e script cliente para streaming de respostas.
- `mysite/oraculo/templates/treinar_ia.html` — formulário de envio para treinar/gerar index (upload site/conteúdo/PDF).
- `mysite/oraculo/templates/ver_fontes.html` — página para exibir contextos/fontes encontrados.
- `mysite/oraculo/send.py` (se presente) — não modificado diretamente aqui, mas utilizado via wrappers; ver arquivo do projeto.
- `mysite/usuarios/views.py` — adicionei/garanti `logout_view()` e fluxos de login/cadastro (ajustes de robustez). 
- `mysite/usuarios/urls.py` — rota `logout/` adicionada.
- `mysite/usuarios/templates/cadastro.html` — atualizado para novo layout.
- `mysite/usuarios/templates/login.html` — atualizado para novo layout.
- `mysite/usuarios/templates/permissoes.html` — atualizado para novo layout.
- `mysite/templates/base.html` — novo layout (nav, rodapé, inclusão de Tailwind CDN e `css/main.css`, `js/main.js`).
- `mysite/templates/static/css/main.css` — novo CSS base (tipografia, helpers).
- `mysite/templates/static/js/main.js` — JS leve para interações UI.
- `mysite/templates/static/logo.svg` — novo logo simples.
- `mysite/templates/static/assistente_virtual.png` — imagem usada no chat.
- `mysite/core/urls.py` — adicionado redirecionamento da raiz (`/`) para `/oraculo/chat/`.

Observação: o sinalizador/worker que cria o FAISS está em `mysite/oraculo/signals.py` (não foi modificado), ele é a rotina que executa a construção/atualização do banco FAISS quando um `Treinamento` é criado.

---

## 6) Como testar rapidamente (checklist)
- [ ] Ativar `venv311` e garantir `python -V` é 3.11.x.  
- [ ] `python mysite\manage.py migrate --noinput`  
- [ ] `python mysite\manage.py qcluster` (em outra aba)  
- [ ] `python mysite\manage.py runserver 8001`  
- [ ] Abrir `http://127.0.0.1:8001/` (será redirecionado para `/oraculo/chat/`)  
- [ ] Abrir `/oraculo/treinar_ia/`, enviar conteúdo e observar tarefas no terminal do `qcluster` para criação do índice FAISS.  
- [ ] Voltar ao chat e enviar uma pergunta — se o index existir, o streaming responderá; caso contrário, a aplicação avisará para treinar primeiro.

---

## 7) Observações sobre dependências pesadas
- Pacotes como `faiss-cpu`, `numpy` (algumas versões) e `zstandard` podem exigir ferramentas de compilação no Windows (MSVC). Recomendação: usar Python 3.11 (wheels), ou instalar Visual C++ Build Tools se precisar compilar.
- Eu instalei as dependências do `requirements.txt` com `venv311` usando `pip` (o processo baixou as wheels compatíveis para 3.11 na minha máquina).

---

## 8) Próximos passos e sugestões
- Criar um `management command` para (re)construir o índice FAISS manualmente (útil para CI ou recuperação manual).  
- Adicionar monitor/health-check para `banco_faiss/` e um botão 'Rebuild index' na UI (posso implementar).  
- Adicionar testes automatizados básicos para endpoints do chat e treinamento.  

---

## 9) Contato / quem fez as alterações
- Alterações aplicadas pelo time de suporte local (histórico interno no repositório). Caso queiram eu posso abrir um PR com commits separados e mensagens por alteração.

---

Se quiser, eu já:
- gero um `PR` com essas mudanças;  
- implemento um endpoint `rebuild_index` que força a criação do FAISS a partir do conteúdo já salvo;  
- adiciono instruções de deploy para produção (WSGI/ASGI + Gunicorn/ Daphne). 

Diga qual desses próximos passos prefere que eu faça.
