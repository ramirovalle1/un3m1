from django.db import models
from django.db.models.functions import Coalesce
import datetime
from sga.funciones import remover_caracteres_tildes_unicode
from datetime import datetime, timedelta, date
from dateutil.relativedelta import relativedelta
from sga.models import *
from django.db.models import F, Sum
from django.db.models import FloatField
from django.utils import timezone


class DocumentosPlantillas(ModeloBase):
    descripcion = models.TextField(default='', verbose_name=u'Descripción')

    class Meta:
        verbose_name = 'Documento para Plantilla'
        verbose_name_plural = 'Documentos para Plantillas'

    def __str__(self):
        return u'%s' % (self.descripcion)


class CategoriaPlantillas(ModeloBase):
    descripcion = models.TextField(default='', verbose_name=u'Descripción')

    class Meta:
        verbose_name = 'Categoría para Plantilla'
        verbose_name_plural = 'Categoría para Plantillas'

    def __str__(self):
        return u'%s' % (self.descripcion)


class PlantillaProcesos(ModeloBase):
    nomenclatura = models.CharField(default='', max_length=1000, blank=True, null=True, verbose_name='Nomenclatura')
    categoria = models.ForeignKey(CategoriaPlantillas, blank=True, null=True, verbose_name=u'Categoria', on_delete=models.CASCADE)
    version = models.CharField(default='', max_length=1000, blank=True, null=True, verbose_name='Versión de Plantilla')
    descripcion = models.TextField(default='', verbose_name=u'Descripción')
    vigente = models.BooleanField(default=False, verbose_name='Vigente')

    def numrequisitos(self):
        return self.requisitosplantillaprocesos_set.values('id').filter(status=True).count()

    def str_vigente(self):
        return 'fa fa-check-circle text-success' if self.vigente else 'fa fa-times-circle text-error'

    class Meta:
        verbose_name = ' Plantilla de Procesos'
        verbose_name_plural = 'Plantillas de Procesos'

    def __str__(self):
        return u'%s - %s' % (self.descripcion, self.version)


class RequisitosPlantillaProcesos(ModeloBase):
    cab = models.ForeignKey(PlantillaProcesos, blank=True, null=True, verbose_name=u'Plantilla', on_delete=models.CASCADE)
    ref = models.ForeignKey('self', blank=True, null=True, verbose_name=u'Depende de', on_delete=models.CASCADE)
    documento = models.ForeignKey(DocumentosPlantillas, blank=True, null=True, verbose_name=u'Documento', on_delete=models.CASCADE)
    orden = models.IntegerField(default=0, verbose_name='Orden')
    responsable = models.ForeignKey('sagest.DenominacionPuesto', on_delete=models.CASCADE, blank=True, null=True, verbose_name=u'Responsable', related_name='+')
    horas = models.IntegerField(default=0, blank=True, null=True, verbose_name='Tiempo de ejecución en horas')
    obligatorio = models.BooleanField(default=False, blank=True, null=True, verbose_name='¿Es obligatorio?')
    departamentoreponsable = models.ForeignKey('sagest.Departamento', on_delete=models.CASCADE, blank=True, null=True, verbose_name='Departamento Responsable')

    def str_obligatorio(self):
        return 'fa fa-check-circle text-success' if self.obligatorio else 'fa fa-times-circle text-error'

    class Meta:
        verbose_name = 'Requisitos Plantilla de Procesos'
        verbose_name_plural = 'Requisitos Plantillas de Procesos'

    def __str__(self):
        return u'%s) %s - %s' % (self.orden, self.documento, self.responsable)


ROLES_USUARIOS_DOCUMENTAL = (
    (1, u'Propietario'),
    (2, u'Lector'),
    (3, u'Editor'),
    (4, u'Sin Acceso'),
)

ACCIONES_PERMITIDAS = [
    (1, 'addfile', 'Adicionar Archivos'),
    (2, 'addfolder', 'Adicionar Carpetas'),
    (3, 'delfile', 'Eliminar Archivos'),
    (4, 'delfolder', 'Eliminar Carpetas'),
]


