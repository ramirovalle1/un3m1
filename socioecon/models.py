# -*- coding: UTF-8 -*-
import sys

from django.core.cache import cache
from django.db import models
from django.db.models.query_utils import Q
from django.db.models import Sum
from sga.funciones import ModeloBase, null_to_numeric
from sga.models import VALOR_SI_NO, Persona

unicode =str

def socioecon_list_classes():
    listclass = []
    current_module = sys.modules[__name__]
    for key in dir(current_module):
        if isinstance(getattr(current_module, key), type):
            try:
                a = eval(key + '.objects')
                listclass.append(key)
            except:
                pass
    return listclass


ESTADO_SOLICITUD = (
    (1, u'PENDIENTE'),
    (2, u'APROBADO'),
    (3, u'RECHAZADO')
)

ACTIVIDADES_RECREACION = (
    (1, u'TV'),
    (2, u'DEPORTE'),
    (3, u'CONVIVENCIA'),
    (4, u'PASEO'),
    (5, u'LECTURA'),
    (6, u'NINGUNO'),
    (7, u'OTROS')
)

REALIZA_TAREAS = (
    (1, u'CASA'),
    (2, u'CUARTO'),
    (3, u'SALA'),
    (4, u'UNIVERSIDAD'),
    (5, u'PATIO'),
    (6, u'AULA'),
    (7, u'BIBLIOTECA'),
    (8, u'OTROS')
)

SALUBRIDAD_VIDA = (
    (1, u'ACEPTABLE'),
    (2, u'NO ACEPTABLE')
)

ESTADO_GENERAL = (
    (1, u'EXCELENTE'),
    (2, u'BUENO'),
    (3, u'REGULAR')
)

TIPO_SERVICIO = (
    (1, u'INTERNET'),
    (2, u'ENERGIA ELÉCTRICA'),
    (3, u'TV PAGADA')
)

ITEM_ADQUIRIR = (
    (1, u'EQUIPO TECNOLÓGICO'),
    (2, u'PLAN DE DATOS PARA SERVICIOS A INTERNET'),
    (3, u'NINGUNO')
)



# QUERY Y CONSULTAS - ESTRATO NIVEL SOCIOECONOMICO
def cantidad_total_gruposocioeconomico(gruposocioe):
    return FichaSocioeconomicaINEC.objects.filter(grupoeconomico=gruposocioe).count()


# GRUPOS SOCIOECONOMICOS POR CARRERAS
def cantidad_gruposocioeconomico_carrera(gruposocioe, carrera):
    return FichaSocioeconomicaINEC.objects.filter(grupoeconomico=gruposocioe, persona__inscripcion__carrera=carrera, persona__usuario__is_active=True).distinct().count()


# GRUPOS SOCIOECONOMICOS POR COORDINACIONES
def cantidad_gruposocioeconomico_coordinacion(gruposocioe, coordinacion):
    return FichaSocioeconomicaINEC.objects.filter(grupoeconomico=gruposocioe, persona__inscripcion__carrera__in=coordinacion.carrera.all(), persona__inscripcion__sede=coordinacion.sede, persona__usuario__is_active=True).distinct().count()


# NIVELES DE ESCOLARIDAD DEL JEFE DE HOGAR POR CARRERAS
def cantidad_nivel_educacion_jefehogar_carrera(nivelesc, carrera):
    return FichaSocioeconomicaINEC.objects.filter(niveljefehogar=nivelesc, persona__inscripcion__carrera=carrera, persona__usuario__is_active=True).distinct().count()


# NIVELES DE ESCOLARIDAD DEL JEFE DE HOGAR POR COORDINACIONES
def cantidad_nivel_educacion_jefehogar_coordinacion(nivelesc, coordinacion):
    return FichaSocioeconomicaINEC.objects.filter(niveljefehogar=nivelesc, persona__inscripcion__carrera__in=coordinacion.carrera.all(), persona__inscripcion__sede=coordinacion.sede, persona__usuario__is_active=True).distinct().count()


# TIPOS DE HOGAR DE ESTUDIANTES POR CARRERAS
def cantidad_tipo_hogar_carrera(th, carrera):
    return FichaSocioeconomicaINEC.objects.filter(tipohogar=th, persona__inscripcion__carrera=carrera, persona__usuario__is_active=True).distinct().count()


# TIPOS DE HOGAR DE ESTUDIANTES POR COORDINACIONES
def cantidad_tipo_hogar_coordinacion(th, coordinacion):
    return FichaSocioeconomicaINEC.objects.filter(tipohogar=th, persona__inscripcion__carrera__in=coordinacion.carrera.all(), persona__inscripcion__sede=coordinacion.sede, persona__usuario__is_active=True).distinct().count()


# DEPENDENCIA ECONOMICA DE ESTUDIANTES POR CARRERAS
def cantidad_sidependientes_carrera(carrera):
    return FichaSocioeconomicaINEC.objects.filter(esdependiente=True, persona__inscripcion__carrera=carrera, persona__usuario__is_active=True).distinct().count()


def cantidad_nodependientes_carrera(carrera):
    return FichaSocioeconomicaINEC.objects.filter(esdependiente=False, persona__inscripcion__carrera=carrera, persona__usuario__is_active=True).distinct().count()


# DEPENDENCIA ECONOMICA DE ESTUDIANTES POR COORDINACIONES
def cantidad_sidependientes_coordinacion(coordinacion):
    return FichaSocioeconomicaINEC.objects.filter(esdependiente=True, persona__inscripcion__carrera__in=coordinacion.carrera.all(), persona__inscripcion__sede=coordinacion.sede, persona__usuario__is_active=True).distinct().count()


def cantidad_nodependientes_coordinacion(coordinacion):
    return FichaSocioeconomicaINEC.objects.filter(esdependiente=False, persona__inscripcion__carrera__in=coordinacion.carrera.all(), persona__inscripcion__sede=coordinacion.sede, persona__usuario__is_active=True).distinct().count()


# CABEZAS DE FAMILIAS ESTUDIANTES POR CARRERAS
def cantidad_sicabezasf_carrera(carrera):
    return FichaSocioeconomicaINEC.objects.filter(escabezafamilia=True, persona__inscripcion__carrera=carrera, persona__usuario__is_active=True).distinct().count()


def cantidad_nocabezasf_carrera(carrera):
    return FichaSocioeconomicaINEC.objects.filter(escabezafamilia=False, persona__inscripcion__carrera=carrera, persona__usuario__is_active=True).distinct().count()


# CABEZAS DE FAMILIAS ESTUDIANTES POR COORDINACIONES
def cantidad_sicabezasf_coordinacion(coordinacion):
    return FichaSocioeconomicaINEC.objects.filter(escabezafamilia=True, persona__inscripcion__carrera__in=coordinacion.carrera.all(), persona__inscripcion__sede=coordinacion.sede, persona__usuario__is_active=True).distinct().count()


def cantidad_nocabezasf_coordinacion(coordinacion):
    return FichaSocioeconomicaINEC.objects.filter(escabezafamilia=False, persona__inscripcion__carrera__in=coordinacion.carrera.all(), persona__inscripcion__sede=coordinacion.sede, persona__usuario__is_active=True).distinct().count()


class FormaTrabajo(ModeloBase):
    nombre = models.CharField(max_length=100)

    class Meta:
        verbose_name = u'Forma de trabajo'
        verbose_name_plural = u'Formas de trabajo'
        unique_together = ('nombre',)

    def __str__(self):
        return self.nombre

    @staticmethod
    def flexbox_query(q, extra=None, limit=25):
        if extra:
            return eval('FormaTrabajo.objects.filter(Q(nombre__icontains="%s")).filter(%s).distinct()[:%s]' % (q, extra, limit))
        return FormaTrabajo.objects.filter(Q(nombre__icontains=q)).distinct()[:limit]

    def flexbox_repr(self):
        return u'%s' % self.nombre

    def flexbox_alias(self):
        return [self.id, self.nombre.upper()]

    def save(self, *args, **kwargs):
        self.nombre = self.nombre.upper()
        super(FormaTrabajo, self).save(*args, **kwargs)


