from datetime import timedelta, datetime

from django.db import models

# Create your models here.
from certi.models import CertificadoAsistenteCertificadora, Certificado
from sga.funciones import ModeloBase, remover_caracteres_especiales_unicode
from sga.models import Periodo, NivelMalla, Persona, Carrera, Malla, CoordinadorCarrera, Coordinacion

ROLES_RESPONSABLE=(
    (0, u'Validador de requisitos'),
    (1, u'Visualizador de requisitos'),
    (2, u'Asistente de facultad'),
)
ESTADO_SOLICITUD=(
    (0, u'Pendiente'),
    (1, u'Aprobado'),
    (2, u'Rechazado'),
    (3, u'En trámite'),
    (4, u'Finalizado'),
)
ESTADO_VALIDACION_REQUISITOS=(
    (0, u'Pendiente'),
    (1, u'Aprobado'),
    (2, u'Rechazado'),
    (3, u'Corregir'),
    (4, u'Corregido'),

)
ESTADO_VALIDACION=(
    (0, u'Aprobado por gestión academica'),
    (1, u'Rechazado por gestión academica'),
    (2, u'Aprobado por director'),
    (3, u'Rechazado por director'),
)
class ResponsableHomologacion(ModeloBase):
    estado = models.BooleanField(default=False, verbose_name=u"¿Activo?")
    persona = models.ForeignKey(Persona, blank=True, null=True, verbose_name=u"Persona responsable de validacion de solicitud", related_name='+', on_delete=models.PROTECT)
    rol = models.IntegerField(choices=ROLES_RESPONSABLE, default=0, verbose_name=u'Roles de responsable')
    coordinaciones = models.ManyToManyField("sga.Coordinacion", verbose_name=u'Coordinación o facultad')
    carrera = models.ForeignKey(Carrera, blank=True, null=True, verbose_name=u'Carrera',on_delete=models.PROTECT)

    def __str__(self):
        return u'%s-%s' % (self.persona, self.get_rol_display())

    class Meta:
        verbose_name = 'Responsable Homologación'
        verbose_name_plural = 'Responsables Homologaciónes'

class RequisitosHomologacion(ModeloBase):
    nombre = models.CharField(max_length=1000, blank=True, null=True, verbose_name=u"Descripción")
    leyenda = models.CharField(max_length=1000, blank=True, null=True, verbose_name=u'Mensaje Ayuda')
    archivo = models.FileField(upload_to='requisitos_homologacion', verbose_name=u'Documento de Guía')

    def typefile(self):
        if self.archivo:
            return self.archivo.name[self.archivo.name.rfind("."):]
        else:
            return None

    def __str__(self):
        return u'%s' % self.nombre.capitalize()

    class Meta:
        verbose_name = 'Requisito Homologación'
        verbose_name_plural = 'Requisitos Homologaciónes'

