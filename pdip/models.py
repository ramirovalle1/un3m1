import calendar
import unicodedata
import math
import xlsxwriter
from django.db import models

from pdip.process_background import notificar_persona_a_fimar_acta_pago, actualizar_acta_pago_posgrado, \
    notificar_subir_factura_profesionales, \
    actualizar_todas_las_solicitudes_orden_and_opcional_de_todos_los_requisitos_de_pago, \
    notificar_contrato_subido_para_registrar_analista_validador
from sga.funciones import ModeloBase, remover_caracteres_especiales_unicode, log, notificacion,remover_caracteres_tildes_unicode
from sagest.models import *
from django.utils import timezone
from django.db.models.aggregates import Count, Max
import calendar as c

from sga.funcionesxhtml2pdf import convert_html_to_pdf
from sga.models import DiasNoLaborable, DIAS_CHOICES, Turno, Paralelo, Nivel


class Perms(models.Model):
    class Meta:
        permissions = (
            ("puede_editar_contrato_posgrado", "Puede editar contrato de posgrado"),
            ("puede_visualizar_actas_de_pagos_posgrado", "Puede visualizar actas de pago posgrado"),
            ("puede_ver_todas_las_solicitudes_de_pago_posgrado", "Puede ver todas las solicitudes de pago posgrado"),
            ("puede_gestionar_todas_las_actas_de_pago_posgrado", "Puede gestionar todas las actas de pago posgrado"),
            ("puede_ver_seguimiento_de_pago_epunemi", "Puede ver seguimiento de pagos epunemi posgrado"),
            ("puede_adicionar_pago_solicitud_pago_realizado_epunemi", "Puede adicionar pago realizado solicitud pago por epunemi posgrado"),
            ("puede_notificar_subir_factura_solicitud_pago", "Puede notificar subir factura de solicitudes de pago posgrado"),
            ("puede_aprobar_factura_epunemi", "Puede aprobar factura de solicitudes de pago posgrado"),
            ("puede_rechazar_factura_epunemi", "Puede rechazar factura de solicitudes de pago posgrado"),
            ("puede_eliminar_solicitudes_pago_posgrado", "Puede eliminar solicitudes de pago posgrado"),
        )


ESTADO_CONTRATO = (
    (0, u'PENDIENTE'),
    (1, u'APROBADO'),
    (2, u'EN PROCESO'),
    (3, u'SUSCRIBIR GERENTE'),
    (4, u'SUSCRIBIR BENEFICIARIO'),
    (5, u'FINALIZADO'),
    (6, u'RECHAZADO'),
    (7, u'ANULADO'),

)

PERFIL_CONTRATO = (
    (0, u'TUTOR'),
    (1, u'DOCENTE'),
    (2, u'COORDINADOR'),
)

TIPO_CAMPO = (
    (1, u'TEXTO'),
    (2, u'NUMERO'),
    (3, u'FECHA'),
    (4, u'HORA'),
    (5, u'COMBO'),
    (6, u'FUNCION')
)

ESTADO_CERTIFICACION = (
    (0, u'PENDIENTE'),
    (1, u'ELABORADO'),
    (2, u'APROBADO'),
    (3, u'RECHAZADO'),
)
TIPO_INFORME = (
    (0, u'MEMORANDO'),
    (1, u'ACTIVIDAD Y JORNADA'),
    (2, u'ACTA CONTROL'),
    (3, u'INFORME ACTIVIDAD'),
)


class ActividadesPerfil(ModeloBase):
    descripcion = models.TextField(default='', blank=True, null=True, verbose_name=u"Actividades Registrada")

    def __str__(self):
        return u'%s ' % self.descripcion

    def en_uso(self):
        return self.perfilpuestodip_set.exists()

    def bitcaroaactividad_uso(self):
        return self.bitacoraactividaddiaria_set.filter(status=True).exists()

    def save(self, *args, **kwargs):
        self.descripcion = self.descripcion.upper()
        super(ActividadesPerfil, self).save(*args, **kwargs)

    class Meta:
        verbose_name = u'Actividad del Puesto'
        verbose_name_plural = u'Actividades del Puesto'
        ordering = ('descripcion',)


class PerfilPuestoDip(ModeloBase):
    nombre = models.CharField(max_length=1000, default='', verbose_name=u'Nombre')
    actividades  = models.ManyToManyField(ActividadesPerfil)
    def __str__(self):
        return u'%s' % (self.nombre)

    def save(self, *args, **kwargs):
        self.nombre = self.nombre.upper()
        super(PerfilPuestoDip, self).save(*args, **kwargs)
    def actividadesperfil(self):
        return self.actividadescontratoperfil_set.filter(status=True).all().order_by('actividad_id').distinct('actividad_id')
    def en_uso(self):
        return self.plantillacontratodip_set.exists()

    class Meta:
        verbose_name = u"Perfil Puesto"
        verbose_name_plural = u"Perfiles de Puesto"


class CertificacionPresupuestariaDip(ModeloBase):
    valor = models.DecimalField(max_digits=30, decimal_places=2, default=0,
                                verbose_name=u"Valor total de certificación")
    fecha = models.DateField(blank=True, null=True, verbose_name=u'Fecha de certificación')
    descripcion = models.CharField(default='', max_length=1000, verbose_name=u"Descripcion")
    partida = models.CharField(default='', max_length=300, verbose_name=u"partida")
    archivo = models.FileField(upload_to='certificacionepunemi/%Y', verbose_name=u'Archivo')
    estado = models.IntegerField(default=0, choices=ESTADO_CERTIFICACION, verbose_name=u'Estado de Contrato')
    codigo = models.CharField(null=True, blank=True, max_length=25, verbose_name=u'Codigo certificacion presupuestaria')
    saldo = models.DecimalField(max_digits=30, decimal_places=2, default=0, verbose_name=u"Saldo total de certificación")

    def __str__(self):
        return u"%s - %s - %s (%s)" % (self.descripcion, self.valor,self.codigo, self.fecha)

    def esta_en_contrato(self):
        return self.contratodip_set.filter(status=True).exists()

    def detalles_certificacion(self):
        return self.detallecertificacionpresupuestariadip_set.filter(status=True)

    def tiene_detalles(self):
        return self.detalles_certificacion().exists()

    class Meta:
        verbose_name = u'Certificación'
        verbose_name_plural = u'Certificaciones'
        ordering = ('descripcion',)

    def get_str_codigo_fecha(self):
        return f"{self.codigo} - {self.fecha}"

    def save(self, *args, **kwargs):
        self.descripcion = self.descripcion.upper()
        self.codigo = self.codigo.upper()
        super(CertificacionPresupuestariaDip, self).save(*args, **kwargs)


class CampoContratoDip(ModeloBase):
    descripcion = models.CharField(default='', max_length=300, verbose_name=u"Descripcion")
    tipo = models.IntegerField(choices=TIPO_CAMPO, default=1, verbose_name=u"Tipo Campo")
    script = models.TextField(default='', verbose_name=u"Script")
    identificador = models.CharField(default='', max_length=300, verbose_name=u"Identificador")

    def __str__(self):
        return u"%s" % self.descripcion

    class Meta:
        verbose_name = u'Campo Contrato'
        verbose_name_plural = u'Campos Contratos'
        ordering = ('descripcion',)
        # unique_together = ('descripcion',)

    def en_uso(self):
        return self.campoplantillacontratodip_set.exists()

    def identifica(self):
        return '${CAMPO%s}'% self.identificador

    def save(self, *args, **kwargs):
        self.descripcion = self.descripcion.upper()
        self.identificador = self.identificador.upper()
        super(CampoContratoDip, self).save(*args, **kwargs)


class PlantillaContratoDip(ModeloBase):
    anio = models.IntegerField(default=0, verbose_name=u"Año")
    descripcion = models.CharField(default='', max_length=300, verbose_name=u"Descripcion")
    archivo = models.FileField(upload_to='contratoepunemi/plantilla/%Y', verbose_name=u'Archivo')
    vigente = models.BooleanField(default=False, verbose_name=u"Vigente")
    perfil = models.ForeignKey(PerfilPuestoDip,null=True, blank=True,on_delete=models.CASCADE, verbose_name=u"Perfil de contrato")

    def __str__(self):
        return u"%s" % self.descripcion

    class Meta:
        verbose_name = u'Tipo Contrato'
        verbose_name_plural = u'Tipos Contratos'
        ordering = ('anio', 'descripcion',)

    def download_link(self):
        return self.archivo.url

    def en_uso(self):
        return self.contratodip_set.filter(status=True).exists()

    def cantidad_campos(self):
        return self.campoplantillacontratodip_set.count()

    def color_configurado(self):
        label = 'label label-warning'
        if self.campoplantillacontratodip_set.exists():
            label = 'label label-succes'
        return label

    def configurado(self):
        texto = 'FALTA CONFIGURAR'
        if self.campoplantillacontratodip_set.exists():
            texto = 'CONFIGURADO'
        return texto

    def save(self, *args, **kwargs):
        self.descripcion = self.descripcion.upper()
        super(PlantillaContratoDip, self).save(*args, **kwargs)


class CampoPlantillaContratoDip(ModeloBase):
    contrato = models.ForeignKey(PlantillaContratoDip, verbose_name=u"Contrato",on_delete=models.CASCADE)
    campos = models.ForeignKey(CampoContratoDip, verbose_name=u"Campos",on_delete=models.CASCADE)

    def __str__(self):
        return u"%s - %s" % (self.contrato, self.campos)

    def combo(self):
        return self.campos.script.split(';')

    def funcion(self):
        lista = []
        resultquery = eval(self.campos.script)
        for listacampos in resultquery:
            lista.append(listacampos)
        return lista

    def extraer_datos(self, contratodip):
        genero = contratodip.persona.sexo.id
        campos = ContratoDipDetalle.objects.filter(contratodip=contratodip, campo=self)
        if campos:
            campo = campos[0].valor
            if campo != '':
                return campos[0].valor
        if self.campos.tipo == 5:
            datos = self.campos.script.split(";")
            if datos.__len__() == 2:
                return datos[genero - 1]
            else:
                return ''
        else:
            contrato = contratodip
            campo = ContratoDipDetalle.objects.filter(contratodip=contrato, campo=self).order_by('-id')
            if campo:
                return campo[0].valor
            else:
                return ''

    class Meta:
        verbose_name = u'Campo Seleccionado Contrato'
        verbose_name_plural = u'Campos Seleccionados Contratos'
        ordering = ('contrato', 'campos')
        # unique_together = ('contrato', 'campos')


FORMA_PAGO_CONTRATO = (
    (0, u'MENSUAL'),
    (1, u'FIN DE MÓDULO'),
)

class Departamento(ModeloBase):
    nombre = models.CharField(verbose_name=u'Nombre departameno', null=True, blank=True, max_length=300)
    responsable = models.ForeignKey('sga.Persona', related_name='+', blank=True, null=True, verbose_name=u'Responsable', on_delete=models.CASCADE)
    responsable_subrogante = models.ManyToManyField('sga.Persona', related_name='+', verbose_name=u'Responsable Subrogante')

    class Meta:
        verbose_name = u'Departamento posgrado'
        verbose_name_plural = u'Departamentos posgrado'
        ordering = ('-id','nombre')

    def __str__(self):
        return f"{self.nombre} - {self.responsable}"

    def en_uso(self):
        return self.gestion_set.values('id').filter(status=True).exists()


class Gestion(ModeloBase):
    departamento = models.ForeignKey(Departamento, verbose_name=u"Departamento posgrado", on_delete=models.CASCADE)
    gestion = models.CharField(max_length=300, verbose_name=u"Gestión o maestría")
    cargo = models.CharField(max_length=500, verbose_name=u"Cargo")
    responsable = models.ForeignKey('sga.Persona', related_name='+', blank=True, null=True, verbose_name=u'Responsable',on_delete=models.CASCADE)
    responsablesubrogante = models.ForeignKey('sga.Persona', related_name='+', blank=True, null=True,verbose_name=u'Responsable', on_delete=models.CASCADE)

    class Meta:
        verbose_name = u'Gestión posgrado'
        verbose_name_plural = u'Gestiones posgrado'
        ordering = ('-id', 'gestion')

    def __str__(self):
        return f"{self.cargo}-{self.gestion}({self.responsable})"

TIPO_GRUPO = (
    (0, u"-----------"),
    (1, u"ADMINISTRATIVO"),
    (2, u"PROFESOR"),
)
TIPO_REQUISITO = (
    (1, u"CONTRATACIÓN"),
    (2, u"PAGO"),
)
TIPO_PAGO = (
    (0, u"-----------"),
    (1, u"MENSUAL"),
    (2, u"MÓDULAR"),
)

class ContratoDip(ModeloBase):
    codigocontrato = models.CharField(default='', max_length=20, verbose_name=u"Código Contrato")
    plantilla = models.ForeignKey(PlantillaContratoDip,null=True, blank=True, verbose_name=u"Plantilla de Contrato",on_delete=models.CASCADE)
    invitacion = models.ForeignKey('postulaciondip.InscripcionInvitacion', blank=True, null=True, verbose_name=u'Invitación',on_delete=models.CASCADE)
    persona = models.ForeignKey('sga.Persona', blank=True, null=True, verbose_name=u'Persona',on_delete=models.CASCADE)
    descripcion = models.TextField(default='', null=True, blank=True, verbose_name=u'Descripción')
    materia = models.ForeignKey('sga.ProfesorMateria', verbose_name=u'Materia', blank=True, null=True,on_delete=models.CASCADE)
    nummeses = models.IntegerField(default=0, verbose_name=u"Num. Meses",blank=True, null=True)
    rmu = models.DecimalField(max_digits=30, decimal_places=2, default=0, verbose_name=u"RMU")
    estado = models.IntegerField(default=0, choices=ESTADO_CONTRATO, verbose_name=u'Estado de Contrato')
    tipo = models.IntegerField(default=0, choices=PERFIL_CONTRATO, verbose_name=u'Tipo Contrato')
    tipogrupo = models.IntegerField(default=0, choices=TIPO_GRUPO, verbose_name=u'Tipo Grupo')
    tipopago = models.IntegerField(default=0, choices=TIPO_PAGO, verbose_name=u'Tipo Pago')
    fechainicio = models.DateField(blank=True, null=True, verbose_name=u'Fecha inicio del contrato')
    fechafin = models.DateField(blank=True, null=True, verbose_name=u'Fecha fin del contrato')
    archivo = models.FileField(upload_to='contratosepunemi/contrato',blank=True, null=True, max_length=150, verbose_name=u'Archivo')
    certificacion = models.ForeignKey(CertificacionPresupuestariaDip, null=True, blank=True, verbose_name='Certificacion Presupuestaria',on_delete=models.CASCADE)
    iva = models.ForeignKey('sagest.IvaAplicado',null=True, verbose_name=u'IVA',on_delete=models.CASCADE)
    valoriva = models.DecimalField(default=0, max_digits=30, null=True,decimal_places=2, verbose_name=u'Valor IVA')
    valortotal = models.DecimalField(default=0, max_digits=30,null=True, decimal_places=2, verbose_name=u'Valor total')
    seccion = models.ForeignKey('sagest.SeccionDepartamento',on_delete=models.SET_NULL,null=True, blank=True, verbose_name=u"Seccion Departamento")
    gestion = models.ForeignKey(Gestion,on_delete=models.SET_NULL,null=True, blank=True, verbose_name=u"Gestion Departamento")
    cargo = models.ForeignKey(PerfilPuestoDip,on_delete=models.SET_NULL,null=True, blank=True, verbose_name=u"Cargo/Puesto")
    manual = models.BooleanField(verbose_name="Gestion manual",default=False)
    fechafinalizacion = models.DateField(blank=True, null=True, verbose_name=u'Fecha de Finalizacion')
    actividadesextra = models.ManyToManyField(ActividadesPerfil,verbose_name='Actividades Extra')
    carrera = models.ForeignKey("sga.Carrera", blank=True, null=True, verbose_name=u'Carrera', on_delete=models.CASCADE) #Se sustituyó por la tabla ContratoCarrera
    # bitacora = models.BooleanField(default=False,blank=True,null=True, verbose_name=u'Activa bitacora')
    fechaaplazo = models.DateField(blank=True,null=True, verbose_name='Fecha aplazado')
    validadorgp = models.ForeignKey('sga.Persona',related_name='validadorgp', blank=True, null=True, verbose_name=u'Persona',on_delete=models.SET_NULL)

    def save(self, *args, **kwargs):
        if self.descripcion:
            self.descripcion = self.descripcion.upper()
        if self.codigocontrato:
            self.codigocontrato = self.codigocontrato.upper()
        super(ContratoDip, self).save(*args, **kwargs)

    def titulo_contrato(self):
        return '#{} {} ${}'.format(self.pk, self.get_tipo_display(), self.rmu)

    def get_contratos_a_su_cargo(self):
        return ContratoDip.objects.filter(validadorgp = self.persona,fechainicio__lte=datetime.now() , fechafin__gte = datetime.now())

    def color_estado(self):
        estado = 'text-muted'
        if self.estado == 1 or self.estado == 3:
            estado = 'text-success'
        elif self.estado == 2:
            estado = 'text-warning'
        elif self.estado == 5:
            estado = 'text-info'
        elif self.estado >= 6:
            estado = 'text-danger'
        return estado

    def total_dias(self):
        return (self.fechafin-self.fechainicio).days

    def cuotas(self):
        return self.contratodipmetodopago_set.filter(status=True)

    def total_pagado(self):
        return self.contratodipmetodopago_set.filter(status=True, cancelado=True).aggregate(total=Sum('valorcuota')).get('total')

    def total_pendiente(self):
        return self.contratodipmetodopago_set.filter(status=True, cancelado=False).aggregate(total=Sum('valorcuota')).get('total')

    def __str__(self):
        return u'#%s %s - $ %s' % (self.codigocontrato, self.persona, self.valortotal)

    def download_link(self):
        return self.archivo.url

    def secuencia_codigo(self):
        reg = MemoActividadPosgrado.objects.filter(status=True,secuenciamemo__anioejercicio__anioejercicio = datetime.now().year).aggregate(sec=Max('secuencia')+1)

        if reg['sec'] is None:
            secuencia = 1
        else:
            secuencia = reg['sec']
        return secuencia

    def secuencia_informe(self):
        reg = SolicitudPago.objects.values('id').filter(status=True,contrato=self)
        if not reg:
            secuencia = 1
        else:
            secuencia = len(reg)+1
        return secuencia
    def secuencia_inftecnico(self):
        reg = InformeTecnico.objects.filter(status=True,secuenciageneral__anioejercicio__anioejercicio = datetime.now().year).aggregate(sec=Max('secuencia')+1)
        if reg['sec'] is None:
            secuencia = 1
        else:
            secuencia = reg['sec']
        return secuencia
    def secuencia_actapago(self):
        reg = ActaPago.objects.filter(status=True,secuenciageneral__anioejercicio__anioejercicio = datetime.now().year).aggregate(sec=Max('secuencia')+1)
        if reg['sec'] is None:
            secuencia = 1
        else:
            secuencia = reg['sec']
        return secuencia

    def calfindesemana(self, dia, mes, anio):
        try:
            from sagest.models import BitacoraActividadDiaria
            if c.SATURDAY == c.weekday(int(anio), int(mes), int(dia)):
                return 'fin'
            elif c.SUNDAY == c.weekday(int(anio), int(mes), int(dia)):
                return 'fin'
            elif BitacoraActividadDiaria.objects.filter(status=True, fecha__day=int(dia), fecha__month=int(mes), fecha__year=int(anio), persona=self.persona).exists():
                return BitacoraActividadDiaria.objects.filter(status=True, fecha__day=int(dia), fecha__month=int(mes), fecha__year=int(anio), persona=self.persona)
            return None
        except Exception as ex:
            return 0
    def actividadescontrato(self):
        return self.actividadescontratoperfil_set.filter(status=True).all().distinct()

    def actividades_posgrado(self,f):
        from sagest.models import BitacoraActividadDiaria
        actividades = BitacoraActividadDiaria.objects.filter(status=True,persona=self.persona,fecha__date=f.date())
        if actividades:
            return True, actividades, f
        elif DiasNoLaborable.objects.values('id').filter(status=True,fecha=f.date(),motivo=1).exists():
            dias = DiasNoLaborable.objects.filter(status=True, fecha=f.date()).order_by('-id').first()
            return None, f'{dias.get_motivo_display()} - {dias.observaciones}'.upper(), f
        elif f.weekday() in [5, 6]:
            return None, 'FIN DE SEMANA', f
        return None, 'SIN ACTIVIDADES', f

    class Meta:
        verbose_name = u"Contrato Pagos"
        verbose_name_plural = u"Contratos de Pagos"

    def get_horario(self):
        return self.horarioplanificacioncontrato_set.filter(status=True)

    def get_turno_por_fecha(self, dia):
        return self.horarioplanificacioncontrato_set.filter(inicio__lte=dia, fin__gte=dia, dia=dia.weekday() + 1, status=True).first()

    def get_tiempo_dedicacion(self):
        if self.cargo:
            cargo = self.cargo.id
            if cargo == 101:
                return 40
            elif cargo == 100:
                return 20
            return 1000
        return 1000

    def get_requisitos_contratacion_cargados_ids(self):
        try:
            from postulaciondip.models import Requisito
            requisito_id =  ContratoRequisito.objects.filter(status=True,contratodip = self).values_list('requisito_id',flat=True)
            return Requisito.objects.filter(pk__in = requisito_id) if requisito_id else []
        except Exception as ex:
            pass

    def get_requisitos_contratacion_cargados(self):
        try:
            from postulaciondip.models import Requisito
            return  ContratoRequisito.objects.filter(status=True,contratodip = self)
        except Exception as ex:
            pass

    def get_requisitos_contratacion_pendientes_cargar(self):
        try:
            from postulaciondip.models import Requisito
            eRequisitos = None
            eContratacionConfiguracionRequisito = ContratacionConfiguracionRequisito.objects.filter(status=True,  activo=True)
            requisitos = eContratacionConfiguracionRequisito.first() if eContratacionConfiguracionRequisito.exists() else None
            requisitos_pendientes_ids =  requisitos.get_requisitos().exclude(requisito__in =self.get_requisitos_contratacion_cargados_ids()).values_list('requisito_id', flat=True)  if requisitos else None
            if requisitos_pendientes_ids:
                eRequisitos = Requisito.objects.filter(pk__in=requisitos_pendientes_ids)
            return eRequisitos
        except Exception as ex:
            pass

    def get_tiene_pago_realizado_en_el_mes(self,anio,mes):
        try:
            pago = self.contratodippagofactura_set.filter(status=True,anio=anio, mes=mes)
            if pago.exists():
                return pago.first()
            return False
        except Exception as ex:
            return False

    def estructura_de_pagos_contrato(self):
        try:
            fecha_inicio = self.fechainicio
            fecha_fin = self.fechafin
            # Calcular los meses entre la fecha de inicio y fin
            meses = []
            fecha_actual = fecha_inicio
            while fecha_actual <= fecha_fin:
                anio = fecha_actual.year
                mes_numero = fecha_actual.month
                mes_nombre = fecha_actual.strftime('%B')  # Nombre del mes en español
                meses.append((anio,mes_numero,  MESES_CHOICES[mes_numero- 1][1]))
                fecha_actual = fecha_actual.replace(day=1) + timedelta(days=32)  # Añadir un mes a la fecha actual

            # Crear la estructura de pagos
            estructura = []
            for anio,mes_numero, mes_nombre in meses:
                pago = self.get_tiene_pago_realizado_en_el_mes(anio=anio, mes=mes_numero)
                pago_mensual = {
                    'anio': anio,
                    'numero_mes': mes_numero,
                    'nombre_mes':mes_nombre ,
                    'monto': pago.monto_a_pagar if pago else 0.00,
                    'fecha_pago': pago.fecha_pago if pago else 'pendiente'
                }
                estructura.append(pago_mensual)

            return estructura
        except Exception as ex:
            pass

    def notificar_contrato_subido_para_registrar_analista_validador(self,request):
        try:
            ePersonas= Persona.objects.filter(status=True, pk__in=[2356,])#diana macias
            a = notificar_contrato_subido_para_registrar_analista_validador(request, ePersonas)
            a.start()
        except:
            pass
