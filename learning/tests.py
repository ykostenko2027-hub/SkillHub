from django.test import TestCase
from rest_framework import status
from rest_framework.test import APIClient
from .models import Category, Course, Enrollment


class ErrorHandlingAndApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.category = Category.objects.create(name="IT")
        self.course = Course.objects.create(
            title="Python",
            category=self.category,
            price=100.0,
        )

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
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_swagger_json_available(self):
        response = self.client.get("/swagger/v1/swagger.json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