class DepartamentoArchivos(ModeloBase):
    departamento = models.ForeignKey('sagest.Departamento', blank=True, null=True, verbose_name=u'Departamento', on_delete=models.CASCADE)
    responsable = models.ForeignKey('sga.Persona', related_name='+', blank=True, null=True, verbose_name=u'Responsable', on_delete=models.CASCADE)
    filesize = models.DecimalField(default=0, max_digits=100, decimal_places=2, verbose_name='Tamaño de Archivos')
    storagesizegb = models.DecimalField(default=0, max_digits=100, decimal_places=2, verbose_name='Storage Permitido GB')
    storagesizemb = models.DecimalField(default=0, max_digits=100, decimal_places=2, verbose_name='Storage Permitido MB')
    nomslug = models.SlugField(null=True, blank=True, verbose_name='Nomenclatura Departamental')

    def tienesolicitudes(self):
        return SolicitudProcesoDocumental.objects.values('id').filter(status=True, estado=1, gestion__departamento=self).exists()

    def numsolicitudes(self):
        return SolicitudProcesoDocumental.objects.values('id').filter(status=True, estado=1, gestion__departamento=self).count()

    def storageocupadomb(self):
        qsarchivo = DepartamentoArchivoDocumentos.objects.filter(status=True, carpeta__gestion__departamento=self).aggregate(total=Coalesce(Sum(('filesize')), 0, output_field=FloatField())).get('total')
        return round(qsarchivo, 2)

    def storageocupadogb(self):
        try:
            return round(self.storageocupadomb() / 1024, 2)
        except Exception as ex:
            return 0

    def porcentajeocupado(self):
        try:
            storageocupado_ = self.storageocupadomb()
            porcentaje = (storageocupado_ / float(self.storagesizemb)) * 100
            return round(porcentaje, 2)
        except Exception as ex:
            return 0

    def traergestiones(self):
        return self.departamentoarchivosgestiones_set.filter(status=True).order_by('gestion__descripcion')

    def numgestiones(self):
        return self.departamentoarchivosgestiones_set.values('id').filter(status=True).count()

    def enuso(self):
        return self.departamentoarchivosgestiones_set.values('id').filter(status=True).exists()

    def __str__(self):
        return u"%s" % (self.departamento)

    class Meta:
        verbose_name = 'Departamento Archivos'
        verbose_name_plural = 'Departamento Archivos'
        ordering = ['departamento']

    def save(self, *args, **kwargs):
        self.nomslug = self.nomslug.upper()
        super(DepartamentoArchivos, self).save(*args, **kwargs)


class DepartamentoArchivosGestiones(ModeloBase):
    departamento = models.ForeignKey(DepartamentoArchivos, blank=True, null=True, verbose_name=u'Departamento', on_delete=models.CASCADE)
    gestion = models.ForeignKey('sagest.SeccionDepartamento', blank=True, null=True, verbose_name=u'Gestion', on_delete=models.CASCADE)
    responsable = models.ForeignKey('sga.Persona', related_name='+', blank=True, null=True, verbose_name=u'Responsable', on_delete=models.CASCADE)
    nomslug = models.SlugField(null=True, blank=True, verbose_name='Nomenclatura Gestión')

    def tienesolicitudes(self):
        return SolicitudProcesoDocumental.objects.values('id').filter(status=True, estado=1, gestion=self).exists()

    def numsolicitudes(self):
        return SolicitudProcesoDocumental.objects.values('id').filter(status=True, estado=1, gestion=self).count()

    def traerprimernivel(self):
        return self.departamentoarchivocarpeta_set.filter(status=True, parent=0, carpetaref__isnull=True).order_by('nombre')

    def enuso(self):
        return self.departamentoarchivocarpeta_set.filter(status=True).exists()

    def __str__(self):
        return f"{self.departamento} - {self.gestion}"

    class Meta:
        verbose_name = 'Gestión Departamento Archivos'
        verbose_name_plural = 'Gestión Departamento Archivos'
        ordering = ['departamento', 'gestion']

    def save(self, *args, **kwargs):
        self.nomslug = self.nomslug.upper()
        super(DepartamentoArchivosGestiones, self).save(*args, **kwargs)


TIPO_CARPETA_PROCESO = (
    (1, u'Estructurado'),
    (2, u'No Estructurado'),
)


ESTADO_SOLICITUD_DOCUMENTAL = (
    (1, u'Pendiente'),
    (2, u'Aprobado'),
    (3, u'Rechazado'),
)

ESTADO_PROCESO = (
    (1, u'Pendiente'),
    (2, u'En Proceso'),
    (3, u'Finalizado'),
    (4, u'Anulado'),
)


