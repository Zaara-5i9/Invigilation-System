"""
Django management command to send reminders for pending invigilation assignments
Run this command periodically (e.g., every 30 minutes) via cron or task scheduler
"""
from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta

from exams.models import InvigilationAssignment
from exams.utils import send_reminder_email, check_and_expire_pending_assignments


class Command(BaseCommand):
    help = 'Send reminders for pending invigilation assignments and expire overdue ones'

    def add_arguments(self, parser):
        parser.add_argument(
            '--reminder-hours',
            type=float,
            default=1.0,
            help='Send reminder if deadline is within this many hours (default: 1.0)'
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be done without actually sending emails'
        )

    def handle(self, *args, **options):
        reminder_hours = options['reminder_hours']
        dry_run = options['dry_run']
        
        self.stdout.write(self.style.SUCCESS(f'Starting assignment reminder check...'))
        
        # First, expire any overdue assignments
        expired_count = check_and_expire_pending_assignments()
        if expired_count > 0:
            self.stdout.write(
                self.style.WARNING(f'Expired {expired_count} overdue assignment(s)')
            )
        
        # Find pending assignments that need reminders
        now = timezone.now()
        reminder_threshold = now + timedelta(hours=reminder_hours)
        
        pending_assignments = InvigilationAssignment.objects.filter(
            status=InvigilationAssignment.PENDING_CONFIRMATION,
            confirmation_deadline__lte=reminder_threshold,
            confirmation_deadline__gte=now,
            reminder_sent_at__isnull=True  # Haven't sent reminder yet
        ).select_related(
            'faculty__user',
            'exam_session_hall__exam',
            'exam_session_hall__hall'
        )
        
        reminder_count = 0
        error_count = 0
        
        for assignment in pending_assignments:
            faculty_name = assignment.faculty.user.get_full_name() or assignment.faculty.user.username
            exam_info = f"{assignment.exam_session_hall.exam.course_code} on {assignment.exam_session_hall.exam.exam_date}"
            
            if dry_run:
                self.stdout.write(
                    f'[DRY RUN] Would send reminder to {faculty_name} for {exam_info}'
                )
                reminder_count += 1
            else:
                try:
                    success = send_reminder_email(assignment)
                    if success:
                        assignment.reminder_sent_at = now
                        assignment.save(update_fields=['reminder_sent_at'])
                        self.stdout.write(
                            self.style.SUCCESS(f'✓ Sent reminder to {faculty_name} for {exam_info}')
                        )
                        reminder_count += 1
                    else:
                        self.stdout.write(
                            self.style.ERROR(f'✗ Failed to send reminder to {faculty_name}')
                        )
                        error_count += 1
                except Exception as e:
                    self.stdout.write(
                        self.style.ERROR(f'✗ Error sending reminder to {faculty_name}: {str(e)}')
                    )
                    error_count += 1
        
        # Summary
        self.stdout.write(self.style.SUCCESS('\n' + '='*50))
        self.stdout.write(self.style.SUCCESS('Summary:'))
        self.stdout.write(f'  Expired assignments: {expired_count}')
        self.stdout.write(f'  Reminders sent: {reminder_count}')
        if error_count > 0:
            self.stdout.write(self.style.ERROR(f'  Errors: {error_count}'))
        
        if dry_run:
            self.stdout.write(self.style.WARNING('\n[DRY RUN MODE] No emails were actually sent'))
        
        self.stdout.write(self.style.SUCCESS('='*50))
