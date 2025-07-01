# -*- coding: UTF-8 -*-
from datetime import datetime

from sga.funciones import ModeloBase
from django.db import models
from django.db.models.query_utils import Q
from django.db.models import Sum, Count, F

# from sga.models import Profesor, LineaInvestigacion

from sagest.models import Departamento


unicode = str

TIPO_REGISTRO_RECORRIDO = (
    (1, u'CONVOCATORIA'),
    (2, u'POSTULACION')
)


TIPO_REQUISITO = (
    (1, u'GENERAL'),
    (2, u'CÉDULA DE CIUDADANÍA'),
    (3, u'PAPELETA DE VOTACIÓN'),
    (4, u'EVALUACIÓN DESEMPEÑO')
)


TIPO_RUBRO = (
    (1, u'MAT'),
    (2, u'PSJ'),
    (3, u'PUB'),
    (4, u'SEG'),
    (5, u'IMP'),
    (6, u'MBI'),
    (7, u'MAN')
)


TIPO_ESTUDIO = (
    (1, u'POSDOCTORADO'),
    (2, u'DOCTORADO'),
    (3, u'MAESTRÍA')
)


TIPO_PERMISO = (
    (1, u'PERMANENTE'),
    (2, u'TEMPORAL')
)


TIPO_LICENCIA = (
    (1, u'CON SUELDO'),
    (2, u'SIN SUELDO')
)


ESTADO_ARCHIVO = (
    (1, u"CARGADO"),
    (2, u"VALIDADO"),
    (3, u"RECHAZADO"),
    (4, u"NOVEDAD"),
    (5, u"EN REVISIÓN"),
    (6, u"NO CARGADO")
)


TIPO_DOCUMENTO = (
    (1, u'SOLICITUD DE BECA'),
    (2, u'INFORME JURÍDICO'),
    (3, u'RESOLUCION OCS')
)


TIPO_INFORME = (
    (1, u'OTORGAMIENTO'),
    (2, u'JURÍDICO')
)


ESTADO_INFORME = (
    (1, u"ELABORADO"),
    (2, u'POR REVISAR'),
    (3, u"REVISADO"),
    (4, u"VALIDADO"),
    (5, u"NOVEDADES"),
    (6, u"CARGADO")
)


ESTADO_VALIDACION = (
    (1, u'ACEPTADA'),
    (2, u'NOVEDAD'),
    (3, u'RECHAZADA')
)


ESTADO_INFORME_OTORGAMIENTO = (
    (1, u'ACEPTADO'),
    (2, u'FIRMADO'),
    (3, u'NOVEDAD'),
    (4, u'POR REVISAR')
)


RESULTADO_RESOLUCION = (
    (1, u'FAVORABLE'),
    (2, u'NO FAVORABLE')
)


ESTADO_CERTIFICACION_PRESUPUESTARIA = (
    (1, u'SOLICITADO'),
    (2, u'EMITIDA')
)


class RecorridoRegistro(ModeloBase):
    tiporegistro = models.IntegerField(choices=TIPO_REGISTRO_RECORRIDO, default=1, verbose_name=u'Tipo de registro')
    registroid = models.IntegerField(default=0, verbose_name=u'Id del registro')
    fecha = models.DateField(verbose_name=u'Fecha recorrido')
    departamento = models.ForeignKey(Departamento, blank=True, null=True, on_delete=models.CASCADE, verbose_name=u'Departamento')
    persona = models.ForeignKey("sga.Persona", blank=True, null=True, on_delete=models.CASCADE, verbose_name=u"Persona")
    observacion = models.TextField(default='', verbose_name=u'Observación del recorrido')
    estado = models.ForeignKey("sagest.EstadoSolicitud", on_delete=models.CASCADE, verbose_name=u'Estado asignado')

    def __str__(self):
        return u'%s - %s - %s' % (self.get_tiporegistro_display(), self.fecha, self.estado.descripcion)

    class Meta:
        verbose_name = u"Recorrido de registro proceso beca docente"
        verbose_name_plural = u"Recorridos de registros proceso beca docente"

    def save(self, *args, **kwargs):
        self.observacion = self.observacion.strip().upper()
        super(RecorridoRegistro, self).save(*args, **kwargs)


class Requisito(ModeloBase):
    tipo = models.IntegerField(choices=TIPO_REQUISITO, default=1, verbose_name=u'Tipo')
    numero = models.IntegerField(default=0, verbose_name=u'Número de requisito')
    descripcion = models.TextField(default='', verbose_name=u'Descripción')
    observacion = models.CharField(max_length=500, default='', verbose_name=u'Observación')
    vigente = models.BooleanField(default=True, verbose_name=u'Vigente')

    def __str__(self):
        return f'{self.descripcion} - {self.get_tipo_display()}'

    class Meta:
        verbose_name = u"Requisito general para becas de docentes"
        verbose_name_plural = u"Requisitos generales para becas de docentes"


class Documento(ModeloBase):
    tipo = models.IntegerField(choices=TIPO_DOCUMENTO, default=1, verbose_name=u'Tipo')
    descripcion = models.TextField(default='', verbose_name=u'Descripción')
    observacion = models.CharField(max_length=500, default='', verbose_name=u'Observación')
    vigente = models.BooleanField(default=True, verbose_name=u'Vigente')

    def __str__(self):
        return f'{self.descripcion} - {self.get_tipo_display()}'

    class Meta:
        verbose_name = u"Documento para becas de docentes"
        verbose_name_plural = u"Documentos para becas de docentes"


class Rubro(ModeloBase):
    tipo = models.IntegerField(choices=TIPO_RUBRO, default=1, verbose_name=u'Tipo')
    descripcion = models.TextField(default='', verbose_name=u'Descripción')
    vigente = models.BooleanField(default=True, verbose_name=u'Vigente')

    def __str__(self):
        return f'{self.descripcion} - {self.get_tipo_display()}'

    class Meta:
        verbose_name = u"Rubro para presupuesto de beca de docentes"
        verbose_name_plural = u"Rubros para presupuesto de becas de docentes"


