from django.db import models
from django.template import Context, loader

from model_utils.models import TimeStampedModel

from thinkspace.apps.pages.urlresolvers import reverse
from thinkspace.lib.db.models import View

from .managers import DictManager
from .utils import moneyfmt
import mimetypes

class Cut(models.Model):
    name = models.CharField(max_length=100)
    abbr = models.CharField('Abbreviation', max_length=5, db_index=True)
    aliases = models.TextField(blank=True, help_text='One entry per line. Case-insensitive.')
    desc = models.TextField('Description', blank=True)
    order = models.PositiveSmallIntegerField(default=9999)
    objects = DictManager()

    def __unicode__(self):
        return self.name

    class Meta:
        verbose_name = 'Cut'
        verbose_name_plural = 'Cuts'
        ordering = ['order', 'name']

# TODO: Abstract base model for cut?  Or just phase out local cuts entirely..
class CutView(View):
    name = models.CharField(max_length=100)
    abbr = models.CharField('Abbreviation', max_length=5, db_index=True)
    aliases = models.TextField(blank=True, help_text='One entry per line. Case-insensitive.')
    desc = models.TextField('Description', blank=True)
    order = models.PositiveSmallIntegerField(default=9999)
    is_local = models.BooleanField()
    objects = DictManager()

    class Meta(View.Meta):
        verbose_name = 'cut'
        verbose_name_plural = 'cuts'
        ordering = ['order', 'name']

    def __unicode__(self):
        return self.name

class Color(models.Model):
    abbr = models.CharField(max_length=5, db_index=True)
    aliases = models.TextField(blank=True, help_text='One entry per line. Case-insensitive.')
    objects = DictManager()

    def __unicode__(self):
        return self.abbr

    class Meta:
        verbose_name = 'Color'
        verbose_name_plural = 'Colors'
        ordering = ['abbr']

class Clarity(models.Model):
    name = models.CharField(max_length=100)
    abbr = models.CharField('Abbreviation', max_length=5, db_index=True)
    aliases = models.TextField(blank=True, help_text='One entry per line. Case-insensitive.')
    desc = models.TextField('Description', blank=True)
    order = models.PositiveSmallIntegerField(default=9999)
    objects = DictManager()

    def __unicode__(self):
        return self.abbr

    class Meta:
        verbose_name = 'Clarity'
        verbose_name_plural = 'Clarity'
        ordering = ['order', 'name']

class Grading(models.Model):
    name = models.CharField(max_length=100)
    abbr = models.CharField('Abbreviation', max_length=10, db_index=True)
    aliases = models.TextField(blank=True, help_text='One entry per line. Case-insensitive.')
    order = models.PositiveSmallIntegerField(default=9999)
    objects = DictManager()

    def __unicode__(self):
        return self.name

    class Meta:
        verbose_name = 'Grading'
        verbose_name_plural = 'Gradings'
        ordering = ['order', 'name']

class Fluorescence(models.Model):
    name = models.CharField(max_length=100)
    abbr = models.CharField('Abbreviation', max_length=5, db_index=True)
    aliases = models.TextField(blank=True, help_text='One entry per line. Case-insensitive.')
    order = models.PositiveSmallIntegerField(default=9999)
    objects = DictManager()

    def __unicode__(self):
        return u'%s (%s)' % (self.name, self.abbr)

    class Meta:
        verbose_name = 'Fluorescence'
        verbose_name_plural = 'Fluorescence'
        ordering = ['order', 'name']

class FluorescenceColor(models.Model):
    name = models.CharField(max_length=100)
    abbr = models.CharField('Abbreviation', max_length=5, db_index=True)
    aliases = models.TextField(blank=True, help_text='One entry per line. Case-insensitive.')
    objects = DictManager()

    def __unicode__(self):
        return u'%s (%s)' % (self.name, self.abbr)

    class Meta:
        verbose_name = 'Fluorescence Color'
        verbose_name_plural = 'Fluorescence Colors'
        ordering = ['name']

