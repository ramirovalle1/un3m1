# -*- coding: UTF-8 -*-
from _decimal import Decimal
import time

from django import template
from django.core.exceptions import ObjectDoesNotExist
from django.db import models, connections, transaction
from django.db.models import manager, Q

from settings import TIPO_RESPUESTA_EVALUACION, DEBUG
from sga.funciones import fechaletra_corta, fields_model, field_default_value_model, trimestre, null_to_decimal, \
    convertir_fecha, generar_usuario_admision
from sga.models import SubirMatrizInscripcion, Carrera, HistorialProcesoSubirMatrizInscripcion, \
    RegistroTareaSubirMatrizInscripcion, HistorialSubirMatrizInscripcion, ObservacionSubirMatrizInscripcion, \
    CriterioSubirMatrizInscripcion, TituloProcesoSubirMatrizInscripcion, ProcesoSubirMatrizInscripcion, Nivel, \
    Materia, Modalidad, Asignatura, Raza, Persona, Provincia, Canton, Inscripcion, DocumentosDeInscripcion, Sede, \
    Sesion, Matricula, MateriaAsignada, AsignaturaMalla, Asignatura, Paralelo, PerfilUsuario, AuditoriaMatricula, \
    PerdidaGratuidad, Pais, Parroquia, Malla, PersonaTituloUniversidad, InstitucionEducacionSuperior, \
    NacionalidadIndigena, Discapacidad, InstitucionBeca, InscripcionMalla, RecordAcademico
from sagest.models import Rubro, TipoOtroRubro
from datetime import datetime, timedelta, date
from django.contrib.contenttypes.models import ContentType
from django.contrib.contenttypes.fields import GenericForeignKey, GenericRelation
from settings import MATRICULACION_LIBRE, UTILIZA_GRUPOS_ALUMNOS, NOMBRE_NIVEL_AUTOMATICO, MATRICULACION_POR_NIVEL, \
    CAPACIDAD_MATERIA_INICIAL, CUPO_POR_MATERIA, APROBACION_DISTRIBUTIVO, USA_EVALUACION_INTEGRAL, \
    TIPO_DOCENTE_TEORIA, TIPO_DOCENTE_PRACTICA, VERIFICAR_CONFLICTO_DOCENTE, TIPO_CUOTA_RUBRO, SITE_STORAGE, \
    HORAS_VIGENCIA, ADMISION_ID, USA_TIPOS_INSCRIPCIONES, NOTA_ESTADO_EN_CURSO, TIPO_INSCRIPCION_INICIAL, \
    TIPO_DOCENTE_FIRMA, TIPO_DOCENTE_AYUDANTIA, EMAIL_INSTITUCIONAL_AUTOMATICO, EMAIL_DOMAIN, ALUMNOS_GROUP_ID
from sga.funciones import log, convertir_fecha, puede_realizar_accion, puede_realizar_accion_afirmativo, \
    null_to_decimal, generar_nombre, fechatope, convertir_fecha_invertida, variable_valor, MiPaginador, \
    dia_semana_ennumero_fecha, null_to_numeric, calculate_username, generar_usuario
from openpyxl import load_workbook


class My_CriterioSubirMatrizInscripcion(CriterioSubirMatrizInscripcion):
    objects = models.Manager()

    class Meta:
        proxy = True
        verbose_name = u"Criterio de Importar matriz de inscripción"
        verbose_name_plural = u"Criterios de Importar matriz de inscripción"

    def __init__(self, *args, **kwargs):
        super(My_CriterioSubirMatrizInscripcion, self).__init__(*args, **kwargs)

    def save(self, *args, **kwargs):
        super(My_CriterioSubirMatrizInscripcion, self).save(*args, **kwargs)


class My_ProcesoSubirMatrizInscripcion(ProcesoSubirMatrizInscripcion):
    objects = models.Manager()

    class Meta:
        proxy = True

    def __init__(self, *args, **kwargs):
        super(My_ProcesoSubirMatrizInscripcion, self).__init__(*args, **kwargs)

    def save(self, *args, **kwargs):
        super(My_ProcesoSubirMatrizInscripcion, self).save(*args, **kwargs)


class My_TituloProcesoSubirMatrizInscripcion(TituloProcesoSubirMatrizInscripcion):
    objects = models.Manager()

    class Meta:
        proxy = True
        verbose_name = u"Proceso Matriz de aspirante de SENESCYT"
        verbose_name_plural = u"Procesos Matriz de aspirantes de SENESCYT"

    def __init__(self, *args, **kwargs):
        super(My_TituloProcesoSubirMatrizInscripcion, self).__init__(*args, **kwargs)

    def procesos(self):
        return My_ProcesoSubirMatrizInscripcion.objects.filter(status=True, proceso=self).order_by('orden')

    def save(self, *args, **kwargs):
        super(My_TituloProcesoSubirMatrizInscripcion, self).save(*args, **kwargs)


class My_RegistroTareaSubirMatrizInscripcion(RegistroTareaSubirMatrizInscripcion):
    objects = models.Manager()

    class Meta:
        proxy = True

    def __init__(self, *args, **kwargs):
        super(My_RegistroTareaSubirMatrizInscripcion, self).__init__(*args, **kwargs)

    def status_tarea(self):
        return self.tarea.statusProcess()

    def result_tarea(self):
        return self.tarea.resultProcess()

    def cancel_tarea(self):
        return self.tarea.cancelProcess()

    def save(self, *args, **kwargs):
        super(My_RegistroTareaSubirMatrizInscripcion, self).save(*args, **kwargs)


