from django.conf import settings
from django.db import migrations

SNAPSHOT_TASK_NAME = "warehouse.create_scheduled_inventory_snapshot"


def use_configured_timezone(apps, schema_editor):
    """Schedules created while the project ran in UTC are re-anchored to TIME_ZONE."""
    PeriodicTask = apps.get_model("django_celery_beat", "PeriodicTask")
    CrontabSchedule = apps.get_model("django_celery_beat", "CrontabSchedule")
    ids = PeriodicTask.objects.filter(
        task=SNAPSHOT_TASK_NAME, crontab__isnull=False
    ).values_list("crontab_id", flat=True)
    CrontabSchedule.objects.filter(pk__in=list(ids)).update(timezone=settings.TIME_ZONE)


class Migration(migrations.Migration):
    dependencies = [
        ("warehouse", "0094_global_settings_code_sequence"),
        ("django_celery_beat", "0019_alter_periodictasks_options"),
    ]

    operations = [
        migrations.RunPython(use_configured_timezone, migrations.RunPython.noop)
    ]
