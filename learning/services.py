from rest_framework.exceptions import NotFound, ValidationError
from .repositories import CourseRepository, EnrollmentRepository


class CourseService:
    @staticmethod
    def get_courses():
        return CourseRepository.get_all()

    @staticmethod
    def get_course_or_404(pk):
        course = CourseRepository.get_by_id(pk)
        if not course:
            raise NotFound("Курс не знайдено.")
        return course


class EnrollmentService:
    @staticmethod
    def get_course_enrollments(course_id):
        CourseService.get_course_or_404(course_id)
        return EnrollmentRepository.get_for_course(course_id)

    @staticmethod
    def register_student(course_id, student_name, student_email):
        course = CourseService.get_course_or_404(course_id)
        if not student_name or not student_email:
            raise ValidationError("Ім'я та email студента є обов'язковими.")
        return EnrollmentRepository.create(course, student_name, student_email)