class Certifier(models.Model):
    name = models.CharField(max_length=255)
    abbr = models.CharField('Abbreviation', max_length=255, db_index=True)
    aliases = models.TextField(blank=True, help_text='One entry per line. Case-insensitive.')
    url = models.URLField('URL', blank=True)
    desc = models.TextField('Description', blank=True)
    disabled = models.BooleanField(default=False)
    objects = DictManager()

    def __unicode__(self):
        return u'%s' % (self.abbr)

    class Meta:
        verbose_name = 'Certifier'
        verbose_name_plural = 'Certifiers'
        ordering = ['abbr']

class DiamondMarkup(models.Model):
    start_price = models.DecimalField('Start Price', max_digits=10, decimal_places=2)
    end_price = models.DecimalField('End Price', max_digits=10, decimal_places=2)
    percent = models.DecimalField(max_digits=5, decimal_places=2, help_text='Markup percent (35.00 for 35%)')

    def __unicode__(self):
        return u'%d - %d: %d' % (self.start_price, self.end_price, self.percent)

    class Meta:
        verbose_name = 'Diamond Markup'
        verbose_name_plural = 'Diamond Markups'
        ordering = ['percent']

class DiamondBase(TimeStampedModel):
    SOURCE_CHOICES = (
        ('local', 'Local'),
        ('rapaport', 'Rapaport'),
        ('rapnet10', 'Rapaport 1.0'),
    )

    active = models.BooleanField(default=True)
    source = models.CharField(max_length=64, choices=SOURCE_CHOICES)
    lot_num = models.CharField('Lot #', max_length=100, blank=True)
    stock_number = models.CharField('Stock #', max_length=100, blank=True)
    owner = models.CharField('Owner', max_length=255, blank=True)
    cut = models.ForeignKey(Cut, verbose_name='Cut', related_name='%(class)s_cut_set')
    cut_grade = models.ForeignKey(Grading, verbose_name='Cut Grade', null=True, blank=True, related_name='%(class)s_cut_grade_set')
    color = models.ForeignKey(Color, verbose_name='Color', null=True, blank=True, related_name='%(class)s_color_set')
    clarity = models.ForeignKey(Clarity, verbose_name='Clarity', null=True, blank=True, related_name='%(class)s_clarity_set')
    carat_weight = models.DecimalField('Weight', max_digits=5, decimal_places=2, db_index=True)
    carat_price = models.DecimalField('Price / Ct.', max_digits=10, decimal_places=2)
    price = models.DecimalField('Price', max_digits=10, decimal_places=2)
    certifier = models.ForeignKey(Certifier, verbose_name='Certifier', null=True, blank=True, related_name='%(class)s_certifier_set')
    cert_num = models.CharField('Cert Report #', max_length=255, blank=True)
    cert_image = models.CharField('Cert Image', max_length=255, blank=True)
    cert_image_local = models.FileField('Cert Image', upload_to='tsj_gemstone/certificates/', blank=True)
    depth_percent = models.DecimalField('Depth %', max_digits=5, decimal_places=2, null=True, blank=True)
    table_percent = models.DecimalField('Table %', max_digits=5, decimal_places=2, null=True, blank=True)
    girdle = models.CharField('Girdle', max_length=50, blank=True)
    culet = models.CharField('Culet', max_length=50, blank=True)
    polish = models.ForeignKey(Grading, verbose_name='Polish', null=True, blank=True, related_name='%(class)s_polish_set')
    symmetry = models.ForeignKey(Grading, verbose_name='Symmetry', null=True, blank=True, related_name='%(class)s_symmetry_set')
    fluorescence = models.ForeignKey(Fluorescence, verbose_name='Fluorescence', null=True, blank=True, related_name='%(class)s_fluorescence_set')
    fluorescence_color = models.ForeignKey(FluorescenceColor, verbose_name='Fluorescence Color', null=True, blank=True, related_name='%(class)s_fluorescence_color_set')
    length = models.DecimalField('Length', max_digits=5, decimal_places=2, null=True, blank=True)
    width = models.DecimalField('Width', max_digits=5, decimal_places=2, null=True, blank=True)
    depth = models.DecimalField('Depth', max_digits=5, decimal_places=2, null=True, blank=True)
    comment = models.TextField('Comment', blank=True)
    city = models.CharField('City', max_length=255, blank=True)
    state = models.CharField('State', max_length=255, blank=True)
    country = models.CharField('Country', max_length=255, blank=True)
    manmade = models.NullBooleanField(default=False, verbose_name='Man-made')

    # TODO: Abstract Rapaport information to a different model
    rap_date = models.DateTimeField('Date added to Rapaport', blank=True, null=True)

    def formatted_price(self):
        return moneyfmt(self.price, dp='', places=0)
    formatted_price.short_description = 'Price'
    formatted_price.admin_order_field = 'price'

    def formatted_carat_price(self, dp='', places=0):
        return moneyfmt(self.carat_price, dp='', places=0)
    formatted_carat_price.short_description = 'Price / Ct.'
    formatted_carat_price.admin_order_field = 'carat_price'

    def get_absolute_url(self):
        return reverse('gemstone-detail', kwargs={'pk': self.pk})

    def get_price(self):
        return self.price

    def handle_order_item(self, orderitem):
        orderitem.name = '%s Diamond' % self.cut
        orderitem.sku = self.stock_number

    def display_order_item(self, order_item):
        t = loader.get_template('tsj_gemstone/includes/order_item.html')
        c = Context({'item': self, 'order_item': order_item})
        return t.render(c)

    def display_email_item(self, order_item=None):
        t = loader.get_template('tsj_gemstone/includes/email_item.txt')
        c = Context({'item': self, 'order_item': order_item})
        return t.render(c)

    def get_cert_image_type(self):
        if self.cert_image: 
            type, encoding = mimetypes.guess_type(self.cert_image)
            if type in ('image/jpeg', 'image/png', 'image/gif'):
                return 'image'
            else:
                return 'other'
        else:
            return None

    def __unicode__(self):
        return u'%s' % (self.lot_num)

    class Meta:
        abstract = True
        ordering = ['carat_weight']

