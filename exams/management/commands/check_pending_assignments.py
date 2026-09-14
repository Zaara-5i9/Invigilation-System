from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta
from exams.models import InvigilationAssignment
from exams.utils import send_reminder_email, check_and_expire_pending_assignments


class Command(BaseCommand):
    help = 'Check pending invigilation assignments and send reminders or mark as expired'

    def handle(self, *args, **options):
        now = timezone.now()
        
        # Check and expire assignments past deadline
        expired_count = check_and_expire_pending_assignments()
        if expired_count > 0:
            self.stdout.write(
                self.style.WARNING(f'Marked {expired_count} assignments as expired')
            )
        
        # Send reminders for assignments approaching deadline (within 30 minutes)
        reminder_threshold = now + timedelta(minutes=30)
        pending_assignments = InvigilationAssignment.objects.filter(
            status=InvigilationAssignment.PENDING_CONFIRMATION,
            confirmation_deadline__lte=reminder_threshold,
            confirmation_deadline__gt=now,
            reminder_sent_at__isnull=True
        ).select_related('faculty__user', 'exam_session_hall__exam', 'exam_session_hall__hall')
        
        reminder_count = 0
        for assignment in pending_assignments:
            if send_reminder_email(assignment):
                assignment.reminder_sent_at = now
                assignment.save(update_fields=['reminder_sent_at'])
                reminder_count += 1
        
        if reminder_count > 0:
            self.stdout.write(
                self.style.SUCCESS(f'Sent {reminder_count} reminder emails')
            )
        
        # Send initial notifications for assignments created 3 hours before exam
        # (This would typically be triggered when auto-allocation runs)
        three_hours_from_now = now + timedelta(hours=3)
        upcoming_assignments = InvigilationAssignment.objects.filter(
            status=InvigilationAssignment.PENDING_CONFIRMATION,
            notification_sent_at__isnull=True,
            exam_session_hall__exam__exam_date=three_hours_from_now.date()
        ).select_related('faculty__user', 'exam_session_hall__exam', 'exam_session_hall__hall')
        
        notification_count = 0
        for assignment in upcoming_assignments:
            from exams.utils import send_invigilation_assignment_email
            if send_invigilation_assignment_email(assignment):
                assignment.notification_sent_at = now
                assignment.save(update_fields=['notification_sent_at'])
                notification_count += 1
        
        if notification_count > 0:
            self.stdout.write(
                self.style.SUCCESS(f'Sent {notification_count} initial notifications')
            )
        
        if expired_count == 0 and reminder_count == 0 and notification_count == 0:
            self.stdout.write(
                self.style.SUCCESS('No pending actions required')
            )
