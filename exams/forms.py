from django import forms
from .models import Department, Exam
from timetable.models import Course


class ExamTimetableUploadForm(forms.Form):
    file = forms.FileField(
        help_text=(
            "CSV columns: department_code, course_code, course_name, exam_type, "
            "year, semester, exam_date (YYYY-MM-DD), start_time (HH:MM), end_time (HH:MM)"
        )
    )


class ExamCreateForm(forms.ModelForm):
    SEMESTER_CHOICES = [(1, "1"), (2, "2")]
    YEAR_CHOICES = [(1, "1"), (2, "2"), (3, "3"), (4, "4")]
    
    course_code = forms.ChoiceField(choices=[], required=True, widget=forms.Select(attrs={'class': 'form-control'}))
    semester = forms.ChoiceField(choices=SEMESTER_CHOICES, required=True, widget=forms.Select(attrs={'class': 'form-control'}))
    year = forms.ChoiceField(choices=YEAR_CHOICES, required=True, widget=forms.Select(attrs={'class': 'form-control'}))
    
    class Meta:
        model = Exam
        fields = [
            'course_code', 'course_name', 'exam_type', 'department', 
            'year', 'semester', 'exam_date', 'start_time', 'end_time'
        ]
        widgets = {
            'course_name': forms.TextInput(attrs={'class': 'form-control', 'readonly': True}),
            'exam_type': forms.Select(attrs={'class': 'form-control'}),
            'department': forms.Select(attrs={'class': 'form-control'}),
            'exam_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'start_time': forms.TimeInput(attrs={'class': 'form-control', 'type': 'time'}),
            'end_time': forms.TimeInput(attrs={'class': 'form-control', 'type': 'time'}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Widget attributes are already set in field definitions
        
        # If form is being populated with existing data, load courses
        if (self.data.get('department') and self.data.get('year') and 
            self.data.get('semester')):
            self._load_courses()
    
    def _load_courses(self):
        department_id = self.data.get('department') or self.initial.get('department')
        year = self.data.get('year') or self.initial.get('year')
        semester = self.data.get('semester') or self.initial.get('semester')
        
        if department_id and year and semester:
            courses = Course.objects.filter(
                department_id=department_id, 
                year=year, 
                semester=semester
            )
            self.fields['course_code'].choices = [('', '-- Select Course --')] + [
                (course.code, course.code) for course in courses  # Only show course code
            ]
        else:
            self.fields['course_code'].choices = [('', '-- Select Department, Year and Semester First --')]
