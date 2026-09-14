from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.auth import get_user_model
from django.contrib import messages
from django.http import HttpResponse, JsonResponse
from django.utils import timezone
from django.db.models import Prefetch
from .models import Exam, Department, ExamSessionHall, InvigilationAssignment
from accounts.models import Faculty
from leaves.models import FacultyLeave
from timetable.models import FacultyTimeSlot, Course
from .forms import ExamTimetableUploadForm, ExamCreateForm
from datetime import datetime, timedelta
import json
import csv

User = get_user_model()

from django.contrib import messages
from django.db.models import Count, Q
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from accounts.models import Faculty
from leaves.models import FacultyLeave
from timetable.models import FacultyTimeSlot

from .forms import ExamTimetableUploadForm
from .models import Department, Exam, ExamHall, ExamSessionHall, InvigilationAssignment


@staff_member_required
def admin_dashboard(request):
    # Ensure default departments exist
    if not Department.objects.exists():
        Department.objects.bulk_create(
            [
                Department(code="CSE", name="Computer Science and Engineering"),
                Department(code="CSM", name="Computer Science and AI/ML"),
                Department(code="CSD", name="Computer Science and Data Science"),
                Department(code="ECE", name="Electronics and Communication Engineering"),
                Department(code="EEE", name="Electrical and Electronics Engineering"),
                Department(code="MECH", name="Mechanical Engineering"),
                Department(code="CIVIL", name="Civil Engineering"),
            ]
        )

    today = timezone.localdate()
    upcoming_exams = Exam.objects.filter(exam_date__gte=today).order_by("exam_date", "start_time")[:10]

    pending_assignments = InvigilationAssignment.objects.filter(
        status=InvigilationAssignment.PENDING_CONFIRMATION
    ).select_related("exam_session_hall__exam")

    # Calculate comprehensive statistics
    total_faculty_count = Faculty.objects.filter(is_active=True).count()
    first_login_count = Faculty.objects.filter(must_change_password=True, is_active=True).count()
    upcoming_exams_count = Exam.objects.filter(exam_date__gte=today).count()
    today_exams_count = Exam.objects.filter(exam_date=today).count()
    pending_assignments_count = pending_assignments.count()
    
    # Additional statistics
    total_departments = Department.objects.count()
    total_exams = Exam.objects.count()
    completed_exams = Exam.objects.filter(exam_date__lt=today).count()

    context = {
        "upcoming_exams_count": upcoming_exams_count,
        "today_exams_count": today_exams_count,
        "pending_assignments_count": pending_assignments_count,
        "upcoming_exams": upcoming_exams,
        "total_faculty_count": total_faculty_count,
        "first_login_count": first_login_count,
        "total_departments": total_departments,
        "total_exams": total_exams,
        "completed_exams": completed_exams,
        "today": today,
    }
    return render(request, "exams/admin_dashboard.html", context)


@staff_member_required
def upload_exam_timetable(request):
    """Upload exam timetable (exam schedule) via CSV."""

    if request.method == "POST":
        form = ExamTimetableUploadForm(request.POST, request.FILES)
        if form.is_valid():
            file = form.cleaned_data["file"]
            decoded = file.read().decode("utf-8")
            reader = csv.DictReader(decoded.splitlines())

            created = 0
            for row in reader:
                dept_code = row.get("department_code", "").strip().upper()
                course_code = row.get("course_code", "").strip()
                course_name = row.get("course_name", "").strip()
                exam_type = row.get("exam_type", "").strip().upper() or Exam.TEST
                year = row.get("year", "").strip()
                semester = row.get("semester", "").strip()
                exam_date = row.get("exam_date", "").strip()
                start_time = row.get("start_time", "").strip()
                end_time = row.get("end_time", "").strip()

                if not (dept_code and course_code and exam_date and start_time and end_time and year and semester):
                    continue

                try:
                    department = Department.objects.get(code=dept_code)
                except Department.DoesNotExist:
                    continue

                Exam.objects.create(
                    course_code=course_code,
                    course_name=course_name or course_code,
                    exam_type=exam_type,
                    department=department,
                    year=int(year),
                    semester=int(semester),
                    exam_date=exam_date,
                    start_time=start_time,
                    end_time=end_time,
                    created_by=request.user,
                )
                created += 1

            messages.success(request, f"Exam timetable uploaded. Created {created} exams.")
            return redirect("exams:exam_list")
    else:
        form = ExamTimetableUploadForm()

    return render(request, "exams/upload_exam_timetable.html", {"form": form})


