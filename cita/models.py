from django.db import models
from django.db.models.functions import Coalesce
import datetime


from sga.funciones import remover_caracteres_tildes_unicode
from datetime import datetime, timedelta, date
from dateutil.relativedelta import relativedelta
from sga.models import *

# TUPLAS
PRIORIDAD_SERVICIO = (
    (1, u'Alta'),
    (2, u'Media'),
    (3, u'Baja')
)

UBICACION = (
    (1, u'Superior'),
    (2, u'Inferior'),
)

SECCION = (
    (1, u'Acerca de nosotros'),
    (2, u'Áreas'),
    (3, u'Noticias'),
    (4, u'Eventos'),
    (5, u'Nuestro Equipo'),
)

TIPO_RESPONSABLE = ((0, u'Principal'), (1, u'General'), (2, u'Específico'))

ESTADO_SOLICITUD_SERVICIO = (
    (0, u'Pendiente'),
    (1, u'Agendado'),
    (2, u'Anulado'),
    (3, u'Corregir'),
    (4, u'Rechazado'),
    (5, u'Finalizado'),
    (6, u'En trámite')

)

ESTADOS_DOCUMENTOS_SOLICITUD = (
    (0, u'Pendiente'),
    (1, u'Aprobado'),
    (2, u'Corregir'),
    (3, u'Rechazado'),
    (4, u'Corregido'),
    (5, u'Solicitar'),
)

TIPO_ATENCION = (
    (0, u'Todos'),
    (1, u'Presencial'),
    (2, u'Virtual')
)

CONF_SERVICIOS = (
    (0, u''),
    (1, u'Unemi Empleo'),
    (2, u'Encuestas Unemi'),
    (3, u'Orgullosamente Unemi')
)

TIPO_PROCESOS = (
    (1, u'Proceso Cognitivo'),
    (2, u'Adaptaciones de Acceso '),
    (3, u'Otros'),
)

NIVEL_ACADEMICO = (
    (1, u'Primaria'),
    (2, u'Secundaria'),
    (3, u'Tercer Nivel'),
    (4, u'Cuarto Nivel'),
    (5, u'PHD'),
    (6, u'Ninguno'),
)

GRADO_ACADEMICO = (
    (1, u'Primero'),
    (2, u'Segundo'),
    (3, u'Tercero'),
    (4, u'Cuarto'),
    (5, u'Quinto'),
    (6, u'Sexto'),
    (7, u'Septimo'),

)
TIPO_INFORME_PSICOLOGICO = (
    (1, u'Informe Clinico'),
    (2, u'Informe Psicopedagógico'),
    (3, u'Informe Psicometrico'),
    (4, u'Informe Refuerzo Academico'),

)
TIPO_NIVEL_ACADEMICO = (
    (1, u'Inicial I '),
    (2, u'Inicial II'),
    (3, u'Preparatoria ( 1º grado de Educación General Básica)'),
    (5, u'Básica Elemental (2º, 3º, 4º grado de Educación General Básica)'),
    (6, u'Básica Media (5º, 6º, 7º grado de Educación General Básica)'),
    (7, u'Básica Superior (8º, 9º, 10º grado de Educación General Básica)'),
    (8, u'1º de Bachillerato'),
    (9, u'2º de bachillerato'),
    (10, u'3º de bachillerato'),
    (11, u'Bachiller'),
    (12, u'Tecnólogo'),
    (13, u'Estudios Universitarios en proceso'),
    (14, u'Egresado Universitario'),
    (15, u'Tercer Nivel'),
    (16, u'Posgrado'),
    (17, u'PHD'),
    (18, u'Otros'),

)
# TIPO_ESTRUCTURA = (
#     (1, u'General'),
#     (2, u'Areas evaluadas'),
#     (3, u'Tecnicas e Instrumentos'),
#     (4, u'Informe Potencialidades '),
#     (5, u'Informe Necesidades '),
#     (6, u'Test '),
#
# )

TIPO_SEGMENTACION = (
    (1, u'Top izquierda'),
    (2, u'Top derecha'),
    (3, u'Centro'),
    (4, u'Centro combinado'),

)


CENTRO_CUIDADO=(
    (1, 'Centro de cuidado público'),
    (2, 'Centro de cuidado privado'),
    (3, 'Centro de educativo público'),
    (4, 'Centro de educativo privado'),
    (5, 'Otros(especifique)'),
)
# TIPO_GESTION_VINCULACION = (
#     (1, u'Centro de Asesoría y Defensa Jurídica'),
#     (2, u'Centro del Consultorio Psicológico '),
#     (3, u'Gestión de Proyectos de Servicio Comunitarios '),
#     (4, u'Unidad de Emprendimiento'),
#     (5, u'Seguimiento a Graduados'),
#     (6, u'Gestión de Difunción Cultural y Artística '),
#     (7, u'Practicas Pre Profesionales '),
#
#
# )
TIPO_PUBLICACION=(
    (1, 'Noticias Generales'),
    (2, 'Tips'),
    (3, 'Eventos'),
    (4, 'Normativas'),
    (5, 'Resoluciones'),
    (6, 'Otros'),

)
TIPO_WEBINAR=(
    (1, 'PROXIMAMENTE'),
    (2, 'FINALIZADO'),
    (3, 'INFORMATIVO'),
    (4, 'VIGENTE'),
)

TIPO_ORDEN = (
    (1, u'Top 1'),
    (2, u'Top 2'),
    (3, u'Top 3'),
    (4, u'Top 3'),

)
# TABLAS PADRES
class TurnoCita(ModeloBase):
    comienza = models.TimeField(verbose_name=u'Comienza')
    termina = models.TimeField(verbose_name=u'Termina')
    mostrar = models.BooleanField(default=False, verbose_name=u"Mostrar")

    def __str__(self):
        return u'Comienza: %s - Termina: %s' % (self.comienza, self.termina)

    def nombre_horario(self):
        return self.comienza.strftime("%H:%M") + ' a ' + self.termina.strftime("%H:%M")

    def fechas_horarios(self):
        return self.comienza.strftime('%d-%m-%Y') + " al " + self.fechafin.strftime('%d-%m-%Y')

    def en_uso(self):
        return self.horarioserviciocita_set.filter(status=True).exists()

    class Meta:
        verbose_name = u"Turno Cita"
        verbose_name_plural = u"Turnos Citas"
        # unique_together = ('comienza', 'termina',)

class DepartamentoServicio(ModeloBase):
    nombre = models.CharField(max_length=100, verbose_name=u'Nombre')
    departamento = models.ForeignKey('sagest.Departamento', on_delete=models.CASCADE, blank=True, null=True, verbose_name=U'Departamento de Servicio')
    responsable = models.ManyToManyField('sga.Persona', verbose_name='Responsable configuracion de servicio')
    descripcion = models.CharField(default='', max_length=5000, verbose_name=u'Descripción')
    portada = models.FileField(upload_to='agendamientocitas', blank=True, null=True,verbose_name=u'Portada de Departamento')
    gestion = models.ForeignKey('sagest.SeccionDepartamento', blank=True, null=True, verbose_name=u"Gestión",
                                on_delete=models.CASCADE)
    nombresistema = models.CharField(max_length=100, blank=True, null=True, verbose_name=u'Nombre de sistema')
    tiposistema = models.CharField(max_length=100, blank=True, null=True, verbose_name=u'Tipo de sistema')
    url_entrada = models.CharField(max_length=100, blank=True, null=True, verbose_name=u'Url del sistema')
    logonavbar =  models.FileField(upload_to='gestionvinculacion/logonavbar', blank=True, null=True,
                                verbose_name=u'Logo del navbar')
    logofooter = models.FileField(upload_to='gestionvinculacion/logofooter', blank=True, null=True,
                                  verbose_name=u'Logo del Footer')

    def get_portada(self):
        if self.logonavbar:
            return self.logonavbar.url

    def get_footer(self):
        if self.logofooter:
            return self.logofooter.url

    def nombre_input(self):
        return remover_caracteres_especiales_unicode(self.nombre).lower().replace(' ', '_')

    def servicio_configurado(self):
        return ServicioConfigurado.objects.filter(status=True, serviciocita__departamentoservicio=self)

    def en_uso(self):
        return self.serviciocita_set.filter(status=True, mostrar=True).exists()

    def __str__(self):
        return self.nombre

    def save(self, *args, **kwargs):
        self.nombre = self.nombre.upper()
        super(DepartamentoServicio, self).save(*args, **kwargs)

    class Meta:
        verbose_name = 'Departamento Servicio'
        verbose_name_plural = 'Departamentos Servicios'
        ordering = ('-id',)