class ContratoCarrera(ModeloBase):
    contrato = models.ForeignKey(ContratoDip, blank=True, null=True, verbose_name=u'Contrato', on_delete=models.CASCADE)
    carrera = models.ForeignKey("sga.Carrera", blank=True, null=True, verbose_name=u'Carrera', on_delete=models.CASCADE)

    def __str__(self):
        return u'#%s %s - $ %s' % (self.contrato.codigocontrato, self.contrato.invitacion, self.carrera.nombre)

    class Meta:
        verbose_name = u"Contrato por carrera"
        verbose_name_plural = u"Contratos por carrera"
        ordering = ('-id',)

class ContratoAreaPrograma(ModeloBase):
    contrato = models.ForeignKey(ContratoDip, blank=True, null=True, verbose_name=u'Contrato', on_delete=models.CASCADE)
    departamento = models.ForeignKey("sagest.SeccionDepartamento", blank=True, null=True, verbose_name=u'Area o programa', on_delete=models.CASCADE)
    gestion = models.ForeignKey(Gestion, blank=True, null=True, verbose_name=u'Area o programa', on_delete=models.CASCADE)

    def __str__(self):
        return u'#%s - %s' % (self.contrato.codigocontrato, self.gestion.cargo)

    class Meta:
        verbose_name = u"Contrato area o programa"
        verbose_name_plural = u"Contratos area o programas"
        ordering = ('-id',)

class HistorialContratoDipCarreras(ModeloBase):
    contratocarrera = models.ForeignKey(ContratoCarrera, blank=True, null=True, verbose_name=u'Contrato', on_delete=models.CASCADE)
    carrera = models.ForeignKey("sga.Carrera", blank=True, null=True, verbose_name=u'Carrera', on_delete=models.CASCADE)

    def __str__(self):
        return u'#%s - (%s)' % (self.contratocarrera, self.carrera.nombre)

    class Meta:
        verbose_name = u"Historial contrato por carrera"
        verbose_name_plural = u"Historial contratos por carrera"
        ordering = ('-id',)


class ContratoDipDetalle(ModeloBase):
    contratodip = models.ForeignKey(ContratoDip, verbose_name=u"Cabecera de contrato",on_delete=models.CASCADE)
    campo = models.ForeignKey(CampoPlantillaContratoDip, verbose_name=u"Campo configurado",on_delete=models.CASCADE)
    valor = models.TextField(default='', verbose_name=u"Valor del Campo configurado")

    class Meta:
        verbose_name = u"Detalle del contrato"
        verbose_name_plural = u"Detalles de contratos"

class HistorialContratoDip(ModeloBase):
    contratodip = models.ForeignKey(ContratoDip, null=True, blank=True, verbose_name=u"Contrato Dip",on_delete=models.CASCADE)
    observacion = models.TextField(default='', null=True, blank=True, verbose_name=u'observación')
    estado = models.IntegerField(default=0, choices=ESTADO_CONTRATO, verbose_name=u'Estado de Contrato')
    persona = models.ForeignKey('sga.Persona', blank=True, null=True, verbose_name=u'Persona que realiza la acción',on_delete=models.CASCADE)

    def save(self, *args, **kwargs):
        self.observacion = self.observacion.upper()
        super(HistorialContratoDip, self).save(*args, **kwargs)

    def color_estado(self):
        estado = 'label-primary'
        if self.estado == 1 or self.estado == 3:
            estado = 'label-success'
        elif self.estado == 2:
            estado = 'label-warning'
        elif self.estado >= 6:
            estado = 'label-important'
        return estado

    class Meta:
        verbose_name = u"Historial del contrato"
        verbose_name_plural = u"Historiales del contrato"

TIPO_TRANSACCION = (
    (0, u'INGRESO'),
    (1, u'EGRESO'),
)

class DetalleCertificacionPresupuestariaDip(ModeloBase):
    certificado = models.ForeignKey(CertificacionPresupuestariaDip, null=True, blank=True, verbose_name=u"Certificacion Presupuestaria",on_delete=models.CASCADE)
    contratodip = models.ForeignKey(ContratoDip, null=True, blank=True, verbose_name=u"Contrato Dip",on_delete=models.CASCADE)
    valor = models.DecimalField(max_digits=30, decimal_places=2, default=0, verbose_name=u"Valor")
    fecha = models.DateField(blank=True, null=True, verbose_name=u'Fecha de certificación')
    tipo = models.IntegerField(default=0, choices=TIPO_TRANSACCION, verbose_name=u'Tipo Transaccion')
    devengado = models.DecimalField(max_digits=30, decimal_places=2, default=0, verbose_name=u"Valor devengado")
    saldo = models.DecimalField(max_digits=30, decimal_places=2, default=0, verbose_name=u"Saldo")

    def __str__(self):
        return u"%s - %s -%s" % (self.valor, self.fecha.strftime(''), self.get_tipo_display())

    class Meta:
        verbose_name = u'DetalleCertificación'
        verbose_name_plural = u'DetalleCertificaciones'
        ordering = ('certificado',)

class ActividadesContratoPerfil(ModeloBase):
    contrato = models.ForeignKey(ContratoDip,on_delete=models.CASCADE,null =True,blank=True,verbose_name="Contratos")
    perfil = models.ForeignKey(PerfilPuestoDip,on_delete=models.CASCADE,null=True,blank=True,verbose_name="Cargo")
    actividad = models.ForeignKey(ActividadesPerfil,on_delete=models.CASCADE,null=True,blank=True, verbose_name='Actividad')
    obligatoria = models.BooleanField(default=False,verbose_name='¿Es obligatoria?')

    def __str__(self):
        return 'El estado de la actividad %s es: %s'%(str(self.actividad),str(self.obligatoria))

    def actividades(self):
        if self.actividad.filter(status=True).exists():
            return self.actividad.filter(status=True)
        return None

    class Meta:
        verbose_name = u"Actividad Contrato Perfil"
        verbose_name_plural = u"Actividades Contratos Perfiles"
        ordering = ('id',)

#MODELOS PROCESO DE PAGOS

class ContratoDipMetodoPago(ModeloBase):
    contratodip = models.ForeignKey(ContratoDip, null=True, blank=True, verbose_name=u"Contrato",on_delete=models.CASCADE)
    numerocuota = models.IntegerField(verbose_name=u'Nùmero de Cuota', default=1)
    valorcuota = models.DecimalField(max_digits=30, decimal_places=2, default=0, verbose_name=u"Valor Cuota")
    cancelado = models.BooleanField(default=False, verbose_name=u"¿Cuota Cancelada?")
    fecha_pago = models.DateField(null=True, blank=True, verbose_name=u"Fecha de pago")

    class Meta:
        verbose_name = u"Contrato Mètodo Pago"
        verbose_name_plural = u"Contratos  MètodosPagos"

    def __str__(self):
        return u'Cuota: %s - valor: %s - Fecha: %s' % (self.numerocuota, self.valorcuota, self.fecha_pago)

    def tiene_solicitud(self):
        return self.solicitudpago_set.filter(status=True).exists()

    def solicitud_pago(self):
        return self.solicitudpago_set.filter(status=True).first()

class ClasificacionRequisitoPago(ModeloBase):
    descripcion = models.TextField(default='', verbose_name=u'Descripcion')

class RequisitoPagoDip(ModeloBase):
    nombre = models.CharField(max_length=1000, default='', verbose_name=u'Requisito')
    leyenda = models.CharField(max_length=1000, blank=True, null=True, verbose_name=u'Mensaje Ayuda')
    archivo = models.FileField(upload_to='requisitopagodip', blank=True, null=True, verbose_name=u'Documento de Guía')
    clasificacion = models.ForeignKey(ClasificacionRequisitoPago,on_delete=models.SET_NULL, null=True, blank=True)

    def nombre_input(self):
        return remover_caracteres_especiales_unicode(self.nombre).lower().replace(' ', '_')

    def __str__(self):
        return u'%s' % (self.nombre)

    class Meta:
        verbose_name = u"Requisito Pagos"
        verbose_name_plural = u"Requisitos de Pagos"

    def save(self, *args, **kwargs):
        self.nombre = self.nombre.upper()
        self.leyenda = self.leyenda.upper()
        super(RequisitoPagoDip, self).save(*args, **kwargs)

class ProcesoPago(ModeloBase):
    version = models.IntegerField(default=1, verbose_name=u'Nro de versión')
    nombre = models.CharField(max_length=1000, default='', verbose_name=u'Nombre del proceso')
    descripcion = models.TextField(default='', null=True, blank=True, verbose_name=u'Descripción')
    mostrar = models.BooleanField(default=False, verbose_name=u'Mostrar/No mostrar')
    perfil = models.IntegerField(default=0, choices=PERFIL_CONTRATO, verbose_name=u'Tipo Contrato')

    def traer_pasos(self):
        return self.pasoprocesopago_set.filter(status=True).order_by('numeropaso')

    def __str__(self):
        return u'%s - %s' % (self.nombre, self.version)

    class Meta:
        verbose_name = u"Proceso Pagos"
        verbose_name_plural = u"Procesos de Pagos"

    def save(self, *args, **kwargs):
        self.nombre = self.nombre.strip().upper()
        self.descripcion = self.descripcion.strip().upper()
        super(ProcesoPago, self).save(*args, **kwargs)

    def tiene_pasos(self):
        return self.pasoprocesopago_set.filter(status=True).exists()


ESTADOS_PAGO_SOLICITUD = (
    (0, u'PENDIENTE PROFESIONAL'),
    (3, u'PENDIENTE G.P'),
    (4, u'VALIDADO G.P.'),
    (5, u'DEVUELTO G.P.'),
    (6, u'POR LEGALIZAR JEFE INMEDIATO'),
    (7, u'LEGALIZADO JEFE INMEDIATO'),
    (8, u'PROCESO EN EJECUCIÓN G.P.'),
    (1, u'VALIDADO'),
    (2, u'APROBADO'),
)

ESTADOS_TRAMITE = (
    (0, u'PENDIENTE'),
    (1, u'ENVIADO VIP'),
    (2, u'ENVIADO VICERRECTORADO.'),
    (3, u'ENVIADO EPUNEMI'),
)

ESTADOS_TRAMITE_PAGO = (
    (0, u'PENDIENTE'),
    (1, u'PENDIENTE SUBIR FACTURA'),
    (2, u'FACTURA SUBIDA'),
    (3, u'ACTUALIZAR FACTURA'),
    (4, u'PAGO REALIZADO'),
    (5, u'FACTURA APROBADA POR EPUNEMI'),
    (6, u'FACTURA ACTUALIZADA'),
)

ESTADOS_PAGO_REQUISITO = (
    (0, u'PENDIENTE'),
    (1, u'VALIDADO JEFE INMEDIATO'),
    (2, u'APROBADO'),
    (3, u'EN PROCESO'),
    (4, u'FINALIZADA'),
    (5, u'RECHAZADO'),
    (6, u'ANULADO'),
    (7, u'ESPERA APROBACIÓN'),
    (8, u'ACTUALIZAR DOCUMENTO'),
    (9, u'FIRMADO PROFESIONAL'),
)

#REVISION G.P.
#DEVUELTO G.P.
#POR LEGALIZAR JEFE INMEDIATO
#LEGALIZADO JEFE INMEDIATO
#PROCESO EN EJEUCION G.P.
#REVISIÓN VICERECTORADO
#REVISÓN RECTORADO
#APROBADO PARA EP.



class PasoProcesoPago(ModeloBase):
    pasoanterior = models.ForeignKey('self', blank=True, null=True, related_name='paso_anterior', verbose_name='Paso Anterior',on_delete=models.CASCADE)
    numeropaso = models.IntegerField(default=0, verbose_name=u'Número de paso')
    proceso = models.ForeignKey(ProcesoPago, verbose_name=u'Proceso de pago',on_delete=models.CASCADE)
    descripcion = models.TextField(default='', null=True, blank=True, verbose_name=u'Descripción')
    valida = models.ForeignKey('sagest.DenominacionPuesto', related_name='+', blank=True, null=True, verbose_name=u'Valida Documentación',on_delete=models.CASCADE)
    carga = models.ForeignKey('sagest.DenominacionPuesto', related_name='+', blank=True, null=True, verbose_name=u'Carga Documentación',on_delete=models.CASCADE)
    estadovalida = models.IntegerField(default=0, choices=ESTADOS_PAGO_SOLICITUD, verbose_name=u'Estados de validación')
    estadorechazado = models.IntegerField(default=0, choices=ESTADOS_PAGO_SOLICITUD, verbose_name=u'Estados de rechazado')
    finaliza = models.BooleanField(default=False, verbose_name=u'Fin del proceso')
    beneficiario = models.BooleanField(default=False, verbose_name=u'Paso aplica a docente?')
    genera_informe = models.BooleanField(default=False, verbose_name=u'Genera Informe')
    carga_archivo = models.BooleanField(default=False, verbose_name=u'Carga Archivo')
    valida_archivo = models.BooleanField(default=False, verbose_name=u'Valida Archivo')
    leyenda = models.CharField(max_length=1000, blank=True, null=True, verbose_name=u'Mensaje Ayuda')
    tiempoalerta_carga = models.IntegerField(default=0, verbose_name=u'Tiempo de Alerta Carga')
    tiempoalerta_validacion = models.IntegerField(default=0, verbose_name=u'Tiempo de Alerta Validación')

    def save(self, *args, **kwargs):
        self.descripcion = self.descripcion.strip().upper()
        super(PasoProcesoPago, self).save(*args, **kwargs)

    def color_estado_valida(self):
        label = 'label label-default'
        if self.estadovalida == 0:
            label = 'label label-default'
        elif self.estadovalida == 1:
            label = 'label label-green'
        elif self.estadovalida == 2:
            label = 'label label-info'
        elif self.estadovalida == 3:
            label = 'label label-success'
        elif self.estadovalida == 4:
            label = 'label label-important'
        elif self.estadovalida == 5:
            label = 'label label-important'
        elif self.estadovalida == 6:
            label = 'label label-warning'
        return label

    def color_estado_rechazado(self):
        label = 'label label-default'
        if self.estadorechazado == 0:
            label = 'label label-default'
        elif self.estadorechazado == 1:
            label = 'label label-green'
        elif self.estadorechazado == 2:
            label = 'label label-info'
        elif self.estadorechazado == 3:
            label = 'label label-success'
        elif self.estadorechazado == 4:
            label = 'label label-important'
        elif self.estadorechazado == 5:
            label = 'label label-important'
        elif self.estadorechazado == 6:
            label = 'label label-warning'
        return label

    def finaliza_str(self):
        return 'fa fa-check-circle text-success' if self.finaliza else 'fa fa-times-circle text-error'

    def beneficiario_str(self):
        return 'fa fa-check-circle text-success' if self.beneficiario else 'fa fa-times-circle text-error'

    def genera_informe_str(self):
        return 'fa fa-check-circle text-success' if self.genera_informe else 'fa fa-times-circle text-error'

    def carga_archivo_str(self):
        return 'fa fa-check-circle text-success' if self.carga_archivo else 'fa fa-times-circle text-error'

    def valida_archivo_str(self):
        return 'fa fa-check-circle text-success' if self.valida_archivo else 'fa fa-times-circle text-error'

    def requisitos(self):
        return self.requisitopasopago_set.filter(status=True).order_by('requisito__nombre')

    def __str__(self):
        return u'PASO: %s' % (self.numeropaso)

    class Meta:
        verbose_name = u"Paso de Proceso"
        verbose_name_plural = u"Pasos de Procesos"

class RequisitoPasoPago(ModeloBase):
    requisito = models.ForeignKey(RequisitoPagoDip, verbose_name=u'Requisito',on_delete=models.CASCADE)
    paso = models.ForeignKey(PasoProcesoPago, verbose_name=u'Paso',on_delete=models.CASCADE)

    def __str__(self):
        return u'%s - %s' % (self.requisito, self.paso.numeropaso)

    class Meta:
        verbose_name = u"Requisito Paso"
        verbose_name_plural = u"Requisitos Pasos"

