# -*- coding: UTF-8 -*-
import json
import os
import shutil
import tempfile
import unicodedata

import PyPDF2
from django.contrib.auth.models import User, Group
from django.contrib.sessions.models import Session
from django.core.files import File
from django.core.files.base import ContentFile
from django.db import models, transaction

from postulaciondip.proccess_background import notificar_convocatoria_posgrado, \
    notificar_acta_revisada, notificar_persona_a_firmar, notificar_analistas_acta_firmada_completa, \
    notificar_acta_para_ser_revisada, notificar_analistas_estado_invitacion, proceso_notificar_votacion_comite, \
    notificar_realizar_votacion_director_posgrado, notificar_analistas_acta_votacion_completa, \
    actualizar_acta_seleccion_docente, \
    notificar_analistas_requisitos_subidos_por_personal_a_contratar, actualizar_informe_de_contratacion_posgrado, \
    actualizar_memo_informe_de_contratacion_posgrado, notificar_persona_a_fimar_informe_contratacion, \
    notificar_acta_revisada_reprogramacion, \
    proceso_guardado_principal_alternos_de_todas_las_convocatorias_de_los_paralelos
from settings import SITE_STORAGE
from sga.funciones import ModeloBase, null_to_decimal, daterange, variable_valor, log, generar_nombre
from django.contrib.contenttypes.models import ContentType
from inno.models import PerfilRequeridoPac, DetalleFuncionSustantivaDocenciaPac
from sga.models import Periodo, Carrera, TipoProfesor, Administrativo, DIAS_CHOICES, Turno, Materia, Paralelo, \
    CamposTitulosPostulacion, Titulacion, Notificacion, Reporte
from sagest.models import DenominacionPuesto, AnioEjercicio
from pdip.models import PerfilPuestoDip, CertificacionPresupuestariaDip, ContratoDip
from posgrado.models import CohorteMaestria
from django.db.models.query_utils import Q
from django.db.models import Count, PROTECT, Sum, Avg, Min, Max, F, OuterRef, Subquery, FloatField
from datetime import datetime, timedelta
from sga.funcionesxhtml2pdf import convert_html_to_pdf

unicode = str

ESTADO_ADMINISTRATIVO_MATERIA = (
    (0, 'INGRESADO'),
    (1, 'CONTRATADO'),
    (2, 'PLANIFICADO'),
    (3, 'CONVOCADO')
)


ESTADO_REVISION = (
    (1, u"REVISION"),
    (2, u"APROBADO"),
    (3, u"NO CUMPLE EL PERFIL"),
    (4, u"CONTROL PREVIO"),
    (5, u"VALIDADO"),
    (6, u"EJECUTADO"),
    (7, 'INCUMPLIMIENTO DE ENTREGA DE DOCUMENTO'),
    (8, 'CONTRATADO'),
    (9, 'INICIAR PROCESO'),
    (10, 'REESTRUCTURACIÓN ACADÉMICA'),
    (11, 'BANCO DE ELEGIBLE'),
    (12, 'APROBADO PARA REVISIÓN DEL COMITÉ'),
)

ESTADO_INSCRIPCION_POSTULANTE = (
    (1, u"PENDIENTE"),
    (2, u"ENVIADO"),
    (3, u"EN PROCESO"),
    (4, u"ACEPTADO"),
    (5, u"RECHAZADO"),
)

ESTADO_REVISIONDOCUMENTO = (
    (1, u"PENDIENTE"),
    (2, u"APROBADO"),
    (3, u"CORREGIR"),
)

TIPOREVISOR = (
    (1, u"VALIDA"),
    (2, u"COORDINADOR"),
    (3, u"GERENTE"),
    (4, u"TALENTO HUMANO"),
)

TIPO_REVISION = (
    (1, u"EVIDENCIA"),
    (2, u"APROBACION TOTAL"),
)

TIPO_REVISIONINS = (
    (1, u"GENERAL"),
    (2, u"CONVOCATORIA"),
)

TIPO_ARCHIVO = (
    (1, u"PDF"),
    (2, u"IMG"),
)

TIPO_INSCRIPCION = (
    (1, u"INTERNO"),
    (2, u"EXTERNO"),
)

TIPO_CONVOCATORIA = (
    (1, u"DOCENTE MODULAR"),
    (2, u"DOCENTE INVITADO"),
    (3, u"ADMINISTRATIVO"),
)

TIPO_DOCUMENTO_INVITACION = (
    (1, U"OTROS"),
    (2, u"CONTRATACIÓN (DOCENTE)"),
    (3, u"PAGO (DOCENTE)"),
)

ESTADO_PARALELOS_EN_ACTA = (
    (1, 'APROBADO'),
    (2, 'RECHAZADO'),
    (3, 'REEMPLAZO'),
    (4, 'APLAZADO'),
)


class TipoDocente(ModeloBase):
    nombre = models.CharField(default='', max_length=100, verbose_name=u"Nombre")
    abreviatura = models.CharField(default='', max_length=10, verbose_name=u'Abreviatura')

    class Meta:
        verbose_name = u"Tipo Profesor"
        verbose_name_plural = u"Tipos de Profesores"
        ordering = ['-nombre']
        unique_together = ('nombre',)

    def __str__(self):
        return u'%s' % self.nombre

    def save(self, *args, **kwargs):
        self.nombre = self.nombre.upper().strip()
        self.abreviatura = self.abreviatura.upper().strip()
        super(TipoDocente, self).save(*args, **kwargs)


class Requisito(ModeloBase):
    nombre = models.CharField(default='', max_length=250, verbose_name=u"Nombre del archivo")
    observacion = models.CharField(default='', max_length=500, verbose_name=u"Observación")
    activo = models.BooleanField(default=True, verbose_name=u"Activo")
    archivo = models.FileField(upload_to='formatorequisito/%Y/%m/%d', blank=True, null=True, verbose_name=u'Archivo')
    tipoarchivo = models.IntegerField(choices=TIPO_ARCHIVO, default=1, verbose_name=u'Formato pdf o img')

    def __str__(self):
        return u'%s' % self.nombre

    class Meta:
        verbose_name = u"Requisito"
        verbose_name_plural = u"Requisitos"
        ordering = ['id']

    def enuso_convocatoria(self):
        return self.requisitosconvocatoria_set.filter(status=True).exists()

    def enuso_generales(self):
        return self.requisitogenerales_set.filter(status=True).exists()


class RequisitoGenerales(ModeloBase):
    requisito = models.ForeignKey(Requisito, verbose_name=u'Postulante', on_delete=models.CASCADE)

    def __str__(self):
        return u'%s' % self.requisito

    def detalle_requisitosgenerales(self, persona):
        if self.requisitogeneralespersona_set.values("id").filter(persona=persona,status=True).exists():
            return self.requisitogeneralespersona_set.get(persona=persona,status=True)
        else:
            return None

    def enuso_requigenerales(self):
        return self.requisitogeneralespersona_set.filter(status=True).exists()


class RequisitoGeneralesPersona(ModeloBase):
    persona = models.ForeignKey('sga.Persona', verbose_name=u'Postulante', on_delete=models.CASCADE)
    requisitogeneral = models.ForeignKey(RequisitoGenerales, verbose_name=u'Requisito generall', on_delete=models.CASCADE)
    archivo = models.FileField(upload_to='evidenciapostulacion/%Y/%m/%d', blank=True, null=True, verbose_name=u'Archivo')
    estado = models.IntegerField(choices=ESTADO_REVISION, default=1, verbose_name=u'Estado')
    fecharevision = models.DateTimeField(blank=True, null=True)
    personaaprobador = models.ForeignKey('sga.Persona', blank=True, null=True, verbose_name=u'Quien aprueba' , related_name='+', on_delete=models.CASCADE)
    observacion = models.TextField(blank=True, null=True, verbose_name=u"Observación")

    def __str__(self):
        return u'%s' % self.persona

    def download_evidencia(self):
        return self.archivo.url


class HistorialReqGeneral(ModeloBase):
    requisitogeneral = models.ForeignKey(RequisitoGeneralesPersona, blank=True, null=True, verbose_name=u'Inscripcion convocatoria', on_delete=models.CASCADE)
    observacion = models.TextField(blank=True, null=True, verbose_name=u"Observación postulante")
    estado = models.IntegerField(choices=ESTADO_REVISION, default=1, verbose_name=u'Estado')


class InscripcionPostulante(ModeloBase):
    persona = models.ForeignKey('sga.Persona', verbose_name=u'Persona', on_delete=models.CASCADE)
    activo = models.BooleanField(default=True, verbose_name=u"Activo")
    estado = models.IntegerField(choices=ESTADO_INSCRIPCION_POSTULANTE, default=1, verbose_name=u'Estado')
    hoja_vida = models.FileField(upload_to='inscripcionpostulanteposgrado/', blank=True, null=True, verbose_name=u'Hoja vida')
    def __str__(self):
        return u'%s' % self.persona

    class Meta:
        verbose_name = u"Inscripcion Postulante"
        verbose_name_plural = u"Inscripcion Postulantes"
        ordering = ['id']

    def color_estado(self):
        color = 'default'
        if self.estado == 2:
            color = "info"
        elif self.estado == 3:
            color = "warning"
        elif self.estado == 4:
            color = "succcess"
        elif self.estado == 5:
            color = "warning"
        return color

    def get_convocatorias(self, tipo):
        return Convocatoria.objects.filter(tipo=tipo, activo=True, fechafin__gte=datetime.now().date(), status=True)

    def existen_convocatorias_disponibles(self, convocatorias):
        for convocatoria in convocatorias:
           if convocatoria.puede_postular(self):
              return True
        return False

    def es_banco_elegible(self):
        return self.inscripcionconvocatoria_set.filter(status=True,estado = 11).exists()

    def get_convocatorias_que_postulo(self):
        eInscripcionConvocatoria = self.inscripcionconvocatoria_set.filter(status=True).order_by('convocatoria__periodo')
        return eInscripcionConvocatoria if eInscripcionConvocatoria.exists() else None


class ClasificacionAC(ModeloBase):
    codigo = models.CharField(default='', max_length=80, blank=True, null=True, verbose_name=u"Codigo")
    descripcion = models.TextField(blank=True, null=True, verbose_name=u"Descripcion")
    nivel = models.IntegerField(default=1, verbose_name=u'Nivel')
    activo = models.BooleanField(default=False, verbose_name=u"Activo para postulante")

    def __str__(self):
        return u'%s' % self.codigo


class ActividadEconomica(ModeloBase):
    persona = models.ForeignKey('sga.Persona', verbose_name=u'Persona', on_delete=models.CASCADE)
    actividad = models.ForeignKey(ClasificacionAC, verbose_name=u'Persona', on_delete=models.CASCADE)
    principal = models.BooleanField(default=False, verbose_name=u"Activo")

    def __str__(self):
        return u'%s' % self.persona

    class Meta:
        verbose_name = u"Actividad Económica"
        verbose_name_plural = u"Actividades Económicas"
        ordering = ['id']

class TiempoDedicacion(ModeloBase):
    descripcion = models.TextField(verbose_name=u"Descripción")
    horas = models.IntegerField( verbose_name=u"Descripción")

    def __str__(self):
        return f"{self.descripcion}"

    class Meta:
        verbose_name = u"Tiempo Dediacion "
        verbose_name_plural = u"Tiempo Dediacion"
        ordering = ['id']


class Convocatoria(ModeloBase):
    asignaturamalla = models.ForeignKey('sga.AsignaturaMalla', verbose_name=u'Asignatura malla', on_delete=models.CASCADE, blank=True, null=True)
    fechainiciorequisito = models.DateField(verbose_name=u"Fecha Inicio Requisito", null=True, blank=True)
    fechafinrequisito = models.DateField(verbose_name=u"Fecha Fin Requisito", null=True, blank=True)
    nombre = models.CharField(default='', max_length=500, blank=True, null=True, verbose_name=u"Nombre")
    activo = models.BooleanField(default=True, verbose_name=u"Activo")
    fechainicio = models.DateField(verbose_name=u"Fecha Inicio", null=True, blank=True)
    fechafin = models.DateField(verbose_name=u"Fecha Fin", null=True, blank=True)
    perfilrequeridopac = models.ManyToManyField(PerfilRequeridoPac, blank=True, verbose_name=u'Perfil Requerido')
    periodo = models.ForeignKey(Periodo, on_delete=models.CASCADE, blank=True, null=True, verbose_name=u'Periodo')
    carrera = models.ForeignKey(Carrera, on_delete=models.CASCADE, blank=True, null=True, verbose_name=u'Carrera')
    tipodocente = models.ForeignKey(TipoProfesor, on_delete=models.CASCADE, blank=True, null=True, verbose_name=u'Tipo de Docente')
    vacantes = models.IntegerField(verbose_name=u"Vacantes", blank=True, null=True, default=1)
    paralelos = models.IntegerField(verbose_name=u'Paralelos', default=1, blank=True, null=True)
    tipo = models.IntegerField(choices=TIPO_CONVOCATORIA, default=1, verbose_name=u'Típo')
    campoamplio = models.ManyToManyField('sga.AreaConocimientoTitulacion', verbose_name=u'Campo Amplio')
    campoespecifico = models.ManyToManyField('sga.SubAreaConocimientoTitulacion', verbose_name=u'Campo Especifico')
    campodetallado = models.ManyToManyField('sga.SubAreaEspecificaConocimientoTitulacion',verbose_name=u'Campo Detallado')
    descripcion = models.TextField(verbose_name=u"Descripción ", max_length=700,blank=True, null=True)
    iniciohorario =  models.DateField(verbose_name=u"Fecha Inicio horario", null=True, blank=True)
    finhorario = models.DateField(verbose_name=u"Fecha Fin horario", null=True, blank=True)
    tiempodedicacion = models.ForeignKey(TiempoDedicacion, on_delete=models.CASCADE, blank=True, null=True, verbose_name=u'Tiempo dedicacion')

    def __str__(self):
        return u'(%s) %s %s %s %s %s' % (self.pk ,self.asignaturamalla.asignatura if self.asignaturamalla else self.nombre,
                                    '- COHORTE:' if self.periodo else '',
                                    self.periodo.cohorte if self.periodo else '',
                                    self.periodo.anio if self.periodo else '',
                                    f"- [{self.totalinscritos()}]")

    def titulo(self):
        return u'%s %s %s %s' % (self.asignaturamalla.asignatura if self.asignaturamalla else self.nombre,
                                    '- COHORTE:' if self.periodo else '',
                                    self.periodo.cohorte if self.periodo else '',
                                    self.periodo.anio if self.periodo else '' )
    class Meta:
        verbose_name = u"Convocatoria"
        verbose_name_plural = u"Convocatorias"
        ordering = ['id']

    def get_convocatoria_postulada(self,postulante):
        eInscripcionConvocatoria = InscripcionConvocatoria.objects.filter(status=True, postulante=postulante, convocatoria=self)
        return eInscripcionConvocatoria.first() if eInscripcionConvocatoria.exists() else None
    def get_code(self):
        return "%04d" % self.id

    def totalinscritos(self):
        return self.inscripcionconvocatoria_set.values_list('id').filter(postulante__status=True, status=True).count()

    def listadoinscritos(self):
        return self.inscripcionconvocatoria_set.filter(status=True)

    def totalinscritos(self):
        return self.inscripcionconvocatoria_set.filter(status=True).count()

    def totalinscritos_aprobados(self):
        return self.inscripcionconvocatoria_set.filter(status=True, estado = 2).count()

    def requisitosconvocatoria(self):
        return self.requisitosconvocatoria_set.filter(status=True).order_by('-requisito__id')

    def total_requisitos_convocatoria(self):
        return self.requisitosconvocatoria_set.filter(status=True).count()

    def get_existen_requisitos_configurados(self):
        return self.requisitosconvocatoria_set.filter(status=True).exists()

    def get_estado(self):
        if self.fechafin >= datetime.now().date() and self.activo:
            estado, htmlclass = 'ACTIVO', 'success'
        else:
            if not self.activo:
                estado, htmlclass = u'INACTIVO', 'secondary'
            else:
                estado, htmlclass = u'EXPIRADO', 'warning'

        return {'estado': '%s' % estado, 'color': '%s' % htmlclass}

    def puede_postular(self, postulante):
        if self.tipo == 1:
            return self.titulados_acorde_al_campo_del_perfil_requerido().filter(persona=postulante.persona).exists() and postulante.persona.titulacion_set.values('id').filter(titulo__nivel__id__in=[4], status=True).exists()

        elif self.tipo == 2:
            return postulante.persona.titulacion_set.values('id').filter(titulo__nivel__id__in=[3, 4], status=True).exists()

    def get_postulantes(self):
        return self.inscripcionconvocatoria_set.filter(postulante__status=True, status=True)

    def get_postulantes_aprobados(self):
        return self.inscripcionconvocatoria_set.filter(estado=2, status=True)

    def get_postulantes_reprobados(self):
        return self.inscripcionconvocatoria_set.filter(status=True).exclude(estado__in = [2,11])

    def get_postulantes_banco_elegible(self):
        return self.inscripcionconvocatoria_set.filter(status=True,estado = 11)

    def get_actas_generadas(self):
        return self.actaparalelo_set.filter(acta__archivo__isnull=False, status=True).count()

    def get_actas(self):
        return self.actaparalelo_set.filter(status=True)

    def get_horas_modulo(self):
        return DetalleFuncionSustantivaDocenciaPac.objects.filter(asignatura=self.asignaturamalla.asignatura, status=True).first()

    def get_horas_componente_docente(self):
        horas = self.asignaturamalla.horasacdtotal  if self.asignaturamalla.horasacdtotal else 0
        return horas

    def get_valor_hora_modulo(self):
        model = DetalleFuncionSustantivaDocenciaPac.objects.filter(asignatura=self.asignaturamalla.asignatura, status=True).first()
        return model.valorhoramodulo if model else 0

    def get_valor_total_modulo(self):
        return self.get_horas_componente_docente() * self.get_valor_hora_modulo()

    def get_detalle_funcion_sustantiva_docencia(self):
        return DetalleFuncionSustantivaDocenciaPac.objects.filter(asignatura=self.asignaturamalla.asignatura, status=True).first()

    def get_camposamplios(self):
        return self.campoamplio.all()

    def get_camposespecificos(self):
        return self.campoespecifico.all()

    def get_camposdetallados(self):
        return self.campodetallado.all()

    def configurado_solo_campo_amplio(self):
        return True if self.get_camposamplios().exists() and not self.get_camposespecificos().exists() and not self.get_camposdetallados().exists() else False

    def configurado_solo_campo_especifico(self):
        return True if self.get_camposespecificos().exists() and not self.get_camposamplios().exists() and not self.get_camposdetallados().exists() else False

    def configurado_solo_campo_detallado(self):
        return True if self.get_camposdetallados().exists() and not self.get_camposamplios().exists() and not self.get_camposespecificos().exists() else False

    def configurado_solo_campo_amplio_and_campo_especifico(self):
        return True if self.get_camposamplios().exists() and self.get_camposespecificos().exists() and not self.get_camposdetallados().exists() else False

    def configurado_solo_campo_amplio_and_campo_detallado(self):
        return True if self.get_camposamplios().exists() and self.get_camposdetallados().exists() and not self.get_camposespecificos().exists() else False

    def configurado_campo_amplio_and_campo_especifico_and_campo_detallado(self):
        return True if self.get_camposamplios().exists() and self.get_camposespecificos().exists() and  self.get_camposdetallados().exists() else False

    def get_titulos_campos_amplios(self):
        ids_camposamplios = self.get_camposamplios().values_list('pk', flat=True)
        eTitulos_campoamplio_id = CamposTitulosPostulacion.objects.filter(status=True,campoamplio__in=ids_camposamplios).values_list('titulo_id', flat=True).distinct()
        return eTitulos_campoamplio_id

    def get_titulos_campos_especificos(self):
        ids_camposespecificos= self.get_camposespecificos().values_list('pk',flat =True)
        eTitulos_campoespecifico_id = CamposTitulosPostulacion.objects.filter(status=True,campoespecifico__in=ids_camposespecificos).values_list('titulo_id', flat=True).distinct()
        return eTitulos_campoespecifico_id

    def get_titulos_campos_detallados(self):
        ids_camposdetallados= self.get_camposdetallados().values_list('pk',flat =True)
        eTitulos_camposdetallados_id = CamposTitulosPostulacion.objects.filter(status=True,campodetallado__in=ids_camposdetallados).values_list('titulo_id', flat=True).distinct()
        return eTitulos_camposdetallados_id

    def titulados_acorde_al_campo_del_perfil_requerido(self):
        eTitulos_campoamplio_ids = None
        eTitulos_campoespecifico_ids = None
        eTitulos_camposdetallados_ids  =None
        eTitulos_id = [0, ]

        if self.configurado_solo_campo_amplio():
            eTitulos_campoamplio_ids =  self.get_titulos_campos_amplios()
            # Obtener los IDs de los títulos que cumplen con el campo
            eTitulos_id =eTitulos_campoamplio_ids

        if self.configurado_solo_campo_especifico():
            eTitulos_campoespecifico_ids =  self.get_titulos_campos_especificos()
            # Obtener los IDs de los títulos que cumplen con el campo
            eTitulos_id = eTitulos_campoespecifico_ids

        if self.configurado_solo_campo_detallado():
            eTitulos_camposdetallados_ids = self.get_titulos_campos_detallados()
            # Obtener los IDs de los títulos que cumplen con el campo
            eTitulos_id = eTitulos_camposdetallados_ids

        if self.configurado_solo_campo_amplio_and_campo_especifico():
            eTitulos_campoamplio_ids =  self.get_titulos_campos_amplios()
            eTitulos_campoespecifico_ids = self.get_titulos_campos_especificos()
            # Obtener los IDs de los títulos que cumplen con ambos campos (intersección)
            eTitulos_id = set(eTitulos_campoamplio_ids) & set(eTitulos_campoespecifico_ids)

        if self.configurado_solo_campo_amplio_and_campo_detallado():
            eTitulos_campoamplio_ids =  self.get_titulos_campos_amplios()
            eTitulos_camposdetallados_ids = self.get_titulos_campos_detallados()

            # Obtener los IDs de los títulos que cumplen con ambos campos (intersección)
            eTitulos_id = set(eTitulos_campoamplio_ids) &  set(eTitulos_camposdetallados_ids)

        if self.configurado_campo_amplio_and_campo_especifico_and_campo_detallado():
            eTitulos_campoamplio_ids = self.get_titulos_campos_amplios()
            eTitulos_campoespecifico_ids = self.get_titulos_campos_especificos()
            eTitulos_camposdetallados_ids = self.get_titulos_campos_detallados()

            # Obtener los IDs de los títulos que cumplen con los campos (intersección)
            eTitulos_id = set(eTitulos_campoamplio_ids) & set(eTitulos_campoespecifico_ids) & set(eTitulos_camposdetallados_ids)

        # Filtrar las personas con el titulo que cumplen las condiciones de los campos
        eTitulacion = Titulacion.objects.filter(status=True, titulo_id__in=eTitulos_id,persona__status=True)

        return eTitulacion

    def notificar_perfiles_compatibles(self,request):
        if self.activo and self.fechafin >= datetime.now().date() and datetime.now().date() >= self.fechainicio:
            ePerfilComplatibles = self.titulados_acorde_al_campo_del_perfil_requerido()
            a = notificar_convocatoria_posgrado(request,ePerfilComplatibles,self)
            a.start()

    def get_turno_por_fecha(self, dia):
        return self.horarioplanificacionconvocatoria_set.filter(inicio__lte=dia, fin__gte=dia, dia=dia.weekday() + 1, status=True).first()

    def get_horario(self):
        return self.horarioplanificacionconvocatoria_set.filter(status=True)

    def get_dias_intermedios(self):
        horarios = self.get_horario()
        newlist = []
        for h in horarios: newlist += [x for x in daterange(h.inicio, h.fin + timedelta(1)) if
                                       h.dia == x.weekday() + 1 and not x == self.iniciohorario and not x == self.finhorario]

        return newlist

    def get_escuela_de_negocio(self):
        return self.carrera.escuelaposgrado

    def postulantes_revisados_todos(self):
        try:
            return False if self.inscripcionconvocatoria_set.filter(status=True,estado=1).exists() else True
        except Exception as ex:
            return False

    def notificar_vicerrector_posgrado(self,request,persona):
        try:
            from sga.models import Persona
            ePersonas = Persona.objects.filter(pk__in=variable_valor('IDS_PERSONAS_NOTIFICAR_CONVOCATORIA_POSGRADO'))
            titulonotificacion =f"{persona} apertura convocatoria: {self.nombre} - {self.fechainicio} hasta {self.fechafin}"
            cuerponotificacion = f"Convocatoria aperturada por {persona} <br> Tipo convocatoria: {self.get_tipo_display()}  <br> Nombre convocatoria: {self.nombre} <br>Código convocatoría: {self.pk}<br> Periodo: {self.periodo} <br> Carrera: {self.carrera} <br> Módulo: {self.asignaturamalla} <br> Fecha inicio:{self.fechainicio} <br> Fecha fin: {self.fechafin} <br> Tipo docente: {self.tipodocente} <br> Vacantes: {self.vacantes} <br> Vacantes: {self.paralelos}"
            for ePersona in ePersonas:
                notificacion = Notificacion(
                    titulo=titulonotificacion,
                    cuerpo=cuerponotificacion,
                    destinatario=ePersona,
                    url=f"https://sga.unemi.edu.ec/adm_postulacion?action=convocatorias",
                    content_type=None,
                    object_id=None,
                    prioridad=1,
                    app_label='SGA',
                    fecha_hora_visible=datetime.now() + timedelta(days=3))
                notificacion.save(request)
        except Exception as ex:
            pass

    def notificar_vicerrector_posgrado_edita_convocatoria(self,request,persona):
            try:
                from sga.models import Persona
                ePersonas = Persona.objects.filter(pk__in=variable_valor('IDS_PERSONAS_NOTIFICAR_CONVOCATORIA_POSGRADO'))
                titulonotificacion =f"{persona} edita convocatoria: {self.nombre} - {self.fechainicio} hasta {self.fechafin}"
                cuerponotificacion = f"Convocatoria editada por {persona} <br> Tipo convocatoria: {self.get_tipo_display()}  <br> Nombre convocatoria: {self.nombre} <br>Código convocatoría: {self.pk}<br> Periodo: {self.periodo} <br> Carrera: {self.carrera} <br> Módulo: {self.asignaturamalla} <br> Fecha inicio:{self.fechainicio} <br> Fecha fin: {self.fechafin} <br> Tipo docente: {self.tipodocente} <br> Vacantes: {self.vacantes} <br> Vacantes: {self.paralelos}"
                for ePersona in ePersonas:
                    notificacion = Notificacion(
                        titulo=titulonotificacion,
                        cuerpo=cuerponotificacion,
                        destinatario=ePersona,
                        url=f"https://sga.unemi.edu.ec/adm_postulacion?action=convocatorias",
                        content_type=None,
                        object_id=None,
                        prioridad=1,
                        app_label='SGA',
                        fecha_hora_visible=datetime.now() + timedelta(days=3))
                    notificacion.save(request)
            except Exception as ex:
                pass

class HistorialConvocatoria(ModeloBase):
    convocatoria = models.ForeignKey(Convocatoria, verbose_name=u'convocatoria', on_delete=models.CASCADE)
    persona = models.ForeignKey('sga.Persona', verbose_name=u'Persona', on_delete=models.CASCADE)
    fecha = models.DateField(verbose_name=u"Fecha")
    perfilrequeridopac = models.ManyToManyField(PerfilRequeridoPac, blank=True, verbose_name=u'Perfil Requerido')
    campoamplio = models.ManyToManyField('sga.AreaConocimientoTitulacion', verbose_name=u'Campo Amplio')
    campoespecifico = models.ManyToManyField('sga.SubAreaConocimientoTitulacion', verbose_name=u'Campo Especifico')
    campodetallado = models.ManyToManyField('sga.SubAreaEspecificaConocimientoTitulacion', verbose_name=u'Campo Detallado')
    tipodocente = models.ForeignKey(TipoProfesor, on_delete=models.CASCADE, blank=True, null=True,verbose_name=u'Tipo de Docente')
    fechainicio = models.DateField(verbose_name=u"Fecha Inicio", null=True, blank=True)
    fechafin = models.DateField(verbose_name=u"Fecha Fin", null=True, blank=True)
    vacantes = models.IntegerField(verbose_name=u"Vacantes", blank=True, null=True, default=1)
    paralelos = models.IntegerField(verbose_name=u'Paralelos', default=1, blank=True, null=True)

    def __str__(self):
        return u'%s' % self.convocatoria

    class Meta:
        verbose_name = u"Historial Convocatoria"
        verbose_name_plural = u"Historial Convocatoria"
        ordering = ['id']

class RequisitosConvocatoria(ModeloBase):
    convocatoria = models.ForeignKey(Convocatoria, verbose_name=u'Convocatoria', on_delete=models.CASCADE)
    requisito = models.ForeignKey(Requisito, blank=True, null=True, verbose_name=u'Requisito', on_delete=models.CASCADE)
    opcional = models.BooleanField(default=False, verbose_name=u"opcional")

    def __str__(self):
        return u'%s' % self.convocatoria

    class Meta:
        verbose_name = u"Requisito por Convocatoria"
        verbose_name_plural = u"Requisitos por Convocatoria"
        ordering = ['id']

    def detalle_requisitosmaestriacohorte(self, inscripcionconvocatoria):
        if self.inscripcionconvocatoriarequisitos_set.values("id").filter(inscripcionconvocatoria=inscripcionconvocatoria,status=True).exists():
            return self.inscripcionconvocatoriarequisitos_set.get(inscripcionconvocatoria=inscripcionconvocatoria,status=True)
        else:
            return None

    def requisito_ocupado_ins(self):
        return self.inscripcionconvocatoriarequisitos_set.filter(status=True).exists()

class InscripcionConvocatoria(ModeloBase):
    postulante = models.ForeignKey(InscripcionPostulante, verbose_name=u'Postulante', on_delete=models.CASCADE)
    convocatoria = models.ForeignKey(Convocatoria, verbose_name=u'Convocatoria', on_delete=models.CASCADE)
    estado = models.IntegerField(choices=ESTADO_REVISION, default=1, verbose_name=u'Estado requisito convocatoria')
    observacioncon = models.TextField(blank=True, null=True, verbose_name=u"Observación requisito convocatoria")
    estadogen = models.IntegerField(choices=ESTADO_REVISION, default=1, verbose_name=u'Estado proceso contratación')
    observaciongen = models.TextField(blank=True, null=True, verbose_name=u"Observación requisito general")
    link = models.TextField(blank=True, null=True, verbose_name=u"link", max_length=250)

    def __str__(self):
        return u'%s' % self.postulante

    class Meta:
        verbose_name = u"Inscripción Convocatoria"
        verbose_name_plural = u"Inscripción Convocatorias"
        ordering = ['id']

    def listadorequisitos(self):
        return self.convocatoria.requisitosconvocatoria_set.filter(status=True)

    def get_invitacion(self):
        return self.inscripcioninvitacion_set.filter(status=True)

    def listadorequisitoscargados(self):
        return self.inscripcionconvocatoriarequisitos_set.filter(status=True)

    def requisitosgeneralescargados(self):
        return self.postulante.persona.requisitogeneralespersona_set.filter(status=True)

    def total_requisitos_general_cargados(self):
        return self.postulante.persona.requisitogeneralespersona_set.filter(status=True).count()

    def total_requisitos_convocatoria_cargados(self):
        return self.inscripcionconvocatoriarequisitos_set.filter(status=True).count()

    def color_estado(self):
        estado = 'primary'
        if self.estado == 1:
            estado = 'warning'
        elif self.estado == 2:
            estado = 'success'
        elif self.estado == 3:
            estado = 'danger'
        elif self.estado >= 4:
            estado = 'secondary'
        return estado

    def acepto_invitacion(self):
        return self.inscripcioninvitacion_set.values('id').filter(status=True, estadoinvitacion=4).exists()

    def get_fecha_revision_requisitos(self):
        if self.inscripcioninvitacion_set.values('id').filter(status=True).exists():
            return self.inscripcioninvitacion_set.filter(status=True).first().fecharevisionrequisitos

    def get_requisitos_cargados_historico(self):
        _invitacionespasadas = InscripcionInvitacion.objects.filter(inscripcion__postulante__persona=self.postulante.persona, status=True)
        return InscripcionConvocatoriaRequisitos.objects.filter(inscripcioninvitacion__in=_invitacionespasadas, status=True).order_by('-requisito__requisito__id')

    def get_requisitos_por_cargar(self):
        return self.convocatoria.requisitosconvocatoria().exclude(requisito__id__in=self.get_requisitos_cargados_historico().values_list('requisito__requisito__id', flat=True))

    def get_requisitos_preaprobados(self):
        return InscripcionRequisitoPreAprobado.objects.filter(inscripcioninvitacion__inscripcion=self, requisitoconvocatoria__id__in=self.listadorequisitos().values_list('id', flat=True), status=True).first()

    def get_personalacontratar(self):
        return PersonalAContratar.objects.filter(inscripcion=self, actaparalelo__convocatoria=self.convocatoria, actaparalelo__estado=1, status=True).first()

    def acta_cerrada(self):
        eActaParalelo = self.convocatoria.actaparalelo_set.filter(status=True)
        if  eActaParalelo.exists():
            return True if eActaParalelo.first().acta.estado == 4 else False
        else:
            False

    def get_voto_miembro_comite(self,miembrocomite):
        voto_miembro_comite = self.votacioncomiteacademico_set.filter(status=True,miembrocomite = miembrocomite)
        return voto_miembro_comite.first() if voto_miembro_comite.exists() else None

    def inscrito_dicto_clase(self):
        from sga.models import ProfesorMateria
        return ProfesorMateria.objects.filter(status=True,profesor__persona__cedula = self.postulante.persona.cedula, materia__asignatura = self.convocatoria.asignaturamalla.asignatura).exists()

    def esta_inscripcionconvocatoria_esta_como_principal_o_alterno_en_el_acta(self,eActaParalelo):
        try:
            eInscripcionConvocatoria =self
            ePersonalAContratar = PersonalAContratar.objects.filter(status=True,inscripcion =eInscripcionConvocatoria,actaparalelo = eActaParalelo)
            if ePersonalAContratar.exists():
                return ePersonalAContratar.first()
            else:
                return None
        except Exception as ex:
            return None


    def esta_inscripcionconvocatoria_esta_como_principal_o_alterno_en_el_acta_validacion_baremo(self,eActaParalelo):
        try:
            eInscripcionConvocatoria =self
            ePersonalAContratar = PersonalAContratar.objects.filter(status=True,inscripcion =eInscripcionConvocatoria,actaparalelo__acta = eActaParalelo.acta)
            return True if ePersonalAContratar.exists() else False
        except Exception as ex:
            return False
