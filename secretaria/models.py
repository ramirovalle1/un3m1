import os
import json
from datetime import datetime, timedelta
from decimal import Decimal, ROUND_HALF_UP
# from django.contrib.auth.models import ContentType
from django.contrib.contenttypes.fields import ContentType, GenericForeignKey
from django.db import models
from django.forms import model_to_dict
from PyPDF2 import PdfFileMerger
# from certi.funciones import unir_pdf
from sga.funciones import ModeloBase, remover_caracteres_especiales_unicode, notificacion2
from settings import SITE_STORAGE, JR_USEROUTPUT_FOLDER
from sga.funcionesxhtml2pdf import conviert_html_to_pdfsave_path
from sga.models import Reporte, Coordinacion, Carrera, Persona, LogReporteDescarga, Periodo, Inscripcion, Matricula, \
    PerfilUsuario, Notificacion, PerfilAccesoUsuario
from sagest.models import Departamento, DistributivoPersona, Rubro
from django.contrib.auth.models import Group
from posgrado.models import CohorteMaestria

def nombre_carrera_pos(carrera):
    nombre = f'{carrera.nombre} MODALIDAD {carrera.get_modalidad_display()}'
    if carrera.mencion:
        nombre = f'{carrera.nombre} CON MENCIÓN EN {carrera.mencion} MODALIDAD {carrera.get_modalidad_display()}'
    return nombre

class Perms(models.Model):
    class Meta:
        permissions = (
            ("puede_firmar_certificados", "Puede firmar certificados"),
            ("puede_configurar_homologacion", "Puede configurar asignaturas homologables"),
            ("puede_procesar_certificados", "Puede procesar certificados"),
            # ("puede_eliminar_certificados", "Eliminar certificados"),
            # ("puede_modificar_unidades_certificadoras", "Modificar unidades certificadoras"),
            # ("puede_eliminar_unidades_certificadoras", "Eliminar unidades certificadoras"),
            # ("puede_modificar_asistentes_certificadoras", "Modificar asistentes certificadoras"),
            # ("puede_eliminar_asistentes_certificadoras", "Eliminar asistentes certificadoras"),
        )
ROLES_TIPO_CATEGORIA = (
    ('1', 'Admisión'),
    ('2', 'Pregrado'),
    ('3', 'Posgrado'),
)

class CategoriaServicio(ModeloBase):
    nombre = models.CharField(default='', max_length=200, verbose_name=u'Nombre')
    descripcion = models.TextField(default='', blank=True, null=True, verbose_name=u'Descripción')
    icono = models.TextField(default='', blank=True, null=True, verbose_name=u'Icono')
    roles = models.TextField(default='', max_length=50, blank=True, null=True, verbose_name=u'Roles')
    grupos = models.ManyToManyField(Group, verbose_name=u'Grupos', related_name='+')
    activo = models.BooleanField(default=True, verbose_name=u'Activo')

    def __str__(self):
        return self.nombre

    class Meta:
        verbose_name = u"Categoria"
        verbose_name_plural = u"Categorias"
        ordering = ['nombre']
        unique_together = ['nombre']

    def puede_eliminar(self):
        return not Servicio.objects.values("id").filter(categoria=self).exists()

    def get_displays_roles(self):
        listroles = []
        if self.roles:
            for rol in ROLES_TIPO_CATEGORIA:
                if rol[0] in self.roles:
                    listroles.append(rol)
        return listroles

    def displays_rol(self):
        cadena = ''
        if self.roles:
            c = 1
            for rol in ROLES_TIPO_CATEGORIA:
                if rol[0] in self.roles:
                    if c == len(self.roles.split(',')):
                        cadena += str(rol[1])
                        c += 1
                    else:
                        cadena += str(rol[1]) + ' - '
                        c += 1
        return cadena

    def es_admision(self):
        return True if '1' in self.roles else False

    def es_pregrado(self):
        return True if '2' in self.roles else False

    def es_posgrado(self):
        return True if '3' in self.roles else False

    def total_solicitudes(self):
        can = 0
        if self.id == 7:
            can = Solicitud.objects.filter(servicio__categoria=self).count()
        else:
            can = Solicitud.objects.filter(status=True, servicio__categoria=self).count()
        return can

    def total_solicitudes_2(self, persona):
        if persona.usuario.is_superuser:
            solicitudes = Solicitud.objects.filter(servicio__categoria=self).order_by('id').distinct()
        elif 'DIRECTOR DE LA ESCUELA DE POSGRADO DE EDUCACIÓN' in persona.usuario.groups.all().distinct().values_list('name', flat=True):
            solicitudes = Solicitud.objects.filter(servicio__categoria=self, perfil__inscripcion__carrera__escuelaposgrado__id=2).order_by('id').distinct()
        elif 'DIRECTOR DE LA ESCUELA DE POSGRADO DE CIENCIAS DE LA SALUD' in persona.usuario.groups.all().distinct().values_list('name', flat=True):
            solicitudes = Solicitud.objects.filter(servicio__categoria=self, perfil__inscripcion__carrera__escuelaposgrado__id=1).order_by('id').distinct()
        elif 'DIRECTOR DE LA ESCUELA DE POSGRADO DE NEGOCIOS Y DERECHO' in persona.usuario.groups.all().distinct().values_list('name', flat=True):
            solicitudes = Solicitud.objects.filter(servicio__categoria=self, perfil__inscripcion__carrera__escuelaposgrado__id=3).order_by('id').distinct()
        elif 'SOLO_TITULACION_EX' in persona.usuario.groups.all().distinct().values_list('name', flat=True):
            if CohorteMaestria.objects.filter(status=True, coordinador=persona).exists():
                idcarreras = CohorteMaestria.objects.filter(status=True, coordinador=persona).values_list('maestriaadmision__carrera__id', flat=True).order_by('maestriaadmision__carrera__id').distinct()
                solicitudes = Solicitud.objects.filter(servicio__categoria=self, perfil__inscripcion__carrera__id__in=idcarreras).order_by('id').distinct()
            else:
                solicitudes = Solicitud.objects.filter(servicio__categoria=self).order_by('id').distinct()
        else:
            solicitudes = Solicitud.objects.filter(servicio__categoria=self).order_by('id').distinct()
        return solicitudes.count()

    def total_solicitadas(self):
        return Solicitud.objects.filter(status=True, servicio__categoria=self, estado=1).count()

    def total_pendientes(self):
        return Solicitud.objects.filter(status=True, servicio__categoria=self, estado=3).count()

    def total_pagadas(self):
        return Solicitud.objects.filter(status=True, servicio__categoria=self, estado=4).count()

    def total_asignado(self):
        return Solicitud.objects.filter(status=True, servicio__categoria=self, estado=6).count()

    def total_reasignado(self):
        return Solicitud.objects.filter(status=True, servicio__categoria=self, estado=5).count()

    def total_rechazado(self):
        return Solicitud.objects.filter(status=True, servicio__categoria=self, estado=7).count()

    def total_vencidas(self):
        return Solicitud.objects.filter(status=True, servicio__categoria=self, estado=9).count()

    def total_entregados(self):
        return Solicitud.objects.filter(status=True, servicio__categoria=self, estado=2).count()

    def total_eliminados(self):
        return Solicitud.objects.filter(status=True, servicio__categoria=self, estado=8).count()

    def grupos_categoria(self):
        return self.grupos.all()

    def cantidades_gigantic(self):
        dicc = {}
        solicitudes = Solicitud.objects.filter(servicio__categoria=self).values_list('estado', flat=True).order_by('estado').distinct()
        for est in solicitudes:
            clave = dict(ESTADO_SOLICITUD)[est]
            valor = Solicitud.objects.filter(servicio__categoria=self, estado=est).distinct().count()
            dicc[clave] = valor
        return dicc

    def cantidades_gigantic_2(self, persona):
        try:
            dicc = {}
            if persona.usuario.is_superuser:
                solicitudes = Solicitud.objects.filter(servicio__categoria=self).values_list('estado', flat=True).order_by('estado').distinct()
                ids = Solicitud.objects.filter(servicio__categoria=self).values_list('id', flat=True).order_by('id').distinct()
            elif 'DIRECTOR DE LA ESCUELA DE POSGRADO DE EDUCACIÓN' in persona.usuario.groups.all().distinct().values_list('name', flat=True):
                solicitudes = Solicitud.objects.filter(servicio__categoria=self, perfil__inscripcion__carrera__escuelaposgrado__id=2).values_list('estado', flat=True).order_by('estado').distinct()
                ids = Solicitud.objects.filter(servicio__categoria=self, perfil__inscripcion__carrera__escuelaposgrado__id=2).values_list('id', flat=True).order_by('id').distinct()
            elif 'DIRECTOR DE LA ESCUELA DE POSGRADO DE CIENCIAS DE LA SALUD' in persona.usuario.groups.all().distinct().values_list('name', flat=True):
                solicitudes = Solicitud.objects.filter(servicio__categoria=self, perfil__inscripcion__carrera__escuelaposgrado__id=1).values_list('estado', flat=True).order_by('estado').distinct()
                ids = Solicitud.objects.filter(servicio__categoria=self, perfil__inscripcion__carrera__escuelaposgrado__id=1).values_list('id', flat=True).order_by('id').distinct()
            elif 'DIRECTOR DE LA ESCUELA DE POSGRADO DE NEGOCIOS Y DERECHO' in persona.usuario.groups.all().distinct().values_list('name', flat=True):
                solicitudes = Solicitud.objects.filter(servicio__categoria=self, perfil__inscripcion__carrera__escuelaposgrado__id=3).values_list('estado', flat=True).order_by('estado').distinct()
                ids = Solicitud.objects.filter(servicio__categoria=self, perfil__inscripcion__carrera__escuelaposgrado__id=3).values_list('id', flat=True).order_by('id').distinct()
            elif 'SOLO_TITULACION_EX' in persona.usuario.groups.all().distinct().values_list('name', flat=True):
                if CohorteMaestria.objects.filter(status=True, coordinador=persona).exists():
                    idcarreras = CohorteMaestria.objects.filter(status=True, coordinador=persona).values_list('maestriaadmision__carrera__id', flat=True).order_by('maestriaadmision__carrera__id').distinct()
                    solicitudes = Solicitud.objects.filter(servicio__categoria=self, perfil__inscripcion__carrera__id__in=idcarreras).values_list('estado', flat=True).order_by('estado').distinct()
                    ids = Solicitud.objects.filter(servicio__categoria=self, perfil__inscripcion__carrera__id__in=idcarreras).values_list('id', flat=True).order_by('id').distinct()
                else:
                    solicitudes = Solicitud.objects.filter(servicio__categoria=self).values_list('estado', flat=True).order_by('estado').distinct()
                    ids = Solicitud.objects.filter(servicio__categoria=self).values_list('id', flat=True).order_by('id').distinct()
            else:
                solicitudes = Solicitud.objects.filter(servicio__categoria=self).values_list('estado', flat=True).order_by('estado').distinct()
                ids = Solicitud.objects.filter(servicio__categoria=self).values_list('id', flat=True).order_by('id').distinct()

            for est in solicitudes:
                clave = dict(ESTADO_SOLICITUD)[est]
                valor = Solicitud.objects.filter(servicio__categoria=self, estado=est, id__in=ids).distinct().count()
                dicc[clave] = valor
            return dicc
        except Exception as ex:
            pass

    def estados_activos(self):
        dicc = {}
        solicitudes = Solicitud.objects.filter(servicio__categoria=self).values_list('estado', flat=True).order_by('estado').distinct()
        for est in solicitudes:
            clave = dict(ESTADO_SOLICITUD)[est]
            valor = est
            dicc[clave] = valor
        return dicc

    def save(self, *args, **kwargs):
        self.nombre = self.nombre.strip()
        self.descripcion = self.descripcion.strip()
        super(CategoriaServicio, self).save(*args, **kwargs)


