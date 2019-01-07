# Generated by Django 2.1.2 on 2019-01-06 23:57

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('booker', '0002_calendar_student'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='calendar',
            name='bookable',
        ),
        migrations.AddField(
            model_name='calendar',
            name='gcal_id',
            field=models.CharField(default='no calendar', max_length=100),
        ),
        migrations.AddField(
            model_name='calendar',
            name='minutes_per_booking',
            field=models.IntegerField(default=-1),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='officehour',
            name='minutes_per_booking',
            field=models.IntegerField(default=-1),
            preserve_default=False,
        ),
        migrations.AlterField(
            model_name='calendar',
            name='id',
            field=models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID'),
        ),
    ]
