import os
from datetime import datetime, timedelta
from decimal import Decimal, ROUND_HALF_UP
from django.db import models
from django.forms import model_to_dict
from PyPDF2 import PdfFileMerger
# from certi.funciones import unir_pdf
from sga.funciones import ModeloBase, remover_caracteres_especiales_unicode
from settings import SITE_STORAGE, JR_USEROUTPUT_FOLDER
from sga.funcionesxhtml2pdf import conviert_html_to_pdfsave_path
from sga.models import Reporte, Coordinacion, Carrera, Persona, LogReporteDescarga, Periodo, Inscripcion, Matricula, \
    PerfilUsuario
from sagest.models import Departamento, DistributivoPersona

CLASIFICACION_CERTIFICADO = (
    (1, "Calificaciones"),
    (2, "Cumplimiento"),
    (3, "Estudios"),
    (4, "Grado"),
)

TIPO_CERTIFICACION_CERTIFICADO = (
    (1, "Matricula"),
    (2, "Inscripcion"),
    (3, "En Curso"),
)

TIPO_VALIDACION_CERTIFICADO = (
    (1, "Departamento"),
    (2, "Facultad"),
)

TIPO_ORIGEN_CERTIFICADO = (
    (1, "Interno"),
    (2, "Externo"),
    (3, "Fisico"),
    (4, "Rubrica"),
)

TIPO_VIGENCIA_CERTIFICADO = (
    (0, "Ninguna"),
    (1, "Horas"),
    (2, "Días"),
    (3, "Meses"),
    (4, "Años"),
)

DESTINO_CERTIFICADO = (
    (1, "Estudiantes"),
    (2, "Administrativos"),
    (3, "Docentes"),
)


class Perms(models.Model):
    class Meta:
        permissions = (
            ("puede_modificar_certificados", "Modificar certificados"),
            ("puede_eliminar_certificados", "Eliminar certificados"),
            ("puede_modificar_unidades_certificadoras", "Modificar unidades certificadoras"),
            ("puede_eliminar_unidades_certificadoras", "Eliminar unidades certificadoras"),
            ("puede_modificar_asistentes_certificadoras", "Modificar asistentes certificadoras"),
            ("puede_eliminar_asistentes_certificadoras", "Eliminar asistentes certificadoras"),
        )


CHOICE_FUNCCION_LIST_ADJUNTAR = (
    (1, 'adjuntar_malla_curricular'),
    (2, 'adjuntar_silabo_plananalitico'),
)

class FuncionAdjuntarArchivoCertificado(ModeloBase):
    nombrevisual = models.CharField(max_length=100, verbose_name=u"Nombre Visual")
    nombrefuncion = models.IntegerField(choices=CHOICE_FUNCCION_LIST_ADJUNTAR, verbose_name=u"Nombre funcion")

    def __str__(self):
        return u'%s' % self.nombrevisual

    def adjuntar_malla_curricular2(self, logreporte):
        from certi.funciones import unir_pdf, elimina_tildes
        try:
            data = {}
            data['inscripcion'] = inscripcion = logreporte.content_type.model_class().objects.get(pk=logreporte.object_id)
            data['malla'] = malla = inscripcion.mi_malla()
            archivo = malla.archivo
            result, mensaje, reportfile = unir_pdf(archivo, logreporte)
            if not result:
                raise NameError(mensaje)
            return result, mensaje, reportfile

            # if malla.archivo:
            #     archivoresultado = os.path.join(JR_USEROUTPUT_FOLDER, logreporte.usuario_creacion.username)
            #     listadopdfs = [
            #         "".join([SITE_STORAGE, logreporte.url]).replace('//', '/'),
            #         "".join([SITE_STORAGE, malla.archivo.url]).replace('//', '/')
            #     ]
            #     merger = PdfFileMerger()
            #     [merger.append(pdf) for pdf in listadopdfs]
            #     with open(archivoresultado+'/resultado.pdf', "wb") as new_file:
            #         merger.write(new_file)
            #     return {'result': True, 'mensaje': u'Combinacion Completa'}
            # else:
            #     raise NameError('Certificado Sin Malla Adjunta')
        except Exception as ex:
            return False, u'Fallo operación %s' % str(ex), None

    def adjuntar_malla_curricular(self, logreporte):
        from certi.funciones import unir_pdf, elimina_tildes
        try:
            data = {}
            data['inscripcion'] = inscripcion = logreporte.content_type.model_class().objects.get(pk=logreporte.object_id)
            data['malla'] = malla = inscripcion.mi_malla()
            data['title'] = u'Malla del alumno'
            data['nivelesdemallas'] = nivelesmalla = malla.niveles_malla()
            data['colspan_general'] = nivelesmalla.count() - 2
            data['ejesformativos'] = malla.ejesformativos_malla()
            data['pagesize'] = 'A4'
            data['rowasignaturas'] = [i for i in range(0, malla.obtner_numero_mayor_asignaturamalla())]
            output_folder = os.path.join(JR_USEROUTPUT_FOLDER, elimina_tildes(logreporte.usuario_creacion.username), '')
            pdfname = 'mallacurricular'+str(inscripcion.id)+".pdf"
            result, mensaje, reportfile = conviert_html_to_pdfsave_path('adm_certificados/utils_pdf/newmallacurricular.html', data, output_folder, pdfname)
            if not result:
                raise NameError(mensaje)
            result, mensaje, reportfile = unir_pdf(reportfile, logreporte)
            if not result:
                raise NameError(mensaje)
            return result, mensaje, reportfile
        except Exception as ex:
            return False, u'Fallo operación %s' % str(ex), None

    def save(self, *args, **kwargs):
        self.nombrevisual = self.nombrevisual.upper()
        super(FuncionAdjuntarArchivoCertificado, self).save(*args, **kwargs)

    class Meta:
        verbose_name = u"Función Adjuntar Archivo Certificado"
        verbose_name_plural = u"Funciones Adjuntar Archivos Certificados"
        ordering = ['-fecha_creacion']


