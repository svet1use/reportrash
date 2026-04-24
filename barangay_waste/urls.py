from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from waste_management import views
from waste_management.views import migrate_database 

urlpatterns = [
    path('create-admin/', create_admin, name='create_admin'),  # Add this line

    path('migrate/', migrate_database, name='migrate'),

    path('admin/', admin.site.urls),
    path('', include('waste_management.urls')),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