class MotivoCita(ModeloBase):
    departamentoservicio = models.ForeignKey(DepartamentoServicio, blank=True, null=True, on_delete=models.CASCADE,
                                             verbose_name='Departamento de servicio')
    descripcion = models.CharField(default='', max_length=5000, verbose_name=u'Descripción')

    def __str__(self):
        return "{}".format(self.descripcion)

    class Meta:
        verbose_name = u"Motivo de Cita"
        verbose_name_plural = u"Motivo de Citas"

# class DetalleMotivoCita(ModeloBase):
#     motivocita = models.ForeignKey(MotivoCita, blank=True, null=True, on_delete=models.CASCADE,
#                                              verbose_name='Motivos de citas')
#     codigo = models.CharField(max_length=20, verbose_name='Codigo del submotivo', blank=True, null=True)
#     descripcion= models.CharField(default='', max_length=5000, verbose_name=u'Descripción submotivo')
#
#     def __str__(self):
#         return "{}".format(self.descripcion)
#
#     class Meta:
#         verbose_name = u"Submotivo de Cita"
#         verbose_name_plural = u"Submotivos de Citas"

class ServicioCita(ModeloBase):
    departamentoservicio = models.ForeignKey(DepartamentoServicio,blank=True, null=True, on_delete=models.CASCADE, verbose_name='Departamento de servicio')
    nombre = models.CharField(max_length=100, verbose_name=u'Nombre')
    descripcion = models.CharField(default='', max_length=5000, verbose_name=u'Descripción')
    cuerpodescripcion = models.TextField(default='', blank=True, null=True, verbose_name=u'Contenido del servicio')
    portada = models.FileField(upload_to='agendamientocitas', blank=True, null=True,verbose_name=u'Portada de Servicio')
    link_atencion = models.CharField(default='', max_length=5000, verbose_name=u'Enlace de atención  de zoom')
    tipo_atencion = models.IntegerField(choices=TIPO_ATENCION, null=True, blank=True, verbose_name=u'Tipo de atención')
    gestion_servicio = models.IntegerField(choices=CONF_SERVICIOS, null=True, blank=True, verbose_name=u'Tipo de atención')
    mostrar = models.BooleanField(default=False, verbose_name=u'Mostrar Servicio')
    lugar = models.CharField(default='', max_length=5000, verbose_name=u'Lugar de atención presencial')
    bloque = models.ForeignKey('sagest.Bloque', blank=True, null=True, on_delete=models.CASCADE, verbose_name='Bloque de atención')
    responsable = models.ForeignKey('sga.Persona',  blank=True, null=True, on_delete=models.PROTECT, verbose_name='Responsable de servicio')
    motivos = models.ManyToManyField(MotivoCita, verbose_name='Motivos de cita')

    def save(self, *args, **kwargs):
        self.nombre = self.nombre.upper()
        super(ServicioCita, self).save(*args, **kwargs)

    def get_portada(self):
        if self.portada:
            return f'https://sga.unemi.edu.ec/{self.portada.url}'
        else:
            return f'/static/images/serviciosvinculacion/psicometria.jpg'

    def nombre_input(self):
        return remover_caracteres_especiales_unicode(self.nombre).lower().replace(' ', '_')

    def procesos(self):
        return self.proceso_set.filter(mostrar=True,status=True)

    def procesos_tipoinforme(self, tipoinforme):
        return self.proceso_set.filter(mostrar=True,status=True, tipoinforme=tipoinforme)

    def __str__(self):
        return self.nombre

    class Meta:
        verbose_name = 'Servicio de Cita'
        verbose_name_plural = 'Servicios de Citas'
        ordering = ('id',)

class Requisito(ModeloBase):
    nombre = models.CharField(max_length=100, verbose_name=u'Nombre')
    descripcion = models.CharField(default='', max_length=5000, verbose_name=u'Descripción')

    def __str__(self):
        return u'%s' % (self.nombre)

    def nombre_input(self):
        return remover_caracteres_especiales_unicode(self.nombre).lower().replace(' ', '_')

    def en_uso(self):
        return self.requisitoserviciocita_set.filter(status=True).exists()

    def save(self, *args, **kwargs):
        self.nombre = self.nombre.upper()
        super(Requisito, self).save(*args, **kwargs)

    class Meta:
        verbose_name = 'Requisito Servicio'
        verbose_name_plural = 'Requisitos Servicios'
        ordering = ('-id',)


# TABALAS HIJOS
class ServicioConfigurado(ModeloBase):
    nombre = models.CharField(max_length=100, blank=True, null=True, verbose_name=u'Nombre de configuracion')
    serviciocita = models.ForeignKey(ServicioCita, on_delete=models.CASCADE, verbose_name='Servicio Cita')
    # descripcion = models.CharField(default='', max_length=5000, verbose_name=u'Descripción')
    # portada = models.FileField(upload_to='agendamientocitas', blank=True, null=True,verbose_name=u'Portada de Servicio')
    prioridad = models.IntegerField(choices=PRIORIDAD_SERVICIO, null=True, blank=True, verbose_name=u'Prioridad')
    # departamento = models.ForeignKey('sagest.Departamento', on_delete=models.CASCADE, blank=True, null=True,verbose_name=U'Departamento de Servicio')
    mostrar = models.BooleanField(default=False, verbose_name=u'Mostrar')
    cupo = models.IntegerField(default=0, verbose_name=u"Cantidad maxima de cupos disponibles por turno")
    numdias = models.IntegerField(default=0, verbose_name='Número de días para reservación')
    numdiasinicio = models.IntegerField(default=0, verbose_name='Número de inicios de días para reservación')
    soloadministrativo = models.BooleanField(default=False, verbose_name=u'Solo disponible para Administrativos')
    def  generar_turno(self, persona):
        persona_cita = PersonaCitaAgendada.objects.filter(persona=persona)
        num = str(len(persona_cita) + 1)
        if len(num) == 1:
            num = '000' + num
        elif len(num) == 2:
            num = '00' + num
        elif len(num) == 3:
            num = '0' + num
        servicio = (self.nombre[0:3]).upper()
        arreglo = str(persona).split()
        siglas = ''
        for letra in arreglo:
            siglas += letra[:1]
        return str(siglas + '-' + servicio + '-' + num)

    def __str__(self):
        return u'%s | %s' % (self.serviciocita, self.nombre)

    def responsable_departamento(self):
        return self.serviciocita.departamentoservicio.responsable

    def nombre_input(self):
        return remover_caracteres_especiales_unicode(self.serviciocita.nombre).lower().replace(' ', '_')

    def responsables(self):
        return self.responsableserviciocita_set.filter(status=True)

    def responsables_activos(self):
        return self.responsableserviciocita_set.filter(status=True, activo=True)

    def requisitos(self):
        return self.requisitoserviciocita_set.filter(status=True)

    def requisitos_visibles(self):
        return self.requisitoserviciocita_set.filter(status=True, mostrar=True)

    def requisitos_sin_archivos(self):
        return self.requisitoserviciocita_set.filter(status=True, mostrar=True, archivo=False)

    def requisitos_excl(self, cita):
        ids_excl = cita.documentos_subidos().filter(obligatorio=True, archivo__isnull=False).values_list('requisito__requisito_id', flat=True)
        ids_fil = cita.documentos_subidos().filter(obligatorio=False, archivo__isnull=True).values_list('requisito__requisito_id', flat=True)
        return self.requisitoserviciocita_set.filter(Q(id__in=ids_fil) | Q(status=True, mostrar=True, archivo=True)).exclude(requisito_id__in=ids_excl)

    def requisitos_con_archivos(self):
        return self.requisitoserviciocita_set.filter(status=True, mostrar=True, archivo=True)

    def horarios_activos(self, dia, turno):
        horarios = HorarioServicioCita.objects.filter(dia=dia, responsableservicio__servicio=self,
                                                      status=True).order_by('turno')
        return horarios.filter(turno=turno) if horarios.exists() else ""

    def existe_cita_agendada(self, persona):
        return PersonaCitaAgendada.objects.filter(status=True, horario__responsableservicio__servicio=self,
                                                  estado__in=[0, 1], persona=persona).exists()

    class Meta:
        verbose_name = 'Servicio Configurado'
        verbose_name_plural = 'Servicios Configurados'
        ordering = ('-id',)


