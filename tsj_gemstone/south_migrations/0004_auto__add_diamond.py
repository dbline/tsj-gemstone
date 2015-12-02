# -*- coding: utf-8 -*-
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Adding model 'Diamond'
        db.create_table('tsj_gemstone_diamond', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('created', self.gf('model_utils.fields.AutoCreatedField')(default=datetime.datetime.now)),
            ('modified', self.gf('model_utils.fields.AutoLastModifiedField')(default=datetime.datetime.now)),
            ('active', self.gf('django.db.models.fields.BooleanField')(default=True)),
            ('source', self.gf('django.db.models.fields.CharField')(max_length=64)),
            ('lot_num', self.gf('django.db.models.fields.CharField')(max_length=100, blank=True)),
            ('stock_number', self.gf('django.db.models.fields.CharField')(max_length=100, blank=True)),
            ('owner', self.gf('django.db.models.fields.CharField')(max_length=100, blank=True)),
            ('cut', self.gf('django.db.models.fields.related.ForeignKey')(related_name='diamond_cut_set', to=orm['tsj_gemstone.Cut'])),
            ('cut_grade', self.gf('django.db.models.fields.related.ForeignKey')(blank=True, related_name='diamond_cut_grade_set', null=True, to=orm['tsj_gemstone.Grading'])),
            ('color', self.gf('django.db.models.fields.related.ForeignKey')(blank=True, related_name='diamond_color_set', null=True, to=orm['tsj_gemstone.Color'])),
            ('clarity', self.gf('django.db.models.fields.related.ForeignKey')(blank=True, related_name='diamond_clarity_set', null=True, to=orm['tsj_gemstone.Clarity'])),
            ('carat_weight', self.gf('django.db.models.fields.DecimalField')(max_digits=5, decimal_places=2)),
            ('carat_price', self.gf('django.db.models.fields.DecimalField')(max_digits=10, decimal_places=2)),
            ('price', self.gf('django.db.models.fields.DecimalField')(max_digits=10, decimal_places=2)),
            ('certifier', self.gf('django.db.models.fields.related.ForeignKey')(blank=True, related_name='diamond_certifier_set', null=True, to=orm['tsj_gemstone.Certifier'])),
            ('cert_num', self.gf('django.db.models.fields.CharField')(max_length=255, blank=True)),
            ('cert_image', self.gf('django.db.models.fields.CharField')(max_length=255, blank=True)),
            ('depth_percent', self.gf('django.db.models.fields.DecimalField')(null=True, max_digits=5, decimal_places=2, blank=True)),
            ('table_percent', self.gf('django.db.models.fields.DecimalField')(null=True, max_digits=5, decimal_places=2, blank=True)),
            ('girdle', self.gf('django.db.models.fields.CharField')(max_length=50, blank=True)),
            ('culet', self.gf('django.db.models.fields.CharField')(max_length=50, blank=True)),
            ('polish', self.gf('django.db.models.fields.related.ForeignKey')(blank=True, related_name='diamond_polish_set', null=True, to=orm['tsj_gemstone.Grading'])),
            ('symmetry', self.gf('django.db.models.fields.related.ForeignKey')(blank=True, related_name='diamond_symmetry_set', null=True, to=orm['tsj_gemstone.Grading'])),
            ('fluorescence', self.gf('django.db.models.fields.related.ForeignKey')(blank=True, related_name='diamond_fluorescence_set', null=True, to=orm['tsj_gemstone.Fluorescence'])),
            ('fluorescence_color', self.gf('django.db.models.fields.related.ForeignKey')(blank=True, related_name='diamond_fluorescence_color_set', null=True, to=orm['tsj_gemstone.FluorescenceColor'])),
            ('length', self.gf('django.db.models.fields.DecimalField')(null=True, max_digits=5, decimal_places=2, blank=True)),
            ('width', self.gf('django.db.models.fields.DecimalField')(null=True, max_digits=5, decimal_places=2, blank=True)),
            ('depth', self.gf('django.db.models.fields.DecimalField')(null=True, max_digits=5, decimal_places=2, blank=True)),
            ('comment', self.gf('django.db.models.fields.TextField')(blank=True)),
            ('city', self.gf('django.db.models.fields.CharField')(max_length=255, blank=True)),
            ('state', self.gf('django.db.models.fields.CharField')(max_length=255, blank=True)),
            ('country', self.gf('django.db.models.fields.CharField')(max_length=255, blank=True)),
            ('rap_date', self.gf('django.db.models.fields.DateTimeField')(null=True, blank=True)),
        ))
        db.send_create_signal('tsj_gemstone', ['Diamond'])


    def backwards(self, orm):
        # Deleting model 'Diamond'
        db.delete_table('tsj_gemstone_diamond')


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
        'tsj_gemstone.diamond': {
            'Meta': {'ordering': "['carat_weight']", 'object_name': 'Diamond'},
            'active': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'carat_price': ('django.db.models.fields.DecimalField', [], {'max_digits': '10', 'decimal_places': '2'}),
            'carat_weight': ('django.db.models.fields.DecimalField', [], {'max_digits': '5', 'decimal_places': '2'}),
            'cert_image': ('django.db.models.fields.CharField', [], {'max_length': '255', 'blank': 'True'}),
            'cert_num': ('django.db.models.fields.CharField', [], {'max_length': '255', 'blank': 'True'}),
            'certifier': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'diamond_certifier_set'", 'null': 'True', 'to': "orm['tsj_gemstone.Certifier']"}),
            'city': ('django.db.models.fields.CharField', [], {'max_length': '255', 'blank': 'True'}),
            'clarity': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'diamond_clarity_set'", 'null': 'True', 'to': "orm['tsj_gemstone.Clarity']"}),
            'color': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'diamond_color_set'", 'null': 'True', 'to': "orm['tsj_gemstone.Color']"}),
            'comment': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'country': ('django.db.models.fields.CharField', [], {'max_length': '255', 'blank': 'True'}),
            'created': ('model_utils.fields.AutoCreatedField', [], {'default': 'datetime.datetime.now'}),
            'culet': ('django.db.models.fields.CharField', [], {'max_length': '50', 'blank': 'True'}),
            'cut': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'diamond_cut_set'", 'to': "orm['tsj_gemstone.Cut']"}),
            'cut_grade': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'diamond_cut_grade_set'", 'null': 'True', 'to': "orm['tsj_gemstone.Grading']"}),
            'depth': ('django.db.models.fields.DecimalField', [], {'null': 'True', 'max_digits': '5', 'decimal_places': '2', 'blank': 'True'}),
            'depth_percent': ('django.db.models.fields.DecimalField', [], {'null': 'True', 'max_digits': '5', 'decimal_places': '2', 'blank': 'True'}),
            'fluorescence': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'diamond_fluorescence_set'", 'null': 'True', 'to': "orm['tsj_gemstone.Fluorescence']"}),
            'fluorescence_color': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'diamond_fluorescence_color_set'", 'null': 'True', 'to': "orm['tsj_gemstone.FluorescenceColor']"}),
            'girdle': ('django.db.models.fields.CharField', [], {'max_length': '50', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'length': ('django.db.models.fields.DecimalField', [], {'null': 'True', 'max_digits': '5', 'decimal_places': '2', 'blank': 'True'}),
            'lot_num': ('django.db.models.fields.CharField', [], {'max_length': '100', 'blank': 'True'}),
            'modified': ('model_utils.fields.AutoLastModifiedField', [], {'default': 'datetime.datetime.now'}),
            'owner': ('django.db.models.fields.CharField', [], {'max_length': '100', 'blank': 'True'}),
            'polish': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'diamond_polish_set'", 'null': 'True', 'to': "orm['tsj_gemstone.Grading']"}),
            'price': ('django.db.models.fields.DecimalField', [], {'max_digits': '10', 'decimal_places': '2'}),
            'rap_date': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'}),
            'source': ('django.db.models.fields.CharField', [], {'max_length': '64'}),
            'state': ('django.db.models.fields.CharField', [], {'max_length': '255', 'blank': 'True'}),
            'stock_number': ('django.db.models.fields.CharField', [], {'max_length': '100', 'blank': 'True'}),
            'symmetry': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'diamond_symmetry_set'", 'null': 'True', 'to': "orm['tsj_gemstone.Grading']"}),
            'table_percent': ('django.db.models.fields.DecimalField', [], {'null': 'True', 'max_digits': '5', 'decimal_places': '2', 'blank': 'True'}),
            'width': ('django.db.models.fields.DecimalField', [], {'null': 'True', 'max_digits': '5', 'decimal_places': '2', 'blank': 'True'})
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