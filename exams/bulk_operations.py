"""
Bulk operations for exams and assignments
"""
from django.contrib import messages
from django.db import transaction
from django.utils import timezone

from .models import Exam, InvigilationAssignment
from notifications.utils import create_notification, Notification


def bulk_delete_exams(exam_ids, user):
    """
    Delete multiple exams at once
    
    Args:
        exam_ids: List of exam IDs to delete
        user: User performing the operation
    
    Returns:
        tuple: (success_count, error_count, errors)
    """
    success_count = 0
    error_count = 0
    errors = []
    
    try:
        with transaction.atomic():
            exams = Exam.objects.filter(id__in=exam_ids)
            
            for exam in exams:
                try:
                    # Check if exam has assignments
                    assignment_count = InvigilationAssignment.objects.filter(
                        exam_session_hall__exam=exam
                    ).count()
                    
                    if assignment_count > 0:
                        errors.append(f"Exam {exam.course_code} has {assignment_count} assignments. Cannot delete.")
                        error_count += 1
                        continue
                    
                    exam.delete()
                    success_count += 1
                    
                except Exception as e:
                    errors.append(f"Error deleting {exam.course_code}: {str(e)}")
                    error_count += 1
    
    except Exception as e:
        errors.append(f"Transaction error: {str(e)}")
        error_count = len(exam_ids)
        success_count = 0
    
    return success_count, error_count, errors


def bulk_cancel_assignments(assignment_ids, reason, user):
    """
    Cancel multiple assignments at once
    
    Args:
        assignment_ids: List of assignment IDs to cancel
        reason: Reason for cancellation
        user: User performing the operation
    
    Returns:
        tuple: (success_count, error_count, errors)
    """
    success_count = 0
    error_count = 0
    errors = []
    
    try:
        with transaction.atomic():
            assignments = InvigilationAssignment.objects.filter(
                id__in=assignment_ids
            ).select_related('faculty__user', 'exam_session_hall__exam')
            
            for assignment in assignments:
                try:
                    # Only cancel if not already confirmed
                    if assignment.status == InvigilationAssignment.CONFIRMED:
                        errors.append(
                            f"Assignment for {assignment.faculty.user.get_full_name()} "
                            f"is already confirmed. Cannot cancel."
                        )
                        error_count += 1
                        continue
                    
                    assignment.status = InvigilationAssignment.CANCELLED
                    assignment.save(update_fields=['status'])
                    
                    # Create notification
                    exam = assignment.exam_session_hall.exam
                    create_notification(
                        user=assignment.faculty.user,
                        notification_type=Notification.ASSIGNMENT_CANCELLED,
                        title="Assignment Cancelled",
                        message=f"Your assignment for {exam.course_code} on {exam.exam_date} has been cancelled. Reason: {reason}",
                        link="/exams/faculty/dashboard/",
                        priority='HIGH'
                    )
                    
                    success_count += 1
                    
                except Exception as e:
                    errors.append(f"Error cancelling assignment: {str(e)}")
                    error_count += 1
    
    except Exception as e:
        errors.append(f"Transaction error: {str(e)}")
        error_count = len(assignment_ids)
        success_count = 0
    
    return success_count, error_count, errors