class RequisitoServicioCita(ModeloBase):
    servicio = models.ForeignKey(ServicioConfigurado, on_delete=models.CASCADE, verbose_name='Servicio Configurado')
    requisito = models.ForeignKey(Requisito, on_delete=models.CASCADE, verbose_name='Requisitos')
    mostrar = models.BooleanField(default=False, verbose_name=u'Mostrar')
    opcional = models.BooleanField(default=False, verbose_name='Requisito opcional')
    archivo = models.BooleanField(default=False, verbose_name='Requisito con archivo')

    def __str__(self):
        return u'%s %s' % (self.requisito, self.servicio)

    def documentos_subidos(self):
        return self.documentossolicitudservicio_set.filter(status=True).order_by('-id')

    def documento_subido(self, id):
        return self.documentossolicitudservicio_set.filter(status=True, cita_id=id).first()

    class Meta:
        verbose_name = 'Requisito Servicio'
        verbose_name_plural = 'Requisitos Servicios'
        ordering = ('-id',)

class ResponsableGrupoServicio(ModeloBase):
    responsable = models.ForeignKey('sga.Persona', on_delete=models.PROTECT, verbose_name='Responsable')
    descripcion = models.CharField(default='', max_length=10000, verbose_name=u'Descripción')
    cargo = models.CharField(default='', max_length=200, verbose_name=u'Describa el cargo')
    departamentoservicio = models.ForeignKey(DepartamentoServicio, blank=True, null=True, on_delete=models.CASCADE,
                                             verbose_name='Departamento de servicio')
    activo = models.BooleanField(default=False, verbose_name=u'Activo')
    abreviatura = models.CharField(default='', max_length=100, verbose_name=u'Describa abreviatura cadémico')


    # servicio = models.ForeignKey(ServicioConfigurado, on_delete=models.PROTECT, verbose_name='Servicio Configurado')
    def __str__(self):
        return u'%s' % (self.responsable)

    class Meta:
        verbose_name = u"Responsable Grupo Servicio"
        verbose_name_plural = u"Responsables Grupos Servicios"

class ResponsableServicioCita(ModeloBase):
    servicio = models.ForeignKey(ServicioConfigurado, on_delete=models.PROTECT, verbose_name='Servicio Configurado')

    responsable = models.ForeignKey('sga.Persona', on_delete=models.PROTECT, verbose_name='Responsable')
    activo = models.BooleanField(default=False, verbose_name=u'Activo')
    tipo = models.IntegerField(choices=TIPO_RESPONSABLE, null=True, blank=True, verbose_name=u'Tipo Responsable')
    responsablegruposervicio = models.ForeignKey(ResponsableGrupoServicio,  null=True, blank=True, on_delete=models.PROTECT, verbose_name='Responsable Grupo Servicio')

    def __str__(self):
        return u'%s | %s' % (self.responsable.nombre_completo_minus(), self.get_tipo_display())

    class Meta:
        verbose_name = u"Responsable de servicio"
        verbose_name_plural = u"Responsables de servicios"
        ordering = ('-id',)


class HorarioServicioCita(ModeloBase):
    responsableservicio = models.ForeignKey(ResponsableServicioCita, on_delete=models.PROTECT, null=True, blank=True,verbose_name='Responsable de atencion en horario')
    servicio = models.ForeignKey(ServicioConfigurado,null=True, blank=True, on_delete=models.PROTECT, verbose_name='Servicio Configurado')
    turno = models.ForeignKey(TurnoCita, on_delete=models.PROTECT, verbose_name='Turno')
    dia = models.IntegerField(choices=DIAS_CHOICES, default=0, verbose_name=u'Dia')
    fechainicio = models.DateField(blank=True, null=True, verbose_name=u'Fecha Inicial')
    fechafin = models.DateField(blank=True, null=True, verbose_name=u'Fecha Fin')
    mostrar = models.BooleanField(default=False, verbose_name=u'Mostrar')
    tipo_atencion = models.IntegerField(choices=TIPO_ATENCION, null=True, blank=True, verbose_name=u'Tipo de atención')
    def __str__(self):
        return u'%s %s' % (self.responsableservicio.servicio, self.turno)

    def to_dict(self):
        return {
            'id': self.id,
            'horario_display':self.get_tipo_atencion_display,
            'responsable_servicio': self.responsableservicio.id if self.responsableservicio else None,
            'servicio_configurado': self.servicio.id if self.servicio else None,
            'turno': self.turno.id,
            'dia': self.dia,
            'fechainicio': str(self.fechainicio) if self.fechainicio else None,
            'fechafin': str(self.fechafin) if self.fechafin else None,
            'mostrar': self.mostrar,
            'tipo_atencion': self.tipo_atencion,
        }

    def en_uso(self):
        return self.personacitaagendada_set.filter(
            status=True
        ).exclude(
            Q(estado=2) | Q(estado=4)
        ).exists()
        #return  self.personacitaagendada_set.filter(status = True).exclude(estado_in=[2,4]).exists()

    def generar_turno(self, persona):
        persona_cita = PersonaCitaAgendada.objects.filter(persona=persona)
        num = str(len(persona_cita) + 1)
        if len(num) == 1:
            num = '000' + num
        elif len(num) == 2:
            num = '00' + num
        elif len(num) == 3:
            num = '0' + num
        servicio = (self.responsableservicio.servicio.serviciocita.nombre[0:3]).upper()
        arreglo = str(persona).split()
        siglas = ''
        for letra in arreglo:
            siglas += letra[:1]
        return str(siglas + '-' + servicio + '-' + num)

    def citas_disponibles(self, fecha):
        try:
            citas = PersonaCitaAgendada.objects.filter(horario=self, status=True, fechacita=fecha, estado__in=[0, 1, 3, 6])
            subcitas = SubCitaAgendada.objects.filter(horario=self, status=True, fechacita=fecha, estado__in=[0, 1, 3, 6])
            return self.responsableservicio.servicio.cupo - len(citas) - len(subcitas)
        except Exception as ex:
            pass

    def horario_disponible(self, fecha):
        disponible = True
        fecha = datetime.strptime(fecha, '%Y-%m-%d').date()
        if fecha == datetime.now().date():
            if datetime.now().time() > self.turno.comienza:
                disponible = False
        return disponible

    def fechas_horarios(self):
        return self.fechainicio.strftime('%d-%m-%Y') + " al " + self.fechafin.strftime('%d-%m-%Y')

    def requisitos_archivo(self):
        return RequisitoServicioCita.objects.filter(status=True, servicio=self.responsableservicio.servicio, mostrar=True, archivo=True)

    def requisitos(self):
        return RequisitoServicioCita.objects.filter(status=True, servicio=self.responsableservicio.servicio, mostrar=True)

    class Meta:
        verbose_name = u"Horario de servicio"
        verbose_name_plural = u"Horarios de servicios"


