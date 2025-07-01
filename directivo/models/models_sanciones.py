#OTROS
from datetime import datetime, timedelta
from unidecode import unidecode

#DJANGO
from django.db import models
from django.contrib.contenttypes.models import ContentType

#CORE
from core.choices.models.sagest import (TIPO_FALTA,ESTADO_DESICION_AUDIENCIA, PUNTO_CONTROL, TIPO_REQUISITO, ESTADO_SANCION_PERSONA,ESTADO_AUDIENCIA,
                                        ESTADO_INCIDENCIA, ACCION_REALIZADA, TIPO_DOCUMENTOS,ESTADO_PRUEBA_DESCARGO,
                                        ESTADO_LEGALIZACION_DOCUMENTO, ETAPA_INCIDENCIA, ROL_FIRMA_DOCUMENTO, ESTADO_APROBACION_ASISTENCIA,
                                        ESTADO_NOTIFICACION_SANCION, ESTADO_FIRMA_ACCION_PERSONAL_SANCION)
#SGA
from sga.funciones import ModeloBase


# Manual de funciones
class ManualFuncion(ModeloBase):
    persona = models.ForeignKey('sga.Persona', on_delete=models.CASCADE, verbose_name='Persona')
    perfilpuesto = models.ForeignKey('sagest.PerfilPuestoTh', on_delete=models.CASCADE, verbose_name='Perfil Puesto')

    def __str__(self):
        return f'{self.persona} | {self.perfilpuesto}'

    class Meta:
        verbose_name = 'Manual de Función'
        verbose_name_plural = 'Manuales de Funciones'
        ordering = ['-id']

class ManualFuncionActividad(ModeloBase):
    manualfuncion = models.ForeignKey(ManualFuncion, on_delete=models.CASCADE, verbose_name='Manual de Función')
    descripcion = models.TextField(default='', verbose_name='Descripción')

    def __str__(self):
        return self.descripcion

    class Meta:
        verbose_name = 'Detalle de Manual de Función'
        verbose_name_plural = 'Detalles de Manuales de Funciones'
        ordering = ['-id']

class RequisitoSancion(ModeloBase):
    nombre = models.CharField(default='', max_length=200, verbose_name='Nombre del requisito de la sanción')
    descripcion = models.TextField(default='', verbose_name='Descripción')
    tiporequisto = models.IntegerField(default=1, choices=TIPO_REQUISITO, verbose_name='Tipo de requisito')

    def __str__(self):
        return self.nombre

    def formatos_permitidos(self):
        if self.tiporequisto == 2:
            return ['.png', '.jpg', '.jpeg']
        return ['.pdf']
    def icono(self):
        if self.tiporequisto == 1:
            return 'bi bi-camera-video'
        elif self.tiporequisto == 2:
            return 'bi bi-image'
        elif self.tiporequisto == 3:
            return 'bi bi-filetype-pdf'
        return 'bi bi-link-45deg'

    def type_input(self):
        if self.tiporequisto in [1, 4]:
            return 'url'
        return 'file'

    def existe_requisitomotivosancion(self):
        return self.requisitomotivosancion_set.filter(status=True).values('id').exists()

    class Meta:
        verbose_name = 'Requisito de sanción'
        verbose_name_plural = 'Requisitos de sanciones'
        ordering = ['-id']

class FaltaDisciplinaria(ModeloBase):
    regimen_laboral = models.ForeignKey('sagest.RegimenLaboral', on_delete=models.CASCADE, verbose_name='Regimen laboral')
    nombre = models.CharField(default='', max_length=200, verbose_name='Nombre de la falta disciplinaria')
    descripcion = models.TextField(default='', verbose_name='Descripción')
    articulo = models.TextField(default='', verbose_name='Articulo')
    motivacionjuridica = models.TextField(default='', verbose_name='Motivacion Juridica')

    def __str__(self):
        return self.nombre

    def motivos(self):
        return self.motivosancion_set.filter(status=True)
    def motivos_principales(self):
        return self.motivosancion_set.filter(status=True, principal=True)
    class Meta:
        verbose_name = 'Falta Disciplinaria'
        verbose_name_plural = 'Faltas Disciplinarias'
        ordering = ['-id']

class MotivoSancion(ModeloBase):
    falta = models.ForeignKey(FaltaDisciplinaria,  blank=True, null=True, verbose_name=u'Falta Disciplinaria', on_delete=models.CASCADE)
    motivoref = models.ForeignKey('self', blank=True, null=True, verbose_name=u'Motivo referenciado', on_delete=models.CASCADE)
    nombre = models.CharField(default='', max_length=200, verbose_name='Nombre del motivo de la sanción')
    descripcion = models.TextField(default='', verbose_name='Descripción')
    principal = models.BooleanField(default=False, verbose_name='¿Es principal?')

    def __str__(self):
        return self.nombre

    def requisitos(self):
        return self.requisitomotivosancion_set.filter(activo=True)

    def sub_motivos(self):
        return MotivoSancion.objects.filter(motivoref=self, status=True, principal=False).order_by('id')

    def existe_incidencia(self):
        return self.incidenciasancion_set.filter(status=True).exists()

    def existe_requisitomotivosancion(self):
        return self.requisitomotivosancion_set.filter(status=True).values('id').exists()

    class Meta:
        verbose_name = 'Motivo de Sanción'
        verbose_name_plural = 'Motivos de Sanción'
        ordering = ['-id']

class RequisitoMotivoSancion(ModeloBase):
    requisito = models.ForeignKey(RequisitoSancion, on_delete=models.CASCADE, verbose_name='Requisito de sanción')
    motivo = models.ForeignKey(MotivoSancion, on_delete=models.CASCADE, verbose_name='Motivo de sanción')
    activo = models.BooleanField(default=True, verbose_name='Activo')
    obligatorio = models.BooleanField(default=True, verbose_name='¿Es obligatorio?')
    punto_control = models.IntegerField(default=0, choices=PUNTO_CONTROL, verbose_name='Punto de Control')

    def __str__(self):
        return self.requisito.nombre

    def existe_incidencia(self):
        return self.evidenciapersonasancion_set.filter(persona_sancion__incidencia__status=True ).values('id').exists()

    class Meta:
        verbose_name = 'Requisito de motivo de sanción'
        verbose_name_plural = 'Requisitos de motivos de sanciones'
        ordering = ['-id']