class My_SubirMatrizInscripcion(SubirMatrizInscripcion):
    objects = models.Manager()

    class Meta:
        proxy = True

    def __init__(self, *args, **kwargs):
        super(My_SubirMatrizInscripcion, self).__init__(*args, **kwargs)

    def contentype_app_model(self):
        return ContentType.objects.get(app_label='sga', model='subirmatrizinscripcion')

    def inactivar_procesos(self, request):
        self.estado = 4
        self.status = False
        self.save(request)
        procesos = self.historialprocesosubirmatrizinscripcion_set.all()
        for proceso in procesos:
            proceso.estado = 1
            proceso.save(request)
            historiales = proceso.historialsubirmatrizinscripcion_set.all()
            for historial in historiales:
                observaciones = historial.observacionsubirmatrizinscripcion_set.all()
                for observacion in observaciones:
                    observacion.status = False
                    observacion.save(request)
        self.cancelar_proceso_matricula()

    def listado_procesos(self):
        return My_ProcesoSubirMatrizInscripcion.objects.filter(proceso=self.proceso)

    def procesos(self):
        return My_HistorialProcesoSubirMatrizInscripcion.objects.filter(status=True, matriz=self).order_by('proceso__orden')

    def ultimo_proceso(self):
        ultimo_init = ultimo_error = ultimo_success = My_HistorialProcesoSubirMatrizInscripcion.objects.filter(matriz=self, status=True)
        ultimo_init = ultimo_init.filter(estado=1).order_by('proceso__orden')
        ultimo_error = ultimo_error.filter(estado=3).order_by('proceso__orden')
        ultimo_success = ultimo_success.filter(estado=2).order_by('proceso__orden')
        if ultimo_error.exists():
            return ultimo_error[0]
        elif ultimo_init.exists():
            return ultimo_init[0]
        elif ultimo_success.exists():
            return ultimo_success[0]
        else:
            return []

    def siguiente_proceso(self):
        ultimo_init = ultimo_error = My_HistorialProcesoSubirMatrizInscripcion.objects.filter(matriz=self, status=True)
        ultimo_init = ultimo_init.filter(estado=1).order_by('proceso__orden')
        ultimo_error = ultimo_error.filter(estado=3).order_by('proceso__orden')
        if ultimo_init.exists():
            return ultimo_init[0]
        elif ultimo_error.exists():
            return ultimo_error[0]
        else:
            return []

    def proceso_pendiente(self):
        historial = My_HistorialProcesoSubirMatrizInscripcion.objects.filter(matriz=self, status=True, estado__in=[3, 4])
        return True if not historial.exists() else False

    def historial_procesos(self):
        return My_HistorialProcesoSubirMatrizInscripcion.objects.filter(matriz=self, status=True)

    def total_procesos(self):
        return My_HistorialProcesoSubirMatrizInscripcion.objects.values("id").filter(matriz=self, status=True).count()

    def total_procesos_exitosos(self):
        return My_HistorialProcesoSubirMatrizInscripcion.objects.values("id").filter(matriz=self, status=True, estado=2).count()

    def puede_editar(self):
        historial = My_HistorialProcesoSubirMatrizInscripcion.objects.filter(matriz=self, status=True, proceso__accion='VALIDA_MATRIZ', estado__in=[1, 3, 4])
        return True if historial.values("id").exists() else False

    def mis_registro_tareas(self):
        return My_RegistroTareaSubirMatrizInscripcion.objects.filter(matriz=self, status=True)

    def mis_tareas_proceso_matriz(self):
        tasks = self.mis_registro_tareas()
        return tasks.filter(proceso=1, content_type=None, object_id=None).order_by('-fecha_creacion')

    def puede_ejecutar_matriz(self):
        # tasks = My_RegistroTareaSubirMatrizInscripcion.objects.filter(matriz=self).order_by('-fecha_creacion')
        # if not tasks.filter(proceso__in=[1,2,3]).exists():
        #     return True
        # if tasks.filter(proceso__in=[2,3]).exists():
        #     return False
        # isCanRun = False
        # for task in tasks.filter(proceso=1):
        #     if task.status_tarea() in ['FAILURE'] or My_HistorialProcesoSubirMatrizInscripcion.objects.filter(matriz=self, estado=3).exists():
        #         isCanRun = True
        #         break
        # return isCanRun
        return True

    def tareas_matriculacion_masiva(self):
        #return self.registrotareasubirmatrizinscripcion_set.filter(proceso=2, content_type=None, object_id=None).order_by('-fecha_creacion')
        return My_RegistroTareaSubirMatrizInscripcion.objects.filter(proceso=2, content_type=None, object_id=None, matriz=self).order_by('-fecha_creacion')


    def tareas_matriculacion_carrera(self, carrera):
        content_type = ContentType.objects.get_for_model(carrera)
        #return self.registrotareasubirmatrizinscripcion_set.filter(proceso=3, content_type=content_type, object_id=carrera.id).order_by('-fecha_creacion')
        return My_RegistroTareaSubirMatrizInscripcion.objects.filter(proceso=3, content_type=content_type, object_id=carrera.id, matriz=self).order_by('-fecha_creacion')

    def puede_ejecutar_matricular(self, carrera=None):
        #tasks = self.registrotareasubirmatrizinscripcion_set.filter(proceso__in=[2, 3]).order_by('-fecha_creacion')
        tasks = My_RegistroTareaSubirMatrizInscripcion.objects.filter(proceso__in=[2, 3], matriz=self).order_by('-fecha_creacion')
        if carrera:
            tasks = tasks.filter(content_type=ContentType.objects.get_for_model(carrera), object_id=carrera.id, proceso=3)
        if not tasks.exists():
            return True
        isCanRun = False
        for task in tasks:
            if task.status_tarea() in ['FAILURE']:
                isCanRun = True
                break
        return isCanRun

    def status_matricular_masiva(self):
        #tasks = self.registrotareasubirmatrizinscripcion_set.filter(proceso=2).order_by('-fecha_creacion')
        tasks = My_RegistroTareaSubirMatrizInscripcion.objects.filter(proceso=2, matriz=self).order_by('-fecha_creacion')
        return 'NO_START' if not tasks.exists() else tasks[0].status_tarea()

    def status_matricular_carrera(self, carrera_id):
        carrera_id = int(carrera_id) if carrera_id is str else carrera_id
        carrera = Carrera.objects.get(pk=carrera_id)
        tasks = My_RegistroTareaSubirMatrizInscripcion.objects.filter(content_type=ContentType.objects.get_for_model(carrera), object_id=carrera.id, proceso=3, matriz=self).order_by('-fecha_creacion')
        return 'NO_START' if not tasks.exists() else tasks[0].status_tarea()

    def cancelar_proceso_matriz(self):
        #tasks = self.registrotareasubirmatrizinscripcion_set.filter(proceso=1).order_by('-fecha_creacion')
        tasks = My_RegistroTareaSubirMatrizInscripcion.objects.filter(proceso=1, matriz=self).order_by('-fecha_creacion')
        if tasks.exists():
            for task in tasks:
                if task.status_tarea() == 'PENDING':
                    task.cancel_tarea()

    def cancelar_proceso_matricula(self):
        tasks = My_RegistroTareaSubirMatrizInscripcion.objects.filter(proceso__in=[2, 3], matriz=self).order_by('-fecha_creacion')
        #tasks = self.registrotareasubirmatrizinscripcion_set.filter(proceso__in=[2, 3]).order_by('-fecha_creacion')
        if tasks.values("id").exists():
            for task in tasks:
                my_task = My_RegistroTareaSubirMatrizInscripcion(task)
                if my_task.status_tarea() == 'PENDING':
                    my_task.cancel_tarea()

    def cancelar_proceso_matricula_masiva(self):
        #tasks = self.registrotareasubirmatrizinscripcion_set.filter(proceso=2).order_by('-fecha_creacion')
        tasks = My_RegistroTareaSubirMatrizInscripcion.objects.filter(proceso=2, matriz=self).order_by('-fecha_creacion')
        if tasks.exists():
            for task in tasks:
                if task.status_tarea() == 'PENDING':
                    task.cancel_tarea()

    def cancelar_proceso_matricula_carrera(self, carrera):
        content_type = ContentType.objects.get_for_model(carrera)
        tasks = My_RegistroTareaSubirMatrizInscripcion.objects.filter(content_type=carrera, object_id=carrera.id, proceso=3, matriz=self).order_by('-fecha_creacion')
        #tasks = self.registrotareasubirmatrizinscripcion_set.filter(content_type=carrera, object_id=carrera.id, proceso=3).order_by('-fecha_creacion')
        if tasks.exists():
            for task in tasks:
                if task.status_tarea() == 'PENDING':
                    task.cancel_tarea()

    def validar_matriz_senescyt(self, proceso, persona):
        if proceso:
            historial_observaciones_errores = proceso.deshabilitar_observaciones_errores(persona.usuario)
            historial_observaciones_exitosos = proceso.deshabilitar_observaciones_exitosos(persona.usuario)
            if proceso:
                historial = My_HistorialSubirMatrizInscripcion(historial=proceso, estado=1)
                historial.save(usuario_id=persona.usuario.id)
                crear_observacion(historial, [], persona)
        return True

    def crear_persona_senescyt(self, proceso, persona):
        # INVALIDO [FALSE] TODOS LAS OBSERVACIONES YA SEAN [ERROR, SUCCESS]
        if proceso:
            historial_observaciones_errores = proceso.deshabilitar_observaciones_errores(persona.usuario)
            historial_observaciones_exitosos = proceso.deshabilitar_observaciones_exitosos(persona.usuario)

        # CONSULTO LAS OBSERVACIONES DE SUCCESS DEL PROCESO VALIDA_MATRIZ
        historial_proceso_validar = My_HistorialProcesoSubirMatrizInscripcion.objects.filter(status=True,
                                                                                             proceso__accion='VALIDA_MATRIZ',
                                                                                             matriz=self)
        print(historial_proceso_validar)
        cedulas = Matricula.objects.filter( status=True, nivel__periodo_id=336, retiradomatricula=False, materiaasignada__materia__asignaturamalla__malla__carrera__coordinacion=9).values_list('inscripcion__persona__cedula', flat=True)
        cedulas_matriculas = ",".join(f"'{cedula}'" for cedula in cedulas)
        if not len(cedulas_matriculas):
            cedulas_matriculas = "'0'"
        # historial_proceso_validar = matriz.historialprocesosubirmatrizinscripcion_set.filter(status=True, proceso__accion='VALIDA_MATRIZ')
        if not historial_proceso_validar.exists():
            mensaje = {'mensaje': 'No existe data a procesar'}
            if historial_observaciones_errores.exists():
                crear_observacion(historial_observaciones_errores[0], mensaje, persona)
            else:
                if proceso:
                    historial = My_HistorialSubirMatrizInscripcion(historial=proceso, estado=2)
                    historial.save(usuario_id=persona.usuario.id)
                    crear_observacion(historial, mensaje, persona)
            return False
        else:
            # historial_proceso_validar_observaciones_success = historial_proceso_validar[0].historialsubirmatrizinscripcion_set.filter(status=True, estado=1)
            historial_proceso_validar_observaciones_success = My_HistorialSubirMatrizInscripcion.objects.filter(status=True, estado=1, historial=historial_proceso_validar[0])
            if not historial_proceso_validar_observaciones_success.exists():
                mensaje = {'mensaje': 'No existe data a procesar'}
                if historial_observaciones_errores.exists():
                    crear_observacion(historial_observaciones_errores[0], mensaje, persona)
                else:
                    if proceso:
                        historial = My_HistorialSubirMatrizInscripcion(historial=proceso, estado=2)
                        historial.save(usuario_id=persona.usuario.id)
                        crear_observacion(historial, mensaje, persona)
                return False

        observaciones_success = historial_proceso_validar_observaciones_success[0].observaciones()

        if not observaciones_success.exists():
            return False
        dataErrorObservaciones = []
        dataSuccessObservaciones = []

        errorfichero = False
        cursor = connections['admision'].cursor()
        sql = f"""
            SELECT 
                app_p.id, 
                app_p.type_document, 
                app_p.document, 
                app_p."names", 
                app_p.firstname, 
                app_p.lastname,
                app_p.cellphone_number,
                app_p.residence_phone_number,
                app_p.personal_email,
                app_p.datebirth,
                app_s."name" AS sexo,
                app_c_r."name" AS pais_residencia,
                app_p_r."name" AS provincia_residencia,
                app_ca_r."name" AS canton_residencia,
                app_pa_r."name" AS parroquia_residencia,
                app_p.residence_main_street AS calle_principal_residencia,
                app_p.residence_side_street AS calle_secundaria_residencia,
                app_p.residence_number AS numero_casa_residencia,
                app_qc."id" AS id_qc
            FROM app_quotaassignmentapplicantcareer AS app_qc
            INNER JOIN app_applicant AS app_a ON app_a.id = app_qc.applicant_id
            INNER JOIN app_inscription AS app_i ON app_i.id = app_a.inscription_id
            INNER JOIN app_person AS app_p ON app_p.id=app_i.person_id
            LEFT JOIN app_sex AS app_s ON app_s.id=app_p.sex_id
            LEFT JOIN app_country AS app_c_r ON app_c_r.id=app_p.residence_country_id
            LEFT JOIN app_province AS app_p_r ON app_p_r.id=app_p.residence_province_id
            LEFT JOIN app_canton AS app_ca_r ON app_ca_r.id=app_p.residence_canton_id
            LEFT JOIN app_parish AS app_pa_r ON app_pa_r.id=app_p.residence_parish_id
            WHERE app_a.period_id={self.periodo_id_sag}
            and not app_p.document in ({cedulas_matriculas})
            """
        cursor.execute(sql)
        results = cursor.fetchall()
        total = len(results)
        contador = 0
        from unidecode import unidecode
        for result in results:
            dataFila = {}
            # print(result)
            contador += 1
            with transaction.atomic():
                try:
                    documento = result[2]
                    tipo_documento = result[1]
                    ePersona = Persona.objects.filter(Q(cedula=documento) | Q(pasaporte=documento)).first()
                    update = False
                    if not ePersona:
                        if tipo_documento == 1:  # CEDULA
                            ePersona = Persona(cedula=documento)
                        else:  # PASAPORTE
                            ePersona = Persona(pasaporte=documento)
                        ePersona.status = True
                        ePersona.apellido1 = result[4]
                        ePersona.apellido2 = result[5]
                        ePersona.nombres = result[3]
                        ePersona.sexo_id = 1 if result[10] == 'Mujer' else 2
                        ePersona.nacimiento = result[9] if result[9] else datetime.now().date()
                        ePersona.paisnacimiento = None
                        ePersona.provincianacimiento = None
                        ePersona.cantonnacimiento = None
                        try:
                            ePais = Pais.objects.get(nombre=str(result[11]).upper())
                        except ObjectDoesNotExist:
                            ePais = None
                        eProvincia = None
                        eCanton = None
                        eParroquia = None
                        if ePais:
                            try:
                                eProvincia = Provincia.objects.get(nombre=str(result[12]).upper(), pais=ePais)
                            except ObjectDoesNotExist:
                                eProvincia = None
                            if eProvincia:
                                try:
                                    eCanton = Canton.objects.get(nombre=str(result[13]).upper(), provincia=eProvincia)
                                except ObjectDoesNotExist:
                                    eCanton = None
                                if eCanton:
                                    try:
                                        eParroquia = Parroquia.objects.get(nombre=str(result[14]).upper(), canton=eCanton)
                                    except ObjectDoesNotExist:
                                        eParroquia = None
                        ePersona.pais = ePais
                        ePersona.provincia = eProvincia
                        ePersona.canton = eCanton
                        ePersona.parroquia = eParroquia
                        ePersona.email = result[8]
                        ePersona.telefono = result[6]
                        ePersona.telefono_conv = result[7]
                        ePersona.save(usuario_id=persona.usuario.id)
                    elif not unidecode(ePersona.apellido1) == unidecode(result[4]) or not unidecode(ePersona.apellido2) == unidecode(result[5]) or not unidecode(ePersona.nombres) ==  unidecode(result[3]):
                        if not result[5] == '':
                            update = not ePersona.inscripcion_set.filter(status=True).exclude(carrera__coordinacion=9).exists()
                            ePersona.status = True
                            ePersona.apellido1 = result[4]
                            ePersona.apellido2 = result[5]
                            ePersona.nombres = result[3]
                            ePersona.sexo_id = 1 if result[10] == 'Mujer' else 2
                            ePersona.nacimiento = result[9] if result[9] else datetime.now().date()
                            ePersona.email = result[8]
                            ePersona.telefono = result[6]
                            ePersona.telefono_conv = result[7]
                            ePersona.save(usuario_id=persona.usuario.id)
                    if not ePersona.usuario:
                        username = calculate_username(ePersona)
                        usuario = generar_usuario_admision(ePersona, username, ALUMNOS_GROUP_ID)
                        if EMAIL_INSTITUCIONAL_AUTOMATICO:
                            ePersona.emailinst = username + '@' + EMAIL_DOMAIN
                            ePersona.save(usuario_id=persona.usuario_id)
                    else:
                        username = calculate_username(ePersona)
                        if not ePersona.usuario.username == username and update:
                            replaceuser = ePersona.usuario
                            replaceuser.username = username
                            replaceuser.save()
                            if EMAIL_INSTITUCIONAL_AUTOMATICO:
                                ePersona.emailinst = username + '@' + EMAIL_DOMAIN
                                ePersona.save(usuario_id=persona.usuario_id)
                        if not ePersona.usuario.is_active:
                            eUser = ePersona.usuario
                            eUser.is_active = True
                            eUser.set_password(ePersona.documento())
                            eUser.save()
                            ePersona.cambiar_clave()
                    dataFila['PERSONA_ID'] = ePersona.id if ePersona else 0
                    dataFila['ID_QC'] = result[18] if not result[18] in ['', "", 'NULL', None] else 0
                    print(f"{total}/{contador} Creo/Actualizo --> Persona:{ePersona.__str__()}")
                except Exception as ex:
                    transaction.set_rollback(True)
                    errorfichero = True
                    dataErrorObservaciones.append({'data': result, 'error': ex.__str__()})

            if dataFila:
                dataSuccessObservaciones.append(dataFila)
        if errorfichero:
            if historial_observaciones_errores.exists():
                crear_observacion(historial_observaciones_errores[0], dataErrorObservaciones, persona)
            else:
                if proceso:
                    historial = My_HistorialSubirMatrizInscripcion(historial=proceso, estado=2)
                    historial.save(usuario_id=persona.usuario.id)
                    crear_observacion(historial, dataErrorObservaciones, persona)
            return False
        else:
            if historial_observaciones_exitosos.exists():
                crear_observacion(historial_observaciones_exitosos[0], dataSuccessObservaciones, persona)
            else:
                if proceso:
                    historial = My_HistorialSubirMatrizInscripcion(historial=proceso, estado=1)
                    historial.save(usuario_id=persona.usuario.id)
                    crear_observacion(historial, dataSuccessObservaciones, persona)
            return True

    def crear_inscripcion_senescyt(self, proceso, persona):
        # INVALIDO [FALSE] TODOS LAS OBSERVACIONES YA SEAN [ERROR, SUCCESS]
        if proceso:
            historial_observaciones_errores = proceso.deshabilitar_observaciones_errores(persona.usuario)
            historial_observaciones_exitosos = proceso.deshabilitar_observaciones_exitosos(persona.usuario)

        # CONSULTO LAS OBSERVACIONES DE SUCCESS DEL PROCESO CREA_PERSONA
        historial_proceso_persona = My_HistorialProcesoSubirMatrizInscripcion.objects.filter(status=True,
                                                                                             proceso__accion='CREA_PERSONA',
                                                                                             matriz=self)
        if not historial_proceso_persona.exists():
            mensaje = {'mensaje': 'No existe data a procesar'}
            if historial_observaciones_errores.exists():
                crear_observacion(historial_observaciones_errores[0], mensaje, persona)
            else:
                if proceso:
                    historial = My_HistorialSubirMatrizInscripcion(historial=proceso, estado=2)
                    historial.save(usuario_id=persona.usuario.id)
                    crear_observacion(historial, mensaje, persona)
            return False
        else:
            historial_proceso_persona_observaciones_success = My_HistorialSubirMatrizInscripcion.objects.filter(status=True, estado=1, historial=historial_proceso_persona[0])
            if not historial_proceso_persona_observaciones_success.exists():
                mensaje = {'mensaje': 'No existe data a procesar'}
                if historial_observaciones_errores.exists():
                    crear_observacion(historial_observaciones_errores[0], mensaje, persona)
                else:
                    if proceso:
                        historial = My_HistorialSubirMatrizInscripcion(historial=proceso, estado=2)
                        historial.save(usuario_id=persona.usuario.id)
                        crear_observacion(historial, mensaje, persona)
                return False

        observaciones_success = historial_proceso_persona_observaciones_success[0].observaciones()
        if not observaciones_success.exists():
            return False
        dataErrorObservaciones = []
        dataSuccessObservaciones = []
        errorfichero = False
        eSede = Sede.objects.get(pk=1)
        contador = 0
        total = len(observaciones_success[0].observacion)
        for arrDataSuccess in observaciones_success[0].observacion:
            # print(arrDataSuccess)
            contador += 1
            dataFila = {}
            tiene_titulo_publico = False
            isAcceptQuotaActive = False
            id_qc = arrDataSuccess.get('ID_QC', 0)
            persona_id = arrDataSuccess.get('PERSONA_ID', 0)
            with transaction.atomic():
                try:
                    try:
                        ePersona = Persona.objects.get(pk=persona_id)
                    except ObjectDoesNotExist:
                        raise NameError(u"No se encontro persona")

                    cursor = connections['admision'].cursor()
                    sql = f"""
                            SELECT 
                                app_a.id AS aplicante_id,
                                app_qc.application_score AS nota_postulacion,
                                app_apc.malla_admision_pk AS malla_id,
--                                 app_a."isAcceptQuotaActive"
                                app_a."isAsignadoCupoHistoricoSNNA"
                            FROM app_quotaassignmentapplicantcareer AS app_qc
                            INNER JOIN app_applicant AS app_a ON app_a.id = app_qc.applicant_id
                            INNER JOIN app_academicperiodcareer AS app_apc ON app_apc.career_id = app_qc.career_id AND app_apc.period_id={self.periodo_id_sag}
                            WHERE app_a.period_id={self.periodo_id_sag} AND app_qc.id={id_qc} LIMIT 1
                                """
                    cursor.execute(sql)
                    row = cursor.fetchone()
                    aplicante_id = row[0]
                    puntaje = row[1]
                    malla_id = row[2]
                    isAcceptQuotaActive = row[3]

                    try:
                        eMalla = Malla.objects.get(pk=malla_id)
                    except ObjectDoesNotExist:
                        raise NameError(u"No se encontro malla")
                    eCarrera = eMalla.carrera
                    eModalidad = eMalla.modalidad

                    if eCarrera and ePersona and eModalidad and eSede:
                        try:
                            eInscripcion = Inscripcion.objects.get(persona=ePersona, carrera=eCarrera)
                        except ObjectDoesNotExist:
                            eInscripcion = Inscripcion(persona=ePersona,
                                                       puntajesenescyt=puntaje,
                                                       fecha=datetime.now().date(),
                                                       carrera=eCarrera,
                                                       coordinacion=eCarrera.coordinacion_carrera(),
                                                       modalidad=eModalidad,
                                                       sede=eSede,
                                                       colegio="N/S" if not ePersona.inscripcion_set.filter().exists() else ePersona.inscripcion_set.filter()[0].colegio)
                            eInscripcion.save(usuario_id=persona.usuario.id)
                            ePersona.crear_perfil(inscripcion=eInscripcion, visible=False)
                            documentos = DocumentosDeInscripcion(inscripcion=eInscripcion,
                                                                 titulo=False,
                                                                 acta=False,
                                                                 cedula=False,
                                                                 votacion=False,
                                                                 actaconv=False,
                                                                 partida_nac=False,
                                                                 pre=False,
                                                                 observaciones_pre='',
                                                                 fotos=False)
                            documentos.save(usuario_id=persona.usuario.id)
                        # eInscripcion.preguntas_inscripcion()
                        # mallaalu = eInscripcion.inscripcionmalla_set.all()
                        # mallaalu.delete()
                        # eInscripcion.actualizar_nivel()
                        # eInscripcion.modalidad = eModalidad
                        # eInscripcion.bloqueomatricula = False
                        # eInscripcionMalla = InscripcionMalla(inscripcion=eInscripcion, malla=eMalla)
                        # eInscripcionMalla.save()
                        eInscripcion.save(usuario_id=persona.usuario.id)
                        dataFila['INSCRIPCION_ID'] = eInscripcion.id
                        dataFila['ID_QC'] = id_qc
                        print(f"{total}/{contador}  Creo/Actualizo --> Inscripción:{eInscripcion.__str__()}")
                        sql = f"""
                                SELECT  
                                    app_pat.formation_type, 
                                    app_pat.level_education, 
                                    app_pat.title, 
                                    app_pat.institution,
                                    app_pat.title_type,
                                    app_pat.degree_date,
                                    app_pat.graduation_date,
                                    app_pat.study_start_date,	
                                    app_pat.registration_date,
                                    app_pat.registration_number,
                                    app_pat.country_study,
                                    app_pat.financing_type,
                                    app_pat.name_career
                                FROM app_quotaassignmentapplicantcareer AS app_qc
                                INNER JOIN app_applicant AS app_a ON app_a.id = app_qc.applicant_id
                                INNER JOIN app_inscription AS app_i ON app_i.id= app_a.inscription_id
                                INNER JOIN app_person AS app_p ON app_p.id=app_i.person_id
                                INNER JOIN app_personacademictraining AS app_pat ON app_pat.person_id=app_p.id
                                WHERE app_a.period_id={self.periodo_id_sag} 
--                                 AND app_qc."isAcceptQuota" = TRUE 
                                AND app_pat.formation_type = 3 AND app_qc.id={id_qc}
                                """
                        cursor.execute(sql)
                        results = cursor.fetchall()
                        print(f"{total}/{contador}  Consulta SQL :{results}")
                        for result in results:
                            codigoregistro = result[9]
                            fecharegistro = result[8]
                            fechainicio = result[7]
                            fecharegresado = result[6]
                            fechaacta = result[5]
                            try:
                                ePersonaTituloUniversidad = PersonaTituloUniversidad.objects.get(persona=ePersona, codigoregistro=codigoregistro)
                            except ObjectDoesNotExist:
                                ePersonaTituloUniversidad = PersonaTituloUniversidad(persona=ePersona,
                                                                                     codigoregistro=codigoregistro)
                            ePersonaTituloUniversidad.fecharegistro=fecharegistro
                            ePersonaTituloUniversidad.fechainicio=fechainicio
                            ePersonaTituloUniversidad.fecharegresado=fecharegresado
                            ePersonaTituloUniversidad.fechaacta=fechaacta
                            if result[10]:
                                try:
                                    ePaisUniversidad = Pais.objects.get(nombre=str(result[10]).upper())
                                except ObjectDoesNotExist:
                                    ePaisUniversidad = Pais(nombre=str(result[10]).upper())
                                    ePaisUniversidad.save()
                                try:
                                    eInstitucionEducacionSuperior = InstitucionEducacionSuperior.objects.get(nombre=str(result[3]).upper())
                                    eInstitucionEducacionSuperior.pais=ePaisUniversidad
                                except ObjectDoesNotExist:
                                    eInstitucionEducacionSuperior = InstitucionEducacionSuperior(nombre=str(result[3]).upper(),
                                                                                                 pais=ePaisUniversidad)
                                eInstitucionEducacionSuperior.save()
                                ePersonaTituloUniversidad.universidad=eInstitucionEducacionSuperior
                                financing_type = result[11]
                                tipouniversidad = 0
                                if financing_type == 1: #PRIVADA
                                    tipouniversidad = 4
                                elif financing_type == 2: #PUBLICA
                                    tipouniversidad = 1
                                elif financing_type == 3: #PARTICULAR AUTOFINANCIADA
                                    tipouniversidad = 2
                                elif financing_type == 4: #PARTICULAR COFINANCIADA
                                    tipouniversidad = 3
                                ePersonaTituloUniversidad.tipouniversidad = tipouniversidad
                            ePersonaTituloUniversidad.nombrecarrera = result[12]
                            tiponivel = 0
                            level_education = result[1]
                            if level_education == 1: #TECNICO-TECNOLOGO
                                tiponivel = 2
                            elif level_education == 2: #TERCER NIVEL
                                tiponivel = 4
                            elif level_education == 3: #CUARTO NIVEL
                                tiponivel = 5
                            ePersonaTituloUniversidad.tiponivel = tiponivel
                            ePersonaTituloUniversidad.save()
                            if ePersonaTituloUniversidad.fechainicio:
                                if ePersonaTituloUniversidad.fechainicio.year > 2008 and isAcceptQuotaActive:
                                    tiene_titulo_publico = True

                        if tiene_titulo_publico or isAcceptQuotaActive:
                            observacion = f"Reportado por la SENESCYT"
                            if tiene_titulo_publico:
                                observacion = f"{observacion}, Registra TITULO TERCER NIVEL REGISTRO SNIESE"
                            if isAcceptQuotaActive:
                                observacion = f" {observacion}, Registra CUPO ACEPTADO Y ACTIVO EN SENESCYT"
                            # if segunda_carrera:
                            #     observacion = f" {observacion}, Registra SOLICITUD DE SEGUNDA CARRERA EN RAES"
                            try:
                                ePerdidaGratuidad = PerdidaGratuidad.objects.get(inscripcion=eInscripcion)
                            except ObjectDoesNotExist:
                                ePerdidaGratuidad = PerdidaGratuidad(inscripcion=eInscripcion)
                            ePerdidaGratuidad.motivo = 1
                            ePerdidaGratuidad.titulo = None
                            ePerdidaGratuidad.titulo_sniese = tiene_titulo_publico
                            ePerdidaGratuidad.cupo_aceptado_senescyt = isAcceptQuotaActive
                            ePerdidaGratuidad.segunda_carrera_raes = False
                            ePerdidaGratuidad.observacion = observacion
                            ePerdidaGratuidad.save(usuario_id=persona.usuario.id)
                            eInscripcion.gratuidad = False
                            eInscripcion.estado_gratuidad = 3
                            eInscripcion.save(usuario_id=persona.usuario.id)
                        print(f"{total}/{contador}  eInscripcion :{eInscripcion.__str__()}")
                    else:
                        raise NameError(f"No se puede procesar la persona ID {persona_id}")
                except Exception as ex:
                    errorfichero = True
                    transaction.set_rollback(True)
                    dataErrorObservaciones.append({'data': arrDataSuccess, 'error': ex.__str__()})

            if dataFila:
                dataSuccessObservaciones.append(dataFila)
        print("PROCESO DE CREAR INSCRIPCIÓN")
        print(dataSuccessObservaciones)
        if errorfichero:
            if historial_observaciones_errores.exists():
                crear_observacion(historial_observaciones_errores[0], dataErrorObservaciones, persona)
            else:
                if proceso:
                    historial = My_HistorialSubirMatrizInscripcion(historial=proceso, estado=2)
                    historial.save(usuario_id=persona.usuario.id)
                    crear_observacion(historial, dataErrorObservaciones, persona)
            return False
        else:
            if historial_observaciones_exitosos.exists():
                crear_observacion(historial_observaciones_exitosos[0], dataSuccessObservaciones, persona)
            else:
                if proceso:
                    historial = My_HistorialSubirMatrizInscripcion(historial=proceso, estado=1)
                    historial.save(usuario_id=persona.usuario.id)
                    crear_observacion(historial, dataSuccessObservaciones, persona)
            return True

    def crear_inscripcion_perfil_senescyt(self, proceso, persona):
        # INVALIDO [FALSE] TODOS LAS OBSERVACIONES YA SEAN [ERROR, SUCCESS]
        if proceso:
            historial_observaciones_errores = proceso.deshabilitar_observaciones_errores(persona.usuario)
            historial_observaciones_exitosos = proceso.deshabilitar_observaciones_exitosos(persona.usuario)

        # CONSULTO LAS OBSERVACIONES DE SUCCESS DEL PROCESO CREA_INSCRIPCION
        # historial_proceso_inscripcion = matriz.historialprocesosubirmatrizinscripcion_set.filter(status=True, proceso__accion='CREA_INSCRIPCION')
        historial_proceso_inscripcion = My_HistorialProcesoSubirMatrizInscripcion.objects.filter(status=True,
                                                                                                 proceso__accion='CREA_INSCRIPCION',
                                                                                                 matriz=self)
        if not historial_proceso_inscripcion.exists():
            mensaje = {'mensaje': 'No existe data a procesar'}
            if historial_observaciones_errores.exists():
                crear_observacion(historial_observaciones_errores[0], mensaje, persona)
            else:
                if proceso:
                    historial = My_HistorialSubirMatrizInscripcion(historial=proceso, estado=2)
                    historial.save(usuario_id=persona.usuario.id)
                    crear_observacion(historial, mensaje, persona)
            return False
        else:
            historial_proceso_inscripcion_observaciones_success = My_HistorialSubirMatrizInscripcion.objects.filter(status=True, estado=1, historial=historial_proceso_inscripcion[0])
            if not historial_proceso_inscripcion_observaciones_success.exists():
                mensaje = {'mensaje': 'No existe data a procesar'}
                if historial_observaciones_errores.exists():
                    crear_observacion(historial_observaciones_errores[0], mensaje, persona)
                else:
                    if proceso:
                        historial = My_HistorialSubirMatrizInscripcion(historial=proceso, estado=2)
                        historial.save(usuario_id=persona.usuario.id)
                        crear_observacion(historial, mensaje, persona)
                return False

        observaciones_success = historial_proceso_inscripcion_observaciones_success[0].observaciones()
        if not observaciones_success.exists():
            return False

        dataErrorObservaciones = []
        dataSuccessObservaciones = []
        errorfichero = False
        eSede = Sede.objects.get(pk=1)
        contador = 0
        total = len(observaciones_success[0].observacion)
        for arrDataSuccess in observaciones_success[0].observacion:
            # print(arrDataSuccess)
            contador += 1
            dataFila = {}
            inscripcion_id = arrDataSuccess.get('INSCRIPCION_ID', 0)
            id_qc = arrDataSuccess.get('ID_QC', 0)
            with transaction.atomic():
                try:
                    try:
                        eInscripcion = Inscripcion.objects.get(pk=inscripcion_id)
                    except ObjectDoesNotExist:
                        raise NameError(f"No se encontro Inscripcion ID: {inscripcion_id}")
                    ePerfilInscripcion = eInscripcion.persona.mi_perfil()
                    print(f"{total}/{contador} Creo/Actualizo --> Perfil-Inscripción:{ePerfilInscripcion.__str__()}")
                    cursor = connections['admision'].cursor()
                    sql = f"""
                            SELECT  
                               app_qc.id,
                               app_e."name" AS etnia,
                               app_e.raza_pk AS raza_pk,
                               app_ni."name" AS nacionalidad_indigena,
                               app_ni.nacionalidad_pk AS nacionalidad_pk,
                               app_d."name" AS discapacidad,
                               app_d.discapacidad_pk,
                               app_pd.percentage AS porcentaje,
                               app_pd.number_card AS carne,
                               app_ci."name" AS institucion,
                               app_ci.institucion_pk
                            FROM app_quotaassignmentapplicantcareer AS app_qc
                            INNER JOIN app_applicant AS app_a ON app_a.id = app_qc.applicant_id
                            INNER JOIN app_inscription AS app_i ON app_i.id= app_a.inscription_id
                            INNER JOIN app_person AS app_p ON app_p.id=app_i.person_id
                            LEFT JOIN app_personethnicity AS app_pe ON app_pe.person_id=app_p.id
                            LEFT JOIN app_ethnicity AS app_e ON app_e.id=app_pe.ethnicity_id
                            LEFT JOIN app_nationalityindigenous AS app_ni ON app_ni.id=app_pe.nationality_id
                            LEFT JOIN app_persondisability AS app_pd ON app_pd.person_id=app_p.id
                            LEFT JOIN app_disability AS app_d ON app_d.id=app_pd.disability_id
                            LEFT JOIN app_certifyinginstitution AS app_ci ON app_ci.id=app_pd.institution_id
                            WHERE app_a.period_id={self.periodo_id_sag} AND app_pe."isVerified"
                            AND app_qc.id={id_qc}
                    """
                    cursor.execute(sql)
                    result = cursor.fetchone()
                    etnia = result[1] if result else ''
                    nacionalidad = result[3] if result else ''
                    if etnia and result:
                        try:
                            if result[2]:
                                eRaza = Raza.objects.get(pk=result[2])
                            else:
                                eRaza = Raza.objects.get(nombre=str(result[1]).upper())
                        except ObjectDoesNotExist:
                            eRaza = Raza(nombre=result[1])
                            eRaza.save()
                        ePerfilInscripcion.raza = eRaza
                    if nacionalidad and result:
                        try:
                            if result[4]:
                                eNacionalidadIndigena = NacionalidadIndigena.objects.get(pk=result[4])
                            else:
                                eNacionalidadIndigena = NacionalidadIndigena.objects.get(nombre=str(result[3]).upper())
                        except ObjectDoesNotExist:
                            eNacionalidadIndigena = NacionalidadIndigena(nombre=result[3])
                            eNacionalidadIndigena.save()
                        ePerfilInscripcion.nacionalidadindigena = eNacionalidadIndigena
                    discapacidad = result[5] if result else None
                    if discapacidad:
                        try:
                            if result[6]:
                                eDiscapacidad = Discapacidad.objects.get(pk=result[6])
                            else:
                                eDiscapacidad = Discapacidad.objects.get(nombre=str(result[5]).upper())
                        except ObjectDoesNotExist:
                            eDiscapacidad = Discapacidad(nombre=result[5])
                            eDiscapacidad.save()
                        ePerfilInscripcion.tienediscapacidad = True
                        ePerfilInscripcion.tipodiscapacidad = eDiscapacidad
                        ePerfilInscripcion.porcientodiscapacidad = result[7]
                        ePerfilInscripcion.carnetdiscapacidad = result[8]
                        if result and result[9]:
                            try:
                                if result[10]:
                                    eInstitucionBeca = InstitucionBeca.objects.get(pk=result[10], tiporegistro=2)
                                else:
                                    eInstitucionBeca = InstitucionBeca.objects.get(nombre=str(result[9]).upper(), tiporegistro=2)
                            except ObjectDoesNotExist:
                                eInstitucionBeca = InstitucionBeca(nombre=result[9], tiporegistro=2)
                                eInstitucionBeca.save()
                            ePerfilInscripcion.institucionvalida = eInstitucionBeca
                    ePerfilInscripcion.save(usuario_id=persona.usuario.id)
                    dataFila['PERFILINSCRIPCION_ID'] = ePerfilInscripcion.pk
                    dataFila['INSCRIPCION_ID'] = eInscripcion.pk
                    dataFila['CARRERA_ID'] = eInscripcion.carrera.pk
                    dataFila['MODALIDAD_ID'] = eInscripcion.modalidad.pk
                except Exception as ex:
                    errorfichero = True
                    transaction.set_rollback(True)
                    dataErrorObservaciones.append({'data': arrDataSuccess, 'error': ex.__str__()})
            if dataFila:
                dataSuccessObservaciones.append(dataFila)
        if errorfichero:
            if historial_observaciones_errores.exists():
                crear_observacion(historial_observaciones_errores[0], dataErrorObservaciones, persona)
            else:
                if proceso:
                    historial = My_HistorialSubirMatrizInscripcion(historial=proceso, estado=2)
                    historial.save(usuario_id=persona.usuario.id)
                    crear_observacion(historial, dataErrorObservaciones, persona)
            return False
        else:
            if historial_observaciones_exitosos.exists():
                crear_observacion(historial_observaciones_exitosos[0], dataSuccessObservaciones, persona)
            else:
                if proceso:
                    historial = My_HistorialSubirMatrizInscripcion(historial=proceso, estado=1)
                    historial.save(usuario_id=persona.usuario.id)
                    crear_observacion(historial, dataSuccessObservaciones, persona)
            return True

    def eliminar_matricula(self, periodo, persona, carrera):
        matriculas = Matricula.objects.filter(nivel__periodo=periodo, inscripcion__carrera=carrera, automatriculaadmision=True)
        for matricula in matriculas:
            rubro = Rubro.objects.filter(matricula=matricula, status=True)
            tiene_pagos = False
            if rubro.exists():
                tiene_pagos = Rubro.objects.filter(matricula=matricula, status=True)[0].tiene_pagos()
            if not tiene_pagos:
                matricula.delete()

        return True


    def matriculacion_senescyt(self, periodo, persona, oCarrera=None):
        try:
            '''
            :parameter matriz, periodo, persona, **kwargs
            :param obligatorily [matriz, periodo, persona]
            :param optionals kwargs [carrera_id]
            Permite matricular masivamente o por carrera.
            :return {
                    'isValid': Boolean,
                    'iData': [],
                    'iMensaje': {
                                'error': [],
                                'succes': [],
                                'warning': []
                                }
                    }
            '''
            print("entra a la función matriculacion_senescyt")
            #oCarrera = None
            isMasivo = False if oCarrera else True

            # CONSULTO LAS OBSERVACIONES DE SUCCESS DEL PROCESO CREA_PERFIL
            historial_proceso_perfil = My_HistorialProcesoSubirMatrizInscripcion.objects.filter(status=True, proceso__accion='CREA_PERFIL', matriz=self)
            if not historial_proceso_perfil.exists():
                return {'isValid': False,
                        'iData': [],
                        'iMensaje': {'error': ["Error, No se encontro el proceso de perfil a ejecutar"],
                                     'succes': [],
                                     'warning': []}
                        }
            else:
                historial_proceso_perfil_observaciones_success = My_HistorialSubirMatrizInscripcion.objects.filter(status=True, estado=1, historial=historial_proceso_perfil[0])
                if not historial_proceso_perfil_observaciones_success.exists():
                    return {'isValid': False,
                            'iData': [],
                            'iMensaje': {'error': ["Error, No existe data a procesar"],
                                         'succes': [],
                                         'warning': []}
                            }

            observaciones_success = historial_proceso_perfil_observaciones_success[0].observaciones()
            sede = Sede.objects.get(pk=1)
            niveles = Nivel.objects.filter(periodo=periodo, nivellibrecoordinacion__coordinacion=ADMISION_ID)
            sesiones = Sesion.objects.filter(pk__in=Nivel.objects.filter(periodo=periodo, nivellibrecoordinacion__coordinacion=ADMISION_ID).distinct().values_list('sesion_id'))
            '''
            dataNiveles = []
            #CARGO NIVELES CON CARRERA, ASIGNATURAS, PARALELOS CON CUPOS
            for nivel_aux in niveles:
                sesiones_aux = Sesion.objects.filter(pk__in=niveles.distinct().values_list('sesion_id'))
                dataSesiones = []
                for sesion_aux in sesiones_aux:
                    carreras_aux = Carrera.objects.filter(pk__in=AsignaturaMalla.objects.filter(materia__nivel=nivel_aux, materia__nivel__sesion=sesion_aux).values_list('malla__carrera').distinct())
                    dataCarreras = []
                    for carrera_aux in carreras_aux:
                        asignaturas_aux = Asignatura.objects.filter(pk__in=Materia.objects.filter(nivel=nivel_aux, nivel__sesion=sesion_aux, asignaturamalla__malla__carrera=carrera_aux).values_list('asignatura').distinct())
                        dataAsignaturas = []
                        for asignatura_aux in asignaturas_aux:
                            paralelos_aux = Paralelo.objects.filter(pk__in=Materia.objects.filter(nivel=nivel_aux, nivel__sesion=sesion_aux, asignaturamalla__malla__carrera=carrera_aux, asignatura=asignatura_aux).values_list('paralelomateria').distinct())
                            dataParalelos = []
                            for paralelo_aux in paralelos_aux:
                                materia_aux = Materia.objects.get(nivel=nivel_aux, nivel__sesion=sesion_aux, asignatura=asignatura_aux, paralelomateria=paralelo_aux, asignaturamalla__malla__carrera=carrera_aux)
                                dataParalelos.append({'id': materia_aux.id, 'cupo': materia_aux.cupo, 'cupo_adicional': materia_aux.cupoadicional, 'total_matriculados': MateriaAsignada.objects.filter(materia=materia_aux).count()})
                            dataAsignaturas.append({'id': asignatura_aux.id, 'paralelos': dataParalelos})
                        dataCarreras.append({'id': carrera_aux.id, 'asignaturas': dataAsignaturas})
                    dataSesiones.append({'id': sesion_aux.id, 'carreras': dataCarreras})
                dataNiveles.append({'id': nivel_aux.id, 'sesiones': dataSesiones})
            dataDistributivoAux = {'niveles': dataNiveles}
    
            print(dataDistributivoAux)
            '''
            linea = 1
            for arrDataSuccess in observaciones_success[0].observacion:
                print(arrDataSuccess)
                inscripcion_id = arrDataSuccess['INSCRIPCION_ID']
                modalidad_id = arrDataSuccess['MODALIDAD_ID']
                carrera_id = arrDataSuccess['CARRERA_ID']
                # gratuidad = arrDataSuccess['GRATUIDAD']

                try:
                    eInscripcion = Inscripcion.objects.get(pk=inscripcion_id)
                except ObjectDoesNotExist:
                    eInscripcion = None

                try:
                    eCarrera = Carrera.objects.get(pk=carrera_id)
                except ObjectDoesNotExist:
                    eCarrera = None

                # if carrera_id == 70:
                #     print(eCarrera)

                if not isMasivo:
                    if oCarrera.id == eCarrera.id:
                        eInscripcion = Inscripcion.objects.get(pk=inscripcion_id, carrera=eCarrera)
                    else:
                        eInscripcion = None

                if eInscripcion:
                    perfiles_usuarios = PerfilUsuario.objects.filter(persona=eInscripcion.persona, inscripcion=eInscripcion)
                    if not perfiles_usuarios.values("id").exists():
                        eInscripcion.persona.crear_perfil(inscripcion=eInscripcion, visible=False)

                    nivel_id = 0
                    for sesion in sesiones:
                        # MODALIDAD EN LINEA (LE AGREGO LA SESION DE EN LINEA)
                        if sesion.id in [13] and eInscripcion.modalidad.id in [3]:
                            eInscripcion.sesion = sesion
                            nivel_id = 1742
                        # MODALIDAD EN SEMIPRESENCIAL O PRESENCIAL (LE AGREGO EL ID DE LA SESION DE FNSEMANA)
                        elif sesion.id in [7, 11, 12] and eInscripcion.modalidad.id in [1, 2]:
                            eInscripcion.sesion = sesion
                            nivel_id = 1741

                    eInscripcion.save(usuario_id=persona.usuario.id)
                    # hago la matriculación
                    mimalla = eInscripcion.malla_inscripcion()
                    mallaacutualcarrera = Malla.objects.filter(status=True, carrera=eCarrera, validamatricula=True, vigente=True).first()
                    if mallaacutualcarrera and mimalla and (not mallaacutualcarrera.id == mimalla.malla_id):
                        malla = eInscripcion.inscripcionmalla_set.filter(status=True)
                        malla.delete()
                        im = InscripcionMalla(inscripcion=eInscripcion, malla=mallaacutualcarrera)
                        im.save()
                        eInscripcion.actualizar_creditos()
                        mimalla = im
                    print(nivel_id)
                    # nivel = Nivel.objects.get(periodo=periodo, sesion=eInscripcion.sesion, sede=sede)
                    nivel = Nivel.objects.get(pk=nivel_id)

                    if Materia.objects.filter(nivel__periodo=periodo, asignaturamalla__malla=mimalla.malla, asignaturamalla__malla__carrera=eInscripcion.carrera, nivel__sesion=eInscripcion.sesion).exists():
                        # if not eInscripcion.matricula_periodo(periodo):
                        matricula = Matricula.objects.filter(inscripcion=eInscripcion, nivel=nivel).first()
                        if not matricula:
                            matricula = Matricula(inscripcion=eInscripcion,
                                                  nivel=nivel,
                                                  pago=False,
                                                  iece=False,
                                                  becado=False,
                                                  porcientobeca=0,
                                                  fecha=datetime.now().date(),
                                                  hora=datetime.now().time(),
                                                  fechatope=fechatope(datetime.now().date()),
                                                  automatriculaadmision=True,
                                                  fechaautomatriculaadmision=datetime.now(),
                                                  cuposenescyt=True)
                            matricula.save(usuario_id=persona.usuario.id)
                        # else:
                        #     matricula = Matricula.objects.get(inscripcion=eInscripcion, nivel=nivel)
                        print(matricula)
                        eMateriaAsignadas = MateriaAsignada.objects.filter(matricula=matricula)
                        if not eMateriaAsignadas.values("id").exists():
                            # paralelos = Materia.objects.filter(nivel__periodo=periodo, asignaturamalla__malla=mimalla.malla, asignaturamalla__malla__carrera=inscripcion.carrera, nivel__sesion=inscripcion.sesion).values_list('paralelo').distinct().order_by('paralelo')
                            paralelos = Materia.objects.filter(nivel__periodo=periodo, asignaturamalla__malla=mimalla.malla, asignaturamalla__malla__carrera=eInscripcion.carrera, nivel__sesion=eInscripcion.sesion).values_list('paralelomateria').distinct()

                            if paralelos.values("id").exists():
                                paralelo_atomar = None
                                tiene_cupo_paralelo = False
                                for paralelo in paralelos:
                                    tiene_cupo_paralelo_aux = True
                                    for mat in Materia.objects.filter(nivel__periodo=periodo, paralelomateria=paralelo, asignaturamalla__malla=mimalla.malla, asignaturamalla__malla__carrera=eCarrera, nivel__sesion=eInscripcion.sesion):
                                        if MateriaAsignada.objects.filter(materia=mat).count()+1 > mat.cupo:
                                            tiene_cupo_paralelo_aux = False
                                            break
                                    if tiene_cupo_paralelo_aux:
                                        paralelo_atomar = paralelo
                                        tiene_cupo_paralelo = True
                                        break
                                if tiene_cupo_paralelo:
                                    materias_c = Materia.objects.filter(nivel__periodo=periodo, paralelomateria=paralelo_atomar, asignaturamalla__malla=mimalla.malla, asignaturamalla__malla__carrera=eCarrera, nivel__sesion=eInscripcion.sesion)
                                    for materia in materias_c:
                                        if not MateriaAsignada.objects.values('id').filter(matricula=matricula, materia=materia).exists():
                                            matriculas = matricula.inscripcion.historicorecordacademico_set.values('id').filter(asignatura=materia.asignatura, fecha__lt=materia.nivel.fin).count() + 1
                                            materiaasignada = MateriaAsignada(matricula=matricula,
                                                                              materia=materia,
                                                                              notafinal=0,
                                                                              asistenciafinal=0,
                                                                              cerrado=False,
                                                                              matriculas=matriculas,
                                                                              observaciones='',
                                                                              estado_id=NOTA_ESTADO_EN_CURSO,
                                                                              cobroperdidagratuidad=eInscripcion.gratuidad)
                                            materiaasignada.save(usuario_id=persona.usuario.id)
                                            materiaasignada.asistencias()
                                            materiaasignada.evaluacion()
                                            materiaasignada.mis_planificaciones()
                                            materiaasignada.save(usuario_id=persona.usuario.id)
                                            print(materiaasignada)

                        matricula.actualizar_horas_creditos()
                        matricula.estado_matricula = 2
                        matricula.save(usuario_id=persona.usuario.id)
                        matricula.calcula_nivel()
                        eInscripcion.actualizar_nivel()
                        if eInscripcion.estado_gratuidad == 3:
                            if eInscripcion.sesion_id == 13:
                                tiporubromatricula = TipoOtroRubro.objects.get(pk=3019)
                            else:
                                tiporubromatricula = TipoOtroRubro.objects.get(pk=3011)
                            eMateriaAsignadas.update(cobroperdidagratuidad=True)
                            if matricula.tipomatricula_id == 1:
                                matricula.estado_matricula = 2
                                matricula.save(usuario_id=persona.usuario.id)

                            num_materias = MateriaAsignada.objects.filter(matricula=matricula, cobroperdidagratuidad=True).count()
                            valor_x_materia = 20
                            valor_total = num_materias * valor_x_materia

                            if not Rubro.objects.filter(persona=eInscripcion.persona, matricula=matricula).exists():
                                print(eInscripcion.gratuidad)
                                rubro1 = Rubro(tipo=tiporubromatricula,
                                               persona=eInscripcion.persona,
                                               matricula=matricula,
                                               nombre=tiporubromatricula.nombre + ' - ' + periodo.nombre,
                                               cuota=1,
                                               fecha=datetime.now().date(),
                                               # fechavence=datetime.now().date() + timedelta(days=22),
                                               fechavence=datetime.now().date(),
                                               valor=valor_total,
                                               iva_id=1,
                                               valoriva=0,
                                               valortotal=valor_total,
                                               saldo=valor_total,
                                               cancelado=False)
                                rubro1.save(usuario_id=persona.usuario.id)
                                print(rubro1)
                            else:
                                rubro1 = Rubro.objects.filter(persona=eInscripcion.persona, matricula=matricula)[0]
                                rubro1.tipo=tiporubromatricula
                                rubro1.nombre = tiporubromatricula.nombre + ' - ' + periodo.nombre
                                rubro1.cuota = 1
                                rubro1.fecha = datetime.now().date()
                                # rubro1.fechavence = datetime.now().date() + timedelta(days=22)
                                rubro1.fechavence=datetime.now().date(),
                                rubro1.valor = valor_total
                                rubro1.iva_id = 1
                                rubro1.valoriva = 0
                                rubro1.valortotal = valor_total
                                rubro1.saldo = valor_total
                                rubro1.cancelado = False
                                rubro1.save(usuario_id=persona.usuario.id)
                                print(rubro1)
                        """if not matricula.notificadoadmision:
                            mimalla = matricula.inscripcion.malla_inscripcion()
                            cuenta = cuenta_email_disponible()
                            titulo = "Confirmación de Matrícula Admisión 1S-2021"
                            if mimalla.malla.inicio.year == 2020:
                                print("Enviando ", linea, " de ")
                                print("Procesando: ", cuenta, " - ", matricula.inscripcion.persona.identificacion(), " - ",
                                      matricula.inscripcion)
                                if matricula.inscripcion.persona.emailpersonal():
                                    send_html_mail(titulo,
                                                   "emails/notificacionmatricula.html",
                                                   {'sistema': u'SGA - UNEMI',
                                                    'fecha': datetime.now().date(),
                                                    'hora': datetime.now().time(),
                                                    'persona': matricula.inscripcion.persona,
                                                    },
                                                   matricula.inscripcion.persona.emailpersonal(),
                                                   [],
                                                   cuenta=CUENTAS_CORREOS[cuenta][1]
                                                   )
                                    # # Temporizador para evitar que se bloquee el servicion de gmail
                                    time.sleep(3)
                                    matricula.notificadoadmision = True
                                    matricula.save(usuario_id=persona.usuario.id)"""
                linea += 1

            return {'isValid': True,
                    'iData': [],
                    'iMensaje': {'error': [],
                                 'succes': [],
                                 'warning': []}
                    }
        except Exception as ex:
            print(ex)

    def activar_perfiles_usuarios_admision(self, periodo, persona, oCarrera=None):
        print("INICIA PROCESO")
        sede = Sede.objects.get(pk=1)
        niveles = Nivel.objects.filter(periodo=periodo, nivellibrecoordinacion__coordinacion=ADMISION_ID)
        sesiones = Sesion.objects.filter(pk__in=Nivel.objects.filter(periodo=periodo, nivellibrecoordinacion__coordinacion=ADMISION_ID).distinct().values_list('sesion_id'))
        materias = Materia.objects.filter(nivel__in=niveles, status=True)
        if oCarrera:
            materias = materias.filter(asignaturamalla__malla__carrera_id=oCarrera.id)
        print(materias)
        matriculas = Matricula.objects.filter(materiaasignada__materia__in=materias)
        for matricula in matriculas:
            inscripcion = matricula.inscripcion
            perfs = PerfilUsuario.objects.filter(inscripcion=inscripcion, persona=inscripcion.persona, visible=False)
            if perfs.exists():
                print(inscripcion.persona)
                per = perfs.first()
                per.visible = True
                per.status = True
                per.save(usuario_id=persona.usuario.id)
        return

    def matricula_2_repetidores_admision(self, periodoactual, periodoanterior, persona, carrera, nivel, data=None, isCelery=False):
        from django.db.models import Count
        print("INICIA PROCESO")
        if not data:
            if isCelery:
                return False
            NameError("No se encontro información")
        sede = Sede.objects.get(pk=1)
        niveles = Nivel.objects.filter(periodo=periodoactual, nivellibrecoordinacion__coordinacion=ADMISION_ID)
        sesiones = Sesion.objects.filter(pk__in=Nivel.objects.filter(periodo=periodoactual, nivellibrecoordinacion__coordinacion=ADMISION_ID).distinct().values_list('sesion_id'))
        materias = Materia.objects.filter(nivel__in=niveles, status=True)
        if carrera:
            materias = materias.filter(asignaturamalla__malla__carrera=carrera)
        # print(materias)
        # MATRICULAS DEL PERIODO MAYO A SEPTIEMBRE 2021 EN PREGRADO
        persona_ids = Matricula.objects.filter(status=True, nivel__periodo=periodoanterior, nivelmalla_id=1).exclude(inscripcion__coordinacion_id=9).values('inscripcion__persona_id').distinct()
        # persona_ids_aux = Matricula.objects.filter(status=True, nivel__periodo=periodoactual, materiaasignada__isnull=False).values('inscripcion__persona_id').distinct()
        # personas_ids = persona_ids | persona_ids_aux
        personas_ids = persona_ids
        # MATRICULAS DEL PERIODO JUNIO A SEPTIEMBRE 2021 EN ADMISION
        repetidores = Matricula.objects.filter(status=True, inscripcion__carrera=carrera, aprobado=False, nivel__periodo=periodoanterior, termino=True).exclude(inscripcion__persona_id__in=personas_ids)
        total = len(repetidores.values("id"))
        print(f"Total: {total}")
        contador = 0
        for repe in repetidores:
            contador += 1
            if repe.mismaterias():
                # if repe.materiaasignada_set.filter(status=True).exclude(materiaasignadaretiro__valida=False).count() == 3:
                inscripcion = repe.inscripcion
                if inscripcion.bloqueomatricula:
                    inscripcion.bloqueomatricula = False
                    inscripcion.save(usuario_id=persona.usuario.id)
                # perfiles_usuarios = PerfilUsuario.objects.filter(persona=inscripcion.persona, inscripcion=inscripcion)
                # if perfiles_usuarios.exists():
                #     perfil = perfiles_usuarios.first()
                #     perfil.visible = False
                #     perfil.save(usuario_id=persona.usuario.id)
                mimalla = inscripcion.mi_malla()
                mallaacutualcarrera = Malla.objects.filter(status=True, carrera=inscripcion.carrera, validamatricula=True, vigente=True).first()
                if mallaacutualcarrera and mimalla and (not mallaacutualcarrera.id == mimalla.id):
                    malla = inscripcion.inscripcionmalla_set.filter(status=True)
                    malla.delete()
                    im = InscripcionMalla(inscripcion=inscripcion, malla=mallaacutualcarrera)
                    im.save()
                    inscripcion.actualizar_creditos()
                    mimalla = im.malla
                if not Materia.objects.filter(nivel__periodo=periodoactual, asignaturamalla__malla=mimalla, asignaturamalla__malla__carrera=inscripcion.carrera).exists():
                    return False
                matricula = Matricula.objects.filter(inscripcion=inscripcion, nivel=nivel).first()

                # if not repe.inscripcion.matricula_periodo(periodoactual):
                if not matricula:
                    matricula = Matricula(inscripcion=inscripcion,
                                          nivel=nivel,
                                          pago=False,
                                          iece=False,
                                          becado=False,
                                          porcientobeca=0,
                                          fecha=datetime.now().date(),
                                          hora=datetime.now().time(),
                                          fechatope=fechatope(datetime.now().date()),
                                          automatriculaadmision=True,
                                          fechaautomatriculaadmision=datetime.now(),
                                          termino=False)
                    matricula.save(usuario_id=persona.usuario.id)
                # else:
                #     matricula = Matricula.objects.get(inscripcion=inscripcion, nivel=nivel)
                print(f"{total}/{contador} --> {matricula.__str__()}")
                if not MateriaAsignada.objects.values("id").filter(matricula=matricula).exists():
                    materias = MateriaAsignada.objects.filter(matricula=repe, estado_id=2)
                    eRecordAcademicos = RecordAcademico.objects.filter(inscripcion=repe.inscripcion, materiaregular__id__in=materias.values_list('materia__id', flat=True), status=True)
                    materias_actuales = []
                    paralelos = []
                    for eRecordAcademico in eRecordAcademicos:
                        # print(eRecordAcademico.asignatura.id)
                        for d in data:
                            # print(d)
                            if eRecordAcademico.asignatura_id == int(d['asignatura_anterior']):
                                asignatura_actual_id = int(d['asignatura_actual'])
                                mats = Materia.objects.filter(nivel=nivel, asignaturamalla__malla=mimalla, asignatura_id=asignatura_actual_id)
                                if not MateriaAsignada.objects.filter(materia_id__in=mats.values_list('id', flat=True), matricula=matricula).exists():
                                    for mat in mats:
                                        cupo = mat.cupo
                                        matriculados = MateriaAsignada.objects.filter(materia=mat).count()
                                        if matriculados <= cupo:
                                            paralelos.append(mat.paralelomateria.id)
                                            materias_actuales.append(mat.id)
                                            break
                    # print(materias_actuales)
                    for iMat in materias_actuales:
                        materia = Materia.objects.get(pk=iMat)
                        if not MateriaAsignada.objects.filter(matricula=matricula, materia=materia).exists():
                            num_matriculas = repe.inscripcion.historicorecordacademico_set.values('id').filter(asignatura=materia.asignatura, fecha__lt=materia.nivel.fin).count() + 1
                            if num_matriculas > 2:
                                matricula.delete()
                                break
                            materiaasignada = MateriaAsignada(matricula=matricula,
                                                              materia=materia,
                                                              notafinal=0,
                                                              asistenciafinal=0,
                                                              cerrado=False,
                                                              matriculas=num_matriculas,
                                                              observaciones='',
                                                              estado_id=NOTA_ESTADO_EN_CURSO,
                                                              cobroperdidagratuidad=True)
                            materiaasignada.save(usuario_id=persona.usuario.id)
                            materiaasignada.asistencias()
                            materiaasignada.evaluacion()
                            materiaasignada.mis_planificaciones()
                            materiaasignada.save(usuario_id=persona.usuario.id)
                            # print(materiaasignada)
                matricula.actualizar_horas_creditos()
                matricula.estado_matricula = 2
                matricula.save(usuario_id=persona.usuario.id)
                matricula.calcula_nivel()
                inscripcion.actualizar_nivel()
                #if not materia.asignatura.id in [4837]:

                if inscripcion.sesion_id == 13:
                    tiporubromatricula = TipoOtroRubro.objects.get(pk=3019)
                else:
                    tiporubromatricula = TipoOtroRubro.objects.get(pk=3011)

                # num_materias = MateriaAsignada.objects.filter(matricula=matricula, cobroperdidagratuidad=True).exclude(materia__asignatura_id=4837).count()
                num_materias = MateriaAsignada.objects.filter(matricula=matricula, cobroperdidagratuidad=True).count()
                if num_materias > 0:
                    valor_x_materia = 20
                    valor_total = num_materias * valor_x_materia
                    matricula.estado_matricula = 1
                    matricula.save(usuario_id=persona.usuario.id)
                    if not Rubro.objects.filter(persona=inscripcion.persona, matricula=matricula).exists():
                        rubro1 = Rubro(tipo=tiporubromatricula,
                                       persona=inscripcion.persona,
                                       matricula=matricula,
                                       nombre=tiporubromatricula.nombre + ' - ' + periodoactual.nombre,
                                       cuota=1,
                                       fecha=datetime.now().date(),
                                       # fechavence=datetime.now().date() + timedelta(days=22),
                                       fechavence=(datetime(2024, 10, 31, 0, 0, 0)).date(),
                                       valor=valor_total,
                                       iva_id=1,
                                       valoriva=0,
                                       valortotal=valor_total,
                                       saldo=valor_total,
                                       cancelado=False)
                        rubro1.save(usuario_id=persona.usuario.id)
                        # print(rubro1)
        return


    def cargar_distributivo_matriz_admision(self, periodo, periodoanterior):
        # CONSULTO LAS OBSERVACIONES DE SUCCESS DEL PROCESO CREA_PERFIL
        historial_proceso_perfil = My_HistorialProcesoSubirMatrizInscripcion.objects.filter(status=True, proceso__accion='CREA_PERFIL', matriz=self)
        if not historial_proceso_perfil.exists():
            return {'isValid': False,
                    'iData': [],
                    'iMensaje': {'error': ["Error, No se encontro el proceso de perfil a ejecutar"],
                                 'succes': [],
                                 'warning': []},
                    'cupoDemanda': 0,
                    'cupoOfertado': 0,
                    'isCanEnroll': False
                    }
        else:
            historial_proceso_perfil_observaciones_success = My_HistorialSubirMatrizInscripcion.objects.filter(status=True, estado=1, historial=historial_proceso_perfil[0])
            if not historial_proceso_perfil_observaciones_success.exists():
                return {'isValid': False,
                        'iData': [],
                        'iMensaje': {'error': "Error, No se encontro información del proceso de perfil",
                                     'succes': None,
                                     'warning': None},
                        'cupoDemanda': 0,
                        'cupoOfertado': 0,
                        'isCanEnroll': False
                        }

        observaciones_success = historial_proceso_perfil_observaciones_success[0].observaciones()
        carrera_ids = []
        modalidad_ids = []
        iMatriz = []
        for arrDataSuccess in observaciones_success[0].observacion:
            for key, value in arrDataSuccess.items():
                if key == 'CARRERA_ID' and not value in carrera_ids:
                    carrera_ids.append(value)
                if key == 'MODALIDAD_ID' and not value in modalidad_ids:
                    modalidad_ids.append(value)
        for modalidad in modalidad_ids:
            countModalidad = 0
            arrCarreras = []
            for arrDataSuccess in observaciones_success[0].observacion:
                if arrDataSuccess['MODALIDAD_ID'] == modalidad:
                    countModalidad += 1
                    if not arrDataSuccess['CARRERA_ID'] in arrCarreras:
                        arrCarreras.append(arrDataSuccess['CARRERA_ID'])
            aCarreras = []
            for carrera in arrCarreras:
                countCarrera = 0
                for arrDataSuccess in observaciones_success[0].observacion:
                    if arrDataSuccess['MODALIDAD_ID'] == modalidad and arrDataSuccess['CARRERA_ID'] == carrera:
                        countCarrera += 1
                aCarreras.append({'id': carrera, 'count': countCarrera})
            iMatriz.append({'id': modalidad, 'count': countModalidad, 'carreras': aCarreras})
        carreras = Carrera.objects.filter(pk__in=carrera_ids)
        carrerasError = []
        # sesion = json.loads(request.POST['sesion'])
        # sesiones = Sesion.objects.filter(pk__in=sesion)
        niveles = Nivel.objects.filter(periodo=periodo, nivellibrecoordinacion__coordinacion=ADMISION_ID)

        isValid = True
        for carrera in carreras:
            if not Materia.objects.filter(nivel__in=niveles, asignaturamalla__malla__carrera=carrera).exists():
                carrerasError.append(carrera.nombre)
        iMensaje = {'error': [], 'succes': [], 'warning': []}
        if carrerasError:
            iMensaje['warning'].append("Información, no se encontro planificación en el distributivo para las siguientes carreras (%s)" % (', '.join(carrerasError)))
            isValid = True
        dataNivel = []
        TYPE_SUCCESS = 'success'
        TYPE_ERROR = 'error'
        TYPE_WARNING = 'warning'
        cupoOfertado = 0
        # MATRICULAS DEL PERIODO MAYO A SEPTIEMBRE 2021 EN PREGRADO
        persona_ids = Matricula.objects.filter(status=True, nivel__periodo=periodoanterior, nivelmalla_id=1).exclude(inscripcion__coordinacion_id=9).values('inscripcion__persona_id').distinct()
        persona_ids_aux = Matricula.objects.filter(status=True, nivel__periodo=periodo, materiaasignada__isnull=False).values('inscripcion__persona_id').distinct()
        personas_ids = persona_ids | persona_ids_aux
        # MATRICULAS DEL PERIODO JUNIO A SEPTIEMBRE 2021 EN ADMISION
        matriculas_old = Matricula.objects.filter(status=True, aprobado=False, nivel__periodo=periodoanterior).exclude(inscripcion__persona_id__in=personas_ids)
        total_demanda_carrera = 0
        for nivel in niveles:
            dataModalidad = []
            cupoNivel = 0
            cupoModalidad = 0
            cupoCarrera = 0
            cupoAsignatura = 0
            cupoParalelo = 0
            msgNivel = None
            auModalidades = Modalidad.objects.filter(pk__in=Materia.objects.filter(nivel=nivel).values_list('asignaturamalla__malla__modalidad_id').distinct())
            for modalidad in auModalidades:
                dataCarrera = []
                cupoModalidad = 0
                msgModalidad = None
                auCarreras = Carrera.objects.filter(pk__in=Materia.objects.filter(nivel=nivel, asignaturamalla__malla__modalidad=modalidad).values_list('asignaturamalla__malla__carrera_id').distinct())
                for carrera in auCarreras:
                    dataAsignatura = []
                    cupoCarrera = 0
                    msgCarrera = None
                    countMateria = 0
                    total_demanda_carrera = 0
                    auAsignaturas = Asignatura.objects.filter(pk__in=Materia.objects.filter(nivel=nivel, asignaturamalla__malla__modalidad=modalidad, asignaturamalla__malla__carrera=carrera).values_list('asignaturamalla__asignatura_id').distinct())
                    for asignatura in auAsignaturas:
                        dataParalelo = []
                        countMateria += 1
                        msgAsignatura = None
                        cupoParalelo = 0
                        cupoAsignatura = 0
                        auMaterias = Materia.objects.filter(nivel=nivel, asignaturamalla__malla__modalidad=modalidad, asignaturamalla__malla__carrera=carrera, asignaturamalla__asignatura=asignatura)
                        for paralelo in auMaterias:
                            msgParalelo = None
                            dataParalelo.append({'id': paralelo.id,
                                                 'nombre': paralelo.paralelomateria.nombre,
                                                 'cupo': paralelo.cupo,
                                                 'msg': msgParalelo,
                                                 'tipo': TYPE_SUCCESS
                                                 })
                            cupoParalelo += paralelo.cupo
                        cupoAsignatura += cupoParalelo
                        cupoCarrera += cupoParalelo
                        dataAsignatura.append({'id': asignatura.id,
                                               'nombre': asignatura.nombre,
                                               'cupo': cupoAsignatura,
                                               'paralelos': dataParalelo,
                                               'msg': msgAsignatura,
                                               'tipo': TYPE_SUCCESS
                                               })
                    try:
                        cupoCarrera = int(cupoCarrera / countMateria)
                    except ZeroDivisionError:
                        cupoCarrera = 0
                    cupoModalidad += cupoCarrera
                    searchCarrera = False
                    typeCarrera = TYPE_SUCCESS
                    for iModalidad in iMatriz:
                        for iCarrera in iModalidad['carreras']:
                            if iCarrera['id'] == carrera.id:
                                total_demanda_carrera = iCarrera['count']
                                if iCarrera['count'] > cupoCarrera:
                                    msgCarrera = u"Error, en la carrera %s el cupo ofertado (%s) es inferior al cupo a matricular (%s)" % (carrera.nombre, cupoCarrera, iCarrera['count'])
                                    isValid = False
                                    typeCarrera = TYPE_ERROR
                                searchCarrera = True
                    if not searchCarrera:
                        msgCarrera = u"Información, en la carrera %s del distributivo no tiene demanda de la SENESCYT" % carrera.nombre
                        typeCarrera = TYPE_WARNING
                    if countMateria < 3:
                        msgCarrera = u"Información, en la carrera %s del distributivo tiene planificada %s materias" % (carrera.nombre, countMateria)
                        typeCarrera = TYPE_WARNING
                    if typeCarrera != TYPE_SUCCESS:
                        for iAsignatura in range(0, len(dataAsignatura)):
                            vv = dataAsignatura[iAsignatura]['tipo']
                            if dataAsignatura[iAsignatura]['tipo'] == TYPE_SUCCESS:
                                dataAsignatura[iAsignatura]['tipo'] = typeCarrera
                                dataAsignatura[iAsignatura]['msg'] = msgCarrera
                                for iParalelo in range(0, len(dataAsignatura[iAsignatura]['paralelos'])):
                                    if dataAsignatura[iAsignatura]['paralelos'][iParalelo]['tipo'] == TYPE_SUCCESS:
                                        dataAsignatura[iAsignatura]['paralelos'][iParalelo]['tipo'] = typeCarrera
                                        dataAsignatura[iAsignatura]['paralelos'][iParalelo]['msg'] = msgCarrera

                    dataCarrera.append({'id': carrera.id,
                                        'nombre': carrera.nombre,
                                        'cupo': cupoCarrera,
                                        'cupo2m': matriculas_old.filter(inscripcion__carrera=carrera).count(),
                                        'materias': dataAsignatura,
                                        'msg': msgCarrera,
                                        'tipo': typeCarrera,
                                        'total_demanda': total_demanda_carrera,
                                        'total_matriculados': Matricula.objects.filter(nivel=nivel, inscripcion__carrera=carrera, inscripcion__modalidad=modalidad).count()
                                        })

                searchModalidad = False
                typeModalidad = TYPE_SUCCESS
                for iModalidad in iMatriz:
                    if iModalidad['id'] == modalidad.id:
                        if iModalidad['count'] > cupoModalidad:
                            msgModalidad = u"Error, en la modalidad %s el cupo ofertado (%s) es inferior al cupo a matricular (%s)" % (modalidad.nombre, cupoModalidad, iModalidad['count'])
                            isValid = False
                            typeModalidad = TYPE_ERROR
                        searchModalidad = True
                if not searchModalidad:
                    msgModalidad = u"Información, en la modalidad %s planificada en el distributivo no tiene demanda de la SENESCYT" % modalidad.nombre
                    typeModalidad = TYPE_WARNING
                dataModalidad.append({'id': modalidad.id,
                                      'nombre': modalidad.nombre,
                                      'cupo': cupoModalidad,
                                      'carreras': dataCarrera,
                                      'msg': msgModalidad,
                                      'tipo': typeModalidad
                                      })
            cupoNivel += cupoModalidad
            cupoOfertado += cupoNivel
            dataNivel.append({'id': nivel.id,
                              'nombre': nivel.__str__(),
                              'cupo': cupoNivel,
                              'modalidades': dataModalidad,
                              'msg': msgNivel,
                              'tipo': TYPE_SUCCESS
                              })
        cupoDemanda = len(observaciones_success[0].observacion)
        total_repetidores = matriculas_old.count()
        isCanEnroll = True
        if cupoDemanda > cupoOfertado or total_repetidores > cupoOfertado:
            isValid = False
            isCanEnroll = False
            iMensaje['error'].append("Error, el número de postulantes (%s) supera al número de oferta planificada en el distributivo (%s)" % (cupoDemanda + total_repetidores, cupoOfertado))

        print(self.status_matricular_masiva())
        if self.status_matricular_masiva() == 'STARTED' or self.status_matricular_masiva() == 'PENDING':
            isCanEnroll = False

        return {'isValid': isValid,
                'iData': dataNivel,
                'iMensaje': iMensaje,
                'cupoDemanda': cupoDemanda,
                'cupoOfertado': cupoOfertado,
                'cuporReprobado': total_repetidores,
                'isCanEnroll': isCanEnroll
                }

    def save(self, *args, **kwargs):
        super(My_SubirMatrizInscripcion, self).save(*args, **kwargs)


