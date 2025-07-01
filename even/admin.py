from django.contrib import admin
from .models import *
from sga.funciones import ModeloBase
from django import forms
from sga.admin import ModeloBaseAdmin
from sagest.admin import ModeloBaseTabularAdmin


admin.site.register(Evento, ModeloBaseAdmin)
admin.site.register(TipoEvento, ModeloBaseAdmin)
admin.site.register(PeriodoEvento, ModeloBaseAdmin)
admin.site.register(DetallePeriodoEvento, ModeloBaseAdmin)
admin.site.register(RegistroEvento, ModeloBaseAdmin)