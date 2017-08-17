# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('tsj_gemstone', '0006_copy_price'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='diamondmarkup',
            name='end_price',
        ),
        migrations.RemoveField(
            model_name='diamondmarkup',
            name='start_price',
        ),
    ]
