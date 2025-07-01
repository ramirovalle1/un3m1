from django.contrib import admin
from settings import MANAGERS
from sga.models import ParentescoPersona
from socioecon.models import FormaTrabajo, PersonaCubreGasto, TipoHogar, TipoVivienda, MaterialPared, MaterialPiso, \
    CantidadBannoDucha, TipoServicioHigienico, CantidadCelularHogar, CantidadTVColorHogar, CantidadVehiculoHogar, \
    NivelEstudio, OcupacionJefeHogar, GrupoSocioEconomico, FichaSocioeconomicaINEC, \
    TipoViviendaPro


class ModeloBaseAdmin(admin.ModelAdmin):

    def get_actions(self, request):
        actions = super(ModeloBaseAdmin, self).get_actions(request)
        # if request.user.username not in [x[0] for x in MANAGERS]:
        #     del actions['delete_selected']
        return actions

    def has_add_permission(self, request):
        return request.user.username in [x[0] for x in MANAGERS]

    def has_change_permission(self, request, obj=None):
        return True

    def has_delete_permission(self, request, obj=None):
        return request.user.username in [x[0] for x in MANAGERS]

    def get_form(self, request, obj=None, **kwargs):
        self.exclude = ("usuario_creacion", "fecha_creacion", "usuario_modificacion", "fecha_modificacion")
        form = super(ModeloBaseAdmin, self).get_form(request, obj, **kwargs)
        return form

    def save_model(self, request, obj, form, change):
        if request.user.username not in [x[0] for x in MANAGERS]:
            raise Exception(u"Sin permiso a modificacion")
        else:
            obj.save(request)


class PersonaExtensionAdmin(ModeloBaseAdmin):
    list_display = ('persona', 'estadocivil', 'tienelicencia', 'tieneconyuge', 'hijos', 'padre', 'madre', 'conyuge')
    ordering = ('persona__apellido1', 'estadocivil')
    search_fields = ('persona__apellido1',)


class PersonaSustentaHogarAdmin(ModeloBaseAdmin):
    list_display = ('persona', 'parentesco', 'formatrabajo', 'ingresomensual')
    ordering = ('persona', 'ingresomensual')
    search_fields = ('formatrabajo',)


class TipoViviendaAdmin(ModeloBaseAdmin):
    list_display = ('nombre', 'codigo', 'puntaje')
    ordering = ('puntaje',)
    search_fields = ('codigo',)


class MaterialParedAdmin(ModeloBaseAdmin):
    list_display = ('nombre', 'codigo', 'puntaje')
    ordering = ('puntaje',)
    search_fields = ('codigo',)


class MaterialPisoAdmin(ModeloBaseAdmin):
    list_display = ('nombre', 'codigo', 'puntaje')
    ordering = ('puntaje',)
    search_fields = ('codigo',)


class CantidadBannoDuchaAdmin(ModeloBaseAdmin):
    list_display = ('nombre', 'codigo', 'puntaje')
    ordering = ('puntaje',)
    search_fields = ('codigo',)


class TipoServicioHigienicoAdmin(ModeloBaseAdmin):
    list_display = ('nombre', 'codigo', 'puntaje')
    ordering = ('puntaje',)
    search_fields = ('codigo',)


class CantidadCelularHogarAdmin(ModeloBaseAdmin):
    list_display = ('nombre', 'codigo', 'puntaje')
    ordering = ('puntaje',)
    search_fields = ('codigo',)


class CantidadTVColorHogarAdmin(ModeloBaseAdmin):
    list_display = ('nombre', 'codigo', 'puntaje')
    ordering = ('puntaje',)
    search_fields = ('codigo',)


class CantidadVehiculoHogarAdmin(ModeloBaseAdmin):
    list_display = ('nombre', 'codigo', 'puntaje')
    ordering = ('puntaje',)
    search_fields = ('codigo',)


class NivelEstudioAdmin(ModeloBaseAdmin):
    list_display = ('nombre', 'codigo', 'puntaje')
    ordering = ('puntaje',)
    search_fields = ('codigo',)


class OcupacionJefeHogarAdmin(ModeloBaseAdmin):
    list_display = ('nombre', 'codigo', 'puntaje')
    ordering = ('puntaje',)
    search_fields = ('codigo',)


class GrupoSocioEconomicoAdmin(ModeloBaseAdmin):
    list_display = ('codigo', 'nombre', 'umbralinicio', 'umbralfin')
    ordering = ('-umbralinicio',)
    search_fields = ('codigo',)


class FichaSocioeconomicaINECAdmin(ModeloBaseAdmin):
    list_display = ('persona', 'grupoeconomico', 'puntajetotal', 'tipohogar')
    search_fields = ('persona__apellido1', 'persona__apellido2', 'persona__nombres', 'persona__cedula')


admin.site.register(FichaSocioeconomicaINEC, FichaSocioeconomicaINECAdmin)
admin.site.register(FormaTrabajo, ModeloBaseAdmin)
admin.site.register(ParentescoPersona, ModeloBaseAdmin)
admin.site.register(PersonaCubreGasto, ModeloBaseAdmin)
admin.site.register(TipoHogar, ModeloBaseAdmin)
admin.site.register(TipoVivienda, TipoViviendaAdmin)
admin.site.register(TipoViviendaPro, ModeloBaseAdmin)
admin.site.register(MaterialPiso, MaterialPisoAdmin)
admin.site.register(MaterialPared, MaterialParedAdmin)
admin.site.register(CantidadBannoDucha, CantidadBannoDuchaAdmin)
admin.site.register(TipoServicioHigienico, TipoServicioHigienicoAdmin)
admin.site.register(CantidadCelularHogar, CantidadCelularHogarAdmin)
admin.site.register(CantidadTVColorHogar, CantidadTVColorHogarAdmin)
admin.site.register(CantidadVehiculoHogar, CantidadVehiculoHogarAdmin)
admin.site.register(NivelEstudio, NivelEstudioAdmin)
admin.site.register(OcupacionJefeHogar, OcupacionJefeHogarAdmin)
admin.site.register(GrupoSocioEconomico, GrupoSocioEconomicoAdmin)