class Convocatoria(ModeloBase):
    descripcion = models.CharField(max_length=150, default='', verbose_name=u'Descripción')
    iniciopos = models.DateField(verbose_name=u'Fecha inicio de postulación')
    finpos = models.DateField(verbose_name=u'Fecha fin de postulación')
    mensajepos = models.TextField(default='', verbose_name=u'Mensaje informativo postulación')
    inicioveri = models.DateField(verbose_name=u'Fecha inicio de verificación de requisitos')
    finveri = models.DateField(verbose_name=u'Fecha fin de verificación de requisitos')
    mensajeveri = models.TextField(default='', verbose_name=u'Mensaje informativo verificación requisitos')
    iniciosel = models.DateField(verbose_name=u'Fecha inicio de calificación y selección')
    finsel = models.DateField(verbose_name=u'Fecha fin de verificación de calificación y selección')
    mensajesel = models.TextField(default='', verbose_name=u'Mensaje informativo calificación y selección')
    inicioadj = models.DateField(verbose_name=u'Fecha inicio de adjudicación')
    finadj = models.DateField(verbose_name=u'Fecha fin de adjudicación')
    mensajeadj = models.TextField(default='', verbose_name=u'Mensaje informativo adjudicación')
    inicionoti = models.DateField(verbose_name=u'Fecha inicio de notificación')
    finnoti = models.DateField(verbose_name=u'Fecha fin de notificación')
    mensajenoti = models.TextField(default='', verbose_name=u'Mensaje informativo notificación')
    vigente = models.BooleanField(default=True, verbose_name=u'Convocatoria vigente')
    archivoresolucion = models.FileField(upload_to='becadocente/convocatoria/%Y/%m/%d', blank=True, null=True, verbose_name=u'Archivo Resolución OCS aprobación convocatoria')
    archivoconvocatoria = models.FileField(upload_to='becadocente/convocatoria/%Y/%m/%d', blank=True, null=True, verbose_name=u'Archivo Convocatoria')
    planformacion = models.CharField(max_length=150, default='', verbose_name=u'Descripción plan de formación de posgrado')
    numeroinforme = models.CharField(max_length=150, default='', verbose_name=u'Número de informe presentado a ocas')
    resolucionocas = models.CharField(max_length=150, default='', verbose_name=u'Número de resolución ocas')
    archivoconsolidado = models.FileField(upload_to='becadocente/consolidado/%Y/%m/%d', blank=True, null=True, verbose_name=u'Archivo consolidado de información de postulaciones')
    estado = models.ForeignKey("sagest.EstadoSolicitud", on_delete=models.CASCADE, verbose_name=u"Estado asignado")

    def __str__(self):
        return f'{self.descripcion} - {self.iniciopos} - {self.finpos} - {self.estado.descripcion}'

    class Meta:
        verbose_name = u"Convocatoria para becas de docentes"
        verbose_name_plural = u"Convocatorias para becas de docentes"

    def save(self, *args, **kwargs):
        self.descripcion = self.descripcion.strip().upper()
        super(Convocatoria, self).save(*args, **kwargs)

    def puede_editar(self):
        return self.vigente

    def requisitos(self):
        return self.requisitoconvocatoria_set.filter(status=True).order_by('secuencia')

    def total_solicitudes_beca(self, persona):
        if persona.es_coordinador_investigacion():
            return self.solicitud_set.values('id').filter(status=True, estadovalidacion=1, informeogen=True, estadoinformeo=2).exclude(estado__valor=1).count()
        elif persona.es_vicerrector_investigacion():
            return self.solicitud_set.values('id').filter(status=True, estadovalidacion=1, informeogen=True, estadoinformeo=2, inotificadovi=True).exclude(estado__valor=1).count()
        elif persona.pertenece_a_departamento(122):
            return self.solicitud_set.values('id').filter(status=True, criteriojuridico=True).exclude(estado__valor=1).count()
        elif persona.pertenece_a_departamento(95):
            return self.solicitud_set.values('id').filter(status=True, cpresupuestaria=True).count()
        else:
            return self.solicitud_set.values('id').filter(status=True).exclude(estado__valor=1).count()

    def formatos(self):
        return self.formatoconvocatoria_set.filter(status=True).order_by('id')

    def puede_verificar_convocatoria_becadocente(self, persona):
        return True

        # if persona.es_analista_investigacion():
        #     return self.estado.valor == 8
        # elif persona.es_experto_investigacion():
        #     return self.estado.valor in [1, 2, 3]
        # elif persona.es_coordinador_investigacion():
        #     return self.estado.valor in [2, 4, 5]
        # elif persona.es_vicerrector_investigacion():
        #     return self.estado.valor in [4, 6, 7]
        # elif persona.es_rector():
        #     return self.estado.valor in [6, 8, 9]
        # else:
        #     return False

    def puede_verrecorrido_convocatoria_becadocente(self, persona):
        if persona.es_analista_investigacion():
            return True
        elif persona.es_experto_investigacion():
            return True
        elif persona.es_coordinador_investigacion():
            return True
        elif persona.es_vicerrector_investigacion():
            return True
        elif persona.es_rector():
            return True
        else:
            return False

    def tipo_accion_verificar_convocatoria_becadocente(self, persona):
        if persona.es_analista_investigacion():
            return 'Publicar'
        elif persona.es_experto_investigacion():
            return 'Revisar'
        elif persona.es_coordinador_investigacion():
            return 'Validar'
        elif persona.es_vicerrector_investigacion():
            return 'Aprobar'
        elif persona.es_rector():
            return 'Autorizar'
        else:
            return ''

    def revisada(self):
        revisados = RecorridoRegistro.objects.values('id').filter(tiporegistro=1, registroid=self.id, estado__valor=2, status=True).order_by('-id')
        rechazados = RecorridoRegistro.objects.values('id').filter(tiporegistro=1, registroid=self.id, estado__valor=3, status=True).order_by('-id')

        if not rechazados and not revisados:
            return False
        else:
            if revisados and not rechazados:
                return True
            elif rechazados and not revisados:
                return False
            else:
                if revisados[0]['id'] > rechazados[0]['id']:
                    return True
                else:
                    return False

    def recorrido(self):
        return RecorridoRegistro.objects.filter(tiporegistro=1, registroid=self.id, status=True).order_by('id')

    def puede_postular(self, profesor):
        # Verifico que sea TITULAR u OCASIONAL
        if profesor.nivelcategoria.id in [1, 2]:
            # Verifico que el periodo de postulación esté vigente
            if self.iniciopos <= datetime.now().date() <= self.finpos and self.estado.valor == 10:
                # Verifico que el profesor no tenga postulaciones
                tiene = self.profesor_tiene_postulacion(profesor)
                return not tiene
            else:
                return False
        else:
            return False

    def profesor_tiene_postulacion(self, profesor):
        return self.solicitud_set.values("id").filter(status=True, profesor=profesor).exists()

    def rubros(self):
        return self.rubroconvocatoria_set.filter(status=True).order_by('secuencia')

    def comite_institucional_becas(self):
        return self.integrantecomite_set.filter(status=True).order_by('secuencia')

    def es_secretario_comite(self, persona):
        return self.comite_institucional_becas().filter(persona=persona, secretario=True, vigente=True).exists()

    def postulaciones_sin_certificacion(self):
        return self.solicitud_set.filter(status=True, cpresupuestaria=False, estado__valor=25).order_by('-fecha_creacion')

    def postulaciones_sin_consolidar(self):
        return self.solicitud_set.filter(status=True, cpresupuestaria=True, estado__valor__in=[30, 31]).order_by('profesor__persona__apellido1', 'profesor__persona__apellido2', 'profesor__persona__nombres')

    def postulaciones_consolidadas(self):
        return self.solicitud_set.filter(status=True, cpresupuestaria=True, estado__valor=31).order_by('profesor__persona__apellido1', 'profesor__persona__apellido2', 'profesor__persona__nombres')