class SolicitudPago(ModeloBase):
    contrato = models.ForeignKey(ContratoDip, blank=True, null=True, verbose_name=u'Contrato',on_delete=models.CASCADE)
    cuentabancaria = models.ForeignKey('sga.CuentaBancariaPersona', blank=True, null=True, verbose_name=u'Cuenta Bancaria',on_delete=models.CASCADE)
    materia = models.ForeignKey('sga.ProfesorMateria', verbose_name=u'Materia', blank=True, null=True,on_delete=models.CASCADE)  # borrar despues no olvidar
    cuotapago = models.ForeignKey(ContratoDipMetodoPago, blank=True, null=True, verbose_name=u'Cuota de pago',on_delete=models.CASCADE)
    estado = models.IntegerField(default=0, choices=ESTADOS_PAGO_SOLICITUD, verbose_name=u'Estado de solicitud')
    numero = models.IntegerField(default=0, verbose_name=u'Número de solicitud')
    valor_solicitado = models.DecimalField(default=0, max_digits=16, decimal_places=2, verbose_name='Valor Solicitado')
    total_pagado = models.DecimalField(default=0, max_digits=16, decimal_places=2, verbose_name='Valor Pagado')
    fechainicio = models.DateTimeField(verbose_name='Fecha inicio', null=True, blank=True)
    fechaifin = models.DateTimeField(verbose_name='Fecha fin', null=True, blank=True)
    puede_subir_factura = models.BooleanField(default=False, verbose_name=u"¿Puede subir factura?")
    estadotramite = models.IntegerField(default=0, choices=ESTADOS_TRAMITE, verbose_name=u'Estado tramite')
    estadotramitepago = models.IntegerField(default=0, choices=ESTADOS_TRAMITE_PAGO, verbose_name=u'Estado pago')
    pago_realizado = models.BooleanField(default=False, verbose_name=u"¿pago realizado?")
    fechasubidafactura = models.DateTimeField(verbose_name='Fecha subida factura', null=True, blank=True)
    horas_ejecutadas_coordinador = models.FloatField( verbose_name=u'Horas ejecutadas coordinador',null=True, blank=True)

    def solicitud_proceso_en_ejecucion(self):
        return True if self.estado ==8 else False

    def epunemi_aprobo_factura(self):
            return True if self.estadotramitepago ==5 else False

    def tramite_factura_no_habilitada(self):
        return True if self.estadotramitepago == 0 else False

    def tramite_pendiente_subir_factura(self):
        return True if self.estadotramitepago == 1 else False

    def tramite_factura_subida(self):
        return True if self.estadotramitepago == 2 else False

    def tramite_actualizar_factura_subida(self):
        return True if self.estadotramitepago == 3 else False

    def tramite_factura_actualizada_subida(self):
            return True if self.estadotramitepago == 6 else False

    def tramite_pago_realizado(self):
        return True if self.estadotramitepago == 4 else False


    def no_eliminar(self):
        return not self.requisitosolicitudpago_set.filter(status=True, estado__in=[1, 2, 3, 4, 5]).exists()

    def historial_pago(self):
        return self.historialprocesosolicitud_set.filter(status=True).order_by('-pk')

    def iniciales_personas(self):
        nombresinciales, nombre = '', self.contrato.persona.nombres.split()
        if len(nombre) > 1:
            nombresiniciales = '{}{}'.format(nombre[0][0], nombre[1][0])
        else:
            nombresiniciales = '{}'.format(nombre[0][0])
        inicialespersona = '{}{}{}'.format(nombresiniciales, self.contrato.persona.apellido1[0],
                                           self.contrato.persona.apellido2[0])
        return inicialespersona

    def cod_solicitud(self):
        return 'PAGOS-{}-{}-{}-{}'.format(self.fecha_creacion.month, self.fecha_creacion.year,
                                          self.iniciales_personas(), self.numero)

    def color_estado(self):
        label = 'text-muted'
        if self.estado == 0:
            label = 'text-muted'
        elif self.estado == 1:
            label = 'text-success'
        elif self.estado == 2:
            label = 'text-info'
        elif self.estado == 3:
            label = 'text-success'
        elif self.estado == 4:
            label = 'text-danger'
        elif self.estado == 5:
            label = 'text-danger'
        elif self.estado == 6:
            label = 'text-warning'
        return label

    def color_estadotramite(self):
        label = 'text-muted'
        if self.estadotramite == 0:
            label = 'text-muted'
        elif self.estadotramite == 1:
            label = 'text-success'
        elif self.estadotramite == 2:
            label = 'text-info'
        elif self.estadotramite == 3:
            label = 'text-success'
        elif self.estadotramite == 4:
            label = 'text-danger'
        elif self.estadotramite == 5:
            label = 'text-danger'
        elif self.estadotramite == 6:
            label = 'text-warning'
        return label

    def color_estadotramitepago(self):
            label = 'text-muted'
            if self.estadotramitepago == 0:
                label = 'text-muted'
            elif self.estadotramitepago == 1:
                label = 'text-muted'
            elif self.estadotramitepago == 2:
                label = 'text-info'
            elif self.estadotramitepago == 3:
                label = 'text-danger'
            elif self.estadotramitepago == 4:
                label = 'text-success'
            elif self.estadotramitepago == 5:
                label = 'text-success'
            elif self.estadotramitepago == 6:
                label = 'text-info'
            return label

    def traer_pasos_solicitud(self):
        return self.requisitosolicitudpago_set.filter(status=True)

    def traer_pasos_aprobados(self):
        return self.requisitosolicitudpago_set.filter(status=True, estado=1)

    def paso_principal_validado(self):
        return self.traer_pasos_solicitud().first()

    def paso_actual(self):
        pasoactual = 1
        for paso in self.traer_pasos_solicitud():
            if paso.estado == 2 or paso.estado == 3 or paso.estado == 2:
                pasoactual = paso.paso.numeropaso
        return pasoactual

    def traer_paso_actual(self):
        pasoactual = None
        for paso in self.traer_pasos_solicitud():
            if paso.estado == 2 or paso.estado == 3 or paso.estado == 2 or paso.estado == 6 or paso.estado == 4:
                pasoactual = paso
        return pasoactual

    def total_pasos(self):
        return self.requisitosolicitudpago_set.filter(status=True).count()

    def pasos_pendientes(self):
        return self.requisitosolicitudpago_set.filter(status=True, estado=0).count()

    def pasos_aprobados(self):
        return self.requisitosolicitudpago_set.filter(status=True, estado=1).count()

    def pasos_enproceso(self):
        return self.requisitosolicitudpago_set.filter(status=True, estado=2).count()

    def pasos_rechazados(self):
        return self.requisitosolicitudpago_set.filter(status=True, estado=3).count()

    def calcular_progreso(self):
        try:
            porcentaje, totalpasos, totalaprobados = 0, self.total_pasos(), self.pasos_aprobados()
            if totalaprobados > 0:
                porcentaje = (totalaprobados / totalpasos) * 100
                return round(porcentaje, 2)
            else:
                return 0
        except Exception as ex:
            return 0

    def color_barra(self):
        color, porcentaje = 'bar', self.calcular_progreso()
        if porcentaje >= 80:
            color = 'bar-success'
        elif porcentaje < 80 and porcentaje > 50:
            color = 'bar-warning'
        else:
            color = 'bar'
        return color

    def traer_ultimo_historial(self):
        return HistorialProcesoSolicitud.objects.filter(status=True, requisito__solicitud=self,
                                                        requisito__solicitud__contrato=self.contrato,
                                                        requisito__requisito_id=14).order_by('-pk').first()

    def traer_puesto_contrato_persona(self):
        return 'DOCENTE'  # Aqui va el PerfilPuesto Posgrado

    def traer_file_firmado_colaborador(self):
        return HistorialProcesoSolicitud.objects.filter(status=True, estado__in = [0,2], requisito__solicitud=self,
                                                        requisito__solicitud__contrato=self.contrato,
                                                        persona_ejecucion=self.contrato.persona,
                                                        requisito__requisito_id=14).order_by('-id').first()

    def traer_informe_actividades_firmado(self):
        return HistorialProcesoSolicitud.objects.filter(status=True, requisito__solicitud=self,requisito__solicitud__contrato=self.contrato,requisito__requisito_id=14).order_by('-id').first()

    def __str__(self):
        return u'%s - %s' % (self.contrato.persona, self.get_estado_display())

    class Meta:
        verbose_name = u"Solicitud de Pagos Posgrado"
        verbose_name_plural = u"Solicitud de Pagos Posgrado"
        ordering = ('-id',)

    def load_info_monthly(self):
        return SolicitudInformePago.objects.filter(status=True, solicitud=self).order_by('id')

    def guardar_informe_solicitud_pago(self, request, requisito_id, observacion, hoy, persona, observacion_historial,
                                       name_file, resp):
        try:
            from pdip.models import RequisitoSolicitudPago
            if RequisitoSolicitudPago.objects.values('id').filter(status=True, solicitud=self,requisito_id=requisito_id).exists():
                requisito = RequisitoSolicitudPago.objects.filter(status=True, solicitud=self,requisito_id=requisito_id).order_by('-id').first()
            else:
                requisito = RequisitoSolicitudPago(
                    solicitud=self,
                    orden='1',
                    requisito_id=requisito_id,
                    observacion=observacion
                )
                requisito.save(request)
                self.guardar_requisitos_solicitud_pagos(request, hoy, persona)  # guardar los demas documentos de pagos
            #
            if HistorialProcesoSolicitud.objects.filter(status=True, persona_ejecucion=persona, requisito=requisito):
                hist_ = HistorialProcesoSolicitud.objects.filter(status=True, persona_ejecucion=persona,requisito=requisito).order_by('-id').first()
                hist_.fecha_ejecucion = hoy
            else:
                hist_ = HistorialProcesoSolicitud(
                    observacion=observacion_historial,
                    fecha_ejecucion=hoy,
                    persona_ejecucion=persona,
                    requisito=requisito
                )
            hist_.archivo.save(f'{name_file.replace(".pdf", "")}.pdf', resp)
            hist_.save(request)
            return requisito, hist_
        except Exception as ex:
            pass

    def actualizar_informe_de_actividades(self, request, requisito_id, observacion, hoy, persona, observacion_historial,name_file, resp):
        try:
            from pdip.models import RequisitoSolicitudPago
            if RequisitoSolicitudPago.objects.values('id').filter(status=True, solicitud=self,requisito_id=requisito_id).exists():
                requisito = RequisitoSolicitudPago.objects.filter(status=True, solicitud=self,requisito_id=requisito_id).order_by('-id').first()
            else:
                requisito = RequisitoSolicitudPago(
                    solicitud=self,
                    orden='1',
                    requisito_id=requisito_id,
                    observacion=observacion
                )
                requisito.save(request)
            requisito.estado= 0
            requisito.save(request)
            hist_ = HistorialProcesoSolicitud(
                observacion=observacion_historial,
                fecha_ejecucion=hoy,
                persona_ejecucion=persona,
                requisito=requisito
            )
            hist_.archivo.save(f'{name_file.replace(".pdf", "")}.pdf', resp)
            hist_.save(request)
            return requisito, hist_
        except Exception as ex:
            pass

    def guardar_informe_solicitud_pago_desde_cronograma_posgrado(self, request, requisito_id, observacion, hoy, persona, observacion_historial,file):
        try:
            from pdip.models import RequisitoSolicitudPago
            if RequisitoSolicitudPago.objects.values('id').filter(status=True, solicitud=self,requisito_id=requisito_id).exists():
                requisito = RequisitoSolicitudPago.objects.filter(status=True, solicitud=self,requisito_id=requisito_id).order_by('-id').first()
            else:
                requisito = RequisitoSolicitudPago(
                    solicitud=self,
                    orden='1',
                    requisito_id=requisito_id,
                    observacion=observacion
                )
                requisito.save(request)
                self.guardar_requisitos_solicitud_pagos(request, hoy, persona)  # guardar los demas documentos de pagos
            #
            if HistorialProcesoSolicitud.objects.filter(status=True, persona_ejecucion=persona, requisito=requisito):
                hist_ = HistorialProcesoSolicitud.objects.filter(status=True, persona_ejecucion=persona,requisito=requisito).order_by('-id').first()
                hist_.fecha_ejecucion = hoy
            else:
                hist_ = HistorialProcesoSolicitud(
                    observacion=observacion_historial,
                    fecha_ejecucion=hoy,
                    persona_ejecucion=persona,
                    requisito=requisito
                )
            hist_.archivo = file
            hist_.save(request)
            return requisito, hist_
        except Exception as ex:
            pass

    def guardar_requisitos_solicitud_pagos(self, request, hoy, persona):
        try:
            INFORME_DE_ACTIVIDADES = 14
            eGrupoRequisitoPago = GrupoRequisitoPago.objects.filter(status=True)
            if not eGrupoRequisitoPago.exists():
                raise NameError("No tiene configurado los requisitos de pago")
            eGrupoRequisitoPago = eGrupoRequisitoPago.first()
            if eGrupoRequisitoPago.get_requisitos():
                for eRequisitoPago in eGrupoRequisitoPago.get_requisitos().exclude(requisitopagodip_id__in=[INFORME_DE_ACTIVIDADES]):
                    requisito = eRequisitoPago.requisitopagodip
                    if not RequisitoSolicitudPago.objects.values('id').filter(status=True, solicitud=self,requisito=requisito).exists():
                        eRequisitoSolicitudPago = RequisitoSolicitudPago(
                            solicitud=self,
                            orden=eRequisitoPago.orden,
                            requisito=requisito,
                            opcional=eRequisitoPago.opcional,
                            observacion=''
                        )
                        eRequisitoSolicitudPago.save(request)



                        hist_ = HistorialProcesoSolicitud(
                            observacion='Generación inicial requisito',
                            fecha_ejecucion=hoy,
                            persona_ejecucion=persona,
                            requisito=eRequisitoSolicitudPago
                        )
                        hist_.save(request)
                        # clono los requisitos qu eesten en pagos anteriores
                        eRequisitoSolicitudPago.generar_clonar_documento_pdf_requisito_pago(persona, request)
        except Exception as ex:
            pass

    def solicitud_en_proceso(self):
        return True if self.estado == 8 else False

    def solicitud_esta_en_acta_de_pago(self):
        eDetalleActaPago= DetalleActaPago.objects.filter(status=True, actapagoposgrado__status=True, solicitudpago__status=True, solicitudpago=self)
        return eDetalleActaPago.first() if eDetalleActaPago.exists() else False

    def get_check_list_pago_configurado_en_solicitud_de_pago(self):
        return self.requisitosolicitudpago_set.filter(status=True).order_by('orden')

    def tiene_cargado_documento_check_list_acta_pago(self,eRequisitoPagoDip):
        try:
            eRequisitoSolicitudPago = self.requisitosolicitudpago_set.filter(status=True,requisito = eRequisitoPagoDip)
            if eRequisitoSolicitudPago:
                if eRequisitoSolicitudPago.first().last_historial():
                    return eRequisitoSolicitudPago.first().last_historial().archivo if eRequisitoSolicitudPago.first().last_historial().archivo else None
            return None
        except Exception as ex:
            pass

    def tiene_aprobado_por_analista_documento_check_list_acta_pago(self, eRequisitoPagoDip):
        try:
            eRequisitoSolicitudPago = self.requisitosolicitudpago_set.filter(status=True, requisito=eRequisitoPagoDip)
            if eRequisitoSolicitudPago:
                return True if eRequisitoSolicitudPago.first().estado == 2 else False
            return False
        except Exception as ex:
            pass

    def get_detalle_acta_pago(self):
        try:
            eDetalleActaPago = self.detalleactapago_set.filter(status=True, actapagoposgrado__status=True)
            return eDetalleActaPago.first() if eDetalleActaPago.exists() else False
        except Exception as ex:
            return False

    def generar_documento_pdf_check_list_de_pago_solicitud(self,request,persona_ejecucion):
        try:
            data, fechaemision = {},datetime.now().date()
            hoy = datetime.now().date()
            name = unicodedata.normalize('NFD', u"informe_%s" % (self.pk)).encode('ascii', 'ignore').decode("utf-8").lower().replace(' ', '_').replace('-', '')
            filename = generar_nombre(u"%s_" % name, f"{name}.pdf")
            filepath = '/historialsolicitudpagoposgrado/{0}/{1}/{2}/{3}'.format(persona_ejecucion.pk, hoy.year, hoy.month, hoy.day)
            folder_pdf = os.path.join(SITE_STORAGE, 'media', 'historialsolicitudpagoposgrado', f'{persona_ejecucion.pk}', hoy.year.__str__(), hoy.month.__str__(),hoy.day.__str__(), '')
            os.makedirs(os.path.join(folder_pdf), exist_ok=True)
            data['pagesize'] = 'A4'
            data['request'] = request
            data['fechaemision'] = fechaemision
            data['eSolicitudPago'] = self
            return os.path.join(filepath, filename) if convert_html_to_pdf('adm_solicitudpago/docs/check_list_pago_pdf.html', data, filename, folder_pdf) else None
        except Exception as ex:
            pass

    def get_meses_entre_fecha_inicio_fin_pago(self):
        try:
            if self.fechainicio and self.fechaifin:
                inicio = self.fechainicio
                fin = self.fechaifin
                diferencia = relativedelta(fin, inicio)
                total_meses = diferencia.years * 12 + diferencia.months
                meses = []
                for i in range(total_meses + 1):
                    fecha = inicio + relativedelta(months=i)
                    nombre_mes = MESES_CHOICES[fecha.month - 1][1]
                    meses.append((nombre_mes, fecha.month))
                return meses
            else:
                return None
        except Exception as ex:
            return

    def get_str_meses_entre_fechas_inicio_fin(self):
        mensaje = ''
        for mes in self.get_meses_entre_fecha_inicio_fin_pago():
            mensaje+= f'{mes[0]}, '
        mensaje = mensaje[:-2]
        mensaje += ''
        return mensaje

    def get_subio_todo_los_requisitos_de_pago(self):
        INFORME_ACTIVIDAD = 14
        CHECK_LIST_DE_PAGO = 16
        FACTURA = 4
        FORMATO_DE_PROVEEDORES = 6
        RELACION_DEPENDENCIA_LABORAL = 20
        IMPEDIMENTO_PARA_EJERCER_CARGO_PUBLICO = 19
        subio_todo=True
        eRequisitoSolicitudPagos = RequisitoSolicitudPago.objects.filter(status=True,opcional=False,solicitud = self)
        for eRequisitoSolicitudPago in eRequisitoSolicitudPagos:
            if not eRequisitoSolicitudPago.requisito.pk in (INFORME_ACTIVIDAD,CHECK_LIST_DE_PAGO,FACTURA,RELACION_DEPENDENCIA_LABORAL,IMPEDIMENTO_PARA_EJERCER_CARGO_PUBLICO):
                if eRequisitoSolicitudPago.last_historial():
                    if eRequisitoSolicitudPago.last_historial().archivo:
                        if eRequisitoSolicitudPago.last_historial().archivo.name =='':
                            subio_todo = False
                            break
                    else:
                        subio_todo = False
                        break
                else:
                    subio_todo = False
                    break
        return subio_todo

    def get_requisito_informe_actividad_pago(self):
        INFORME_ACTIVIDAD = 14
        requisito = None
        eRequisitoSolicitudPagos = RequisitoSolicitudPago.objects.filter(status=True, solicitud = self,requisito__pk = INFORME_ACTIVIDAD)
        if eRequisitoSolicitudPagos.exists():
            requisito= eRequisitoSolicitudPagos.first()
        return requisito



    def get_requisitos_solicitados_configurados_administrativos(self):
        requisitos = None
        eGrupoRequisitoPago = GrupoRequisitoPago.objects.filter(status=True,activo=True,tipogrupo=1)
        if eGrupoRequisitoPago.exists():
            requisitos = eGrupoRequisitoPago.first().get_requisitos()
        return requisitos

    def get_requisitos_solicitados_configurados_administrativos_tics(self):
        requisitos = None
        eGrupoRequisitoPago = GrupoRequisitoPago.objects.filter(status=True,activo=True,tipogrupo=1)
        if eGrupoRequisitoPago.exists():
            requisitos = eGrupoRequisitoPago.first().get_requisitos().exclude(requisitopagodip_id__in = [19,20])
        return requisitos

    def tienen_aprobado_los_requisitos_por_analista_excluyendo_la_factura(self):
        try:
            INFORME_DE_ACTIVIDADES = 14
            CERTIFICACION_BANCARIA = 5
            FORMATO_DE_PROVEEDORES = 6
            CERTIFICACION_PRESUPUESTARIA = 15
            CHECK_LIST_DE_PAGO = 16
            FACTURA = 4
            RELACION_DE_DEPENDENCIA_LABORAL = 20
            IMPEDIMENTO_EJERCER_CARGO_PUBLICO = 19
            TIENEN_APROBADO_LOS_REQUISITOS_POR_ANALISTA = True
            eSolicitudPago = self
            for eRequisitoPagoDip in self.get_requisitos_solicitados_configurados_administrativos():
                if not eRequisitoPagoDip.requisitopagodip.id == CHECK_LIST_DE_PAGO and not eRequisitoPagoDip.requisitopagodip.id == FACTURA and not eRequisitoPagoDip.requisitopagodip.id == INFORME_DE_ACTIVIDADES :
                    if not eSolicitudPago.tiene_aprobado_por_analista_documento_check_list_acta_pago(eRequisitoPagoDip.requisitopagodip):
                        TIENEN_APROBADO_LOS_REQUISITOS_POR_ANALISTA = False
                        break
            return TIENEN_APROBADO_LOS_REQUISITOS_POR_ANALISTA
        except Exception as ex:
            pass

    def tienen_aprobado_los_requisitos_por_analista_excluyendo_la_factura_y_requisitos_tics(self):
        try:
            INFORME_DE_ACTIVIDADES = 14
            CERTIFICACION_BANCARIA = 5
            FORMATO_DE_PROVEEDORES = 6
            CERTIFICACION_PRESUPUESTARIA = 15
            CHECK_LIST_DE_PAGO = 16
            FACTURA = 4
            RELACION_DE_DEPENDENCIA_LABORAL = 20
            IMPEDIMENTO_EJERCER_CARGO_PUBLICO = 19
            TIENEN_APROBADO_LOS_REQUISITOS_POR_ANALISTA = True
            eSolicitudPago = self
            for eRequisitoPagoDip in self.get_requisitos_solicitados_configurados_administrativos_tics():
                if not eRequisitoPagoDip.requisitopagodip.id == CHECK_LIST_DE_PAGO and not eRequisitoPagoDip.requisitopagodip.id == FACTURA and not eRequisitoPagoDip.requisitopagodip.id == INFORME_DE_ACTIVIDADES :
                    if not eSolicitudPago.tiene_aprobado_por_analista_documento_check_list_acta_pago(eRequisitoPagoDip.requisitopagodip):
                        TIENEN_APROBADO_LOS_REQUISITOS_POR_ANALISTA = False
                        break
            return TIENEN_APROBADO_LOS_REQUISITOS_POR_ANALISTA
        except Exception as ex:
            pass

    def calcular_totaldias(self, fechainicio, fechafin):
        #CALCULA EL TOTAL DE DÍAS QUE HA TRABAJADO EL EMPLEADO
        totaldias = fechafin.day - fechainicio.day
        return totaldias

    def obtener_fechas_inicio_fin(self):
        from datetime import datetime, timedelta
        from dateutil.relativedelta import relativedelta
        # Convertir las cadenas de fecha en objetos datetime
        fecha_inicio = self.fechainicio
        fecha_fin = self.fechaifin
        # Calcular la diferencia en meses entre las fechas
        diferencia_meses = (fecha_fin.year - fecha_inicio.year) * 12 + fecha_fin.month - fecha_inicio.month + 1
        # Si la diferencia es 1, entonces es solo un mes
        if diferencia_meses == 1:
            return [(fecha_inicio, fecha_fin)]

        # Lista para almacenar las fechas de inicio y fin de cada mes
        fechas_inicio_fin = []

        # Iterar sobre los meses dentro del rango de fechas
        fecha_actual = fecha_inicio
        for _ in range(diferencia_meses):
            # Calcular la fecha de fin del mes actual
            fecha_fin_mes = fecha_actual + relativedelta(day=31)

            # Si la fecha de fin del mes actual es posterior a la fecha fin,
            # establecerla como la fecha fin
            if fecha_fin_mes > fecha_fin:
                fecha_fin_mes = fecha_fin

            # Agregar las fechas de inicio y fin del mes actual a la lista
            fechas_inicio_fin.append((fecha_actual, fecha_fin_mes))

            # Calcular la fecha de inicio del siguiente mes
            fecha_actual += relativedelta(months=1)
            fecha_actual = fecha_actual.replace(day=1)

        return fechas_inicio_fin

    def calcular_valor_a_pagar_pago(self):
        try:
            dias_transcurridos = 0
            total_dias = 30
            total_pago_subtotal = 0
            total_pago_iva = 0
            if not self.horas_ejecutadas_coordinador:
                fecha_inicio = self.fechainicio
                fecha_fin = self.fechaifin
                fechas_inicio_fin = self.obtener_fechas_inicio_fin()

                for inicio, fin in fechas_inicio_fin:
                    subtotal_contrato = self.contrato.valortotal/ Decimal(1 + self.contrato.iva.porcientoiva)
                    iva_contrato = subtotal_contrato *Decimal(self.contrato.iva.porcientoiva)
                    rmu_contrato = subtotal_contrato+iva_contrato
                    valorporhora = subtotal_contrato/30

                    if fin.day == 31 or fin.day == 28:
                        dias_transcurridos = (fin - inicio).days
                    else:
                        dias_transcurridos = (fin - inicio).days + 1

                    if dias_transcurridos == 31 or (inicio.month  == 2 and (dias_transcurridos == 29 or dias_transcurridos == 28)):
                        dias_transcurridos = 30
                    subtotal_a_pagar = round(round(valorporhora,4) *  dias_transcurridos, 2)

                    total_pago_subtotal  += round(float(subtotal_a_pagar),2)

                total_pago_iva = round(total_pago_subtotal * float(self.contrato.iva.porcientoiva) * 100) / 100
                # total_pago_iva =  round(total_pago_subtotal *Decimal(0.15), 2)
                total_a_pagar_rmu =   round(float(total_pago_subtotal) +total_pago_iva, 2)
                return round(total_pago_subtotal,2),round(total_pago_iva, 2),total_a_pagar_rmu,dias_transcurridos
            else:
                #es coordinador
                fecha_inicio = self.fechainicio
                fecha_fin = self.fechaifin
                fechas_inicio_fin = self.obtener_fechas_inicio_fin()
                for inicio, fin in fechas_inicio_fin:
                    if fin.day == 31 or fin.day == 28:
                        dias_transcurridos = (fin - inicio).days
                    else:
                        dias_transcurridos = (fin - inicio).days + 1

                    if dias_transcurridos == 31 or (inicio.month == 2 and (dias_transcurridos == 29 or dias_transcurridos == 28)):
                        dias_transcurridos = 30

                horas_ejecutadas= 40 if self.horas_ejecutadas_coordinador > 40 else self.horas_ejecutadas_coordinador
                sueldo_completo = self.contrato.valortotal
                subtotal_contrato = sueldo_completo/ Decimal(1 + self.contrato.iva.porcientoiva)
                valor_por_hora = subtotal_contrato / 40
                total_pago_subtotal =  round(float(valor_por_hora) * horas_ejecutadas, 2)
                total_pago_iva = total_pago_subtotal * float(self.contrato.iva.porcientoiva)
                valor_real_a_pagar_total =  round(total_pago_subtotal + total_pago_iva, 2)
                return total_pago_subtotal, round(total_pago_iva, 2), valor_real_a_pagar_total, dias_transcurridos

        except Exception as ex:
            pass

    def descargar_requisitos(self, request):
        from django.http import HttpResponse
        try:
            eSolicitudPago = self
            rutas_certificados = []
            dominiosistema = request.build_absolute_uri('/')[:-1].strip("/")
            directory = os.path.join(SITE_STORAGE, 'media/zip')
            try:
                os.stat(directory)
            except:
                os.mkdir(directory)

            directory = os.path.join(SITE_STORAGE, 'media/documentosactapagopersonal')
            try:
                os.stat(directory)
            except:
                os.mkdir(directory)

            url = os.path.join(SITE_STORAGE, 'media', 'zip', f'{remover_caracteres_tildes_unicode(remover_caracteres_especiales_unicode(eSolicitudPago.contrato.persona.__str__()))}.zip')
            url_zip = url
            fantasy_zip = zipfile.ZipFile(url, 'w')
            persona = eSolicitudPago.contrato.persona
            carpeta_persona = f"{persona}/"
            if eSolicitudPago.solicitud_esta_en_acta_de_pago():
                acta_pago = SITE_STORAGE + eSolicitudPago.solicitud_esta_en_acta_de_pago().actapagoposgrado.archivo.url
                fantasy_zip.write(acta_pago, carpeta_persona + os.path.basename(acta_pago))
                memo_posgrado = SITE_STORAGE + eSolicitudPago.solicitud_esta_en_acta_de_pago().actapagoposgrado.archivo_memo.url
                fantasy_zip.write(memo_posgrado, carpeta_persona + os.path.basename(memo_posgrado))

                if eSolicitudPago.solicitud_esta_en_acta_de_pago().actapagoposgrado.archivo_memo_vice:
                    memo_vicerrectorado = SITE_STORAGE + eSolicitudPago.solicitud_esta_en_acta_de_pago().actapagoposgrado.archivo_memo_vice.url
                    fantasy_zip.write(memo_vicerrectorado, carpeta_persona + os.path.basename(memo_vicerrectorado))

                check_general = SITE_STORAGE + eSolicitudPago.solicitud_esta_en_acta_de_pago().actapagoposgrado.archivo_check_list.url
                fantasy_zip.write(check_general, carpeta_persona + os.path.basename(check_general))

            for eRequisitoSolicitudPago in eSolicitudPago.traer_pasos_solicitud().order_by("orden"):
                try:
                    ruta_archivo = eRequisitoSolicitudPago.last_historial().archivo.url
                    temp_pdf_path = SITE_STORAGE + ruta_archivo
                    url_archivo = (temp_pdf_path).replace('\\', '/')
                    ruta_archivo = (url_archivo).replace('//', '/')

                    # Agregar el archivo PDF a la carpeta de la inscripción dentro del ZIP
                    fantasy_zip.write(ruta_archivo, carpeta_persona + os.path.basename(ruta_archivo))
                except Exception as ex:
                    pass

            fantasy_zip.close()
            response = HttpResponse(open(url_zip, 'rb'), content_type='application/zip')
            response['Content-Disposition'] = f'attachment; filename={eSolicitudPago.contrato.persona}.zip'
            return response
        except Exception as ex:
            return None

    def notificar_pago_realizado(self,request):
        from sga.models import Notificacion
        try:
            from sga.templatetags.sga_extras import encrypt
            id_detalleacta = self.solicitud_esta_en_acta_de_pago().pk if self.solicitud_esta_en_acta_de_pago() else 0
            PAGO_REALIZADO=4
            self.estadotramitepago = PAGO_REALIZADO
            self.save(request)
            titulonotificacion = f'Pago mes: {self.get_str_meses_entre_fechas_inicio_fin()} - por acreditar en cuenta bancaria.'
            cuerponotificacion = f'Su pago del mes de {self.get_str_meses_entre_fechas_inicio_fin()} fue subido y está por acreditar a su cuenta bancaria.'
            notificacion = Notificacion(
                titulo=titulonotificacion,
                cuerpo=cuerponotificacion,
                destinatario=self.contrato.persona,
                url=f"https://sga.unemi.edu.ec/pro_solicitudpago?action=requisitos_solicitudes_pagos&id={encrypt(self.pk)}",
                content_type=None,
                object_id=None,
                prioridad=3,
                app_label='SGA',
                fecha_hora_visible=datetime.now() + timedelta(days=5))
            notificacion.save(request)

            titulonotificacionanalista = f'Pago mes: {self.get_str_meses_entre_fechas_inicio_fin()} realizado {self.contrato.persona}.'
            cuerponotificacionanalista = f'{self.contrato.persona} pago realizado del mes de {self.get_str_meses_entre_fechas_inicio_fin()} fue realizado por epunemi.'
            notificacion = Notificacion(
                titulo=titulonotificacionanalista,
                cuerpo=cuerponotificacionanalista,
                destinatario=self.contrato.validadorgp,
                url=f"https://sga.unemi.edu.ec/adm_solicitudpago?action=facturas_a_pagar&id={id_detalleacta}",
                content_type=None,
                object_id=None,
                prioridad=3,
                app_label='SGA',
                fecha_hora_visible=datetime.now() + timedelta(days=5))
            notificacion.save(request)
        except Exception as ex:
            pass

    def notificar_subir_factura(self,request):
        from sga.models import Notificacion
        from sga.templatetags.sga_extras import encrypt
        try:
            titulonotificacion = f'Subi Factura Mes: {self.get_str_meses_entre_fechas_inicio_fin()} '
            cuerponotificacion = f'Su pago del mes de {self.get_str_meses_entre_fechas_inicio_fin()} fue aprobado, favor subir la factura.'
            notificacion = Notificacion(
                titulo=titulonotificacion,
                cuerpo=cuerponotificacion,
                destinatario=self.contrato.persona,
                url=f"https://sga.unemi.edu.ec/pro_solicitudpago?action=requisitos_solicitudes_pagos&id={encrypt(self.pk)}",
                content_type=None,
                object_id=None,
                prioridad=3,
                app_label='SGA',
                fecha_hora_visible=datetime.now() + timedelta(days=5))
            notificacion.save(request)

            self.puede_subir_factura = True
            self.save(request)
        except Exception as ex:
            pass

    def guardar_historial_de_rechazo_factura_por_epunemi(self,request,eRequisitoSolicitudPago,obs,persona):
        try:
            requisito =eRequisitoSolicitudPago
            requisito.observacion = f'Factura rechazada por epunemi, por el motivo: {obs}'
            requisito.estado = 5
            requisito.save(request)
            log(f'Rechazo epunemi la factura: {requisito}', request, 'change')
            obshisto = HistorialObseracionSolicitudPago(
                solicitud=self,
                observacion=f'Factura rechazada por epunemi, por el motivo: {obs}',
                persona=persona,
                estado=0,
                fecha=datetime.now()
            )
            obshisto.save(request)
            eHistorialProcesoSolicitud =requisito.last_historial().guardar_historial_rechazo_epunemi_requisito_factura(request, f'Factura rechazada por epunemi, por el motivo: {obs}', persona)
        except Exception as ex:
            pass

    def notificar_rechazo_epunemi_actualizar_factura(self,request):
        from sga.models import Notificacion
        from sga.templatetags.sga_extras import encrypt
        try:
            id_detalleacta = self.solicitud_esta_en_acta_de_pago().pk if self.solicitud_esta_en_acta_de_pago() else 0
            titulonotificacion = f'Actualizar Factura Mes: {self.get_str_meses_entre_fechas_inicio_fin()} '
            cuerponotificacion = f'Actualizar factura del mes de {self.get_str_meses_entre_fechas_inicio_fin()} fue rechazada, favor actualizar.'
            notificacion = Notificacion(
                titulo=titulonotificacion,
                cuerpo=cuerponotificacion,
                destinatario=self.contrato.persona,
                url=f"https://sga.unemi.edu.ec/pro_solicitudpago?action=requisitos_solicitudes_pagos&id={encrypt(self.pk)}",
                content_type=None,
                object_id=None,
                prioridad=3,
                app_label='SGA',
                fecha_hora_visible=datetime.now() + timedelta(days=5))
            notificacion.save(request)

            titulonotificacionanalista = f'{self.contrato.persona} debe actualizar Factura Mes: {self.get_str_meses_entre_fechas_inicio_fin()} '
            cuerponotificacionanalista = f'{self.contrato.persona} debe actualizar factura del mes de {self.get_str_meses_entre_fechas_inicio_fin()} fue rechazada,comunicar al colaborador,actualizar.'
            notificacion = Notificacion(
                titulo=titulonotificacionanalista,
                cuerpo=cuerponotificacionanalista,
                destinatario=self.contrato.validadorgp,
                url=f"https://sga.unemi.edu.ec/adm_solicitudpago?action=facturas_a_pagar&id={id_detalleacta}",
                content_type=None,
                object_id=None,
                prioridad=3,
                app_label='SGA',
                fecha_hora_visible=datetime.now() + timedelta(days=5))
            notificacion.save(request)

        except Exception as ex:
            pass

    def notificar_aprobacion_factura_epunemi(self,request):
            from sga.models import Notificacion
            from sga.templatetags.sga_extras import encrypt
            try:
                id_detalleacta = self.solicitud_esta_en_acta_de_pago().pk if self.solicitud_esta_en_acta_de_pago() else 0
                titulonotificacion = f'Factura Aprobada Mes: {self.get_str_meses_entre_fechas_inicio_fin()} '
                cuerponotificacion = f'Factura del mes de {self.get_str_meses_entre_fechas_inicio_fin()} fue Aprobada.'
                notificacion = Notificacion(
                    titulo=titulonotificacion,
                    cuerpo=cuerponotificacion,
                    destinatario=self.contrato.persona,
                    url=f"https://sga.unemi.edu.ec/pro_solicitudpago?action=requisitos_solicitudes_pagos&id={encrypt(self.pk)}",
                    content_type=None,
                    object_id=None,
                    prioridad=3,
                    app_label='SGA',
                    fecha_hora_visible=datetime.now() + timedelta(days=5))
                notificacion.save(request)

                titulonotificacionanalista = f'{self.contrato.persona} Factura Aprobada Mes: {self.get_str_meses_entre_fechas_inicio_fin()} '
                cuerponotificacionanalista = f'{self.contrato.persona} factura del mes de {self.get_str_meses_entre_fechas_inicio_fin()} fue aprobada.'
                notificacion = Notificacion(
                    titulo=titulonotificacionanalista,
                    cuerpo=cuerponotificacionanalista,
                    destinatario=self.contrato.validadorgp,
                    url=f"https://sga.unemi.edu.ec/adm_solicitudpago?action=facturas_a_pagar&id={id_detalleacta}",
                    content_type=None,
                    object_id=None,
                    prioridad=3,
                    app_label='SGA',
                    fecha_hora_visible=datetime.now() + timedelta(days=5))
                notificacion.save(request)

            except Exception as ex:
                pass

    def notificar_factura_subida_por_el_colaborado(self,request):
        from sga.models import Notificacion
        try:
            id_detalleacta = self.solicitud_esta_en_acta_de_pago().pk if self.solicitud_esta_en_acta_de_pago() else 0
            FACTURA_SUBIDA=2
            FACTURA_ACTUALIZADA=6
            ENVIADA_A_ACTUALIZAR_FACTURA=3
            titulonotificacion = f'Factura mes: {self.get_str_meses_entre_fechas_inicio_fin()} - Subida por {self.contrato.persona} .'
            cuerponotificacion = f'{self.contrato.persona} subió  la factura del mes de {self.get_str_meses_entre_fechas_inicio_fin()}.'
            notificacion = Notificacion(
                titulo=titulonotificacion,
                cuerpo=cuerponotificacion,
                destinatario=self.contrato.validadorgp,
                url=f"https://sga.unemi.edu.ec/adm_solicitudpago?action=facturas_a_pagar&id={id_detalleacta}",
                content_type=None,
                object_id=None,
                prioridad=3,
                app_label='SGA',
                fecha_hora_visible=datetime.now() + timedelta(days=5))
            notificacion.save(request)

            eGrupo = Group.objects.get(pk=485)
            eUsers = eGrupo.user_set.all()


            for user in eUsers:
                ePersona = Persona.objects.filter(status=True, usuario=user).first()
                notificacion = Notificacion(
                    titulo=titulonotificacion,
                    cuerpo=cuerponotificacion,
                    destinatario=ePersona,
                    url=f"https://sga.unemi.edu.ec/adm_solicitudpago?action=facturas_a_pagar&id={id_detalleacta}",
                    content_type=None,
                    object_id=None,
                    prioridad=3,
                    app_label='SGA',
                    fecha_hora_visible=datetime.now() + timedelta(days=5))
                notificacion.save(request)

            self.fechasubidafactura = datetime.now()
            if  self.estadotramitepago == ENVIADA_A_ACTUALIZAR_FACTURA:
                self.estadotramitepago = FACTURA_ACTUALIZADA
            else:
                self.estadotramitepago = FACTURA_SUBIDA
            self.save(request)
        except Exception as ex:
            pass

    def guardar_pago_realizado(self,request,fecha_pago,mes_numero,anio,monto_a_pagar):
        try:
            eContratoDipPagoFactura = ContratoDipPagoFactura(
                contratodip= self.contrato,
                monto_a_pagar = monto_a_pagar,
                anio =anio,
                mes = mes_numero,
                fecha_pago = fecha_pago
            )
            eContratoDipPagoFactura.save(request)
            self.pago_realizado =True
            self.save(request)

        except Exception as ex:
            pass

    def get_factura(self):
        try:
            FACTURA = 4
            archivo_factura = False
            if self.traer_pasos_solicitud().order_by("orden").filter(requisito_id=FACTURA):
                factura = self.traer_pasos_solicitud().order_by("orden").filter(requisito_id=FACTURA).first()
                if factura.last_historial():
                    if factura.last_historial().archivo:
                        archivo_factura = factura.last_historial().archivo

            return archivo_factura
        except Exception as ex:
            pass

    def get_requisitosolicitudpago_factura(self):
        try:
            FACTURA = 4
            requisitosolicitudpago = None
            if self.traer_pasos_solicitud().order_by("orden").filter(requisito_id=FACTURA):
                erequisitosolicitudpago = self.traer_pasos_solicitud().order_by("orden").filter(requisito_id=FACTURA).first()
                if erequisitosolicitudpago:
                        requisitosolicitudpago = erequisitosolicitudpago

            return requisitosolicitudpago
        except Exception as ex:
            return None


