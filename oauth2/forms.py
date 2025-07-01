from __future__ import unicode_literals
from django import forms

from crispy_forms.bootstrap import PrependedText
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Submit, Div, Field

from django.contrib.auth import get_user_model
from django.contrib.auth.forms import UserCreationForm, UserChangeForm
from django.contrib.auth.forms import AuthenticationForm


User = get_user_model()


class LoginForm(AuthenticationForm):
    username = forms.CharField(
        widget=forms.TextInput(),
        help_text='Ingrese su nombre de usuario',
        label=u'Usuario'
    )
    password = forms.CharField(
        widget=forms.PasswordInput(),
        help_text='No comparta su contraseña',
        label=u"Contraseña"
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper(self)
        # self.fields['username'] = 'Please fill up Username'
        # self.fields['password'] = 'Do not share your password'
        self.helper.layout = Layout(
            PrependedText('username', '<i class="fa fa-user"></i>'),
            PrependedText('password', '<i class="fa fa-lock"></i>'),
            Submit('submit', 'Entrar', css_class='btn btn-success')
        )


class SignUpForm(UserCreationForm):
    first_name = forms.CharField(max_length=30, required=False, help_text='Optional.')
    last_name = forms.CharField(max_length=30, required=False, help_text='Optional.')
    email = forms.EmailField(max_length=254, help_text='Required. Inform a valid email address.')

    class Meta:
        model = User
        fields = ('username', 'first_name', 'last_name', 'email', 'password1', 'password2', )


class UpdateUserForm(forms.ModelForm):

    class Meta:
        model = User
        fields = ('username', 'first_name', 'last_name', 'email',)