class RequisitoConvocatoria(ModeloBase):
    convocatoria = models.ForeignKey(Convocatoria, on_delete=models.CASCADE, verbose_name=u'Convocatoria')
    requisito = models.ForeignKey(Requisito, on_delete=models.CASCADE, verbose_name=u'Requisito')
    requierearchivo = models.BooleanField(default=False, verbose_name=u'Requiere cargar archivo')
    secuencia = models.IntegerField(default=0, verbose_name=u'Número de orden en el que se listan')

    def __str__(self):
        return u'%s - %s - %s' % (self.convocatoria.descripcion, self.requisito.descripcion, self.requierearchivo)

    class Meta:
        verbose_name = u"Requisito de la convocatoria"
        verbose_name_plural = u"Requisitos de las convocatorias"


class DocumentoConvocatoria(ModeloBase):
    convocatoria = models.ForeignKey(Convocatoria, on_delete=models.CASCADE, verbose_name=u'Convocatoria')
    documento = models.ForeignKey(Documento, on_delete=models.CASCADE, verbose_name=u'Documento')

    def __str__(self):
        return u'%s - %s' % (self.convocatoria.descripcion, self.documento.descripcion)

    class Meta:
        verbose_name = u"Documento de la convocatoria"
        verbose_name_plural = u"Documentos de las convocatorias"


class RubroConvocatoria(ModeloBase):
    convocatoria = models.ForeignKey(Convocatoria, on_delete=models.CASCADE, verbose_name=u'Convocatoria')
    rubro = models.ForeignKey(Rubro, on_delete=models.CASCADE, verbose_name=u'Rubro')
    secuencia = models.IntegerField(default=0, verbose_name=u'Número de orden en el que se listan')

    def __str__(self):
        return u'%s - %s' % (self.convocatoria.descripcion, self.rubro.descripcion)

    class Meta:
        verbose_name = u"Rubro de la convocatoria"
        verbose_name_plural = u"Rubros de las convocatorias"


class FormatoConvocatoria(ModeloBase):
    convocatoria = models.ForeignKey(Convocatoria, on_delete=models.CASCADE, verbose_name=u'Convocatoria')
    descripcion = models.CharField(max_length=250, default='', verbose_name=u'Descripción')
    archivo = models.FileField(upload_to='becadocenteformato/%Y/%m/%d', blank=True, null=True, verbose_name=u'Archivo del formato')

    def __str__(self):
        return u'%s - %s' % (self.convocatoria.descripcion, self.descripcion)

    class Meta:
        verbose_name = u"Formato de la convocatoria"
        verbose_name_plural = u"Formatos de las convocatorias"

    def save(self, *args, **kwargs):
        self.descripcion = self.descripcion.strip()
        super(FormatoConvocatoria, self).save(*args, **kwargs)


