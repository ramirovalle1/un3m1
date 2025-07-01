from __future__ import unicode_literals

# import json
from datetime import datetime
from django.contrib.admin.utils import NestedObjects
# from django.contrib.auth import get_permission_codename
from django.contrib.auth.models import User, Group, Permission
from django.db.models import Q
from django.utils.encoding import force_str
from django.utils.text import capfirst

from sga.funciones import ModeloBase
from django.db import models
from django.utils.encoding import smart_str
from django.core.cache import cache


def get_deleted_objects(objs, using):
    collector = NestedObjects(using=using)
    collector.collect(objs)
    perms_needed = set()

    def format_callback(obj):
        opts = obj._meta
        no_edit_link = '%s: %s' % (capfirst(opts.verbose_name), force_str(obj))
        return no_edit_link

    to_delete = collector.nested(format_callback)
    protected = [format_callback(obj) for obj in collector.protected]
    model_count = {model._meta.verbose_name_plural: len(objs) for model, objs in collector.model_objs.items()}

    return to_delete, model_count, perms_needed, protected


APP_SGA = 1
APP_SAGEST = 2
APP_POSGRADO = 3
APP_MARCADAS = 4
APP_POSTULATE = 5
APP_ESTUDIANTE = 6
APP_EMPLEO = 7
APP_EMPRESA = 8
APP_NIVELACION = 9
APP_EXAMEN = 10
APP_VINCULACION = 11
APP_FORMACION = 12
FLAG_SUCCESSFUL = 1
FLAG_FAILED = 2
FLAG_UNKNOWN = 3


class Perms(models.Model):
    class Meta:
        permissions = (
            ("puede_acceder_usuario", "Acceder usuarios"),
            ("puede_acceder_grupo", "Acceder grupos"),
            ("puede_acceder_modulo", "Acceder módulos"),
            ("puede_acceder_grupos_modulos", "Acceder grupos módulos"),
            ("puede_acceder_persona", "Acceder personas"),
            ("puede_acceder_perfil_acceso_usuario", "Acceder perfiles acceso usuarios"),
            ("puede_acceder_periodo_academico", "Acceder periodos académicos"),
            ("puede_acceder_variables_globales", "Acceder variables globales"),
            ("puede_acceder_motivo_matricula_especial", "Acceder motivos matrícula especial"),
            ("puede_acceder_estado_matricula_especial", "Acceder estados matrícula especial"),
            ("puede_acceder_proceso_matricula_especial", "Acceder procesos matrícula especial"),
            ("puede_acceder_config_proceso_matricula_especial", "Acceder configuración del proceso matrícula especial"),
            ("puede_acceder_motivo_retiro_matricula", "Acceder motivos retiro matrícula"),
            ("puede_acceder_estado_retiro_matricula", "Acceder estados retiro matrícula"),
            ("puede_acceder_proceso_retiro_matricula", "Acceder procesos retiro matrícula"),
            ("puede_acceder_config_proceso_retiro_matricula", "Acceder configuración del proceso retiro matrícula"),
            ("puede_acceder_config_carnet", "Acceder configuración de carné"),
            ("puede_acceder_web_services_wsdl", "Acceder servicio web WSDL"),
            ("puede_acceder_periodo_crontab", "Acceder periodo crontab"),
            ("puede_acceder_ajuste_plantilla", "Acceder ajustes de plantillas"),
            ("puede_acceder_dia_no_laborable", "Acceder días no laborables"),
            ("puede_agregar_usuario", "Agregar usuario"),
            ("puede_modificar_usuario", "Modificar usuario"),
            ("puede_eliminar_usuario", "Elimnar usuario"),
            ("puede_resetear_clave_usuario", "Resetear clave usuario"),
            ("puede_agregar_modulo", "Agregar modulo"),
            ("puede_modificar_modulo", "Modificar modulo"),
            ("puede_eliminar_modulo", "Eliminar modulo"),
            ("puede_agregar_grupo", "Agregar grupo"),
            ("puede_modificar_grupo", "Modificar grupo"),
            ("puede_eliminar_grupo", "Eliminar grupo"),
            ("puede_agregar_grupos_modulos", "Agregar grupos modulos"),
            ("puede_modificar_grupos_modulos", "Modificar grupos modulos"),
            ("puede_eliminar_grupos_modulos", "Eliminar grupos modulos"),
            ("puede_agregar_persona", "Agregar persona"),
            ("puede_modificar_persona", "Modificar persona"),
            ("puede_eliminar_persona", "Eliminar persona"),
            ("puede_agregar_perfil_acceso_usuario", "Agregar perfil acceso usuario"),
            ("puede_modificar_perfil_acceso_usuario", "Modificar perfil acceso usuario"),
            ("puede_eliminar_perfil_acceso_usuario", "Eliminar perfil acceso usuario"),
            ("puede_agregar_periodo_academico", "Agregar periodo académico"),
            ("puede_modificar_periodo_academico", "Modificar periodo académico"),
            ("puede_eliminar_periodo_academico", "Eliminar periodo académico"),
            ("puede_modificar_periodo_academico_grupo", "Modificar periodo académico grupo"),
            ("puede_modificar_periodo_academico_matriculacion", "Modificar periodo académico matriculación"),
            ("puede_modificar_periodo_academico_niveles", "Modificar periodo académico niveles"),
            ("puede_modificar_periodo_academico_finanzas", "Modificar periodo académico finanzas"),
            ("puede_ver_periodo_academico_estadistica_matricula", "Ver periodo académico - estadísticas matrícula"),
            ("puede_modificar_periodo_academico_academia", "Modificar periodo académico academia"),
            ("puede_agregar_variable_global", "Agregar variable global"),
            ("puede_modificar_variable_global", "Modificar variable global"),
            ("puede_eliminar_variable_global", "Eliminar variable global"),
            ("puede_agregar_motivo_matricula_especial", "Agregar motivo matrícula especial"),
            ("puede_modificar_motivo_matricula_especial", "Modificar motivo matrícula especial"),
            ("puede_eliminar_motivo_matricula_especial", "Eliminar motivo matrícula especial"),
            ("puede_agregar_estado_matricula_especial", "Agregar estado matrícula especial"),
            ("puede_modificar_estado_matricula_especial", "Modificar estado matrícula especial"),
            ("puede_eliminar_estado_matricula_especial", "Eliminar estado matrícula especial"),
            ("puede_agregar_proceso_matricula_especial", "Agregar proceso matrícula especial"),
            ("puede_modificar_proceso_matricula_especial", "Modificar proceso matrícula especial"),
            ("puede_eliminar_proceso_matricula_especial", "Eliminar proceso matrícula especial"),
            ("puede_agregar_config_proceso_matricula_especial", "Agregar configuración de proceso matrícula especial"),
            ("puede_modificar_config_proceso_matricula_especial",
             "Modificar configuración de proceso matrícula especial"),
            (
            "puede_eliminar_config_proceso_matricula_especial", "Eliminar configuración de proceso matrícula especial"),
            ("puede_agregar_motivo_retiro_matricula", "Agregar motivo retiro matrícula"),
            ("puede_modificar_motivo_retiro_matricula", "Modificar motivo retiro matrícula"),
            ("puede_eliminar_motivo_retiro_matricula", "Eliminar motivo retiro matrícula"),
            ("puede_agregar_estado_retiro_matricula", "Agregar estado retiro matrícula"),
            ("puede_modificar_estado_retiro_matricula", "Modificar estado retiro matrícula"),
            ("puede_eliminar_estado_retiro_matricula", "Eliminar estado retiro matrícula"),
            ("puede_agregar_proceso_retiro_matricula", "Agregar proceso retiro matrícula"),
            ("puede_modificar_proceso_retiro_matricula", "Modificar proceso retiro matrícula"),
            ("puede_eliminar_proceso_retiro_matricula", "Eliminar proceso retiro matrícula"),
            ("puede_agregar_config_proceso_retiro_matricula", "Agregar configuración de proceso retiro matrícula"),
            ("puede_modificar_config_proceso_retiro_matricularetiro_matricula",
             "Modificar configuración de proceso retiro matrícula"),
            ("puede_eliminar_config_proceso_retiro_matricula", "Eliminar configuración de proceso retiro matrícula"),
            ("puede_agregar_config_carnet", "Agregar configuración de carné"),
            ("puede_modificar_config_carnet", "Modificar configuración de carné"),
            ("puede_eliminar_config_carnet", "Eliminar configuración de carné"),
            ("puede_agregar_web_services_wsdl", "Agregar servicio web WSDL"),
            ("puede_modificar_web_services_wsdl", "Modificar servicio web WSDL"),
            ("puede_eliminar_web_services_wsdl", "Eliminar servicio web WSDL"),
            ("puede_resetear_password_web_services_wsdl", "Resetear clave de usuario del servicio web WSDL"),
            ("puede_agregar_periodo_crontab", "Agregar periodo crontab"),
            ("puede_modificar_periodo_crontab", "Modificar periodo crontab"),
            ("puede_eliminar_periodo_crontab", "Eliminar periodo crontab"),
            ("puede_agregar_ajuste_plantilla", "Agregar ajuste de plantilla"),
            ("puede_modificar_ajuste_plantilla", "Modificar ajuste de plantilla"),
            ("puede_eliminar_ajuste_plantilla", "Eliminar ajuste de plantilla"),
            ("puede_agregar_dia_no_laborable", "Agregar días no laborables"),
            ("puede_modificar_dia_no_laborable", "Modificar días no laborables"),
            ("puede_eliminar_dia_no_laborable", "Eliminar días no laborables"),
        )


class Usuario(User):
    class Meta:
        proxy = True

    def __str__(self):
        return f"{self.username} - {'Activo' if self.is_active else 'Inactivo'}"
        super(Usuario, self).__str__()

    @staticmethod
    def flexbox_query(q, extra=None, limit=25):
        if q:
            q = q.lower()
        return Usuario.objects.filter(Q(username__contains=q))[:limit]

    def flexbox_repr(self):
        return self.__str__()


class LogQuery(ModeloBase):
    baseafectada = models.TextField(default='', verbose_name=u'Base Afectada', blank=True)
    query = models.TextField(default='', verbose_name=u'Query Ejecutado', blank=True)
    filasafectadas = models.TextField(default='', verbose_name=u'Filas Afectadas', blank=True)
    url_archivo = models.TextField(default='', verbose_name=u'Url Archivo', blank=True)

