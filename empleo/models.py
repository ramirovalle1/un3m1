from datetime import datetime

from django.contrib.auth.models import User
from django.db import models

from empresa.models import RepresentantesEmpresa
from sagest.models import TipoContrato
from sga.funciones import ModeloBase
from sga.models import Empleador, Titulacion, Pais, Provincia, Canton, Graduado, Inscripcion, Persona

NIVEL_INSTRUCCION = (
    # (1, u'PRIMARIA'),
    (2, u'Estudiante universitario'),
    (3, u'Tercer nivel'),
    (4, u'Cuarto nivel')
)

TIPO_SOLICITUD = (
    (0, 'Unemi Empleo'),
    (1, 'Convenios')
)

MODALIDAD= (
    (1, u'Presencial'),
    (2, u'En línea'),
    (3, u'Semipresencial'),
)

DEDICACION = (
    (1, u'Tiempo Completo (40 Horas)'),
    (2, u'Medio tiempo (20 Horas)'),
    (3, u'Tiempo parcial (18 Horas)'),
    (4, u'Tiempo parcial (10 Horas)'),
)

JORNADA = (
    (1, u'Matutina'),
    (2, u'Nocturna'),
    (3, u'Matutina y nocturna'),
    (4, u'En línea'),
    (5, u'Fin de semana'),
    (6, u'Matutina, vespertina, nocturna'),
    (7, u'Matutina, vespertina'),
    (8, u'Vespertina, nocturna'),
    (9, u'Vespertina'),
)

ESTADOS_APLICACION = (
    (0, u'Postulación enviada'),
    (1, u'Curriculum revisado'),
    (2, u'Apto'),
    (3, u'No apto'),
)

ESTADOS_CONTRATO = (
    (0, u'Pendiente'),
    (1, u'Contratado'),
    (2, u'No contratado'),
)

ESTADOS_EMPRESA = (
    (0, u'Pendiente'),
    (1, u'Aprobado'),
    (2, u'Rechazado'),
    (3, u'Corregir'),
)


GENERO= (
    (0, u'Ambos'),
    (2, u'Masculino'),
    (1, u'Femenino'),
)
POSTULANTE = (
    (0, u'Graduados'),
    (1, u'Estudiantes'),
    (2, u'Ambos'),
)
TIEMPO = (
    (0, u'Menor ó igual a 1 año'),
    (1, u'2 Años'),
    (2, u'3 Años'),
    (3, u'Mayor ó igual a 4 años'),
    (4, u'Sin experiencia'),
)

OPCION_OBSERVACION_HOJAVIDA = (
    (0, u'--Seleccione un motivo de rechazo--'),
    (1, u'Experiencia Laboral'),
    (2, u'Nivel Académico'),
    (3, u'Nivel de Idioma Extranjero'),
    (4, u'Capacitaciones'),
    (5, u'Otros')
)

OPCION_OBSERVACION_CONTRATO = (
    (0, u'--Seleccione un motivo de rechazo--'),
    (1, u'Pruebas Psicométricas'),
    (2, u'Pruebas de conocimiento'),
    (3, u'Entrevista personal'),
    (4, u'Pruebas psicológicas'),
    (5, u'Otros')
)

ESTADOS_SOLICITUD = (
    (0, u'Pendiente'),
    (1, u'Aprobado'),
    (2, u'Rechazado'),
)


class SolicitudAprobacionEmpresa(ModeloBase):
    empleador = models.ForeignKey(Empleador, verbose_name='Empresa Empleadora', blank=True, null=True, on_delete=models.CASCADE)
    fecha = models.DateTimeField(blank=True, null=True, verbose_name=u"Fecha")
    estado = models.BooleanField(default=True, verbose_name=u'Estado')
    observacion = models.CharField(default='', max_length=500, verbose_name=u"Descripción de la aprobacion")
    estadoempresa = models.IntegerField(choices=ESTADOS_EMPRESA, default=0, verbose_name=u'Estado de solicitud de aprobacion')
    tiposolicitud = models.IntegerField(choices=TIPO_SOLICITUD, default=0, verbose_name=u'Tipo de Solicitud de aprobacion')

    def __str__(self):
        return '{} {}'.format(self.empleador, self.get_estadoempresa_display())

    class Meta:
        verbose_name = u"Solicitud de empresa"
        verbose_name_plural = u"Solicitudes de empresas"

    def save(self, *args, **kwargs):
        super(SolicitudAprobacionEmpresa, self).save(*args, **kwargs)


