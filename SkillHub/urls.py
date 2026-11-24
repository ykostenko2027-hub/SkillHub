from django.conf import settings
from django.contrib import admin
from django.urls import include, path, re_path
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView
from learning.views import auth_login, auth_register, health_check, job_status

from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
)

urlpatterns = [
    path("admin/", admin.site.urls),
    path("health/", health_check, name="health-check"),
    re_path(r"^auth/register/?$", auth_register, name="root-auth-register"),
    re_path(r"^auth/login/?$", auth_login, name="root-auth-login"),
    re_path(r"^jobs/(?P<job_id>[^/]+)/?$", job_status, name="root-job-status"),
    path("api/", include("learning.urls")),
    path("api/schema/", SpectacularAPIView.as_view(), name="schema"),

    path('api/token/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('api/token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
]

if settings.DEBUG or getattr(settings, "ENVIRONMENT", "development") != "production":
    urlpatterns += [
        path("swagger/v1/swagger.json", SpectacularAPIView.as_view(), name="swagger-json"),
        path("swagger/", SpectacularSwaggerView.as_view(url_name="schema"), name="swagger-ui"),
    ]