PROCESO_SERVICIO = (
    (1, "Certificado Interno"),
    (2, "Certificado Externo"),
    (3, "Planes de estudios"),
    (4, "Copias certificadas"),
    (5, "Reimpresión de titulos"),
    (6, "Duplicados de carné"),
    (7, "Homologación"),
    (8, "Certificado Fisico"),
    (9, "Titulación Extraordinaria"),
    (10, "Certificados Rubrica"),
)


class Servicio(ModeloBase):
    orden = models.IntegerField(blank=True, null=True, default=0, verbose_name=u'Orden')
    nombre = models.CharField(default='', max_length=500, blank=True, null=True, verbose_name=u'Nombre')
    alias = models.CharField(default='', max_length=20, blank=True, null=True, verbose_name=u"Alias del servicio")
    categoria = models.ForeignKey(CategoriaServicio, on_delete=models.CASCADE, related_name='+', verbose_name=u'Categoria')
    tiporubro = models.ForeignKey('sagest.TipoOtroRubro', on_delete=models.CASCADE, blank=True, null=True, related_name='+', verbose_name=u'Tipo de Rubro')
    proceso = models.IntegerField(default=0, choices=PROCESO_SERVICIO, blank=True, null=True, verbose_name=u"Proceso")
    costo = models.DecimalField(max_digits=30, decimal_places=16, default=0, verbose_name=u'Costo')
    activo = models.BooleanField(default=True, verbose_name=u'Activo')

    def __str__(self):
        return f"{self.nombre} ({self.categoria.nombre}) - ${Decimal(self.costo).quantize(Decimal('.01'))}"

    class Meta:
        verbose_name = u"Servicio"
        verbose_name_plural = u"Servicios"
        ordering = ['categoria', 'nombre']
        unique_together = ['categoria', 'nombre']

    def puede_eliminar(self):
        from certi.models import Certificado
        eSolicitudes = Solicitud.objects.values("id").filter(servicio=self)
        if eSolicitudes.exists():
            return False
        if self.es_certificado():
            return not Certificado.objects.values("id").filter(servicio=self).exists()
        return True

    def es_certificado(self):
        return self.proceso in [1, 2]

    def solicitudes(self):
        self.solicitud_set.all()

    def certificados_ofertados(self):
        from certi.models import Certificado
        lista_cer =[]
        certificados = Certificado.objects.filter(status=True, servicio=self)
        for certificado in certificados:
            co = certificado.codigo + ' - ' +  certificado.certificacion
            lista_cer.append(co)
        return  lista_cer

    def save(self, *args, **kwargs):
        self.nombre = self.nombre.strip()
        self.alias = self.alias.strip()
        super(Servicio, self).save(*args, **kwargs)


ESTADO_SOLICITUD = (
    (1, u'Solicitado'),
    (2, u'Entregado'),
    (3, u'Pendiente'),
    (4, u'Pagado'),
    (5, u'Reasignado'),
    (6, u'Asignado'),
    (7, u'Rechazado'),
    (8, u'Eliminado'),
    (9, u'Vencido'),
    (10, u'Informe en proceso'),
    (11, u'Informe elaborado'),
    (12, u'Informe aprobado'),
    (13, u'Informe rechazado'),
    (14, u'Informe aceptado'),
    (15, u'Cronograma en proceso'),
    (16, u'Cronograma entregado'),
    (17, u'Informe revisado'),
    (18, u'Cronograma revisado'),
    (19, u'Cronograma elaborado'),
    (20, u'Cronograma aprobado'),
    (21, u'Cronograma rechazado'),
    (22, u'Pendiente de firmar'),
    (23, u'Borrador'),
    (24, u'Asignaturas revisadas'),
    (25, u'Asignaturas aceptadas'),
    (26, u'Homologación en proceso'),
    (27, u'Homologación ejecutada'),
)

ESTADO_SOLICITUD_COLOR = (
    (1, 'color: #3a87ad!important; font-weight: bold; font-size:12px'),
    (2, 'color: #198754!important; font-weight: bold; font-size:12px'),
    (3, 'color: #FE9900!important; font-weight: bold; font-size:12px'),
    (4, 'color: #0d6efd!important; font-weight: bold; font-size:12px'),
    (5, 'color: #6c757d!important; font-weight: bold; font-size:12px'),
    (6, 'color: #212529!important; font-weight: bold; font-size:12px'),
    (7, 'color: #dc3545!important; font-weight: bold; font-size:12px'),
    (8, 'color: #dc3545!important; font-weight: bold; font-size:12px'),
    (9, 'color: #dc3545!important; font-weight: bold; font-size:12px'),
    (10, 'color: #FE9900!important; font-weight: bold; font-size:12px'),
    (11, 'color: #000000!important; font-weight: bold; font-size:12px'),
    (12, 'color: #198754!important; font-weight: bold; font-size:12px'),
    (13, 'color: #dc3545!important; font-weight: bold; font-size:12px'),
    (14, 'color: #00BFFF!important; font-weight: bold; font-size:12px'),
    (15, 'color: #FE9900!important; font-weight: bold; font-size:12px'),
    (16, 'color: #00BFFF!important; font-weight: bold; font-size:12px'),
    (17, 'color: #FE9900!important; font-weight: bold; font-size:12px'),
    (18, 'color: #FE9900!important; font-weight: bold; font-size:12px'),
    (19, 'color: #000000!important; font-weight: bold; font-size:12px'),
    (20, 'color: #198754!important; font-weight: bold; font-size:12px'),
    (21, 'color: #dc3545!important; font-weight: bold; font-size:12px'),
    (22, 'color: #FE9900!important; font-weight: bold; font-size:12px'),
    (23, 'color: #282828!important; font-weight: bold; font-size:12px'),
    (24, 'color: #3a87ad!important; font-weight: bold; font-size:12px'),
    (25, 'color: #198754!important; font-weight: bold; font-size:12px'),
    (26, 'color: #FE9900!important; font-weight: bold; font-size:12px'),
    (27, 'color: #198754!important; font-weight: bold; font-size:12px'),
)

TIPO_DOCUMENTO = (
    (1, u'Ninguno'),
    (2, u'Documento físico'),
    (3, u'Documento con firma electrónica'),
)

def solicitud_user_directory_path(instance, filename):
    # print(instance)
    fecha = datetime.now().date()
    return 'secretaria/solicitud/{0}/{1}/{2}/{3}/{4}'.format(instance.perfil.persona.pk, fecha.year, fecha.month, fecha.day, filename)