class PersonaSustentaHogar(ModeloBase):
    persona = models.CharField(max_length=200)
    parentesco = models.ForeignKey('sga.ParentescoPersona', on_delete=models.CASCADE)
    formatrabajo = models.ForeignKey(FormaTrabajo, on_delete=models.CASCADE)
    ingresomensual = models.FloatField(default=0.00)

    class Meta:
        verbose_name = u'Persona sustenta Hogar'
        verbose_name_plural = u'Personas sustentan Hogar'

    def __str__(self):
        return self.persona + ' ' + unicode(self.formatrabajo) + ' ($' + str(self.ingresomensual) + ')'

    def save(self, *args, **kwargs):
        self.persona = self.persona.upper()
        super(PersonaSustentaHogar, self).save(*args, **kwargs)


class PersonaCubreGasto(ModeloBase):
    nombre = models.CharField(max_length=100)

    class Meta:
        verbose_name = u'Persona cubre gasto estudiante'
        verbose_name_plural = u'Personas cubren gastos estudiantes'
        unique_together = ('nombre',)

    def __str__(self):
        return self.nombre

    @staticmethod
    def flexbox_query(q, extra=None, limit=25):
        if extra:
            return eval('PersonaCubreGasto.objects.filter(Q(nombre__icontains="%s")).filter(%s).distinct()[:%s]' % (q, extra, limit))
        return PersonaCubreGasto.objects.filter(Q(nombre__icontains=q)).distinct()[:limit]

    def flexbox_repr(self):
        return u'%s' % self.nombre

    def flexbox_alias(self):
        return [self.id, self.nombre.upper()]

    def save(self, *args, **kwargs):
        self.nombre = self.nombre.upper()
        super(PersonaCubreGasto, self).save(*args, **kwargs)


class TipoHogar(ModeloBase):
    nombre = models.CharField(max_length=100)

    class Meta:
        verbose_name = u'Tipo de Hogar'
        verbose_name_plural = u'Tipos de Hogares'
        ordering = ['nombre']
        unique_together = ('nombre',)

    def __str__(self):
        return self.nombre

    @staticmethod
    def flexbox_query(q, extra=None, limit=25):
        if extra:
            return eval('TipoHogar.objects.filter(Q(nombre__icontains="%s")).filter(%s).distinct()[:%s]' % (q, extra, limit))
        return TipoHogar.objects.filter(Q(nombre__icontains=q)).distinct()[:limit]

    def flexbox_repr(self):
        return u'%s' % self.nombre

    def flexbox_alias(self):
        return [self.id, self.nombre.upper()]

    def cantidad_total_estudiantes(self):
        return FichaSocioeconomicaINEC.objects.filter(tipohogar=self).count()

    def save(self, *args, **kwargs):
        self.nombre = self.nombre.upper()
        super(TipoHogar, self).save(*args, **kwargs)


class TipoVivienda(ModeloBase):
    nombre = models.CharField(max_length=100)
    codigo = models.CharField(max_length=4, blank=True, null=True)
    puntaje = models.FloatField(default=0)

    class Meta:
        verbose_name = u'Tipo de vivienda'
        verbose_name_plural = u'Tipos de viviendas'
        unique_together = ('nombre',)

    def __str__(self):
        return '[' + self.codigo + ']' + ' ' + self.nombre if self.codigo else self.nombre

    @staticmethod
    def flexbox_query(q, extra=None, limit=25):
        if extra:
            return eval('TipoVivienda.objects.filter(Q(nombre__icontains="%s")).filter(%s).distinct()[:%s]' % (q, extra, limit))
        return TipoVivienda.objects.filter(Q(nombre__icontains=q)).distinct()[:limit]

    def flexbox_repr(self):
        return u'%s' % self.nombre

    def flexbox_alias(self):
        return [self.id, self.nombre.upper()]

    def save(self, *args, **kwargs):
        self.nombre = self.nombre.upper()
        self.codigo = self.codigo.upper()
        super(TipoVivienda, self).save(*args, **kwargs)


class MaterialPared(ModeloBase):
    nombre = models.CharField(max_length=100)
    codigo = models.CharField(max_length=4, blank=True, null=True)
    puntaje = models.FloatField(default=0)

    class Meta:
        verbose_name = u'Material predomina en Pared'
        verbose_name_plural = u'Materiales predominan en Paredes'
        unique_together = ('nombre',)

    def __str__(self):
        return '[' + self.codigo + ']' + ' ' + self.nombre if self.codigo else self.nombre

    @staticmethod
    def flexbox_query(q, extra=None, limit=25):
        if extra:
            return eval('MaterialPared.objects.filter(Q(nombre__icontains="%s")).filter(%s).distinct()[:%s]' % (q, extra, limit))
        return MaterialPared.objects.filter(Q(nombre__icontains=q)).distinct()[:limit]

    def flexbox_repr(self):
        return u'%s' % self.nombre

    def flexbox_alias(self):
        return [self.id, self.nombre.upper()]

    def save(self, *args, **kwargs):
        self.nombre = self.nombre.upper()
        self.codigo = self.codigo.upper()
        super(MaterialPared, self).save(*args, **kwargs)


class MaterialPiso(ModeloBase):
    nombre = models.CharField(max_length=100)
    codigo = models.CharField(max_length=4, blank=True, null=True)
    puntaje = models.FloatField(default=0)

    class Meta:
        verbose_name = u'Material predomina en piso'
        verbose_name_plural = u'Materiales predominan en pisos'
        unique_together = ('nombre',)

    def __str__(self):
        return '[' + self.codigo + ']' + ' ' + self.nombre if self.codigo else self.nombre

    @staticmethod
    def flexbox_query(q, extra=None, limit=25):
        if extra:
            return eval('MaterialPiso.objects.filter(Q(nombre__icontains="%s")).filter(%s).distinct()[:%s]' % (q, extra, limit))
        return MaterialPiso.objects.filter(Q(nombre__icontains=q)).distinct()[:limit]

    def flexbox_repr(self):
        return u'%s' % self.nombre

    def flexbox_alias(self):
        return [self.id, self.nombre.upper()]

    def save(self, *args, **kwargs):
        self.nombre = self.nombre.upper()
        self.codigo = self.codigo.upper()
        super(MaterialPiso, self).save(*args, **kwargs)


class CantidadBannoDucha(ModeloBase):
    nombre = models.CharField(max_length=100)
    codigo = models.CharField(max_length=4, blank=True, null=True)
    puntaje = models.FloatField(default=0)

    class Meta:
        verbose_name = u'Cantidad baños con ducha'
        verbose_name_plural = u'Cantidad de baños con ducha'
        unique_together = ('nombre',)

    def __str__(self):
        return '[' + self.codigo + ']' + ' ' + self.nombre if self.codigo else self.nombre

    @staticmethod
    def flexbox_query(q, extra=None, limit=25):
        if extra:
            return eval('CantidadBannoDucha.objects.filter(Q(nombre__icontains="%s")).filter(%s).distinct()[:%s]' % (q, extra, limit))
        return CantidadBannoDucha.objects.filter(Q(nombre__icontains=q)).distinct()[:limit]

    def flexbox_repr(self):
        return u'%s' % self.nombre

    def flexbox_alias(self):
        return [self.id, self.nombre.upper()]

    def save(self, *args, **kwargs):
        self.nombre = self.nombre.upper()
        self.codigo = self.codigo.upper()
        super(CantidadBannoDucha, self).save(*args, **kwargs)


