import csv
import io

from django.contrib import messages
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.auth.decorators import login_required
from django.db.models import Case, IntegerField, When
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from accounts.models import Faculty
from leaves.models import FacultyLeave

from .forms import CourseForm, FacultyTimeSlotForm, TimetableUploadForm
from .models import Course, FacultyTimeSlot


@staff_member_required
def upload_timetable(request):
    """Admin view to upload faculty timetables via CSV."""

    if request.method == "POST":
        form = TimetableUploadForm(request.POST, request.FILES)
        if form.is_valid():
            file = form.cleaned_data["file"]
            decoded = file.read().decode("utf-8")
            reader = csv.DictReader(io.StringIO(decoded))

            created = 0
            for row in reader:
                emp_id = row.get("employee_id", "").strip()
                day = row.get("day", "").strip().upper()[:3]
                start = row.get("start_time", "").strip()
                end = row.get("end_time", "").strip()
                course_code = row.get("course_code", "").strip()
                course_name = row.get("course_name", "").strip()
                year_str = row.get("year", "").strip()
                is_lab_str = row.get("is_lab", "").strip().lower()

                if not (emp_id and day and start and end):
                    continue

                try:
                    faculty = Faculty.objects.get(employee_id=emp_id)
                except Faculty.DoesNotExist:
                    continue

                year_val = int(year_str) if year_str.isdigit() else None

                FacultyTimeSlot.objects.create(
                    faculty=faculty,
                    day_of_week=day,
                    start_time=start,
                    end_time=end,
                    course_code=course_code,
                    course_name=course_name,
                    year=year_val,
                    is_lab=is_lab_str in {"1", "true", "yes"},
                )
                created += 1

            messages.success(request, f"Uploaded timetable. Created {created} slots.")
            return redirect("exams:admin_dashboard")
    else:
        form = TimetableUploadForm()

    return render(request, "timetable/upload_timetable.html", {"form": form})


@staff_member_required
def manage_courses(request):
    """Admin view to manage courses with edit/delete functionality and filters."""
    from django.core.paginator import Paginator
    from django.db.models import Q

    # Get filter parameters
    department_filter = request.GET.get('department', '')
    year_filter = request.GET.get('year', '')
    semester_filter = request.GET.get('semester', '')
    search_query = request.GET.get('search', '')

    # Start with all courses
    courses = Course.objects.all().select_related('department')

    # Apply filters
    if department_filter:
        courses = courses.filter(department_id=department_filter)
    if year_filter:
        courses = courses.filter(year=year_filter)
    if semester_filter:
        courses = courses.filter(semester=semester_filter)
    if search_query:
        courses = courses.filter(
            Q(code__icontains=search_query) | Q(name__icontains=search_query)
        )

    # Order results
    courses = courses.order_by('department__code', 'year', 'semester', 'code')
    
    # Add pagination
    paginator = Paginator(courses, 50)
    page_number = request.GET.get('page')
    courses = paginator.get_page(page_number)

    # Get departments for filter dropdown
    from exams.models import Department
    departments = Department.objects.all().order_by('name')

    context = {
        'courses': courses,
        'departments': departments,
        'department_filter': department_filter,
        'year_filter': year_filter,
        'semester_filter': semester_filter,
        'search_query': search_query,
    }

    return render(request, "timetable/manage_courses.html", context)


@staff_member_required
def view_courses(request):
    """View-only course listing with filters."""
    from django.core.paginator import Paginator
    from django.db.models import Q

    # Get filter parameters
    department_filter = request.GET.get('department', '')
    year_filter = request.GET.get('year', '')
    semester_filter = request.GET.get('semester', '')
    search_query = request.GET.get('search', '')

    # Start with all courses
    courses = Course.objects.all().select_related('department')

    # Apply filters
    if department_filter:
        courses = courses.filter(department_id=department_filter)
    if year_filter:
        courses = courses.filter(year=year_filter)
    if semester_filter:
        courses = courses.filter(semester=semester_filter)
    if search_query:
        courses = courses.filter(
            Q(code__icontains=search_query) | Q(name__icontains=search_query)
        )

    # Order results
    courses = courses.order_by('department__code', 'year', 'semester', 'code')
    
    # Add pagination
    paginator = Paginator(courses, 50)
    page_number = request.GET.get('page')
    courses = paginator.get_page(page_number)

    # Get departments for filter dropdown
    from exams.models import Department
    departments = Department.objects.all().order_by('name')

    context = {
        'courses': courses,
        'departments': departments,
        'department_filter': department_filter,
        'year_filter': year_filter,
        'semester_filter': semester_filter,
        'search_query': search_query,
    }

    return render(request, "timetable/view_courses.html", context)


