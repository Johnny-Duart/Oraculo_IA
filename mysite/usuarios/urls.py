from django.urls import path

from . import views

urlpatterns = [
    path("cadastro/", views.cadastro, name="cadastro"),
    path("login/", views.login, name="login"),
    path("permissoes/", views.permissoes, name="permissoes"),
    path(
        "tornar_gerente/<int:id>", views.tornar_gerente, name="tornar_gerente"
    ),
    path(
        "remover-gerente/<int:user_id>/",
        views.remover_gerente,
        name="remover_gerente",
    ),
]
