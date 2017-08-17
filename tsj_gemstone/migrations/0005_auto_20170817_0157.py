# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('tsj_gemstone', '0004_auto_20170815_1732'),
    ]

    operations = [
        migrations.AddField(
            model_name='diamondmarkup',
            name='maximum_carat_weight',
            field=models.DecimalField(decimal_places=2, max_digits=5, blank=True, help_text=b'The maximum carat weight for this markup to be applied.', null=True, verbose_name=b'Max Carat Weight'),
        ),
        migrations.AddField(
            model_name='diamondmarkup',
            name='maximum_price',
            field=models.DecimalField(decimal_places=2, max_digits=10, blank=True, help_text=b'The maximum price for this markup to be applied.', null=True, verbose_name=b'Max Price'),
        ),
        migrations.AddField(
            model_name='diamondmarkup',
            name='minimum_carat_weight',
            field=models.DecimalField(decimal_places=2, max_digits=5, blank=True, help_text=b'The minimum carat weight for this markup to be applied.', null=True, verbose_name=b'Min Carat Weight'),
        ),
        migrations.AddField(
            model_name='diamondmarkup',
            name='minimum_price',
            field=models.DecimalField(decimal_places=2, max_digits=10, blank=True, help_text=b'The minimum price for this markup to be applied.', null=True, verbose_name=b'Min Price'),
        ),
        migrations.AlterField(
            model_name='diamondmarkup',
            name='end_price',
            field=models.DecimalField(verbose_name=b'Max Price', max_digits=10, decimal_places=2),
        ),
        migrations.AlterField(
            model_name='diamondmarkup',
            name='start_price',
            field=models.DecimalField(verbose_name=b'Min Price', max_digits=10, decimal_places=2),
        ),
    ]
