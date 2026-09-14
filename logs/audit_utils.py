"""
Enhanced audit trail utilities for comprehensive logging
"""
from django.utils import timezone
from .models import FacultyActionLog


class AuditLogger:
    """Centralized audit logging utility"""
    
    # Action types
    PROFILE_UPDATE = 'PROFILE_UPDATE'
    TIMETABLE_ADD = 'TIMETABLE_ADD'
    TIMETABLE_UPDATE = 'TIMETABLE_UPDATE'
    TIMETABLE_DELETE = 'TIMETABLE_DELETE'
    LEAVE_APPLY = 'LEAVE_APPLY'
    ASSIGNMENT_CONFIRM = 'ASSIGNMENT_CONFIRM'
    ASSIGNMENT_DECLINE = 'ASSIGNMENT_DECLINE'
    PASSWORD_CHANGE = 'PASSWORD_CHANGE'
    LOGIN = 'LOGIN'
    LOGOUT = 'LOGOUT'
    
    @staticmethod
    def log_action(faculty, action_type, description, ip_address=None, user_agent=None):
        """
        Log a faculty action
        
        Args:
            faculty: Faculty object
            action_type: Type of action (use constants above)
            description: Detailed description of the action
            ip_address: Optional IP address
            user_agent: Optional user agent string
        
        Returns:
            FacultyActionLog object
        """
        return FacultyActionLog.objects.create(
            faculty=faculty,
            action_type=action_type,
            description=description,
            ip_address=ip_address,
            user_agent=user_agent
        )
    
    @staticmethod
    def log_profile_update(faculty, changes, request=None):
        """Log profile update with changes"""
        description = f"Profile updated: {changes}"
        ip = request.META.get('REMOTE_ADDR') if request else None
        user_agent = request.META.get('HTTP_USER_AGENT') if request else None
        
        return AuditLogger.log_action(
            faculty=faculty,
            action_type=AuditLogger.PROFILE_UPDATE,
            description=description,
            ip_address=ip,
            user_agent=user_agent
        )
    
    @staticmethod
    def log_timetable_change(faculty, action, details, request=None):
        """Log timetable changes"""
        action_types = {
            'add': AuditLogger.TIMETABLE_ADD,
            'update': AuditLogger.TIMETABLE_UPDATE,
            'delete': AuditLogger.TIMETABLE_DELETE,
        }
        
        ip = request.META.get('REMOTE_ADDR') if request else None
        user_agent = request.META.get('HTTP_USER_AGENT') if request else None
        
        return AuditLogger.log_action(
            faculty=faculty,
            action_type=action_types.get(action, AuditLogger.TIMETABLE_UPDATE),
            description=details,
            ip_address=ip,
            user_agent=user_agent
        )
    
    @staticmethod
    def log_assignment_response(faculty, assignment, status, reason=None, request=None):
        """Log assignment confirmation or decline"""
        exam = assignment.exam_session_hall.exam
        description = f"{status} assignment for {exam.course_code} on {exam.exam_date}"
        if reason:
            description += f". Reason: {reason}"
        
        action_type = (AuditLogger.ASSIGNMENT_CONFIRM if status == 'CONFIRMED' 
                      else AuditLogger.ASSIGNMENT_DECLINE)
        
        ip = request.META.get('REMOTE_ADDR') if request else None
        user_agent = request.META.get('HTTP_USER_AGENT') if request else None
        
        return AuditLogger.log_action(
            faculty=faculty,
            action_type=action_type,
            description=description,
            ip_address=ip,
            user_agent=user_agent
        )
    
    @staticmethod
    def log_leave_application(faculty, leave, request=None):
        """Log leave application"""
        description = f"Applied for leave from {leave.start_date} to {leave.end_date}"
        if leave.reason:
            description += f". Reason: {leave.reason}"
        
        ip = request.META.get('REMOTE_ADDR') if request else None
        user_agent = request.META.get('HTTP_USER_AGENT') if request else None
        
        return AuditLogger.log_action(
            faculty=faculty,
            action_type=AuditLogger.LEAVE_APPLY,
            description=description,
            ip_address=ip,
            user_agent=user_agent
        )
    
    @staticmethod
    def log_login(faculty, request=None):
        """Log successful login"""
        ip = request.META.get('REMOTE_ADDR') if request else None
        user_agent = request.META.get('HTTP_USER_AGENT') if request else None
        
        return AuditLogger.log_action(
            faculty=faculty,
            action_type=AuditLogger.LOGIN,
            description="Logged in",
            ip_address=ip,
            user_agent=user_agent
        )
    
    @staticmethod
    def log_password_change(faculty, request=None):
        """Log password change"""
        ip = request.META.get('REMOTE_ADDR') if request else None
        user_agent = request.META.get('HTTP_USER_AGENT') if request else None
        
        return AuditLogger.log_action(
            faculty=faculty,
            action_type=AuditLogger.PASSWORD_CHANGE,
            description="Password changed",
            ip_address=ip,
            user_agent=user_agent
        )


class AdminAuditLogger:
    """Audit logging for admin actions"""
    
    @staticmethod
    def log_exam_created(user, exam):
        """Log exam creation"""
        from logs.models import AdminActionLog
        return AdminActionLog.objects.create(
            user=user,
            action_type='EXAM_CREATE',
            description=f"Created exam: {exam.course_code} for {exam.department.code} Y{exam.year}S{exam.semester} on {exam.exam_date}",
            related_object_type='Exam',
            related_object_id=exam.id
        )
    
    @staticmethod
    def log_exam_deleted(user, exam_info):
        """Log exam deletion"""
        from logs.models import AdminActionLog
        return AdminActionLog.objects.create(
            user=user,
            action_type='EXAM_DELETE',
            description=f"Deleted exam: {exam_info}",
            related_object_type='Exam'
        )
    
    @staticmethod
    def log_assignment_created(user, assignment):
        """Log assignment creation"""
        from logs.models import AdminActionLog
        exam = assignment.exam_session_hall.exam
        faculty = assignment.faculty
        return AdminActionLog.objects.create(
            user=user,
            action_type='ASSIGNMENT_CREATE',
            description=f"Assigned {faculty.user.get_full_name()} to {exam.course_code} on {exam.exam_date}",
            related_object_type='InvigilationAssignment',
            related_object_id=assignment.id
        )
    
    @staticmethod
    def log_bulk_operation(user, operation_type, count, details):
        """Log bulk operations"""
        from logs.models import AdminActionLog
        return AdminActionLog.objects.create(
            user=user,
            action_type=f'BULK_{operation_type}',
            description=f"Bulk {operation_type}: {count} items. {details}",
            related_object_type='Bulk'
        )
    
    @staticmethod
    def log_suggestion_action(user, suggestion, action):
        """Log suggestion implementation/rejection"""
        from logs.models import AdminActionLog
        return AdminActionLog.objects.create(
            user=user,
            action_type=f'SUGGESTION_{action}',
            description=f"{action} suggestion for {suggestion.faculty.user.get_full_name()} - {suggestion.exam.course_code}",
            related_object_type='AllocationSuggestion',
            related_object_id=suggestion.id
        )