class Solicitud(ModeloBase):
    codigo = models.CharField(default='', max_length=100, blank=True, null=True, verbose_name=u'Código', db_index=True)
    secuencia = models.IntegerField(default=0, blank=True, null=True, verbose_name=u'Secuencia')
    prefix = models.CharField(blank=True, null=True, max_length=10, verbose_name=u'Prefijo del código')
    suffix = models.CharField(blank=True, null=True, max_length=10, verbose_name=u'Sufijo del código')
    perfil = models.ForeignKey(PerfilUsuario, on_delete=models.CASCADE, related_name='+', verbose_name=u'Perfil')
    servicio = models.ForeignKey(Servicio, on_delete=models.CASCADE, related_name='+', verbose_name=u'Servicio')
    origen_content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE, related_name='+', verbose_name=u'Modelo de origen', blank=True, null=True)
    origen_object_id = models.PositiveIntegerField(blank=True, null=True, verbose_name=u'ID de origen')
    descripcion = models.TextField(default='', verbose_name=u'Descripción')
    parametros = models.JSONField(verbose_name=u'Parametros', null=True, blank=True)
    archivo_solicitud = models.FileField(upload_to=solicitud_user_directory_path, max_length=1000, blank=True, null=True, verbose_name=u'Archivo de solicitud')
    fecha = models.DateField(blank=True, null=True, verbose_name=u"Fecha")
    hora = models.TimeField(blank=True, null=True, verbose_name=u"Hora")
    estado = models.IntegerField(default=1, choices=ESTADO_SOLICITUD, verbose_name=u'Estado')
    responsable = models.ForeignKey(Persona, on_delete=models.CASCADE, blank=True, null=True, related_name='+', verbose_name=u'Responsable')
    destino_content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE, related_name='+', verbose_name=u'Modelo de destino', blank=True, null=True)
    destino_object_id = models.PositiveIntegerField(blank=True, null=True, verbose_name=u'ID de destino')
    archivo_respuesta = models.FileField(upload_to=solicitud_user_directory_path, max_length=1000, blank=True, null=True, verbose_name=u'Archivo de respuesta')
    cantidad = models.IntegerField(blank=True, null=True, default=0, verbose_name=u'Cantidad')
    valor_unitario = models.DecimalField(max_digits=30, decimal_places=16, default=0, verbose_name=u'Valor unitario')
    subtotal = models.DecimalField(max_digits=30, decimal_places=16, default=0, verbose_name=u'Subtotal')
    iva = models.DecimalField(max_digits=30, decimal_places=16, default=0, verbose_name=u'I.V.A')
    descuento = models.DecimalField(max_digits=30, decimal_places=16, default=0, verbose_name=u'Descuento')
    tiempo_cobro = models.IntegerField(default=72, blank=True, null=True, verbose_name=u"Tiempo de cobro solicitud")
    en_proceso = models.BooleanField(default=False, verbose_name=u'En proceso de atención')
    origen_content_object = GenericForeignKey('origen_content_type', 'origen_object_id')
    destino_content_object = GenericForeignKey('destino_content_type', 'destino_object_id')
    archivo_solicitud_fisica = models.FileField(upload_to=solicitud_user_directory_path, max_length=1000, blank=True, null=True, verbose_name=u'Archivo de solicitud de certificado físico')
    fecha_retiro = models.DateField(blank=True, null=True, verbose_name=u"Fecha de retiro de certificado físico")
    hora_retiro = models.TimeField(blank=True, null=True, verbose_name=u"Hora e retiro de certificado físico")
    lugar_retiro = models.TextField(default='', verbose_name=u'Lugar de retiro')
    notificado_fisico = models.BooleanField(default=False, verbose_name=u'Notifica certificados físicos')
    notificado_segundorubro = models.BooleanField(default=False, verbose_name=u'Notifica pago de segundo rubro')
    tipodocumento = models.IntegerField(default=1, choices=TIPO_DOCUMENTO, verbose_name=u'Tipo de documento')
    certificadofirmado = models.BooleanField(default=False, verbose_name=u'¿Se ha firmado el certificado?')
    respaldo = models.FileField(upload_to='respaldocertificado/%Y/%m/%d', blank=True, null=True, verbose_name=u'Respaldo de certificado')
    inscripcioncohorte = models.ForeignKey('posgrado.InscripcionCohorte', blank=True, null=True, verbose_name=u'Aspirante', on_delete=models.CASCADE)
    firmadoec = models.BooleanField(default=False, verbose_name=u'¿Se ha firmado con firma electrónica?')
    carrera_homologada = models.ForeignKey('sga.Carrera', blank=True, null=True, verbose_name=u'Carrera con la que se va a homologar', on_delete=models.CASCADE)
    visible = models.BooleanField(default=False, verbose_name=u'¿Mostrar notas de asignaturas?')
    ficha = models.FileField(upload_to=solicitud_user_directory_path, max_length=1000, blank=True, null=True, verbose_name=u'Ficha de homologación posgrado')

    def __str__(self):
        return f"{self.perfil.persona.__str__()} - {self.servicio.nombre} ({self.fecha.__str__()} {self.hora.__str__()})"

    def total(self):
        return Decimal(self.subtotal + self.iva + self.descuento).quantize(Decimal('.01'))

    def puede_eliminar(self):
        return (not self.en_proceso and (self.estado == 1 )) and not self.estado == 8

    def color_estado_display(self):
        return dict(ESTADO_SOLICITUD_COLOR)[self.estado]

    def generar_certificado(self,persona=None):
        from secretaria.funciones import generar_certificado_digital
        per = persona.usuario if persona else self.perfil.persona.usuario
        eCertificado = self.origen_content_object
        parametros = self.parametros
        ids_persona = [x.id for x in Persona.objects.filter(pk__in=[self.perfil.persona_id])]
        parametros['dirigidos'] = json.dumps(ids_persona)
        parametros['no_persona_session'] = True
        parametros['app'] = 'sie'
        result, aData, mensaje = generar_certificado_digital(self.perfil.persona, eCertificado.reporte, per, parametros, self)
        if not result:
            raise NameError(mensaje)

    def procesar_pago_certificado_digital(self, eRubro):
        from sga.models import Notificacion
        eSolicitud = self
        ePagos = eRubro.pago_set.filter(status=True)
        if eRubro.cancelado:
            eSolicitud.en_proceso = True
            eSolicitud.estado = 4
            eSolicitud.save()
            eSolicitud.crea_historial_pago(ePagos)
            self.generar_certificado()
        elif ePagos.values("id").exists():
            eSolicitud.en_proceso = True
            eSolicitud.estado = 3
            eSolicitud.save()
            fechas = list(ePagos.values_list('fecha')) if ePagos.values("id").exists() else []
            eSolicitud.crea_historial_pago(ePagos)
            eSolicitud.generar_notificacion(eSolicitud.perfil.persona)

    def procesar_pagos(self, eRubro):
        if self.servicio.proceso in (1, 2, 10):
            self.procesar_pago_certificado_digital(eRubro)

    def save(self, *args, **kwargs):
        super(Solicitud, self).save(*args, **kwargs)

    def crea_historial_pago(self, ePagos):
        from sga.models import Notificacion
        eSolicitud = self
        eSolicitud.proceso = True
        for pago in ePagos:
            pagoContentType = ContentType.objects.get_for_model(pago)
            eHistorialSolicitud = HistorialSolicitud(solicitud=eSolicitud,
                                                     observacion=f'Realizó un pago por el valor de: ',
                                                     fecha=datetime.now().date(),
                                                     hora=datetime.now().time(),
                                                     estado=eSolicitud.estado,
                                                     responsable_id=1,
                                                     destino_content_type=pagoContentType,
                                                     destino_object_id=pago.id)
            eHistorialSolicitud.save()

    def fecha_limite_pago(self):
        fecha_limite = datetime.combine(self.fecha, self.hora) + timedelta(hours=self.tiempo_cobro)
        return fecha_limite

    def anular_solicitud(self):
        self.estado = 8
        self.save()
        return self.estado

    def anular_solicitudes_vencidas(self):
        eSolicitudes = Solicitud.objects.filter(status=True, estado__in=(1,3))
        for eSolicitud in eSolicitudes:
            fecha_limite = eSolicitud.fecha_limite_pago()
            if fecha_limite <= datetime.today():
                solicitudVencida = eSolicitud
                ePersona = solicitudVencida.perfil.persona
                solicitudVencida.estado = 9
                solicitudVencida.en_proceso = False
                solicitudVencida.save()
                eRubro = Rubro.objects.get(persona= ePersona, solicitud=solicitudVencida)
                # if not eRubro.tiene_pagos():
                #     eRubro.status = False
                #     eRubro.save()
                #eRubro.delete()
                eHistorialSolicitud = HistorialSolicitud(solicitud=solicitudVencida,
                                                         observacion=f'Cambio de estado por solicitud vencida',
                                                         fecha=datetime.now().date(),
                                                         hora=datetime.now().time(),
                                                         estado=solicitudVencida.estado,
                                                         responsable=ePersona)
                eHistorialSolicitud.save()

                solicitudVencida.generar_notificacion(ePersona)



        eSolicitudes = Solicitud.objects.filter(status=True, estado=9)

        if eSolicitudes:
            for solicitudVencida in eSolicitudes:
                fecha_comparacion= solicitudVencida.fecha_limite_pago() + timedelta(days=1)
                ePersona = solicitudVencida.perfil.persona
                if fecha_comparacion.date() < datetime.today().date():
                    eRubro = Rubro.objects.get(persona= ePersona, solicitud=solicitudVencida)
                    if eRubro.tiene_pagos():
                        solicitudVencida.estado = 3
                        solicitudVencida.en_proceso = True
                        eRubro.save()
                    else:
                        eRubro.status = False
                        solicitudVencida.en_proceso = False
                        eRubro.save()

    def verificar_proceso(self, persona):
        if self.estado == 1 :
            self.en_proceso = True
            self.estado = 3
            self.save()
            eHistorialSolicitud = HistorialSolicitud(solicitud=self,
                                                             observacion=f'Cambio de estado por proceso de atención',
                                                             fecha=datetime.now().date(),
                                                             hora=datetime.now().time(),
                                                             estado=self.estado,
                                                             responsable=persona)
            eHistorialSolicitud.save()

    def generar_historial(self, responsable, observacion):

        eHistorialSolicitud = HistorialSolicitud(solicitud=self,
                                                 observacion=observacion,
                                                 fecha=datetime.now().date(),
                                                 hora=datetime.now().time(),
                                                 estado=self.estado,
                                                 responsable=responsable)
        eHistorialSolicitud.save()

    def verificar_fecha(self, fecha_verificacion):
        try:
            fecha_verificacion = fecha_verificacion
            fecha_comparacion = self.fecha_limite_pago().date() + timedelta(days=1)
            if fecha_verificacion.date() >= fecha_comparacion:
                if not self.en_proceso and self.estado == 9:
                    #rubro = self.rubro_set.filter(solicitud=self)[0]
                    rubro = Rubro.objects.get(solicitud=self)
                    pago = rubro.pago_set.filter(status=True)
                    if pago:
                        self.estado == 3
                        rubro.status = True
                        rubro.save()
        except Exception as ex:
            import sys
            raise NameError(f"Error def verificar_fecha: {ex} - linea: {sys.exc_info()[-1].tb_lineno}")

    def generar_notificacion(self, ePersona):
        eSolicitud = self
        titulo = f'Cambio de estado de la solicitud código {eSolicitud.codigo}'
        cuerpo = f'Solicitud código {eSolicitud.codigo} se encuentra en estado {eSolicitud.get_estado_display()}'
        eNotificacion = Notificacion(titulo=titulo,
                                     cuerpo=cuerpo,
                                     destinatario=ePersona,
                                     perfil=eSolicitud.perfil,
                                     url='/alu_secretaria/mis_pedidos',
                                     prioridad=1,
                                     app_label='SIE',
                                     fecha_hora_visible=datetime.now() + timedelta(days=2),
                                     tipo=1,
                                     en_proceso=False,
                                     content_type=ContentType.objects.get_for_model(eSolicitud),
                                     object_id=eSolicitud.pk,
                                     )
        eNotificacion.save()

    def generar_notificacion_2(self, ePersona):
        eSolicitud = self
        titulo = f'Cambio de estado de la solicitud código {eSolicitud.codigo}'
        cuerpo = f'Solicitud código {eSolicitud.codigo} se encuentra en estado {eSolicitud.get_estado_display()}. Le recordamos que tiene 3 días más para efectuar el pago. De lo contrario, los rubros serán eliminados y la solicitud también y tendrá que repetir el proceso.'
        eNotificacion = Notificacion(titulo=titulo,
                                     cuerpo=cuerpo,
                                     destinatario=ePersona,
                                     perfil=eSolicitud.perfil,
                                     url='/alu_secretaria/mis_pedidos',
                                     prioridad=1,
                                     app_label='SIE',
                                     fecha_hora_visible=datetime.now() + timedelta(days=2),
                                     tipo=1,
                                     en_proceso=False,
                                     content_type=ContentType.objects.get_for_model(eSolicitud),
                                     object_id=eSolicitud.pk,
                                     )
        eNotificacion.save()


    def obtener_pagos(self):
        eRubro = Rubro.objects.get(solicitud= self)
        ePagos = eRubro.pago_set.filter(status= True)
        return ePagos

    def tiene_rubro_pagado(self):
        from sagest.models import Pago
        eRubro = Rubro.objects.filter(status=True, solicitud=self, cancelado=True).order_by('id').first()
        return True if Pago.objects.filter(status=True, rubro=eRubro).exists() else False

    def tiene_rubro_pagado2(self):
        from sagest.models import Pago
        eRubro = Rubro.objects.filter(status=True, solicitud=self, cancelado=True).order_by('id').first()
        return '1' if Pago.objects.filter(status=True, rubro=eRubro).exists() else '0'

    def tiene_rubro_generado(self):
        return True if Rubro.objects.filter(status=True, solicitud=self, tipo=self.servicio.tiporubro).exists() else False

    def tiene_2do_rubro_pagado(self):
        from sagest.models import Pago
        eRubro = Rubro.objects.filter(status=True, solicitud=self, cancelado=True, tipo__id=3442).order_by('id').first()
        return True if Pago.objects.filter(status=True, rubro=eRubro).exists() else False

    def tiene_rubro_informe(self):
        return True if Rubro.objects.filter(status=True, solicitud=self, tipo__id=3401).exists() else False

    def tiene_rubro_ingreso(self):
        return True if Rubro.objects.filter(status=True, solicitud=self, tipo__id=3442).exists() else False

    def certificado_solicitado(self):
        from certi.models import Certificado
        certifi = Certificado.objects.get(pk=self.origen_object_id)
        return certifi

    def esta_siendo_atendido(self):
        return True if HistorialSolicitud.objects.filter(status=True, atendido=True, solicitud=self) else False

    def secretaria_encargada(self):
        histo = HistorialSolicitud.objects.filter(status=True, atendido=True, solicitud=self).order_by('-id').first()
        return histo.responsable

    def tiene_actividades_tituex(self):
        from posgrado.models import DetalleActividadCronogramaTitulacion
        return True if DetalleActividadCronogramaTitulacion.objects.filter(status=True, solicitud=self).exists() else False

    def download_descargado(self):
        return self.archivo_solicitud.url

    def lista_asignaturas(self):
        return SolicitudAsignatura.objects.filter(status=True, solicitud=self).exclude(estado=4).order_by('id').distinct()

    def lista_asignaturas_nombres(self):
        asignaturas = SolicitudAsignatura.objects.filter(status=True, solicitud=self).order_by('id').distinct()
        nombres_asignaturas = ", ".join(asig.asignaturamalla.asignatura.nombre for asig in asignaturas)
        return f'{nombres_asignaturas}.'

    def lista_asignaturas_favorables(self):
        asignaturas = SolicitudAsignatura.objects.filter(status=True, solicitud=self, estado=2).order_by('id').distinct()
        nombres_asignaturas = ", ".join(asig.asignaturamalla.asignatura.nombre for asig in asignaturas)
        return f'{nombres_asignaturas}.'

    def lista_asignaturas_no_favorables(self):
        asignaturas = SolicitudAsignatura.objects.filter(status=True, solicitud=self, estado=3).order_by('id').distinct()
        nombres_asignaturas = ", ".join(asig.asignaturamalla.asignatura.nombre for asig in asignaturas)
        return f'{nombres_asignaturas}.'

    def notificar_escuela(self):
        if self.perfil.inscripcion.carrera.id in PerfilAccesoUsuario.objects.filter(status=True, grupo__name__exact='DIRECTOR DE LA ESCUELA DE POSGRADO DE EDUCACIÓN').values_list('carrera_id', flat=True):
            cargo = 'DIRECTOR DE LA ESCUELA DE POSGRADO DE EDUCACIÓN'
            dir = Persona.objects.filter(usuario__groups__name=cargo).order_by('id').first()
            titulo = "REVISIÓN DE INFORME TÉCNICO DE PERTINENCIA"
            cuerpo = f'Se informa a {dir} que el coordinador del programa de {self.perfil.inscripcion.carrera} ha subido el informe técnico de pertinencia del maestrante {self.perfil.inscripcion.persona}. Por favor, realizar la respectiva revisión y la posterior aprobación o rechazo para continuar con el proceso.'

            notificacion2(titulo, cuerpo, dir, None, '/adm_secretaria?action=versolicitudes&id=' + str(self.servicio.categoria.id) + '&ids=0&s=' + str(self.codigo), dir.pk, 1, 'sga', dir)
        elif self.perfil.inscripcion.carrera.id in PerfilAccesoUsuario.objects.filter(status=True, grupo__name__exact='DIRECTOR DE LA ESCUELA DE POSGRADO DE CIENCIAS DE LA SALUD').values_list('carrera_id', flat=True):
            cargo = 'DIRECTOR DE LA ESCUELA DE POSGRADO DE CIENCIAS DE LA SALUD'
            dir = Persona.objects.filter(usuario__groups__name=cargo).order_by('id').first()
            titulo = "REVISIÓN DE INFORME TÉCNICO DE PERTINENCIA"
            cuerpo = f'Se informa a {dir} que el coordinador del programa de {self.perfil.inscripcion.carrera} ha subido el informe técnico de pertinencia del maestrante {self.perfil.inscripcion.persona}. Por favor, realizar la respectiva revisión y la posterior aprobación o rechazo para continuar con el proceso.'

            notificacion2(titulo, cuerpo, dir, None, '/adm_secretaria?action=versolicitudes&id=' + str(self.servicio.categoria.id) + '&ids=0&s=' + str(self.codigo), dir.pk, 1, 'sga', dir)
        elif self.perfil.inscripcion.carrera.id in PerfilAccesoUsuario.objects.filter(status=True, grupo__name__exact='DIRECTOR DE LA ESCUELA DE POSGRADO DE NEGOCIOS Y DERECHO').values_list('carrera_id', flat=True):
            cargo = 'DIRECTOR DE LA ESCUELA DE POSGRADO DE NEGOCIOS Y DERECHO'
            dir = Persona.objects.filter(usuario__groups__name=cargo).order_by('id').first()
            titulo = "REVISIÓN DE INFORME TÉCNICO DE PERTINENCIA"
            cuerpo = f'Se informa a {dir} que el coordinador del programa de {self.perfil.inscripcion.carrera} ha subido el informe técnico de pertinencia del maestrante {self.perfil.inscripcion.persona}. Por favor, realizar la respectiva revisión y la posterior aprobación o rechazo para continuar con el proceso.'

            notificacion2(titulo, cuerpo, dir, None, '/adm_secretaria?action=versolicitudes&id=' + str(self.servicio.categoria.id) + '&ids=0&s=' + str(self.codigo), dir.pk, 1, 'sga', dir)
        return True

    def coordinador(self):
        coordinador = None
        if CohorteMaestria.objects.filter(status=True, maestriaadmision__carrera=self.perfil.inscripcion.carrera).exists():
            coordinador = CohorteMaestria.objects.filter(status=True, maestriaadmision__carrera=self.perfil.inscripcion.carrera).order_by('-id').first().coordinador
        return coordinador

    def solicitud_asignatura(self, eAsignatura):
        try:
            from sga.models import Malla, AsignaturaMalla
            soli = None

            if SolicitudAsignatura.objects.filter(status=True, solicitud=self, asignaturamalla__asignatura__id=eAsignatura.id).exists():
                soli = SolicitudAsignatura.objects.filter(status=True, solicitud=self, asignaturamalla__asignatura__id=eAsignatura.id).first()
            return soli
        except Exception as ex:
            pass

    def solicitud_asignatura_matches(self, eAsignaturaMalla):
        try:
            from sga.models import Inscripcion, InscripcionMalla, AsignaturaMalla, RecordAcademico
            reg = None
            inscrito = Inscripcion.objects.filter(status=True, carrera=self.perfil.inscripcion.carrera, persona=self.perfil.persona).first()
            malla = InscripcionMalla.objects.filter(status=True, inscripcion=inscrito).first().malla
            idch = AsignaturaMalla.objects.filter(status=True, malla=malla, nohomologa=False).values_list('asignatura__id', flat=True)

            inscritoa = Inscripcion.objects.filter(status=True, carrera=self.carrera_homologada, persona=self.perfil.persona).first()
            if eAsignaturaMalla.asignatura.id in idch:
                reg = AsignaturaMalla.objects.filter(status=True, malla=malla, nohomologa=False, asignatura__id=eAsignaturaMalla.asignatura.id).first()
            return reg
        except Exception as ex:
            pass

    def solicitud_asignatura_record(self, eAsignaturaMalla):
        try:
            from sga.models import Inscripcion, InscripcionMalla, AsignaturaMalla, RecordAcademico
            reg = None

            inscrito = Inscripcion.objects.filter(status=True, carrera=self.perfil.inscripcion.carrera, persona=self.perfil.persona).first()
            malla = InscripcionMalla.objects.filter(status=True, inscripcion=inscrito).first().malla
            idch = AsignaturaMalla.objects.filter(status=True, malla=malla, nohomologa=False).values_list('asignatura__id', flat=True)

            inscritoa = Inscripcion.objects.filter(status=True, carrera=self.carrera_homologada, persona=self.perfil.persona).first()

            idasis = AsignaturaCompatibleHomologacion.objects.filter(status=True, asignaturach=eAsignaturaMalla).values_list('asignaturama__id', flat=True).order_by('asignaturama__id').distinct()

            if AsignaturaCompatibleHomologacion.objects.filter(status=True, asignaturach=eAsignaturaMalla).exists():
                eAsignaturasAplica = AsignaturaCompatibleHomologacion.objects.filter(status=True, asignaturach=eAsignaturaMalla)

                for eAsiA in eAsignaturasAplica:
                    if RecordAcademico.objects.filter(status=True, inscripcion__persona=inscritoa.persona, asignaturamalla_id=eAsiA.asignaturama.id).exists():
                        reg = RecordAcademico.objects.filter(status=True, inscripcion__persona=inscritoa.persona,
                                                             asignaturamalla_id=eAsiA.asignaturama.id).first()
                return reg

            elif eAsignaturaMalla.asignatura.id in idch:
                reg = RecordAcademico.objects.filter(status=True, inscripcion=inscritoa, asignaturamalla__asignatura=eAsignaturaMalla.asignatura).first()

                return reg
            else:
                return None
        except Exception as ex:
            pass

    def record_academia(self, eAsignaturaMalla):
        try:
            from sga.models import Inscripcion, InscripcionMalla, AsignaturaMalla, RecordAcademico
            reg = None
            inscritoa = Inscripcion.objects.filter(status=True, carrera=self.carrera_homologada, persona=self.perfil.persona).first()
            if RecordAcademico.objects.filter(status=True, inscripcion=inscritoa, asignaturamalla__asignatura=eAsignaturaMalla.asignatura, asignaturamalla__nohomologa=False).exists():
                reg = RecordAcademico.objects.filter(status=True, inscripcion=inscritoa, asignaturamalla__asignatura=eAsignaturaMalla.asignatura, asignaturamalla__nohomologa=False).first()
            return reg
        except Exception as ex:
            pass

    def ficha_homologacion(self):
        from sga.models import InscripcionMalla, AsignaturaMalla, RecordAcademico
        try:
            eRecordsLi = []

            eSolicitud = self
            eInscripcionHo = Inscripcion.objects.get(status=True, carrera=eSolicitud.carrera_homologada,
                                                     persona=eSolicitud.perfil.persona)
            eInscripcionMallaHo = InscripcionMalla.objects.get(status=True, inscripcion=eInscripcionHo)
            eAsignaturasMallaHo = AsignaturaMalla.objects.filter(status=True, malla=eInscripcionMallaHo.malla)

            eInscripcionNew = Inscripcion.objects.get(status=True, carrera=eSolicitud.perfil.inscripcion.carrera,
                                                      persona=eSolicitud.perfil.persona)
            eInscripcionMallaNew = InscripcionMalla.objects.get(status=True, inscripcion=eInscripcionNew)
            eAsignaturasMallaNew = AsignaturaMalla.objects.filter(status=True, malla=eInscripcionMallaNew.malla)

            eSolicitudesAsignatura = SolicitudAsignatura.objects.filter(status=True, solicitud=eSolicitud,
                                                                        record__isnull=False)
            eRecordsLi = []
            c = id = 0
            eSolicitudA = eSolicitudB = eSolicitudC = None
            tienefavorable = 0
            for eAsignaturaHo in eAsignaturasMallaHo:
                eRecord = eSolicitud.record_academia(eAsignaturaHo)

                eRecordsLi.append({
                    "id": eAsignaturaHo.id,
                    "asignatura": eRecord.asignaturamalla.asignatura.nombre if eRecord is not None else eAsignaturaHo.asignatura.nombre,
                    "nota": eRecord.nota if eRecord is not None else 0,
                    "horas": eRecord.horas if eRecord is not None else eAsignaturaHo.horas,
                    "creditos": eRecord.creditos if eRecord is not None else eAsignaturaHo.creditos,
                    "asignatura2": '',
                    "nota2": 0,
                    "horas2": 0,
                    "creditos2": 0,
                    "color": '',
                    "porcentaje": 0,
                    "color2": '',
                    "colorfont": '',
                    "nos": '',
                    "orden": 0,
                    "solasi": None,
                    "idasih": 0
                })

            for eSolicitudAsignatura in eSolicitudesAsignatura:
                for eRecordLi in eRecordsLi:
                    if eRecordLi['id'] == eSolicitudAsignatura.record.asignaturamalla.id:
                        eRecordLi['asignatura2'] = eSolicitudAsignatura.asignaturamalla.asignatura.nombre
                        eRecordLi['nota2'] = eSolicitudAsignatura.record.nota
                        eRecordLi['horas2'] = eSolicitudAsignatura.record.horas
                        eRecordLi['creditos2'] = eSolicitudAsignatura.record.creditos
                        eRecordLi['porcentaje'] = 100
                        eRecordLi['orden'] = 3
                        eRecordLi['idasih'] = eSolicitudAsignatura.asignaturamalla.id
                        eRecordLi['solasi'] = eSolicitudAsignatura
                        if eSolicitudAsignatura.estado == 4:
                            eRecordLi['color'] = '#FE9900'
                            eRecordLi['color2'] = '#FE9900'
                            eRecordLi['colorfont'] = 'white'
                            eRecordLi['nos'] = 'no'
                            tienefavorable = 1
                        else:
                            eRecordLi['color'] = '#198754'
                            eRecordLi['color2'] = '#124076'
                            eRecordLi['colorfont'] = 'white'
                            tienefavorable = 1

            valores_id_sin_cero = [diccionario["idasih"] for diccionario in eRecordsLi if diccionario["idasih"] != 0]

            diccionarios_con_id_cero = [diccionario for diccionario in eRecordsLi if diccionario["idasih"] == 0]

            c = 0
            for eRecordLi in diccionarios_con_id_cero:
                if c <= eAsignaturasMallaNew.exclude(id__in=valores_id_sin_cero).distinct().count() - 1:
                    eSolicitudAsignatura2 = eAsignaturasMallaNew.exclude(id__in=valores_id_sin_cero)[c]
                    eRecordLi['asignatura2'] = eSolicitudAsignatura2.asignatura.nombre
                    eRecordLi['nota2'] = 0
                    eRecordLi['horas2'] = eSolicitudAsignatura2.horas
                    eRecordLi['creditos2'] = eSolicitudAsignatura2.creditos
                    eRecordLi['porcentaje'] = 0
                    eRecordLi['orden'] = 0
                    eRecordLi['idasih'] = eSolicitudAsignatura2.id
                    if eSolicitud.solicitud_asignatura(eSolicitudAsignatura2.asignatura):
                        eRecordLi['color'] = '#124076'
                        eRecordLi['color2'] = '#124076'
                        eRecordLi['colorfont'] = 'white'
                        eRecordLi['orden'] = 1

                    c += 1

            valores_id_sin_cero2 = [diccionario["idasih"] for diccionario in eRecordsLi if diccionario["idasih"] != 0]

            if eAsignaturasMallaNew.exclude(id__in=valores_id_sin_cero2).distinct().count() > 0:
                for eAsignatura3 in eAsignaturasMallaNew.exclude(id__in=valores_id_sin_cero2).distinct():
                    eRecordsLi.append({
                        "id": '',
                        "asignatura": '',
                        "nota": '',
                        "horas": '',
                        "creditos": '',
                        "asignatura2": eAsignatura3.asignatura.nombre,
                        "nota2": 0,
                        "horas2": eAsignatura3.horas,
                        "creditos2": eAsignatura3.creditos,
                        "color": '',
                        "porcentaje": 0,
                        "color2": '',
                        "colorfont": '',
                        "nos": '',
                        "orden": 0,
                        "solasi": None,
                        "idasih": 0
                    })

            eRecordsLi = sorted(eRecordsLi, key=lambda x: x["orden"], reverse=True)
            return eRecordsLi
        except Exception as ex:
            pass

    def fecha_recepcion(self):
        try:
            fecha = HistorialSolicitud.objects.filter(status=True, solicitud=self, estado=1).order_by('-id').first().fecha
            dia = fecha.day
            mes = ''
            if fecha.month == 1:
                mes = 'ENERO'
            elif fecha.month == 2:
                mes = 'FEBRERO'
            elif fecha.month == 3:
                mes = 'MARZO'
            elif fecha.month == 4:
                mes = 'ABRIL'
            elif fecha.month == 5:
                mes = 'MAYO'
            elif fecha.month == 6:
                mes = 'JUNIO'
            elif fecha.month == 7:
                mes = 'JULIO'
            elif fecha.month == 8:
                mes = 'AGOSTO'
            elif fecha.month == 9:
                mes = 'SEPTIEMBRE'
            elif fecha.month == 10:
                mes = 'OCTUBRE'
            elif fecha.month == 11:
                mes = 'NOVIEMBRE'
            elif fecha.month == 12:
                mes = 'DICIEMBRE'
            anio = fecha.year
            return f'{dia} DE {mes} DE {anio}'
        except Exception as ex:
            pass

    def fecha_revision(self):
        try:
            fecha = HistorialSolicitud.objects.filter(status=True, solicitud=self, estado=24).order_by('-id').first().fecha
            dia = fecha.day
            mes = ''
            if fecha.month == 1:
                mes = 'ENERO'
            elif fecha.month == 2:
                mes = 'FEBRERO'
            elif fecha.month == 3:
                mes = 'MARZO'
            elif fecha.month == 4:
                mes = 'ABRIL'
            elif fecha.month == 5:
                mes = 'MAYO'
            elif fecha.month == 6:
                mes = 'JUNIO'
            elif fecha.month == 7:
                mes = 'JULIO'
            elif fecha.month == 8:
                mes = 'AGOSTO'
            elif fecha.month == 9:
                mes = 'SEPTIEMBRE'
            elif fecha.month == 10:
                mes = 'OCTUBRE'
            elif fecha.month == 11:
                mes = 'NOVIEMBRE'
            elif fecha.month == 12:
                mes = 'DICIEMBRE'
            anio = fecha.year
            return f'{dia} {mes} /{anio}'
        except Exception as ex:
            pass

    def director_escuela(self):
        director = ''
        if self.perfil.inscripcion.carrera.id in PerfilAccesoUsuario.objects.filter(status=True,
                                                                                    grupo__name__exact='DIRECTOR DE LA ESCUELA DE POSGRADO DE EDUCACIÓN').values_list(
                'carrera_id', flat=True):
            cargo = 'DIRECTOR DE LA ESCUELA DE POSGRADO DE EDUCACIÓN'
            director = Persona.objects.filter(usuario__groups__name=cargo).order_by('id').first()
        elif self.perfil.inscripcion.carrera.id in PerfilAccesoUsuario.objects.filter(status=True,
                                                                                      grupo__name__exact='DIRECTOR DE LA ESCUELA DE POSGRADO DE CIENCIAS DE LA SALUD').values_list(
                'carrera_id', flat=True):
            cargo = 'DIRECTOR DE LA ESCUELA DE POSGRADO DE CIENCIAS DE LA SALUD'
            director = Persona.objects.filter(usuario__groups__name=cargo).order_by('id').first()
        elif self.perfil.inscripcion.carrera.id in PerfilAccesoUsuario.objects.filter(status=True,
                                                                                      grupo__name__exact='DIRECTOR DE LA ESCUELA DE POSGRADO DE NEGOCIOS Y DERECHO').values_list(
                'carrera_id', flat=True):
            cargo = 'DIRECTOR DE LA ESCUELA DE POSGRADO DE NEGOCIOS Y DERECHO'
            director = Persona.objects.filter(usuario__groups__name=cargo).order_by('id').first()
        return director.__str__() if director else ''

    def descargar_ficha(self):
        from settings import MEDIA_URL, MEDIA_ROOT, SITE_STORAGE
        import xlsxwriter
        from sga.funciones import null_to_decimal
        from django.db.models import Sum
        try:
            __author__ = 'Unemi'

            eSolicitud = self
            ruta = f'{SITE_STORAGE}/static/logos/logo_posgrado_mailing.png'
            ruta = ruta.replace('\\', '/')

            directory = os.path.join(MEDIA_ROOT, 'reportes', 'fichas_homologacion')
            try:
                os.stat(directory)
            except:
                os.mkdir(directory)
            nombre_archivo = f'Ficha_homologacion_{eSolicitud.codigo}.xlsx'
            directory = os.path.join(MEDIA_ROOT, 'reportes', 'fichas_homologacion', nombre_archivo)

            workbook = xlsxwriter.Workbook(directory)
            ws = workbook.add_worksheet('fichas')
            ws.set_column(0, 0, 5)
            ws.set_row(20, 30)
            ws.set_row(21, 50)

            ws.set_row(22, 50)
            ws.set_row(23, 50)
            ws.set_row(24, 50)
            ws.set_row(25, 50)
            ws.set_row(26, 50)
            ws.set_row(27, 50)
            ws.set_row(28, 50)
            ws.set_row(29, 50)
            ws.set_row(30, 50)
            ws.set_row(31, 50)

            ws.set_column(1, 1, 17)
            ws.set_column(2, 2, 14)
            ws.set_column(3, 3, 10)
            ws.set_column(4, 4, 12)
            ws.set_column(5, 5, 5)
            ws.set_column(6, 6, 17)
            ws.set_column(7, 7, 14)
            ws.set_column(8, 8, 10)
            ws.set_column(9, 9, 12)
            ws.set_column(10, 10, 10)
            ws.set_column(11, 11, 7)
            ws.set_column(12, 12, 7)
            ws.set_column(13, 13, 10)

            formatoceldacab = workbook.add_format(
                {'align': 'center', 'bold': 1, 'border': 1, 'text_wrap': True, 'fg_color': '#A6A6A6', 'font_color': 'black',
                 'font_size': 6, 'font_name': 'Times New Roman', 'valign': 'vcenter'})

            formatoceldacab4 = workbook.add_format(
                {'align': 'center', 'bold': 1, 'text_wrap': True, 'font_color': 'black', 'font_size': 11,
                 'font_name': 'Times New Roman', 'valign': 'vcenter'})

            formatoceldacab5 = workbook.add_format(
                {'align': 'right', 'bold': 1, 'text_wrap': True, 'font_color': 'black', 'font_size': 11,
                 'font_name': 'Times New Roman', 'valign': 'vcenter'})

            formatoceldacab6 = workbook.add_format(
                {'align': 'center', 'bold': 1, 'border': 2, 'text_wrap': True, 'font_color': 'black', 'font_size': 11,
                 'font_name': 'Times New Roman', 'valign': 'vcenter'})

            formatoceldacab7 = workbook.add_format(
                {'align': 'left', 'bold': 1, 'text_wrap': True, 'font_color': 'black', 'font_size': 11,
                 'font_name': 'Times New Roman', 'valign': 'vcenter'})

            formatoceldacab8 = workbook.add_format(
                {'align': 'left', 'text_wrap': True, 'font_color': 'black', 'font_size': 11, 'font_name': 'Times New Roman',
                 'valign': 'vcenter'})

            formatoceldacab9 = workbook.add_format(
                {'align': 'left', 'bold': 1, 'text_wrap': True, 'font_color': 'black', 'font_size': 10,
                 'font_name': 'Times New Roman', 'valign': 'vcenter'})

            formatoceldacab10 = workbook.add_format(
                {'align': 'left', 'text_wrap': True, 'font_color': 'black', 'font_size': 10, 'font_name': 'Times New Roman',
                 'valign': 'vcenter'})

            formatoceldaleft = workbook.add_format(
                {'text_wrap': True, 'align': 'center', 'valign': 'vcenter', 'border': 1, 'font_size': 6,
                 'font_name': 'Times New Roman'})

            formatoceldaleft3 = workbook.add_format(
                {'text_wrap': True, 'align': 'left', 'valign': 'vcenter', 'border': 1, 'font_size': 6,
                 'font_name': 'Times New Roman'})

            formatoceldaleft2 = workbook.add_format(
                {'text_wrap': True, 'bold': 1, 'align': 'center', 'valign': 'vcenter', 'border': 1, 'font_size': 6,
                 'font_name': 'Times New Roman', 'fg_color': '#A6A6A6'})

            ws.insert_image('A1', ruta, {'x_scale': 25 / 100, 'y_scale': 25 / 100})

            ws.merge_range('A5:N5', 'UNIVERSIDAD ESTATAL DE MILAGRO', formatoceldacab4)
            ws.merge_range('A6:N6', 'VICERRECTORADO DE INVESTIGACIÓN Y POSGRADO', formatoceldacab4)
            ws.merge_range('A7:N7', 'DIRECCIÓN DE POSGRADO', formatoceldacab4)
            ws.merge_range('A8:N8', 'RECONOCIMIENTO U HOMOLOGACIÓN DE ESTUDIOS', formatoceldacab4)
            ws.merge_range('A9:N9', 'FICHA COMPARATIVA INTERNA', formatoceldacab4)

            ws.merge_range('K10:M10', f'CÓDIGO', formatoceldacab5)
            ws.write('N10', eSolicitud.id, formatoceldacab6)

            ws.merge_range('A12:C12', f'NOMBRE DEL ESTUDIANTE: ', formatoceldacab7)
            ws.merge_range('D12:N12', f'{eSolicitud.perfil.persona}', formatoceldacab8)
            ws.merge_range('A13:B13', f'CÉDULA: ', formatoceldacab7)
            ws.merge_range('C13:N13', f'{eSolicitud.perfil.persona.cedula}', formatoceldacab8)
            ws.merge_range('A14:F14', f'PROGRAMA DE MAESTRÍA/UNIVERSIDAD DE PROCEDENCIA: ', formatoceldacab7)
            ws.merge_range('G14:N14', f'{nombre_carrera_pos(eSolicitud.carrera_homologada)}/ UNEMI', formatoceldacab8)
            ws.merge_range('A15:D15', f'PLAN DE ESTUDIO DE PROCEDENCIA: ', formatoceldacab7)
            ws.merge_range('E15:N15', f'{nombre_carrera_pos(eSolicitud.carrera_homologada)}', formatoceldacab8)
            ws.merge_range('A16:D16', f'PLAN DE ESTUDIO A HOMOLOGAR: ', formatoceldacab7)
            ws.merge_range('E16:N16', f'{nombre_carrera_pos(eSolicitud.perfil.inscripcion.carrera)}', formatoceldacab8)
            ws.merge_range('A17:B17', f'MODALIDAD: ', formatoceldacab7)
            ws.merge_range('C17:N17', f'{eSolicitud.perfil.inscripcion.carrera.get_modalidad_display()}', formatoceldacab8)

            ws.merge_range('H19:N19', f'FECHA DE RECEPCIÓN: {eSolicitud.fecha_recepcion()}', formatoceldacab7)

            ws.merge_range('A21:A22', 'No.', formatoceldacab)
            ws.merge_range('B21:E21', f'{nombre_carrera_pos(eSolicitud.carrera_homologada)}', formatoceldacab)
            ws.write('B22', 'ASIGNATURAS', formatoceldacab)
            ws.write('C22', 'CALIFICACIÓN', formatoceldacab)
            ws.write('D22', 'HORAS', formatoceldacab)
            ws.write('E22', 'CRÉDITOS', formatoceldacab)
            ws.merge_range('F21:F22', 'No.', formatoceldacab)
            ws.merge_range('G21:J21', f'{nombre_carrera_pos(eSolicitud.perfil.inscripcion.carrera)}', formatoceldacab)
            ws.write('G22', 'ASIGNATURAS', formatoceldacab)
            ws.write('H22', 'CALIFICACIÓN', formatoceldacab)
            ws.write('I22', 'HORAS', formatoceldacab)
            ws.write('J22', 'CRÉDITOS', formatoceldacab)
            ws.merge_range('K21:K22', '% COMPARATIVO DE CONTENIDOS (SIMILITUD)', formatoceldacab)
            ws.merge_range('L21:M21', '% SE ACEPTA ASIGNATURA', formatoceldacab)
            ws.write('L22', 'SI', formatoceldacab)
            ws.write('M22', 'NO', formatoceldacab)
            ws.merge_range('N21:N22', '% ABREVIACIÓN HOM', formatoceldacab)

            filas_recorridas = 23
            cont = 1

            eTotalasignaturaspa = SolicitudAsignatura.objects.filter(status=True, solicitud=eSolicitud).distinct().count()
            eTotalasignaturasap = SolicitudAsignatura.objects.filter(status=True, solicitud=eSolicitud,
                                                                     estado=2).distinct().count()

            eTotalhoraspa = null_to_decimal(SolicitudAsignatura.objects.filter(status=True, solicitud=eSolicitud).distinct().aggregate(horas=Sum('asignaturamalla__horas'))['horas'], 0)
            eTotalhorasap = null_to_decimal(SolicitudAsignatura.objects.filter(status=True, solicitud=eSolicitud, estado=2).distinct().aggregate(horas=Sum('horas'))['horas'], 0)

            eTotalcreditospa = null_to_decimal(SolicitudAsignatura.objects.filter(status=True, solicitud=eSolicitud).distinct().aggregate(creditos=Sum('asignaturamalla__creditos'))['creditos'], 0)
            eTotalcreditosap = null_to_decimal(SolicitudAsignatura.objects.filter(status=True, solicitud=eSolicitud, estado=2).distinct().aggregate(creditos=Sum('creditos'))['creditos'], 0)

            for eRecord in eSolicitud.ficha_homologacion():
                ws.write('A%s' % filas_recorridas, str(cont), formatoceldaleft2)
                ws.write('B%s' % filas_recorridas, str(eRecord['asignatura']), formatoceldaleft3)
                ws.write('C%s' % filas_recorridas, str(eRecord['nota']), formatoceldaleft)
                ws.write('D%s' % filas_recorridas, str(eRecord['horas']), formatoceldaleft)
                ws.write('E%s' % filas_recorridas, str(eRecord['creditos']), formatoceldaleft)
                ws.write('F%s' % filas_recorridas, str(cont), formatoceldaleft2)
                ws.write('G%s' % filas_recorridas, str(eRecord['asignatura2']), formatoceldaleft3)
                ws.write('H%s' % filas_recorridas, str(eRecord['nota2']), formatoceldaleft)
                ws.write('I%s' % filas_recorridas, str(eRecord['horas2']), formatoceldaleft)
                ws.write('J%s' % filas_recorridas, str(eRecord['creditos2']), formatoceldaleft)
                ws.write('K%s' % filas_recorridas, str(eRecord['porcentaje']) + '%', formatoceldaleft)
                ws.write('L%s' % filas_recorridas, str('X' if eRecord['porcentaje'] == 100 else ''), formatoceldaleft)
                ws.write('M%s' % filas_recorridas, str('X' if eRecord['porcentaje'] == 0 else ''), formatoceldaleft)
                ws.write('N%s' % filas_recorridas, str('HOM'), formatoceldaleft)

                filas_recorridas += 1
                cont += 1

            ws.merge_range(f'B{filas_recorridas + 1}:E{filas_recorridas + 1}', 'No. DE ASIGNATURAS POR APROBAR: ', formatoceldacab9)
            ws.write(f'F{filas_recorridas + 1}', eTotalasignaturaspa, formatoceldacab10)
            ws.merge_range(f'B{filas_recorridas + 2}:E{filas_recorridas + 2}', 'TOTAL HORAS POR HOMOLOGAR: ', formatoceldacab9)
            ws.write(f'F{filas_recorridas + 2}', eTotalhoraspa, formatoceldacab10)
            ws.merge_range(f'B{filas_recorridas + 3}:E{filas_recorridas + 3}', 'TOTAL CRÉDITOS POR HOMOLOGAR: ', formatoceldacab9)
            ws.write(f'F{filas_recorridas + 3}', eTotalcreditospa, formatoceldacab10)

            ws.merge_range(f'G{filas_recorridas + 1}:J{filas_recorridas + 1}', 'No. DE ASIGNATURAS APROBADAS: ', formatoceldacab9)
            ws.write(f'K{filas_recorridas + 1}', eTotalasignaturasap, formatoceldacab10)
            ws.merge_range(f'G{filas_recorridas + 2}:J{filas_recorridas + 2}', 'TOTAL HORAS HOMOLOGADAS: ', formatoceldacab9)
            ws.write(f'K{filas_recorridas + 2}', eTotalhorasap, formatoceldacab10)
            ws.merge_range(f'G{filas_recorridas + 3}:J{filas_recorridas + 3}', 'TOTAL CRÉDITOS HOMOLOGADOS: ', formatoceldacab9)
            ws.write(f'K{filas_recorridas + 3}', eTotalcreditosap, formatoceldacab10)

            ws.merge_range(f'A{filas_recorridas + 4}:B{filas_recorridas + 4}', 'OBSERVACIÓN: ', formatoceldacab9)

            ws.merge_range(f'H{filas_recorridas + 11}:N{filas_recorridas + 11}', f'FECHA DE REVISIÓN: {eSolicitud.fecha_revision()}', formatoceldacab9)

            ws.merge_range(f'A{filas_recorridas + 13}:B{filas_recorridas + 13}', 'REALIZADA POR: ', formatoceldacab9)
            ws.merge_range(f'C{filas_recorridas + 13}:F{filas_recorridas + 13}', eSolicitud.inscripcioncohorte.cohortes.coordinador.__str__(), formatoceldacab10)
            ws.merge_range(f'A{filas_recorridas + 14}:B{filas_recorridas + 14}', 'APROBADA POR: ', formatoceldacab9)
            ws.merge_range(f'C{filas_recorridas + 14}:F{filas_recorridas + 14}', eSolicitud.director_escuela(), formatoceldacab10)

            workbook.close()
            ruta = "{}reportes/fichas_homologacion/{}".format(MEDIA_URL, nombre_archivo)
            eSolicitud.ficha = ruta
            eSolicitud.save()
        except Exception as ex:
            pass

    def tiene_informe(self):
        return InformeHomologacionPosgrado.objects.filter(status=True, solicitud=self).order_by('id').first()

    def tiene_informe_firmado(self):
        estado = False
        if self.tiene_informe():
            if IntegrantesInformeHomologacion.objects.filter(status=True, informe=self.tiene_informe(), firmado=True).exists():
                estado = True
        return estado

    def primer_historial(self):
        return HistorialSolicitud.objects.filter(status=True, solicitud=self).order_by('id').first()

    def director_titu(self):
        dir = None
        if IntegrantesCronogramaTituEx.objects.filter(status=True, solicitud=self, tipo=1).exists():
            dir = IntegrantesCronogramaTituEx.objects.filter(status=True, solicitud=self, tipo=1).first()
        return dir

    def coordinador_titu(self):
        cor = None
        if IntegrantesCronogramaTituEx.objects.filter(status=True, solicitud=self, tipo=2).exists():
            cor = IntegrantesCronogramaTituEx.objects.filter(status=True, solicitud=self, tipo=2).first()
        return cor

    class Meta:
        verbose_name = u"Solicitud"
        verbose_name_plural = u"Solicitudes"
        ordering = ['perfil', 'fecha', 'hora']
        indexes = [
            models.Index(fields=["origen_content_type", "origen_object_id"]),
            models.Index(fields=["destino_content_type", "destino_object_id"]),
        ]
        unique_together = ('codigo',)


