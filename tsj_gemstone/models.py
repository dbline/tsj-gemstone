from django.db import models
from django.template import Context, loader

from jsonfield import JSONField
from model_utils.models import TimeStampedModel
import mimetypes

from thinkspace.apps.pages.urlresolvers import reverse
from thinkspace.lib.db.models import View
from ts_company.prefs import prefs as company_prefs
from tsj_gemstone.managers import DictManager, NameDictManager
from tsj_gemstone.utils import moneyfmt

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
    is_local = models.BooleanField(default=False)
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
    desc = models.TextField('Description', blank=True)
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
    desc = models.TextField('Description', blank=True)
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
    desc = models.TextField('Description', blank=True)
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
    desc = models.TextField('Description', blank=True)
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

class FancyColor(models.Model):
    name = models.CharField(max_length=100)
    aliases = models.TextField(blank=True, help_text='One entry per line. Case-insensitive.')
    objects = NameDictManager()

    def __unicode__(self):
        return self.name

    class Meta:
        verbose_name = 'Fancy Color'
        verbose_name_plural = 'Fancy Colors'
        ordering = ['name']

class FancyColorIntensity(models.Model):
    name = models.CharField(max_length=100)
    aliases = models.TextField(blank=True, help_text='One entry per line. Case-insensitive.')
    order = models.PositiveSmallIntegerField(default=9999)
    objects = NameDictManager()

    def __unicode__(self):
        return self.name

    class Meta:
        verbose_name = 'Fancy Color Intensity'
        verbose_name_plural = 'Fancy Color Intensities'
        ordering = ['order', 'name']

class FancyColorOvertone(models.Model):
    name = models.CharField(max_length=100)
    aliases = models.TextField(blank=True, help_text='One entry per line. Case-insensitive.')
    objects = NameDictManager()

    def __unicode__(self):
        return self.name

    class Meta:
        verbose_name = 'Fancy Color Overtone'
        verbose_name_plural = 'Fancy Color Overtones'
        ordering = ['name']

class DiamondMarkup(models.Model):
    minimum_carat_weight = models.DecimalField('Min Carat Weight',
            max_digits=5, decimal_places=2, blank=True, null=True,
            help_text="The minimum carat weight for this markup to be applied.")
    maximum_carat_weight = models.DecimalField('Max Carat Weight',
            max_digits=5, decimal_places=2, blank=True, null=True,
            help_text="The maximum carat weight for this markup to be applied.")
    minimum_price = models.DecimalField('Min Price',
            max_digits=10, decimal_places=2, blank=True, null=True,
            help_text="The minimum price for this markup to be applied.")
    maximum_price = models.DecimalField('Max Price',
            max_digits=10, decimal_places=2, blank=True, null=True,
            help_text="The maximum price for this markup to be applied.")
    percent = models.DecimalField(max_digits=5, decimal_places=2, help_text='Markup percent (35.00 for 35%)')

    def __unicode__(self):
        if self:
            if self.minimum_carat_weight:
                return u'%s - %s: %s' % (self.minimum_carat_weight, self.maximum_carat_weight, self.percent)
            else:
                return u'%s - %s: %s' % (self.minimum_price, self.maximum_price, self.percent)
        else:
            return 'DiamondMarkup'

    class Meta:
        verbose_name = 'Diamond Markup'
        verbose_name_plural = 'Diamond Markups'
        ordering = ['percent']

