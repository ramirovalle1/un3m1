# -*- coding: utf-8 -*-
import os

from django import forms
from django.forms import ModelForm
from django.forms.utils import ErrorList
from django.utils.safestring import mark_safe


class CheckboxSelectMultipleCustom(forms.CheckboxSelectMultiple):
    def render(self, *args, **kwargs):
        output = super(CheckboxSelectMultipleCustom, self).render(*args, **kwargs)
        return mark_safe(output.replace(u'<ul>', u'<div class="custom-multiselect" style="width: 600px;overflow: scroll"><ul>').replace(u'</ul>', u'</ul></div>').replace(u'<li>', u'').replace(u'</li>', u'').replace(u'<label', u'<div style="width: 900px"><li').replace(u'</label>', u'</li></div>'))


class ExtFileField(forms.FileField):
    """
    * max_upload_size - a number indicating the maximum file size allowed for upload.
            500Kb - 524288
            1MB - 1048576
            2.5MB - 2621440
            5MB - 5242880
            10MB - 10485760
            20MB - 20971520
            50MB - 5242880
            100MB 104857600
            250MB - 214958080
            500MB - 429916160
    t = ExtFileField(ext_whitelist=(".pdf", ".txt"), max_upload_size=)
    """

    def __init__(self, *args, **kwargs):
        ext_whitelist = kwargs.pop("ext_whitelist")
        self.ext_whitelist = [i.lower() for i in ext_whitelist]
        self.max_upload_size = kwargs.pop("max_upload_size")
        super(ExtFileField, self).__init__(*args, **kwargs)

    def clean(self, *args, **kwargs):
        upload = super(ExtFileField, self).clean(*args, **kwargs)
        if upload:
            size = upload.size
            filename = upload.name
            ext = os.path.splitext(filename)[1]
            ext = ext.lower()
            if size == 0 or ext not in self.ext_whitelist or size > self.max_upload_size:
                raise forms.ValidationError("Tipo de fichero o tamanno no permitido!")


class FixedForm(ModelForm):
    date_fields = []

    def __init__(self, *args, **kwargs):
        super(ModelForm, self).__init__(*args, **kwargs)
        for f in self.date_fields:
            self.fields[f].widget.format = '%d-%m-%Y'
            self.fields[f].input_formats = ['%d-%m-%Y']


class MY_Form(forms.Form):
    _errors_aux = {}

    def __init__(self, data=None, files=None, auto_id='id_%s', prefix=None,
                 initial=None, error_class=ErrorList, label_suffix=None,
                 empty_permitted=False, field_order=None, use_required_attribute=None, renderer=None):
        super(MY_Form, self).__init__(data=data, files=files, auto_id=auto_id, prefix=prefix, initial=initial,
                                      error_class=error_class, label_suffix=label_suffix,
                                      empty_permitted=empty_permitted, field_order=field_order,
                                      use_required_attribute=use_required_attribute, renderer=renderer)

    def addError(self, field, message):
        self._errors_aux[field] = message

    def addErrors(self, errors):
        self._errors_aux = errors

    def getError(self, field):
        return self._errors_aux[field]

    def getErrors(self):
        return self._errors_aux

    def clearErrors(self):
        self._errors_aux = {}

    def isErrorEmpty(self):
        return True if self._errors_aux else False

    def toArray(self):
        fields = []
        for field in self.fields:
            # print(self.fields[field])
            # print(type(self.fields[field]))
            if isinstance(self.fields[field], forms.BooleanField):
                value = False
                if field in self.data:
                    if self.data[field].lower() in ('false', '0'):
                        value = False
                    else:
                        value = bool(self.data[field])
                fields.append({'field': field, 'value': value})
            else:
                fields.append({'field': field, 'value': self.data[field] if field in self.data and self.data[field] else ''})

        return {'errors': self._errors_aux, "fields": fields}

    def toArrayLogin(self):
        fields = {'username': self.data['username'] if 'username' in self.data and self.data['username'] else '',
                  'password': '',
                  }
        # toArray.update(arr)
        return {'errors': self._errors_aux, "fields": fields}

    def disable_field(self, name_field):
        self.fields[name_field].widget.attrs['readonly'] = True
        self.fields[name_field].widget.attrs['disabled'] = True

    def enable_field(self, name_field):
        self.fields[name_field].widget.attrs['readonly'] = False
        self.fields[name_field].widget.attrs['disabled'] = False

    def reading_mode_field(self, name_field, value):
        self.fields[name_field].widget.attrs['readonly'] = value

    def lock_mode_field(self, name_field, value):
        self.fields[name_field].widget.attrs['disabled'] = value

    def view(self):
        for field in self.fields:
            self.disable_field(field)