class UserQuery(ModeloBase):
    user = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name=u'Usuario')
    description = models.TextField(default='', verbose_name=u'Observación/Detalle', blank=True)

    class Meta:
        verbose_name = u"usuario permitido para querys"
        verbose_name_plural = u"usuarios permitidos para querys"

class LogEntryLoginManager(models.Manager):
    use_in_migrations = True

    def log_action(self, action_flag, action_app, ip_private, ip_public, browser, ops, cookies, screen_size, user=None,
                   change_message=None):
        self.model.objects.create(user=user,
                                  action_flag=action_flag,
                                  action_app=action_app,
                                  ip_private=ip_private,
                                  ip_public=ip_public,
                                  browser=browser,
                                  ops=ops,
                                  cookies=cookies,
                                  screen_size=screen_size,
                                  change_message=change_message)


class LogEntryLogin(models.Model):
    action_time = models.DateTimeField(default=datetime.now, editable=False, verbose_name=u"Tiempo de Acción")
    user = models.ForeignKey(User, on_delete=models.CASCADE, blank=True, null=True, related_name='+', verbose_name=u"Usuario")
    action_app = models.PositiveSmallIntegerField(verbose_name=u"Acción de Aplicación")
    action_flag = models.PositiveSmallIntegerField(verbose_name=u"Acción de Inicio")
    ip_private = models.CharField(max_length=100, blank=True, null=True, db_index=True, verbose_name=u"IP Privada")
    ip_public = models.CharField(max_length=100, blank=True, null=True, db_index=True, verbose_name=u"IP Publica")
    browser = models.CharField(default='', max_length=100, blank=True, null=True, db_index=True, verbose_name=u"Browser")
    ops = models.CharField(default='', max_length=50, blank=True, null=True, db_index=True, verbose_name=u"Sistema Operativo")
    cookies = models.TextField(blank=True, null=True, db_index=True, verbose_name=u"Cookies")
    screen_size = models.CharField(default='', max_length=50, blank=True, null=True, db_index=True, verbose_name=u"Tamaño de Pantalla")
    change_message = models.TextField(blank=True, null=True, db_index=True, verbose_name=u"Observación")

    objects = LogEntryLoginManager()

    def __repr__(self):
        return smart_str(self.action_time)

    def __str__(self):
        from sga.models import Persona
        if self.user:
            if Persona.objects.filter(usuario=self.user).exists():
                person = self.user.persona_set.first()
                return u"%s >> PERSONA: %s - APP: %s - BROWSER: %s - OPS: %s - IPP: %s - IPI: %s - COOKIES: %s - SCREENSIZE: %s" % (
                    self.get_action_flag(), person.__str__(), self.get_action_app(), self.browser, self.ops,
                    self.ip_public,
                    self.ip_private, self.cookies, self.screen_size)
            else:
                return u"%s >> USUARIO: %s - APP: %s - BROWSER: %s - OPS: %s - IPPU: %s - IPPR: %s - COOKIES: %s - SCREENSIZE: %s" % (
                    self.get_action_flag(), self.user.username, self.get_action_app(), self.browser, self.ops,
                    self.ip_public, self.ip_private, self.cookies, self.screen_size)
        else:

            return u"%s >> %s - APP: %s - BROWSER: %s - OPS: %s - IPPU: %s - IPPR: %s - COOKIES: %s - SCREENSIZE: %s" % (
                self.get_action_flag(), self.change_message, self.get_action_app(), self.browser, self.ops,
                self.ip_public,
                self.ip_private, self.cookies, self.screen_size)

    def is_sga(self):
        return self.action_app == APP_SGA

    def is_sagest(self):
        return self.action_app == APP_SAGEST

    def is_posgrado(self):
        return self.action_app == APP_POSGRADO

    def is_marcadas(self):
        return self.action_app == APP_MARCADAS

    def is_successful(self):
        return self.action_flag == FLAG_SUCCESSFUL

    def is_failed(self):
        return self.action_flag == FLAG_FAILED

    def is_unknown(self):
        return self.action_flag == FLAG_UNKNOWN

    def get_person(self):
        if self.user:
            if self.user.persona_set.values("id").exists():
                return self.user.persona_set.first().nombre_completo_inverso()
            else:
                return self.user
        return 'SIN USUARIO'

    def get_ip_private(self):
        from sga.funciones import convertir_string_ip
        return convertir_string_ip(self.ip_private)

    def get_ip_public(self):
        from sga.funciones import convertir_string_ip
        return convertir_string_ip(self.ip_public)

    def get_action_app(self):
        if self.is_sga():
            return 'SGA'
        elif self.is_sagest():
            return 'SAGEST'
        elif self.is_posgrado():
            return 'POSGRADO'
        elif self.is_marcadas():
            return 'MARCADAS'
        else:
            return 'DESCONOCIDA'

    def get_action_flag(self):
        if self.is_successful():
            return 'EXITOSO'
        elif self.is_failed():
            return 'FALLIDO'
        else:
            return 'DESCONOCIDO'

    def get_data_message(self):
        # if self.is_unknown():
        #     return Truncator(self.__str__()).chars(len(self.__str__())-5, truncate = '___')
        return self.__str__()

    def save(self, *args, **kwargs):
        super(LogEntryLogin, self).save(*args, **kwargs)

    class Meta:
        verbose_name = u"Entrada de Registro Iniciar de Sesión"
        verbose_name_plural = u"Entradas de Registros Iniciar de Sesión"
        ordering = ('-action_time',)


class IPWhiteList(ModeloBase):
    ip = models.CharField(default='', max_length=20, verbose_name=u'Motivo')
    observacion = models.TextField(default='', verbose_name=u'Observación')
    habilitado = models.BooleanField(default=True, verbose_name=u'Habilitado')
    sga = models.BooleanField(default=False, verbose_name=u'SGA')
    sagest = models.BooleanField(default=False, verbose_name=u'SAGEST')
    posgrado = models.BooleanField(default=False, verbose_name=u'POSGRADO')

    def __str__(self):
        return u'%s' % self.ip

    def total_acceso(self):
        if self.ip.endswith(".0.0"):
            ipv = self.ip.split('.')
            return len(LogEntryLogin.objects.values("id").filter(ip_private__icontains=ipv[0] + '.' + ipv[1]))
        elif self.ip.endswith(".0"):
            ipv = self.ip.split('.')
            return len(
                LogEntryLogin.objects.values("id").filter(ip_private__icontains=ipv[0] + '.' + ipv[1] + '.' + ipv[2]))
        return 0

    def save(self, *args, **kwargs):
        self.observacion = self.observacion.upper().strip()
        self.ip = self.ip.upper().strip()
        super(IPWhiteList, self).save(*args, **kwargs)

    class Meta:
        verbose_name = u"IP Lista Blanca"
        verbose_name_plural = u"IPs Lista Blanca"
        unique_together = ('ip',)


class WebSocket(ModeloBase):
    url = models.CharField(max_length=250, verbose_name=u'URL', help_text=u'URL del servicio del Socket')
    token = models.TextField(verbose_name=u'Token', null=True, blank=True, help_text=u'Token de comunicación')
    observacion = models.TextField(default='', verbose_name=u'Observación')
    habilitado = models.BooleanField(default=False, verbose_name=u'Habilitado')
    sga = models.BooleanField(default=False, verbose_name=u'SGA')
    sagest = models.BooleanField(default=False, verbose_name=u'SAGEST')
    posgrado = models.BooleanField(default=False, verbose_name=u'POSGRADO')
    postulacionposgrado = models.BooleanField(default=False, verbose_name=u'POSTULACION POSGRADO')
    api = models.BooleanField(default=False, verbose_name=u'API')

    def __str__(self):
        return u'%s' % self.url

    class Meta:
        verbose_name = u"WebSocket"
        verbose_name_plural = u"WebSockets"
        unique_together = ('url',)

    def delete_cache(self):
        # from sga.templatetags.sga_extras import encrypt
        if cache.has_key(f"web_socket_api_serializer"):
            cache.delete(f"web_socket_api_serializer")

    def delete(self, *args, **kwargs):
        self.delete_cache()
        super(WebSocket, self).delete(*args, **kwargs)

    def save(self, *args, **kwargs):
        self.url = self.url.strip()
        if self.token:
            self.token = self.token.strip()
        self.delete_cache()
        super(WebSocket, self).save(*args, **kwargs)


class PeriodoGrupo(ModeloBase):
    periodo = models.ForeignKey('sga.Periodo', on_delete=models.CASCADE, related_name='+', verbose_name=u'Periodo académico')
    grupos = models.ManyToManyField(Group, verbose_name=u'Grupos')
    visible = models.BooleanField(default=True, verbose_name=u'Visible')

    def __str__(self):
        return u'%s' % self.periodo

    def save(self, *args, **kwargs):
        super(PeriodoGrupo, self).save(*args, **kwargs)

    class Meta:
        verbose_name = u"Periodo grupo"
        verbose_name_plural = u"Periodos grupos"
        unique_together = ('periodo',)


ESTADO_DOMINIO = (
    (0, u"NINGUNO"),
    (1, u"ACTIVO"),
    (2, u"INACTIVO"),
)


class SubDominio(ModeloBase):
    nombre = models.TextField(default='', verbose_name=u'Nombre', blank=True)
    fecha_caduca_certificado = models.DateTimeField(verbose_name=u'fecha caduca certificado', blank=True, null=True)
    fecha_caduca_dominio = models.DateTimeField(verbose_name=u'fecha caduca dominio', blank=True, null=True)
    estado = models.IntegerField(choices=ESTADO_DOMINIO, default=1, verbose_name=u'Estado de dominio')

    def __str__(self):
        return u'%s cert: %s domi: %s (%s)' % (
            self.nombre, self.fecha_caduca_certificado, self.fecha_caduca_dominio, self.get_estado_display())

    class Meta:
        verbose_name = u"Sub dominio"
        verbose_name_plural = u"Sub dominios"
        ordering = ('nombre',)


ACTION_TYPE_USER_TOKEN = (
    (1, u'PASSWORD_RECOVERY'),
    (2, u'REMOVE_MATERIA'),
    (3, u'DELETE_MATRICULA'),
    (4, u'USER_PROFILE_CHANGE'),
    (5, u'LOGIN_EPUNEMI'),
    (6, u'VIEW_KEY_ACCESS_QUIZ')
)