ESTADO_HIST_COLOR = (
    (1, 'color: #3a87ad!important; font-weight: bold; font-size:12px'),
    (2, 'color: #FE9900!important; font-weight: bold; font-size:12px'),
    (3, 'color: #198754!important; font-weight: bold; font-size:12px'),
)

class HistorialSolicitud(ModeloBase):
    solicitud = models.ForeignKey(Solicitud, on_delete=models.CASCADE, related_name='+', verbose_name=u'Solicitud')
    observacion = models.TextField(default='', verbose_name=u'Observación')
    archivo = models.FileField(upload_to=solicitud_user_directory_path, blank=True, null=True, verbose_name=u'Archivo')
    fecha = models.DateField(blank=True, null=True, verbose_name=u"Fecha")
    hora = models.TimeField(blank=True, null=True, verbose_name=u"Hora")
    estado = models.IntegerField(default=1, choices=ESTADO_SOLICITUD, verbose_name=u'Estado')
    responsable = models.ForeignKey(Persona, on_delete=models.CASCADE, related_name='+', blank=True, null=True, verbose_name=u'Responsable')
    destino_content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE, related_name='+', verbose_name=u'Modelo de destino', blank=True, null=True)
    destino_object_id = models.PositiveIntegerField(blank=True, null=True, verbose_name=u'ID de destino')
    destino_content_object = GenericForeignKey('destino_content_type', 'destino_object_id')
    atendido = models.BooleanField(default=False, verbose_name=u'Verfica si la solicitud de certificado física esta siendo atendida')
    urldrive = models.CharField(default='', max_length=500, null=True, blank=True, verbose_name=u"Url Drive")
    tipodocumento = models.IntegerField(default=1, choices=TIPO_DOCUMENTO, verbose_name=u'Tipo de documento')

    def __str__(self):
        return f"{self.solicitud.__str__()} - {self.get_estado_display()})"

    def color_estado_display(self):
        return dict(ESTADO_SOLICITUD_COLOR)[self.estado]

    def save(self, *args, **kwargs):
        super(HistorialSolicitud, self).save(*args, **kwargs)

    class Meta:
        verbose_name = u"Historial de Solicitud"
        verbose_name_plural = u"Historial de Solicitudes"
        ordering = ['solicitud', 'fecha', 'hora']
        indexes = [
            models.Index(fields=["destino_content_type", "destino_object_id"]),
        ]