class PersonaCitaAgendada(ModeloBase):
    codigo = models.CharField(max_length=20, verbose_name='Codigo de cita generado', blank=True, null=True)
    persona = models.ForeignKey('sga.Persona', verbose_name=u'Persona', on_delete=models.CASCADE)
    perfil = models.ForeignKey('sga.PerfilUsuario', blank=True, null=True, verbose_name=u'Perfil Persona',
                               on_delete=models.CASCADE)
    horario = models.ForeignKey(HorarioServicioCita, blank=True, null=True, verbose_name=u'Turno',
                                on_delete=models.CASCADE)
    servicio = models.ForeignKey(ServicioConfigurado, on_delete=models.CASCADE, blank=True, null=True, verbose_name='Servicio Configurado')
    estado = models.IntegerField(choices=ESTADO_SOLICITUD_SERVICIO, default=1, verbose_name=u'Estado')
    fechacita = models.DateField(blank=True, null=True, verbose_name='Fecha de la Cita')
    observacion = models.TextField(default='', null=True, blank=True, verbose_name=u'Observación')
    asistio = models.BooleanField(default=False, verbose_name=u'Asistencia de la Cita')
    persona_responsable = models.ForeignKey(Persona, blank=True, null=True, verbose_name=u"Persona Responsable",related_name='+', on_delete=models.PROTECT)
    tipo_atencion = models.IntegerField(choices=TIPO_ATENCION, null=True, blank=True, verbose_name=u'Tipo de atención')
    escitaemergente= models.BooleanField(null=True,blank=True, default=False, verbose_name=u'Cita emergente')
    comienza = models.TimeField(null=True, blank=True, verbose_name=u'Hora Inicio')
    termina = models.TimeField(null=True, blank=True, verbose_name=u'Hora Fin')
    familiar = models.ForeignKey('sga.PersonaDatosFamiliares', null=True, blank=True, verbose_name=u'Persona Dato Familiar', on_delete=models.CASCADE)
    espersonal = models.BooleanField(null=True, blank=True, default=False, verbose_name=u'Cita personal')
    motivoconsulta = models.ForeignKey(MotivoCita, blank=True, null=True, verbose_name=u"Motivo de Consulta",
                                       on_delete=models.CASCADE)
    descripcionmotivo= models.CharField(default='', max_length=500, verbose_name=u'Descripción del motivo',
                                                 blank=True, null=True)

    def dias_disponibles(self):
        try:
            rangofechasstr, rangofechas, fechahasta, fechadesde = [], [], self.ffinalreserva, self.finicialreserva
            for day in range((fechahasta - fechadesde).days + 1):
                fechafiltro = fechadesde + timedelta(days=day)
                # rangofechas.append("{} {}".format((fechadesde + timedelta(days=day)).strftime("%d"), (fechadesde + timedelta(days=day)).strftime("%b")))
                rangofechas.append(fechafiltro)
            return rangofechas
        except Exception as ex:
            return []

    def obtener_personal_familiar(self):
        if self.espersonal:
            return {
                'tipo': 'Personal',
                'informacion': {
                    'nombre': self.persona.nombre_completo_minus,
                    'cedula': self.persona.cedula,
                    'sexo': self.persona.sexo,
                    'nacimiento': self.persona.nacimiento,
                    'estadocivil': self.persona.estado_civil_descripcion,
                    'credo': self.persona.credo,
                    'email': self.persona.emailinst,
                    'telefono': self.persona.telefono,
                    'ciudad': self.persona.canton.nombre,
                    'direccion': self.persona.direccion_corta,

                }
            }
        else:
            return {
                'tipo': 'Familiar',
                'informacion': {
                    'nombre': self.familiar.nombre_completo_minus,
                    'cedula': self.familiar.identificacion,
                    'sexo': self.familiar.persona.sexo,
                    'nacimiento': self.familiar.obtener_edad,
                    'estadocivil': self.familiar.persona.estado_civil_descripcion,
                    'credo': self.familiar.persona.credo,
                    'email': self.familiar.persona.emailinst,
                    'telefono': self.familiar.persona.telefono,
                    'ciudad': self.familiar.persona.canton.nombre,
                    'direccion': self.familiar.persona.direccion_corta,
                }
            }

    def get_persona(self):
        if not self.familiar:
            return self.persona
        else:
            return self.familiar.personafamiliar

    def color_estado(self):
        color = 'bg-default'
        if self.estado == 1:
            color = "bg-success"
        elif self.estado == 2:
            color = "bg-danger"
        elif self.estado == 3:
            color = "bg-warning"
        elif self.estado == 4:
            color = "bg-danger"
        elif self.estado == 5:
            color = "bg-secondary"
        elif self.estado == 6:
            color = "bg-primary"
        return color
    def color_estado_text(self):
        color = 'text-default'
        if self.estado == 1:
            color = "text-success"
        elif self.estado == 2:
            color = "text-danger"
        elif self.estado == 3:
            color = "text-warning"
        elif self.estado == 4:
            color = "text-danger"
        elif self.estado == 5:
            color = "text-secondary"
        elif self.estado == 6:
            color = "text-primary"
        return color

    def puede_cancelar(self):
        puede=True
        fechaactual = (datetime.now() + timedelta(minutes=14))
        turno = self.horario.turno.comienza
        if self.estado != 0 and self.estado != 1:
            puede=False
        elif datetime.now().date() > self.fechacita:
            puede = False
        elif fechaactual.time() > turno and datetime.now().date() == self.fechacita:
            puede=False
        return puede

    def doc_validacion(self):
        estado=0
        documentos=self.documentossolicitudservicio_set.filter(status=True, obligatorio=True)
        if len(documentos) == len(documentos.filter(estados=1)):
            estado = 1
        elif documentos.filter(estados=2).exists():
            estado=2
        elif documentos.filter(status=True, estados=0).exists():
            estado=0
        return estado

    def doc_porcorregir(self):
        return self.documentossolicitudservicio_set.filter(status=True, estados=2)

    def doc_pendientes(self):
        return self.documentossolicitudservicio_set.filter(status=True, estados=0)

    def doc_aprobados(self):
        return self.documentossolicitudservicio_set.filter(status=True, estados=1)

    def doc_rechazados(self):
        return self.documentossolicitudservicio_set.filter(status=True, estados=3)

    def doc_solicitados(self):
        cont=0
        if not self.estado == 2 and not self.estado == 4 and not self.estado == 5:
            documentos = self.documentossolicitudservicio_set.filter(status=True, estados__in=[0,6])
            for documento in documentos:
                if not documento.archivo and documento.obligatorio:
                    cont+=1
        return cont

    def documentos_subidos(self):
        return self.documentossolicitudservicio_set.filter(status=True).order_by('pk')

    def observaciones(self):
    #     x = self.subcita_set.filter(status=True, persona_responsable__isnull=False).exclude(persona_responsable=self.persona_responsable).order_by('persona_responsable_id').distinct()
    #     #idDerivado = x[0].persona_responsable.id
    #
         return GestionServicioCita.objects.filter(cita=self, status=True).order_by('-pk')

    def responsables_subcitas(self):
        return self.subcita_set.filter(status=True, persona_responsable__isnull=False).exclude(persona_responsable=self.persona_responsable).order_by('persona_responsable_id').distinct()

    def responsables_subcitas_no_duplicados(self):
        responsables = self.subcita_set.filter(status=True, persona_responsable__isnull=False).exclude(
            persona_responsable=self.persona_responsable).order_by('persona_responsable_id')

        responsables_sin_duplicados = []
        ultimo_responsable = None
        for responsable in responsables:
            if responsable.persona_responsable != ultimo_responsable:
                responsables_sin_duplicados.append(responsable.persona_responsable)
                ultimo_responsable = responsable.persona_responsable

        return responsables_sin_duplicados

    def responsables_subcitas_list(self):
        lista=[self.persona_responsable.id]
        subcitas = self.subcita_set.filter(status=True, persona_responsable__isnull=False).exclude(persona_responsable=self.persona_responsable).values_list('persona_responsable_id',flat=True).order_by('persona_responsable_id').distinct()
        return lista + list(subcitas)

    def subcitas(self):
        return SubCitaAgendada.objects.filter(citaprincipal=self, status=True).order_by('fechacita')

    def ultima_subcita(self):
        # Obtener la última subcita agendada para esta cita principal
        ultima_subcita = SubCitaAgendada.objects.filter(citaprincipal=self, status=True).order_by('-fechacita').last()

        return ultima_subcita

    def subcitas_exits(self):
        return SubCitaAgendada.objects.filter(citaprincipal=self, status=True).exists()

    def proceso(self):
        #return self.servicio.serviciocita.departamentoservicio.proceso_set.filter(mostrar=True)
        return self.servicio.serviciocita.proceso_set.filter(mostrar=True)

    def get_gestion(self):
        return self.servicio.serviciocita.departamentoservicio.gestion

    def get_gestionservicio(self):
        return self.servicio.serviciocita.departamentoservicio

    def get_informepsicologico(self, tipo):
        return self.informepsicologico_set.filter(status=True, tipoinforme=tipo).first()

    def servicio_persona(self, persona):
        subcita = self.subcitas().filter(es_derivacion=True, persona_responsable=persona).exclude(
            citaprincipal__persona_responsable=persona).order_by('servicio_id').distinct().first()
        if subcita:
            return subcita.servicio.serviciocita
        else:
            return self.servicio.serviciocita

    def formulario_activo(self, persona):
        tiposervicios = {5: 2, 6: 1, 7: 3, 8: 4}
        subcita = self.subcitas().filter(es_derivacion=True, persona_responsable=persona).exclude(
            citaprincipal__persona_responsable=persona).order_by('servicio_id').distinct().first()
        tipoinforme= None
        if subcita:
            tipoinforme = tiposervicios[subcita.servicio.serviciocita.id]
        elif self.servicio.serviciocita.id in [5, 6, 7, 8]:
            tipoinforme = tiposervicios[self.servicio.serviciocita.id]
        return  tipoinforme

    def get_informe_tipo(self, tipoinforme):
        return self.informepsicologico_set.filter(status=True,tipoinforme=tipoinforme).first()

    def get_procesos(self, tipoinforme):
        informe = self.informepsicologico_set.filter(status=True,tipoinforme=tipoinforme).first()
        detalleinforme = DetalleHistorialPsicologico.objects.filter(informe = informe, status=True).select_related('proceso')

        #psicopedagogico
        if tipoinforme == 2:
            subtituloProcesos = {}
            for x in detalleinforme:
                detalleprocesos = []
                subtitulo = x.proceso.subtitulo

                detalleprocesos.append({
                    'descripcion': x.proceso.descripcion,
                    'marcada': x.marcada,
                    'observacion': x.observacion,
                    'subtitulo': subtitulo
                })
                if subtitulo in subtituloProcesos:
                    subtituloProcesos[subtitulo]['detalleprocesos'].extend(detalleprocesos.copy())
                else:
                    # Si el subtitulo no existe, agrega una nueva entrada en subtituloProcesos
                    subtituloProcesos[subtitulo] = {
                        'valor_subtitulo': subtitulo,
                        'detalleprocesos': detalleprocesos.copy()
                    }

            return subtituloProcesos

        return detalleinforme
        #return proceso.detallehistorialpsicologico_set.all()



    def __str__(self):
        return "{} ({})".format(self.persona, self.horario)

    class Meta:
        verbose_name = u"Solicitud Servicio Cita"
        verbose_name_plural = u"Solicitudes Servicios Citas"