APP_LABEL = (
    (1, u'SGA'),
    (2, u'SAGEST'),
    (3, u'POSGRADO'),
    (4, u'SIE'),
    (5, u'EPUNEMI'),
    (6, u'NIVELACION'),
    (7, u'POSTULATE'),
    (8, u'EMPLEO'),
    (9, u'EXAMEN'),
)

class UserToken(ModeloBase):
    user = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name=u'Usuario')
    token = models.CharField(default='', max_length=500, verbose_name=u'Token', db_index=True)
    action_type = models.IntegerField(choices=ACTION_TYPE_USER_TOKEN, default=1, verbose_name=u'Tipo de acción')
    date_expires = models.DateTimeField(verbose_name=u'Fecha de expiración', db_index=True)
    app = models.IntegerField(choices=APP_LABEL, default=1, verbose_name=u'Sistema')
    isActive = models.BooleanField(default=True, verbose_name=u"Activo?")

    def __str__(self):
        return f"{self.user} - {self.date_expires}"

    def isValidoToken(self):
        if self.isActive:
            return self.date_expires >= datetime.now()
        return False

    def inactiveToken(self):
        self.isActive = False
        self.save()

    class Meta:
        verbose_name = u"Token Usuario"
        verbose_name_plural = u"Tokens Usuarios"
        ordering = ('user', 'date_expires',)
        unique_together = ('token',)


class CronogramaCarrera(ModeloBase):
    carrera = models.ForeignKey('sga.Carrera', on_delete=models.CASCADE, verbose_name=u'Carrera')
    nivel = models.ManyToManyField('sga.NivelMalla', verbose_name=u'Niveles')
    sesion = models.ManyToManyField('sga.Sesion', verbose_name=u'Sección')
    fechainicio = models.DateField(null=True, blank=True, verbose_name=u'Fecha inicio')
    horainicio = models.TimeField(null=True, blank=True, verbose_name=u'Hora inicio')
    fechafin = models.DateField(null=True, blank=True, verbose_name=u'Fecha fin')
    horafin = models.TimeField(null=True, blank=True, verbose_name=u'Hora fin')
    activo = models.BooleanField(default=False, verbose_name=u'Activo')

    def __str__(self):
        return u'%s: %s - %s' % (self.carrera, self.fechainicio, self.fechafin)

    class Meta:
        verbose_name = u"Cronograma de carrera"
        verbose_name_plural = u"Cronogramas de carreras"
        ordering = ['carrera', 'fechainicio', 'fechafin']

    def tiene_niveles(self):
        return self.nivel.all().values("id").exists()

    def niveles(self):
        return self.nivel.all()

    def tiene_sesiones(self):
        return self.sesion.all().values("id").exists()

    def sesiones(self):
        return self.sesion.all()

    def delete_cache(self):
        # from sga.templatetags.sga_extras import encrypt
        from sga.funciones import variable_valor
        id_periodo_login_matricula = variable_valor('ID_BLOQUEO_LOGIN_MATRICULA')
        if id_periodo_login_matricula is None:
            id_periodo_login_matricula = 0

        if id_periodo_login_matricula:
            if cache.has_key(f"cronograma_matricula_periodo_id_{id_periodo_login_matricula}"):
                cache.delete(f"cronograma_matricula_periodo_id_{id_periodo_login_matricula}")

    def delete(self, *args, **kwargs):
        self.delete_cache()
        super(CronogramaCarrera, self).delete(*args, **kwargs)

    def save(self, *args, **kwargs):
        self.delete_cache()
        super(CronogramaCarrera, self).save(*args, **kwargs)


class CronogramaCoordinacion(ModeloBase):
    coordinacion = models.ForeignKey('sga.Coordinacion', on_delete=models.CASCADE, verbose_name=u'Coordinación')
    cronogramacarrera = models.ManyToManyField(CronogramaCarrera, verbose_name=u'Carreras')
    fechainicio = models.DateField(null=True, blank=True, verbose_name=u'Fecha inicio')
    horainicio = models.TimeField(null=True, blank=True, verbose_name=u'Hora inicio')
    fechafin = models.DateField(null=True, blank=True, verbose_name=u'Fecha fin')
    horafin = models.TimeField(null=True, blank=True, verbose_name=u'Hora fin')
    activo = models.BooleanField(default=False, verbose_name=u'Activo')

    def __str__(self):
        return u'%s: %s - %s' % (self.coordinacion, self.fechainicio, self.fechafin)

    class Meta:
        verbose_name = u"Cronograma de coordinación"
        verbose_name_plural = u"Cronogramas de coordinaciones"
        ordering = ['coordinacion', 'fechainicio', 'fechafin']

    def tiene_cronogramacarreras(self):
        return self.cronogramacarrera.all().values("id").exists()

    def cronogramacarreras(self):
        return self.cronogramacarrera.all()

    def delete_cache(self):
        # from sga.templatetags.sga_extras import encrypt
        from sga.funciones import variable_valor
        id_periodo_login_matricula = variable_valor('ID_BLOQUEO_LOGIN_MATRICULA')
        if id_periodo_login_matricula is None:
            id_periodo_login_matricula = 0

        if id_periodo_login_matricula:
            if cache.has_key(f"cronograma_matricula_periodo_id_{id_periodo_login_matricula}"):
                cache.delete(f"cronograma_matricula_periodo_id_{id_periodo_login_matricula}")

    def delete(self, *args, **kwargs):
        self.delete_cache()
        super(CronogramaCoordinacion, self).delete(*args, **kwargs)

    def save(self, *args, **kwargs):
        self.delete_cache()
        super(CronogramaCoordinacion, self).save(*args, **kwargs)



TIPO_PERIODO_CRONTAB_CHOICES = (
    (1, "ADMISION"),
    (2, "PREGRADO"),
    (3, "POSGRADO"),
)


class PeriodoCrontab(ModeloBase):
    periodo = models.ForeignKey('sga.Periodo', on_delete=models.CASCADE, blank=True, null=True, verbose_name=u'Periodo')
    type = models.IntegerField(default=0, choices=TIPO_PERIODO_CRONTAB_CHOICES, verbose_name=u'Tipo')
    is_activo = models.BooleanField(default=False, verbose_name=u"Esta activo?")
    upgrade_level_inscription = models.BooleanField(default=False, verbose_name=u"Actualizar nivel inscripción?")
    upgrade_state_enrollment = models.BooleanField(default=False, verbose_name=u"Actualizar estado matrícula?")
    upgrade_level_enrollment = models.BooleanField(default=False, verbose_name=u"Actualizar nivel matrícula?")
    create_lesson_previa = models.BooleanField(default=False, verbose_name=u"Crear lección")
    delete_lesson_previa = models.BooleanField(default=False, verbose_name=u"Eliminar lección")
    notify_student_activities = models.BooleanField(default=False, verbose_name=u"Notificar actividades del estudiante")
    bloqueo_state_enrollment = models.BooleanField(default=False, verbose_name=u"Bloqueo estado matrícula?")

    def __str__(self):
        return f"{self.periodo.__str__()} - {self.get_type_display()}"

    def validate_duplication(self):
        if self.is_activo:
            if self.id:
                return PeriodoCrontab.objects.filter(is_activo=True, type=self.type).exclude(pk=self.id).exists()
            else:
                return PeriodoCrontab.objects.filter(is_activo=True, type=self.type).exists()

    def save(self, *args, **kwargs):
        if self.validate_duplication():
            raise NameError(u"Existe otro periodo activo para cron")
        super(PeriodoCrontab, self).save(*args, **kwargs)

    class Meta:
        verbose_name = u'Periodo crontab'
        verbose_name_plural = u'Periodos academia'
        ordering = ('periodo',)
        unique_together = ('periodo',)


APP_LABEL_TEMPLATE = APP_LABEL


class TemplateBaseSetting(ModeloBase):
    name_system = models.CharField(max_length=500, default='', verbose_name=u'Nombre del Sistema')
    app = models.IntegerField(choices=APP_LABEL_TEMPLATE, default=1, verbose_name=u'Aplicación')
    use_menu_favorite_module = models.BooleanField(default=False, verbose_name=u"Usar modulo favorito")
    use_menu_notification = models.BooleanField(default=False, verbose_name=u"Usar notificación")
    use_menu_user_manual = models.BooleanField(default=False, verbose_name=u"Usar manual de usuario")
    use_api = models.BooleanField(default=False, verbose_name=u"Usar API")

    def __str__(self):
        return f"{self.name_system} - {self.get_app_display()}"

    class Meta:
        verbose_name = u'Ajuste de Plantilla Base'
        verbose_name_plural = u'Ajustes de Plantilla Base'
        ordering = ('app',)
        unique_together = ('name_system', 'app',)

    def es_sga(self):
        return self.app == 1

    def es_sagest(self):
        return self.app == 2

    def es_posgrado(self):
        return self.app == 3

    def delete_cache(self):
        # from sga.templatetags.sga_extras import encrypt
        if self.app == 4:
            if cache.has_key(f"template_base_setting_app_sie_serializer"):
                cache.delete(f"template_base_setting_app_sie_serializer")

    def delete(self, *args, **kwargs):
        self.delete_cache()
        super(TemplateBaseSetting, self).delete(*args, **kwargs)

    def save(self, *args, **kwargs):
        self.name_system = self.name_system.strip()
        self.delete_cache()
        super(TemplateBaseSetting, self).save(*args, **kwargs)


