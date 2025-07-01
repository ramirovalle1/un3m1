from __future__ import unicode_literals

import json
from decimal import Decimal
from datetime import datetime
from django.core.cache import cache
from django.db import models
from django.db.models import Q
from django.forms import model_to_dict

from bd.models import CronogramaCoordinacion, UserToken, CronogramaCoordinacionPrematricula
from sagest.models import Departamento
from sga.models import Periodo, Coordinacion, PeriodoMatriculacion, MateriaAsignada, Matricula, Inscripcion, \
    AsignaturaMalla, Persona, Carrera, Materia
from sagest.models import Rubro
from sga.funciones import ModeloBase, remover_caracteres_especiales_unicode


TIPO_MATRICULA_CHOICES = (
    (1, "ADMISION"),
    (2, "PREGRADO"),
    (3, "POSGRADO"),
)


class ArticuloUltimaMatricula(ModeloBase):
    descripcion = models.TextField(default='', verbose_name=u'Descripción')
    activo = models.BooleanField(default=True, verbose_name=u'Activo?')

    def __str__(self):
        return u'%s' % self.descripcion

    def save(self, *args, **kwargs):
        super(ArticuloUltimaMatricula, self).save(*args, **kwargs)

    class Meta:
        verbose_name = u"Artículo de ultima matrícula"
        verbose_name_plural = u"Artículos de ultima matrícula"


class CasoUltimaMatricula(ModeloBase):
    articulo = models.ForeignKey(ArticuloUltimaMatricula, on_delete=models.CASCADE, verbose_name=u'Artículo')
    orden = models.IntegerField(default=0, verbose_name=u'Orden')
    descripcion = models.TextField(default='', verbose_name=u'Descripción')
    activo = models.BooleanField(default=True, verbose_name=u'Activo?')
    validar = models.BooleanField(default=True, verbose_name=u'Validar?')

    def __str__(self):
        return u'%s' % self.descripcion

    def save(self, *args, **kwargs):
        super(CasoUltimaMatricula, self).save(*args, **kwargs)

    class Meta:
        verbose_name = u"Caso de ultima matrícula"
        verbose_name_plural = u"Casos de ultima matrícula"
        ordering = ['articulo', 'orden']
        unique_together = ('articulo', 'descripcion')


class ConfiguracionUltimaMatricula(ModeloBase):
    tipo = models.IntegerField(default=0, choices=TIPO_MATRICULA_CHOICES, verbose_name=u'Tipo')
    nombre = models.CharField(default='', max_length=250, verbose_name=u'Nombre')
    articulo = models.ForeignKey(ArticuloUltimaMatricula, on_delete=models.CASCADE, verbose_name=u'Artículo')
    caso = models.ManyToManyField(CasoUltimaMatricula, verbose_name=u'Caso')
    activo = models.BooleanField(default=True, verbose_name=u'Activo?')

    def __str__(self):
        return u'%s - %s' % (self.tipo, self.nombre)

    def casos(self):
        return self.caso.all()

    def save(self, *args, **kwargs):
        super(ConfiguracionUltimaMatricula, self).save(*args, **kwargs)

    class Meta:
        verbose_name = u"Configuración de ultima matrícula"
        verbose_name_plural = u"Configuraciones de ultima matrícula"
        ordering = ['tipo']
        unique_together = ('tipo', 'nombre')


class PeriodoMatricula(ModeloBase):
    periodo = models.ForeignKey(Periodo, verbose_name=u'Periodo académico', on_delete=models.CASCADE)
    activo = models.BooleanField(default=True, verbose_name=u'Activo (matriculacionactiva)')
    tipo = models.IntegerField(default=0, choices=TIPO_MATRICULA_CHOICES, verbose_name=u'Tipo de matricula')
    valida_coordinacion = models.BooleanField(default=False, verbose_name=u'Valida coordinaciones')
    valida_materia_carrera = models.BooleanField(default=False, verbose_name=u'Valida solo materia carrera')
    valida_seccion = models.BooleanField(default=False, verbose_name=u'Valida solo sección')
    valida_cupo_materia = models.BooleanField(default=False, verbose_name=u'Valida cupo de materia')
    valida_horario_materia = models.BooleanField(default=False, verbose_name=u'Valida horario de materia')
    valida_conflicto_horario = models.BooleanField(default=False, verbose_name=u'Valida conflicto de horario de materia')
    valida_deuda = models.BooleanField(default=False, verbose_name=u'Valida deuda')
    bloquea_por_deuda = models.BooleanField(default=False, verbose_name=u'Bloquea por deuda')
    tiporubro = models.ManyToManyField('sagest.TipoOtroRubro', verbose_name=u'Tipos de rubros')
    ver_cupo_materia = models.BooleanField(default=False, verbose_name=u'Ver cupo de materia')
    ver_horario_materia = models.BooleanField(default=False, verbose_name=u'Ver horario de materia')
    ver_deduda = models.BooleanField(default=False, verbose_name=u'Ver detalle de deuda')
    ver_profesor_materia = models.BooleanField(default=True, verbose_name=u'Ver profesor de matería')
    coordinacion = models.ManyToManyField(Coordinacion, verbose_name=u'Coordinaciones')
    valida_cronograma = models.BooleanField(default=False, verbose_name=u'Valida cronograma')
    cronograma = models.ManyToManyField(CronogramaCoordinacion, verbose_name=u'Conogramas')
    cronogramaprematricula = models.ManyToManyField(CronogramaCoordinacionPrematricula, verbose_name=u'Conogramas Pre matricula')
    valida_cronogramaprematricula = models.BooleanField(default=False, verbose_name=u'Valida cronograma prematricula')
    valida_cuotas_rubro = models.BooleanField(default=False, verbose_name=u'Valida número de cuotas en rubro')
    num_cuotas_rubro = models.IntegerField(default=0, null=True, verbose_name=u'Número de cuotas en rubro')
    monto_rubro_cuotas = models.DecimalField(default=0, max_digits=30, decimal_places=2, verbose_name=u'Valor referencial')
    valida_rubro_acta_compromiso = models.BooleanField(default=False, verbose_name=u'Valida acta de compromiso de rubro')
    valida_gratuidad = models.BooleanField(default=True, verbose_name=u'Valida gratuidad')
    porcentaje_perdidad_parcial_gratuidad = models.IntegerField(default=60, null=True, verbose_name=u'Porcentaje de perdidad parcial de la gratuidad')
    porcentaje_perdidad_total_gratuidad = models.IntegerField(default=30, null=True, verbose_name=u'Porcentaje de perdidad total de la gratuidad')
    valida_materias_maxima = models.BooleanField(default=True, verbose_name=u'Valida maximo de materias')
    num_materias_maxima = models.IntegerField(default=10, null=True, verbose_name=u'Número de materias maximas a elegir')
    valida_terminos = models.BooleanField(default=True, verbose_name=u'Valida terminos')
    terminos = models.TextField(default='', null=True, blank=True, verbose_name=u'Terminos')
    valida_login = models.BooleanField(default=False, verbose_name=u'Valida ingreso al login')
    valida_redirect_panel = models.BooleanField(default=False, verbose_name=u'Valida redireccion del panel')
    ver_eliminar_matricula = models.BooleanField(default=False, verbose_name=u'Ver botón de eliminar matricula')
    puede_agregar_materia = models.BooleanField(default=False, verbose_name=u'Valida puede agregar materias')
    seguridad_remove_materia = models.BooleanField(default=False, verbose_name=u'Valida seguridad al remover materias')
    puede_agregar_materia_rubro_pagados = models.BooleanField(default=False, verbose_name=u'Valida puede agregar materias con rubro pagados')
    puede_eliminar_materia_rubro_pagados = models.BooleanField(default=False, verbose_name=u'Valida puede eliminar materias con rubro pagados')
    puede_agregar_materia_rubro_diferidos = models.BooleanField(default=False, verbose_name=u'Valida puede agregar materias con rubro diferidos')
    puede_eliminar_materia_rubro_diferidos = models.BooleanField(default=False, verbose_name=u'Valida puede eliminar materias con rubro diferidos')
    valida_envio_mail = models.BooleanField(default=False, verbose_name=u'Valida envio de email')
    num_matriculas = models.IntegerField(default=3, null=True, verbose_name=u'Valida número de matrículas')
    num_materias_maxima_ultima_matricula = models.IntegerField(default=3, null=True, verbose_name=u'Número de materias maximas a elegir en última matrícula')
    valida_configuracion_ultima_matricula = models.BooleanField(default=False, verbose_name=u'Valida configuración de última matrícula')
    configuracion_ultima_matricula = models.ForeignKey(ConfiguracionUltimaMatricula, blank=True, null=True, verbose_name=u'Configuracion de última matrícula', on_delete=models.CASCADE)
    valida_proceos_matricula_especial = models.BooleanField(default=False, verbose_name=u'Valida matrícula especial')
    proceso_matricula_especial = models.ForeignKey('matricula.ProcesoMatriculaEspecial', blank=True, null=True, verbose_name=u'Periodo académico',on_delete=models.CASCADE)
    valida_uso_carnet = models.BooleanField(default=False, verbose_name=u'Valida uso de carné estudiantil')
    configuracion_carnet = models.ForeignKey('certi.ConfiguracionCarnet', blank=True, null=True, verbose_name=u'Configuración de carné',on_delete=models.CASCADE)
    fecha_vencimiento_rubro = models.DateField(null=True, blank=True, verbose_name=u'Fecha de vencimiento de rubro')
    mostrar_terminos_examenes = models.BooleanField(default=False, verbose_name=u'Mostrar terminos Examenes')
    terminos_examenes = models.TextField(default='', null=True, blank=True, verbose_name=u'Terminos Examenes')
    terminos_nivelacion = models.TextField(default='', null=True, blank=True, verbose_name=u'Terminos de nivelacion')

    def __str__(self):
        return u'%s (%s)' % (self.periodo, self.get_tipo_display())

    class Meta:
        verbose_name = u"Periodo lectivo - Matricula"
        verbose_name_plural = u"Periodos lectivos - Matriculas"
        ordering = ['periodo__inicio']
        unique_together = ('periodo', 'tipo')

    def esta_matriculaactiva(self):
        return self.periodo.matriculacionactiva

    def esta_periodoactivo(self):
        return self.periodo.status and self.periodo.activo

    def esta_periodoactivomatricula(self):
        return self.esta_matriculaactiva() and self.esta_periodoactivo()

    def tiene_coordincaciones(self):
        return self.coordinacion.all().values("id").exists()

    def coordinaciones(self):
        return self.coordinacion.all()

    def tiene_tiposrubros(self):
        return self.tiporubro.all().values("id").exists()

    def tiposrubros(self):
        return self.tiporubro.all()

    def tiene_cronograma_coordinaciones(self):
        return self.cronograma.all().values("id").exists()

    def cronograma_coordinaciones(self):
        return self.cronograma.all()

    def tiene_cronograma_carreras(self):
        return PeriodoMatriculacion.objects.values('id').filter(periodo=self.periodo).exists()

    def tiene_fecha_cuotas_rubro(self):
        return self.fechacuotarubro_set.values('id').filter(status=True).exists()

    def fecha_cuotas_rubro(self):
        return self.fechacuotarubro_set.filter(status=True).order_by('cuota')

    def tiene_cronograma_coordinacionesprematricula(self):
        return self.cronogramaprematricula.filter(status=True).values('id').exists()

    def cronograma_coordinacionesprematricula(self):
        return self.cronogramaprematricula.filter(status=True)

    def delete_cache(self):
        from sga.templatetags.sga_extras import encrypt
        from sga.funciones import variable_valor
        id_periodo_login_matricula = variable_valor('ID_BLOQUEO_LOGIN_MATRICULA')
        if id_periodo_login_matricula is None:
            id_periodo_login_matricula = 0
        if self.periodo_id == id_periodo_login_matricula:
            if cache.has_key(f"cronograma_matricula_periodo_id_{self.periodo_id}"):
                cache.delete(f"cronograma_matricula_periodo_id_{self.periodo_id}")

    def delete(self, *args, **kwargs):
        self.delete_cache()
        super(PeriodoMatricula, self).delete(*args, **kwargs)

    def save(self, *args, **kwargs):
        self.delete_cache()
        super(PeriodoMatricula, self).save(*args, **kwargs)