class EstructuraInforme(ModeloBase):
    servicio = models.ForeignKey(ServicioCita, blank=True, null=True, verbose_name=u"Servicios",
                                 on_delete=models.CASCADE)
    tipoinforme = models.IntegerField(choices=TIPO_INFORME_PSICOLOGICO, null=True, blank=True,
                                      verbose_name=u'Tipo de informe')
    titulo = models.TextField(default='', blank=True, null=True, verbose_name='Titulo')
    activo = models.BooleanField(default=False,verbose_name=u'Mostrar')
    orden = models.IntegerField(default=False, null=True, blank=True, verbose_name='Orden')
    segmentacion = models.IntegerField(choices=TIPO_SEGMENTACION , null=True, blank=True,
                                      verbose_name=u'Tipo de Segmentación')
    seccion = models.IntegerField(default=False, null=True, blank=True, verbose_name='Sección')
    def __str__(self):
        return "{}".format(self.titulo)

    def get_tipoinforme_display(self):
        return dict(TIPO_INFORME_PSICOLOGICO).get(int(self.tipoinforme), '')



    class Meta:
        verbose_name = u"Estructura Informe"
        verbose_name_plural = u"Estructuras Informes"


class InformePsicologico(ModeloBase):
    codigo = models.CharField(max_length=9, verbose_name='Historia Clinica N°', blank=True, null=True)
    personacita = models.ForeignKey(PersonaCitaAgendada, blank=True, null=True, verbose_name=u"Cita agendada",
                             on_delete=models.CASCADE)
    motivoconsulta= models.ForeignKey(MotivoCita, blank=True, null=True, verbose_name=u"Motivo de Consulta",
                             on_delete=models.CASCADE)
    descripcionmotivoconsulta = models.CharField(default='', max_length=5000, verbose_name=u'Descripción del motivo', blank=True, null=True)

    archivo = models.FileField(upload_to='agendamientocitas/historialclinico', blank=True, null=True, verbose_name=u'Archivo')
    # niveltitulacion = models.ForeignKey('sga.NivelTitulacion', blank=True, null=True, verbose_name=u"Cita agendada",
    #                          on_delete=models.CASCADE)
    niveltitulacion = models.IntegerField(choices=TIPO_NIVEL_ACADEMICO, null=True, blank=True, verbose_name=u'Nivel academico')
    tipoinforme = models.IntegerField(choices=TIPO_INFORME_PSICOLOGICO , null=True, blank=True,
                                      verbose_name=u'Tipo de informe')
    grado = models.IntegerField(default=False, null=True, blank=True, verbose_name='Grado')
    institucioneducativa = models.CharField(max_length=200, blank=True, null=True,
                                            verbose_name=u"Institución Educativa")

    # institucioneducativa = models.ForeignKey(InstitucionesColegio, blank=True, null=True, verbose_name=u"Instituciones Educativas",
    #                          on_delete=models.CASCADE)


    def __str__(self):
        return "{} {}".format(self.personacita, self.motivoconsulta)

    def obtener_ultimo_secuencial_con_ceros(servicio):
        #ultimo_secuencial = InformePsicologico.objects.values_list('codigo', flat=True).order_by('-codigo').first()

        mi_tipoinforme = 0
        if servicio == 5:
            mi_tipoinforme = 2

        if servicio == 7:
            mi_tipoinforme = 3

        if servicio == 6:
            mi_tipoinforme = 1

        ultimo_secuencial = InformePsicologico.objects.filter(tipoinforme=mi_tipoinforme).values_list('codigo', flat=True).order_by('-codigo').first()

        if ultimo_secuencial is not None:
            # Obtener el número entero a partir del código
            ultimo_numero = int(ultimo_secuencial)

            # Incrementar el número
            nuevo_numero = ultimo_numero + 1

            # Formatear con ceros a la izquierda
            nuevo_codigo = f'{nuevo_numero:09}'  # 9 es la longitud total deseada

            return nuevo_codigo
        else:
            # Si no hay registros, comenzar con "000000001"
            return '000000001'

    def obtener_familiares(self):
        if not self.personacita.espersonal:
            return self.personacita.persona.familiares().order_by('-id')
        elif self.personacita.familiar:
            return self.personacita.familiar.personafamiliar.familiares().order_by('-id')
        else:
            return None

    def repuestas_informe(self):
        lista= []
        estructuras = EstructuraInforme.objects.filter(tipoinforme=self.tipoinforme, activo=True)
        for e in estructuras:
            respuesta = e.detalleinformepsicologico_set.filter(status=True, informe=self).first()
            if respuesta:
                lista.append(respuesta)
        return lista

    class Meta:
        verbose_name = u"Informe Psicologico"
        verbose_name_plural = u"Informes Psicologicos"