class MenuFavoriteProfile(ModeloBase):
    setting = models.ForeignKey(TemplateBaseSetting, on_delete=models.CASCADE, verbose_name=u'Ajuste de plantilla')
    profile = models.ForeignKey('sga.PerfilUsuario', on_delete=models.CASCADE, verbose_name=u'Perfil Usuario')
    modules = models.ManyToManyField('sga.Modulo', verbose_name=u'Modulos')

    def __str__(self):
        return f"{self.setting.__str__()} - {self.profile.persona.__str__()} ({self.profile.__str__()})"

    def tiene_modulos(self):
        return self.modules.values("id").all().exists()

    def mis_modulos_id(self):
        if self.tiene_modulos():
            if self.setting.es_sga():
                return self.modules.filter(activo=True, status=True, sga=True).values_list('id', flat=True).distinct()
            elif self.setting.es_sagest():
                return self.modules.filter(activo=True, status=True, sagest=True).values_list('id',
                                                                                              flat=True).distinct()
            elif self.setting.es_posgrado():
                return self.modules.filter(activo=True, status=True, posgrado=True).values_list('id',
                                                                                                flat=True).distinct()
            else:
                return None
        return None

    def mis_modulos(self):
        if self.tiene_modulos():
            if self.setting.es_sga():
                return self.modules.filter(activo=True, status=True, sga=True)
            elif self.setting.es_sagest():
                return self.modules.filter(activo=True, status=True, sagest=True)
            elif self.setting.es_posgrado():
                return self.modules.filter(activo=True, status=True, posgrado=True)
            else:
                return None
        return None

    def save(self, *args, **kwargs):
        from sga.templatetags.sga_extras import encrypt
        if self.profile:
            eMenuFavoriteProfilesEnCache = cache.get(f"module_favorites_perfilprincipal_id_{encrypt(self.profile.id)}")
            if not eMenuFavoriteProfilesEnCache is None:
                cache.delete(f"module_favorites_perfilprincipal_id_{encrypt(self.profile.id)}")
        super(MenuFavoriteProfile, self).save(*args, **kwargs)

    class Meta:
        verbose_name = u'Menu Favorito Perfil'
        verbose_name_plural = u'Menus Favorito Perfil'
        ordering = ('setting',)
        unique_together = ('setting', 'profile',)


class Geolocation(ModeloBase):
    accuracy = models.FloatField(default=0, null=True, blank=True, verbose_name='Exactitud')
    altitude = models.FloatField(default=0, null=True, blank=True, verbose_name='Altitud')
    altitudeAccuracy = models.FloatField(default=0, null=True, blank=True, verbose_name='Altitud Exactitud')
    heading = models.FloatField(default=0, null=True, blank=True, verbose_name='Cabecera')
    latitude = models.FloatField(default=0, verbose_name='Latitud')
    longitude = models.FloatField(default=0, verbose_name='Longitud')
    speed = models.FloatField(default=0, null=True, blank=True, verbose_name='Velocidad')

    class Meta:
        verbose_name = u'Geolocalización'
        verbose_name_plural = u'Geolocalizaciones'
        unique_together = ('latitude', 'longitude',)


class GeolocationUser(ModeloBase):
    user = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name=u"Usuario")
    geolocation = models.ForeignKey(Geolocation, on_delete=models.CASCADE, verbose_name=u"Geolocalización")

    class Meta:
        verbose_name = u'Geolocalización de Usuario'
        verbose_name_plural = u'Geolocalizaciones de Usuario'
        ordering = ('user', 'geolocation')
        unique_together = ('user', 'geolocation',)


class CronogramaCarreraPreMatricula(ModeloBase):
    carrera = models.ForeignKey('sga.Carrera', on_delete=models.CASCADE, verbose_name=u'Carrera')
    nivel = models.ManyToManyField('sga.NivelMalla', verbose_name=u'Niveles')
    fechainicio = models.DateField(null=True, blank=True, verbose_name=u'Fecha inicio')
    horainicio = models.TimeField(null=True, blank=True, verbose_name=u'Hora inicio')
    fechafin = models.DateField(null=True, blank=True, verbose_name=u'Fecha fin')
    horafin = models.TimeField(null=True, blank=True, verbose_name=u'Hora fin')
    activo = models.BooleanField(default=False, verbose_name=u'Activo')

    def __str__(self):
        return u'%s: %s - %s' % (self.carrera, self.fechainicio, self.fechafin)

    def tiene_niveles(self):
        return self.nivel.all().values("id").exists()

    def niveles(self):
        return self.nivel.all()

    class Meta:
        verbose_name = u"Cronograma de carrera pre matricula"
        verbose_name_plural = u"Cronogramas de carreras pre matricula"
        ordering = ['carrera', 'fechainicio', 'fechafin']


class CronogramaCoordinacionPrematricula(ModeloBase):
    coordinacion = models.ForeignKey('sga.Coordinacion', on_delete=models.CASCADE, verbose_name=u'Coordinación')
    cronogramacarrera = models.ManyToManyField(CronogramaCarreraPreMatricula, verbose_name=u'Carreras')
    fechainicio = models.DateField(null=True, blank=True, verbose_name=u'Fecha inicio')
    horainicio = models.TimeField(null=True, blank=True, verbose_name=u'Hora inicio')
    fechafin = models.DateField(null=True, blank=True, verbose_name=u'Fecha fin')
    horafin = models.TimeField(null=True, blank=True, verbose_name=u'Hora fin')
    activo = models.BooleanField(default=False, verbose_name=u'Activo')

    def __str__(self):
        return u'%s: %s - %s' % (self.coordinacion, self.fechainicio, self.fechafin)

    def tiene_cronogramacarrerasprematricula(self):
        return self.cronogramacarrera.all().values("id").exists()

    def cronogramacarrerasprematricula(self):
        return self.cronogramacarrera.all()

    class Meta:
        verbose_name = u"Cronograma de coordinación pre matricula"
        verbose_name_plural = u"Cronogramas de coordinaciones pre matricula"
        ordering = ['coordinacion', 'fechainicio', 'fechafin']


CHOICES_FUNCION_REQUISITO_INGRESO_UNIDAD_INTEGRACION_CURRICULAR = (
    (1, u"estar_matriculado_todas_asignaturas_ultimo_periodo_academico"),
    (2, u"asignaturas_aprobadas_primero_penultimo_nivel"),
    (3, u"ficha_estudiantil_actualizada_completa"),
    (4, u"haber_aprobado_modulos_ingles"),
    (5, u"haber_aprobado_modulos_computacion"),
    (6, u"haber_cumplido_horas_creditos_practicas_preprofesionales"),
    (7, u"haber_cumplido_horas_creditos_vinculacion"),
    (8, u"no_adeudar_institucion"),
    (9, u"tiene_certificacion_segunda_lengua_sin_aprobar_director_carrera"),
    (10, u"tiene_certificacion_segunda_lengua_aprobado_director_carrera"),
    (11, u"asignaturas_aprobadas_primero_ultimo_nivel"),
    (12, u"asignaturas_aprobadas_primero_septimo_nivel"),
    (13, u"tener_certificado_inglesb2"),
)

CHOICES_FUNCION_DETALLE_REQUISITO = (
    (2, u"detalle_aprobadas_primero_penultimo_nivel"),
    (3, u"detalle_ficha_estudiantil_actualizada_completa"),
    (4, u"detalle_aprobado_modulos_ingles"),
    (5, u"detalle_aprobado_modulos_computacion"),
    (6, u"detalle_cumplido_horas_creditos_practicas_preprofesionales"),
    (7, u"detalle_cumplido_horas_creditos_vinculacion"),
    (11, u"detalle_aprobadas_primero_ultimo_nivel"),
)


class FuncionRequisitoIngresoUnidadIntegracionCurricular(ModeloBase):
    nombre = models.CharField(max_length=250, verbose_name=u'Requisito')
    modelpage = models.CharField(default='', blank=True, null=True, max_length=100, verbose_name=u'Pantalla model')
    mensajenocumple = models.TextField(default='', blank=True, null=True, verbose_name=u'Mensaje cuando no cumple requisito')
    validasecretariageneral = models.BooleanField(default=True, verbose_name=u'Valido para secretaria general')
    funcion = models.IntegerField(choices=CHOICES_FUNCION_REQUISITO_INGRESO_UNIDAD_INTEGRACION_CURRICULAR, default=0, verbose_name=u'Función a ejecutar')

    def __str__(self):
        return u'%s' % self.nombre

    class Meta:
        verbose_name = u'Funcion de Requisito de Titulación'
        verbose_name_plural = u'Funciones de Requisito de titulación'
        unique_together = ('funcion', 'nombre',)

    def nombre_funcion(self):
        return dict(CHOICES_FUNCION_REQUISITO_INGRESO_UNIDAD_INTEGRACION_CURRICULAR)[self.funcion]

    def nombre_funcionrequisito(self):
        valida = False
        for li in CHOICES_FUNCION_DETALLE_REQUISITO:
            if self.funcion == li[0]:
                valida = True
        if valida:
            if dict(CHOICES_FUNCION_DETALLE_REQUISITO)[self.funcion]:
                return dict(CHOICES_FUNCION_DETALLE_REQUISITO)[self.funcion]
        else:
            return False


class UserProfileChangeToken(ModeloBase):
    perfil_origen = models.ForeignKey('sga.PerfilUsuario', related_name='+', verbose_name=u'Perfil Origen', on_delete=models.CASCADE)
    perfil_destino = models.ForeignKey('sga.PerfilUsuario', related_name='+', verbose_name=u'Perfil Destino', on_delete=models.CASCADE)
    periodo = models.ForeignKey('sga.Periodo', blank=True, null=True, related_name='+', verbose_name=u'Periodo', on_delete=models.CASCADE)
    user_token = models.ForeignKey(UserToken, verbose_name=u'Token', on_delete=models.CASCADE)
    codigo = models.CharField(default='', max_length=250, verbose_name=u'Código', db_index=True)
    isActive = models.BooleanField(default=True, verbose_name=u"Activo?")
    app = models.IntegerField(choices=APP_LABEL, default=1, verbose_name=u'Sistema')

    def __str__(self):
        return f"{self.perfil_origen.persona.__str__()} entro como este usuario {self.perfil_destino.persona.usuario.username.__str__()}"

    def isValidoCodigo(self, codigo):
        if not self.user_token.isValidoToken():
            return False
        return self.codigo == codigo

    def inactiveToken(self):
        self.isActive = False
        self.save()

    class Meta:
        verbose_name = u"Token Cambio de Perfil de Usuario"
        verbose_name_plural = u"Tokens de Cambio de Perfil de Usuario"
        ordering = ('perfil_origen', 'perfil_destino',)


