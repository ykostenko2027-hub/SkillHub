from django.db import connection, reset_queries
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import filters, status, viewsets
from rest_framework.decorators import action, api_view
from rest_framework.response import Response

from .models import Category, Course, Enrollment
from .pagination import CoursePagination
from .serializers import (
    CategorySerializer,
    CourseDetailSerializer,
    CourseListSerializer,
    CreateEnrollmentSerializer,
    EnrollmentSerializer,
)
from .services import CourseService, EnrollmentService


@api_view(["GET"])
def health_check(request):
    return Response({"status": "ok"})


class CategoryViewSet(viewsets.ModelViewSet):
    queryset = Category.objects.all()
    serializer_class = CategorySerializer


class CourseViewSet(viewsets.ModelViewSet):
    pagination_class = CoursePagination
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ["category"]
    search_fields = ["title", "description"]
    ordering_fields = ["created_at", "title", "price"]
    ordering = ["created_at", "id"]

    def get_queryset(self):
        return CourseService.get_courses()

    def get_serializer_class(self):
        if self.action == "list":
            return CourseListSerializer
        return CourseDetailSerializer

    @action(detail=True, methods=["get", "post"])
    def enrollments(self, request, pk=None):
        if request.method == "POST":
            serializer = CreateEnrollmentSerializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            enrollment = EnrollmentService.register_student(
                course_id=pk,
                student_name=serializer.validated_data["student_name"],
                student_email=serializer.validated_data["student_email"],
            )
            return Response(EnrollmentSerializer(enrollment).data, status=status.HTTP_201_CREATED)

        enrollments = EnrollmentService.get_course_enrollments(pk)
        return Response(EnrollmentSerializer(enrollments, many=True).data)

    @action(detail=False, methods=["get"], url_path="n1-demo")
    def n1_demo(self, request):
        old_debug = connection.force_debug_cursor
        connection.force_debug_cursor = True
        try:
            reset_queries()
            courses = list(Course.objects.all())
            for c in courses:
                _ = Enrollment.objects.filter(course=c).count()
            unoptimized_queries = len(connection.queries)

            reset_queries()
            _ = list(CourseService.get_courses())
            optimized_queries = len(connection.queries)

            return Response({
                "n_plus_one_naive_queries": unoptimized_queries,
                "optimized_queries": optimized_queries,
                "fixed": optimized_queries < unoptimized_queries or len(courses) <= 1,
            })
        finally:
            connection.force_debug_cursor = old_debug