@staff_member_required
def create_exam(request):
    """Create a single exam via UI form."""
    
    if request.method == "POST":
        form = ExamCreateForm(request.POST)
        if form.is_valid():
            # Get the course to populate course_name
            try:
                course = Course.objects.get(
                    code=form.cleaned_data['course_code'],
                    department=form.cleaned_data['department'],
                    year=form.cleaned_data['year'],
                    semester=form.cleaned_data['semester']
                )
                course_name = course.name
            except Course.DoesNotExist:
                course_name = form.cleaned_data['course_code']
            
            exam = form.save(commit=False)
            exam.course_name = course_name
            exam.created_by = request.user
            exam.save()
            messages.success(request, f"Exam '{exam.course_code} - {exam.course_name}' created successfully.")
            return redirect("exams:exam_list")
    else:
        form = ExamCreateForm()

    return render(request, "exams/create_exam.html", {"form": form})


@staff_member_required
def create_exam_batch(request):
    """Create multiple exams at once"""
    import json
    from datetime import datetime
    from django.db import transaction
    
    departments = Department.objects.all().order_by('code')
    departments_json = json.dumps([{'id': d.id, 'code': d.code, 'name': d.name} for d in departments])
    
    if request.method == "POST":
        created_count = 0
        errors = []
        
        # Parse the form data
        exam_data = {}
        for key, value in request.POST.items():
            if key.startswith('exams['):
                # Parse exams[0][department] format
                parts = key.replace('exams[', '').replace(']', '').split('[')
                if len(parts) == 2:
                    index, field = parts
                    if index not in exam_data:
                        exam_data[index] = {}
                    exam_data[index][field] = value
        
        try:
            with transaction.atomic():
                # Create exams
                for index, data in exam_data.items():
                    try:
                        # Validate required fields
                        required_fields = ['department', 'year', 'semester', 'course_code', 
                                         'exam_type', 'exam_date', 'start_time', 'end_time']
                        missing = [f for f in required_fields if not data.get(f)]
                        if missing:
                            errors.append(f"Row {int(index)+1}: Missing fields: {', '.join(missing)}")
                            continue
                        
                        # Get department
                        department = Department.objects.get(id=data['department'])
                        
                        # Lookup course name from Course model
                        course_code = data['course_code']
                        try:
                            course = Course.objects.get(
                                code=course_code,
                                department=department,
                                year=int(data['year']),
                                semester=int(data['semester'])
                            )
                            course_name = course.name
                        except Course.DoesNotExist:
                            # Fallback to provided course_name or course_code
                            course_name = data.get('course_name', course_code)
                        
                        # Parse date and time
                        exam_date = datetime.strptime(data['exam_date'], '%Y-%m-%d').date()
                        start_time = datetime.strptime(data['start_time'], '%H:%M').time()
                        end_time = datetime.strptime(data['end_time'], '%H:%M').time()
                        
                        # Create exam
                        exam = Exam.objects.create(
                            course_code=course_code,
                            course_name=course_name,
                            exam_type=data['exam_type'],
                            department=department,
                            year=int(data['year']),
                            semester=int(data['semester']),
                            exam_date=exam_date,
                            start_time=start_time,
                            end_time=end_time,
                            created_by=request.user
                        )
                        created_count += 1
                        
                    except Department.DoesNotExist:
                        errors.append(f"Row {int(index)+1}: Invalid department")
                    except ValueError as e:
                        errors.append(f"Row {int(index)+1}: Invalid date/time format - {str(e)}")
                    except Exception as e:
                        errors.append(f"Row {int(index)+1}: Error - {str(e)}")
                
                # If there are errors, rollback by raising exception
                if errors:
                    raise Exception("Validation errors occurred")
                
                # Show success message
                messages.success(request, f"Successfully created {created_count} exam(s)!")
                return redirect("exams:exam_list")
                
        except Exception as e:
            # Show errors
            if errors:
                for error in errors:
                    messages.error(request, error)
            else:
                messages.error(request, f"Error creating exams: {str(e)}")
    
    context = {
        'departments_json': departments_json,
    }
    return render(request, "exams/create_exam_batch.html", context)


@login_required
def api_courses(request):
    """API endpoint to fetch courses by department, year and semester."""
    department_id = request.GET.get('department')
    year = request.GET.get('year')
    semester = request.GET.get('semester')
    
    print(f"API called with: department={department_id}, year={year}, semester={semester}")
    
    if not department_id or not year or not semester:
        print("Missing parameters")
        return JsonResponse({'courses': []})
    
    try:
        department_id = int(department_id)
        year = int(year)
        semester = int(semester)
        print(f"Parsed: department_id={department_id}, year={year}, semester={semester}")
        
        courses = Course.objects.filter(
            department_id=department_id, 
            year=year, 
            semester=semester
        ).values('code', 'name')
        
        courses_list = list(courses)
        print(f"Found courses: {courses_list}")
        
        return JsonResponse({'courses': courses_list})
    except (ValueError, TypeError) as e:
        print(f"Error parsing parameters: {e}")
        return JsonResponse({'courses': []})


