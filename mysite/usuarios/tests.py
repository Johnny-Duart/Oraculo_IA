from django.contrib.auth.models import Group, User
from django.contrib.messages import get_messages
from django.test import Client, TestCase
from django.urls import reverse
from rolepermissions.roles import assign_role, clear_roles, get_user_roles


class CadastroViewTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.url = reverse("cadastro")

    def test_cadastro_get_renders_template(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "cadastro.html")

    def test_cadastro_password_mismatch(self):
        response = self.client.post(
            self.url,
            {
                "username": "novousuario",
                "senha": "password123",
                "confirmar_senha": "password999",
            },
            follow=True,
        )
        self.assertRedirects(response, self.url)
        self.assertFalse(User.objects.filter(username="novousuario").exists())
        messages = [m.message for m in get_messages(response.wsgi_request)]
        self.assertIn("As senhas sao diferentes", messages)

    def test_cadastro_short_password(self):
        response = self.client.post(
            self.url,
            {
                "username": "novousuario",
                "senha": "123",
                "confirmar_senha": "123",
            },
            follow=True,
        )
        self.assertRedirects(response, self.url)
        self.assertFalse(User.objects.filter(username="novousuario").exists())
        messages = [m.message for m in get_messages(response.wsgi_request)]
        self.assertIn("senha deve conter pelo menos 6 caracteres", messages)

    def test_cadastro_existing_username(self):
        User.objects.create_user(username="existente", password="password123")
        response = self.client.post(
            self.url,
            {
                "username": "existente",
                "senha": "password123",
                "confirmar_senha": "password123",
            },
            follow=True,
        )
        self.assertRedirects(response, self.url)
        messages = [m.message for m in get_messages(response.wsgi_request)]
        self.assertIn("Ja existe um usuario com esse username", messages)

    def test_cadastro_success(self):
        response = self.client.post(
            self.url,
            {
                "username": "novousuario",
                "senha": "password123",
                "confirmar_senha": "password123",
            },
        )
        self.assertRedirects(response, reverse("login"))
        self.assertTrue(User.objects.filter(username="novousuario").exists())


class LoginLogoutViewTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.login_url = reverse("login")
        self.logout_url = reverse("logout")
        self.user = User.objects.create_user(
            username="testuser", password="password123"
        )

    def test_login_get_renders_template(self):
        response = self.client.get(self.login_url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "login.html")

    def test_login_invalid_credentials(self):
        response = self.client.post(
            self.login_url,
            {"username": "testuser", "senha": "wrongpassword"},
            follow=True,
        )
        self.assertRedirects(response, self.login_url)
        messages = [m.message for m in get_messages(response.wsgi_request)]
        self.assertIn("Username ou senha invalidos!", messages)

    def test_login_valid_credentials(self):
        response = self.client.post(
            self.login_url,
            {"username": "testuser", "senha": "password123"},
        )
        self.assertRedirects(response, reverse("chat"))

    def test_logout(self):
        self.client.login(username="testuser", password="password123")
        response = self.client.get(self.logout_url)
        self.assertRedirects(response, reverse("login"))


class PermissoesViewTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.permissoes_url = reverse("permissoes")
        self.superuser = User.objects.create_superuser(
            username="adminuser", password="adminpassword123", email="admin@test.com"
        )
        self.funcionario = User.objects.create_user(
            username="funcionario1", password="password123"
        )
        self.gerente_user = User.objects.create_user(
            username="gerente1", password="password123"
        )
        assign_role(self.gerente_user, "gerente")

    def test_permissoes_anonymous_redirects(self):
        response = self.client.get(self.permissoes_url)
        self.assertEqual(response.status_code, 302)

    def test_permissoes_standard_user_forbidden(self):
        self.client.login(username="funcionario1", password="password123")
        response = self.client.get(self.permissoes_url)
        self.assertEqual(response.status_code, 404)

    def test_permissoes_superuser_access(self):
        self.client.login(username="adminuser", password="adminpassword123")
        response = self.client.get(self.permissoes_url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "permissoes.html")
        self.assertIn("funcionario1", [u.username for u in response.context["users"]])

    def test_permissoes_gerente_access(self):
        self.client.login(username="gerente1", password="password123")
        response = self.client.get(self.permissoes_url)
        self.assertEqual(response.status_code, 200)

    def test_tornar_gerente(self):
        self.client.login(username="adminuser", password="adminpassword123")
        url = reverse("tornar_gerente", args=[self.funcionario.id])
        response = self.client.get(url)
        self.assertRedirects(response, self.permissoes_url)
        roles = [r.get_name() for r in get_user_roles(self.funcionario)]
        self.assertIn("gerente", roles)

    def test_remover_gerente(self):
        self.client.login(username="adminuser", password="adminpassword123")
        url = reverse("remover_gerente", args=[self.gerente_user.id])
        response = self.client.get(url)
        self.assertRedirects(response, self.permissoes_url)
        self.assertFalse(
            self.gerente_user.groups.filter(name="gerente").exists()
        )

    def test_excluir_usuario_success(self):
        self.client.login(username="adminuser", password="adminpassword123")
        url = reverse("excluir_usuario", args=[self.funcionario.id])
        response = self.client.get(url)
        self.assertRedirects(response, self.permissoes_url)
        self.assertFalse(User.objects.filter(id=self.funcionario.id).exists())

    def test_excluir_usuario_cannot_delete_self(self):
        self.client.login(username="gerente1", password="password123")
        url = reverse("excluir_usuario", args=[self.gerente_user.id])
        response = self.client.get(url, follow=True)
        self.assertRedirects(response, self.permissoes_url)
        self.assertTrue(User.objects.filter(id=self.gerente_user.id).exists())
        messages = [m.message for m in get_messages(response.wsgi_request)]
        self.assertIn("Você não pode excluir sua própria conta!", messages)

    def test_excluir_usuario_cannot_delete_superuser(self):
        self.client.login(username="gerente1", password="password123")
        url = reverse("excluir_usuario", args=[self.superuser.id])
        response = self.client.get(url, follow=True)
        self.assertRedirects(response, self.permissoes_url)
        self.assertTrue(User.objects.filter(id=self.superuser.id).exists())
        messages = [m.message for m in get_messages(response.wsgi_request)]
        self.assertIn("Não é permitido excluir um superusuário!", messages)
