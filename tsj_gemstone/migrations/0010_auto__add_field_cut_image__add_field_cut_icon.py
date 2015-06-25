# -*- coding: utf-8 -*-
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Adding field 'Cut.image'
        db.add_column(u'tsj_gemstone_cut', 'image',
                      self.gf('django.db.models.fields.files.ImageField')(default='', max_length=100, blank=True),
                      keep_default=False)

        # Adding field 'Cut.icon'
        db.add_column(u'tsj_gemstone_cut', 'icon',
                      self.gf('django.db.models.fields.TextField')(default='', blank=True),
                      keep_default=False)


    def backwards(self, orm):
        # Deleting field 'Cut.image'
        db.delete_column(u'tsj_gemstone_cut', 'image')

        # Deleting field 'Cut.icon'
        db.delete_column(u'tsj_gemstone_cut', 'icon')


    models = {
        u'tsj_gemstone.certifier': {
            'Meta': {'ordering': "['abbr']", 'object_name': 'Certifier'},
            'abbr': ('django.db.models.fields.CharField', [], {'max_length': '255', 'db_index': 'True'}),
            'aliases': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'desc': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'disabled': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'url': ('django.db.models.fields.URLField', [], {'max_length': '200', 'blank': 'True'})
        },
        u'tsj_gemstone.clarity': {
            'Meta': {'ordering': "['order', 'name']", 'object_name': 'Clarity'},
            'abbr': ('django.db.models.fields.CharField', [], {'max_length': '5', 'db_index': 'True'}),
            'aliases': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'desc': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'order': ('django.db.models.fields.PositiveSmallIntegerField', [], {'default': '9999'})
        },
        u'tsj_gemstone.color': {
            'Meta': {'ordering': "['abbr']", 'object_name': 'Color'},
            'abbr': ('django.db.models.fields.CharField', [], {'max_length': '5', 'db_index': 'True'}),
            'aliases': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'})
        },
        u'tsj_gemstone.cut': {
            'Meta': {'ordering': "['order', 'name']", 'object_name': 'Cut'},
            'abbr': ('django.db.models.fields.CharField', [], {'max_length': '5', 'db_index': 'True'}),
            'aliases': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'desc': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'icon': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'image': ('django.db.models.fields.files.ImageField', [], {'max_length': '100', 'blank': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'order': ('django.db.models.fields.PositiveSmallIntegerField', [], {'default': '9999'})
        },
        u'tsj_gemstone.cutview': {
            'Meta': {'ordering': "['order', 'name']", 'object_name': 'CutView', 'managed': 'False'},
            'abbr': ('django.db.models.fields.CharField', [], {'max_length': '5', 'db_index': 'True'}),
            'aliases': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'desc': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_local': ('django.db.models.fields.BooleanField', [], {}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'order': ('django.db.models.fields.PositiveSmallIntegerField', [], {'default': '9999'})
        },
        u'tsj_gemstone.diamond': {
            'Meta': {'ordering': "['carat_weight']", 'object_name': 'Diamond'},
            'active': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'carat_price': ('django.db.models.fields.DecimalField', [], {'max_digits': '10', 'decimal_places': '2'}),
            'carat_weight': ('django.db.models.fields.DecimalField', [], {'max_digits': '5', 'decimal_places': '2', 'db_index': 'True'}),
            'cert_image': ('django.db.models.fields.CharField', [], {'max_length': '255', 'blank': 'True'}),
            'cert_image_local': ('django.db.models.fields.files.FileField', [], {'max_length': '100', 'blank': 'True'}),
            'cert_num': ('django.db.models.fields.CharField', [], {'max_length': '255', 'blank': 'True'}),
            'certifier': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'diamond_certifier_set'", 'null': 'True', 'to': u"orm['tsj_gemstone.Certifier']"}),
            'city': ('django.db.models.fields.CharField', [], {'max_length': '255', 'blank': 'True'}),
            'clarity': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'diamond_clarity_set'", 'null': 'True', 'to': u"orm['tsj_gemstone.Clarity']"}),
            'color': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'diamond_color_set'", 'null': 'True', 'to': u"orm['tsj_gemstone.Color']"}),
            'comment': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'country': ('django.db.models.fields.CharField', [], {'max_length': '255', 'blank': 'True'}),
            'created': ('model_utils.fields.AutoCreatedField', [], {'default': 'datetime.datetime.now'}),
            'culet': ('django.db.models.fields.CharField', [], {'max_length': '50', 'blank': 'True'}),
            'cut': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'diamond_cut_set'", 'to': u"orm['tsj_gemstone.Cut']"}),
            'cut_grade': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'diamond_cut_grade_set'", 'null': 'True', 'to': u"orm['tsj_gemstone.Grading']"}),
            'depth': ('django.db.models.fields.DecimalField', [], {'null': 'True', 'max_digits': '5', 'decimal_places': '2', 'blank': 'True'}),
            'depth_percent': ('django.db.models.fields.DecimalField', [], {'null': 'True', 'max_digits': '5', 'decimal_places': '2', 'blank': 'True'}),
            'fluorescence': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'diamond_fluorescence_set'", 'null': 'True', 'to': u"orm['tsj_gemstone.Fluorescence']"}),
            'fluorescence_color': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'diamond_fluorescence_color_set'", 'null': 'True', 'to': u"orm['tsj_gemstone.FluorescenceColor']"}),
            'girdle': ('django.db.models.fields.CharField', [], {'max_length': '50', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'length': ('django.db.models.fields.DecimalField', [], {'null': 'True', 'max_digits': '5', 'decimal_places': '2', 'blank': 'True'}),
            'lot_num': ('django.db.models.fields.CharField', [], {'max_length': '100', 'blank': 'True'}),
            'manmade': ('django.db.models.fields.NullBooleanField', [], {'default': 'False', 'null': 'True', 'blank': 'True'}),
            'modified': ('model_utils.fields.AutoLastModifiedField', [], {'default': 'datetime.datetime.now'}),
            'owner': ('django.db.models.fields.CharField', [], {'max_length': '255', 'blank': 'True'}),
            'polish': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'diamond_polish_set'", 'null': 'True', 'to': u"orm['tsj_gemstone.Grading']"}),
            'price': ('django.db.models.fields.DecimalField', [], {'max_digits': '10', 'decimal_places': '2'}),
            'rap_date': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'}),
            'source': ('django.db.models.fields.CharField', [], {'max_length': '64'}),
            'state': ('django.db.models.fields.CharField', [], {'max_length': '255', 'blank': 'True'}),
            'stock_number': ('django.db.models.fields.CharField', [], {'max_length': '100', 'blank': 'True'}),
            'symmetry': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'diamond_symmetry_set'", 'null': 'True', 'to': u"orm['tsj_gemstone.Grading']"}),
            'table_percent': ('django.db.models.fields.DecimalField', [], {'null': 'True', 'max_digits': '5', 'decimal_places': '2', 'blank': 'True'}),
            'width': ('django.db.models.fields.DecimalField', [], {'null': 'True', 'max_digits': '5', 'decimal_places': '2', 'blank': 'True'})
        },
        u'tsj_gemstone.diamondmarkup': {
            'Meta': {'ordering': "['percent']", 'object_name': 'DiamondMarkup'},
            'end_price': ('django.db.models.fields.DecimalField', [], {'max_digits': '10', 'decimal_places': '2'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'percent': ('django.db.models.fields.DecimalField', [], {'max_digits': '5', 'decimal_places': '2'}),
            'start_price': ('django.db.models.fields.DecimalField', [], {'max_digits': '10', 'decimal_places': '2'})
        },
        u'tsj_gemstone.fluorescence': {
            'Meta': {'ordering': "['order', 'name']", 'object_name': 'Fluorescence'},
            'abbr': ('django.db.models.fields.CharField', [], {'max_length': '5', 'db_index': 'True'}),
            'aliases': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'order': ('django.db.models.fields.PositiveSmallIntegerField', [], {'default': '9999'})
        },
        u'tsj_gemstone.fluorescencecolor': {
            'Meta': {'ordering': "['name']", 'object_name': 'FluorescenceColor'},
            'abbr': ('django.db.models.fields.CharField', [], {'max_length': '5', 'db_index': 'True'}),
            'aliases': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'})
        },
        u'tsj_gemstone.grading': {
            'Meta': {'ordering': "['order', 'name']", 'object_name': 'Grading'},
            'abbr': ('django.db.models.fields.CharField', [], {'max_length': '10', 'db_index': 'True'}),
            'aliases': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'order': ('django.db.models.fields.PositiveSmallIntegerField', [], {'default': '9999'})
        },
        u'tsj_gemstone.importlog': {
            'Meta': {'ordering': "['-imported']", 'object_name': 'ImportLog'},
            'failures': ('django.db.models.fields.PositiveIntegerField', [], {'default': '0'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'imported': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'successes': ('django.db.models.fields.PositiveIntegerField', [], {'default': '0'}),
            'type': ('django.db.models.fields.CharField', [], {'default': "'R'", 'max_length': '1'})
        },
        u'tsj_gemstone.importlogentry': {
            'Meta': {'ordering': "(u'_order',)", 'object_name': 'ImportLogEntry'},
            '_order': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            'added': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'csv_line': ('django.db.models.fields.PositiveIntegerField', [], {'default': '0'}),
            'details': ('django.db.models.fields.TextField', [], {}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'import_log': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['tsj_gemstone.ImportLog']"}),
            'problem': ('django.db.models.fields.CharField', [], {'max_length': '255'})
        }
    }

    complete_apps = ['tsj_gemstone']