class HistorialAprobacionEmpresa(ModeloBase):
    empleador = models.ForeignKey(Empleador, verbose_name='Empresa Empleadora', blank=True, null=True, on_delete=models.CASCADE)
    solicitud = models.ForeignKey(SolicitudAprobacionEmpresa, verbose_name='Solicitud de Empresa', blank=True, null=True, on_delete=models.CASCADE)
    fecha = models.DateTimeField(blank=True, null=True, verbose_name=u"Fecha de aprobacion")

    def __str__(self):
        return '{} {}'.format(self.solicitud, self.fecha.strftime('%Y-%m-%d'))

    class Meta:
        verbose_name = u"Historial de aprobación de empresa"
        verbose_name_plural = u"Historiales de aprobaciones de empresas"

    def save(self, *args, **kwargs):
        super(HistorialAprobacionEmpresa, self).save(*args, **kwargs)


class OfertaLaboralEmpresa(ModeloBase):
    empresa = models.ForeignKey(Empleador, on_delete=models.CASCADE, blank=True, null=True, verbose_name=u'Empresa ofertante')
    encargado = models.ForeignKey(RepresentantesEmpresa, on_delete=models.CASCADE, blank=True, null=True, verbose_name=u"Encargado del proceso")
    titulo = models.CharField(max_length=1200, blank=True, null=True, verbose_name='Titulo')
    descripcion = models.TextField(blank=True, null=True, verbose_name='Descripcion')
    carrera = models.ManyToManyField('sga.Carrera', related_name='+', verbose_name='Carreras Relacionadas')
    carrerarelacionada = models.ManyToManyField('sga.Carrera', related_name='+', verbose_name='Carreras Relacionadas')
    campoamplio = models.ManyToManyField('sga.AreaConocimientoTitulacion', verbose_name=u'Campo Amplio')
    campoespecifico = models.ManyToManyField('sga.SubAreaConocimientoTitulacion', verbose_name=u'Campo Especifico')
    campodetallado = models.ManyToManyField('sga.SubAreaEspecificaConocimientoTitulacion', verbose_name=u'Campo Detallado')
    nivel = models.IntegerField(choices=NIVEL_INSTRUCCION, null=True, blank=True, verbose_name=u'Nivel de instrucción')
    modalidad = models.IntegerField(choices=MODALIDAD, null=True, blank=True, verbose_name=u'Modalidad')
    dedicacion = models.IntegerField(choices=DEDICACION, null=True, blank=True, verbose_name=u'Dedicación')
    jornada = models.IntegerField(choices=JORNADA, null=True, blank=True, verbose_name=u'Jornada')
    rmu = models.FloatField(blank=True, null=True, verbose_name=u'Remuneracion mensual unificada')
    vigente = models.BooleanField(default=False, verbose_name='¿Vigente?')
    finicio = models.DateField(verbose_name=u'Fecha inicio oferta', blank=True, null=True)
    ffin = models.DateField(verbose_name=u'Fecha fin oferta', blank=True, null=True)

    finiciopostulacion = models.DateField(verbose_name=u'Fecha inicio postulacion', blank=True, null=True)
    ffinpostlacion = models.DateField(verbose_name=u'Fecha fin postulacion', blank=True, null=True)

    finiciorevision = models.DateField(verbose_name=u'Fecha inicio revision', blank=True, null=True)
    ffinrevision = models.DateField(verbose_name=u'Fecha fin revision', blank=True, null=True)

    tipocontrato = models.ForeignKey(TipoContrato, on_delete=models.CASCADE, blank=True, null=True, verbose_name=u'Tipo de Contrato')
    vacantes = models.IntegerField(default=1, verbose_name=u'Total Vacantes')
    muestranombre = models.BooleanField(default=False, verbose_name='¿Muestra el nombre de la empresa?')
    muestrarmu = models.BooleanField(default=False, verbose_name='¿Muestra la remuneración?')
    discapacitados = models.BooleanField(default=False, verbose_name='¿Acepta discapacitados?')
    viajar = models.BooleanField(default=False, verbose_name='¿Disponibilidad para viajar?')
    carropropio = models.BooleanField(default=False, verbose_name='¿Necesidad de vehículo propio?')
    requiereexpe = models.BooleanField(default=False, verbose_name='¿Requiere Experiencia?')
    sexo = models.IntegerField(choices=GENERO, null=True, blank=True, verbose_name=u'Sexo')
    quienpostula = models.IntegerField(choices=POSTULANTE, null=True, blank=True, verbose_name=u'Quien postula')
    tiempoexperiencia = models.IntegerField(choices=TIEMPO, null=True, blank=True, verbose_name=u'Tiempo de experiencia')
    conocimiento = models.TextField(blank=True, null=True, verbose_name='Conocimientos específicos')
    funciones = models.TextField(blank=True, null=True, verbose_name='Funciones principales')
    habilidades = models.TextField(blank=True, null=True, verbose_name='Habilidades específicas requeridas')
    areatrabajo = models.TextField(blank=True, null=True, verbose_name='Area de trabajo')
    pais = models.ForeignKey(Pais, blank=True, null=True, related_name='+', verbose_name=u'País residencia', on_delete=models.CASCADE)
    provincia = models.ForeignKey(Provincia, blank=True, null=True, related_name='+', verbose_name=u"Provincia de residencia", on_delete=models.CASCADE)
    canton = models.ForeignKey(Canton, blank=True, null=True, related_name='+', verbose_name=u"Canton de residencia", on_delete=models.CASCADE)
    direccion = models.CharField(default='', max_length=300, verbose_name=u"Direccion")
    estadooferta = models.IntegerField(choices=ESTADOS_EMPRESA, default=0, verbose_name=u'Estado de oferta laboral')
    muestrapromedio = models.BooleanField(default=True, verbose_name='¿Desea que se muestre el promedio del postulante?')
    observacion_rechazo = models.TextField(blank=True, null=True, verbose_name='Motivo de rechazo de la oferta')

    def participantes(self):
        return self.personaaplicaoferta_set.filter(status=True).order_by('persona__apellido1')

    def total_postulantes(self):
        return self.personaaplicaoferta_set.values('id').filter(status=True).count()

    def total_postulantes_hoy(self):
        return self.personaaplicaoferta_set.values('id').filter(status=True, fecha_creacion__gte=datetime.now().date()).count()

    def puede_aplicar_postulante_nivel(self, persona):
        # QUIEN POSTULA !!!
        #     (0, u'Graduados'),
        #     (1, u'Estudiantes'),
        #     (2, u'Ambos'),
        if not self.permite_aplicar():
            return False
        inscripciones = Inscripcion.objects.filter(status=True, carrera_id__in=self.oferta_carreras_total(), persona=persona, coordinacion__id__lte=5).values_list('id', flat=True)
        solicitud = SolicitudRevisionTitulo.objects.filter(inscripcion_id__in=inscripciones, estado=1).exists()
        graduado = Graduado.objects.filter(status=True, inscripcion_id__in=inscripciones).exists()
        if self.quienpostula == 0:
            return graduado or solicitud
        elif self.quienpostula == 1:
            return inscripciones.exists()
        return graduado or inscripciones.exists() or solicitud

    def permite_aplicar(self):
        if not self.ffinpostlacion:
            return False
        return self.finiciopostulacion <= datetime.now().date() <= self.ffinpostlacion

    def existe_relacion(self):
        return not self.personaaplicaoferta_set.values('id').exists()

    def vigente_str(self):
        return 'fa fa-check-circle text-success' if self.vigente else 'fa fa-times-circle text-error'

    def puede_eliminar(self):
        return not self.personaaplicaoferta_set.values('id').exists() and not self.estadooferta == 1

    def tiene_carrerasrelacionadas(self):
        return self.carrerarelacionada.filter(status=True).exclude(id__in=self.carrera.values_list('id', flat=True))

    def oferta_carreras_total(self):
        dat = []
        car = self.carrera.values_list('id', flat=True)
        for c in car:
            dat.append(c)
        if self.tiene_carrerasrelacionadas():
            for c in self.tiene_carrerasrelacionadas().values_list('id', flat=True):
                dat.append(c)
        return dat

    def __str__(self):
        return '{}'.format(self.titulo)

    class Meta:
        verbose_name = u"Oferta laboral"
        verbose_name_plural = u"Ofertas laborales"