class HistorialAprobacionIns(ModeloBase):
    inscripcion = models.ForeignKey(InscripcionConvocatoria, blank=True, null=True, verbose_name=u'Inscripcion convocatoria', on_delete=models.CASCADE)
    observacion = models.TextField(blank=True, null=True, verbose_name=u"Observación postulante")
    estado = models.IntegerField(choices=ESTADO_REVISION, default=1, verbose_name=u'Estado')
    tiporevision = models.IntegerField(choices=TIPO_REVISIONINS, default=1, verbose_name=u'Tipo de revision')


ESTADOS_PROCESO = (
    (0, u'PENDIENTE'),
    (1, u'APROBADO'),
    (2, u'EN PROCESO'),
    (3, u'FINALIZADA'),
    (4, u'RECHAZADO'),
    (5, u'ANULADO'),
    (6, u'ESPERA APROBACIÓN'),
)

class TipoProceso(ModeloBase):
    nombre = models.CharField(default='', max_length=200, blank=True, null=True, verbose_name=u"Nombre")

    def __str__(self):
        return u'%s' % self.nombre

    def en_uso(self):
        return self.proceso_set.filter(status=True).exists()

    def save(self, *args, **kwargs):
        self.nombre = self.nombre.strip().upper()
        super(TipoProceso, self).save(*args, **kwargs)


class Proceso(ModeloBase):
    tipo = models.ForeignKey(TipoProceso, blank=True, null=True, verbose_name=u'Tipo de Proceso', on_delete=models.CASCADE)
    nombre = models.CharField(default='', max_length=200, blank=True, null=True, verbose_name=u"Nombre")
    activo = models.BooleanField(default=True, verbose_name=u"Activo")
    perfil = models.ForeignKey('pdip.PerfilPuestoDip',null=True, blank=True, verbose_name=u"Perfil",on_delete=models.CASCADE)
    version = models.IntegerField(default=1, verbose_name=u'Nro de versión')


    def __str__(self):
        return u'%s' % self.nombre

    def listadopasos(self):
        return self.pasosproceso_set.filter(status=True).order_by('secuencia')

    def tiene_pasos(self):
        return self.pasosproceso_set.filter(status=True).exists()

    def listadorequisitos(self):
        return self.requisitosproceso_set.filter(status=True).order_by('requisito_id')

    def save(self, *args, **kwargs):
        self.nombre = self.nombre.strip().upper()
        super(Proceso, self).save(*args, **kwargs)


class RequisitosProceso(ModeloBase):
    proceso = models.ForeignKey(Proceso, verbose_name=u'Proceso', on_delete=models.CASCADE)
    requisito = models.ForeignKey(Requisito, blank=True, null=True, verbose_name=u'Requisito', on_delete=models.CASCADE)

    def __str__(self):
        return u'%s' % self.proceso


class PasosProceso(ModeloBase):
    proceso = models.ForeignKey(Proceso, blank=True, null=True, verbose_name=u'Proceso', on_delete=models.CASCADE)
    nombre = models.CharField(default='', max_length=300, blank=True, null=True, verbose_name=u"Nombre")
    activo = models.BooleanField(default=True, verbose_name=u"Activo")
    secuencia = models.IntegerField(default=1, verbose_name=u'Secuencia')
    tiporevisor = models.IntegerField(default=0, choices=TIPOREVISOR, verbose_name=u'Estados de validación')
    valida = models.ForeignKey('sagest.DenominacionPuesto',blank=True, null=True, verbose_name=u'Valida Documentación', on_delete=models.CASCADE)
    pasoanterior = models.ForeignKey('self', blank=True, null=True, related_name='paso_anterior', verbose_name='Paso Anterior', on_delete=models.CASCADE)
    numeropaso = models.IntegerField(default=0, verbose_name=u'Número de paso')
    carga = models.ForeignKey('sagest.DenominacionPuesto', related_name='+', blank=True, null=True, verbose_name=u'Carga Documentación', on_delete=models.CASCADE)
    estadovalida = models.IntegerField(default=0, choices=ESTADOS_PROCESO, verbose_name=u'Estados de validación')
    estadorechazado = models.IntegerField(default=0, choices=ESTADOS_PROCESO, verbose_name=u'Estados de rechazado')
    finaliza = models.BooleanField(default=False, verbose_name=u'Fin del proceso')
    habilitacontrato = models.BooleanField(default=False, verbose_name=u'Fin del proceso')
    beneficiario = models.BooleanField(default=False, verbose_name=u'Paso aplica a docente?')
    genera_informe = models.BooleanField(default=False, verbose_name=u'Genera Informe')
    carga_archivo = models.BooleanField(default=False, verbose_name=u'Carga Archivo')
    valida_archivo = models.BooleanField(default=False, verbose_name=u'Valida Archivo')
    leyenda = models.CharField(max_length=1000, blank=True, null=True, verbose_name=u'Mensaje Ayuda')
    tiempoalerta_carga = models.IntegerField(default=0, verbose_name=u'Tiempo de Alerta Carga')
    tiempoalerta_validacion = models.IntegerField(default=0, verbose_name=u'Tiempo de Alerta Validación')

    def __str__(self):
        return u'%s' % self.nombre

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

    def valida_archivo_str(self):
        return 'fa fa-check-circle text-success' if self.habilitacontrato else 'fa fa-times-circle text-error'

    def requisitos(self):
        return self.requisitopasopago_set.filter(status=True).order_by('requisito__nombre')

    def save(self, *args, **kwargs):
        self.nombre = self.nombre.upper()
        self.leyenda = self.leyenda.upper()
        super(PasosProceso, self).save(*args, **kwargs)


class InscripcionInvitacion(ModeloBase):
    inscripcion = models.ForeignKey(InscripcionConvocatoria, blank=True, null=True, verbose_name=u'Para enviarle invitacion de dar clases', on_delete=models.CASCADE)
    pasosproceso = models.ForeignKey(PasosProceso, blank=True, null=True, verbose_name=u'pasos', on_delete=models.CASCADE)
    materia = models.ForeignKey('sga.Materia', blank=True, null=True, verbose_name=u'materia', on_delete=models.CASCADE)
    fechaaceptacion = models.DateTimeField(blank=True, null=True)
    estado = models.IntegerField(choices=ESTADO_REVISION, default=1, verbose_name=u'Estado')
    estadoinvitacion = models.IntegerField(choices=ESTADO_INSCRIPCION_POSTULANTE, default=1, verbose_name=u'Estado invitación')
    archivo = models.FileField(upload_to='invitaciondip/%Y/%m/%d', blank=True, null=True, verbose_name=u'Archivo')
    fecharevisionrequisitos = models.DateTimeField(blank=True, null=True, verbose_name=u"Fecha en que se validarán generalmente los requisitos de contratación")
    fechaarequisitos = models.DateTimeField(blank=True, null=True, verbose_name=u"Fecha en que se aprobaron los requisitos de contratación")
    estadorequisitos = models.IntegerField(choices=ESTADO_REVISION, default=1, verbose_name=u'Estado requisito general')
    observacionrequisitos = models.TextField(blank=True, null=True, verbose_name=u"Observación requisito general")
    actaparalelo = models.ForeignKey("postulaciondip.ActaParalelo", blank=True, null=True, verbose_name=u'Paralelo Docente', on_delete=models.CASCADE)
    configuracionrequisitos = models.BooleanField(verbose_name=u"¿Requisitos configurados completos?" , default = False)

    def __str__(self):
        return u'%s' % self.inscripcion

    class Meta:
        verbose_name = u"Inscripción a Invitación"
        verbose_name_plural = u"Inscripciones a Invitación"
        ordering = ['id']

    def contrato_str(self):
        contrato = self.contratodip_set.filter(status=True).exclude(estado=5).exists()
        return 'fa fa-check-circle text-success' if contrato else 'fa fa-times-circle text-error'

    def tiene_contrato(self):
        return self.contratodip_set.filter(status=True).exclude(estado=5).exists()

    def traer_contrato(self):
        return self.contratodip_set.get(status=True, estado__in=[0,1,2,3,4])

    def estado_contrato(self):
        if self.contratodip_set.filter(status=True).exclude(estado=5).exists():
            contrato = self.contratodip_set.filter(status=True).exclude(estado=5)[0]
            return contrato.color_estado()

    def listadorequisitoscargados(self):
        return self.inscripcionconvocatoriarequisitos_set.filter(status=True).order_by('requisito__requisito__id')
        #return self.inscripcionrequisito_set.filter(status=True).order_by('requisitoproceso__requisito_id')
    def detalle_inscripcionrequisito(self, requisito):
        return self.inscripcionconvocatoriarequisitos_set.filter(requisito=requisito, status=True).first()

    def color_estado(self):
        color, e = 'secondary', self.estado
        if e == 2:
            color = 'success'
        elif e == 3:
            color = 'warning'
        elif e == 4:
            color = 'dark'
        elif e == 5:
            color = 'primary'
        elif e == 6:
            color = 'dark bg-opacity-50'
        return color

    def get_genero(self):
        return self.inscripcion.postulante.persona.es_mujer()

    def nombre_titulo(self):
        persona, titulo4_pn, abreviatura = self.inscripcion.postulante.persona, '', ''
        nombre_title = f'{persona}'.lower().title()
        titulos = persona.titulacion_set.filter(status=True, titulo__nivel__id=4)
        if titulos:
            abreviatura = 'PhD.' if titulos.filter(titulo__abreviatura__icontains="PHD") else 'MSc.'

        return abreviatura + ' ' + nombre_title

    def get_documentos(self):
        return self.documentoinvitacion_set.filter(status=True, estado=1)

    def get_codigo_secuencia_documento(self,request,clasificacion_documento_invitacion_id):
        abreviaturanombre = ''
        documento = ClasificacionDocumentoInvitacion.objects.get(pk=clasificacion_documento_invitacion_id)
        secuencia = SecuenciaDocumentoInvitacion(tipo=documento)
        secuencia.save(request)
        codigo = secuencia.set_secuencia()
        for c in self.inscripcion.postulante.persona.nombre_completo().split(' '):
            abreviaturanombre += c[0] if c.__len__() else ''
        codigodocumento = "ITI-POS-%s-%s-%s" % (abreviaturanombre, "%03d" % codigo, secuencia.anioejercicio)

        return codigodocumento,secuencia

    def generar_acta_aceptacion(self,request,pdf_file):
        try:
            with transaction.atomic():
                CARTA_ACEPTACION_ID = 2
                EDocumentoInvitacion = DocumentoInvitacion.objects.filter(status=True, inscripcioninvitacion=self, clasificacion_id=CARTA_ACEPTACION_ID)
                filename = generar_nombre(f'carta_aceptacion_{self.id}_','aceptacion')+ ".pdf"
                if EDocumentoInvitacion.exists():
                    instance = EDocumentoInvitacion.first()
                    instance.archivo.save(filename, pdf_file, save=True)
                    instance.save(request)
                else:
                    codigodocumento, secuencia = self.get_codigo_secuencia_documento(request, CARTA_ACEPTACION_ID)
                    instance = DocumentoInvitacion(
                        codigo =codigodocumento,
                        clasificacion_id=CARTA_ACEPTACION_ID,
                        secuenciadocumento=secuencia,
                        inscripcioninvitacion=self,
                        archivo=filename
                    )
                    instance.archivo.save(filename, pdf_file)
                    instance.save(request)
        except Exception as ex:
            pass

    def generar_acta_de_invitacion(self,request,pdf_file):
        try:
            with transaction.atomic():
                CARTA_INVITACION_ID = 3
                EDocumentoInvitacion = DocumentoInvitacion.objects.filter(status=True, inscripcioninvitacion=self, clasificacion_id=CARTA_INVITACION_ID)
                filename = generar_nombre(f'carta_invitacion_{self.id}_', 'invitacion')+ ".pdf"
                if EDocumentoInvitacion.exists():
                    instance = EDocumentoInvitacion.first()
                    instance.archivo.save(filename, pdf_file, save=True)
                    instance.save(request)
                else:
                    codigodocumento, secuencia = self.get_codigo_secuencia_documento(request, CARTA_INVITACION_ID)
                    instance = DocumentoInvitacion(
                        codigo =codigodocumento,
                        clasificacion_id=CARTA_INVITACION_ID,
                        secuenciadocumento=secuencia,
                        inscripcioninvitacion=self,
                        archivo=filename
                    )
                    instance.archivo.save(filename, pdf_file)
                    instance.save(request)
        except Exception as ex:
            pass

    def get_carta_de_aceptacion(self):
        CARTA_ACEPTACION_ID = 2
        carta = self.documentoinvitacion_set.filter(status=True,clasificacion_id =CARTA_ACEPTACION_ID)
        return carta.first()

    def get_carta_de_invitacion(self):
        CARTA_INVITACION_ID = 3
        carta = self.documentoinvitacion_set.filter(status=True,clasificacion_id =CARTA_INVITACION_ID)
        return carta.first()

    def notificar_estado_invitacion_a_analistas(self,request,ePersonalApoyoMaestrias = None,eInscripcionInvitacion=None):
        eGrupo = Group.objects.get(pk=422)
        eUsers = eGrupo.user_set.all()
        a = notificar_analistas_estado_invitacion(request, eUsers,ePersonalApoyoMaestrias, eInscripcionInvitacion)
        a.start()

    def get_horario_pregrado(self,periodo):
        from sga.models import Profesor, Clase, ProfesorMateria, DetalleDistributivo, ComplexivoClase, ComplexivoLeccion,Sesion
        from inno.models import HorarioTutoriaAcademica
        try:
            if not Profesor.objects.filter(persona=self.inscripcion.postulante.persona).exists():
                return None
            profesor =Profesor.objects.filter(persona=self.inscripcion.postulante.persona).first()


            data ={}
            hoy = datetime.now().date()
            horaactual = datetime.now().time()
            numerosemanaactual = datetime.today().isocalendar()[1]
            data['hoy'] = hoy
            data['horaactual'] = horaactual
            data['numerosemanaactual'] = numerosemanaactual
            data['diaactual'] = diaactual = hoy.isocalendar()[2]
            data['title'] = u'Horario del profesor'

            data['profesor'] = profesor
            data['semana'] = ['Lunes', 'Martes', 'Miercoles', 'Jueves', 'Viernes', 'Sabado', 'Domingo']
            semana = semanatutoria = [[1, 'Lunes'], [2, 'Martes'], [3, 'Miercoles'], [4, 'Jueves'], [5, 'Viernes'], [6, 'Sabado'], [7, 'Domingo']]
            data['periodo'] = periodo
            data['semana'] = semana
            data['semanatutoria'] = semanatutoria
            clases = Clase.objects.filter(status=True,
                                          activo=True,
                                          materia__fechafinasistencias__gte=hoy,
                                          fin__gte=hoy,
                                          materia__nivel__periodo=periodo,
                                          materia__nivel__periodo__visible=True,
                                          materia__nivel__periodo__visiblehorario=True,
                                          materia__profesormateria__profesor=profesor,
                                          materia__profesormateria__principal=True,
                                          materia__profesormateria__tipoprofesor_id__in=[11, 12, 1, 2, 5, 8, 7, 10, 13, 14, 15, 17],
                                          tipoprofesor_id__in=[11, 12, 1, 2, 5, 8, 7, 10, 13, 14, 15, 17]).order_by('inicio')
            clasesayudante = Clase.objects.values_list('id').filter(status=True,
                                                                    activo=True,
                                                                    materia__fechafinasistencias__gte=hoy,
                                                                    fin__gte=hoy,
                                                                    materia__nivel__periodo=periodo,
                                                                    materia__nivel__periodo__visible=True,
                                                                    materia__nivel__periodo__visiblehorario=True,
                                                                    materia__profesormateria__profesor_id=profesor.id,
                                                                    profesorayudante_id=profesor.id,
                                                                    materia__profesormateria__principal=True).order_by('inicio')
            clases_turnos = profesor.extraer_clases_y_turnos_practica(datetime.now().date(), periodo)
            clases = Clase.objects.filter(
                Q(pk__in=clases.values_list('id')) | Q(pk__in=clasesayudante) | Q(pk__in=clases_turnos[0].values_list('id'))).distinct()
            data['clases'] = clases
            materiasnoprogramadas = ProfesorMateria.objects.filter(status=True,
                                                                   profesor_id=profesor.id,
                                                                   materia__nivel__periodo__visible=True,
                                                                   materia__nivel__periodo__visiblehorario=True,
                                                                   materia__nivel__periodo=periodo,
                                                                   tipoprofesor_id__in=[11, 12, 1, 2, 5, 8, 7, 10, 13, 14, 15, 17],
                                                                   hasta__gt=hoy,
                                                                   activo=True,
                                                                   principal=True).exclude(
                materia__id__in=clases.values_list("materia_id", flat=True), profesor=profesor)
            data['materiasnoprogramadas'] = materiasnoprogramadas
            idturnostutoria = []
            if DetalleDistributivo.objects.filter(distributivo__profesor=profesor, distributivo__periodo=periodo,
                                                  criteriodocenciaperiodo__criterio_id__in=[7]).exists():
                if HorarioTutoriaAcademica.objects.filter(status=True, profesor=profesor, periodo=periodo).exists():
                    idturnostutoria = HorarioTutoriaAcademica.objects.values_list('turno_id').filter(status=True, profesor=profesor,
                                                                                                     periodo=periodo).distinct()
            clasecomplexivo = complexivo = ComplexivoClase.objects.filter(status=True, activo=True,
                                                                          materia__profesor__profesorTitulacion_id=profesor.id, materia__status=True)
            data['clasecomplexivo'] = clasecomplexivo
            sesiones = Sesion.objects.filter(
                Q(turno__id__in=clases.values_list('turno__id').distinct()) | Q(turno__complexivoclase__in=complexivo) | Q(
                    turno__id__in=idturnostutoria)).distinct()
            complexivoabierto = ComplexivoLeccion.objects.filter(status=True, abierta=True,
                                                                 clase__materia__profesor__profesorTitulacion_id=profesor.id)
            disponiblecomplexivo = len(complexivoabierto) == 0
            data['sesiones'] = sesiones
            return data
        except Exception as ex:
            pass

    def get_requisito_cargado_personal_contratar(self,eRequisitoConvocatoria):
        return self.inscripcionconvocatoriarequisitos_set.filter(inscripcioninvitacion= self,requisito = eRequisitoConvocatoria).first()

    def get_personal_a_contratar(self):
        return PersonalAContratar.objects.filter(status=True,inscripcion =self.inscripcion,actaparalelo  = self.actaparalelo).first()

    def notificar_subida_requisitos_completos_a_analistas(self,request,ePersonalApoyoMaestrias = None,eInscripcionInvitacion=None):
        eGrupo = Group.objects.get(pk=422)
        eUsers = eGrupo.user_set.all()
        a = notificar_analistas_requisitos_subidos_por_personal_a_contratar(request, eUsers,ePersonalApoyoMaestrias, eInscripcionInvitacion)
        a.start()
class InscripcionConvocatoriaRequisitos(ModeloBase):
    inscripcioninvitacion = models.ForeignKey(InscripcionInvitacion, verbose_name=u'Inscripcion', on_delete=models.CASCADE, blank=True, null=True)
    requisito = models.ForeignKey(RequisitosConvocatoria, verbose_name=u'Convocatoria', on_delete=models.CASCADE)
    observacion = models.TextField(blank=True, null=True, verbose_name=u"Observación postulante")
    archivo = models.FileField(upload_to='evidenciapostulacion/%Y/%m/%d', blank=True, null=True, verbose_name=u'Archivo')
    estado = models.IntegerField(choices=ESTADO_REVISION, default=1, verbose_name=u'Estado')
    fecharevision = models.DateTimeField(blank=True, null=True, verbose_name=u"Fecha en que se validarán los requisitos de contratación")
    personaaprobador = models.ForeignKey('sga.Persona', blank=True, null=True, verbose_name=u'Quien aprueba', on_delete=models.CASCADE)
    fecha_caducidad = models.DateTimeField(blank=True, null=True, verbose_name=u"Fecha caducidad documento")
    def __str__(self):
        return u'%s' % self.inscripcioninvitacion

    def download_evidencia(self):
        return self.archivo.url if self.archivo else "#"

    def color_estado(self):
        color, e = 'default', self.estado
        if e == 2:
            color = 'success'
        elif e == 3:
            color = 'warning'
        elif e == 4:
            color = 'dark'
        elif e == 5:
            color = 'primary'
        elif e == 6:
            color = 'dark bg-opacity-50'
        return color

    def carga_automatica_requisito_del_sistema(self,request):
        from sga.reportes import run_report_v1
        try:
            CERTIFICADO_DE_REGISTRO_DE_TÍTULOS_SENESCYT = 5
            CERTIFICADO_DE_VOTACION = 11
            TITULO_TERCER = 6
            TITULO_CUARTO_NIVEL = 12
            HOJA_DE_VIDA_DEL_PROFESIONAL = 1
            COPIA_DE_CEDULA_DE_IDENTIDAD_O_PASAPORTE = 2
            ePersona = self.inscripcioninvitacion.inscripcion.postulante.persona
            pdf_merger = PyPDF2.PdfFileMerger()

            if self.requisito.requisito_id == CERTIFICADO_DE_REGISTRO_DE_TÍTULOS_SENESCYT:
                if ePersona.mis_titulaciones().count() > 0:
                    titulos = ePersona.mis_titulaciones().filter(titulo__nivel__nivel__in=[3, 4]).order_by('-titulo__nivel__nivel')
                    if titulos.count() > 0:
                        for titulo in titulos:
                            documento_registro_senecyt = titulo.registroarchivo
                            pdf_merger.append(documento_registro_senecyt)

                        # Crea un archivo temporal para el PDF unido
                        with tempfile.NamedTemporaryFile(delete=False) as temp_pdf:
                            pdf_merger.write(temp_pdf)
                            # Vuelve al principio del archivo antes de leerlo
                            temp_pdf.seek(0)
                            self.archivo.save('registro_senecyt.pdf', File(temp_pdf), save=True)

            if self.requisito.requisito_id == TITULO_TERCER:
                if ePersona.mis_titulaciones().count() > 0:
                    titulos = ePersona.mis_titulaciones().filter(titulo__nivel__nivel__in=[3]).order_by('-titulo__nivel__nivel')
                    if titulos.count() > 0:
                        for titulo in titulos:
                            documento_titulo = titulo.archivo
                            pdf_merger.append(documento_titulo)

                        # Crea un archivo temporal para el PDF unido
                        with tempfile.NamedTemporaryFile(delete=False) as temp_pdf:
                            pdf_merger.write(temp_pdf)
                            # Vuelve al principio del archivo antes de leerlo
                            temp_pdf.seek(0)
                            self.archivo.save('titulo_tercer_nivel.pdf', File(temp_pdf), save=True)

            if self.requisito.requisito_id == TITULO_CUARTO_NIVEL:
                if ePersona.mis_titulaciones().count() > 0:
                    titulos = ePersona.mis_titulaciones().filter(titulo__nivel__nivel__in=[4]).order_by('-titulo__nivel__nivel')
                    if titulos.count() > 0:
                        for titulo in titulos:
                            documento_titulo = titulo.archivo
                            pdf_merger.append(documento_titulo)

                        # Crea un archivo temporal para el PDF unido
                        with tempfile.NamedTemporaryFile(delete=False) as temp_pdf:
                            pdf_merger.write(temp_pdf)
                            # Vuelve al principio del archivo antes de leerlo
                            temp_pdf.seek(0)
                            self.archivo.save('titulo_cuarto_nivel.pdf', File(temp_pdf), save=True)

            if self.requisito.requisito_id == HOJA_DE_VIDA_DEL_PROFESIONAL:
                reporte = None
                tipo = 'pdf'
                paRequest = {
                    'persona':ePersona.pk,
                }
                reporte = Reporte.objects.get(id=634)
                d = run_report_v1(reporte=reporte, tipo=tipo, paRequest=paRequest, request=request)

                if not d['isSuccess']:
                    raise NameError(d['mensaje'])
                else:
                    url_archivo = (SITE_STORAGE + d['data']['reportfile']).replace('\\', '/')
                    ruta_archivo = (url_archivo).replace('//', '/')
                    # Abre el archivo y lee su contenido binario
                    with open(ruta_archivo, 'rb') as archivo_pdf:
                        contenido_pdf = archivo_pdf.read()
                    self.archivo.save('hoja_vida.pdf', ContentFile(contenido_pdf), save=True)

            if self.requisito.requisito_id == COPIA_DE_CEDULA_DE_IDENTIDAD_O_PASAPORTE:
                cedula = ePersona.documentos_personales().cedula
                if cedula:
                    pdf_merger.append(cedula)
                # Crea un archivo temporal para el PDF unido
                with tempfile.NamedTemporaryFile(delete=False) as temp_pdf:
                    pdf_merger.write(temp_pdf)
                    # Vuelve al principio del archivo antes de leerlo
                    temp_pdf.seek(0)
                    self.archivo.save('cedula_o_pasaporte.pdf', File(temp_pdf), save=True)

            if self.requisito.requisito_id == CERTIFICADO_DE_VOTACION:
                papeleta = ePersona.documentos_personales().papeleta
                if papeleta:
                    pdf_merger.append(papeleta)
                # Crea un archivo temporal para el PDF unido
                with tempfile.NamedTemporaryFile(delete=False) as temp_pdf:
                    pdf_merger.write(temp_pdf)
                    # Vuelve al principio del archivo antes de leerlo
                    temp_pdf.seek(0)
                    self.archivo.save('papeleta_votacion.pdf', File(temp_pdf), save=True)


        except Exception as ex:
            pass

    def carga_automatica_requisito_de_la_ultima_convocatoria(self, request,ePersonaAContratar):
        try:
            CERTIFICADO_DE_REGISTRO_DE_TÍTULOS_SENESCYT = 5
            TITULO_TERCER_Y_CUARTO_NIVEL = 6
            HOJA_DE_VIDA_DEL_PROFESIONAL = 1
            COPIA_DE_CEDULA_DE_IDENTIDAD_O_PASAPORTE_Y_PAPELETA_DE_VOTACION = 2
            ePersona = self.inscripcioninvitacion.inscripcion.postulante.persona
            ultima_invitacion = ePersonaAContratar.get_ultima_invitacion_exclude_actual()
            if ultima_invitacion:
                if ultima_invitacion.filter(requisito__requisito = self.requisito.requisito).exists():
                    ultimo_requisito = ultima_invitacion.filter(requisito__requisito = self.requisito.requisito).first()
                    if  ultimo_requisito.archivo != '':
                        url_archivo = (SITE_STORAGE + ultimo_requisito.archivo.url).replace('\\', '/')
                        ruta_archivo = (url_archivo).replace('//', '/')
                        # Abre el archivo y lee su contenido binario
                        with open(ruta_archivo, 'rb') as archivo_pdf:
                            self.archivo.save('requisito_convocatoria_anterior.pdf', File(archivo_pdf), save=True)
                        self.fecha_caducidad = ultimo_requisito.fecha_caducidad
                        self.save(request)
        except Exception as ex:
            pass

    def carga_automatica_requisito_de_la_ultima_convocatoria_todos(self, request,ePersonaAContratar):
        try:
            documento_cargado = False
            ePersona = self.inscripcioninvitacion.inscripcion.postulante.persona
            ultima_invitacion = ePersonaAContratar.get_ultima_invitacion_exclude_actual()
            if ultima_invitacion:
                if ultima_invitacion.filter(requisito__requisito = self.requisito.requisito).exists():
                    ultimo_requisito = ultima_invitacion.filter(requisito__requisito = self.requisito.requisito).first()
                    if  ultimo_requisito.archivo != '':
                        url_archivo = (SITE_STORAGE + ultimo_requisito.archivo.url).replace('\\', '/')
                        ruta_archivo = (url_archivo).replace('//', '/')
                        # Abre el archivo y lee su contenido binario
                        with open(ruta_archivo, 'rb') as archivo_pdf:
                            self.archivo.save('requisito_convocatoria_anterior.pdf', File(archivo_pdf), save=True)
                        self.fecha_caducidad = ultimo_requisito.fecha_caducidad
                        self.save(request)
                        documento_cargado = True
            return documento_cargado
        except Exception as ex:
            pass


ESTADOS_REQUISITO = (
    (0, u'POR CONFIGURAR'),
    (1, u'CARGAR ANALISTA'),
    (2, u'CARGADO'),
    (3, u'CARGAR POSTULANTE'),

)



class HistorialAprobacion(ModeloBase):
    inscripcionrequisito = models.ForeignKey(InscripcionConvocatoriaRequisitos, blank=True, null=True, verbose_name=u'Requisito de la convocatoria del postulante', on_delete=models.CASCADE)
    observacion = models.TextField(blank=True, null=True, verbose_name=u"Observación postulante")
    estado = models.IntegerField(choices=ESTADO_REVISION, default=1, verbose_name=u'Estado')
    tiporevision = models.IntegerField(choices=TIPO_REVISION, default=1, verbose_name=u'Tipo de revision')
    archivo = models.FileField(upload_to='evidenciapostulacion/%Y/%m/%d', blank=True, null=True, verbose_name=u'Archivo')


class HistorialInvitacion(ModeloBase):
    invitacion = models.ForeignKey(InscripcionInvitacion, blank=True, null=True, verbose_name=u'Invitación', on_delete=models.CASCADE)
    pasosproceso = models.ForeignKey(PasosProceso, blank=True, null=True, verbose_name=u'pasos', on_delete=models.CASCADE)
    fechaaceptacion = models.DateTimeField(blank=True, null=True)
    estado = models.IntegerField(choices=ESTADO_REVISION, default=1, verbose_name=u'Estado')
    estadoinvitacion = models.IntegerField(choices=ESTADO_INSCRIPCION_POSTULANTE, default=1, verbose_name=u'Estado invitación')
    observacion = models.TextField(blank=True, null=True, verbose_name=u"Observación")
    personaaprobador = models.ForeignKey('sga.Persona', blank=True, null=True, verbose_name=u'Quien aprueba', related_name='+', on_delete=models.CASCADE)
    archivo = models.FileField(upload_to='invitaciondip/%Y/%m/%d', blank=True, null=True, verbose_name=u'Archivo')

    def __str__(self):
        return u'%s' % self.invitacion

    class Meta:
        verbose_name = u"Historial Invitacion"
        verbose_name_plural = u"Historial Invitaciones"
        ordering = ['id']


class InscripcionRequisito(ModeloBase):
    inscripcioninvitacion = models.ForeignKey(InscripcionInvitacion, blank=True, null=True, verbose_name=u'Para enviarle invitacion de dar clases', on_delete=models.CASCADE)
    requisitoproceso = models.ForeignKey(RequisitosProceso, blank=True, null=True, verbose_name=u'Requisito proceso', on_delete=models.CASCADE)
    archivo = models.FileField(upload_to='evidenciapostulacion/%Y/%m/%d', blank=True, null=True, verbose_name=u'Archivo')
    estado = models.IntegerField(choices=ESTADO_REVISIONDOCUMENTO, default=1, verbose_name=u'Estado')
    fecharevision = models.DateTimeField(blank=True, null=True)
    personaaprobador = models.ForeignKey('sga.Persona', blank=True, null=True, verbose_name=u'Quien aprueba', related_name='+', on_delete=models.CASCADE)
    observacion = models.TextField(blank=True, null=True, verbose_name=u"Observación")

    def __str__(self):
        return u'%s' % self.inscripcioninvitacion

    class Meta:
        verbose_name = u"Inscripcion Requisito"
        verbose_name_plural = u"Inscripcion Requisito"
        ordering = ['id']

    def download_evidencia(self):
        return self.archivo.url


class HistorialAprobacionInscripcion(ModeloBase):
    inscripcionrequisito = models.ForeignKey(InscripcionRequisito, blank=True, null=True, verbose_name=u'Requisito de la convocatoria del postulante', on_delete=models.CASCADE)
    observacion = models.TextField(blank=True, null=True, verbose_name=u"Observación postulante")
    estado = models.IntegerField(choices=ESTADO_REVISION, default=1, verbose_name=u'Estado')
    tiporevision = models.IntegerField(choices=TIPO_REVISION, default=1, verbose_name=u'Tipo de revision')
    persona = models.ForeignKey('sga.Persona', blank=True, null=True, verbose_name=u'Quien aprueba', on_delete=models.CASCADE)

    def __str__(self):
        return u"%s" % self.get_estado_display()

    class Meta:
        verbose_name = u"Historial de Aprobacion de la Inscripcion"
        verbose_name_plural = u"Historial de Aprobacion de las Inscripciones"
        ordering = ['-id']