@staff_member_required
def add_courses_batch(request):
    """Batch course creation interface similar to faculty batch creation."""
    from exams.models import Department
    
    if request.method == "POST":
        action = request.POST.get('action')
        
        if action == 'add_row':
            # Return a new row for AJAX
            row_index = int(request.POST.get('row_index', 0))
            departments = Department.objects.all().order_by('name')
            return render(request, 'timetable/partials/course_batch_row.html', {
                'departments': departments,
                'row_index': row_index
            })
        
        elif action == 'create':
            # Process batch course creation
            courses_created = 0
            errors = []
            
            # Get all form data
            row_count = 0
            while f'department_{row_count}' in request.POST:
                try:
                    department_id = request.POST.get(f'department_{row_count}')
                    year = request.POST.get(f'year_{row_count}')
                    semester = request.POST.get(f'semester_{row_count}')
                    code = request.POST.get(f'code_{row_count}')
                    name = request.POST.get(f'name_{row_count}')
                    
                    # Skip empty rows
                    if not all([department_id, year, semester, code, name]):
                        row_count += 1
                        continue
                    
                    # Create course
                    course, created = Course.objects.get_or_create(
                        department_id=department_id,
                        code=code,
                        year=int(year),
                        semester=int(semester),
                        defaults={'name': name}
                    )
                    
                    if created:
                        courses_created += 1
                    else:
                        # Update name if course exists
                        if course.name != name:
                            course.name = name
                            course.save()
                        
                except Exception as e:
                    errors.append(f"Row {row_count + 1}: {str(e)}")
                
                row_count += 1
            
            if courses_created > 0:
                messages.success(request, f"Successfully created {courses_created} courses.")
            if errors:
                for error in errors:
                    messages.error(request, error)
            
            return redirect('timetable:add_courses_batch')
    
    # GET request - show the form
    departments = Department.objects.all().order_by('name')
    return render(request, 'timetable/add_courses_batch.html', {'departments': departments})


@staff_member_required
def delete_course(request, pk):
    """Delete a course"""
    course = get_object_or_404(Course, pk=pk)
    
    if request.method == "POST":
        course_name = f"{course.code} - {course.name}"
        course.delete()
        messages.success(request, f"Course '{course_name}' deleted successfully.")
        return redirect("timetable:manage_courses")
    
    return render(request, "timetable/delete_course.html", {"course": course})


@staff_member_required
def edit_course(request, pk):
    """Edit a course"""
    course = get_object_or_404(Course, pk=pk)
    
    if request.method == "POST":
        form = CourseForm(request.POST, instance=course)
        if form.is_valid():
            form.save()
            messages.success(request, f"Course '{course.code}' updated successfully.")
            return redirect("timetable:manage_courses")
    else:
        form = CourseForm(instance=course)
    
    return render(request, "timetable/edit_course.html", {"form": form, "course": course})