@staff_member_required
def allocation_overview(request):
    """Block-wise overview of invigilation allocations for admins."""

    date_str = request.GET.get("date")
    block = request.GET.get("block", "").strip()

    assignments = (
        InvigilationAssignment.objects.select_related(
            "exam_session_hall__exam",
            "exam_session_hall__hall",
            "faculty__user",
            "faculty__department",
        )
        .filter(status__in=[
            InvigilationAssignment.PENDING_CONFIRMATION,
            InvigilationAssignment.CONFIRMED,
        ])
    )

    if date_str:
        try:
            filter_date = datetime.strptime(date_str, "%Y-%m-%d").date()
            assignments = assignments.filter(exam_session_hall__exam__exam_date=filter_date)
        except ValueError:
            date_str = ""

    if block:
        assignments = assignments.filter(exam_session_hall__hall__block__iexact=block)

    assignments = assignments.order_by(
        "exam_session_hall__exam__exam_date",
        "exam_session_hall__hall__block",
        "exam_session_hall__hall__name",
        "faculty__department__code",
        "faculty__user__last_name",
    )

    # Collect distinct dates and blocks for filter dropdowns
    dates = (
        Exam.objects.order_by("exam_date")
        .values_list("exam_date", flat=True)
        .distinct()
    )
    blocks = (
        ExamSessionHall.objects.select_related("hall")
        .values_list("hall__block", flat=True)
        .distinct()
    )

    context = {
        "assignments": assignments,
        "filter_date": date_str or "",
        "filter_block": block,
        "dates": dates,
        "blocks": blocks,
    }
    return render(request, "exams/allocation_overview.html", context)


@staff_member_required
def manage_departments(request):
    """Simple UI for platform admin to view/add/delete departments."""

    if request.method == "POST":
        # Add new department
        code = request.POST.get("code", "").strip().upper()
        name = request.POST.get("name", "").strip()
        delete_id = request.POST.get("delete_id")

        if delete_id:
            Department.objects.filter(id=delete_id).delete()
        elif code and name:
            Department.objects.get_or_create(code=code, defaults={"name": name})

        return redirect("exams:manage_departments")

    departments = Department.objects.all().order_by("code")
    return render(request, "exams/manage_departments.html", {"departments": departments})


@staff_member_required
def manage_halls(request):
    """Simple UI for platform admin to add/delete exam halls (blocks / rooms)."""

    if request.method == "POST":
        delete_id = request.POST.get("delete_id")
        if delete_id:
            ExamHall.objects.filter(id=delete_id).delete()
            return redirect("exams:manage_halls")

        name = request.POST.get("name", "").strip()
        block = request.POST.get("block", "").strip()
        floor = request.POST.get("floor", "").strip()
        capacity = request.POST.get("capacity", "").strip()

        if name and block:
            try:
                cap_val = int(capacity) if capacity else 0
            except ValueError:
                cap_val = 0
            ExamHall.objects.create(
                name=name,
                block=block,
                floor=floor,
                capacity=cap_val,
                is_active=True,
            )
            messages.success(request, "Hall/room added.")
            return redirect("exams:manage_halls")

    # Order by block, then floor (G/0,1,2,...) and then name
    floor_order = ["G", "GROUND", "0", "1", "2", "3"]
    def floor_key(h):
        f = (h.floor or "").upper()
        try:
            idx = floor_order.index(f)
        except ValueError:
            idx = len(floor_order)
        return (h.block, idx, h.name)

    halls = sorted(ExamHall.objects.all(), key=floor_key)
    return render(request, "exams/manage_halls.html", {"halls": halls})


@staff_member_required
def blocks_list(request):
    """List distinct blocks; clicking a block shows its rooms."""

    blocks = (
        ExamHall.objects.values_list("block", flat=True)
        .distinct()
        .order_by("block")
    )
    return render(request, "exams/blocks_list.html", {"blocks": blocks})


