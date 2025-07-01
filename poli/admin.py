from django.contrib import admin

# Register your models here.
from poli.models import InstitucionEscuela
from sga.admin import ModeloBaseAdmin


class InstitucionEscuelaAdmin(ModeloBaseAdmin):
    list_display = ('id', 'nombre')


admin.site.register(InstitucionEscuela, InstitucionEscuelaAdmin)