class TipoServicioHigienico(ModeloBase):
    nombre = models.CharField(max_length=100)
    codigo = models.CharField(max_length=4, blank=True, null=True)
    puntaje = models.FloatField(default=0)

    class Meta:
        verbose_name = u'Tipo de servicio higienico'
        verbose_name_plural = u'Tipos de servicio higienico'
        unique_together = ('nombre',)

    def __str__(self):
        return '[' + self.codigo + ']' + ' ' + self.nombre if self.codigo else self.nombre

    @staticmethod
    def flexbox_query(q, extra=None, limit=25):
        if extra:
            return eval('TipoServicioHigienico.objects.filter(Q(nombre__icontains="%s")).filter(%s).distinct()[:%s]' % (q, extra, limit))
        return TipoServicioHigienico.objects.filter(Q(nombre__icontains=q)).distinct()[:limit]

    def flexbox_repr(self):
        return u'%s' % self.nombre

    def flexbox_alias(self):
        return [self.id, self.nombre.upper()]

    def save(self, *args, **kwargs):
        self.nombre = self.nombre.upper()
        self.codigo = self.codigo.upper()
        super(TipoServicioHigienico, self).save(*args, **kwargs)


class CantidadCelularHogar(ModeloBase):
    nombre = models.CharField(max_length=100)
    codigo = models.CharField(max_length=4, blank=True, null=True)
    puntaje = models.FloatField(default=0)

    class Meta:
        verbose_name = u'Cantidad de celulares en hogar'
        verbose_name_plural = u'Cantidad de celulares en hogar'
        unique_together = ('nombre',)

    def __str__(self):
        return '[' + self.codigo + ']' + ' ' + self.nombre if self.codigo else self.nombre

    @staticmethod
    def flexbox_query(q, extra=None, limit=25):
        if extra:
            return eval('CantidadCelularHogar.objects.filter(Q(nombre__icontains="%s")).filter(%s).distinct()[:%s]' % (q, extra, limit))
        return CantidadCelularHogar.objects.filter(Q(nombre__icontains=q)).distinct()[:limit]

    def flexbox_repr(self):
        return u'%s' % self.nombre

    def flexbox_alias(self):
        return [self.id, self.nombre.upper()]

    def save(self, *args, **kwargs):
        self.nombre = self.nombre.upper()
        self.codigo = self.codigo.upper()
        super(CantidadCelularHogar, self).save(*args, **kwargs)


class CantidadTVColorHogar(ModeloBase):
    nombre = models.CharField(max_length=100)
    codigo = models.CharField(max_length=4, blank=True, null=True)
    puntaje = models.FloatField(default=0)

    class Meta:
        verbose_name = u'Cantidad de televisores a color en hogar'
        verbose_name_plural = u'Cantidad de televisores a color en hogar'
        unique_together = ('nombre',)

    def __str__(self):
        return '[' + self.codigo + ']' + ' ' + self.nombre if self.codigo else self.nombre

    @staticmethod
    def flexbox_query(q, extra=None, limit=25):
        if extra:
            return eval('CantidadTVColorHogar.objects.filter(Q(nombre__icontains="%s")).filter(%s).distinct()[:%s]' % (q, extra, limit))
        return CantidadTVColorHogar.objects.filter(Q(nombre__icontains=q)).distinct()[:limit]

    def flexbox_repr(self):
        return u'%s' % self.nombre

    def flexbox_alias(self):
        return [self.id, self.nombre.upper()]

    def save(self, *args, **kwargs):
        self.nombre = self.nombre.upper()
        self.codigo = self.codigo.upper()
        super(CantidadTVColorHogar, self).save(*args, **kwargs)


class CantidadVehiculoHogar(ModeloBase):
    nombre = models.CharField(max_length=100)
    codigo = models.CharField(max_length=4, blank=True, null=True)
    puntaje = models.FloatField(default=0)

    class Meta:
        verbose_name = u'Cantidad de vehiculo en hogar'
        verbose_name_plural = u'Cantidad de vehiculos en hogar'
        unique_together = ('nombre',)

    def __str__(self):
        return '[' + self.codigo + ']' + ' ' + self.nombre if self.codigo else self.nombre

    @staticmethod
    def flexbox_query(q, extra=None, limit=25):
        if extra:
            return eval('CantidadVehiculoHogar.objects.filter(Q(nombre__icontains="%s")).filter(%s).distinct()[:%s]' % (q, extra, limit))
        return CantidadVehiculoHogar.objects.filter(Q(nombre__icontains=q)).distinct()[:limit]

    def flexbox_repr(self):
        return u'%s' % self.nombre

    def flexbox_alias(self):
        return [self.id, self.nombre.upper()]

    def save(self, *args, **kwargs):
        self.nombre = self.nombre.upper()
        self.codigo = self.codigo.upper()
        super(CantidadVehiculoHogar, self).save(*args, **kwargs)


class NivelEstudio(ModeloBase):
    nombre = models.CharField(max_length=100)
    codigo = models.CharField(max_length=4, blank=True, null=True)
    puntaje = models.FloatField(default=0)

    class Meta:
        verbose_name = u'Nivel de estudio'
        verbose_name_plural = u'Niveles de estudios'
        ordering = ['puntaje']
        unique_together = ('nombre',)

    def __str__(self):
        return '[' + self.codigo + ']' + ' ' + self.nombre if self.codigo else self.nombre

    @staticmethod
    def flexbox_query(q, extra=None, limit=25):
        if extra:
            return eval('NivelEstudio.objects.filter(Q(nombre__icontains="%s")).filter(%s).distinct()[:%s]' % (q, extra, limit))
        return NivelEstudio.objects.filter(Q(nombre__icontains=q)).distinct()[:limit]

    def flexbox_repr(self):
        return u'%s' % self.nombre

    def flexbox_alias(self):
        return [self.id, self.nombre.upper()]

    def cantidad_total_estudiantes(self):
        return FichaSocioeconomicaINEC.objects.values("id").filter(niveljefehogar=self).count()

    def save(self, *args, **kwargs):
        self.nombre = self.nombre.upper()
        self.codigo = self.codigo.upper()
        super(NivelEstudio, self).save(*args, **kwargs)


class OcupacionJefeHogar(ModeloBase):
    nombre = models.CharField(max_length=200)
    codigo = models.CharField(max_length=4, blank=True, null=True)
    puntaje = models.FloatField(default=0)

    class Meta:
        verbose_name = u'Ocupacion - jefe hogar'
        verbose_name_plural = u'Ocupaciones - jefes hogares'
        unique_together = ('nombre',)

    def __str__(self):
        return '[' + self.codigo + ']' + ' ' + self.nombre if self.codigo else self.nombre

    @staticmethod
    def flexbox_query(q, extra=None, limit=25):
        if extra:
            return eval('OcupacionJefeHogar.objects.filter(Q(nombre__icontains="%s")).filter(%s).distinct()[:%s]' % (q, extra, limit))
        return OcupacionJefeHogar.objects.filter(Q(nombre__icontains=q)).distinct()[:limit]

    def flexbox_repr(self):
        return u'%s' % self.nombre

    def flexbox_alias(self):
        return [self.id, self.nombre.upper()]

    def save(self, *args, **kwargs):
        self.nombre = self.nombre.upper()
        self.codigo = self.codigo.upper()
        super(OcupacionJefeHogar, self).save(*args, **kwargs)