@login_required
def faculty_timetable(request):
    """Faculty view of their own timetable."""

    try:
        faculty = request.user.faculty_profile
    except Faculty.DoesNotExist:  # type: ignore[attr-defined]
        messages.error(request, "You do not have a faculty profile configured.")
        return redirect("accounts:dashboard")

    day_order = Case(
        When(day_of_week="MON", then=0),
        When(day_of_week="TUE", then=1),
        When(day_of_week="WED", then=2),
        When(day_of_week="THU", then=3),
        When(day_of_week="FRI", then=4),
        When(day_of_week="SAT", then=5),
        When(day_of_week="SUN", then=6),
        output_field=IntegerField(),
    )

    slots = (
        FacultyTimeSlot.objects.filter(faculty=faculty)
        .annotate(day_order=day_order)
        .order_by("day_order", "start_time")
    )

    today = timezone.localdate()
    approved_leaves = (
        FacultyLeave.objects.filter(
            faculty=faculty,
            status=FacultyLeave.APPROVED,
            end_date__gte=today,
        )
        .order_by("start_date")
    )

    # Define the fixed days and time slots for the grid view
    days = [
        ("MON", "Monday"),
        ("TUE", "Tuesday"),
        ("WED", "Wednesday"),
        ("THU", "Thursday"),
        ("FRI", "Friday"),
        ("SAT", "Saturday"),
    ]

    time_slots = [
        ("09:30-10:30", "9:30 - 10:30"),
        ("10:30-11:30", "10:30 - 11:30"),
        ("11:30-12:30", "11:30 - 12:30"),
        ("12:30-13:30", "12:30 - 1:30 (LUNCH)"),
        ("13:30-14:30", "1:30 - 2:30"),
        ("14:30-15:30", "2:30 - 3:30"),
        ("15:30-16:30", "3:30 - 4:30"),
    ]

    # Build a grid mapping day -> slot label -> list of FacultyTimeSlot objects
    grid = {day_code: {key: [] for key, _ in time_slots} for day_code, _ in days}

    for s in slots:
        # Build a key like "HH:MM-HH:MM" from the stored times
        key = f"{s.start_time.strftime('%H:%M')}-{s.end_time.strftime('%H:%M')}"
        if s.day_of_week in grid and key in grid[s.day_of_week]:
            grid[s.day_of_week][key].append(s)

    context = {
        "days": days,
        "time_slots": time_slots,
        "grid": grid,
        "approved_leaves": approved_leaves,
    }
    return render(request, "timetable/faculty_timetable.html", context)


@login_required
def add_slot(request):
    try:
        faculty = request.user.faculty_profile
    except Faculty.DoesNotExist:  # type: ignore[attr-defined]
        messages.error(request, "You do not have a faculty profile configured.")
        return redirect("accounts:dashboard")

    if request.method == "POST":
        form = FacultyTimeSlotForm(request.POST)
        if form.is_valid():
            day = form.cleaned_data["day_of_week"]
            start = form.cleaned_data["start_time"]
            end = form.cleaned_data["end_time"]

            # Prevent overlapping slots for the same faculty and day
            conflict_qs = FacultyTimeSlot.objects.filter(faculty=faculty, day_of_week=day)
            for existing in conflict_qs:
                if existing.start_time < end and start < existing.end_time:
                    form.add_error(
                        None,
                        "This time overlaps with an existing slot on this day ("
                        f"{existing.start_time}–{existing.end_time}).",
                    )
                    break

            if not form.errors:
                slot = form.save(commit=False)
                slot.faculty = faculty
                slot.save()
                messages.success(request, "Time slot added to your timetable.")
                return redirect("timetable:faculty_timetable")
    else:
        form = FacultyTimeSlotForm()

    return render(request, "timetable/add_slot.html", {"form": form})


@login_required
def delete_slot(request, pk):
    try:
        faculty = request.user.faculty_profile
    except Faculty.DoesNotExist:  # type: ignore[attr-defined]
        messages.error(request, "You do not have a faculty profile configured.")
        return redirect("accounts:dashboard")

    slot = get_object_or_404(FacultyTimeSlot, pk=pk, faculty=faculty)
    if request.method == "POST":
        slot.delete()
        messages.success(request, "Time slot removed from your timetable.")
        return redirect("timetable:faculty_timetable")

    return render(request, "timetable/confirm_delete_slot.html", {"slot": slot})


@login_required
def faculty_timetable_grid(request):
    """Interactive grid view of faculty timetable"""
    import json
    from exams.models import Department
    
    try:
        faculty = request.user.faculty_profile
    except Faculty.DoesNotExist:
        messages.error(request, "You do not have a faculty profile configured.")
        return redirect("accounts:dashboard")
    
    slots = FacultyTimeSlot.objects.filter(faculty=faculty).select_related('department')
    departments = Department.objects.all().order_by('name')
    
    # Convert slots to JSON for JavaScript
    slots_data = []
    for slot in slots:
        slots_data.append({
            'id': slot.id,
            'day_of_week': slot.day_of_week,
            'start_time': slot.start_time.strftime('%H:%M'),
            'end_time': slot.end_time.strftime('%H:%M'),
            'department': slot.department.id if slot.department else '',
            'course_code': slot.course_code,
            'course_name': slot.course_name,
            'year': slot.year,
            'semester': slot.semester,
            'is_lab': slot.is_lab
        })
    
    context = {
        'slots_json': json.dumps(slots_data),
        'departments': departments,
        'departments_json': json.dumps([{'id': d.id, 'code': d.code, 'name': d.name} for d in departments])
    }
    return render(request, 'timetable/faculty_timetable_grid.html', context)