class My_HistorialProcesoSubirMatrizInscripcion(HistorialProcesoSubirMatrizInscripcion):
    objects = models.Manager()

    class Meta:
        proxy = True

    def __init__(self, *args, **kwargs):
        super(My_HistorialProcesoSubirMatrizInscripcion, self).__init__(*args, **kwargs)

    def historial_observaciones_exitoso(self):
        return My_HistorialSubirMatrizInscripcion.objects.filter(estado=1, historial=self)[0].observaciones()

    def historial_total_observaciones_exitoso(self):
        return My_HistorialSubirMatrizInscripcion.objects.filter(estado=1, historial=self)[0].total_observaciones()

    def historial_observaciones_error(self):
        return My_HistorialSubirMatrizInscripcion.objects.filter(estado=2, historial=self)[0].observaciones()

    def historial_total_observaciones_error(self):
        return My_HistorialSubirMatrizInscripcion.objects.filter(estado=2, historial=self)[0].total_observaciones()

    def deshabilitar_observaciones_errores(self, usuario):
        historial_observaciones = My_HistorialSubirMatrizInscripcion.objects.filter(status=True, estado=2, historial=self)
        for historial in historial_observaciones:
            historial.deshabilitar_observaciones(usuario)
        return historial_observaciones

    def deshabilitar_observaciones_exitosos(self, usuario):
        historial_observaciones = My_HistorialSubirMatrizInscripcion.objects.filter(status=True, estado=2, historial=self)
        for historial in historial_observaciones:
            historial.deshabilitar_observaciones(usuario)
        return historial_observaciones

    def save(self, *args, **kwargs):
        super(My_HistorialProcesoSubirMatrizInscripcion, self).save(*args, **kwargs)


