import csv
import io

from django import forms

from .models import Course, FacultyTimeSlot
from accounts.models import Faculty


class TimetableUploadForm(forms.Form):
    file = forms.FileField(
        help_text=(
            "CSV with columns: employee_id, day, start_time, end_time, "
            "course_code, course_name, year, is_lab"
        )
    )


class CourseForm(forms.ModelForm):
    class Meta:
        model = Course
        fields = ["department", "year", "semester", "code", "name"]
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Add Bootstrap classes to all fields
        for field_name, field in self.fields.items():
            if isinstance(field.widget, forms.Select):
                field.widget.attrs.update({'class': 'form-select'})
            else:
                field.widget.attrs.update({'class': 'form-control'})
        
        # Department dropdown
        self.fields["department"].widget = forms.Select(
            attrs={'class': 'form-select'},
            choices=[("", "Select department")] + [(dept.id, f"{dept.code} - {dept.name}") for dept in self.fields["department"].queryset]
        )
        # Year dropdown 1-4
        self.fields["year"].widget = forms.Select(
            attrs={'class': 'form-select'},
            choices=[("", "Select year"), (1, "Year 1"), (2, "Year 2"), (3, "Year 3"), (4, "Year 4")]
        )
        # Semester dropdown 1-2
        self.fields["semester"].widget = forms.Select(
            attrs={'class': 'form-select'},
            choices=[("", "Select semester"), (1, "Semester 1"), (2, "Semester 2")]
        )
        
        # Add placeholders
        self.fields["code"].widget.attrs.update({'placeholder': 'e.g., CS101, R204GA05101'})
        self.fields["name"].widget.attrs.update({'placeholder': 'e.g., Programming Fundamentals'})


class FacultyTimeSlotForm(forms.ModelForm):
    TIME_CHOICES = [
        ("09:30", "09:30"),
        ("10:30", "10:30"),
        ("11:30", "11:30"),
        ("12:30", "12:30"),
        ("13:30", "13:30"),
        ("14:30", "14:30"),
        ("15:30", "15:30"),
        ("16:30", "16:30"),
    ]

    class Meta:
        model = FacultyTimeSlot
        fields = [
            "day_of_week",
            "start_time",
            "end_time",
            "course_code",
            "course_name",
            "year",
            "is_lab",
        ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Year dropdown 1-4
        self.fields["year"].widget = forms.Select(
            choices=[("", "Select year"), (1, "1"), (2, "2"), (3, "3"), (4, "4")]
        )

        # Predefined times for start/end
        self.fields["start_time"].widget = forms.Select(choices=self.TIME_CHOICES)
        self.fields["end_time"].widget = forms.Select(choices=self.TIME_CHOICES)

        # Use a dropdown for course_code. Filter by selected year when available.
        # course_name is auto-filled from Course in clean() and shown as read-only.
        self.fields["course_name"].widget = forms.TextInput(attrs={"readonly": "readonly"})

        # Show all defined courses in the dropdown; clean() will enforce that
        # the selected course actually belongs to the selected year.
        courses_qs = Course.objects.all()

        # Encode the course year into the label so front-end JS can filter
        # courses per selected year (label example: "Y1 - CSE101 - Programming in C").
        self.fields["course_code"].widget = forms.Select(
            choices=[("", "Select course")] + [
                (c.code, f"Y{c.year} - {c.code} - {c.name}") for c in courses_qs
            ]
        )

    def clean(self):
        cleaned = super().clean()
        year = cleaned.get("year")
        code = cleaned.get("course_code")
        start = cleaned.get("start_time")
        end = cleaned.get("end_time")

        # Enforce end_time strictly greater than start_time
        if start and end and end <= start:
            self.add_error("end_time", "End time must be greater than start time.")

        # Require year before a course can be selected
        if code and not year:
            self.add_error("year", "Please select the year before choosing a course.")

        # Auto-populate course_name from Course table for the selected year + code
        if year and code:
            try:
                course = Course.objects.get(code=code, year=year)
                cleaned["course_name"] = course.name
            except Course.DoesNotExist:
                self.add_error("course_code", "Selected course does not exist for this year.")

        return cleaned