class DiamondBase(TimeStampedModel):
    active = models.BooleanField(default=True)
    source = models.CharField(max_length=64)
    lot_num = models.CharField('Lot #', max_length=100, blank=True)
    stock_number = models.CharField('Stock #', max_length=100, blank=True)
    owner = models.CharField('Owner', max_length=255, blank=True)
    image = models.CharField('Image URL', max_length=255, blank=True, null=True)
    image_local = models.FileField('Upload Image', upload_to='tsj_gemstone/images/', blank=True, null=True)
    cut = models.ForeignKey(Cut, verbose_name='Cut', related_name='%(class)s_cut_set')
    cut_grade = models.ForeignKey(Grading, verbose_name='Cut Grade', null=True, blank=True, related_name='%(class)s_cut_grade_set')
    color = models.ForeignKey(Color, verbose_name='Color', null=True, blank=True, related_name='%(class)s_color_set')
    clarity = models.ForeignKey(Clarity, verbose_name='Clarity', null=True, blank=True, related_name='%(class)s_clarity_set')
    carat_weight = models.DecimalField('Weight', max_digits=5, decimal_places=2, db_index=True)
    carat_price = models.DecimalField('Price / Ct.', max_digits=10, decimal_places=2)
    price = models.DecimalField('Price', max_digits=10, decimal_places=2)
    certifier = models.ForeignKey(Certifier, verbose_name='Lab', null=True, blank=True, related_name='%(class)s_certifier_set')
    cert_num = models.CharField('Lab Report #', max_length=255, blank=True)
    cert_image = models.CharField('Lab Report URL', max_length=255, blank=True)
    cert_image_local = models.FileField('Upload Cert Image', upload_to='tsj_gemstone/certificates/', blank=True)
    depth_percent = models.DecimalField('Depth %', max_digits=5, decimal_places=2, null=True, blank=True)
    table_percent = models.DecimalField('Table %', max_digits=5, decimal_places=2, null=True, blank=True)
    girdle = models.CharField('Girdle', max_length=50, blank=True)
    culet = models.CharField('Culet', max_length=50, blank=True)
    polish = models.ForeignKey(Grading, verbose_name='Polish', null=True, blank=True, related_name='%(class)s_polish_set')
    symmetry = models.ForeignKey(Grading, verbose_name='Symmetry', null=True, blank=True, related_name='%(class)s_symmetry_set')
    fluorescence = models.ForeignKey(Fluorescence, verbose_name='Fluorescence', null=True, blank=True, related_name='%(class)s_fluorescence_set')
    fluorescence_color = models.ForeignKey(FluorescenceColor, verbose_name='Fluorescence Color', null=True, blank=True, related_name='%(class)s_fluorescence_color_set')
    fancy_color = models.ForeignKey(FancyColor, verbose_name='Fancy Color', null=True, blank=True)
    fancy_color_intensity = models.ForeignKey(FancyColorIntensity, verbose_name='Fancy Color Intensity', null=True, blank=True)
    fancy_color_overtone = models.ForeignKey(FancyColorOvertone, verbose_name='Fancy Color Overtone', null=True, blank=True)
    length = models.DecimalField('Length', max_digits=5, decimal_places=2, null=True, blank=True)
    width = models.DecimalField('Width', max_digits=5, decimal_places=2, null=True, blank=True)
    depth = models.DecimalField('Depth', max_digits=5, decimal_places=2, null=True, blank=True)
    comment = models.TextField('Comment', blank=True)
    city = models.CharField('City', max_length=255, blank=True)
    state = models.CharField('State', max_length=255, blank=True)
    country = models.CharField('Country', max_length=255, blank=True)
    manmade = models.NullBooleanField(default=False, verbose_name='Man-made')
    laser_inscribed = models.NullBooleanField(default=False, verbose_name='Laser Inscribed')

    # TODO: Abstract Rapaport information to a different model
    rap_date = models.DateTimeField('Date Added', blank=True, null=True)

    data = JSONField(default={})

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
        c = Context({'item': self, 'order_item': order_item, 'prefs': company_prefs})
        return t.render(c)

    def get_report_url(self):
        if self.certifier and self.cert_num:
            if self.certifier.abbr == 'GIA':
                url = 'https://www.gia.edu/report-check?reportno=%s' % self.cert_num
            elif self.certifier.abbr == 'AGS':
                url = 'http://www.agslab.com/reportTypes/pdqr.php?StoneID=%s&Weight=%s&D=1' % (self.cert_num, self.carat_weight)
            elif self.certifier.abbr == 'EGL':
                url = 'http://www.eglusa.com/verify-a-report-results/?st_num=%s' % self.cert_num[2:]
            elif self.certifier.abbr == 'IGI':
                url = 'http://igiworldwide.com/verify.php?r=%s' % self.cert_num
            elif self.certifier.abbr == 'HRD':
                url = 'http://ws2.hrdantwerp.com/HRD.CertificateService.WebAPI/certificate?certificateNumber=%s&certificateType=CERT' % self.cert_num
            else:
                url = None
        else:
            url = None
        return url

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
        # 1.9 compat: tsj_gemstone.ImportLogEntry: (models.E021) 'ordering' and 'order_with_respect_to' cannot be used together
        # MATT: We really just want to drop these import models anyway
        #order_with_respect_to = 'import_log'
        ordering = ['-added', 'csv_line']