class PuntoControl(ModeloBase):
    nombre = models.CharField(default='', max_length=200, verbose_name='Nombre de la entrada')
    slug = models.SlugField(default='', max_length=200, verbose_name='Slug')
    # object_id = models.IntegerField(blank=True, null=True, verbose_name="Id de objeto")
    content_type = models.ForeignKey(ContentType, models.SET_NULL, verbose_name=u'Modelo', blank=True, null=True)
    motivos = models.ManyToManyField(MotivoSancion, verbose_name='Motivos de sanción')

    def __str__(self):
        return f'{self.nombre}'

    class Meta:
        verbose_name = 'Punto de Control'
        verbose_name_plural = 'Puntos de control'
        ordering = ['-id']

class IncidenciaSancion(ModeloBase):
    falta = models.ForeignKey(FaltaDisciplinaria, blank=True, null=True, on_delete=models.CASCADE, verbose_name='Falta disciplinaria')
    codigo = models.CharField(default='', max_length=100, verbose_name='Código del proceso')
    numero = models.IntegerField(default=0, verbose_name='Numero de incidencia')
    persona = models.ForeignKey('sga.Persona', blank=True, null=True, on_delete=models.CASCADE, verbose_name='Responsable que crea la incidencia')
    departamento = models.ForeignKey('sagest.Departamento', on_delete=models.CASCADE, verbose_name='Departamento', blank=True, null=True)
    motivo = models.ForeignKey(MotivoSancion, blank=True, null=True, on_delete=models.CASCADE, verbose_name='Motivo de la sanción')
    etapa = models.IntegerField(default=1, choices=ETAPA_INCIDENCIA, verbose_name='Etapa de incidencia')
    estado = models.IntegerField(default=1, choices=ESTADO_INCIDENCIA, verbose_name='Estado de incidencia')
    observacion = models.TextField(default='', blank=True, null=True, verbose_name='Observación Reportada')
    fecha = models.DateTimeField(blank=True, null=True, verbose_name='Fecha de la falta cometida')
    fecha_fin = models.DateTimeField(blank=True, null=True, verbose_name='Fecha cuando se finalizo el caso')
    archivo = models.FileField(blank=True, null=True, upload_to='evidencia_sancion_noprocede/', verbose_name=u'Archivo incidencia caso')

    def __str__(self):
        return self.codigo

    def color_estado(self):
        if self.estado == 0:
            return 'text-muted'
        elif self.estado == 1:
            return 'text-primary'
        elif self.estado == 2:
            return 'text-success'
        elif self.estado == 3:
            return 'text-info'
        elif self.estado == 4:
            return 'text-secondary'
        elif self.estado >= 5:
            return 'text-primary'
        return 'text-danger'
    def personas_sancion(self):
        return self.personasancion_set.filter(status=True)

    def validador_th(self):
        return self.responsableetapaincidencia_set.filter(status=True,
                                                          etapa=2,
                                                          accion=1,
                                                          tipo_doc=1).last()
    def responsable_etapa(self, etapa, tipo_doc, accion):
        return self.responsableetapaincidencia_set.filter(status=True,
                                                          etapa=etapa,
                                                          accion=accion,
                                                          tipo_doc=tipo_doc).last()
    def puede_remitir_caso(self, persona):
        if estado == 1 and self.persona == persona:
            return True
        return estado

    def motivos(self):
        return self.falta.motivosancion_set.filter(status=True)
    def motivos_principales(self):
        return self.motivos().filter(status=True, principal=True)

    def documento(self, tipo_doc):
        return self.documentoetapaincidencia_set.filter(status=True,tipo_doc=int(tipo_doc)).last()

    def personas_sancion_text(self):
        personas = self.personas_sancion_prodecedente().filter(estado=1)
        palabra = 'el servidor'
        if len(personas) > 1:
            palabra = f'los servidores'
        for idx, per in enumerate(personas):
            indice = idx+1
            cargo  = per.persona.mi_cargo_administrativo() if per.persona.mi_cargo_administrativo() else per.persona.mi_cargo()
            palabra += f' {per.persona.nombre_completo_titulo()}, {cargo}'
            if len(personas) > 1 and indice < len(personas) :
                if indice == len(personas) - 1:
                    palabra += ' y '
                else:
                    palabra += ', '
        return palabra
    def personas_sancion_text2(self):
        personas = self.personas_sancion_prodecedente().filter(estado=1)
        palabra = 'el servidor'
        if len(personas) > 1:
            palabra = f'los servidores'
        for idx, per in enumerate(personas):
            indice = idx+1
            cargo  = per.persona.mi_cargo_administrativo() if per.persona.mi_cargo_administrativo() else per.persona.mi_cargo()
            palabra += f' {per.persona.nombre_completo_titulo()}'
            if len(personas) > 1 and indice < len(personas) :
                if indice == len(personas) - 1:
                    palabra += ' y '
                else:
                    palabra += ', '
        return palabra
    def personas_sancion_cedula_text(self):
        personas = self.personas_sancion_prodecedente().filter(estado=1)
        palabra = 'el servidor publico'
        if len(personas) > 1:
            palabra = f'los servidores públicos'
        for idx, per in enumerate(personas):
            indice = idx + 1
            cargo  = per.persona.mi_cargo_administrativo() if per.persona.mi_cargo_administrativo() else per.persona.mi_cargo()
            palabra += f' {per.persona.nombre_completo_minus()} con número de cédula {per.persona.cedula}'
            if len(personas) > 1 and indice < len(personas):
                if idx+1 == len(personas) - 1:
                    palabra += ' y '
                else:
                    palabra += ', '
        return palabra
    def personas_sancion_text_acta(self):
        personas = self.personas_sancion_prodecedente().filter(estado=1)
        palabra=''
        for idx, per in enumerate(personas):
            indice = idx + 1
            cargo  = per.persona.mi_cargo_administrativo() if per.persona.mi_cargo_administrativo() else per.persona.mi_cargo()
            palabra += f'{per.persona.nombre_completo_minus()}'
            if len(personas) > 1 and indice < len(personas):
                if idx+1 == len(personas) - 1:
                    palabra += ' y '
                else:
                    palabra += ', '
        return palabra

    def personas_sancion_prodecedente(self):
        return self.personas_sancion().exclude(estado=2)

    def get_responsables_acta_audiencia(self):
        return ResponsableFirma.objects.filter(firma_doc=True, tipo_doc=2, status=True)

    def permisos_sancion(self, tipo_doc, persona):
        from directivo.utils.funciones import permisos_sanciones
        context={}
        hoy = datetime.now()
        personas_sancion = self.personas_sancion().filter(persona=persona)
        context['audiencia_actual'] = audiencia = self.audiencia_actual()
        context['validador'] = validador = self.validador_th()
        informe_hecho = self.documento(1)
        acta = self.documento(2)
        informe_tecnico = self.documento(4)
        acta_accion_personal = self.documento(3)
        context['acta_reunion'] = acta_reunion = self.documento(5)
        if not personas_sancion:
            context['acta'] = acta
            context['informe_tecnico'] = informe_tecnico
            context['informe_hecho'] = informe_hecho
            permisos = permisos_sanciones(persona)
            permiso_compartido = (permisos['gestor_th'] or permisos['director_th'])
            perms_secretaria_gestor = (permisos['gestor_th'] or permisos['secretaria'])
            context['director_th'] = permisos['director_th']
            context['gestor_th'] = permisos['gestor_th']
            context['secretaria'] = permisos['secretaria']
            context['genera_informes'] = genera_informes = permisos['genera_informes']
            context['puede_ver_opciones'] = permiso_compartido or permisos['revisor']

            # PERMISOS PARA VALIDACION DE PROCEDENCIA
            context['puede_validar'] = self.estado == 2 and permisos['gestor_th']
            es_validador = validador and validador.persona == persona
            es_procedente = self.estado != 4
            context['puede_generar_acta_reunion'] = not es_procedente and not acta_reunion and permiso_compartido
            if es_procedente:
                context['puede_gestionar_caso'] = es_validador and self.estado < 4
                context['puede_validar_descargo'] = es_validador and self.estado < 8 and self.estado > 4
                # PERMISOS DE GENERAR DOCUMENTO
                if not informe_hecho:
                    # Consultar si es el validaro que debe generar el informe o cualquiera que tenga el permiso de gestor
                    context['puede_generar_informe_h'] = self.estado == 3 and (permisos['gestor_th'] or genera_informes)
                else:
                    # PERMISOS PARA NOTIFICACIÓN DE DESCARGO
                    context['puede_remitir_descargo'] = self.estado == 3 and informe_hecho.estado == 3 and permiso_compartido

                context['personas_sancion'] = self.personas_sancion()
                context['personas_sancion_procedentes'] = self.personas_sancion_prodecedente()

                # PERMISOS PARA FINALIZAR ETAPA 2
                context['puede_finalizar_etapa_2'] = self.estado == 5 and permiso_compartido

                # PERMISO PARA CONTROLAR EL ADICIONAR PLANIFICACION DE AUDIENCIA
                existen_audiencias = self.audiencias().exists()
                context['puede_definir_audiencia'] = self.estado == 6 and permiso_compartido and not existen_audiencias

                context['audiencias'] = self.audiencias()
                if audiencia:
                    fecha = audiencia.fecha
                    context['puede_iniciar_audiencia'] = perms_secretaria_gestor and audiencia.estado in [1, 2] #and audiencia.fecha == hoy.date()
                    context['puede_gestionar_audiencia'] = perms_secretaria_gestor  and audiencia.estado in [4, 5] and self.estado == 7
                    if audiencia.estado == 5:
                        context['puede_ver_resusolucion_audiencia'] = audiencia.estado_desicion != 0
                        context['puede_generar_acta'] = permiso_compartido and not acta and audiencia.estado_desicion != 0
                        context['puede_validar_audiencia'] = permiso_compartido and audiencia.estado_desicion == 0
                    if audiencia.estado_desicion == 2:
                        context['puede_generar_accion'] = permiso_compartido
                        context['puede_generar_informe_t'] = (permiso_compartido or genera_informes) and not informe_tecnico
                    context['puede_finalizar_etapa_3'] = self.estado in [8, 9] and permiso_compartido and informe_tecnico and acta and acta_accion_personal
        else:
            # PERMISOS PARA RESPUESTAS DE DESCARGO Y VISUALIZACIÓN EN GENERAL DE PERSONA A SER PROCESADA
            context['audiencias'] = self.audiencias().filter(estado__gte=1)
            context['personas_sancion'] = context['personas_sancion_procedentes']= personas_sancion
            persona_sancion = personas_sancion.first()

            if persona_sancion.estado == 3:
                context['informe_tecnico'] = informe_tecnico
            if not persona_sancion.estado in [0, 2]:
                context['informe_hecho'] = informe_hecho
                context['acta'] = acta
            fecha_notify = persona_sancion.fecha_notify if persona_sancion.fecha_notify else None
            dentroplazo = False
            if fecha_notify:
                dentroplazo = fecha_notify + timedelta(days=1) >= hoy
            context['puede_subir_descargo'] = self.estado == 5 and persona_sancion.estado == 1 and dentroplazo
            context['puede_confirmar_descargo'] = self.estado == 5 and persona_sancion.bloqueo
        return context

    def audiencias(self):
        return self.audienciasancion_set.filter(status=True)

    def audiencia_actual(self):
        return self.audiencias().exclude(estado=3).last()

    class Meta:
        verbose_name = 'Incidencia de sanción'
        verbose_name_plural = 'Incidencias de sanciones'
        ordering = ['-id']


