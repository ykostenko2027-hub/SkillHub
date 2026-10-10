from .exceptions import ConflictException, NotFoundException, ValidationException
from .repositories import CourseRepository, EnrollmentRepository


class CourseService:
    @staticmethod
    def get_courses():
        return CourseRepository.get_all()

    @staticmethod
    def get_course_or_404(pk):
        course = CourseRepository.get_by_id(pk)
        if not course:
            raise NotFoundException(f"Course with id '{pk}' does not exist.")
        return course


class EnrollmentService:
    @staticmethod
    def get_course_enrollments(course_id):
        CourseService.get_course_or_404(course_id)
        return EnrollmentRepository.get_for_course(course_id)

    @staticmethod
    def register_student(course_id, student_name, student_email):
        course = CourseService.get_course_or_404(course_id)
        email = student_email.strip().lower()
        if EnrollmentRepository.exists(course_id, email):
            raise ConflictException("This attendee is already registered for the course.")
        if EnrollmentRepository.count(course_id) >= 10:
            raise ValidationException("The course is at full capacity.")
        return EnrollmentRepository.create(course, student_name, email)