ESTADO_ASIGNATURA = (
    (1, "En revisión"),
    (2, "Aplica"),
    (3, "No aplica"),
    (4, "No seleccionada"),
)

ESTADO_ASIGNATURA_COLOR = (
    (1, 'color: #FE9900!important; font-weight: bold; font-size:12px'),
    (2, 'color: #198754!important; font-weight: bold; font-size:12px'),
    (3, 'color: #dc3545!important; font-weight: bold; font-size:12px'),
    (4, 'color: #dc3545!important; font-weight: bold; font-size:12px'),
)

class SolicitudAsignatura(ModeloBase):
    solicitud = models.ForeignKey(Solicitud, on_delete=models.CASCADE, related_name='+', verbose_name=u'Solicitud')
    asignaturamalla = models.ForeignKey('sga.AsignaturaMalla', blank=True, null=True, verbose_name=u'Asignatura malla', on_delete=models.CASCADE)
    estado = models.IntegerField(default=1, choices=ESTADO_ASIGNATURA, blank=True, null=True, verbose_name=u"Tipo origen")
    nota = models.FloatField(default=0, blank=True, null=True, verbose_name=u'Nota de record')
    horas = models.FloatField(default=0, blank=True, null=True, verbose_name=u'Horas')
    creditos = models.FloatField(default=0, blank=True, null=True, verbose_name=u'Creditos')
    record = models.ForeignKey('sga.RecordAcademico', blank=True, null=True, verbose_name=u'Record compatible con asigntura seleccionada', on_delete=models.CASCADE)

    def __str__(self):
        return f"{self.solicitud.inscripcioncohorte} - {self.asignaturamalla} - {self.get_estado_display()})"

    def color_estado_display(self):
        return dict(ESTADO_ASIGNATURA_COLOR)[self.estado]

    class Meta:
        verbose_name = u"Detalle de asignatura homologadas"
        verbose_name_plural = u"Detalles de asignaturas homologadass"
        ordering = ['id']