def certificado_background_card_directory_path(instance, filename):
    fecha = datetime.now().date()
    return 'certificado/imagen/tarjeta/{0}/{1}/{2}/{3}'.format(fecha.year, fecha.month, fecha.day, filename)


class Certificado(ModeloBase):
    from secretaria.models import Servicio
    codigo = models.CharField(max_length=10, verbose_name=u"Código")
    clasificacion = models.IntegerField(default=1, choices=CLASIFICACION_CERTIFICADO, verbose_name=u"Clasificación")
    certificacion = models.CharField(max_length=350, verbose_name=u"Certificación", db_index=True)
    tipo_certificacion = models.IntegerField(default=1, choices=TIPO_CERTIFICACION_CERTIFICADO, verbose_name=u"Tipo certificación")
    tipo_validacion = models.IntegerField(default=1, choices=TIPO_VALIDACION_CERTIFICADO, verbose_name=u"Tipo validación")
    tipo_origen = models.IntegerField(default=1, choices=TIPO_ORIGEN_CERTIFICADO, blank=True, null=True, verbose_name=u"Tipo origen")
    version = models.FloatField(default=0.0, verbose_name=u"Versión")
    primera_emision = models.DateField(blank=True, null=True, verbose_name=u"Primera emisión")
    ultima_modificacion = models.DateField(blank=True, null=True, verbose_name=u"Ultima modificación")
    reporte = models.ForeignKey(Reporte, related_name='+', on_delete=models.CASCADE, blank=True, null=True, verbose_name=u"Reporte")
    visible = models.BooleanField(default=False, verbose_name=u"Visible?")
    vigencia = models.IntegerField(default=0, blank=True, null=True, verbose_name=u"Vigencia")
    tipo_vigencia = models.IntegerField(default=0, choices=TIPO_VIGENCIA_CERTIFICADO, verbose_name=u"Tipo de Vigencia")
    destino = models.IntegerField(default=1, choices=DESTINO_CERTIFICADO, verbose_name=u"Destino")
    coordinacion = models.ManyToManyField(Coordinacion, verbose_name=u'Coordinaciones')
    adjuntararchivo = models.BooleanField(default=False, verbose_name=u"Adjuntar Archivo?")
    funcionadjuntar = models.ForeignKey(FuncionAdjuntarArchivoCertificado, related_name='+', on_delete=models.CASCADE, blank=True, null=True, verbose_name=u"Función")
    servicio = models.ForeignKey(Servicio, related_name='+', on_delete=models.CASCADE, blank=True, null=True, verbose_name=u"Servicio")
    costo = models.DecimalField(max_digits=30, decimal_places=16, default=0, blank=True, null=True, verbose_name=u'Costo')
    #tiempo_cobro = models.DurationField(default=timedelta(hours=72))
    tiempo_cobro = models.IntegerField(default=72, blank=True, null=True, verbose_name=u"Tiempo de cobro")
    imagen_tarjeta = models.FileField(upload_to=certificado_background_card_directory_path, max_length=500, blank=True, null=True, verbose_name=u'Fondo de trajeta')
    mallaculminada = models.BooleanField(default=False, verbose_name=u"Requiere malla culminada?")
    # reporte_previsualizacion = models.ForeignKey(Reporte, related_name='+', on_delete=models.CASCADE, blank=True, null=True, verbose_name=u"Reporte con marca de agua, con fines de previsualización")

    def __str__(self):
        return u'%s - %s' % (self.codigo, self.certificacion)

    def tiene_unidades_certificadoras(self):
        return CertificadoUnidadCertificadora.objects.values("id").filter(status=True, certificado=self).exists()

    def unidades_certificadoras(self):
        return CertificadoUnidadCertificadora.objects.filter(status=True, certificado=self)

    def get_coordinaciones(self):
        return self.coordinacion.all()

    def tiempo_vigencia(self):
        if self.tipo_vigencia == 0:
            return "Ninguna"
        elif self.tipo_vigencia == 1:
            return f"{self.vigencia} Horas"
        elif self.tipo_vigencia == 2:
            return f"{self.vigencia} Días"
        elif self.tipo_vigencia == 3:
            return f"{self.vigencia} Meses"
        else:
            if self.vigencia > 1:
                return f"{self.vigencia} Años"
            else:
                return f"{self.vigencia} Año"
        return "No aplica"

    def save(self, *args, **kwargs):
        super(Certificado, self).save(*args, **kwargs)

    class Meta:
        verbose_name = u"Certificado"
        verbose_name_plural = u"Certificados"
        ordering = ['codigo', 'version']