class FechaCuotaRubro(ModeloBase):
    periodo = models.ForeignKey(PeriodoMatricula, verbose_name=u'Periodo de matricula',on_delete=models.CASCADE)
    cuota = models.IntegerField(default=0, verbose_name=u'Cuota')
    fecha = models.DateField(verbose_name=u'Fecha')

    def save(self, *args, **kwargs):
        super(FechaCuotaRubro, self).save(*args, **kwargs)

    class Meta:
        verbose_name = u"Fecha cuotas de rubro Periodo lectivo - Matricula"
        verbose_name_plural = u"Fechas de cuotas de rubro del Periodo lectivo - Matriculas"
        ordering = ['cuota']
        unique_together = ('periodo', 'fecha', )


class MateriaAsignadaToken(ModeloBase):
    materia_asignada = models.ForeignKey(MateriaAsignada, verbose_name=u'Usuario',on_delete=models.CASCADE)
    user_token = models.ForeignKey(UserToken, verbose_name=u'Token',on_delete=models.CASCADE)
    codigo = models.CharField(default='', max_length=10, verbose_name=u'Código', db_index=True)
    isActive = models.BooleanField(default=True, verbose_name=u"Activo?")
    num_email = models.IntegerField(default=1, verbose_name=u"Número de veces de envio de correo")

    def __str__(self):
        return f"{self.materia_asignada} - {self.user_token}"

    def isValidoCodigo(self, codigo):
        if not self.user_token.isValidoToken():
            return False
        return self.codigo == codigo

    def inactiveToken(self):
        self.isActive = False
        self.save()

    class Meta:
        verbose_name = u"Token Materia Asignada"
        verbose_name_plural = u"Tokens Materia Asignada"
        ordering = ('materia_asignada', 'user_token', )
        # unique_together = ('token',)


class MatriculaToken(ModeloBase):
    matricula = models.ForeignKey(Matricula, verbose_name=u'Matricula', on_delete=models.CASCADE)
    user_token = models.ForeignKey(UserToken, verbose_name=u'Token', on_delete=models.CASCADE)
    codigo = models.CharField(default='', max_length=10, verbose_name=u'Código', db_index=True)
    isActive = models.BooleanField(default=True, verbose_name=u"Activo?")
    num_email = models.IntegerField(default=1, verbose_name=u"Número de veces de envio de correo")

    def __str__(self):
        return f"{self.matricula} - {self.user_token}"

    def isValidoCodigo(self, codigo):
        if not self.user_token.isValidoToken():
            return False
        return self.codigo == codigo

    def inactiveToken(self):
        self.isActive = False
        self.save()

    class Meta:
        verbose_name = u"Token Matricula"
        verbose_name_plural = u"Tokens Matricula"
        ordering = ('matricula', 'user_token', )
        # unique_together = ('token',)


ACCION_ESTADO_MATRICULA_ESPECIAL_CHOICES = (
    (1, "SOLICITADO"),
    (2, "RECHAZADO"),
    (3, "MATRICULADO"),
    (4, "EN_REVISION"),
    (5, "EN_TRAMITE"),
    (6, "CANCELAR"),
    (7, "NOTIFICADO"),
)


class EstadoMatriculaEspecial(ModeloBase):
    nombre = models.CharField(default='', max_length=100, verbose_name=u'Nombre')
    color = models.CharField(default='', max_length=100, verbose_name=u'Color')
    editable = models.BooleanField(default=False, verbose_name=u'Editable?')
    accion = models.IntegerField(choices=ACCION_ESTADO_MATRICULA_ESPECIAL_CHOICES, default=1, verbose_name=u"Acción")

    def __str__(self):
        return f"{self.nombre}"

    def es_editable(self):
        return self.editable

    def en_uso(self):
        if ConfigProcesoMatriculaEspecial.objects.values("id").filter(Q(estado_ok=self) | Q(estado_nok=self)).exists():
            return True
        elif SolicitudMatriculaEspecial.objects.values("id").filter(estado=self).exists():
            return  True
        return False

    def save(self, *args, **kwargs):
        estados = EstadoMatriculaEspecial.objects.values("id").all()
        if not self.nombre:
            raise NameError(u"Ingrese un nombre")
        if not self.color:
            raise NameError(u"Ingrese un nombre de clase de color")
        self.nombre = self.nombre.strip()
        self.color = self.color.strip()
        if self.id:
            if estados.filter(accion=self.accion).exclude(pk=self.id).exists():
                raise NameError(u"Acción ya existe")
        else:
            if estados.filter(accion=self.accion).exists():
                raise NameError(u"Acción ya existe")
        super(EstadoMatriculaEspecial, self).save(*args, **kwargs)

    class Meta:
        verbose_name = u"Estado de matricula especial"
        verbose_name_plural = u"Estados de matricula especial"
        ordering = ('nombre', )
        unique_together = ('accion',)


MOTIVO_MATRICULA_CHOICES = (
    (1, "CASO FORTUITO"),
    (2, "FUERZA MAYOR"),
)


class MotivoMatriculaEspecial(ModeloBase):
    nombre = models.CharField(default='', max_length=500, verbose_name=u'Nombre')
    detalle = models.TextField(default='', blank=True, null=True, verbose_name=u'Detalle')
    tipo = models.IntegerField(choices=MOTIVO_MATRICULA_CHOICES, default=1, verbose_name=u"Tipo")
    activo = models.BooleanField(default=True, verbose_name=u'Activo')

    def __str__(self):
        return f"{self.nombre}"

    def en_uso(self):
        if SolicitudMatriculaEspecial.objects.values("id").filter(motivo=self).exists():
            return True
        elif ProcesoMatriculaEspecial.objects.values("id").filter(motivo=self).exists():
            return True
        return False

    def save(self, *args, **kwargs):
        self.nombre = self.nombre.strip()
        super(MotivoMatriculaEspecial, self).save(*args, **kwargs)

    class Meta:
        verbose_name = u"Motivo de matrícula especial"
        verbose_name_plural = u"Motivos de matrículas especiales"
        ordering = ('nombre', )
        unique_together = ('nombre', 'tipo', 'activo', )