class Solicitud(ModeloBase):
    convocatoria = models.ForeignKey(Convocatoria, on_delete=models.CASCADE, verbose_name=u'Convocatoria')
    fechasolicitud = models.DateTimeField(blank=True, null=True, verbose_name=u'Fecha de solicitud')
    numero = models.IntegerField(blank=True, null=True, verbose_name=u'Número de solicitud')
    profesor = models.ForeignKey("sga.Profesor", on_delete=models.CASCADE, verbose_name=u'Profesor')
    tipoestudio = models.IntegerField(choices=TIPO_ESTUDIO, default=1, verbose_name=u'Tipo de estudios')
    programa = models.CharField(max_length=250, default='', verbose_name=u'Programa de estudios')
    tituloobtener = models.CharField(max_length=150, default='', verbose_name=u'Título a obtener')
    institucion = models.ForeignKey("sga.InstitucionEducacionSuperior", on_delete=models.CASCADE, verbose_name=u'Institucion de educacion superior')
    pais = models.ForeignKey("sga.Pais", on_delete=models.CASCADE, verbose_name=u'País')
    provincia = models.ForeignKey("sga.Provincia", on_delete=models.CASCADE, verbose_name=u'Provincia')
    canton = models.ForeignKey("sga.Canton", on_delete=models.CASCADE, verbose_name=u'Canton')
    parroquia = models.ForeignKey("sga.Parroquia", blank=True, null=True, on_delete=models.CASCADE, verbose_name=u'Parroquia')
    inicio = models.DateField(verbose_name=u'Fecha de inicio de estudios')
    fin = models.DateField(verbose_name=u'Fecha de fin de estudios')
    modalidad = models.ForeignKey("sga.Modalidad", on_delete=models.CASCADE, verbose_name=u'Modalidad de estudios')
    tienetematitulacion = models.BooleanField(default=False, verbose_name=u'Dispone tema o proyecto para titulación')
    tematitulacion = models.TextField(default='', verbose_name=u'Posible tema o proyecto para titulación')
    lineainvestigacion = models.ForeignKey("sga.LineaInvestigacion", blank=True, null=True, on_delete=models.CASCADE, verbose_name=u'Línea de investigación')
    ausentismo = models.BooleanField(default=False, verbose_name=u'Requiere ausentarse de UNEMI')
    tipopermiso = models.IntegerField(choices=TIPO_PERMISO, blank=True, null=True, verbose_name=u'Tipo de permiso')
    tiempomes = models.IntegerField(default=0, verbose_name=u'Tiempo de permiso en meses')
    tipolicencia = models.IntegerField(choices=TIPO_LICENCIA, blank=True, null=True, verbose_name=u'Tipo de licencia')
    imparteclase = models.BooleanField(default=False, verbose_name=u'Puede impartir clases durante sus estudios')
    presupuesto = models.DecimalField(default=0, max_digits=30, decimal_places=2, verbose_name=u"Monto presupuesto para estudios")
    criteriojuridico = models.BooleanField(default=False, verbose_name=u'Requiere criterio jurídico')
    observacion = models.TextField(default='', verbose_name=u'Observación')
    validada = models.BooleanField(default=False, verbose_name=u'Revisada/Validada')
    estadovalidacion = models.IntegerField(choices=ESTADO_VALIDACION, blank=True, null=True, verbose_name=u'Estado de validación')
    informejgen = models.BooleanField(default=False, verbose_name=u'Informe de jurídico de beca generado')
    informeogen = models.BooleanField(default=False, verbose_name=u'Informe de otorgamiento de beca generado')
    estadoinformeo = models.IntegerField(choices=ESTADO_INFORME_OTORGAMIENTO, blank=True, null=True, verbose_name=u'Estado del informe de otorgamiento del docente')
    inotificadovi = models.BooleanField(default=False, verbose_name=u'Informe notificado al vicerrector de investigación')
    irevisadovi = models.BooleanField(default=False, verbose_name=u'Informe revisado por vicerrector de investigación')
    inotificadocb = models.BooleanField(default=False, verbose_name=u'Informe notificado al comité institucional de becas')
    irevisadocb = models.BooleanField(default=False, verbose_name=u'Informe revisado por comité institucional de becas')
    resultadocb = models.IntegerField(choices=RESULTADO_RESOLUCION, blank=True, null=True, verbose_name=u'Resultado del comité de becas')
    cpresupuestaria = models.BooleanField(default=False, verbose_name=u'Certificación presupuestaria solicitada')
    estado = models.ForeignKey("sagest.EstadoSolicitud", on_delete=models.CASCADE, verbose_name=u'Estado asignado')

    def __str__(self):
        return u'%s - %s' % (self.convocatoria.descripcion, self.profesor)

    class Meta:
        verbose_name = u"Solicitud de Beca"
        verbose_name_plural = u"Solicitudes de Becas"

    def save(self, *args, **kwargs):
        self.programa = self.programa.strip().upper()
        self.tituloobtener = self.tituloobtener.strip().upper()
        self.observacion = self.observacion.strip().upper()
        super(Solicitud, self).save(*args, **kwargs)

    def puede_editar(self):
        return self.estado.valor in [1, 4]

    def puede_eliminar(self):
        # return self.estado.valor in [1, 2, 4]
        return self.estado.valor in [1, 4]

    def puede_agregar_presupuesto(self):
        return not self.solicitudpresupuesto_set.values("id").filter(status=True).exists()

    def puede_editar_presupuesto(self):
        return self.estado.valor in [1, 4]

    def puede_imprimir_solicitud(self):
        if self.estado.valor == 1:
            return self.presupuesto > 0
        else:
            return self.archivo_solicitud().estado == 4

    def puede_firmar_solicitud(self):
        return not self.fechasolicitud is None

    def archivo_solicitud(self):
        if self.solicituddocumento_set.values("id").filter(status=True, documento__tipo=1).exists():
            return self.solicituddocumento_set.filter(status=True, documento__tipo=1)[0]
        else:
            return None

    def puede_confirmar(self):
        if self.estado.valor == 1:
            # Verifica si tiene cargado el documento firmado de la solicitud de beca
            return self.solicituddocumento_set.values("id").filter(status=True, documento__tipo=1, archivofirmado__gt='', estado=1).exists()
        else:
            return False

    def puede_revisar(self):
        return self.estado.valor in [2, 3, 4]

    def recorrido(self):
        return RecorridoRegistro.objects.filter(tiporegistro=2, registroid=self.id, status=True).order_by('id')

    def requisitos(self):
        return self.solicitudrequisito_set.filter(status=True).order_by('requisito__numero')

    def documentos(self):
        return self.solicituddocumento_set.filter(status=True).order_by('id')

    def rubros(self):
        return self.solicitudpresupuesto_set.filter(status=True)[0].rubros()

    def tiene_presupuesto(self):
        return self.solicitudpresupuesto_set.values("id").filter(status=True).exists()

    def presupuesto_solicitud(self):
        if self.solicitudpresupuesto_set.values("id").filter(status=True).exists():
            return self.solicitudpresupuesto_set.filter(status=True)[0]
        return None

    def puede_generar_informe_otorgamiento(self):
        # return self.estado.valor in [9, 11, 12, 13, 15] and self.tiene_requisito_carta()
        return self.estado.valor in [9, 11, 12, 13, 16] and self.tiene_requisito_carta()

    def tiene_informe_otorgamiento(self):
        return self.informefactibilidad_set.values("id").filter(status=True, tipo=1).exists()

    def informe_otorgamiento(self):
        return self.informefactibilidad_set.filter(status=True, tipo=1, vigente=True)[0]

    def tiene_informe_juridico(self):
        return self.informefactibilidad_set.values("id").filter(status=True, tipo=2).exists()

    def informe_juridico(self):
        return self.informefactibilidad_set.filter(status=True, tipo=2)[0]

    def requisitos_novedad(self):
        return self.requisitos().filter(estado__in=[3, 4])

    def documentos_novedad(self):
        return self.documentos().filter(estado__in=[3, 4])

    def tiene_requisito_carta(self):
        return self.requisitos().filter(~Q(estado=6), requisito__numero=5).exists()

    def puede_revisar_informe_otorgamiento(self):
        # return self.estado.valor in [13, 14, 15, 17]
        return self.estado.valor in [13, 14, 15, 16, 18]

    def puede_firmar_informe_otorgamiento_docente(self):
        return self.estado.valor in [14, 15, 18]

    def falta_firma_informe_otorgamiento_docente(self):
        return self.estado.valor in [14, 15, 18] and self.informe_otorgamiento().firmavalida is False

    def puede_manipular_informejuridico(self):
        return self.estado.valor in [8, 9, 10, 11]

    def puede_notificar_informe_otorgamiento(self):
        # return self.estado.valor in [14, 16, 17]
        return self.estado.valor in [15, 17, 18]

    def puede_notificar_a_comite(self):
        return self.estado.valor in [19, 20]

    def puede_revisar_comite(self):
        return self.estado.valor in [20, 21, 22, 26]

    def resolucion_comite(self, informe):
        if self.resolucioncomite_set.filter(status=True, vigente=True, informe=informe).exists():
            return self.resolucioncomite_set.filter(status=True, vigente=True, informe=informe)[0]
        else:
            return None

    def puede_habilitar_edicion(self):
        return self.estado.valor == 2

    def puede_revisar_resolucion_comite(self):
        return self.estado.valor == 23

    def certificacion_presupuestaria_emitida(self):
        if CertificacionPresupuestaria.objects.values("id").filter(status=True, estado=2, certificacionpresupuestariadetalle__solicitud=self, certificacionpresupuestariadetalle__status=True).exists():
            return CertificacionPresupuestaria.objects.filter(status=True, estado=2, certificacionpresupuestariadetalle__solicitud=self, certificacionpresupuestariadetalle__status=True)[0]
        return None

    def puede_registrar_resultado_ocas(self):
        return self.estado.valor == 32

    def archivo_resolucion_ocas(self):
        if self.solicituddocumento_set.values("id").filter(status=True, documento__tipo=3).exists():
            return self.solicituddocumento_set.filter(status=True, documento__tipo=3)[0]
        else:
            return None


