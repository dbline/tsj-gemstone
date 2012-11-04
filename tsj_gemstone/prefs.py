from django import forms
from django.utils.translation import ugettext as _

from thinkspace.apps.preferences import AppPreferences, PreferencesForm

class GemstonePreferencesForm(PreferencesForm):
    rapaport_username = forms.CharField(help_text=_(u'Your Rapaport username.'), required=False)
    rapaport_password = forms.CharField(help_text=_(u'Your Rapaport password.'), required=False, widget=forms.PasswordInput)
    rapaport_minimum_carat_weight = forms.DecimalField(label='Minimum Carat Weight',
            initial='.2', help_text="The minimum carat weight to import into the database. Any diamond below this will be ignored. Set this to 0 if you want all carat weights to be accepted.")
    rapaport_must_be_certified = forms.BooleanField(label='Must Be Certified',
            required=False, initial=True, help_text="Every imported diamond must be certified. If the certifier doesn't exist in the database, an entry will be automatically created by the import tool. If the diamond being imported isn't certified, it will be discarded.")
    rapaport_verify_cert_images = forms.BooleanField(label='Verify Cert. Images',
            required=False, help_text="If a certificate image URL is provided, confirm the URL. This will slow the import process down considerably as each defined certificate image is independently confirmed. If the image doesn't exist, the URL is removed from the diamond being imported but the rest of the diamond will be imported as expected.")

class GemstonePreferences(AppPreferences):
    fieldsets = (
        (_('Rapaport'), {
            'fields': (
                'rapaport_username',
                'rapaport_password',
                'rapaport_minimum_carat_weight',
                'rapaport_must_be_certified',
                'rapaport_verify_cert_images',
            ),
        }),
    )
    form = GemstonePreferencesForm
    verbose_name = 'Gemstone'

prefs = GemstonePreferences()
