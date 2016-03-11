# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
import django.utils.timezone
import model_utils.fields


class Migration(migrations.Migration):

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='CutView',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('name', models.CharField(max_length=100)),
                ('abbr', models.CharField(max_length=5, verbose_name=b'Abbreviation', db_index=True)),
                ('aliases', models.TextField(help_text=b'One entry per line. Case-insensitive.', blank=True)),
                ('desc', models.TextField(verbose_name=b'Description', blank=True)),
                ('order', models.PositiveSmallIntegerField(default=9999)),
                ('is_local', models.BooleanField(default=False)),
            ],
            options={
                'ordering': ['order', 'name'],
                'verbose_name': 'cut',
                'abstract': False,
                'managed': False,
                'verbose_name_plural': 'cuts',
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='Certifier',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('name', models.CharField(max_length=255)),
                ('abbr', models.CharField(max_length=255, verbose_name=b'Abbreviation', db_index=True)),
                ('aliases', models.TextField(help_text=b'One entry per line. Case-insensitive.', blank=True)),
                ('url', models.URLField(verbose_name=b'URL', blank=True)),
                ('desc', models.TextField(verbose_name=b'Description', blank=True)),
                ('disabled', models.BooleanField(default=False)),
            ],
            options={
                'ordering': ['abbr'],
                'verbose_name': 'Certifier',
                'verbose_name_plural': 'Certifiers',
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='Clarity',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('name', models.CharField(max_length=100)),
                ('abbr', models.CharField(max_length=5, verbose_name=b'Abbreviation', db_index=True)),
                ('aliases', models.TextField(help_text=b'One entry per line. Case-insensitive.', blank=True)),
                ('desc', models.TextField(verbose_name=b'Description', blank=True)),
                ('order', models.PositiveSmallIntegerField(default=9999)),
            ],
            options={
                'ordering': ['order', 'name'],
                'verbose_name': 'Clarity',
                'verbose_name_plural': 'Clarity',
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='Color',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('abbr', models.CharField(max_length=5, db_index=True)),
                ('aliases', models.TextField(help_text=b'One entry per line. Case-insensitive.', blank=True)),
                ('desc', models.TextField(verbose_name=b'Description', blank=True)),
            ],
            options={
                'ordering': ['abbr'],
                'verbose_name': 'Color',
                'verbose_name_plural': 'Colors',
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='Cut',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('name', models.CharField(max_length=100)),
                ('abbr', models.CharField(max_length=5, verbose_name=b'Abbreviation', db_index=True)),
                ('aliases', models.TextField(help_text=b'One entry per line. Case-insensitive.', blank=True)),
                ('desc', models.TextField(verbose_name=b'Description', blank=True)),
                ('order', models.PositiveSmallIntegerField(default=9999)),
            ],
            options={
                'ordering': ['order', 'name'],
                'verbose_name': 'Cut',
                'verbose_name_plural': 'Cuts',
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='Diamond',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('created', model_utils.fields.AutoCreatedField(default=django.utils.timezone.now, verbose_name='created', editable=False)),
                ('modified', model_utils.fields.AutoLastModifiedField(default=django.utils.timezone.now, verbose_name='modified', editable=False)),
                ('active', models.BooleanField(default=True)),
                ('source', models.CharField(max_length=64)),
                ('lot_num', models.CharField(max_length=100, verbose_name=b'Lot #', blank=True)),
                ('stock_number', models.CharField(max_length=100, verbose_name=b'Stock #', blank=True)),
                ('owner', models.CharField(max_length=255, verbose_name=b'Owner', blank=True)),
                ('image', models.CharField(max_length=255, null=True, verbose_name=b'Image URL', blank=True)),
                ('image_local', models.FileField(upload_to=b'tsj_gemstone/images/', null=True, verbose_name=b'Upload Image', blank=True)),
                ('carat_weight', models.DecimalField(verbose_name=b'Weight', max_digits=5, decimal_places=2, db_index=True)),
                ('carat_price', models.DecimalField(verbose_name=b'Price / Ct.', max_digits=10, decimal_places=2)),
                ('price', models.DecimalField(verbose_name=b'Price', max_digits=10, decimal_places=2)),
                ('cert_num', models.CharField(max_length=255, verbose_name=b'Lab Report #', blank=True)),
                ('cert_image', models.CharField(max_length=255, verbose_name=b'Lab Report URL', blank=True)),
                ('cert_image_local', models.FileField(upload_to=b'tsj_gemstone/certificates/', verbose_name=b'Upload Cert Image', blank=True)),
                ('depth_percent', models.DecimalField(null=True, verbose_name=b'Depth %', max_digits=5, decimal_places=2, blank=True)),
                ('table_percent', models.DecimalField(null=True, verbose_name=b'Table %', max_digits=5, decimal_places=2, blank=True)),
                ('girdle', models.CharField(max_length=50, verbose_name=b'Girdle', blank=True)),
                ('culet', models.CharField(max_length=50, verbose_name=b'Culet', blank=True)),
                ('length', models.DecimalField(null=True, verbose_name=b'Length', max_digits=5, decimal_places=2, blank=True)),
                ('width', models.DecimalField(null=True, verbose_name=b'Width', max_digits=5, decimal_places=2, blank=True)),
                ('depth', models.DecimalField(null=True, verbose_name=b'Depth', max_digits=5, decimal_places=2, blank=True)),
                ('comment', models.TextField(verbose_name=b'Comment', blank=True)),
                ('city', models.CharField(max_length=255, verbose_name=b'City', blank=True)),
                ('state', models.CharField(max_length=255, verbose_name=b'State', blank=True)),
                ('country', models.CharField(max_length=255, verbose_name=b'Country', blank=True)),
                ('manmade', models.NullBooleanField(default=False, verbose_name=b'Man-made')),
                ('rap_date', models.DateTimeField(null=True, verbose_name=b'Date Added', blank=True)),
                ('certifier', models.ForeignKey(related_name='diamond_certifier_set', verbose_name=b'Lab', blank=True, to='tsj_gemstone.Certifier', null=True)),
                ('clarity', models.ForeignKey(related_name='diamond_clarity_set', verbose_name=b'Clarity', blank=True, to='tsj_gemstone.Clarity', null=True)),
                ('color', models.ForeignKey(related_name='diamond_color_set', verbose_name=b'Color', blank=True, to='tsj_gemstone.Color', null=True)),
                ('cut', models.ForeignKey(related_name='diamond_cut_set', verbose_name=b'Cut', to='tsj_gemstone.Cut')),
            ],
            options={
                'ordering': ['carat_weight'],
                'abstract': False,
                'verbose_name': 'Diamond',
                'verbose_name_plural': 'Diamonds',
                'permissions': (('can_import_diamonds', 'Can Import Diamonds'),),
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='DiamondMarkup',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('start_price', models.DecimalField(verbose_name=b'Start Price', max_digits=10, decimal_places=2)),
                ('end_price', models.DecimalField(verbose_name=b'End Price', max_digits=10, decimal_places=2)),
                ('percent', models.DecimalField(help_text=b'Markup percent (35.00 for 35%)', max_digits=5, decimal_places=2)),
            ],
            options={
                'ordering': ['percent'],
                'verbose_name': 'Diamond Markup',
                'verbose_name_plural': 'Diamond Markups',
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='Fluorescence',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('name', models.CharField(max_length=100)),
                ('abbr', models.CharField(max_length=5, verbose_name=b'Abbreviation', db_index=True)),
                ('aliases', models.TextField(help_text=b'One entry per line. Case-insensitive.', blank=True)),
                ('desc', models.TextField(verbose_name=b'Description', blank=True)),
                ('order', models.PositiveSmallIntegerField(default=9999)),
            ],
            options={
                'ordering': ['order', 'name'],
                'verbose_name': 'Fluorescence',
                'verbose_name_plural': 'Fluorescence',
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='FluorescenceColor',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('name', models.CharField(max_length=100)),
                ('abbr', models.CharField(max_length=5, verbose_name=b'Abbreviation', db_index=True)),
                ('aliases', models.TextField(help_text=b'One entry per line. Case-insensitive.', blank=True)),
                ('desc', models.TextField(verbose_name=b'Description', blank=True)),
            ],
            options={
                'ordering': ['name'],
                'verbose_name': 'Fluorescence Color',
                'verbose_name_plural': 'Fluorescence Colors',
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='Grading',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('name', models.CharField(max_length=100)),
                ('abbr', models.CharField(max_length=10, verbose_name=b'Abbreviation', db_index=True)),
                ('aliases', models.TextField(help_text=b'One entry per line. Case-insensitive.', blank=True)),
                ('desc', models.TextField(verbose_name=b'Description', blank=True)),
                ('order', models.PositiveSmallIntegerField(default=9999)),
            ],
            options={
                'ordering': ['order', 'name'],
                'verbose_name': 'Grading',
                'verbose_name_plural': 'Gradings',
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='ImportLog',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('imported', models.DateTimeField(auto_now_add=True, verbose_name=b'Imported')),
                ('type', models.CharField(default=b'R', max_length=1, verbose_name=b'Type', choices=[(b'R', b'Ring'), (b'D', b'Diamond')])),
                ('successes', models.PositiveIntegerField(default=0, help_text=b'The total number of items that were successfully imported.', verbose_name=b'Successes')),
                ('failures', models.PositiveIntegerField(default=0, help_text=b'The total number of items that failed to import.', verbose_name=b'Failures')),
            ],
            options={
                'ordering': ['-imported'],
                'verbose_name': 'Import Log',
                'verbose_name_plural': 'Import Logs',
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='ImportLogEntry',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('added', models.DateTimeField(auto_now_add=True, verbose_name=b'Added')),
                ('csv_line', models.PositiveIntegerField(default=0, help_text=b'The line that was being imported from the CSV file.', verbose_name=b'CSV Line')),
                ('problem', models.CharField(help_text=b"The reason the line wasn't imported.", max_length=255, verbose_name=b'Problem')),
                ('details', models.TextField(help_text=b'Some details about the failed import attempt to help with debugging.', verbose_name=b'Details')),
                ('import_log', models.ForeignKey(to='tsj_gemstone.ImportLog')),
            ],
            options={
                'ordering': ['-added', 'csv_line'],
                'verbose_name': 'Import Log Entry',
                'verbose_name_plural': 'Import Log Entries',
            },
            bases=(models.Model,),
        ),
        migrations.AlterOrderWithRespectTo(
            name='importlogentry',
            order_with_respect_to='import_log',
        ),
        migrations.AddField(
            model_name='diamond',
            name='cut_grade',
            field=models.ForeignKey(related_name='diamond_cut_grade_set', verbose_name=b'Cut Grade', blank=True, to='tsj_gemstone.Grading', null=True),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='diamond',
            name='fluorescence',
            field=models.ForeignKey(related_name='diamond_fluorescence_set', verbose_name=b'Fluorescence', blank=True, to='tsj_gemstone.Fluorescence', null=True),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='diamond',
            name='fluorescence_color',
            field=models.ForeignKey(related_name='diamond_fluorescence_color_set', verbose_name=b'Fluorescence Color', blank=True, to='tsj_gemstone.FluorescenceColor', null=True),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='diamond',
            name='polish',
            field=models.ForeignKey(related_name='diamond_polish_set', verbose_name=b'Polish', blank=True, to='tsj_gemstone.Grading', null=True),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='diamond',
            name='symmetry',
            field=models.ForeignKey(related_name='diamond_symmetry_set', verbose_name=b'Symmetry', blank=True, to='tsj_gemstone.Grading', null=True),
            preserve_default=True,
        ),
    ]