class SolicitudInformePago(ModeloBase):
    solicitud = models.ForeignKey(SolicitudPago, verbose_name="Solicitud de pago", null=True, blank=True,
                                  on_delete=models.SET_NULL)
    informe = models.ForeignKey("inno.InformeMensualDocente", verbose_name="Informe mensual docente", null=True,
                                blank=True, on_delete=models.SET_NULL)

    class Meta:
        verbose_name = 'Solicitud pago de informe mensual docente'
        verbose_name_plural = 'Solicitud pagos de informes mensuales docentes'
        ordering = ['-id']

    def __str__(self):
        return f"{self.solicitud}-{self.informe}"


class HistorialObseracionSolicitudPago(ModeloBase):
    solicitud = models.ForeignKey(SolicitudPago, verbose_name="Solicitud de pago", null=True, blank=True,
                                  on_delete=models.SET_NULL)
    observacion = models.TextField(verbose_name='Observacion', null=True, blank=True)
    estado = models.IntegerField(default=0, choices=ESTADOS_PAGO_SOLICITUD, null=True, blank=True)
    persona = models.ForeignKey(Persona, verbose_name='Persona ejecuta accion', null=True, blank=True,
                                on_delete=models.SET_NULL)
    fecha = models.DateTimeField(verbose_name='Fecha', null=True, blank=True)

    class Meta:
        verbose_name = 'Historial observacion solicitud pago'
        verbose_name_plural = 'Historial observacion solicitud pago'
        ordering = ['-id']

    def __str__(self):
        return f'{self.observacion}({self.get_estado_display()}): {self.solicitud}'


class RequisitoSolicitudPago(ModeloBase):
    solicitud = models.ForeignKey(SolicitudPago, verbose_name=u'Paso', on_delete=models.CASCADE)
    orden = models.IntegerField(verbose_name=u"Orden" , default = 0)
    requisito = models.ForeignKey(RequisitoPagoDip, verbose_name=u'Requisito', on_delete=models.CASCADE)
    estado = models.IntegerField(default=0, choices=ESTADOS_PAGO_REQUISITO, verbose_name=u'Estado de requisito')
    opcional = models.BooleanField(default=False, verbose_name=u"opcional")
    observacion = models.TextField(default='', verbose_name=u'Observacion del requisito')

    def save(self, *args, **kwargs):
        self.observacion = self.observacion.strip().upper()
        super(RequisitoSolicitudPago, self).save(*args, **kwargs)

    def color_estado(self):
        label = 'text-muted'
        if self.estado == 0:
            label = 'text-muted'
        elif self.estado == 1:
            label = 'text-success'
        elif self.estado == 2:
            label = 'text-success'
        elif self.estado == 3:
            label = 'text-success'
        elif self.estado == 4:
            label = 'text-danger'
        elif self.estado == 5:
            label = 'text-danger'
        elif self.estado == 6:
            label = 'text-warning'
        elif self.estado == 7:
            label = 'text-warning'
        elif self.estado == 8:
            label = 'text-warning'
        return label

    def last_historial(self):
        return HistorialProcesoSolicitud.objects.filter(status=True, requisito=self).order_by('-id').first()

    def last_historial_persona(self,persona_ejecucion):
        return HistorialProcesoSolicitud.objects.filter(status=True, requisito=self,persona_ejecucion=persona_ejecucion).order_by('-id').first()

    def es_informe_de_actividades(self):
        return True if self.requisito.id == 14 else False

    def es_factura(self):
        return True if self.requisito.id == 4 else False

    def __str__(self):
        return u'%s - %s' % (self.solicitud, self.requisito)

    class Meta:
        verbose_name = u"Requisito Paso Pago"
        verbose_name_plural = u"Requisito Paso Pago"

    def generar_clonar_documento_pdf_requisito_pago(self,persona,request):
        try:
            from django.core.files import File
            CHECK_LIST_DE_PAGO = 16
            FACTURA = 4
            FORMATO_DE_PROVEEDORES = 6
            RELACION_DEPENDENCIA_LABORAL = 20
            IMPEDIMENTO_PARA_EJERCER_CARGO_PUBLICO = 19
            hoy = datetime.now().date()
            eRequisitoPagoDip = self.requisito
            eContratoDip = self.solicitud.contrato
            if not eRequisitoPagoDip.pk in (CHECK_LIST_DE_PAGO,FACTURA,RELACION_DEPENDENCIA_LABORAL,IMPEDIMENTO_PARA_EJERCER_CARGO_PUBLICO):
                historial_requisitos_de_pagos = RequisitoSolicitudPago.objects.filter(status=True,solicitud__status=True,solicitud__contrato=eContratoDip,requisito= eRequisitoPagoDip).order_by('id').exclude(pk=self.pk)
                archivo= None
                if historial_requisitos_de_pagos:
                    ultimo_requisito = historial_requisitos_de_pagos.last()
                    eHistorialProcesoSolicitud = HistorialProcesoSolicitud.objects.filter(status=True,requisito=ultimo_requisito).order_by('id')
                    if eHistorialProcesoSolicitud:
                        ultimo_archivo_de_requisito = eHistorialProcesoSolicitud.last()
                        if ultimo_archivo_de_requisito.fecha_caducidad >=datetime.now():
                            eHistorialProcesoSolicitud = HistorialProcesoSolicitud(
                                observacion='Requisito clonado del último pago realizado.',
                                fecha_ejecucion=hoy,
                                persona_ejecucion=persona,
                                requisito=self,
                                fecha_caducidad = ultimo_archivo_de_requisito.fecha_caducidad,
                                archivo=ultimo_archivo_de_requisito.archivo,
                                estado=2
                            )
                            eHistorialProcesoSolicitud.save(request)
                            self.estado = 2
                            self.observacion = "Requisito clonado de la ultima solicitud realizada."
                            self.save(request)
                            log(f'Requisito clonado: {self.eHistorialProcesoSolicitud.requisito}', request, 'change')

            if eRequisitoPagoDip.pk in [CHECK_LIST_DE_PAGO]:
                documento= "/media/" + self.solicitud.generar_documento_pdf_check_list_de_pago_solicitud(request,persona)
                url_archivo = (SITE_STORAGE + documento).replace('\\', '/')
                ruta_archivo = (url_archivo).replace('//', '/')
                eHistorialProcesoSolicitud = HistorialProcesoSolicitud(
                    observacion='Requisito clonado de la ultima solicitud realizada.',
                    fecha_ejecucion=hoy,
                    persona_ejecucion=persona,
                    requisito=self,

                )
                # Abre el archivo y lee su contenido binario
                with open(ruta_archivo, 'rb') as archivo_pdf:
                    eHistorialProcesoSolicitud.archivo.save('requisito_check_list_pago.pdf', File(archivo_pdf), save=True)
                eHistorialProcesoSolicitud.save(request)
                self.estado = 0
                self.observacion = "Check list generado"
                self.save(request)
                log(f'Requisito generado: {eHistorialProcesoSolicitud.requisito}', request, 'change')


        except Exception as ex:
            pass

    def importar_guardar_contrato(self, request,persona):
        try:
            from django.core.files import File
            hoy = datetime.now().date()
            if self.solicitud.contrato.archivo:
                archivo = self.solicitud.contrato.archivo.url
                url_archivo = (SITE_STORAGE + archivo).replace('\\', '/')
                ruta_archivo = (url_archivo).replace('//', '/')
                eHistorialProcesoSolicitud = HistorialProcesoSolicitud(
                    observacion='Requisito migrado.',
                    fecha_ejecucion=hoy,
                    persona_ejecucion=persona,
                    requisito=self,

                )
                # Abre el archivo y lee su contenido binario
                with open(ruta_archivo, 'rb') as archivo_pdf:
                    eHistorialProcesoSolicitud.archivo.save(f'contrato.pdf', File(archivo_pdf),save=True)
                eHistorialProcesoSolicitud.save(request)
                return True
            else:
                return False
        except Exception as ex:
            pass

    def importar_guardar_certificacionpresupuestaria(self, request,persona):
        try:
            from django.core.files import File
            hoy = datetime.now().date()
            if self.solicitud.contrato.certificacion.archivo:
                archivo = self.solicitud.contrato.certificacion.archivo.url
                url_archivo = (SITE_STORAGE + archivo).replace('\\', '/')
                ruta_archivo = (url_archivo).replace('//', '/')
                eHistorialProcesoSolicitud = HistorialProcesoSolicitud(
                    observacion='Requisito migrado.',
                    fecha_ejecucion=hoy,
                    persona_ejecucion=persona,
                    requisito=self,

                )
                # Abre el archivo y lee su contenido binario
                with open(ruta_archivo, 'rb') as archivo_pdf:
                    eHistorialProcesoSolicitud.archivo.save('certificacion_presupuestaria.pdf', File(archivo_pdf), save=True)
                eHistorialProcesoSolicitud.save(request)
                return True
            else:
                return False

        except Exception as ex:
            pass


ACCIONES_PASOS = (
    (0, u'INICIO'),
    (1, u'CARGAR ARCHIVOS'),
    (2, u'VALIDAR ARCHIVOS'),
    (3, u'FINALIZO'),
)

def bitacora_user_directory_path(instance, filename):
    # print(instance)
    fecha = datetime.now().date()
    return 'historialsolicitudpagoposgrado/{0}/{1}/{2}/{3}/{4}'.format(instance.persona_ejecucion.pk, fecha.year, fecha.month, fecha.day, filename)

class HistorialProcesoSolicitud(ModeloBase):
    estado = models.IntegerField(default=0, choices=ESTADOS_PAGO_REQUISITO, verbose_name=u'Estado de requisito')
    observacion = models.TextField(default='', verbose_name=u'Observacion del requisito')
    fecha_maxima = models.DateTimeField(blank=True, null=True, verbose_name='Fecha y Hora de Alerta')
    fecha_ejecucion = models.DateTimeField(blank=True, null=True, verbose_name='Fecha y Hora de Ejecución')
    fecha_caducidad = models.DateTimeField(blank=True, null=True, verbose_name='Fecha caducidad')
    persona_ejecucion = models.ForeignKey('sga.Persona', blank=True, null=True, verbose_name=u'Persona Ejecución', related_name='+',on_delete=models.CASCADE)
    accion = models.IntegerField(default=0, choices=ACCIONES_PASOS, verbose_name=u'Acción de pasos')
    requisito = models.ForeignKey(RequisitoSolicitudPago, null=True, blank=True, on_delete=models.CASCADE, verbose_name='Requisito solicitud pago')
    archivo = models.FileField(upload_to=bitacora_user_directory_path, verbose_name=u'Archivo Firmado',  null=True, blank=True)

    def __str__(self):
        return u'%s' % (self.observacion)

    class Meta:
        verbose_name = u"Historial Paso Pago"
        verbose_name_plural = u"Historial Paso Pago"
        ordering = ('-id',)

    def diasfaltantes_estado(self):
        fechaactual = datetime.now()
        if self.fecha_maxima and self.estado == 2:
            x = self.fecha_maxima.astimezone(timezone.get_current_timezone()).replace(tzinfo=None) - fechaactual
            if x.days >= 0:
                return 1
            elif x.days < 0:
                return 2
            else:
                return 0
        else:
            return 0

    def diasfaltantes_days(self):
        try:
            fechaactual = datetime.now()
            if self.estado in (4, 5):
                return '<b class="text-important">{}</b>'.format(self.get_estado_display())
            if self.estado == 2:
                fechaactual = datetime.now()
                tiempo = self.fecha_maxima.astimezone(timezone.get_current_timezone()).replace(
                    tzinfo=None) - fechaactual
                if tiempo.days >= 0:
                    return '<b class="text-info">{} <i class="fa fa-question-circle tr" title="Tiempo que falta"></i></b>'.format(str(tiempo).replace('day', 'dia').split('.')[0])
                else:
                    tiempofuera = fechaactual - self.fecha_maxima.astimezone(timezone.get_current_timezone()).replace(tzinfo=None)
                    return '<b class="text-error">{} <i class="fa fa-question-circle tr" title="Fuera de tiempo"></i></b>'.format(str(tiempofuera).replace('day', 'dia').split('.')[0])
            else:
                return False
        except Exception as ex:
            return '<i class="fa fa-question-circle tr" title="Sin Generar"></i>'

    def tiemporealizado(self):
        if self.fecha_creacion:
            fechapaso = self.fecha_creacion.astimezone(timezone.get_current_timezone()).replace(tzinfo=None)
            fechalimite = self.fecha_maxima.astimezone(timezone.get_current_timezone()).replace(tzinfo=None)
            if self.fecha_ejecucion:
                if self.accion == 0:
                    return '<label class="label label-success tr" title="Inicio">EJECUTADO</label>'
                fechanotificacion = self.fecha_ejecucion.astimezone(timezone.get_current_timezone()).replace(
                    tzinfo=None)
                tiempo = fechanotificacion - fechapaso
                tiemporeal = fechalimite - fechanotificacion
                if tiempo <= tiemporeal:
                    try:
                        return '<b class="text-info">{} <i class="fa fa-question-circle tr" title="Generado dentro de este tiempo {}"></i></b>'.format(
                            str(tiempo).replace('day', 'dia').split('.')[0],
                            str(tiemporeal).replace('day', 'dia').split('.')[0])
                    except Exception as ex:
                        return '<b class="text-info">{} <i class="fa fa-question-circle tr" title="Generado dentro de este tiempo {}"></i></b>'.format(
                            str(tiempo).replace('day', 'dia'), str(tiemporeal).replace('day', 'dia'))
                else:
                    try:
                        return '<b class="text-important">{} <i class="fa fa-question-circle tr" title="Retrazado, debio ser generado dentro de {}"></i></b>'.format(
                            str(tiempo).replace('day', 'dia').split('.')[0],
                            str(tiemporeal).replace('day', 'dia').split('.')[0])
                    except Exception as ex:
                        return '<b class="text-important">{} <i class="fa fa-question-circle tr" title="Retrazado, debio ser generado dentro de  {}"></i></b>'.format(
                            str(tiempo).replace('day', 'dia'), str(tiemporeal).replace('day', 'dia'))
            else:
                return '<i class="fa fa-question-circle tr" title="En Proceso"></i>'
        else:
            return '<i class="fa fa-question-circle tr" title="Sin Generar"></i>'

    def save(self, *args, **kwargs):
        self.observacion = self.observacion.strip().upper()
        super(HistorialProcesoSolicitud, self).save(*args, **kwargs)

    def color_estado(self):
        label = 'text-muted'
        if self.estado == 0:
            label = 'text-muted'
        elif self.estado == 1:
            label = 'text-success'
        elif self.estado == 2:
            label = 'text-success'
        elif self.estado == 3:
            label = 'text-success'
        elif self.estado == 4:
            label = 'text-danger'
        elif self.estado == 5:
            label = 'text-danger'
        elif self.estado == 6:
            label = 'text-warning'
        elif self.estado == 8:
            label = 'text-warning'
        return label

    def notificar_revision_requisito_pago(self,request, cuerponotificacion):
        from sga.models import Notificacion
        try:
            titulonotificacion = f'SOLICITUD DE PAGO: Actualizar requisito: {self.requisito.requisito.nombre}'
            notificacion = Notificacion(
                titulo=titulonotificacion,
                cuerpo=cuerponotificacion,
                destinatario=self.requisito.solicitud.contrato.persona,
                url=f"https://sga.unemi.edu.ec/pro_solicitudpago",
                content_type=None,
                object_id=None,
                prioridad=3,
                app_label='SGA',
                fecha_hora_visible=datetime.now() + timedelta(days=3))
            notificacion.save(request)
        except Exception as ex:
            pass

    def guardar_historial_observacionsolicitudpago(self,request,cuerpo):
        try:
            eHistorialObseracionSolicitudPago = HistorialObseracionSolicitudPago(
                solicitud=self.requisito.solicitud,
                observacion=cuerpo,
                persona=self.requisito.solicitud.contrato.persona,
                estado=0,
                fecha=datetime.now()
            )
            eHistorialObseracionSolicitudPago.save(request)
        except Exception as ex:
            pass

    def guardar_revision_requisito_pago(self, request, estado, observacion,persona,fecha_caducidad):
        try:
            APROBADO = 2
            RECHAZADO = 5
            ACTUALIZAR = 8
            self.estado = estado
            self.observacion = observacion
            self.persona = persona
            self.fecha_caducidad = fecha_caducidad
            self.save(request)
            if  estado == APROBADO:
                obs = f'requisito:  {self.requisito.requisito.nombre} validado'
                self.estado = APROBADO
                self.requisito.estado = APROBADO
                self.requisito.observacion = obs
                self.requisito.save(request)
                self.save(request)
                self.guardar_historial_observacionsolicitudpago(request, obs)
            else:
                self.estado = ACTUALIZAR
                self.requisito.estado = ACTUALIZAR
                self.requisito.observacion = observacion
                self.requisito.save(request)
                self.save(request)
                log(f'Requisito rechazo de pago: {self.requisito.requisito.nombre}', request, 'change')
                cuerpo = f'Actualizar requisito {self.requisito.requisito.nombre}, ver el historial para visualizar la observación'
                self.notificar_revision_requisito_pago(request, cuerpo)
                self.guardar_historial_observacionsolicitudpago(request, f'requisito:  {self.requisito.requisito.nombre} rechazado')

            log(u'{} : Validación de Requisito Individual pago - {}'.format(self.requisito.nombre,  self.solicitud.contrato.persona), request,"edit")
        except Exception as ex:
            pass

    def guardar_historial_rechazo_epunemi_requisito_factura(self, request, observacion, persona):
        try:
            ACTUALIZAR = 8
            self.estado = ACTUALIZAR
            self.observacion = observacion
            self.persona = persona
            self.save(request)
            log(f'Requisito rechazo de pago por epunemi: {self.requisito.requisito.nombre}', request, 'change')
        except Exception as ex:
            pass


