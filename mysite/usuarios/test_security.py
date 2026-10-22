from django.contrib.auth.models import Group, User
from django.contrib.messages import get_messages
from django.test import Client, TestCase
from django.urls import reverse
from rolepermissions.roles import assign_role


class UserSecurityAccessControlTests(TestCase):
    """
    Testes de Segurança: Controle de Acesso, RBAC e Prevenção de Escalada de Privilégios
    """

    def setUp(self):
        self.anonymous_client = Client()
        self.common_user = User.objects.create_user(
            username="funcionario_comum", password="password123"
        )
        self.common_client = Client()
        self.common_client.force_login(self.common_user)

        self.gerente_user = User.objects.create_user(
            username="gerente_user", password="password123"
        )
        assign_role(self.gerente_user, "gerente")
        self.gerente_client = Client()
        self.gerente_client.force_login(self.gerente_user)

        self.superuser = User.objects.create_superuser(
            username="super_admin", password="password123", email="admin@teste.com"
        )

        self.target_user = User.objects.create_user(
            username="usuario_alvo", password="password123"
        )

    def test_anonymous_access_denied_on_permissoes(self):
        response = self.anonymous_client.get(reverse("permissoes"))
        self.assertEqual(response.status_code, 302)
        self.assertIn("/usuarios/login/", response.url)

    def test_anonymous_access_denied_on_tornar_gerente(self):
        response = self.anonymous_client.get(
            reverse("tornar_gerente", kwargs={"id": self.target_user.id})
        )
        self.assertEqual(response.status_code, 302)
        self.assertIn("/usuarios/login/", response.url)

    def test_anonymous_access_denied_on_remover_gerente(self):
        response = self.anonymous_client.get(
            reverse("remover_gerente", kwargs={"user_id": self.target_user.id})
        )
        self.assertEqual(response.status_code, 302)
        self.assertIn("/usuarios/login/", response.url)

    def test_anonymous_access_denied_on_excluir_usuario(self):
        response = self.anonymous_client.get(
            reverse("excluir_usuario", kwargs={"user_id": self.target_user.id})
        )
        self.assertEqual(response.status_code, 302)
        self.assertIn("/usuarios/login/", response.url)

    def test_regular_user_cannot_access_permissoes(self):
        response = self.common_client.get(reverse("permissoes"))
        self.assertEqual(response.status_code, 404)

    def test_regular_user_cannot_promote_other_user(self):
        response = self.common_client.get(
            reverse("tornar_gerente", kwargs={"id": self.target_user.id})
        )
        self.assertEqual(response.status_code, 404)
        gerente_group = Group.objects.get_or_create(name="gerente")[0]
        self.assertNotIn(gerente_group, self.target_user.groups.all())

    def test_regular_user_cannot_demote_gerente(self):
        assign_role(self.target_user, "gerente")
        response = self.common_client.get(
            reverse("remover_gerente", kwargs={"user_id": self.target_user.id})
        )
        self.assertEqual(response.status_code, 404)
        gerente_group = Group.objects.get(name="gerente")
        self.assertIn(gerente_group, self.target_user.groups.all())

    def test_regular_user_cannot_delete_other_user(self):
        response = self.common_client.get(
            reverse("excluir_usuario", kwargs={"user_id": self.target_user.id})
        )
        self.assertEqual(response.status_code, 404)
        self.assertTrue(User.objects.filter(id=self.target_user.id).exists())

    def test_gerente_cannot_delete_self(self):
        response = self.gerente_client.get(
            reverse("excluir_usuario", kwargs={"user_id": self.gerente_user.id}),
            follow=True,
        )
        self.assertRedirects(response, reverse("permissoes"))
        self.assertTrue(User.objects.filter(id=self.gerente_user.id).exists())
        messages = [m.message for m in get_messages(response.wsgi_request)]
        self.assertIn("Você não pode excluir sua própria conta!", messages)

    def test_gerente_cannot_delete_superuser(self):
        response = self.gerente_client.get(
            reverse("excluir_usuario", kwargs={"user_id": self.superuser.id}),
            follow=True,
        )
        self.assertRedirects(response, reverse("permissoes"))
        self.assertTrue(User.objects.filter(id=self.superuser.id).exists())
        messages = [m.message for m in get_messages(response.wsgi_request)]
        self.assertIn("Não é permitido excluir um superusuário!", messages)

    def test_superusers_excluded_from_permissoes_list(self):
        response = self.gerente_client.get(reverse("permissoes"))
        self.assertEqual(response.status_code, 200)
        users_in_context = response.context["users"]
        self.assertNotIn(self.superuser, users_in_context)
        self.assertNotIn(self.gerente_user, users_in_context)