class PeriodoHomologacion(ModeloBase):
    periodo = models.ForeignKey(Periodo, on_delete=models.CASCADE, verbose_name=u'Periodo de apertura')
    publico = models.BooleanField(default=False, verbose_name=u'Publicado')
    motivo = models.TextField(default='', null=True, blank=True, verbose_name=u'Motivo de apertura')
    numdias = models.IntegerField(default=0, verbose_name='Número de días maximo para corrección de documentos')
    fechaapertura = models.DateField(blank=True, null=True, verbose_name=u'Fecha apertura')
    fechacierre = models.DateField(blank=True, null=True, verbose_name=u'Fecha cierre')
    fechainiciorecepciondocumentos = models.DateField(blank=True, null=True,verbose_name=u'Inicio Recepcion de Documentos')
    fechacierrerecepciondocumentos = models.DateField(blank=True, null=True, verbose_name=u'Fin Recepcion de Documentos')
    fechainiciorevisiongacademica = models.DateField(blank=True, null=True, verbose_name=u'Inicio Verificación de Requisitos por responsable de gestión academica')
    fechacierrerevisiongacademica= models.DateField(blank=True, null=True, verbose_name=u'Fin Verificación de Requisitos por responsable de gestión academica')
    fechainiciovaldirector = models.DateField(blank=True, null=True, verbose_name=u'Inicio Validación del director')
    fechacierrevaldirector = models.DateField(blank=True, null=True, verbose_name=u'Fin Validación del director')
    fechainicioremitiraprobados = models.DateField(blank=True, null=True, verbose_name=u'Inicio Remitir solicitudes aprobadas')
    fechacierreremitiraprobados = models.DateField(blank=True, null=True, verbose_name=u'Fin Remitir solicitudes aprobadas')

    def __str__(self):
        return u'%s' % (self.periodo)

    def en_uso(self):
        return not self.solicitudestudiantehomologacion_set.filter(status=True).exists()

    def solicitudes(self):
        return self.solicitudestudiantehomologacion_set.filter(status=True)

    def puede_solicitar(self, id):
        return not self.solicitudestudiantehomologacion_set.filter(status=True, inscripcion_id=id, estado__in=[0,1,3,4]).exists()

    def requisitos(self):
        return self.requisitoperiodohomologacion_set.filter(status=True)

    def requisitos_visibles(self):
        return self.requisitoperiodohomologacion_set.filter(status=True, mostrar=True)

    def total_solicitudes(self):
        return len(self.solicitudestudiantehomologacion_set.filter(status=True))

    def solicitudes_pendientes(self):
        return len(self.solicitudestudiantehomologacion_set.filter(status=True, estado=0))

    def solicitudes_entramite(self):
        return len(self.solicitudestudiantehomologacion_set.filter(status=True, estado=3))

    def solicitudes_aprobados(self):
        return len(self.solicitudestudiantehomologacion_set.filter(status=True, estado__in=[1,4]))

    def solicitudes_rechazados(self):
        return len(self.solicitudestudiantehomologacion_set.filter(status=True, estado=2))

    def estado_periodo(self):
        if self.fechaapertura <= datetime.now().date() and self.fechacierre >= datetime.now().date():
            return [True,'Abierto','bg-success']
        return [False,'Cerrado','bg-danger']

    class Meta:
        verbose_name = 'Periodo Homologación'
        verbose_name_plural = 'Periodos Homologación'
        ordering = ('-id',)

class RequisitoPeriodoHomologacion(ModeloBase):
    periodo_h = models.ForeignKey(PeriodoHomologacion, on_delete=models.CASCADE, verbose_name='Periodo de homologación de asignatura')
    requisito = models.ForeignKey(RequisitosHomologacion, on_delete=models.CASCADE, verbose_name='Requisitos')
    mostrar = models.BooleanField(default=False, verbose_name=u'Mostrar')
    opcional = models.BooleanField(default=False, verbose_name='Requisito opcional')
    multiple = models.BooleanField(default=False, verbose_name='Permitir Subir archivos multiples')
    essilabo = models.BooleanField(default=False, verbose_name='Requisito es Silabo?')

    def __str__(self):
        return u'%s %s' % (self.requisito, self.periodo_h)

    def documentos_subidos(self):
        return self.documentossolicitudservicio_set.filter(status=True).order_by('-id')

    def nombre_input(self):
        return remover_caracteres_especiales_unicode(self.requisito.nombre).lower().replace(' ', '_')

    class Meta:
        verbose_name = 'Requisito Periodo Homologación'
        verbose_name_plural = 'Requisitos Periodo Homologaciónes'
        ordering = ('-id',)