class CabRefuerzoAcademico(ModeloBase):

    asignatura = models.CharField(default='', max_length=5000, verbose_name=u'Asignatura', blank=True, null=True)
    grado_egb = models.CharField(default=False,max_length=5000, null=True, blank=True, verbose_name='Grado EGB')

    def __str__(self):
        return "{}".format(self.asignatura)
    class Meta:
        verbose_name = u"Informe Refuezo Academico"
        verbose_name_plural = u"Informes Refuerzos Academicos"


class DetRefuerzoAcademico(ModeloBase):
    cabrefuerzo = models.ForeignKey(CabRefuerzoAcademico, blank=True, null=True, verbose_name=u"Cabecera del refuerzo academico",
                                    on_delete=models.CASCADE)
    personacita = models.ForeignKey(PersonaCitaAgendada, blank=True, null=True, verbose_name=u"Cita agendada",
                                    on_delete=models.CASCADE)
    destreza = models.CharField(default='', max_length=5000, verbose_name=u'Destreza', blank=True, null=True)
    actividad = models.CharField(default='', max_length=5000, verbose_name=u'Actividad', blank=True, null=True)
    observacion = models.CharField(default='', max_length=5000, verbose_name=u'Observación', blank=True, null=True)
    fecha = models.DateField(blank=True, null=True, verbose_name='Fecha del refuerzo')

    def __str__(self):
        return "{}".format(self.cabrefuerzo)

    class Meta:
        verbose_name = u" Detalle Informe Refuezo Academico"
        verbose_name_plural = u" Detalles Informes Refuerzos Academicos"

class RefuerzoAcademico(ModeloBase):
    personacita = models.ForeignKey(PersonaCitaAgendada, blank=True, null=True, verbose_name=u"Cita agendada",
                                    on_delete=models.CASCADE)
    destreza = models.CharField(default='', max_length=5000, verbose_name=u'Destreza', blank=True, null=True)
    archivo = models.FileField(upload_to='AgendamientoCita/GestionRefuerzo', blank=True, null=True,
                               verbose_name=u'Archivo')

    actividad = models.CharField(default='', max_length=5000, verbose_name=u'Actividad', blank=True, null=True)
    observacion = models.CharField(default='', max_length=5000, verbose_name=u'Observación', blank=True, null=True)
    fecha = models.DateField(blank=True, null=True, verbose_name='Fecha del refuerzo')
    asignatura = models.CharField(default='', max_length=5000, verbose_name=u'Asignatura', blank=True, null=True)
    grado_egb = models.CharField(default=False,max_length=5000, null=True, blank=True, verbose_name='Grado EGB')

    def __str__(self):
        return "{}".format(self.personacita)
    class Meta:
        verbose_name = u"Informe Refuezo Academico"
        verbose_name_plural = u"Informes Refuerzos Academicos"

class Proceso(ModeloBase):

    servicio = models.ForeignKey(ServicioCita, blank=True, null=True, verbose_name=u"Servicios",
                                 on_delete=models.CASCADE)
    descripcion = models.CharField(default='', max_length=5000, verbose_name=u'Descripción')
    tipo_proceso = models.IntegerField(choices=TIPO_PROCESOS, null=True, blank=True, verbose_name=u'Tipo de atención')
    mostrar = models.BooleanField(default=False, verbose_name=u'Mostrar Proceso')
    subtitulo = models.CharField(default='', max_length=5000, verbose_name=u'Descripción')
    tipoinforme = models.IntegerField(choices=TIPO_INFORME_PSICOLOGICO, null=True, blank=True,
                                      verbose_name=u'Tipo de informe')

    # observacion = models.CharField(default='', max_length=5000, verbose_name=u'Observación')

    # def obtener_informe_proceso(request):
    #     try:
    #         id_servicio = int(request.GET.get('id', 0))
    #         proceso = Proceso.objects.filter(servicio_id=id_servicio).first()
    #
    #         if proceso:
    #             data = {
    #                 'result': 'ok',
    #                 'tipo_proceso': proceso.tipo_proceso,
    #                 'tipo_informe': proceso.tipoinforme,
    #             }
    #         else:
    #             data = {'result': 'error', 'mensaje': 'No se encontró información para el servicio seleccionado.'}
    #
    #         return JsonResponse(data)
    #
    #     except Exception as e:
    #         return JsonResponse({"result": "error", "mensaje": "Error al obtener los datos."})

    def __str__(self):
        return "{}".format(self.descripcion)

    class Meta:
        verbose_name = u"Proceso"
        verbose_name_plural = u"Procesos"



class DetalleHistorialPsicologico(ModeloBase):
    informe = models.ForeignKey(InformePsicologico, blank=True, null=True, verbose_name=u"Informe Psicologico",
                                    on_delete=models.CASCADE)
    proceso = models.ForeignKey(Proceso, blank=True, null=True, on_delete=models.CASCADE,
                                verbose_name='Proceso de citas')

    observacion = models.TextField(default='', blank=True, null=True, verbose_name='Observación')
    marcada = models.BooleanField(default=False, verbose_name='Marcada')
    def __str__(self):
        return "{} {}".format(self.informe, self.proceso)

    class Meta:
        verbose_name = u"Detalle Historial Clinico"
        verbose_name_plural = u"Detalle Historiales Clinicos"

class DetalleInformePsicologico(ModeloBase):
    # titulo = models.TextField(default='', blank=True, null=True, verbose_name='Titulo')
    descripcion = models.TextField(default='', blank=True, null=True, verbose_name='Descripción')
    archivo = models.FileField(upload_to='agendamientocitas/historialclinico', blank=True, null=True,
                               verbose_name=u'Archivo')
    informe = models.ForeignKey(InformePsicologico, blank=True, null=True, verbose_name=u"Informe Psicologico", on_delete=models.CASCADE)
    estructura = models.ForeignKey(EstructuraInforme, blank=True, null=True, on_delete=models.CASCADE,
                                verbose_name='Estructura de Informe')
    # tipo_estructura = models.IntegerField(choices=TIPO_ESTRUCTURA, null=True, blank=True, verbose_name=u'Tipo Estructura')

    def __str__(self):
        return "{} {}".format(self.descripcion, self.informe)

    class Meta:
        verbose_name = u"Detalle Informe Psicologico"
        verbose_name_plural = u"Detalles Informes Psicologicos"