class SolicitudRequisito(ModeloBase):
    solicitud = models.ForeignKey(Solicitud, on_delete=models.CASCADE, verbose_name=u'Solicitud')
    requisito = models.ForeignKey(Requisito, on_delete=models.CASCADE, verbose_name=u'Requisito')
    archivo = models.FileField(upload_to='becadocente/requisito/%Y/%m/%d', blank=True, null=True, verbose_name=u'Archivo del requisito')
    numeropagina = models.IntegerField(default=0, verbose_name=u'Número de páginas')
    personarevisa = models.ForeignKey("sga.Persona", on_delete=models.CASCADE, blank=True, null=True, verbose_name=u"Persona revisa")
    fecharevisa = models.DateTimeField(blank=True, null=True, verbose_name=u'Fecha revisión')
    observacion = models.TextField(default='', verbose_name=u'Observación')
    estado = models.IntegerField(choices=ESTADO_ARCHIVO, default=1, verbose_name=u'Estado')
    personarevisacb = models.ForeignKey("sga.Persona", related_name="+", on_delete=models.CASCADE, blank=True, null=True, verbose_name=u"Persona revisa del comité de becas")
    fecharevisacb = models.DateTimeField(blank=True, null=True, verbose_name=u'Fecha revisión comité de becas')
    observacioncb = models.TextField(default='', verbose_name=u'Observación comité de becas')
    estadocb = models.IntegerField(choices=ESTADO_ARCHIVO, blank=True, null=True, verbose_name=u'Estado comité de becas')

    def __str__(self):
        return u'%s - %s - %s' % (self.solicitud, self.requisito, self.get_estado_display())

    class Meta:
        verbose_name = u"Requisito de Solicitud de Beca"
        verbose_name_plural = u"Requisitos de Solicitudes de Becas"

    def save(self, *args, **kwargs):
        self.observacion = self.observacion.strip().upper()
        super(SolicitudRequisito, self).save(*args, **kwargs)

    def color_estado(self):
        if self.estado == 1:
            return 'info'
        elif self.estado == 2:
            return 'success'
        elif self.estado in [3, 4]:
            return 'important'
        elif self.estado == 5:
            return 'inverse'
        else:
            return 'warning'


class SolicitudPresupuesto(ModeloBase):
    solicitud = models.ForeignKey(Solicitud, on_delete=models.CASCADE, verbose_name=u'Solicitud')
    numeroperiodo = models.IntegerField(default=0, verbose_name=u'Número de periodos')
    total = models.DecimalField(default=0, max_digits=30, decimal_places=2, verbose_name=u"Total presupuesto")

    def __str__(self):
        return u'%s - %s - %s' % (self.solicitud, self.numeroperiodo, self.total)

    class Meta:
        verbose_name = u"Presupuesto de Solicitud de Beca"
        verbose_name_plural = u"Presupuestos de Solicitudes de Becas"

    def rubros(self):
        return self.solicitudpresupuestorubro_set.filter(status=True).order_by('id')

    def total_general(self):
        return SolicitudPresupuestoRubroDetalle.objects.filter(status=True, presupuestorubro__solicitudpresupuesto=self).aggregate(total=Sum('subtotal'))['total']

    def total_anio(self, anio):
        return SolicitudPresupuestoRubroDetalle.objects.filter(status=True, anio=anio, presupuestorubro__solicitudpresupuesto=self).aggregate(total=Sum('subtotal'))['total']

    def detalle_presupuesto_rubros(self):
        return SolicitudPresupuestoRubroDetalle.objects.filter(status=True, presupuestorubro__solicitudpresupuesto=self)

    def detalle_presupuesto_rubros_periodo(self, periodo):
        return SolicitudPresupuestoRubroDetalle.objects.filter(status=True, presupuestorubro__solicitudpresupuesto=self, periodo=periodo)


