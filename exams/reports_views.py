"""
Reports and Analytics Views for Invigilation System
"""
from django.contrib.admin.views.decorators import staff_member_required
from django.shortcuts import render
from django.db.models import Count, Q, Avg
from django.utils import timezone
from datetime import timedelta
import json

from .models import (
    Exam, InvigilationAssignment, Department, 
    ExamSessionHall, AllocationSuggestion
)
from accounts.models import Faculty


@staff_member_required
def reports_dashboard(request):
    """Main reports and analytics dashboard"""
    
    # Date range filter
    date_from = request.GET.get('date_from')
    date_to = request.GET.get('date_to')
    
    # Default to current semester (last 6 months)
    if not date_from:
        date_from = (timezone.now() - timedelta(days=180)).date()
    if not date_to:
        date_to = timezone.now().date()
    
    # Filter exams by date range
    exams = Exam.objects.filter(exam_date__gte=date_from, exam_date__lte=date_to)
    
    # Overall Statistics
    total_exams = exams.count()
    total_assignments = InvigilationAssignment.objects.filter(
        exam_session_hall__exam__in=exams
    ).count()
    
    confirmed_assignments = InvigilationAssignment.objects.filter(
        exam_session_hall__exam__in=exams,
        status=InvigilationAssignment.CONFIRMED
    ).count()
    
    declined_assignments = InvigilationAssignment.objects.filter(
        exam_session_hall__exam__in=exams,
        status=InvigilationAssignment.DECLINED
    ).count()
    
    pending_assignments = InvigilationAssignment.objects.filter(
        exam_session_hall__exam__in=exams,
        status=InvigilationAssignment.PENDING_CONFIRMATION
    ).count()
    
    # Faculty Workload Distribution
    faculty_workload = InvigilationAssignment.objects.filter(
        exam_session_hall__exam__in=exams,
        status__in=[InvigilationAssignment.CONFIRMED, InvigilationAssignment.PENDING_CONFIRMATION]
    ).values(
        'faculty__user__first_name',
        'faculty__user__last_name',
        'faculty__employee_id',
        'faculty__department__code'
    ).annotate(
        total_duties=Count('id'),
        confirmed=Count('id', filter=Q(status=InvigilationAssignment.CONFIRMED)),
        pending=Count('id', filter=Q(status=InvigilationAssignment.PENDING_CONFIRMATION))
    ).order_by('-total_duties')[:20]  # Top 20 faculty
    
    # Department-wise Statistics
    dept_stats = Department.objects.annotate(
        total_exams=Count('exams', filter=Q(exams__exam_date__gte=date_from, exams__exam_date__lte=date_to)),
        total_faculty=Count('faculty', filter=Q(faculty__is_active=True)),
        total_assignments=Count(
            'faculty__invigilation_assignments',
            filter=Q(
                faculty__invigilation_assignments__exam_session_hall__exam__exam_date__gte=date_from,
                faculty__invigilation_assignments__exam_session_hall__exam__exam_date__lte=date_to
            )
        )
    ).order_by('code')
    
    # Monthly Distribution
    monthly_data = exams.extra(
        select={'month': "strftime('%%Y-%%m', exam_date)"}
    ).values('month').annotate(
        exam_count=Count('id')
    ).order_by('month')
    
    # Prepare chart data
    monthly_labels = [item['month'] for item in monthly_data]
    monthly_values = [item['exam_count'] for item in monthly_data]
    
    # Faculty workload chart data
    faculty_labels = [
        f"{item['faculty__user__first_name']} {item['faculty__user__last_name']}"
        for item in faculty_workload
    ]
    faculty_values = [item['total_duties'] for item in faculty_workload]
    
    # Department chart data
    dept_labels = [dept.code for dept in dept_stats]
    dept_exam_values = [dept.total_exams for dept in dept_stats]
    dept_assignment_values = [dept.total_assignments for dept in dept_stats]
    
    # Acceptance Rate
    acceptance_rate = 0
    if total_assignments > 0:
        acceptance_rate = round((confirmed_assignments / total_assignments) * 100, 1)
    
    context = {
        'date_from': date_from,
        'date_to': date_to,
        'total_exams': total_exams,
        'total_assignments': total_assignments,
        'confirmed_assignments': confirmed_assignments,
        'declined_assignments': declined_assignments,
        'pending_assignments': pending_assignments,
        'acceptance_rate': acceptance_rate,
        'faculty_workload': faculty_workload,
        'dept_stats': dept_stats,
        
        # Chart data (JSON)
        'monthly_labels_json': json.dumps(monthly_labels),
        'monthly_values_json': json.dumps(monthly_values),
        'faculty_labels_json': json.dumps(faculty_labels),
        'faculty_values_json': json.dumps(faculty_values),
        'dept_labels_json': json.dumps(dept_labels),
        'dept_exam_values_json': json.dumps(dept_exam_values),
        'dept_assignment_values_json': json.dumps(dept_assignment_values),
    }
    
    return render(request, 'exams/reports_dashboard.html', context)