@staff_member_required
def block_detail(request, block_code):
    """Show rooms for a single block, ordered by floor, with faculty cabins info."""

    block_code = block_code.strip()
    halls_qs = ExamHall.objects.filter(block=block_code)

    floor_order = ["G", "GROUND", "0", "1", "2", "3"]

    def floor_key(h):
        f = (h.floor or "").upper()
        try:
            idx = floor_order.index(f)
        except ValueError:
            idx = len(floor_order)
        return (idx, h.name)

    halls = sorted(halls_qs, key=floor_key)

    # Map room name -> list of faculty names for cabins in this block/room
    room_names = [h.name for h in halls]
    faculty_qs = Faculty.objects.filter(cabin_block=block_code, cabin_room__in=room_names).select_related("user")
    faculty_by_room = {}
    for f in faculty_qs:
        key = f.cabin_room
        faculty_by_room.setdefault(key, []).append(f.user.get_full_name() or f.user.username)

    return render(
        request,
        "exams/block_detail.html",
        {"block_code": block_code, "halls": halls, "faculty_by_room": faculty_by_room},
    )


@staff_member_required
def exam_list(request):
    exams = Exam.objects.select_related("department").order_by("exam_date", "start_time")
    return render(request, "exams/exam_list.html", {"exams": exams})


@staff_member_required
def exam_detail(request, pk):
    from exams.models import AllocationSuggestion
    
    exam = get_object_or_404(Exam.objects.select_related("department"), pk=pk)
    session_halls = (
        ExamSessionHall.objects.filter(exam=exam)
        .select_related("hall")
        .prefetch_related(
            Prefetch(
                "assignments",
                queryset=InvigilationAssignment.objects.select_related("faculty__user", "faculty__department"),
            )
        )
        .order_by("hall__block", "hall__floor", "hall__name")
    )

    # Build assignments_by_hall for quick lookup
    assignments_by_hall = {}
    for session in session_halls:
        assignments_by_hall.setdefault(session.hall, list(session.assignments.all()))

    has_assignments = InvigilationAssignment.objects.filter(exam_session_hall__exam=exam).exists()
    
    # Check for pending suggestions
    pending_suggestions_count = AllocationSuggestion.objects.filter(
        exam=exam,
        status=AllocationSuggestion.PENDING
    ).count()

    context = {
        "exam": exam,
        "session_halls": session_halls,
        "assignments_by_hall": assignments_by_hall,
        "has_assignments": has_assignments,
        "pending_suggestions_count": pending_suggestions_count,
    }
    return render(request, "exams/exam_detail.html", context)


@staff_member_required
def configure_exam_halls(request, pk):
    """Step before auto-allocation: choose block and rooms (halls) for this exam.

    Admin selects a block and then marks which rooms in that block are available
    for this exam. We create ExamSessionHall entries accordingly and then run
    the existing auto-allocation logic.
    """

    exam = get_object_or_404(Exam, pk=pk)

    # Preload all halls grouped by block so admin can select rooms from
    # multiple blocks for the same examination in one step.
    blocks = (
        ExamHall.objects.values_list("block", flat=True)
        .distinct()
        .order_by("block")
    )
    halls_by_block = {}
    floor_order = ["G", "GROUND", "0", "1", "2", "3"]

    def floor_key(h):
        f = (h.floor or "").upper()
        try:
            idx = floor_order.index(f)
        except ValueError:
            idx = len(floor_order)
        return (idx, h.name)

    for b in blocks:
        qs = ExamHall.objects.filter(block=b)
        halls_by_block[b] = sorted(qs, key=floor_key)

    if request.method == "POST":
        hall_ids = request.POST.getlist("hall_ids")

        # Clear previous room mappings for this exam
        ExamSessionHall.objects.filter(exam=exam).delete()

        for hid in hall_ids:
            try:
                hall = ExamHall.objects.get(id=hid)
            except ExamHall.DoesNotExist:
                continue
            # Read required invigilators per room (default to 1)
            req_key = f"req_{hid}"
            required = int(request.POST.get(req_key, "1"))
            ExamSessionHall.objects.create(exam=exam, hall=hall, required_invigilators=required)

        if hall_ids:
            messages.success(request, "Rooms selected for this exam. Auto-allocating duties now.")
            return redirect("exams:auto_allocate_for_exam", pk=exam.pk)
        else:
            messages.warning(request, "No rooms selected. Please choose at least one room.")

    context = {
        "exam": exam,
        "blocks": blocks,
        "halls_by_block": halls_by_block,
    }
    return render(request, "exams/configure_exam_halls.html", context)


