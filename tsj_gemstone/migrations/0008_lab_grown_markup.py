# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('tsj_gemstone', '0007_auto_20170817_0213'),
    ]

    operations = [
        migrations.CreateModel(
            name='LabGrownDiamondMarkup',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('minimum_carat_weight', models.DecimalField(decimal_places=2, max_digits=5, blank=True, help_text=b'The minimum carat weight for this markup to be applied.', null=True, verbose_name=b'Min Carat Weight')),
                ('maximum_carat_weight', models.DecimalField(decimal_places=2, max_digits=5, blank=True, help_text=b'The maximum carat weight for this markup to be applied.', null=True, verbose_name=b'Max Carat Weight')),
                ('minimum_price', models.DecimalField(decimal_places=2, max_digits=10, blank=True, help_text=b'The minimum price for this markup to be applied.', null=True, verbose_name=b'Min Price')),
                ('maximum_price', models.DecimalField(decimal_places=2, max_digits=10, blank=True, help_text=b'The maximum price for this markup to be applied.', null=True, verbose_name=b'Max Price')),
                ('percent', models.DecimalField(help_text=b'Markup percent (35.00 for 35%)', max_digits=5, decimal_places=2)),
            ],
            options={
                'ordering': ['percent'],
                'verbose_name': 'Lab Grown Markup',
                'verbose_name_plural': 'Lab Grown Markups',
            },
        ),
        migrations.AlterField(
            model_name='diamond',
            name='manmade',
            field=models.NullBooleanField(default=False, verbose_name=b'Lab Grown'),
        ),
    ]