class GestionPermisos(ModeloBase):
    # app = models.IntegerField(choices=APP_LABEL, default=1, verbose_name=u'Sistema')
    modulo = models.ForeignKey('sga.Modulo', blank=True, null=True, verbose_name=u'Modulo', on_delete=models.CASCADE)
    permiso = models.ForeignKey(Permission, blank=True, null=True, verbose_name=u'Permiso', on_delete=models.CASCADE)
    descripcion = models.CharField(u"Descripcion", blank=True, null=True, max_length=500)
    foto = models.FileField(upload_to='sys_permissions/%Y/%m/%d', blank=True, null=True, verbose_name=u'Ubicación')

    def __str__(self):
        return f"{self.permiso} [{self.modulo}]"

    class Meta:
        verbose_name = u"Gestión de permiso"
        verbose_name_plural = u"Gestión de permisos"
        ordering = ('modulo',)

    def totalusuariospermiso(self):
        cont = 0
        if self.permiso.group_set.all().exists():
            for x in self.permiso.group_set.all():
                cont += len(x.user_set.all())
                if cont > 100:
                    return '+100'
        return len(self.permiso.user_set.values_list('id', flat=True)) + cont

    def totalgrupospermiso(self):
        return len(self.permiso.group_set.values_list('id', flat=True))


class CategoriaIndice(ModeloBase):
    descripcion = models.CharField(verbose_name=u'descripcion', max_length=200, blank=True, null=True)

    def traerContenido(self):
        return ContenidoIndice.objects.filter(status=True, categoriaindice=self).order_by('descripcion')

    def totalContenido(self):
        return ContenidoIndice.objects.filter(status=True, categoriaindice=self).count()

    def __str__(self):
        return '{}'.format(self.descripcion)

    class Meta:
        verbose_name = u"Categoria Indice"
        verbose_name_plural = u"Categorias de Indices"
        ordering = ('descripcion',)


class ContenidoIndice(ModeloBase):
    descripcion = models.CharField(verbose_name=u'descripcion', max_length=200, blank=True, null=True)
    categoriaindice = models.ForeignKey(CategoriaIndice, blank=True, null=True, verbose_name=u'categoria',
                                        on_delete=models.CASCADE)

    def traerContenidoDocumento(self):
        return ContenidoDocumento.objects.filter(status=True, contenidoindice=self).order_by('titulo')

    def __str__(self):
        return '{} - {}'.format(self.descripcion, self.categoriaindice.descripcion)

    class Meta:
        verbose_name = u"Contenido Indice"
        verbose_name_plural = u"Contenido de Indices"
        ordering = ('descripcion',)


class ContenidoDocumento(ModeloBase):
    titulo = models.CharField(verbose_name=u'titulo', max_length=200, blank=True, null=True)
    texto = models.TextField(verbose_name=u'texto', blank=True, null=True)
    contenidoindice = models.ForeignKey(ContenidoIndice, blank=True, null=True, verbose_name='contenido',
                                        on_delete=models.CASCADE)

    def __str__(self):
        return '{}'.format(self.titulo)

    class Meta:
        verbose_name = u"Contenido Documento"
        verbose_name_plural = u"Contenido de Documentos"


class LogQueryFavoritos(ModeloBase):
    logquery = models.ForeignKey(LogQuery, blank=True, null=True, verbose_name='Log Query', on_delete=models.CASCADE)
    descripcion = models.CharField(verbose_name=u'Descripción', max_length=500, blank=True, null=True)

    def __str__(self):
        return u'%s' % self.logquery

    class Meta:
        verbose_name = u"Log Query Favoritos"
        verbose_name_plural = u"Log Query Favoritos"
        ordering = ('-id',)


TYPE_SECURITY = (
    (1, "Código (Dispositivos)"),
)


class UserAccessSecurity(ModeloBase):
    user = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name=u'Usuario')
    isActive = models.BooleanField(default=True, verbose_name=u"Activo?")

    def __str__(self):
        return f"{self.user} - ({'Activa seguridad' if self.isActive else 'Inactiva seguridad'})"

    class Meta:
        verbose_name = u"Seguridad de acceso del usuario"
        verbose_name_plural = u"Seguridad de acceso de los usuarios"
        ordering = ('user',)
        unique_together = ('user',)

    def delete_cache(self):
        from sga.templatetags.sga_extras import encrypt
        access = cache.get(f"user_access_security_{encrypt(self.user_id)}")
        if access:
            cache.delete(f"user_access_security_{encrypt(self.user_id)}")

    def delete(self, *args, **kwargs):
        self.delete_cache()
        super(UserAccessSecurity, self).delete(*args, **kwargs)

    def save(self, *args, **kwargs):
        self.delete_cache()
        super(UserAccessSecurity, self).save(*args, **kwargs)


class UserAccessSecurityType(ModeloBase):
    user_access = models.ForeignKey(UserAccessSecurity, on_delete=models.CASCADE, verbose_name=u'Usuario acceso')
    type = models.IntegerField(choices=TYPE_SECURITY, default=1, verbose_name=u'Tipo')
    number_devices = models.IntegerField(default=10, null=True, blank=True, verbose_name=u'Número de dispositivos')
    isActive = models.BooleanField(default=False, verbose_name=u"Activo?")

    def __str__(self):
        return f"{self.user_access.user.username} - ({self.get_type_display()})"

    class Meta:
        verbose_name = u"Tipo de seguridad de acceso"
        verbose_name_plural = u"Tipos de seguridad de acceso"
        ordering = ('user_access__user__username', 'type')
        unique_together = ('user_access', 'type')

    def total_devices(self):
        return len(UserAccessSecurityDevice.objects.values("id").filter(user_access_type=self))

    def can_add_device(self):
        number_devices = self.number_devices if self.number_devices else 10
        return self.total_devices() <= number_devices

    def delete_cache(self):
        from sga.templatetags.sga_extras import encrypt
        access = cache.get(f"user_access_security_type_{encrypt(self.user_access.user_id)}")
        if access:
            cache.delete(f"user_access_security_type_{encrypt(self.user_access.user_id)}")

    def delete(self, *args, **kwargs):
        self.delete_cache()
        super(UserAccessSecurityType, self).delete(*args, **kwargs)

    def save(self, *args, **kwargs):
        self.delete_cache()
        super(UserAccessSecurityType, self).save(*args, **kwargs)


class UserAccessSecurityCode(ModeloBase):
    user_access_type = models.ForeignKey(UserAccessSecurityType, verbose_name=u'Usuario Seguridad', on_delete=models.CASCADE)
    date_expires = models.DateTimeField(verbose_name=u'Fecha/Hora de expiración', db_index=True)
    codigo = models.CharField(max_length=10, verbose_name=u'Código', db_index=True)
    isActive = models.BooleanField(default=True, verbose_name=u"Activo?")
    wasValidated = models.BooleanField(default=False, verbose_name=u"Fue validado?")

    def __str__(self):
        return f"{self.user_access_type.__str__()}"

    class Meta:
        verbose_name = u"Código de seguridad de acceso usuario"
        verbose_name_plural = u"Códigos de seguridad de acceso usuario"
        ordering = ('user_access_type', 'date_expires',)

    def isValidoCodigo(self, codigo):
        if self.isActive:
            return self.isValidoTime() and self.codigo == codigo
        return False

    def isValidoTime(self):
        return self.date_expires >= datetime.now()

    def inactiveToken(self):
        self.isActive = False
        self.save()

    def delete_cache(self):
        from sga.templatetags.sga_extras import encrypt
        access = cache.get(f"user_access_security_code_{encrypt(self.user_access_type.user_access.user_id)}")
        if access:
            cache.delete(f"user_access_security_code_{encrypt(self.user_access_type.user_access.user_id)}")

    def delete(self, *args, **kwargs):
        self.delete_cache()
        super(UserAccessSecurityCode, self).delete(*args, **kwargs)

    def save(self, *args, **kwargs):
        self.delete_cache()
        super(UserAccessSecurityCode, self).save(*args, **kwargs)


TYPE_DEVICES = (
    (1, 'Móvil'),
    (2, 'Tableta'),
    (3, 'Táctil adaptable'),
    (4, 'PC'),
    (5, 'Boot'),
    (6, 'Otros'),
)


class UserAccessSecurityDevice(ModeloBase):
    user_access_type = models.ForeignKey(UserAccessSecurityType, verbose_name=u'Usuario Seguridad', on_delete=models.CASCADE)
    ip_public = models.CharField(max_length=100, blank=True, null=True, db_index=True, verbose_name=u"IP Publica")
    type = models.IntegerField(choices=TYPE_DEVICES, db_index=True, verbose_name=u"Tipo")
    browser = models.CharField(max_length=100, blank=True, null=True, db_index=True, verbose_name=u"Navegador")
    browser_version = models.CharField(max_length=50, blank=True, null=True, db_index=True, verbose_name=u"Versión del navegador ")
    os = models.CharField(max_length=100, blank=True, null=True, db_index=True, verbose_name=u"Sistema Operativo")
    os_version = models.CharField(max_length=50, blank=True, null=True, db_index=True, verbose_name=u"Sistema Operativo versión")
    screen_size = models.CharField(max_length=50, blank=True, null=True, db_index=True, verbose_name=u"Tamaño de Pantalla")
    device = models.CharField(max_length=100, blank=True, null=True, db_index=True, verbose_name=u"Dispositivo")
    last_access = models.DateTimeField(verbose_name=u'Último acceso', db_index=True)
    isActive = models.BooleanField(default=True, verbose_name=u"Activo?")

    def __str__(self):
        return f"IP:{self.ip_public} - Navegador: {self.browser}({self.browser_version}) - OS: {self.os}({self.os_version})"

    class Meta:
        verbose_name = u"Dispositivo de acceso usuario"
        verbose_name_plural = u"Dispositivos de acceso usuario"
        ordering = ('user_access_type', 'isActive', 'last_access', 'ip_public', 'browser', 'os', 'type')

    def delete_cache(self):
        from sga.templatetags.sga_extras import encrypt
        if cache.has_key(f"user_access_security_device_{encrypt(self.user_access_type.user_access.user_id)}"):
            cache.delete(f"user_access_security_device_{encrypt(self.user_access_type.user_access.user_id)}")

    def delete(self, *args, **kwargs):
        self.delete_cache()
        super(UserAccessSecurityDevice, self).delete(*args, **kwargs)

    def save(self, *args, **kwargs):
        self.delete_cache()
        super(UserAccessSecurityDevice, self).save(*args, **kwargs)



