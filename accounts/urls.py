from django.urls import path
from django.contrib.auth import views as auth_views

from . import views
from . import profile_views

app_name = "accounts"

urlpatterns = [
    path("login/", views.PlatformLoginView.as_view(), name="login"),
    path("logout/", auth_views.LogoutView.as_view(), name="logout"),
    path("dashboard/", views.dashboard_router, name="dashboard"),
    path("faculty/create/", views.create_faculty, name="create_faculty"),
    path("faculty/create-batch/", views.create_faculty_batch, name="create_faculty_batch"),
    path("faculty/list/", views.faculty_list, name="faculty_list"),
    path("faculty/profile/edit/", profile_views.faculty_profile_edit, name="faculty_profile_edit"),
    path("faculty/<int:pk>/detail/", profile_views.faculty_detail_admin, name="faculty_detail_admin"),
    path("faculty/action-logs/", profile_views.faculty_action_logs, name="faculty_action_logs"),
    path("forgot-password/", views.forgot_password, name="forgot_password"),
    path("reset-password-with-otp/", views.reset_password_with_otp, name="reset_password_with_otp"),
    path("verify-otp/", views.verify_otp, name="verify_otp"),
    path("first-login-password/", views.first_login_password_change, name="first_login_password_change"),
]