def bulk_reassign_duties(assignment_ids, new_faculty_id, user):
    """
    Reassign multiple duties to a different faculty member
    
    Args:
        assignment_ids: List of assignment IDs to reassign
        new_faculty_id: ID of new faculty to assign
        user: User performing the operation
    
    Returns:
        tuple: (success_count, error_count, errors)
    """
    from accounts.models import Faculty
    
    success_count = 0
    error_count = 0
    errors = []
    
    try:
        new_faculty = Faculty.objects.get(id=new_faculty_id)
    except Faculty.DoesNotExist:
        return 0, len(assignment_ids), ["New faculty not found"]
    
    try:
        with transaction.atomic():
            assignments = InvigilationAssignment.objects.filter(
                id__in=assignment_ids
            ).select_related('faculty__user', 'exam_session_hall__exam')
            
            for assignment in assignments:
                try:
                    old_faculty = assignment.faculty
                    exam = assignment.exam_session_hall.exam
                    
                    # Mark old assignment as reassigned
                    assignment.status = InvigilationAssignment.REASSIGNED
                    assignment.save(update_fields=['status'])
                    
                    # Create new assignment
                    new_assignment = InvigilationAssignment.objects.create(
                        exam_session_hall=assignment.exam_session_hall,
                        faculty=new_faculty,
                        status=InvigilationAssignment.PENDING_CONFIRMATION
                    )
                    
                    # Set deadline
                    from datetime import datetime, timedelta
                    exam_start_dt = datetime.combine(exam.exam_date, exam.start_time)
                    deadline = timezone.make_aware(exam_start_dt) - timedelta(hours=1, minutes=30)
                    new_assignment.confirmation_deadline = deadline
                    new_assignment.notification_sent_at = timezone.now()
                    new_assignment.save(update_fields=['confirmation_deadline', 'notification_sent_at'])
                    
                    # Notify old faculty
                    create_notification(
                        user=old_faculty.user,
                        notification_type=Notification.ASSIGNMENT_CANCELLED,
                        title="Assignment Reassigned",
                        message=f"Your assignment for {exam.course_code} on {exam.exam_date} has been reassigned to another faculty member.",
                        link="/exams/faculty/dashboard/",
                        priority='MEDIUM'
                    )
                    
                    # Notify new faculty
                    from notifications.utils import notify_assignment_created
                    notify_assignment_created(new_assignment)
                    
                    # Send email to new faculty
                    from exams.utils import send_invigilation_assignment_email
                    send_invigilation_assignment_email(new_assignment)
                    
                    success_count += 1
                    
                except Exception as e:
                    errors.append(f"Error reassigning assignment: {str(e)}")
                    error_count += 1
    
    except Exception as e:
        errors.append(f"Transaction error: {str(e)}")
        error_count = len(assignment_ids)
        success_count = 0
    
    return success_count, error_count, errors


def bulk_approve_leaves(leave_ids, user):
    """
    Approve multiple leave requests at once
    
    Args:
        leave_ids: List of leave IDs to approve
        user: User performing the operation
    
    Returns:
        tuple: (success_count, error_count, errors)
    """
    from leaves.models import FacultyLeave
    from notifications.utils import notify_leave_status
    
    success_count = 0
    error_count = 0
    errors = []
    
    try:
        with transaction.atomic():
            leaves = FacultyLeave.objects.filter(
                id__in=leave_ids,
                status=FacultyLeave.PENDING
            ).select_related('faculty__user')
            
            for leave in leaves:
                try:
                    leave.status = FacultyLeave.APPROVED
                    leave.save(update_fields=['status'])
                    
                    # Create notification
                    notify_leave_status(leave, 'APPROVED')
                    
                    success_count += 1
                    
                except Exception as e:
                    errors.append(f"Error approving leave: {str(e)}")
                    error_count += 1
    
    except Exception as e:
        errors.append(f"Transaction error: {str(e)}")
        error_count = len(leave_ids)
        success_count = 0
    
    return success_count, error_count, errors


def bulk_reject_leaves(leave_ids, user):
    """
    Reject multiple leave requests at once
    
    Args:
        leave_ids: List of leave IDs to reject
        user: User performing the operation
    
    Returns:
        tuple: (success_count, error_count, errors)
    """
    from leaves.models import FacultyLeave
    from notifications.utils import notify_leave_status
    
    success_count = 0
    error_count = 0
    errors = []
    
    try:
        with transaction.atomic():
            leaves = FacultyLeave.objects.filter(
                id__in=leave_ids,
                status=FacultyLeave.PENDING
            ).select_related('faculty__user')
            
            for leave in leaves:
                try:
                    leave.status = FacultyLeave.REJECTED
                    leave.save(update_fields=['status'])
                    
                    # Create notification
                    notify_leave_status(leave, 'REJECTED')
                    
                    success_count += 1
                    
                except Exception as e:
                    errors.append(f"Error rejecting leave: {str(e)}")
                    error_count += 1
    
    except Exception as e:
        errors.append(f"Transaction error: {str(e)}")
        error_count = len(leave_ids)
        success_count = 0
    
    return success_count, error_count, errors