class RolPersonalApoyo(ModeloBase):
    descripcion = models.TextField(default='', verbose_name=u'Descripcion')

    def __str__(self):
        return u'%s' % self.descripcion

    def save(self, *args, **kwargs):
        self.descripcion = self.descripcion.upper()
        super(RolPersonalApoyo,self).save(*args, **kwargs)

    class Meta:
        verbose_name = u"Rol del Personal"
        verbose_name_plural = u"Roles del Personal"
        ordering = ['-id']

    def en_uso(self):
        return self.personalapoyo_set.filter(status=True).exists()


class PersonalApoyo(ModeloBase):
    persona = models.ForeignKey('sga.Persona', blank=True, null=True, verbose_name=u'Personal de Apoyo', on_delete=models.CASCADE)
    rol = models.ForeignKey(RolPersonalApoyo, blank=True, null=True, verbose_name=u'Rol del Personal de Apoyo', on_delete=models.CASCADE)
    fechadesde = models.DateTimeField(blank=True, null=True, verbose_name=u'Vigencia Personal Desde')
    fechahasta = models.DateTimeField(blank=True, null=True, verbose_name=u'Vigencia Personal Hasta')

    def __str__(self):
        return u'%s (%s)' % (self.persona, self.rol)

    class Meta:
        verbose_name = u"Personal Apoyo Maestría"
        verbose_name_plural = u"Personal Apoyo Maestrías"
        ordering = ['-id']

    def en_uso(self):
        return self.personalapoyomaestria_set.filter(status=True).exists()

    def get_contrato(self):
        return self.persona.contratodip_set.filter(Q(status=True)).order_by('-id').first()

class PersonalApoyoMaestria(ModeloBase):
    personalapoyo = models.ForeignKey(PersonalApoyo, blank=True, null=True, verbose_name=u'Personal de Apoyo',on_delete=models.CASCADE)
    fechainicio = models.DateTimeField(blank=True, null=True, verbose_name=u'Fecha de Inicio Meta')
    fechafin = models.DateTimeField(blank=True, null=True, verbose_name=u'Fecha de Fin Meta')
    carrera = models.ForeignKey(Carrera, null=True, blank=True, verbose_name=u'Carrera', on_delete=models.CASCADE)
    periodo = models.ManyToManyField(Periodo, verbose_name=u'Periodo')

    def __str__(self):
        return u'%s' % self.personalapoyo

    class Meta:
        verbose_name = u"Personal de Apoyo Maestría"
        verbose_name_plural = u"Personal de Apoyo Maestrías"
        ordering = ['-id']

    def get_contrato(self):
        return self.personalapoyo.persona.contratodip_set.filter(Q(status=True)).order_by('-id').first()


class ClasificacionDocumentoInvitacion(ModeloBase):
    descripcion = models.TextField(default='', verbose_name=u'Descripcion', blank=True, null=True)
    abreviatura = models.CharField(verbose_name=u"Abreviatura", max_length=10, blank=True, null=True, default='')
    tipodocumento = models.IntegerField(choices=TIPO_DOCUMENTO_INVITACION, default=1, verbose_name=u'Típo de documento')

    def __str__(self):
        return u'%s' % self.descripcion

    class Meta:
        verbose_name = u"Clasificacion del Documento"
        verbose_name_plural = u"Clasificacion de los Documentos"
        ordering = ['-id']

    def save(self, *args, **kwargs):
        self.descripcion = self.descripcion.upper()
        super(ClasificacionDocumentoInvitacion,self).save(*args, **kwargs)


class SecuenciaDocumentoInvitacion(ModeloBase):
    anioejercicio = models.ForeignKey(AnioEjercicio, verbose_name=u'Año ejercicio', on_delete=models.CASCADE, blank=True, null=True)
    secuencia = models.IntegerField(verbose_name=u'Secuencia', default=0, blank=True, null=True)
    tipo = models.ForeignKey(ClasificacionDocumentoInvitacion, blank=True, null=True, verbose_name=u'Tipo de Documento', on_delete=models.CASCADE)

    def __str__(self):
        return u'%s-%s' % (self.secuencia, self.anioejercicio)

    class Meta:
        verbose_name = u"Secuencia Documento Invitacion"
        verbose_name_plural = u"Secuencia de los Documentos"
        ordering = ['-id']

    def save(self, *args, **kwargs):
        hoy = datetime.now().date()
        aModel = AnioEjercicio.objects.filter(anioejercicio=hoy.year, status=True).first()
        self.anioejercicio = AnioEjercicio.objects.create(anioejercicio=hoy.year) if not aModel else aModel
        # Check if the instance has a primary key (id) assigned
        if self.pk is None:
            # This is an add operation
            numeracion = 1 + null_to_decimal(SecuenciaDocumentoInvitacion.objects.filter(anioejercicio=self.anioejercicio, tipo=self.tipo).aggregate(valor=Max('secuencia'))['valor'])
        else:
            # This is an edit operation
            numeracion = self.secuencia

        self.secuencia = numeracion
        super(SecuenciaDocumentoInvitacion, self).save(*args, **kwargs)

    def set_secuencia(self):
        return self.secuencia

    def get_secuencia_anio(self):
        return f'{self.set_secuencia()}-{self.anioejercicio}'

    def get_anio_secuencia(self):
        return f'{self.anioejercicio}-{self.set_secuencia()}'


class DocumentoInvitacion(ModeloBase):
    secuenciadocumento = models.ForeignKey(SecuenciaDocumentoInvitacion, verbose_name='Secuencia Memo', on_delete=models.CASCADE, blank=True, null=True)
    codigo = models.TextField(default='', verbose_name=u'Código', blank=True, null=True)
    archivo = models.FileField(upload_to='documentospostulaciondip/documentos/%Y', blank=True, null=True, verbose_name=u'Archivo')
    estado = models.IntegerField(choices=ESTADO_REVISION, default=1, verbose_name=u'Estado')
    clasificacion = models.ForeignKey(ClasificacionDocumentoInvitacion, blank=True, null=True, verbose_name=u'Clasificación', on_delete=models.CASCADE)
    inscripcioninvitacion = models.ForeignKey(InscripcionInvitacion, blank=True, null=True, verbose_name=u'Inscripción', on_delete=models.CASCADE)
    informecontratacion = models.ForeignKey("InformeContratacion", blank=True, null=True, verbose_name=u'InformeContratacion', on_delete=models.CASCADE)

    def __str__(self):
        return u'%s - %s' % (self.clasificacion, self.codigo.upper())

    class Meta:
        verbose_name = u"Documento Invitación"
        verbose_name_plural = u"Documentos Invitación"
        ordering = ['-id']

    def get_anio_ejercicio(self):
        hoy = datetime.now().date()
        if AnioEjercicio.objects.values('id').filter(anioejercicio=hoy.year, status=True).exists():
            anio = AnioEjercicio.objects.filter(anioejercicio=hoy.year, status=True).first()
        else:
            anio = AnioEjercicio(anioejercicio=hoy.year)
            anio.save()

        return anio

    def download_link(self):
        return self.archivo.url

    def get_secuencia_documento(self):
        anio = self.get_anio_ejercicio()
        numeracion = SecuenciaDocumentoInvitacion.objects.filter(status=True, anioejercicio=anio, tipo=self.clasificacion).count() + 1
        if not SecuenciaDocumentoInvitacion.objects.values('id').filter(anioejercicio=anio, secuencia=numeracion, tipo=self.clasificacion).exists():
            sdi = SecuenciaDocumentoInvitacion(anioejercicio=anio, secuencia=numeracion, tipo=self.clasificacion)
            sdi.save()
            self.secuenciadocumento = sdi
            self.save()


class HistorialDocumentoInvitacion(ModeloBase):
    documentoinvitacion = models.ForeignKey(DocumentoInvitacion, blank=True, null=True, verbose_name=u'Documento invitacion', on_delete=models.CASCADE)
    archivo = models.FileField(upload_to='documentospostulaciondip/historialdocumentos/%Y/%m/%d', blank=True, null=True, verbose_name=u'Archivo')
    observacion = models.TextField(default='', verbose_name=u'Observacion', blank=True, null=True)
    estado = models.IntegerField(choices=ESTADO_REVISION, default=1, verbose_name=u'Estado')

    def __str__(self):
        return u'%s' % self.documentoinvitacion

    class Meta:
        verbose_name = u"Historial Documento Invitación"
        verbose_name_plural = u"Historial Documentos Invitación"
        ordering = ['-id']


class FirmasDocumentoInvitacion(ModeloBase):
    firma = models.FileField(upload_to='documentospostulaciondip/firmas/%Y/%m/%d', blank=True, null=True, verbose_name=u'Firma')
    cargo = models.ForeignKey(PerfilPuestoDip, blank=True, null=True, verbose_name=u'Cargo', on_delete=models.CASCADE)
    documentoinvitacion = models.ForeignKey(ClasificacionDocumentoInvitacion, blank=True, null=True, verbose_name=u'Tipo de documento', on_delete=models.CASCADE)
    persona = models.ForeignKey('sga.Persona', blank=True, null=True, verbose_name=u'Persona Responsable', on_delete=models.CASCADE)
    responsabilidad = models.TextField(default='', verbose_name=u'Responsabilidad', blank=True, null=True)

    def __str__(self):
        return u'%s' % self.persona

    class Meta:
        verbose_name = u"Documento Invitación"
        verbose_name_plural = u"Documentos Invitación"
        ordering = ['id']


class ComiteAcademicoPosgrado(ModeloBase):
    nombre = models.CharField(verbose_name=u"Nombre", blank=True, null=True, max_length=100)
    abreviatura = models.CharField(verbose_name=u"Abreviatura", blank=True, null=True, max_length=10)
    tipodocente = models.ForeignKey('pdip.PerfilPuestoDip', verbose_name=u"Perfil Puesto", blank=True, null=True, on_delete=models.CASCADE)
    apuntador = models.ForeignKey(Administrativo, verbose_name=u"Apuntador/a", blank=True, null=True, on_delete=models.CASCADE)

    def __str__(self):
        return u"%s - %s" % (self.nombre, self.tipodocente)

    class Meta:
        verbose_name = u"Comité Académico"
        verbose_name_plural = u"Comites Académicos"
        ordering = ['id',]

    def get_integrantes(self):
        return self.integrantecomiteacademicoposgrado_set.filter(status=True)


    def asignar_permiso_al_modulo(self,request):
        for integrante in self.integrantecomiteacademicoposgrado_set.filter(status=True):
            integrante.asignar_permiso_al_modulo(request)

class TipoPersonal(ModeloBase):
    descripcion = models.TextField(verbose_name=u"Descripcion", blank=True, null=True)

    def __str__(self):
        return "%s" % self.descripcion

    class Meta:
        verbose_name = u"Tipo Personal"
        verbose_name_plural = u"Tipo de Personal"
        ordering = ['id']

    def save(self, *args, **kwargs):
        self.descripcion = self.descripcion.strip().upper()
        super(TipoPersonal, self).save(*args, **kwargs)

TIPO_CARGO_CHOICE  = (
    (0, 'N/A'),
    (1, 'E'),
    (2, 'S'),
    (3, 'D'),
)

class IntegranteComiteAcademicoPosgrado(ModeloBase):
    cargo = models.ForeignKey(PerfilPuestoDip, blank=True, null=True, verbose_name=u'Cargo', on_delete=models.CASCADE)
    comite = models.ForeignKey(ComiteAcademicoPosgrado, blank=True, null=True, verbose_name=u'Comité académico', on_delete=models.CASCADE)
    persona = models.ForeignKey('sga.Persona', blank=True, null=True, verbose_name=u'Persona responsable', on_delete=models.CASCADE)
    tipo_cargo = models.IntegerField(choices=TIPO_CARGO_CHOICE, default=0, verbose_name=u'tipo acta', blank=True,null=True)
    tipo = models.ForeignKey(TipoPersonal, blank=True, null=True, verbose_name=u'Tipo de integrante', on_delete=models.CASCADE)

    def __str__(self):
        return u'%s - %s' % (self.comite.abreviatura if self.comite.abreviatura else '', self.persona)

    def asignar_permiso_al_modulo(self,request):
        eGrupo = Group.objects.get(pk=425)
        user = self.persona.usuario
        if user not in eGrupo.user_set.all():
            eGrupo.user_set.add(user)
            eGrupo.save()
        if not self.persona.administrativo_set.exists():
            administrativo = Administrativo(persona=self.persona,fechaingreso=datetime.now().date(), activo=True)
            administrativo.save(request)
            grupo = Group.objects.get(pk=variable_valor('ADMINISTRATIVOS_GROUP_ID'))
            grupo.user_set.add(self.persona.usuario)
            grupo.save()
            self.persona.crear_perfil(administrativo=administrativo)
            log(u'Adiciono administrativo: %s' % administrativo, request, "add")

    def get_votos_realizados(self,actaparalelo):
        try:
            return self.votacioncomiteacademico_set.filter(status=True,actaparalelo=actaparalelo)
        except Exception as ex:
            return None
    def get_generar_registro_baremo_miembro_comite(self,request,eActaParalelo,eInscripcionConvocatoria):
        try:
            eVotacionComiteAcademicos = VotacionComiteAcademico.objects.filter(actaparalelo =eActaParalelo,miembrocomite = self,inscripcion = eInscripcionConvocatoria,status=True)
            if not eVotacionComiteAcademicos.exists():
                eVotacionComiteAcademico = VotacionComiteAcademico(
                    actaparalelo=eActaParalelo,
                    miembrocomite=self,
                    inscripcion=eInscripcionConvocatoria
                )
                eVotacionComiteAcademico.save(request)
                eVotacionComiteAcademico.actaparalelo.acta.guardar_recorrido_acta_seleccion_docente(request,
                                                                                    actaparalelo=eVotacionComiteAcademico.actaparalelo,
                                                                                    persona=self.persona,
                                                                                    observacion=f"Realizó voto: por {eVotacionComiteAcademico} - {self.cargo}",
                                                                                    archivo=None)
            else:
                eVotacionComiteAcademico = eVotacionComiteAcademicos.first()

            return eVotacionComiteAcademico
        except Exception as ex:
            return None


    class Meta:
        verbose_name = u"Integrante Comité Académico"
        verbose_name_plural = u"Integrantes Comité Académico"
        ordering = ['id']

TIPO_GENERACION_ACTA = (
    (1, 'ORIGINAL'),
    (2, 'REPROGRAMACIÓN')
)
TIPO_FORMATO_ACTA = (
    (1, 'Acta Normal'),
    (2, 'Acta Invitado'),
)

ESTADO_ACTA = (
    (1, 'PENDIENTE'),
    (2, 'REVISIÓN'),
    (3, 'POR LEGALIZAR'),
    (4, 'LEGALIZADA'),
    (5, 'REPROGRAMACIÓN')
)

ESTADO_INFORME_CONTRATACION = (
    (1, 'PENDIENTE'),
    (2, 'POR LEGALIZAR'),
    (3, 'LEGALIZADA')
)




VALOR_X_HORA = (
    (1, '0'),
    (2, '50'),
    (3, '60')
)

class ActaSeleccionDocente(ModeloBase):
    comite = models.ForeignKey(ComiteAcademicoPosgrado, blank=True, null=True, verbose_name=u'Comité Académico', on_delete=models.CASCADE)
    lugar = models.TextField(verbose_name=u"Lugar", blank=True, null=True)
    fecha_generacion = models.DateTimeField(verbose_name=u"Fecha de generación", blank=True, null=True)
    fecha_legalizacion = models.DateTimeField(verbose_name=u"Fecha de legalización", blank=True, null=True)
    plazo_generacion = models.DateTimeField(verbose_name=u"Plazo de generación", blank=True, null=True)
    plazo_legalizacion = models.DateTimeField(verbose_name=u"Plazo de legalización", blank=True, null=True)
    archivo = models.FileField(upload_to='actaselecciondocente/%Y', blank=True, null=True, verbose_name=u'Acta de Ganador', max_length=600)
    codigo = models.IntegerField(verbose_name=u'Código', blank=True, null=True)
    cerrada = models.BooleanField(verbose_name=u"¿Está cerrada?", blank=True, null=True)
    observacion_ep = models.TextField(verbose_name=u"Observacion para evaluación de perfil", blank=True, null=True)
    tipoacta = models.IntegerField(choices=TIPO_GENERACION_ACTA, default=1, verbose_name=u'tipo acta')
    detalle = models.TextField(verbose_name=u"Detalle", blank=True, null=True)
    estado = models.IntegerField(choices=ESTADO_ACTA, default=1, verbose_name=u'estado acta')
    convocadopor = models.ForeignKey(Administrativo, blank=True, null=True, verbose_name=u'Convocado por', related_name='+', on_delete=models.CASCADE)
    organizadopor = models.ForeignKey(Administrativo, blank=True, null=True, verbose_name=u'Organizado por', on_delete=models.CASCADE)
    tipo_formato_acta = models.IntegerField(choices=TIPO_FORMATO_ACTA, default=1, verbose_name=u'tipo formato acta')
    detalle_resolucion = models.TextField(verbose_name=u"Detalle resolución", blank=True, null=True)
    secuenciadocumento = models.ForeignKey(SecuenciaDocumentoInvitacion, verbose_name='Secuencia', on_delete=models.CASCADE, blank=True, null=True)
    numero = models.TextField(default='', verbose_name=u'Número', blank=True, null=True)
    enviada_a_comite = models.BooleanField(verbose_name=u"enviada a comite", default=False)
    fecha_hora_inicio_revision_comite = models.DateTimeField(verbose_name=u"Fecha hora inicio revision comite",blank=True, null=True)
    fecha_hora_fin_revision_comite = models.DateTimeField(verbose_name=u"Fecha hora fin revision comite", blank=True, null=True)



    def __str__(self):
        return u'[%s] %s' % (self.get_codigo(), self.comite.nombre)

    class Meta:
        verbose_name = u"Acta de Comité Académico de las Escuelas de Posgrado"
        verbose_name_plural = u"Actas de Comité Académico de las Escuelas de Posgrado"
        ordering = ['id']

    def puede_realizar_votacion_segun_cronograma(self):
        try:
            hoy = datetime.now()
            if self.fecha_hora_fin_revision_comite:
                puede = True if self.fecha_hora_fin_revision_comite >= hoy  else False
            else:
                puede = False
            return puede
        except Exception as ex:
            return  False

    def get_anio_ejercicio(self):
        hoy = datetime.now().date()
        if AnioEjercicio.objects.values('id').filter(anioejercicio=hoy.year, status=True).exists():
            anio = AnioEjercicio.objects.filter(anioejercicio=hoy.year, status=True).first()
        else:
            anio = AnioEjercicio(anioejercicio=hoy.year)
            anio.save()

        return anio

    def get_secuencia(self):
        anio = self.get_anio_ejercicio()
        numeracion = SecuenciaDocumentoInvitacion.objects.filter(status=True, anioejercicio=anio, tipo_id = 5).count() + 1
        if not SecuenciaDocumentoInvitacion.objects.values('id').filter(anioejercicio=anio, secuencia=numeracion, tipo_id = 5).exists():
            sdi = SecuenciaDocumentoInvitacion(anioejercicio=anio, secuencia=numeracion, tipo_id = 5)
            sdi.save()
            self.secuenciadocumento = sdi
            self.numero = f"{numeracion} - {anio}"
            self.codigo = numeracion
            self.save()

    def save(self, *args, **kwargs):
        super(ActaSeleccionDocente, self).save(*args, **kwargs)

    def get_existen_paralelos_pendiente_prerevision(self):
        return self.actaparalelo_set.filter(status=True,estadoprerevision = 1).exists()

    def get_existen_paralelos_rechazados_prerevision(self):
        return self.actaparalelo_set.filter(status=True,estadoprerevision = 3).exists()

    def get_paralelos_rechazados_prerevision(self):
        return self.actaparalelo_set.filter(status=True,estadoprerevision = 3)

    def volver_a_pendientes_paralelos_rechazados(self,request,persona):
        try:
           for eActaParalelo in self.get_paralelos_rechazados_prerevision():
               eActaParalelo.estadoprerevision = 1
               eActaParalelo.save(request)
               eActaParalelo.guardar_historial_acta_paralelo(request,persona, 1,'Paralelo reiniciado para su revisión respectiva')
        except Exception as ex:
            pass

    def notificar_acta_revisada_a_la_gestion_de_posgrado(self,request,ePersonalApoyoMaestrias = None):
        eGrupo = Group.objects.get(pk=422)
        eUsers = eGrupo.user_set.all()
        a = notificar_acta_revisada(request,eUsers,ePersonalApoyoMaestrias,self)
        a.start()

    def notificar_acta_reprogramacion_gestion_posgrado_comite(self,request,ePersonalApoyoMaestrias = None):
        eGrupo = Group.objects.get(pk=422)
        eUsers = eGrupo.user_set.all()
        a = notificar_acta_revisada_reprogramacion(request,eUsers,ePersonalApoyoMaestrias,self)
        a.start()


    def notificar_a_la_persona_que_le_toca_firmar(self,request):
        integrantecomiteacademicoposgrado = self.get_debe_firmar()
        if not integrantecomiteacademicoposgrado == None:
            if not HistorialActaSeleccionDocente.objects.filter(acta=self, firmadopor=integrantecomiteacademicoposgrado, status=True).values('id').exists():
                ePersona = integrantecomiteacademicoposgrado.persona
                a = notificar_persona_a_firmar(request,ePersona,self)
                a.start()

    def notificar_acta_firmada_por_todos(self,request,ePersonalApoyoMaestrias = None):
        eGrupo = Group.objects.get(pk=422)
        eUsers = eGrupo.user_set.all()
        a = notificar_analistas_acta_firmada_completa(request, eUsers,ePersonalApoyoMaestrias, self)
        a.start()

    def notificar_acta_votacion_por_todos_los_paralelos(self,request,ePersonalApoyoMaestrias = None):
        eGrupo = Group.objects.get(pk=422)
        eUsers = eGrupo.user_set.all()
        a = notificar_analistas_acta_votacion_completa(request, eUsers,ePersonalApoyoMaestrias, self)
        a.start()

    def notificar_votacion_al_comite(self,request):
        a = proceso_notificar_votacion_comite(request=request,eIntegranteComiteAcademicoPosgrado = self.get_integrante_comite(),eActaSeleccionDocente = self)
        a.start()

    def notificar_acta_para_revision(self,request):
        from sga.models import Persona
        ePersonas = Persona.objects.filter(status=True, pk__in =variable_valor('REVISION_ACTA_COMITE_POSGRADO_PERSONA_IDS'))
        a = notificar_acta_para_ser_revisada(request, ePersonas, self)
        a.start()

    def archivo_url(self):
        return self.archivo.url if self.archivo else '#'

    def get_codigo(self):
        return  self.numero

    def get_codigo_informe(self):
        return "%s-ACEP-%s" % (self.get_codigo(), self.fecha_generacion.year if self.fecha_generacion else self.fecha_creacion.year)

    def get_experta_gestion_administrativa_posgrado(self):
        from sga.models import Persona
        return Persona.objects.get(pk=variable_valor('ID_EXPERTO_GESTION_POSGRADO'))

    def get_firmas(self):
        filtro = Q(status=True, tipo__in=[1]) if self.get_convocatorias().filter(convocatoria__tipodocente=20).exists() else Q(status=True)
        return self.comite.get_integrantes().filter(filtro)

    def get_totalpostulantes(self):
        return InscripcionConvocatoria.objects.filter(convocatoria__in=self.actaparalelo_set.filter(status=True).values_list('convocatoria', flat=True), convocatoria__status=True, status=True)

    def get_totalpostulantesaprobados(self):
        return InscripcionConvocatoria.objects.filter(convocatoria__in=self.actaparalelo_set.filter(status=True).values_list('convocatoria', flat=True), estado=2, convocatoria__status=True, status=True)

    def get_totalpostulantesrechazados(self):
        return InscripcionConvocatoria.objects.filter(convocatoria__in=self.actaparalelo_set.filter(status=True).values_list('convocatoria', flat=True), convocatoria__status=True, status=True).exclude(estado=2)

    def get_planaccion(self):
        return self.planaccion_set.filter(integrantecomiteacademico__status=True, status=True)

    def get_paralelo_ganador(self):
        # Donde 1 = PRINCIPAL
        return self.actaparalelo_set.filter(status=True, personalacontratar__tipo=1, personalacontratar__status=True)

    def porcentaje_configuracion(self, progress=25):
        ids = self.actaparalelo_set.filter(status=True).values_list('convocatoria',flat=True).distinct().order_by('convocatoria')
        eConvocatorias = Convocatoria.objects.filter(pk__in = ids)
        paralelos0 = sum([x.paralelos if x else 0 for x in eConvocatorias])
        total_paralelos = self.actaparalelo_set.filter(status=True).count()
        tiene_pers = self.actaparalelo_set.filter(personalacontratar__status=True, acta__status=True, status=True).values('id').distinct().count()
        tiene_hora = self.actaparalelo_set.filter(horarioclases__status=True, acta__status=True, status=True).values('id').distinct().count()
        tiene_plan = self.planaccion_set.filter(status=True, acta__status=True).values('id').exists()
        if tiene_pers: progress += ((tiene_pers/total_paralelos) * 25) if total_paralelos else 0
        if self.tipo_formato_acta== 2:
            progress += ((total_paralelos/total_paralelos) * 25) if total_paralelos else 0
        else:
            if tiene_hora: progress += ((tiene_hora/total_paralelos) * 25) if total_paralelos else 0
        if tiene_plan: progress += 25
        return progress

    def get_integrante_comite(self):
        return self.comite.integrantecomiteacademicoposgrado_set.filter(status=True)

    def puede_legalizar_acta(self, persona):
        return self.comite.integrantecomiteacademicoposgrado_set.values('id').filter(persona=persona, status=True).exists()

    def total_firmas_por_acta(self):
        return self.historialactaselecciondocente_set.filter(status=True).values('firmadopor').count()

    def plazo_legalizar_acta(self, plazo=10):
        hoy = datetime.now().date() + timedelta(plazo)
        return self.get_paralelo_ganador().annotate(plazo=( F('inicio') - hoy)).order_by('inicio').first()

    def get_ganador(self):
        return PersonalAContratar.objects.filter(actaparalelo__acta=self, tipo=1, status=True)

    def get_personalacontratar(self):
        return PersonalAContratar.objects.filter(actaparalelo__acta=self, tipo__in=[1,2, 3], status=True)

    def get_alternos(self):
        return PersonalAContratar.objects.filter(actaparalelo__acta=self, tipo__in=[2, 3], actaparalelo__status=True, status=True)

    def get_convocatorias(self):
        return self.actaparalelo_set.filter(status=True).order_by('inicio')

    def guardar_de_todas_las_convocatorias_los_principales_y_alternos(self,request):
        for eActaParalelo in self.get_convocatorias():
            eActaParalelo.get_personal().update(status=False)

        for eActaParalelo in self.get_convocatorias():
            eActaParalelo.guardar_automatico_principales_de_toda_el_acta(request)

        for eActaParalelo in self.get_convocatorias():
            eActaParalelo.guardar_automatico_alternos_banco_elegible_de_toda_el_acta(request)

    def get_encabezado_convocatorias_sin_repetir(self):
        convocatorias_id= self.actaparalelo_set.values_list('convocatoria_id',flat =True).filter(status=True).order_by('inicio')
        return Convocatoria.objects.filter(status=True, pk__in =convocatorias_id)

    def get_convocatorias_asignaturas(self):
        return self.actaparalelo_set.filter(status=True
                                            ).distinct('convocatoria__asignaturamalla__asignatura_id').order_by(
            'convocatoria__asignaturamalla__asignatura_id', 'inicio'
        ).select_related(
            'convocatoria__asignaturamalla'
        )

    def get_total_vacantes(self, asignatura=None):
        filtro = Q(status=True) if not asignatura else Q(convocatoria__asignaturamalla__asignatura=asignatura, status=True)
        ids = self.actaparalelo_set.filter(filtro).values_list('convocatoria', flat=True).distinct().order_by('convocatoria')
        eConvocatorias = Convocatoria.objects.filter(pk__in=ids)
        return sum([x.vacantes if x else 0 for x in eConvocatorias])

    def get_plazo_legalizacion(self, **kwargs):
        from sga.funciones import variable_valor

        val = kwargs.pop('plazo', variable_valor('PLAZO_LEGALIZAR_ACTA_SELECCION'))
        plazo_minimo = inicio = datetime.now().date() + timedelta(val)
        if paralelo := self.actaparalelo_set.values('inicio').filter(status=True).order_by('inicio').first():
            inicio = paralelo['inicio']

        result = (inicio - plazo_minimo).days
        return result if result >= 0 else 0

    def tiene_invitaciones(self):
        return InscripcionInvitacion.objects.values('id').filter(actaparalelo__acta=self, status=True).exists()

    def obtener_actas_paralelos_sin_horario(self):
        id_paralelos=[]
        eActaParalelo = ActaParalelo.objects.filter(status=True,acta=self)
        for acta in eActaParalelo:
            eHorarioClases = HorarioClases.objects.filter(status=True, actaparalelo = acta)
            if not eHorarioClases.exists():
                id_paralelos.append(acta.pk)
        actas_paralelos_sin_horario = ActaParalelo.objects.filter(pk__in=id_paralelos)
        return actas_paralelos_sin_horario

    def configurada_100_porciento(self):
        return True if  self.porcentaje_configuracion()== 100 else False

    def configurada_75_porciento(self):
        return True if  self.porcentaje_configuracion()>= 75 else False

    def lista_para_enviar_a_revision(self):
        PENDIENTE = 1
        return True if self.configurada_100_porciento() and self.estado == PENDIENTE else False

    def puede_suprimir_acta_enviada_a_revision(self):
        REVISION_ACTA = 2
        return True if self.configurada_100_porciento() and self.estado == REVISION_ACTA else False

    def firmada_por_todos(self):
       return True if self.total_firmas_por_acta() == self.get_integrante_comite().count() else False

    def firmada_por_almenos_uno(self):
       return True if self.total_firmas_por_acta() > 0 else False

    def no_firmada_por_nadie(self):
       return True if self.total_firmas_por_acta() == 0 else False

    def enviada_a_revision_or_lista_para_legalizar(self):
        REVISION_ACTA = 2
        LEGALIZAR= 3
        return True if self.estado == REVISION_ACTA  or self.estado == LEGALIZAR  else False

    def esta_legalizada(self):
        LEGALIZADA= 4
        return True if self.estado == LEGALIZADA  else False

    def esta_reprogramacion(self):
        REPROGRAMACION= 5
        return True if self.estado == REPROGRAMACION  else False

    def enviada_a_revision(self):
        REVISION_ACTA = 2
        return True if self.estado == REVISION_ACTA  else False

    def iniciar_proceso_legalizar_acta(self,request):
        LEGALIZAR = 3
        self.estado = LEGALIZAR
        self.save(request)
        ePersonalApoyoMaestrias = None
        eActaParalelo = ActaParalelo.objects.filter(status=True, acta=self)
        if eActaParalelo.exists():
            carrera = eActaParalelo.first().convocatoria.carrera
            periodo = eActaParalelo.first().convocatoria.periodo
            ePersonalApoyoMaestrias = PersonalApoyoMaestria.objects.filter(status=True, carrera=carrera,periodo=periodo)

        self.notificar_acta_revisada_a_la_gestion_de_posgrado(request, ePersonalApoyoMaestrias)
        self.notificar_a_la_persona_que_le_toca_firmar(request)

    def lista_para_legalizar(self):
        return True if self.estado == 3 else False

    def todos_los_principales_estan_pendiente(self):
        PENDIENTE = 1
        todos_los_pendientes = self.get_ganador().filter(estado=PENDIENTE).exclude(actaparalelo__acta__estado=4).count()
        todos = self.get_ganador().count()
        return True if todos == todos_los_pendientes else False

    def existe_almenos_un_principal_pendiente(self):
        PENDIENTE = 1
        total_pendientes = self.get_ganador().filter(estado=PENDIENTE).count()
        return True if total_pendientes > 0 else False

    def existe_almenos_un_principal_en_reprogramacion(self):
        REPROGRAMACION = 2
        total_reprogramacion = self.get_ganador().filter(estado=REPROGRAMACION).count()
        return True if total_reprogramacion > 0 else False

    def obtener_reprogramaciones(self):
        REPROGRAMACION = 2
        reprogramaciones = self.get_ganador().filter(estado=REPROGRAMACION)
        return reprogramaciones

    def obtener_cantidad_ganadores(self):
        ganadores = self.get_ganador().count()
        return ganadores

    def existe_director_de_posgrado(self):
        return True if self.comite.get_integrantes().filter(Q(status=True),  Q(cargo__nombre__contains='DECANO DE POSGRADO') |Q(cargo__nombre__contains='DIRECTOR DE POSGRADO') | Q(cargo__nombre__contains='VICERRECTOR DE INVESTIGACIÓN Y POSGRADO')).exists() else False

    def existe_coordinador_de_programa_de_posgrado(self):
        return True if self.comite.get_integrantes().filter(status=True).filter(Q(cargo__nombre__icontains='coordinador del programa') | Q(cargo__nombre__icontains='coordinadora del programa') | Q(cargo__nombre__icontains='coordinador/a del programa')).exists() else False

    def existe_profesor_a_fin_programa(self):
        return True if self.comite.get_integrantes().filter(status=True).filter(Q(cargo__nombre__icontains='PROFESOR A FIN AL PROGRAMA')|Q(cargo__nombre__icontains='PROFESOR AFÍN AL PROGRAMA')).exists() else False

    def existe_director_de_la_escuela_de_posgrado(self):
        return True if  self.comite.get_integrantes().filter(status=True).filter(Q(cargo__nombre__icontains='DIRECTOR DE LA ESCUELA') |Q(cargo__nombre__icontains='DIRECTORA DE LA ESCUELA')).exists() else False

    def get_director_de_posgrado(self):
        return self.comite.get_integrantes().filter(Q(status=True),Q(cargo__nombre__contains='DECANO DE POSGRADO') | Q(cargo__nombre__contains='DIRECTOR DE POSGRADO') | Q(cargo__nombre__contains='VICERRECTOR DE INVESTIGACIÓN Y POSGRADO')).first()

    def get_coordinador_de_programa_de_posgrado(self):
        return self.comite.get_integrantes().filter(status=True).filter(Q(cargo__nombre__icontains='coordinador del programa') | Q(cargo__nombre__icontains='coordinadora del programa') | Q(cargo__nombre__icontains='coordinador/a del programa') | Q(cargo__nombre__icontains='coordinador de maestria')| Q(cargo__nombre__icontains='coordinadora de maestria')).first()

    def get_director_de_la_escuela_de_posgrado(self):
        return self.comite.get_integrantes().filter(status=True).filter(Q(cargo__nombre__icontains='DIRECTOR DE LA ESCUELA') |Q(cargo__nombre__icontains='DIRECTORA DE LA ESCUELA')).first()

    def get_profesor_a_fin_programa(self):
        return self.comite.get_integrantes().filter(status=True).filter(Q(cargo__nombre__icontains='PROFESOR A FIN AL PROGRAMA')|Q(cargo__nombre__icontains='PROFESOR AFÍN AL PROGRAMA')).first()

    def existe_plan_de_accion_de_director_posgrado(self):
        return True if self.planaccion_set.filter(status=True, integrantecomiteacademico= self.get_director_de_posgrado()).exists() else False

    def existe_plan_de_accion_de_coordinador_de_programa_de_maestria(self):
        return True if self.planaccion_set.filter(status=True, integrantecomiteacademico= self.get_coordinador_de_programa_de_posgrado()).exists() else False

    def existe_plan_de_accion_director_o_cordionador_de_programa(self):
        return True if self.existe_plan_de_accion_de_director_posgrado() or self.existe_plan_de_accion_de_coordinador_de_programa_de_maestria() else False

    def generar_acta_reprogramacion(self,request):
        try:
            REPROGRAMACION = 2
            hoy = datetime.now().date()
            with transaction.atomic():
                codigo = null_to_decimal(ActaSeleccionDocente.objects.filter(fecha_creacion__year=hoy.year).aggregate(code=Max('codigo'))[ 'code']) + 1
                reprogramaciones = self.obtener_reprogramaciones()
                eNewActaSeleccionDocente = ActaSeleccionDocente(
                    comite=self.comite,
                    lugar='',
                    codigo=codigo,
                    plazo_generacion=hoy + timedelta(variable_valor('PLAZO_GENERAR_ACTA_SELECCION')),
                    plazo_legalizacion=hoy + timedelta(variable_valor('PLAZO_LEGALIZAR_ACTA_SELECCION')),
                    tipoacta=REPROGRAMACION
                )
                eNewActaSeleccionDocente.save(request)
                log(u'genero acta de reprogramacion: %s' % eNewActaSeleccionDocente, request, "add")
                for ePersonalAContratar in reprogramaciones:
                    eNewConvocatoria = self.generar_nueva_convocatoria(request,ePersonalAContratar.actaparalelo.convocatoria)

                    eActaParalelo = ActaParalelo(
                        acta=eNewActaSeleccionDocente,
                        paralelo=ePersonalAContratar.actaparalelo.paralelo,
                        convocatoria= eNewConvocatoria,
                        inicio= hoy,
                        fin = hoy  + timedelta(days=3)
                    )
                    eActaParalelo.save(request)
                    log(u'Generar reprogramacion completa: newacta, newconvocatoria new paralelo: %s' % eActaParalelo, request, "add")
        except Exception as ex:
            transaction.set_rollback(True)

    def generar_nueva_convocatoria(self,request,convocaroria_anterior):
        eConvocatoria = Convocatoria(asignaturamalla=convocaroria_anterior.asignaturamalla,
                                     nombre='Repr: ' + convocaroria_anterior.nombre,
                                     fechainicio=convocaroria_anterior.fechainicio,
                                     fechafin=convocaroria_anterior.fechafin,
                                     activo=False,
                                     tipodocente=convocaroria_anterior.tipodocente,
                                     carrera=convocaroria_anterior.carrera,
                                     periodo=convocaroria_anterior.periodo,
                                     vacantes=1,
                                     paralelos=1,
                                     tipo=convocaroria_anterior.tipo)
        eConvocatoria.save(request)

        return eConvocatoria

    def guardar_historial_reprogramacion(self, request,ePersonalAContratar,persona):
        eHistorialReprogramacion = HistorialReprogramacion(
            personalcontratar=ePersonalAContratar,
            fecha=datetime.now().date(),
            persona=persona
        )
        eHistorialReprogramacion.save(request)

    def eliminar_personal_a_contratar_y_acta_paralelo_de_la_acta_original(self, request,ePersonalAContratar):
        ePersonalAContratar.status = False
        ePersonalAContratar.save(request)
        ePersonalAContratar.actaparalelo.status = False
        ePersonalAContratar.actaparalelo.save(request)

    def quitar_del_acta_las_reprogramaciones(self,request,persona):
        try:
            REPROGRAMACION = 2
            with transaction.atomic():
                reprogramaciones = self.obtener_reprogramaciones()
                for ePersonalAContratar in reprogramaciones:
                    self.eliminar_personal_a_contratar_y_acta_paralelo_de_la_acta_original(request,ePersonalAContratar)
                    self.guardar_historial_reprogramacion(request,ePersonalAContratar,persona)

        except Exception as ex:
            transaction.set_rollback(True)

    def get_historial_reprogramacion(self):
        return HistorialReprogramacion.objects.filter(status=True,personalcontratar__actaparalelo__acta = self)

    def get_integrante(self,persona):
        integrante = self.comite.get_integrantes().filter(persona=persona, status=True).first()
        return integrante if integrante else None

    def get_debe_firmar(self):
        eOrdenFirmaActaSeleccionDocente = OrdenFirmaActaSeleccionDocente.objects.filter(status=True).order_by('orden')
        for orden in eOrdenFirmaActaSeleccionDocente:
            eintegrante = eval('self.' + orden.funcion)
            if not HistorialActaSeleccionDocente.objects.filter(acta=self, firmadopor=eintegrante, status=True).values('id').exists():
                return eintegrante

    def get_puede_firma_integrante_segun_orden(self,persona):
        eOrdenFirmaActaSeleccionDocente =  OrdenFirmaActaSeleccionDocente.objects.filter(status=True).order_by('orden')
        integrante_anterior_firmo = True
        eintegrante_anterior=None
        integrante = self.get_integrante(persona)
        for orden in eOrdenFirmaActaSeleccionDocente:
            eintegrante = eval('self.' + orden.funcion)
            if eintegrante:
                if integrante.pk == eintegrante.pk:
                    if orden.orden > 1:
                        orden_anterior = OrdenFirmaActaSeleccionDocente.objects.get(orden=orden.orden - 1,status=True)
                        eintegrante_anterior = eval('self.' + orden_anterior.funcion)
                        integrante_anterior_firmo = True if HistorialActaSeleccionDocente.objects.filter(acta=self, firmadopor=eintegrante_anterior, status=True).values('id').exists() else False
                    break
            else:
                return False, f"No esta configurado para firmar, no esta registrado el {orden} como parte del tribunal"

        if integrante_anterior_firmo:
            return True, eintegrante_anterior
        else:
            eintegrante_anterior = self.get_debe_firmar()
            return False,eintegrante_anterior

    def firmada_por_todos_los_integrante(self):
       return self.firmada_por_todos()

    def guardar_alternos_como_banco_elegibles(self):
        alternos = self.get_alternos()
        for alterno in alternos:
            alterno.inscripcion.estado = 11
            alterno.save()

    def generar_plan_de_accion_automatico(self,request):
        if self.existe_director_de_posgrado():
            ePlanAccion = PlanAccion(
                acta=self,
                integrantecomiteacademico=self.get_director_de_posgrado(),
                resolucion="Se compromete desde la Dirección de Posgrado gestionar los procesos de contratación establecido en la presente acta."
            )
            ePlanAccion.save(request)

        if self.existe_coordinador_de_programa_de_posgrado():
            ePlanAccion = PlanAccion(
                acta=self,
                integrantecomiteacademico=self.get_coordinador_de_programa_de_posgrado(),
                resolucion="Coordinar, supervisar y controlar el buen desarrollo académico de el/los módulos a ejecutarse; además de brindar el asesoramiento administrativo al/los profesionales seleccionados en conjunto con el Asistente de Posgrado 2, para la entrega de los documentos habilitantes para iniciar el proceso de contratación y posterior consignación de sus haberes, en los tiempos oportunos."
            )
            ePlanAccion.save(request)

    def get_votaron_por_todos_los_paralelos(self):
        votaron_todos = True
        if self.get_convocatorias():
            for actaparalelo in self.get_convocatorias():
                if not actaparalelo.get_votaron_todos_por_paralelo():
                    votaron_todos=False
                    pass
        else:
            votaron_todos = False
        return votaron_todos

    def get_voto_diretor_por_todos_los_paralelos(self):
        votaron_todos = True
        if self.get_convocatorias():
            for actaparalelo in self.get_convocatorias():
                if not actaparalelo.get_voto_director_todos_paralelo():
                    votaron_todos=False
                    pass
        else:
            votaron_todos = False
        return votaron_todos

    def get_cumple_horario_horas_acompanamiento_docente(self):
        cumple = True
        if self.get_convocatorias():
            for actaparalelo in self.get_convocatorias():
                if not actaparalelo.get_total_horas_horario_docente() == actaparalelo.convocatoria.get_horas_componente_docente():
                    cumple = False
                    pass
                break
        else:
            cumple = False
        return cumple

    def cantidad_votos_completos_por_miembro_comite(self):
        votos_completos = {
            "coordinador": 0,
            "director_escuela": 0,
            "director_posgrado": 0,
            "profesor_a_fin": 0
        }

        if self.get_convocatorias():
            for actaparalelo in self.get_convocatorias():
                if actaparalelo.get_voto_almenos_1_coordinador():
                    votos_completos["coordinador"] += 1
                if actaparalelo.get_voto_almenos_1_director_escuela() :
                    votos_completos["director_escuela"] += 1
                if actaparalelo.get_voto_almenos_1_director_posgrado():
                    votos_completos["director_posgrado"] += 1
                if actaparalelo.get_voto_almenos_1_profesor_a_fin():
                    votos_completos["profesor_a_fin"] += 1

        return votos_completos

    def realizo_votos_miembro_comite(self,actaparalelo, persona):
        try:
            votaron_todos = True
            miembro = actaparalelo.acta.get_integrante(persona)
            cantidad_inscritos_elegibles = actaparalelo.cantidad_de_postulantes_elegibles()
            votaron_todos = True if cantidad_inscritos_elegibles == miembro.get_votos_realizados(actaparalelo).count()  else False
            return votaron_todos
        except Exception as ex:
            return False

    def actualizar_documeto_pdf_acta(self,request):
        try:
            a = actualizar_acta_seleccion_docente(request,self)
            a.start()
        except Exception as ex:
            pass

    def get_cumple_con_horas_docente(self):
        cumplen = True
        if self.get_convocatorias():
            for actaparalelo in self.get_convocatorias():
                if not actaparalelo.get_total_horas_horario_docente() == actaparalelo.convocatoria.get_horas_componente_docente():
                    cumplen=False
                    break
        else:
            cumplen = False
        return cumplen

    def get_tiene_horario_en_todas_las_fechas(self):
        cumplen = True
        if self.get_convocatorias():
            for actaparalelo in self.get_convocatorias():
                if not actaparalelo.get_tiene_horario_en_fecha_inicio_y_fecha_fin_de_paralelo():
                    cumplen=False
                    break
        else:
            cumplen = False
        return cumplen

    def get_configuracion_general_acta_seleccion_docente(self):
        eConfiguracionGeneralActaSeleccionDocente = ConfiguracionGeneralActaSeleccionDocente.objects.filter(status=True)
        return eConfiguracionGeneralActaSeleccionDocente.first() if eConfiguracionGeneralActaSeleccionDocente.exists() else None

    def get_existe_almenos1_personal_a_contratar_con_requisitos_aprobados(self):
        cumple_almenos_1_requisitos_contratacion = False
        if self.get_convocatorias():
            for actaparalelo in self.get_convocatorias():
                if actaparalelo.get_ganador().estado== 4:
                    cumple_almenos_1_requisitos_contratacion=True
                    break
        else:
            cumple_almenos_1_requisitos_contratacion = False
        return cumple_almenos_1_requisitos_contratacion

    def get_personal_a_contratar_cumple_requisitos_contratacion(self):
        ids_personal_contratar = []
        if self.get_convocatorias():
            for actaparalelo in self.get_convocatorias():
                if actaparalelo.get_ganador().estado == 4:
                    ids_personal_contratar.append(actaparalelo.get_ganador().pk)

        return PersonalAContratar.objects.filter(Q(status=True),Q(pk__in=ids_personal_contratar))

    def get_personal_contratar_informe_contratacion(self):
        return DetalleInformeContratacion.objects.filter(status=True,personalcontratar__actaparalelo__acta = self)

    def guardar_recorrido_acta_seleccion_docente(self, request=None,actaparalelo=None,persona=None,observacion = None,archivo =None):
        try:
            hoy = datetime.now()
            eRecorridoActaSeleccionDocente = RecorridoActaSeleccionDocente(
                acta=self,
                actaparalelo=actaparalelo,
                persona=persona,
                fecha=hoy,
                observacion=observacion,
                archivo=archivo
            )
            eRecorridoActaSeleccionDocente.save(request)
        except Exception as ex:
            pass

    def todos_los_miembros_del_comite_votaron_por_todos_los_banco_de_elegibles(self):
        try:
            votaron_todos = True
            if self.get_convocatorias():
                for actaparalelo in self.get_convocatorias():
                    cantidad_inscritos_elegibles = actaparalelo.cantidad_de_postulantes_elegibles()
                    if not cantidad_inscritos_elegibles == actaparalelo.get_votos_coordinador().count() == actaparalelo.get_votos_profesor_a_fin().count() == actaparalelo.get_votos_director_escuela().count() == actaparalelo.get_votos_director_posgrado().count():
                        votaron_todos = False
                        break
            else:
                votaron_todos = False
            return votaron_todos
        except Exception as ex:
            return False

    def ejecutar_en_segundo_plano_guardado_principal_alternos(self,request):
        try:
            eGrupo = Group.objects.get(pk=422)
            eUsers = eGrupo.user_set.all()
            a = proceso_guardado_principal_alternos_de_todas_las_convocatorias_de_los_paralelos(request, self,eUsers)
            a.start()
        except Exception as ex:
            pass

