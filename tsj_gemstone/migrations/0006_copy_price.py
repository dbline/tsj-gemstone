# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models

def startend_to_minmax(apps, schema_editor):
    # We can't import the DiamondMarkup model directly as it may be a newer
    # version than this migration expects. We use the historical version.
    DiamondMarkup = apps.get_model('tsj_gemstone', 'DiamondMarkup')
    for markup in DiamondMarkup.objects.all():
        markup.minimum_price = markup.start_price
        markup.maximum_price = markup.end_price
        markup.save()

def minmax_to_startend(apps, schema_editor):
    # We can't import the DiamondMarkup model directly as it may be a newer
    # version than this migration expects. We use the historical version.
    DiamondMarkup = apps.get_model('tsj_gemstone', 'DiamondMarkup')
    for markup in DiamondMarkup.objects.all():
        markup.start_price = markup.minimum_price
        markup.end_price = markup.maximum_price
        markup.save()

class Migration(migrations.Migration):

    dependencies = [
        ('tsj_gemstone', '0005_auto_20170817_0157'),
    ]

    operations = [
        migrations.RunPython(startend_to_minmax, minmax_to_startend),
    ]
