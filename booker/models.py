from django.db import models
from django.db.models.signals import post_save, pre_delete
from django.dispatch import receiver
import datetime

from booker.gcal import get_service, parse_datetime
import mysite.settings as settings

NO_CAL_SIGNAL = 'no calendar'

class Calendar(models.Model):
    gcal_id = models.CharField(max_length=100, default=NO_CAL_SIGNAL)
    name = models.CharField(max_length=25)
    minutes_per_booking = models.IntegerField()

    def cal_made(self):
        return self.gcal_id != NO_CAL_SIGNAL

    def make_cal(self, cal_timezone=settings.TIME_ZONE):
        if self.cal_made():
            print("found cal ", self.gcal_id)
            return False
        else:
            calendar = {
                'summary': self.name,
                'timeZone': cal_timezone
            }
            service = get_service()
            created_calendar = service.calendars().insert(body=calendar).execute()

            self.gcal_id = created_calendar['id']
            self.save()

            rule = {
                'scope': {
                    'type': 'default',
                },
                'role': 'reader'
            }

            created_rule = service.acl().insert(calendarId=self.gcal_id, body=rule).execute()

            return True

    def delete_cal(self):
        if self.cal_made():
            #print('DELETING', self.name)
            service = get_service()
            calendar_id = self.gcal_id
            service.calendars().delete(calendarId=calendar_id).execute()
            self.gcal_id = NO_CAL_SIGNAL
            self.save()
            return True
        return False

    def events_within(self, starttime, endtime=None):
        if endtime is None:
            endtime = starttime + datetime.timedelta(hours=24)
        service = get_service()
        page_token = None
        while True:
            resp = service.events().list(
                calendarId=self.gcal_id,
                pageToken=page_token,
                timeMin=starttime.isoformat(),
                timeMax=endtime.isoformat(),
                singleEvents=True,
            ).execute()
            yield from resp['items']
            page_token = resp.get('nextPageToken')
            if not page_token:
                break

    def grant_write_permission(self, email):
        service = get_service()
        rule = {
            'scope': {
                'type': 'user',
                'value': email,
            },
            'role': 'writer',
        }
        return service.acl().insert(calendarId=self.gcal_id, body=rule).execute()['id']


    def remove_write_permission(self, email):
        service = get_service()
        for rule in self.all_rules():
            if rule['scope']['type'] == 'user' and rule['scope']['value'] == email:
                service.acl().delete(calendarId=self.gcal_id, ruleId=rule['id'])


    def all_rules(self):
        service = get_service()
        page_token = None
        while True:
            resp = service.acl().list(
                calendarId=self.gcal_id,
                pageToken=page_token,
            ).execute()
            yield from resp['items']
            page_token = resp.get('nextPageToken')
            if not page_token:
                break

@receiver(post_save, sender=Calendar)
def add_permission_and_get_id_upon_add_calendar(sender, **kwargs):
    instance = kwargs['instance']
    if kwargs['created']:
        instance.make_cal()
        for ta in TA.objects.all():
            instance.grant_write_permission(ta.email)

@receiver(pre_delete, sender=Calendar)
def remove_gcalendar(sender, **kwargs):
    instance = kwargs['instance']
    instance.delete_cal


# Force email addresses to be lowercase
class LowerField(models.CharField):
    def get_prep_value(self, value):
        return str(value).lower()

class TA(models.Model):
    email = LowerField(max_length=50)

    @classmethod
    def make(cls, email):
        self = cls()
        self.email = email
        self.save()
        return self

class Student(models.Model):
    email = LowerField(max_length=50)

    @classmethod
    def make(cls, email):
        self = cls()
        self.email = email
        self.save()
        return self

@receiver(post_save, sender=TA)
def add_permission_upon_add_ta(sender, **kwargs):
    instance = kwargs['instance']
    if kwargs['created']:
        for cal in Calendar.objects.all():
            cal.grant_write_permission(instance.email)

@receiver(pre_delete, sender=TA)
def remove_permission_upon_remove_ta(sender, **kwargs):
    instance = kwargs['instance']
    for cal in Calendar.objects.all():
        cal.remove_write_permission(instance.email)



class OfficeHour(models.Model):
    starttime = models.DateTimeField()
    endtime = models.DateTimeField()
    location = models.CharField(max_length=20, default='contact staff')
    event_id = models.CharField(max_length=50, unique=True, default='no event')
    minutes_per_booking = models.IntegerField()

    @classmethod
    def make_from_event(cls, event, minutes_per_booking):
        self = cls()
        self.starttime = parse_datetime(event['start']['dateTime'])
        self.endtime = parse_datetime(event['end']['dateTime'])
        if 'location' in event:
            self.location = event['location']
        else:
            self.location = 'TBD'
        self.event_id = event['id']
        self.minutes_per_booking = minutes_per_booking
        self.save()
        return self


class Bookable(models.Model):
    officehour = models.ForeignKey('OfficeHour', on_delete=models.CASCADE)
    starttime = models.DateTimeField()

    def booked(self):
        return hasattr(self, 'booker') and self.booker is not None

    def available(self):
        return not self.booked()

    @classmethod
    def make(cls, officehour, starttime):
        self = cls()
        self.officehour = officehour
        self.starttime = starttime
        self.save()
        return self

    @staticmethod
    def any_available_at_time(time):
        return any(map(Bookable.available, Bookable.objects.filter(starttime=time)))

    @staticmethod
    def select_available_at_time(time):
        for b in Bookable.objects.filter(starttime=time):
            if b.available():
                return b
        else:
            return None


@receiver(post_save, sender=OfficeHour)
def spawn_bookables(sender, **kwargs):
    if kwargs['created']:
        instance = kwargs['instance']
        if instance.minutes_per_booking <= 0:
            return
        t = instance.starttime
        delta = datetime.timedelta(minutes=instance.minutes_per_booking)
        epsilan = datetime.timedelta(minutes=1)
        count = 0
        while t + delta <= instance.endtime + epsilan:
            count += 1
            if count % 7 != 0: # skip a slot for each 6 bookables
                Bookable.make(instance, t)
            t = t + delta
