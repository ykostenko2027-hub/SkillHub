from .repositories import CategoryRepository, CourseRepository, EnrollmentRepository


class CategoryService:
    @staticmethod
    def list_categories():
        return CategoryRepository.get_all()


class CourseService:
    @staticmethod
    def list_courses():
        return CourseRepository.get_all()

    @staticmethod
    def get_course(course_id):
        return CourseRepository.get_by_id(course_id)


class EnrollmentService:
    @staticmethod
    def register_student(course_id, student_name, student_email):
        course = CourseRepository.get_by_id(course_id)
        if not course:
            raise ValueError(f"Курс з ID {course_id} не знайдено.")
        return EnrollmentRepository.create(course, student_name, student_email)
