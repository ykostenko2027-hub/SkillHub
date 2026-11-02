import logging
import os
import time
import uuid
from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from rest_framework import status
from rest_framework.test import APIClient
from SkillHub.config import AppOptions
from .background_jobs import (
    BackgroundJobStatus,
    BackgroundTaskQueue,
    InMemoryJobStatusStore,
    confirmation_sender,
    job_status_store,
)
from .models import AppUser, Category, Course, Enrollment, UserRoleAssignment
from .storage import LocalCoverImageStorage


class ConfigurationTests(TestCase):
    def test_environment_defaults(self):
        self.assertEqual(AppOptions.MAX_FILE_SIZE_BY_ENV["development"], 10)
        self.assertEqual(AppOptions.MAX_FILE_SIZE_BY_ENV["staging"], 7)
        self.assertEqual(AppOptions.MAX_FILE_SIZE_BY_ENV["production"], 5)

    def test_validation_fails_on_empty_secret_key(self):
        original = AppOptions.SECRET_KEY
        try:
            AppOptions.SECRET_KEY = ""
            with self.assertRaises(ImproperlyConfigured):
                AppOptions.validate()
        finally:
            AppOptions.SECRET_KEY = original

    def test_validation_fails_on_invalid_file_size(self):
        original = AppOptions.MAX_FILE_SIZE_MB
        try:
            AppOptions.MAX_FILE_SIZE_MB = 0
            with self.assertRaises(ImproperlyConfigured):
                AppOptions.validate()

            AppOptions.MAX_FILE_SIZE_MB = 101
            with self.assertRaises(ImproperlyConfigured):
                AppOptions.validate()
        finally:
            AppOptions.MAX_FILE_SIZE_MB = original

    def test_validation_fails_on_demo_key_in_production(self):
        orig_env = AppOptions.ENVIRONMENT
        orig_key = AppOptions.SECRET_KEY
        try:
            AppOptions.ENVIRONMENT = "production"
            AppOptions.SECRET_KEY = "insecure-demo-key"
            with self.assertRaises(ImproperlyConfigured):
                AppOptions.validate()
        finally:
            AppOptions.ENVIRONMENT = orig_env
            AppOptions.SECRET_KEY = orig_key


class ErrorHandlingAndApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.category = Category.objects.create(name="IT")
        self.course = Course.objects.create(
            title="Python",
            category=self.category,
            price=100.0,
        )

    def tearDown(self):
        upload_dir = LocalCoverImageStorage.get_upload_dir()
        if os.path.exists(upload_dir):
            for file_name in os.listdir(upload_dir):
                file_path = os.path.join(upload_dir, file_name)
                try:
                    os.remove(file_path)
                except OSError:
                    pass

    def test_health_check(self):
        response = self.client.get("/health/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data, {"status": "ok"})

    def test_validation_error_returns_400(self):
        response = self.client.post(
            f"/api/courses/{self.course.id}/enrollments/",
            {"student_name": "Ivan"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response["Content-Type"], "application/problem+json")
        self.assertEqual(response.data["status"], 400)
        self.assertEqual(response.data["title"], "Validation error")

    def test_not_found_returns_404(self):
        response = self.client.get("/api/courses/99999/")
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(response["Content-Type"], "application/problem+json")
        self.assertEqual(response.data["status"], 404)
        self.assertEqual(response.data["title"], "Resource not found")
        self.assertIn("99999", response.data["detail"])

    def test_conflict_returns_409(self):
        self.client.post(
            f"/api/courses/{self.course.id}/enrollments/",
            {"student_name": "Ivan", "student_email": "ivan@test.com"},
            format="json",
        )
        response = self.client.post(
            f"/api/courses/{self.course.id}/enrollments/",
            {"student_name": "Ivan", "student_email": "ivan@test.com"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_409_CONFLICT)
        self.assertEqual(response["Content-Type"], "application/problem+json")
        self.assertEqual(response.data["status"], 409)
        self.assertEqual(response.data["title"], "Resource conflict")

    def test_capacity_exceeded_returns_422(self):
        for i in range(10):
            Enrollment.objects.create(
                course=self.course,
                student_name=f"Student {i}",
                student_email=f"student{i}@test.com",
            )
        response = self.client.post(
            f"/api/courses/{self.course.id}/enrollments/",
            {"student_name": "Extra", "student_email": "extra@test.com"},
            format="json",
        )
        self.assertEqual(response.status_code, 422)
        self.assertEqual(response["Content-Type"], "application/problem+json")
        self.assertEqual(response.data["status"], 422)
        self.assertEqual(response.data["title"], "Business rule violation")

    def test_unexpected_error_returns_500(self):
        from unittest.mock import patch
        with patch("learning.services.CourseService.get_courses", side_effect=Exception("DB failure")):
            response = self.client.get("/api/courses/")
            self.assertEqual(response.status_code, status.HTTP_500_INTERNAL_SERVER_ERROR)
            self.assertEqual(response["Content-Type"], "application/problem+json")
            self.assertEqual(response.data["status"], 500)
            self.assertEqual(response.data["title"], "An unexpected error occurred")
            self.assertEqual(response.data["detail"], "The server could not complete the request.")
            self.assertNotIn("DB failure", str(response.data["detail"]))

    def test_n_plus_one_prevention(self):
        for i in range(5):
            c = Course.objects.create(title=f"Course {i}", category=self.category)
            Enrollment.objects.create(course=c, student_name=f"S {i}", student_email=f"s{i}@test.com")
        with self.assertNumQueries(2):
            response = self.client.get("/api/courses/")
            self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_swagger_ui_available(self):
        response = self.client.get("/swagger/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_openapi_schema_available(self):
        response = self.client.get("/api/schema/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_swagger_json_available(self):
        response = self.client.get("/swagger/v1/swagger.json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_upload_cover_success(self):
        file_content = b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR"
        image = SimpleUploadedFile("cover.png", file_content, content_type="image/png")
        response = self.client.post(
            f"/api/courses/{self.course.id}/cover/",
            {"cover": image},
            format="multipart",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["cover_image_url"], f"/api/courses/{self.course.id}/cover/")
        self.course.refresh_from_db()
        self.assertIsNotNone(self.course.cover_image_path)
        self.assertTrue(self.course.cover_image_path.endswith(".png"))
        path = LocalCoverImageStorage.get_path(self.course.cover_image_path)
        self.assertTrue(os.path.exists(path))

    def test_get_cover_success(self):
        file_content = b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR"
        image = SimpleUploadedFile("cover.png", file_content, content_type="image/png")
        self.client.post(
            f"/api/courses/{self.course.id}/cover/",
            {"cover": image},
            format="multipart",
        )
        response = self.client.get(f"/api/courses/{self.course.id}/cover/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response["Content-Type"], "image/png")
        self.assertEqual(b"".join(response.streaming_content), file_content)

    def test_upload_cover_invalid_type_returns_400(self):
        text_file = SimpleUploadedFile("notes.txt", b"plain text", content_type="text/plain")
        response = self.client.post(
            f"/api/courses/{self.course.id}/cover/",
            {"cover": text_file},
            format="multipart",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response["Content-Type"], "application/problem+json")
        self.assertEqual(response.data["title"], "Invalid cover image")
        self.course.refresh_from_db()
        self.assertIsNone(self.course.cover_image_path)

    def test_upload_cover_non_existent_course_returns_404(self):
        file_content = b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR"
        image = SimpleUploadedFile("cover.png", file_content, content_type="image/png")
        response = self.client.post(
            "/api/courses/99999/cover/",
            {"cover": image},
            format="multipart",
        )
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(response["Content-Type"], "application/problem+json")

    def test_delete_cover_success(self):
        file_content = b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR"
        image = SimpleUploadedFile("cover.png", file_content, content_type="image/png")
        self.client.post(
            f"/api/courses/{self.course.id}/cover/",
            {"cover": image},
            format="multipart",
        )
        self.course.refresh_from_db()
        old_path = LocalCoverImageStorage.get_path(self.course.cover_image_path)
        self.assertTrue(os.path.exists(old_path))

        del_response = self.client.delete(f"/api/courses/{self.course.id}/cover/")
        self.assertEqual(del_response.status_code, status.HTTP_204_NO_CONTENT)
        self.course.refresh_from_db()
        self.assertIsNone(self.course.cover_image_path)
        self.assertFalse(os.path.exists(old_path))

        get_response = self.client.get(f"/api/courses/{self.course.id}/cover/")
        self.assertEqual(get_response.status_code, status.HTTP_404_NOT_FOUND)

    def test_replace_cover_deletes_previous_file(self):
        image1 = SimpleUploadedFile("cover1.png", b"\x89PNG\r\n\x1a\n1", content_type="image/png")
        self.client.post(f"/api/courses/{self.course.id}/cover/", {"cover": image1}, format="multipart")
        self.course.refresh_from_db()
        first_path = LocalCoverImageStorage.get_path(self.course.cover_image_path)
        self.assertTrue(os.path.exists(first_path))

        image2 = SimpleUploadedFile("cover2.jpg", b"\xff\xd8\xff2", content_type="image/jpeg")
        self.client.post(f"/api/courses/{self.course.id}/cover/", {"cover": image2}, format="multipart")
        self.course.refresh_from_db()
        second_path = LocalCoverImageStorage.get_path(self.course.cover_image_path)
        self.assertTrue(os.path.exists(second_path))
        self.assertFalse(os.path.exists(first_path))


class BackgroundJobsTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.category = Category.objects.create(name="DevOps")
        self.course = Course.objects.create(
            title="Kubernetes",
            category=self.category,
            price=200.0,
        )
        self.orig_delay = confirmation_sender.delay
        confirmation_sender.delay = 0
        self.bg_logger = logging.getLogger("learning.background_jobs")
        self.orig_disabled = self.bg_logger.disabled
        self.bg_logger.disabled = True

    def tearDown(self):
        self.bg_logger.disabled = self.orig_disabled
        confirmation_sender.delay = self.orig_delay
        job_status_store.clear()

    def test_task_queue_enqueue_dequeue(self):
        queue_instance = BackgroundTaskQueue()
        work_item = lambda token: None
        queue_instance.enqueue(work_item)
        dequeued = queue_instance.dequeue()
        self.assertIs(dequeued, work_item)

    def test_job_status_store_lifecycle(self):
        store = InMemoryJobStatusStore()
        job_id = store.create_job()
        self.assertEqual(store.get_status(job_id), BackgroundJobStatus.PENDING)
        store.set_status(job_id, BackgroundJobStatus.DONE)
        self.assertEqual(store.get_status(job_id), BackgroundJobStatus.DONE)
        random_id = uuid.uuid4()
        self.assertIsNone(store.get_status(random_id))

    def test_create_enrollment_enqueues_background_task_and_finishes_done(self):
        response = self.client.post(
            f"/api/courses/{self.course.id}/enrollments/",
            {"student_name": "Oksana", "student_email": "oksana@example.com"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIn("jobId", response.data)
        self.assertIn("registration", response.data)
        self.assertEqual(response.data["registration"]["student_name"], "Oksana")
        job_id = response.data["jobId"]

        final_status = None
        for _ in range(20):
            status_response = self.client.get(f"/jobs/{job_id}/")
            self.assertEqual(status_response.status_code, status.HTTP_200_OK)
            final_status = status_response.data["status"]
            if final_status == BackgroundJobStatus.DONE:
                break
            time.sleep(0.05)

        self.assertEqual(final_status, BackgroundJobStatus.DONE)

    def test_unknown_job_id_returns_404_problem_details(self):
        non_existent_id = "00000000-0000-0000-0000-000000000001"
        response = self.client.get(f"/jobs/{non_existent_id}/")
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(response["Content-Type"], "application/problem+json")
        self.assertEqual(response.data["status"], 404)
        self.assertEqual(response.data["title"], "Resource not found")
        self.assertIn(non_existent_id, response.data["detail"])

    def test_failed_job_and_worker_resilience(self):
        response_failed = self.client.post(
            f"/api/courses/{self.course.id}/enrollments/",
            {"student_name": "Failing Student", "student_email": "fail@example.com"},
            format="json",
        )
        self.assertEqual(response_failed.status_code, status.HTTP_201_CREATED)
        failed_job_id = response_failed.data["jobId"]

        final_status_failed = None
        for _ in range(20):
            res = self.client.get(f"/jobs/{failed_job_id}/")
            final_status_failed = res.data["status"]
            if final_status_failed == BackgroundJobStatus.FAILED:
                break
            time.sleep(0.05)
        self.assertEqual(final_status_failed, BackgroundJobStatus.FAILED)

        response_ok = self.client.post(
            f"/api/courses/{self.course.id}/enrollments/",
            {"student_name": "Successful Student", "student_email": "success@example.com"},
            format="json",
        )
        self.assertEqual(response_ok.status_code, status.HTTP_201_CREATED)
        ok_job_id = response_ok.data["jobId"]

        final_status_ok = None
        for _ in range(20):
            res = self.client.get(f"/jobs/{ok_job_id}/")
            final_status_ok = res.data["status"]
            if final_status_ok == BackgroundJobStatus.DONE:
                break
            time.sleep(0.05)
        self.assertEqual(final_status_ok, BackgroundJobStatus.DONE)

    def test_in_memory_job_lost_after_store_cleared(self):
        response = self.client.post(
            f"/api/courses/{self.course.id}/enrollments/",
            {"student_name": "Memory Test", "student_email": "memory@example.com"},
            format="json",
        )
        job_id = response.data["jobId"]
        job_status_store.clear()
        res = self.client.get(f"/jobs/{job_id}/")
        self.assertEqual(res.status_code, status.HTTP_404_NOT_FOUND)
        self.assertTrue(Enrollment.objects.filter(student_email="memory@example.com").exists())


class QueryOptimizationAndPaginationTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.category = Category.objects.create(name="Data")
        self.course = Course.objects.create(title="SQL Tuning", category=self.category, price=150.0)

    def test_course_composite_index_defined(self):
        index_names = [idx.name for idx in Course._meta.indexes]
        self.assertIn("ix_course_created_at_id", index_names)

    def test_page_size_over_100_returns_400(self):
        response = self.client.get("/api/courses/?page_size=101")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response["Content-Type"], "application/problem+json")
        self.assertEqual(response.data["status"], 400)


class AuthRegistrationAndLoginTests(TestCase):
    def setUp(self):
        self.client = APIClient()

    def test_register_success_normalizes_email_and_assigns_attendee_role(self):
        response = self.client.post(
            "/auth/register",
            {
                "email": "  Student14@Example.com  ",
                "password": "Password1",
                "firstName": "  Оксана ",
                "lastName": " Коваль  ",
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["email"], "student14@example.com")
        self.assertEqual(response.data["firstName"], "Оксана")
        self.assertEqual(response.data["lastName"], "Коваль")
        self.assertEqual(response.data["displayName"], "Оксана Коваль")
        self.assertEqual(response.data["roles"], ["Attendee"])
        self.assertNotIn("password", response.data)
        self.assertNotIn("passwordHash", response.data)

        user = AppUser.objects.get(email="student14@example.com")
        self.assertTrue(user.password_hash.startswith("$2b$12$"))
        self.assertNotEqual(user.password_hash, "Password1")
        self.assertTrue(UserRoleAssignment.objects.filter(user=user, role="Attendee").exists())

    def test_register_with_custom_display_name(self):
        response = self.client.post(
            "/auth/register",
            {
                "email": "custom@example.com",
                "password": "Password1",
                "firstName": "Оксана",
                "lastName": "Коваль",
                "displayName": "  Oksana K.  ",
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["displayName"], "Oksana K.")

    def test_register_duplicate_email_returns_409(self):
        payload = {
            "email": "student14@example.com",
            "password": "Password1",
            "firstName": "Оксана",
            "lastName": "Коваль",
        }
        self.client.post("/auth/register", payload, format="json")
        response = self.client.post(
            "/auth/register",
            {**payload, "email": "STUDENT14@EXAMPLE.COM"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_409_CONFLICT)
        self.assertEqual(response["Content-Type"], "application/problem+json")
        self.assertEqual(response.data["status"], 409)
        self.assertEqual(response.data["detail"], "An account with this email already exists.")

    def test_login_success_and_invalid_credentials_return_401(self):
        self.client.post(
            "/auth/register",
            {
                "email": "student14@example.com",
                "password": "Password1",
                "firstName": "Оксана",
                "lastName": "Коваль",
            },
            format="json",
        )
        ok_res = self.client.post(
            "/auth/login",
            {"email": "  STUDENT14@example.com ", "password": "Password1"},
            format="json",
        )
        self.assertEqual(ok_res.status_code, status.HTTP_200_OK)
        self.assertEqual(ok_res.data["email"], "student14@example.com")
        self.assertEqual(ok_res.data["roles"], ["Attendee"])

        wrong_pw = self.client.post(
            "/auth/login",
            {"email": "student14@example.com", "password": "Password2"},
            format="json",
        )
        self.assertEqual(wrong_pw.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertEqual(wrong_pw["Content-Type"], "application/problem+json")
        self.assertEqual(wrong_pw.data["title"], "Invalid credentials")
        self.assertEqual(wrong_pw.data["detail"], "Invalid email or password.")

        unknown_user = self.client.post(
            "/auth/login",
            {"email": "nobody@example.com", "password": "Password1"},
            format="json",
        )
        self.assertEqual(unknown_user.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertEqual(unknown_user.data["title"], wrong_pw.data["title"])
        self.assertEqual(unknown_user.data["detail"], wrong_pw.data["detail"])

    def test_invalid_passwords_and_whitespace_names_return_400(self):
        invalid_passwords = [
            "Pass1",
            "password1",
            "PASSWORD1",
            "PasswordOnly",
            "Пароль123",
            "Password 1",
            "Password1!",
        ]
        for pwd in invalid_passwords:
            res = self.client.post(
                "/auth/register",
                {
                    "email": "test@example.com",
                    "password": pwd,
                    "firstName": "Оксана",
                    "lastName": "Коваль",
                },
                format="json",
            )
            self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)

        blank_name_res = self.client.post(
            "/auth/register",
            {
                "email": "test@example.com",
                "password": "Password1",
                "firstName": "   ",
                "lastName": "Коваль",
            },
            format="json",
        )
        self.assertEqual(blank_name_res.status_code, status.HTTP_400_BAD_REQUEST)

    def test_role_injection_in_register_is_ignored(self):
        response = self.client.post(
            "/auth/register",
            {
                "email": "hacker@example.com",
                "password": "Password1",
                "firstName": "Іван",
                "lastName": "Петренко",
                "roles": ["Admin"],
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["roles"], ["Attendee"])
