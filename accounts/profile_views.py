from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.contrib.admin.views.decorators import staff_member_required
from accounts.models import Faculty
from logs.models import FacultyActionLog
from django.contrib.auth.models import User


@login_required
def faculty_profile_edit(request):
    """Allow faculty to edit their profile"""
    try:
        faculty = request.user.faculty_profile
    except Faculty.DoesNotExist:
        messages.error(request, "You do not have a faculty profile.")
        return redirect("accounts:dashboard")
    
    if request.method == "POST":
        # Fields faculty can edit
        phone_number = request.POST.get("phone_number", "").strip()
        cabin_block = request.POST.get("cabin_block", "").strip()
        cabin_room = request.POST.get("cabin_room", "").strip()
        
        # Track changes
        changes = []
        if faculty.phone_number != phone_number:
            changes.append(f"Phone: {faculty.phone_number} → {phone_number}")
            faculty.phone_number = phone_number
        
        if faculty.cabin_block != cabin_block:
            changes.append(f"Cabin Block: {faculty.cabin_block} → {cabin_block}")
            faculty.cabin_block = cabin_block
        
        if faculty.cabin_room != cabin_room:
            changes.append(f"Cabin Room: {faculty.cabin_room} → {cabin_room}")
            faculty.cabin_room = cabin_room
        
        if changes:
            faculty.save()
            
            # Log the action
            FacultyActionLog.objects.create(
                faculty=faculty,
                action_type="PROFILE_UPDATE",
                description="; ".join(changes)
            )
            
            messages.success(request, "Profile updated successfully.")
        else:
            messages.info(request, "No changes detected.")
        
        return redirect("accounts:faculty_profile_edit")
    
    return render(request, "accounts/faculty_profile_edit.html", {"faculty": faculty})


@staff_member_required
def faculty_action_logs(request):
    """Admin view to see all faculty action logs"""
    faculty_filter = request.GET.get("faculty", "")
    
    logs = FacultyActionLog.objects.select_related("faculty__user", "faculty__department").order_by("-created_at")
    
    if faculty_filter:
        logs = logs.filter(faculty__employee_id__icontains=faculty_filter) | logs.filter(faculty__user__username__icontains=faculty_filter) | logs.filter(faculty__user__first_name__icontains=faculty_filter) | logs.filter(faculty__user__last_name__icontains=faculty_filter)
    
    # Get all faculty for filter dropdown
    all_faculty = Faculty.objects.select_related("user").filter(is_active=True).order_by("user__first_name", "user__last_name")
    
    return render(request, "accounts/faculty_action_logs.html", {
        "logs": logs[:200],  # Limit to recent 200
        "all_faculty": all_faculty,
        "faculty_filter": faculty_filter
    })


@staff_member_required
def faculty_detail_admin(request, pk):
    """Admin view to see detailed faculty information and their logs"""
    faculty = get_object_or_404(Faculty.objects.select_related("user", "department"), pk=pk)
    logs = FacultyActionLog.objects.filter(faculty=faculty).order_by("-created_at")[:50]
    
    # Get invigilation statistics
    from exams.models import InvigilationAssignment
    total_assignments = InvigilationAssignment.objects.filter(faculty=faculty).count()
    confirmed = InvigilationAssignment.objects.filter(faculty=faculty, status=InvigilationAssignment.CONFIRMED).count()
    declined = InvigilationAssignment.objects.filter(faculty=faculty, status=InvigilationAssignment.DECLINED).count()
    pending = InvigilationAssignment.objects.filter(faculty=faculty, status=InvigilationAssignment.PENDING_CONFIRMATION).count()
    
    return render(request, "accounts/faculty_detail_admin.html", {
        "faculty": faculty,
        "logs": logs,
        "stats": {
            "total": total_assignments,
            "confirmed": confirmed,
            "declined": declined,
            "pending": pending
        }
    })
