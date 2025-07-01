import json
from datetime import datetime

from django import forms
from django.contrib.auth.models import User
from django.contrib.auth.hashers import check_password
from django.db.models import Q
from django.forms import DateTimeInput

from bd.models import APP_VINCULACION, FLAG_FAILED, FLAG_UNKNOWN
from core.custom_forms import FormModeloBase
from sga.funciones import validarcedula, loglogin
from sga.models import TIPOS_IDENTIFICACION, Sexo, Persona, CUENTAS_CORREOS, miinstitucion
from sga.tasks import send_html_mail
from utils.filtros_genericos import consultarPersona
from utils.validators import v_sololetrasform, v_cedulaform, v_solonumerosform


class LoginForm(FormModeloBase):
    username = forms.CharField(label='Usuario', widget=forms.TextInput(attrs={'icon': 'fa fa-user'}))
    password = forms.CharField(label='Contraseña', max_length=70, widget=forms.PasswordInput(attrs={'icon': 'fa fa-lock', 'input_group_pass': True}))

    def __init__(self, *args, **kwargs):
        super(LoginForm, self).__init__(*args, **kwargs)
        for field in self.fields:
            self.fields[field].error_messages = {'required': f'Este campo es requerido'}

    def clean(self):
        cleaned_data = super(LoginForm, self).clean()

        # Acceder a los datos limpios y validados
        cleaned_data['username'] = username = cleaned_data.get('username').lower().strip()
        password = cleaned_data.get('password')

        # Acceder a los datos crudos
        data = self.data
        context = json.loads(data['lista_items1'])[0]
        cleaned_data['tiposistema'] = tipo_app = data['tiposistema']
        cleaned_data['nombresistema'] = nombreapp = data['nombresistema']
        cleaned_data['browser'] = browser = context['navegador']
        cleaned_data['ops'] = ops = context['os']
        cleaned_data['cookies'] = cookies = context['cookies']
        cleaned_data['screensize'] = screensize = context['screensize']
        cleaned_data['url_offline'] = url_offline = context['url_offline'] if 'url_offline' in context else ''
        cleaned_data['capippriva'] = capippriva = data['capipprivada'] if 'capipprivada' in data else ''
        cleaned_data['client_address'] = client_address = data['client_address'] if 'client_address' in data else ''

        # Validaciones de acceso
        if not User.objects.filter(username=username).exists():
            self.add_error('username', 'No existe usuario con los datos ingresado.')
        else:
            usuario = User.objects.get(username=username)
            if not usuario.is_active:
                self.add_error('username', 'Usuario inactivo.')
                loglogin(action_flag=FLAG_FAILED, action_app=APP_VINCULACION, ip_private=capippriva, ip_public=client_address,
                         browser=browser, ops=ops, cookies=cookies, screen_size=screensize, user=usuario, change_message=u"Usuario no activo")
            else:
                persona = Persona.objects.filter(usuario=usuario).first()
                if not persona:
                    self.add_error('username', 'No existe usuario con los datos ingresado.')
                    loglogin(action_flag=FLAG_UNKNOWN, action_app=APP_VINCULACION, ip_private=capippriva,
                             ip_public=client_address, browser=browser, ops=ops, cookies=cookies,
                             screen_size=screensize, change_message=u"USUARIO: %s - CLAVE: %s" % (username, password))

                if not check_password(password, usuario.password):
                    self.add_error('password', 'Contraseña incorrecta.')
                    loglogin(action_flag=FLAG_FAILED, action_app=APP_VINCULACION, ip_private=capippriva,
                             ip_public=client_address, browser=browser, ops=ops, cookies=cookies,
                             screen_size=screensize, user=usuario, change_message=u"Clave Incorrecta")
                    send_html_mail(f"Login fallido {nombreapp}", "emails/loginfallido.html",
                                   {'sistema': u'Login fallido, contraseña incorrecta.',
                                    'fecha': datetime.now().date(), 'hora': datetime.now().time(), 'bs': browser,
                                    'ip': client_address, 'ipvalida': capippriva, 'os': ops,
                                    'cookies': cookies, 'screensize': screensize,
                                    't': miinstitucion(), 'tit': f'{nombreapp}'},
                                   persona.lista_emails_envio(), [], cuenta=CUENTAS_CORREOS[4][1])

                if persona and not persona.tiene_perfil():
                    self.add_error('username', 'No existen perfiles activos.')
                    loglogin(action_flag=FLAG_FAILED, action_app=APP_VINCULACION, ip_private=capippriva,
                             ip_public=client_address, browser=browser, ops=ops, cookies=cookies,
                             screen_size=screensize, user=usuario, change_message=u"Sin perfiles activos")
                    send_html_mail(f"Login fallido {nombreapp}", "emails/loginfallido.html",
                                   {'sistema': u'Login fallido, no existen perfiles activos.',
                                    'fecha': datetime.now().date(), 'hora': datetime.now().time(), 'bs': browser,
                                    'ip': client_address, 'ipvalida': capippriva, 'os': ops,
                                    'cookies': cookies, 'screensize': screensize,
                                    't': miinstitucion(), 'tit': f'{nombreapp}'},
                                   persona.lista_emails_envio(), [], cuenta=CUENTAS_CORREOS[4][1])

        return self.cleaned_data


