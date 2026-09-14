from django.contrib import admin

from .models import FacultyActionLog


@admin.register(FacultyActionLog)
class FacultyActionLogAdmin(admin.ModelAdmin):
    list_display = ("faculty", "action_type", "created_at")
    list_filter = ("action_type", "created_at")
    search_fields = ("faculty__employee_id", "faculty__user__username", "action_type")