class ProcesoMatriculaEspecial(ModeloBase):
    version = models.IntegerField(default=1, verbose_name=u'Versión del proceso')
    sufijo = models.CharField(default='', max_length=25, verbose_name=u'Sufijo')
    nombre = models.CharField(default='', max_length=300, verbose_name=u'Nombre del proceso')
    activo = models.BooleanField(default=True, verbose_name=u'Activo')
    motivo = models.ManyToManyField(MotivoMatriculaEspecial)

    def __str__(self):
        return f"{self.nombre} - V.{self.version} ({'ACTIVO' if self.activo else 'INACTIVO'})"

    def motivos(self):
        return self.motivo.all()

    def tiene_motivos(self):
        return self.motivos().exists()

    def tiene_configurado(self):
        return self.configprocesomatriculaespecial_set.filter(status=True).exists()

    def configuraciones_proceso(self):
        return self.configprocesomatriculaespecial_set.filter(status=True).order_by('orden')

    def en_uso(self):
        if SolicitudMatriculaEspecial.objects.values("id").filter(proceso=self).exists():
            return True
        elif ConfigProcesoMatriculaEspecial.objects.values("id").filter(proceso=self).exists():
            return True
        return False

    def save(self, *args, **kwargs):
        if not self.version:
            raise NameError(u"Versión debe ser mayor a cero")
        if not self.sufijo:
            raise NameError(u"Ingrese un sufijo")
        if not self.nombre:
            raise NameError(u"Nombre del proceso no debe estar vacio")
        procesos = ProcesoMatriculaEspecial.objects.values("id").filter(status=True)
        if self.id:
            if self.activo and procesos.filter(activo=True).exclude(pk=self.id).exists():
                raise NameError(u"Existe un proceso activo, solo se permite uno activo")
            if procesos.filter(version=self.version).exclude(pk=self.id).exists():
                raise NameError(f"Ya existe versión {self.version}, solo se permite una versión")
        else:
            if self.activo and procesos.filter(activo=True).exists():
                raise NameError(u"Existe un proceso activo, solo se permite uno activo")
            if procesos.filter(version=self.version).exists():
                raise NameError(f"Ya existe versión {self.version}, solo se permite una versión")
        self.sufijo = self.sufijo.strip().upper()
        self.nombre = self.nombre.strip()
        super(ProcesoMatriculaEspecial, self).save(*args, **kwargs)

    class Meta:
        verbose_name = u"Proceso de matrícula especial"
        verbose_name_plural = u"Procesos de matrícula especial"
        ordering = ('version', )
        unique_together = ('version', )


TIPO_ENTIDAD_MATRICULA_ESPECIAL_CHOICES = (
    (1, "DEPARTAMENTO"),
    (2, "COORDINACION"),
    (3, "USUARIO"),
)

TIPO_VALIDACION_MATRICULA_ESPECIAL_CHOICES = (
    (1, "SOLICITUD"),
    (2, "REVISAR"),
    (3, "MATRICULAR"),
    (4, "NOTIFICAR"),
)


ACCION_MATRICULA_ESPECIAL_CHOICES = (
    (1, "SOLICITAR"),
    (2, "REVISAR"),
    (3, "APROBAR"),
    (4, "MATRICULAR"),
    (5, "RECHAZAR"),
    (6, "CANCELAR"),
    (7, "NOTIFICAR"),
)


class ConfigProcesoMatriculaEspecial(ModeloBase):
    proceso = models.ForeignKey(ProcesoMatriculaEspecial, verbose_name=u'Proceso',on_delete=models.CASCADE)
    orden = models.IntegerField(default=1, verbose_name=u'Orden/Paso')
    nombre = models.CharField(default='', max_length=200, verbose_name=u'Nombre de acción')
    tipo_entidad = models.IntegerField(choices=TIPO_ENTIDAD_MATRICULA_ESPECIAL_CHOICES, default=1, verbose_name=u"Tipo departamento")
    tipo_validacion = models.IntegerField(choices=TIPO_VALIDACION_MATRICULA_ESPECIAL_CHOICES, default=1, verbose_name=u"Tipo validación")
    obligar_archivo = models.BooleanField(default=False, verbose_name=u'Obligar archivo')
    obligar_observacion = models.BooleanField(default=False, verbose_name=u'Obligar observación')
    estado_ok = models.ForeignKey(EstadoMatriculaEspecial, related_name='+', verbose_name=u'Estado aceptado',on_delete=models.CASCADE)
    estado_nok = models.ForeignKey(EstadoMatriculaEspecial, related_name='+', verbose_name=u'Estado no aceptado',on_delete=models.CASCADE)
    accion_ok = models.IntegerField(choices=ACCION_MATRICULA_ESPECIAL_CHOICES, default=1, verbose_name=u"Acción aceptada")
    accion_nok = models.IntegerField(choices=ACCION_MATRICULA_ESPECIAL_CHOICES, default=1, verbose_name=u"Acción no aceptada")
    boton_ok_verbose = models.CharField(default='', max_length=100, verbose_name=u'Boton aceptado')
    boton_nok_verbose = models.CharField(default='', max_length=100, verbose_name=u'Boton no aceptado')
    boton_ok_label = models.CharField(default='', max_length=100, verbose_name=u'Boton aceptado color')
    boton_nok_label = models.CharField(default='', max_length=100, verbose_name=u'Boton no aceptado color')

    def __str__(self):
        return f"{self.nombre} - PASO: {self.orden}"

    def es_departamento(self):
        return self.tipo_entidad == 1

    def es_coordinacion(self):
        return self.tipo_entidad == 2

    def es_usuario(self):
        return self.tipo_entidad == 3

    def tiene_responsables(self):
        return ConfigProcesoMatriculaEspecialAsistente.objects.values("id").filter(configuracion=self).exists()

    def responsables(self):
        return ConfigProcesoMatriculaEspecialAsistente.objects.filter(configuracion=self)

    def coordinaciones(self):
        return Coordinacion.objects.filter(pk__in=self.responsables().values_list("coordinacion__id", flat=True).distinct())

    def get_coodinacion(self, solicitud):
        if not ConfigProcesoMatriculaEspecialAsistente.objects.filter(configuracion=self, coordinacion=solicitud.inscripcion.coordinacion).exists():
            return None
        return ConfigProcesoMatriculaEspecialAsistente.objects.filter(configuracion=self, coordinacion=solicitud.inscripcion.coordinacion)[0].coordinacion

    def estados(self):
        return self.estado.all()

    def tiene_estados(self):
        return self.estados().exists()

    def en_uso(self):
        if SolicitudMatriculaEspecial.objects.values("id").filter(proceso=self.proceso).exists():
            return True
        elif ConfigProcesoMatriculaEspecialAsistente.objects.values("id").filter(configuracion=self).exists():
            return True
        return False

    def tiene_historial(self, solicitud):
        return HistorialSolicitudMatriculaEspecial.objects.values("id").filter(solicitud=solicitud, paso=self, status=True).exists()

    def historial(self, solicitud):
        if self.tiene_historial(solicitud):
            return HistorialSolicitudMatriculaEspecial.objects.filter(solicitud=solicitud, paso=self, status=True)
        return None

    def class_active(self, solicitud):
        clase = ""
        active = False
        if not self.tiene_historial(solicitud):
            clase = "disabled"
            active = False
        elif solicitud.estado.id in self.historial(solicitud).values_list('estado_id', flat=True).distinct():
            clase = "active"
            active = True
        return clase, active

    def paso_atras(self, solicitud):
        pasos = ConfigProcesoMatriculaEspecial.objects.filter(proceso=solicitud.proceso, status=True).distinct()
        atras = None
        clase = ""
        active = False
        if pasos.filter(orden=self.orden - 1).exists():
            atras = ConfigProcesoMatriculaEspecial.objects.filter(pk__in=HistorialSolicitudMatriculaEspecial.objects.values_list("paso_id", flat=True).filter(solicitud=solicitud, status=True).distinct(), orden__lte=self.orden - 1).distinct()
            if atras.exists():
                atras = atras.order_by('-orden')[0]
                clase, active = atras.class_active(solicitud)
        return atras, clase

    def paso_siguiente(self, solicitud):
        pasos = ConfigProcesoMatriculaEspecial.objects.filter(proceso=solicitud.proceso, status=True).distinct()
        siguiente = None
        clase = ""
        active = False
        if pasos.filter(orden=self.orden + 1).exists():
            aSiguiente = ConfigProcesoMatriculaEspecial.objects.filter(pk__in=HistorialSolicitudMatriculaEspecial.objects.values_list("paso_id", flat=True).filter(solicitud=solicitud, status=True).distinct(), orden__gte=self.orden + 1).distinct()
            if aSiguiente.exists():
                siguiente = aSiguiente.order_by('orden')[0]
                clase, active = siguiente.class_active(solicitud)
        return siguiente, clase

    def botones_navegacion(self, solicitud):
        aux_pasos = ConfigProcesoMatriculaEspecial.objects.filter(pk__in=HistorialSolicitudMatriculaEspecial.objects.values_list("paso_id", flat=True).filter(solicitud=solicitud, status=True).distinct()).distinct()
        inicio = self.orden == aux_pasos.values_list("orden").order_by('orden').first()[0]
        fin = self.orden == aux_pasos.values_list("orden").order_by('orden').last()[0]
        aPasoAtras = self.paso_atras(solicitud)
        aPasoSiguiente = self.paso_siguiente(solicitud)
        return inicio, fin, aPasoAtras, aPasoSiguiente

    def save(self, *args, **kwargs):
        if not self.orden:
            raise NameError(u"Orden debe ser mayor a cero")
        if not self.nombre:
            raise NameError(u"Nombre no existe")
        self.nombre = self.nombre.strip()
        configuraciones = ConfigProcesoMatriculaEspecial.objects.values("id").filter(status=True, proceso=self.proceso)
        if self.id:
            if configuraciones.filter(orden=self.orden).exclude(pk=self.id).exists():
                raise NameError(u"Orden debe ser unico para el proceso")
        else:
            if configuraciones.filter(orden=self.orden).exists():
                raise NameError(u"Orden debe ser unico para el proceso")

        super(ConfigProcesoMatriculaEspecial, self).save(*args, **kwargs)

    class Meta:
        verbose_name = u"Configuración del proceso de matrícula especial"
        verbose_name_plural = u"Configuraciones del proceso de matrícula especiale"
        ordering = ('proceso', 'orden', )
        unique_together = ('proceso', 'orden', )


