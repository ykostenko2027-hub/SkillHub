from rest_framework import serializers
from .models import Category, Course, Enrollment


class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = ["id", "name"]


class EnrollmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Enrollment
        fields = ["id", "student_name", "student_email", "status", "enrolled_at"]
        read_only_fields = ["id", "status", "enrolled_at"]


class CreateEnrollmentSerializer(serializers.Serializer):
    student_name = serializers.CharField(max_length=100)
    student_email = serializers.EmailField(max_length=320)


class CourseCoverUploadSerializer(serializers.Serializer):
    cover = serializers.FileField()


class CourseListSerializer(serializers.ModelSerializer):
    category_name = serializers.CharField(source="category.name", read_only=True)
    enrollment_count = serializers.IntegerField(read_only=True, default=0)
    cover_image_url = serializers.SerializerMethodField()

    class Meta:
        model = Course
        fields = [
            "id",
            "title",
            "price",
            "category",
            "category_name",
            "enrollment_count",
            "cover_image_url",
            "created_at",
        ]

    def get_cover_image_url(self, obj) -> str | None:
        if obj.cover_image_path:
            return f"/api/courses/{obj.id}/cover/"
        return None


class CourseDetailSerializer(serializers.ModelSerializer):
    category_name = serializers.CharField(source="category.name", read_only=True)
    enrollments = EnrollmentSerializer(many=True, read_only=True)
    cover_image_url = serializers.SerializerMethodField()

    class Meta:
        model = Course
        fields = [
            "id",
            "title",
            "description",
            "price",
            "category",
            "category_name",
            "cover_image_url",
            "created_at",
            "enrollments",
        ]

    def get_cover_image_url(self, obj) -> str | None:
        if obj.cover_image_path:
            return f"/api/courses/{obj.id}/cover/"
        return None