class CertificadoUnidadCertificadora(ModeloBase):
    certificado = models.ForeignKey(Certificado, on_delete=models.CASCADE, related_name='+', verbose_name=u"Certificado")
    departamento = models.ForeignKey(Departamento, on_delete=models.CASCADE, related_name='+', blank=True, null=True, verbose_name=u"Unidad certifcadora (Departamento)")
    coordinacion = models.ForeignKey(Coordinacion, on_delete=models.CASCADE, related_name='+', blank=True, null=True, verbose_name=u"Unidad certifcadora (Facultad)")
    alias = models.CharField(max_length=20, blank=True, null=True, verbose_name=u"Alias del departamento/facultad")
    responsable = models.ForeignKey(Persona, on_delete=models.CASCADE, related_name='+', verbose_name=u'Firma de responsabilidad')
    responsable_titulo = models.CharField(max_length=250, blank=True, null=True, verbose_name=u"Nombre del responsable con titulo")
    responsable_denominacion = models.CharField(max_length=350, blank=True, null=True, verbose_name=u"Denominación del puesto del responsable")
    compartir_responsabilidad = models.BooleanField(default=False, verbose_name=u"Compartir responsabilidad con Facultad")

    def __str__(self):
        if self.coordinacion:
            return u'%s - %s' % (self.coordinacion.__str__(), self.certificado.codigo)
        else:
            return u'%s - %s' % (self.departamento.__str__(), self.certificado.codigo)

    def tiene_responsable(self):
        return True if self.responsable else False

    def tiene_asistentes_certificadoras(self):
        return CertificadoAsistenteCertificadora.objects.values("id").filter(status=True, unidad_certificadora=self).exists()

    def asistentes_certificadoras(self):
        return CertificadoAsistenteCertificadora.objects.filter(status=True, unidad_certificadora=self)

    def certificados_responsables(self, tipo_origen):
        unidades = CertificadoUnidadCertificadora.objects.filter(status=True, responsable=self.responsable, certificado__tipo_origen=tipo_origen)
        #return  unidades
        return Certificado.objects.filter(status=True, pk__in=unidades.values_list('certificado_id', flat=True), tipo_origen=tipo_origen)

    def save(self, *args, **kwargs):
        self.alias = self.alias.upper()
        if self.certificado:
            if self.certificado.tipo_validacion == 1:
                self.coordinacion = None
                if not self.departamento:
                    raise NameError(u"Ingrese el departamento")
            if self.certificado.tipo_validacion == 2:
                if not self.coordinacion:
                    raise NameError(u"Ingrese la facultad")
                if not self.departamento:
                    raise NameError(u"Ingrese el departamento")
        super(CertificadoUnidadCertificadora, self).save(*args, **kwargs)

    class Meta:
        verbose_name = u"Firma de unidad certificadora"
        verbose_name_plural = u"Firmas de unidades certificadoras"
        ordering = ['certificado', 'responsable']


