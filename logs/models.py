from django.db import models


class FacultyActionLog(models.Model):
    faculty = models.ForeignKey('accounts.Faculty', on_delete=models.CASCADE, related_name='action_logs')
    action_type = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['faculty', '-created_at']),
            models.Index(fields=['action_type']),
        ]

    def __str__(self) -> str:
        return f"{self.faculty} - {self.action_type} @ {self.created_at}"


class AdminActionLog(models.Model):
    """Log for admin actions"""
    user = models.ForeignKey('auth.User', on_delete=models.CASCADE, related_name='admin_action_logs')
    action_type = models.CharField(max_length=100)
    description = models.TextField()
    related_object_type = models.CharField(max_length=50, blank=True)
    related_object_id = models.IntegerField(null=True, blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', '-created_at']),
            models.Index(fields=['action_type']),
            models.Index(fields=['related_object_type', 'related_object_id']),
        ]
    
    def __str__(self) -> str:
        return f"{self.user.username} - {self.action_type} @ {self.created_at}"

