"""Models relating to Teaching Assistants."""
from django.db import models
from laborganizer.models import Semester


class ScorePair(models.Model):
    """A score pair representing a course catalog ID and a TA's score."""

    def __str__(self):
        """Define human readable object name."""
        return f'{self.score_catalog_id}:{self.score}'

    score_catalog_id = models.CharField('Catalog ID for score', max_length=10)
    score = models.IntegerField('Score')

    # semester this ScorePair is assigned to
    semester = models.ForeignKey("laborganizer.Semester",
                                 on_delete=models.CASCADE,
                                 blank=True,
                                 null=True)

    # key to the schedule this score belongs to
    schedule_key = models.CharField('Schedule Key', max_length=10,
                                    blank=True, null=True)


class TA(models.Model):
    """TA Object. Primary key is predefined as an integer value by Django."""

    class Meta:
        """Metadata regarding TA's."""

        verbose_name = 'TA'
        verbose_name_plural = 'TA\'s'

    def __str__(self):
        """Human readable class name, for admin site."""
        return self.first_name + ' ' + self.last_name

    def flip_contract_status(self):
        """Flip the contracted status of this TA."""
        if self.contracted:
            self.contracted = False
        else:
            self.contracted = True
        self.save()

    def get_all_assigned_semesters(self):
        """
        Get a list of all semesters this TA is assigned to.

        Return a Python list of tuples with index 0 being the time and
        index 1 being the year, i.e. ('SPR', 2022).
        """
        semester_list = []
        for semester in self.assigned_semesters.all():
            semester_list.append((semester.semester_time, semester.year))
        return semester_list

    def get_all_assigned_labs(self):
        """
        Get a list of all labs this TA is assigned to.

        Returns the name of the lab in human readable format.
        """
        lab_list = []
        for lab in self.assigned_labs.all():
            lab_list.append(lab.__str__())
        return ', '.join(lab_list)

    def get_assigned_labs(self, semester):
        """Get all assigned labs for the given semester."""
        try:
            semester = Semester.objects.get(semester_time=semester['time'],
                                            year=semester['year'])
        except Semester.DoesNotExist:
            return None

        lab_list = []
        for lab in self.assigned_labs.all():
            if lab.semester == semester:
                lab_list.append(lab)
        return lab_list

    def get_assignments_from_template(self, schedule):
        """Get all the labs a TA is assigned to based on a template schedule."""
        # get the template schedule
        assignment_list = []
        for assignment in schedule.assignments.all():
            if assignment.ta == self:
                assignment_list.append(assignment.lab)
        return assignment_list

    def score_exists(self, lab, schedule_key):
        """
        Check if a score already exists for a TA for a given lab.

        If a score exists, return the ScorePair object, otherwise
        return None.
        """
        index = 0
        for score in self.scores.all():
            if (score.score_catalog_id == lab.catalog_id and
                score.semester == lab.semester and
                int(score.schedule_key) == schedule_key):
                # found a matching ScorePair
                return score
            index += 1
        # did not find a matching ScorePair
        return None

    def get_score(self, lab, schedule_key):
        """Get the score of a given lab, if it exits."""
        score_pair = self.score_exists(lab, schedule_key)
        if score_pair is None:
            return None
        return score_pair.score

    def assign_score(self, score, lab, schedule_key):
        """Assign a ScorePair object for a given lab."""
        # if a current ScorePair exists for this lab, update it
        score_pair = self.score_exists(lab, schedule_key)

        # check if the score exists
        if score_pair is None:
            # it does not, create a new ScorePair
            new_score = ScorePair.objects.create(score_catalog_id=lab.catalog_id,
                                                 score=score,
                                                 semester=lab.semester,
                                                 schedule_key=schedule_key)
            # save changes to database
            self.scores.add(new_score)
            new_score.save()
        else:
            # score exists, update it
            score_pair.score = score
            score_pair.save()

        # save all ScorePair changes
        self.save()

    def get_experience(self):
        """Return a Python list of tuples of all experience."""
        experience = self.experience.split(',')
        experience_list = []
        for course in experience:
            subject = ''
            catalog_id = ''
            for character in course:
                # check if the character is a number
                if character >= '0' and character <= '9':
                    # add it to the catalog id
                    catalog_id += character
                elif character != ' ':
                    # character is a letter
                    subject += character
            experience_list.append((subject, catalog_id))
        return experience_list

    def get_availability(self):
        """Return a formatted dictionary of all TA availabilty."""
        avail = {}
        availability = Availability.objects.get(pk=self.availability_key)
        for index, class_time in enumerate(availability.class_times.all()):
            avail[str(index)] = {
                'days': class_time.get_days(),
                'start_time': class_time.start_time,
                'end_time': class_time.end_time,
                'semester_name': class_time.semester_name,
            }
        return avail

    def assign_to_lab(self, lab, all_tas):
        """Assign this TA to the given lab."""
        # unassign any previously assigned TA
        lab.unassign_ta(all_tas)

        # assign this TA
        self.assigned_labs.add(lab)

        # save changes
        self.save()

    def get_semesters(self):
        """Get a list of all semesters this TA is assigned to."""
        semesters = []
        for semester in self.assigned_semesters.all():
            semesters.append(semester.__str__())
        return ', '.join(semesters)

    def get_semester_objects(self):
        """Get all semester objects this TA is assigned to."""
        semesters = []
        for semester in self.assigned_semesters.all():
            semesters.append(semester)
        return semesters

    def is_assigned_to_semester(self, semester_to_check):
        """Check if this TA is assigned to the given semester."""
        for semester in self.assigned_semesters.all():
            if semester == semester_to_check:
                return True
        return False

    def has_assigned_semesters(self):
        """Check if this TA has any assigned semesters."""
        return len(self.assigned_semesters.all()) > 0

    def update_semesters(self, semester_list):
        """Given a list of semesters, update the assignemnts to this TA."""
        # loop through all given semesters
        for semester in semester_list:
            year = semester[3:]
            time = semester[:3]
            semester = Semester.objects.get(year=year, semester_time=time)

            # check if the TA is already assigned to that semester
            if not self.is_assigned_to_semester(semester):
                self.assigned_semesters.add(semester)

        # loop through semesters TA is already assigned to
        for semester in self.assigned_semesters.all():
            # check if they're assigned to a semester NOT in the given list
            if str(semester) not in semester_list:
                # they are, unassign them
                self.assigned_semesters.remove(semester)

    def get_lab_objects(self):
        """Get all the lab objects a TA is assigned to."""
        return self.assigned_labs.all()

    # define choice variable
    YEAR = (
        ('FR', 'Freshman'),
        ('SO', 'Sophomore'),
        ('JR', 'Junior'),
        ('SR', 'Senior'),
        ('GR', 'Graduate')
        )

    # define fields
    first_name = models.CharField('TA\'s first name',
                                  max_length=50, default='missing')
    last_name = models.CharField('TA\'s last name',
                                 max_length=50, default='missing')
    student_id = models.CharField('TA\'s student ID', max_length=50,
                                  unique=True, blank=True, null=True)

    contracted = models.BooleanField('Contracted', blank=True, null=True)

    # stored as a comma delimited list starting with the subject followed by
    # the catalog id, i.e.
    # (CS126, MAT305, CS249)
    experience = models.TextField('TA\'s experience', blank=True)

    year = models.CharField('TA\'s current year', max_length=2,
                            choices=YEAR, blank=True)

    holds_key = models.IntegerField('Primary Holds key', blank=True,
                                    null=True, unique=True)

    availability_key = models.IntegerField('Primary Availability key',
                                           blank=True, null=True, unique=True)

    scores = models.ManyToManyField(ScorePair, blank=True)

    assigned_semesters = models.ManyToManyField("laborganizer.Semester",
                                                blank=True)

    assigned_labs = models.ManyToManyField("laborganizer.Lab",
                                           blank=True)