class GrupoSocioEconomico(ModeloBase):
    nombre = models.CharField(max_length=100)
    codigo = models.CharField(max_length=2)
    umbralinicio = models.FloatField(default=0)
    umbralfin = models.FloatField(default=0)

    class Meta:
        verbose_name = u'Grupo socioeconomico'
        verbose_name_plural = u'Grupos socioeconomicos'
        ordering = ['-umbralinicio']
        unique_together = ('nombre',)

    def __str__(self):
        return self.codigo + ' (' + self.nombre + ') Umbrales: De ' + str(self.umbralinicio) + ' a ' + str(self.umbralfin)

    def nombre_corto(self):
        return self.codigo + ' (' + self.nombre + ')'

    def cantidad_total_estudiantes(self):
        return FichaSocioeconomicaINEC.objects.values("id").filter(grupoeconomico=self).count()

    def style_color(self):
        if self.id == 1:
            return 'color: #fff; background-color: #198754;'
        elif self.id == 2:
            return 'color: #000; background-color: #20c997;'
        elif self.id == 3:
            return 'color: #000; background-color: #ffc107;'
        elif self.id == 4:
            return 'color: #000; background-color: #fd7e14;'
        elif self.id == 5:
            return 'color: #fff; background-color: #dc3545;'
        else:
            return 'color: #000; background-color: #0dcaf0;'

    def save(self, *args, **kwargs):
        self.nombre = self.nombre.upper()
        self.codigo = self.codigo.upper()
        super(GrupoSocioEconomico, self).save(*args, **kwargs)


class TipoViviendaPro(ModeloBase):
    nombre = models.CharField(max_length=100)
    codigo = models.CharField(max_length=4, blank=True, null=True)
    puntaje = models.FloatField(default=0)

    class Meta:
        verbose_name = u'Vivienda Propia'
        verbose_name_plural = u'Viviendas Propias'
        unique_together = ('nombre',)

    def __str__(self):
        return '[' + self.codigo + ']' + ' ' + self.nombre if self.codigo else self.nombre

    @staticmethod
    def flexbox_query(q, extra=None, limit=25):
        if extra:
            return eval('TipoViviendaPro.objects.filter(Q(nombre__icontains="%s")).filter(%s).distinct()[:%s]' % (q, extra, limit))
        return TipoViviendaPro.objects.filter(Q(nombre__icontains=q)).distinct()[:limit]

    def flexbox_repr(self):
        return u'%s' % self.nombre

    def flexbox_alias(self):
        return [self.id, self.nombre.upper()]

    def save(self, *args, **kwargs):
        self.nombre = self.nombre.upper()
        self.codigo = self.codigo.upper()
        super(TipoViviendaPro, self).save(*args, **kwargs)


class ProveedorServicio(ModeloBase):
    nombre = models.CharField(max_length=100, verbose_name=u"Nombre")
    tiposervicio = models.IntegerField(choices=TIPO_SERVICIO, verbose_name=u"Tipo de servicio del proveedor")

    def __str__(self):
        return u"%s" % self.nombre

    @staticmethod
    def flexbox_query(q, extra=None, limit=25):
        if extra:
            return eval('ProveedorServicio.objects.filter(Q(nombre__icontains="%s")).filter(%s).distinct()[:%s]' % (q, extra, limit))
        return ProveedorServicio.objects.filter(Q(nombre__icontains=q)).distinct()[:limit]

    def flexbox_repr(self):
        return u'%s' % self.nombre

    def flexbox_alias(self):
        return [self.id, self.nombre.upper()]

    class Meta:
        verbose_name = u"Proveedor de servicio"
        verbose_name_plural = u"Proveedores de servicios"

    def save(self, *args, **kwargs):
        self.nombre = self.nombre.upper().strip()
        super(ProveedorServicio, self).save(*args, **kwargs)

    def flexbox_repr(self):
        return u"%s" % (self.nombre)