# -------- PENDIENTE DEFINICION

# class PasoSolicitudPagos(ModeloBase):
#     fecha = models.DateField(blank=True, null=True, verbose_name=u'Fecha')  # BORRAR DESPUES
#     solicitud = models.ForeignKey(SolicitudPago, verbose_name=u'Solicitud',on_delete=models.CASCADE)
#     paso = models.ForeignKey(PasoProcesoPago, verbose_name=u'Paso',on_delete=models.CASCADE)
#     observacion = models.TextField(default='', verbose_name=u'Observacion de Revisión')
#     estado = models.IntegerField(default=0, choices=ESTADOS_PAGO_DIP, verbose_name=u'Estado de paso')
#
#     def save(self, *args, **kwargs):
#         self.observacion = self.observacion.strip().upper()
#         super(PasoSolicitudPagos, self).save(*args, **kwargs)
#
#     def color_estado(self):
#         label = 'label label-default'
#         if self.estado == 0:
#             label = 'label label-default'
#         elif self.estado == 1:
#             label = 'label label-green'
#         elif self.estado == 2:
#             label = 'label label-info'
#         elif self.estado == 3:
#             label = 'label label-success'
#         elif self.estado == 4:
#             label = 'label label-important'
#         elif self.estado == 5:
#             label = 'label label-important'
#         elif self.estado == 6:
#             label = 'label label-warning'
#         return label
#
#     def siguiente_paso(self):
#         return self.paso.numeropaso + 1
#
#     def puede_continuar(self):
#         return (self.estado == 1 and not self.paso.finaliza)
#
#     def requisito_paso(self):
#         return self.requisitopasosolicitudpagos_set.filter(status=True).order_by('requisito__nombre')
#
#     def __str__(self):
#         return u'%s - %s' % (self.solicitud, self.paso.numeropaso)
#
#     class Meta:
#         verbose_name = u"Pasos Solicitud Pago"
#         verbose_name_plural = u"Pasos Solicitud Pago"

class SecuenciaMemoActividadPosgrado(ModeloBase):
    anioejercicio = models.ForeignKey('sagest.AnioEjercicio',verbose_name='Anio ejercicio',on_delete=models.CASCADE)
    tipo = models.ForeignKey(PlantillaContratoDip,verbose_name='Tipo',on_delete=models.CASCADE,null=True,blank=True)
    secuencia = models.CharField(verbose_name='Secuencia',max_length=300)

    def __str__(self):
        return u'%s-%s' % (self.secuencia,self.anioejercicio)

    def en_uso(self):
        return self.memoactividadposgrado_set.values('id').exists()
    class Meta:
        verbose_name = u"Secuencia Actividad Posgrado"
        verbose_name_plural = u"Secuencia Actividad Posgrado"
        ordering = ('id',)

class HistorialPagoMes(ModeloBase):
    contrato = models.ForeignKey(ContratoDip,on_delete=models.CASCADE,verbose_name='Contrato')
    cancelado = models.BooleanField(default=False, verbose_name=u"¿Pago mensual Cancelada?")
    fecha_pago = models.DateField(null=True, blank=True, verbose_name=u"Fecha de pago")

    def __str__(self):
        return 'Mes %s - profesional: %s - estado de pago %s' % (self.fecha_pago,self.contrato.persona, 'Pagado' if self.cancelado else 'Pendiente')
    class Meta:
        verbose_name = u"Pago Mes"
        verbose_name_plural = u"Pagos Mensuales"
        ordering = ('id',)

class MemoActividadPosgrado(ModeloBase):
    secuenciamemo = models.ForeignKey(SecuenciaMemoActividadPosgrado,verbose_name='Secuencia Memo', on_delete=models.CASCADE)
    contrato = models.ForeignKey(ContratoDip, verbose_name='Contrato', on_delete=models.CASCADE,null=True,blank=True)
    mes = models.IntegerField(verbose_name='Mes Generado',null=True,blank=True,choices=MESES_CHOICES)
    secuencia = models.IntegerField(default='000',verbose_name='Secuencia')
    archivo = models.FileField(upload_to='contratoepunemi/memo/', verbose_name=u'Archivo')
    archivofirmado = models.FileField(upload_to='contratoepunemi/memo/', verbose_name=u'Archivo', null=True, blank=True)
    codigoqr = models.BooleanField(default=False, verbose_name=u"Admitidos generado con código QR")
    historialpago = models.ForeignKey(HistorialPagoMes, verbose_name='Historial de pago mensual', blank=True, null=True, on_delete=models.CASCADE)

    def __str__(self):
        return u'%s-%s' %(self.secuencia,self.secuenciamemo)

    def download_link(self):
        return self.archivo.url
    class Meta:
        verbose_name = u"Secuencia Memo Posgrado"
        verbose_name_plural = u"Secuencia Memo Posgrado"
        ordering = ('id',)

class InformeActividadJornada(ModeloBase):
    secuenciageneral = models.ForeignKey(SecuenciaMemoActividadPosgrado,verbose_name='Secuencia Informe Actividad', on_delete=models.CASCADE)
    contrato = models.ForeignKey(ContratoDip, verbose_name='Contrato', on_delete=models.CASCADE, null=True, blank=True)
    mes = models.IntegerField(verbose_name='Mes Generado', null=True, blank=True, choices=MESES_CHOICES)
    fechainicio= models.DateTimeField(verbose_name='Fecha inicio',null=True,blank=True)
    fechaifin= models.DateTimeField(verbose_name='Fecha inicio',null=True,blank=True)
    secuencia = models.TextField(default='000', verbose_name='Secuencia',null=True,blank=True)
    archivo = models.FileField(upload_to='contratoepunemi/informe/', verbose_name=u'Archivo')
    historialpago = models.ForeignKey(HistorialPagoMes, verbose_name='Historial de pago mensual', blank=True, null=True, on_delete=models.CASCADE)

    def __str__(self):
        return u'%s-%s' % (self.secuencia, self.secuenciageneral)

    def download_link(self):
        return self.archivo.url

    class Meta:
        verbose_name = u"Secuencia Actividad Horario"
        verbose_name_plural = u"Secuencia Actividad Horario"
        ordering = ('id',)
class InformeTecnico(ModeloBase):
    secuenciageneral = models.ForeignKey(SecuenciaMemoActividadPosgrado,verbose_name='Secuencia Informe Tecnico', on_delete=models.CASCADE)
    contrato = models.ForeignKey(ContratoDip, verbose_name='Contrato', on_delete=models.CASCADE, null=True, blank=True)
    mes = models.IntegerField(verbose_name='Mes Generado', null=True, blank=True, choices=MESES_CHOICES)
    secuencia = models.IntegerField(default='000', verbose_name='Secuencia')
    archivo = models.FileField(upload_to='contratoepunemi/inftec/', verbose_name=u'Archivo')
    archivofirmado = models.FileField(upload_to='contratoepunemi/inftec/', verbose_name=u'Archivo', null=True, blank=True)
    codigoqr = models.BooleanField(default=False, verbose_name=u"Admitidos generado con código QR")
    historialpago = models.ForeignKey(HistorialPagoMes, verbose_name='Historial de pago mensual', blank=True, null=True, on_delete=models.CASCADE)

    def __str__(self):
        return u'%s-%s' % (self.secuencia, self.secuenciageneral)

    def download_link(self):
        return self.archivo.url

    class Meta:
        ordering = ('id',)
        verbose_name = u"Informe Tecnico"
        verbose_name_plural = u"Informes Tecnicos"

class ActaPago(ModeloBase):
    secuenciageneral = models.ForeignKey(SecuenciaMemoActividadPosgrado,verbose_name='Secuencia Acta Pago', on_delete=models.CASCADE)
    contrato = models.ForeignKey(ContratoDip, verbose_name='Contrato', on_delete=models.CASCADE, null=True, blank=True)
    mes = models.IntegerField(verbose_name='Mes Generado', null=True, blank=True, choices=MESES_CHOICES)
    secuencia = models.IntegerField(default='000', verbose_name='Secuencia')
    archivo = models.FileField(upload_to='contratoepunemi/actapago/', verbose_name=u'Archivo')
    archivofirmado = models.FileField(upload_to='contratoepunemi/actapago/', verbose_name=u'Archivo', null=True, blank=True)
    codigoqr = models.BooleanField(default=False, verbose_name=u"Admitidos generado con código QR")
    historialpago = models.ForeignKey(HistorialPagoMes,verbose_name='Historial de pago mensual',blank=True,null=True,on_delete=models.CASCADE)

    def __str__(self):
        return u'%s-%s' % (self.secuencia, self.secuenciageneral)

    def download_link(self):
        return self.archivo.url

    class Meta:
        ordering = ('id',)
        verbose_name = u"Acta de Pago"
        verbose_name_plural = u"Actas de Pagos"

class PlantillaInformes(ModeloBase):
    nombre = models.CharField(verbose_name = 'Plantilla ',max_length=250)
    tipo = models.IntegerField(verbose_name='Tipo Informe',default=0,choices=TIPO_INFORME)
    archivo = models.FileField(upload_to='contratoepunemi/informes/',verbose_name=u'Archivo')
    vigente = models.BooleanField(verbose_name='Vigente', )
    anio = models.IntegerField(default=0, verbose_name=u"Año")

    def __str__(self):
        return '%s' % self.nombre

    def save(self, *args, **kwargs):
        self.nombre = self.nombre.upper().strip()
        super(PlantillaInformes,self).save(*args, **kwargs)
    class Meta:
        verbose_name = u"Plantilla Informe"
        verbose_name_plural = u"Plantilla Informe"
        ordering = ('id',)

class DocumentoContrato(ModeloBase):
    nombre = models.CharField(verbose_name=u'Nombre documento', max_length=500)
    codigo = models.CharField(verbose_name=u'Codigo documento', max_length=500)
    campo = models.ForeignKey(CampoContratoDip, verbose_name=u'Campo referencia documento',on_delete=models.CASCADE)

    def __str__(self):
        return f'{self.nombre} {self.codigo}'

    class Meta:
        verbose_name = u"Documento contrato"
        verbose_name_plural = u"Documentos de contrato"
        ordering = ('id',)

class GrupoRevisionPago(ModeloBase):
    nombre = models.CharField(verbose_name=u'Nombre de grupo', max_length=500, null=True,blank=True)
    persona = models.ForeignKey(Persona, verbose_name='Persona encargada de revision', null=True, blank=True, on_delete=models.SET_NULL)

    class Meta:
        verbose_name = 'Grupo revision de pago'
        verbose_name_plural = 'Grupos revisiones de pagos'
        ordering = ['-id']

    def __str__(self):
        return f'{self.persona} - {self.nombre}'

    def laodgrouppayment(self):
        return self.gruporevisionpagocontrato_set.filter(status=True)

class GrupoRevisionPagoContrato(ModeloBase):
    gruporevision = models.ForeignKey(GrupoRevisionPago, verbose_name=u'Grupo revision', null=True, blank=True, on_delete=models.SET_NULL)
    personacontrato = models.ForeignKey(Persona, verbose_name=u'Persona contratado', null=True, blank=True, on_delete=models.SET_NULL)

    class Meta:
        verbose_name = 'Grupo revision contrato'
        verbose_name_plural = 'Grupo revision contrato'
        ordering = ['-id']

    def __str__(self):
        return f'{self.gruporevision}: {self.personacontrato}'

class HorarioPlanificacionContrato(ModeloBase):
    dia = models.IntegerField(choices=DIAS_CHOICES, default=1, verbose_name=u'Día')
    turno = models.ManyToManyField(Turno, verbose_name=u"Turnos", blank=True)
    inicio = models.DateField(blank=True, null=True, verbose_name=u'Fecha inicial', db_index=True)
    fin = models.DateField(blank=True, null=True, verbose_name=u'Fecha final', db_index=True)
    contrato = models.ForeignKey(ContratoDip, blank=True, null=True, verbose_name=u'contrato', on_delete=models.SET_NULL)

    def __str__(self):
        return u'%s' % self.get_dia_display()

    class Meta:
        verbose_name = u"Horario planificacion contrato"
        verbose_name_plural = u"Horario planificacion contrato"
        ordering = ['id']

    def get_color_dia(self):
        if self.dia == 1:
            return ''
        elif self.dia == 2:
            return ''
        elif self.dia == 3:
            return ''
        elif self.dia == 4:
            return ''
        elif self.dia == 5:
            return ''
        elif self.dia == 6:
            return ''
        elif self.dia == 27:
            return ''


class RecursoPresupuestarioPosgrado(ModeloBase):
    descripcion= models.CharField(max_length=350, verbose_name=u"Descripción")


    def __str__(self):
        return self.descripcion

    def get_programas_maestrias(self):
        return self.cabecerarecursopresupuestarioposgrado_set.filter(status=True)

    def get_total_recurso(self):
        total = 0
        cabecerarecursopresupuestarioposgrado_id = self.cabecerarecursopresupuestarioposgrado_set.values_list('id',flat=True).filter(status=True)
        eItemRecursoPresupuestarioPosgrado_id = ItemRecursoPresupuestarioPosgrado.objects.values_list('pk',flat=True).filter(status=True,cabecerarecursopresupuestarioposgrado_id__in=cabecerarecursopresupuestarioposgrado_id)
        eDetalleRecursoPresupuestarioPosgrado = DetalleRecursoPresupuestarioPosgrado.objects.filter(status=True,itemrecursopresupuestarioposgrado_id__in = eItemRecursoPresupuestarioPosgrado_id )
        for detalle in eDetalleRecursoPresupuestarioPosgrado:
            total += detalle.calcular_total_a_certificar()
        return total

    class Meta:
        verbose_name = u' Recurso Presupuestario Posgrado'
        verbose_name_plural = u'  Recurso Presupuestario Posgrado'
        ordering = ('id',)

class CabeceraRecursoPresupuestarioPosgrado(ModeloBase):
    recursopresupuestarioPosgrado = models.ForeignKey(RecursoPresupuestarioPosgrado, on_delete=models.CASCADE,verbose_name=u'cabecerarecursopresupuestarioposgrado')
    malla = models.ForeignKey("sga.Malla", verbose_name=u'Malla', on_delete=models.CASCADE)
    periodo = models.ForeignKey("sga.Periodo", on_delete=models.CASCADE, verbose_name=u'Periodo')


    def __str__(self):
        return u"%s - %s" %(self.malla.carrera.nombre,self.get_periodo_anio_romano())

    def get_items(self):
        return self.itemrecursopresupuestarioposgrado_set.filter(status=True)

    def get_periodo_anio_romano(self):
        return f"{self.periodo.numero_cohorte_romano()} - {self.periodo.anio}"


    class Meta:
        verbose_name = u'Cabecera Recurso Presupuestario Posgrado'
        verbose_name_plural = u' Cabecera Recurso Presupuestario Posgrado'
        ordering = ('id',)


class ItemRecursoPresupuestarioPosgrado(ModeloBase):
    cabecerarecursopresupuestarioposgrado = models.ForeignKey(CabeceraRecursoPresupuestarioPosgrado, on_delete=models.CASCADE, verbose_name=u'cabecerarecursopresupuestarioposgrado')
    total_paralelos = models.IntegerField(default=0, verbose_name=u'Total paralelos')
    modulos_a_dictar = models.IntegerField(default=0, verbose_name=u'Módulos a dictar')


    def get_items(self):
        return self.detallerecursopresupuestarioposgrado_set.filter(status=True)

    class Meta:
        verbose_name = u'Item Recurso Presupuestario Posgrado'
        verbose_name_plural = u'Item Recurso Presupuestario Posgrado'
        ordering = ('id',)

    def __str__(self):
        return u"total paralelos: %s - modulos dictar: %s" % (self.total_paralelos,self.modulos_a_dictar)


class DetalleRecursoPresupuestarioPosgrado(ModeloBase):
    itemrecursopresupuestarioposgrado = models.ForeignKey(ItemRecursoPresupuestarioPosgrado, blank=True, null=True, on_delete=models.CASCADE, verbose_name=u'cabecerarecursopresupuestarioposgrado')
    desglosemoduloadictar = models.IntegerField(default=0, verbose_name=u'Desglose de los  módulos a dictar')
    horaspormodulo = models.IntegerField(default=0, verbose_name=u'Horas por módulo')
    valor_x_hora = models.ForeignKey("postulaciondip.ValorPorHoraInformeContratacion", verbose_name='valor por hora', on_delete=models.CASCADE)
    categoriadocente = models.ForeignKey("sga.TipoProfesor", on_delete=models.CASCADE, verbose_name=u'Tipo de Docente')


    class Meta:
        verbose_name = u'Detalle Recurso Presupuestario Posgrado'
        verbose_name_plural = u'Detalle Recurso Presupuestario Posgrado'
        ordering = ('id',)

    def __str__(self):
        return u"%s - %s - %s - %s" % (self.desglosemoduloadictar, self.horaspormodulo, self.valor_x_hora, self.categoriadocente)

    def calcular_total_horas(self):
        total = self.desglosemoduloadictar * self.horaspormodulo
        return total

    def calcular_total_a_certificar(self):
        if self.categoriadocente_id ==15 :# profesor autor
            total = (self.calcular_total_horas() * self.valor_x_hora.valor)
        else:
            total = (self.calcular_total_horas() * self.valor_x_hora.valor) * self.itemrecursopresupuestarioposgrado.total_paralelos
        return total

class ContratacionConfiguracionRequisito(ModeloBase):
    nombre = models.CharField(max_length=1000, default='', verbose_name=u'Nombre')
    activo = models.BooleanField(verbose_name="Activo", default=True)

    class Meta:
        verbose_name = u'Contratacion Configuracion Requisito'
        verbose_name_plural = u'Contratacion Configuracion Requisito'
        ordering = ('id',)

    def __str__(self):
        return u"%s" % (self.nombre)

    def get_activo_str(self):
        etiqueta = f"<span class='badge rounded-pill bg-success'>Activo</span>"  if self.activo else f"<span class='badge rounded-pill bg-danger'>no Activo</span>"
        return etiqueta

    def get_requisitos(self):
        return self.requisitocontratacionconfiguracionrequisito_set.filter(status=True)

    def en_uso(self):
        return self.requisitocontratacionconfiguracionrequisito_set.filter(status=True).exists()

class RequisitoContratacionConfiguracionRequisito(ModeloBase):
    contratacionconfiguracionrequisito = models.ForeignKey(ContratacionConfiguracionRequisito, verbose_name=u'contratacionconfiguracionrequisito', on_delete=models.CASCADE)
    requisito = models.ForeignKey("postulaciondip.Requisito",  verbose_name=u'Requisito', on_delete=models.CASCADE)
    tipo = models.IntegerField(default=1, choices=TIPO_REQUISITO, verbose_name=u'Tipo Requisito', blank = True, null = True)
    opcional = models.BooleanField(default=False, verbose_name=u"opcional")

    class Meta:
        verbose_name = u'Requisito Contratacion Configuracion Requisito'
        verbose_name_plural = u'Requisito Contratacion Configuracion Requisito'
        ordering = ('id',)

    def __str__(self):
        return u"%s" % (self.requisito)

    def get_opcional_str(self):
        etiqueta = f"<span class='badge rounded-pill bg-success'>Si</span>"  if self.opcional else f"<span class='badge rounded-pill bg-danger'>No</span>"
        return etiqueta

    def en_uso(self):
        return self.contratacionconfiguracionrequisito.filter(status=True,requisito=self.requisito).exists()

class ContratoRequisito(ModeloBase):
    contratodip =  models.ForeignKey(ContratoDip,  verbose_name=u'contrato', on_delete=models.CASCADE)
    requisito = models.ForeignKey("postulaciondip.Requisito",  verbose_name=u'Requisito', on_delete=models.CASCADE)
    archivo = models.FileField(upload_to='contratosepunemi/requisitos', blank=True, null=True, max_length=700,verbose_name=u'Archivo')
    fecha_caducidad = models.DateTimeField(blank=True, null=True, verbose_name=u"Fecha caducidad documento")

    class Meta:
        verbose_name = u'Contrato Requisito'
        verbose_name_plural = u'Contrato Requisito'
        ordering = ('id',)

    def __str__(self):
        return u"%s" % (self.contratodip)

