from django import forms
from django.utils.translation import ugettext as _
from django.contrib.auth.models import Group

from thinkspace.apps.preferences.forms import PreferencesForm
from thinkspace.apps.preferences.options import AppPreferences

class GemstonePreferencesForm(PreferencesForm):
    MARKUP_CHOICES = (
        ('price', 'Price'),
        ('carat_weight', 'Carat Weight'),
    )
    PRICE_CHOICES = (
        ('none', 'Off'), #TODO: Eventually change stored value to 'off' to standardize with tsj_catalog
        ('admin', 'Admin'),
        ('auth', 'Authenticated'),
        ('anon', 'Everyone'), #TODO: Eventually change stored value to 'all' to standardize with tsj_catalog
        ('group', 'Group'),
    )
    RAPNET_VERSIONS = (
        ('', 'Select a subscription type'),
        ('rapnet10', 'Download Listing Service'),
        ('rapnetii', 'Instant Inventory'),
    )

    show_prices = forms.ChoiceField(label='Show Prices to', choices=PRICE_CHOICES, help_text=_(u'Control how gemstone prices are shown on your website.'))
    group = forms.ModelChoiceField(queryset=Group.objects.all(), required=False, help_text='Limit prices to a specific group')
    add_to_cart = forms.BooleanField(required=False, label='Add to Cart')

    markup = forms.ChoiceField(choices=MARKUP_CHOICES, required=True, help_text='Control how diamonds are marked up.')

    rapaport_username = forms.CharField(label='Username', help_text=_(u'Your Rapaport username.'), required=False)
    rapaport_password = forms.CharField(label='Password', help_text=_(u'Your Rapaport password.'), required=False, widget=forms.PasswordInput(render_value=True, attrs={'autocomplete':'new-password'}))
    rapaport_url = forms.URLField(label='DLS URL', required=False, help_text=_(u'A Download Listing Service URL which overrides all of the following criteria if specified'))
    rapaport_version = forms.ChoiceField(label='Subscription Type', choices=RAPNET_VERSIONS, required=False)

    rapaport_minimum_carat_weight = forms.DecimalField(label='Min Carat Weight', widget=forms.TextInput,
            initial='0', help_text="The minimum carat weight to import into the database. Any diamond below this will be ignored. Set this to 0 if you want all carat weights to be accepted.")
    rapaport_maximum_carat_weight = forms.DecimalField(label='Max Carat Weight', widget=forms.TextInput,
            initial='0', help_text="The maximum carat weight to import into the database. Any diamond above this will be ignored. Set this to 0 if you want all carat weights to be accepted.")

    rapaport_minimum_price = forms.DecimalField(label='Min Price', widget=forms.TextInput,
            initial='0', help_text="The minimum price to import into the database. Any diamond below this will be ignored. Set this to 0 if you want all prices to be accepted.")
    rapaport_maximum_price = forms.DecimalField(label='Max Price', widget=forms.TextInput,
            initial='0', help_text="The maximum price to import into the database. Any diamond above this will be ignored. Set this to 0 if you want all prices to be accepted.")

    rapaport_must_be_certified = forms.BooleanField(label='Must Be Certified',
            required=False, initial=True, help_text="Every imported diamond must be certified. If the certifier doesn't exist in the database, an entry will be automatically created by the import tool. If the diamond being imported isn't certified, it will be discarded. If the certifier of the diamond being imported exists but is disabled, it will be discarded.")
    rapaport_verify_cert_images = forms.BooleanField(label='Verify Cert. Images',
            required=False, help_text="If a certificate image URL is provided, confirm the URL. This will slow the import process down considerably as each defined certificate image is independently confirmed. If the image doesn't exist, the URL is removed from the diamond being imported but the rest of the diamond will be imported as expected.")

    include_mined = forms.BooleanField(label='Include Mined Diamonds', required=False, initial=True)
    include_lab_grown = forms.BooleanField(label='Include Lab-Grown Diamonds', required=False, initial=False)

    backend = forms.CharField(label='Backend', help_text="Used for local backends, can separate multiple with commas or spaces", required=False)
    idex_access_key = forms.CharField(label='IDEX Access Key', help_text="Your IDEX access key", required=False)
    polygon_id = forms.CharField(label='Polygon ID', help_text="Your Polygon ID", required=False)
    asc = forms.CharField(label='ASC Account', help_text='FTP account for ASC', required=False)

    vdb_api_key = forms.CharField(label='VDB API Key', help_text="Your VDB API key", required=False)
    vdb_access_token = forms.CharField(label='VDB Access Token', help_text="Your VDB access token", required=False)

    amipi = forms.BooleanField(required=False, label='Amipi')
    brilliantediamond = forms.BooleanField(required=False, label='Brilliante Diamond')
    gndiamond = forms.BooleanField(required=False, label='GN Diamond')
    hasenfeld = forms.BooleanField(required=False, label='Hasenfeld-Stein')
    leibish = forms.BooleanField(required=False, label='Leibish & Co.')
    mdl = forms.BooleanField(required=False, label='MDL (Canadian Dollar)')
    mgeller = forms.BooleanField(required=False, label='M. Geller Diamonds')
    mid = forms.BooleanField(required=False, label='MID House of Diamonds')
    ofermizrahi = forms.BooleanField(required=False, label='Ofer Mizrahi Diamonds')
    premiergem = forms.BooleanField(required=False, label='Premier Gem')
    puregrowndiamonds = forms.BooleanField(required=False, label='Pure Grown Diamonds')
    rdi = forms.BooleanField(required=False, label='RDI Diamonds')
    rditrading = forms.BooleanField(required=False, label='RDI Trading')
    rditrading_advanced = forms.BooleanField(required=False, label='RDI Trading (Advanced)')
    sahar_atid = forms.BooleanField(required=False, label='Sahar Atid')
    stuller = forms.BooleanField(required=False)
    vantyghem = forms.BooleanField(required=False, label='Vantyghem (Canadian Dollar)')

    sarine_template = forms.CharField(label='Sarine Template', help_text='ID for overriding default Sarine Template', required=False)

    def clean_group(self):
        group = self.cleaned_data.get('group')
        if isinstance(group, Group):
            return group.pk
        return group

