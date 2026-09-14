"""
In-app notification system for faculty and admin
"""
from django.db import models
from django.conf import settings


class Notification(models.Model):
    """In-app notifications for users"""
    
    # Notification types
    ASSIGNMENT_NEW = 'ASSIGNMENT_NEW'
    ASSIGNMENT_REMINDER = 'ASSIGNMENT_REMINDER'
    ASSIGNMENT_EXPIRED = 'ASSIGNMENT_EXPIRED'
    ASSIGNMENT_CANCELLED = 'ASSIGNMENT_CANCELLED'
    LEAVE_APPROVED = 'LEAVE_APPROVED'
    LEAVE_REJECTED = 'LEAVE_REJECTED'
    TIMETABLE_UPDATED = 'TIMETABLE_UPDATED'
    SYSTEM_ANNOUNCEMENT = 'SYSTEM_ANNOUNCEMENT'
    
    TYPE_CHOICES = [
        (ASSIGNMENT_NEW, 'New Assignment'),
        (ASSIGNMENT_REMINDER, 'Assignment Reminder'),
        (ASSIGNMENT_EXPIRED, 'Assignment Expired'),
        (ASSIGNMENT_CANCELLED, 'Assignment Cancelled'),
        (LEAVE_APPROVED, 'Leave Approved'),
        (LEAVE_REJECTED, 'Leave Rejected'),
        (TIMETABLE_UPDATED, 'Timetable Updated'),
        (SYSTEM_ANNOUNCEMENT, 'System Announcement'),
    ]
    
    # Priority levels
    LOW = 'LOW'
    MEDIUM = 'MEDIUM'
    HIGH = 'HIGH'
    URGENT = 'URGENT'
    
    PRIORITY_CHOICES = [
        (LOW, 'Low'),
        (MEDIUM, 'Medium'),
        (HIGH, 'High'),
        (URGENT, 'Urgent'),
    ]
    
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='notifications'
    )
    notification_type = models.CharField(max_length=30, choices=TYPE_CHOICES)
    priority = models.CharField(max_length=10, choices=PRIORITY_CHOICES, default=MEDIUM)
    title = models.CharField(max_length=200)
    message = models.TextField()
    link = models.CharField(max_length=500, blank=True, help_text="URL to related object")
    
    is_read = models.BooleanField(default=False)
    read_at = models.DateTimeField(null=True, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField(null=True, blank=True, help_text="Auto-delete after this date")
    
    # Optional: Link to related objects
    related_assignment_id = models.IntegerField(null=True, blank=True)
    related_leave_id = models.IntegerField(null=True, blank=True)
    related_exam_id = models.IntegerField(null=True, blank=True)
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', 'is_read']),
            models.Index(fields=['created_at']),
        ]
    
    def __str__(self):
        return f"{self.user.username} - {self.title}"
    
    def mark_as_read(self):
        """Mark notification as read"""
        if not self.is_read:
            from django.utils import timezone
            self.is_read = True
            self.read_at = timezone.now()
            self.save(update_fields=['is_read', 'read_at'])


class NotificationPreference(models.Model):
    """User preferences for notifications"""
    
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='notification_preferences'
    )
    
    # Email preferences
    email_new_assignment = models.BooleanField(default=True)
    email_assignment_reminder = models.BooleanField(default=True)
    email_leave_status = models.BooleanField(default=True)
    email_system_announcements = models.BooleanField(default=True)
    
    # In-app preferences
    inapp_new_assignment = models.BooleanField(default=True)
    inapp_assignment_reminder = models.BooleanField(default=True)
    inapp_leave_status = models.BooleanField(default=True)
    inapp_system_announcements = models.BooleanField(default=True)
    
    # Digest preferences
    daily_digest = models.BooleanField(default=False, help_text="Receive daily summary email")
    weekly_digest = models.BooleanField(default=False, help_text="Receive weekly summary email")
    
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"Preferences for {self.user.username}"
