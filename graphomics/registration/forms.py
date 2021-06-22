from django import forms
from django.contrib.auth import get_user_model

User = get_user_model()


class UserForm(forms.ModelForm):
    password = forms.CharField(widget=forms.PasswordInput(attrs={'style': 'width: 100%'}))

    class Meta:
        model = User
        fields = ('username', 'email', 'password')
        widgets = {
            'username': forms.TextInput(attrs={'style': 'width: 100%'}),
            'email': forms.TextInput(attrs={'style': 'width: 100%'})
        }