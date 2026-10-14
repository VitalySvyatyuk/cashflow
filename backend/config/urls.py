from django.contrib import admin
from django.urls import include, path

admin.site.site_header = "Cashflow — администрирование"
admin.site.site_title = "Cashflow"
admin.site.index_title = "Управление игрой"

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/", include("core.urls")),
    path("api/", include("game.urls")),
]