class FichaSocioeconomicaINEC(ModeloBase):
    persona = models.ForeignKey('sga.Persona', blank=True, null=True, on_delete=models.CASCADE)
    puntajetotal = models.FloatField(default=0)
    grupoeconomico = models.ForeignKey(GrupoSocioEconomico, blank=True, null=True, on_delete=models.CASCADE)
    # ESTRUCTURA FAMILIAR
    tipohogar = models.ForeignKey(TipoHogar, blank=True, null=True, on_delete=models.CASCADE)
    # GASTOS GENERALES
    escabezafamilia = models.BooleanField(default=False)
    esdependiente = models.BooleanField(default=False)
    personacubregasto = models.ForeignKey(PersonaCubreGasto, blank=True, null=True, on_delete=models.CASCADE)
    otroscubregasto = models.CharField(max_length=200, blank=True, null=True)
    # EN CASO DE ESCOGER OTROS CUBRE GASTOS, ESPECIFICAR EN ESTE CAMPO
    sustentahogar = models.ManyToManyField(PersonaSustentaHogar)
    # CARACTERISTICAS DE LA VIVIENDA
    tipovivienda = models.ForeignKey(TipoVivienda, blank=True, null=True, on_delete=models.CASCADE)
    val_tipovivienda = models.FloatField(default=0)
    materialpared = models.ForeignKey(MaterialPared, blank=True, null=True, on_delete=models.CASCADE)
    val_materialpared = models.FloatField(default=0)
    materialpiso = models.ForeignKey(MaterialPiso, blank=True, null=True, on_delete=models.CASCADE)
    val_materialpiso = models.FloatField(default=0)
    cantbannoducha = models.ForeignKey(CantidadBannoDucha, blank=True, null=True, on_delete=models.CASCADE)
    val_cantbannoducha = models.FloatField(default=0)
    tiposervhig = models.ForeignKey(TipoServicioHigienico, blank=True, null=True, on_delete=models.CASCADE)
    val_tiposervhig = models.FloatField(default=0)
    # ACCESO A LA TECNOLOGIA
    tieneinternet = models.BooleanField(default=False)
    val_tieneinternet = models.FloatField(default=0)
    tienedesktop = models.BooleanField(default=False)
    val_tienedesktop = models.FloatField(default=0)
    tienelaptop = models.BooleanField(default=False)
    val_tienelaptop = models.FloatField(default=0)
    cantcelulares = models.ForeignKey(CantidadCelularHogar, blank=True, null=True, on_delete=models.CASCADE)
    val_cantcelulares = models.FloatField(default=0)

    internetpanf = models.BooleanField(default=False)
    equipotienecamara = models.BooleanField(default=False)
    proveedorinternet = models.ForeignKey(ProveedorServicio, blank=True, null=True, on_delete=models.CASCADE)

    # POSESION DE BIENES
    tienetelefconv = models.BooleanField(default=False)
    val_tienetelefconv = models.FloatField(default=0)
    tienecocinahorno = models.BooleanField(default=False)
    val_tienecocinahorno = models.FloatField(default=0)
    tienerefrig = models.BooleanField(default=False)
    val_tienerefrig = models.FloatField(default=0)
    tienelavadora = models.BooleanField(default=False)
    val_tienelavadora = models.FloatField(default=0)
    tienemusica = models.BooleanField(default=False)
    val_tienemusica = models.FloatField(default=0)
    canttvcolor = models.ForeignKey(CantidadTVColorHogar, blank=True, null=True, on_delete=models.CASCADE)
    val_canttvcolor = models.FloatField(default=0)
    cantvehiculos = models.ForeignKey(CantidadVehiculoHogar, blank=True, null=True, on_delete=models.CASCADE)
    val_cantvehiculos = models.FloatField(default=0)
    # HABITOS DE CONSUMO
    compravestcc = models.BooleanField(default=False)
    val_compravestcc = models.FloatField(default=0)
    usainternetseism = models.BooleanField(default=False)
    val_usainternetseism = models.FloatField(default=0)
    usacorreonotrab = models.BooleanField(default=False)
    val_usacorreonotrab = models.FloatField(default=0)
    registroredsocial = models.BooleanField(default=False)
    val_registroredsocial = models.FloatField(default=0)
    leidolibrotresm = models.BooleanField(default=False)
    val_leidolibrotresm = models.FloatField(default=0)
    # NIVEL DE ESTUDIOS JEFE DE HOGAR
    niveljefehogar = models.ForeignKey(NivelEstudio, blank=True, null=True, on_delete=models.CASCADE)
    val_niveljefehogar = models.FloatField(default=0)
    # ACTIVIDAD ECONOMICA DEL HOGAR
    alguienafiliado = models.BooleanField(default=False)
    val_alguienafiliado = models.FloatField(default=0)
    alguienseguro = models.BooleanField(default=False)
    val_alguienseguro = models.FloatField(default=0)
    ocupacionjefehogar = models.ForeignKey(OcupacionJefeHogar, blank=True, null=True, on_delete=models.CASCADE)
    val_ocupacionjefehogar = models.FloatField(default=0)
    tipoviviendapro = models.ForeignKey(TipoViviendaPro, blank=True, null=True, on_delete=models.CASCADE)
    tienesala = models.BooleanField(default=False)
    tienecomedor = models.BooleanField(default=False)
    tienecocina = models.BooleanField(default=False)
    tienebanio = models.BooleanField(default=False)
    tieneluz = models.BooleanField(default=False)
    tieneagua = models.BooleanField(default=False)
    tienetelefono = models.BooleanField(default=False)
    tienealcantarilla = models.BooleanField(default=False)
    horastareahogar = models.IntegerField(default=0, verbose_name=u'Horas Tarea Hogar')
    horastrabajodomestico = models.IntegerField(default=0, verbose_name=u'Horas Trabajo Domesticos')
    horastrabajofuera = models.IntegerField(default=0, verbose_name=u'Horas Trabajos Fuera')
    tipoactividad = models.IntegerField(choices=ACTIVIDADES_RECREACION, default=0, verbose_name=u'Actividades recreacion')
    otrosactividad = models.CharField(max_length=200, blank=True, null=True)
    horashacertareas = models.IntegerField(default=0, verbose_name=u'Horas Hecer Tareas')
    tipotarea = models.IntegerField(choices=REALIZA_TAREAS, default=0, verbose_name=u'Realiza Tarea')
    otrostarea = models.CharField(max_length=200, blank=True, null=True)
    tienefolleto = models.BooleanField(default=False)
    tienecomputador = models.BooleanField(default=False)
    tieneenciclopedia = models.BooleanField(default=False)
    tienecyber = models.BooleanField(default=False)
    tienebiblioteca = models.BooleanField(default=False)
    tienemuseo = models.BooleanField(default=False)
    tienearearecreacion = models.BooleanField(default=False)
    otrosrecursos = models.CharField(max_length=200, blank=True, null=True)
    otrossector = models.CharField(max_length=200, blank=True, null=True)
    tienediabetes = models.BooleanField(default=False)
    tienehipertencion = models.BooleanField(default=False)
    tieneparkinson = models.BooleanField(default=False)
    tienecancer = models.BooleanField(default=False)
    tienealzheimer = models.BooleanField(default=False)
    tienevitiligo = models.BooleanField(default=False)
    tienedesgastamiento = models.BooleanField(default=False)
    tienepielblanca = models.BooleanField(default=False)
    otrasenfermedades = models.CharField(max_length=200, blank=True, null=True)
    tienesida = models.BooleanField(default=False)
    enfermedadescomunes = models.CharField(max_length=200, blank=True, null=True)
    salubridadvida = models.IntegerField(choices=SALUBRIDAD_VIDA, default=0, verbose_name=u'Salubridad Vida')
    estadogeneral = models.IntegerField(choices=ESTADO_GENERAL, default=0, verbose_name=u'Estado General')
    tratamientomedico = models.CharField(max_length=200, blank=True, null=True)
    confirmar = models.BooleanField(default=False)

    class Meta:
        verbose_name = u'Ficha socioeconomica'
        verbose_name_plural = u'Fichas socioeconomicas'
        unique_together = ('persona',)

    def __str__(self):
        return str(self.persona.nombre_completo()) + ' - ' + str(self.tipohogar)

    def tipo_act(self):
        return ACTIVIDADES_RECREACION[self.tipoactividad - 1][1]

    def total_ingresos_sustentahogar(self):
        return null_to_numeric(self.sustentahogar.all().aggregate(valor=Sum('ingresomensual'))['valor'])

    def calcular_puntaje_total(self):
        return self.val_tipovivienda + self.val_materialpared + self.val_materialpiso + self.val_cantbannoducha + self.val_tiposervhig + \
            self.val_tieneinternet + self.val_tienedesktop + self.val_tienelaptop + self.val_cantcelulares + \
            self.val_tienetelefconv + self.val_tienecocinahorno + self.val_tienerefrig + self.val_tienelavadora + self.val_tienemusica + self.val_canttvcolor + self.val_cantvehiculos + \
            self.val_compravestcc + self.val_usainternetseism + self.val_usacorreonotrab + self.val_registroredsocial + self.val_leidolibrotresm + \
            self.val_niveljefehogar + self.val_alguienafiliado + self.val_alguienseguro + self.val_ocupacionjefehogar

    def determinar_grupo_economico(self):
        return GrupoSocioEconomico.objects.filter(umbralinicio__lte=self.puntajetotal, umbralfin__gte=self.puntajetotal)[:1].get() if GrupoSocioEconomico.objects.values('id').filter(umbralinicio__lte=self.puntajetotal, umbralfin__gte=self.puntajetotal).exists() else None

    def delete_cache(self):
        from sga.templatetags.sga_extras import encrypt
        if self.persona_id:
            if cache.has_key(f"ficha_socio_economica_persona_id_{encrypt(self.persona_id)}"):
                cache.delete(f"ficha_socio_economica_persona_id_{encrypt(self.persona_id)}")
            if cache.has_key(f"tiene_ficha_socioeconomica_confirmada_persona_id_{encrypt(self.persona_id)}"):
                cache.delete(f"tiene_ficha_socioeconomica_confirmada_persona_id_{encrypt(self.persona_id)}")

    def delete(self, *args, **kwargs):
        self.delete_cache()
        super(FichaSocioeconomicaINEC, self).delete(*args, **kwargs)

    def save(self, *args, **kwargs):
        self.otroscubregasto = self.otroscubregasto.upper() if self.otroscubregasto else ''
        self.puntajetotal = self.calcular_puntaje_total()
        self.grupoeconomico = self.determinar_grupo_economico()
        self.delete_cache()
        super(FichaSocioeconomicaINEC, self).save(*args, **kwargs)