# LA TABLA SE UTILIZARA PARA TODA TIPO DE CONSULTA PARA LA DINARDAP
# DESDE UN PRINCIPIO SE PENSO PARA LA SENESCYT PERO POSTERIOR VIENIERON NUEVOS SERVICIOS
class HistorialPersonaConsultaTitulo(ModeloBase):
    class Servicios(models.IntegerChoices):
        NINGUNO             = 0, "Ninguno"
        SENESCYT            = 4651, "SENESCYT"
        MINEDUC             = 5169, "MINEDUC"
    persona = models.ForeignKey('sga.Persona', verbose_name=u'Persona', on_delete=models.CASCADE)
    fecha = models.DateField(verbose_name=u"Fecha/Hora consulta")
    obtuvo = models.BooleanField(default=False, verbose_name=u"Obtuvo datos?")
    servicio = models.IntegerField(choices=Servicios.choices, default=Servicios.NINGUNO, blank=True, null=True, verbose_name=u"Servicio")

    def __str__(self):
        return f"Persona:{self.persona.__str__()} - Fecha: {self.fecha.__str__()} - Servicio:{self.get_servicio_display()}"

    class Meta:
        verbose_name = u"Historial de consulta de titulo"
        verbose_name_plural = u"Historial de consultas de titulos"
        ordering = ('persona', 'fecha')


PRIORIDAD_REQUERIMIENTO = (
    (1, 'Baja'),
    (2, 'Media'),
    (3, 'Alta'),
)


ESTADO_REQUERIMIENTO = (
    (1, 'Pendiente'),
    (2, 'En proceso'),
    (3, 'Finalizado'),
)


ESTADO_EVIDENCIA_INFORME_POA = (
    (1, 'Pendiente'),
    (2, 'En proceso'),
    (3, 'Legalizado'),
    (4, 'Remitido POA'),
)

ESTADO_INDICADOR_POA = (
    (1, 'Informe avance de resultados'),#echo
    (2, 'Informe técnico de resultados'),
    (3, 'Reporte general'),
)

class ProcesoSCRUM(ModeloBase):
    direccion = models.ForeignKey('sagest.Departamento', on_delete=models.CASCADE, blank=True, null=True, verbose_name='Dirección Solicitante', related_name='+')
    gestion_recepta = models.ForeignKey('sagest.SeccionDepartamento', on_delete=models.CASCADE, blank=True, null=True, verbose_name='Gestión que recepta el requisito', related_name='+')
    descripcion = models.TextField(default='', verbose_name='Descripción', blank=True, null=True)
    equipos = models.ManyToManyField('bd.EquipoSCRUM', verbose_name='Equipos que participan en este proceso')

    def __str__(self):
        return f'{self.descripcion}'

    def ids_lideres(self):
        lista = []
        for p in self.equipos.all():
            lista.append(p.lider.id)
        return lista

    def lista_integrantes(self):
        lista = []
        for p in self.equipos.all():
            lista.append({'value': p.lider.id, 'text': p.lider.nombre_completo_minus()})
            for ir in p.integrantes.all():
                lista.append({'value': ir.id, 'text': ir.nombre_completo_minus()})
        return lista

    def en_uso(self):
        return self.incidenciascrum_set.filter(status=True).exists()

    class Meta:
        verbose_name = u"Categoria de Incidencias"
        verbose_name_plural = u"Categoria de Incidencias"



class IncidenciaSCRUM(ModeloBase):
    categoria = models.ForeignKey(ProcesoSCRUM, on_delete=models.CASCADE, blank=True, null=True, verbose_name='Categoria')
    requerimiento = models.ForeignKey('automatiza.RequerimientoPlanificacionAutomatiza', on_delete=models.CASCADE, blank=True, null=True, verbose_name='Requerimiento')
    titulo = models.CharField(max_length=5000, blank=True, null=True, default='', verbose_name='Título')
    descripcion = models.TextField(default='', verbose_name='Descripción', blank=True, null=True)
    app = models.IntegerField(choices=APP_LABEL, default=1, verbose_name=u'Sistema')
    prioridad = models.IntegerField(choices=PRIORIDAD_REQUERIMIENTO, default=1, verbose_name=u'Prioridad')
    estado = models.IntegerField(choices=ESTADO_REQUERIMIENTO, default=1, verbose_name=u'Estado')
    asignadoa = models.ForeignKey('sga.Persona', on_delete=models.CASCADE, blank=True, null=True, verbose_name='Asignado a', related_name='+')
    asignadopor = models.ForeignKey('sga.Persona', on_delete=models.CASCADE, blank=True, null=True, verbose_name='Asignado por', related_name='+')
    finicioactividad = models.DateTimeField(default=None, blank=True, null=True, verbose_name='Fecha que inicio la actividad')
    ffinactividad = models.DateTimeField(default=None, blank=True, null=True, verbose_name='Fecha que finalizo la actividad')
    orden = models.IntegerField(default=1, verbose_name='Orden')

    def get_datos_reporte_encuesta_satisfaccion(self):
        from sagest.models import DistributivoPersona

        if self.requerimiento.responsable.es_administrativo():
            tipousuario = 'ADMINISTRATIVO'
        elif self.requerimiento.responsable.es_profesor():
            tipousuario = 'PROFESOR'

        cargo = DistributivoPersona.objects.filter(persona=self.requerimiento.responsable)
        if cargo.exists():
            cargo = cargo[0].denominacionpuesto.descripcion
        else:
            cargo = ''

        return {
            'solicitante': self.requerimiento.responsable.nombre_completo_inverso(),
            'tipousuario': tipousuario,
            'cargo': cargo,
            'cedula': self.requerimiento.responsable.cedula,
            'correo': self.requerimiento.responsable.emailinst if self.requerimiento.responsable.emailinst else self.requerimiento.responsable.email,
            'requerimiento': self.requerimiento.procedimiento,
            'fecha': self.requerimiento.fecha_creacion.strftime('%d/%m/%Y') if self.requerimiento.fecha_creacion else '',
            'asiganadoa': self.asignadoa.nombre_completo_inverso(),
            }

    def respuestas_encuesta(self):
        return self.requerimiento.respuestas_encuesta()

    def incidencias_secundarias(self):
        return self.incidenciasecundariasscrum_set.filter(status=True)

    def comentarios(self):
        return self.comentarioincidenciascrum_set.filter(status=True)

    def incidencias_secundarias_count(self):
        return self.incidenciasecundariasscrum_set.values('id').filter(status=True).count()

    def comentarios_count(self):
        return self.comentarioincidenciascrum_set.values('id').filter(status=True).count()

    def color_estado(self):
        if self.estado == 1:
            return 'texto-blue'
        elif self.estado == 2:
            return 'text-warning'
        else:
            return 'text-success'

    def color_prioridad(self):
        if self.prioridad == 1:
            return 'text-primary'
        elif self.prioridad == 2:
            return 'text-warning'
        else:
            return 'text-danger'

    def lideres_departamento(self):
        from sga.models import Persona
        direccion = self.requerimiento.gestion.departamento
        procesos = ProcesoSCRUM.objects.filter(status=True, direccion=direccion)
        lista = []
        for p in procesos:
            lista.extend(p.ids_lideres())
        equipos = EquipoSCRUM.objects.filter(status=True, esgestor=True)
        for equipo in equipos:
            lista.extend(equipo.integrantes.all().values_list('id', flat=True))
            lista.append(equipo.lider.id)
        lista = list(set(lista))
        return Persona.objects.filter(id__in=lista)

    def tipo_sistema(self, app=''):
        app_label = app if app else self.app
        if app_label == 1:
            return 2
        elif app_label == 2:
            return 1
        elif app_label == 3:
            return 4
        elif app_label == 6:
            return 5
        elif app_label == 7:
            return 9
        else:
            return 2

    def actividad_bitacora(self):
        from sagest.models import BitacoraActividadDiaria
        bitacora = BitacoraActividadDiaria.objects.filter((Q(fecha__date=self.finicioactividad.date(), descripcion=self.descripcion) |
                                                          Q(incidenciascrum_id=self.id)) & Q(status=True, persona=self.asignadoa)).first()
        return bitacora

    def __str__(self):
        return '{}'.format(self.titulo)

    class Meta:
        verbose_name = u"Incidencia"
        verbose_name_plural = u"Incidencia"


class IncidenciaSecundariasSCRUM(ModeloBase):
    incidencia = models.ForeignKey(IncidenciaSCRUM, on_delete=models.CASCADE, blank=True, null=True, verbose_name='Incidencia')
    descripcion = models.TextField(default='', verbose_name='Descripción', blank=True, null=True)
    asignadoa = models.ForeignKey('sga.Persona', on_delete=models.CASCADE, blank=True, null=True, verbose_name='Asignado a', related_name='+')
    prioridad = models.IntegerField(choices=PRIORIDAD_REQUERIMIENTO, default=1, verbose_name=u'Prioridad')
    estado = models.IntegerField(choices=ESTADO_REQUERIMIENTO, default=1, verbose_name=u'Estado')
    finicioactividad = models.DateTimeField(default=None, blank=True, null=True, verbose_name='Fecha que inicio la actividad')
    ffinactividad = models.DateTimeField(default=None, blank=True, null=True, verbose_name='Fecha que finalizo la actividad')

    def __str__(self):
        return '{}, {}'.format(self.incidencia.__str__(), self.descripcion)

    class Meta:
        verbose_name = u"Incidencia Secundaria"
        verbose_name_plural = u"Incidencia Secundarias"


class ComentarioIncidenciaSCRUM(ModeloBase):
    incidencia = models.ForeignKey(IncidenciaSCRUM, on_delete=models.CASCADE, blank=True, null=True, verbose_name='Incidencia')
    observacion = models.TextField(default='', verbose_name='Observación', blank=True, null=True)
    archivo = models.FileField(upload_to='archivo_adjunto/', blank=True, null=True, verbose_name=u'Adjunto')

    def __str__(self):
        return '{}, {}'.format(self.incidencia.__str__(), self.observacion)

    def tipo_archivo(self):
        namefile = self.archivo.name
        ext = namefile[namefile.rfind("."):].lower()
        if ext in ['.pdf']:
            return {'formato': 'pdf', 'icon': 'fa-file-pdf-o text-danger'}
        elif ext in ['.png', '.jpg', '.jpeg', '.svg']:
            return {'formato': 'img', 'icon': 'fa-file-image texto-blue'}
        elif ext in ['.xls', '.xlsx', '.xlsx', '.xlsb']:
            return {'formato': 'excel', 'icon': 'fa-file-excel-o text-success'}
        elif ext in ['.docx', '.doc']:
            return {'formato': 'word', 'icon': 'fa-file-word-o text-primary'}
        else:
            return {'formato': 'otro', 'icon': 'fa-file text-secondary'}

    class Meta:
        verbose_name = u"Comentario Incidencia"
        verbose_name_plural = u"Comentario Incidencia"