class Diamond(DiamondBase):
    class Meta(DiamondBase.Meta):
        verbose_name = 'Diamond'
        verbose_name_plural = 'Diamonds'
        permissions = (("can_import_diamonds", "Can Import Diamonds"),)

# TODO: Generalize import logging into inventory_common or Django logging
class ImportLog(models.Model):
    TYPE_CHOICES = (
        ('R', 'Ring'),
        ('D', 'Diamond'),
    )

    imported = models.DateTimeField('Imported', auto_now_add=True)
    type = models.CharField('Type', max_length=1, default='R', choices=TYPE_CHOICES)
    successes = models.PositiveIntegerField('Successes', default=0, help_text="The total number of items that were successfully imported.")
    failures = models.PositiveIntegerField('Failures', default=0, help_text="The total number of items that failed to import.")

    def __unicode__(self):
        return u"%s Import on %s" % (self.get_type_display(), self.imported.strftime('%B %d, %Y, %I:%M %p'))

    class Meta:
        verbose_name = 'Import Log'
        verbose_name_plural = 'Import Logs'
        ordering = ['-imported']

class ImportLogEntry(models.Model):
    import_log = models.ForeignKey(ImportLog)
    added = models.DateTimeField('Added', auto_now_add=True)
    csv_line = models.PositiveIntegerField('CSV Line', default=0, help_text="The line that was being imported from the CSV file.")
    problem = models.CharField('Problem', max_length=255, help_text="The reason the line wasn't imported.")
    details = models.TextField('Details', help_text="Some details about the failed import attempt to help with debugging.")

    def __unicode__(self):
        return u"Line %s: %s" % (self.csv_line, self.problem)

    class Meta:
        verbose_name = 'Import Log Entry'
        verbose_name_plural = 'Import Log Entries'
        order_with_respect_to = 'import_log'
        ordering = ['-added', 'csv_line']
