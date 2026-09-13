from .models import Category, Course, Enrollment


class CategoryRepository:
    @staticmethod
    def get_all():
        return Category.objects.all()

    @staticmethod
    def get_by_id(category_id):
        return Category.objects.filter(id=category_id).first()

    @staticmethod
    def create(name):
        return Category.objects.create(name=name)


class CourseRepository:
    @staticmethod
    def get_all():
        return Course.objects.select_related("category").all()

    @staticmethod
    def get_by_id(course_id):
        return Course.objects.select_related("category").filter(id=course_id).first()

    @staticmethod
    def create(title, category, description="", price=0.0):
        return Course.objects.create(
            title=title,
            category=category,
            description=description,
            price=price,
        )


class EnrollmentRepository:
    @staticmethod
    def get_by_course(course_id):
        return Enrollment.objects.filter(course_id=course_id)

    @staticmethod
    def create(course, student_name, student_email):
        return Enrollment.objects.create(
            course=course,
            student_name=student_name,
            student_email=student_email,
        )
