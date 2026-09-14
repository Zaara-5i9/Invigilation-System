"""
Utility functions for creating notifications
"""
from .models import Notification, NotificationPreference


def create_notification(user, notification_type, title, message, link='', priority='MEDIUM', **kwargs):
    """
    Create a notification for a user
    
    Args:
        user: User object
        notification_type: Type of notification (from Notification.TYPE_CHOICES)
        title: Notification title
        message: Notification message
        link: Optional URL link
        priority: Priority level (LOW, MEDIUM, HIGH, URGENT)
        **kwargs: Additional fields (related_assignment_id, related_leave_id, etc.)
    
    Returns:
        Notification object or None if user has disabled this type
    """
    # Check user preferences
    try:
        prefs = NotificationPreference.objects.get(user=user)
        
        # Check if user wants this type of notification
        type_mapping = {
            Notification.ASSIGNMENT_NEW: prefs.inapp_new_assignment,
            Notification.ASSIGNMENT_REMINDER: prefs.inapp_assignment_reminder,
            Notification.LEAVE_APPROVED: prefs.inapp_leave_status,
            Notification.LEAVE_REJECTED: prefs.inapp_leave_status,
            Notification.SYSTEM_ANNOUNCEMENT: prefs.inapp_system_announcements,
        }
        
        if notification_type in type_mapping and not type_mapping[notification_type]:
            return None  # User has disabled this notification type
            
    except NotificationPreference.DoesNotExist:
        pass  # No preferences set, create notification anyway
    
    # Create notification
    notification = Notification.objects.create(
        user=user,
        notification_type=notification_type,
        title=title,
        message=message,
        link=link,
        priority=priority,
        **kwargs
    )
    
    return notification


def notify_assignment_created(assignment):
    """Create notification for new assignment"""
    exam = assignment.exam_session_hall.exam
    hall = assignment.exam_session_hall.hall
    
    title = f"New Invigilation Duty Assigned"
    message = (
        f"You have been assigned invigilation duty for {exam.course_code} "
        f"on {exam.exam_date.strftime('%B %d, %Y')} at {hall.name}. "
        f"Please confirm your availability."
    )
    link = f"/exams/faculty/dashboard/"
    
    return create_notification(
        user=assignment.faculty.user,
        notification_type=Notification.ASSIGNMENT_NEW,
        title=title,
        message=message,
        link=link,
        priority='HIGH',
        related_assignment_id=assignment.id
    )


def notify_assignment_reminder(assignment):
    """Create notification for assignment reminder"""
    exam = assignment.exam_session_hall.exam
    
    title = f"Reminder: Confirm Your Duty"
    message = (
        f"Please confirm your invigilation duty for {exam.course_code} "
        f"on {exam.exam_date.strftime('%B %d, %Y')}. "
        f"Deadline: {assignment.confirmation_deadline.strftime('%B %d, %I:%M %p')}"
    )
    link = f"/exams/faculty/dashboard/"
    
    return create_notification(
        user=assignment.faculty.user,
        notification_type=Notification.ASSIGNMENT_REMINDER,
        title=title,
        message=message,
        link=link,
        priority='URGENT',
        related_assignment_id=assignment.id
    )


def notify_leave_status(leave, status):
    """Create notification for leave approval/rejection"""
    if status == 'APPROVED':
        title = "Leave Request Approved"
        message = f"Your leave request from {leave.start_date} to {leave.end_date} has been approved."
        notification_type = Notification.LEAVE_APPROVED
    else:
        title = "Leave Request Rejected"
        message = f"Your leave request from {leave.start_date} to {leave.end_date} has been rejected."
        notification_type = Notification.LEAVE_REJECTED
    
    link = "/leaves/faculty/"
    
    return create_notification(
        user=leave.faculty.user,
        notification_type=notification_type,
        title=title,
        message=message,
        link=link,
        priority='MEDIUM',
        related_leave_id=leave.id
    )


def notify_system_announcement(users, title, message, priority='MEDIUM'):
    """Create system announcement for multiple users"""
    notifications = []
    for user in users:
        notif = create_notification(
            user=user,
            notification_type=Notification.SYSTEM_ANNOUNCEMENT,
            title=title,
            message=message,
            link='',
            priority=priority
        )
        if notif:
            notifications.append(notif)
    
    return notifications
