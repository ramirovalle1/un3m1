from django.contrib import admin
from bd.models import LogEntryLogin, IPWhiteList, PeriodoGrupo, SubDominio, WebSocket, TemplateBaseSetting, \
    CronogramaCarreraPreMatricula, CronogramaCoordinacionPrematricula, \
    FuncionRequisitoIngresoUnidadIntegracionCurricular, UserQuery

from sga.admin import MANAGERS


class ModeloBaseAdmin(admin.ModelAdmin):
    def get_actions(self, request):
        actions = super(ModeloBaseAdmin, self).get_actions(request)
        if request.user.username not in [x[0] for x in MANAGERS]:
            del actions['delete_selected']
        return actions

    def has_add_permission(self, request):
        return request.user.username in [x[0] for x in MANAGERS]

    def has_module_permission(self, request):
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
            raise Exception('Sin permiso a modificacion')
        else:
            obj.save(request)


class ActionFlagListFilter(admin.SimpleListFilter):
    title = u'Acción'
    parameter_name = 'action_flag'

    def lookups(self, request, model_admin):
        return (
            ('1', "EXITOSO"),
            ('2', "FALLIDO"),
            ('3', "DESCONOCIDO"),
        )

    def queryset(self, request, queryset):
        if self.value():
            return queryset.filter(action_flag=self.value())


class ActionAPPListFilter(admin.SimpleListFilter):
    title = u'SISTEMA'
    parameter_name = 'action_app'

    def lookups(self, request, model_admin):
        return (
            ('1', "SGA"),
            ('2', "SAGEST"),
            ('3', "POSGRADO"),
            ('4', "MARCADAS"),
        )

    def queryset(self, request, queryset):
        if self.value():
            return queryset.filter(action_app=self.value())


class LogEntryLoginAdmin(ModeloBaseAdmin):
    actions = None
    date_hierarchy = 'action_time'
    list_filter = [ActionFlagListFilter, ActionAPPListFilter]
    search_fields = ['user__username', 'change_message']
    list_display = ['action_time', 'user', 'ip_public', 'get_action_flag', 'get_action_app', 'get_data_message']
    raw_id_fields = ('user',)
    readonly_fields = ('action_time', 'user', 'action_app', 'action_flag', 'ip_public', 'ip_private', 'browser', 'ops', 'cookies', 'screen_size', 'change_message')

    def change_view(self, request, object_id, extra_context=None):
        """ customize add/edit form to remove save / save and continue """
        extra_context = extra_context or {}
        extra_context['show_save_and_continue'] = False
        extra_context['show_save'] = False
        return super().change_view(request, object_id, extra_context=extra_context)

    def get_actions(self, request):
        actions = super(LogEntryLoginAdmin, self).get_actions(request)
        if 'delete_selected' in actions:
            del actions['delete_selected']
        return actions

    def has_add_permission(self, request):
        super(LogEntryLoginAdmin, self).has_add_permission(request)
        return False

    def has_delete_permission(self, request, obj=None):
        super(LogEntryLoginAdmin, self).has_delete_permission(request, obj)
        return False


class SubDominioAdmin(ModeloBaseAdmin):
    search_fields = ['nombre', ]
    list_display = ['nombre', 'fecha_caduca_certificado', 'fecha_caduca_dominio', 'estado']


class WebSocketAdmin(ModeloBaseAdmin):
    search_fields = ['url', ]
    list_display = ['url', 'token', 'habilitado', 'sga', 'sagest', 'posgrado']


class TemplateBaseSettingAdmin(ModeloBaseAdmin):
    list_display = ['name_system', 'get_app_display', 'use_menu_favorite_module', 'use_menu_notification', 'use_menu_user_manual']


class FuncionRequisitoIngresoUnidadIntegracionCurricularAdmin(ModeloBaseAdmin):
    list_display = ['nombre', 'funcion']

class UserQueryAdmin(ModeloBaseAdmin):
    list_display = ['user', 'description']
    raw_id_fields = ('user',)

admin.site.register(LogEntryLogin, LogEntryLoginAdmin)
admin.site.register(IPWhiteList, ModeloBaseAdmin)
admin.site.register(PeriodoGrupo, ModeloBaseAdmin)
admin.site.register(SubDominio, SubDominioAdmin)
admin.site.register(WebSocket, WebSocketAdmin)
admin.site.register(TemplateBaseSetting, TemplateBaseSettingAdmin)
admin.site.register(CronogramaCarreraPreMatricula, ModeloBaseAdmin)
admin.site.register(CronogramaCoordinacionPrematricula, ModeloBaseAdmin)
admin.site.register(FuncionRequisitoIngresoUnidadIntegracionCurricular, FuncionRequisitoIngresoUnidadIntegracionCurricularAdmin)
admin.site.register(UserQuery, UserQueryAdmin)
