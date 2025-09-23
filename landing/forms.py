from django import forms


class LeadForm(forms.Form):
  email = forms.EmailField(label='Tu email', widget=forms.EmailInput(
    attrs={'placeholder':'tu@email.com','class':'input-email'}
  ))