class HistorialActaSeleccionDocente(ModeloBase):
    acta = models.ForeignKey(ActaSeleccionDocente, blank=True, null=True, verbose_name=u'Acta selección docente', on_delete=models.CASCADE)
    firmadopor = models.ForeignKey(IntegranteComiteAcademicoPosgrado, blank=True, null=True, verbose_name=u'Firmado por', on_delete=models.CASCADE)
    fecha_legalizacion = models.DateTimeField(verbose_name=u"Fecha de firma", blank=True, null=True)
    observacion = models.TextField(verbose_name=u"Observación", blank=True, null=True, default='')
    archivo = models.FileField(upload_to='actahistorial/', blank=True, null=True,verbose_name=u"Acta firmada",max_length=600)
    def __str__(self):
        return u'%s' % self.acta

    class Meta:
        verbose_name = u"Historial del acta de selección"
        verbose_name_plural = u"Historial del acta de selección"
        ordering = ['id']


ESTADO_REVISION_PARALELO = (
    (1, 'PENDIENTE'),
    (2, 'APROBADO'),
    (3, 'RECHAZADO'),
)


class ActaParalelo(ModeloBase):
    acta = models.ForeignKey(ActaSeleccionDocente, blank=True, null=True, verbose_name=u'Acta', on_delete=models.CASCADE)
    paralelo = models.ForeignKey(Paralelo, blank=True, null=True, verbose_name=u'Paralelos', on_delete=models.CASCADE)
    inicio = models.DateField(blank=True, null=True, verbose_name=u'Fecha de inicio del módulo', db_index=True)
    fin = models.DateField(blank=True, null=True, verbose_name=u'Fecha fin del módulo', db_index=True)
    convocatoria = models.ForeignKey(Convocatoria, blank=True, null=True, verbose_name=u'Convocatoria', on_delete=models.CASCADE)
    estado = models.IntegerField(choices=ESTADO_PARALELOS_EN_ACTA, default=1, verbose_name=u'Estado')
    estadoprerevision = models.IntegerField(choices=ESTADO_REVISION_PARALELO, default=1, verbose_name=u'Estado')

    def __str__(self):
        return u'%s %s - [%s al %s]' % (self.convocatoria.asignaturamalla.asignatura if self.convocatoria else '', self.paralelo, self.inicio.strftime("%d-%m-%Y"), self.fin.strftime("%d-%m-%Y"))

    class Meta:
        verbose_name = u"Paralelo del Acta"
        verbose_name_plural = u"Paralelos del Acta"
        ordering = ['id']

    def get_display_estadoprerevision(self):
        estado = ''
        if self.estadoprerevision == 1:
            estado = f"<span class='badge rounded-pill bg-primary'>{self.get_estadoprerevision_display()}</span>"

        if self.estadoprerevision == 2:
            estado = f"<span class='badge rounded-pill bg-success'>{self.get_estadoprerevision_display()}</span>"

        if self.estadoprerevision == 3:
            estado =  f"<span class='badge rounded-pill bg-warning'>{self.get_estadoprerevision_display()}</span>"

        return estado

    def guardar_historial_acta_paralelo(self,request,persona,estadoprerevision,observacion):
        try:
            eActaParaleloHistorial = ActaParaleloHistorial(
                actaparalelo=self,
                estadoprerevision=estadoprerevision,
                observacion=observacion,
                persona=persona
            )
            eActaParaleloHistorial.save(request)
        except Exception as ex:
            pass

    def get_historial_acta_paralelo(self):
        return self.actaparalelohistorial_set.filter(status=True)

    def get_horario(self):
        return self.horarioclases_set.filter(status=True)

    def get_horario_v2(self):
        _response = []
        for dia in DIAS_CHOICES:
            if turnos := self.horarioclases_set.filter(dia=dia[0], status=True).values_list('turno__id', flat=True).distinct():
                _response.append({'dia': f"{dia[1]}".capitalize(), 'turno': Turno.objects.filter(id__in=turnos, status=True)})
        return _response

    def get_horario_lunes_viernes(self):
        return self.horarioclases_set.filter(dia__in=[1,2,3,4,5], status=True)

    def get_horario_sabado_domingo(self):
        return self.horarioclases_set.filter(dia__in=[0, 6, 7], status=True)

    def get_personal(self):
        return self.personalacontratar_set.filter(status=True)

    def get_personal_principal(self):
        # Asumiendo que 1 = PRINCIPAL en la base
        return self.personalacontratar_set.filter(tipo__id=1, status=True)

    def get_personal_alterno(self):
        # Asumiendo que 2 = ALTERNO en la base
        return self.personalacontratar_set.filter(tipo__in=[2, 3], status=True)

    def get_media(self):
        if self.inicio and self.fin:
            diferencia = self.fin - self.inicio
            return self.inicio + timedelta(days=diferencia.days / 2)

    def en_uso(self):
        return self.get_horario().values('id').exists() or self.personalacontratar_set.filter(status=True).values('id').exists()

    def get_turno_por_fecha(self, dia):
        return self.horarioclases_set.filter(inicio__lte=dia, fin__gte=dia, dia=dia.weekday() + 1, status=True).first()

    def get_dias_intermedios(self):
        horarios = self.get_horario().order_by('inicio')
        newlist = []
        for h in horarios: newlist += [x for x in daterange(h.inicio, h.fin + timedelta(1)) if h.dia == x.weekday() + 1 and not x == self.inicio and not x == self.fin]

        return newlist

    def get_ganador(self):
        return self.personalacontratar_set.filter(tipo__id=1, status=True).first()

    def clonar_horario_de_la_convocatoria_en_el_acta(self,request):
        if not HorarioClases.objects.filter(status=True, actaparalelo=self).exists():
            for horario in self.convocatoria.get_horario():
                eHorarioClases = HorarioClases(
                    dia=horario.dia,
                    actaparalelo=self,
                    inicio=horario.inicio,
                    fin=horario.fin,
                )
                eHorarioClases.save(request)
                for turno in horario.turno.all():
                    eHorarioClases.turno.add(turno)
                log(u"Copia horario de la convocaotria al paralelo de la acta", request, 'add')

    def get_miembro_comite_coordinador(self):
        eActaSeleccionDocente = self.acta
        return eActaSeleccionDocente.get_coordinador_de_programa_de_posgrado() if eActaSeleccionDocente.existe_coordinador_de_programa_de_posgrado() else None

    def get_miembro_comite_profesor_a_fin(self):
        eActaSeleccionDocente = self.acta
        return eActaSeleccionDocente.get_profesor_a_fin_programa() if eActaSeleccionDocente.existe_profesor_a_fin_programa() else None

    def get_miembro_comite_director_escuela(self):
        eActaSeleccionDocente = self.acta
        return eActaSeleccionDocente.get_director_de_la_escuela_de_posgrado() if eActaSeleccionDocente.existe_director_de_la_escuela_de_posgrado() else None

    def get_miembro_comite_director_posgrado(self):
        eActaSeleccionDocente = self.acta
        return eActaSeleccionDocente.get_director_de_posgrado() if eActaSeleccionDocente.existe_director_de_posgrado() else None

    def get_votos_coordinador(self):
        coordinador = self.get_miembro_comite_coordinador()
        try:
            return coordinador.get_votos_realizados(self)
        except Exception as ex:
            return None

    def get_votos_profesor_a_fin(self):
        profesor_a_fin = self.get_miembro_comite_profesor_a_fin()
        try:
            return profesor_a_fin.get_votos_realizados(self)
        except Exception as ex:
            return None

    def get_votos_director_escuela(self):
        director_escuela = self.get_miembro_comite_director_escuela()
        try:
            return director_escuela.get_votos_realizados(self)
        except Exception as ex:
            return None

    def get_votos_director_posgrado(self):
        director_posgrado = self.get_miembro_comite_director_posgrado()
        try:
            return director_posgrado.get_votos_realizados(self)
        except Exception as ex:
            return None

    def get_votos_coordinador_principal(self):
        try:
            return self.get_votos_coordinador().filter(tipo_id=1).first() if self.get_votos_coordinador().filter(tipo_id=1).exists() else None
        except Exception as ex:
            return None

    def get_baremo_coordinador_principal(self,eInscripcionConvocatoria = None):
        try:
            if eInscripcionConvocatoria:
                votacioncomiteacademico = self.get_votos_coordinador().filter(tipo_id=1).first() if self.get_votos_coordinador().filter(tipo_id=1).exists() else None
                eBaremoComiteAcademico = BaremoComiteAcademico.objects.filter(status=True, votacioncomiteacademico=votacioncomiteacademico,votacioncomiteacademico__inscripcion =eInscripcionConvocatoria )
            else:
                votacioncomiteacademico = self.get_votos_coordinador().filter(
                    tipo_id=1).first() if self.get_votos_coordinador().filter(tipo_id=1).exists() else None
                eBaremoComiteAcademico = BaremoComiteAcademico.objects.filter(status=True,
                                                                              votacioncomiteacademico=votacioncomiteacademico)
            return  eBaremoComiteAcademico.aggregate(total_puntaje=Sum('puntaje')) if eBaremoComiteAcademico else None
        except Exception as ex:
            return None

    def get_votos_coordinador_alterno_1(self):
        try:
            return self.get_votos_coordinador().filter(tipo_id=2).first() if self.get_votos_coordinador().filter(tipo_id=2).exists() else None
        except Exception as ex:
            return None

    def get_baremo_coordinador_alterno_1(self,eInscripcionConvocatoria = None):
        try:
            if eInscripcionConvocatoria:
                votacioncomiteacademico = self.get_votos_coordinador().filter( tipo_id=2).first() if self.get_votos_coordinador().filter(tipo_id=2).exists() else None
                eBaremoComiteAcademico = BaremoComiteAcademico.objects.filter(status=True,votacioncomiteacademico=votacioncomiteacademico,votacioncomiteacademico__inscripcion =eInscripcionConvocatoria )
            else:
                votacioncomiteacademico = self.get_votos_coordinador().filter(tipo_id=2).first() if self.get_votos_coordinador().filter(tipo_id=2).exists() else None
                eBaremoComiteAcademico = BaremoComiteAcademico.objects.filter(status=True,votacioncomiteacademico=votacioncomiteacademico)
            return eBaremoComiteAcademico.aggregate(total_puntaje=Sum('puntaje')) if eBaremoComiteAcademico else None

        except Exception as ex:
            return None

    def get_votos_coordinador_alterno_2(self):
        try:
            return self.get_votos_coordinador().filter(tipo_id=3).first() if self.get_votos_coordinador().filter(tipo_id=3).exists() else None
        except Exception as ex:
            return None

    def get_baremo_coordinador_alterno_2(self,eInscripcionConvocatoria = None):
        try:
            if eInscripcionConvocatoria:
                votacioncomiteacademico= self.get_votos_coordinador().filter(tipo_id=3).first() if self.get_votos_coordinador().filter(tipo_id=3).exists() else None
                eBaremoComiteAcademico = BaremoComiteAcademico.objects.filter(status=True, votacioncomiteacademico=votacioncomiteacademico,votacioncomiteacademico__inscripcion =eInscripcionConvocatoria )
            else:
                votacioncomiteacademico = self.get_votos_coordinador().filter(
                    tipo_id=3).first() if self.get_votos_coordinador().filter(tipo_id=3).exists() else None
                eBaremoComiteAcademico = BaremoComiteAcademico.objects.filter(status=True,
                                                                              votacioncomiteacademico=votacioncomiteacademico)
            return eBaremoComiteAcademico.aggregate(total_puntaje=Sum('puntaje')) if eBaremoComiteAcademico else None
        except Exception as ex:
            return None

    def get_votos_profesor_a_fin_principal(self):
        try:
            return self.get_votos_profesor_a_fin().filter(tipo_id=1).first() if self.get_votos_profesor_a_fin().filter(tipo_id=1).exists() else None
        except Exception as ex:
            return None

    def get_baremo_profesor_a_fin_principal(self,eInscripcionConvocatoria = None):
        try:
            if eInscripcionConvocatoria:
                votacioncomiteacademico= self.get_votos_profesor_a_fin().filter(tipo_id=1).first() if self.get_votos_profesor_a_fin().filter(tipo_id=1).exists() else None
                eBaremoComiteAcademico = BaremoComiteAcademico.objects.filter(status=True, votacioncomiteacademico=votacioncomiteacademico,votacioncomiteacademico__inscripcion =eInscripcionConvocatoria )
            else:
                votacioncomiteacademico = self.get_votos_profesor_a_fin().filter(tipo_id=1).first() if self.get_votos_profesor_a_fin().filter(tipo_id=1).exists() else None
                eBaremoComiteAcademico = BaremoComiteAcademico.objects.filter(status=True,votacioncomiteacademico=votacioncomiteacademico)
            return eBaremoComiteAcademico.aggregate(total_puntaje=Sum('puntaje')) if eBaremoComiteAcademico else None
        except Exception as ex:
            return None

    def get_votos_profesor_a_fin_alterno_1(self):
        try:
            return self.get_votos_profesor_a_fin().filter(tipo_id=2).first() if self.get_votos_profesor_a_fin().filter(tipo_id=2).exists() else None
        except Exception as ex:
            return None

    def get_baremo_profesor_a_fin_alterno_1(self,eInscripcionConvocatoria = None):
        try:
            if eInscripcionConvocatoria:
                votacioncomiteacademico = self.get_votos_profesor_a_fin().filter(tipo_id=2).first() if self.get_votos_profesor_a_fin().filter(tipo_id=2).exists() else None
                eBaremoComiteAcademico = BaremoComiteAcademico.objects.filter(status=True, votacioncomiteacademico=votacioncomiteacademico,votacioncomiteacademico__inscripcion =eInscripcionConvocatoria )
            else:
                votacioncomiteacademico = self.get_votos_profesor_a_fin().filter(
                    tipo_id=2).first() if self.get_votos_profesor_a_fin().filter(tipo_id=2).exists() else None
                eBaremoComiteAcademico = BaremoComiteAcademico.objects.filter(status=True,
                                                                              votacioncomiteacademico=votacioncomiteacademico)
            return eBaremoComiteAcademico.aggregate(total_puntaje=Sum('puntaje')) if eBaremoComiteAcademico else None
        except Exception as ex:
            return None

    def get_votos_profesor_a_fin_alterno_2(self):
        try:
            return self.get_votos_profesor_a_fin().filter(tipo_id=3).first() if self.get_votos_profesor_a_fin().filter(tipo_id=3).exists() else None
        except Exception as ex:
            return None

    def get_baremo_profesor_a_fin_alterno_2(self,eInscripcionConvocatoria = None):
        try:
            if eInscripcionConvocatoria:
                votacioncomiteacademico =  self.get_votos_profesor_a_fin().filter(tipo_id=3).first() if self.get_votos_profesor_a_fin().filter(tipo_id=3).exists() else None
                eBaremoComiteAcademico = BaremoComiteAcademico.objects.filter(status=True, votacioncomiteacademico=votacioncomiteacademico,votacioncomiteacademico__inscripcion =eInscripcionConvocatoria )
            else:
                votacioncomiteacademico = self.get_votos_profesor_a_fin().filter(
                    tipo_id=3).first() if self.get_votos_profesor_a_fin().filter(tipo_id=3).exists() else None
                eBaremoComiteAcademico = BaremoComiteAcademico.objects.filter(status=True,
                                                                              votacioncomiteacademico=votacioncomiteacademico)
            return eBaremoComiteAcademico.aggregate(total_puntaje=Sum('puntaje')) if eBaremoComiteAcademico else None
        except Exception as ex:
            return None

    def get_votos_director_escuela_principal(self):
        try:
            return self.get_votos_director_escuela().filter(tipo_id=1).first() if self.get_votos_director_escuela().filter(tipo_id=1).exists() else None
        except Exception as ex:
            return None

    def get_baremo_director_escuela_principal(self,eInscripcionConvocatoria = None):
        try:
            if eInscripcionConvocatoria:
                votacioncomiteacademico = self.get_votos_director_escuela().filter(tipo_id=1).first() if self.get_votos_director_escuela().filter(tipo_id=1).exists() else None
                eBaremoComiteAcademico = BaremoComiteAcademico.objects.filter(status=True, votacioncomiteacademico=votacioncomiteacademico,votacioncomiteacademico__inscripcion =eInscripcionConvocatoria )
            else:
                votacioncomiteacademico = self.get_votos_director_escuela().filter(
                    tipo_id=1).first() if self.get_votos_director_escuela().filter(tipo_id=1).exists() else None
                eBaremoComiteAcademico = BaremoComiteAcademico.objects.filter(status=True,
                                                                              votacioncomiteacademico=votacioncomiteacademico)
            return eBaremoComiteAcademico.aggregate(total_puntaje=Sum('puntaje')) if eBaremoComiteAcademico else None
        except Exception as ex:
            return None

    def get_votos_director_escuela_alterno_1(self):
        try:
            return self.get_votos_director_escuela().filter(tipo_id=2).first() if self.get_votos_director_escuela().filter(tipo_id=2).exists() else None
        except Exception as ex:
            return None

    def get_baremo_director_escuela_alterno_1(self,eInscripcionConvocatoria = None):
        try:
            if eInscripcionConvocatoria:
                votacioncomiteacademico = self.get_votos_director_escuela().filter(tipo_id=2).first() if self.get_votos_director_escuela().filter(tipo_id=2).exists() else None
                eBaremoComiteAcademico = BaremoComiteAcademico.objects.filter(status=True,votacioncomiteacademico=votacioncomiteacademico,votacioncomiteacademico__inscripcion =eInscripcionConvocatoria )
            else:
                votacioncomiteacademico = self.get_votos_director_escuela().filter(
                    tipo_id=2).first() if self.get_votos_director_escuela().filter(tipo_id=2).exists() else None
                eBaremoComiteAcademico = BaremoComiteAcademico.objects.filter(status=True,
                                                                              votacioncomiteacademico=votacioncomiteacademico)
            return eBaremoComiteAcademico.aggregate(total_puntaje=Sum('puntaje')) if eBaremoComiteAcademico else None
        except Exception as ex:
            return None

    def get_votos_director_escuela_alterno_2(self):
        try:
            return self.get_votos_director_escuela().filter(tipo_id=3).first() if self.get_votos_director_escuela().filter(tipo_id=3).exists() else None
        except Exception as ex:
            return None

    def get_baremo_director_escuela_alterno_2(self,eInscripcionConvocatoria = None):
        try:
            if eInscripcionConvocatoria:
                votacioncomiteacademico = self.get_votos_director_escuela().filter(tipo_id=3).first() if self.get_votos_director_escuela().filter(tipo_id=3).exists() else None
                eBaremoComiteAcademico = BaremoComiteAcademico.objects.filter(status=True,   votacioncomiteacademico=votacioncomiteacademico,votacioncomiteacademico__inscripcion =eInscripcionConvocatoria )
            else:
                votacioncomiteacademico = self.get_votos_director_escuela().filter(
                    tipo_id=3).first() if self.get_votos_director_escuela().filter(tipo_id=3).exists() else None
                eBaremoComiteAcademico = BaremoComiteAcademico.objects.filter(status=True,
                                                                              votacioncomiteacademico=votacioncomiteacademico)
            return eBaremoComiteAcademico.aggregate(total_puntaje=Sum('puntaje')) if eBaremoComiteAcademico else None
        except Exception as ex:
            return None

    def get_votos_director_posgrado_principal(self):
        try:
            return self.get_votos_director_posgrado().filter(tipo_id=1).first() if self.get_votos_director_posgrado().filter(tipo_id=1).exists() else None
        except Exception as ex:
            return None

    def get_baremo_director_posgrado_principal(self,eInscripcionConvocatoria = None):
            try:
                if eInscripcionConvocatoria:
                    votacioncomiteacademico = self.get_votos_director_posgrado().filter(tipo_id=1).first() if self.get_votos_director_posgrado().filter(tipo_id=1).exists() else None
                    eBaremoComiteAcademico = BaremoComiteAcademico.objects.filter(status=True, votacioncomiteacademico=votacioncomiteacademico,votacioncomiteacademico__inscripcion =eInscripcionConvocatoria )
                else:
                    votacioncomiteacademico = self.get_votos_director_posgrado().filter(
                        tipo_id=1).first() if self.get_votos_director_posgrado().filter(tipo_id=1).exists() else None
                    eBaremoComiteAcademico = BaremoComiteAcademico.objects.filter(status=True,
                                                                                  votacioncomiteacademico=votacioncomiteacademico)
                return eBaremoComiteAcademico.aggregate(total_puntaje=Sum('puntaje')) if eBaremoComiteAcademico else None
            except Exception as ex:
                return None

    def get_votos_director_posgrado_alterno_1(self):
        try:
            return self.get_votos_director_posgrado().filter(tipo_id=2).first() if self.get_votos_director_posgrado().filter(tipo_id=2).exists() else None
        except Exception as ex:
            return None

    def get_baremo_director_posgrado_alterno_1(self,eInscripcionConvocatoria = None):
        try:
            if eInscripcionConvocatoria:
                votacioncomiteacademico = self.get_votos_director_posgrado().filter(tipo_id=2).first() if self.get_votos_director_posgrado().filter(tipo_id=2).exists() else None
                eBaremoComiteAcademico = BaremoComiteAcademico.objects.filter(status=True, votacioncomiteacademico=votacioncomiteacademico,votacioncomiteacademico__inscripcion =eInscripcionConvocatoria )
            else:
                votacioncomiteacademico = self.get_votos_director_posgrado().filter(
                    tipo_id=2).first() if self.get_votos_director_posgrado().filter(tipo_id=2).exists() else None
                eBaremoComiteAcademico = BaremoComiteAcademico.objects.filter(status=True,
                                                                              votacioncomiteacademico=votacioncomiteacademico)
            return eBaremoComiteAcademico.aggregate(total_puntaje=Sum('puntaje')) if eBaremoComiteAcademico else None
        except Exception as ex:
            return None

    def get_votos_director_posgrado_alterno_2(self):
        try:
            return self.get_votos_director_posgrado().filter(tipo_id=3).first() if self.get_votos_director_posgrado().filter(tipo_id=3).exists() else None
        except Exception as ex:
            return None

    def get_baremo_director_posgrado_alterno_2(self,eInscripcionConvocatoria = None):
        try:
            if eInscripcionConvocatoria:
                votacioncomiteacademico = self.get_votos_director_posgrado().filter(tipo_id=3).first() if self.get_votos_director_posgrado().filter(tipo_id=3).exists() else None
                eBaremoComiteAcademico = BaremoComiteAcademico.objects.filter(status=True,votacioncomiteacademico=votacioncomiteacademico,votacioncomiteacademico__inscripcion =eInscripcionConvocatoria )
            else:
                votacioncomiteacademico = self.get_votos_director_posgrado().filter(tipo_id=3).first() if self.get_votos_director_posgrado().filter(tipo_id=3).exists() else None
                eBaremoComiteAcademico = BaremoComiteAcademico.objects.filter(status=True, votacioncomiteacademico=votacioncomiteacademico)
            return eBaremoComiteAcademico.aggregate(total_puntaje=Sum('puntaje')) if eBaremoComiteAcademico else None
        except Exception as ex:
            return None

    def get_voto_almenos_1_coordinador(self):
        try:
            if self.get_votos_coordinador().filter(tipo_id__in=(1, 2, 3)).exists():
                return self.get_votos_coordinador().filter(tipo_id__in=(1,2,3)).exists()
            else:
                if self.get_votos_coordinador().exists():
                    return self.get_votos_coordinador().exists()
        except Exception as ex:
            return False

    def get_voto_almenos_1_profesor_a_fin(self):
        try:
            if self.get_votos_profesor_a_fin().filter(tipo_id__in=(1, 2, 3)).exists():
                return self.get_votos_profesor_a_fin().filter(tipo_id__in=(1,2,3)).exists()
            else:
                if self.get_votos_profesor_a_fin().exists():
                    return self.get_votos_profesor_a_fin().exists()

        except Exception as ex:
            return False

    def get_voto_almenos_1_director_escuela(self):
        try:
            if self.get_votos_director_escuela().filter(tipo_id__in=(1, 2, 3)).exists():
                return self.get_votos_director_escuela().filter(tipo_id__in=(1,2,3)).exists()
            else:
                if self.get_votos_director_escuela().exists():
                    return self.get_votos_director_escuela().exists()
        except Exception as ex:
            return False

    def get_voto_almenos_1_director_posgrado(self):
        try:
            if self.get_votos_director_posgrado().filter(tipo_id__in=(1,2,3)).exists():
                return self.get_votos_director_posgrado().filter(tipo_id__in=(1,2,3)).exists()
            else:
                if self.get_votos_director_posgrado().exists():
                    return self.get_votos_director_posgrado().exists()
        except Exception as ex:
            return False

    def get_votaron_todos_por_paralelo(self):
        return True if self.get_voto_almenos_1_coordinador() and self.get_voto_almenos_1_profesor_a_fin() and self.get_voto_almenos_1_director_escuela() and self.get_voto_almenos_1_director_posgrado() else False

    def get_voto_director_todos_paralelo(self):
        return True if self.get_voto_almenos_1_director_posgrado() else False

    def get_votaron_todos_por_paralelo_sin_director_posgrado(self):
        return True if self.get_voto_almenos_1_coordinador() and self.get_voto_almenos_1_profesor_a_fin() and self.get_voto_almenos_1_director_escuela()  else False

    def get_notificar_director_para_que_vote(self,request):
        votaron_todos_sin_director = self.get_votaron_todos_por_paralelo_sin_director_posgrado()
        if votaron_todos_sin_director:
            a = notificar_realizar_votacion_director_posgrado(request, self)
            a.start()

    def valida_choque_horario_pregrado(self,eHorarioClases,eInscripcionConvocatoria):
        from sga.models import Clase, ProfesorMateria
        try:
            persona = eInscripcionConvocatoria.postulante.persona
            for horario in eHorarioClases:
                lista_turnos = horario.turno.all()
                dia = horario.dia
                inicio = horario.inicio
                fin = horario.fin
                profesormateria = ProfesorMateria.objects.filter(profesor__persona=persona, materia__cerrado=False,
                                                                 materia__inicio__lte=inicio, materia__fin__gte=fin)
                for pm in profesormateria:
                    tipoprofesor = pm.tipoprofesor
                    periodo = pm.materia.nivel.periodo
                    profesor = pm.profesor
                    materia = pm.materia
                    for turno in lista_turnos:
                        claseconflicto = Clase.objects.filter(
                            Q(inicio__lte=inicio, fin__gte=inicio) | Q(inicio__lte=fin, fin__gte=fin) | Q(
                                inicio__gte=inicio, fin__lte=fin),
                            Q(turno=turno, dia=dia, activo=True, materia__cerrado=False, profesor=profesor))
                        if claseconflicto: raise NameError(f"El profesor ya tiene asignada una materia en el  turno : {turno} y día: {dia}.")

                    for turno in lista_turnos:
                        claseconflicto = Clase.objects.filter(
                            Q(inicio__lte=inicio, fin__gte=inicio) | Q(inicio__lte=fin, fin__gte=fin) | Q(
                                inicio__gte=inicio, fin__lte=fin), materia__nivel__periodo=periodo, turno=turno,
                            dia=dia, activo=True, materia__cerrado=False)
                        if claseconflicto.values('id').filter(tipoprofesor=tipoprofesor, profesor=profesor,
                                                              materia__asignatura_id=materia.asignatura.id).exists():
                            raise NameError(
                                f"La materia ya existe en este turno: {turno}, dia : {dia}, aula y profesor en ese rango de fechas.")

                        elif claseconflicto.values('id').filter(tipoprofesor=tipoprofesor, profesor=profesor).exists():
                            raise NameError(
                                f"El profesor ya tiene asignada una materia en ese turno: {turno}, día: {dia} y aula.")

                    if materia.tipomateria == 1:
                        for turno in lista_turnos:
                            verificar_conflito_docente = profesor.existe_conflicto_docente(periodo, materia,
                                                                                           tipoprofesor, inicio, fin,
                                                                                           dia, turno)
                            if verificar_conflito_docente[0]: raise NameError(verificar_conflito_docente[1])

                    elif materia.coordinacion().id != 9:
                        for turno in lista_turnos:
                            verificar_conflito_docente = profesor.existe_conflicto_docente(periodo, materia,
                                                                                           tipoprofesor, inicio, fin,
                                                                                           dia, turno)
                            if verificar_conflito_docente[0]: raise NameError(verificar_conflito_docente[1])

            return {'result': True}

        except Exception as ex:
            return {'result': False, 'mensaje': u"%s" % ex.__str__()}

    def valida_choque_horario_en_actas_generadas(self,eHorarioClases_new,eInscripcionConvocatoria,eActaParalelo):
        try:
            ePersonalAContratars = PersonalAContratar.objects.filter(status=True, tipo_id=1,inscripcion__postulante__persona=eInscripcionConvocatoria.postulante.persona).exclude(actaparalelo__convocatoria__id=eInscripcionConvocatoria.convocatoria.id)

            for horario in eHorarioClases_new:
                lista_turnos = horario.turno.all()
                dia = horario.dia
                inicio = horario.inicio
                fin = horario.fin
                for turno in lista_turnos:
                    for ePersonalAContratar in ePersonalAContratars:
                        eActaParalelo = ePersonalAContratar.actaparalelo
                        eHorarioClasesePersonalAContratar = HorarioClases.objects.filter(status=True,
                                                                                         actaparalelo=eActaParalelo).filter(
                            Q(dia=dia) & ((Q(turno__comienza__gte=turno.comienza) & Q(
                                turno__termina__lte=turno.termina)) |
                                          (Q(turno__comienza__lte=turno.comienza) & Q(
                                              turno__termina__gte=turno.termina)) |
                                          (Q(turno__comienza__lte=turno.termina) & Q(
                                              turno__comienza__gte=turno.comienza)) |
                                          (Q(turno__termina__gte=turno.comienza) & Q(
                                              turno__termina__lte=turno.termina))) &
                            ((Q(inicio__gte=inicio) & Q(fin__lte=fin)) | (Q(inicio__lte=inicio) & Q(fin__gte=fin)) | Q(
                                inicio__lte=fin) & Q(inicio__gte=inicio)) | (Q(fin__gte=inicio) & Q(fin__lte=fin))
                        )
                        if eHorarioClasesePersonalAContratar.exists():
                            raise NameError(f"Conficto de horarios en acta: {eActaParalelo.acta} - {eActaParalelo}")

            return {'result': True}

        except Exception as ex:
            return {'result': False, 'mensaje': u"%s" % ex.__str__()}


    def validar_para_guardar_principales_alternos_1_2_el_resto_poner_como_banco_elegible(self):
        try:
            from sga.models import Profesor
            hoy = datetime.now().date()
            eActaParalelo = self
            choque_horario_pregrado_principal = False
            choque_horario_en_actas_generadas_principal = False
            choque_horario_pregrado_alterno_1 = False
            choque_horario_en_actas_generadas_alterno_1 = False
            choque_horario_pregrado_alterno_2 = False
            choque_horario_en_actas_generadas_alterno_2 = False
            error_principal = False
            error_alterno_1 = False
            error_alterno_2 = False
            errores_principal = []
            errores_alterno_1 = []
            errores_alterno_2 = []
            votaciones_ordenadas_de_mayor_a_menor = self.get_baremo_por_integrante_comite()
            for resultado in votaciones_ordenadas_de_mayor_a_menor:
                eInscripcionConvocatoriaPk = int(resultado['eInscripcionConvocatoriaPk'])
                eInscripcionConvocatoria = InscripcionConvocatoria.objects.get(pk=eInscripcionConvocatoriaPk)

                tipoinscripcion = 1 if Profesor.objects.values('id').filter(persona=eInscripcionConvocatoria.postulante.persona,status=True).exists() else 2
                if resultado['tipo']== 'principal':
                    if PersonalAContratar.objects.filter(actaparalelo=eActaParalelo, tipo_id=1, status=True).exists():
                        error_principal =True
                        errores_principal.append(u'Exedió el número de postulantes de tipo PRINCIPAL.')
                    cantidadcontratos = PersonalAContratar.objects.values('id').filter(
                        inscripcion=eInscripcionConvocatoria, fecha_creacion__year=hoy.year, tipo__id=1,
                        actaparalelo__convocatoria__tipodocente__in=[18, 15],
                        actaparalelo__convocatoria__status=True, actaparalelo__acta__status=True,
                        actaparalelo__status=True, actaparalelo__acta__fecha_legalizacion__isnull=False,
                        status=True).count()
                    if cantidadcontratos > 3:
                        error_principal = True
                        errores_principal.append(u'Exedió el número de contratos por año para docentes de tipo PROFESOR y PROFESOR AUTOR.')

                    # Validacion de choque de horario
                    evalida_choque_horario_pregrado = self.valida_choque_horario_pregrado(eActaParalelo.get_horario(), eInscripcionConvocatoria)
                    if not evalida_choque_horario_pregrado.get('result'):
                        choque_horario_pregrado = True
                        errores_principal.append(evalida_choque_horario_pregrado.get('mensaje'))
                        error_principal = True

                    evalida_choque_horario_en_actas_generadas = self.valida_choque_horario_en_actas_generadas(eActaParalelo.get_horario(), eInscripcionConvocatoria, eActaParalelo)
                    if not evalida_choque_horario_en_actas_generadas.get('result'):
                        choque_horario_en_actas_generadas = True
                        errores_principal.append(evalida_choque_horario_pregrado.get('mensaje'))
                        error_principal = True

                elif resultado['tipo']== 'alterno_1':
                    if PersonalAContratar.objects.filter(actaparalelo=eActaParalelo, tipo_id=2, status=True).exists():
                        error_alterno_1 = True
                        errores_alterno_1.append(f'Exedió el número de postulantes de tipo ALTERNO 1.')

                        # Validacion de choque de horario
                        evalida_choque_horario_pregrado = self.valida_choque_horario_pregrado(eActaParalelo.get_horario(), eInscripcionConvocatoria)
                        if not evalida_choque_horario_pregrado.get('result'):
                            choque_horario_pregrado_alterno_1 = True
                            errores_alterno_1.append(evalida_choque_horario_pregrado.get('mensaje'))
                            error_alterno_1 = True

                        evalida_choque_horario_en_actas_generadas = self.valida_choque_horario_en_actas_generadas(eActaParalelo.get_horario(), eInscripcionConvocatoria, eActaParalelo)
                        if not evalida_choque_horario_en_actas_generadas.get('result'):
                            choque_horario_en_actas_generadas_alterno_1 = True
                            errores_alterno_1.append(evalida_choque_horario_pregrado.get('mensaje'))
                            error_alterno_1 = True

                elif resultado['tipo']== 'alterno_2':
                    if PersonalAContratar.objects.filter(actaparalelo=eActaParalelo, tipo_id=3, status=True).exists():
                        error_alterno_2 = True
                        errores_alterno_2.append(f'Exedió el número de postulantes de tipo ALTERNO 2.')
                        # Validacion de choque de horario
                        evalida_choque_horario_pregrado = self.valida_choque_horario_pregrado(eActaParalelo.get_horario(), eInscripcionConvocatoria)
                        if not evalida_choque_horario_pregrado.get('result'):
                            choque_horario_pregrado_alterno_2 = True
                            errores_alterno_2.append(evalida_choque_horario_pregrado.get('mensaje'))
                            error_alterno_2 = True

                        evalida_choque_horario_en_actas_generadas = self.valida_choque_horario_en_actas_generadas(eActaParalelo.get_horario(), eInscripcionConvocatoria, eActaParalelo)
                        if not evalida_choque_horario_en_actas_generadas.get('result'):
                            choque_horario_en_actas_generadas_alterno_2 = True
                            errores_alterno_2.append(evalida_choque_horario_pregrado.get('mensaje'))
                            error_alterno_2 = True

            return choque_horario_pregrado_principal,choque_horario_en_actas_generadas_principal,choque_horario_pregrado_alterno_1,choque_horario_en_actas_generadas_alterno_1,choque_horario_pregrado_alterno_2,choque_horario_en_actas_generadas_alterno_2,error_principal,error_alterno_1,error_alterno_2,errores_principal,errores_alterno_1,errores_alterno_2

        except Exception as ex:
            pass

    def asignar_etiqueta(self, resultado):
        etiqueta = None
        if resultado['tipo'] == 'principal':
            if not resultado['choque_horario_pregrado'] and not resultado['choque_horario_otra_acta']:
                etiqueta = 'principal'

        elif resultado['tipo'] == 'alterno_1':
            if not resultado['choque_horario_pregrado'] and not resultado['choque_horario_otra_acta']:
                etiqueta = 'alterno_1'

        elif resultado['tipo'] == 'alterno_2':
            if not resultado['choque_horario_pregrado'] and not resultado['choque_horario_otra_acta']:
                etiqueta = 'alterno_2'

        elif resultado['tipo'] == 'banco_elegible':
            etiqueta = 'banco_elegible'

        return etiqueta

    def seleccionar_los_principales_alternos_banco_elegibles_que_no_tienen_conflictos(self):
        try:
            hoy = datetime.now().date()
            eActaParalelo = self
            principal = []
            alterno_1 = []
            alterno_2 = []
            banco_elegible = []
            votaciones_ordenadas_de_mayor_a_menor = self.get_baremo_por_integrante_comite()
            for resultado in votaciones_ordenadas_de_mayor_a_menor:
                if not resultado['choque_horario_pregrado'] and not resultado['choque_horario_otra_acta']:
                    if  not principal:
                        principal.append(resultado)
                        # Si es alterno 1 y aún no se ha asignado un alterno 1
                    elif  not alterno_1:
                        alterno_1.append(resultado)
                        # Si es alterno 2 y aún no se ha asignado un alterno 2
                    elif  not alterno_2:
                        alterno_2.append(resultado)
                        # Si ya se han asignado principal, alterno 1 y alterno 2, entonces es banco elegible
                    else:
                        banco_elegible.append(resultado)

            return principal, alterno_1, alterno_2, banco_elegible


        except Exception as ex:
            pass

    def seleccionar_alternos_banco_elegibles_que_no_tienen_conflictos(self):
        try:
            hoy = datetime.now().date()
            eActaParalelo = self
            alterno_1 = []
            alterno_2 = []
            banco_elegible = []
            votaciones_ordenadas_de_mayor_a_menor = self.get_baremo_por_integrante_comite()
            for resultado in votaciones_ordenadas_de_mayor_a_menor:
                if not resultado['choque_horario_pregrado'] and not resultado['choque_horario_otra_acta']:
                    if not alterno_1 and not resultado['ya_esta_en_otro_paralelo']:
                        alterno_1.append(resultado)
                        # Si es alterno 2 y aún no se ha asignado un alterno 2
                    elif not alterno_2 and not resultado['ya_esta_en_otro_paralelo']:
                        alterno_2.append(resultado)
                        # Si ya se han asignado principal, alterno 1 y alterno 2, entonces es banco elegible
                    elif not resultado['ya_esta_en_otro_paralelo']:
                        banco_elegible.append(resultado)

            return alterno_1, alterno_2, banco_elegible


        except Exception as ex:
            pass

    def seleccionar_los_principales_que_no_tienen_conflictos(self):
        try:
            hoy = datetime.now().date()
            eActaParalelo = self
            principal = []
            votaciones_ordenadas_de_mayor_a_menor = self.get_baremo_por_integrante_comite()
            for resultado in votaciones_ordenadas_de_mayor_a_menor:
                if not resultado['choque_horario_pregrado'] and not resultado['choque_horario_otra_acta']:
                    if not principal and not resultado['ya_esta_en_otro_paralelo']:
                        principal.append(resultado)
            return principal

        except Exception as ex:
            pass

    def guardar_automatico_principal_alternos(self,request):
        try:
            self.get_personal().update(status=False)
            hoy = datetime.now().date()
            eActaParalelo = self
            principal, alterno_1, alterno_2, banco_elegible = self.seleccionar_los_principales_alternos_banco_elegibles_que_no_tienen_conflictos()

            if principal:
                eInscripcionConvocatoriaPk = int(principal[0]['eInscripcionConvocatoriaPk'])
                eInscripcionConvocatoria = InscripcionConvocatoria.objects.get(pk=eInscripcionConvocatoriaPk)
                self.guardar_principale_automatico(request,eInscripcionConvocatoria)

            if alterno_1:
                eInscripcionConvocatoriaPk = int(alterno_1[0]['eInscripcionConvocatoriaPk'])
                eInscripcionConvocatoria = InscripcionConvocatoria.objects.get(pk=eInscripcionConvocatoriaPk)
                self.guardar_alterno_1_automatico(request,eInscripcionConvocatoria)

            if alterno_2:
                eInscripcionConvocatoriaPk = int(alterno_2[0]['eInscripcionConvocatoriaPk'])
                eInscripcionConvocatoria = InscripcionConvocatoria.objects.get(pk=eInscripcionConvocatoriaPk)
                self.guardar_alterno_2_automatico(request,eInscripcionConvocatoria)

            if banco_elegible:
                for banco in banco_elegible:
                    eInscripcionConvocatoriaPk = int(banco['eInscripcionConvocatoriaPk'])
                    eInscripcionConvocatoria = InscripcionConvocatoria.objects.get(pk=eInscripcionConvocatoriaPk)
                    self.guardar_banco_elegible_automatico(request,eInscripcionConvocatoria)

        except Exception as ex:
            pass

    def guardar_automatico_alternos_banco_elegible_de_toda_el_acta(self,request):
        try:
            # self.get_personal().update(status=False)
            hoy = datetime.now().date()
            eActaParalelo = self
            alterno_1, alterno_2, banco_elegible = self.seleccionar_alternos_banco_elegibles_que_no_tienen_conflictos()

            if alterno_1:
                eInscripcionConvocatoriaPk = int(alterno_1[0]['eInscripcionConvocatoriaPk'])
                eInscripcionConvocatoria = InscripcionConvocatoria.objects.get(pk=eInscripcionConvocatoriaPk)
                self.guardar_alterno_1_automatico(request,eInscripcionConvocatoria)

            if alterno_2:
                eInscripcionConvocatoriaPk = int(alterno_2[0]['eInscripcionConvocatoriaPk'])
                eInscripcionConvocatoria = InscripcionConvocatoria.objects.get(pk=eInscripcionConvocatoriaPk)
                self.guardar_alterno_2_automatico(request,eInscripcionConvocatoria)

            if banco_elegible:
                for banco in banco_elegible:
                    eInscripcionConvocatoriaPk = int(banco['eInscripcionConvocatoriaPk'])
                    eInscripcionConvocatoria = InscripcionConvocatoria.objects.get(pk=eInscripcionConvocatoriaPk)
                    self.guardar_banco_elegible_automatico(request,eInscripcionConvocatoria)

        except Exception as ex:
            pass

    def guardar_automatico_principales_de_toda_el_acta(self,request):
            try:
                self.get_personal().update(status=False)
                hoy = datetime.now().date()
                eActaParalelo = self
                principal = self.seleccionar_los_principales_que_no_tienen_conflictos()
                if principal:
                    eInscripcionConvocatoriaPk = int(principal[0]['eInscripcionConvocatoriaPk'])
                    eInscripcionConvocatoria = InscripcionConvocatoria.objects.get(pk=eInscripcionConvocatoriaPk)
                    self.guardar_principale_automatico(request,eInscripcionConvocatoria)
            except Exception as ex:
                pass

    def guardar_segun_validacion_principal_alternos(self,request):
            try:
                self.guardar_automatico_principal_alternos(request)
                self.acta.actualizar_documeto_pdf_acta(request)
            except Exception as ex:
                pass

    def guardar_principale_automatico(self,request,eInscripcionConvocatoria):
        try:
            from sga.models import Profesor
            eActaParalelo = self
            tipoinscripcion = 1 if Profesor.objects.values('id').filter(persona=eInscripcionConvocatoria.postulante.persona,status=True).exists() else 2
            p = PersonalAContratar(inscripcion=eInscripcionConvocatoria, tipo_id=1, actaparalelo=eActaParalelo, tipoinscripcion=tipoinscripcion)
            p.save(request)
            eInscripcionConvocatoria.estado =2
            eInscripcionConvocatoria.save(request)

        except Exception as ex:
            pass

    def guardar_alterno_1_automatico(self,request,eInscripcionConvocatoria):
        try:
            from sga.models import Profesor
            eActaParalelo = self
            tipoinscripcion = 1 if Profesor.objects.values('id').filter(persona=eInscripcionConvocatoria.postulante.persona,status=True).exists() else 2
            p = PersonalAContratar(inscripcion=eInscripcionConvocatoria, tipo_id=2, actaparalelo=eActaParalelo,tipoinscripcion=tipoinscripcion)
            p.save(request)

        except Exception as ex:
            pass

    def guardar_alterno_2_automatico(self,request,eInscripcionConvocatoria):
        try:
            from sga.models import Profesor
            eActaParalelo = self
            tipoinscripcion = 1 if Profesor.objects.values('id').filter(persona=eInscripcionConvocatoria.postulante.persona,status=True).exists() else 2
            p = PersonalAContratar(inscripcion=eInscripcionConvocatoria, tipo_id=3, actaparalelo=eActaParalelo,tipoinscripcion=tipoinscripcion)
            p.save(request)
        except Exception as ex:
            pass

    def guardar_banco_elegible_automatico(self,request,eInscripcionConvocatoria):
        try:
            eInscripcionConvocatoria.estado = 11
            eInscripcionConvocatoria.save(request)
        except Exception as ex:
            pass

    def get_total_horas_horario_docente(self):
        cantidad_de_turnos = 0
        horarios = HorarioClases.objects.filter(actaparalelo=self, status=True)
        if horarios:
            dias = horarios.annotate(cantidad_turnos=Count('turno'))
            if dias:
                for dia in dias:
                    cantidad_de_turnos += dia.cantidad_turnos

        return cantidad_de_turnos

    def get_paralelo_cumple_total_horas_docente(self):
        cumplen = True
        if not self.get_total_horas_horario_docente() == self.convocatoria.get_horas_componente_docente():
            cumplen = False
        return cumplen

    def get_tiene_horario_en_fecha_inicio_y_fecha_fin_de_paralelo(self):
        return self.horarioclases_set.filter(status=True, inicio = self.inicio).exists() and self.horarioclases_set.filter(status=True, fin= self.fin).exists()

    def get_puntaje_total_baremo_principal(self):
        try:
            ePersonalAContratar = self.get_personal_principal().first() if  self.get_personal_principal().exists() else None
            if ePersonalAContratar:
                eInscripcionConvocatoria = ePersonalAContratar.inscripcion
                resultado  = self.get_calificacion_baremo_por_inscripcion_convocatoria(eInscripcionConvocatoria)
                total = resultado[0]['promedio_baremo']
            else:
                total = 0
            return total
        except Exception as ex:
            return 0

    def get_puntaje_total_baremo_alterno_1(self):
        alterno1Pk = 2
        ePersonalAContratar = self.get_personal_alterno().filter(tipo = alterno1Pk).first() if self.get_personal_alterno().filter(tipo = alterno1Pk).exists() else None
        if ePersonalAContratar:
            eInscripcionConvocatoria = ePersonalAContratar.inscripcion
            resultado = self.get_calificacion_baremo_por_inscripcion_convocatoria(eInscripcionConvocatoria)
            total = resultado[0]['promedio_baremo']
        else:
            total = 0
        return total

    def get_puntaje_total_baremo_alterno_2(self):
        alterno2Pk = 3
        ePersonalAContratar = self.get_personal_alterno().filter(tipo=alterno2Pk).first() if self.get_personal_alterno().filter(tipo=alterno2Pk).exists() else None
        if ePersonalAContratar:
            eInscripcionConvocatoria = ePersonalAContratar.inscripcion
            resultado = self.get_calificacion_baremo_por_inscripcion_convocatoria(eInscripcionConvocatoria)
            total = resultado[0]['promedio_baremo']
        else:
            total = 0
        return total

    def get_resultado_baremo(self):
        return VotacionComiteAcademico.objects.filter(actaparalelo=self,status=True)

    def get_baremo_agrupado_por_postulante(self):
        eVotacionComiteAcademicoPk = VotacionComiteAcademico.objects.filter(actaparalelo=self, status=True).values_list('inscripcion',flat=True)
        return InscripcionConvocatoria.objects.filter(pk__in =eVotacionComiteAcademicoPk)

    def get_baremo_por_integrante_comite(self):
        hoy = datetime.now().date()
        estructura = []
        eInscripcionConvocatorias = self.get_baremo_agrupado_por_postulante()

        # Obtener los tipos de miembros de comité
        tipos_miembros = ['principal', 'alterno 1', 'alterno 2']

        for index, eInscripcionConvocatoria in enumerate(eInscripcionConvocatorias):
            inscripcion_data = {
                'eInscripcionConvocatoria': eInscripcionConvocatoria,
                'eInscripcionConvocatoriaPk': eInscripcionConvocatoria.pk,
                'ePersonalAContratarGanador': eInscripcionConvocatoria.esta_inscripcionconvocatoria_esta_como_principal_o_alterno_en_el_acta(self),
                'ya_esta_en_otro_paralelo': False,
                'comite': {'miembros': []},
                'suma_puntaje_todos_comite': 0.0,
                'promedio_baremo': 0.0,
                'realizaron_todos_votos': False,
                'choque_horario_pregrado': False,
                'choque_horario_otra_acta': False,
                'mas_de_3_contrato_anio': False,
                'cantidad_contrato': 0,
                'mensaje_choque_horario': False,
                'mensaje_choque_horario_otra_acta': False
            }
            total_puntaje = 0
            total_miembros_calificaron = 0
            realizaron_todos_votos = True
            for i, miembrocomite in enumerate(self.acta.get_integrante_comite()):
                eVotacionComiteAcademico = VotacionComiteAcademico.objects.filter(actaparalelo=self, status=True,
                                                                                  inscripcion=eInscripcionConvocatoria,
                                                                                  miembrocomite=miembrocomite)
                if eVotacionComiteAcademico.exists():
                    total_baremo = eVotacionComiteAcademico.first().get_calificacion_total_baremo()
                    if total_baremo:
                        total_puntaje += total_baremo['total_puntaje']
                        # Determinar el tipo de miembro de comité
                        inscripcion_data['comite']['miembros'].append({'miembro': miembrocomite, 'realizo_voto': 'Si', 'puntaje': total_baremo['total_puntaje']})
                        total_miembros_calificaron += 1
                    else:
                        inscripcion_data['comite']['miembros'].append({'miembro': miembrocomite, 'realizo_voto': 'No', 'puntaje': 0})

                else:
                    # Si no se encontró la votación, considerarlo como 'banco elegible'
                    inscripcion_data['comite']['miembros'].append({'miembro': miembrocomite, 'realizo_voto': 'No', 'puntaje': 0})
                    realizaron_todos_votos = False

            inscripcion_data['suma_puntaje_todos_comite'] = total_puntaje
            inscripcion_data['total_miembros_calificaron'] = total_miembros_calificaron
            promedio =  0 if total_miembros_calificaron == 0 else  round(total_puntaje / total_miembros_calificaron, 2)
            inscripcion_data['promedio_baremo'] = promedio
            inscripcion_data['realizaron_todos_votos'] = realizaron_todos_votos

            # Validacion de choque de horario
            evalida_choque_horario_pregrado = self.valida_choque_horario_pregrado(self.get_horario(),eInscripcionConvocatoria)
            if not evalida_choque_horario_pregrado.get('result'):
                inscripcion_data['choque_horario_pregrado'] = True
                inscripcion_data['mensaje_choque_horario'] =evalida_choque_horario_pregrado.get('mensaje')

            evalida_choque_horario_en_actas_generadas = self.valida_choque_horario_en_actas_generadas(self.get_horario(), eInscripcionConvocatoria, self)
            if not evalida_choque_horario_en_actas_generadas.get('result'):
                inscripcion_data['choque_horario_otra_acta'] = True
                inscripcion_data['mensaje_choque_horario'] =evalida_choque_horario_en_actas_generadas.get('mensaje')

            cantidadcontratos = PersonalAContratar.objects.values('id').filter(
                inscripcion=eInscripcionConvocatoria, fecha_creacion__year=hoy.year, tipo__id=1,
                actaparalelo__convocatoria__tipodocente__in=[18, 15],
                actaparalelo__convocatoria__status=True, actaparalelo__acta__status=True,
                actaparalelo__status=True, actaparalelo__acta__fecha_legalizacion__isnull=False,
                status=True).count()
            if cantidadcontratos > 3:
                inscripcion_data['mas_de_3_contrato_anio'] = True
            inscripcion_data['cantidad_contrato'] = cantidadcontratos
            inscripcion_data['ya_esta_en_otro_paralelo'] = eInscripcionConvocatoria.esta_inscripcionconvocatoria_esta_como_principal_o_alterno_en_el_acta_validacion_baremo(self)

            estructura.append(inscripcion_data)

        # Ordenar la estructura de mayor a menor por el promedio del baremo
        estructura_ordenada = sorted(estructura, key=lambda x: x['promedio_baremo'], reverse=True)

        # Asignar los tipos a los primeros tres elementos
        for index, item in enumerate(estructura_ordenada):
            if index == 0:
                item['tipo'] = 'principal'
            elif index == 1:
                item['tipo'] = 'alterno_1'
            elif index == 2:
                item['tipo'] = 'alterno_2'
            else:
                item['tipo'] = 'banco_elegible'


        return estructura_ordenada

    def get_calificacion_baremo_por_inscripcion_convocatoria(self,eInscripcionConvocatoria):
        hoy = datetime.now().date()
        estructura = []

        inscripcion_data = {
            'eInscripcionConvocatoria': eInscripcionConvocatoria,
            'eInscripcionConvocatoriaPk': eInscripcionConvocatoria.pk,
            'comite': {'miembros': []},
            'suma_puntaje_todos_comite': 0.0,
            'promedio_baremo': 0.0
        }
        total_puntaje = 0
        total_miembros_calificaron = 0
        realizaron_todos_votos = True
        for i, miembrocomite in enumerate(self.acta.get_integrante_comite()):
            eVotacionComiteAcademico = VotacionComiteAcademico.objects.filter(actaparalelo=self, status=True,
                                                                              inscripcion=eInscripcionConvocatoria,
                                                                              miembrocomite=miembrocomite)
            if eVotacionComiteAcademico.exists():
                total_baremo = eVotacionComiteAcademico.first().get_calificacion_total_baremo()
                if total_baremo:
                    total_puntaje += total_baremo['total_puntaje']
                    # Determinar el tipo de miembro de comité
                    inscripcion_data['comite']['miembros'].append({'miembro': miembrocomite, 'realizo_voto': 'Si', 'puntaje': total_baremo['total_puntaje']})
                    total_miembros_calificaron += 1
                else:
                    inscripcion_data['comite']['miembros'].append({'miembro': miembrocomite, 'realizo_voto': 'No', 'puntaje': 0})

            else:
                # Si no se encontró la votación, considerarlo como 'banco elegible'
                inscripcion_data['comite']['miembros'].append({'miembro': miembrocomite, 'realizo_voto': 'No', 'puntaje': 0})
                realizaron_todos_votos = False

        inscripcion_data['suma_puntaje_todos_comite'] = total_puntaje
        inscripcion_data['total_miembros_calificaron'] = total_miembros_calificaron
        promedio =  0 if total_miembros_calificaron == 0 else  round(total_puntaje / total_miembros_calificaron, 2)
        inscripcion_data['promedio_baremo'] = promedio

        estructura.append(inscripcion_data)

        return estructura

    def cantidad_de_postulantes_elegibles(self):
        try:
            NO_CUMPLE_PERFIL = 3
            eInscripcionConvocatorias = InscripcionConvocatoria.objects.filter(convocatoria=self.convocatoria,status=True, postulante__status=True).exclude(estado=NO_CUMPLE_PERFIL).count()
            return eInscripcionConvocatorias
        except Exception as ex:
            return 0
