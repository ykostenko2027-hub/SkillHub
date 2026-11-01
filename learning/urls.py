from django.urls import include, path, re_path
from rest_framework.routers import DefaultRouter
from .views import CategoryViewSet, CourseViewSet, job_status

router = DefaultRouter()
router.register(r"categories", CategoryViewSet)
router.register(r"courses", CourseViewSet, basename="course")

urlpatterns = [
    re_path(r"^jobs/(?P<job_id>[^/]+)/?$", job_status, name="api-job-status"),
    path("", include(router.urls)),
]