class EvidenciaInformePoa(ModeloBase):
    descripcion = models.TextField(default='', verbose_name='Descripción', blank=True, null=True)
    archivo = models.FileField(upload_to='evidenciapoa/%Y/', blank=True, null=True, verbose_name=u'Archivo')
    fechadesde = models.DateField(default=None, blank=True, null=True, verbose_name='Fecha desde')
    fechahasta = models.DateField(default=None, blank=True, null=True, verbose_name='Fecha hasta')
    persona = models.ForeignKey('sga.Persona', on_delete=models.CASCADE, blank=True, null=True, verbose_name='Persona')
    estado = models.IntegerField(choices=ESTADO_EVIDENCIA_INFORME_POA, default=1, verbose_name=u'Estado')
    evidenciaref = models.ForeignKey('self', blank=True, null=True, verbose_name=u'Evidencia', on_delete=models.CASCADE)
    indicador = models.IntegerField(blank=True, null=True, choices=ESTADO_INDICADOR_POA, verbose_name=u'Indicador')

    def __str__(self):
        return '{}'.format(self.descripcion)

    def get_responsables(self):
        return self.responsablefirmaevidenciapoa_set.filter(status=True).order_by('orden')

    def informe_firmaron_todos(self):
        responsabeles = self.get_responsables()
        return len(responsabeles) == responsabeles.filter(firmo=True).count()

    def color_estado(self):
        if self.estado == 1:
            return 'text-secondary'
        elif self.estado == 2:
            return 'text-primary'
        elif self.estado == 3:
            return 'text-success'
        else:
            return 'text-warning'


class ResponsableFirmaEvidenciaPoA(ModeloBase):
    persona = models.ForeignKey('sga.Persona', on_delete=models.CASCADE, blank=True, null=True, verbose_name='Persona')
    evidenciainforme = models.ForeignKey(EvidenciaInformePoa, on_delete=models.CASCADE, blank=True, null=True, verbose_name='Evidencia de informe')
    cargo = models.ForeignKey('sagest.DenominacionPuesto', null=True, blank=True, on_delete=models.CASCADE, verbose_name=u"Cargo del que firma el informe ")
    firmo = models.BooleanField(default=False, verbose_name=u'¿Firmo?')
    orden = models.IntegerField(default=0, verbose_name=u'Orden de firmar el informe')

    def __str__(self):
        return '{}'.format(self.persona)


class ProcesoOpcionSistema(ModeloBase):
    descripcion = models.TextField(default='', verbose_name='descripcion', blank=True, null=True)

    def __str__(self):
        return '{}'.format(self.descripcion)

    def en_uso(self):
        return True if self.inventarioopcionsistema_set.values('id').filter(status=True) else False

    class Meta:
        verbose_name = u"Proceso de opción del Sistema "
        verbose_name_plural = u"Procesos de opción del Sistema"

class TipoOpcionSistema(ModeloBase):
    descripcion = models.TextField(default='', verbose_name='descripcion', blank=True, null=True)

    def __str__(self):
        return '{}'.format(self.descripcion)

    def en_uso(self):
        return True if self.inventarioopcionsistema_set.values('id').filter(status=True) else False

    class Meta:
        verbose_name = u"Tipo de opción del Sistema "
        verbose_name_plural = u"Tipos de opción del Sistema"

class InventarioOpcionSistema(ModeloBase):
    modulo = models.ForeignKey('sga.Modulo', on_delete=models.CASCADE, blank=True, null=True, verbose_name=u'Modulo')
    nombre = models.TextField(default='', verbose_name='Nombre', blank=True, null=True)
    url = models.TextField(default='', verbose_name='URL', blank=True, null=True)
    descripcion = models.TextField(default='', verbose_name='Descripción', blank=True, null=True)
    archivo = models.FileField(upload_to='archivoopcion/%Y/%m/%d', blank=True, null=True, verbose_name=u'Archivo')
    proceso = models.ForeignKey(ProcesoOpcionSistema, on_delete=models.CASCADE, blank=True, null=True, verbose_name=u'Proceso')
    tipo = models.ForeignKey(TipoOpcionSistema, on_delete=models.CASCADE, blank=True, null=True, verbose_name=u'Tipo')
    preguntauxplora = models.TextField(default='', verbose_name='Pregunta Uxplora', blank=True, null=True)
    activouxplora = models.BooleanField(default=False, verbose_name=u'¿Activo para prueba de mouse?')
    posicion_x = models.FloatField(default=0, verbose_name='Posición X de la opcion en la imagen uxplora')
    posicion_y = models.FloatField(default=0, verbose_name='Posición Y de la opcion en la imagen uxplora')
    ratio = models.IntegerField(default=0, verbose_name='Ratio de la posicion con respecto a x,y de la opcion en la imagen uxplora')


    def __str__(self):
        return '{} - {}'.format(self.nombre, self.modulo.__str__())

    class Meta:
        verbose_name = u"Inventario de opcion del Sistema "
        verbose_name_plural = u"Inventario de opciones del Sistema"

    def evaluado_uxplora(self, userid, identificacion):
        from django.db import transaction, connections
        try:
            conexion = connections['uxplora']
            cursor = conexion.cursor()
            sql = """ SELECT idopcion FROM mousetrackapp_logmousetrack WHERE status = '%s' and userid = '%s' and identificacion = '%s' and idopcion = %s; """ \
                  % (True, userid, identificacion, self.id)
            cursor.execute(sql)
            idsvistos = cursor.fetchall()
            conexion.commit()
            cursor.close()
            if self.id in list(idsvistos[0]):
                return True
            return False
        except Exception as e:
            return False

class EquipoSCRUM(ModeloBase):
    nombre = models.CharField(default='',max_length=200, verbose_name='Nombre del equipo')
    descripcion = models.TextField(default='', verbose_name='Descripción del equipo')
    lider = models.ForeignKey('sga.Persona', on_delete=models.CASCADE, verbose_name='Líder del equipo')
    integrantes = models.ManyToManyField('sga.Persona', verbose_name='Integrántes del equipo', related_name='integrantes')
    esgestor = models.BooleanField(default=False, verbose_name='Es gestor de todas las actividades')

    def __str__(self):
        return self.nombre

    def en_uso(self):
        return self.procesoscrum_set.filter(status=True).exists()

    def pendiente(self):
        incidencias = IncidenciaSCRUM.objects.filter(
                                                     Q(asignadoa_id__in=self.integrantes.values_list('id',flat=True).all())
                                                    |Q(asignadoa_id=self.lider.id),
                                                        status=True, estado=1).distinct()
        return incidencias

    def proceso(self):
        incidencias = IncidenciaSCRUM.objects.filter(Q(asignadoa_id__in=self.integrantes.values_list('id',flat=True).all())
                                                    |Q(asignadoa_id=self.lider.id),
                                                     status=True, estado=2).distinct()
        return incidencias

    def finalizado(self):
        incidencias = IncidenciaSCRUM.objects.filter(Q(asignadoa_id__in=self.integrantes.values_list('id',flat=True).all())
                                                        |Q(asignadoa_id=self.lider.id),
                                                         status=True, estado=3).distinct()
        return incidencias

    def total_incidencias(self):
        incidencias = IncidenciaSCRUM.objects.filter(
                                                     Q(asignadoa_id__in=self.integrantes.values_list('id',flat=True).all())
                                                    |Q(asignadoa_id=self.lider.id),
                                                        status=True).distinct()
        return incidencias

    def lista_integrantes(self):
        lista = []
        lista.append({'value': self.lider.id, 'text': self.lider.nombre_completo_minus()})
        for ir in self.integrantes.all():
            lista.append({'value': ir.id, 'text': ir.nombre_completo_minus()})
        return lista
    def actividades_fecha(self,integrante, inicio=None,fin=None):
        incidencias = IncidenciaSCRUM.objects.filter(asignadoa_id=integrante,status=True)
        lista = []
        if inicio and fin:
            incidencias = incidencias.filter(finicioactividad__gte=inicio, finicioactividad__lte=fin)
        pendiente= incidencias.values_list('id').filter(estado=1).count()
        proceso= incidencias.values_list('id').filter(estado=2).count()
        finalizados= incidencias.values_list('id').filter(estado=3).count()
        lista.append({'pendientes': pendiente, 'proceso': proceso,
                      'finalizados': finalizados, 'total': incidencias.count()})

        return lista

    def totales_por_equipos_fecha_plan(self, planificacion, desde, hasta):
        filtro = (Q(asignadoa_id__in=self.integrantes.values_list('id', flat=True).all())
                  & Q( status=True)
                | Q(asignadoa_id=self.lider.id))

        if planificacion:
            filtro = filtro & Q(requerimiento__periodo_id=planificacion)

        if desde and hasta:
            filtro = filtro & Q(finicioactividad__gte=desde, finicioactividad__lte=hasta)

        incidencias = IncidenciaSCRUM.objects.filter(filtro).distinct()
        pendientes = incidencias.values_list('id').filter(estado=1).count()
        proceso = incidencias.values_list('id').filter(estado=2).count()
        finalizadas = incidencias.values_list('id').filter(estado=3).count()

        return {
            "pendiente": pendientes,
            "proceso": proceso,
            "finalizado": finalizadas
        }

    def totales_incidencias_fecha_plan(self, planificacion, desde, hasta):
        filtro = (Q(asignadoa_id__in=self.integrantes.values_list('id',flat=True).all())
                  & Q(status=True)
                  | Q(asignadoa_id=self.lider.id))

        if planificacion:
            filtro = filtro & Q(requerimiento__periodo_id=planificacion)

        if desde and hasta:
            filtro = filtro & Q(finicioactividad__gte=desde, finicioactividad__lte=hasta)

        total = IncidenciaSCRUM.objects.values_list("id").filter(filtro).distinct().count()
        return total