class ConfigProcesoMatriculaEspecialAsistente(ModeloBase):
    configuracion = models.ForeignKey(ConfigProcesoMatriculaEspecial, related_name='+', verbose_name=u'Configuración',on_delete=models.CASCADE)
    departamento = models.ForeignKey(Departamento, blank=True, null=True, related_name='+', verbose_name=u'Departamento',on_delete=models.CASCADE)
    coordinacion = models.ForeignKey(Coordinacion, blank=True, null=True, related_name='+', verbose_name=u'Coordinación',on_delete=models.CASCADE)
    responsable = models.ForeignKey(Persona, related_name='+', verbose_name=u'Responsable',on_delete=models.CASCADE)
    carrera = models.ManyToManyField(Carrera, verbose_name=u'Carreras')
    activo = models.BooleanField(default=True, verbose_name=u'Activo')

    def __str__(self):
        return u'%s - %s' % (self.responsable.__str__(), self.configuracion.__str__())

    def carreras(self):
        return self.carrera.all()

    def tiene_carreras(self):
        return self.carreras().exists()

    def en_uso(self):
        return SolicitudMatriculaEspecial.objects.values("id").filter(proceso=self.configuracion.proceso).exists()

    def save(self, *args, **kwargs):
        configuraciones = ConfigProcesoMatriculaEspecialAsistente.objects.filter(configuracion=self.configuracion)
        if self.id:
            if self.configuracion.tipo_entidad == 1:
                if configuraciones.filter(departamento=self.departamento).exclude(pk=self.id).exists():
                    raise NameError(u"Existe departamento registrado")
        else:
            if self.configuracion.tipo_entidad == 1:
                if configuraciones.filter(departamento=self.departamento).exists():
                    raise NameError(u"Existe departamento registrado")
        super(ConfigProcesoMatriculaEspecialAsistente, self).save(*args, **kwargs)

    class Meta:
        verbose_name = u"Responsable de la facultad del proceso matricula especial"
        verbose_name_plural = u"Responsables de la facultad del proceso matricula especial"
        ordering = ('configuracion', )


class SolicitudMatriculaEspecial(ModeloBase):
    codigo = models.CharField(default='', max_length=100, verbose_name=u'Código')
    secuencia = models.IntegerField(default=0, verbose_name=u'Secuencia')
    proceso = models.ForeignKey(ProcesoMatriculaEspecial, related_name='+', verbose_name=u'Proceso de matricula especial',on_delete=models.CASCADE)
    paso = models.ForeignKey(ConfigProcesoMatriculaEspecial, related_name='+', blank=True, null=True, verbose_name=u"Paso",on_delete=models.CASCADE)
    inscripcion = models.ForeignKey(Inscripcion, related_name='+', verbose_name=u"Inscripcion",on_delete=models.CASCADE)
    periodo = models.ForeignKey(Periodo, related_name='+', verbose_name=u"Periodo académico",on_delete=models.CASCADE)
    descripcion = models.TextField(default='', verbose_name=u'Descripción')
    motivo = models.ForeignKey(MotivoMatriculaEspecial, verbose_name=u"Motivo", on_delete=models.CASCADE)
    archivo = models.FileField(upload_to='solicitud/matricula/especial/%Y/%m/%d', blank=True, null=True, verbose_name=u'Archivo del solicitante')
    informe = models.FileField(upload_to='informe/matricula/especial/%Y/%m/%d', blank=True, null=True, verbose_name=u'Informe de aprobación')
    fecha = models.DateField(verbose_name=u'Fecha de solicitud')
    hora = models.TimeField(verbose_name=u'Hora de solicitud')
    estado = models.ForeignKey(EstadoMatriculaEspecial, related_name='+', verbose_name=u"Estado",on_delete=models.CASCADE)
    matricula = models.ForeignKey(Matricula, null=True, blank=True, on_delete=models.SET_NULL, related_name='+', verbose_name=u'Matricula')

    def __str__(self):
        return f"SOLICITUD {self.inscripcion.persona.__str__()} - {self.periodo.__str__()} - {self.motivo.get_tipo_display()}"

    def detalle_asignaturas(self):
        return SolicitudMatriculaEspecialAsignatura.objects.filter(solicitud=self)

    def tiene_detalle_asignaturas(self):
        return self.detalle_asignaturas().exists()

    def total_detalle_asignaturas(self):
        if not self.tiene_detalle_asignaturas():
            return 0
        return self.detalle_asignaturas().count()

    def historial(self):
        if not HistorialSolicitudMatriculaEspecial.objects.values("id").filter(solicitud=self).exists():
            return None
        return HistorialSolicitudMatriculaEspecial.objects.filter(solicitud=self)

    def tiene_historial(self):
        if not self.historial():
            return False
        return self.historial().values("id").exists()

    class Meta:
        verbose_name = u"Solicitud de matrícula especial"
        verbose_name_plural = u"Solicitudes de matrículas especiales"
        ordering = ('periodo', 'fecha', 'hora', 'inscripcion', )
        # unique_together = ('periodo', 'inscripcion', )


ESTADO_ASIGNACION_MATRICULA_ESPECIAL_CHOICES = (
    (1, "SOLICITADO"),
    (2, "ASIGNADA"),
    (3, "NO ASIGNADA"),
    (4, "RECHAZADO"),
    (5, "ELIMINADA"),
    (6, "EN REVISIÓN"),
)


class SolicitudMatriculaEspecialAsignatura(ModeloBase):
    solicitud = models.ForeignKey(SolicitudMatriculaEspecial, related_name='+', verbose_name=u"Solicitud Matrícula",on_delete=models.CASCADE)
    asignatura = models.ForeignKey(AsignaturaMalla, related_name='+', verbose_name=u"Asignatura",on_delete=models.CASCADE)
    materiaasignada = models.ForeignKey(MateriaAsignada, blank=True, null=True, related_name='+', on_delete=models.SET_NULL, verbose_name=u"MateriaAsignada")
    estado = models.IntegerField(choices=ESTADO_ASIGNACION_MATRICULA_ESPECIAL_CHOICES, default=1, verbose_name=u"Estado")
    observacion = models.TextField(default='', blank=True, null=True, verbose_name=u'Observación')

    def __str__(self):
        return f"SOLICITUD: {self.solicitud.__str__()} - Asignatura: {self.asignatura.__str__()} - ({self.get_estado_display()})"

    class Meta:
        verbose_name = u"Solicitud asignatura de matrícula especial"
        verbose_name_plural = u"Solicitud asignaturas de matrícula especial"
        ordering = ('solicitud', 'asignatura', )
        unique_together = ('solicitud', 'asignatura', )


class HistorialSolicitudMatriculaEspecial(ModeloBase):
    solicitud = models.ForeignKey(SolicitudMatriculaEspecial, related_name='+', verbose_name=u"Solicitud Matrícula",on_delete=models.CASCADE)
    paso = models.ForeignKey(ConfigProcesoMatriculaEspecial, related_name='+', blank=True, null=True, verbose_name=u"Paso",on_delete=models.CASCADE)
    fecha = models.DateField(verbose_name=u'Fecha de solicitud')
    hora = models.TimeField(verbose_name=u'Hora de solicitud')
    estado = models.ForeignKey(EstadoMatriculaEspecial, related_name='+', verbose_name=u"Estado",on_delete=models.CASCADE)
    departamento = models.ForeignKey(Departamento, blank=True, null=True, related_name='+', verbose_name=u'Departamento',on_delete=models.CASCADE)
    coordinacion = models.ForeignKey(Coordinacion, blank=True, null=True, related_name='+', verbose_name=u'Coordinación',on_delete=models.CASCADE)
    observacion = models.TextField(default='', verbose_name=u'Observación', blank=True)
    responsable = models.ForeignKey(Persona, related_name='+', verbose_name=u'Persona responable',on_delete=models.CASCADE)
    archivo = models.FileField(upload_to='historial/matricula/especial/%Y/%m/%d', blank=True, null=True, verbose_name=u'Archivo')

    def __str__(self):
        if self.paso.es_departamento():
            return f"SOLICITUD {self.solicitud.__str__()} - {self.departamento.__str__()} - {self.estado.__str__()}"
        elif self.paso.es_coordinacion():
            return f"SOLICITUD {self.solicitud.__str__()} - {self.coordinacion.__str__()} - {self.estado.__str__()}"
        else:
            return f"SOLICITUD {self.solicitud.__str__()} - {self.estado.__str__()}"

    def fecha_hora(self):
        return datetime.combine(self.fecha, self.hora)

    class Meta:
        verbose_name = u"Historial de solicitud de matrícula especial"
        verbose_name_plural = u"Historiales de solicitud matrícula especial"
        ordering = ('solicitud', 'paso', )


ACCION_ESTADO_RETIRO_MATRICULA_CHOICES = (
    (1, "SOLICITADO"),
    (2, "RECHAZADO"),
    (3, "RETIRADO"),
    (4, "EN_REVISION"),
    (5, "EN_TRAMITE"),
    (6, "CANCELAR"),
    (7, "NOTIFICADO"),
)


