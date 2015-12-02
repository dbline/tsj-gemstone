# -*- coding: utf-8 -*-
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Deleting model 'Diamond'
        db.delete_table('tsj_gemstone_diamond')


    def backwards(self, orm):
        # Adding model 'Diamond'
        db.create_table('tsj_gemstone_diamond', (
            ('comment', self.gf('django.db.models.fields.TextField')(blank=True)),
            ('updated', self.gf('django.db.models.fields.DateTimeField')(auto_now=True, blank=True)),
            ('added', self.gf('django.db.models.fields.DateTimeField')(auto_now_add=True, blank=True)),
            ('fluorescence_color', self.gf('django.db.models.fields.related.ForeignKey')(related_name='diamond_fluorescence_color_set', null=True, to=orm['tsj_gemstone.FluorescenceColor'], blank=True)),
            ('symmetry', self.gf('django.db.models.fields.related.ForeignKey')(related_name='diamond_symmetry_set', null=True, to=orm['tsj_gemstone.Grading'], blank=True)),
            ('state', self.gf('django.db.models.fields.CharField')(max_length=255, blank=True)),
            ('certifier', self.gf('django.db.models.fields.related.ForeignKey')(related_name='diamond_certifier_set', null=True, to=orm['tsj_gemstone.Certifier'], blank=True)),
            ('price', self.gf('django.db.models.fields.DecimalField')(max_digits=10, decimal_places=2)),
            ('table_percent', self.gf('django.db.models.fields.DecimalField')(null=True, max_digits=5, decimal_places=2, blank=True)),
            ('carat_weight', self.gf('django.db.models.fields.DecimalField')(max_digits=5, decimal_places=2)),
            ('culet', self.gf('django.db.models.fields.CharField')(max_length=50, blank=True)),
            ('lot_num', self.gf('django.db.models.fields.CharField')(max_length=100, primary_key=True)),
            ('owner', self.gf('django.db.models.fields.CharField')(max_length=100, blank=True)),
            ('polish', self.gf('django.db.models.fields.related.ForeignKey')(related_name='diamond_polish_set', null=True, to=orm['tsj_gemstone.Grading'], blank=True)),
            ('stock_number', self.gf('django.db.models.fields.CharField')(max_length=100, blank=True)),
            ('clarity', self.gf('django.db.models.fields.related.ForeignKey')(related_name='diamond_clarity_set', null=True, to=orm['tsj_gemstone.Clarity'], blank=True)),
            ('cert_num', self.gf('django.db.models.fields.CharField')(max_length=255, blank=True)),
            ('city', self.gf('django.db.models.fields.CharField')(max_length=255, blank=True)),
            ('cut', self.gf('django.db.models.fields.related.ForeignKey')(related_name='diamond_cut_set', to=orm['tsj_gemstone.Cut'])),
            ('fluorescence', self.gf('django.db.models.fields.related.ForeignKey')(related_name='diamond_fluorescence_set', null=True, to=orm['tsj_gemstone.Fluorescence'], blank=True)),
            ('width', self.gf('django.db.models.fields.DecimalField')(null=True, max_digits=5, decimal_places=2, blank=True)),
            ('country', self.gf('django.db.models.fields.CharField')(max_length=255, blank=True)),
            ('length', self.gf('django.db.models.fields.DecimalField')(null=True, max_digits=5, decimal_places=2, blank=True)),
            ('cert_image', self.gf('django.db.models.fields.CharField')(max_length=255, blank=True)),
            ('depth_percent', self.gf('django.db.models.fields.DecimalField')(null=True, max_digits=5, decimal_places=2, blank=True)),
            ('color', self.gf('django.db.models.fields.related.ForeignKey')(related_name='diamond_color_set', null=True, to=orm['tsj_gemstone.Color'], blank=True)),
            ('depth', self.gf('django.db.models.fields.DecimalField')(null=True, max_digits=5, decimal_places=2, blank=True)),
            ('rap_date', self.gf('django.db.models.fields.DateTimeField')()),
            ('girdle', self.gf('django.db.models.fields.CharField')(max_length=50, blank=True)),
            ('carat_price', self.gf('django.db.models.fields.DecimalField')(max_digits=10, decimal_places=2)),
            ('cut_grade', self.gf('django.db.models.fields.related.ForeignKey')(related_name='diamond_cut_grade_set', null=True, to=orm['tsj_gemstone.Grading'], blank=True)),
        ))
        db.send_create_signal('tsj_gemstone', ['Diamond'])


    models = {
        'tsj_gemstone.certifier': {
            'Meta': {'ordering': "['abbr']", 'object_name': 'Certifier'},
            'abbr': ('django.db.models.fields.CharField', [], {'max_length': '255', 'db_index': 'True'}),
            'aliases': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'desc': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'disabled': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'url': ('django.db.models.fields.URLField', [], {'max_length': '200', 'blank': 'True'})
        },
        'tsj_gemstone.clarity': {
            'Meta': {'ordering': "['order', 'name']", 'object_name': 'Clarity'},
            'abbr': ('django.db.models.fields.CharField', [], {'max_length': '5', 'db_index': 'True'}),
            'aliases': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'desc': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'order': ('django.db.models.fields.PositiveSmallIntegerField', [], {'default': '9999'})
        },
        'tsj_gemstone.color': {
            'Meta': {'ordering': "['abbr']", 'object_name': 'Color'},
            'abbr': ('django.db.models.fields.CharField', [], {'max_length': '5', 'db_index': 'True'}),
            'aliases': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'})
        },
        'tsj_gemstone.cut': {
            'Meta': {'ordering': "['order', 'name']", 'object_name': 'Cut'},
            'abbr': ('django.db.models.fields.CharField', [], {'max_length': '5', 'db_index': 'True'}),
            'aliases': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'desc': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'order': ('django.db.models.fields.PositiveSmallIntegerField', [], {'default': '9999'})
        },
        'tsj_gemstone.diamondmarkup': {
            'Meta': {'ordering': "['percent']", 'object_name': 'DiamondMarkup'},
            'end_price': ('django.db.models.fields.DecimalField', [], {'max_digits': '10', 'decimal_places': '2'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'percent': ('django.db.models.fields.DecimalField', [], {'max_digits': '5', 'decimal_places': '2'}),
            'start_price': ('django.db.models.fields.DecimalField', [], {'max_digits': '10', 'decimal_places': '2'})
        },
        'tsj_gemstone.fluorescence': {
            'Meta': {'ordering': "['order', 'name']", 'object_name': 'Fluorescence'},
            'abbr': ('django.db.models.fields.CharField', [], {'max_length': '5', 'db_index': 'True'}),
            'aliases': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'order': ('django.db.models.fields.PositiveSmallIntegerField', [], {'default': '9999'})
        },
        'tsj_gemstone.fluorescencecolor': {
            'Meta': {'ordering': "['name']", 'object_name': 'FluorescenceColor'},
            'abbr': ('django.db.models.fields.CharField', [], {'max_length': '5', 'db_index': 'True'}),
            'aliases': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'})
        },
        'tsj_gemstone.grading': {
            'Meta': {'ordering': "['order', 'name']", 'object_name': 'Grading'},
            'abbr': ('django.db.models.fields.CharField', [], {'max_length': '10', 'db_index': 'True'}),
            'aliases': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'order': ('django.db.models.fields.PositiveSmallIntegerField', [], {'default': '9999'})
        },
        'tsj_gemstone.importlog': {
            'Meta': {'ordering': "['-imported']", 'object_name': 'ImportLog'},
            'failures': ('django.db.models.fields.PositiveIntegerField', [], {'default': '0'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'imported': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'successes': ('django.db.models.fields.PositiveIntegerField', [], {'default': '0'}),
            'type': ('django.db.models.fields.CharField', [], {'default': "'R'", 'max_length': '1'})
        },
        'tsj_gemstone.importlogentry': {
            'Meta': {'ordering': "('_order',)", 'object_name': 'ImportLogEntry'},
            '_order': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            'added': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'csv_line': ('django.db.models.fields.PositiveIntegerField', [], {'default': '0'}),
            'details': ('django.db.models.fields.TextField', [], {}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'import_log': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['tsj_gemstone.ImportLog']"}),
            'problem': ('django.db.models.fields.CharField', [], {'max_length': '255'})
        }
    }

    complete_apps = ['tsj_gemstone']