@login_required
def api_slot_create(request):
    """API endpoint to create a timetable slot"""
    from django.http import JsonResponse
    from logs.models import FacultyActionLog
    from datetime import datetime
    from exams.models import Department
    
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'Method not allowed'}, status=405)
    
    try:
        faculty = request.user.faculty_profile
    except Faculty.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'No faculty profile'}, status=403)
    
    try:
        day_of_week = request.POST.get('day_of_week')
        start_time_str = request.POST.get('start_time')
        end_time_str = request.POST.get('end_time')
        department_id = request.POST.get('department')
        course_code = request.POST.get('course_code')
        course_name = request.POST.get('course_name')
        year = request.POST.get('year')
        semester = request.POST.get('semester')
        is_lab = request.POST.get('is_lab') == 'on'
        
        # Parse times for overlap check
        start_time = datetime.strptime(start_time_str, '%H:%M').time()
        end_time = datetime.strptime(end_time_str, '%H:%M').time()
        
        # Get department
        department = Department.objects.get(id=department_id)
        
        # Check for overlapping slots
        overlapping = FacultyTimeSlot.objects.filter(
            faculty=faculty,
            day_of_week=day_of_week,
            start_time__lt=end_time,
            end_time__gt=start_time
        ).exists()
        
        if overlapping:
            return JsonResponse({
                'success': False,
                'error': 'This time slot overlaps with an existing class'
            }, status=400)
        
        # Create slot
        slot = FacultyTimeSlot.objects.create(
            faculty=faculty,
            day_of_week=day_of_week,
            start_time=start_time,
            end_time=end_time,
            department=department,
            course_code=course_code,
            course_name=course_name,
            year=int(year) if year else None,
            semester=int(semester) if semester else None,
            is_lab=is_lab
        )
        
        # Log action
        FacultyActionLog.objects.create(
            faculty=faculty,
            action_type='TIMETABLE_ADD',
            description=f"Added class: {course_code} ({department.code} Y{year}S{semester}) on {day_of_week} {start_time_str}-{end_time_str}"
        )
        
        return JsonResponse({'success': True, 'slot_id': slot.id})
    
    except Department.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Department not found'}, status=400)
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=400)


@login_required
def api_slot_update(request, pk):
    """API endpoint to update a timetable slot"""
    from django.http import JsonResponse
    from logs.models import FacultyActionLog
    from exams.models import Department
    
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'Method not allowed'}, status=405)
    
    try:
        faculty = request.user.faculty_profile
    except Faculty.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'No faculty profile'}, status=403)
    
    try:
        slot = FacultyTimeSlot.objects.get(pk=pk, faculty=faculty)
        
        department_id = request.POST.get('department')
        if department_id:
            department = Department.objects.get(id=department_id)
            slot.department = department
        
        slot.course_code = request.POST.get('course_code')
        slot.course_name = request.POST.get('course_name')
        slot.year = int(request.POST.get('year')) if request.POST.get('year') else None
        slot.semester = int(request.POST.get('semester')) if request.POST.get('semester') else None
        slot.is_lab = request.POST.get('is_lab') == 'on'
        slot.save()
        
        # Log action
        FacultyActionLog.objects.create(
            faculty=faculty,
            action_type='TIMETABLE_UPDATE',
            description=f"Updated class: {slot.course_code} ({slot.department.code if slot.department else 'N/A'} Y{slot.year}S{slot.semester}) on {slot.day_of_week} {slot.start_time}-{slot.end_time}"
        )
        
        return JsonResponse({'success': True})
    
    except FacultyTimeSlot.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Slot not found'}, status=404)
    except Department.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Department not found'}, status=400)
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=400)