ESTADO_PERSONAL_CONTRATAR = (
    (1, 'PENDIENTE'),
    (2, 'REPROGRAMACIÓN ACADÉMICA'),
    (3, 'INICIAR PROCESO'),
    (4, 'VALIDO PARA CONTRATACIÓN'),
)


ESTADO_PERSONAL_CONTRATACION =(
(1, 'PENDIENTE'),
(2, 'EN INFORME DE CONTRATACIÓN'),
(3, 'VÁLIDADO POR POSGRADO'),
)

class ActaParaleloHistorial(ModeloBase):
    actaparalelo = models.ForeignKey(ActaParalelo, blank=True, null=True, verbose_name=u'Acta', on_delete=models.CASCADE)
    estadoprerevision = models.IntegerField(choices=ESTADO_REVISION_PARALELO, default=1, verbose_name=u'Estado')
    observacion  = models.TextField(verbose_name=u"Observación", blank=True, null=True, default=u"Ninguna")
    persona = models.ForeignKey('sga.Persona', blank=True, null=True, verbose_name=u'Persona', on_delete=models.CASCADE)
    def __str__(self):
        return u'%s' % self.actaparalelo

    class Meta:
        verbose_name = u"ActaParaleloHistorial"
        verbose_name_plural = u"ActaParaleloHistorial"
        ordering = ['id']

    def get_display_estadoprerevision(self):
        estado = ''
        if self.estadoprerevision == 1:
            estado = f"<span class='badge rounded-pill bg-primary'>{self.get_estadoprerevision_display()}</span>"

        if self.estadoprerevision == 2:
            estado = f"<span class='badge rounded-pill bg-success'>{self.get_estadoprerevision_display()}</span>"

        if self.estadoprerevision == 3:
            estado =  f"<span class='badge rounded-pill bg-warning'>{self.get_estadoprerevision_display()}</span>"