class SolicitudPresupuestoRubro(ModeloBase):
    solicitudpresupuesto = models.ForeignKey(SolicitudPresupuesto, on_delete=models.CASCADE, verbose_name=u'Solicitud de presupuesto')
    rubro = models.ForeignKey(Rubro, on_delete=models.CASCADE, verbose_name=u'Rubro')
    valorunitario = models.DecimalField(default=0, max_digits=30, decimal_places=2, verbose_name=u"Valor unitario")

    def __str__(self):
        return u'%s - %s - %s' % (self.solicitudpresupuesto.solicitud, self.rubro, self.valorunitario)

    class Meta:
        verbose_name = u"Rubro de Presupuesto de Solicitud de Beca"
        verbose_name_plural = u"Rubros de Presupuestos de Solicitudes de Becas"

    def detalle_anio(self, anio):
        return self.solicitudpresupuestorubrodetalle_set.filter(status=True, anio=anio)[0]

    def total_rubro(self):
        return self.solicitudpresupuestorubrodetalle_set.filter(status=True).aggregate(total=Sum('subtotal'))['total']


class SolicitudPresupuestoRubroDetalle(ModeloBase):
    presupuestorubro = models.ForeignKey(SolicitudPresupuestoRubro, on_delete=models.CASCADE, verbose_name=u'Rubro de Solicitud de presupuesto')
    periodo = models.IntegerField(default=0, verbose_name=u'Número de periodo')
    anio = models.IntegerField(default=0, verbose_name=u'Anio del periodo')
    valorunitario = models.DecimalField(default=0, max_digits=30, decimal_places=2, verbose_name=u"Valor unitario")
    cantidad = models.DecimalField(default=0, max_digits=30, decimal_places=2, verbose_name=u"Cantidad")
    subtotal = models.DecimalField(default=0, max_digits=30, decimal_places=2, verbose_name=u"Subtotal")

    def __str__(self):
        return u'%s - %s - %s' % (self.presupuestorubro.rubro, self.anio, self.subtotal)

    class Meta:
        verbose_name = u"Detalle de Rubro de Presupuesto de Solicitud de Beca"
        verbose_name_plural = u"Detalles de Rubros de Presupuestos de Solicitudes de Becas"


class SolicitudDocumento(ModeloBase):
    solicitud = models.ForeignKey(Solicitud, on_delete=models.CASCADE, verbose_name=u'Solicitud')
    documento = models.ForeignKey(Documento, on_delete=models.CASCADE, verbose_name=u'Documento')
    archivo = models.FileField(upload_to='becadocente/documento/generado/%Y/%m/%d', blank=True, null=True, verbose_name=u'Archivo del documento')
    archivofirmado = models.FileField(upload_to='becadocente/documento/firmado/%Y/%m/%d', blank=True, null=True, verbose_name=u'Archivo del documento con firma')
    numeropagina = models.IntegerField(default=0, verbose_name=u'Número de páginas')
    personarevisa = models.ForeignKey("sga.Persona", on_delete=models.CASCADE, blank=True, null=True, verbose_name=u"Persona revisa")
    fecharevisa = models.DateTimeField(blank=True, null=True, verbose_name=u'Fecha revisión')
    observacion = models.TextField(default='', verbose_name=u'Observación')
    estado = models.IntegerField(choices=ESTADO_ARCHIVO, default=1, verbose_name=u'Estado')

    def __str__(self):
        return u'%s - %s - %s' % (self.solicitud, self.documento, self.get_estado_display())

    class Meta:
        verbose_name = u"Documento de Solicitud de Beca"
        verbose_name_plural = u"Documentos de Solicitudes de Becas"

    def save(self, *args, **kwargs):
        self.observacion = self.observacion.strip().upper()
        super(SolicitudDocumento, self).save(*args, **kwargs)

    def color_estado(self):
        if self.estado == 1:
            return 'info'
        elif self.estado == 2:
            return 'success'
        elif self.estado in [3, 4]:
            return 'important'
        elif self.estado == 5:
            return 'inverse'
        else:
            return 'warning'