class PersonaSancion(ModeloBase):
    incidencia = models.ForeignKey(IncidenciaSancion, on_delete=models.CASCADE, verbose_name='Incidencia de sanción')
    persona = models.ForeignKey('sga.Persona', on_delete=models.CASCADE, verbose_name='Persona')
    estado = models.IntegerField(default=0, choices=ESTADO_SANCION_PERSONA, verbose_name='Estado de incidencia')
    accionpersonal = models.ForeignKey('sagest.AccionPersonal', blank=True, null=True, on_delete=models.CASCADE, verbose_name='Acción personal')
    fecha_notify = models.DateTimeField(blank=True, null=True, verbose_name='Fecha de notificación para carga de respuestas de descargo')
    bloqueo = models.BooleanField(default=False, verbose_name='Bloqueo del sistema por acción solicitada')
    notificacion = models.IntegerField(default=0, blank=True, null=True, choices=ESTADO_NOTIFICACION_SANCION, verbose_name='Estado de notificación')

    def __str__(self):
        return f'{self.incidencia.codigo} | {self.persona}'

    def color_estado(self):
        if self.estado in [2, 4]:
            return 'texto-blue'
        elif self.estado in [1, 3]:
            return 'text-primary'
        return 'text-muted'
    def evidencias(self):
        return self.evidenciapersonasancion_set.filter(status=True).order_by('requisito_motivo__requisito')

    def requisitos(self):
        return self.incidencia.punto_control.motivos.all()

    def permisos_sancion(self, persona):
        hoy = datetime.now()
        fecha_notify = self.fecha_notify if self.fecha_notify else None
        dentroplazo = False
        if fecha_notify:
            dentroplazo = fecha_notify + timedelta(days=1) >= hoy
        puede_subir_descargo = self.estado == 5 and self.estado == 1 and dentroplazo
        return {'persona_sancion':persona_sancion,'puede_subir_descargo': puede_subir_descargo}

    def respuestas_descargo(self):
        return self.respuestadescargo_set.filter(status=True)

    def accion_personal(self):
        return DocumentoEtapaIncidencia.objects.filter(incidencia=self.incidencia, tipo_doc=3, persona_recepta=self.persona, status=True).last()

    def documento(self):
        return DocumentoEtapaIncidencia.objects.filter(incidencia=self.incidencia, tipo_doc=3, persona_recepta=self.persona, status=True).last()

    def consulta_firma_persona_sancion(self, tipo_doc):
        return self.consultafirmapersonasancion_set.filter(status=True, tipo_doc=tipo_doc).first()

    def servidor_firma_accion_personal(self):
        consulta_firma = self.consulta_firma_persona_sancion(3)
        firma_servidor = False
        if consulta_firma:
            firma_servidor = consulta_firma.estado == 1
        return firma_servidor

    class Meta:
        verbose_name = 'Persona Sanción'
        verbose_name_plural = 'Personas Sanciones'
        ordering = ['-id']