class PersonalAContratar(ModeloBase):
    inscripcion = models.ForeignKey(InscripcionConvocatoria, blank=True, null=True, verbose_name=u'Persona a contratar', on_delete=models.CASCADE)
    tipo = models.ForeignKey(TipoPersonal, blank=True, null=True, verbose_name=u'Tipo', on_delete=models.CASCADE)
    actaparalelo = models.ForeignKey(ActaParalelo, blank=True, null=True, verbose_name=u'Acta', on_delete=models.CASCADE)
    tipoinscripcion = models.IntegerField(verbose_name=u"Tipo de inscripción", choices=TIPO_INSCRIPCION, blank=True, null=True)
    observacion = models.TextField(verbose_name=u"Observación", blank=True, null=True, default=u"Ninguna")
    estado =  models.IntegerField(choices=ESTADO_PERSONAL_CONTRATAR, default=1, verbose_name=u'estado requisitos')
    estado_contratacion =  models.IntegerField(choices=ESTADO_PERSONAL_CONTRATACION, default=1, verbose_name=u'estado')

    def __str__(self):
        return u'%s/%s' % (self.inscripcion, self.get_tipoinscripcion_display())

    def get_requisitos(self):
        return InscripcionConvocatoriaRequisitos.objects.filter(status=True,inscripcioninvitacion=self.get_estado_invitacion())

    def get_informe_contratacion(self):
        detalle = self.detalleinformecontratacion_set.filter(status=True).first() if self.detalleinformecontratacion_set.filter(status=True).exists() else None
        return detalle.informecontratacion if detalle else  None

    def get_detalle_informe_contratacion(self):
        return self.detalleinformecontratacion_set.filter(status=True).first() if self.detalleinformecontratacion_set.filter(status=True).exists() else None

    class Meta:
        verbose_name = u"Personal a Contratar"
        verbose_name_plural = u"Personal a Contratar"
        ordering = ['id']
    #
    # def get_titulos_postulacion(self):
    #     titulos = Titulacion.objects.values_list('titulo_id', flat=True).filter(persona=self.inscripcion.postulante.persona, status=True)
    #     perfilesrequeridos = self.inscripcion.convocatoria.perfilrequeridopac.values_list('titulacion__campoamplio__id', flat=True).filter(status=True).exclude(titulacion__campoamplio__id=None).distinct()
    #     return CamposTitulosPostulacion.objects.filter(titulo__id__in=titulos, campoamplio__id__in=perfilesrequeridos, status=True).order_by('-titulo__nivel__nivel').distinct()

    def get_cohorte_anio(self):
        return f"COHORTE {self.actaparalelo.convocatoria.periodo.numero_cohorte_romano()} - {self.actaparalelo.convocatoria.periodo.anio}"

    def get_titulos_postulacion(self):
        resultado = None
        eTitulaciones = Titulacion.objects.filter(persona=self.inscripcion.postulante.persona, status=True)
        if eTitulaciones.filter( principal =True).exists():
            resultado = eTitulaciones.filter( principal =True).first()
        else:
            if eTitulaciones.filter(titulo__nivel_id = 4).exists():
                resultado =  eTitulaciones.filter(titulo__nivel_id = 4).first()
            else:
                resultado = eTitulaciones.first()

        return resultado

    def eliminar_personal(self,request):
        self.status=False
        self.save(request)

    def volver_a_estado_revision_para_comite(self,request):
        self.inscripcion.estado = 12
        self.inscripcion.save(request)

    def acta_cerrada(self):
        eActaParalelo = self.actaparalelo.filter(status=True)
        if eActaParalelo.exists():
            return True if eActaParalelo.first().acta.estado == 4 else False
        else:
            False

    def hacer_principal_y_actualizar_al_principal_anterior(self,request):
        PRINCIPAL = 1
        ePersonalAContratarPrincipal = PersonalAContratar.objects.filter(status = True,actaparalelo = self.actaparalelo, tipo_id=PRINCIPAL).first()
        ePersonalAContratarPrincipal.tipo = self.tipo
        ePersonalAContratarPrincipal.estado = 1
        ePersonalAContratarPrincipal.save(request)
        self.tipo_id = PRINCIPAL
        self.save(request)

    def get_estado_invitacion(self):
        eInscripcionInvitacion = InscripcionInvitacion.objects.filter(status=True,inscripcion =  self.inscripcion,actaparalelo =self.actaparalelo)
        return eInscripcionInvitacion.first() if eInscripcionInvitacion.exists() else None

    def get_requisitos_configurados(self):
        return ConfiguracionRequisitosPersonalContratar.objects.filter(status=True, personalcontratar=self)

    def get_requisitos_configurados_por_cargar(self):
        return self.get_requisitos_configurados().filter(estado_requisito = 3)

    def get_requisitos_configurados_cargar_analista(self):
        return self.get_requisitos_configurados().filter(estado_requisito = 1)

    def get_requisitos_configurados_cargados_en_el_sistema(self):
        return self.get_requisitos_configurados().filter(estado_requisito = 2)

    def get_requisitos_no_configurados(self):
        return self.get_requisitos_configurados().filter(Q(estado_requisito = 0) | Q(estado_requisito = 1))

    def get_requisitos_convocatoria(self):
        ids_requisito = self.get_requisitos_configurados().exclude(estado_requisito = 0).values_list('requisitoconvocatoria__requisito_id',flat = True)#RequisitosConvocatoria
        return self.actaparalelo.convocatoria.requisitosconvocatoria().exclude(requisito__in =ids_requisito)

    def get_requisitos_convocatoria_para_postulante(self):
        ids_requisito = self.get_requisitos_configurados().exclude(estado_requisito__in = [1,2]).values_list('requisitoconvocatoria__requisito_id',flat = True)#RequisitosConvocatoria
        if ids_requisito:
            return self.actaparalelo.convocatoria.requisitosconvocatoria().filter(requisito__in=ids_requisito)
        else:
            return self.actaparalelo.convocatoria.requisitosconvocatoria()

    def actualizar_configuracion_requisitos(self,request,estado_id,requisitoconvocatoria_id):
        if not self.get_requisitos_configurados().filter(requisitoconvocatoria_id =requisitoconvocatoria_id,status = True ).exists():
            eConfiguracionRequisitosPersonalContratar = ConfiguracionRequisitosPersonalContratar(
                personalcontratar=self,
                requisitoconvocatoria_id=requisitoconvocatoria_id,
                estado_requisito=estado_id
            )
        else:
            eConfiguracionRequisitosPersonalContratar = self.get_requisitos_configurados().filter(requisitoconvocatoria_id =requisitoconvocatoria_id,status = True ).first()
            eConfiguracionRequisitosPersonalContratar.estado_requisito = estado_id
        eConfiguracionRequisitosPersonalContratar.save(request)
        return eConfiguracionRequisitosPersonalContratar

    def generar_configuracion_requisito_personal_contratar_por_defecto(self, request):
        if self.get_requisitos_convocatoria() and not self.get_requisitos_configurados():
            for requisito_convocatoria in self.get_requisitos_convocatoria():
                eConfiguracionRequisitosPersonalContratar = ConfiguracionRequisitosPersonalContratar(  # creo la configuracion del requisito
                    personalcontratar=self,
                    requisitoconvocatoria=requisito_convocatoria,
                    estado_requisito=0
                )
                eConfiguracionRequisitosPersonalContratar.save(request)

    def generar_configuracion_load_requisitos_auto_personal_contratar(self,request):
        from postulaciondip.adm_postulacion import crear_invitacion

        self.generar_configuracion_requisito_personal_contratar_por_defecto(request)
        if self.get_estado_invitacion():  # pregunto si existe invitacion para guardar el requisito con esa invitacion
            for requisito_no_configurados in self.get_requisitos_configurados():  # leo los requisitos  configurados
                eInscripcionConvocatoriaRequisitos = InscripcionConvocatoriaRequisitos.objects.filter(status=True,
                                                                                                      inscripcioninvitacion=self.get_estado_invitacion(),
                                                                                                      requisito=requisito_no_configurados.requisitoconvocatoria)
                if not eInscripcionConvocatoriaRequisitos.exists():
                    eInscripcionConvocatoriaRequisitos = InscripcionConvocatoriaRequisitos(
                        # creo el requisito sin el documento
                        inscripcioninvitacion=self.get_estado_invitacion(),
                        requisito=requisito_no_configurados.requisitoconvocatoria,
                        observacion='Ninguna',
                        estado=1
                    )
                    eInscripcionConvocatoriaRequisitos.save(request)
                else:
                    eInscripcionConvocatoriaRequisitos = eInscripcionConvocatoriaRequisitos.first()
                estado_requisito = 1 if eInscripcionConvocatoriaRequisitos.carga_automatica_requisito_de_la_ultima_convocatoria_todos(
                    request, self) else 3
                requisito_no_configurados.estado_requisito = estado_requisito
                requisito_no_configurados.save(request)
        else:
            acta = self.actaparalelo.acta
            ganador = self
            inscripcion = self.inscripcion
            jsonresponse = crear_invitacion(request, acta=acta, ganador=ganador, inscripcionconvocatoria=inscripcion)
            jsonresponse = json.loads(jsonresponse.content)
            if not jsonresponse.get('result'): raise NameError(jsonresponse.get('mensaje'))

            for requisito_no_configurados in self.get_requisitos_no_configurados():  # leo los requisitos no configurados
                eInscripcionConvocatoriaRequisitos = InscripcionConvocatoriaRequisitos(
                    # creo el requisito sin el documento
                    inscripcioninvitacion=self.get_estado_invitacion(),
                    requisito=requisito_no_configurados.requisitoconvocatoria,
                    observacion='Ninguna',
                    estado=1
                )
                eInscripcionConvocatoriaRequisitos.save(request)
                estado_requisito = 1 if eInscripcionConvocatoriaRequisitos.carga_automatica_requisito_de_la_ultima_convocatoria_todos(
                    request, self) else 3
                requisito_no_configurados.estado_requisito = estado_requisito
                requisito_no_configurados.save(request)


    def generar_configuracion_load_requisitos_sga_auto_personal_contratar(self,request):
        from postulaciondip.adm_postulacion import crear_invitacion
        CERTIFICADO_DE_REGISTRO_DE_TÍTULOS_SENESCYT = 5
        CERTIFICADO_DE_VOTACION = 11
        TITULO_TERCER = 6
        TITULO_CUARTO_NIVEL = 12
        HOJA_DE_VIDA_DEL_PROFESIONAL = 1
        COPIA_DE_CEDULA_DE_IDENTIDAD_O_PASAPORTE = 2

        self.generar_configuracion_requisito_personal_contratar_por_defecto(request)
        if self.get_estado_invitacion():  # pregunto si existe invitacion para guardar el requisito con esa invitacion
            for requisito_no_configurados in self.get_requisitos_configurados():#leo los requisitos no configurados
                eInscripcionConvocatoriaRequisitos = InscripcionConvocatoriaRequisitos.objects.filter(status=True, inscripcioninvitacion=self.get_estado_invitacion(),requisito=requisito_no_configurados.requisitoconvocatoria)
                if not eInscripcionConvocatoriaRequisitos.exists():
                    eInscripcionConvocatoriaRequisitos = InscripcionConvocatoriaRequisitos(# creo el requisito sin el documento
                        inscripcioninvitacion=self.get_estado_invitacion(),
                        requisito=requisito_no_configurados.requisitoconvocatoria,
                        observacion='Ninguna',
                        estado=1
                    )
                    eInscripcionConvocatoriaRequisitos.save(request)
                else:
                    eInscripcionConvocatoriaRequisitos = eInscripcionConvocatoriaRequisitos.first()

                if eInscripcionConvocatoriaRequisitos.requisito.requisito.pk in(CERTIFICADO_DE_REGISTRO_DE_TÍTULOS_SENESCYT, CERTIFICADO_DE_VOTACION, TITULO_TERCER, TITULO_CUARTO_NIVEL, HOJA_DE_VIDA_DEL_PROFESIONAL, COPIA_DE_CEDULA_DE_IDENTIDAD_O_PASAPORTE):
                    eInscripcionConvocatoriaRequisitos.carga_automatica_requisito_del_sistema(request)
                    estado_requisito = 1
                else:
                    estado_requisito = 3

                requisito_no_configurados.estado_requisito = estado_requisito
                requisito_no_configurados.save(request)
        else:
            acta = self.actaparalelo.acta
            ganador = self
            inscripcion = self.inscripcion
            jsonresponse = crear_invitacion(request, acta=acta, ganador=ganador, inscripcionconvocatoria=inscripcion)
            jsonresponse = json.loads(jsonresponse.content)
            if not jsonresponse.get('result'): raise NameError(jsonresponse.get('mensaje'))

            for requisito_no_configurados in self.get_requisitos_no_configurados():#leo los requisitos no configurados
                eInscripcionConvocatoriaRequisitos = InscripcionConvocatoriaRequisitos(# creo el requisito sin el documento
                    inscripcioninvitacion=self.get_estado_invitacion(),
                    requisito=requisito_no_configurados.requisitoconvocatoria,
                    observacion='Ninguna',
                    estado=1
                )
                eInscripcionConvocatoriaRequisitos.save(request)
                estado_requisito = 1 if eInscripcionConvocatoriaRequisitos.carga_automatica_requisito_de_la_ultima_convocatoria_todos(request,self) else 3
                requisito_no_configurados.estado_requisito = estado_requisito
                requisito_no_configurados.save(request)


    def get_ultima_invitacion_exclude_actual(self):
        invitacion_convocatoria_actual = self.get_estado_invitacion()
        ultima_invitacion_convocatoria = InscripcionInvitacion.objects.filter(status=True,inscripcion__postulante__persona =   self.inscripcion.postulante.persona).exclude(pk = invitacion_convocatoria_actual.pk).order_by('-id')
        return ultima_invitacion_convocatoria.first().listadorequisitoscargados() if ultima_invitacion_convocatoria.exists() else None

    def generar_automatico_requisitos_convocatoria(self,request):
        try:
            if not self.actaparalelo.convocatoria.get_existen_requisitos_configurados():
                eRequisitos = Requisito.objects.filter(status=True, id__in = variable_valor('IDS_REQUISITOS_CONVOCATORIAS_AUTOMATICO'))
                for requisito in eRequisitos:
                    if not RequisitosConvocatoria.objects.filter(requisito=requisito, convocatoria=self.actaparalelo.convocatoria, status=True):
                        requisito = RequisitosConvocatoria(requisito=requisito, convocatoria=self.actaparalelo.convocatoria)
                        if requisito == '8':
                            requisito.opcional = True
                        requisito.save(request)
        except Exception as ex:
            pass

    def get_codigo_secuencia_informe_contratacion(self,request):
        abreviaturanombre = ''
        documento = ClasificacionDocumentoInvitacion.objects.get(pk=1)

        secuencia.save(request)
        codigo = secuencia.set_secuencia()
        for c in self.inscripcion.postulante.persona.nombre_completo().split(' '):
            abreviaturanombre += c[0] if c.__len__() else ''
        codigodocumento = "ITI-POS-%s-%s-%s" % (abreviaturanombre, "%03d" % codigo, secuencia.anioejercicio)

        return codigodocumento,secuencia

    def get_estadocontratacion_display(self):
        if self.estado_contratacion == 1:
            return f'<span  title="Estado informe contratación" style="font-size: 11px" class=" badge bg-light-warning text-dark-warning">{self.get_estado_contratacion_display() }</span>'
        elif self.estado_contratacion == 2:
            return f'<span  title="Estado informe contratación" style="font-size: 11px" class=" badge bg-light-primary text-dark-primary">{self.get_estado_contratacion_display() }</span>'
        elif self.estado_contratacion == 3:
            return f'<span  title="Estado informe contratación" style="font-size: 11px" class=" badge bg-light-success text-dark-success">{self.get_estado_contratacion_display() }</span>'
        else:
            return self.get_estado_contratacion_display()

ESTADO_ACTAPARALELO_PERSONAL= (
    (1, 'agregado'),
    (2, 'editado'),
    (3, 'eliminado')
)
class HistorialPersonalContratarActaParalelo(ModeloBase):
    persona = models.ForeignKey('sga.Persona', verbose_name=u'Persona', on_delete=models.CASCADE)
    fecha = models.DateField(verbose_name=u"Fecha")
    personalcontratar = models.ForeignKey(PersonalAContratar, verbose_name=u'Personal', on_delete=models.CASCADE)
    estado =  models.IntegerField(choices=ESTADO_ACTAPARALELO_PERSONAL, default=1, verbose_name=u'estado')

    def __str__(self):
        return u'%s' % self.estado

    class Meta:
        verbose_name = u"HistorialPersonalContratarActaParalelo"
        verbose_name_plural = u"HistorialPersonalContratarActaParalelo"
        ordering = ['id']

class HistorialReprogramacion(ModeloBase):
    persona = models.ForeignKey('sga.Persona', verbose_name=u'Persona', on_delete=models.CASCADE)
    fecha = models.DateField(verbose_name=u"Fecha")
    personalcontratar = models.ForeignKey(PersonalAContratar, verbose_name=u'Personal Reprogramación', on_delete=models.CASCADE)

    def __str__(self):
        return u'%s' % self.personalcontratar

    class Meta:
        verbose_name = u"Historial Reprogramacion"
        verbose_name_plural = u"Historial Reprogramacion"
        ordering = ['id']



class HorarioClases(ModeloBase):
    dia = models.IntegerField(choices=DIAS_CHOICES, default=1, verbose_name=u'Día')
    turno = models.ManyToManyField(Turno, verbose_name=u"Turnos", blank=True)
    actaparalelo = models.ForeignKey(ActaParalelo, blank=True, null=True, verbose_name=u'Acta y paralelos', on_delete=models.CASCADE)
    inicio = models.DateField(blank=True, null=True, verbose_name=u'Fecha inicial', db_index=True)
    fin = models.DateField(blank=True, null=True, verbose_name=u'Fecha final', db_index=True)

    def __str__(self):
        return u'%s' % self.get_dia_display()

    class Meta:
        verbose_name = u"Horario de Clases"
        verbose_name_plural = u"Horario de Clases"
        ordering = ['id']

    def get_media(self):
        if self.inicio and self.fin:
            diferencia = self.fin - self.inicio
            return self.inicio + timedelta(days=diferencia.days / 2)

    def get_turno_lte(self):
        return self.turno.filter(status=True).order_by('comienza').first()

    def get_turno_gte(self):
        return self.turno.filter(status=True).order_by('-comienza').first()

    def get_turno_dia(self):
        return self.get_turno_lte().comienza.strftime("%H:%M %p") + ' a ' + self.get_turno_gte().termina.strftime("%H:%M %p")


class PlanAccion(ModeloBase):
    integrantecomiteacademico = models.ForeignKey(IntegranteComiteAcademicoPosgrado, blank=True, null=True, verbose_name=u'Dirigido a', on_delete=models.CASCADE)
    resolucion = models.TextField(verbose_name=u"Resolución", blank=True, null=True)
    acta = models.ForeignKey(ActaSeleccionDocente, blank=True, null=True, verbose_name=u'Acta', on_delete=models.CASCADE)

    def __str__(self):
        return u'%s' % self.acta

    class Meta:
        verbose_name = u"Plan de Accion"
        verbose_name_plural = u"Plan de Accion"
        ordering = ['id']


class InscripcionRequisitoPreAprobado(ModeloBase):
    inscripcioninvitacion = models.ForeignKey(InscripcionInvitacion, blank=True, null=True, verbose_name=u'Para enviarle invitacion de dar clases', on_delete=models.CASCADE)
    requisitoconvocatoria = models.ManyToManyField(RequisitosConvocatoria, verbose_name=u'Requisito')
    estado = models.IntegerField(choices=ESTADO_REVISIONDOCUMENTO, default=1, verbose_name=u'Estado')
    fecharevision = models.DateTimeField(blank=True, null=True)
    personaaprobador = models.ForeignKey('sga.Persona', blank=True, null=True, verbose_name=u'Quien aprueba', related_name='+', on_delete=models.CASCADE)

    def __str__(self):
        return u'%s' % self.inscripcioninvitacion

    class Meta:
        verbose_name = u"Inscripcion Requisito Pre Aprobado"
        verbose_name_plural = u"Inscripcion Requisito Pre Aprobado"
        ordering = ['id']


TIPO = (
    (1, 'MODULAR'),
    (2, 'MENSUAL'),
    (3, 'N/A')
)

DENOMINACION = (
    (1, 'PROFESOR'),
    (2, 'PROFESOR TUTOR'),
    (3, 'PROFESOR AUTOR'),
    (4, 'INVITADO'),
    (5, 'N/A'),
)

class PlanificacionMateria(ModeloBase):
    materia = models.ForeignKey("sga.Materia", blank=True, null=True, verbose_name=u'Materia', on_delete=models.CASCADE, related_name="materia")
    profesormateria = models.ForeignKey("sga.ProfesorMateria", blank=True, null=True, verbose_name=u'Profesor Materia', on_delete=models.CASCADE)
    tipodocente = models.ForeignKey(TipoDocente, blank=True, null=True, verbose_name=u'Tipo de Docente', on_delete=models.CASCADE)
    denominacion = models.IntegerField(choices=DENOMINACION, default=1, verbose_name=u'Denominación')
    tipo = models.IntegerField(choices=TIPO, default=1, verbose_name=u'Tipo')
    actaparalelo = models.ForeignKey(ActaParalelo, blank=True, null=True, verbose_name=u'Paralelos en acta de comité académico', on_delete=models.CASCADE)
    estado = models.IntegerField(choices=ESTADO_ADMINISTRATIVO_MATERIA, default=0, verbose_name=u'Estado')
    fecha = models.DateTimeField(verbose_name="Fecha contrato", blank=True, null=True)
    fechapago = models.DateTimeField(verbose_name="Fecha pago", blank=True, null=True)
    observacion = models.TextField(verbose_name=u"Observación", blank=True, null=True, default=u"Ninguna")
    pagado = models.BooleanField(default=False, verbose_name=u"Pagado")
    #planificacion
    profesor =models.BooleanField(default=False, verbose_name=u"Necesito profesor")
    autor =models.BooleanField(default=False, verbose_name=u"Necesito profesor autor")
    invitado =models.BooleanField(default=False, verbose_name=u"Necesito invitado")
    lanzar_convocatoria =models.BooleanField(default=False, verbose_name=u"Lanzar convocatoria")
    inicio_profesor = models.DateField(blank=True, null=True, verbose_name=u'Fecha de inicio profesor', db_index=True)
    fin_profesor = models.DateField(blank=True, null=True, verbose_name=u'Fecha fin del profesor', db_index=True)
    inicio_autor = models.DateField(blank=True, null=True, verbose_name=u'Fecha de inicio del autor', db_index=True)
    fin_autor = models.DateField(blank=True, null=True, verbose_name=u'Fecha fin del autor', db_index=True)
    observacionsolicitud = models.TextField(verbose_name=u"Observación planifiaciòn", blank=True, null=True, default=u"Ninguna")
    inicio_invitado = models.DateField(blank=True, null=True, verbose_name=u'Fecha de inicio del invitado', db_index=True)
    fin_invitado = models.DateField(blank=True, null=True, verbose_name=u'Fecha fin del invitado', db_index=True)
    convocatoria = models.ForeignKey(Convocatoria, blank=True, null=True, verbose_name=u'Convocatoria', on_delete=models.CASCADE)

    class Meta:
        verbose_name = u"PlanificacionMateria"
        verbose_name_plural = u"PlanificacionMateria"
        ordering = ['id']

    def requiere_profesor(self):
        return 'Si' if self.profesor  and not self.autor and not self.invitado else 'No'

    def requiere_lanzar_convocatoria(self):
        return 'Si' if self.lanzar_convocatoria else 'No'

    def requiere_profesor_and_profesor_autor(self):
        return 'Si' if self.profesor  and self.autor and not self.invitado else 'No'

    def requiere_invitado_and_profesor_autor(self):
        return 'Si' if self.invitado  and self.autor and not self.profesor else 'No'

    def requiere_invitado(self):
        return 'Si' if self.invitado and not self.autor and not self.profesor else 'No'

    def boolean_requiere_profesor(self):
        return True if self.profesor and not self.autor and not self.invitado else False

    def boolean_requiere_lanzar_convocatoria(self):
        return True if self.lanzar_convocatoria else False

    def boolean_requiere_profesor_and_profesor_autor(self):
        return True if self.profesor  and self.autor and not self.invitado else False

    def boolean_requiere_invitado_and_profesor_autor(self):
        return True if self.invitado  and self.autor and not self.profesor else False

    def boolean_requiere_invitado(self):
        return True if self.invitado and not self.autor and not self.profesor else False

    def es_planificada(self):
        eMateria = Materia.objects.get(pk=self.materia_id)
        return True if eMateria.inicio and eMateria.fin and  eMateria.fechafinasistencias and eMateria.existe_horario()  else False

    def get_estado(self):
        if self.estado == 0:
            return f"<span class='badge rounded-pill bg-primary'>{self.get_estado_display()}</span>"

        if self.estado == 1:
            return f"<span class='badge rounded-pill bg-success'>{self.get_estado_display()}</span>"

        if self.estado == 2:
            return f"<span class='badge rounded-pill bg-warning'>{self.get_estado_display()}</span>"

        if self.estado == 3:
            return f"<span class='badge rounded-pill bg-secondary'>{self.get_estado_display()}</span>"

        if self.estado == 4:
            return f"<span class='badge rounded-pill bg-warning'>{self.get_estado_display()}</span>"

    def get_nombre_convocatoria_a_lanzar(self):
        return f"PL-{self.materia.asignatura} - {self.materia.paralelo}"

    def get_nombre_paralelo_a_lanzar_masivo(self):
        return f"{self.materia.paralelo}"

    def get_nombre_asignatura_a_lanzar(self):
        return f"PL-{self.materia.asignatura}"
    def get_tipo_docente_requiere(self):
        tipo_docente =None
        if self.profesor and not self.autor and not self.invitado:
            tipo_docente = TipoProfesor.objects.filter(pk=18)
        elif self.autor and not self.profesor and not self.invitado:
            tipo_docente = TipoProfesor.objects.filter(pk=15)
        elif self.profesor and not self.autor and self.invitado:
            tipo_docente = TipoProfesor.objects.filter(pk=18)
        elif self.autor and not self.profesor and self.invitado:
            tipo_docente = TipoProfesor.objects.filter(pk=15)
        elif self.autor and  self.profesor and self.invitado:
            tipo_docente = TipoProfesor.objects.filter(pk__in=(18,15))
        return tipo_docente

    def __str__(self):
        if self.pagado:
            return f"{self.get_estado_display()} - {self.get_denominacion_display()} - {self.tipodocente} - PAGADO"
        else:
            return f"{self.get_estado_display()} - {self.get_denominacion_display()}"

    def puede_convocar(self):
        return True if self.estado not in (0,1,3) and  self.lanzar_convocatoria and not self.boolean_requiere_invitado()  else False

    def crear_convocatoria_tipo_profesor(self,_nombre,_asignaturamalla,_carrera_id,_fechainicio,_fechafin,_periodo,_activo,_ePlanificacionMateria,_perfilrequeridopac,_vacantes,_paralelos,_tipo,_campoamplio,_campoespecifico,_campodetallado,request):
        with transaction.atomic():
            tipo_profesor = TipoProfesor.objects.get(pk=18)
            convocatoria = Convocatoria(asignaturamalla=_asignaturamalla,
                                        nombre=f" {_nombre} - {tipo_profesor.__str__()}",
                                        fechainicio=_fechainicio,
                                        fechafin=_fechafin,
                                        activo=_activo,
                                        tipodocente=tipo_profesor,
                                        carrera_id=_carrera_id,
                                        periodo_id=_periodo,
                                        vacantes=_vacantes,
                                        paralelos=_paralelos,
                                        tipo=_tipo)
            convocatoria.save(request)
            _ePlanificacionMateria.estado = 3
            _ePlanificacionMateria.convocatoria = convocatoria
            _ePlanificacionMateria.save(request)
            if _perfilrequeridopac: convocatoria.perfilrequeridopac.set( _perfilrequeridopac)
            if _campoamplio: convocatoria.campoamplio.set(_campoamplio)
            if _campoespecifico: convocatoria.campoespecifico.set(_campoespecifico)
            if _campodetallado: convocatoria.campodetallado.set(_campodetallado)
            convocatoria.notificar_perfiles_compatibles(request)
            log(u'Agregó convocatoria masiva tipo profesor: %s' % convocatoria, request, "add")

    def crear_convocatoria_tipo_profesor_masivo(self,_nombre,_asignaturamalla,_carrera_id,_fechainicio,_fechafin,_periodo,_activo,_ePlanificacionMateriasTipoProfesor,_perfilrequeridopac,_vacantes,_paralelos,_tipo,_campoamplio,_campoespecifico,_campodetallado,request):
        with transaction.atomic():
            tipo_profesor = TipoProfesor.objects.get(pk=18)
            convocatoria = Convocatoria(asignaturamalla=_asignaturamalla,
                                        nombre=f" {_nombre} - {tipo_profesor.__str__()}",
                                        fechainicio=_fechainicio,
                                        fechafin=_fechafin,
                                        activo=_activo,
                                        tipodocente=tipo_profesor,
                                        carrera_id=_carrera_id,
                                        periodo_id=_periodo,
                                        vacantes=_vacantes,
                                        paralelos=_paralelos,
                                        tipo=_tipo)
            convocatoria.save(request)
            for _ePlanificacionMateria in _ePlanificacionMateriasTipoProfesor:
                _ePlanificacionMateria.estado = 3
                _ePlanificacionMateria.convocatoria = convocatoria
                _ePlanificacionMateria.save(request)

            if _perfilrequeridopac: convocatoria.perfilrequeridopac.set( _perfilrequeridopac)
            if _campoamplio: convocatoria.campoamplio.set(_campoamplio)
            if _campoespecifico: convocatoria.campoespecifico.set(_campoespecifico)
            if _campodetallado: convocatoria.campodetallado.set(_campodetallado)
            convocatoria.notificar_perfiles_compatibles(request)
            log(u'Agregó convocatoria masiva tipo profesor: %s' % convocatoria, request, "add")


    def crear_convocatoria_tipo_profesor_autor_masivo(self,_nombre,_asignaturamalla,_carrera_id,_fechainicio,_fechafin,_periodo,_activo,_ePlanificacionMateriasTipoProfesorAutor,_perfilrequeridopac,_vacantes,_paralelos,_tipo,_campoamplio,_campoespecifico,_campodetallado,request):
        with transaction.atomic():
            tipo_profesor = TipoProfesor.objects.get(pk=15)
            convocatoria = Convocatoria(asignaturamalla=_asignaturamalla,
                                        nombre=f" {_nombre} - {tipo_profesor.__str__()}",
                                        fechainicio=_fechainicio,
                                        fechafin=_fechafin,
                                        activo=_activo,
                                        tipodocente=tipo_profesor,
                                        carrera_id=_carrera_id,
                                        periodo_id=_periodo,
                                        vacantes=_vacantes,
                                        paralelos=_paralelos,
                                        tipo=_tipo)
            convocatoria.save(request)
            for _ePlanificacionMateria in _ePlanificacionMateriasTipoProfesorAutor:
                _ePlanificacionMateria.estado = 3
                _ePlanificacionMateria.convocatoria = convocatoria
                _ePlanificacionMateria.save(request)

            if _perfilrequeridopac: convocatoria.perfilrequeridopac.set(_perfilrequeridopac)
            if _campoamplio: convocatoria.campoamplio.set(_campoamplio)
            if _campoespecifico: convocatoria.campoespecifico.set(_campoespecifico)
            if _campodetallado: convocatoria.campodetallado.set(_campodetallado)
            convocatoria.notificar_perfiles_compatibles(request)
            log(u'Agregó convocatoria masiva tipo profesor autor: %s' % convocatoria, request, "add")

    def crear_convocatoria_tipo_profesor_autor(self,_nombre,_asignaturamalla,_carrera_id,_fechainicio,_fechafin,_periodo,_activo,_ePlanificacionMateria,_perfilrequeridopac,_vacantes,_paralelos,_tipo,_campoamplio,_campoespecifico,_campodetallado,request):
        with transaction.atomic():
            tipo_profesor = TipoProfesor.objects.get(pk=15)
            convocatoria = Convocatoria(asignaturamalla=_asignaturamalla,
                                        nombre=f" {_nombre} - {tipo_profesor.__str__()}",
                                        fechainicio=_fechainicio,
                                        fechafin=_fechafin,
                                        activo=_activo,
                                        tipodocente=tipo_profesor,
                                        carrera_id=_carrera_id,
                                        periodo_id=_periodo,
                                        vacantes=_vacantes,
                                        paralelos=_paralelos,
                                        tipo=_tipo)
            convocatoria.save(request)
            _ePlanificacionMateria.estado = 3
            _ePlanificacionMateria.convocatoria = convocatoria
            _ePlanificacionMateria.save(request)
            if _perfilrequeridopac: convocatoria.perfilrequeridopac.set(_perfilrequeridopac)
            if _campoamplio: convocatoria.campoamplio.set(_campoamplio)
            if _campoespecifico: convocatoria.campoespecifico.set(_campoespecifico)
            if _campodetallado: convocatoria.campodetallado.set(_campodetallado)
            convocatoria.notificar_perfiles_compatibles(request)
            log(u'Agregó convocatoria masiva tipo profesor autor: %s' % convocatoria, request, "add")


