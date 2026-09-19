"""初始追蹤標的（feature-spec §1）。"""
from django.db import migrations

from notify.constants import DEFAULT_TARGETS


def seed(apps, schema_editor):
    WatchTarget = apps.get_model("notify", "WatchTarget")
    for t in DEFAULT_TARGETS:
        WatchTarget.objects.get_or_create(symbol=t["symbol"], defaults=t)


def unseed(apps, schema_editor):
    WatchTarget = apps.get_model("notify", "WatchTarget")
    symbols = [t["symbol"] for t in DEFAULT_TARGETS]
    WatchTarget.objects.filter(symbol__in=symbols).delete()


class Migration(migrations.Migration):
    dependencies = [("notify", "0001_initial")]
    operations = [migrations.RunPython(seed, unseed)]