class FichaSocioeconomicaReplayINEC(ModeloBase):
    persona = models.ForeignKey('sga.Persona', blank=True, null=True, on_delete=models.CASCADE)
    puntajetotal = models.FloatField(default=0)
    grupoeconomico = models.ForeignKey(GrupoSocioEconomico, blank=True, null=True, on_delete=models.CASCADE)
    # ESTRUCTURA FAMILIAR
    tipohogar = models.ForeignKey(TipoHogar, blank=True, null=True, on_delete=models.CASCADE)
    # GASTOS GENERALES
    escabezafamilia = models.BooleanField(default=False)
    esdependiente = models.BooleanField(default=False)
    personacubregasto = models.ForeignKey(PersonaCubreGasto, blank=True, null=True, on_delete=models.CASCADE)
    otroscubregasto = models.CharField(max_length=200, blank=True, null=True)
    # EN CASO DE ESCOGER OTROS CUBRE GASTOS, ESPECIFICAR EN ESTE CAMPO
    # sustentahogar = models.ManyToManyField(PersonaSustentaHogar)
    # CARACTERISTICAS DE LA VIVIENDA
    tipovivienda = models.ForeignKey(TipoVivienda, blank=True, null=True, on_delete=models.CASCADE)
    val_tipovivienda = models.FloatField(default=0)
    materialpared = models.ForeignKey(MaterialPared, blank=True, null=True, on_delete=models.CASCADE)
    val_materialpared = models.FloatField(default=0)
    materialpiso = models.ForeignKey(MaterialPiso, blank=True, null=True, on_delete=models.CASCADE)
    val_materialpiso = models.FloatField(default=0)
    cantbannoducha = models.ForeignKey(CantidadBannoDucha, blank=True, null=True, on_delete=models.CASCADE)
    val_cantbannoducha = models.FloatField(default=0)
    tiposervhig = models.ForeignKey(TipoServicioHigienico, blank=True, null=True, on_delete=models.CASCADE)
    val_tiposervhig = models.FloatField(default=0)
    # ACCESO A LA TECNOLOGIA
    tieneinternet = models.BooleanField(default=False)
    val_tieneinternet = models.FloatField(default=0)
    tienedesktop = models.BooleanField(default=False)
    val_tienedesktop = models.FloatField(default=0)
    tienelaptop = models.BooleanField(default=False)
    val_tienelaptop = models.FloatField(default=0)
    cantcelulares = models.ForeignKey(CantidadCelularHogar, blank=True, null=True, on_delete=models.CASCADE)
    val_cantcelulares = models.FloatField(default=0)
    # POSESION DE BIENES
    tienetelefconv = models.BooleanField(default=False)
    val_tienetelefconv = models.FloatField(default=0)
    tienecocinahorno = models.BooleanField(default=False)
    val_tienecocinahorno = models.FloatField(default=0)
    tienerefrig = models.BooleanField(default=False)
    val_tienerefrig = models.FloatField(default=0)
    tienelavadora = models.BooleanField(default=False)
    val_tienelavadora = models.FloatField(default=0)
    tienemusica = models.BooleanField(default=False)
    val_tienemusica = models.FloatField(default=0)
    canttvcolor = models.ForeignKey(CantidadTVColorHogar, blank=True, null=True, on_delete=models.CASCADE)
    val_canttvcolor = models.FloatField(default=0)
    cantvehiculos = models.ForeignKey(CantidadVehiculoHogar, blank=True, null=True, on_delete=models.CASCADE)
    val_cantvehiculos = models.FloatField(default=0)
    # HABITOS DE CONSUMO
    compravestcc = models.BooleanField(default=False)
    val_compravestcc = models.FloatField(default=0)
    usainternetseism = models.BooleanField(default=False)
    val_usainternetseism = models.FloatField(default=0)
    usacorreonotrab = models.BooleanField(default=False)
    val_usacorreonotrab = models.FloatField(default=0)
    registroredsocial = models.BooleanField(default=False)
    val_registroredsocial = models.FloatField(default=0)
    leidolibrotresm = models.BooleanField(default=False)
    val_leidolibrotresm = models.FloatField(default=0)
    # NIVEL DE ESTUDIOS JEFE DE HOGAR
    niveljefehogar = models.ForeignKey(NivelEstudio, blank=True, null=True, on_delete=models.CASCADE)
    val_niveljefehogar = models.FloatField(default=0)
    # ACTIVIDAD ECONOMICA DEL HOGAR
    alguienafiliado = models.BooleanField(default=False)
    val_alguienafiliado = models.FloatField(default=0)
    alguienseguro = models.BooleanField(default=False)
    val_alguienseguro = models.FloatField(default=0)
    ocupacionjefehogar = models.ForeignKey(OcupacionJefeHogar, blank=True, null=True, on_delete=models.CASCADE)
    val_ocupacionjefehogar = models.FloatField(default=0)
    tipoviviendapro = models.ForeignKey(TipoViviendaPro, blank=True, null=True, on_delete=models.CASCADE)
    proveedorinternet = models.ForeignKey(ProveedorServicio, blank=True, null=True, on_delete=models.CASCADE)
    tienesala = models.BooleanField(default=False)
    tienecomedor = models.BooleanField(default=False)
    tienecocina = models.BooleanField(default=False)
    tienebanio = models.BooleanField(default=False)
    tieneluz = models.BooleanField(default=False)
    tieneagua = models.BooleanField(default=False)
    tienetelefono = models.BooleanField(default=False)
    tienealcantarilla = models.BooleanField(default=False)
    horastareahogar = models.IntegerField(default=0, verbose_name=u'Horas Tarea Hogar')
    horastrabajodomestico = models.IntegerField(default=0, verbose_name=u'Horas Trabajo Domesticos')
    horastrabajofuera = models.IntegerField(default=0, verbose_name=u'Horas Trabajos Fuera')
    tipoactividad = models.IntegerField(choices=ACTIVIDADES_RECREACION, default=0, verbose_name=u'Actividades recreacion')
    otrosactividad = models.CharField(max_length=200, blank=True, null=True)
    horashacertareas = models.IntegerField(default=0, verbose_name=u'Horas Hecer Tareas')
    tipotarea = models.IntegerField(choices=REALIZA_TAREAS, default=0, verbose_name=u'Realiza Tarea')
    otrostarea = models.CharField(max_length=200, blank=True, null=True)
    tienefolleto = models.BooleanField(default=False)
    tienecomputador = models.BooleanField(default=False)
    tieneenciclopedia = models.BooleanField(default=False)
    tienecyber = models.BooleanField(default=False)
    tienebiblioteca = models.BooleanField(default=False)
    tienemuseo = models.BooleanField(default=False)
    tienearearecreacion = models.BooleanField(default=False)
    otrosrecursos = models.CharField(max_length=200, blank=True, null=True)
    otrossector = models.CharField(max_length=200, blank=True, null=True)
    tienediabetes = models.BooleanField(default=False)
    tienehipertencion = models.BooleanField(default=False)
    tieneparkinson = models.BooleanField(default=False)
    tienecancer = models.BooleanField(default=False)
    tienealzheimer = models.BooleanField(default=False)
    tienevitiligo = models.BooleanField(default=False)
    tienedesgastamiento = models.BooleanField(default=False)
    tienepielblanca = models.BooleanField(default=False)
    otrasenfermedades = models.CharField(max_length=200, blank=True, null=True)
    tienesida = models.BooleanField(default=False)
    enfermedadescomunes = models.CharField(max_length=200, blank=True, null=True)
    salubridadvida = models.IntegerField(choices=SALUBRIDAD_VIDA, default=0, verbose_name=u'Salubridad Vida')
    estadogeneral = models.IntegerField(choices=ESTADO_GENERAL, default=0, verbose_name=u'Estado General')
    tratamientomedico = models.CharField(max_length=200, blank=True, null=True)
    confirmar = models.BooleanField(default=False)
    personaaprueba = models.ForeignKey('sga.Persona', related_name='personaaprueba_set', verbose_name=u"Aprobador", blank=True, null=True, on_delete=models.CASCADE)
    obseaprueba = models.TextField(blank=True, null=True, verbose_name=u'Descripción Aprueba')
    estadosolicitud = models.IntegerField(choices=ESTADO_SOLICITUD, default=1, blank=True, null=True, verbose_name=u"Estado solicitud")

    class Meta:
        verbose_name = u'Ficha socioeconomica Replay'
        verbose_name_plural = u'Fichas socioeconomicas Replay'

    def __str__(self):
        return str(self.persona.nombre_completo()) + ' - ' + str(self.tipohogar)

    def calcular_puntaje_total(self):
        return self.val_tipovivienda + self.val_materialpared + self.val_materialpiso + self.val_cantbannoducha + self.val_tiposervhig + \
            self.val_tieneinternet + self.val_tienedesktop + self.val_tienelaptop + self.val_cantcelulares + \
            self.val_tienetelefconv + self.val_tienecocinahorno + self.val_tienerefrig + self.val_tienelavadora + self.val_tienemusica + self.val_canttvcolor + self.val_cantvehiculos + \
            self.val_compravestcc + self.val_usainternetseism + self.val_usacorreonotrab + self.val_registroredsocial + self.val_leidolibrotresm + \
            self.val_niveljefehogar + self.val_alguienafiliado + self.val_alguienseguro + self.val_ocupacionjefehogar

    def determinar_grupo_economico(self):
        return GrupoSocioEconomico.objects.filter(umbralinicio__lte=self.puntajetotal, umbralfin__gte=self.puntajetotal)[:1].get() if GrupoSocioEconomico.objects.values('id').filter(umbralinicio__lte=self.puntajetotal, umbralfin__gte=self.puntajetotal).exists() else None

    def delete_cache(self):
        from sga.templatetags.sga_extras import encrypt
        if self.persona_id:
            if cache.has_key(f"ficha_socio_economica_persona_id_{encrypt(self.persona_id)}"):
                cache.delete(f"ficha_socio_economica_persona_id_{encrypt(self.persona_id)}")
            if cache.has_key(f"tiene_ficha_socioeconomica_confirmada_persona_id_{encrypt(self.persona_id)}"):
                cache.delete(f"tiene_ficha_socioeconomica_confirmada_persona_id_{encrypt(self.persona_id)}")

    def delete(self, *args, **kwargs):
        self.delete_cache()
        super(FichaSocioeconomicaReplayINEC, self).delete(*args, **kwargs)

    def save(self, *args, **kwargs):
        self.otroscubregasto = self.otroscubregasto.upper() if self.otroscubregasto else ''
        self.puntajetotal = self.calcular_puntaje_total()
        self.obseaprueba = self.obseaprueba.upper() if self.obseaprueba else ''
        self.grupoeconomico = self.determinar_grupo_economico()
        self.delete_cache()
        super(FichaSocioeconomicaReplayINEC, self).save(*args, **kwargs)


