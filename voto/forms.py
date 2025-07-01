import os
from datetime import datetime, timedelta
from ckeditor.widgets import CKEditorWidget
from ckeditor_uploader.widgets import CKEditorUploadingWidget
from django import forms
from django.contrib.auth.models import Group
from django.db.models import Q
from django.forms.models import ModelForm, ModelChoiceField
from django.forms.widgets import DateTimeInput, CheckboxInput, FileInput
from django.utils.safestring import mark_safe
from django.db import models, connection, connections

from sagest.models import OpcionSistema, Departamento, ESTADOS_SOLICITUD_PRODUCTOS
from sga.forms import ExtFileField, deshabilitar_campo
from sga.models import Persona

class EvidenciaActaForm(forms.Form):
    acta_evidencia = ExtFileField(label=u'Evidencia Acta', required=True,
                           help_text=u'Tamaño Maximo permitido 4Mb, en formato pdf, jpg, jpeg, png',
                           ext_whitelist=(".pdf", ".jpg", ".jpeg", ".png",), max_upload_size=4194304,
                           widget=forms.FileInput(
                               attrs={'formwidth': '100%', 'data-allowed-file-extensions': 'png pdf jpg jpeg'}))