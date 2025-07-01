from core.custom_forms import FormModeloBase
from django import forms
from sga.forms import ExtFileField


class ValidarCetificadoForm(FormModeloBase):
    archivo = ExtFileField(label=u'Archivo', required=False,
                           help_text=u'Tamaño Maximo permitido 10Mb, en formato pdf',
                           ext_whitelist=(".jpg", ".jpeg", ".png"), max_upload_size=100194304, widget=forms.FileInput(attrs={'class':'dropify ', 'col': '12', 'data-allowed-file-extensions': 'pdf'}))
