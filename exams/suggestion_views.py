from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib import messages
from django.utils import timezone
from exams.models import Exam, AllocationSuggestion, InvigilationAssignment
from accounts.models import Faculty
import json


@staff_member_required
def allocation_suggestions(request, pk):
    """View all allocation suggestions for an exam"""
    exam = get_object_or_404(Exam.objects.select_related("department"), pk=pk)
    
    suggestions = AllocationSuggestion.objects.filter(
        exam=exam
    ).select_related(
        'faculty__user',
        'faculty__department',
        'exam_session_hall__hall'
    ).order_by('status', '-created_at')
    
    # Group by status
    pending = suggestions.filter(status=AllocationSuggestion.PENDING)
    reviewed = suggestions.filter(status=AllocationSuggestion.REVIEWED)
    implemented = suggestions.filter(status=AllocationSuggestion.IMPLEMENTED)
    rejected = suggestions.filter(status=AllocationSuggestion.REJECTED)
    
    context = {
        'exam': exam,
        'suggestions': suggestions,
        'pending': pending,
        'reviewed': reviewed,
        'implemented': implemented,
        'rejected': rejected,
        'total_count': suggestions.count(),
        'pending_count': pending.count(),
    }
    
    return render(request, 'exams/allocation_suggestions.html', context)


@staff_member_required
def suggestion_detail(request, pk):
    """View and manage a specific suggestion"""
    suggestion = get_object_or_404(
        AllocationSuggestion.objects.select_related(
            'exam',
            'exam_session_hall__hall',
            'faculty__user',
            'faculty__department'
        ),
        pk=pk
    )
    
    # Parse clash details
    try:
        clash_data = json.loads(suggestion.clash_details)
    except:
        clash_data = {'details': suggestion.clash_details}
    
    if request.method == 'POST':
        action = request.POST.get('action')
        
        if action == 'implement':
            # Mark as implemented and assign the faculty
            suggestion.status = AllocationSuggestion.IMPLEMENTED
            suggestion.reviewed_at = timezone.now()
            suggestion.reviewed_by = request.user
            suggestion.admin_notes = request.POST.get('notes', '')
            suggestion.save()
            
            # Create the assignment
            assignment, created = InvigilationAssignment.objects.get_or_create(
                exam_session_hall=suggestion.exam_session_hall,
                faculty=suggestion.faculty,
                defaults={
                    "status": InvigilationAssignment.PENDING_CONFIRMATION,
                },
            )
            
            if created:
                from datetime import datetime, timedelta
                from django.utils import timezone as tz
                exam = suggestion.exam
                exam_start_dt = datetime.combine(exam.exam_date, exam.start_time)
                deadline = tz.make_aware(exam_start_dt) - timedelta(hours=1, minutes=30)
                assignment.confirmation_deadline = deadline
                assignment.notification_sent_at = tz.now()
                assignment.save(update_fields=["confirmation_deadline", "notification_sent_at"])
                
                # Send email
                from exams.utils import send_invigilation_assignment_email
                send_invigilation_assignment_email(assignment)
            
            messages.success(request, f"Suggestion implemented! Assignment created for {suggestion.faculty.user.get_full_name()}.")
            return redirect('exams:allocation_suggestions', pk=suggestion.exam.pk)
        
        elif action == 'reject':
            suggestion.status = AllocationSuggestion.REJECTED
            suggestion.reviewed_at = timezone.now()
            suggestion.reviewed_by = request.user
            suggestion.admin_notes = request.POST.get('notes', '')
            suggestion.save()
            
            messages.info(request, "Suggestion rejected.")
            return redirect('exams:allocation_suggestions', pk=suggestion.exam.pk)
        
        elif action == 'mark_reviewed':
            suggestion.status = AllocationSuggestion.REVIEWED
            suggestion.reviewed_at = timezone.now()
            suggestion.reviewed_by = request.user
            suggestion.admin_notes = request.POST.get('notes', '')
            suggestion.save()
            
            messages.info(request, "Suggestion marked as reviewed.")
            return redirect('exams:allocation_suggestions', pk=suggestion.exam.pk)
    
    context = {
        'suggestion': suggestion,
        'clash_data': clash_data,
    }
    
    return render(request, 'exams/suggestion_detail.html', context)


@staff_member_required
def all_suggestions_list(request):
    """View all pending suggestions across all exams"""
    status_filter = request.GET.get('status', 'PENDING')
    
    suggestions = AllocationSuggestion.objects.select_related(
        'exam__department',
        'exam_session_hall__hall',
        'faculty__user',
        'faculty__department'
    )
    
    if status_filter and status_filter != 'ALL':
        suggestions = suggestions.filter(status=status_filter)
    
    suggestions = suggestions.order_by('-created_at')[:100]
    
    context = {
        'suggestions': suggestions,
        'status_filter': status_filter,
        'total_pending': AllocationSuggestion.objects.filter(status=AllocationSuggestion.PENDING).count(),
    }
    
    return render(request, 'exams/all_suggestions_list.html', context)