TIPO_FORMATO_CERTIFICADO = (
    (1, "Fisico"),
    (2, "Personalizado"),
    (3, "Interno"),
    (4, "Externo"),
)

class InformeHomologacionPosgrado(ModeloBase):
    class EstadoRevision(models.IntegerChoices):
        PENDIENTE = 1, "PENDIENTE"
        PORLEGALIZAR = 2, "POR LEGALIZAR"
        LEGALIZADO = 3, "LEGALIZADO"

    codigo = models.CharField(default='', max_length=100, blank=True, null=True, verbose_name=u'Código', db_index=True)
    fechaemision = models.DateField(verbose_name=u"Fecha Emisión del informe")
    para = models.ForeignKey('sga.Persona', blank=True, null=True, verbose_name=u'Para', related_name='+', on_delete=models.CASCADE)
    de = models.ForeignKey('sga.Persona', blank=True, null=True, verbose_name=u'De', on_delete=models.CASCADE)
    solicitud = models.ForeignKey(Solicitud, verbose_name="Solicitante", on_delete=models.CASCADE)
    estadorevision = models.IntegerField(choices=EstadoRevision.choices, default=EstadoRevision.PENDIENTE, blank=True, null=True,verbose_name=u"Estado Revisión del informe")

    def __str__(self):
        return f"{self.fechaemision} - {self.solicitud}"

    def get_integrantes_firman(self):
        return self.integrantesinformehomologacion_set.filter(status=True).order_by("orden")

    def get_cantidad_de_integrantes_que_han_firmado(self):
        return self.integrantesinformehomologacion_set.filter(status=True, firmado=True).count()

    def firmo_analista(self):
        return True if self.integrantesinformehomologacion_set.filter(status=True, firmado=True, orden=2) else False

    def analista(self):
        return self.integrantesinformehomologacion_set.filter(status=True, orden=2).first()

    def firmo_coordinador(self):
        return True if self.integrantesinformehomologacion_set.filter(status=True, firmado=True, orden=1) else False

    def coordinador(self):
        return self.integrantesinformehomologacion_set.filter(status=True, orden=1).first()

    def firmo_director(self):
        return True if self.integrantesinformehomologacion_set.filter(status=True, firmado=True, orden=3) else False

    def director(self):
        return self.integrantesinformehomologacion_set.filter(status=True, orden=1).first()

    def ultima_historial(self):
        return HistorialInformeHomologacion.objects.filter(status=True, informe=self, estadorevision=1).order_by('-id').first()

    def ultima_historial_firma(self, orden):
        fecha = 'NO GENERADO'
        integrante = IntegrantesInformeHomologacion.objects.get(status=True, informe=self, orden=orden)

        if HistorialInformeHomologacion.objects.filter(status=True, informe=self, persona=integrante.persona).exists():
            fecha = HistorialInformeHomologacion.objects.filter(status=True, informe=self, persona=integrante.persona).order_by('-id').first().fecha
        return fecha


    def archivo_actual(self):
        try:
            return HistorialInformeHomologacion.objects.filter(status=True, informe=self).order_by('-id').first().archivo.url
        except Exception as ex:
            pass

    def archivo_actual_2(self):
        try:
            return HistorialInformeHomologacion.objects.filter(status=True, informe=self).order_by('-id').first().archivo
        except Exception as ex:
            pass

    def get_integrantes_notifican(self):
        return self.integrantesinformehomologacion_set.filter(status=True).exclude(orden=3).order_by("orden")

    class Meta:
        verbose_name = u"Informe de homologacion"
        verbose_name_plural = u"Informes de homologacion"
        ordering = ['-id']

