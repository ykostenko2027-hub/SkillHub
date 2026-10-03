from django.contrib import admin
from django.urls import include, path
from learning.views import health_check

urlpatterns = [
    path("admin/", admin.site.urls),
    path("health/", health_check, name="health-check"),
    path("api/", include("learning.urls")),
]
