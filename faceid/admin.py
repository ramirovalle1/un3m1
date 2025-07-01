from django.contrib import admin

from sga.admin import ModeloBaseAdmin
# from faceid.models import ControlAccesoFaceId
# Register your models here.

class ControlAccesoFaceIdAdmin(ModeloBaseAdmin):
    list_display = ('id', 'app', 'profile', 'activo', 'todos')


# admin.site.register(ControlAccesoFaceId, ControlAccesoFaceIdAdmin)