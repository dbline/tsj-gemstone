# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('tsj_gemstone', '0002_diamond_data'),
    ]

    operations = [
        migrations.AlterOrderWithRespectTo(
            name='importlogentry',
            order_with_respect_to=None,
        ),
    ]