class PersonaAplicaOferta(ModeloBase):
    persona = models.ForeignKey('sga.Persona', blank=True, null=True, on_delete=models.PROTECT, verbose_name=u"Persona")
    oferta = models.ForeignKey(OfertaLaboralEmpresa, blank=True, null=True, on_delete=models.PROTECT, verbose_name=u"Oferta Aplicada")
    obsgeneral = models.TextField(default='', verbose_name='Observación General')
    estado = models.IntegerField(choices=ESTADOS_APLICACION, default=0, verbose_name=u'Estado Postulación')
    opc_hojavida = models.IntegerField(choices=OPCION_OBSERVACION_HOJAVIDA, default=0, verbose_name=u'Opciones de Observacion Hoja de Vida')
    observacionhojavida = models.CharField(default='', max_length=500, verbose_name=u"Motivo hoja de vida")
    revisado_por = models.ForeignKey(User, on_delete=models.PROTECT, related_name='+', blank=True, null=True, verbose_name='Revisado por')
    fecha_revision = models.DateTimeField(blank=True, null=True, verbose_name='Fecha Revisión')
    fecha_contrato = models.DateTimeField(blank=True, null=True, verbose_name='Fecha Contratación')
    aceptaterminos = models.BooleanField(default=True, verbose_name='¿Aceptó terminos?')
    estcontrato = models.IntegerField(choices=ESTADOS_CONTRATO, default=0, verbose_name=u'Estado Contrato')
    opc_contrato = models.IntegerField(choices=OPCION_OBSERVACION_CONTRATO, default=0,
                                       verbose_name=u'Opciones de Observacion Contrato')
    observacioncontrato = models.CharField(default='', max_length=500, verbose_name=u"Motivo Contrato")
    #estadocontrato = models.BooleanField(default=False, verbose_name='¿Contratado?')

    def estado_color(self):
        estados = ['badge-warning', 'badge-info', 'badge-success', 'badge-important']
        return estados[int(self.estado)]

    def __str__(self):
        return '{} [{}]'.format(self.persona.__str__(), self.oferta.__str__())

    def save(self, *args, **kwargs):
        super(PersonaAplicaOferta, self).save(*args, **kwargs)

    class Meta:
        verbose_name = u"Persona Partida"
        verbose_name_plural = u"Persona Partida"


