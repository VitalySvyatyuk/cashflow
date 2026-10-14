from django.contrib.auth import authenticate, login, logout
from django.views.decorators.csrf import ensure_csrf_cookie
from rest_framework import serializers
from rest_framework.decorators import api_view, permission_classes
from rest_framework.exceptions import AuthenticationFailed
from rest_framework.permissions import AllowAny
from rest_framework.response import Response


class LoginSerializer(serializers.Serializer):
    username = serializers.CharField()
    password = serializers.CharField()


def _user_data(user):
    if not user.is_authenticated:
        return {"user": None}
    return {"user": {"username": user.username, "is_host": user.is_superuser}}


@ensure_csrf_cookie
@api_view(["GET"])
@permission_classes([AllowAny])
def session(request):
    """Текущий пользователь; заодно выставляет cookie csrftoken для SPA."""
    return Response(_user_data(request.user))


@api_view(["POST"])
@permission_classes([AllowAny])
def login_view(request):
    data = LoginSerializer(data=request.data)
    data.is_valid(raise_exception=True)
    user = authenticate(request, **data.validated_data)
    if user is None:
        raise AuthenticationFailed("Неверный логин или пароль.")
    login(request, user)
    return Response(_user_data(user))


@api_view(["POST"])
@permission_classes([AllowAny])
def logout_view(request):
    logout(request)
    return Response(_user_data(request.user))