class ActaDocumentacion(ModeloBase):
    documentoinvitacion = models.ForeignKey(DocumentoInvitacion, blank=True, null=True, verbose_name=u'Documento invitacion', on_delete=models.CASCADE)
    acta = models.ForeignKey(ActaSeleccionDocente, blank=True, null=True, verbose_name=u'Acta de comité académico', on_delete=models.CASCADE)

    def __str__(self):
        return u'%s' % self.documentoinvitacion

    class Meta:
        verbose_name = u"Documento derivado del acta de comité académico"
        verbose_name_plural = u"Documentos derivados del acta de comité académico"
        ordering = ['-id']

class OrdenFirmaActaSeleccionDocente(ModeloBase):
    descripcion = models.TextField(verbose_name=u"Descripción")
    orden = models.IntegerField(verbose_name=u"Orden")
    funcion = models.TextField(verbose_name="Funcion", blank=True,null=True)

    def __str__(self):
        return f"{self.orden} .- {self.descripcion}"

    class Meta:
        verbose_name = u"Orden Firma Acta Seleccion Docente"
        verbose_name_plural = u"Orden Firma Acta Seleccion Docente"
        ordering = ['-id']

class MensajePredeterminado(ModeloBase):
    descripcion = models.TextField(verbose_name=u"Descripción")

    def __str__(self):
        return f"{self.descripcion}"

    class Meta:
        verbose_name = u"Mensaje Predeterminados"
        verbose_name_plural = u"Mensaje Predeterminados"
        ordering = ['-id']


class HorarioPlanificacionConvocatoria(ModeloBase):
    dia = models.IntegerField(choices=DIAS_CHOICES, default=1, verbose_name=u'Día')
    turno = models.ManyToManyField(Turno, verbose_name=u"Turnos", blank=True)
    inicio = models.DateField(blank=True, null=True, verbose_name=u'Fecha inicial', db_index=True)
    fin = models.DateField(blank=True, null=True, verbose_name=u'Fecha final', db_index=True)
    convocatoria = models.ForeignKey(Convocatoria, blank=True, null=True, verbose_name=u'convocatoria', on_delete=models.CASCADE)

    def __str__(self):
        return u'%s' % self.get_dia_display()

    class Meta:
        verbose_name = u"Horario planificacion convocatoria"
        verbose_name_plural = u"Horario planificacion convocatoria"
        ordering = ['id']

    def get_media(self):
        if self.inicio and self.fin:
            diferencia = self.fin - self.inicio
            return self.inicio + timedelta(days=diferencia.days / 2)

    def get_turno_lte(self):
        return self.turno.filter(status=True).order_by('comienza').first()

    def get_turno_gte(self):
        return self.turno.filter(status=True).order_by('-comienza').first()

    def get_turno_dia(self):
        return self.get_turno_lte().comienza.strftime("%H:%M %p") + ' a ' + self.get_turno_gte().termina.strftime("%H:%M %p")



class VotacionComiteAcademico(ModeloBase):
    miembrocomite = models.ForeignKey(IntegranteComiteAcademicoPosgrado, verbose_name=u'Miembro comité académico', on_delete=models.CASCADE)
    inscripcion = models.ForeignKey(InscripcionConvocatoria, verbose_name=u'Persona a contratar', on_delete=models.CASCADE)
    tipo = models.ForeignKey(TipoPersonal, verbose_name=u'Tipo', on_delete=models.CASCADE, blank=True, null=True)
    actaparalelo = models.ForeignKey(ActaParalelo, verbose_name=u'Paralelos en acta de comité académico',  on_delete=models.CASCADE)

    def __str__(self):
        return f"{self.inscripcion}"

    class Meta:
        verbose_name = u"Votacion Comite Academico"
        verbose_name_plural = u"Votacion Comite Academico"
        ordering = ['id']

    def get_calificacion_total_baremo(self):
        return self.baremocomiteacademico_set.filter(status=True).aggregate(total_puntaje=Sum('puntaje')) if self.baremocomiteacademico_set.filter(status=True).exists() else None

    def get_rubrica_activa_baremo(self):
        eRubricaSeleccionDocentes = RubricaSeleccionDocente.objects.filter(status=True, activo=True)
        eRubricaSeleccionDocente = eRubricaSeleccionDocentes.first() if eRubricaSeleccionDocentes.exists() else None
        return eRubricaSeleccionDocente

    def get_pk_calificacion_baremo_realizado(self):
        detallesubitemrubricaselecciondocente =  BaremoComiteAcademico.objects.filter(status=True,votacioncomiteacademico = self).values_list('detallesubitemrubricaselecciondocente',flat=True) if BaremoComiteAcademico.objects.filter(status=True,votacioncomiteacademico = self).exists() else 0
        return DetalleSubItemRubricaSeleccionDocente.objects.filter(pk__in=detallesubitemrubricaselecciondocente)

    def crear_estructura(self):
        estructura =[]
        eBaremoComiteAcademico = BaremoComiteAcademico.objects.filter(status=True,votacioncomiteacademico=self)
        eBaremoComiteAcademicoPk = eBaremoComiteAcademico.values_list('detallesubitemrubricaselecciondocente', flat=True)
        rubricas_baremo_detallado = eBaremoComiteAcademico.first().detallesubitemrubricaselecciondocente.detalleitemrubricaselecciondocente.rubricaselecciondocente.get_items_rubrica_seleccion_docente()

        for eDetalleItemRubricaSeleccionDocente in  rubricas_baremo_detallado:
            puntaje = 0
            eDetalleSubItemRubricaSeleccionDocentePk = 0
            for eDetalleSubItemRubricaSeleccionDocente in eDetalleItemRubricaSeleccionDocente.get_subitems_rubrica_seleccion_docente():

                if eDetalleSubItemRubricaSeleccionDocente.pk in  eBaremoComiteAcademicoPk :
                    puntaje = eDetalleSubItemRubricaSeleccionDocente.puntaje
                    eDetalleSubItemRubricaSeleccionDocentePk = eDetalleSubItemRubricaSeleccionDocente.pk


            estructura.append({
                'miembrocomitePk':self.miembrocomite.pk,
                'personPk':self.miembrocomite.persona.pk,
                'titulo':eDetalleItemRubricaSeleccionDocente,
                'eDetalleItemRubricaSeleccionDocentePk':eDetalleItemRubricaSeleccionDocente.pk,
                'eDetalleSubItemRubricaSeleccionDocentePk':eDetalleSubItemRubricaSeleccionDocentePk,
                'eDetalleSubItemRubricaSeleccionDocente':DetalleSubItemRubricaSeleccionDocente.objects.get(pk=eDetalleSubItemRubricaSeleccionDocentePk) if eDetalleSubItemRubricaSeleccionDocentePk !=0 else  None,
                'puntaje':puntaje
            })
        return estructura






class BaremoComiteAcademico(ModeloBase):
    votacioncomiteacademico = models.ForeignKey(VotacionComiteAcademico, verbose_name=u'Votacion', on_delete=models.CASCADE)
    detallesubitemrubricaselecciondocente = models.ForeignKey("postulaciondip.DetalleSubItemRubricaSeleccionDocente", on_delete=models.CASCADE)
    puntaje = models.FloatField(default=0.00)

    def __str__(self):
        return f"{self.puntaje}"

    class Meta:
        verbose_name = u"BaremoComiteAcademico"
        verbose_name_plural = u"BaremoComiteAcademico"
        ordering = ['id']


class ConfiguracionRequisitosPersonalContratar(ModeloBase):
    personalcontratar = models.ForeignKey(PersonalAContratar, verbose_name=u'PersonalContratar', on_delete=models.CASCADE, blank=True, null=True)
    requisitoconvocatoria = models.ForeignKey(RequisitosConvocatoria, verbose_name=u'Convocatoria', on_delete=models.CASCADE)
    estado_requisito = models.IntegerField(default=0, choices=ESTADOS_REQUISITO, verbose_name=u'Estados requisito')

    def __str__(self):
        return f"{self.requisito}"

    def get_requisito(self):
        eInscripcionInvitacion = self.personalcontratar.get_estado_invitacion() if self.personalcontratar.get_estado_invitacion() else None
        eInscripcionConvocatoriaRequisitos = InscripcionConvocatoriaRequisitos.objects.filter(status=True, inscripcioninvitacion = eInscripcionInvitacion ,requisito = self.requisitoconvocatoria)

        return eInscripcionConvocatoriaRequisitos.first() if eInscripcionConvocatoriaRequisitos.exists() else None

    def carga_automatica_editar_el_archivo_and_fecha_caducidad(self,request):
        CERTIFICADO_DE_REGISTRO_DE_TÍTULOS_SENESCYT = 5
        CERTIFICADO_DE_VOTACION = 11
        TITULO_TERCER = 6
        TITULO_CUARTO_NIVEL = 12
        HOJA_DE_VIDA_DEL_PROFESIONAL = 1
        COPIA_DE_CEDULA_DE_IDENTIDAD_O_PASAPORTE = 2
        eInscripcionConvocatoriaRequisitos = self.get_requisito()
        if eInscripcionConvocatoriaRequisitos:
            if self.estado_requisito == 0:  # por configurar
                eInscripcionConvocatoriaRequisitos.archivo = None
                eInscripcionConvocatoriaRequisitos.fecha_caducidad = None
                eInscripcionConvocatoriaRequisitos.estado = 1
            if self.estado_requisito == 1:  # cargar analista

                eInscripcionConvocatoriaRequisitos.carga_automatica_requisito_del_sistema(request)
                ePersonaAContratar  = self.personalcontratar
                if not self.requisitoconvocatoria.requisito_id in (CERTIFICADO_DE_REGISTRO_DE_TÍTULOS_SENESCYT, CERTIFICADO_DE_VOTACION , TITULO_TERCER , TITULO_CUARTO_NIVEL, HOJA_DE_VIDA_DEL_PROFESIONAL, COPIA_DE_CEDULA_DE_IDENTIDAD_O_PASAPORTE):
                    eInscripcionConvocatoriaRequisitos.carga_automatica_requisito_de_la_ultima_convocatoria(request,ePersonaAContratar)

            if self.estado_requisito == 3:  # cargar postulante
                eInscripcionConvocatoriaRequisitos.archivo = None
                eInscripcionConvocatoriaRequisitos.fecha_caducidad = None
                eInscripcionConvocatoriaRequisitos.estado = 1
            eInscripcionConvocatoriaRequisitos.save(request)
        else:
            if self.estado_requisito == 1:
                eInscripcionConvocatoriaRequisitos = InscripcionConvocatoriaRequisitos(
                    inscripcioninvitacion=self.personalcontratar.get_estado_invitacion(),
                    requisito=self.requisitoconvocatoria,
                    observacion='Ninguna',
                    estado=1
                    )
                eInscripcionConvocatoriaRequisitos.save(request)
                eInscripcionConvocatoriaRequisitos.carga_automatica_requisito_del_sistema(request)


class ConfiguracionGeneralActaSeleccionDocente(ModeloBase):
    convocado_por = models.ForeignKey(Administrativo,  verbose_name=u'Convocado por', related_name='+', on_delete=models.CASCADE)
    cargo_convocado_por = models.ForeignKey(PerfilPuestoDip, related_name='+' ,verbose_name=u'Cargo convocado por', on_delete=models.CASCADE)
    organizado_por = models.ForeignKey(Administrativo,  verbose_name=u'Organizado por', on_delete=models.CASCADE)
    cargo_organizado_por = models.ForeignKey(PerfilPuestoDip,  verbose_name=u'Cargo organizado por', on_delete=models.CASCADE)
    tipo_cargo_convocado_por = models.IntegerField(choices=TIPO_CARGO_CHOICE, default=0, verbose_name=u'tipo cargo convocado por')
    tipo_cargo_organizado_por = models.IntegerField(choices=TIPO_CARGO_CHOICE, default=0, verbose_name=u'tipo cargo organizado por')


    def __str__(self):
        return f"{self.pk}"

    class Meta:
        verbose_name = u"Configuracion General Acta Seleccion Docente"
        verbose_name_plural = u"Configuracion General Acta Seleccion Docente"
        ordering = ['-id']

class ResponsabilidadFirma(ModeloBase):
    responsabilidad = models.TextField(default='', verbose_name=u'Responsabilidad')

    class Meta:
        verbose_name = u"responsabilidad"
        verbose_name_plural = u"responsabilidad"
        ordering = ['-id']

    def __str__(self):
        return self.responsabilidad

    def en_uso(self):
        return self.ordenfirmaactapago_set.filter(status=True).exists() and self.ordenfirmaactapago_set.filter(status=True).exists()

class ValorPorHoraInformeContratacion(ModeloBase):
    valor = models.DecimalField(decimal_places=2, default=0, max_digits=30, verbose_name='Valor')

    class Meta:
        verbose_name = u"Valor Por Hora Informe Contratacion"
        verbose_name_plural = u"Valor Por Hora Informe Contratacion"
        ordering = ['-id']

    def __str__(self):
        return u'%s' % (self.valor)

class OrdenFirmaInformeContratacion(ModeloBase):
    responsabilidadfirma =models.ForeignKey(ResponsabilidadFirma,  verbose_name=u'responsabilidad firma', on_delete=models.CASCADE)
    orden = models.IntegerField(verbose_name=u"Orden")

    def __str__(self):
        return f"{self.responsabilidadfirma}"

    class Meta:
        verbose_name = u"Orden Firma informe contratacion"
        verbose_name_plural = u"Orden Firma informe contratacion"
        ordering = ['-id']

class ConfiguracionInforme(ModeloBase):
    antecedentes = models.CharField(default='', max_length=900000, verbose_name=u"antecedentes")
    motivacionjuridica = models.CharField(default='', max_length=600000, verbose_name=u"motivacion juridica")
    para = models.ForeignKey(Administrativo, blank=True, null=True, verbose_name=u'Para', related_name='+', on_delete=models.CASCADE)
    de = models.ForeignKey(Administrativo, blank=True, null=True, verbose_name=u'De', on_delete=models.CASCADE)


    def __str__(self):
        return f'configuracion informe {self.pk}'

    class Meta:
        verbose_name = u"configuracion Informe contratación"
        verbose_name_plural = u"configuracion Informes de contratación"
        ordering = ['-id']

