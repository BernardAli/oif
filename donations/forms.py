from decimal import Decimal
from django import forms
from .models import Donation


class DonationForm(forms.ModelForm):
    donor_name = forms.CharField(
        max_length=160,
        widget=forms.TextInput(attrs={"class": "form-input"}),
    )
    donor_email = forms.EmailField(
        widget=forms.EmailInput(attrs={"class": "form-input"}),
    )
    amount = forms.DecimalField(
        min_value=Decimal("1.00"), max_digits=12, decimal_places=2,
        widget=forms.NumberInput(attrs={"class": "form-input",
                                        "placeholder": "0.00", "step": "0.01"}))

    class Meta:
        model = Donation
        fields = (
            "donor_name", "donor_email", "amount", "channel", "campaign",
            "note", "is_recurring",
        )
        widgets = {
            "channel": forms.Select(attrs={"class": "form-input"}),
            "campaign": forms.TextInput(attrs={"class": "form-input"}),
            "note": forms.Textarea(attrs={"class": "form-input", "rows": 2,
                                          "placeholder": "Optional message (e.g. "
                                          "'In honour of…')"}),
        }

    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        if user and user.is_authenticated and not self.is_bound:
            self.fields["donor_name"].initial = user.get_full_name() or user.username
            self.fields["donor_email"].initial = user.email