@login_required
def api_slot_delete(request, pk):
    """API endpoint to delete a timetable slot"""
    from django.http import JsonResponse
    from logs.models import FacultyActionLog
    
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'Method not allowed'}, status=405)
    
    try:
        faculty = request.user.faculty_profile
    except Faculty.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'No faculty profile'}, status=403)
    
    try:
        slot = FacultyTimeSlot.objects.get(pk=pk, faculty=faculty)
        
        # Log action before deleting
        FacultyActionLog.objects.create(
            faculty=faculty,
            action_type='TIMETABLE_DELETE',
            description=f"Deleted class: {slot.course_code} on {slot.day_of_week} {slot.start_time}-{slot.end_time}"
        )
        
        slot.delete()
        
        return JsonResponse({'success': True})
    
    except FacultyTimeSlot.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Slot not found'}, status=404)
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=400)


@staff_member_required
def admin_view_faculty_timetables(request):
    """Admin view to browse all faculty timetables with filters."""
    from django.core.paginator import Paginator
    from django.db.models import Q

    # Get filter parameters
    department_filter = request.GET.get('department', '')
    faculty_filter = request.GET.get('faculty', '')
    search_query = request.GET.get('search', '')

    # Start with all faculty
    faculty_list = Faculty.objects.all().select_related('department', 'user').prefetch_related('timetable_slots')

    # Apply filters
    if department_filter:
        faculty_list = faculty_list.filter(department_id=department_filter)
    if faculty_filter:
        faculty_list = faculty_list.filter(id=faculty_filter)
    if search_query:
        faculty_list = faculty_list.filter(
            Q(user__first_name__icontains=search_query) | 
            Q(user__last_name__icontains=search_query) |
            Q(employee_id__icontains=search_query)
        )

    # Order results
    faculty_list = faculty_list.order_by('department__code', 'user__first_name', 'user__last_name')
    
    # Add pagination
    paginator = Paginator(faculty_list, 20)
    page_number = request.GET.get('page')
    faculty_list = paginator.get_page(page_number)

    # Get departments for filter dropdown
    from exams.models import Department
    departments = Department.objects.all().order_by('name')
    
    # Get all faculty for faculty filter dropdown
    all_faculty = Faculty.objects.all().select_related('user', 'department').order_by('user__first_name', 'user__last_name')

    context = {
        'faculty_list': faculty_list,
        'departments': departments,
        'all_faculty': all_faculty,
        'department_filter': department_filter,
        'faculty_filter': faculty_filter,
        'search_query': search_query,
    }

    return render(request, "timetable/admin_view_faculty_timetables.html", context)


@staff_member_required
def admin_add_faculty_timetable(request):
    """Admin interface to add/edit faculty timetables using grid interface."""
    from exams.models import Department
    from django.http import JsonResponse
    import json
    
    # Get departments for dropdown
    departments = Department.objects.all().order_by('name')
    
    # Handle AJAX requests for faculty list
    if request.method == "POST" and request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        department_id = request.POST.get('department_id')
        if department_id:
            faculty_list = Faculty.objects.filter(department_id=department_id).select_related('user').order_by('user__first_name', 'user__last_name')
            faculty_data = [{'id': f.id, 'name': f.user.get_full_name() or f.user.username, 'employee_id': f.employee_id} for f in faculty_list]
            return JsonResponse({'faculty': faculty_data})
        return JsonResponse({'faculty': []})
    
    # Handle faculty selection
    selected_faculty = None
    faculty_slots = []
    if request.GET.get('faculty_id'):
        try:
            selected_faculty = Faculty.objects.select_related('user', 'department').get(id=request.GET.get('faculty_id'))
            # Get existing slots for this faculty
            slots = FacultyTimeSlot.objects.filter(faculty=selected_faculty).select_related('department')
            
            # Convert slots to JSON for JavaScript
            faculty_slots = []
            for slot in slots:
                faculty_slots.append({
                    'id': slot.id,
                    'day_of_week': slot.day_of_week,
                    'start_time': slot.start_time.strftime('%H:%M'),
                    'end_time': slot.end_time.strftime('%H:%M'),
                    'department': slot.department.id if slot.department else '',
                    'course_code': slot.course_code,
                    'course_name': slot.course_name,
                    'year': slot.year,
                    'semester': slot.semester,
                    'is_lab': slot.is_lab
                })
        except Faculty.DoesNotExist:
            pass

    context = {
        'departments': departments,
        'selected_faculty': selected_faculty,
        'faculty_slots_json': json.dumps(faculty_slots),
    }

    return render(request, "timetable/admin_add_faculty_timetable.html", context)


