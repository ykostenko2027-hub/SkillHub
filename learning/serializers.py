from rest_framework import serializers
from .models import Category, Course, Enrollment


def validate_ascii_password(value):
    if len(value) < 8 or len(value) > 72:
        raise serializers.ValidationError("Password must be between 8 and 72 characters.")
    for ch in value:
        is_upper = "A" <= ch <= "Z"
        is_lower = "a" <= ch <= "z"
        is_digit = "0" <= ch <= "9"
        if not (is_upper or is_lower or is_digit):
            raise serializers.ValidationError("Password may contain only Latin letters (A-Z, a-z) and digits (0-9).")
    if not any("A" <= ch <= "Z" for ch in value):
        raise serializers.ValidationError("Password must contain at least one uppercase letter (A-Z).")
    if not any("a" <= ch <= "z" for ch in value):
        raise serializers.ValidationError("Password must contain at least one lowercase letter (a-z).")
    if not any("0" <= ch <= "9" for ch in value):
        raise serializers.ValidationError("Password must contain at least one digit (0-9).")
    return value


class RegisterSerializer(serializers.Serializer):
    email = serializers.EmailField(max_length=320)
    password = serializers.CharField(
        min_length=8,
        max_length=72,
        trim_whitespace=False,
        write_only=True,
        validators=[validate_ascii_password],
    )
    firstName = serializers.CharField(required=False, allow_blank=True, trim_whitespace=False)
    first_name = serializers.CharField(required=False, allow_blank=True, trim_whitespace=False, write_only=True)
    lastName = serializers.CharField(required=False, allow_blank=True, trim_whitespace=False)
    last_name = serializers.CharField(required=False, allow_blank=True, trim_whitespace=False, write_only=True)
    displayName = serializers.CharField(
        required=False,
        allow_null=True,
        allow_blank=True,
        trim_whitespace=False,
    )
    display_name = serializers.CharField(
        required=False,
        allow_null=True,
        allow_blank=True,
        trim_whitespace=False,
        write_only=True,
    )

    def validate_email(self, value):
        normalized = value.strip().lower()
        if not normalized or len(normalized) > 320:
            raise serializers.ValidationError("Email is invalid.")
        return normalized

    def validate(self, attrs):
        raw_first = attrs.get("firstName") if "firstName" in attrs else attrs.get("first_name")
        if raw_first is None or not str(raw_first).strip():
            raise serializers.ValidationError({"firstName": ["First name is required."]})
        first_name = str(raw_first).strip()
        if len(first_name) > 100:
            raise serializers.ValidationError({"firstName": ["First name must not exceed 100 characters."]})

        raw_last = attrs.get("lastName") if "lastName" in attrs else attrs.get("last_name")
        if raw_last is None or not str(raw_last).strip():
            raise serializers.ValidationError({"lastName": ["Last name is required."]})
        last_name = str(raw_last).strip()
        if len(last_name) > 100:
            raise serializers.ValidationError({"lastName": ["Last name must not exceed 100 characters."]})

        has_display = "displayName" in attrs or "display_name" in attrs
        raw_display = attrs.get("displayName") if "displayName" in attrs else attrs.get("display_name")
        display_name = None
        if has_display and raw_display is not None:
            trimmed_display = str(raw_display).strip()
            if not trimmed_display:
                raise serializers.ValidationError({"displayName": ["Display name cannot be blank."]})
            if len(trimmed_display) > 80:
                raise serializers.ValidationError({"displayName": ["Display name must not exceed 80 characters."]})
            display_name = trimmed_display

        attrs["first_name"] = first_name
        attrs["last_name"] = last_name
        attrs["display_name"] = display_name
        return attrs


class LoginSerializer(serializers.Serializer):
    email = serializers.EmailField(max_length=320)
    password = serializers.CharField(
        min_length=8,
        max_length=72,
        trim_whitespace=False,
        write_only=True,
        validators=[validate_ascii_password],
    )

    def validate_email(self, value):
        normalized = value.strip().lower()
        if not normalized or len(normalized) > 320:
            raise serializers.ValidationError("Email is invalid.")
        return normalized


class UserDtoSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    email = serializers.EmailField()
    firstName = serializers.CharField()
    lastName = serializers.CharField()
    displayName = serializers.CharField()
    roles = serializers.ListField(child=serializers.CharField())


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


class CreateRegistrationResponseSerializer(serializers.Serializer):
    registration = EnrollmentSerializer()
    jobId = serializers.UUIDField()


class JobStatusSerializer(serializers.Serializer):
    jobId = serializers.UUIDField()
    status = serializers.CharField()


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