class GrupoRequisitoPago(ModeloBase):
    descripcion = models.TextField(default='', verbose_name=u"Grupo requisito pago")
    tipogrupo = models.IntegerField(default=0, choices=TIPO_GRUPO, verbose_name=u'Tipo Grupo')
    activo = models.BooleanField(default=False, verbose_name=u"activo")

    class Meta:
        verbose_name = u'Grupo Requisito Pago'
        verbose_name_plural = u'Grupo Requisito Pago'
        ordering = ('id',)

    def __str__(self):
        return u"%s" % (self.descripcion)

    def en_uso(self):
        return self.requisitopagogruporequisito_set.filter(status=True).exists()

    def get_requisitos(self):
        return self.requisitopagogruporequisito_set.filter(status=True).order_by('orden')

    def en_uso(self):
        return self.requisitopagogruporequisito_set.exists()

    def actualizar_orden_tipo_opcional_de_solicitudes_de_requisitos_de_pagos(self,request,persona):
        try:
            a = actualizar_todas_las_solicitudes_orden_and_opcional_de_todos_los_requisitos_de_pago(request, self)
            a.start()
        except Exception as ex:
            pass

class RequisitoPagoGrupoRequisito(ModeloBase):
    gruporequisitopago = models.ForeignKey(GrupoRequisitoPago, verbose_name=u'Requisito', on_delete=models.CASCADE)
    requisitopagodip = models.ForeignKey(RequisitoPagoDip, verbose_name=u'Requisito', on_delete=models.CASCADE)
    opcional = models.BooleanField(default=False, verbose_name=u"opcional")
    orden = models.IntegerField(verbose_name=u"Orden" , default = 0)

    class Meta:
        verbose_name = u'Requisito Pago Grupo Requisito'
        verbose_name_plural = u'Requisito Pago Grupo Requisito'
        ordering = ('id',)

    def get_opcional_str(self):
        etiqueta = f"<span class='badge rounded-pill bg-success'>Si</span>"  if self.opcional else f"<span class='badge rounded-pill bg-danger'>No</span>"
        return etiqueta

    def __str__(self):
        return u"%s" % (self.requisitopagodip)

    def en_uso(self):
        return RequisitoSolicitudPago.objects.filter(status=True,requisito = self.requisitopagodip).exists()

class OrdenFirmaActaPago(ModeloBase):
    responsabilidadfirma =models.ForeignKey("postulaciondip.ResponsabilidadFirma",  verbose_name=u'responsabilidad firma', on_delete=models.CASCADE)
    orden = models.IntegerField(verbose_name=u"Orden")

    def __str__(self):
        return f"{self.responsabilidadfirma}"

    def en_uso(self):
        return self.actapagointegrantesfirma_set.filter(status=True).exists()
    class Meta:
        verbose_name = u"Orden Firma acta pago"
        verbose_name_plural = u"Orden acta pago"
        ordering = ['-id']



class SecuenciaActaPagosPosgrado(ModeloBase):
    anioejercicio = models.ForeignKey("sagest.AnioEjercicio", verbose_name=u'Año ejercicio', on_delete=models.CASCADE, blank=True, null=True)
    secuencia = models.IntegerField(verbose_name=u'Secuencia', default=0, blank=True, null=True)

    def __str__(self):
        return u'%s-%s' % (self.secuencia, self.anioejercicio)

    class Meta:
        verbose_name = u"SecuenciaActaPagosPosgrado"
        verbose_name_plural = u"SecuenciaActaPagosPosgrado"
        ordering = ['-id']

    def save(self, *args, **kwargs):
        from sagest.models import AnioEjercicio
        hoy = datetime.now().date()
        aModel = AnioEjercicio.objects.filter(anioejercicio=hoy.year, status=True).first()
        self.anioejercicio = AnioEjercicio.objects.create(anioejercicio=hoy.year) if not aModel else aModel
        # Check if the instance has a primary key (id) assigned
        if self.pk is None:
            # This is an add operation
            numeracion = 1 + null_to_decimal(SecuenciaActaPagosPosgrado.objects.filter(anioejercicio=self.anioejercicio,status=True).aggregate(valor=Max('secuencia'))['valor'])
        else:
            # This is an edit operation
            numeracion = self.secuencia

        self.secuencia = numeracion
        super(SecuenciaActaPagosPosgrado, self).save(*args, **kwargs)

    def set_secuencia(self):
        return self.secuencia

    def get_secuencia_anio(self):
        return f'{self.set_secuencia()}-{self.anioejercicio}'

    def get_anio_secuencia(self):
        return f'{self.anioejercicio}-{self.set_secuencia()}'