#Inicio models Donacion
class TipoProducto(ModeloBase):
    descripcion = models.TextField(default='', blank=True, null=True, verbose_name=u'Descripcion')

    def __str__(self):
        return u'%s' % (self.descripcion)

    class Meta:
        verbose_name = u"Tipo de producto"
        verbose_name_plural = u"Tipos de productos"

    def save(self, *args, **kwargs):
        self.descripcion = self.descripcion.strip().upper() if self.descripcion else ''
        super(TipoProducto, self).save(*args, **kwargs)

    def en_uso(self):
        return self.producto_set.values('id').filter(status=True).exists()

class Producto(ModeloBase):
    descripcion = models.TextField(default='', blank=True, null=True, verbose_name=u'Descripcion')
    tipoproducto = models.ForeignKey(TipoProducto, on_delete=models.CASCADE, blank=True, null=True, verbose_name=u'Tipo de producto')

    def __str__(self):
        return u'%s' % self.descripcion.upper()

    class Meta:
        verbose_name = u"Producto"
        verbose_name_plural = u"Productos"

    def save(self, *args, **kwargs):
        self.descripcion = self.descripcion.upper().strip()
        super(Producto, self).save(*args, **kwargs)

    def en_uso(self):
        return self.detalleproductopublicacion_set.values('id').filter(publicaciondonacion__status=True, status=True).exists()

class PoblacionDonacion(ModeloBase):
    nombre = models.TextField(default='', blank=True, null=True, verbose_name=u'Nombre')

    def __str__(self):
        return u'%s' % (self.nombre)

    class Meta:
        verbose_name = u"Poblacion"
        verbose_name_plural = u"Poblaciones"

    def save(self, *args, **kwargs):
        self.nombre = self.nombre.upper().strip()
        super(PoblacionDonacion, self).save(*args, **kwargs)

    def en_uso(self):
        return self.publicaciondonacion_set.values('id').filter(status=True).exists()

class TipoDonacion(ModeloBase):
    nombre = models.TextField(default='', blank=True, null=True, verbose_name=u'Nombre')

    def __str__(self):
        return u'%s' % (self.nombre)

    class Meta:
        verbose_name = u"Tipo de donacion"
        verbose_name_plural = u"Tipo de donaciones"

    def save(self, *args, **kwargs):
        self.nombre = self.nombre.strip().upper() if self.nombre else ''
        super(TipoDonacion, self).save(*args, **kwargs)

    def en_uso(self):
        return self.publicaciondonacion_set.values('id').filter(status=True).exists()


PUBLICACION_DONACION_PRIORIDAD = (
    (1, 'ALTA'),
    (2, 'MEDIA'),
    (3, 'BAJA'),
)

PUBLICACION_DONACION_ESTADO = (
    (1, 'PENDIENTE'),
    (2, 'APROBADO'),
    (3, 'RECHAZADO'),
)

class PublicacionDonacion(ModeloBase):
    nombre = models.TextField(default='', blank=True, null=True, verbose_name=u'Nombre')
    persona = models.ForeignKey(Persona, blank=True, null=True, verbose_name=u'Persona', on_delete=models.CASCADE)
    objetivo = models.TextField(default='', blank=True, null=True, verbose_name=u'Objetivo')
    poblacion = models.ManyToManyField(PoblacionDonacion, verbose_name=u'Poblacion')
    tipodonacion = models.ForeignKey(TipoDonacion, blank=True, null=True, verbose_name=u'Tipo de donacion', on_delete=models.CASCADE)
    fechainiciorecepcion = models.DateField(null=True, blank=True, verbose_name=u'Fecha inicio de recepcion')
    fechafinrecepcion = models.DateField(null=True, blank=True, verbose_name=u'Fecha fin de recepcion')
    fechainicioentrega = models.DateField(null=True, blank=True, verbose_name=u'Fecha inicio de entrega')
    fechafinentrega = models.DateField(null=True, blank=True, verbose_name=u'Fecha fin de entrega')
    evidencianecesidad = models.FileField(upload_to='socioecon/donaciones/necesidad/%Y/%m/%d', null=True, blank=True, default='', verbose_name=u"Evidencia necesidad")
    evidenciaejecucion = models.FileField(upload_to='socioecon/donaciones/ejecucion/%Y/%m/%d', null=True, blank=True, default='', verbose_name=u"Evidencia ejecucion")
    mostrarfotoperfil = models.BooleanField(blank=True, null=True, verbose_name=u"Mostrar foto perfil", default=False)
    estadoprioridad = models.IntegerField(choices=PUBLICACION_DONACION_PRIORIDAD, default=3, blank=True, null=True, verbose_name=u"Prioridad")
    estado = models.IntegerField(choices=PUBLICACION_DONACION_ESTADO, blank=True, null=True, verbose_name=u"Estado", default=1)

    def __str__(self):
        return u'%s - %s' % (self.nombre, self.persona.nombre_completo_inverso())

    class Meta:
        verbose_name = u"Publicacion donacion"
        verbose_name_plural = u"Publicacion de donaciones"
        ordering = ('-pk',)

    def get_productos(self):
        return self.detalleproductopublicacion_set.filter(status=True)

    def get_timepublicadohace(self, date):
        lista = []
        index = 0 if date.days == 0 else 1
        lista.append([int(str(date).split(',')[index].split('.')[0].split(':')[0]),
                      int(str(date).split(',')[index].split('.')[0].split(':')[1]),
                      int(str(date).split(',')[index].split('.')[0].split(':')[2])])
        return lista

    def filtros(self, POST, persona):
        try:
            from django.http import HttpResponseRedirect
            from sga.funciones import convertir_fecha
            from django.db.models import Q
            filtro = Q(status=True)
            idpersona = (int(POST['idp']) if POST['idp'] else 0) if 'idp' in POST else 0
            fechadesde = u"%s 00:00:00" % convertir_fecha(POST['fd']) if POST['fd'].strip() else ''
            fechahasta = u"%s 23:59:59" % convertir_fecha(POST['fh']) if POST['fh'].strip() else ''

            if 'fir' in POST:
                fechainiciorecepcion = (u"%s" % convertir_fecha(POST['fir'])) if POST['fir'].strip() else ''
                fechafinrecepcion = u"%s" % convertir_fecha(POST['ffr']) if POST['ffr'].strip() else ''
                fechainicioentrega = u"%s" % convertir_fecha(POST['fie']) if POST['fie'].strip() else ''
                fechafinentrega = u"%s" % convertir_fecha(POST['ffe']) if POST['ffe'].strip() else ''
                estadoaprobacion = int(POST['ea']) if POST['ea'].strip() else 0
                estadoprioridad = int(POST['ep']) if POST['ep'].strip() else 0

                if estadoaprobacion:
                    filtro = filtro & Q(estado=estadoaprobacion)

                if estadoprioridad:
                    filtro = filtro & Q(estadoprioridad=estadoprioridad)

                if fechainiciorecepcion:
                    filtro = filtro & Q(fechainiciorecepcion__gte=fechainiciorecepcion)

                if fechafinrecepcion:
                    filtro = filtro & Q(fechafinrecepcion__lte=fechafinrecepcion)

                if fechainicioentrega:
                    filtro = filtro & Q(fechainicioentrega__gte=fechainicioentrega)

                if fechafinentrega:
                    filtro = filtro & Q(fechafinentrega__lte=fechafinentrega)

            if fechadesde:
                filtro = filtro & Q(fecha_creacion__gte=fechadesde)

            if fechahasta:
                filtro = filtro & Q(fecha_creacion__lte=fechahasta)

            if idpersona:
                filtro = filtro & Q(persona_id=idpersona)

            return PublicacionDonacion.objects.filter(filtro)
        except Exception as ex:
            raise NameError(f'Error en los criterios de busqueda. {ex.__str__()}')

    def color_estadoprioridad(self):
        estado = 'label-primary'
        if self.estadoprioridad >= 1:
            estado = 'label-important'
        elif self.estadoprioridad == 2:
            estado = 'label-warning'
        return estado

    def color_estado(self):
        estado = 'label-primary'
        if self.estado == 1:
            estado = 'label-secondary'
        elif self.estado == 2:
            estado = 'label-success'
        elif self.estado >= 3:
            estado = 'label-important'
        return estado

    def lista_responsables(self):
        return ['jcuadradoh2@unemi.edu.ec', 'mlozadam@unemi.edu.ec', 'ncastroc1@unemi.edu.ec', 'jcantosv4@unemi.edu.ec', 'jguijarroo@unemi.edu.ec', 'dsolorzanor3@unemi.edu.ec']