class Meta:
        verbose_name = u"Equipo Scrum"
        verbose_name_plural = u"Equipos Scrum"
        ordering = ['-fecha_creacion', ]

TIPO_EJECUTOR = (
    (0, 'Archivo'),
    (1, 'Código'),
)

class PythonProcess(ModeloBase):
    nombre = models.CharField(max_length=100, verbose_name='Nombre del proceso', blank=True, null=True)
    descripcion = models.TextField(default='', verbose_name='descripcion', blank=True, null=True)
    code = models.TextField(default='', verbose_name='Fragmento de Código', blank=True, null=True)
    tipo = models.IntegerField(choices=TIPO_EJECUTOR, default=1, verbose_name=u'Tipo de ejecutor')
    archivo = models.FileField(upload_to='archivos_py/', blank=True, null=True, verbose_name=u'Archivos de Python a ejecutar')
    anexo = models.FileField(upload_to='anexo_py/', blank=True, null=True, verbose_name=u'Anexos')

    class Meta:
        verbose_name = u"Proceso del sistema"
        verbose_name_plural = u"Procesos del Sistema"

    def __str__(self):
        return '{} {}'.format(self.nombre, self.descripcion)


def get_path_person_files(ePersona, _file):
    documento = ePersona.documento()
    return 'persona/archivos/historicos/{0}/{1}'.format(f'{_file}', f'{documento}')


def upload_historico_persona_migrante_directory_path(instance, filename):
    ahora = datetime.now()
    path = get_path_person_files(instance.persona, 'migrante')
    return '{0}/{1}/{2}/{3}/{4}'.format(f'{path}', f'{str(ahora.year)}', f'{ahora.month:02d}', f'{ahora.day:02d}', filename)


def upload_historico_persona_discapacidad_directory_path(instance, filename):
    ahora = datetime.now()
    path = get_path_person_files(instance.persona, 'discapacidad')
    return '{0}/{1}/{2}/{3}/{4}'.format(f'{path}', f'{str(ahora.year)}', f'{ahora.month:02d}', f'{ahora.day:02d}', filename)


def upload_historico_persona_etnia_directory_path(instance, filename):
    ahora = datetime.now()
    path = get_path_person_files(instance.persona, 'etnia')
    return '{0}/{1}/{2}/{3}/{4}'.format(f'{path}', f'{str(ahora.year)}', f'{ahora.month:02d}', f'{ahora.day:02d}', filename)




class HistoricoPersona(ModeloBase):
    from core.choices.models.sga import MY_ESTADOS_PERMANENCIA, \
        MY_TIPO_CELULAR, MY_GRADO
    from core.choices.models.general import MY_ESTADO_REVISION_ARCHIVO
    persona = models.ForeignKey('sga.Persona', related_name='+', on_delete=models.CASCADE, verbose_name=u"Persona")
    fechahora = models.DateTimeField(null=True, blank=True, verbose_name='Fecha y hora de actualización')
    paisnacimiento = models.ForeignKey('sga.Pais', blank=True, null=True, related_name='+', verbose_name=u'País de nacimiento', on_delete=models.CASCADE)
    provincianacimiento = models.ForeignKey('sga.Provincia', blank=True, null=True, related_name='+', verbose_name=u"Provincia de nacimiento", on_delete=models.CASCADE)
    cantonnacimiento = models.ForeignKey('sga.Canton', blank=True, null=True, related_name='+', verbose_name=u"Canton de nacimiento", on_delete=models.CASCADE)
    parroquianacimiento = models.ForeignKey('sga.Parroquia', blank=True, null=True, related_name='+', verbose_name=u"Parroquia de nacimiento", on_delete=models.CASCADE)
    paisnacionalidad = models.ForeignKey('sga.Pais', blank=True, null=True, related_name='+', verbose_name=u'País de nacionalidad', on_delete=models.CASCADE)
    paisresidencia = models.ForeignKey('sga.Pais', blank=True, null=True, related_name='+', verbose_name=u'País residencia', on_delete=models.CASCADE)
    provinciaresidencia = models.ForeignKey('sga.Provincia', blank=True, null=True, related_name='+', verbose_name=u"Provincia de residencia", on_delete=models.CASCADE)
    cantonresidencia = models.ForeignKey('sga.Canton', blank=True, null=True, related_name='+', verbose_name=u"Canton de residencia", on_delete=models.CASCADE)
    parroquiaresidencia = models.ForeignKey('sga.Parroquia', blank=True, null=True, related_name='+', verbose_name=u"Parroquia de residencia", on_delete=models.CASCADE)
    ciudadelaresidencia = models.CharField(default='', blank=True, null=True, max_length=300, verbose_name=u"Ciudadela de residencia")
    sectorresidencia = models.CharField(default='', blank=True, null=True, max_length=300, verbose_name=u"Sector de residencia")
    ciudadresidencia = models.CharField(default='', max_length=50, verbose_name=u"Ciudad de residencia")
    direccionresidencia = models.CharField(default='', max_length=300, verbose_name=u"Calle principal de residencia")
    direccion2residencia = models.CharField(default='', max_length=300, verbose_name=u"Calle secundaria de residencia")
    num_direccionresidencia = models.CharField(default='', max_length=15, verbose_name=u"Numero de residencia")
    referenciaresidencia = models.CharField(default='', max_length=100, verbose_name=u"Referencia de residencia")
    anioresidencia = models.IntegerField(default=0, null=True, blank=True, verbose_name=u'Años de residencia')
    mesresidencia = models.IntegerField(default=0, null=True, blank=True, verbose_name=u'Meses de residencia')
    fecharetornoresidencia = models.DateField(blank=True, null=True, verbose_name=u'Fecha de retorno')
    archivoresidencia = models.FileField(blank=True, null=True, upload_to=upload_historico_persona_migrante_directory_path, verbose_name=u'Archivo del certificado de migrante retornado')
    estadoarchivoresidenia = models.IntegerField(choices=MY_ESTADO_REVISION_ARCHIVO, blank=True, null=True, verbose_name=u'Estado de revisión del archivo')
    observacionarchivoresidencia = models.TextField(verbose_name=u'Observación de revisión', blank=True, null=True)
    verificadoresidencia = models.BooleanField(default=False, verbose_name=u"Verificado migrante")
    estadopermanenciaresidencia = models.IntegerField(choices=MY_ESTADOS_PERMANENCIA, default=1, blank=True, null=True, verbose_name=u'Estado de Permanencia Pais')
    tipocelular = models.IntegerField(choices=MY_TIPO_CELULAR, default=0, verbose_name=u'Tipo celular')
    telefono = models.CharField(default='', max_length=50, verbose_name=u"Telefono movil")
    telefono_conv = models.CharField(default='', max_length=50, verbose_name=u"Telefono fijo")
    email = models.CharField(default='', max_length=200, verbose_name=u"Correo electronico personal")
    lgtbi = models.BooleanField(default=False, verbose_name=u'GLTBI')
    tienediscapacidad = models.BooleanField(default=False, verbose_name=u"¿Tiene Discapacidad?")
    tipodiscapacidad = models.ForeignKey('sga.Discapacidad', null=True, blank=True, verbose_name=u"Tipo de Discapacidad", on_delete=models.CASCADE)
    porcientodiscapacidad = models.FloatField(default=0, null=True, blank=True, verbose_name=u'% de Discapacidad')
    carnetdiscapacidad = models.CharField(default='', null=True, blank=True, max_length=50, verbose_name=u'Carnet Discapacitado')
    archivodiscapacidad = models.FileField(upload_to=upload_historico_persona_discapacidad_directory_path, blank=True, null=True, verbose_name=u'Archivo Discapacida')
    verificadiscapacidad = models.BooleanField(default=False, verbose_name=u"Verifica Discapacidad?")
    estadoarchivodiscapacidad = models.IntegerField(choices=MY_ESTADO_REVISION_ARCHIVO, blank=True, null=True, verbose_name=u'Estado de revisión del archivo')
    observacionarchivodiscapacidad = models.TextField(verbose_name=u'Observación de revisión archivo discapacidad', blank=True, null=True)
    institucionvalidadiscapacidad = models.ForeignKey('sga.InstitucionBeca', blank=True, null=True, verbose_name=u'Institución valida discapacidad', on_delete=models.CASCADE)
    tienediscapacidadmultiple = models.BooleanField(default=False, verbose_name=u"Tiene Discapacidad multiple?")
    tipodiscapacidadmultiple = models.ManyToManyField('sga.Discapacidad', related_name='+', verbose_name=u"Tipo de Discapacidad multiple")
    archivovaloraciondiscapacidad = models.FileField(upload_to=upload_historico_persona_discapacidad_directory_path, blank=True, null=True, verbose_name=u'Archivo valoracion')
    subtipodiscapacidad = models.ManyToManyField('sga.SubTipoDiscapacidad', related_name='+', verbose_name=u"Sub Tipo de Discapacidad")
    gradodiscapacidad = models.IntegerField(choices=MY_GRADO, default=0, blank=True, null=True, verbose_name=u"Grado de Discapacidad")
    raza = models.ForeignKey('sga.Raza', blank=True, null=True, verbose_name=u'Raza', on_delete=models.CASCADE)
    nacionalidadindigena = models.ForeignKey('sga.NacionalidadIndigena', blank=True, null=True, verbose_name=u'Nacionalidad indigena', on_delete=models.CASCADE)
    archivoraza = models.FileField(upload_to=upload_historico_persona_etnia_directory_path, blank=True, null=True, verbose_name=u'Archivo raza')
    estadoarchivoraza = models.IntegerField(choices=MY_ESTADO_REVISION_ARCHIVO, blank=True, null=True, verbose_name=u'Estado de revisión del archivo')
    observacionarchivoraza = models.TextField(verbose_name=u'Observación de revisión archivo raza', blank=True, null=True)
    verificaraza = models.BooleanField(default=False, verbose_name=u"Verifica Raza?")

    def __str__(self):
        return f"{self.persona.__str__()} - {self.fechahora.__str__()}"

    def save(self, *args, **kwargs):
        super(HistoricoPersona, self).save(*args, **kwargs)

    class Meta:
        verbose_name = u"Historico de persona"
        verbose_name_plural = u"Historicos de personas"
        ordering = ('persona',)
        # unique_together = ('periodo', 'persona',)
