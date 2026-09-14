"""
Notification views for in-app notifications
"""
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, get_object_or_404, redirect
from django.http import JsonResponse
from django.contrib import messages
from django.core.paginator import Paginator

from .models import Notification, NotificationPreference


@login_required
def notification_list(request):
    """List all notifications for current user"""
    notifications = Notification.objects.filter(user=request.user)
    
    # Filter by read status
    filter_type = request.GET.get('filter', 'all')
    if filter_type == 'unread':
        notifications = notifications.filter(is_read=False)
    elif filter_type == 'read':
        notifications = notifications.filter(is_read=True)
    
    # Pagination
    paginator = Paginator(notifications, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # Count unread and read
    unread_count = Notification.objects.filter(user=request.user, is_read=False).count()
    read_count = Notification.objects.filter(user=request.user, is_read=True).count()
    
    context = {
        'page_obj': page_obj,
        'filter_type': filter_type,
        'unread_count': unread_count,
        'read_count': read_count,
    }
    
    return render(request, 'notifications/notification_list.html', context)


@login_required
def mark_as_read(request, pk):
    """Mark a notification as read"""
    notification = get_object_or_404(Notification, pk=pk, user=request.user)
    notification.mark_as_read()
    
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return JsonResponse({'success': True})
    
    return redirect('notifications:notification_list')


@login_required
def mark_all_as_read(request):
    """Mark all notifications as read"""
    if request.method == 'POST':
        from django.utils import timezone
        Notification.objects.filter(user=request.user, is_read=False).update(
            is_read=True,
            read_at=timezone.now()
        )
        messages.success(request, 'All notifications marked as read')
    
    return redirect('notifications:notification_list')


@login_required
def delete_notification(request, pk):
    """Delete a notification"""
    notification = get_object_or_404(Notification, pk=pk, user=request.user)
    
    if request.method == 'POST':
        notification.delete()
        messages.success(request, 'Notification deleted')
    
    return redirect('notifications:notification_list')


@login_required
def notification_preferences(request):
    """Manage notification preferences"""
    preferences, created = NotificationPreference.objects.get_or_create(user=request.user)
    
    if request.method == 'POST':
        # Update preferences
        preferences.email_new_assignment = request.POST.get('email_new_assignment') == 'on'
        preferences.email_assignment_reminder = request.POST.get('email_assignment_reminder') == 'on'
        preferences.email_leave_status = request.POST.get('email_leave_status') == 'on'
        preferences.email_system_announcements = request.POST.get('email_system_announcements') == 'on'
        
        preferences.inapp_new_assignment = request.POST.get('inapp_new_assignment') == 'on'
        preferences.inapp_assignment_reminder = request.POST.get('inapp_assignment_reminder') == 'on'
        preferences.inapp_leave_status = request.POST.get('inapp_leave_status') == 'on'
        preferences.inapp_system_announcements = request.POST.get('inapp_system_announcements') == 'on'
        
        preferences.daily_digest = request.POST.get('daily_digest') == 'on'
        preferences.weekly_digest = request.POST.get('weekly_digest') == 'on'
        
        preferences.save()
        messages.success(request, 'Notification preferences updated')
        return redirect('notifications:notification_preferences')
    
    context = {
        'preferences': preferences,
    }
    
    return render(request, 'notifications/notification_preferences.html', context)


@login_required
def get_unread_count(request):
    """API endpoint to get unread notification count"""
    count = Notification.objects.filter(user=request.user, is_read=False).count()
    return JsonResponse({'count': count})


@login_required
def get_recent_notifications(request):
    """API endpoint to get recent notifications"""
    notifications = Notification.objects.filter(user=request.user).order_by('-created_at')[:5]
    
    data = [{
        'id': n.id,
        'title': n.title,
        'message': n.message[:100],
        'type': n.notification_type,
        'priority': n.priority,
        'is_read': n.is_read,
        'created_at': n.created_at.isoformat(),
        'link': n.link,
    } for n in notifications]
    
    return JsonResponse({'notifications': data})
