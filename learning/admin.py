from django.contrib import admin
from .models import Category, Course, Enrollment

admin.site.register(Category)
admin.site.register(Course)
admin.site.register(Enrollment)