@staff_member_required
def admin_api_slot_create(request):
    """Admin API endpoint to create a timetable slot for any faculty"""
    from django.http import JsonResponse
    from logs.models import AdminActionLog
    from datetime import datetime
    from exams.models import Department
    
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'Method not allowed'}, status=405)
    
    try:
        faculty_id = request.POST.get('faculty_id')
        if not faculty_id:
            return JsonResponse({'success': False, 'error': 'Faculty ID required'}, status=400)
        
        faculty = Faculty.objects.get(id=faculty_id)
        
        day_of_week = request.POST.get('day_of_week')
        start_time_str = request.POST.get('start_time')
        end_time_str = request.POST.get('end_time')
        department_id = request.POST.get('department')
        course_code = request.POST.get('course_code')
        course_name = request.POST.get('course_name')
        year = request.POST.get('year')
        semester = request.POST.get('semester')
        is_lab = request.POST.get('is_lab') == 'on'
        
        # Parse times for overlap check
        start_time = datetime.strptime(start_time_str, '%H:%M').time()
        end_time = datetime.strptime(end_time_str, '%H:%M').time()
        
        # Get department
        department = Department.objects.get(id=department_id)
        
        # Check for overlapping slots
        overlapping = FacultyTimeSlot.objects.filter(
            faculty=faculty,
            day_of_week=day_of_week,
            start_time__lt=end_time,
            end_time__gt=start_time
        ).exists()
        
        if overlapping:
            return JsonResponse({
                'success': False,
                'error': 'This time slot overlaps with an existing class'
            }, status=400)
        
        # Create slot
        slot = FacultyTimeSlot.objects.create(
            faculty=faculty,
            day_of_week=day_of_week,
            start_time=start_time,
            end_time=end_time,
            department=department,
            course_code=course_code,
            course_name=course_name,
            year=int(year) if year else None,
            semester=int(semester) if semester else None,
            is_lab=is_lab
        )
        
        # Log admin action
        AdminActionLog.objects.create(
            user=request.user,
            action_type='TIMETABLE_ADD',
            description=f"Added class for {faculty.user.get_full_name()} ({faculty.employee_id}): {course_code} ({department.code} Y{year}S{semester}) on {day_of_week} {start_time_str}-{end_time_str}",
            ip_address=request.META.get('REMOTE_ADDR'),
            user_agent=request.META.get('HTTP_USER_AGENT', '')[:200]
        )
        
        return JsonResponse({'success': True, 'slot_id': slot.id})
    
    except Faculty.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Faculty not found'}, status=400)
    except Department.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Department not found'}, status=400)
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=400)


@staff_member_required
def admin_api_slot_update(request, pk):
    """Admin API endpoint to update a timetable slot"""
    from django.http import JsonResponse
    from logs.models import AdminActionLog
    from exams.models import Department
    
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'Method not allowed'}, status=405)
    
    try:
        slot = FacultyTimeSlot.objects.get(pk=pk)
        
        department_id = request.POST.get('department')
        if department_id:
            department = Department.objects.get(id=department_id)
            slot.department = department
        
        slot.course_code = request.POST.get('course_code')
        slot.course_name = request.POST.get('course_name')
        slot.year = int(request.POST.get('year')) if request.POST.get('year') else None
        slot.semester = int(request.POST.get('semester')) if request.POST.get('semester') else None
        slot.is_lab = request.POST.get('is_lab') == 'on'
        slot.save()
        
        # Log admin action
        AdminActionLog.objects.create(
            user=request.user,
            action_type='TIMETABLE_UPDATE',
            description=f"Updated class for {slot.faculty.user.get_full_name()} ({slot.faculty.employee_id}): {slot.course_code} ({slot.department.code if slot.department else 'N/A'} Y{slot.year}S{slot.semester}) on {slot.day_of_week} {slot.start_time}-{slot.end_time}",
            ip_address=request.META.get('REMOTE_ADDR'),
            user_agent=request.META.get('HTTP_USER_AGENT', '')[:200]
        )
        
        return JsonResponse({'success': True})
    
    except FacultyTimeSlot.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Slot not found'}, status=404)
    except Department.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Department not found'}, status=400)
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=400)