class InformeContratacion(ModeloBase):
    fechaemision=models.DateField(verbose_name=u"Fecha Emisión")
    para = models.ForeignKey(Administrativo, blank=True, null=True, verbose_name=u'Para', related_name='+', on_delete=models.CASCADE)
    de = models.ForeignKey(Administrativo, blank=True, null=True, verbose_name=u'De', on_delete=models.CASCADE)
    objeto = models.TextField(blank=True, null=True, verbose_name="Objeto")
    estado = models.IntegerField(choices=ESTADO_INFORME_CONTRATACION, default=1, verbose_name=u'estado Informe')
    antecedentes = models.CharField(default='', max_length=6000, verbose_name=u"antecedentes resoluciones")
    motivacion_tecnica = models.CharField(default='', max_length=6000, verbose_name=u"motivacion tecnica")
    conclusiones = models.CharField(default='', max_length=6000, verbose_name=u"conclusiones")
    recomendaciones = models.CharField(default='', max_length=6000, verbose_name=u"reomendaciones")

    class Meta:
        verbose_name = u" configuracion Informe contratación"
        verbose_name_plural = u"configuracion Informes de contratación"
        ordering = ['-id']

    def __str__(self):
        return u"%s" % self.para

    def notificar_orden_integrante_toca_firmar(self,request):
        a = notificar_persona_a_fimar_informe_contratacion(request,self)
        a.start()

    def get_revisado_todos_los_expedientes_de_este_informe_por_vicerrectorado(self):
        eExpedienteContratacionPendientesRevisar = ExpedienteContratacion.objects.filter(status=True,detalleInformeContratacion__informecontratacion = self,revisado_vicerrectorado=False)
        return False if eExpedienteContratacionPendientesRevisar.exists() else True

    def get_enviado_a_rectorado(self):
        eExpedienteContratacionPendientesRevisar = ExpedienteContratacion.objects.filter(status=True,detalleInformeContratacion__informecontratacion=self,revisado_vicerrectorado=True,estado_expediente = 1)
        existe = False
        if eExpedienteContratacionPendientesRevisar:
            existe = False if eExpedienteContratacionPendientesRevisar.exists() else True
        return existe

    def get_estado_expedientes_completos_revisar_display(self):
        display = '<span  title="Estado revisión vicerrectorado" style="font-size: 11px" class=" badge bg-light-success text-dark-success">REVISIÓN COMPLETA</span>' if  self.get_revisado_todos_los_expedientes_de_este_informe_por_vicerrectorado() else '<span  title="Estado revisión vicerrectorado" style="font-size: 11px" class=" badge bg-light-warning text-dark-warning">PENDIENTE</span>'
        return display

    def get_enviado_rectorado_display(self):
        display = '<span  title="Estado revisión vicerrectorado" style="font-size: 11px" class=" badge bg-light-success text-dark-success">ENVIADO RECTORADO</span>' if  self.get_enviado_a_rectorado() else '<span  title="Estado revisión vicerrectorado" style="font-size: 11px" class=" badge bg-light-warning text-dark-warning">PENDIENTE</span>'
        return display

    def generar_expediente_contratacion(self,request):
        try:
            detalleinformecontratacion = self.detalleinformecontratacion_set.filter(status=True)
            for detalle in detalleinformecontratacion:
                personalcontratar = detalle.personalcontratar
                personalcontratar.estado_contratacion = 3
                personalcontratar.save(request)
                if  not ExpedienteContratacion.objects.filter(status=True,detalleInformeContratacion =detalle).exists():
                    eExpedienteContratacion = ExpedienteContratacion (
                        detalleInformeContratacion =detalle
                    )
                    eExpedienteContratacion.save(request)

        except Exception as ex:
            pass

    def get_documento_informe(self):
        documento = self.documentoinvitacion_set.filter(status=True,clasificacion = 1)
        return documento.first() if documento.exists() else None

    def reiniciar_informe(self,request,persona):
        try:
            observacion = 'Se reinicio el informe de contratación'
            self.get_integrantes_firman().update(firmo=False)
            self.generar_actualizar_informe_memo_contratacion_pdf(request)
            self.estado = 1
            self.guardar_historial_informe_contratacion(request, persona, observacion, None)
            self.save(request)
        except Exception as ex:
            pass

    def get_documento_memo(self):
        documento = self.documentoinvitacion_set.filter(status=True,clasificacion = 4)
        return documento.first() if documento.exists() else None

    def get_cantidad_de_integrantes_que_han_firmado(self):
        return self.informecontratacionintegrantesfirma_set.filter(status=True,firmo=True).count()

    def get_debe_firmar(self):
        eInformeContratacionIntegrantesFirma  = self.get_integrantes_firman()
        for integrante in eInformeContratacionIntegrantesFirma:
            if not integrante.firmo:
                return integrante
        return None

    def get_integrante(self, persona):
        integrante = self.get_integrantes_firman().filter(persona=persona, status=True).first()
        return integrante if integrante else None

    def existen_informes_que_deba_firmar_el_integrante_aprobador(self,persona):
        try:
            return InformeContratacionIntegrantesFirma.objects.filter(status = True,ordenFirmaInformeContratacion__responsabilidadfirma_id__in = [3,4],persona = persona).exists()
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
            return False, f"{persona}, No se encuentra configurado para firmar el informe de contratación"

    def guardar_historial_informe_contratacion(self,request,persona,observacion,archivo):
        try:
            eHistorialInformeContratacion = HistorialInformeContratacion(
                informecontratacion=self,
                persona = persona,
                observacion = observacion,
                archivo = archivo
            )
            eHistorialInformeContratacion.save(request)


        except Exception as ex:
            pass

    def get_historial_informe_contratacion(self):
        return self.historialinformecontratacion_set.filter(status=True).order_by('id')

    def actualizar_estado_del_informe_de_contratacion(self,request):
        if self.estado == 1:  # pendientes
            self.estado = 2  # firmado pasa a por legalizar
            self.save(request)

        if self.informe_firmado_por_todos():
            self.estado = 3  # paso a legalizado
            self.generar_expediente_contratacion(request)
            self.save(request)

    def informe_firmado_por_todos(self):
        return True if self.get_cantidad_de_integrantes_que_han_firmado() == self.get_integrantes_firman().count() else False

    def informe_contratacion_pendiente(self):
        return True if self.estado == 1 else False

    def informe_contratacion_por_legalizar(self):
        return True if self.estado == 2 else False

    def informe_contratacion_legalizado(self):
        return True if self.estado == 3 else False

    def get_historial_informe_contratacion(self):
        return self.historialinformecontratacion_set.filter(status=True)

    def get_estado_informe_contratacion(self):
        display = f'{self.get_estado_display()}'
        if self.estado == 1:
            display =  f'<span  title="Estado informe contratación" style="font-size: 11px" class=" badge bg-light-warning text-dark-warning">{self.get_estado_display() }</span>'
        if self.estado == 2:
            display =  f'<span  title="Estado informe contratación" style="font-size: 11px" class=" badge bg-light-primary text-dark-primary">{self.get_estado_display() }</span>'
        if self.estado == 3:
            display =  f'<span  title="Estado informe contratación" style="font-size: 11px" class=" badge bg-light-success text-dark-success">{self.get_estado_display() }</span>'

        return display

    def diccionario_VALOR_X_HORA(self):
        return ValorPorHoraInformeContratacion.objects.filter(status=True)

    def get_integrantes_firman(self):
        return self.informecontratacionintegrantesfirma_set.filter(status=True).order_by("ordenFirmaInformeContratacion__orden")

    def actualizar_todos_los_integrantes_a_firmado_completo(self,request):
        for integrante in self.get_integrantes_firman():
            integrante.firmo =True
            integrante.save(request)

    def archivo_informe_url(self):
        if self.get_documento_informe():
            return self.get_documento_informe().archivo.url if self.get_documento_informe().archivo else '#'
        else:
            return "#"

    def archivo_memo_url(self):
        if  self.get_documento_memo():
            return self.get_documento_memo().archivo.url if self.get_documento_memo().archivo else '#'
        else:
            return "#"

    def get_detalle_informe_contratacion(self):
        return self.detalleinformecontratacion_set.filter(status=True)

    def get_clasificacion_personal_por_actas(self):
        return self.detalleinformecontratacion_set.values("personalcontratar__actaparalelo__acta").filter(status=True)

    def get_persona_elabora(self):
        integrante = self.informecontratacionintegrantesfirma_set.filter(status=True,ordenFirmaInformeContratacion__responsabilidadfirma_id = 1)
        return integrante.first().persona if integrante.exists() else None

    def get_persona_valida_experta(self):
        integrante = self.informecontratacionintegrantesfirma_set.filter(status=True,ordenFirmaInformeContratacion__responsabilidadfirma_id = 2)
        return integrante.first().persona if integrante.exists() else None

    def get_persona_valida_aprueba(self):
        integrante = self.informecontratacionintegrantesfirma_set.filter(status=True,
                                                                         ordenFirmaInformeContratacion__responsabilidadfirma_id=4)
        return integrante.first().persona if integrante.exists() else None

    def get_persona_aprueba_director(self):
        integrante = self.informecontratacionintegrantesfirma_set.filter(status=True,ordenFirmaInformeContratacion__responsabilidadfirma_id = 3)
        return integrante.first().persona if integrante.exists() else None

    def persona_es_quien_firma_informe_memo(self,pk):
        return True if self.informecontratacionintegrantesfirma_set.filter(status=True,pk = pk,ordenFirmaInformeContratacion__responsabilidadfirma_id__in = [3,4]).exists() else False

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

    def generar_actualizar_codigo_secuencia(self,request,documento_pdf,tipo_documento):
        try:
            codigodocumento = ''
            persona = self.get_persona_elabora()
            if tipo_documento == 1 : #INFORME
                abreviaturanombre = ''
                if persona:
                    for c in persona.nombre_completo().split(' '):
                        abreviaturanombre += c[0] if c.__len__() else ''
                eDocumentoInvitacion = DocumentoInvitacion.objects.filter(status=True, clasificacion_id=1, informecontratacion=self)
                if not eDocumentoInvitacion.exists():
                    documento = ClasificacionDocumentoInvitacion.objects.get(pk=1)
                    secuencia = SecuenciaDocumentoInvitacion(tipo=documento)
                    secuencia.save(request)
                    codigo = secuencia.set_secuencia()
                    codigodocumento = "ITI-POS-%s-%s-%s" % (abreviaturanombre, "%03d" % codigo, secuencia.anioejercicio)
                    eDocumentoInvitacion = DocumentoInvitacion(secuenciadocumento=secuencia, codigo=codigodocumento,informecontratacion = self,clasificacion=documento,archivo=documento_pdf)
                    eDocumentoInvitacion.save(request)
                else:
                    codigodocumento = "ITI-POS-%s-%s-%s" % ( abreviaturanombre, "%03d" % eDocumentoInvitacion.first().secuenciadocumento.set_secuencia(),eDocumentoInvitacion.first().secuenciadocumento.anioejercicio)
                    eDocumentoInvitacion.update(archivo=documento_pdf,codigo=codigodocumento)


            if tipo_documento == 4: # memo
                abreviaturanombre = ''
                eDocumentoInvitacion = DocumentoInvitacion.objects.filter(status=True, clasificacion_id=4,
                                                                          informecontratacion=self)
                if not eDocumentoInvitacion.exists():
                    documento = ClasificacionDocumentoInvitacion.objects.get(pk=4)
                    secuencia = SecuenciaDocumentoInvitacion(tipo=documento)
                    secuencia.save(request)
                    codigo = secuencia.set_secuencia()
                    codigodocumento = "UNEMI-DP-%s-%s-MEM" % (secuencia.anioejercicio, "%03d" % codigo)
                    eDocumentoInvitacion = DocumentoInvitacion(secuenciadocumento=secuencia, codigo=codigodocumento,
                                                               informecontratacion=self, clasificacion=documento,
                                                               archivo=documento_pdf)
                    eDocumentoInvitacion.save(request)
                else:
                    codigodocumento = "UNEMI-DP-%s-%s-MEM" % (eDocumentoInvitacion.first().secuenciadocumento.anioejercicio,"%03d" % eDocumentoInvitacion.first().secuenciadocumento.set_secuencia())
                    eDocumentoInvitacion.update(archivo=documento_pdf,codigo=codigodocumento)




            return codigodocumento
        except Exception as ex:
            pass

    def generar_actualizar_carga_automatica_informe_contratacion(self,ePersonalAContratars,persona,request):
        guardado_correcto, mensaje =   self.guardar_detalle_informe_contratacion(ePersonalAContratars,request)
        if guardado_correcto:
            self.objeto = self.generar_texto_objeto_informe_contratacion()
            self.antecedentes = self.generar_texto_antecedente_resoluciones_informe_contratacion()
            self.motivacion_tecnica = self.generar_texto_motivacion_tecnica_informe_contratacion()
            self.conclusiones = self.generar_texto_conclusiones()
            self.recomendaciones = self.generar_texto_recomendaciones()
            self.registrar_integrantes_firman(persona, request)
            self.save(request)
            self.generar_actualizar_informe_memo_contratacion_pdf_segundo_plano(request)


        return guardado_correcto , mensaje

    def actualizar_autollenado_informe_contratacion(self,request):
        try:
            self.fechaemision = datetime.now().date()
            self.objeto = self.generar_texto_objeto_informe_contratacion()
            self.antecedentes = self.generar_texto_antecedente_resoluciones_informe_contratacion()
            self.motivacion_tecnica = self.generar_texto_motivacion_tecnica_informe_contratacion()
            # self.conclusiones = self.generar_texto_conclusiones()
            self.save(request)
        except Exception as ex:
            pass

    def guardar_detalle_informe_contratacion(self,ePersonalAContratars,request):
        try:
            for personalcontratar in ePersonalAContratars:
                if personalcontratar.estado_contratacion == 1:
                    eDetalleInformeContratacion = DetalleInformeContratacion(
                        informecontratacion=self,
                        personalcontratar=personalcontratar
                    )
                    eDetalleInformeContratacion.save(request)
                    personalcontratar.estado_contratacion = 2# actualizo que esta en informe
                    personalcontratar.save(request)
            mensaje = "Personal  guardado correctamente"
            return True,mensaje
        except Exception as ex:
            mensaje = f"{ex.__str__()}"
            return False,mensaje

    def get_programas_periodo_maestrias(self):
        carreras_periodo = self.get_detalle_informe_contratacion().annotate(carrera = F('personalcontratar__actaparalelo__convocatoria__carrera_id' ), periodo =F('personalcontratar__actaparalelo__convocatoria__periodo_id')).distinct('carrera').values_list('carrera','periodo').filter(status=True).order_by("carrera")
        return carreras_periodo

    def get_actas_de_comite_academico(self):
        actas_comite_id = self.get_detalle_informe_contratacion().annotate(acta=F('personalcontratar__actaparalelo__acta')).distinct('acta').values_list('acta').filter(status=True).order_by("acta")
        eActaSeleccionDocente = ActaSeleccionDocente.objects.filter(status=True,pk__in=actas_comite_id)
        return eActaSeleccionDocente

    def get_programas_maestria_display(self):
        carreras_maestrias=[]
        for carrera_maestria in self.get_programas_periodo_maestrias():
            eCarrera = Carrera.objects.get(pk=carrera_maestria[0])
            ePeriodo = Periodo.objects.get(pk=carrera_maestria[1])
            carreras_maestrias.append({
                'nombre' : f"{eCarrera} - COHORTE {ePeriodo.numero_cohorte_romano() } - {ePeriodo.anio}",
                'eCarrera' :eCarrera,
                'eCohorte' : f"COHORTE {ePeriodo.numero_cohorte_romano()} - {ePeriodo.anio}"
            })
        return carreras_maestrias

    def get_tipo_profesores(self):
        tipoprofesor_id = self.get_detalle_informe_contratacion().annotate(tipo_profesor = F('personalcontratar__actaparalelo__convocatoria__tipodocente')).values_list('tipo_profesor',flat =True).distinct('tipo_profesor').order_by('tipo_profesor')
        return TipoProfesor.objects.filter(status=True, pk__in=tipoprofesor_id)

    def get_cantidad_de_profesionales(self):
        return self.detalleinformecontratacion_set.filter(status=True).count()

    def get_expedientes(self):
        detalle= self.detalleinformecontratacion_set.filter(status=True)
        eExpedienteContratacion = ExpedienteContratacion.objects.filter(status=True, detalleInformeContratacion__in= detalle)
        return eExpedienteContratacion

    def get_expedientes_vice_envia_a_rectorado(self):
        eExpedienteContratacion=self.get_expedientes()
        return eExpedienteContratacion.filter(revisado_vicerrectorado=True,estado_aprobacion_vicerrectorado = 2)

    def get_estado_expedientes_revisado_por_vicerrectorado_display(self):
        return True if self.get_expedientes_vice_envia_a_rectorado().filter(estado_expediente = 3).exists() else False

    def get_total_contratar_expediente_aprobados_por_vicerrectorado(self):
        total = 0
        for expediente in self.get_expedientes_vice_envia_a_rectorado():
            total += expediente.detalleInformeContratacion.calcular_total_horas_x_valorporhora()
        return total

    def get_configuracion_general_informe_contratacion(self):
        return ConfiguracionInforme.objects.filter(status=True).first() if ConfiguracionInforme.objects.filter(status=True).exists() else None

    def generar_texto_de_actas_de_comite_academico_informe_contratacion(self):
        mensaje = f""
        for acta in self.get_actas_de_comite_academico():
            mensaje += f"N°. {acta.secuenciadocumento.secuencia } de fecha { self.convertir_fecha_a_fecha_letra(acta.fecha_generacion) }, "
        return mensaje

    def generar_texto_objeto_informe_contratacion(self):
        mensaje = f"Informe técnico de contratación por honorarios profesionales en calidad de "
        for tipo_profesor in self.get_tipo_profesores():
            mensaje += f"{tipo_profesor}, "

        if len(self.get_programas_maestria_display()) == 1:
            mensaje += "del programa de"
        else:
            mensaje += "de los programas de"

        for programa in self.get_programas_maestria_display():
            mensaje += f" {programa['nombre']}, "
        mensaje = mensaje[:-2]
        mensaje += '.'
        return mensaje

    def generar_texto_asunto_memo_contratacion(self):
        mensaje = f"Solicitud de contratación "
        mensaje += f'del profesional ' if self.get_cantidad_de_profesionales() == 1 else 'de los profesionales '
        mensaje += f"en calidad de "
        for tipo_profesor in self.get_tipo_profesores():
            mensaje += f"{tipo_profesor}, "
        mensaje += f'del módulo del programa de   ' if self.get_cantidad_de_profesionales() == 1 else 'de los módulos de programas de '
        for programa in self.get_programas_maestria_display():
            mensaje += f" {programa['eCarrera']}, "
        mensaje = mensaje[:-2]
        mensaje += '.'
        return mensaje

    def generar_texto_cuerpo_memo_vicerrectorado_a_rectorado(self):
        mensaje = f'<p style="text-align: justify">De mi consideración:</p>'
        mensaje += f'<p style="text-align: justify"> En virtud al cumplimiento de los documentos habilitantes para iniciar el proceso de contratación de los profesionales aprobados por el Comité Académico de las Escuelas de Posgrado; y, en relación a la solicitud de elaboración de '
        mensaje += f' contrato respectivo' if self.get_cantidad_de_profesionales() == 1 else 'de contratos respectivos'
        mensaje += f', generada por el PhD. Eduardo Espinoza Solis/Director de Posgrado, este despacho, valida la contratación de los siguientes profesionales, según nómina:</p>'
        return mensaje

    def generar_texto_cuerpo_memo_contratacion(self):
        mensaje = f'<p style="text-align: justify">De mi consideración:</p>'
        mensaje += f'<p style="text-align: justify">En virtud al “Proyecto de Inversión en el ámbito de Cooperación entre UNEMI y EPUNEMI, para fortalecer la Interinstitucionalidad a través de desarrollo de programas de Posgrado, de educación continua, eventos culturales, científicos y académicos con los mecanismos integrados de la operatividad entre la Universidad Estatal de Milagro y la EPUNEMI”, aprobado por RESOLUCIÓN DE DIRECTORIO No. 004-SO-003-2024-DIR-EPUNEMI-04 ante el crecimiento significativo de las actividades de comercialización y producción de los programas de cuarto nivel de Posgrado; y, en relación la organización administrativa/financiera para el normal desarrollo académico de los programas de Maestrías, con la finalidad de continuar con el proceso de contratación '
        mensaje += f"en calidad de "
        for tipo_profesor in self.get_tipo_profesores():
            mensaje += f"{tipo_profesor}, "
        mensaje += f'por concepto de honorarios profesionales en '
        mensaje += "la " if len(self.get_programas_maestria_display()) == 1 else "las siguientes maestrías: "
        for programa in self.get_programas_maestria_display():
            mensaje += f" {programa['eCarrera']}, "

        mensaje += f'agradeceré a Usted, se sirva disponer a quien corresponda se gestione '
        mensaje += f'el contrato a favor del profesional.' if self.get_cantidad_de_profesionales() == 1 else f'los contratos a favor de los profesionales.'
        mensaje += f' Se anexa el Informe Técnico <b>No. {self.get_documento_informe().codigo}</b>, el mismo que refleja el siguiente detalle: </p>'

        mensaje = mensaje[:-2]
        mensaje += '.'
        return mensaje

    def generar_texto_antecedente_resoluciones_informe_contratacion(self):
        from inno.models import ProgramaPac
        nombre_mes = lambda x: ["Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio", "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre","Diciembre"][int(x) - 1]
        mensaje =''

        for programa in self.get_programas_maestria_display():
            eProgramaPac = ProgramaPac.objects.filter(status=True, carrera = programa['eCarrera'])
            fechaaprobacioncaces = eProgramaPac.first().fechaaprobacioncaces
            month, day = "%02d" % fechaaprobacioncaces.month, "%02d" % fechaaprobacioncaces.day
            mes = "%s" % nombre_mes(int(fechaaprobacioncaces.strftime("%m")))
            fecha_letra = f"{day} de {mes.lower()} de {fechaaprobacioncaces.year}"
            mensaje += f"<p>Mediante Resolución {eProgramaPac.first().numeroresolucioncaces} de fecha {fecha_letra} en el que, el Consejo de Educación Superior (ces) resolvió aprobar el proyecto de {programa['eCarrera'].nombre} presentado por la Universidad Estatal de Milagro. </p>"

        return mensaje

    def convertir_fecha_a_fecha_letra(self,fecha):
        nombre_mes = lambda x: \
        ["Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio", "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre",
         "Diciembre"][int(x) - 1]
        month, day = "%02d" % fecha.month, "%02d" % fecha.day
        mes = "%s" % nombre_mes(int(fecha.strftime("%m")))
        fecha_letra = f"{day} de {mes.lower()} de {fecha.year}"
        return fecha_letra

    def generar_texto_motivacion_tecnica_informe_contratacion(self):
        from postulaciondip.funciones import numero_a_letras_informe_contratacion_posgrado
        mensaje = '<p>Se solicita la contratación '
        mensaje += f'del profesional aprobado ' if self.get_cantidad_de_profesionales() == 1 else 'de los profesionales aprobados '
        mensaje += 'mediante Acta de Comité Académico de Posgrado, en virtud a la certificación presupuestaría emitida por la Empresa Pública de Producción y Desarrollo Estratégico de la Universidad Estatal de Milagro, descrito en la tabla 1 de la motivación técnica del presente informe. </p>'
        mensaje += '<p>En virtud de que el Consejo de Educación Superior (CES) resolvió aprobar el/los proyecto(s) de Maestría(s) a la Universidad Estatal de Milagro descritos en el antecedente del presente informe; y, conforme a la disponibilidad del recurso presupuestario certificado por la Empresa Pública de Producción y Desarrollo Estratégico de la Universidad Estatal de Milagro, la Dirección de Posgrado solicita la contratación de los siguientes profesionales descritos en la tabla 1. </p>'
        mensaje += f'<p>En virtud de la necesidad de dotar a {numero_a_letras_informe_contratacion_posgrado(self.get_cantidad_de_profesionales())} ({self.get_cantidad_de_profesionales()}) '
        mensaje += f'profesional ' if self.get_cantidad_de_profesionales() == 1  else 'profesionales '
        mensaje +=f'en el programas de ' if self.get_cantidad_de_profesionales() == 1  else 'en los programas de '
        for programa in self.get_programas_maestria_display():
            mensaje += f"{programa['eCarrera'].nombre} ,"
        mensaje += f'se convocó a través de “Postulación Posgrado” la participación de profesionales que cumplan con el perfil requerido para ingresar al proceso de selección a través del módulo “SELECCIÓN DOCENTES POSGRADOS”, en este contexto, mediante Acta de Comité de las Escuelas de Posgrado, resolvieron a  los  profesionales selectos a contratar en los programas de maestrías, según cohorte y paralelo, señalados en la tabla 1.</p>'
        mensaje += f'<p> El ({self.get_cantidad_de_profesionales()}) profesional selecto se encuentra validado' if self.get_cantidad_de_profesionales() == 1 else f"<p> Los ({self.get_cantidad_de_profesionales()}) profesionales selectos se encuentran validados"
        mensaje += f" los documentos habilitantes para iniciar la solicitud de contratación ante nuestra autoridad pertinente de la institución para su debida autorización.</p>"
        return mensaje

    def registrar_integrantes_firman(self,persona,request):
        from sga.models import Persona
        ELABORADO_Y_REVISADO_POR = 1
        VALIDADO_POR = 2
        APROBADO_POR = 3
        VALIDADO_Y_APROBADO_POR = 4
        hoy = datetime.now().date()
        ePersonalApoyoMaestria = PersonalApoyoMaestria.objects.filter(personalapoyo__persona=persona, fechafin__gte=hoy, status=True)
        elaborado_y_revisado_por = None
        if ePersonalApoyoMaestria.exists():
            elaborado_y_revisado_por = ePersonalApoyoMaestria.first().personalapoyo.persona #analista encargado

        eInformeContratacionIntegrantesFirma = InformeContratacionIntegrantesFirma(
            informecontratacion = self,
            ordenFirmaInformeContratacion_id = ELABORADO_Y_REVISADO_POR,
            persona =elaborado_y_revisado_por,
        )
        eInformeContratacionIntegrantesFirma.save(request)

        #ePersonaExperta = Persona.objects.get(pk=variable_valor('ID_EXPERTO_GESTION_POSGRADO'))#diana macias

        #eInformeContratacionIntegrantesFirma = InformeContratacionIntegrantesFirma(
        #    informecontratacion=self,
        #    ordenFirmaInformeContratacion_id=VALIDADO_POR,
        #    persona=ePersonaExperta,
        #)
        #eInformeContratacionIntegrantesFirma.save(request)

        ePersonaDirector = ConfiguracionInforme.objects.filter(status=True).first().de #espinoza solis

        eInformeContratacionIntegrantesFirma = InformeContratacionIntegrantesFirma(
            informecontratacion=self,
            ordenFirmaInformeContratacion_id=VALIDADO_Y_APROBADO_POR,
            persona=ePersonaDirector.persona,
        )
        eInformeContratacionIntegrantesFirma.save(request)

    def generar_actualizar_informe_memo_contratacion_pdf(self,request):
        try:
            self.actualizar_autollenado_informe_contratacion(request)
            self.generar_actualizar_codigo_secuencia(request, None, 1)
            self.generar_actualizar_codigo_secuencia(request, None, 4)
            archivo_informe = self.generar_actualizar_informe_contratacion_pdf(request)
            archivo_memo =self.generar_actualizar_memorandum_informe_contratacion_pdf(request)
            self.generar_actualizar_codigo_secuencia(request, archivo_informe, 1)
            self.generar_actualizar_codigo_secuencia(request, archivo_memo, 4)
            return True
        except Exception as ex:
            pass

    def generar_actualizar_informe_contratacion_pdf(self,request):
        try:
            eInformeContratacion = self
            data, fechaemision = {}, self.fechaemision
            hoy = datetime.now().date()
            name = unicodedata.normalize('NFD', u"informe_%s" % (self.pk)).encode('ascii', 'ignore').decode("utf-8").lower().replace(' ', '_').replace('-', '')
            filename = generar_nombre(u"%s_" % name, f"{name}.pdf")
            filepath = u"documentospostulaciondip/documentos/%s" % hoy.year
            folder_pdf = os.path.join(SITE_STORAGE, 'media', 'documentospostulaciondip','documentos',hoy.year.__str__(),'')
            os.makedirs(os.path.join(folder_pdf), exist_ok=True)
            data['pagesize'] = 'A4'
            data['request'] = request
            data['fechaemision'] = fechaemision
            data['eInformeContratacion'] = eInformeContratacion
            return os.path.join(filepath, filename) if convert_html_to_pdf('adm_contratacion/docs/informe_contratacion_pdf.html', data, filename, folder_pdf) else None

        except Exception as ex:
            pass

    def generar_actualizar_memorandum_informe_contratacion_pdf(self,request):
        try:
            eInformeContratacion = self
            data, fechaemision = {}, self.fechaemision
            hoy = datetime.now().date()
            name = unicodedata.normalize('NFD', u"memo_%s" % (self.pk)).encode('ascii', 'ignore').decode("utf-8").lower().replace(' ', '_').replace('-', '')

            #

            filename = generar_nombre(u"%s_" % name, f"{name}.pdf")

            filepath = u"documentospostulaciondip/documentos/%s" % hoy.year
            folder_pdf = os.path.join(SITE_STORAGE, 'media', 'documentospostulaciondip', 'documentos', hoy.year.__str__(),'')
            os.makedirs(os.path.join(folder_pdf), exist_ok=True)
            data['pagesize'] = 'A4'
            data['request'] = request
            data['fechaemision'] = eInformeContratacion.convertir_fecha_a_fecha_letra(fechaemision)
            data['eInformeContratacion'] = eInformeContratacion
            return os.path.join(filepath, filename) if convert_html_to_pdf('adm_contratacion/docs/memo_informe_contratacion_pdf.html', data, filename, folder_pdf) else None
        except Exception as ex:
            pass

    def generar_actualizar_informe_memo_contratacion_pdf_segundo_plano(self,request):
        self.actualizar_autollenado_informe_contratacion(request)
        a = actualizar_informe_de_contratacion_posgrado(request, self)
        a.start()
        b = actualizar_memo_informe_de_contratacion_posgrado(request, self)
        b.start()

    def guardar_con_secuencia_archivo_informe_contratacion(self,request):
        self.generar_actualizar_codigo_secuencia(request, None, 1)
        archivo_informe = self.generar_actualizar_informe_contratacion_pdf(request)
        self.generar_actualizar_codigo_secuencia(request, archivo_informe, 1)

    def guardar_con_secuencia_archivo_memo_contratacion(self,request):
        self.generar_actualizar_codigo_secuencia(request, None, 4)
        archivo_memo = self.generar_actualizar_memorandum_informe_contratacion_pdf(request)
        self.generar_actualizar_codigo_secuencia(request, archivo_memo, 4)

    def generar_texto_conclusiones(self):
        mensaje = "<p> A partir de lo descrito en el presente informe se concluye: </p>"
        mensaje += " <ul>"
        mensaje += " <li> Que, "
        mensaje += f'el profesional ' if self.get_cantidad_de_profesionales() == 1 else f' los profesionales '
        mensaje += " que se detallan en la tabla 1 dentro de la motivación técnica del presente informe,"
        mensaje += " se encuentra aprobado" if self.get_cantidad_de_profesionales() == 1 else f' se encuentran aprobados '
        mensaje += " por el Comité Académico de las Escuelas de Posgrado respectivos, la misma que fue selecto a través del módulo “SELECCIÓN PROFESOR POSGRADO”.</li>"
        mensaje += "</ul>"
        mensaje += " <ul>"
        mensaje += " <li> Que, una vez revisado los documentos habilitantes "
        mensaje += f'del (1) profesional ' if self.get_cantidad_de_profesionales() == 1 else f'de los ({self.get_cantidad_de_profesionales()}) profesionales '
        mensaje += "para iniciar el proceso de contratación, el número de horas, valor y módulo registrado "
        if len(self.get_programas_maestria_display()) == 1:
            mensaje += " en el programa de Maestría descrito "
        else:
            mensaje += "en los programas de Maestrías descritos "
        mensaje += "en la tabla 1; y, revisada la disponibilidad de tiempo de los profesionales a contratar, se solicita iniciar el proceso de contratación por honorarios profesionales previa autorización por la máxima autoridad.</li>"
        mensaje += "  </ul>"
        mensaje += " <ul>"
        mensaje += " <li> Que, el valor a contratar se encuentra reservado en las certificaciones presupuestarias señaladas en la tabla 1 del presente informe, emitidas por la Empresa Pública de Producción y Desarrollo Estratégico de la Universidad Estatal de Milagro.</li>"
        mensaje += "  </ul>"
        return mensaje

    def generar_texto_recomendaciones(self):
            mensaje = "<li> Se solicita la continuidad del proceso de contratación para el adecuado desarrollo de los programas de maestrías descritos en la tabla 1 antes señalada.</li>"
            return mensaje

    def get_total(self):
        total = 0
        for detalle in self.get_detalle_informe_contratacion():
            total += detalle.calcular_total_horas_x_valorporhora()
        return total


    def todos_los_expedientes(self):
        eDetalleInformeContratacion = self.detalleinformecontratacion_set.filter(status=True)
        eExpedienteContratacion = ExpedienteContratacion.objects.filter(status=True, detalleInformeContratacion__in=eDetalleInformeContratacion)
        return eExpedienteContratacion.filter(status=True)

    def existen_expedientes_pendientes_por_revisar_vicerrectorado(self):
        eExpedienteContratacion = self.todos_los_expedientes()
        return  eExpedienteContratacion.filter(status=True,revisado_vicerrectorado =False).exists()

    def cantidad_expedientes_revisados_vicerrectorado(self):
        eExpedienteContratacion = self.todos_los_expedientes()
        return eExpedienteContratacion.filter(revisado_vicerrectorado =True).count()

    def cantidad_expedientes_pendientes_revisar_vicerrectorado(self):
        eExpedienteContratacion = self.todos_los_expedientes()
        return eExpedienteContratacion.filter(revisado_vicerrectorado =False).count()

class HistorialInformeContratacion(ModeloBase):
    informecontratacion = models.ForeignKey(InformeContratacion, blank=True, null=True, verbose_name=u'Acta selección docente', on_delete=models.CASCADE)
    persona = models.ForeignKey("sga.persona", blank=True, null=True, verbose_name=u'Persona', on_delete=models.CASCADE)
    observacion = models.TextField(verbose_name=u"Observación", blank=True, null=True, default='')
    archivo = models.FileField(upload_to='InformeContratacionPosgradoHistorial/', blank=True, null=True,verbose_name=u"Acta firmada",max_length=600)
    def __str__(self):
        return u'%s' % self.acta

    def archivo_url(self):
        return self.archivo.url if self.archivo else '#'
    class Meta:
        verbose_name = u"Historial Informe Contratacion"
        verbose_name_plural = u"Historial Informe Contratacion"
        ordering = ['id']

class InformeContratacionIntegrantesFirma(ModeloBase):
    informecontratacion =models.ForeignKey(InformeContratacion,  verbose_name=u'informe contratacion', on_delete=models.CASCADE)
    ordenFirmaInformeContratacion =models.ForeignKey(OrdenFirmaInformeContratacion,  verbose_name=u'Responsabilidad', on_delete=models.CASCADE)
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
                cargo = self.persona.cargo_persona().denominacionpuesto.descripcion
        return cargo

    class Meta:
        verbose_name = u"Firma documento informe contratacion posgrado"
        verbose_name_plural = u"Firma documento informe contratacion posgrado"
        ordering = ['-id']

class DetalleInformeContratacion(ModeloBase):
    informecontratacion = models.ForeignKey(InformeContratacion, verbose_name='Informe cabecera', on_delete=models.CASCADE)
    personalcontratar = models.ForeignKey(PersonalAContratar, verbose_name='personal contratar', on_delete=models.CASCADE)
    valor_x_hora = models.ForeignKey(ValorPorHoraInformeContratacion, blank=True, null=True,verbose_name='valor por hora', on_delete=models.CASCADE)
    aplicaIva = models.BooleanField(verbose_name=u"Aplica Iva" ,default = False)
    certificacionpresupuestaria = models.ForeignKey(CertificacionPresupuestariaDip, blank=True, null=True, verbose_name='certificacion presupuestaria', on_delete=models.CASCADE)

    def __str__(self):
        return u"%s" % self.personalcontratar

    class Meta:
        verbose_name = u"Detalle Informe contratación"
        verbose_name_plural = u"Detalle Informes de contratación"
        ordering = ['-id']

    def calcular_total_horas_x_valorporhora(self):
        cantidad = self.valor_x_hora.valor if self.valor_x_hora != None else 0
        valor =  cantidad * self.personalcontratar.actaparalelo.get_total_horas_horario_docente()
        return valor

    def eliminar_personal_contratar_en_detalle_informe_contratacion_and_cambiar_estado_a_pendiente(self,request):
        ePersonalAContratar = self.personalcontratar
        ePersonalAContratar.estado_contratacion = 1
        ePersonalAContratar.save(request)
        self.status=False
        self.save(request)


    def existe_expediente_generado(self):
        return self.expedientecontratacion_set.filter(status=True).exists()

    def get_expediente_contratacion(self):
        return self.expedientecontratacion_set.filter(status=True).first() if self.expedientecontratacion_set.filter(status=True).exists() else None

    def get_estado_expediente_contratacion_display(self):
        display = ''
        if self.existe_expediente_generado():
            if self.expedientecontratacion_set.filter(status=True).first().estado_expediente == 1:
                display = f'<span  title="Estado informe contratación" style="font-size: 11px" class=" badge bg-light-warning text-dark-warning">{self.expedientecontratacion_set.filter(status=True).first().get_estado_expediente_display()}</span>'
            if self.expedientecontratacion_set.filter(status=True).first().estado_expediente == 2:
                display = f'<span  title="Estado informe contratación" style="font-size: 11px" class=" badge bg-light-primary text-dark-primary">{self.expedientecontratacion_set.filter(status=True).first().get_estado_expediente_display()}</span>'
            if self.expedientecontratacion_set.filter(status=True).first().estado_expediente == 3:
                display = f'<span  title="Estado informe contratación" style="font-size: 11px" class=" badge bg-light-success text-dark-success">{self.expedientecontratacion_set.filter(status=True).first().get_estado_expediente_display()}</span>'

        return display

ESTADO_EXPEDIENTE_CONTRATACION =(
(1, 'EN VICERRECTORADO'),
(2, 'DEVUELTO POR VICERRECTORADO'),
(3, 'ENVIADO A RECTORADO'),
(4, 'DEVUELTO POR RECTORADO'),

)
ESTADO_APROBACIONES =(
(1, 'PENDIENTE'),
(2, 'APROBADO'),
(3, 'RECHAZADO'),
)

class ExpedienteContratacion(ModeloBase):
    detalleInformeContratacion = models.ForeignKey(DetalleInformeContratacion, verbose_name='Informe cabecera', on_delete=models.CASCADE)
    revisado_vicerrectorado = models.BooleanField(default=False, verbose_name=u"Revisado vicerrectorado")
    revisado_rectorado = models.BooleanField(default=False, verbose_name=u"Revisado rectorado")
    estado_aprobacion_vicerrectorado = models.IntegerField(choices=ESTADO_APROBACIONES, default=1, verbose_name=u'estado aprobación vicerrectorado')
    estado_aprobacion_rectorado = models.IntegerField(choices=ESTADO_APROBACIONES, default=1, verbose_name=u'estado aprobación rectorado')
    estado_expediente = models.IntegerField(choices=ESTADO_EXPEDIENTE_CONTRATACION, default=1, verbose_name=u'estado contratacion')
    observacion_vicerrectorado = models.CharField(default='', max_length=900, verbose_name=u"Observación vicerrectorado")
    observacion_rectorado = models.CharField(default='', max_length=900, verbose_name=u"Observación rectorado")
    aprobacion_contratacion = models.BooleanField(default=False, verbose_name=u"Aprobación contratación")

    def __str__(self):
        return u"%s" % self.detalleInformeContratacion

    class Meta:
        verbose_name = u"Expediente contratación "
        verbose_name_plural = u"Expediente contratación"
        ordering = ['-id']

    def revisado_por_vicerectorado(self):
        display = ''
        if self.revisado_vicerrectorado:
            display = f'<span  title="Estado expediente revisión" style="font-size: 11px" class=" badge bg-light-warning text-dark-success">REVISADO POR VICERRECTORADO</span>'
        else:
            display = f'<span  title="Estado expediente revisión" style="font-size: 11px" class=" badge bg-light-warning text-dark-warning">PENDIENTE REVISIÓN VICERRECTORADO</span>'
        return display

    def revisado_por_rectorado(self):
        display = ''
        if self.revisado_rectorado:
            display = f'<span  title="Estado expediente revisión" style="font-size: 11px" class=" badge bg-light-warning text-dark-success">REVISADO RECTORADO</span>'
        else:
            display = f'<span  title="Estado expediente revisión" style="font-size: 11px" class=" badge bg-light-warning text-dark-warning">PENDIENTE REVISIÓN RECTORADO</span>'
        return display

    def estado_revisado_vicerrectorado(self):
        display = ''
        if self.revisado_vicerrectorado:
            display = f'<span  title="Estado expediente revisión" style="font-size: 11px" class=" badge bg-light-success text-dark-success">REVISADO</span>'
        else:
            display = f'<span  title="Estado expediente revisión" style="font-size: 11px" class=" badge bg-light-warning text-dark-warning">PENDIENTE</span>'
        return display

    def estado_aprobado_vicerrectorado(self):
        display = ''
        if self.estado_aprobacion_vicerrectorado == 1:
            display = f'<span  title="Estado expediente revisión" style="font-size: 11px" class=" badge bg-light-warning text-dark-warning">PENDIENTE</span>'
        elif self.estado_aprobacion_vicerrectorado ==2:
            display = f'<span  title="Estado expediente revisión" style="font-size: 11px" class=" badge bg-light-success text-dark-success">APROBADO</span>'
        else:
            display = f'<span  title="Estado expediente revisión" style="font-size: 11px" class=" badge bg-light-danger text-dark-danger">RECHAZADO</span>'
        return display


class ActaParaleloRevisionVicerrectorado(ModeloBase):
    actaparalelo = models.ForeignKey(ActaParalelo, verbose_name='acta Paralelo', on_delete=models.CASCADE)
    observacion = models.CharField(default='', max_length=800, verbose_name=u"Observación")


    def __str__(self):
        return u"%s" % self.actaparalelo

    class Meta:
        verbose_name = u"ActaParaleloRevisionVicerrectorado "
        verbose_name_plural = u"ActaParaleloRevisionVicerrectorado"
        ordering = ['-id']


class RecorridoActaSeleccionDocente(ModeloBase):
    acta = models.ForeignKey(ActaSeleccionDocente,blank=True, null=True,  verbose_name=u'Acta selección docente', on_delete=models.CASCADE)
    actaparalelo = models.ForeignKey(ActaParalelo, blank=True, null=True, verbose_name=u'Acta y paralelos', on_delete=models.CASCADE)
    persona = models.ForeignKey('sga.Persona', verbose_name=u'Persona', on_delete=models.CASCADE)
    fecha = models.DateField(verbose_name=u"Fecha")
    observacion = models.TextField(verbose_name=u"Observación", blank=True, null=True, default='')
    archivo = models.FileField(upload_to='actahistorial/', blank=True, null=True,verbose_name=u"Acta firmada",max_length=600)
    def __str__(self):
        return u'%s' % self.acta

    class Meta:
        verbose_name = u"Historial del acta de selección"
        verbose_name_plural = u"Historial del acta de selección"
        ordering = ['id']


class RubricaSeleccionDocente(ModeloBase):
    descripcion = models.TextField(default='', verbose_name=u'Descripcion')
    activo = models.BooleanField(default=False, verbose_name=u'Activo')

    def __str__(self):
        return u'%s' % (self.descripcion)

    class Meta:
        verbose_name = u'RubricaSeleccionDocente'
        verbose_name_plural = u'RubricaSeleccionDocente'
        ordering = ('id',)

    def get_items_rubrica_seleccion_docente(self):
        return self.detalleitemrubricaselecciondocente_set.filter(status=True).order_by('id')

class DetalleItemRubricaSeleccionDocente(ModeloBase):
    rubricaselecciondocente = models.ForeignKey(RubricaSeleccionDocente, on_delete=models.CASCADE)
    descripcion = models.TextField(default='', verbose_name=u'Descripcion')
    orden = models.IntegerField(default=0)

    def __str__(self):
        return u'%s' % (self.descripcion)

    def get_subitems_rubrica_seleccion_docente(self):
        return self.detallesubitemrubricaselecciondocente_set.filter(status=True).order_by('id')

    class Meta:
        verbose_name = u'DetalleItemRubricaSeleccionDocente'
        verbose_name_plural = u'DetalleItemRubricaSeleccionDocente'
        ordering = ('id',)


class DetalleSubItemRubricaSeleccionDocente(ModeloBase):
    detalleitemrubricaselecciondocente = models.ForeignKey(DetalleItemRubricaSeleccionDocente, on_delete=models.CASCADE)
    descripcion = models.TextField(default='', verbose_name=u'Descripcion')
    puntaje = models.IntegerField(default=0, verbose_name=u'puntaje')
    orden = models.IntegerField(default=0)


    def __str__(self):
        return u'%s' % (self.descripcion)

    class Meta:
        verbose_name = u'DetalleSubItemRubricaSeleccionDocente'
        verbose_name_plural = u'DetalleSubItemRubricaSeleccionDocente'
        ordering = ('id',)



class Perms(models.Model):
    class Meta:
        permissions = (
            ("puede_cargar_acta_legalizada", "Ingresar acta legalizada."),
            ("puede_gestionar_personal_apoyo", "Puede crear, editar, eliminar y visualizar el personal de apoyo."),
            ("puede_configurar_plazos_acta", u"Puede editar los plazos de generación y legalización del acta de comite académico."),
            ("puede_firmar_actas_seleccion_docente_posgrado", u"Puede firmar y ver actas de selección docente."),
            ("puede_realizar_planificacion_materias_posgrado", u"Puede realizar planificaciòn materias posgrado"),
            ("puede_visualizar_reporte_planificacion_materia_posgrado", u"Puede visualizar reporte planificacion materia posgrado"),
            ("puede_entrar_como_user_a_seleccionposgrado", u"puede entrar como user a seleccionposgrado "),
            ("puede_ver_todas_las_actas_de_seleccion_docente_posgrado", u"puede ver todas las actas de seleccion docente posgrado "),
            ("puede_adicionar_personal_acta_seleccion_docente", u"puede adicionar aprobados actas seleccion docente "),
            ("puede_editar_eliminar_personal_acta_seleccion_docente", u"puede editar eliminar aprobados actas seleccion docente "),
            ("puede_reiniciar_acta_seleccion_docente_posgrado", u"puede reiniciar actas seleccion docente "),
        )