class SolicitudEstudianteHomologacion(ModeloBase):
    inscripcion = models.ForeignKey('sga.Inscripcion', verbose_name=u'Inscripción de estudiante', on_delete=models.CASCADE)
    periodo_h = models.ForeignKey(PeriodoHomologacion, on_delete=models.CASCADE, verbose_name=u'Periodo Aperturado')
    mensaje = models.TextField(default='', null=True, blank=True, verbose_name=u'Mensaje de estudiante')
    estado = models.IntegerField(choices=ESTADO_SOLICITUD, default=0, verbose_name=u'Estado general de solicitud')
    malla_anterior = models.ForeignKey(Malla, blank=True, null=True, verbose_name=u"Malla a Homologar", on_delete=models.CASCADE)
    carrera_anterior = models.TextField(default='', blank=True, null=True,verbose_name='Carrera anteterior en caso que no sea de carrera unemi')
    revision_gacademica = models.IntegerField(choices=ESTADO_VALIDACION_REQUISITOS, default=0,verbose_name=u'Revisión Gestión academica')
    fecha_revision_gacademica = models.DateTimeField(blank=True, null=True, verbose_name='Fecha Revisión Gestión academica')
    persona_gacademica = models.ForeignKey(ResponsableHomologacion, blank=True, null=True, verbose_name=u"Persona Gestión Academica",related_name='+', on_delete=models.PROTECT)
    observacion_gacademica = models.TextField(default='', blank=True, null=True, verbose_name='Observación de Gestión Academica')
    revision_director = models.IntegerField(choices=ESTADO_SOLICITUD, default=0, verbose_name=u'Revisión Director de Carrera')
    fecha_revision_director = models.DateTimeField(blank=True, null=True,verbose_name='Fecha Revisión Director de Carrera')
    persona_director = models.ForeignKey(Persona, blank=True, null=True, verbose_name=u"Persona Director de Carrera",related_name='+', on_delete=models.PROTECT)
    observacion_director = models.TextField(default='', blank=True, null=True,verbose_name='Observación Director de Carrera')
    archivoresoluciondirector = models.FileField(upload_to='ResolucionHomologacionAsignatura', blank=True, null=True, verbose_name=u'Archivo Resolucion Director')
    revision_directivo = models.IntegerField(choices=ESTADO_SOLICITUD, default=0, verbose_name=u'Resolución directivo')
    fecha_resolucion_aprobacion = models.DateTimeField(blank=True, null=True,verbose_name='Fecha de registro de homologación en sistema')
    asistente_facultad = models.ForeignKey(Persona, blank=True, null=True, verbose_name=u"Persona asistente de facultad",related_name='+', on_delete=models.PROTECT)
    archivoresoluciondirectivo = models.FileField(upload_to='ResolucionAprobacionDirectivo', blank=True, null=True,verbose_name=u'Archivo Resolución Directivo')
    observacion = models.TextField(default='', blank=True, null=True, verbose_name='Observación Final')
    imgevidencia = models.ImageField(verbose_name=u"Evidencia de datos cargados al sistema", blank=True, null=True, upload_to='ResolucionAprobacionDirectivo/evidencia')

    def __str__(self):
        return f'{self.inscripcion}'

    def get_director(self):
        return CoordinadorCarrera.objects.filter(status=True, carrera=self.inscripcion.carrera, tipo=3, periodo__tipo_id=2, periodo_id=self.periodo_h.periodo_id).last()

    def get_asistente_facultad(self):
        return CertificadoAsistenteCertificadora.objects.filter(status=True, carrera=self.inscripcion.carrera,
                                                                unidad_certificadora__certificado__status=True,
                                                                unidad_certificadora__certificado__tipo_validacion=2,
                                                                unidad_certificadora__certificado__visible=True).last()

    def get_asistente_coordinacion(self):
        coordinacion=self.inscripcion.carrera.coordinacion_set.filter(status=True).last()
        if coordinacion:
            return ResponsableHomologacion.objects.filter(status=True, coordinaciones=coordinacion, estado=True,rol=2).last()
        return False

    def color_estado_solicitud(self):
        color = 'bg-default'
        if self.estado == 1:
            color = "bg-success"
        elif self.estado == 2:
            color = "bg-danger"
        elif self.estado == 3:
            color = "bg-primary"
        elif self.estado == 4:
            color = "bg-secondary"
        return color

    def color_revision_director(self):
        color = 'bg-default'
        if self.revision_director == 1:
            color = "bg-success"
        elif self.revision_director == 2:
            color = "bg-danger"
        return color

    def color_revision_directivo(self):
        color = 'bg-default'
        if self.revision_directivo == 1:
            color = "bg-success"
        elif self.revision_directivo == 2:
            color = "bg-danger"
        return color

    def color_validacion_gacademico(self):
        color = 'bg-default'
        if self.revision_gacademica == 1:
            color = "bg-success"
        elif self.revision_gacademica == 2:
            color = "bg-danger"
        elif self.revision_gacademica == 3:
            color = "bg-warning"
        return color

    def documentos_subidos(self):
        return self.documentossolicitudhomologacion_set.filter(status=True).order_by('pk')

    def documentos_subidos_rq(self, id):
        return self.documentossolicitudhomologacion_set.filter(status=True,requisito_id=id).order_by('pk')

    def doc_subidos(self):
        return len(self.documentossolicitudhomologacion_set.filter(status=True).exclude(archivo=''))

    def doc_validacion(self):
        documentos=self.documentossolicitudhomologacion_set.filter(status=True, obligatorio=True)
        estado=0
        if len(documentos) == len(documentos.filter(estado=1)):
            estado=1
        elif len(documentos) == len(documentos.filter(estado=2)):
            estado=2
        elif documentos.filter(estado=3).exists():
            estado=3
        elif documentos.filter(estado=0).exists() or documentos.filter(estado=2).exists():
            estado=0
        return estado

    def doc_pendientes(self):
        return len(self.documentossolicitudhomologacion_set.filter(status=True, estado=0).exclude(archivo=''))

    def doc_aprobados(self):
        return len(self.documentossolicitudhomologacion_set.filter(status=True, estado=1))

    def doc_corregir(self):
        return len(self.documentossolicitudhomologacion_set.filter(status=True, estado=3))

    def doc_rechazados(self):
        return len(self.documentossolicitudhomologacion_set.filter(status=True, estado=2))

    def doc_corregidos(self):
        return len(self.documentossolicitudhomologacion_set.filter(status=True, estado=4))

    def puede_rechazar(self):
        if self.estado == 0 or self.revision_director == 0 or self.estado == 3:
            return True
        return False

    def puede_validar(self):
        if self.estado == 0 or self.estado == 3 or self.revision_director == 0:
            return True
        return False

    def paso_actual(self):
        paso, paso_aprobado, lista=0, 0, []
        if self.revision_gacademica != 0:
            paso = 1 if self.revision_gacademica == 1 else 0
            paso_aprobado=self.revision_director
        if self.revision_director != 0:
            paso = 2 if self.revision_director == 1 else 1
            paso_aprobado = self.revision_directivo
        if self.revision_directivo != 0:
            paso = 3 if self.revision_directivo == 1 else 2
            paso_aprobado = self.revision_directivo
        lista=[paso, paso_aprobado]
        return lista

    def puede_verproceso(self, id):
        if self.estado == 4 or self.estado == 2 or self.periodo_h.fechacierre < datetime.now().date():
            return True
        # elif self.persona_gacademica.persona.id == id:
        #     return True
        # elif self.get_director().persona.id == id or self.persona_director.id == id:
        if self.get_director():
            if self.get_director().persona_id == id:
                if self.revision_directivo == 1:
                    return True
        elif ResponsableHomologacion.objects.filter(status=True, estado=True, persona_id=id).exists():
            return True
        return False

    def opciones_disponibles(self):
        #Se quito validación por fecha, dandoles la opción e subir requisitos o validar fuera del periodo seleccionado.
        # if not self.estado == 4 and not self.estado == 2 and not self.periodo_h.fechacierre < datetime.now().date():
        if not self.estado == 4 and not self.estado == 2:
            return True
        return False

    def seguimiento_revision(self):
        return self.seguimientorevision_set.filter(status=True, documento__isnull=False)

    class Meta:
        verbose_name = 'Solicitud Estudiante Homologación'
        verbose_name_plural = 'Solicitudes Estudiantes Homologaciónes'

