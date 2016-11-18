# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models
import jsonfield.fields


class Migration(migrations.Migration):

    dependencies = [
        ('tsj_gemstone', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='diamond',
            name='data',
            field=jsonfield.fields.JSONField(default={}),
        ),
    ]