class DocumentosSolicitudServicio(ModeloBase):
    cita = models.ForeignKey(PersonaCitaAgendada, blank=True, null=True, verbose_name=u"Cita agendada",on_delete=models.CASCADE)
    requisito = models.ForeignKey(RequisitoServicioCita, blank=True, null=True, verbose_name=u"Documento",on_delete=models.CASCADE)
    archivo = models.FileField(upload_to='AgendamientoCita', blank=True, null=True, verbose_name=u'Archivo')
    estados = models.IntegerField(choices=ESTADOS_DOCUMENTOS_SOLICITUD, default=0, verbose_name=u'Estados')
    observacion = models.TextField(default='', blank=True, null=True, verbose_name='Observación')
    f_validacion = models.DateTimeField(blank=True, null=True, verbose_name='Fecha de validación de documento')
    f_correccion = models.DateTimeField(blank=True, null=True, verbose_name='Fecha de correccion de documento')
    obligatorio = models.BooleanField(default=False, verbose_name='Documento Obligatorio')

    def typefile(self):
        if self.archivo:
            return self.archivo.name[self.archivo.name.rfind("."):]
        else:
            return None

    def color_estado(self):
        color = 'bg-default'
        if self.estados == 1:
            color = "bg-success"
        elif self.estados == 2:
            color = "bg-warning"
        elif self.estados == 3:
            color = "bg-danger"
        elif self.estados == 4:
            color = "bg-secondary"
        return color

    def __str__(self):
        return u'%s %s' % (self.cita.persona, self.requisito)

class SubCitaAgendada(ModeloBase):
    citaprincipal = models.ForeignKey(PersonaCitaAgendada, blank=True, null=True, verbose_name=u"Cita Principal",related_name='subcita_set', on_delete=models.PROTECT)
    servicio = models.ForeignKey(ServicioConfigurado, on_delete=models.CASCADE, blank=True, null=True, verbose_name='Servicio Configurado')
    observacion = models.TextField(default='', null=True, blank=True, verbose_name=u'Observación')
    asistio = models.BooleanField(default=False, verbose_name=u'Asistencia de la Cita')
    estado = models.IntegerField(choices=ESTADO_SOLICITUD_SERVICIO, default=1, verbose_name=u'Estado')
    horario = models.ForeignKey(HorarioServicioCita, blank=True, null=True, verbose_name=u'Turno',on_delete=models.CASCADE)
    fechacita = models.DateField(blank=True, null=True, verbose_name='Fecha de la Cita')
    tipo_atencion = models.IntegerField(choices=TIPO_ATENCION, null=True, blank=True, verbose_name=u'Tipo de atención')
    persona_responsable = models.ForeignKey(Persona, blank=True, null=True, verbose_name=u"Persona Responsable",related_name='+', on_delete=models.PROTECT)
    es_derivacion = models.BooleanField(default=False, verbose_name=u'Es derivación a otro funcionario')

    def color_estado(self):
        color = 'bg-default'
        if self.estado == 1:
            color = "bg-success"
        elif self.estado == 2:
            color = "bg-danger"
        elif self.estado == 3:
            color = "bg-warning"
        elif self.estado == 4:
            color = "bg-danger"
        elif self.estado == 5:
            color = "bg-secondary"
        elif self.estado == 6:
            color = "bg-primary"
        return color

    def observaciones(self):
        return GestionServicioCita.objects.filter(subcita=self, status=True).order_by('-pk')

    def __str__(self):
        return "{} ({})".format(self.citaprincipal.persona, self.horario)

    class Meta:
        verbose_name = u"Sub Cita"
        verbose_name_plural = u"Sub Citas"

class GestionServicioCita(ModeloBase):
    cita = models.ForeignKey(PersonaCitaAgendada, blank=True, null=True, verbose_name=u"Cita Principal",related_name='+', on_delete=models.CASCADE)
    subcita = models.ForeignKey(SubCitaAgendada, blank=True, null=True, verbose_name=u"Sub cita",related_name='+', on_delete=models.CASCADE)
    observacion = models.TextField(default='', null=True, blank=True, verbose_name=u'Observación')
    mostrar = models.BooleanField(default=False, verbose_name=u"Mostrar Observación")
    archivo = models.FileField(upload_to='AgendamientoCita/GestionServicioCita', blank=True, null=True, verbose_name=u'Archivo')

    def __str__(self):
        return "{}-{}".format(self.cita, self.subcita)

    class Meta:
        verbose_name = u"Sub Cita"
        verbose_name_plural = u"Sub Citas"

class HistorialSolicitudCita(ModeloBase):
    cita = models.ForeignKey(PersonaCitaAgendada, blank=True, null=True, verbose_name=u"Cita agendada",on_delete=models.CASCADE)
    documento = models.ForeignKey(DocumentosSolicitudServicio, blank=True, null=True, verbose_name=u"Documento Subido",on_delete=models.CASCADE)
    estado_documento = models.IntegerField(choices=ESTADOS_DOCUMENTOS_SOLICITUD, default=0, verbose_name=u'Estado actual del documento')
    estado_solicitud = models.IntegerField(choices=ESTADO_SOLICITUD_SERVICIO, default=0, verbose_name=u'Estado actual de la solicitud')
    observacion = models.TextField(default='', blank=True, null=True, verbose_name='Observación')

    def color_estado_doc(self):
        color = 'bg-default'
        if self.estado_documento == 1:
            color = "bg-success"
        if self.estado_documento == 2:
            color = "bg-warning"
        if self.estado_documento == 3:
            color = "bg-secondary"
        return color

    def color_estado_soli(self):
        color = 'bg-default'
        if self.estado_solicitud == 1:
            color = "bg-success"
        if self.estado_solicitud == 2:
            color = "bg-danger"
        if self.estado_solicitud == 3:
            color = "bg-secondary"
        return color

    def __str__(self):
        return u'%s' % (self.documento)

#PAGINA WEB

class NoticiasVinculacion(ModeloBase):
    # servicio = models.ForeignKey(ServicioCita, blank=True, null=True, verbose_name=u"Servicios",
    #                              on_delete=models.CASCADE)
    departamentoservicio = models.ForeignKey(DepartamentoServicio, blank=True, null=True, on_delete=models.CASCADE,
                                             verbose_name='Departamento de servicio')
    titulo = models.CharField(default='', max_length=200, verbose_name=u'Titulo principal de la noticia')
    subtitulo = models.CharField(default='', max_length=200, verbose_name=u'Subtitulo de la noticia')
    descripcion = models.TextField(default='', blank=True, null=True, verbose_name=u'Descripción')
    # tipogestiones = models.IntegerField(choices=TIPO_GESTION_VINCULACION, null=True, blank=True,
    #                                   verbose_name=u'Tipo de Gestiones')
    tipopuplicacion = models.IntegerField(choices=TIPO_PUBLICACION, null=True, blank=True,
                                      verbose_name=u'Tipo de Webinar')
    estadowebinar = models.IntegerField(choices=TIPO_WEBINAR, null=True, blank=True,
                                          verbose_name=u'Tipo de estado webinar')
    principal = models.BooleanField(default=False, verbose_name='Es una noticia principal')
    portada = models.FileField(upload_to='gestionvinculacion/noticias', blank=True, null=True, verbose_name=u'Portada de noticia')
    publicado = models.BooleanField(default=False, verbose_name='El cuerpo esta publicado')
    archivo = models.FileField(upload_to='gestionvinculacion/archivo', blank=True, null=True,
                               verbose_name=u'Archivo')

    def __str__(self):
        return f'{self.titulo}'

    def nombre_input(self, archivename = ""):
        return remover_caracteres_especiales_unicode(archivename).lower().replace(' ', '_')

    def puede_cambiar_tipo_original_publicacion(self):
        if self.principal:
            noticias = NoticiasVinculacion.objects.filter(status=True, principal=True, publicado=True, departamentoservicio=self.departamentoservicio)
            return len(noticias) < 3
        return True

    def publicar_text(self):
        if not self.publicado:
            return 'publicar'
        else:
            return 'quitar publicación'

    def principal_text(self):
        if not self.principal:
            return 'Estas por cambiar el tipo de notícia a principal'
        else:
            return 'Estas por cambiar el tipo de notícia a general'

    # def puede_cambiar_tipo(self):
    #     if not self.principal:
    #         noticias = NoticiasVinculacion.objects.filter(status=True, principal=True, publicado=True, departamentoservicio__id = self.departamentoservicio__id)
    #         return len(noticias) < 3
    #     return True

    def puede_cambiar_tipo(self):
        if not self.principal:
            noticias = NoticiasVinculacion.objects.filter(
                status=True,
                principal=True,
                publicado=True,
                departamentoservicio=self.departamentoservicio
            )
            return noticias.count() < 3
        return True

    def get_fondo(self):
        if not self.portada:
            return '/static/images/serviciovinculacion/header-psicologia.png'
        else:
            return self.portada.url

    class Meta:
        verbose_name = u"Noticia Gestion Vinculacion"
        verbose_name_plural = u"Noticias Gestiones Vinculacion"