def _faculty_has_clash(faculty, exam):
    """
    Check if faculty has a timetable clash with the exam.
    Returns: (has_clash: bool, clash_details: dict or None)
    
    Logic:
    - If faculty is teaching the SAME year students during exam time, 
      they are FREE (students are in exam, class cancelled)
    - If faculty is teaching DIFFERENT year students, they have a CLASH
    """
    exam_start = datetime.combine(exam.exam_date, exam.start_time)
    exam_end = datetime.combine(exam.exam_date, exam.end_time)

    weekday = exam.exam_date.strftime("%a").upper()[:3]

    slots = FacultyTimeSlot.objects.filter(faculty=faculty, day_of_week=weekday)
    
    for slot in slots:
        slot_start = datetime.combine(exam.exam_date, slot.start_time)
        slot_end = datetime.combine(exam.exam_date, slot.end_time)
        
        # Check if there's a time overlap
        if slot_start < exam_end and exam_start < slot_end:
            # If teaching the same year as exam, class is cancelled (students in exam)
            # So faculty is FREE - no clash
            if slot.year and slot.year == exam.year:
                continue
            
            # Faculty is teaching different year students - CLASH!
            clash_info = {
                'slot': slot,
                'time': f"{slot.start_time.strftime('%H:%M')} - {slot.end_time.strftime('%H:%M')}",
                'course': f"{slot.course_code} - {slot.course_name}" if slot.course_code else "Unknown Course",
                'year': slot.year,
                'is_lab': slot.is_lab
            }
            return True, clash_info
    
    return False, None


def _faculty_on_approved_leave(faculty, exam_date):
    return FacultyLeave.objects.filter(
        faculty=faculty,
        status=FacultyLeave.APPROVED,
        start_date__lte=exam_date,
        end_date__gte=exam_date,
    ).exists()


