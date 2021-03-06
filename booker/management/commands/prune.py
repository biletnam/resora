from django.core.management.base import BaseCommand

from booker.models import OfficeHour, Bookable
import mysite.settings as settings

import datetime
import pytz


class Command(BaseCommand):
    help = "'prune' removes any bookables and officehours that have passed"

    def handle(self, *args, **options):
        now = datetime.datetime.now(pytz.timezone(settings.TIME_ZONE))
        for oh in OfficeHour.objects.filter(endtime__lte=now):
            t = oh.starttime
            oh.delete()
            self.stdout.write(self.style.SUCCESS(
                'Successfully deleted office hour that started at %s' % t
            ))
        for b in Bookable.objects.filter(starttime__lte=now-datetime.timedelta(minutes=10)):
            t = b.starttime
            b.delete()
            self.stdout.write(self.style.SUCCESS(
                'Successfully deleted bookable that started at %s' % t
            ))