class SolicitudProcesoDocumental(ModeloBase):
    numsolicitud = models.IntegerField(default=0, verbose_name='Num. Solicitud')
    tipo = models.IntegerField(choices=TIPO_CARPETA_PROCESO, blank=True, null=True, verbose_name=u'Tipo Proceso')
    gestion = models.ForeignKey(DepartamentoArchivosGestiones, blank=True, null=True, verbose_name=u'Gestión', on_delete=models.CASCADE, related_name='+')
    persona = models.ForeignKey(Persona, blank=True, null=True, verbose_name=u'Persona', on_delete=models.CASCADE, related_name='+')
    categoria = models.ForeignKey(CategoriaPlantillas, blank=True, null=True, verbose_name=u'Categoria', on_delete=models.CASCADE)
    plantilla = models.ForeignKey(PlantillaProcesos, blank=True, null=True, verbose_name=u'Plantilla', on_delete=models.CASCADE)
    finicio = models.DateField(default='', verbose_name='Fecha Inicio')
    nombre = models.TextField(default='', verbose_name=u'Nomenclatura Proceso')
    descripcion = models.TextField(default='', verbose_name=u'Descripción')
    archivo = models_utils.FileSecretField(upload_to=models_utils.UploadToPath('solprocesos'), blank=True, null=True, verbose_name=u'Documento')
    estado = models.IntegerField(choices=ESTADO_SOLICITUD_DOCUMENTAL, default=1, verbose_name=u'Estado Solicitud')
    estado_proceso = models.IntegerField(choices=ESTADO_PROCESO, default=1, verbose_name=u'Estado Proceso')
    observacion_validacion = models.TextField(default='', verbose_name=u'Observación de Validación')

    def traer_carpeta(self):
        return self.departamentoarchivocarpeta_set.filter(status=True).first()

    def folder_name(self):
        return self.persona.usuario.username.lower().strip()

    def estado_label(self):
        label = 'label label-default'
        if self.estado == 1:
            label = 'label label-default'
        elif self.estado == 2:
            label = 'label label-success'
        elif self.estado == 3:
            label = 'label label-danger'
        return label

    def tipo_label(self):
        label = 'label label-info'
        if self.tipo == 1:
            label = 'label label-default'
        elif self.tipo == 2:
            label = 'label label-info'
        return label

    def porcentaje_completado(self):
        depadocumentos=DepartamentoArchivoDocumentos.objects.filter(status=True, carpeta__solicitud=self)
        cantidad=len(depadocumentos)
        completado=len(depadocumentos.filter(fcarga_documento__isnull=False))
        porcentaje = 0
        if cantidad > 0 and completado > 0:
            if cantidad != completado:
                porcentaje=(((cantidad-completado)/cantidad)*100)*completado
            else:
                porcentaje=100
        return int(porcentaje)

    def total_archivos(self):
        depadocumentos=DepartamentoArchivoDocumentos.objects.filter(status=True, carpeta__solicitud=self)
        return len(depadocumentos)
    class Meta:
        verbose_name = ' Plantilla de Procesos'
        verbose_name_plural = 'Plantillas de Procesos'

    def __str__(self):
        return u'%s - %s' % (self.descripcion, self.persona)


