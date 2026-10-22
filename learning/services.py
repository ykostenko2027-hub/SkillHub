from .exceptions import ConflictException, NotFoundException, ValidationException
from .repositories import CourseRepository, EnrollmentRepository
from .storage import LocalCoverImageStorage


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

    @staticmethod
    def upload_cover(pk, file):
        course = CourseService.get_course_or_404(pk)
        previous_cover = course.cover_image_path
        new_cover = LocalCoverImageStorage.save(file)
        try:
            CourseRepository.update_cover(course, new_cover)
        except Exception:
            LocalCoverImageStorage.delete(new_cover)
            raise
        if previous_cover:
            LocalCoverImageStorage.delete(previous_cover)
        return course

    @staticmethod
    def get_cover(pk):
        course = CourseService.get_course_or_404(pk)
        if not course.cover_image_path:
            raise NotFoundException(f"Course with id '{pk}' does not have a cover image.")
        path = LocalCoverImageStorage.get_path(course.cover_image_path)
        if not path:
            raise NotFoundException(f"The cover image for course with id '{pk}' is unavailable.")
        content_type = "image/png" if path.endswith(".png") else "image/jpeg"
        return path, content_type

    @staticmethod
    def delete_cover(pk):
        course = CourseService.get_course_or_404(pk)
        if course.cover_image_path:
            LocalCoverImageStorage.delete(course.cover_image_path)
            CourseRepository.update_cover(course, None)

    @staticmethod
    def delete_course(course):
        if course.cover_image_path:
            LocalCoverImageStorage.delete(course.cover_image_path)
        CourseRepository.delete(course)


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