class DocumentosSolicitudHomologacion(ModeloBase):
    solicitud = models.ForeignKey(SolicitudEstudianteHomologacion, blank=True, null=True, verbose_name=u"Solicitud de homologacion",on_delete=models.CASCADE)
    requisito = models.ForeignKey(RequisitoPeriodoHomologacion, blank=True, null=True, verbose_name=u"Requisitos solicitado",on_delete=models.CASCADE)
    archivo = models.FileField(upload_to='DocumentoHomologacion', blank=True, null=True, verbose_name=u'Archivo')
    estado = models.IntegerField(choices=ESTADO_VALIDACION_REQUISITOS, default=0, verbose_name=u'Estados')
    observacion = models.TextField(default='', blank=True, null=True, verbose_name='Observación')
    f_validacion = models.DateTimeField(blank=True, null=True, verbose_name='Fecha de validación de documento')
    f_correccion = models.DateTimeField(blank=True, null=True, verbose_name='Fecha de corrección de documento')
    obligatorio = models.BooleanField(default=False, verbose_name='Documento Obligatorio')
    descripcion = models.TextField(default='', blank=True, null=True, verbose_name='Descripción del documento')
    nivel = models.ForeignKey(NivelMalla, blank=True, null=True, verbose_name=u"Nivel de Silabo", on_delete=models.CASCADE)

    def typefile(self):
        if self.archivo:
            return self.archivo.name[self.archivo.name.rfind("."):]
        else:
            return None

    def color_estado(self):
        color = 'bg-default'
        if self.estado == 1:
            color = "bg-success"
        elif self.estado == 2:
            color = "bg-danger"
        elif self.estado == 3:
            color = "bg-warning"
        elif self.estado == 4:
            color = "bg-secondary"
        return color

    def name_documento(self):
        nombre=f'{self.requisito.requisito.nombre.capitalize()}'
        if self.descripcion:
            nombre += f' - ({self.descripcion})'
        if self.nivel:
            nombre += f' - ({self.nivel.nombre.capitalize()})'
        return nombre

    def puede_remplazar(self):
        if not self.estado == 0 and not self.estado == 3:
            return False
        elif not self.solicitud.revision_gacademica == 0 and not self.solicitud.revision_gacademica == 3:
            return False
        elif not self.solicitud.estado == 0 and not self.solicitud.estado == 3:
            return False
        return True
    def __str__(self):
        return u'%s %s' % (self.solicitud, self.requisito)

    class Meta:
        verbose_name = 'Documento Solicitud Homologación'
        verbose_name_plural = 'Documentos Solicitudes Homologaciónes'
        ordering = ('requisito__requisito_id',)