class DepartamentoArchivoCarpeta(ModeloBase):
    solicitud = models.ForeignKey(SolicitudProcesoDocumental, blank=True, null=True, verbose_name=u"Solicitud", on_delete=models.CASCADE)
    gestion = models.ForeignKey(DepartamentoArchivosGestiones, blank=True, null=True, verbose_name=u"Gestión", on_delete=models.CASCADE)
    nombre = models.TextField(default='', blank=True, null=True)
    parent = models.IntegerField(default=0, verbose_name='Nivel Carpeta')
    carpetaref = models.ForeignKey('self', blank=True, null=True, verbose_name=u'Carpeta', on_delete=models.CASCADE)
    esproceso = models.BooleanField(default=True, verbose_name='¿Es Proceso?')
    propietario = models.ForeignKey('sga.Persona', related_name='+', blank=True, null=True, verbose_name=u'Propietario', on_delete=models.CASCADE)
    cerrada = models.BooleanField(default=False, verbose_name='Carpeta Cerrada')

    def next(self):
        return self.parent + 1

    def primera_carpeta(self):
        try:
            nivel_, nombre_ = self.parent, ''
            if nivel_ == 0:
                nombre_ = self.nombre if self.nombre else ''
            else:
                id_, nombre_, parent_ = self.id, self.nombre, self.parent
                nivel_ += 1
                idcarpeta = self.carpetaref.id
                while nivel_ > 0:
                    if idcarpeta:
                        carpetaanterior = DepartamentoArchivoCarpeta.objects.get(pk=idcarpeta)
                        idcarpeta = carpetaanterior.carpetaref.id if carpetaanterior.carpetaref else None
                        nombre_ = carpetaanterior.nombre
                    nivel_ = (nivel_ - 1)
            return str(nombre_).replace('-', '_').replace(' ', '_')
        except Exception as ex:
            return None

    def ruta_carpeta(self):
        try:
            ruta_ = []
            nivel_, folder_ = self.parent, None
            if nivel_ == 0:
                ruta_.append((self.id, self.nombre, self.parent))
            else:
                id_, nombre_, parent_, next_ = self.id, self.nombre, self.parent, self.next()
                nivel_ += 1
                idcarpeta = self.carpetaref.id
                while nivel_ > 0:
                    ruta_.append((id_, nombre_, parent_, next_))
                    if idcarpeta:
                        carpetaanterior = DepartamentoArchivoCarpeta.objects.get(pk=idcarpeta)
                        idcarpeta = carpetaanterior.carpetaref.id if carpetaanterior.carpetaref else None
                        id_, nombre_, parent_, next_ = carpetaanterior.id, carpetaanterior.nombre, carpetaanterior.parent, idcarpeta
                    nivel_ = (nivel_ - 1)
            return ruta_[::-1]
        except Exception as ex:
            return []

    def ruta_carpeta_str(self):
        try:
            ruta_ = '/'
            for l_ in self.ruta_carpeta():
                ruta_ += f'{l_[1]}/'
            return ruta_
        except Exception as ex:
            return []

    def tiene_hijas(self):
        return DepartamentoArchivoCarpeta.objects.values('id').filter(status=True, carpetaref=self).exists()

    def cant_carpetas(self):
        return DepartamentoArchivoCarpeta.objects.values('id').filter(status=True, carpetaref=self).count()

    def traerhijas(self):
        return DepartamentoArchivoCarpeta.objects.filter(status=True, carpetaref=self).order_by('id')

    def tiene_archivos(self):
        return self.departamentoarchivodocumentos_set.values('id').filter(status=True).exists()

    def cant_archivos(self):
        return self.departamentoarchivodocumentos_set.values('id').filter(status=True).count()

    def traerarchivos(self):
        return self.departamentoarchivodocumentos_set.filter(status=True).order_by('id')

    def enuso(self):
        if self.departamentoarchivodocumentos_set.values('id').filter(status=True).exists():
            return True
        else:
            if DepartamentoArchivoCarpeta.objects.values('id').filter(status=True, carpetaref_id=self).exists():
                return True
            else:
                return False

    def dospersonascompartidas(self):
        return self.personascompartidascarpetas_set.filter(status=True, rol__in=[2, 3])[:2]

    def personascompartidas(self):
        return self.personascompartidascarpetas_set.filter(status=True, rol__in=[2, 3])

    def personascompartidasall(self):
        return self.personascompartidascarpetas_set.filter(status=True, rol__in=[1, 2, 3])

    def personascompartidasruta(self):
        ruta = self.ruta_carpeta()
        p_compartidas = []
        for carpeta in ruta:
            dc = DepartamentoArchivoCarpeta.objects.get(pk=carpeta[0])
            p_compartidas += list(dc.personascompartidasall().values_list('persona_id'))
        p_compartidas = list(set(p_compartidas))
        return p_compartidas

    def traeridhijas(self):
        return DepartamentoArchivoCarpeta.objects.filter(status=True, carpetaref=self).values_list('id', flat=True)

    @staticmethod
    def recursivaidhijas(lista, idlist):
        try:
            for l in lista:
                idlist.append(l.id)
                if l.traerhijas():
                    l.recursivaidhijas(l.traerhijas(), idlist)
        except Exception as ex:
            pass

    def total_archivos(self):
        try:
            idslist = [self.id]
            if self.traeridhijas():
                self.recursivaidhijas(self.traerhijas(), idslist)
                cant=DepartamentoArchivoDocumentos.objects.values('id').filter(status=True, carpeta__in=idslist).count()
            else:
                cant=self.cant_archivos()
            return cant
        except Exception as ex:
            return []

    def get_nombre(self):
        return f'Carpeta - {self.nombre}'

    def carpeta_principal(self):
        try:
            nivel_, nombre_ = self.parent, ''
            if nivel_ == 0:
                nombre_ = self.nombre if self.nombre else ''
            else:
                id_, nombre_, parent_ = self.id, self.nombre, self.parent
                nivel_ += 1
                idcarpeta = self.carpetaref.id
                while nivel_ > 0:
                    if idcarpeta:
                        carpetaanterior = DepartamentoArchivoCarpeta.objects.get(pk=idcarpeta)
                        idcarpeta = carpetaanterior.carpetaref.id if carpetaanterior.carpetaref else None
                        id_ = carpetaanterior.id
                    nivel_ = (nivel_ - 1)
            return id_
        except Exception as ex:
            return None

    def carpeta_principal_obj(self):
        try:
            nivel_, nombre_ = self.parent, ''
            if nivel_ == 0:
                principal = self
            else:
                id_, nombre_, parent_ = self.id, self.nombre, self.parent
                nivel_ += 1
                idcarpeta = self.carpetaref.id
                while nivel_ > 0:
                    if idcarpeta:
                        carpetaanterior = DepartamentoArchivoCarpeta.objects.get(pk=idcarpeta)
                        idcarpeta = carpetaanterior.carpetaref.id if carpetaanterior.carpetaref else None
                        id_ = carpetaanterior.id
                    nivel_ = (nivel_ - 1)
                principal = DepartamentoArchivoCarpeta.objects.get(pk=id_)

            return principal
        except Exception as ex:
            return None

    @staticmethod
    def recursivapadre(carpeta, listnombres):
        try:
            if carpeta.carpetaref:
                parent_ = carpeta.carpetaref
                listnombres.append(parent_.nombre)
                carpeta.recursivapadre(parent_, listnombres)
        except Exception as ex:
            pass

    def __str__(self):
        return f'{self.gestion.__str__()} - Carpeta - {self.nombre}'

    class Meta:
        verbose_name = 'Carpetas Acceso Archivos Departamentales'
        verbose_name_plural = 'Carpetas Acceso Archivos Departamentales'


