from django.contrib import admin
from django.urls import path, include, re_path
from django.conf import settings
from django.views.static import serve

admin.site.site_header = "Ronin Cyber Forge - Administração"
admin.site.site_title = "Ronin Cyber Forge"

urlpatterns = [
    path('admin/', admin.site.urls),
    path('login/', include('login.urls')),
    path('', include('app.urls')),
    # Uploads (fotos dos produtos/serviços) também em produção
    re_path(r'^media/(?P<path>.*)$', serve, {'document_root': settings.MEDIA_ROOT}),
]