class GemstonePreferences(AppPreferences):
    fieldsets = (
        (_('General'), {
            'fields': (
                'show_prices',
                'group',
                'add_to_cart',
                'markup',
                'rapaport_minimum_carat_weight',
                'rapaport_maximum_carat_weight',
                'rapaport_minimum_price',
                'rapaport_maximum_price',
                'rapaport_must_be_certified',
                'rapaport_verify_cert_images',
                'include_mined',
                'include_lab_grown',
                'sarine_template',
            ),
        }),
        (_('Built-in Feeds'), {
            'fields': (
                'amipi', 'brilliantediamond', 'gndiamond', 'hasenfeld', 'leibish',
                'mdl', 'mgeller', 'mid', 'ofermizrahi', 'premiergem', 'puregrowndiamonds',
                'rdi', 'rditrading', 'rditrading_advanced', 'stuller', 'vantyghem',
            ),
        }),
        (_('Rapaport'), {
            'fields': (
                'rapaport_username',
                'rapaport_password',
                'rapaport_version',
                'rapaport_url',
            ),
        }),
        (_('IDEX'), {
            'fields': (
                'idex_access_key',
            ),
        }),
        (_('Polygon'), {
            'fields': (
                'polygon_id',
            ),
        }),
        (_('ASC'), {
            'fields': (
                'asc',
            ),
        }),
        (_('VDB'), {
            'fields': (
                'vdb_api_key',
                'vdb_access_token',
            ),
        }),
        (_('Additional Feeds'), {
            'fields': (
                'backend',
            ),
        }),
    )
    form = GemstonePreferencesForm
    verbose_name = 'Gemstone'

prefs = GemstonePreferences()