class ConsultaFirmaPersonaSancion(ModeloBase):
    persona_sancion = models.ForeignKey(PersonaSancion, on_delete=models.CASCADE, verbose_name='Persona Sanción')
    estado = models.IntegerField(default=0, choices=ESTADO_FIRMA_ACCION_PERSONAL_SANCION, verbose_name='Estado de firma')
    motivo = models.TextField(default='', blank=True, null=True, verbose_name='Motivo de negativa')
    tipo_doc = models.IntegerField(blank=True, null=True, choices=TIPO_DOCUMENTOS, verbose_name='Tipo de documento')
    fecha_respuesta = models.DateTimeField(blank=True, null=True, verbose_name='Fecha de respuesta')

    def __str__(self):
        return f'{self.persona_sancion}'

    class Meta:
        verbose_name = 'Consulta de firma de persona sanción'
        verbose_name_plural = 'Consultas de firma de personas sanciones'
        ordering = ['-id']

class AudienciaSancion(ModeloBase):
    incidencia = models.ForeignKey(IncidenciaSancion, on_delete=models.CASCADE, verbose_name='Incidencia de sanción')
    descripcion = models.CharField(default='', max_length=300, verbose_name='Motivo de la audiencia o motivo de la reprogramación')
    numerodelegacion = models.CharField(default='', max_length=50, verbose_name='Número de delegación')
    fecha = models.DateField(blank=True, null=True, verbose_name='Fecha de la audiencia')
    horainicio = models.TimeField(blank=True, null=True, verbose_name='Hora de inicio')
    horafin = models.TimeField(blank=True, null=True, verbose_name='Hora de fin')
    fecha_notify = models.DateTimeField(blank=True, null=True, verbose_name='Fecha de notificación')
    estado = models.IntegerField(default=0, choices=ESTADO_AUDIENCIA, verbose_name='Estado de audiencia')
    bloque = models.ForeignKey('sagest.Bloque', blank=True, null=True, on_delete=models.CASCADE, verbose_name='Bloque de audiencia')
    ubicacion = models.ForeignKey('sagest.Ubicacion', blank=True, null=True, on_delete=models.CASCADE, verbose_name='Ubicación de audiencia')
    referencia = models.CharField(default='', max_length=200, verbose_name='Referencia del lugar de audiencia')
    fecha_inicio = models.DateTimeField(blank=True, null=True, verbose_name='Fecha y hora que inicio la audiencia')
    fecha_fin = models.DateTimeField(blank=True, null=True, verbose_name='Fecha y hora que finalizo la audiencia')
    estado_desicion = models.IntegerField(default=0, choices=ESTADO_DESICION_AUDIENCIA, verbose_name='Estado de la desición de la audiencia')
    observacion = models.TextField(default='', blank=True, null=True, verbose_name='Observación de desición del caso')

    def __str__(self):
        return str(self.fecha)

    def lugar(self):
        palabra = self.bloque.descripcion
        if self.ubicacion:
            if self.ubicacion.piso:
                palabra += f', {self.ubicacion.get_piso_display().lower()}'
            palabra += f', {self.ubicacion}'
        if self.referencia:
            palabra += f' ({self.referencia})'
        return palabra

    def esta_en_audiencia(self):
        hoy = datetime.now()
        fecha = self.fecha
        fecha_inicio = datetime.combine(fecha, self.horainicio)
        fecha_fin = datetime.combine(fecha, self.horafin)
        return hoy >= fecha_inicio and hoy <= fecha_fin

    def estado_text(self):
        if self.esta_en_audiencia():
            return 'En audiencia'
        return self.get_estado_display()

    def color_estado(self):
        if self.estado == 0:
            return 'bg-light-default text-dark-default'
        elif self.estado == 1:
            return 'bg-light-info text-dark-info'
        elif self.estado == 2:
            return 'bg-light-success text-dark-success'
        elif self.estado == 3:
            return 'bg-light-danger text-dark-danger'
        elif self.estado == 4:
            return 'bg-light-warning text-dark-warning'
        return 'bg-light-primary text-dark-primary'
    def color_estadodecision(self):
        if self.estado_desicion == 0:
            return 'bg-light-info text-dark-info'
        elif self.estado_desicion == 2:
            return 'bg-light-warning text-dark-warning'
        elif self.estado_desicion == 1:
            return 'bg-light-success text-dark-success'
        return 'bg-light-primary text-dark-primary'
    def personas_audiencia(self):
        return self.personaaudienciasancion_set.filter(status=True).order_by('rol_firma')

    def personas_firmar_acta_audicencia(self):
        # se excluye al abogado
        return self.personaaudienciasancion_set.filter(status=True).exclude(rol_firma=13).order_by('rol_firma')

    def get_personas_audiencia_procedentes(self):
        persona_sancion_ids =  self.incidencia.personas_sancion().filter(estado=1).values_list('persona_id', flat=True)
        return self.personas_audiencia().filter(persona_id__in=persona_sancion_ids)

    def get_persona_audiencia(self, persona):
        persona_audicencia = self.personas_audiencia().filter(persona=persona).first()
        return persona_audicencia

    def todos_asistiran(self):
        return self.personas_audiencia().filter(asistira=True).count() == self.personas_audiencia().count()

    def personas_audiencia_asistiran(self):
        total =  self.personas_audiencia()
        total_asistiran = total.filter(asistira=True).count()
        total_no_asistiran = total.filter(asistira=False).count()
        total_pendientes = total.filter(asistira=None).count()
        todos = total.count() == total_asistiran
        return {'todos':todos , 'total_asistiran':total_asistiran, 'total_no_asistiran':total_no_asistiran, 'total_pendientes':total_pendientes}

    def personas_audiencia_excl(self):
        ids_exclude=self.incidencia.personas_sancion_prodecedente().values_list('persona_id', flat=True)
        return self.personas_audiencia().exclude(persona_id__in=ids_exclude)

    def puede_editar(self):
        return self.estado == 0
    def puede_reprogramar(self):
        return self.estado in [1, 2]
    def puede_registra_participantes(self):
        return not self.estado in [3, 5]

    def detalle_inicial_audiencia(self):
        lista=['Alegato inicial de parte actora',
               'Alegato inicial del servidor público',
               'Anuncio y reproducción de prueba de la parte actora',
               'Anuncio y reproducción de prueba del servidor público',
               'Alegato Final de la parte actora',
               'Alegato Final del servidor público',
               'Alegato del servidor público para acta de audiencia']
        for idx, l in enumerate(lista):
            DetalleAudienciaSancion.objects.create(audiencia=self, titulo=l, orden=idx+1)

    def detalle_audiencia(self):
        return self.detalleaudienciasancion_set.filter(status=True)

    def detalle_audiencia_alegato_acta_audiencia(self):
        detalle = self.detalleaudienciasancion_set.filter(status=True, orden=7).first()
        if detalle:
            return detalle.descripcion
        else:
            return ''

    def mostar_seccion_asistencia(self):
        return self.estado in [1, 2]

    def mostar_boton_validar_asistencia(self):
        return self.estado in [1, 2]

    class Meta:
        verbose_name = 'Audiencia de sanción'
        verbose_name_plural = 'Audiencias de sanciones'
        ordering = ['fecha']

