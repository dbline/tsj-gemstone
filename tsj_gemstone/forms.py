from django import forms

from thinkspace.apps.preferences.forms import PreferencesForm
from thinkspace.forms.fields import GroupedModelChoiceField

from tsj_gemstone import models as gemstone_models

class GemstoneListArgumentForm(PreferencesForm):
    sources = forms.MultipleChoiceField(choices=[], required=False)

    def __init__(self, *args, **kwargs):
        super(GemstoneListArgumentForm, self).__init__(*args, **kwargs)

        self.fields['sources'].choices = [
            (row[0], row[0]) for row in gemstone_models.Diamond.objects.order_by().values_list('source').distinct()
        ]