@staff_member_required
def admin_api_slot_delete(request, pk):
    """Admin API endpoint to delete a timetable slot"""
    from django.http import JsonResponse
    from logs.models import AdminActionLog
    
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'Method not allowed'}, status=405)
    
    try:
        slot = FacultyTimeSlot.objects.get(pk=pk)
        
        # Log admin action before deleting
        AdminActionLog.objects.create(
            user=request.user,
            action_type='TIMETABLE_DELETE',
            description=f"Deleted class for {slot.faculty.user.get_full_name()} ({slot.faculty.employee_id}): {slot.course_code} on {slot.day_of_week} {slot.start_time}-{slot.end_time}",
            ip_address=request.META.get('REMOTE_ADDR'),
            user_agent=request.META.get('HTTP_USER_AGENT', '')[:200]
        )
        
        slot.delete()
        
        return JsonResponse({'success': True})
    
    except FacultyTimeSlot.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Slot not found'}, status=404)
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=400)

@staff_member_required
def admin_view_faculty_timetable(request, faculty_id):
    """Admin view to see a specific faculty's timetable in read-only mode"""
    from django.db.models import Case, IntegerField, When
    from leaves.models import FacultyLeave
    
    try:
        faculty = Faculty.objects.select_related('user', 'department').get(id=faculty_id)
    except Faculty.DoesNotExist:
        messages.error(request, "Faculty not found.")
        return redirect('timetable:admin_view_faculty_timetables')

    day_order = Case(
        When(day_of_week="MON", then=0),
        When(day_of_week="TUE", then=1),
        When(day_of_week="WED", then=2),
        When(day_of_week="THU", then=3),
        When(day_of_week="FRI", then=4),
        When(day_of_week="SAT", then=5),
        When(day_of_week="SUN", then=6),
        output_field=IntegerField(),
    )

    slots = (
        FacultyTimeSlot.objects.filter(faculty=faculty)
        .annotate(day_order=day_order)
        .order_by("day_order", "start_time")
        .select_related('department')
    )

    today = timezone.localdate()
    approved_leaves = (
        FacultyLeave.objects.filter(
            faculty=faculty,
            status=FacultyLeave.APPROVED,
            end_date__gte=today,
        )
        .order_by("start_date")
    )

    # Define the fixed days and time slots for the grid view
    days = [
        ("MON", "Monday"),
        ("TUE", "Tuesday"),
        ("WED", "Wednesday"),
        ("THU", "Thursday"),
        ("FRI", "Friday"),
        ("SAT", "Saturday"),
    ]

    time_slots = [
        ("09:30-10:30", "9:30 - 10:30"),
        ("10:30-11:30", "10:30 - 11:30"),
        ("11:30-12:30", "11:30 - 12:30"),
        ("12:30-13:30", "12:30 - 1:30 (LUNCH)"),
        ("13:30-14:30", "1:30 - 2:30"),
        ("14:30-15:30", "2:30 - 3:30"),
        ("15:30-16:30", "3:30 - 4:30"),
    ]

    # Build a grid mapping day -> slot label -> list of FacultyTimeSlot objects
    grid = {day_code: {key: [] for key, _ in time_slots} for day_code, _ in days}

    for s in slots:
        # Build a key like "HH:MM-HH:MM" from the stored times
        key = f"{s.start_time.strftime('%H:%M')}-{s.end_time.strftime('%H:%M')}"
        if s.day_of_week in grid and key in grid[s.day_of_week]:
            grid[s.day_of_week][key].append(s)

    context = {
        "faculty": faculty,
        "days": days,
        "time_slots": time_slots,
        "grid": grid,
        "approved_leaves": approved_leaves,
        "is_admin_view": True,  # Flag to indicate this is admin view
        "lab_sessions_count": slots.filter(is_lab=True).count(),
        "total_slots_count": slots.count(),
    }
    return render(request, "timetable/admin_view_faculty_timetable.html", context)