class DetalleAudienciaSancion(ModeloBase):
    audiencia = models.ForeignKey(AudienciaSancion, on_delete=models.CASCADE, verbose_name='Audiencia de sanción')
    titulo = models.CharField(default='', max_length=1000, verbose_name='Titulo de la sección')
    descripcion = models.TextField(default='', blank=True, null=True, verbose_name='Descripción de la audiencia')
    orden = models.IntegerField(default=1, verbose_name='Orden de la sección')
    def __str__(self):
        return self.titulo

    class Meta:
        verbose_name = 'Detalle de audiencia de sanción'
        verbose_name_plural = 'Detalles de audiencias de sanciones'
        ordering = ['orden']

class PersonaAudienciaSancion(ModeloBase):
    audiencia = models.ForeignKey(AudienciaSancion, on_delete=models.CASCADE, verbose_name='Audiencia de sanción')
    persona = models.ForeignKey('sga.Persona',blank=True, null=True,  on_delete=models.CASCADE, verbose_name='Persona')
    asistira = models.BooleanField(null=True, blank=True, verbose_name='¿Asistirá a la audiencia?')
    asistio = models.BooleanField(null=True, blank=True, verbose_name='¿Asistió a la audiencia?')
    justificacion = models.TextField(default='', blank=True, null=True, verbose_name='Justificación de no asistencia')
    observacion_asis = models.TextField(default='', blank=True, null=True, verbose_name='Observación de rechazo asistencia')
    archivo = models.FileField(upload_to='evidencia_justificacion_sanciones/', blank=True, null=True, verbose_name='Archivo de justificación')
    validacion_asis = models.IntegerField(blank=True, null=True, default=0, choices=ESTADO_APROBACION_ASISTENCIA, verbose_name='Validación de asistencia')
    rol_firma = models.IntegerField(blank=True, null=True, choices=ROL_FIRMA_DOCUMENTO, verbose_name='Rol del participante en la audiencia')
    def __str__(self):
        return f'{self.audiencia} | {self.persona}'

    def asistira_text(self):
        if self.asistira is None:
            return '<span class="text-muted">Pendiente</span>'
        elif self.asistira:
            return '<span class="text-success">Asistirá</span>'
        return '<span class="text-danger">No asistirá</span>'

    def color_validacion_asis(self):
        if self.validacion_asis == 0:
            return 'secondary'
        elif self.validacion_asis == 1:
            return 'success'
        return 'danger'

    def get_cargo(self):
        return self.persona.mi_cargo_administrativo() if self.persona.mi_cargo_administrativo() else self.persona.mi_cargo()

    def get_persona_sancion(self):
        return self.audiencia.incidencia.personas_sancion().filter(persona=self.persona).first()

    class Meta:
        verbose_name = 'Persona Audiencia Sanción'
        verbose_name_plural = 'Personas Audiencias Sanciones'
        ordering = ['rol_firma']