class PasswordAndCredentialsSecurityTests(TestCase):
    """
    Testes de Segurança: Armazenamento e Integridade de Credenciais
    """

    def test_password_is_properly_hashed_not_plaintext(self):
        user = User.objects.create_user(
            username="hash_test_user", password="secretpassword123"
        )
        # O password no banco nunca pode ser o texto puro
        self.assertNotEqual(user.password, "secretpassword123")
        # Deve utilizar algoritmo de hashing do Django (ex: pbkdf2_sha256, argon2, etc)
        self.assertTrue(
            user.password.startswith("pbkdf2_sha256$")
            or user.password.startswith("argon2")
            or user.password.startswith("bcrypt")
        )
        self.assertTrue(user.check_password("secretpassword123"))
        self.assertFalse(user.check_password("wrongpassword"))


class CSRFAndSecurityHeadersTests(TestCase):
    """
    Testes de Segurança: CSRF Protection e Cabeçalhos HTTP de Proteção
    """

    def test_login_post_without_csrf_is_rejected_when_enforced(self):
        enforced_client = Client(enforce_csrf_checks=True)
        response = enforced_client.post(
            reverse("login"),
            {"username": "testuser", "senha": "password123"},
        )
        # Sem token CSRF, Django deve responder 403 Forbidden
        self.assertEqual(response.status_code, 403)

    def test_cadastro_post_without_csrf_is_rejected_when_enforced(self):
        enforced_client = Client(enforce_csrf_checks=True)
        response = enforced_client.post(
            reverse("cadastro"),
            {
                "username": "attacker",
                "senha": "password123",
                "confirmar_senha": "password123",
            },
        )
        self.assertEqual(response.status_code, 403)

    def test_security_header_clickjacking_x_frame_options(self):
        client = Client()
        response = client.get(reverse("login"))
        # Middleware XFrameOptionsMiddleware deve enviar cabeçalho de proteção
        self.assertIn("X-Frame-Options", response.headers)
        self.assertIn(response.headers["X-Frame-Options"].upper(), ["DENY", "SAMEORIGIN"])

    def test_security_header_content_type_options(self):
        client = Client()
        response = client.get(reverse("login"))
        # SecurityMiddleware deve enviar nosniff
        self.assertEqual(response.headers.get("X-Content-Type-Options"), "nosniff")


class InjectionSecurityTests(TestCase):
    """
    Testes de Segurança: Proteção contra SQL Injection e XSS
    """

    def test_sql_injection_in_login_fails_safely(self):
        client = Client()
        payloads = [
            "' OR '1'='1",
            "admin' --",
            "admin' /*",
            "' OR 1=1 --",
            "'; DROP TABLE auth_user; --",
        ]
        for payload in payloads:
            response = client.post(
                reverse("login"),
                {"username": payload, "senha": "password123"},
                follow=True,
            )
            # Não deve quebrar o servidor e deve redirecionar com mensagem de credenciais inválidas
            self.assertRedirects(response, reverse("login"))
            messages = [m.message for m in get_messages(response.wsgi_request)]
            self.assertIn("Username ou senha invalidos!", messages)

    def test_xss_in_username_is_escaped_in_html(self):
        gerente = User.objects.create_user(
            username="gerente_adm", password="password123"
        )
        assign_role(gerente, "gerente")
        client = Client()
        client.force_login(gerente)

        # Usuário criado com payload XSS no username
        xss_payload = "<script>alert('xss')</script>"
        User.objects.create_user(username=xss_payload, password="password123")

        response = client.get(reverse("permissoes"))
        self.assertEqual(response.status_code, 200)
        # O HTML renderizado pelo Django deve escapar os caracteres < e >
        content = response.content.decode("utf-8")
        self.assertNotIn("<script>alert('xss')</script>", content)
        self.assertIn("&lt;script&gt;alert(&#x27;xss&#x27;)&lt;/script&gt;", content)