class CertificadoAsistenteCertificadora(ModeloBase):
    unidad_certificadora = models.ForeignKey(CertificadoUnidadCertificadora, on_delete=models.CASCADE, related_name='+', verbose_name=u"Unidad certificadora")
    asistente = models.ForeignKey(Persona, on_delete=models.CASCADE, related_name='+', verbose_name=u'Firma de la asistente')
    asistente_titulo = models.CharField(max_length=250, blank=True, null=True, verbose_name=u"Nombre de la asistente con titulo")
    asistente_denominacion = models.CharField(max_length=350, blank=True, null=True, verbose_name=u"Denominación del puesto de la asistente")
    carrera = models.ManyToManyField(Carrera, verbose_name=u'Carreras')
    coordinacion_compartida = models.ForeignKey(Coordinacion, on_delete=models.CASCADE, related_name='+', verbose_name=u'Coordinación responsabilidad compartida', blank=True, null=True)

    def __str__(self):
        return u'%s - %s' % (self.asistente.__str__(), self.unidad_certificadora.__str__())

    def tiene_asistente(self):
        return True if self.asistente else False

    def tiene_carreras(self):
        return self.carrera.exists()

    def carreras(self):
        return self.carrera.all()

    def certificados_asistentes(self, tipo_origen):
        asistentes = CertificadoAsistenteCertificadora.objects.filter(status=True, asistente=self.asistente, unidad_certificadora__certificado__tipo_origen=tipo_origen)
        #return  unidades
        return Certificado.objects.filter(status=True, pk__in=asistentes.values_list('unidad_certificadora__certificado_id', flat=True), tipo_origen=tipo_origen)

    class Meta:
        verbose_name = u"Firma de la asistente de la unidad certificadora"
        verbose_name_plural = u"Firmas de las asistentes de la unidades certificadoras"
        ordering = ['unidad_certificadora', 'asistente']


class LogValidaCertificado(ModeloBase):
    browser = models.CharField(max_length=250, blank=True, null=True, verbose_name=u"Navegador")
    os = models.CharField(max_length=250, blank=True, null=True, verbose_name=u"Sistema Operativo")
    client_address = models.CharField(max_length=250, blank=True, null=True, verbose_name=u"Dirección IP del cliente")
    ippu = models.CharField(max_length=250, blank=True, null=True, verbose_name=u"Dirección IP Pública")
    screensize = models.CharField(max_length=250, blank=True, null=True, verbose_name=u"Tamaño de la pantalla")
    fechahora = models.DateTimeField(blank=True, null=True, verbose_name=u"Fecha y Hora")
    logdescarga = models.ForeignKey(LogReporteDescarga, on_delete=models.CASCADE, related_name='+', verbose_name=u"Certificado")

    def __str__(self):
        persona = self.logdescarga.get_model_data_persona()
        codigo = self.logdescarga.codigo
        if codigo:
            return u'%s - %s' % (codigo, persona.__str__())
        return u'%s' % persona.__str__()

    class Meta:
        verbose_name = u"Log de validación de certificado"
        verbose_name_plural = u"Log de validaciones de certificados"
        ordering = ['fechahora']


TIPO_PERFIL = (
    (1, "Estudiantes"),
    (2, "Administrativos"),
    (3, "Docentes"),
)

TIPO_CARNET = (
    (1, "Digital"),
    (2, "Impreso"),
)

TIPO_VALIDACION_CARNET = (
    (1, "Anverso"),
    (2, "Reverso"),
    (3, "Anverso y Reverso"),
)


