from django.conf import settings
from django.conf.urls.static import static
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

# В разработке картинки отдаёт Django; на сервере их будет отдавать Caddy.
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
