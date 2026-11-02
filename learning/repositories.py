from django.db import IntegrityError, transaction
from django.db.models import Count
from .exceptions import ConflictException
from .models import AppUser, Course, Enrollment, UserRoleAssignment


class CourseRepository:
    @staticmethod
    def get_all():
        return (
            Course.objects.select_related("category")
            .annotate(enrollment_count=Count("enrollments"))
            .order_by("created_at", "id")
        )

    @staticmethod
    def get_by_id(pk):
        return (
            Course.objects.select_related("category")
            .prefetch_related("enrollments")
            .filter(id=pk)
            .first()
        )

    @staticmethod
    def update_cover(course, file_name):
        course.cover_image_path = file_name
        course.save(update_fields=["cover_image_path"])
        return course

    @staticmethod
    def delete(course):
        course.delete()


class EnrollmentRepository:
    @staticmethod
    def get_for_course(course_id):
        return Enrollment.objects.filter(course_id=course_id).order_by("-enrolled_at", "id")

    @staticmethod
    def exists(course_id, student_email):
        return Enrollment.objects.filter(
            course_id=course_id,
            student_email=student_email,
        ).exists()

    @staticmethod
    def count(course_id):
        return Enrollment.objects.filter(course_id=course_id).count()

    @staticmethod
    def create(course, student_name, student_email):
        return Enrollment.objects.create(
            course=course,
            student_name=student_name.strip(),
            student_email=student_email.strip(),
        )


class UserRepository:
    @staticmethod
    def get_by_email(email):
        return (
            AppUser.objects.prefetch_related("roles")
            .filter(email=email)
            .first()
        )

    @staticmethod
    def create_user(email, first_name, last_name, display_name, password_hash, role):
        try:
            with transaction.atomic():
                user = AppUser.objects.create(
                    email=email,
                    first_name=first_name,
                    last_name=last_name,
                    display_name=display_name,
                    password_hash=password_hash,
                )
                UserRoleAssignment.objects.create(user=user, role=role)
                return user
        except IntegrityError:
            raise ConflictException("An account with this email already exists.")