class HistorialInformeHomologacion(ModeloBase):
    class EstadoRevision(models.IntegerChoices):
        PENDIENTE = 1, "PENDIENTE"
        PORLEGALIZAR = 2, "POR LEGALIZAR"
        LEGALIZADO = 3, "LEGALIZADO"

    informe = models.ForeignKey(InformeHomologacionPosgrado, verbose_name="Informe homologación", on_delete=models.CASCADE)
    persona = models.ForeignKey('sga.Persona', blank=True, null=True, verbose_name=u'Responsable', on_delete=models.CASCADE)
    fecha = models.DateField(blank=True, null=True, verbose_name=u"Fecha")
    hora = models.TimeField(blank=True, null=True, verbose_name=u"Hora")
    observacion = models.TextField(verbose_name=u"Observación", blank=True, null=True, default='')
    estadorevision = models.IntegerField(choices=EstadoRevision.choices, default=EstadoRevision.PENDIENTE, blank=True, null=True,verbose_name=u"Estado Revisión del informe")
    archivo = models.FileField(upload_to='InformeHomologacionHistorial/', blank=True, null=True,verbose_name=u"Informe firmado",max_length=600)

    def __str__(self):
        return f"{self.informe}"

    def color_estado_display(self):
        return dict(ESTADO_SOLICITUD_COLOR)[self.estadorevision]

    class Meta:
        verbose_name = u"Historial de Informe Ho"
        verbose_name_plural = u"Historiales de Informes de Ho"
        ordering = ['-id']

