from django.urls import path

from core import auth_views
from core.views import health

urlpatterns = [
    path("health/", health, name="health"),
    path("auth/session/", auth_views.session, name="auth-session"),
    path("auth/login/", auth_views.login_view, name="auth-login"),
    path("auth/logout/", auth_views.logout_view, name="auth-logout"),
]