class EstadoRetiroMatricula(ModeloBase):
    nombre = models.CharField(default='', max_length=100, verbose_name=u'Nombre')
    color = models.CharField(default='', max_length=100, verbose_name=u'Color')
    editable = models.BooleanField(default=False, verbose_name=u'Editable?')
    accion = models.IntegerField(choices=ACCION_ESTADO_RETIRO_MATRICULA_CHOICES, default=1, verbose_name=u"Acción")

    def __str__(self):
        return f"{self.nombre}"

    def es_editable(self):
        return self.editable

    def en_uso(self):
        if ConfigProcesoRetiroMatricula.objects.values("id").filter(Q(estado_ok=self) | Q(estado_nok=self)).exists():
            return True
        elif SolicitudRetiroMatricula.objects.values("id").filter(estado=self).exists():
            return True
        return False

    def save(self, *args, **kwargs):
        estados = EstadoRetiroMatricula.objects.all()
        if not self.nombre:
            raise NameError(u"Ingrese un nombre")
        if not self.color:
            raise NameError(u"Ingrese un nombre de clase de color")
        self.nombre = self.nombre.strip()
        self.color = self.color.strip()
        if self.id:
            if estados.values("id").filter(accion=self.accion).exclude(pk=self.id).exists():
                raise NameError(u"Acción ya existe")
        else:
            if estados.filter(accion=self.accion).exists():
                raise NameError(u"Acción ya existe")
        super(EstadoRetiroMatricula, self).save(*args, **kwargs)

    class Meta:
        verbose_name = u"Estado de retiro de matricula"
        verbose_name_plural = u"Estados de retiro de matricula"
        ordering = ('nombre', )
        unique_together = ('accion',)


class MotivoRetiroMatricula(ModeloBase):
    nombre = models.CharField(default='', max_length=500, verbose_name=u'Nombre')
    detalle = models.TextField(default='', blank=True, null=True, verbose_name=u'Detalle')
    tipo = models.IntegerField(choices=MOTIVO_MATRICULA_CHOICES, default=1, verbose_name=u"Tipo")
    activo = models.BooleanField(default=True, verbose_name=u'Activo')

    def __str__(self):
        return f"{self.nombre}"

    def en_uso(self):
        if SolicitudRetiroMatricula.objects.values("id").filter(motivo=self).exists():
            return True
        elif ProcesoRetiroMatricula.objects.values("id").filter(motivo=self).exists():
            return True
        return False

    def save(self, *args, **kwargs):
        self.nombre = self.nombre.strip()
        super(MotivoRetiroMatricula, self).save(*args, **kwargs)

    class Meta:
        verbose_name = u"Motivo de retiro de matrícula"
        verbose_name_plural = u"Motivos de retiros de matrícula"
        ordering = ('nombre', )
        unique_together = ('nombre', 'tipo', 'activo', )


class ProcesoRetiroMatricula(ModeloBase):
    version = models.IntegerField(default=1, verbose_name=u'Versión del proceso')
    sufijo = models.CharField(default='', max_length=25, verbose_name=u'Sufijo')
    nombre = models.CharField(default='', max_length=300, verbose_name=u'Nombre del proceso')
    activo = models.BooleanField(default=True, verbose_name=u'Activo')
    motivo = models.ManyToManyField(MotivoRetiroMatricula)

    def __str__(self):
        return f"{self.nombre} - V.{self.version} ({'ACTIVO' if self.activo else 'INACTIVO'})"

    def motivos(self):
        return self.motivo.all()

    def tiene_motivos(self):
        return self.motivos().exists()

    def tiene_configurado(self):
        return self.Configprocesoretiromatricula_set.filter(status=True).exists()

    def configuraciones_proceso(self):
        return self.Configprocesoretiromatricula_set.filter(status=True).order_by('orden')

    def en_uso(self):
        if SolicitudRetiroMatricula.objects.values("id").filter(proceso=self).exists():
            return True
        elif ConfigProcesoRetiroMatricula.objects.values("id").filter(proceso=self).exists():
            return True
        return False

    def save(self, *args, **kwargs):
        if not self.version:
            raise NameError(u"Versión debe ser mayor a cero")
        if not self.sufijo:
            raise NameError(u"Ingrese un sufijo")
        if not self.nombre:
            raise NameError(u"Nombre del proceso no debe estar vacio")
        procesos = ProcesoRetiroMatricula.objects.values("id").filter(status=True)
        if self.id:
            if self.activo and procesos.filter(activo=True).exclude(pk=self.id).exists():
                raise NameError(u"Existe un proceso activo, solo se permite uno activo")
            if procesos.filter(version=self.version).exclude(pk=self.id).exists():
                raise NameError(f"Ya existe versión {self.version}, solo se permite una versión")
        else:
            if self.activo and procesos.filter(activo=True).exists():
                raise NameError(u"Existe un proceso activo, solo se permite uno activo")
            if procesos.filter(version=self.version).exists():
                raise NameError(f"Ya existe versión {self.version}, solo se permite una versión")
        self.sufijo = self.sufijo.strip().upper()
        self.nombre = self.nombre.strip()
        super(ProcesoRetiroMatricula, self).save(*args, **kwargs)

    class Meta:
        verbose_name = u"Proceso de retiro de matrícula"
        verbose_name_plural = u"Procesos de retiro de matrícula"
        ordering = ('version', )
        unique_together = ('version', )


TIPO_ENTIDAD_RETIRO_MATRICULA_CHOICES = (
    (1, "DEPARTAMENTO"),
    (2, "COORDINACION"),
    (3, "USUARIO"),
)


TIPO_VALIDACION_RETIRO_MATRICULA_CHOICES = (
    (1, "SOLICITUD"),
    (2, "REVISAR"),
    (3, "VALIDAR"),
    (4, "APROBAR"),
    (5, "RETIRO"),
    (6, "NOTIFICAR"),
)


ACCION_RETIRO_MATRICULA_CHOICES = (
    (1, "SOLICITAR"),
    (2, "REVISAR"),
    (3, "APROBAR"),
    (4, "RETIRAR"),
    (5, "RECHAZAR"),
    (6, "CANCELAR"),
    (7, "NOTIFICAR"),
    (8, "VALIDAR"),
)

TIPO_TIEMPO_ATENCION = (
    (0, "Ninguna"),
    (1, "Horas"),
    (2, "Días"),
    (3, "Meses"),
    (4, "Años"),
)
ESTADOS = (
    (0, "Pendiente"),
    (1, "Aceptado"),
    (2, "Rechazado"),
    (3, "Matriculado"),
)