class ResponsableFirma(ModeloBase):
    persona = models.ForeignKey('sga.Persona', blank=True, null=True, on_delete=models.CASCADE, verbose_name='Responsable que firma')
    firma_doc = models.BooleanField(default=False, verbose_name='La persona es encargada de firmar un documento')
    tipo_doc = models.IntegerField(default=1, choices=TIPO_DOCUMENTOS, verbose_name='Tipo de documento que firma')
    rol_doc = models.IntegerField(default=1, choices=ROL_FIRMA_DOCUMENTO, verbose_name='Rol que cumple en el documento')
    orden = models.IntegerField(default=1, verbose_name=u"Orden")

    def __str__(self):
        return str(self.persona)

    def get_cargo(self):
        return self.persona.mi_cargo_administrativo() if self.persona.mi_cargo_administrativo() else self.persona.mi_cargo()

    class Meta:
        verbose_name = 'Responsable que firma un documento'
        verbose_name_plural = 'Responsables que firman un documento'
        ordering = ['orden']

class ResponsableEtapaIncidencia(ModeloBase):
    incidencia = models.ForeignKey(IncidenciaSancion, on_delete=models.CASCADE, verbose_name='Incidencia de sanción')
    persona = models.ForeignKey('sga.Persona', blank=True, null=True, on_delete=models.CASCADE, verbose_name='Responsable que valida el proceder de la incidencia')
    observacion = models.TextField(default='', blank=True, null=True, verbose_name='Observación')
    etapa = models.IntegerField(default=1, choices=ETAPA_INCIDENCIA, verbose_name='Etapa de incidencia')
    accion = models.IntegerField(default=1, choices=ACCION_REALIZADA, verbose_name='Acción que realizo en el sistema')
    firma_doc = models.BooleanField(default=False, verbose_name='La persona es encargada de firmar un documento')
    tipo_doc = models.IntegerField(default=1, choices=TIPO_DOCUMENTOS, verbose_name='Tipo de documento que firma')
    orden = models.IntegerField(default=1, verbose_name=u"Orden")

    def __str__(self):
        return str(self.persona)

    class Meta:
        verbose_name = 'Responsable de etapa de incidencia'
        verbose_name_plural = 'Responsables de etapas de incidencias'
        ordering = ['orden']

class HistorialIncidenciaSancion(ModeloBase):
    incidencia = models.ForeignKey(IncidenciaSancion, on_delete=models.CASCADE, verbose_name='Incidencia de sanción')
    persona = models.ForeignKey('sga.Persona', blank=True, null=True, on_delete=models.CASCADE, verbose_name='Persona que realiza la acción')
    etapa = models.IntegerField(default=1, choices=ETAPA_INCIDENCIA, verbose_name='Etapa de incidencia')
    estado = models.IntegerField(default=1, choices=ESTADO_INCIDENCIA, verbose_name='Estado de incidencia general')
    accion = models.IntegerField(default=1, choices=ACCION_REALIZADA, verbose_name='Acción realizada')
    observacion = models.TextField(default='', blank=True, null=True, verbose_name='Observación')

    def __str__(self):
        return self.incidencia.codigo

    class Meta:
        verbose_name = 'Historial de incidencia de sanción'
        verbose_name_plural = 'Historiales de incidencias de sanciones'
        ordering = ['-id']

class EvidenciaPersonaSancion(ModeloBase):
    persona_sancion = models.ForeignKey(PersonaSancion, on_delete=models.CASCADE, verbose_name='Persona sanción')
    requisito_motivo = models.ForeignKey(RequisitoMotivoSancion,blank=True, null=True, on_delete=models.CASCADE, verbose_name='Requisito de motivo de sanción')
    archivo = models.FileField(upload_to='evidencia_sanciones/', verbose_name='Archivo')
    url = models.URLField(default='', verbose_name='URL')

    def __str__(self):
        return f'{self.persona_sancion} | {self.requisito_motivo}'

    def evidencia(self):
        if self.requisito_motivo:
            if self.requisito_motivo.requisito.tiporequisto in [1, 4] and self.url:
                return f'<a href="{self.url}" target="_blank">{self.url[:30]}</a>'
            elif self.requisito_motivo.requisito.tiporequisto == 2 and self.archivo:
                return (f'<a data-fancybox="image" href="{self.archivo.url}" class="texto-blue">'
                        f'<img style="width: 25px!important;"'
                        f'class="img-4by3-lg rounded " '
                        f'src="{self.archivo.url}"> Imagen cargada</a>')
            elif self.requisito_motivo.requisito.tiporequisto == 3 and self.archivo:
                return (f'<a href="{self.archivo.url}" '
                        'class="texto-blue") '
                        'data-width="2048" data-height="1380" '
                        f'data-fancybox="evidencia_{self.id}"'
                        f'data-caption="Evidencia: {self.requisito_motivo.requisito}"'
                        'data-placement="top"><i '
                        'class="bi bi-filetype-pdf text-danger fs-4">'
                        f'</i> {self.requisito_motivo.requisito}</a>')
        elif self.archivo:
            return (f'<a data-fancybox="image" href="{self.archivo.url}" class="texto-blue">'
                    f'<img style="width: 25px!important;"'
                    f'class="img-4by3-lg rounded " '
                    f'src="{self.archivo.url}"> Imagen capturada por el sistema</a>')
        return '<span class="text-muted">No se ha registrado el requisito</span>'
    class Meta:
        verbose_name = 'Evidencia de persona sanción'
        verbose_name_plural = 'Evidencias de personas sanciones'
        ordering = ['-id']

