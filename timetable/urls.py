from django.urls import path

from . import views

app_name = "timetable"

urlpatterns = [
    path("admin/upload/", views.upload_timetable, name="upload_timetable"),
    path("admin/courses/", views.manage_courses, name="manage_courses"),
    path("admin/courses/view/", views.view_courses, name="view_courses"),
    path("admin/courses/add/", views.add_courses_batch, name="add_courses_batch"),
    path("admin/courses/<int:pk>/edit/", views.edit_course, name="edit_course"),
    path("admin/courses/<int:pk>/delete/", views.delete_course, name="delete_course"),
    path("admin/faculty-timetables/", views.admin_view_faculty_timetables, name="admin_view_faculty_timetables"),
    path("admin/faculty-timetables/add/", views.admin_add_faculty_timetable, name="admin_add_faculty_timetable"),
    path("admin/faculty-timetables/<int:faculty_id>/view/", views.admin_view_faculty_timetable, name="admin_view_faculty_timetable"),
    path("faculty/", views.faculty_timetable, name="faculty_timetable"),
    path("faculty/grid/", views.faculty_timetable_grid, name="faculty_timetable_grid"),
    path("faculty/add/", views.add_slot, name="add_slot"),
    path("faculty/slot/<int:pk>/delete/", views.delete_slot, name="delete_slot"),
    path("api/slot/create/", views.api_slot_create, name="api_slot_create"),
    path("api/slot/<int:pk>/update/", views.api_slot_update, name="api_slot_update"),
    path("api/slot/<int:pk>/delete/", views.api_slot_delete, name="api_slot_delete"),
    path("admin/api/slot/create/", views.admin_api_slot_create, name="admin_api_slot_create"),
    path("admin/api/slot/<int:pk>/update/", views.admin_api_slot_update, name="admin_api_slot_update"),
    path("admin/api/slot/<int:pk>/delete/", views.admin_api_slot_delete, name="admin_api_slot_delete"),
]