class ConfigProcesoRetiroMatricula(ModeloBase):
    proceso = models.ForeignKey(ProcesoRetiroMatricula, verbose_name=u'Proceso',on_delete=models.CASCADE)
    orden = models.IntegerField(default=1, verbose_name=u'Orden/Paso')
    nombre = models.CharField(default='', max_length=200, verbose_name=u'Nombre de acción')
    tipo_entidad = models.IntegerField(choices=TIPO_ENTIDAD_RETIRO_MATRICULA_CHOICES, default=1, verbose_name=u"Tipo departamento")
    tipo_validacion = models.IntegerField(choices=TIPO_VALIDACION_RETIRO_MATRICULA_CHOICES, default=1, verbose_name=u"Tipo validación")
    obligar_archivo = models.BooleanField(default=False, verbose_name=u'Obligar archivo')
    obligar_observacion = models.BooleanField(default=False, verbose_name=u'Obligar observación')
    estado_ok = models.ForeignKey(EstadoRetiroMatricula, related_name='+', verbose_name=u'Estado aceptado',on_delete=models.CASCADE)
    estado_nok = models.ForeignKey(EstadoRetiroMatricula, related_name='+', verbose_name=u'Estado no aceptado',on_delete=models.CASCADE)
    accion_ok = models.IntegerField(choices=ACCION_RETIRO_MATRICULA_CHOICES, default=1, verbose_name=u"Acción aceptada")
    accion_nok = models.IntegerField(choices=ACCION_RETIRO_MATRICULA_CHOICES, default=1, verbose_name=u"Acción no aceptada")
    boton_ok_verbose = models.CharField(default='', max_length=100, verbose_name=u'Boton aceptado')
    boton_nok_verbose = models.CharField(default='', max_length=100, verbose_name=u'Boton no aceptado')
    boton_ok_label = models.CharField(default='', max_length=100, verbose_name=u'Boton aceptado color')
    boton_nok_label = models.CharField(default='', max_length=100, verbose_name=u'Boton no aceptado color')
    tiempo_atencion = models.IntegerField(default=0, blank=True, null=True, verbose_name=u"Tiempo de atención")
    tipo_tiempo_atencion = models.IntegerField(default=0, choices=TIPO_TIEMPO_ATENCION, verbose_name=u"Tipo de tiempo de atención")

    def __str__(self):
        return f"{self.nombre} - PASO: {self.orden}"

    # def valida_tiempo_espera(self, fecha):
    #     ahora = datetime.now()
    #     if tipo_vigencia == 1:
    #         return fechahoraregistro <= ahora + timedelta(hours=vigencia)
    #     elif tipo_vigencia == 2:
    #         return fechahoraregistro <= ahora + timedelta(days=vigencia)
    #     elif tipo_vigencia == 3:
    #         return fechahoraregistro <= ahora + relativedelta(months=vigencia)
    #     elif tipo_vigencia == 4:
    #         return fechahoraregistro <= ahora + relativedelta(years=vigencia)
    #     else:
    #         return True

    def es_departamento(self):
        return self.tipo_entidad == 1

    def es_coordinacion(self):
        return self.tipo_entidad == 2

    def es_usuario(self):
        return self.tipo_entidad == 3

    def tiene_responsables(self):
        return ConfigProcesoRetiroMatriculaAsistente.objects.values("id").filter(configuracion=self).exists()

    def responsables(self):
        return ConfigProcesoRetiroMatriculaAsistente.objects.filter(configuracion=self)

    def coordinaciones(self):
        return Coordinacion.objects.filter(pk__in=self.responsables().values_list("coordinacion__id", flat=True).distinct())

    def get_coodinacion(self, solicitud):
        if not ConfigProcesoRetiroMatriculaAsistente.objects.filter(configuracion=self, coordinacion=solicitud.inscripcion.coordinacion).exists():
            return None
        return ConfigProcesoRetiroMatriculaAsistente.objects.filter(configuracion=self, coordinacion=solicitud.inscripcion.coordinacion)[0].coordinacion

    def estados(self):
        return self.estado.all()

    def tiene_estados(self):
        return self.estados().exists()

    def en_uso(self):
        if SolicitudRetiroMatricula.objects.values("id").filter(proceso=self.proceso).exists():
            return True
        elif ConfigProcesoRetiroMatricula.objects.values("id").filter(configuracion=self).exists():
            return True
        return False

    def tiene_historial(self, solicitud):
        return HistorialSolicitudRetiroMatricula.objects.values("id").filter(solicitud=solicitud, paso=self, status=True).exists()

    def historial(self, solicitud):
        if self.tiene_historial(solicitud):
            return HistorialSolicitudRetiroMatricula.objects.filter(solicitud=solicitud, paso=self, status=True)
        return None

    def class_active(self, solicitud):
        clase = ""
        active = False
        if not self.tiene_historial(solicitud):
            clase = "disabled"
            active = False
        elif solicitud.estado.id in self.historial(solicitud).values_list('estado_id', flat=True).distinct():
            clase = "active"
            active = True
        return clase, active

    def paso_atras(self, solicitud):
        pasos = ConfigProcesoRetiroMatricula.objects.filter(proceso=solicitud.proceso, status=True).distinct()
        atras = None
        clase = ""
        active = False
        if pasos.filter(orden=self.orden - 1).exists():
            atras = ConfigProcesoRetiroMatricula.objects.filter(pk__in=HistorialSolicitudMatriculaEspecial.objects.values_list("paso_id", flat=True).filter(solicitud=solicitud, status=True).distinct(), orden__lte=self.orden - 1).distinct()
            if atras.exists():
                atras = atras.order_by('-orden')[0]
                clase, active = atras.class_active(solicitud)
        return atras, clase

    def paso_siguiente(self, solicitud):
        pasos = ConfigProcesoRetiroMatricula.objects.filter(proceso=solicitud.proceso, status=True).distinct()
        siguiente = None
        clase = ""
        active = False
        if pasos.filter(orden=self.orden + 1).exists():
            aSiguiente = ConfigProcesoRetiroMatricula.objects.filter(pk__in=HistorialSolicitudMatriculaEspecial.objects.values_list("paso_id", flat=True).filter(solicitud=solicitud, status=True).distinct(), orden__gte=self.orden + 1).distinct()
            if aSiguiente.exists():
                siguiente = aSiguiente.order_by('orden')[0]
                clase, active = siguiente.class_active(solicitud)
        return siguiente, clase

    def botones_navegacion(self, solicitud):
        aux_pasos = ConfigProcesoRetiroMatricula.objects.filter(pk__in=HistorialSolicitudMatriculaEspecial.objects.values_list("paso_id", flat=True).filter(solicitud=solicitud, status=True).distinct()).distinct()
        inicio = self.orden == aux_pasos.values_list("orden").order_by('orden').first()[0]
        fin = self.orden == aux_pasos.values_list("orden").order_by('orden').last()[0]
        aPasoAtras = self.paso_atras(solicitud)
        aPasoSiguiente = self.paso_siguiente(solicitud)
        return inicio, fin, aPasoAtras, aPasoSiguiente

    def save(self, *args, **kwargs):
        if not self.orden:
            raise NameError(u"Orden debe ser mayor a cero")
        if not self.nombre:
            raise NameError(u"Nombre no existe")
        self.nombre = self.nombre.strip()
        configuraciones = ConfigProcesoRetiroMatricula.objects.values("id").filter(status=True, proceso=self.proceso)
        if self.id:
            if configuraciones.filter(orden=self.orden).exclude(pk=self.id).exists():
                raise NameError(u"Orden debe ser unico para el proceso")
        else:
            if configuraciones.filter(orden=self.orden).exists():
                raise NameError(u"Orden debe ser unico para el proceso")

        super(ConfigProcesoRetiroMatricula, self).save(*args, **kwargs)

    class Meta:
        verbose_name = u"Configuración del proceso de matrícula especial"
        verbose_name_plural = u"Configuraciones del proceso de matrícula especiale"
        ordering = ('proceso', 'orden',)
        unique_together = ('proceso', 'orden',)


class ConfigProcesoRetiroMatriculaAsistente(ModeloBase):
    configuracion = models.ForeignKey(ConfigProcesoRetiroMatricula, related_name='+', verbose_name=u'Configuración',on_delete=models.CASCADE)
    departamento = models.ForeignKey(Departamento, blank=True, null=True, related_name='+', verbose_name=u'Departamento',on_delete=models.CASCADE)
    coordinacion = models.ForeignKey(Coordinacion, blank=True, null=True, related_name='+', verbose_name=u'Coordinación',on_delete=models.CASCADE)
    responsable = models.ForeignKey(Persona, related_name='+', verbose_name=u'Responsable',on_delete=models.CASCADE)
    carrera = models.ManyToManyField(Carrera, verbose_name=u'Carreras')
    activo = models.BooleanField(default=True, verbose_name=u'Activo')

    def __str__(self):
        return u'%s - %s' % (self.responsable.__str__(), self.configuracion.__str__())

    def carreras(self):
        return self.carrera.all()

    def tiene_carreras(self):
        return self.carreras().exists()

    def en_uso(self):
        return SolicitudMatriculaEspecial.objects.values("id").filter(proceso=self.configuracion.proceso).exists()

    def save(self, *args, **kwargs):
        configuraciones = ConfigProcesoRetiroMatriculaAsistente.objects.filter(configuracion=self.configuracion)
        if self.id:
            if self.configuracion.tipo_entidad == 1:
                if configuraciones.filter(departamento=self.departamento).exclude(pk=self.id).exists():
                    raise NameError(u"Existe departamento registrado")
        else:
            if self.configuracion.tipo_entidad == 1:
                if configuraciones.filter(departamento=self.departamento).exists():
                    raise NameError(u"Existe departamento registrado")
        super(ConfigProcesoRetiroMatriculaAsistente, self).save(*args, **kwargs)

    class Meta:
        verbose_name = u"Responsable de la facultad del proceso matricula especial"
        verbose_name_plural = u"Responsables de la facultad del proceso matricula especial"
        ordering = ('configuracion',)


class SolicitudRetiroMatricula(ModeloBase):
    codigo = models.CharField(default='', max_length=100, verbose_name=u'Código')
    secuencia = models.IntegerField(default=0, verbose_name=u'Secuencia')
    proceso = models.ForeignKey(ProcesoRetiroMatricula, related_name='+', verbose_name=u'Proceso de matricula especial',on_delete=models.CASCADE)
    paso = models.ForeignKey(ConfigProcesoRetiroMatricula, related_name='+', blank=True, null=True, verbose_name=u"Paso",on_delete=models.CASCADE)
    inscripcion = models.ForeignKey(Inscripcion, related_name='+', verbose_name=u"Inscripcion", on_delete=models.CASCADE)
    periodo = models.ForeignKey(Periodo, related_name='+', verbose_name=u"Periodo académico",on_delete=models.CASCADE)
    descripcion = models.TextField(default='', verbose_name=u'Descripción')
    motivo = models.ForeignKey(MotivoRetiroMatricula, verbose_name=u"Motivo",on_delete=models.CASCADE)
    archivo = models.FileField(upload_to='solicitud/matricula/retiro/%Y/%m/%d', blank=True, null=True, verbose_name=u'Archivo del solicitante')
    informe = models.FileField(upload_to='informe/matricula/retiro/%Y/%m/%d', blank=True, null=True, verbose_name=u'Informe de aprobación')
    fecha = models.DateField(verbose_name=u'Fecha de solicitud')
    hora = models.TimeField(verbose_name=u'Hora de solicitud')
    estado = models.ForeignKey(EstadoRetiroMatricula, related_name='+', verbose_name=u"Estado",on_delete=models.CASCADE)
    matricula = models.ForeignKey(Matricula, null=True, blank=True, on_delete=models.SET_NULL, related_name='+', verbose_name=u'Matricula')

    def __str__(self):
        return f"SOLICITUD {self.inscripcion.persona.__str__()} - {self.periodo.__str__()} - {self.motivo.get_tipo_display()}"

    def detalle_asignaturas(self):
        return SolicitudRetiroMatriculaAsignatura.objects.filter(solicitud=self)

    def tiene_detalle_asignaturas(self):
        return self.detalle_asignaturas().exists()

    def total_detalle_asignaturas(self):
        if not self.tiene_detalle_asignaturas():
            return 0
        return self.detalle_asignaturas().count()

    def historial(self):
        if not HistorialSolicitudRetiroMatricula.objects.values("id").filter(solicitud=self).exists():
            return None
        return HistorialSolicitudRetiroMatricula.objects.filter(solicitud=self)

    def tiene_historial(self):
        if not self.historial():
            return False
        return self.historial().values("id").exists()

    class Meta:
        verbose_name = u"Solicitud de matrícula especial"
        verbose_name_plural = u"Solicitudes de matrículas especiales"
        ordering = ('periodo', 'fecha', 'hora', 'inscripcion',)
        # unique_together = ('periodo', 'inscripcion', )


ESTADO_ASIGNACION_RETIRO_MATRICULA_CHOICES = (
    (1, "SOLICITADO"),
    (2, "ASIGNADA"),
    (3, "NO ASIGNADA"),
    (4, "RECHAZADO"),
    (5, "ELIMINADA"),
    (6, "EN REVISIÓN"),
)


