from django import forms
from django.utils.translation import ugettext as _

from thinkspace.apps.preferences import AppPreferences, PreferencesForm

class GemstonePreferencesForm(PreferencesForm):
    RAPAPORT_VERSION_CHOICES = (
        # TODO: We could rename backends.rapaport to backends.rapnet08, but
        #       it's not a big deal since we'll just drop the 0.8 version.
        ('rapaport', '0.8'),
        ('rapnet10', '1.0'),
    )

    rapaport_username = forms.CharField(help_text=_(u'Your Rapaport username.'), required=False)
    rapaport_password = forms.CharField(help_text=_(u'Your Rapaport password.'), required=False, widget=forms.PasswordInput(render_value=True))
    rapaport_url = forms.URLField(required=False, help_text=_(u'A Download Listing Service URL which overrides all of the following criteria if specified'))
    rapaport_version = forms.ChoiceField(required=False, choices=RAPAPORT_VERSION_CHOICES, help_text=_(u'The version of the Rapnet feed.'), initial='rapaport')
    rapaport_minimum_carat_weight = forms.DecimalField(label='Min Carat Weight',
            initial='.2', help_text="The minimum carat weight to import into the database. Any diamond below this will be ignored. Set this to 0 if you want all carat weights to be accepted.")
    rapaport_maximum_carat_weight = forms.DecimalField(label='Max Carat Weight',
            initial='5', help_text="The maximum carat weight to import into the database. Any diamond above this will be ignored. Set this to 0 if you want all carat weights to be accepted.")
    rapaport_minimum_price = forms.DecimalField(label='Min Price',
            initial='1500', help_text="The minimum price to import into the database. Any diamond below this will be ignored. Set this to 0 if you want all prices to be accepted.")
    rapaport_maximum_price = forms.DecimalField(label='Max Price',
            initial='200000', help_text="The maximum price to import into the database. Any diamond above this will be ignored. Set this to 0 if you want all prices to be accepted.")
    rapaport_must_be_certified = forms.BooleanField(label='Must Be Certified',
            required=False, initial=True, help_text="Every imported diamond must be certified. If the certifier doesn't exist in the database, an entry will be automatically created by the import tool. If the diamond being imported isn't certified, it will be discarded. If the certifier of the diamond being imported exists but is disabled, it will be discarded.")
    rapaport_verify_cert_images = forms.BooleanField(label='Verify Cert. Images',
            required=False, help_text="If a certificate image URL is provided, confirm the URL. This will slow the import process down considerably as each defined certificate image is independently confirmed. If the image doesn't exist, the URL is removed from the diamond being imported but the rest of the diamond will be imported as expected.")
    
    PRICE_CHOICES = (
        ('anon', 'All Users'),
        ('auth', 'Authenticated Users'),
        ('none', 'No One'),
    )

    show_prices = forms.ChoiceField(label='Show Prices to', choices=PRICE_CHOICES, help_text=_(u'Control how prices are shown.'))

class GemstonePreferences(AppPreferences):
    fieldsets = (
        (_('General'), {
            'fields': (
                'show_prices',
                'rapaport_minimum_carat_weight',
                'rapaport_maximum_carat_weight',
                'rapaport_minimum_price',
                'rapaport_maximum_price',
                'rapaport_must_be_certified',
                'rapaport_verify_cert_images',
            ),
        }),
        (_('Rapaport'), {
            'fields': (
                'rapaport_username',
                'rapaport_password',
                'rapaport_url',
                'rapaport_version',
            ),
        }),
    )
    form = GemstonePreferencesForm
    verbose_name = 'Gemstone'

prefs = GemstonePreferences()
