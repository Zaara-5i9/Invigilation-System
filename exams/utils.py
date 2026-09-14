from django.core.mail import send_mail, EmailMultiAlternatives
from django.conf import settings
from django.template.loader import render_to_string
from django.utils import timezone
from datetime import datetime, timedelta


def send_invigilation_assignment_email(assignment):
    """Send email notification for new invigilation assignment using HTML template"""
    exam = assignment.exam_session_hall.exam
    hall = assignment.exam_session_hall.hall
    faculty = assignment.faculty
    
    subject = f"Invigilation Duty Assignment - {exam.course_code}"
    
    # Prepare context for template
    context = {
        'faculty_name': faculty.user.get_full_name() or faculty.user.username,
        'course_code': exam.course_code,
        'course_name': exam.course_name,
        'department': exam.department.name,
        'exam_date': exam.exam_date.strftime('%d %B %Y'),
        'start_time': exam.start_time.strftime('%I:%M %p'),
        'end_time': exam.end_time.strftime('%I:%M %p'),
        'hall_name': hall.name,
        'hall_block': hall.block,
        'deadline': assignment.confirmation_deadline.strftime('%d %b %Y, %I:%M %p') if assignment.confirmation_deadline else 'ASAP',
        'login_url': f"{settings.LOGIN_URL if hasattr(settings, 'LOGIN_URL') else 'http://localhost:8000/accounts/login/'}",
    }
    
    # Render HTML template
    html_content = render_to_string('emails/assignment_notification.html', context)
    
    # Plain text fallback
    text_content = f"""
Dear {context['faculty_name']},

You have been assigned invigilation duty for the following exam:

Course: {context['course_code']} - {context['course_name']}
Department: {context['department']}
Date: {context['exam_date']}
Time: {context['start_time']} - {context['end_time']}
Venue: {context['hall_name']}, {context['hall_block']}

Please log in to the platform and confirm your availability by {context['deadline']}.

If you are unable to attend, please decline the assignment immediately so we can arrange a replacement.

Login at: {context['login_url']}

Best regards,
Invigilation Management System
"""
    
    try:
        # Create email with both HTML and plain text
        email = EmailMultiAlternatives(
            subject=subject,
            body=text_content,
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=[faculty.user.email]
        )
        email.attach_alternative(html_content, "text/html")
        email.send(fail_silently=False)
        return True
    except Exception as e:
        print(f"Failed to send email to {faculty.user.email}: {e}")
        return False


def send_reminder_email(assignment):
    """Send reminder email for pending confirmation using HTML template"""
    exam = assignment.exam_session_hall.exam
    hall = assignment.exam_session_hall.hall
    faculty = assignment.faculty
    
    subject = f"⚠️ URGENT: Invigilation Duty Confirmation Required - {exam.course_code}"
    
    # Prepare context for template
    context = {
        'faculty_name': faculty.user.get_full_name() or faculty.user.username,
        'course_code': exam.course_code,
        'course_name': exam.course_name,
        'exam_date': exam.exam_date.strftime('%d %B %Y'),
        'start_time': exam.start_time.strftime('%I:%M %p'),
        'end_time': exam.end_time.strftime('%I:%M %p'),
        'hall_name': hall.name,
        'hall_block': hall.block,
        'deadline': assignment.confirmation_deadline.strftime('%d %b %Y, %I:%M %p') if assignment.confirmation_deadline else 'ASAP',
        'login_url': f"{settings.LOGIN_URL if hasattr(settings, 'LOGIN_URL') else 'http://localhost:8000/accounts/login/'}",
    }
    
    # Render HTML template
    html_content = render_to_string('emails/assignment_reminder.html', context)
    
    # Plain text fallback
    text_content = f"""
Dear {context['faculty_name']},

⚠️ URGENT REMINDER ⚠️

This is a reminder that you have a pending invigilation assignment that requires your confirmation:

Course: {context['course_code']} - {context['course_name']}
Date: {context['exam_date']}
Time: {context['start_time']} - {context['end_time']}
Venue: {context['hall_name']}, {context['hall_block']}

URGENT: Please confirm or decline by {context['deadline']}

Login at: {context['login_url']}

Best regards,
Invigilation Management System
"""
    
    try:
        email = EmailMultiAlternatives(
            subject=subject,
            body=text_content,
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=[faculty.user.email]
        )
        email.attach_alternative(html_content, "text/html")
        email.send(fail_silently=False)
        return True
    except Exception as e:
        print(f"Failed to send reminder email to {faculty.user.email}: {e}")
        return False


def send_assignment_declined_notification_to_admin(assignment):
    """Notify admin when faculty declines assignment"""
    exam = assignment.exam_session_hall.exam
    hall = assignment.exam_session_hall.hall
    faculty = assignment.faculty
    
    subject = f"Faculty Declined Invigilation Duty - {exam.course_code}"
    
    message = f"""
Alert: A faculty member has declined an invigilation assignment.

Faculty: {faculty.user.get_full_name() or faculty.user.username} ({faculty.employee_id})
Course: {exam.course_code} - {exam.course_name}
Date: {exam.exam_date.strftime('%d %B %Y')}
Time: {exam.start_time.strftime('%I:%M %p')} - {exam.end_time.strftime('%I:%M %p')}
Venue: {hall.name}, {hall.block}
Reason: {assignment.decline_reason or 'Not provided'}

Please reassign this duty immediately.

Best regards,
Invigilation Management System
"""
    
    admin_emails = []
    from django.contrib.auth.models import User
    admin_users = User.objects.filter(is_staff=True, is_active=True)
    admin_emails = [user.email for user in admin_users if user.email]
    
    if admin_emails:
        try:
            send_mail(
                subject,
                message,
                settings.DEFAULT_FROM_EMAIL,
                admin_emails,
                fail_silently=False,
            )
            return True
        except Exception as e:
            print(f"Failed to send admin notification: {e}")
            return False
    return False


def check_and_expire_pending_assignments():
    """Check for expired pending assignments and mark them as expired"""
    from exams.models import InvigilationAssignment
    
    now = timezone.now()
    expired_assignments = InvigilationAssignment.objects.filter(
        status=InvigilationAssignment.PENDING_CONFIRMATION,
        confirmation_deadline__lt=now
    )
    
    count = 0
    for assignment in expired_assignments:
        assignment.status = InvigilationAssignment.EXPIRED
        assignment.save(update_fields=['status'])
        send_assignment_declined_notification_to_admin(assignment)
        count += 1
    
    return count