class ReunionMediacion(ModeloBase):
    incidencia = models.ForeignKey(IncidenciaSancion, on_delete=models.CASCADE, verbose_name='Incidencia de sanción')
    convocador = models.ForeignKey('sga.Persona', blank=True, null=True, on_delete=models.CASCADE, related_name='convocador_set', verbose_name='Persona que convoca la reunión')
    organizador = models.ForeignKey('sga.Persona', blank=True, null=True, on_delete=models.CASCADE, related_name='organizador_set', verbose_name='Persona que organiza la reunión')
    apuntador = models.ForeignKey('sga.Persona', blank=True, null=True, on_delete=models.CASCADE, related_name='apuntador_set', verbose_name='Persona que apunta la reunión')
    tema = models.CharField(default='', max_length=300, verbose_name='Tema de la reunión')
    desarrollo = models.TextField(default='', blank=True, null=True, verbose_name='Desarrollo de la reunión')
    conclusion = models.TextField(default='', blank=True, null=True, verbose_name='Conclusiones')
    fecha = models.DateField(blank=True, null=True, verbose_name='Fecha de la audiencia')
    horainicio = models.TimeField(blank=True, null=True, verbose_name='Hora de inicio')
    horafin = models.TimeField(blank=True, null=True, verbose_name='Hora de fin')
    bloque = models.ForeignKey('sagest.Bloque', blank=True, null=True, on_delete=models.CASCADE, verbose_name='Bloque de audiencia')
    ubicacion = models.ForeignKey('sagest.Ubicacion', blank=True, null=True, on_delete=models.CASCADE, verbose_name='Ubicación de audiencia')
    referencia = models.CharField(default='', max_length=200, verbose_name='Referencia del lugar de audiencia')

    def __str__(self):
        return str(self.fecha)

    class Meta:
        verbose_name = 'Reunión de mediación'
        verbose_name_plural = 'Reuniones de mediación'
        ordering = ['fecha']

class DocumentoEtapaIncidencia(ModeloBase):
    incidencia = models.ForeignKey(IncidenciaSancion, on_delete=models.CASCADE, verbose_name='Incidencia de sanción')
    audiencia = models.ForeignKey(AudienciaSancion, blank=True, null=True, on_delete=models.CASCADE, verbose_name='Audiencia de la sanción')
    reunion = models.ForeignKey(ReunionMediacion, blank=True, null=True, on_delete=models.CASCADE, verbose_name='Reunión de mediación')
    accionpersonal = models.ForeignKey('sagest.AccionPersonal', blank=True, null=True, on_delete=models.CASCADE, verbose_name='Acción personal')
    archivo = models.FileField(upload_to='documentos_sanciones/', blank=True, null=True, verbose_name='Archivo')
    estado = models.IntegerField(default=1, choices=ESTADO_LEGALIZACION_DOCUMENTO, verbose_name='Estado de legalización del documento')
    firmado = models.BooleanField(default=False, verbose_name='Documento firmado')
    tipo_doc = models.IntegerField(default=1, choices=TIPO_DOCUMENTOS, verbose_name='Tipo de documento generado')
    # TEXTO DE DOCUMENTO
    persona_elabora = models.ForeignKey('sga.Persona', blank=True, null=True, on_delete=models.CASCADE, related_name='persona_elabora_set', verbose_name='Persona que elabora el documento')
    persona_recepta = models.ForeignKey('sga.Persona', blank=True, null=True, on_delete=models.CASCADE, related_name='persona_recepta_set', verbose_name='Persona que recepta el documento tambien la persona sanción')
    objeto = models.TextField(default='', verbose_name='Objeto')
    antecedentes = models.TextField(default='', verbose_name='Antecedentes')
    motivacion = models.TextField(default='', verbose_name='Motivación Técnica')
    conclusion = models.TextField(default='', verbose_name='Conclusión')
    recomendacion = models.TextField(default='', verbose_name='Recomendación')
    secuencia = models.IntegerField(verbose_name='Secuencia de documento', blank=True, null=True)
    codigo = models.CharField(default='', max_length=50, verbose_name='Código de documento', blank=True, null=True)

    def __str__(self):
        return f'{self.persona_elabora}'

    def name_doc(self):
        return unidecode(f'{self.get_tipo_doc_display()}'.replace(' ', '_').lower())[:15]
    def get_persona_sancion(self):
        return self.incidencia.personas_sancion().filter(persona=self.persona_recepta).first()
    def get_persona_sancion_prop(self, persona):
        return self.incidencia.personas_sancion().filter(persona=persona).first()
    def responsables_legalizacion(self):
        return self.personafirmadocumento_set.filter(status=True)

    def get_responsables_firma_generar_accion_personal(self):
        return self.responsables_legalizacion().exclude(rol_firma__in=[1, 9, 7, 14])

    # se excluye al abodago
    def responsables_firma_acta_audiencia(self):
        return self.personafirmadocumento_set.filter(status=True).exclude(rol_firma=13)

    def get_persona_firma(self, persona):
        return self.responsables_legalizacion().filter(persona=persona).first()

    def puede_firmar(self, persona):
        resp = self.responsables_legalizacion().filter(persona=persona, firmado=False, negativa=False).exists()
        return resp

    def firmado_all(self):
        #negativa: cuando la persona no quiere firmar el documento|solo acción personal
        responsables = self.responsables_legalizacion().filter(negativa=False)
        firmados = responsables.filter(firmado=True, negativa=False).values_list('persona_id', flat=True).order_by('persona_id')
        return len(responsables) == len(firmados)

    def historia_firmas(self):
        return self.historialdocumentofirma_set.filter(status=True)

    def color_esado(self):
        if self.estado == 1:
            return 'texto-blue'
        elif self.estado == 2:
            return 'text-primary'
        return 'text-success'

    def permisos_documento(self, persona):
        from directivo.utils.funciones import permisos_sanciones
        context = {}
        permisos = permisos_sanciones(persona)
        context['puede_editar_documento'] = self.persona_elabora == persona and (permisos['gestor_th'] or permisos['genera_informes'])
        context['puede_firmar'] = self.puede_firmar(persona)
        return context

    def sustanciador(self):
        return self.personafirmadocumento_set.filter(rol_firma=4).first()

    def secretario(self):
        return self.personafirmadocumento_set.filter(rol_firma=5).first()

    def responsable_acciompersonal(self):
        return self.responsables_legalizacion().filter(rol_firma=8).first()
    def delegado_acciompersonal(self):
        return self.responsables_legalizacion().filter(rol_firma=9).first()
    def funcionario_acciompersonal(self):
        return self.responsables_legalizacion().filter(rol_firma=10).first()

    def director_acciompersonal(self):
        return self.responsables_legalizacion().filter(rol_firma=0).first()

    def get_anexos(self):
        return self.anexodocumentoincidencia_set.filter(status=True).order_by('orden')

    class Meta:
        verbose_name = 'Documento de etapa de incidencia'
        verbose_name_plural = 'Documentos de etapas de incidencias'
        ordering = ['-id']