class UnidadMedidaDonacion(ModeloBase):
    nombre = models.CharField(verbose_name=u"Unidad de medida", max_length=20)
    abreviatura = models.CharField(verbose_name=u"Abreviatura", max_length=10)

    class Meta:
        verbose_name = u"Unidad de Medida"
        verbose_name_plural = u"Unidades de Medida"
        ordering = ('nombre',)

    def __str__(self):
        return self.nombre

    def campos(self):
        return self.nombre

    def save(self, *args, **kwargs):
        self.nombre = self.nombre.strip().upper()
        self.abreviatura = self.abreviatura.strip()
        super(UnidadMedidaDonacion, self).save(*args, **kwargs)

    def en_uso(self):
        return self.detalleproductopublicacion_set.values('id').filter(status=True).exists()

class DetalleProductoPublicacion(ModeloBase):
    producto = models.ForeignKey(Producto, blank=True, null=True, verbose_name=u'Producto', on_delete=models.CASCADE)
    cantidad = models.IntegerField(u"Cantidad", blank=True, null=True)
    unidadmedida = models.ForeignKey(UnidadMedidaDonacion, blank=True, null=True, verbose_name=u'Unidad de medida', on_delete=models.CASCADE)
    publicaciondonacion = models.ForeignKey(PublicacionDonacion, blank=True, null=True, verbose_name=u'Publicacion de donacion', on_delete=models.CASCADE)

    def __str__(self):
        return u'[%s] %s' % (self.cantidad, self.producto)

    class Meta:
        verbose_name = u"Detalle del producto"
        verbose_name_plural = u"Detalles del producto"


    def get_cantidadrecaudada(self):
        return int(self.detallecontribuidordonacion_set.all().filter(status=True).aggregate(valor=Sum('cantidad'))['valor']) if self.detallecontribuidordonacion_set.all().filter(status=True) else 0

    def get_porcentaje(self):
        cantidaddonada = self.get_cantidadrecaudada()
        if cantidaddonada:
            total = ((int(cantidaddonada) / int(self.cantidad)) * 100)
            return total if total <= 100 else 100
        else:
            return 0

    def cantidad_estimada(self):
        cantidad = self.cantidad - null_to_numeric(self.detallecontribuidordonacion_set.filter(status=True).aggregate(valor=Sum('cantidad'))['valor'])
        if cantidad:
            return cantidad if cantidad > 0 else 0
        else:
            return 0

    def mi_cantidad_donada(self, persona):
        return null_to_numeric(self.detallecontribuidordonacion_set.filter(status=True, contribuidordonacion__persona=persona).aggregate(cantidadtotal=Sum('cantidad'))['cantidadtotal'])

    def total_productos_solicitud(self):
        local = DetalleProductoPublicacion.objects.filter(publicaciondonacion_id=self.publicaciondonacion).aggregate(cantidadtotal=Sum('cantidad'))
        return local['cantidadtotal'] if local else 0

class ContribuidorDonacion(ModeloBase):
    persona = models.ForeignKey(Persona, blank=True, null=True, verbose_name=u'Persona', on_delete=models.CASCADE)
    es_anonimo = models.BooleanField(verbose_name=u"Anonimo", blank=True, null=True)

    def __str__(self):
        return u'%s' % (self.persona.nombre_completo_inverso())

    class Meta:
        verbose_name = u"Contribuidor donación"
        verbose_name_plural = u"Contribuidores de donación"
        ordering = ('-pk',)


class DetalleContribuidorDonacion(ModeloBase):
    detalleproductopublicacion = models.ForeignKey(DetalleProductoPublicacion, blank=True, null=True, verbose_name=u'Detalle producto', on_delete=models.CASCADE)
    contribuidordonacion = models.ForeignKey(ContribuidorDonacion, blank=True, null=True, verbose_name=u'Contribuidor donacion', on_delete=models.CASCADE)
    cantidad = models.IntegerField(u"Cantidad", blank=True, null=True)

    def __str__(self):
        return u'%s' % (self.contribuidordonacion.persona.nombre_completo_inverso())

    class Meta:
        verbose_name = u"Detalle contribuidor donación"
        verbose_name_plural = u"Detalles contribuidor donación"
        ordering = ('-pk',)


class DetalleAprobacionPublicacionDonacion(ModeloBase):
    publicaciondonacion = models.ForeignKey(PublicacionDonacion, blank=True, null=True, verbose_name=u"Publicación donación", on_delete=models.CASCADE)
    observacion = models.TextField(verbose_name=u"Observacion", blank=True, null=True)
    estado = models.IntegerField(choices=PUBLICACION_DONACION_ESTADO, blank=True, null=True, verbose_name=u"Estado",default=1)
    persona = models.ForeignKey(Persona, blank=True, null=True, verbose_name=u'Persona', on_delete=models.CASCADE)

    def __str__(self):
        return u'%s' % (self.get_estado_display())

    class Meta:
        verbose_name = u"Publicación donación"
        verbose_name_plural = u"Publicación de donaciones"
        ordering = ('-pk',)

    def color_estado(self):
        estado = 'label-primary'
        if self.estado == 1:
            estado = 'label-warning'
        elif self.estado == 2:
            estado = 'label-success'
        elif self.estado >= 3:
            estado = 'label-important'
        return estado