class SolicitudRetiroMatriculaAsignatura(ModeloBase):
    solicitud = models.ForeignKey(SolicitudRetiroMatricula, related_name='+', verbose_name=u"Solicitud Matrícula",on_delete=models.CASCADE)
    asignatura = models.ForeignKey(AsignaturaMalla, related_name='+', verbose_name=u"Asignatura",on_delete=models.CASCADE)
    materiaasignada = models.ForeignKey(MateriaAsignada, blank=True, null=True, related_name='+',  on_delete=models.SET_NULL, verbose_name=u"MateriaAsignada")
    estado = models.IntegerField(choices=ESTADO_ASIGNACION_RETIRO_MATRICULA_CHOICES, default=1, verbose_name=u"Estado")
    observacion = models.TextField(default='', blank=True, null=True, verbose_name=u'Observación')

    def __str__(self):
        return f"SOLICITUD: {self.solicitud.__str__()} - Asignatura: {self.asignatura.__str__()} - ({self.get_estado_display()})"

    class Meta:
        verbose_name = u"Solicitud asignatura de matrícula"
        verbose_name_plural = u"Solicitud asignaturas de matrícula"
        ordering = ('solicitud', 'asignatura',)
        unique_together = ('solicitud', 'asignatura',)


class HistorialSolicitudRetiroMatricula(ModeloBase):
    solicitud = models.ForeignKey(SolicitudRetiroMatricula, related_name='+', verbose_name=u"Solicitud Matrícula",on_delete=models.CASCADE)
    paso = models.ForeignKey(ConfigProcesoRetiroMatricula, related_name='+', blank=True, null=True, verbose_name=u"Paso",on_delete=models.CASCADE)
    fecha = models.DateField(verbose_name=u'Fecha de solicitud')
    hora = models.TimeField(verbose_name=u'Hora de solicitud')
    estado = models.ForeignKey(EstadoRetiroMatricula, related_name='+', verbose_name=u"Estado",on_delete=models.CASCADE)
    departamento = models.ForeignKey(Departamento, blank=True, null=True, related_name='+', verbose_name=u'Departamento',on_delete=models.CASCADE)
    coordinacion = models.ForeignKey(Coordinacion, blank=True, null=True, related_name='+', verbose_name=u'Coordinación',on_delete=models.CASCADE)
    observacion = models.TextField(default='', verbose_name=u'Observación', blank=True)
    responsable = models.ForeignKey(Persona, related_name='+', verbose_name=u'Persona responable',on_delete=models.CASCADE)
    archivo = models.FileField(upload_to='historial/matricula/retiro/%Y/%m/%d', blank=True, null=True, verbose_name=u'Archivo')

    def __str__(self):
        if self.paso.es_departamento():
            return f"SOLICITUD {self.solicitud.__str__()} - {self.departamento.__str__()} - {self.estado.__str__()}"
        elif self.paso.es_coordinacion():
            return f"SOLICITUD {self.solicitud.__str__()} - {self.coordinacion.__str__()} - {self.estado.__str__()}"
        else:
            return f"SOLICITUD {self.solicitud.__str__()} - {self.estado.__str__()}"

    def fecha_hora(self):
        return datetime.combine(self.fecha, self.hora)

    class Meta:
        verbose_name = u"Historial de solicitud de retiro matrícula"
        verbose_name_plural = u"Historiales de solicitud retiro matrícula"
        ordering = ('solicitud', 'paso', )


class CostoOptimoMalla(ModeloBase):
    periodo = models.ForeignKey('sga.Periodo', verbose_name=u'Periodo', on_delete=models.CASCADE)
    malla = models.ForeignKey('sga.Malla', verbose_name=u'Malla', on_delete=models.CASCADE)
    costooptimo = models.DecimalField(max_digits=30, default=0, decimal_places=2, verbose_name=u'Costo óptimo')
    costomatricula = models.DecimalField(max_digits=30, default=0, decimal_places=2, verbose_name=u'Costo matrícula')
    rangominimo = models.FloatField(default=0, verbose_name=u'Rango Mínimo')
    rangomaximo = models.FloatField(default=0, verbose_name=u'Rango Máximo')
    fechainicio = models.DateField(blank=True, null=True, verbose_name=u'Fecha')
    horas = models.FloatField(default=0, verbose_name=u'Horas totales')
    creditos = models.FloatField(default=0, verbose_name=u'Créditos totales')
    niveles = models.IntegerField(default=0, verbose_name=u'Niveles')

    def __str__(self):
        return f"Periodo académico: {self.periodo.__str__()} - Malla: {self.malla.__str__()}"

    def calculo_costomatricula(self):
        from sga.funciones import null_to_decimal
        costo = (Decimal(self.costooptimo).quantize(Decimal('.01'))) * Decimal(0.5).quantize(Decimal('.01'))
        costo = Decimal(costo).quantize(Decimal('.01')) * Decimal(0.1).quantize(Decimal('.01'))
        return null_to_decimal(costo, 2)

    def crear_editar_calculo_niveles(self, request=None):
        from sga.funciones import log
        eNivelMallas = self.malla.niveles_malla()
        for eNivelMalla in eNivelMallas:
            eCostoOptimoNivelMallas = self.costooptimonivelmalla_set.filter(status=True, nivelmalla=eNivelMalla)
            edit = False
            if eCostoOptimoNivelMallas.values("id").exists():
                eCostoOptimoNivelMalla = eCostoOptimoNivelMallas.first()
                edit = True
            else:
                eCostoOptimoNivelMalla = CostoOptimoNivelMalla(costooptimomalla=self,
                                                               nivelmalla=eNivelMalla)
            if request:
                eCostoOptimoNivelMalla.save(request)
                if edit:
                    log(u'Edito calculo de nivel de cobro de matrícula: %s' % eCostoOptimoNivelMalla, request, "edit")
                else:
                    log(u'Adiciono calculo de nivel de cobro de matrícula: %s' % eCostoOptimoNivelMalla, request, "add")
                eCostoOptimoNivelMalla.crear_editar_calculo_gruposocioeconomico(request)
            else:
                eCostoOptimoNivelMalla.save()
                eCostoOptimoNivelMalla.crear_editar_calculo_gruposocioeconomico()

    def carga_costooptimonivelmalla(self):
        return self.costooptimonivelmalla_set.filter(status=True)

    def save(self, *args, **kwargs):
        self.horas = self.malla.suma_horas_validacion_itinerario()
        self.creditos = self.malla.suma_creditos_validacion_itinerario()
        self.costomatricula = self.calculo_costomatricula()
        self.niveles = self.malla.cantidad_niveles()
        if self.fechainicio != self.malla.inicio:
            self.fechainicio = self.malla.inicio
        super(CostoOptimoMalla, self).save(*args, **kwargs)

    class Meta:
        verbose_name = u"Costo óptimo por malla"
        verbose_name_plural = u"Costos óptimos por malla"
        ordering = ('periodo', 'malla', )
        unique_together = ('periodo', 'malla', )


class CostoOptimoNivelMalla(ModeloBase):
    costooptimomalla = models.ForeignKey(CostoOptimoMalla, verbose_name=u'Costo Óptimo Malla', on_delete=models.CASCADE)
    nivelmalla = models.ForeignKey('sga.NivelMalla', verbose_name=u'Nivel malla', on_delete=models.CASCADE)
    creditos = models.FloatField(default=0, verbose_name=u'Créditos totales')
    horas = models.FloatField(default=0, verbose_name=u'Horas totales')
    vct = models.DecimalField(max_digits=30, default=0, decimal_places=2, verbose_name=u"VCT")

    def __str__(self):
        return f"{self.costooptimomalla} - Nivel malla: {self.nivelmalla.nombre}"

    def calculo_vct(self):
        from sga.funciones import null_to_decimal
        try:
            vct = ((Decimal(self.costooptimomalla.costooptimo).quantize(Decimal('.01'))) / Decimal(self.creditos).quantize(Decimal('.01'))) * (Decimal(0.5).quantize(Decimal('.01')))
        except ZeroDivisionError:
            vct = 0
        return null_to_decimal(vct, 2)

    def crear_editar_calculo_gruposocioeconomico(self, request=None):
        from socioecon.models import GrupoSocioEconomico
        from sga.funciones import log
        eGrupoSocioEconomicos = GrupoSocioEconomico.objects.filter(status=True)
        for eGrupoSocioEconomico in eGrupoSocioEconomicos:
            eCostoOptimoGrupoSocioEconomicos = self.costooptimogruposocioeconomico_set.filter(status=True, gruposocioeconomico=eGrupoSocioEconomico)
            edit = False
            if eCostoOptimoGrupoSocioEconomicos.values("id").exists():
                eCostoOptimoGrupoSocioEconomico = eCostoOptimoGrupoSocioEconomicos.first()
                edit = True
            else:
                eCostoOptimoGrupoSocioEconomico = CostoOptimoGrupoSocioEconomico(costooptimonivelmalla=self,
                                                                                 gruposocioeconomico=eGrupoSocioEconomico)
            if request:
                eCostoOptimoGrupoSocioEconomico.save(request)
                if edit:
                    log(u'Edito calculo de grupo socioeconomico de cobro de matrícula: %s' % eCostoOptimoGrupoSocioEconomico, request, "edit")
                else:
                    log(u'Adiciono calculo de grupo socioeconomico de cobro de matrícula: %s' % eCostoOptimoGrupoSocioEconomico, request, "add")
            else:
                eCostoOptimoGrupoSocioEconomico.save()

    def carga_costooptimogruposocioeconomico(self):
        return self.costooptimogruposocioeconomico_set.filter(status=True)

    def save(self, *args, **kwargs):
        self.horas = self.nivelmalla.total_horas(self.costooptimomalla.malla)
        self.creditos = self.nivelmalla.total_creditos(self.costooptimomalla.malla)
        self.vct = self.calculo_vct()
        super(CostoOptimoNivelMalla, self).save(*args, **kwargs)

    class Meta:
        verbose_name = u"Costo óptimo por nivel de la malla"
        verbose_name_plural = u"Costos óptimos por nivel de la malla"
        ordering = ('costooptimomalla', 'nivelmalla',)
        unique_together = ('costooptimomalla', 'nivelmalla',)