class ClassTime(models.Model):
    """
    Represent a pair of times for a single TA.

    1. Start time = the time their class starts
    2. End time = the time their class ends
    3. Days = the days these times are for
    """

    class Meta:
        """Meta information for a ClassTime object."""

        verbose_name = 'Class Time'
        verbose_name_plural = 'Class Times'

    def __str__(self):
        """Human readable object name."""
        return f'{self.start_time}-{self.end_time}'

    def join_days(days_list):
        """Given a Python list of days, join them by commas."""
        return ','.join(days_list)

    def get_days(self):
        """Return a Python list of the days attached to this time."""
        return self.days.split(',')

    # key to TA
    ta = models.ForeignKey(TA, on_delete=models.CASCADE)

    # times
    start_time = models.TimeField(auto_now=False, auto_now_add=False)
    end_time = models.TimeField(auto_now=False, auto_now_add=False)

    # days for these times
    days = models.CharField('Days', max_length=10, blank=True, null=True)
    semester_name = models.TextField('Semester', blank=True)


class Availability(models.Model):
    """Object representing a single TA's availability."""

    class Meta:
        """Metadata regarding Availability objects."""

        verbose_name = 'Availability'
        verbose_name_plural = 'Availability\'s'

    def __str__(self):
        """Human readable object name."""
        return f'{self.ta}\'s Availability'

    def delete_times(self):
        """Delete all the class times for a TA."""
        # remove the times from the availability object
        for time in self.class_times.all():
            self.class_times.remove(time)

        # delete actual ClassTime objects
        ClassTime.objects.filter(ta=self.ta).delete()

    def edit_time(self, time_list, semester_list):
        """Create a new ClassTime object for this TA."""
        # delete the existing class times, if any
        self.delete_times()

        semester_index = 0
        # create new class times for each object
        for new_time in time_list:
            # splice the days from the current index
            days = new_time[2:]

            # join the days list
            days = ClassTime.join_days(days)

            # create a new class time object and assign it to this field
            self.class_times.create(start_time=new_time[0],
                                    end_time=new_time[1],
                                    days=days,
                                    semester_name=semester_list[semester_index],
                                    ta=self.ta)

            semester_index += 1

    def get_class_times(self):
        """Return a list of the TA's class times."""
        time_list = []
        for time in self.class_times.all():
            time_list.append(time.__str__())
        return time_list

    class_times = models.ManyToManyField(ClassTime)

    # key to TA
    ta = models.OneToOneField(TA, on_delete=models.CASCADE)


class Holds(models.Model):
    """Possible holds to be applied to TA accounts."""

    class Meta:
        """Metadata regarding Holds objects."""

        verbose_name = 'Holds'
        verbose_name_plural = 'Holds'

    def __str__(self):
        """Human readable object name."""
        return f'{self.ta}\'s Holds'

    # if the TA has not completed the initialization of their profile
    # NOTE: defaults to true such that a new TA will be required
    #       to update their profile before being scheduled
    incomplete_profile = models.BooleanField('Incomplete profile',
                                             default=True)

    # if the TA needs to update their availability
    update_availability = models.BooleanField('Update availability',
                                              default=False)

    # if the TA needs to update their experience
    update_experience = models.BooleanField('Update experience',
                                            default=False)

    # key to TA
    ta = models.OneToOneField(TA, on_delete=models.CASCADE, verbose_name='TA')