class ConfiguracionCarnet(ModeloBase):
    version = models.IntegerField(default=1, verbose_name=u'Versión')
    nombre = models.CharField(default='', max_length=100, verbose_name=u'Nombre')
    base_anverso = models.FileField(upload_to='carnet/configuracion/base/anverso', blank=True, null=True, verbose_name=u'Base Anversa')
    base_reverso = models.FileField(upload_to='carnet/configuracion/base/reverso', blank=True, null=True, verbose_name=u'Base Reversa')
    reporte = models.ForeignKey(Reporte, on_delete=models.CASCADE, related_name='+', verbose_name=u"Reporte", blank=True, null=True)
    tipo = models.IntegerField(default=1, choices=TIPO_CARNET, blank=True, null=True, verbose_name=u"Tipo")
    tipo_perfil = models.IntegerField(default=1, choices=TIPO_PERFIL, verbose_name=u"Tipo Perfil")
    tipo_validacion = models.IntegerField(default=1, choices=TIPO_VALIDACION_CARNET, verbose_name=u"Tipo validacion")
    activo = models.BooleanField(default=True, verbose_name=u'Activo')
    puede_cargar_foto = models.BooleanField(default=False, verbose_name=u'Puede cargar foto')
    puede_eliminar_carne = models.BooleanField(default=False, verbose_name=u'Puede eliminar carne')
    puede_subir_foto = models.BooleanField(default=False, verbose_name=u'Puede subir foto')

    def __str__(self):
        return f'{self.nombre} (V.{self.version}) - {self.get_tipo_perfil_display()} [{self.get_tipo_display()}]'

    def es_digital(self):
        return self.tipo == 1

    def es_fisico(self):
        return self.tipo == 2

    def es_anverso(self):
        return self.tipo_validacion == 1

    def es_reverso(self):
        return self.tipo_validacion == 2

    def es_anverso_y_reverso(self):
        return self.tipo_validacion == 3

    def es_estudiante(self):
        return self.tipo_perfil == 1

    def es_administrativo(self):
        return self.tipo_perfil == 2

    def es_docente(self):
        return self.tipo_perfil == 3

    def en_uso(self):
        return Carnet.objects.values("id").filter(config=self).exists()

    def save(self, *args, **kwargs):
        if self.es_anverso():
            if not self.base_anverso:
                return NameError(u'Ingrese la base anversa')
            self.base_reverso = None
        if self.es_reverso():
            if not self.base_reverso:
                return NameError(u'Ingrese la base reversa')
            self.base_anverso = None
        if self.es_anverso_y_reverso():
            if not self.base_anverso or not self.base_reverso:
                return NameError(u'Ingrese la base anversa y reversa')
        if not self.version:
            raise NameError(u'Versión Mayor a Cero')
        if not self.nombre:
            raise NameError(u'Ingrese un Nombre')
        self.nombre = self.nombre.strip().upper()
        config = ConfiguracionCarnet.objects.values('id').all()
        if self.id:
            if config.filter(version=self.version, tipo=self.tipo, tipo_perfil=self.tipo_perfil).exclude(pk=self.id).exists():
                raise NameError(u'Vesión Existente')
            # if config.filter(nombre=self.nombre).exclude(pk=self.id).exists():
            #     raise NameError(u'Nombre Existente')
        else:
            if config.filter(version=self.version, tipo=self.tipo, tipo_perfil=self.tipo_perfil).exists():
                raise NameError(u'Vesión Existente')
            # if config.filter(nombre=self.nombre).exists():
            #     raise NameError(u'Nombre Existente')
        super(ConfiguracionCarnet, self).save(*args, **kwargs)

    class Meta:
        verbose_name = u"Configuración Carnet"
        verbose_name_plural = u"Configuraciones Carnet"
        ordering = ['version', 'tipo_perfil']
        unique_together = ['version', 'tipo', 'tipo_perfil']


class Carnet(ModeloBase):
    config = models.ForeignKey(ConfiguracionCarnet, on_delete=models.CASCADE, related_name='+', verbose_name=u'Configuración Carnet')
    persona = models.ForeignKey(Persona, on_delete=models.CASCADE, related_name='+', verbose_name=u'Persona')
    distributivo = models.ForeignKey(DistributivoPersona, on_delete=models.CASCADE, related_name='+', verbose_name=u'Distributivo', blank=True, null=True)
    matricula = models.ForeignKey(Matricula, on_delete=models.CASCADE, related_name='+', verbose_name=u'Periodo', blank=True, null=True)
    codigo_qr = models.CharField(default='', max_length=100, blank=True, null=True, verbose_name=u'Codigo QR')
    pdf = models.URLField(verbose_name=u"PDF", blank=True, null=True)
    png_anverso = models.URLField(verbose_name=u"PNG Anverso", blank=True, null=True)
    png_reverso = models.URLField(verbose_name=u"PNG Reverso", blank=True, null=True)
    activo = models.BooleanField(default=True, verbose_name=u'Activo')
    fecha_emision = models.DateTimeField(verbose_name=u'Fecha Emisión')
    fecha_caducidad = models.DateTimeField(verbose_name=u'Fecha Caducidad', blank=True, null=True)

    def __str__(self):
        return f'{self.persona.__str__()} ({self.config.get_tipo_perfil_display()})'

    def save(self, *args, **kwargs):
        if self.config.es_estudiante():
            if not self.matricula:
                raise NameError(u'El estudiante debe  tener una matricula asignada')
            self.distributivo = None
        elif self.config.es_docente() or self.config.es_administrativo():
            if not self.distributivo:
                raise NameError(f'El {"docente" if self.config.es_docente() else "administrativo"} debe estar en un distributivo')
            self.matricula = None
        else:
            raise NameError(u"No se identifico el tipo de validación")
        super(Carnet, self).save(*args, **kwargs)

    class Meta:
        verbose_name = u"Carnet"
        verbose_name_plural = u"Carnet"
        ordering = ['persona', 'fecha_emision']
        # unique_together = ['version', 'tipo']

