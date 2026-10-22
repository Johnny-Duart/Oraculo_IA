import json
from unittest.mock import MagicMock, patch

from django.conf import settings
from django.contrib.auth.models import User
from django.test import Client, TestCase
from django.urls import reverse
from oraculo.models import DataTreinamento, Pergunta, Treinamento
from oraculo.utils import _make_doc, gerar_documentos, html_para_texto_rag


class OraculoModelTests(TestCase):
    def test_treinamento_str_representations(self):
        t_site = Treinamento.objects.create(site="https://example.com")
        self.assertEqual(str(t_site), "https://example.com")

        t_conteudo = Treinamento.objects.create(
            conteudo="Este é um conteúdo de treinamento longo para teste."
        )
        self.assertTrue(str(t_conteudo).startswith("Este é um conteúdo"))

        t_vazio = Treinamento.objects.create()
        self.assertEqual(str(t_vazio), f"Treinamento #{t_vazio.pk}")

    def test_pergunta_str_representation(self):
        p = Pergunta.objects.create(pergunta="Qual é o horário?")
        self.assertEqual(str(p), "Qual é o horário?")

    def test_pergunta_data_treinamento_relationship(self):
        dt = DataTreinamento.objects.create(
            metadata={"source": "teste"}, texto="Informação importante."
        )
        p = Pergunta.objects.create(pergunta="Dúvida")
        p.data_treinamento.add(dt)
        self.assertEqual(p.data_treinamento.count(), 1)
        self.assertEqual(p.data_treinamento.first().texto, "Informação importante.")


class RAGUtilsTests(TestCase):
    def test_html_para_texto_rag_basic(self):
        html = """
        <html>
            <head><title>Título</title></head>
            <body>
                <h1>Introdução à IA</h1>
                <p>Inteligência artificial é uma tecnologia moderna.</p>
                <ul>
                    <li>Redes Neurais</li>
                    <li>Visão Computacional</li>
                </ul>
            </body>
        </html>
        """
        texto = html_para_texto_rag(html)
        self.assertIn("### INTRODUÇÃO À IA", texto)
        self.assertIn("Inteligência artificial é uma tecnologia moderna.", texto)
        self.assertIn("- Redes Neurais", texto)

    def test_html_para_texto_rag_removes_noise_and_citations(self):
        html = """
        <div>
            <nav><a href="/menu">Menu</a></nav>
            <div id="mw-content-text">
                <h2>História [editar | editar código-fonte]</h2>
                <p>O conceito surgiu em 1950 [1][2].</p>
                <div class="reference">Referência 1</div>
            </div>
            <footer>Rodapé do site</footer>
        </div>
        """
        texto = html_para_texto_rag(html)
        self.assertNotIn("Menu", texto)
        self.assertNotIn("Rodapé do site", texto)
        self.assertNotIn("Referência 1", texto)
        self.assertNotIn("[1]", texto)
        self.assertNotIn("[editar", texto)
        self.assertIn("O conceito surgiu em 1950.", texto)

    def test_make_doc(self):
        doc = _make_doc("Texto do documento", "origem.pdf")
        self.assertEqual(doc.page_content, "Texto do documento")
        self.assertEqual(doc.metadata["arquivo"], "origem.pdf")

    def test_gerar_documentos_conteudo_digitado(self):
        t = Treinamento(conteudo="Regras internas de atendimento")
        docs = gerar_documentos(t)
        self.assertEqual(len(docs), 1)
        self.assertEqual(docs[0].page_content, "Regras internas de atendimento")
        self.assertEqual(docs[0].metadata["arquivo"], "Conteúdo digitado")

    @patch("requests.get")
    def test_gerar_documentos_site(self, mock_get):
        mock_resp = MagicMock()
        mock_resp.text = "<h1>Página de Teste</h1><p>Conteúdo relevante do site.</p>"
        mock_resp.encoding = "utf-8"
        mock_resp.status_code = 200
        mock_resp.raise_for_status = MagicMock()
        mock_get.return_value = mock_resp

        t = Treinamento(site="https://exemplo.com/doc")
        docs = gerar_documentos(t)

        self.assertEqual(len(docs), 1)
        self.assertIn("Conteúdo relevante do site.", docs[0].page_content)
        self.assertEqual(docs[0].metadata["arquivo"], "https://exemplo.com/doc")

    @patch("requests.get")
    def test_gerar_documentos_site_request_error(self, mock_get):
        mock_get.side_effect = Exception("Falha de rede")
        t = Treinamento(site="https://site-invalido.com")
        docs = gerar_documentos(t)
        self.assertEqual(docs, [])


class OraculoViewsTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username="chatuser", password="password123"
        )

    def test_chat_get_renders_template(self):
        response = self.client.get(reverse("chat"))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "chat.html")

    def test_chat_post_saves_pergunta_and_returns_json(self):
        response = self.client.post(
            reverse("chat"), {"pergunta": "Como treinar a IA?"}
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("id", data)
        self.assertTrue(
            Pergunta.objects.filter(id=data["id"], pergunta="Como treinar a IA?").exists()
        )

    def test_treinar_ia_requires_login(self):
        response = self.client.get(reverse("treinar_ia"))
        self.assertEqual(response.status_code, 302)

    def test_treinar_ia_get_authenticated(self):
        self.client.login(username="chatuser", password="password123")
        response = self.client.get(reverse("treinar_ia"))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "treinar_ia.html")

    @patch("oraculo.signals.async_task")
    def test_treinar_ia_post_creates_treinamento(self, mock_async_task):
        self.client.login(username="chatuser", password="password123")
        response = self.client.post(
            reverse("treinar_ia"),
            {"conteudo": "Novo material de treinamento"},
        )
        self.assertRedirects(response, reverse("treinar_ia"))
        self.assertTrue(
            Treinamento.objects.filter(conteudo="Novo material de treinamento").exists()
        )

    def test_ver_fontes_requires_login(self):
        p = Pergunta.objects.create(pergunta="Teste?")
        response = self.client.get(reverse("ver_fontes", args=[p.id]))
        self.assertEqual(response.status_code, 302)

    def test_ver_fontes_404_if_not_found(self):
        self.client.login(username="chatuser", password="password123")
        response = self.client.get(reverse("ver_fontes", args=[999999]))
        self.assertEqual(response.status_code, 404)

    def test_ver_fontes_renders_with_special_unicode_characters(self):
        self.client.login(username="chatuser", password="password123")
        dt = DataTreinamento.objects.create(
            metadata={"arquivo": "Conteúdo digitado"},
            texto="Fórmula com caracteres especiais: y=σ(1⋅0,1+2⋅0.5) e acentuação: café & bistrô",
        )
        p = Pergunta.objects.create(pergunta="Qual é a fórmula?")
        p.data_treinamento.add(dt)

        response = self.client.get(reverse("ver_fontes", args=[p.id]))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "ver_fontes.html")
        self.assertContains(response, "y=σ(1⋅0,1+2⋅0.5)")
        self.assertContains(response, "Texto inserido manualmente no treinamento")

    def test_webhook_whatsapp_get(self):
        response = self.client.get(reverse("webhook_whatsapp"))
        self.assertEqual(response.status_code, 200)
        self.assertIn("Webhook funcionando!", response.content.decode("utf-8"))

    def test_webhook_whatsapp_invalid_method(self):
        response = self.client.put(reverse("webhook_whatsapp"))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content.decode("utf-8"), "Apenas POST")

    def test_webhook_whatsapp_invalid_json(self):
        response = self.client.post(
            reverse("webhook_whatsapp"),
            data="invalid-json-body",
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 400)

    def test_webhook_whatsapp_unauthorized_apikey(self):
        payload = json.dumps({"apikey": "wrong-key", "event": "messages.upsert"})
        response = self.client.post(
            reverse("webhook_whatsapp"),
            data=payload,
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 401)

    def test_webhook_whatsapp_valid_key_ignored_event(self):
        payload = json.dumps(
            {
                "apikey": settings.EVOLUTION_WEBHOOK_APIKEY,
                "event": "connection.update",
            }
        )
        response = self.client.post(
            reverse("webhook_whatsapp"),
            data=payload,
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"status": "ignorado"})
