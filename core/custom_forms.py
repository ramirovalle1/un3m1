import random

from django import forms
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db import models
from django.forms.widgets import DateTimeBaseInput
from django.utils.safestring import mark_safe
from .funciones_adicionales import customgetattr


class NormalModel(models.Model):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for x in self._meta.fields:
            f = x.name
            if isinstance(self._meta.get_field(f), models.BooleanField):
                is_true = customgetattr(self, f)
                t = 'fa-check-circle text-success' if is_true else 'fa-times-circle text-secondary'
                setattr(self, '%s_boolhtml' % f, mark_safe('<i class="fas ' + t + '"></i>'))
                t = "HABILITADO" if is_true else "DESHABILITADO"
                setattr(self, '%s_texthtml' % f, t)
                t = "Sí" if is_true else "No"
                setattr(self, '%s_yesorno' % f, t)
            if isinstance(self._meta.get_field(f), models.DecimalField):
                t = customgetattr(self, f)
                if t != None:
                    setattr(self, '%s_unlocalize' % f, str(t).replace(',', '.'))
                    setattr(self, '%s_money' % f, "{}{}".format(SIMBOLO_MONEDA, str(t).replace(',', '.')))
                    t = int(float(customgetattr(self, f)))
                    setattr(self, '%s_integer' % f, t)

    class Meta:
        abstract = True


class FormError(Exception):
    def __init__(self, form):
        super().__init__("Error en el formulario")
        if isinstance(form, list) or isinstance(form, tuple):
            self.errors = []
            for x in form:
                for k, v in x.errors.items():
                    self.errors.append({k: v[0]})
        else:
            self.errors = [{k: v[0]} for k, v in form.errors.items()]
        self.dict_error = {
            'error': True,
            "form": self.errors,
            "message": "Los datos enviados son inconsistentes"
        }


class CustomDateInput(DateTimeBaseInput):
    def format_value(self, value):
        return str(value or '')


class FormModeloBase(forms.Form):

    class Media:
        css = {
            'all': ('/static/switchery/switchery.min.css',)
        }
        js = (
            '/static/switchery/switchery.min.js',
            f'/static/switchery/renderSwicheryControl.js?v={random.randint(0, 10)}',
        )

    def __init__(self, *args, **kwargs):
        self.ver = kwargs.pop('ver') if 'ver' in kwargs else False
        # self.editando = 'instance' in kwargs
        self.instancia = kwargs.pop('instancia', None)
        no_requeridos = kwargs.pop('no_requeridos') if 'no_requeridos' in kwargs else []
        requeridos = kwargs.pop('requeridos') if 'requeridos' in kwargs else []
        # if self.editando:
        #     self.instancia = kwargs['instance']
        super(FormModeloBase, self).__init__(*args, **kwargs)
        for nr in no_requeridos:
            self.fields[nr].required = False
        for r in requeridos:
            self.fields[r].required = True
        for k, v in self.fields.items():
            field = self.fields[k]
            if isinstance(field, forms.FileField) and self.instancia:
                self.fields[k].required = False
            if isinstance(field, forms.TimeField):
                attrs_ = self.fields[k].widget.attrs
                self.fields[k].widget = CustomDateInput(attrs={'type': 'time'})
                self.fields[k].widget.attrs = attrs_
            if isinstance(field, forms.DateField):
                attrs_ = self.fields[k].widget.attrs
                self.fields[k].widget = CustomDateInput(attrs={'type': 'date'})
                self.fields[k].widget.attrs = attrs_
                # Personalizar el valor inicial si está presente en los datos iniciales del formulario
                if k in self.initial:
                    if self.initial.get(k):
                        fecha_str = self.initial[k].strftime('%Y-%m-%d')
                        self.initial[k] = fecha_str
                # self.fields[k].input_formats = ['%d/%m/%Y']
            elif isinstance(field, forms.BooleanField):
                if 'data-switchery' in self.fields[k].widget.attrs and self.fields[k].widget.attrs['data-switchery']:
                    if 'class' in self.fields[k].widget.attrs :
                        self.fields[k].widget.attrs['class'] += " js-switch"
                    else:
                        self.fields[k].widget.attrs['class'] = "js-switch"
            else:
                if 'class' in self.fields[k].widget.attrs:
                    self.fields[k].widget.attrs['class'] += " form-control"
                else:
                    self.fields[k].widget.attrs['class'] = "form-control"
            if not 'col' in self.fields[k].widget.attrs:
                self.fields[k].widget.attrs['col'] = "12"
            if self.fields[k].required and self.fields[k].label:
                self.fields[k].label = mark_safe(self.fields[k].label + '<span style="color:red;margin-left:2px;"><strong>*</strong></span>')
            # elif not self.fields[k].required and self.fields[k].label:
            #     self.fields[k].label = mark_safe(self.fields[k].label + '<span style="margin-left:2px;" class="text-muted fw-normal fs-6"">(Opcional)</span>')
            self.fields[k].widget.attrs['data-nameinput'] = k
            if self.ver:
                self.fields[k].widget.attrs['readonly'] = "readonly"
