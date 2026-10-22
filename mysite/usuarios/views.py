from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import Group, User
from django.contrib.messages import constants
from django.http import Http404, HttpResponse
from django.shortcuts import redirect, render


def cadastro(request):
    if request.method == "GET":
        return render(request, "cadastro.html")
    elif request.method == "POST":
        username = request.POST.get("username")
        senha = request.POST.get("senha")
        confirmar_senha = request.POST.get("confirmar_senha")

        if senha != confirmar_senha:
            messages.add_message(
                request,
                constants.ERROR,
                "As senhas sao diferentes",
            )
            return redirect("cadastro")

        if len(senha) < 6:
            messages.add_message(
                request,
                constants.ERROR,
                "senha deve conter pelo menos 6 caracteres",
            )
            return redirect("cadastro")

        users = User.objects.filter(username=username)
        if users.exists():
            messages.add_message(
                request,
                constants.ERROR,
                "Ja existe um usuario com esse username",
            )
            return redirect("cadastro")

        User.objects.create_user(username=username, password=senha)

        return redirect("login")


from django.contrib import auth
from django.contrib.auth import authenticate


def login(request):
    if request.method == "GET":
        return render(request, "login.html")
    elif request.method == "POST":
        username = request.POST.get("username")
        senha = request.POST.get("senha")

        user = authenticate(request, username=username, password=senha)

        if user:
            auth.login(request, user)
            return redirect("chat")
        messages.add_message(
            request, constants.ERROR, "Username ou senha invalidos!"
        )
        return redirect("login")


from rolepermissions.checkers import has_role
from rolepermissions.roles import assign_role


@login_required
def permissoes(request):
    if not request.user.is_superuser and not has_role(request.user, "gerente"):
        raise Http404()
    users = User.objects.filter(is_superuser=False).exclude(id=request.user.id)
    return render(request, "permissoes.html", {"users": users})


@login_required
def tornar_gerente(request, id):
    if not request.user.is_superuser and not has_role(request.user, "gerente"):
        raise Http404()
    user = User.objects.get(id=id)
    assign_role(user, "gerente")
    messages.add_message(
        request,
        constants.SUCCESS,
        f"Permissão de Gerente concedida a '{user.username}'.",
    )
    return redirect("permissoes")


@login_required
def remover_gerente(request, user_id):
    if not request.user.is_superuser and not has_role(request.user, "gerente"):
        raise Http404()
    user = User.objects.get(id=user_id)
    try:
        grupo = Group.objects.get(name="gerente")
        user.groups.remove(grupo)
        messages.add_message(
            request,
            constants.SUCCESS,
            f"Permissão de Gerente removida de '{user.username}'.",
        )
    except Group.DoesNotExist:
        pass

    return redirect("permissoes")


@login_required
def excluir_usuario(request, user_id):
    if not request.user.is_superuser and not has_role(request.user, "gerente"):
        raise Http404()

    if request.user.id == user_id:
        messages.add_message(
            request,
            constants.ERROR,
            "Você não pode excluir sua própria conta!",
        )
        return redirect("permissoes")

    try:
        user_to_delete = User.objects.get(id=user_id)
        if user_to_delete.is_superuser:
            messages.add_message(
                request,
                constants.ERROR,
                "Não é permitido excluir um superusuário!",
            )
            return redirect("permissoes")

        nome = user_to_delete.username
        user_to_delete.delete()
        messages.add_message(
            request,
            constants.SUCCESS,
            f"Funcionário '{nome}' foi apagado do banco de dados com sucesso!",
        )
    except User.DoesNotExist:
        messages.add_message(
            request, constants.ERROR, "Funcionário não encontrado."
        )

    return redirect("permissoes")


from django.contrib.auth import logout as auth_logout


def logout_view(request):

    auth_logout(request)
    return redirect("login")