ESTADO_ACTA_PAGO = (
    (1, 'PENDIENTE'),
    (2, 'POR LEGALIZAR'),
    (3, 'LEGALIZADA'),
    (4, 'ENVIADA VIP'),
    (5, 'ENVIADA EPUNEMI')
)
class ActaPagoPosgrado(ModeloBase):
    fechaemision = models.DateField(verbose_name=u"Fecha Emisión")
    objetivo = models.TextField(blank=True, null=True, verbose_name="Objeto")
    titulo = models.TextField(blank=True, null=True, verbose_name="Titulo")
    solicitadopor = models.ForeignKey("sga.persona", blank=True, null=True, verbose_name=u'Solicitado por', related_name='+', on_delete=models.CASCADE)
    para = models.ForeignKey("sga.persona", blank=True, null=True, verbose_name=u'Para', on_delete=models.CASCADE)
    estado = models.IntegerField(choices=ESTADO_ACTA_PAGO, default=1, verbose_name=u'estado acta pago')
    secuenciadocumento = models.ForeignKey(SecuenciaActaPagosPosgrado, verbose_name='Secuencia', on_delete=models.CASCADE, blank=True, null=True)
    codigo = models.TextField(default='', verbose_name=u'Código', blank=True, null=True)
    archivo = models.FileField(upload_to='documentospagoposgrado/actapago/%Y', blank=True, null=True,verbose_name=u'Archivo')
    archivo_memo = models.FileField(upload_to='documentospagoposgrado/memo/%Y', blank=True, null=True,verbose_name=u'Archivo memo')
    archivo_check_list = models.FileField(upload_to='documentospagoposgrado/chek_list/%Y', blank=True, null=True,verbose_name=u'Archivo check list')
    codigomemo = models.TextField(default='', verbose_name=u'Código memo', blank=True, null=True)
    marcojuridico = models.CharField(default='', max_length=120000, verbose_name=u"Marco juridico referencial")
    cuerpocontenido = models.CharField(default='', max_length=120000, verbose_name=u"Cuerpo contenido")
    conclusiones = models.CharField(default='', max_length=120000, verbose_name=u"Conclusiones")
    detallememoposgrado = models.CharField(default='', max_length=120000, verbose_name=u"detallememoposgrado")
    recomendaciones = models.CharField(default='', max_length=120000, verbose_name=u"Recomendaciones")
    archivo_memo_vice = models.FileField(upload_to='documentospagoposgrado/memovice/%Y', blank=True, null=True,verbose_name=u'Archivo memovice')

    class Meta:
        verbose_name = u" ActaPagoPosgrado"
        verbose_name_plural = u"ActaPagoPosgrado"
        ordering = ['-id']

    def __str__(self):
        return u"%s" % self.solicitadopor

    def todos_los_del_acta_tienen_habilitado_subir_factura(self):
        try:
            tienen_habilitado =True
            for detalle in self.get_detalle_solicitudes():
                if  detalle.solicitudpago.puede_subir_factura == False:
                    tienen_habilitado = False
                    break
            return tienen_habilitado
        except Exception as ex:
            return False

    def get_requisitos_solicitados_configurados_administrativos(self):
        requisitos = None
        eGrupoRequisitoPago = GrupoRequisitoPago.objects.filter(status=True,activo=True,tipogrupo=1)
        if eGrupoRequisitoPago.exists():
            requisitos = eGrupoRequisitoPago.first().get_requisitos()
        return requisitos

    def get_requisitos_solicitados_configurados_administrativos_tics(self):
        requisitos = None
        eGrupoRequisitoPago = GrupoRequisitoPago.objects.filter(status=True,activo=True,tipogrupo=1)
        if eGrupoRequisitoPago.exists():
            requisitos = eGrupoRequisitoPago.first().get_requisitos().exclude(requisitopagodip_id__in = [19,20])
        return requisitos

    def convertir_fecha_a_fecha_letra(self,fecha):
        nombre_mes = lambda x: \
        ["Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio", "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre",
         "Diciembre"][int(x) - 1]
        month, day = "%02d" % fecha.month, "%02d" % fecha.day
        mes = "%s" % nombre_mes(int(fecha.strftime("%m")))
        fecha_letra = f"{day} de {mes.lower()} de {fecha.year}"
        return fecha_letra

    def get_mes_fecha(self,fecha):
        nombre_mes = lambda x: \
        ["Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio", "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre",
         "Diciembre"][int(x) - 1]
        month, day = "%02d" % fecha.month, "%02d" % fecha.day
        mes = "%s" % nombre_mes(int(fecha.strftime("%m")))
        return mes

    def acta_pago_firmado_por_todos(self):
        return True if self.get_cantidad_de_integrantes_que_han_firmado() == self.get_integrantes_firman().count() else False

    def get_anio_ejercicio(self):
        from sagest.models import  AnioEjercicio
        hoy = datetime.now().date()
        if AnioEjercicio.objects.values('id').filter(anioejercicio=hoy.year, status=True).exists():
            anio = AnioEjercicio.objects.filter(anioejercicio=hoy.year, status=True).first()
        else:
            anio = AnioEjercicio(anioejercicio=hoy.year)
            anio.save()

        return anio

    def download_link(self):
        return self.archivo.url if self.archivo else "#"

    def download_link_memo(self):
        return self.archivo_memo.url if self.archivo_memo else "#"

    def download_link_memovice(self):
        return self.archivo_memo_vice.url if self.archivo_memo_vice else "#"

    def download_link_check(self):
        return self.archivo_check_list.url if self.archivo_check_list else "#"

    def set_secuencia_documento(self):
        try:
            anio = self.get_anio_ejercicio()
            numeracion = SecuenciaActaPagosPosgrado.objects.filter(status=True, anioejercicio=anio).count() + 1
            if not SecuenciaActaPagosPosgrado.objects.values('id').filter(status=True, anioejercicio=anio, secuencia=numeracion).exists():
                sdi = SecuenciaActaPagosPosgrado(anioejercicio=anio, secuencia=numeracion)
                sdi.save()
                self.secuenciadocumento = sdi
                self.save()

        except Exception as ex:
            return ''

    def eliminar_ultimasecuencia(self):
        try:
            secuenca_documento = self.secuenciadocumento
            eSecuenciaActaPagosPosgrado = SecuenciaActaPagosPosgrado.objects.filter(status=True).order_by('-id').first()
            if eSecuenciaActaPagosPosgrado == secuenca_documento:
                eSecuenciaActaPagosPosgrado.secuencia= secuenca_documento.secuencia - 1
                eSecuenciaActaPagosPosgrado.save()
        except Exception as ex:
            return ''

    def get_codigo_secuencia_acta_pago(self):
        try:
            codigodocumento = ''
            persona = self.get_persona_elabora()
            abreviaturanombre = ''
            for c in persona.nombre_completo().split(' '):
                abreviaturanombre += c[0] if c.__len__() else ''
            if not self.secuenciadocumento:
                self.set_secuencia_documento()
            codigo = self.secuenciadocumento.secuencia
            codigodocumento = "SGA-ACPP-POS-%s-%s-%s" % ( abreviaturanombre, "%03d" % codigo, self.secuenciadocumento.anioejercicio)
            codigodocumento_memo = "SGA-UNEMI-VICEINVYPOSG-%s-%s-MEM" % (self.secuenciadocumento.anioejercicio,"%03d" % codigo)
            return codigodocumento,codigodocumento_memo
        except Exception as ex:
             return ''

    def get_codigo_secuencia_check_list_pago(self):
        try:
            codigodocumento = ''
            persona = self.get_persona_elabora()
            abreviaturanombre = ''
            for c in persona.nombre_completo().split(' '):
                abreviaturanombre += c[0] if c.__len__() else ''
            if not self.secuenciadocumento:
                self.set_secuencia_documento()
            codigo = self.secuenciadocumento.secuencia
            codigodocumento = "SGA-CHECK-LIST-POSGRADO-%s-%s-%s" % ( abreviaturanombre, "%03d" % codigo, self.secuenciadocumento.anioejercicio)
            return codigodocumento
        except Exception as ex:
             return ''

    def acta_firmado_por_todos(self):
        return True if self.get_cantidad_de_integrantes_que_han_firmado() == self.get_integrantes_firman().count() else False

    def acta_pago_pendiente(self):
        return True if self.estado == 1 else False

    def acta_pago_por_legalizar(self):
        return True if self.estado == 2 else False

    def acta_pago_legalizado(self):
        return True if self.estado == 3 else False

    def acta_pago_enviado_vip(self):
        return True if self.estado == 4 else False

    def acta_pago_enviado_epunemi(self):
        return True if self.estado == 5 else False

    def get_integrantes_firman(self):
        return self.actapagointegrantesfirma_set.filter(status=True).order_by("ordenfirmaactapago__orden")

    def get_cantidad_de_integrantes_que_han_firmado(self):
        return self.actapagointegrantesfirma_set.filter(status=True,firmo=True).count()

    def get_debe_firmar(self):
        eActaPagoIntegranteFirma  = self.get_integrantes_firman()
        for integrante in eActaPagoIntegranteFirma:
            if not integrante.firmo:
                return integrante
        return None

    def get_integrante(self, persona):
        integrante = self.get_integrantes_firman().filter(persona=persona, status=True).first()
        return integrante if integrante else None

    def actualizar_todos_los_integrantes_a_firmado_completo(self,request):
        try:
            for integrante in self.get_integrantes_firman():
                integrante.firmo =True
                integrante.save(request)
        except Exception as ex:
            pass

    def existen_acta_pago_que_deba_firmar(self,persona):
        try:
            return ActaPagoIntegrantesFirma.objects.filter(status = True,persona = persona).exists()
        except Exception as ex:
            return False

    def puede_firmar_integrante_segun_orden(self,persona):
        integrante_logeado = self.get_integrante(persona)
        debe_firmar = self.get_debe_firmar()
        if not debe_firmar:
            return False, f"No existen integrantes que tengan que firmar."
        if integrante_logeado:
            if not debe_firmar.firmo:
                if integrante_logeado.pk == self.get_debe_firmar().pk:
                    return True , 'Es su turno de firmar'
                else:
                    return False, f"El integrante que debe firmar es: {self.get_debe_firmar()}"
        else:
            return False, f"{persona}, No se encuentra configurado para firmar acta de pago"

    def guardar_historial_acta_pago(self,request,persona,observacion,archivo):
        try:
            eHistorialActaPago = HistorialActaPago(
                actapagoposgrado=self,
                persona = persona,
                observacion = observacion,
                archivo = archivo
            )
            eHistorialActaPago.save(request)
        except Exception as ex:
            pass

    def guardar_integrantes_firman(self,persona,request):
        try:
            from sga.models import Persona
            hoy = datetime.now().date()
            #----------------------------------------ELABORADO POR
            eActaPagoIntegrantesFirma = ActaPagoIntegrantesFirma(
                actapagoposgrado=self,
                ordenfirmaactapago_id=1,
                persona=persona,
            )
            eActaPagoIntegrantesFirma.save(request)
            if  persona.pk.__str__() in variable_valor('ANALISTAS_PAGO_DEPARTAMENTO_TIC'): # si no es la analista revisora de tivs
                # ----------------------------------------------------------------------- validado y APROBADO POR
                ePersonaDirectorTics = Persona.objects.get(pk=variable_valor('DIRECTORA_TICS'))  # KERLY PALACIOS DIRECTORA DE TICS
                eActaPagoIntegrantesFirma = ActaPagoIntegrantesFirma(
                    actapagoposgrado=self,
                    ordenfirmaactapago_id=3,
                    persona=ePersonaDirectorTics,
                )
                eActaPagoIntegrantesFirma.save(request)
            else:
                # --------------------------------------------------------------------- validado por
                ePersonaExperta = Persona.objects.get(pk=variable_valor('ID_EXPERTO_GESTION_POSGRADO'))  # diana macias

                eActaPagoIntegrantesFirma = ActaPagoIntegrantesFirma(
                    actapagoposgrado=self,
                    ordenfirmaactapago_id=2,
                    persona=ePersonaExperta,
                )
                eActaPagoIntegrantesFirma.save(request)
                # ----------------------------------------------------------------------- APROBADO POR
                ePersonaDirector = ConfiguracionActaPago.objects.filter(status=True).first().para  # espinoza solis

                eActaPagoIntegrantesFirma = ActaPagoIntegrantesFirma(
                    actapagoposgrado=self,
                    ordenfirmaactapago_id=4,
                    persona=ePersonaDirector,
                )
                eActaPagoIntegrantesFirma.save(request)
                # ---------------------------------------------

        except Exception as ex:
            pass

    def get_historial_acta_pago(self):
        return self.historialactapago_set.filter(status=True).order_by('id')

    def actualizar_estado_del_acta_pago(self,request):
        if self.estado == 1:  # pendientes
            self.estado = 2  # firmado pasa a por legalizar
            self.save(request)

        if self.acta_pago_firmado_por_todos():
            self.estado = 3  # paso a legalizado
            self.save(request)

    def get_estado_acta_pago(self):
        display = f'{self.get_estado_display()}'
        if self.estado == 1:
            display = f'<span  title="Estado acta pago" style="font-size: 11px" class=" badge bg-light-warning text-dark-warning">{self.get_estado_display()}</span>'
        if self.estado == 2:
            display = f'<span  title="Estado acta pago" style="font-size: 11px" class=" badge bg-light-primary text-dark-primary">{self.get_estado_display()}</span>'
        if self.estado == 3:
            display = f'<span  title="Estado acta pago" style="font-size: 11px" class=" badge bg-light-success text-dark-success">{self.get_estado_display()}</span>'

        if self.estado == 4:
            display = f'<span  title="Estado acta pago" style="font-size: 11px" class=" badge badge-primary">{self.get_estado_display()}</span>'
        if self.estado == 5:
            display = f'<span  title="Estado acta pago" style="font-size: 11px" class=" badge badge-blue">{self.get_estado_display()}</span>'

        return display

    def get_persona_elabora(self):
        integrante = self.actapagointegrantesfirma_set.filter(status=True,ordenfirmaactapago__responsabilidadfirma_id = 1)
        return integrante.first().persona if integrante.exists() else None

    def get_integrantefirma_elabora(self):
        integrante = self.actapagointegrantesfirma_set.filter(status=True,ordenfirmaactapago__responsabilidadfirma_id = 1)
        return integrante.first() if integrante.exists() else None

    def get_persona_valida_experta(self):
        integrante = self.actapagointegrantesfirma_set.filter(status=True,ordenfirmaactapago__responsabilidadfirma_id = 2)
        return integrante.first().persona if integrante.exists() else None

    def get_persona_valida_aprueba(self):
        integrante = self.actapagointegrantesfirma_set.filter(status=True,ordenfirmaactapago__responsabilidadfirma_id=4)
        return integrante.first().persona if integrante.exists() else None

    def get_persona_aprueba_director(self):
        integrante = self.actapagointegrantesfirma_set.filter(status=True,ordenfirmaactapago__responsabilidadfirma_id = 3)
        return integrante.first().persona if integrante.exists() else None

    def persona_es_quien_firma_acta_pago_memo(self,pk):
        return True if self.actapagointegrantesfirma_set.filter(status=True,pk = pk,ordenfirmaactapago__responsabilidadfirma_id__in = [3,4]).exists() else False

    def persona_es_quien_firma_acta_pago_check_list(self,pk):
            return True if self.actapagointegrantesfirma_set.filter(status=True,pk = pk,ordenfirmaactapago__responsabilidadfirma_id__in = [1]).exists() else False

    def get_str_copia_nombre(self,persona):
        str_nombre = ''
        if persona:
            abr = 'Sr.' if persona.sexo.id == 2 else 'Sra.'
            nombre = persona.nombre_titulos3y4()
            str_nombre =f'{abr} {nombre}'

        return f'{str_nombre}'

    def get_str_copia_cargo(self,persona):
        str_cargo = ''
        if persona:
            str_cargo = persona.cargo_persona().denominacionpuesto.descripcion
        return f'{str_cargo}'

    def get_nombre_copia_experta(self):
        if self.get_persona_valida_experta():
            return self.get_str_copia_nombre(self.get_persona_valida_experta()) if  self.get_str_copia_nombre(self.get_persona_valida_experta()) else ''
        else:
            return self.get_str_copia_nombre(self.get_persona_valida_aprueba()) if  self.get_str_copia_nombre(self.get_persona_valida_aprueba()) else ''

    def get_abreviaturas_copia_elabora_analista_validado_experta(self):
        persona_elabora = self.get_persona_elabora()
        persona_valida= self.get_persona_valida_experta() if self.get_persona_valida_experta() else self.get_persona_valida_aprueba()
        abreviaturanombreelabora = ''
        abreviaturanombrevalida = ''
        abreviaturas = ""

        if persona_elabora:
            persona_elabora = f"{persona_elabora.primerNombre()} {persona_elabora.apellido1}"
            for c in persona_elabora.split(' '):
                abreviaturanombreelabora += c[0] if c.__len__() else ''

        if persona_valida:
            persona_valida = f"{persona_valida.primerNombre()} {persona_valida.apellido1}"
            for c in persona_valida.split(' '):
                abreviaturanombrevalida += c[0] if c.__len__() else ''

        abreviaturas = f"{abreviaturanombreelabora}/{abreviaturanombrevalida}"
        return abreviaturas

    def get_abreviaturas_copia_elabora_analista(self):
        persona_elabora = self.get_persona_elabora()
        persona_valida= self.get_persona_valida_experta() if self.get_persona_valida_experta() else self.get_persona_valida_aprueba()
        abreviaturanombreelabora = ''
        abreviaturanombrevalida = ''
        abreviaturas = ""

        if persona_elabora:
            persona_elabora = f"{persona_elabora.primerNombre()} {persona_elabora.apellido1}"
            for c in persona_elabora.split(' '):
                abreviaturanombreelabora += c[0] if c.__len__() else ''

        abreviaturas = f"{abreviaturanombreelabora}"
        return abreviaturas

    def get_cargo_copia_experta(self):
        if self.get_persona_valida_experta():
            return self.get_str_copia_cargo(self.get_persona_valida_experta()) if self.get_str_copia_nombre(self.get_persona_valida_experta()) else ''
        else:
            return self.get_str_copia_cargo(self.get_persona_valida_aprueba()) if self.get_str_copia_cargo( self.get_persona_valida_aprueba()) else ''

    def get_nombre_copia_analista(self):
        return self.get_str_copia_nombre(self.get_persona_elabora()) if self.get_str_copia_nombre(self.get_persona_elabora()) else ''

    def get_cargo_copia_analista(self):
        return self.get_str_copia_cargo(self.get_persona_elabora()) if self.get_str_copia_cargo(self.get_persona_elabora()) else ''

    def guardar_detalle_acta_pago(self,eSolicitudPagos,request):
        try:
            for solicitudpago in eSolicitudPagos:
                total_pago_subtotal,total_pago_iva,total_a_pagar_rmu,dias_transcurridos = solicitudpago.calcular_valor_a_pagar_pago()
                eDetalleActaPago = DetalleActaPago(
                    actapagoposgrado=self,
                    solicitudpago=solicitudpago,
                    rmu=total_pago_subtotal,
                    valoriva=total_pago_iva,
                    valortotal=total_a_pagar_rmu
                )
                eDetalleActaPago.save(request)
            mensaje = "detalle solicitud de pago  guardado correctamente"
            return True,mensaje
        except Exception as ex:
            mensaje = f"{ex.__str__()}"
            return False,mensaje

    def get_detalle_solicitudes(self):
        return self.detalleactapago_set.filter(status=True,solicitudpago__status=True)

    def get_cantidad_detalle_solicitudes(self):
        return self.detalleactapago_set.filter(status=True,solicitudpago__status=True).count()

    def get_texto_certificaciones_presupuestarias_numero(self):
        try:
            mensaje =''
            for detalle in self.get_detalle_solicitudes().values('solicitudpago__contrato__certificacion__codigo').order_by('solicitudpago__contrato__certificacion__codigo').distinct('solicitudpago__contrato__certificacion__codigo'):
                mensaje += f"No. {detalle['solicitudpago__contrato__certificacion__codigo']}, "
            mensaje = mensaje[:-2]
            mensaje += ''
            return mensaje
        except Exception as ex:
            return ''

    def get_total_a_pagar_detalle_solicitudes(self):
        from django.db.models import Q, Sum
        return self.detalleactapago_set.filter(status=True,solicitudpago__status=True).aggregate(total = Sum('valortotal'))

    def get_cargos_sin_repetir(self):
        try:
            cargos = self.get_detalle_solicitudes().values('solicitudpago__contrato__cargo__nombre').distinct().order_by('solicitudpago__contrato__cargo')
            return cargos
        except Exception as ex:
            pass

    def get_detalle_contratos_solicitud_pago(self):
        try:
            solicitudes_contrato=[]
            for detalleactapago in self.get_detalle_solicitudes():
                eProfesional = detalleactapago.solicitudpago.contrato.persona
                eCargo = detalleactapago.solicitudpago.contrato.cargo
                eCodigocontrato = detalleactapago.solicitudpago.contrato.codigocontrato
                numero_partida = detalleactapago.solicitudpago.contrato.certificacion.codigo
                fecha_inicio_fin = f"""
                    <p style="text-align:center"><span style="font-size:8pt"><span style="font-family:&quot;Tahoma&quot;,sans-serif"><span style="font-family:&quot;Calibri&quot;,sans-serif"><span style="color:black">{detalleactapago.solicitudpago.fechainicio}</span></span></span></span></p>
                    <p style="text-align:center"><span style="font-size:8pt"><span style="font-family:&quot;Tahoma&quot;,sans-serif"><span style="font-family:&quot;Calibri&quot;,sans-serif"><span style="color:black">{detalleactapago.solicitudpago.fechaifin}</span></span></span></span></p>
                """
                rmu = detalleactapago.solicitudpago.contrato.rmu
                iva = detalleactapago.valoriva
                total_pagar = detalleactapago.valortotal
                solicitudes_contrato.append({
                    'eProfesional' : f"{eProfesional}",
                    'cargo' : f"{eCargo}",
                    'eCodigocontrato' : f"{eCodigocontrato}",
                    'numero_partida' : f"{numero_partida}",
                    'fecha_inicio_fin' : f"{fecha_inicio_fin}",
                    'rmu' : f"{rmu}",
                    'iva' : f"{iva}",
                    'total_pagar' : f"{total_pagar}",
                })
            return solicitudes_contrato
        except Exception as ex:
            return ''

    def get_texto_objetivo_acta_pago(self):
        try:
            eConfiguracionActaPago = ConfiguracionActaPago.objects.filter(status=True)
            mensaje = eConfiguracionActaPago.first().objetivo if eConfiguracionActaPago.exists() else ''
            return mensaje
        except Exception as ex:
            return ''

    def get_texto_marco_juridico_acta_pago(self):
        try:
            eConfiguracionActaPago = ConfiguracionActaPago.objects.filter(status=True)
            mensaje = eConfiguracionActaPago.first().marcojuridicoreferencial if eConfiguracionActaPago.exists() else ''
            return mensaje
        except Exception as ex:
            return ''

    def get_texto_titulo_acta_pago(self):
        try:
            eConfiguracionActaPago = ConfiguracionActaPago.objects.filter(status=True)
            mensaje = eConfiguracionActaPago.first().titulo if eConfiguracionActaPago.exists() else ''
            return mensaje
        except Exception as ex:
            return ''

    def get_texto_conclusiones_acta_pago(self):
        try:
            eConfiguracionActaPago = ConfiguracionActaPago.objects.filter(status=True)
            mensaje = eConfiguracionActaPago.first().conclusiones if eConfiguracionActaPago.exists() else ''
            return mensaje
        except Exception as ex:
            return ''

    def get_texto_recomendaciones_acta_pago(self):
        try:
            eConfiguracionActaPago = ConfiguracionActaPago.objects.filter(status=True)
            mensaje = eConfiguracionActaPago.first().recomendaciones if eConfiguracionActaPago.exists() else ''
            return mensaje
        except Exception as ex:
            return ''

    def get_texto_actividad_parte_1(self):
        try:
            mensaje = f'<p style="text-align:justify"><span style="font-size:8pt"><span style="font-family:&quot;Tahoma&quot;,sans-serif"><span style="font-family:&quot;Calibri&quot;,sans-serif">Con la finalidad de continuar con el pago de honorarios profesionales a favor de los '
            for persona_contratada in self.get_cargos_sin_repetir():
                mensaje += f"<strong> {persona_contratada}</strong>"
            mensaje += f', observando la propiedad, legalidad y veracidad de los documentos de respaldos que motivan la realizaci&oacute;n del pago es importante indicar en este punto:</span></span></span></p>'
            mensaje += f'<ol>'
            mensaje += f'<li style="text-align:justify"><span style="font-size:8pt"><span style="font-family:&quot;Tahoma&quot;,sans-serif"><strong><span style="font-family:&quot;Calibri&quot;,sans-serif"><span style="color:black">Tipo de pago a realizar:</span></span></strong><span style="font-family:&quot;Calibri&quot;,sans-serif"><span style="color:black"> Pago por contrato civil de honorarios profesionales en calidad de <strong>&ldquo;</strong></span></span>'
            for persona_contratada in self.get_cargos_sin_repetir():
                mensaje += f'<strong><span style="font-family:&quot;Calibri&quot;,sans-serif">{persona_contratada}, <span style="color:black">&rdquo; </span></span></strong>'
            mensaje += f'<span style="font-family:&quot;Calibri&quot;,sans-serif"><span style="color:black">correspondiente al mes de diciembre 2023.</span></span></span></span></li>'
            mensaje += f'</ol>'
            mensaje += f'<p>&nbsp;</p>'
            return mensaje
        except Exception as ex:
            return ''

    def get_texto_actividad_parte_2_tabla_pagos(self):
        try:
            mensaje = '<table cellspacing="0" class="Table" style="border-collapse:collapse; width:561px">'
            mensaje += '<tbody>'
            #encabezado de la tabla
            mensaje += f"""<tr>
                                            <td style="background-color:#eeece1; border-bottom:1px solid black; border-left:1px solid black; border-right:1px solid black; border-top:1px solid black; height:14px; width:34px">
                                            <p style="text-align:center"><span style="font-size:8pt"><span style="font-family:&quot;Tahoma&quot;,sans-serif"><strong><span style="font-family:&quot;Calibri&quot;,sans-serif"><span style="color:black">No.</span></span></strong></span></span></p>
                                            </td>
                                            <td style="background-color:#eeece1; border-bottom:1px solid black; border-left:none; border-right:1px solid black; border-top:1px solid black; height:14px; width:99px">
                                            <p style="text-align:center"><span style="font-size:8pt"><span style="font-family:&quot;Tahoma&quot;,sans-serif"><strong><span style="font-family:&quot;Calibri&quot;,sans-serif"><span style="color:black">PROFESIONAL</span></span></strong></span></span></p>
                                            </td>
                                            <td style="background-color:#eeece1; border-bottom:1px solid black; border-left:none; border-right:1px solid black; border-top:1px solid black; height:14px; width:78px">
                                            <p style="text-align:center"><span style="font-size:8pt"><span style="font-family:&quot;Tahoma&quot;,sans-serif"><strong><span style="font-family:&quot;Calibri&quot;,sans-serif"><span style="color:black">ACTIVIDAD</span></span></strong></span></span></p>
                                            </td>
                                            <td style="background-color:#eeece1; border-bottom:1px solid black; border-left:none; border-right:1px solid black; border-top:1px solid black; height:14px; width:69px">
                                            <p style="text-align:center"><span style="font-size:8pt"><span style="font-family:&quot;Tahoma&quot;,sans-serif"><strong><span style="font-family:&quot;Calibri&quot;,sans-serif"><span style="color:black">No. CONTRATO</span></span></strong></span></span></p>
                                            </td>
                                            <td style="background-color:#eeece1; border-bottom:1px solid black; border-left:none; border-right:1px solid black; border-top:1px solid black; height:14px; width:49px">
                                            <p style="text-align:center"><span style="font-size:8pt"><span style="font-family:&quot;Tahoma&quot;,sans-serif"><strong><span style="font-family:&quot;Calibri&quot;,sans-serif"><span style="color:black">PARTIDA</span></span></strong></span></span></p>
                                            </td>
                                            <td style="background-color:#eeece1; border-bottom:1px solid black; border-left:none; border-right:1px solid black; border-top:1px solid black; height:14px; width:63px">
                                            <p style="text-align:center"><span style="font-size:8pt"><span style="font-family:&quot;Tahoma&quot;,sans-serif"><strong><span style="font-family:&quot;Calibri&quot;,sans-serif"><span style="color:black">FECHA</span></span></strong></span></span></p>
                                            </td>
                                            <td style="background-color:#eeece1; border-bottom:1px solid black; border-left:none; border-right:1px solid black; border-top:1px solid black; height:14px; width:52px">
                                            <p style="text-align:center"><span style="font-size:8pt"><span style="font-family:&quot;Tahoma&quot;,sans-serif"><strong><span style="font-family:&quot;Calibri&quot;,sans-serif"><span style="color:black">RMU</span></span></strong></span></span></p>
                                            </td>
                                            <td style="background-color:#eeece1; border-bottom:1px solid black; border-left:none; border-right:1px solid black; border-top:1px solid black; height:14px; width:52px">
                                            <p style="text-align:center"><span style="font-size:8pt"><span style="font-family:&quot;Tahoma&quot;,sans-serif"><strong><span style="font-family:&quot;Calibri&quot;,sans-serif"><span style="color:black">IVA</span></span></strong></span></span></p>
                                            </td>
                                            <td style="background-color:#eeece1; border-bottom:1px solid black; border-left:none; border-right:1px solid black; border-top:1px solid black; height:14px; width:64px">
                                            <p style="text-align:center"><span style="font-size:8pt"><span style="font-family:&quot;Tahoma&quot;,sans-serif"><strong><span style="font-family:&quot;Calibri&quot;,sans-serif"><span style="color:black">TOTAL A PAGAR </span></span></strong></span></span></p>
                                            </td>
                                        </tr>"""
            contador = 0
            total_acta_pago = 0
            for persona_contratada in self.get_detalle_contratos_solicitud_pago():
                contador += 1
                total_acta_pago += float(persona_contratada['total_pagar'])
                # filas de la tabla
                mensaje += f"<tr>"
                mensaje += f"""
                            <td style="border-bottom:1px solid black; border-left:1px solid black; border-right:1px solid black; border-top:none; height:45px; width:34px">
                               <p style="text-align:center"><span style="font-size:8pt"><span style="font-family:&quot;Tahoma&quot;,sans-serif"><span style="font-family:&quot;Calibri&quot;,sans-serif"><span style="color:black">{contador}</span></span></span></span></p>
                            </td>
                            """
                mensaje += f"""
                                <td style="border-bottom:1px solid black; border-left:none; border-right:1px solid black; border-top:none; height:45px; width:99px">
                                <p style="text-align:center"><span style="font-size:8pt"><span style="font-family:&quot;Tahoma&quot;,sans-serif"><span style="font-family:&quot;Calibri&quot;,sans-serif"><span style="color:black">{persona_contratada['eProfesional']}</span></span></span></span></p>
                                </td>
                            """
                mensaje += f"""
                            <td style="border-bottom:1px solid black; border-left:none; border-right:1px solid black; border-top:none; height:45px; width:78px">
                            <p style="text-align:center"><span style="font-size:8pt"><span style="font-family:&quot;Tahoma&quot;,sans-serif"><span style="font-family:&quot;Calibri&quot;,sans-serif"><span style="color:black">{persona_contratada['cargo']}</span></span></span></span></p>
                            </td>
                            """
                mensaje += f"""
                            <td style="border-bottom:1px solid black; border-left:none; border-right:1px solid black; border-top:none; height:45px; width:69px">
                            <p style="text-align:center"><span style="font-size:8pt"><span style="font-family:&quot;Tahoma&quot;,sans-serif"><span style="font-family:&quot;Calibri&quot;,sans-serif"><span style="color:black">{persona_contratada['eCodigocontrato']}</span></span></span></span></p>
                            </td>
                           """
                mensaje += f"""
                            <td style="border-bottom:1px solid black; border-left:none; border-right:1px solid black; border-top:none; height:45px; width:49px">
                            <p style="text-align:center"><span style="font-size:8pt"><span style="font-family:&quot;Tahoma&quot;,sans-serif"><span style="font-family:&quot;Calibri&quot;,sans-serif"><span style="color:black">{persona_contratada['numero_partida']}</span></span></span></span></p>
                            </td>
                           """
                mensaje += f"""
                            <td style="border-bottom:1px solid black; border-left:none; border-right:1px solid black; border-top:none; height:45px; width:63px">{persona_contratada['fecha_inicio_fin']}</td>
                           """
                mensaje += f"""
                            <td style="border-bottom:1px solid black; border-left:none; border-right:1px solid black; border-top:none; height:45px; width:52px">
                            <p style="text-align:center"><span style="font-size:8pt"><span style="font-family:&quot;Tahoma&quot;,sans-serif"><span style="font-family:&quot;Calibri&quot;,sans-serif"><span style="color:black">${persona_contratada['rmu']}</span></span></span></span></p>
                            </td>
                           """
                mensaje += f"""
                            <td style="border-bottom:1px solid black; border-left:none; border-right:1px solid black; border-top:none; height:45px; width:52px">
                            <p style="text-align:center"><span style="font-size:8pt"><span style="font-family:&quot;Tahoma&quot;,sans-serif"><span style="font-family:&quot;Calibri&quot;,sans-serif"><span style="color:black">${persona_contratada['iva']}</span></span></span></span></p>
                            </td>
                           """
                mensaje += f"""
                             <td style="border-bottom:1px solid black; border-left:none; border-right:1px solid black; border-top:none; height:45px; width:64px">
                            <p style="text-align:center"><span style="font-size:8pt"><span style="font-family:&quot;Tahoma&quot;,sans-serif"><span style="font-family:&quot;Calibri&quot;,sans-serif"><span style="color:black">${persona_contratada['total_pagar']}</span></span></span></span></p>
                            </td>
                           """
                mensaje += '</tr>'
            #pie de la tabla
            mensaje += f"""
            <tr>
                <td colspan="8" style="border-bottom:1px solid black; border-left:1px solid black; border-right:1px solid black; border-top:none; height:26px; width:496px">
                <p style="text-align:center"><span style="font-size:8pt"><span style="font-family:&quot;Tahoma&quot;,sans-serif"><strong><span style="font-family:&quot;Calibri&quot;,sans-serif"><span style="color:black">TOTAL</span></span></strong></span></span></p>
                </td>
                <td style="border-bottom:1px solid black; border-left:none; border-right:1px solid black; border-top:none; height:26px; width:64px">
                <p style="text-align:center"><span style="font-size:8pt"><span style="font-family:&quot;Tahoma&quot;,sans-serif"><strong><span style="font-family:&quot;Calibri&quot;,sans-serif"><span style="color:black">${total_acta_pago}</span></span></strong></span></span></p>
                </td>
            </tr>
            
            """
            mensaje += '</tbody>'
            mensaje += '</table>'
            return mensaje
        except Exception as ex:
            return ''

    def get_texto_actividad_parte_3_final_del_cuerpo_parte_1(self):
        try:
            mensaje = '<ol><li><strong><span style="font-size:11px"><span style="font-family:&quot;Tahoma&quot;,sans-serif"><span style="font-family:&quot;Calibri&quot;,sans-serif"><span style="color:black">Documentaci&oacute;n de soporte para el pago respectivo:</span></span></span></span></strong></li></ol>'
            mensaje += """
                        <table align="center" cellspacing="0" class="Table" style="border-collapse:collapse; border:medium; height:101px; width:513px">
                            <tbody>
                                <tr>
                                    <td style="border-bottom:1px solid black; border-left:1px solid black; border-right:1px solid black; border-top:1px solid black; height:18px; vertical-align:top">
                                    <p style="text-align:center"><span style="font-size:11px"><span style="font-family:&quot;Tahoma&quot;,sans-serif"><strong><span style="font-family:&quot;Calibri&quot;,sans-serif"><span style="color:black">Detalle de Contrato</span></span></strong></span></span></p>
                                    </td>
                                    <td style="border-bottom:1px solid black; border-left:none; border-right:1px solid black; border-top:1px solid black; height:18px; vertical-align:top">
                                    <p style="text-align:center"><span style="font-size:11px"><span style="font-family:&quot;Tahoma&quot;,sans-serif"><strong><span style="font-family:&quot;Calibri&quot;,sans-serif"><span style="color:black">Documento habilitante</span></span></strong></span></span></p>
                                    </td>
                                    <td style="border-bottom:1px solid black; border-left:none; border-right:1px solid black; border-top:1px solid black; height:18px; vertical-align:top">
                                    <p style="text-align:center"><span style="font-size:11px"><span style="font-family:&quot;Tahoma&quot;,sans-serif"><strong><span style="font-family:&quot;Calibri&quot;,sans-serif"><span style="color:black">Observaci&oacute;n</span></span></strong></span></span></p>
                                    </td>
                                </tr>
                                <tr>
                                    <td style="border-bottom:1px solid black; border-left:1px solid black; border-right:1px solid black; border-top:none; height:45px">
                                    <p style="text-align:center"><span style="font-size:11px"><span style="font-family:&quot;Tahoma&quot;,sans-serif"><span style="font-family:&quot;Calibri&quot;,sans-serif">Cl&aacute;usula<span style="color:black"> Sexta. - Honorarios y Forma de Pago</span></span></span></span></p>
                                    </td>
                                    <td style="border-bottom:1px solid black; border-left:none; border-right:1px solid black; border-top:none; height:45px">
                                    <p style="text-align:center"><span style="font-size:11px"><span style="font-family:&quot;Tahoma&quot;,sans-serif"><span style="font-family:&quot;Calibri&quot;,sans-serif"><span style="color:black">Informe de actividades</span></span></span></span></p>
                                    </td>
                                    <td style="border-bottom:1px solid black; border-left:none; border-right:1px solid black; border-top:none; height:45px">
                                    <p style="text-align:center"><span style="font-size:11px"><span style="font-family:&quot;Tahoma&quot;,sans-serif"><span style="font-family:&quot;Calibri&quot;,sans-serif"><span style="color:black">Cumple</span></span></span></span></p>
                                    </td>
                                </tr>
                            </tbody>
                        </table>
                    """
            mensaje += """
                    <ol start="2">
                        <li><span style="font-size:11px"><span style="font-family:&quot;Tahoma&quot;,sans-serif"><strong><span style="font-family:&quot;Calibri&quot;,sans-serif"><span style="color:black">Otra informaci&oacute;n de soporte:</span></span></strong></span></span></li>
                    </ol>            
            """
            return mensaje
        except Exception as ex:
            return ''

    def get_texto_actividad_parte_3_final_del_cuerpo_parte_2_requisitos_pago(self):
        try:
            mensaje = """
                <ol>
                    <li style="text-align:justify"><span style="font-size:11px"><span style="font-family:&quot;Tahoma&quot;,sans-serif"><span style="font-family:&quot;Calibri&quot;,sans-serif">Informe de actividades</span></span></span></li>
                    <li style="text-align:justify"><span style="font-size:11px"><span style="font-family:&quot;Tahoma&quot;,sans-serif"><span style="font-family:&quot;Calibri&quot;,sans-serif">Formato de Proveedores</span></span></span></li>
                    <li style="text-align:justify"><span style="font-size:11px"><span style="font-family:&quot;Tahoma&quot;,sans-serif"><span style="font-family:&quot;Calibri&quot;,sans-serif">Contrato legalizado</span></span></span></li>
                    <li style="text-align:justify"><span style="font-size:11px"><span style="font-family:&quot;Tahoma&quot;,sans-serif"><span style="font-family:&quot;Calibri&quot;,sans-serif">Factura electr&oacute;nica</span></span></span></li>
                    <li style="text-align:justify"><span style="font-size:11px"><span style="font-family:&quot;Tahoma&quot;,sans-serif"><span style="font-family:&quot;Calibri&quot;,sans-serif">Copia de c&eacute;dula y papeleta de votaci&oacute;n</span></span></span></li>
                    <li style="text-align:justify"><span style="font-size:11px"><span style="font-family:&quot;Tahoma&quot;,sans-serif"><span style="font-family:&quot;Calibri&quot;,sans-serif">Copia de RUC</span></span></span></li>
                    <li style="text-align:justify"><span style="font-size:11px"><span style="font-family:&quot;Tahoma&quot;,sans-serif"><span style="font-family:&quot;Calibri&quot;,sans-serif">Certificado Bancario</span></span></span></li>
                    <li style="text-align:justify"><span style="font-size:11px"><span style="font-family:&quot;Tahoma&quot;,sans-serif"><span style="font-family:&quot;Calibri&quot;,sans-serif">Partida Presupuestaria</span></span></span></li>
                    <li style="text-align:justify"><span style="font-size:11px"><span style="font-family:&quot;Calibri&quot;,sans-serif">Check list de pago</span></span></li>
                </ol>
            """
            return mensaje
        except Exception as ex:
            return ''

    def guardar_detalle_items_acta_pago_documentacion_soporte(self,request):
        try:
            eDetalleItemsActaPagoPosgrado =DetalleItemsActaPagoPosgrado(
                actapagoposgrado=self,
                detallecontrato = 'Cláusula Sexta. - Honorarios y Forma de Pago',
                documentohabilitante = 'Informe técnico de actividades',
                observacion = 'Cumple'
            )
            eDetalleItemsActaPagoPosgrado.save(request)
        except Exception as ex:
            pass

    def get_detalle_items_acta_pago_documentacion_soporte(self):
        return self.detalleitemsactapagoposgrado_set.filter(status=True)

    def generar_actualizar_data_contenido_acta_pagos(self, eSolicitudPagos, persona, request):
        try:
            guardado_correcto, mensaje = self.guardar_detalle_acta_pago(eSolicitudPagos, request)
            if guardado_correcto:
                self.guardar_integrantes_firman(persona,request)
                self.codigo, self.codigomemo = self.get_codigo_secuencia_acta_pago()
                self.objetivo = self.get_texto_objetivo_acta_pago()
                self.guardar_detalle_items_acta_pago_documentacion_soporte(request)
                self.marcojuridico = self.get_texto_marco_juridico_acta_pago()
                if persona.pk == 20570:  # guerra gaibor -encargadapagos tics
                    self.titulo = 'ACTA DE CONTROL PREVIO AL PAGO POR CONTRATO CIVIL DE SERVICIOS PROFESIONALES EPUNEMI-VICEINVPOSG'
                else:
                    self.titulo = self.get_texto_titulo_acta_pago()
                self.conclusiones = self.get_texto_conclusiones_acta_pago()
                self.recomendaciones = self.get_texto_recomendaciones_acta_pago()
                self.save(request)

            return guardado_correcto, mensaje

        except Exception as ex:
            pass

    def generar_actualizar_acta_pago_pdf(self,request):
        try:
            eActaPago = self
            data, fechaemision = {}, self.fechaemision
            hoy = datetime.now().date()
            name = unicodedata.normalize('NFD', u"actapago_%s" % (self.pk)).encode('ascii', 'ignore').decode("utf-8").lower().replace(' ', '_').replace('-', '')
            filename = generar_nombre(u"%s_" % name, f"{name}.pdf")
            filepath = u"documentospagoposgrado/documentos/%s" % hoy.year
            folder_pdf = os.path.join(SITE_STORAGE, 'media', 'documentospagoposgrado','documentos',hoy.year.__str__(),'')
            os.makedirs(os.path.join(folder_pdf), exist_ok=True)
            data['pagesize'] = 'A4'
            data['request'] = request
            data['fechaemision'] = fechaemision
            data['eActaPagoPosgrado'] = eActaPago
            CERTIFICACION_BANCARIA = 5
            FORMATO_DE_PROVEEDORES = 6
            CERTIFICACION_PRESUPUESTARIA = 15
            CHECK_LIST_DE_PAGO = 16
            data['requisitos_cantidad_hoja_1'] = lista_requisitos = [CERTIFICACION_BANCARIA, FORMATO_DE_PROVEEDORES, CERTIFICACION_PRESUPUESTARIA, CHECK_LIST_DE_PAGO]
            ruta_pdf = os.path.join(filepath, filename) if convert_html_to_pdf('adm_solicitudpago/revisionpago/docs/acta_pago_pdf.html', data, filename, folder_pdf) else None
            self.archivo = ruta_pdf
            self.save(request)
            return self.archivo if self.archivo else ''
        except Exception as ex:
            pass

    def generar_actualizar_acta_pago_pdf_tics(self,request):
        try:
            eActaPago = self
            data, fechaemision = {}, self.fechaemision
            hoy = datetime.now().date()
            name = unicodedata.normalize('NFD', u"actapago_%s" % (self.pk)).encode('ascii', 'ignore').decode("utf-8").lower().replace(' ', '_').replace('-', '')
            filename = generar_nombre(u"%s_" % name, f"{name}.pdf")
            filepath = u"documentospagoposgrado/documentos/%s" % hoy.year
            folder_pdf = os.path.join(SITE_STORAGE, 'media', 'documentospagoposgrado','documentos',hoy.year.__str__(),'')
            os.makedirs(os.path.join(folder_pdf), exist_ok=True)
            data['pagesize'] = 'A4'
            data['request'] = request
            data['fechaemision'] = fechaemision
            data['eActaPagoPosgrado'] = eActaPago
            CERTIFICACION_BANCARIA = 5
            FORMATO_DE_PROVEEDORES = 6
            CERTIFICACION_PRESUPUESTARIA = 15
            CHECK_LIST_DE_PAGO = 16
            data['requisitos_cantidad_hoja_1'] = lista_requisitos = [CERTIFICACION_BANCARIA, FORMATO_DE_PROVEEDORES, CERTIFICACION_PRESUPUESTARIA, CHECK_LIST_DE_PAGO]
            ruta_pdf = os.path.join(filepath, filename) if convert_html_to_pdf('adm_solicitudpago/revisionpago/docs/tics/acta_pago_pdf.html', data, filename, folder_pdf) else None
            self.archivo = ruta_pdf
            self.save(request)
            return self.archivo if self.archivo else ''
        except Exception as ex:
            pass

    def generar_actualizar_memo_pago_pdf(self,request):
        try:
            eActaPago = self
            data, fechaemision = {}, self.fechaemision
            hoy = datetime.now().date()
            name = unicodedata.normalize('NFD', u"memo_direccion_posgrado_%s" % (self.pk)).encode('ascii', 'ignore').decode("utf-8").lower().replace(' ', '_').replace('-', '')
            filename = generar_nombre(u"%s_" % name, f"{name}.pdf")
            filepath = u"documentospagoposgrado/documentos/%s" % hoy.year
            folder_pdf = os.path.join(SITE_STORAGE, 'media', 'documentospagoposgrado','documentos',hoy.year.__str__(),'')
            os.makedirs(os.path.join(folder_pdf), exist_ok=True)
            data['pagesize'] = 'A4'
            data['request'] = request
            data['fechaemision'] = eActaPago.convertir_fecha_a_fecha_letra(fechaemision)
            data['eActaPagoPosgrado'] = eActaPago
            ruta_pdf = os.path.join(filepath, filename) if convert_html_to_pdf('adm_solicitudpago/revisionpago/docs/memo_pago_pdf.html', data, filename, folder_pdf) else None
            self.archivo_memo = ruta_pdf
            self.save(request)
            return self.archivo if self.archivo else ''
        except Exception as ex:
            pass

    def generar_actualizar_check_list_pago_pdf(self,request):
        try:

            eActaPago = self
            data, fechaemision = {}, self.fechaemision
            hoy = datetime.now().date()
            name = unicodedata.normalize('NFD', u"check_list_pago_general_%s" % (self.pk)).encode('ascii', 'ignore').decode("utf-8").lower().replace(' ', '_').replace('-', '')
            filename = generar_nombre(u"%s_" % name, f"{name}.pdf")
            filepath = u"documentospagoposgrado/documentos/%s" % hoy.year
            folder_pdf = os.path.join(SITE_STORAGE, 'media', 'documentospagoposgrado', 'documentos', hoy.year.__str__(),'')
            os.makedirs(os.path.join(folder_pdf), exist_ok=True)
            data['pagesize'] = 'A4'
            data['request'] = request
            data['fechaemision'] = fechaemision
            data['eActaPagoPosgrado'] = eActaPago
            CERTIFICACION_BANCARIA = 5
            FORMATO_DE_PROVEEDORES = 6
            CERTIFICACION_PRESUPUESTARIA = 15
            CHECK_LIST_DE_PAGO = 16
            FACTURA = 4
            data['id_factura'] =  FACTURA
            data['CHECK_LIST_DE_PAGO'] =  CHECK_LIST_DE_PAGO
            ruta_pdf = os.path.join(filepath, filename) if convert_html_to_pdf('adm_solicitudpago/revisionpago/docs/check_list_pagos_todos_pdf.html', data, filename, folder_pdf) else None
            self.archivo_check_list= ruta_pdf
            self.save(request)
            return self.archivo_check_list if self.archivo_check_list else ''
        except Exception as ex:
            pass

    def generar_actualizar_check_list_pago_pdf_tics(self,request):
        try:

            eActaPago = self
            data, fechaemision = {}, self.fechaemision
            hoy = datetime.now().date()
            name = unicodedata.normalize('NFD', u"check_list_pago_general_%s" % (self.pk)).encode('ascii', 'ignore').decode("utf-8").lower().replace(' ', '_').replace('-', '')
            filename = generar_nombre(u"%s_" % name, f"{name}.pdf")
            filepath = u"documentospagoposgrado/documentos/%s" % hoy.year
            folder_pdf = os.path.join(SITE_STORAGE, 'media', 'documentospagoposgrado', 'documentos', hoy.year.__str__(),'')
            os.makedirs(os.path.join(folder_pdf), exist_ok=True)
            data['pagesize'] = 'A4'
            data['request'] = request
            data['fechaemision'] = fechaemision
            data['eActaPagoPosgrado'] = eActaPago
            CERTIFICACION_BANCARIA = 5
            FORMATO_DE_PROVEEDORES = 6
            CERTIFICACION_PRESUPUESTARIA = 15
            CHECK_LIST_DE_PAGO = 16
            REGISTRO_DE_IMPEDIMENTO_CARGO_PUBLICO = 19
            RELACION_DEPENDENCIA_LABORAL = 20
            FACTURA = 4
            data['id_factura'] =  FACTURA
            data['REGISTRO_DE_IMPEDIMENTO_CARGO_PUBLICO'] =  REGISTRO_DE_IMPEDIMENTO_CARGO_PUBLICO
            data['RELACION_DEPENDENCIA_LABORAL'] =  RELACION_DEPENDENCIA_LABORAL
            data['CHECK_LIST_DE_PAGO'] =  CHECK_LIST_DE_PAGO
            ruta_pdf = os.path.join(filepath, filename) if convert_html_to_pdf('adm_solicitudpago/revisionpago/docs/tics/check_list_pagos_todos_pdf.html', data, filename, folder_pdf) else None
            self.archivo_check_list= ruta_pdf
            self.save(request)
            return self.archivo_check_list if self.archivo_check_list else ''
        except Exception as ex:
            pass

    def generar_actualizar_acta_pago_documentos_pdf_segundo_plano(self,request):
        try:
            a = actualizar_acta_pago_posgrado(request, self)
            a.start()
        except Exception as ex:
            pass

    def notificar_orden_integrante_toca_firmar(self,request):
        a = notificar_persona_a_fimar_acta_pago(request,self)
        a.start()

    def notificar_subir_factura_profesionales(self,request):
        PENDIENTE_SUBIR_FACTURA=1
        ids= self.get_detalle_solicitudes().values_list('solicitudpago_id',flat=True)
        eSolicitudPago =SolicitudPago.objects.filter(pk__in=ids)
        eSolicitudPago.update(puede_subir_factura = True)
        eSolicitudPago.update(estadotramitepago = PENDIENTE_SUBIR_FACTURA)
        a = notificar_subir_factura_profesionales(request,self)
        a.start()

    def get_mes_pago_solicitud(self):
        return self.get_detalle_solicitudes().first().solicitudpago.fechainicio if self.get_detalle_solicitudes().exists() else None

    def actualizar_codigos_acta_pago_and_memo(self,request):
        try:
            codigo_acta, codigo_memo  = self.get_codigo_secuencia_acta_pago()
            self.codigo =codigo_acta
            self.codigomemo = codigo_memo
            sel.save(request)
        except Exception as ex:
            pass

    def reiniciar_acta_pago(self,request,persona):
        try:
            observacion = 'Se reinicio el acta de pago'
            self.get_integrantes_firman().update(firmo=False)
            self.generar_pdf_acta_pago_en_tiempo_real(request,persona)
            self.estado = 1
            self.guardar_historial_acta_pago(request, persona, observacion, None)
            self.save(request)
        except Exception as ex:
            pass

    def generar_pdf_acta_pago_en_tiempo_real(self,request,persona):
        try:
            if persona.pk == 20570:#guerra gaibor -encargadapagos tics
                archivo_check_list = self.generar_actualizar_check_list_pago_pdf_tics(request)
                self.guardar_historial_acta_pago(request, persona, 'generación archivo check list general',archivo_check_list)
                archivo_acta_pago = self.generar_actualizar_acta_pago_pdf_tics(request)
                self.guardar_historial_acta_pago(request, persona, 'generación archivo acta pago ', archivo_acta_pago)
                archivo_memodip = self.generar_actualizar_memo_pago_pdf(request)
                self.guardar_historial_acta_pago(request, persona, 'generación archivo memo  direccion de tics',archivo_memodip)
            else:
                archivo_check_list = self.generar_actualizar_check_list_pago_pdf(request)
                self.guardar_historial_acta_pago(request, persona, 'generación archivo check list general', archivo_check_list)
                archivo_acta_pago =self.generar_actualizar_acta_pago_pdf(request)
                self.guardar_historial_acta_pago(request, persona, 'generación archivo acta pago ', archivo_acta_pago)
                archivo_memodip= self.generar_actualizar_memo_pago_pdf(request)
                self.guardar_historial_acta_pago(request, persona, 'generación archivo memo  direccion posgrado', archivo_memodip)

        except Exception as ex:
            pass

    def persona_es_quien_firma_acta_pago_y_memo(self, pk):
        return True if self.actapagointegrantesfirma_set.filter(status=True, pk=pk,ordenfirmaactapago__responsabilidadfirma_id__in=[3, 4]).exists() else False

    def generar_texto_asunto_memo_acta_pago(self):
        try:
            mensaje = f"Solicitud de pago por contrato civil de servicios profesionales de  "
            for persona_contratada in self.get_cargos_sin_repetir():
                mensaje += f"{persona_contratada['solicitudpago__contrato__cargo__nombre']}, "
            mensaje += f"correspondiente al mes de {self.get_mes_fecha(self.get_mes_pago_solicitud())} {self.get_mes_pago_solicitud().year }."
            return mensaje
        except Exception as ex:
            return ''

    def generar_texto_cuerpo_memo_acta_pago(self):
        try:
            mensaje = f'<p style="text-align: justify">De mi consideración:</p>'
            mensaje += f'<p style="text-align: justify"> En virtud al “Proyecto de Inversión en el ámbito de Cooperación entre UNEMI y EPUNEMI, para fortalecer la Interinstitucionalidad a través de desarrollo de programas de Posgrado, de educación continua, eventos culturales, científicos y académicos con los mecanismos integrados de la operatividad entre la Universidad Estatal de Milagro y la EPUNEMI”, aprobado por RESOLUCIÓN DE DIRECTORIO No. 004-SO-003-2024-DIR-EPUNEMI-04 ante el crecimiento significativo de las actividades de comercialización y producción de los programas de cuarto nivel de Posgrado; y, en relación la organización administrativa/financiera para el normal desarrollo académico de los programas de Maestrías, agradeceré a usted se sirva disponer a quien corresponda se realice el pago a los profesionales descritos en la tabla 1 profesionales a pagar, relacionados en la estructura de la Dirección de Posgrado por concepto de servicios profesionales. '
            mensaje += f' Se anexa el Acta de Control previo al pago<b> No. {self.codigo}</b>, el mismo que refleja el siguiente detalle: </p>'
            return mensaje
        except Exception as ex:
            return ''

    def validacion_todas_las_solicitudes_son_del_mismo_mes(self):
        try:
            eDetalleActaPagoMes = self.get_detalle_solicitudes().values('solicitudpago__fechainicio__month').distinct().order_by('solicitudpago__fechainicio__month')
            eDetalleActaPagoAnio = self.get_detalle_solicitudes().values('solicitudpago__fechainicio__year').distinct().order_by('solicitudpago__fechainicio__year')
            return True if eDetalleActaPagoMes.count() == 1 and eDetalleActaPagoAnio.count() == 1 else False
        except Exception as ex:
            pass

    def validacion_todas_las_solicitudes_son_tipo_administrativo(self):
        try:
            eDetalleActaPago = self.get_detalle_solicitudes().values('solicitudpago__contrato__tipogrupo').filter(solicitudpago__contrato__tipogrupo=1).distinct().order_by('solicitudpago__contrato__tipogrupo')
            return True if eDetalleActaPago.count() == 1  else False
        except Exception as ex:
            pass

    def validacion_todas_las_solicitudes_son_tipo_profesor(self):
        try:
            eDetalleActaPago = self.get_detalle_solicitudes().values('solicitudpago__contrato__tipogrupo').filter(solicitudpago__contrato__tipogrupo=2).distinct().order_by('solicitudpago__contrato__tipogrupo')
            return True if eDetalleActaPago.count() == 1  else False
        except Exception as ex:
            pass

    def validacion_todas_las_solicitudes_subieron_los_requisitos_de_pago_excluyendo_la_factura(self):
        try:
            CERTIFICACION_BANCARIA = 5
            FORMATO_DE_PROVEEDORES = 6
            CERTIFICACION_PRESUPUESTARIA = 15
            CHECK_LIST_DE_PAGO = 16
            FACTURA = 4
            TODOS_SUBIERON_TODOS_LOS_REQUISITOS = True
            RELACION_DE_DEPENDENCIA_LABORAL = 20
            IMPEDIMENTO_EJERCER_CARGO_PUBLICO = 19
            eDetalleActaPagos = self.get_detalle_solicitudes()
            for eDetalleActaPago in eDetalleActaPagos:
                 for eRequisitoPagoDip in self.get_requisitos_solicitados_configurados_administrativos():
                     if not eRequisitoPagoDip.requisitopagodip.id == CHECK_LIST_DE_PAGO and not eRequisitoPagoDip.requisitopagodip.id ==  FACTURA and not eRequisitoPagoDip.requisitopagodip.id == IMPEDIMENTO_EJERCER_CARGO_PUBLICO and not eRequisitoPagoDip.requisitopagodip.id ==  RELACION_DE_DEPENDENCIA_LABORAL:
                         if not eDetalleActaPago.solicitudpago.tiene_cargado_documento_check_list_acta_pago(eRequisitoPagoDip.requisitopagodip):
                             TODOS_SUBIERON_TODOS_LOS_REQUISITOS = False
                             break
                 if not TODOS_SUBIERON_TODOS_LOS_REQUISITOS:
                     break

            return TODOS_SUBIERON_TODOS_LOS_REQUISITOS
        except Exception as ex:
            pass

    def descargar_requisitos_todos(self,request):
        from django.http import  HttpResponse
        try:
            eActaPagoPosgrado = self
            dominiosistema = request.build_absolute_uri('/')[:-1].strip("/")
            directory = os.path.join(SITE_STORAGE, 'media/zip')
            try:
                os.stat(directory)
            except:
                os.mkdir(directory)

            directory = os.path.join(SITE_STORAGE, 'media/documentosactapagopersonal')
            try:
                os.stat(directory)
            except:
                os.mkdir(directory)

            url = os.path.join(SITE_STORAGE, 'media', 'zip', f'{eActaPagoPosgrado.codigo}.zip')
            url_zip = url
            fantasy_zip = zipfile.ZipFile(url, 'w')
            if eActaPagoPosgrado.get_detalle_solicitudes():
                for eDetalleActaPago in eActaPagoPosgrado.get_detalle_solicitudes():
                    persona = eDetalleActaPago.solicitudpago.contrato.persona
                    carpeta_persona = f"{persona}/"
                    acta_pago = SITE_STORAGE + eDetalleActaPago.actapagoposgrado.archivo.url
                    fantasy_zip.write(acta_pago, carpeta_persona + os.path.basename(acta_pago))
                    memo_posgrado = SITE_STORAGE + eDetalleActaPago.actapagoposgrado.archivo_memo.url
                    fantasy_zip.write(memo_posgrado, carpeta_persona + os.path.basename(memo_posgrado))
                    if eDetalleActaPago.actapagoposgrado.archivo_memo_vice:
                        memo_vicerrectorado = SITE_STORAGE + eDetalleActaPago.actapagoposgrado.archivo_memo_vice.url
                        fantasy_zip.write(memo_vicerrectorado, carpeta_persona + os.path.basename(memo_vicerrectorado))

                    check_general = SITE_STORAGE + eDetalleActaPago.actapagoposgrado.archivo_check_list.url
                    fantasy_zip.write(check_general, carpeta_persona + os.path.basename(check_general))

                    for eRequisitoSolicitudPago in eDetalleActaPago.solicitudpago.traer_pasos_solicitud().order_by("orden"):
                        try:
                            ruta_archivo = eRequisitoSolicitudPago.last_historial().archivo.url
                            ruta_archivo = SITE_STORAGE + ruta_archivo
                            # Agregar el archivo PDF a la carpeta de la inscripción dentro del ZIP
                            fantasy_zip.write(ruta_archivo, carpeta_persona + os.path.basename(ruta_archivo))
                        except Exception as ex:
                            pass

            else:
                raise NameError('Erro al generar')
            fantasy_zip.close()
            response = HttpResponse(open(url_zip, 'rb'), content_type='application/zip')
            response['Content-Disposition'] = f'attachment; filename={eActaPagoPosgrado.codigo}.zip'
            return response
        except Exception as ex:
            return None

