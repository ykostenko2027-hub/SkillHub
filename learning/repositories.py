from django.db.models import Count
from .models import Course, Enrollment


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
