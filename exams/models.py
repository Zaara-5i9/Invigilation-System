from django.db import models
from django.conf import settings
from datetime import datetime


class Department(models.Model):
    name = models.CharField(max_length=100)
    code = models.CharField(max_length=10, unique=True)

    def __str__(self) -> str:
        return f"{self.code} - {self.name}"


class ExamHall(models.Model):
    name = models.CharField(max_length=50)
    block = models.CharField(max_length=50)
    floor = models.CharField(max_length=20, blank=True)
    capacity = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)

    def __str__(self) -> str:
        return f"{self.name} ({self.block})"


class Exam(models.Model):
    MID = 'MID'
    END = 'END'
    TEST = 'TEST'

    EXAM_TYPE_CHOICES = [
        (MID, 'Mid-term'),
        (END, 'End-semester'),
        (TEST, 'Test'),
    ]

    course_code = models.CharField(max_length=20, db_index=True)
    course_name = models.CharField(max_length=200)
    exam_type = models.CharField(max_length=10, choices=EXAM_TYPE_CHOICES)
    department = models.ForeignKey(Department, on_delete=models.CASCADE, related_name='exams', db_index=True)
    year = models.PositiveSmallIntegerField(help_text="Year of study (1-4)", db_index=True)
    semester = models.PositiveSmallIntegerField(db_index=True)
    exam_date = models.DateField(db_index=True)
    start_time = models.TimeField()
    end_time = models.TimeField()
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    subject_teacher = models.ForeignKey('accounts.Faculty', on_delete=models.SET_NULL, null=True, blank=True, related_name='teaching_exams', help_text="Faculty teaching this subject")

    class Meta:
        indexes = [
            models.Index(fields=['exam_date', 'start_time']),
            models.Index(fields=['department', 'year', 'semester']),
        ]

    def __str__(self) -> str:
        return f"{self.course_code} - {self.exam_date}"

    @property
    def day(self):
        """Return the day of the week for the exam date"""
        return self.exam_date.strftime('%A')


class ExamSessionHall(models.Model):
    exam = models.ForeignKey(Exam, on_delete=models.CASCADE, related_name='session_halls')
    hall = models.ForeignKey(ExamHall, on_delete=models.CASCADE, related_name='exam_sessions')
    required_invigilators = models.PositiveIntegerField(default=1)

    def __str__(self) -> str:
        return f"{self.exam} @ {self.hall}"


class InvigilationAssignment(models.Model):
    PENDING_CONFIRMATION = 'PENDING_CONFIRMATION'
    CONFIRMED = 'CONFIRMED'
    DECLINED = 'DECLINED'
    CANCELLED = 'CANCELLED'
    REASSIGNED = 'REASSIGNED'
    EXPIRED = 'EXPIRED'

    STATUS_CHOICES = [
        (PENDING_CONFIRMATION, 'Pending Confirmation'),
        (CONFIRMED, 'Confirmed'),
        (DECLINED, 'Declined'),
        (CANCELLED, 'Cancelled'),
        (REASSIGNED, 'Reassigned'),
        (EXPIRED, 'Expired'),
    ]

    exam_session_hall = models.ForeignKey(ExamSessionHall, on_delete=models.CASCADE, related_name='assignments')
    faculty = models.ForeignKey('accounts.Faculty', on_delete=models.CASCADE, related_name='invigilation_assignments', db_index=True)
    status = models.CharField(max_length=30, choices=STATUS_CHOICES, default=PENDING_CONFIRMATION, db_index=True)
    assigned_at = models.DateTimeField(auto_now_add=True)
    confirmed_at = models.DateTimeField(null=True, blank=True)
    declined_at = models.DateTimeField(null=True, blank=True)
    confirmation_deadline = models.DateTimeField(null=True, blank=True, db_index=True)
    notification_sent_at = models.DateTimeField(null=True, blank=True)
    reminder_sent_at = models.DateTimeField(null=True, blank=True)
    decline_reason = models.TextField(blank=True)

    class Meta:
        indexes = [
            models.Index(fields=['faculty', 'status']),
            models.Index(fields=['status', 'confirmation_deadline']),
        ]

    def __str__(self) -> str:
        return f"{self.exam_session_hall} -> {self.faculty} ({self.status})"


class AllocationSuggestion(models.Model):
    """Stores suggestions for manual intervention when automatic allocation fails"""
    PENDING = 'PENDING'
    REVIEWED = 'REVIEWED'
    IMPLEMENTED = 'IMPLEMENTED'
    REJECTED = 'REJECTED'
    
    STATUS_CHOICES = [
        (PENDING, 'Pending Review'),
        (REVIEWED, 'Reviewed'),
        (IMPLEMENTED, 'Implemented'),
        (REJECTED, 'Rejected'),
    ]
    
    exam = models.ForeignKey(Exam, on_delete=models.CASCADE, related_name='allocation_suggestions')
    exam_session_hall = models.ForeignKey(ExamSessionHall, on_delete=models.CASCADE, related_name='suggestions')
    faculty = models.ForeignKey('accounts.Faculty', on_delete=models.CASCADE, related_name='allocation_suggestions')
    
    # Clash details
    clash_type = models.CharField(max_length=50)  # 'TIMETABLE_CLASH', 'SAME_DEPT', 'SUBJECT_TEACHER', 'ON_LEAVE'
    clash_details = models.TextField()  # JSON or text description
    
    # Suggestion
    suggestion_type = models.CharField(max_length=50)  # 'SWAP_CLASS', 'CANCEL_CLASS', 'FIND_SUBSTITUTE'
    suggestion_text = models.TextField()
    
    # Status
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=PENDING)
    created_at = models.DateTimeField(auto_now_add=True)
    reviewed_at = models.DateTimeField(null=True, blank=True)
    reviewed_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='reviewed_suggestions')
    admin_notes = models.TextField(blank=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self) -> str:
        return f"Suggestion for {self.faculty} - {self.exam} ({self.status})"