class InformeFactibilidad(ModeloBase):
    solicitud = models.ForeignKey(Solicitud, on_delete=models.CASCADE, verbose_name=u'Solicitud')
    tipo = models.IntegerField(choices=TIPO_INFORME, default=1, verbose_name=u'Tipo de informe')
    secuencia = models.IntegerField(default=0, verbose_name=u'Secuencia informe')
    fecha = models.DateTimeField(blank=True, null=True, verbose_name=u'Fecha del informe')
    numero = models.CharField(default='', max_length=150, verbose_name=u'Número')
    remitente = models.ForeignKey("sga.Persona", blank=True, null=True, on_delete=models.CASCADE, verbose_name=u"Persona que elabora el informe")
    cargoremitente = models.ForeignKey("sagest.DenominacionPuesto", blank=True, null=True, on_delete=models.CASCADE, verbose_name=u"Cargo de quién elabora el informe")
    destinatario = models.ForeignKey("sga.Persona", related_name="+", blank=True, null=True, on_delete=models.CASCADE, verbose_name=u"Persona a quién va dirigido el informe")
    cargodestinatario = models.ForeignKey("sagest.DenominacionPuesto", related_name="+", blank=True, null=True, on_delete=models.CASCADE, verbose_name=u"Cargo de a quién va drigido el informe")
    objeto = models.TextField(default='', verbose_name=u'Objeto')
    antecedente = models.TextField(default='', verbose_name=u'Antecedentes')
    motivaciontecnica = models.TextField(default='', verbose_name=u'Motivación técnica')
    conclusion = models.TextField(default='', verbose_name=u'Conclusiones')
    recomendacion = models.TextField(default='', verbose_name=u'Recomendaciones')
    impreso = models.BooleanField(default=False, verbose_name=u'Informe impreso')
    archivo = models.FileField(upload_to='becadocente/informe/generado/%Y/%m/%d', blank=True, null=True, verbose_name=u'Archivo del informe')
    archivofirmado = models.FileField(upload_to='becadocente/informe/firmado/%Y/%m/%d', blank=True, null=True, verbose_name=u'Archivo del informe con firmas')
    observacion = models.TextField(blank=True, null=True, verbose_name=u'Observación de la revisión')
    elabora = models.ForeignKey("sga.Persona", related_name="+", blank=True, null=True, on_delete=models.CASCADE, verbose_name=u"Persona que elabora el informe")
    cargoelabora = models.ForeignKey("sagest.DenominacionPuesto", related_name="+", blank=True, null=True, on_delete=models.CASCADE, verbose_name=u"Cargo de quién elabora el informe")
    verifica = models.ForeignKey("sga.Persona", related_name="+", blank=True, null=True, on_delete=models.CASCADE, verbose_name=u"Persona que verifica el informe")
    cargoverifica = models.ForeignKey("sagest.DenominacionPuesto", related_name="+", blank=True, null=True, on_delete=models.CASCADE, verbose_name=u"Cargo de quién verifica el informe")
    aprueba = models.ForeignKey("sga.Persona", related_name="+", blank=True, null=True, on_delete=models.CASCADE, verbose_name=u"Persona que aprueba el informe")
    cargoaprueba = models.ForeignKey("sagest.DenominacionPuesto", related_name="+", blank=True, null=True, on_delete=models.CASCADE, verbose_name=u"Cargo de quién aprueba el informe")
    firmaelabora = models.BooleanField(default=False, verbose_name=u'Firmado por persona que elabora')
    firmavalida = models.BooleanField(default=False, verbose_name=u'Firmado por persona que valida')
    firmaverifica = models.BooleanField(default=False, verbose_name=u'Firmado por persona que verifica')
    firmaaprueba = models.BooleanField(default=False, verbose_name=u'Firmado por persona que aprueba')
    validado = models.BooleanField(default=False, verbose_name=u'Validado por docente')
    notificadovi = models.BooleanField(default=False, verbose_name=u'Notificado al vicerrector de investigación')
    revisadovi = models.BooleanField(default=False, verbose_name=u'Revisado por vicerrector de investigación')
    notificadocb = models.BooleanField(default=False, verbose_name=u'Notificado al comité institucional de becas')
    revisadocb = models.BooleanField(default=False, verbose_name=u'Revisado por comité institucional de becas')
    vigente = models.BooleanField(default=False, verbose_name=u'Informe vigente')
    estado = models.IntegerField(choices=ESTADO_INFORME, default=1, verbose_name=u'Estado')

    def __str__(self):
        return u'%s - %s - %s' % (self.solicitud, self.numero, self.get_estado_display())

    class Meta:
        verbose_name = u"Informe Factibilidad de Solicitud de Beca"
        verbose_name_plural = u"Informes Factibilidad de Solicitudes de Becas"

    def anexos(self):
        return self.informefactibilidadanexo_set.filter(status=True).order_by('id')

    def color_notificadovi(self):
        return 'success' if self.notificadovi else 'important'

    def color_revisadovi(self):
        return 'success' if self.revisadovi else 'important'

    def color_notificadocb(self):
        return 'success' if self.notificadocb else 'important'

    def color_estado_firmado_elaborado(self):
        if self.firmaelabora:
            return {'color' :'success', 'titulo': 'Firmado Elabora'}
        else:
            return {'color': 'warning', 'titulo': 'Falta firma Elabora'}

    def color_estado_firmado_verificado(self):
        if self.firmaverifica:
            return {'color' :'success', 'titulo': 'Firmado Verifica'}
        else:
            return {'color': 'warning', 'titulo': 'Falta firma Verifica'}

    def color_estado_firmado_aprobado(self):
        if self.firmaaprueba:
            return {'color' :'success', 'titulo': 'Firmado Aprobado'}
        else:
            return {'color': 'warning', 'titulo': 'Falta firma Aprobado'}

    def puede_notificar_investigacion(self):
        return self.firmaelabora and self.firmaverifica and self.firmaaprueba

    def puede_notificar_docente(self):
        return self.firmaelabora and self.firmaverifica and self.firmaaprueba


class InformeFactibilidadAnexo(ModeloBase):
    informe = models.ForeignKey(InformeFactibilidad, on_delete=models.CASCADE, verbose_name=u'Informe de Factibilidad de beca')
    descripcion = models.CharField(max_length=250, default='', verbose_name=u'Descripción')
    fecha = models.DateField(blank=True, null=True, verbose_name=u'Fecha generación de la evidencia')
    numeropagina = models.IntegerField(default=1, verbose_name=u'Número de páginas')
    archivo = models.FileField(upload_to='becadocente/anexoinforme/%Y/%m/%d', blank=True, null=True, verbose_name=u'Archivo del anexo')

    def __str__(self):
        return u'%s - %s' % (self.informe, self.descripcion)

    class Meta:
        verbose_name = u"Anexo del Informe de Factibilidad"
        verbose_name_plural = u"Anexos del Informe de Factibilidad"


class IntegranteComite(ModeloBase):
    convocatoria = models.ForeignKey(Convocatoria, on_delete=models.CASCADE, verbose_name=u'Convocatoria')
    persona = models.ForeignKey("sga.Persona", on_delete=models.CASCADE, verbose_name=u"Persona")
    cargo = models.ForeignKey("sagest.DenominacionPuesto", on_delete=models.CASCADE, verbose_name=u"Cargo")
    secretario = models.BooleanField(default=False, verbose_name=u'Secretario comité')
    vigente = models.BooleanField(default=True, verbose_name=u'Integrante vigente')
    secuencia = models.IntegerField(default=0, verbose_name=u'Número de orden en el que se listan')

    def __str__(self):
        return u'%s - %s' % (self.convocatoria, self.persona.nombre_completo_inverso())

    class Meta:
        verbose_name = u"Integrante del Comité institucional de becas"
        verbose_name_plural = u"Integrantes del Comité institucional de becas"


