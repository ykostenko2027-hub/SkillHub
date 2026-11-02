import bcrypt
from .background_jobs import (
    BackgroundJobStatus,
    background_task_queue,
    confirmation_sender,
    job_status_store,
)
from .exceptions import (
    ConflictException,
    InvalidCredentialsException,
    NotFoundException,
    ValidationException,
)
from .models import UserRole
from .repositories import CourseRepository, EnrollmentRepository, UserRepository
from .storage import LocalCoverImageStorage

BCRYPT_WORK_FACTOR = 12
DUMMY_PASSWORD_HASH = bcrypt.hashpw(
    b"DummyPassword1",
    bcrypt.gensalt(rounds=BCRYPT_WORK_FACTOR),
)


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
        enrollment = EnrollmentRepository.create(course, student_name, email)
        job_id = job_status_store.create_job()
        status_store = job_status_store
        sender = confirmation_sender
        background_task_queue.enqueue(
            lambda stopping_event: EnrollmentService.process_confirmation_job(
                job_id,
                email,
                status_store,
                sender,
                stopping_event,
            )
        )
        return enrollment, job_id

    @staticmethod
    def process_confirmation_job(job_id, attendee_email, status_store, sender, stopping_event):
        status_store.set_status(job_id, BackgroundJobStatus.PROCESSING)
        try:
            if stopping_event and stopping_event.is_set():
                status_store.set_status(job_id, BackgroundJobStatus.CANCELLED)
                return
            sender.send(attendee_email)
            status_store.set_status(job_id, BackgroundJobStatus.DONE)
        except Exception:
            status_store.set_status(job_id, BackgroundJobStatus.FAILED)
            raise


class AuthService:
    @staticmethod
    def register(email, password, first_name, last_name, display_name=None):
        normalized_email = email.strip().lower()
        if UserRepository.get_by_email(normalized_email) is not None:
            raise ConflictException("An account with this email already exists.")

        password_hash = bcrypt.hashpw(
            password.encode("utf-8"),
            bcrypt.gensalt(rounds=BCRYPT_WORK_FACTOR),
        ).decode("utf-8")

        user = UserRepository.create_user(
            email=normalized_email,
            first_name=first_name,
            last_name=last_name,
            display_name=display_name,
            password_hash=password_hash,
            role=UserRole.ATTENDEE,
        )
        return AuthService.to_dto(user, roles=[UserRole.ATTENDEE])

    @staticmethod
    def login(email, password):
        normalized_email = email.strip().lower()
        user = UserRepository.get_by_email(normalized_email)
        target_hash = user.password_hash.encode("utf-8") if user is not None else DUMMY_PASSWORD_HASH
        password_matches = bcrypt.checkpw(password.encode("utf-8"), target_hash)

        if user is None or not password_matches:
            raise InvalidCredentialsException("Invalid email or password.")

        roles = [r.role for r in user.roles.all()]
        return AuthService.to_dto(user, roles=roles)

    @staticmethod
    def to_dto(user, roles=None):
        if roles is None:
            roles = [r.role for r in user.roles.all()]
        display_name = user.display_name if user.display_name else f"{user.first_name} {user.last_name}"
        return {
            "id": str(user.id),
            "email": user.email,
            "firstName": user.first_name,
            "lastName": user.last_name,
            "displayName": display_name,
            "roles": roles,
        }
