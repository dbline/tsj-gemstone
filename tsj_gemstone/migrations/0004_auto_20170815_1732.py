# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('tsj_gemstone', '0003_auto_20170731_2125'),
    ]

    operations = [
        migrations.CreateModel(
            name='FancyColor',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('name', models.CharField(max_length=100)),
                ('aliases', models.TextField(help_text=b'One entry per line. Case-insensitive.', blank=True)),
            ],
            options={
                'ordering': ['name'],
                'verbose_name': 'Fancy Color',
                'verbose_name_plural': 'Fancy Colors',
            },
        ),
        migrations.CreateModel(
            name='FancyColorIntensity',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('name', models.CharField(max_length=100)),
                ('aliases', models.TextField(help_text=b'One entry per line. Case-insensitive.', blank=True)),
                ('order', models.PositiveSmallIntegerField(default=9999)),
            ],
            options={
                'ordering': ['order', 'name'],
                'verbose_name': 'Fancy Color Intensity',
                'verbose_name_plural': 'Fancy Color Intensities',
            },
        ),
        migrations.CreateModel(
            name='FancyColorOvertone',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('name', models.CharField(max_length=100)),
                ('aliases', models.TextField(help_text=b'One entry per line. Case-insensitive.', blank=True)),
            ],
            options={
                'ordering': ['name'],
                'verbose_name': 'Fancy Color Overtone',
                'verbose_name_plural': 'Fancy Color Overtones',
            },
        ),
        migrations.AddField(
            model_name='diamond',
            name='laser_inscribed',
            field=models.NullBooleanField(default=False, verbose_name=b'Laser Inscribed'),
        ),
        migrations.AddField(
            model_name='diamond',
            name='fancy_color',
            field=models.ForeignKey(verbose_name=b'Fancy Color', blank=True, to='tsj_gemstone.FancyColor', null=True),
        ),
        migrations.AddField(
            model_name='diamond',
            name='fancy_color_intensity',
            field=models.ForeignKey(verbose_name=b'Fancy Color Intensity', blank=True, to='tsj_gemstone.FancyColorIntensity', null=True),
        ),
        migrations.AddField(
            model_name='diamond',
            name='fancy_color_overtone',
            field=models.ForeignKey(verbose_name=b'Fancy Color Overtone', blank=True, to='tsj_gemstone.FancyColorOvertone', null=True),
        ),
    ]