class AnexoDocumentoIncidencia(ModeloBase):
    documentoetapa = models.ForeignKey(DocumentoEtapaIncidencia, on_delete=models.CASCADE, verbose_name='Documento de etapa de incidencia')
    nombre = models.CharField(default='', max_length=100, verbose_name='Nombre del anexo')
    archivo = models.FileField(upload_to='anexos_documentos_sanciones/', verbose_name='Archivo')
    orden = models.IntegerField(default=0, verbose_name='Orden de anexo', blank=True, null=True)
    fecha_generacion = models.DateTimeField(blank=True, null=True, verbose_name='Fecha de generación del anexo')
    num_paginas = models.IntegerField(default=0, verbose_name='Número de páginas del anexo', blank=True, null=True)

    def __str__(self):
        return str(self.nombre)

    class Meta:
        verbose_name = 'Anexo de documento de etapa de incidencia'
        verbose_name_plural = 'Anexos de documentos de etapas de incidencias'
        ordering = ['orden']

class PersonaFirmaDocumento(ModeloBase):
    documento = models.ForeignKey(DocumentoEtapaIncidencia, on_delete=models.CASCADE, verbose_name='Documento a firmar')
    persona = models.ForeignKey('sga.Persona', blank=True, null=True, on_delete=models.CASCADE, verbose_name='Responsable que valida el proceder de la incidencia')
    cargo = models.ForeignKey('sagest.DenominacionPuesto', blank=True, null=True, verbose_name=u"Cargo del responsable a firmar", on_delete=models.CASCADE)
    firmado = models.BooleanField(default=False, verbose_name='Firmo documento')
    orden = models.IntegerField(default=1, verbose_name=u"Orden")
    rol_firma = models.IntegerField(blank=True, null=True, default=1, choices=ROL_FIRMA_DOCUMENTO, verbose_name='Rol en el documento')
    subrogante = models.BooleanField(default=False, verbose_name='Subrogante del cargo')
    negativa = models.BooleanField(default=False, verbose_name='Negativa de firma')
    planaccion = models.TextField(default='', blank=True, null=True, verbose_name='Plan de acción')


    def __str__(self):
        return str(self.persona)

    class Meta:
        verbose_name = 'Persona que firma el documento'
        verbose_name_plural = 'Personas que firman el documento'
        ordering = ['orden']

class HistorialDocumentoFirma(ModeloBase):
    documento = models.ForeignKey(DocumentoEtapaIncidencia, on_delete=models.CASCADE, verbose_name='Documento')
    persona = models.ForeignKey('sga.Persona', blank=True, null=True, on_delete=models.CASCADE, verbose_name='Persona que realiza la acción')
    estado = models.IntegerField(default=1, choices=ESTADO_LEGALIZACION_DOCUMENTO, verbose_name='Estado de legalización de documento')
    archivo = models.FileField(upload_to='doc_historial_sancion/', blank=True, null=True, verbose_name='Archivo')

    def __str__(self):
        return self.documento

    def color_esado(self):
        if self.estado == 1:
            return 'texto-blue'
        elif self.estado == 2:
            return 'text-primary'
        return 'text-success'

    class Meta:
        verbose_name = 'Historial de documento firma'
        verbose_name_plural = 'Historial de documentos firmados'
        ordering = ['-id']

class RespuestaDescargo(ModeloBase):
    personasancion = models.ForeignKey(PersonaSancion, on_delete=models.CASCADE, verbose_name='Persona Sanción')
    descripcion = models.CharField(default='', max_length=400, verbose_name='Descripción del archivo')
    archivo = models.FileField(upload_to='respuesta_descargo/', blank=True, null=True, verbose_name='Archivo')
    estado = models.IntegerField(default=0, choices=ESTADO_PRUEBA_DESCARGO, verbose_name='Estado de legalización de documento')
    observacion = models.CharField(default='', max_length=300, verbose_name='Observación de validación')

    def __str__(self):
        return str(self.personasancion)

    def color_estado(self):
        if self.estado == 2:
            return 'texto-danger'
        elif self.estado == 1:
            return 'text-success'
        return 'text-muted'
    def icon_archivo(self):
        from sga.templatetags.sga_extras import tipo_archivo
        tipo = tipo_archivo(self.archivo.name)
        if tipo == 'pdf':
            return 'bi bi-filetype-pdf text-danger'
        elif tipo == 'img':
            return 'bi bi-image-fill'
        return 'bi bi-file-earmark-text'


    class Meta:
        verbose_name = 'Respuesta descargo'
        verbose_name_plural = 'Respuestas de descargo'
        ordering = ['-id']