@staff_member_required
def auto_allocate_for_exam(request, pk):
    from exams.utils import send_invigilation_assignment_email
    from exams.models import AllocationSuggestion
    import random
    import json
    
    exam = get_object_or_404(Exam.objects.select_related("department"), pk=pk)
    session_halls = ExamSessionHall.objects.filter(exam=exam).select_related("hall")

    if not session_halls.exists():
        messages.warning(request, "No halls/rooms are configured for this exam. Please use 'Assign Duties (Select Rooms)' first.")
        return redirect("exams:exam_detail", pk=exam.pk)

    all_faculty = (
        Faculty.objects.filter(is_active=True)
        .exclude(department=exam.department)
        .select_related("department", "user")
    )

    # Track faculty already assigned anywhere for this exam to avoid multiple halls
    global_assigned_ids = set(
        InvigilationAssignment.objects.filter(exam_session_hall__exam=exam).values_list("faculty_id", flat=True)
    )

    total_assigned = 0
    total_emails_sent = 0
    total_suggestions = 0
    
    # Store all suggestions for this allocation
    all_suggestions = []

    for session in session_halls:
        required = session.required_invigilators
        if required <= 0:
            continue

        current_assignments = InvigilationAssignment.objects.filter(exam_session_hall=session)
        already_assigned_ids = set(current_assignments.values_list("faculty_id", flat=True)) | global_assigned_ids

        # Categorize faculty
        eligible = []
        ineligible_with_reasons = []
        
        for faculty in all_faculty:
            # Check 1: Same department (already excluded in query, but track for reporting)
            if faculty.department == exam.department:
                ineligible_with_reasons.append({
                    'faculty': faculty,
                    'reason': 'SAME_DEPT',
                    'details': f"Faculty from {exam.department.code} cannot invigilate {exam.department.code} students"
                })
                continue
            
            # Check 2: Subject teacher
            if exam.subject_teacher and faculty.id == exam.subject_teacher.id:
                ineligible_with_reasons.append({
                    'faculty': faculty,
                    'reason': 'SUBJECT_TEACHER',
                    'details': f"Teaching the subject: {exam.course_code} - {exam.course_name}"
                })
                continue
            
            # Check 3: Already assigned
            if faculty.id in already_assigned_ids:
                ineligible_with_reasons.append({
                    'faculty': faculty,
                    'reason': 'ALREADY_ASSIGNED',
                    'details': f"Already assigned to another hall for this exam"
                })
                continue
            
            # Check 4: On approved leave
            if _faculty_on_approved_leave(faculty, exam.exam_date):
                ineligible_with_reasons.append({
                    'faculty': faculty,
                    'reason': 'ON_LEAVE',
                    'details': f"On approved leave on {exam.exam_date}"
                })
                continue
            
            # Check 5: Timetable clash (enhanced)
            has_clash, clash_info = _faculty_has_clash(faculty, exam)
            if has_clash:
                # Create suggestion for manual intervention
                suggestion_text = (
                    f"Faculty {faculty.user.get_full_name()} ({faculty.employee_id}) has a class during exam time:\n"
                    f"- Time: {clash_info['time']}\n"
                    f"- Course: {clash_info['course']}\n"
                    f"- Teaching Year {clash_info['year']} students\n\n"
                    f"Suggestions:\n"
                    f"1. Swap this class with another faculty member\n"
                    f"2. Reschedule this class to a different time slot\n"
                    f"3. Find a substitute teacher for this period\n"
                    f"4. Cancel this class for the day (if possible)"
                )
                
                ineligible_with_reasons.append({
                    'faculty': faculty,
                    'reason': 'TIMETABLE_CLASH',
                    'details': f"Teaching {clash_info['course']} to Year {clash_info['year']} at {clash_info['time']}",
                    'clash_info': clash_info,
                    'suggestion': suggestion_text
                })
                continue
            
            # Faculty is eligible!
            eligible.append(faculty)

        # Score eligible faculty based on proximity and workload
        scored = []
        for faculty in eligible:
            score = 0
            
            # Proximity bonus: same block gets highest priority
            if faculty.cabin_block and faculty.cabin_block.strip().upper() == session.hall.block.strip().upper():
                score += 100
            
            # Workload: faculty with fewer assignments get priority
            load = InvigilationAssignment.objects.filter(
                faculty=faculty,
                status__in=[InvigilationAssignment.CONFIRMED, InvigilationAssignment.PENDING_CONFIRMATION]
            ).count()
            
            scored.append((score, load, faculty))

        # Sort by score (descending) then by load (ascending)
        scored.sort(key=lambda item: (-item[0], item[1]))

        # Add randomization among faculty with same score and similar load
        if scored:
            final_list = []
            i = 0
            while i < len(scored):
                current_score = scored[i][0]
                current_load = scored[i][1]
                
                # Collect faculty with same score and load within ±1
                group = []
                j = i
                while j < len(scored) and scored[j][0] == current_score and abs(scored[j][1] - current_load) <= 1:
                    group.append(scored[j])
                    j += 1
                
                # Randomize within group
                random.shuffle(group)
                final_list.extend(group)
                i = j
            
            scored = final_list

        chosen = [faculty for _, _, faculty in scored[:required]]

        # Assign chosen faculty
        for faculty in chosen:
            assignment, created = InvigilationAssignment.objects.get_or_create(
                exam_session_hall=session,
                faculty=faculty,
                defaults={
                    "status": InvigilationAssignment.PENDING_CONFIRMATION,
                },
            )
            if created:
                global_assigned_ids.add(faculty.id)
                
                # Set deadline: 1.5 hours before exam start
                exam_start_dt = datetime.combine(exam.exam_date, exam.start_time)
                deadline = timezone.make_aware(exam_start_dt) - timedelta(hours=1, minutes=30)
                assignment.confirmation_deadline = deadline
                assignment.notification_sent_at = timezone.now()
                assignment.save(update_fields=["confirmation_deadline", "notification_sent_at"])
                
                # Send email notification
                if send_invigilation_assignment_email(assignment):
                    total_emails_sent += 1
                
                total_assigned += 1

        # If we couldn't fill all required positions, create suggestions
        shortage = required - len(chosen)
        if shortage > 0:
            # Sort ineligible faculty by reason priority
            # Priority: TIMETABLE_CLASH > ON_LEAVE > ALREADY_ASSIGNED > SUBJECT_TEACHER > SAME_DEPT
            priority_order = {
                'TIMETABLE_CLASH': 1,
                'ON_LEAVE': 2,
                'ALREADY_ASSIGNED': 3,
                'SUBJECT_TEACHER': 4,
                'SAME_DEPT': 5
            }
            
            ineligible_with_reasons.sort(key=lambda x: priority_order.get(x['reason'], 99))
            
            # Create suggestions for top candidates (those with timetable clashes)
            for item in ineligible_with_reasons[:shortage]:
                if item['reason'] == 'TIMETABLE_CLASH':
                    suggestion = AllocationSuggestion.objects.create(
                        exam=exam,
                        exam_session_hall=session,
                        faculty=item['faculty'],
                        clash_type=item['reason'],
                        clash_details=json.dumps({
                            'details': item['details'],
                            'clash_info': {
                                'time': item['clash_info']['time'],
                                'course': item['clash_info']['course'],
                                'year': item['clash_info']['year'],
                                'is_lab': item['clash_info']['is_lab']
                            }
                        }),
                        suggestion_type='SWAP_CLASS',
                        suggestion_text=item['suggestion']
                    )
                    all_suggestions.append(suggestion)
                    total_suggestions += 1
            
            messages.warning(
                request,
                f"⚠️ {session.hall.name}: Could only assign {len(chosen)} of {required} required invigilators. "
                f"{total_suggestions} suggestions created for manual review."
            )
        
        # Debug info for this session
        messages.info(
            request,
            f"✓ {session.hall.name}: {len(eligible)} eligible, {len(chosen)} assigned (required {required}). "
            f"Excluded: same_dept={len([x for x in ineligible_with_reasons if x['reason']=='SAME_DEPT'])}, "
            f"subject_teacher={len([x for x in ineligible_with_reasons if x['reason']=='SUBJECT_TEACHER'])}, "
            f"assigned={len([x for x in ineligible_with_reasons if x['reason']=='ALREADY_ASSIGNED'])}, "
            f"leave={len([x for x in ineligible_with_reasons if x['reason']=='ON_LEAVE'])}, "
            f"clash={len([x for x in ineligible_with_reasons if x['reason']=='TIMETABLE_CLASH'])}"
        )

    # Final summary
    if total_suggestions > 0:
        messages.warning(
            request,
            f"⚠️ MANUAL REVIEW REQUIRED: {total_suggestions} suggestions created. "
            f"<a href='/exams/admin/exams/{exam.pk}/suggestions/' class='alert-link'>Click here to review suggestions</a>",
            extra_tags='safe'
        )
    
    messages.success(
        request, 
        f"✅ Invigilation duties auto-allocated: {total_assigned} assignments created, {total_emails_sent} email notifications sent."
    )
    return redirect("exams:exam_detail", pk=exam.pk)


