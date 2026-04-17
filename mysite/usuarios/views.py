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


def permissoes(request):
    if not request.user.is_superuser:
        raise Http404()
    users = User.objects.filter(is_superuser=False)
    return render(request, "permissoes.html", {"users": users})


from rolepermissions.roles import assign_role


@login_required
def tornar_gerente(request, id):
    user = User.objects.get(id=id)
    assign_role(user, "gerente")
    return redirect("permissoes")


@login_required
def remover_gerente(request, user_id):
    user = User.objects.get(id=user_id)
    grupo = Group.objects.get(name="gerente")

    user.groups.remove(grupo)

    return redirect("permissoes")