class IntegrantesInformeHomologacion(ModeloBase):
    informe = models.ForeignKey(InformeHomologacionPosgrado, verbose_name="Informe homologación", on_delete=models.CASCADE)
    orden = models.PositiveIntegerField(verbose_name=u'Orden de firma')
    persona = models.ForeignKey('sga.Persona', blank=True, null=True, verbose_name=u'Responsable', on_delete=models.CASCADE)
    firmado = models.BooleanField(verbose_name=u"¿Firmó el informe?", default=False)
    cargo = models.CharField(default='', max_length=200, blank=True, null=True, verbose_name=u'Cargo', db_index=True)
    responsabilidad = models.CharField(default='', max_length=200, blank=True, null=True, verbose_name=u'Responsabilidad firma', db_index=True)

    def __str__(self):
        return f"{self.persona} - {self.informe.solicitud}"

    class Meta:
        verbose_name = u"Integrante de Informe de Ho"
        verbose_name_plural = u"Integrantes de Informes de Ho"
        ordering = ['-id']

class SecuenciaInformeHomologacion(ModeloBase):
    anioejercicio = models.ForeignKey('sagest.AnioEjercicio', verbose_name=u'Anio Ejercicio', on_delete=models.CASCADE)
    secuencia = models.IntegerField(default=0, verbose_name=u'Secuencia Informe')

    class Meta:
        verbose_name = u"Secuencia de Informe"
        verbose_name_plural = u"Secuencias de Informe"

    def save(self, *args, **kwargs):
        super(SecuenciaInformeHomologacion, self).save(*args, **kwargs)

class FormatoCertificado(ModeloBase):
    certificacion = models.CharField(default='', max_length=350, verbose_name=u"Certificación")
    tipo_origen = models.IntegerField(default=1, choices=TIPO_FORMATO_CERTIFICADO, blank=True, null=True, verbose_name=u"Tipo origen")
    formato = models.FileField(upload_to='certis/formatos', max_length=500, blank=True, null=True, verbose_name=u'Formato de certificados')
    roles = models.TextField(default='', max_length=50, blank=True, null=True, verbose_name=u'Roles')

    def __str__(self):
        return f"{self.certificacion} - {self.get_tipo_origen_display()})"

    def download_evidencia(self):
        return self.formato.url

    def subido_por(self):
        from sga.models import Persona
        return Persona.objects.get(usuario=self.usuario_creacion.id)

    def displays_rol(self):
        cadena = ''
        if self.roles:
            c = 1
            for rol in ROLES_TIPO_CATEGORIA:
                if rol[0] in self.roles:
                    if c == len(self.roles.split(',')):
                        cadena += str(rol[1])
                        c += 1
                    else:
                        cadena += str(rol[1]) + ' - '
                        c += 1
        return cadena

    def save(self, *args, **kwargs):
        super(FormatoCertificado, self).save(*args, **kwargs)

    class Meta:
        verbose_name = u"Formato de certificados"
        verbose_name_plural = u"Formatos de certificados"
        ordering = ['id']

class AsignaturaCompatibleHomologacion(ModeloBase):
    asignaturach = models.ForeignKey('sga.AsignaturaMalla', blank=True, null=True, verbose_name=u'Asignatura de malla a homologar', on_delete=models.CASCADE)
    asignaturama = models.ForeignKey('sga.AsignaturaMalla', related_name='+', blank=True, null=True, verbose_name=u'Asignatura de malla homologada', on_delete=models.CASCADE)

    def __str__(self):
        return f"{self.asignaturach} - {self.asignaturama}"

    class Meta:
        verbose_name = u"Asignatura compatible homologación"
        verbose_name_plural = u"Asignaturas compatibles homologación"
        ordering = ['id']

class IntegrantesCronogramaTituEx(ModeloBase):
    class TipoAutoridad(models.IntegerChoices):
        PORDEFINIR = 0, "Por Definir"
        DIRECTOR = 1, "Director"
        COORDINADOR = 2, "Coordinador"

    solicitud = models.ForeignKey(Solicitud, verbose_name="Solicitante", on_delete=models.CASCADE)
    tipo = models.IntegerField(choices=TipoAutoridad.choices, default=TipoAutoridad.PORDEFINIR, blank=True, null=True,verbose_name=u"Tipo")
    administrativo = models.ForeignKey('sga.Administrativo', blank=True, null=True, verbose_name=u'Responsable', on_delete=models.CASCADE)
    cargo = models.CharField(default='', max_length=200, blank=True, null=True, verbose_name=u'Cargo', db_index=True)
    responsabilidad = models.CharField(default='', max_length=200, blank=True, null=True, verbose_name=u'Responsabilidad firma', db_index=True)

    def __str__(self):
        return f"{self.solicitud} - {self.administrativo.persona}"

    class Meta:
        verbose_name = u"Integrante de Cronograma de Titulación"
        verbose_name_plural = u"Integrantes de Cronograma de Titulación"
        ordering = ['-id']