class CuerpoNoticiasVinculacion(ModeloBase):
    noticia = models.ForeignKey(NoticiasVinculacion, on_delete=models.CASCADE, verbose_name='Noticia')
    titulo = models.CharField(default='', max_length=100, verbose_name=u'Titulo principal del cuerpo de noticia')
    descripcion = models.TextField(default='', blank=True, null=True, verbose_name=u'Descripción')
    orden = models.IntegerField(default=0, verbose_name='Orden')

    def __str__(self):
        return f'{self.titulo}'

    class Meta:
        verbose_name = u"Cuerpo Noticia Vinculacion"
        verbose_name_plural = u"Cuerpo de Noticias Vinculacion"

class FotoCuerpoNoticiaVinculacion(ModeloBase):
    cuerpo = models.ForeignKey(CuerpoNoticiasVinculacion, on_delete=models.CASCADE, verbose_name='Cuerpo de noticia')
    orden = models.IntegerField(default=0, verbose_name='Orden')
    foto = models.FileField(upload_to='unemideporte/noticias', blank=True, null=True, verbose_name=u'Foto')
    titulo = models.CharField(default='', max_length=100, verbose_name=u'Titulo de la imagen')

    def __str__(self):
        return f'{self.titulo}'

    class Meta:
        verbose_name = u"Foto de Cuerpo Noticia"
        verbose_name_plural = u"Fotos de Cuerpo de Noticias"

class TituloWebSiteServicio(ModeloBase):
    departamentoservicio = models.ForeignKey(DepartamentoServicio, blank=True, null=True, on_delete=models.CASCADE,
                                             verbose_name='Departamento de servicio')
    titulo = models.CharField(default='', max_length=100, verbose_name=u'Titulo principal de la sección')
    subtitulo = models.CharField(default='', max_length=100, verbose_name=u'Subtitulo de la sección')
    seccion = models.IntegerField(blank=True, null=True, choices=SECCION, verbose_name="Sección donde se colocara el texto")
    publicado = models.BooleanField(default=False, verbose_name='El titulo esta publicado')
    fondotitulo = models.FileField(upload_to='unemideporte', blank=True, null=True, verbose_name=u'Fondo del titulo')
    # titulo_nav = models.CharField(default='', max_length=100, verbose_name=u'Titulo seccion navbarr')

    def __str__(self):
        return f'{self.titulo}'

    def get_titulo(self):
        if not self.titulo:
            if self.seccion == 1:
                return 'Nuestros Consultorios'
            if self.seccion == 2:
                return 'Atención Gratuita'

    def get_fondo(self):
        if not self.fondotitulo:
            return '/media/gestionvinculacion/imagenes/header-juridico2024618162531.png'
        else:
            return self.fondotitulo.url

    def cuerpos_top(self):
        return self.cuerpowebsiteservicio_set.filter(status=True, ubicacion=1).order_by('orden')

    def cuerpos_bottom(self):
        return self.cuerpowebsiteservicio_set.filter(status=True, ubicacion=2).order_by('orden')

    class Meta:
        verbose_name = u"Titulo Web Site"
        verbose_name_plural = u"Titulos Web Site"

class CuerpoWebSiteServicio(ModeloBase):
    titulowebsite = models.ForeignKey(TituloWebSiteServicio, blank=True, null=True, on_delete=models.CASCADE, verbose_name='Titulo del website')
    titulo = models.CharField(default='', max_length=100, verbose_name=u'Titulo del cuerpo de sección')
    descripcion = models.TextField(default='', max_length=5000, verbose_name=u'Descripción')
    ubicacion = models.IntegerField(blank=True, null=True, choices=UBICACION, verbose_name="Ubicación donde se colocara el texto")
    publicado = models.BooleanField(default=False, verbose_name='El cuerpo esta publicado')
    orden = models.IntegerField(default=0, verbose_name='Orden')

    def __str__(self):
        return f'{self.titulo}'

    class Meta:
        verbose_name = u"Cuerpo Web Site"
        verbose_name_plural = u"Cuerpos Web Site"

class CardInformativo(ModeloBase):
    departamentoservicio = models.ForeignKey('DepartamentoServicio', blank=True, null=True, on_delete=models.CASCADE, verbose_name='Departamento de servicio')
    titulo = models.CharField(default='', max_length=1000, verbose_name='Titulo principal del cuerpo de alerta')
    subtitulo = models.CharField(default='', max_length=1000, verbose_name='Subtitulo principal del cuerpo de alerta')
    imagen = models.FileField(upload_to='gestionvinculacion/noticias', blank=True, null=True, verbose_name='Portada de noticia')
    fondo = models.CharField(default='', max_length=500, null=True, blank=True, verbose_name='Fondo')  # Cambiado a CharField
    cuerpoinformativa = models.TextField(default='', blank=True, null=True, verbose_name='Descripción de la Alerta', max_length=1000)
    orden = models.IntegerField(default=0, verbose_name='Orden de presentación')

    def __str__(self):
        return f'{self.titulo}'

    def nombre_input(self):
        return remover_caracteres_especiales_unicode(self.titulo).lower().replace(' ', '_')

    def imagen_input(self, imagen):
        return imagen.split('.')[0]

    class Meta:
        verbose_name = 'Card Informativo'
        verbose_name_plural = 'Cards Informativos'

class TerminosCondicion(ModeloBase):
    nombre = models.CharField(default='', max_length=100, verbose_name=u'Nombre')
    descripcion = models.TextField(default='', verbose_name=u'Descripción', blank=True)
    mostrar = models.BooleanField(default=False, verbose_name=u'mostrar')
    general = models.BooleanField(default=False, verbose_name=u'Terminos general')
    servicio = models.ManyToManyField(ServicioCita, verbose_name=u'Servicios')

    def __str__(self):
        return self.nombre

    def save(self, *args, **kwargs):
        self.nombre = self.nombre.upper().strip()
        super(TerminosCondicion, self).save(*args, **kwargs)

    class Meta:
        verbose_name = u"Termino y condicion de Vinculacion"
        verbose_name_plural = u"Terminos y condiciones de Vinculacion"

class  CargaImgvin(ModeloBase):
    departamentoservicio = models.ForeignKey(DepartamentoServicio, blank=True, null=True, on_delete=models.CASCADE,
                                             verbose_name='Departamento de servicio')
    imagen = models.FileField(upload_to='gestionvinculacion/imagenes', blank=True, null=True,
                              verbose_name='Imágenes para la página web')
    descripcion = models.TextField(default='', max_length=100, blank=True, null=True, verbose_name='Descripción')
    # enlace_imagen = models.CharField(max_length=255, blank=True, null=True, verbose_name='Enlace de la imagen')


    def __str__(self):
        return f'{self.descripcion}'

    def imagen_input(self, descripcion):
        return descripcion.split('.')[0]

    class Meta:
        verbose_name = u"Galeria de Imagen"
        verbose_name_plural = u"Galerias de Imagenes"