class ResolucionComite(ModeloBase):
    solicitud = models.ForeignKey(Solicitud, on_delete=models.CASCADE, verbose_name=u'Solicitud')
    informe = models.ForeignKey(InformeFactibilidad, on_delete=models.CASCADE, verbose_name=u'Informe de otorgamiento de beca')
    secuencia = models.IntegerField(default=0, verbose_name=u'Secuencia')
    fecha = models.DateTimeField(verbose_name=u'Fecha')
    numero = models.CharField(default='', max_length=150, verbose_name=u'Número')
    resultado = models.IntegerField(choices=RESULTADO_RESOLUCION, default=1, verbose_name=u'Resultado')
    motivo = models.TextField(default='', verbose_name=u'Motivo del resultado no favorable')
    resuelve = models.TextField(default='', verbose_name=u'Resuelve')
    impreso = models.BooleanField(default=False, verbose_name=u'Resolución impresa')
    archivo = models.FileField(upload_to='becadocente/resolucioncomite/generado/%Y/%m/%d', blank=True, null=True, verbose_name=u'Archivo de la resolución')
    archivofirmado = models.FileField(upload_to='becadocente/resolucioncomite/firmado/%Y/%m/%d', blank=True, null=True, verbose_name=u'Archivo de la resolución firmada')
    personavice = models.ForeignKey("sga.Persona", blank=True, null=True, on_delete=models.CASCADE, verbose_name=u"Persona Vicerrector de Investigación")
    cargovice = models.ForeignKey("sagest.DenominacionPuesto", blank=True, null=True, on_delete=models.CASCADE, verbose_name=u"Cargo Vicerrector")
    personacoord = models.ForeignKey("sga.Persona", related_name="+", blank=True, null=True, on_delete=models.CASCADE, verbose_name=u"Persona Coordinador de Investigación")
    cargocoord = models.ForeignKey("sagest.DenominacionPuesto", related_name="+", blank=True, null=True, on_delete=models.CASCADE, verbose_name=u"Cargo Coordinador")
    firmavice = models.BooleanField(default=False, verbose_name=u'Firmado por Vicerrector de Investigación y Posgrado')
    firmacoord = models.BooleanField(default=False, verbose_name=u'Firmado por Coordinador de Investigación')
    vigente = models.BooleanField(default=False, verbose_name=u'Resolución vigente')
    aceptada = models.BooleanField(default=False, verbose_name=u'Resultado aceptado por el solicitante')
    apelacion = models.BooleanField(default=False, verbose_name=u'Apelada por el solicitante')
    cpresupuestaria = models.BooleanField(default=False, verbose_name=u'Certificación presupuestaria solicitada')
    enviadoocas = models.BooleanField(default=False, verbose_name=u'Resolución enviada a ocas para tratamiento')
    observacion = models.TextField(blank=True, null=True, verbose_name=u'Observación de la revisión')

    def __str__(self):
        return u'%s - %s' % (self.solicitud, self.numero)

    class Meta:
        verbose_name = u"Resolución del Comité institucional"
        verbose_name_plural = u"Resoluciones del Comité institucional"

    def color_resultado(self):
        return 'success' if self.resultado == 1 else 'important'
    def puede_confirmar_resultado(self):
        return self.firmavice and self.firmacoord

    def color_estado_firmado_vicerrector(self):
        if self.firmavice:
            return {'color' :'success', 'titulo': 'Firmado Vicerrector'}
        else:
            return {'color': 'warning', 'titulo': 'Falta firma Vicerrector'}

    def color_estado_firmado_coordinador(self):
        if self.firmacoord:
            return {'color' :'success', 'titulo': 'Firmado Coordinador'}
        else:
            return {'color': 'warning', 'titulo': 'Falta firma Coordinador'}


class CertificacionPresupuestaria(ModeloBase):
    convocatoria = models.ForeignKey(Convocatoria, on_delete=models.CASCADE, verbose_name=u'Convocatoria')
    numero = models.IntegerField(default=0, verbose_name=u'Número solicitud de certificación')
    fecha = models.DateTimeField(verbose_name=u'Fecha de solicitud')
    persona = models.ForeignKey("sga.Persona", on_delete=models.CASCADE, verbose_name=u"Persona que solicita")
    cargo = models.ForeignKey("sagest.DenominacionPuesto", blank=True, null=True, on_delete=models.CASCADE, verbose_name=u"Cargo de quién solicita la certificación")
    concepto = models.TextField(default='', verbose_name=u'Concepto')
    nbeneficiario = models.IntegerField(default=0, verbose_name=u'Número de beneficiarios')
    monto = models.DecimalField(default=0, max_digits=30, decimal_places=2, verbose_name=u"Monto certificación")
    numeromemo = models.CharField(blank=True, null=True, max_length=100, verbose_name=u'Número de memorando')
    fechamemo = models.DateField(blank=True, null=True, verbose_name=u'Fecha de memorando')
    numerocomprobante = models.CharField(blank=True, null=True, max_length=100, verbose_name=u'Número de comprobante modificación presupuestaria')
    fechaemision = models.DateField(blank=True, null=True, verbose_name=u'Fecha de emisión de comprobante')
    numeropartida = models.CharField(blank=True, null=True, max_length=100, verbose_name=u'Número de partida presupuestaria')
    archivo = models.FileField(upload_to='becadocente/certpresupuestaria/%Y/%m/%d', blank=True, null=True, verbose_name=u'Archivo de la certificación')
    estado = models.IntegerField(choices=ESTADO_CERTIFICACION_PRESUPUESTARIA, verbose_name=u'Estado de la solicitud')

    def __str__(self):
        return u'%s - %s - %s' % (self.numero, self.convocatoria, self.monto)

    class Meta:
        verbose_name = u"Certificación Presupuestaria"
        verbose_name_plural = u"Certificaciones Presupuestarias"

    def color_estado(self):
        if self.estado == 1:
            return 'info'
        else:
            return 'success'

    def detalle(self):
        return self.certificacionpresupuestariadetalle_set.filter(status=True).order_by('id')

    def postulaciones_consolidadas(self):
        return self.detalle().filter(solicitud__estado__valor__gte=31).exists()


class CertificacionPresupuestariaDetalle(ModeloBase):
    certificacion = models.ForeignKey(CertificacionPresupuestaria, on_delete=models.CASCADE, verbose_name=u'Certificación presupuestaria')
    solicitud = models.ForeignKey(Solicitud, on_delete=models.CASCADE, verbose_name=u'Solicitud')
    presupuesto = models.DecimalField(default=0, max_digits=30, decimal_places=2, verbose_name=u"Monto presupuesto solicitud")

    def __str__(self):
        return u'%s - %s - %s' % (self.certificacion, self.solicitud, self.presupuesto)

    class Meta:
        verbose_name = u"Detalle de Certificación Presupuestaria"
        verbose_name_plural = u"Detalles de Certificaciones Presupuestarias"