class My_HistorialSubirMatrizInscripcion(HistorialSubirMatrizInscripcion):
    objects = models.Manager()

    class Meta:
        proxy = True

    def __init__(self, *args, **kwargs):
        super(My_HistorialSubirMatrizInscripcion, self).__init__(*args, **kwargs)

    def observaciones(self):
        return My_ObservacionSubirMatrizInscripcion.objects.filter(historial=self, status=True)

    def total_observaciones(self):
        return My_ObservacionSubirMatrizInscripcion.objects.filter(historial=self, status=True).count()

    def deshabilitar_observaciones(self, usuario):
        for historialobs in My_ObservacionSubirMatrizInscripcion.objects.filter(historial=self):
            historialobs.deshabilitar(usuario)

    def save(self, *args, **kwargs):
        super(My_HistorialSubirMatrizInscripcion, self).save(*args, **kwargs)


class My_ObservacionSubirMatrizInscripcion(ObservacionSubirMatrizInscripcion):
    objects = models.Manager()

    class Meta:
        proxy = True

    def __init__(self, *args, **kwargs):
        super(My_ObservacionSubirMatrizInscripcion, self).__init__(*args, **kwargs)

    def deshabilitar(self, usuario):
        self.status = False
        self.save(usuario_id=usuario)

    def save(self, *args, **kwargs):
        super(My_ObservacionSubirMatrizInscripcion, self).save(*args, **kwargs)



def crear_observacion(historial, mensaje, persona):
    obsError = My_ObservacionSubirMatrizInscripcion(historial=historial, observacion=mensaje)
    obsError.save(usuario_id=persona.usuario.id)
