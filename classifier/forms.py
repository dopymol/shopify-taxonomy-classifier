from django import forms
from .models import TaxonomyCategory

class UploadCatalogueForm(forms.Form):
    catalogue = forms.FileField(help_text="Excel (.xlsx) or CSV, up to 25 MB")
    process_now = forms.BooleanField(required=False, initial=False, help_text="Useful for small demonstrations only")

    def clean_catalogue(self):
        f = self.cleaned_data["catalogue"]
        if not f.name.lower().endswith((".xlsx", ".csv")):
            raise forms.ValidationError("Upload an .xlsx or .csv file.")
        if f.size > 25 * 1024 * 1024:
            raise forms.ValidationError("The file must be 25 MB or smaller.")
        return f

class ReviewForm(forms.Form):
    category = forms.ModelChoiceField(queryset=TaxonomyCategory.objects.filter(is_active=True), empty_label=None)
    approved = forms.BooleanField(required=False)
    note = forms.CharField(widget=forms.Textarea(attrs={"rows": 3}), required=False)