class SignupForm(FormModeloBase):
    tipoidentificacion = forms.ChoiceField(label=u"Tipo de documento", required=True,
                                           choices=[TIPOS_IDENTIFICACION[0], TIPOS_IDENTIFICACION[2]],
                                           widget=forms.Select(attrs={'col': '6', 'class': 'select2', 'icon': 'fa fa-address-card'}))
    identificacion = forms.CharField(label=u"Identificación", max_length=10, required=True,
                                     widget=forms.TextInput(attrs={'col': '6', 'placeholder': 'Ingresa tu numero de identificación', 'class': 'soloNumeros', 'icon': 'fas fa-id-card'}))
    nombres = forms.CharField(label=u'Nombres', max_length=100, required=True,
                              widget=forms.TextInput(attrs={'col': '12', 'placeholder': 'Ingra tus nombres completos', 'class': 'soloLetrasET', 'icon': 'fas fa-signature'}))
    apellido1 = forms.CharField(label=u"Primer apellido", max_length=50, required=True,
                                widget=forms.TextInput(attrs={'col': '6', 'placeholder': 'Ingresa tu primer apellido', 'class': 'soloLetrasET', 'icon': 'fas fa-signature'}))
    apellido2 = forms.CharField(label=u"Segundo apellido", max_length=50, required=True,
                                widget=forms.TextInput(attrs={'col': '6', 'placeholder': 'Ingresa tu segundo apellido', 'class': 'soloLetrasET', 'icon': 'fas fa-signature'}))
    sexo = forms.ModelChoiceField(label=u"Sexo", queryset=Sexo.objects.filter(status=True), required=True,
                                  widget=forms.Select(attrs={'col': '6', 'class': 'select2', 'icon': 'fas fa-venus-mars'}))
    nacimiento = forms.DateField(label=u"Fecha de nacimiento", initial=None, required=True,
                                 widget=DateTimeInput(format='%d-%m-%Y', attrs={'col': '6', 'icon': 'fas fa-calendar-days'}))
    telefono = forms.CharField(label=u'Celular', max_length=15, required=False,
                               widget=forms.TextInput(attrs={'col': '6', 'placeholder': 'Digite su número de celular', 'icon': 'fas fa-mobile-button'}))
    email = forms.CharField(label=u"Correo electrónico", max_length=200, required=True,
                            widget=forms.EmailInput(attrs={'col': '6', 'placeholder': 'Ingresa tu correo electrónico', 'icon': 'fa fa-envelope'}))
    # password = forms.CharField(label="Contraseña", max_length=70, widget=forms.PasswordInput(attrs={'col': '6', 'placeholder': 'Ingresa tu contraseña', 'icon': 'fa fa-lock'}))
    # password_confirmation = forms.CharField(label="Confirmar contraseña", max_length=70, widget=forms.PasswordInput(attrs={'col': '6', 'placeholder': 'Ingresa tu contraseña', 'icon': 'fa fa-lock'}))

    def __init__(self, *args, **kwargs):
        super(SignupForm, self).__init__(*args, **kwargs)
        for field in self.fields:
            self.fields[field].error_messages = {'required': f'Este campo es requerido'}

    def clean(self):
        cleaned_data = super().clean()
        # password = cleaned_data.get('password')
        # password_confirmation = cleaned_data.get('password_confirmation')
        nacimiento = cleaned_data.get('nacimiento')
        cleaned_data['nombres'] = nombres = cleaned_data.get('nombres').upper()
        cleaned_data['apellido1'] = apellido1 = cleaned_data.get('apellido1').upper()
        cleaned_data['apellido2'] = apellido2 = cleaned_data.get('apellido2').upper()
        cleaned_data['email'] = email = cleaned_data.get('email').lower()
        cleaned_data['identificacion'] = identificacion = cleaned_data.get('identificacion').upper()
        tipoidentificacion = int(cleaned_data.get('tipoidentificacion'))
        telefono = cleaned_data.get('telefono')
        persona = consultarPersona(identificacion)
        idpersona = persona.id if persona else 0
        # Validaciones de campos
        v_sololetrasform(self, nombres, 'nombres')
        v_sololetrasform(self, apellido1, 'apellido1')
        v_sololetrasform(self, apellido2, 'apellido2')

        # Comprobar existencia con datos ingresados
        if not self.instancia and Persona.objects.filter(email=email, status=True).exclude(id=idpersona).exists():
            self.add_error('email', 'El email ingresado ya esta en uso.')

        if persona and persona.usuario:
            mensaje = 'La identificación ingresada ya esta en uso.'
            self.add_error('identificacion', mensaje)
        elif tipoidentificacion == 1:
            result = validarcedula(identificacion)
            if result != 'Ok':
                self.add_error('identificacion', result)
            # v_cedulaform(self, identificacion, 'identificacion')
        elif identificacion[:2] != 'VS':
            self.add_error('identificacion', 'Pasaporte incorrecto, recuerde colocar VS al inicio.')

        if telefono:
            v_solonumerosform(self, telefono, 'telefono')

        if (datetime.now().year - nacimiento.year) < 18:
            self.add_error('nacimiento', 'Su año de nacimiento indica que es menor de edad.')

        # if len(password) >= 6:
        #     if password.islower() or password.isupper():
        #         msg = "La contraseña tiene que tener por lo menos 1 letra mayúscula y 1 minúscula"
        #         self.add_error('password', msg)
        #     if password.isdigit() or password.isalpha():
        #         msg = "La contraseña tiene que contener números, letras y caracteres especiales"
        #         self.add_error('password', msg)
        # else:
        #     msg = "La contraseña tiene que tener como minimo 6 dígitos"
        #     self.add_error('password', msg)
        #
        # if password != password_confirmation:
        #     msg = "Contraseña no coincide"
        #     self.add_error('password_confirmation', msg)
        return cleaned_data
