from django.db import models
from exams.models import Department


class Course(models.Model):
    YEAR_CHOICES = [(1, "1"), (2, "2"), (3, "3"), (4, "4")]
    SEMESTER_CHOICES = [(1, "1"), (2, "2")]

    department = models.ForeignKey(Department, on_delete=models.CASCADE, related_name='courses')
    code = models.CharField(max_length=20)
    name = models.CharField(max_length=200)
    year = models.PositiveSmallIntegerField(choices=YEAR_CHOICES)
    semester = models.PositiveSmallIntegerField(choices=SEMESTER_CHOICES)

    class Meta:
        unique_together = ("department", "code", "year", "semester")
        ordering = ["department", "year", "semester", "code"]

    def __str__(self) -> str:
        return f"{self.department.code} Y{self.year}S{self.semester} - {self.code} {self.name}"


class FacultyTimeSlot(models.Model):
    MONDAY = 'MON'
    TUESDAY = 'TUE'
    WEDNESDAY = 'WED'
    THURSDAY = 'THU'
    FRIDAY = 'FRI'
    SATURDAY = 'SAT'
    SUNDAY = 'SUN'

    DAY_CHOICES = [
        (MONDAY, 'Monday'),
        (TUESDAY, 'Tuesday'),
        (WEDNESDAY, 'Wednesday'),
        (THURSDAY, 'Thursday'),
        (FRIDAY, 'Friday'),
        (SATURDAY, 'Saturday'),
        (SUNDAY, 'Sunday'),
    ]

    YEAR_CHOICES = [(1, "1"), (2, "2"), (3, "3"), (4, "4")]
    SEMESTER_CHOICES = [(1, "1"), (2, "2")]

    faculty = models.ForeignKey('accounts.Faculty', on_delete=models.CASCADE, related_name='timetable_slots')
    day_of_week = models.CharField(max_length=3, choices=DAY_CHOICES)
    start_time = models.TimeField()
    end_time = models.TimeField()
    department = models.ForeignKey(Department, on_delete=models.CASCADE, related_name='faculty_slots', null=True, blank=True)
    course_code = models.CharField(max_length=20, blank=True)
    course_name = models.CharField(max_length=200, blank=True)
    year = models.PositiveSmallIntegerField(choices=YEAR_CHOICES, null=True, blank=True, help_text="Year of study (1-4)")
    semester = models.PositiveSmallIntegerField(choices=SEMESTER_CHOICES, null=True, blank=True, help_text="Semester (1-2)")
    is_lab = models.BooleanField(default=False)

    def __str__(self) -> str:
        return f"{self.faculty} - {self.day_of_week} {self.start_time}-{self.end_time}"

