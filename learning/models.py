from django.db import models


class Category(models.Model):
    name = models.CharField(max_length=100, unique=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name


class Course(models.Model):
    title = models.CharField(max_length=200, db_index=True)
    description = models.TextField(blank=True, default="")
    category = models.ForeignKey(Category, on_delete=models.CASCADE, related_name="courses")
    price = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ["created_at", "id"]

    def __str__(self):
        return self.title


class Enrollment(models.Model):
    STATUS_CHOICES = [
        ("Pending", "Pending"),
        ("Confirmed", "Confirmed"),
        ("Cancelled", "Cancelled"),
    ]

    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name="enrollments")
    student_name = models.CharField(max_length=100)
    student_email = models.EmailField(max_length=320)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="Pending")
    enrolled_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-enrolled_at", "id"]

    def __str__(self):
        return f"{self.student_name} -> {self.course.title}"