@staff_member_required
def faculty_workload_report(request):
    """Detailed faculty workload report"""
    
    # Date range filter
    date_from = request.GET.get('date_from')
    date_to = request.GET.get('date_to')
    department_id = request.GET.get('department')
    
    if not date_from:
        date_from = (timezone.now() - timedelta(days=180)).date()
    if not date_to:
        date_to = timezone.now().date()
    
    # Get all active faculty
    faculty_qs = Faculty.objects.filter(is_active=True).select_related('user', 'department')
    
    if department_id:
        faculty_qs = faculty_qs.filter(department_id=department_id)
    
    # Annotate with assignment counts
    faculty_list = []
    for faculty in faculty_qs:
        assignments = InvigilationAssignment.objects.filter(
            faculty=faculty,
            exam_session_hall__exam__exam_date__gte=date_from,
            exam_session_hall__exam__exam_date__lte=date_to
        )
        
        total = assignments.count()
        confirmed = assignments.filter(status=InvigilationAssignment.CONFIRMED).count()
        declined = assignments.filter(status=InvigilationAssignment.DECLINED).count()
        pending = assignments.filter(status=InvigilationAssignment.PENDING_CONFIRMATION).count()
        
        faculty_list.append({
            'faculty': faculty,
            'total': total,
            'confirmed': confirmed,
            'declined': declined,
            'pending': pending,
            'acceptance_rate': round((confirmed / total * 100) if total > 0 else 0, 1)
        })
    
    # Sort by total assignments
    faculty_list.sort(key=lambda x: x['total'], reverse=True)
    
    departments = Department.objects.all().order_by('code')
    
    context = {
        'faculty_list': faculty_list,
        'date_from': date_from,
        'date_to': date_to,
        'departments': departments,
        'selected_department': department_id,
    }
    
    return render(request, 'exams/faculty_workload_report.html', context)


@staff_member_required
def export_workload_csv(request):
    """Export faculty workload report as CSV"""
    import csv
    from django.http import HttpResponse
    
    date_from = request.GET.get('date_from')
    date_to = request.GET.get('date_to')
    
    if not date_from:
        date_from = (timezone.now() - timedelta(days=180)).date()
    if not date_to:
        date_to = timezone.now().date()
    
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = f'attachment; filename="faculty_workload_{date_from}_to_{date_to}.csv"'
    
    writer = csv.writer(response)
    writer.writerow([
        'Employee ID', 'Name', 'Department', 'Total Assignments',
        'Confirmed', 'Declined', 'Pending', 'Acceptance Rate (%)'
    ])
    
    faculty_qs = Faculty.objects.filter(is_active=True).select_related('user', 'department')
    
    for faculty in faculty_qs:
        assignments = InvigilationAssignment.objects.filter(
            faculty=faculty,
            exam_session_hall__exam__exam_date__gte=date_from,
            exam_session_hall__exam__exam_date__lte=date_to
        )
        
        total = assignments.count()
        confirmed = assignments.filter(status=InvigilationAssignment.CONFIRMED).count()
        declined = assignments.filter(status=InvigilationAssignment.DECLINED).count()
        pending = assignments.filter(status=InvigilationAssignment.PENDING_CONFIRMATION).count()
        acceptance_rate = round((confirmed / total * 100) if total > 0 else 0, 1)
        
        writer.writerow([
            faculty.employee_id,
            faculty.user.get_full_name() or faculty.user.username,
            faculty.department.code if faculty.department else 'N/A',
            total,
            confirmed,
            declined,
            pending,
            acceptance_rate
        ])
    
    return response


@staff_member_required
def department_statistics(request):
    """Department-wise statistics and comparison"""
    
    date_from = request.GET.get('date_from')
    date_to = request.GET.get('date_to')
    
    if not date_from:
        date_from = (timezone.now() - timedelta(days=180)).date()
    if not date_to:
        date_to = timezone.now().date()
    
    departments = Department.objects.all().order_by('code')
    dept_data = []
    
    for dept in departments:
        exams = Exam.objects.filter(
            department=dept,
            exam_date__gte=date_from,
            exam_date__lte=date_to
        )
        
        faculty_count = Faculty.objects.filter(department=dept, is_active=True).count()
        
        assignments = InvigilationAssignment.objects.filter(
            faculty__department=dept,
            exam_session_hall__exam__exam_date__gte=date_from,
            exam_session_hall__exam__exam_date__lte=date_to
        )
        
        total_assignments = assignments.count()
        confirmed = assignments.filter(status=InvigilationAssignment.CONFIRMED).count()
        
        avg_per_faculty = round(total_assignments / faculty_count, 1) if faculty_count > 0 else 0
        
        dept_data.append({
            'department': dept,
            'total_exams': exams.count(),
            'faculty_count': faculty_count,
            'total_assignments': total_assignments,
            'confirmed_assignments': confirmed,
            'avg_per_faculty': avg_per_faculty
        })
    
    context = {
        'dept_data': dept_data,
        'date_from': date_from,
        'date_to': date_to,
    }
    
    return render(request, 'exams/department_statistics.html', context)