@staff_member_required
def export_exam_allocation_csv(request, pk):
    """Export allocation details for a specific exam as CSV."""

    exam = get_object_or_404(Exam.objects.select_related("department"), pk=pk)
    assignments = (
        InvigilationAssignment.objects.filter(exam_session_hall__exam=exam)
        .select_related(
            "exam_session_hall__exam",
            "exam_session_hall__hall",
            "faculty__user",
            "faculty__department",
        )
        .order_by("exam_session_hall__hall__block", "exam_session_hall__hall__name")
    )

    response = HttpResponse(content_type="text/csv")
    response["Content-Disposition"] = f"attachment; filename=exam_{exam.id}_allocation.csv"

    writer = csv.writer(response)
    writer.writerow([
        "exam_date",
        "start_time",
        "end_time",
        "course_code",
        "course_name",
        "department",
        "hall_block",
        "hall_name",
        "hall_capacity",
        "required_invigilators",
        "faculty_employee_id",
        "faculty_name",
        "faculty_email",
        "faculty_department",
        "status",
        "assigned_at",
        "confirmed_at",
        "declined_at",
    ])
    for a in assignments:
        writer.writerow([
            exam.exam_date,
            exam.start_time,
            exam.end_time,
            exam.course_code,
            exam.course_name,
            exam.department.code,
            a.exam_session_hall.hall.block,
            a.exam_session_hall.hall.name,
            a.exam_session_hall.hall.capacity,
            a.exam_session_hall.required_invigilators,
            a.faculty.employee_id,
            a.faculty.user.get_full_name(),
            a.faculty.user.email,
            a.faculty.department.code,
            a.status,
            a.assigned_at,
            a.confirmed_at,
            a.declined_at,
        ])
    return response


@staff_member_required
def pending_assignments(request):
    """List all pending invigilation assignments with Approve/Decline actions."""
    assignments = (
        InvigilationAssignment.objects.filter(status=InvigilationAssignment.PENDING_CONFIRMATION)
        .select_related(
            "exam_session_hall__exam",
            "exam_session_hall__hall",
            "faculty__user",
            "faculty__department",
        )
        .order_by("confirmation_deadline")
    )
    return render(request, "exams/pending_assignments.html", {"assignments": assignments})


@login_required
def confirm_assignment(request, pk):
    """Approve a pending invigilation assignment."""
    assignment = get_object_or_404(InvigilationAssignment, pk=pk, status=InvigilationAssignment.PENDING_CONFIRMATION)
    assignment.status = InvigilationAssignment.CONFIRMED
    assignment.confirmed_at = timezone.now()
    assignment.save(update_fields=["status", "confirmed_at"])
    messages.success(request, f"Assignment for {assignment.faculty.user.get_full_name()} confirmed.")
    return redirect("exams:pending_assignments")