class PersonasCompartidasCarpetas(ModeloBase):
    carpeta = models.ForeignKey(DepartamentoArchivoCarpeta, blank=True, null=True, verbose_name=u'Carpeta', on_delete=models.CASCADE)
    rol = models.IntegerField(choices=ROLES_USUARIOS_DOCUMENTAL, blank=True, null=True, verbose_name=u'Rol')
    persona = models.ForeignKey('sga.Persona', related_name='+', blank=True, null=True, verbose_name=u'Compartido con:', on_delete=models.CASCADE)

    def __str__(self):
        return f'{self.persona} - {self.get_rol_display()}'

    class Meta:
        verbose_name = 'Personas Compartidas Carpetas'
        verbose_name_plural = 'Personas Compartidas Carpetas'
        ordering = ['persona']


ESTADO_CARGA_ARCHIVO = (
    (1, u'Pendiente'),
    (2, u'Listo'),
    (3, u'Anulado'),
)


class DepartamentoArchivoDocumentos(ModeloBase):
    carpeta = models.ForeignKey(DepartamentoArchivoCarpeta, blank=True, null=True, verbose_name=u'Carpeta', on_delete=models.CASCADE)
    nombre = models.TextField(default='', blank=True, null=True)
    propietario = models.ForeignKey('sga.Persona', related_name='+', blank=True, null=True, verbose_name=u'Propietario', on_delete=models.CASCADE)
    archivo = models_utils.FileSecretField(upload_to=models_utils.UploadToPathDepartamento(''), blank=True, null=True, verbose_name=u'Archivo Repositorio')
    filesize = models.DecimalField(default=0, max_digits=100, decimal_places=2, verbose_name='Tamaño de Archivo en Megabytes')
    ext = models.CharField(default='', max_length=150, blank=True, null=True, verbose_name='Extensión de Archivo')
    ruta = models.TextField(default='', blank=True, null=True, verbose_name='Ruta Logica del Archivo')
    estado = models.IntegerField(choices=ESTADO_CARGA_ARCHIVO, blank=True, null=True, verbose_name=u'Estado')
    fcarga_documento = models.DateTimeField(blank=True, null=True, verbose_name='Fecha de Carga de documento')
    # PARA PROCESOS ESTRUCTURADOS
    requisito = models.ForeignKey(RequisitosPlantillaProcesos, blank=True, null=True, verbose_name='Requisito', on_delete=models.CASCADE)
    orden = models.IntegerField(default=0, verbose_name='Orden')
    responsable = models.ForeignKey('sagest.DenominacionPuesto', on_delete=models.CASCADE, blank=True, null=True, verbose_name=u'Responsable', related_name='+')
    horas = models.IntegerField(default=0, blank=True, null=True, verbose_name='Tiempo de ejecución en horas')
    obligatorio = models.BooleanField(default=False, blank=True, null=True, verbose_name='¿Es obligatorio?')
    departamentoreponsable = models.ForeignKey('sagest.Departamento', on_delete=models.CASCADE, blank=True, null=True, verbose_name='Departamento Responsable')
    # DATOS DE VALIDACIÓN
    validacion_director = models.IntegerField(choices=ESTADO_SOLICITUD_DOCUMENTAL, default=1, blank=True, null=True, verbose_name='¿Validado por director?')
    fvalidacion_director = models.DateField(blank=True, null=True, verbose_name='Fecha de Validación por director')
    validado_por = models.ForeignKey('sga.Persona', related_name='+', blank=True, null=True, verbose_name=u'Validado por', on_delete=models.CASCADE)

    def tiempo_subida(self):
        cal=relativedelta(datetime.now().date(), self.fcarga_documento.date())
        anios= cal.years
        meses= cal.months
        dias = cal.days

        tiempo = datetime.now() - self.fcarga_documento
        segundos = tiempo.seconds
        horas, segundos = divmod(segundos, 3600)
        minutos, segundos = divmod(segundos, 60)

        principal = str(segundos) + ' segundos' if segundos > 1 else str(segundos) + ' segundo'
        secundario = ''
        if anios > 0:
            principal = str(anios) + ' años' if anios > 1 else str(anios) + ' año'
            if not meses == 0:
                secundario = str(meses) + ' meses'if meses > 1 else str(meses) + ' mes'
        elif meses > 0 and anios == 0:
            principal = str(meses) + ' meses' if meses > 1 else str(meses) + ' mes'
            if dias > 0:
                secundario = str(dias) + ' días' if int(dias) > 1 else str(dias) + ' día'
        elif meses == 0 and anios == 0 and dias > 0:
            principal = str(dias) + ' días' if dias > 1 else str(dias) + ' día'
            if not horas == 0:
                secundario = str(horas) + ' horas' if horas > 1 else str(horas) + ' hora'
        elif meses == 0 and anios == 0 and dias == 0 and horas > 0:
            principal = str(horas) + ' horas'if horas > 1 else str(horas) + ' hora'
            if not minutos == 0:
                secundario=str(minutos) + ' minutos' if minutos > 1 else str(minutos) + ' minuto'
        elif meses == 0 and anios == 0 and dias == 0 and horas == 0 and minutos > 0:
            principal = str(minutos) + ' minutos 'if minutos > 1 else str(minutos) + ' minuto'
            if not segundos == 0:
                secundario=str(segundos) + ' segundos' if segundos > 1 else str(segundos) + ' segundo'
        tiemponatural = "{} {} ".format(principal, secundario)
        return tiemponatural

    def requisito_depende(self):
        try:
            requisito_ = self.requisito.ref
            if requisito_:
                return DepartamentoArchivoDocumentos.objects.values('id').filter(status=True, archivo='', requisito=requisito_).exists()
            else:
                return False
        except Exception as ex:
            return False

    def traerruta(self):
        ruta_ = [self.carpeta.nombre]
        if self.carpeta.parent > 0:
            self.carpeta.recursivapadre(self.carpeta, ruta_)
        return ruta_

    def isnew(self):
        try:
            isnew = False
            factual_ = datetime.now()
            fcreacion_ = self.fecha_creacion.astimezone(timezone.get_current_timezone()).replace(tzinfo=None)
            fmaxima_ = fcreacion_ + timedelta(minutes=40)
            if factual_ <= fmaxima_:
                isnew = True
            return isnew
        except Exception as ex:
            return False

    def puede_subir_doc(self):
        puedesubir=True
        if self.requisito.ref:
            departamento=DepartamentoArchivoDocumentos.objects.get(status=True, carpeta=self.carpeta, requisito=self.requisito.ref)
            if not departamento.archivo:
                puedesubir=False
        return puedesubir

    def asignaciones_validadas(self):
        return DepartamentoArchivoDocumentos.objects.filter(status=True, requisito__isnull=False, carpeta=self.carpeta, validacion_director__in=[1,3]).exists()

    def color_validacion(self):
        color = 'label-default'
        icon='fa-info-circle-0'
        if self.validacion_director == 2:
            color = 'label-success'
            icon = 'fa-check-circle'
        elif self.validacion_director == 3:
            color = 'label-important'
            icon = 'fa-window-close'
        diccionario={'color':color, 'icon':icon}
        return diccionario

    def get_nombre(self):
        return f'Archivo - {self.nombre}'

    def get_icono_color(self):
        ext=self.ext.lower()
        icon='fa-file-archive-o'
        color='text-secondary'
        if ext == '.pdf':
            icon='fa-file-pdf-o'
            color='text-danger'
        elif ext == '.docx' or ext == '.doc':
            icon = 'fa-file-word-o'
            color = 'text-primary'
        elif ext == '.png' or ext == '.jpg' or ext == '.jpeg':
            icon = 'fa-file-image'
            color = 'text-secondary'
        elif ext == '.xlsx' or ext == '.xls':
            icon = 'fa-file-excel-o'
            color = 'text-success'

        diccionario={'icon':icon, 'color':color}
        return diccionario

    def typefile(self):
        if self.archivo:
            return self.archivo.name[self.archivo.name.rfind("."):]
        else:
            return None

    def __str__(self):
        return u"%s" % (self.nombre)

    class Meta:
        verbose_name = 'Archivo Carpeta Departamentales'
        verbose_name_plural = 'Archivos Carpetas Departamentales'
        ordering = ['nombre']