class TerminosAplicaOferta(ModeloBase):
    termino = models.TextField(default='', null=True, blank=True, verbose_name='Termino')
    activo = models.BooleanField(default=True, verbose_name='Activo?')

    def __str__(self):
        return 'Termino N° {}'.format(self.pk)


class OfertaTermino(ModeloBase):
    oferta = models.ForeignKey(OfertaLaboralEmpresa, blank=True, null=True, on_delete=models.PROTECT, verbose_name=u"Oferta")
    termino = models.ForeignKey(TerminosAplicaOferta, blank=True, null=True, on_delete=models.PROTECT, verbose_name=u"Oferta")

    def __str__(self):
        return '{} - {}'.format(self.oferta, self.termino)


class CurriculumPersona(ModeloBase):
    persona = models.ForeignKey('sga.Persona', blank=True, null=True, on_delete=models.PROTECT, verbose_name=u"Persona")
    documentocurriculum = models.FileField(upload_to='empleo/curriculum/', blank=True, null=True,verbose_name=u'Curriculum PDF')


class SolicitudRevisionTitulo(ModeloBase):
    inscripcion = models.ForeignKey('sga.Inscripcion', blank=True, null=True, on_delete=models.PROTECT, verbose_name=u"Inscripcion")
    descripcion = models.TextField(default='', null=True, blank=True, verbose_name='Descripcion')
    personaaprueba = models.ForeignKey('sga.Persona', blank=True, null=True, on_delete=models.PROTECT, verbose_name=u"Persona aprueba")
    estado = models.IntegerField(choices=ESTADOS_SOLICITUD, default=0, verbose_name=u'Estado solicitud')
    fechaaprueba = models.DateTimeField(blank=True, null=True, verbose_name='Fecha Revisión')
    observacion = models.TextField(default='', null=True, blank=True, verbose_name='observacion')
    evicencia = models.FileField(upload_to='empleo/titulos/', blank=True, null=True, verbose_name=u'Evidencia Titulo')

    def __str__(self):
        return 'Solicitud N° {} - {}'.format(self.pk, self.inscripcion.persona.nombre_completo_minus())

    class Meta:
        verbose_name = u"Solicitud de revisión de titulo"
        verbose_name_plural = u"Solicitudes de revisión de titulos"

class ResponsableConvenio(ModeloBase):
    convenio = models.ForeignKey('sga.ConvenioEmpresa', on_delete=models.CASCADE, verbose_name='Convenio Empresa')
    persona = models.ForeignKey(Persona, on_delete=models.CASCADE, verbose_name='Responsable interno del convenio')
    cargo = models.ForeignKey("sagest.DenominacionPuesto", on_delete=models.CASCADE, blank=True, null=True, verbose_name=u"Cargo del responsable")

    def __str__(self):
        return f'{self.persona} - {self.cargo}'

    class Meta:
        verbose_name = u"Responsable Convenio"
        verbose_name_plural = u"Responsables de Convenios"
        ordering = ['-fecha_creacion',]