@login_required
def decline_assignment(request, pk):
    """Decline a pending invigilation assignment (Admin view)."""
    assignment = get_object_or_404(InvigilationAssignment, pk=pk, status=InvigilationAssignment.PENDING_CONFIRMATION)
    if request.method == "POST":
        reason = request.POST.get("reason", "").strip()
        assignment.status = InvigilationAssignment.DECLINED
        assignment.declined_at = timezone.now()
        assignment.decline_reason = reason
        assignment.save(update_fields=["status", "declined_at", "decline_reason"])
        messages.success(request, f"Assignment for {assignment.faculty.user.get_full_name()} declined.")
        return redirect("exams:pending_assignments")
    return render(request, "exams/decline_assignment.html", {"assignment": assignment})
    """Export allocation details for a specific exam as CSV."""

    exam = get_object_or_404(Exam.objects.select_related("department"), pk=pk)
    assignments = (
        InvigilationAssignment.objects.filter(exam_session_hall__exam=exam)
        .select_related(
            "exam_session_hall__exam",
            "exam_session_hall__hall",
            "faculty__user",
            "faculty__department",
        )
        .order_by("exam_session_hall__hall__block", "exam_session_hall__hall__name")
    )

    response = HttpResponse(content_type="text/csv")
    response["Content-Disposition"] = f"attachment; filename=exam_{exam.id}_allocation.csv"

    writer = csv.writer(response)
    writer.writerow([
        "exam_date",
        "start_time",
        "end_time",
        "course_code",
        "course_name",
        "hall",
        "block",
        "faculty_name",
        "faculty_department",
        "status",
    ])

    for a in assignments:
        ex = a.exam_session_hall.exam
        hall = a.exam_session_hall.hall
        fac = a.faculty
        user = fac.user
        writer.writerow([
            ex.exam_date,
            ex.start_time,
            ex.end_time,
            ex.course_code,
            ex.course_name,
            hall.name,
            hall.block,
            user.get_full_name() or user.username,
            fac.department.code if fac.department else "",
            a.status,
        ])

    return response


@login_required
def faculty_dashboard(request):
    """Dashboard for faculty to see and respond to invigilation assignments."""

    try:
        faculty = request.user.faculty_profile
    except Faculty.DoesNotExist:  # type: ignore[attr-defined]
        messages.error(request, "You do not have a faculty profile configured.")
        return redirect("accounts:dashboard")

    today = timezone.localdate()

    assignments = (
        InvigilationAssignment.objects.filter(faculty=faculty, exam_session_hall__exam__exam_date__gte=today)
        .select_related("exam_session_hall__exam", "exam_session_hall__hall")
        .order_by("exam_session_hall__exam__exam_date", "exam_session_hall__exam__start_time")
    )
    
    # Check if there are any pending assignments
    has_pending_assignments = assignments.filter(status=InvigilationAssignment.PENDING_CONFIRMATION).exists()

    return render(request, "exams/faculty_dashboard.html", {
        "assignments": assignments,
        "has_pending_assignments": has_pending_assignments
    })


@login_required
def confirm_assignment(request, pk):
    assignment = get_object_or_404(
        InvigilationAssignment.objects.select_related("faculty", "exam_session_hall__exam"), pk=pk
    )

    if not hasattr(request.user, "faculty_profile") or assignment.faculty != request.user.faculty_profile:  # type: ignore[attr-defined]
        messages.error(request, "You are not allowed to modify this assignment.")
        return redirect("exams:faculty_dashboard")

    assignment.status = InvigilationAssignment.CONFIRMED
    assignment.confirmed_at = timezone.now()
    assignment.save(update_fields=["status", "confirmed_at"])

    messages.success(request, "Your availability for this invigilation duty has been confirmed.")
    return redirect("exams:faculty_dashboard")


@login_required
@login_required
def decline_assignment(request, pk):
    """Faculty declines their invigilation assignment"""
    from exams.utils import send_assignment_declined_notification_to_admin
    
    assignment = get_object_or_404(
        InvigilationAssignment.objects.select_related("faculty", "exam_session_hall__exam", "exam_session_hall__hall"), pk=pk
    )

    if not hasattr(request.user, "faculty_profile") or assignment.faculty != request.user.faculty_profile:  # type: ignore[attr-defined]
        messages.error(request, "You are not allowed to modify this assignment.")
        return redirect("exams:faculty_dashboard")

    if request.method == "POST":
        reason = request.POST.get("reason", "").strip()
        assignment.status = InvigilationAssignment.DECLINED
        assignment.declined_at = timezone.now()
        assignment.decline_reason = reason
        assignment.save(update_fields=["status", "declined_at", "decline_reason"])
        
        # Send notification to admin
        send_assignment_declined_notification_to_admin(assignment)
        
        messages.success(request, "You have declined this duty. Admin has been notified for reassignment.")
        return redirect("exams:faculty_dashboard")
    
    return render(request, "exams/decline_assignment.html", {"assignment": assignment})