class DocumentosFirmados(ModeloBase):
    persona = models.ForeignKey(Persona, blank=True, null=True, verbose_name=u'Persona', on_delete=models.CASCADE, related_name='+')
    archivo_original = models_utils.FileSecretField(upload_to=models_utils.UploadToPath('docfirmados/original/'), blank=True, null=True, verbose_name=u'Archivo Original')
    archivo_firmado = models_utils.FileSecretField(upload_to=models_utils.UploadToPath('docfirmados/firmado/'), blank=True, null=True, verbose_name=u'Archivo Firmado')

    def __str__(self):
        return u'%s' % (self.persona)

ACCIONES_REALIZADAS=(
    (0,u'Adición'),
    (1,u'Edición'),
    (2,u'Eliminación'),
    (3,u'Compartir'),
    (4,u'Eliminación definitiva'),
    (5,u'Restauración'),
)
class LogIteraccion(ModeloBase):
    persona = models.ForeignKey(Persona, blank=True, null=True, verbose_name=u'Persona', on_delete=models.CASCADE, related_name='+')
    personas_compartidas = models.ManyToManyField(Persona, verbose_name=u'Personas compartidas')
    nombre = models.TextField(verbose_name="Nombre de registro", blank=True, null=True)
    accion = models.IntegerField(choices=ACCIONES_REALIZADAS, blank=True, null=True, verbose_name=u'Accion realizada')
    mensaje_accion = models.TextField(verbose_name="Mensaje de la accion que se realiza", blank=True, null=True)
    object_id = models.IntegerField(blank=True, null=True, verbose_name="Id de objecto")
    content_type = models.ForeignKey(ContentType, models.SET_NULL, verbose_name=u'Modelo',blank=True,null=True)

    def __str__(self):
        return u'%s' % (self.persona)

    class Meta:
        verbose_name = 'Log de Iteraccion'
        verbose_name_plural = 'Log de Iteracciones'

class Papelera(ModeloBase):
    persona = models.ForeignKey(Persona, blank=True, null=True, verbose_name=u'Persona que elimino el archivo o carpta', on_delete=models.CASCADE, related_name='+')
    personas_compartidas = models.ManyToManyField(Persona, verbose_name=u'Personas compartidas')
    documento = models.ForeignKey(DepartamentoArchivoDocumentos, blank=True, null=True, verbose_name=u'Registro de documento', on_delete=models.CASCADE)
    carpeta = models.ForeignKey(DepartamentoArchivoCarpeta, blank=True, null=True, verbose_name=u'Registro de carpeta', on_delete=models.CASCADE)

    def __str__(self):
        return u'%s' % (self.documento.nombre if self.documento else self.carpeta.nombre)

    class Meta:
        verbose_name = 'Papelera'
        verbose_name_plural = 'Papeleras'