class CostoOptimoGrupoSocioEconomico(ModeloBase):
    costooptimonivelmalla = models.ForeignKey(CostoOptimoNivelMalla, verbose_name=u'Costo Óptimo Nivel Malla', on_delete=models.CASCADE)
    gruposocioeconomico = models.ForeignKey('socioecon.GrupoSocioEconomico', verbose_name=u'Grupo Socioeconomico', on_delete=models.CASCADE)
    porcentaje = models.FloatField(default=0, verbose_name=u'Porcentaje')
    costoarancel = models.DecimalField(max_digits=30, default=0, decimal_places=2, verbose_name=u"Costo arancel")

    def __str__(self):
        return f"{self.costooptimonivelmalla} - Grupo Socioeconomico: {self.gruposocioeconomico.nombre}"

    def calculo_costoarancel(self):
        from sga.funciones import null_to_decimal
        costoarancel = ((Decimal(self.porcentaje).quantize(Decimal('.01'))) * Decimal(self.costooptimonivelmalla.vct).quantize(Decimal('.01')))
        return null_to_decimal(costoarancel, 2)

    def actualizar_porcentaje(self, porcentaje=None):
        if porcentaje is None:
            if self.gruposocioeconomico.pk == 1:
                self.porcentaje = 0.9
            elif self.gruposocioeconomico.pk == 2:
                self.porcentaje = 0.8
            elif self.gruposocioeconomico.pk == 3:
                self.porcentaje = 0.7
            elif self.gruposocioeconomico.pk == 4:
                self.porcentaje = 0.6
            elif self.gruposocioeconomico.pk == 5:
                self.porcentaje = 0.5

    def save(self, *args, **kwargs):
        self.actualizar_porcentaje()
        self.costoarancel = self.calculo_costoarancel()
        super(CostoOptimoGrupoSocioEconomico, self).save(*args, **kwargs)

    class Meta:
        verbose_name = u"Costo óptimo por grupo socioeconomico"
        verbose_name_plural = u"Costos óptimos por grupo socioeconomico"
        ordering = ('costooptimonivelmalla', 'gruposocioeconomico',)
        unique_together = ('costooptimonivelmalla', 'gruposocioeconomico',)


class DetalleRubroMatricula(ModeloBase):
    matricula = models.ForeignKey(Matricula, blank=True, null=True, related_name='+', on_delete=models.CASCADE, verbose_name=u"Matrícula")
    materia = models.ForeignKey(Materia, blank=True, null=True, related_name='+', on_delete=models.SET_NULL, verbose_name=u"Materia")
    # costooptimonivelmalla = models.ForeignKey(CostoOptimoNivelMalla, null=True, blank=True, related_name='+', on_delete=models.SET_NULL, verbose_name=u'Costo Óptimo Nivel Malla')
    # rubro = models.ForeignKey(Rubro, null=True, blank=True, related_name='+', on_delete=models.SET_NULL, verbose_name=u'Rubro')
    costo = models.DecimalField(max_digits=30, default=0, decimal_places=2, verbose_name=u"Costo")
    creditos = models.FloatField(default=0, verbose_name=u'Creditos')
    horas = models.FloatField(default=0, verbose_name=u'Horas')
    activo = models.BooleanField(default=True, verbose_name=u'Activo?')
    fecha = models.DateTimeField(blank=True, null=True)

    def __str__(self):
        eMateriaAsignada = self.get_materiaasignada()
        if eMateriaAsignada:
            return f"MateriaAsignada: {eMateriaAsignada.__str__()} - Costo: {str(self.costo)} - Créditos: {str(self.creditos)}"
        elif self.materia:
            return f"Matricula: {self.matricula.__str__()} / Materia: {self.materia.__str__()} - Costo: {str(self.costo)} - Créditos: {str(self.creditos)}"
        return f"Matricula: {self.matricula.__str__()} - Costo: {str(self.costo)} - Créditos: {str(self.creditos)}"

    def get_materiaasignada(self):
        eMateriaAsignadas = MateriaAsignada.objects.filter(matricula=self.matricula, materia=self.materia)
        if eMateriaAsignadas.values("id").exists():
            return eMateriaAsignadas.first()
        return None

    def get_total(self):
        from sga.funciones import null_to_decimal
        total = ((Decimal(self.costo).quantize(Decimal('.01'))) * Decimal(self.creditos).quantize(Decimal('.01')))
        return null_to_decimal(total, 2)

    def save(self, *args, **kwargs):
        super(DetalleRubroMatricula, self).save(*args, **kwargs)

    class Meta:
        verbose_name = u"Detalle de rubro de matrícula"
        verbose_name_plural = u"Detalles de rubros de matrícula"
        ordering = ('matricula', 'materia',)


class ActualizacionDatos(ModeloBase):
    persona = models.ForeignKey(Persona, related_name='+', on_delete=models.CASCADE, verbose_name=u"Persona")
    periodo = models.ForeignKey(Periodo, related_name='+', on_delete=models.CASCADE, verbose_name=u"Periodo")
    fechahora = models.DateTimeField(null=True, blank=True, verbose_name='Fecha y hora de actualización')
    activo = models.BooleanField(default=False, verbose_name=u'¿Esta activo?')

    def __str__(self):
        return f"{self.persona.__str__()} - {self.periodo.__str__()}"

    def save(self, *args, **kwargs):
        super(ActualizacionDatos, self).save(*args, **kwargs)

    class Meta:
        verbose_name = u"Actualización de datos"
        verbose_name_plural = u"Actualicaciones de datos"
        ordering = ('periodo', 'persona',)
        unique_together = ('periodo', 'persona',)


class SolicitudReservaCupoMateria(ModeloBase):
    periodo = models.ForeignKey(Periodo, on_delete=models.CASCADE, verbose_name=u"Periodo")
    inscripcion = models.ForeignKey(Inscripcion, on_delete=models.CASCADE, verbose_name=u"Inscripcion")
    estado = models.IntegerField(default=0, choices=ESTADOS, verbose_name=u"Estado solicitud reserva")
    periodomatricula = models.ForeignKey(PeriodoMatricula, on_delete=models.CASCADE, verbose_name=u"Periodo de matricula")

    def __str__(self):
        return f"{self.periodo.__str__()} - {self.inscripcion.__str__()} - {self.get_estado_display()}"

    class Meta:
        verbose_name = u"Solicitud de reserva de cupo de materia"
        verbose_name_plural = u"Solicitud de reserva de cupo de materia"


class DetalleSolicitudReservaCupoMateria(ModeloBase):
    from sga.models import Sesion
    solicitud = models.ForeignKey(SolicitudReservaCupoMateria, on_delete=models.CASCADE, verbose_name=u"Solicitud")
    asignaturamalla = models.ForeignKey(AsignaturaMalla, on_delete=models.CASCADE, verbose_name=u"Asignatura malla")
    sesion = models.ForeignKey(Sesion, on_delete=models.CASCADE, verbose_name=u"Asignatura malla")

    def __str__(self):
        return f"{self.solicitud.__str__()} - {self.asignaturamalla.__str__()} - {self.sesion.__str__()}"

    class Meta:
        verbose_name = u"Detalle de asignaturas solicitud de reserva de cupo de materia"
        verbose_name_plural = u"Detalles de asignaturas solicitud de reserva de cupo de materia"


class HistorialAdicionCupoMateria(ModeloBase):
    class EstadoAsignacion(models.IntegerChoices):
        NINGUNO  = 0, u"NINGUNO"
        PENDIENTE  = 1, u"PENDIENTE"
        ASIGNADO  = 2, u"ASIGNADO"

    estado = models.IntegerField(choices=EstadoAsignacion.choices, default=EstadoAsignacion.NINGUNO, verbose_name=u"Estado", blank=True, null=True)
    materia = models.ForeignKey(Materia, on_delete=models.CASCADE, verbose_name=u"Materia")
    cantidad = models.IntegerField(default=0, blank=True, null=True, verbose_name=u"Cantidad cupo")
    asignaturamalla = models.ForeignKey(AsignaturaMalla, on_delete=models.CASCADE, verbose_name=u"Asignatura malla")

    def __str__(self):
        return f"{self.materia.asignaturamalla.asignatura} - {self.cantidad}"

    class Meta:
        verbose_name = u"Historial de adicion de cupo por materia"
        verbose_name_plural = u"Historial de adicion de cupo por materia"

    def cupos_disponibles(self):
        matriculados = self.materia.materiaasignada_set.values('matricula__inscripcion').filter(retiromanual=False, matricula__retiradomatricula=False, matricula__status=True, materia__status=True, materia__asignaturamalla__status=True, materia__asignaturamalla__asignatura__modulo=False, status=True).exclude(materia__asignaturamalla__malla__carrera__coordinacion__id=9).distinct('matricula__inscripcion').count()
        return matriculados - self.materia.cupo


class HistorialMatriculaReserva(ModeloBase):
    detallesolicitud = models.ForeignKey(DetalleSolicitudReservaCupoMateria, on_delete=models.CASCADE, verbose_name=u"Detalle solicitud")
    materiaasignada = models.ForeignKey(MateriaAsignada, on_delete=models.CASCADE, verbose_name=u"Materia asignada")

    def __str__(self):
        return f"{self.materiaasignada.matricula.inscripcion}"

    class Meta:
        verbose_name = u"Historial matrícula reserva"
        verbose_name_plural = u"Historial matrícula reserva"

