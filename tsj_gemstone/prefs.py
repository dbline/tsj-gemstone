from django import forms
from django.utils.translation import ugettext as _

from thinkspace.apps.preferences import AppPreferences, PreferencesForm

class GemstonePreferencesForm(PreferencesForm):
    rapaport_username = forms.CharField(help_text=_(u'Your Rapaport username.'), required=False)
    rapaport_password = forms.CharField(help_text=_(u'Your Rapaport password.'), required=False, widget=forms.PasswordInput(render_value=True))
    rapaport_minimum_carat_weight = forms.DecimalField(label='Minimum Carat Weight',
            initial='.2', help_text="The minimum carat weight to import into the database. Any diamond below this will be ignored. Set this to 0 if you want all carat weights to be accepted.")
    rapaport_maximum_carat_weight = forms.DecimalField(label='Maximum Carat Weight',
            initial='5', help_text="The maximum carat weight to import into the database. Any diamond above this will be ignored. Set this to 0 if you want all carat weights to be accepted.")
    rapaport_minimum_price = forms.DecimalField(label='Minimum Price',
            initial='1500', help_text="The minimum price to import into the database. Any diamond below this will be ignored. Set this to 0 if you want all prices to be accepted.")
    rapaport_maximum_price = forms.DecimalField(label='Maximum Price',
            initial='200000', help_text="The maximum price to import into the database. Any diamond above this will be ignored. Set this to 0 if you want all prices to be accepted.")
    rapaport_must_be_certified = forms.BooleanField(label='Must Be Certified',
            required=False, initial=True, help_text="Every imported diamond must be certified. If the certifier doesn't exist in the database, an entry will be automatically created by the import tool. If the diamond being imported isn't certified, it will be discarded. If the certifier of the diamond being imported exists but is disabled, it will be discarded.")
    rapaport_verify_cert_images = forms.BooleanField(label='Verify Cert. Images',
            required=False, help_text="If a certificate image URL is provided, confirm the URL. This will slow the import process down considerably as each defined certificate image is independently confirmed. If the image doesn't exist, the URL is removed from the diamond being imported but the rest of the diamond will be imported as expected.")

class GemstonePreferences(AppPreferences):
    fieldsets = (
        (_('Rapaport'), {
            'fields': (
                'rapaport_username',
                'rapaport_password',
                'rapaport_minimum_carat_weight',
                'rapaport_maximum_carat_weight',
                'rapaport_minimum_price',
                'rapaport_maximum_price',
                'rapaport_must_be_certified',
                'rapaport_verify_cert_images',
            ),
        }),
    )
    form = GemstonePreferencesForm
    verbose_name = 'Gemstone'

prefs = GemstonePreferences()