class SeguimientoRevision(ModeloBase):
    revisor = models.ForeignKey(Persona, blank=True, null=True, verbose_name=u"Persona Reviso", on_delete=models.CASCADE)
    documento = models.ForeignKey(DocumentosSolicitudHomologacion, blank=True, null=True, verbose_name=u"Documento Revisado", on_delete=models.CASCADE)
    estado_doc = models.IntegerField(choices=ESTADO_VALIDACION_REQUISITOS, default=0, verbose_name=u'Estado de revision documentos')
    solictud = models.ForeignKey(SolicitudEstudianteHomologacion, blank=True, null=True, verbose_name=u"Solicitud de Homologacion", on_delete=models.CASCADE)
    estado = models.IntegerField(choices=ESTADO_SOLICITUD, default=0, verbose_name=u'Estado de revision documentos')
    rutaarchivo = models.TextField(null=True, blank=True, verbose_name=u"Ruta Archivo")
    observacion = models.TextField(default='', blank=True, null=True, verbose_name='Observación')

    def color_estado(self):
        color = 'bg-default'
        if self.estado == 1:
            color = "bg-success"
        elif self.estado == 2:
            color = "bg-danger"
        elif self.estado == 3:
            color = "bg-primary"
        elif self.estado == 4:
            color = "bg-secondary"
        return color

    def color_estado_doc(self):
        color = 'bg-default'
        if self.estado_doc == 1:
            color = "bg-success"
        elif self.estado_doc == 2:
            color = "bg-danger"
        elif self.estado_doc == 3:
            color = "bg-warning"
        elif self.estado_doc == 4:
            color = "bg-secondary"
        return color

    def __str__(self):
        return u'%s' % (self.revisor)

    class Meta:
        verbose_name = 'Seguimiento Revision'
        verbose_name_plural = 'Seguimientos Revisiones'
        ordering = ('-id',)
