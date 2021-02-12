# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('tsj_gemstone', '0008_lab_grown_markup'),
    ]

    operations = [
        migrations.AddField(
            model_name='diamond',
            name='cost',
            field=models.DecimalField(null=True, verbose_name=b'Cost', max_digits=10, decimal_places=2, blank=True),
        ),
    ]