class DetalleItemsActaPagoPosgrado(ModeloBase):
    actapagoposgrado = models.ForeignKey(ActaPagoPosgrado, blank=True, null=True, verbose_name=u'Acta pago', on_delete=models.CASCADE)
    detallecontrato = models.CharField(blank=True, null=True, max_length=900)
    documentohabilitante = models.CharField(blank=True, null=True, max_length=900)
    observacion = models.CharField(blank=True, null=True, max_length=900)

    def __str__(self):
        return u'%s %s' % (self.detallecontrato, self.documentohabilitante)

    class Meta:
        verbose_name = u"DetalleItemsActaPagoPosgrado"
        verbose_name_plural = u"DetalleItemsActaPagoPosgrado"
        ordering = ['id']

class HistorialActaPago(ModeloBase):
    actapagoposgrado = models.ForeignKey(ActaPagoPosgrado, blank=True, null=True, verbose_name=u'Acta pago', on_delete=models.CASCADE)
    persona = models.ForeignKey("sga.persona", blank=True, null=True, verbose_name=u'Persona', on_delete=models.CASCADE)
    observacion = models.TextField(verbose_name=u"Observación", blank=True, null=True, default='')
    archivo = models.FileField(upload_to='actaPagoHistorial/', blank=True, null=True,verbose_name=u"Acta firmada",max_length=600)
    def __str__(self):
        return u'%s' % self.actapagoposgrado

    def archivo_url(self):
        return self.archivo.url if self.archivo else '#'
    class Meta:
        verbose_name = u"Historial acta pago"
        verbose_name_plural = u"Historial acta pago"
        ordering = ['id']


class DetalleActaPago(ModeloBase):
    actapagoposgrado = models.ForeignKey(ActaPagoPosgrado, verbose_name='acta pago', on_delete=models.CASCADE)
    solicitudpago = models.ForeignKey(SolicitudPago, verbose_name='solicitud pago', on_delete=models.CASCADE)
    rmu = models.DecimalField(max_digits=30, decimal_places=2, default=0, verbose_name=u"RMU")
    valoriva = models.DecimalField(default=0, max_digits=30, null=True, decimal_places=2, verbose_name=u'Valor IVA')
    valortotal = models.DecimalField(default=0, max_digits=30, null=True, decimal_places=2, verbose_name=u'Valor total')

    def __str__(self):
        return u"%s" % self.solicitudpago

    class Meta:
        verbose_name = u"Detalle acta pago"
        verbose_name_plural = u"Detalle acta pago"
        ordering = ['-id']

class ActaPagoIntegrantesFirma(ModeloBase):
    actapagoposgrado =models.ForeignKey(ActaPagoPosgrado,  verbose_name=u'Acta pago', on_delete=models.CASCADE)
    ordenfirmaactapago =models.ForeignKey(OrdenFirmaActaPago,  verbose_name=u'Responsabilidad', on_delete=models.CASCADE)
    persona =models.ForeignKey("sga.persona",  verbose_name=u'Persona', on_delete=models.CASCADE, blank=True, null =True)
    firmo =  models.BooleanField(verbose_name=u"¿Firmo?", default=False)

    def __str__(self):
        return f"{self.persona}"

    def get_cargo_responsable_firma(self):
        cargo =None
        if self.persona:
            if not self.persona.cargo_persona():
                eContratoDip = ContratoDip.objects.filter(persona=self.persona, status=True, estado=2).order_by('-id')
                cargo = eContratoDip.first().cargo if eContratoDip.exists() else 'Analista de Posgrado 1'
            else:
                if self.persona.pk  ==  variable_valor('DIRECTORA_TICS'):
                    cargo = 'DIRECTOR/A DE TECNOLOGÍA DE LA INFORMACIÓN Y COMUNICACIONES'
                else:
                    cargo = self.persona.cargo_persona().denominacionpuesto.descripcion
        return cargo

    class Meta:
        verbose_name = u"Acta Pago Integrantes Firma"
        verbose_name_plural = u"Acta Pago Integrantes Firma"
        ordering = ['-id']

TIPO_FORMATO = (
    (1, u'ADMINISTRATIVO'),
    (2, u'PROFESOR MÓDULAR'),

)

class ConfiguracionActaPago(ModeloBase):
    titulo = models.TextField(default='', verbose_name=u"titulo")
    marcojuridicoreferencial = models.CharField(default='', max_length=600000, verbose_name=u"Marco Juridico referencial")
    solicitadopor = models.ForeignKey("sga.persona", blank=True, null=True, verbose_name=u'Solicitado por', related_name='+', on_delete=models.CASCADE)
    para = models.ForeignKey("sga.persona", blank=True, null=True, verbose_name=u'Para', on_delete=models.CASCADE)
    objetivo = models.TextField(blank=True, null=True, max_length=600,verbose_name="Objetivo")
    activo = models.BooleanField(verbose_name="Activo", default=True)
    conclusiones = models.CharField(default='', max_length=600000, verbose_name=u"Conclusiones")
    recomendaciones = models.CharField(default='', max_length=600000,  verbose_name=u"Recomendaciones")

    def __str__(self):
        return f'configuracion informe {self.pk}'

    class Meta:
        verbose_name = u"ConfiguracionActaPago"
        verbose_name_plural = u"ConfiguracionActaPago"
        ordering = ['-id']


class ContratoDipPagoFactura(ModeloBase):
    contratodip = models.ForeignKey(ContratoDip, verbose_name=u"Contrato",on_delete=models.CASCADE)
    monto_a_pagar = models.DecimalField(max_digits=30, decimal_places=2, default=0, verbose_name=u"monto a pagar")
    anio = models.IntegerField(default=0, verbose_name=u"Año pago")
    mes = models.IntegerField(verbose_name='Mes pago', choices=MESES_CHOICES)
    fecha_pago = models.DateField(null=True, blank=True, verbose_name=u"Fecha de pago")

    class Meta:
        verbose_name = u"ContratoDipPagoFactura"
        verbose_name_plural = u"ContratoDipPagoFactura"

    def __str__(self):
        return u'%s' % (self.contratodip)
