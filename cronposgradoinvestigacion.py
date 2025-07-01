#!/usr/bin/env python
import io

import xlrd
import xlwt

from django.core.files.base import ContentFile

from django.db import transaction, connections
from django.db.models.functions import Extract
from django.db.models.functions.datetime import ExtractDay, ExtractYear
from xlrd import book
from xlsxwriter import workbook

from xlwt import easyxf, XFStyle

import os
import sys
import calendar
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
import time as ET
from decimal import Decimal

from django.db.models import Sum, Q, F, ExpressionWrapper, DurationField

from settings import SITE_STORAGE

SITE_ROOT = os.path.dirname(os.path.realpath(__file__))
your_djangoproject_home = os.path.split(SITE_ROOT)[0]
sys.path.append(your_djangoproject_home)

from django.core.wsgi import get_wsgi_application
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "settings")
application = get_wsgi_application()

from investigacion.models import ProyectoInvestigacion, ProyectoInvestigacionRecorrido, ProyectoInvestigacionHistorialArchivo, RubricaEvaluacionItem, EvaluacionProyecto, EvaluacionProyectoDetalle, GrupoInvestigacionIntegrante, PublicacionOrcid, PublicacionScopus, ObraRelevancia, ResponsableServicio, \
    HorarioResponsableServicio, TurnoCita, ServicioGestion, ServicioResponsableServicio
from sagest.commonviews import obtener_estado_solicitud
from sagest.models import Pago, PagoLiquidacion, Rubro, TipoOtroRubro, CuentaContable, ComprobanteAlumno, SolicitudPublicacion
from sga.models import DescuentoPosgradoMatricula, ConfiguracionDescuentoPosgrado, DescuentoPosgradoMatriculaRecorrido, \
    miinstitucion, CUENTAS_CORREOS, Periodo, Matricula, Carrera, FinanciamientoPosgrado, FinanciamientoPosgradoDetalle, DetalleConvenioPago, Persona, Inscripcion, Externo, RedPersona, ProfesorDistributivoHoras, ProyectosInvestigacion, ParticipantesMatrices, Notificacion
from sga.funciones import cuenta_email_disponible_para_envio, null_to_decimal, dia_semana_enletras_fecha, generar_nombre
from sga.tasks import send_html_mail


def actualizar_estado_proyecto():
    print("PROYECTOS DE INVESTIGACIÓN")
    print("==========Proceso de Actualización de estado a EN EJECUCIÓN de proyectos de investigación===========")
    # Consulto los proyectos con estado APROBADO POR OCAS de la CONVOCATORIA 2022
    c = 0
    proyectos = ProyectoInvestigacion.objects.filter(status=True, estado__valor=18, convocatoria_id=3).order_by('id')
    for proyecto in proyectos:
        # Si la fecha actual es mayor o igual a fecha de inicio
        if datetime.now().date() >= proyecto.fechainicio:
            print(proyecto)

            # Consulto el estado que voy a asignar: EN EJECUCIÓN
            estado = obtener_estado_solicitud(3, 20)
            proyecto.estado = estado
            proyecto.ejecucion = 1
            proyecto.save()

            # Creo el recorrido del proyecto
            recorrido = ProyectoInvestigacionRecorrido(proyecto=proyecto,
                                                       fecha=datetime.now().date(),
                                                       observacion='PROYECTO EN EJECUCIÓN',
                                                       estado=estado
                                                       )
            recorrido.save()
            c += 1
            print("Actualizado....")

    print("Total proyectos actualizados: ", c)
    print("")


def notificar_semana_vencimiento_evidencias():
    print("PROYECTOS DE INVESTIGACIÓN")
    print("====Notificación de evidencias no subidas para proyectos en EJECUCIÓN====")
    # Los proyectos con estado EN EJECUCIÓN
    c = 0
    notificados = 0
    proyectos = ProyectoInvestigacion.objects.filter(status=True, estado__valor=20).order_by('id')
    total = proyectos.count()
    for proyecto in proyectos:
        print("Proyecto:")
        print(proyecto)
        notificar = False

        actividades = proyecto.cronograma_detallado()
        for actividad in actividades:
            # print("Actividad:")
            # print(actividad)

            # si no ha finalizado el plazo para subir evidencias y si no existen las mismas
            if actividad.puede_subir_evidencias() and actividad.total_evidencias() == 0:
                dias = (actividad.fechafin - datetime.now().date()).days
                if dias == 7:
                    notificar = True
                    break

        if notificar:
            notificados += 1
            # Envio de e-mail de notificacion al solicitante
            # listacuentascorreo = [23, 24, 25, 26, 27]
            # posgrado1_unemi@unemi.edu.ec
            # posgrado2_unemi@unemi.edu.ec
            # posgrado3_unemi@unemi.edu.ec
            # posgrado4_unemi@unemi.edu.ec
            # posgrado5_unemi@unemi.edu.ec

            listacuentascorreo = [18]  # posgrado@unemi.edu.ec

            lista_email_envio = []
            # lista_email_envio.append('mreinosos@unemi.edu.ec')
            # lista_email_envio.append('olopezn@unemi.edu.ec')

            for integrante in proyecto.integrantes_proyecto():
                lista_email_envio += integrante.persona.lista_emails_envio()

            fechaenvio = datetime.now().date()
            horaenvio = datetime.now().time()
            cuenta = cuenta_email_disponible_para_envio(listacuentascorreo)

            tituloemail = "Recordatorio subida de evidencias de actividades de Proyecto de Investigación"
            tiponotificacion = "SUBIREVIDENCIA"

            send_html_mail(tituloemail,
                           "emails/notificacion_propuesta_proyecto_investigacion.html",
                           {'sistema': u'Posgrado UNEMI',
                            'fecha': fechaenvio,
                            'hora': horaenvio,
                            'tiponotificacion': tiponotificacion,
                            'tituloproyecto': proyecto.titulo,
                            'observaciones': '',
                            't': miinstitucion()
                            },
                           lista_email_envio,
                           # ['isaltosm@unemi.edu.ec'],
                           [],
                           cuenta=CUENTAS_CORREOS[cuenta][1]
                           )

            # Temporizador para evitar que se bloquee el servicio de gmail
            print("Enviando notificación por e-mail.....")
            ET.sleep(3)
            print("Notificado por e-mail")

    print("Proyectos en ejecución: ", total)
    print("Proyectos notificados: ", notificados)
    print("Proceso finalizado...")
    print("")


def actualizar_estado_actividad_proyecto():
    print("PROYECTOS DE INVESTIGACIÓN")
    print("=====Proceso de actualización de estados de las actividades del proyecto=====")
    # Proyectos con estado en ejecución
    proyectos = ProyectoInvestigacion.objects.filter(status=True, estado__valor=20).order_by('id')
    c = 0
    total = proyectos.count()
    hoy = datetime.now().date()
    for proyecto in proyectos:
        c += 1
        print("Procesando ", c, " de ", total)
        print("Proyecto:")
        print(proyecto)

        actividades = proyecto.cronograma_detallado()
        for actividad in actividades:
            print(actividad)
            if actividad.fechainicio <= hoy <= actividad.fechafin and actividad.estado != 2:
                # Asignar estado EN EJECUCIÓN
                actividad.estado = 2
                actividad.save()
                print("Estado cambiado a ", actividad.get_estado_display())
            else:
                print("Estado se mantiene")

            print("")

    print("Procesados: ", (c - 1))
    print("Proceso finalizado...")


def rechazar_solicitudes_becas_sin_evidencias():
    print("BECAS POSGRADO")
    print("=====Proceso de rechazo de las solicitudes de becas que no subieron las evidencias en el plazo establecido=====")
    c = rechazadas = norechazadas = 0

    periodobeca = ConfiguracionDescuentoPosgrado.objects.get(pk=3)
    print(periodobeca)

    # Solicitudes de admitidos, inscritos y que no han subido evidencias
    solicitudes = DescuentoPosgradoMatricula.objects.filter(detalleconfiguraciondescuentoposgrado__configuraciondescuentoposgrado=periodobeca,
                                                            status=True,
                                                            detalleconfiguraciondescuentoposgrado__status=True,
                                                            inscripcioncohorte__integrantegrupoentrevitamsc__estado=2,
                                                            inscripcioncohorte__tipobeca__isnull=False,
                                                            inscripcioncohorte__inscripcion__isnull=False,
                                                            evidenciasdescuentoposgradomatricula__isnull=True
                                                            ).exclude(estado=3).order_by('-id').distinct()
    total = solicitudes.count()
    for solicitud in solicitudes:
        c += 1
        print("Procesando ", c, "de", total)
        solicitante = solicitud.inscripcioncohorte.inscripcion.persona
        print(solicitante.usuario)
        print(solicitante.identificacion())
        print(solicitante)
        print(solicitud.inscripcioncohorte.inscripcion.carrera)
        print(solicitud.detalleconfiguraciondescuentoposgrado.descuentoposgrado.nombre)

        if datetime.now().date() > solicitud.inscripcioncohorte.cohortes.fechafinrequisitobeca:
            print("RECHAZADA")
            # Actualizo estado a RECHAZADO
            solicitud.estado = 3
            solicitud.save()

            # Guardo el recorrido
            recorridosolicitud = DescuentoPosgradoMatriculaRecorrido(
                descuentoposgradomatricula=solicitud,
                fecha=datetime.now().date(),
                persona_id=1,
                observacion='RECHAZO AUTOMÁTICO POR NO SUBIR EVIDENCIAS DENTRO DEL PLAZO ESTABLECIDO',
                estado=3
            )
            recorridosolicitud.save()

            # Notificación por e-mail al solicitante
            # Envio de e-mail de notificacion al solicitante
            # listacuentascorreo = [23, 24, 25, 26, 27]
            # posgrado1_unemi@unemi.edu.ec
            # posgrado2_unemi@unemi.edu.ec
            # posgrado3_unemi@unemi.edu.ec
            # posgrado4_unemi@unemi.edu.ec
            # posgrado5_unemi@unemi.edu.ec
            #
            listacuentascorreo = [18]  # posgrado@unemi.edu.ec

            lista_email_envio = solicitante.lista_emails_envio()

            fechaenvio = datetime.now().date()
            horaenvio = datetime.now().time()
            cuenta = cuenta_email_disponible_para_envio(listacuentascorreo)

            tituloemail = "Solicitud de Beca de Posgrado - Rechazada"
            tiponotificacion = "RECHAZO_SINEVIDENCIA"

            send_html_mail(tituloemail,
                           "emails/notificacion_solicitud_becaposgrado.html",
                           {'sistema': u'Posgrado UNEMI',
                            'fecha': fechaenvio,
                            'hora': horaenvio,
                            'saludo': 'Estimada' if solicitante.sexo_id == 1 else 'Estimado',
                            'solicitante': solicitante.nombre_completo_inverso(),
                            'tiponotificacion': tiponotificacion,
                            'observaciones': '',
                            't': miinstitucion()
                            },
                           lista_email_envio,
                           [],
                           cuenta=CUENTAS_CORREOS[cuenta][1]
                           )
            # Temporizador para evitar que se bloquee el servicion de gmail
            print("Enviando notificación por e-mail.....")
            ET.sleep(3)
            rechazadas += 1
        else:
            print("NO RECHAZADA")
            norechazadas += 1

        print("")


    print("Total solicitudes no rechazadas: ", norechazadas)
    print("Total solicitudes rechazadas: ", rechazadas)
    print("")


def rechazar_solicitudes_becas_situacion_economica():
    print("BECAS POSGRADO")
    print("=====Proceso de rechazo de las solicitudes de becas por Situación económica que no están en el grupo C- ni D=====")
    c = 1
    rechazadas = 0
    periodobeca = ConfiguracionDescuentoPosgrado.objects.get(pk=3)
    print(periodobeca)

    # Solicitudes de admitidos, inscritos, que hayan subido evidencias y que el tipo de beca sea por situación económica
    solicitudes = DescuentoPosgradoMatricula.objects.filter(
        detalleconfiguraciondescuentoposgrado__configuraciondescuentoposgrado=periodobeca,
        status=True,
        detalleconfiguraciondescuentoposgrado__status=True,
        inscripcioncohorte__integrantegrupoentrevitamsc__estado=2,
        inscripcioncohorte__tipobeca__isnull=False,
        inscripcioncohorte__inscripcion__isnull=False,
        evidenciasdescuentoposgradomatricula__isnull=False,
        inscripcioncohorte__rubro__status=True,
        inscripcioncohorte__rubro__admisionposgradotipo__in=[2, 3],
        inscripcioncohorte__rubro__cancelado=True,
        detalleconfiguraciondescuentoposgrado__descuentoposgrado__id=6
        ).exclude(estado=3).order_by('-id').distinct()
    total = solicitudes.count()

    for solicitud in solicitudes:
        print("Procesando ", c, "de", total)
        solicitante = solicitud.inscripcioncohorte.inscripcion.persona
        print(solicitante.usuario)
        print(solicitante.identificacion())
        print(solicitante)
        print(solicitud.inscripcioncohorte.inscripcion.carrera)
        print(solicitud.detalleconfiguraciondescuentoposgrado.descuentoposgrado.nombre)
        gruposocioeconomico = solicitante.mi_ficha().grupoeconomico.codigo
        print(gruposocioeconomico)

        # Si no pertenece al grupo socioeconomico C- ni D
        if gruposocioeconomico not in ['C-', 'D']:
            print("Solicitud rechazada")

            # Actualizo estado a RECHAZADO
            solicitud.estado = 3
            solicitud.save()

            # Guardo el recorrido
            recorridosolicitud = DescuentoPosgradoMatriculaRecorrido(
                descuentoposgradomatricula=solicitud,
                fecha=datetime.now().date(),
                persona_id=1,
                observacion='RECHAZO AUTOMÁTICO POR NO PERTENECER AL GRUPO SOCIOECONÓMICO C- NI D',
                estado=3
            )
            recorridosolicitud.save()

            # Notificación por e-mail al solicitante
            # Envio de e-mail de notificacion al solicitante
            # listacuentascorreo = [23, 24, 25, 26, 27]
            # posgrado1_unemi@unemi.edu.ec
            # posgrado2_unemi@unemi.edu.ec
            # posgrado3_unemi@unemi.edu.ec
            # posgrado4_unemi@unemi.edu.ec
            # posgrado5_unemi@unemi.edu.ec
            #
            listacuentascorreo = [18]  # posgrado@unemi.edu.ec

            lista_email_envio = solicitante.lista_emails_envio()

            fechaenvio = datetime.now().date()
            horaenvio = datetime.now().time()
            cuenta = cuenta_email_disponible_para_envio(listacuentascorreo)

            tituloemail = "Solicitud de Beca de Posgrado - Rechazada"
            tiponotificacion = "RECHAZO_GRUPOSOCIO"

            send_html_mail(tituloemail,
                           "emails/notificacion_solicitud_becaposgrado.html",
                           {'sistema': u'Posgrado UNEMI',
                            'fecha': fechaenvio,
                            'hora': horaenvio,
                            'saludo': 'Estimada' if solicitante.sexo_id == 1 else 'Estimado',
                            'solicitante': solicitante.nombre_completo_inverso(),
                            'tiponotificacion': tiponotificacion,
                            'observaciones': '',
                            't': miinstitucion()
                            },
                           lista_email_envio,
                           [],
                           cuenta=CUENTAS_CORREOS[cuenta][1]
                           )
            # Temporizador para evitar que se bloquee el servicion de gmail
            print("Enviando notificación por e-mail.....")
            ET.sleep(3)
            rechazadas += 1

        print("")
        c += 1

    print("Total solicitudes procesadas: ", total)
    print("Total solicitudes rechazadas por no pertenecer a grupos C- ni D: ", rechazadas)
    print("")


def llenar_historial_archivo():
    c = 0
    proyectos = ProyectoInvestigacion.objects.filter(status=True).order_by('id')
    total = proyectos.count()
    for proyecto in proyectos:
        if proyecto.archivoproyecto:
            c += 1
            print("Procesando ", c)
            print(proyecto)

            historialarchivo = ProyectoInvestigacionHistorialArchivo(
                proyecto=proyecto,
                tipo=1,
                archivo=proyecto.archivoproyecto
            )
            historialarchivo.save()
            print("Historial creado")

    print("Finalizado...")


def notificar_completar_proyectos():
    print(".:: Proceso de notificación completar información de Propuestas de Proyectos de Investigación ::.")

    # fechaactual = datetime.strptime('2022' + '-' + '11' + '-' + '23', '%Y-%m-%d').date()
    fechaactual = datetime.now().date()

    # Proceso se debe ejecutar día MIÉRCOLES
    if dia_semana_enletras_fecha(fechaactual).upper() == 'MIERCOLES':
        # Los proyectos con estado EN EDICIÓN de la convocatoria vigente
        c = 1
        notificados = 0
        proyectos = ProyectoInvestigacion.objects.filter(status=True, estado__valor=1, convocatoria__vigente=True).order_by('id')
        total = proyectos.count()
        for proyecto in proyectos:
            print("Procesando", c, "de", total)
            print("Proyecto:", proyecto)
            notificar = True
            participantes = resumen = presupuesto = cronograma = cronogramacompleto = presupuestocuadrado = True
            documentogenerado = True

            if proyecto.integrantes_proyecto().count() < 2:
                participantes = False

            if not proyecto.resumenpropuesta:
                resumen = False

            if not proyecto.prespuesto_asignado():
                presupuesto = False
            else:
                diferencia = proyecto.montototal - proyecto.presupuesto
                presupuestocuadrado = diferencia == 0

            if not proyecto.cronograma_asignado():
                cronograma = False
            elif not proyecto.total_ponderacion_actividades() == 100.0:
                cronogramacompleto = False

            documentogenerado = proyecto.documentogenerado

            contenidocorreo = []
            if participantes and resumen and presupuesto and presupuestocuadrado and cronograma and cronogramacompleto:
                if documentogenerado:
                    contenidocorreo.append("Finalizar la edición de su propuesta")
                else:
                    contenidocorreo.append("Generar el documento")
                    contenidocorreo.append("Finalizar la edición de su propuesta")
            else:
                if not participantes:
                    contenidocorreo.append("Ingresar los integrantes")
                if not resumen:
                    contenidocorreo.append("Ingresar el contenido")
                if not presupuesto:
                    contenidocorreo.append("Ingresar el presupuesto")
                if not cronograma:
                    contenidocorreo.append("Ingresar el cronograma de actividades")
                if not presupuestocuadrado:
                    contenidocorreo.append("Ingresar el presupuesto completo")
                if not cronogramacompleto:
                    contenidocorreo.append("Ingresar el cronograma de actividades completo")

                contenidocorreo.append("Generar el documento")
                contenidocorreo.append("Finalizar la edición de su propuesta")

            if notificar:
                notificados += 1
                # Envio de e-mail de notificacion al solicitante
                listacuentascorreo = [29]  # investigacion.dip@unemi.edu.ec

                lista_email_envio = []
                lista_email_cco = []
                lista_adjuntos = []
                lista_email_cco.append('isaltosm@unemi.edu.ec')
                # lista_email_envio.append('ivan_saltos_medina@unemi.edu.ec')
                # lista_email_envio.append('olopezn@unemi.edu.ec')

                for integrante in proyecto.integrantes_proyecto():
                    print(integrante)
                    lista_email_envio += integrante.persona.lista_emails_envio()
                    break

                fechaenvio = datetime.now().date()
                horaenvio = datetime.now().time()
                cuenta = cuenta_email_disponible_para_envio(listacuentascorreo)
                tituloemail = "Propuesta de Proyecto de Investigación pendiente de completar y finalizar"
                titulo = "Proyectos de Investigación"
                send_html_mail(tituloemail,
                               "emails/propuestaproyectoinvestigacion.html",
                               {'sistema': u'SGA - UNEMI',
                                'titulo': titulo,
                                'fecha': fechaenvio,
                                'hora': horaenvio,
                                'contenidocorreo': contenidocorreo,
                                'tiponotificacion': 'NOTGEN',
                                'tituloproyecto': proyecto.titulo,
                                'saludo': 'Estimada' if proyecto.profesor.persona.sexo_id == 1 else 'Estimado',
                                'nombrepersona': proyecto.profesor.persona.nombre_completo_inverso()
                                },
                               lista_email_envio,
                               lista_email_cco,
                               lista_adjuntos,
                               cuenta=CUENTAS_CORREOS[cuenta][1]
                               )

                # Temporizador para evitar que se bloquee el servicio de gmail
                print("Enviando notificación por e-mail.....")
                ET.sleep(3)
                print("Notificado por e-mail")
                print("")

            c += 1


        print("Proyectos en edición: ", total)
        print("Proyectos notificados: ", notificados)


        print("Proceso de notificación completar información de Propuestas de Proyectos de Investigación finalizado. . .")
    else:
        print("ATENCIÓN: El proceso únicamente se ejecuta días MIÉRCOLES...")


def notificar_confirmar_postulacion_obra_relevancia():
    print(".:: Proceso de notificación confirmar Postulación a Obras de Relevancia ::.")

    # fechaactual = datetime.strptime('2023' + '-' + '01' + '-' + '31', '%Y-%m-%d').date()
    fechaactual = datetime.now().date()

    # Proceso se debe ejecutar día VIERNES
    # if dia_semana_enletras_fecha(fechaactual).upper() == 'DOMINGO': # MARTES
    if dia_semana_enletras_fecha(fechaactual).upper() in ['MIERCOLES', 'JUEVES', 'VIERNES', 'SABADO', 'DOMINGO']:
        # Consultar las propuestas con estado EN EDICIÓN
        propuestas = ObraRelevancia.objects.filter(status=True, estado__valor=1)
        total = propuestas.count()
        c = 1
        for propuesta in propuestas:
            print("Procesando", c, "de", total)
            print("Postulación:", propuesta)
            solicitante = propuesta.profesor.persona

            # Envio de e-mail de notificacion al solicitante
            listacuentascorreo = [29]  # investigacion.dip@unemi.edu.ec

            lista_email_envio = solicitante.lista_emails_envio()
            # lista_email_envio = ['ivan_saltos_medina@hotmail.com']
            lista_email_cco = []
            lista_archivos_adjuntos = []
            lista_email_cco.append('isaltosm@unemi.edu.ec')

            fechaenvio = datetime.now().date()
            horaenvio = datetime.now().time()
            cuenta = cuenta_email_disponible_para_envio(listacuentascorreo)

            asuntoemail = "Postulación a Obra de Relevancia Pendiente de confirmar"
            titulo = "Postulación Obra de Relevancia"
            tiponotificacion = "NOTGEN"

            send_html_mail(asuntoemail,
                           "emails/postulacionobrarelevancia.html",
                           {'sistema': u'SGA - UNEMI',
                            'titulo': titulo,
                            'fecha': fechaenvio,
                            'hora': horaenvio,
                            'tiponotificacion': tiponotificacion,
                            'saludo': 'Estimada' if solicitante.sexo_id == 1 else 'Estimado',
                            'nombrepersona': solicitante.nombre_completo_inverso(),
                            'obrarelevancia': propuesta
                            },
                           lista_email_envio,
                           lista_email_cco,
                           lista_archivos_adjuntos,
                           cuenta=CUENTAS_CORREOS[cuenta][1]
                           )

            c += 1

        print("Proceso de notificación Proceso de notificación confirmar Postulación a Obras de Relevancia finalizado. . .")
    else:
        print("ATENCIÓN: El proceso únicamente se ejecuta días VIERNES...")


def crear_evaluaciones():
    id = 37

    fecha = datetime.now().date()
    puntajetotal = 100
    observacion = 'N'
    estadoevaluacion = 1

    proyecto = ProyectoInvestigacion.objects.get(pk=id)
    convocatoria = proyecto.convocatoria
    rubricas = RubricaEvaluacionItem.objects.filter(status=True, rubrica__convocatoria=convocatoria).order_by('id')

    print(proyecto)
    evaluadoresi = proyecto.evaluadores_internos()
    evaluadorese = proyecto.evaluadores_externos()

    print("Evaluaciones internas......")

    # CREO EVALUACIONES INTENAS POR CADA EVALUADOR
    for evaluador in evaluadoresi:
        print("Evaluador interno: ", evaluador)
        # CREO LA EVALUACION
        evaluacion = EvaluacionProyecto(
            proyecto=proyecto,
            fecha=fecha,
            tipo=1,
            evaluador=evaluador,
            puntajetotal=puntajetotal,
            observacion=observacion,
            estado=estadoevaluacion
        )
        evaluacion.save()

        print("Evaluación interna creada: ", evaluacion)

        # CREO EL DETALLE
        for rubrica in rubricas:
            detalle = EvaluacionProyectoDetalle(
                evaluacion=evaluacion,
                rubricaitem=rubrica,
                puntaje=rubrica.puntajemaximo
            )
            detalle.save()
            print("Detalle creado: ", detalle)

    # Obtengo estado EVALUACION INTERNA SUPERADA
    estado = obtener_estado_solicitud(3, 8)
    observacion = "ETAPA DE EVALUACIÓN INTERNA SUPERADA"

    # Asignar el estado al proyecto
    proyecto.estado = estado
    proyecto.save()

    print("Proyecto actualizado a ETAPA EVALUACION INTERNA SUPERADA")

    # Creo el recorrido del proyecto
    recorrido = ProyectoInvestigacionRecorrido(proyecto=proyecto,
                                               fecha=datetime.now().date(),
                                               observacion=observacion,
                                               estado=estado
                                               )
    recorrido.save()
    print("Recorrido creado")

    # Se asigna al proyecto el estado EVALUACIÓN EXTERNA
    estado = obtener_estado_solicitud(3, 10)
    observacion = "EVALUACIÓN EXTERNA EN CURSO"
    proyecto.estado = estado
    proyecto.save()
    print("Proyecto actualizado a EVALUACION EXTERNA EN CURSO")

    # Creo el recorrido del proyecto
    recorrido = ProyectoInvestigacionRecorrido(proyecto=proyecto,
                                               fecha=datetime.now().date(),
                                               observacion=observacion,
                                               estado=estado
                                               )
    recorrido.save()
    print("Recorrido creado")
    print("==================================")
    print("Evaluaciones externas......")

    # CREO EVALUACIONES INTENAS POR CADA EVALUADOR
    observacion = ""
    for evaluador in evaluadorese:
        print("Evaluador externo: ", evaluador)
        # CREO LA EVALUACION
        evaluacion = EvaluacionProyecto(
            proyecto=proyecto,
            fecha=fecha,
            tipo=2,
            evaluador=evaluador,
            puntajetotal=puntajetotal,
            observacion=observacion,
            estado=estadoevaluacion
        )
        evaluacion.save()

        print("Evaluación externa creada: ", evaluacion)

        # CREO EL DETALLE
        for rubrica in rubricas:
            detalle = EvaluacionProyectoDetalle(
                evaluacion=evaluacion,
                rubricaitem=rubrica,
                puntaje=rubrica.puntajemaximo
            )
            detalle.save()
            print("Detalle creado: ", detalle)

    # Se asigna al proyecto el estado EVALUACION EXTERNA SUPERADA
    estado = obtener_estado_solicitud(3, 11)
    observacion = "ETAPA DE EVALUACIÓN EXTERNA SUPERADA"

    # Asignar el estado al proyecto
    proyecto.estado = estado
    proyecto.save()
    print("Proyecto actualizado a  EVALUACION EXTERNA SUPERADA")

    # Creo el recorrido del proyecto
    recorrido = ProyectoInvestigacionRecorrido(proyecto=proyecto,
                                               fecha=datetime.now().date(),
                                               observacion=observacion,
                                               estado=estado
                                               )
    recorrido.save()
    print("Recorrido guardado")

    # Se asigna al proyecto el estado ACEPTADO
    estado = obtener_estado_solicitud(3, 13)
    observacion = "PROYECTO ACEPTADO PARA IR A CGA"
    proyecto.estado = estado
    proyecto.save()

    print("Proyecto actualizado a ACEPTADO PARA IR A CGA")

    # Creo el recorrido del proyecto
    recorrido = ProyectoInvestigacionRecorrido(proyecto=proyecto,
                                               fecha=datetime.now().date(),
                                               observacion=observacion,
                                               estado=estado
                                               )
    recorrido.save()
    print("Recorrido creado")

    # Asignar el puntaje de evaluacion interna y externa al proyecto
    puntajeinterna = proyecto.puntaje_final_evaluacion_interna()
    puntajeexterna = proyecto.puntaje_final_evaluacion_externa()

    proyecto.puntajeevalint = puntajeinterna
    proyecto.puntajeevalext = puntajeexterna
    proyecto.save()
    print("Puntajes de evaluacion de proyecto actualizados...")

    print("Registro procesado...")


def reporte_detalle_mensual():
    meses = ["Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio", "Julio", "Agosto", "Septiembre", "Octubre",
             "Noviembre", "Diciembre"]

    # En el combo debo seleccionar AÑO Y MES
    anio_actual = "2021"
    mes_actual = "12"
    ultimodia = str(calendar.monthrange(int(anio_actual), int(mes_actual))[1])
    primerdia = "1"

    # Fecha inicio de mes
    iniciomes = datetime.strptime(anio_actual + '-' + mes_actual + '-' + primerdia, '%Y-%m-%d').date()
    # Fecha fin de mes
    finmes = datetime.strptime(anio_actual + '-' + mes_actual + '-' + ultimodia, '%Y-%m-%d').date()
    # Fecha fin de mes anterior
    fechafinmesanterior = iniciomes - relativedelta(days=1)

    fuentenormal = easyxtitulo = easyxf(
        'font: name Times New Roman, color-index black, bold on , height 350; alignment: horiz centre')
    titulo = easyxf(
        'font: name Times New Roman, color-index black, bold on , height 350; alignment: horiz centre')
    titulo2 = easyxf(
        'font: name Times New Roman, color-index black, bold on , height 250; alignment: horiz centre')
    fuentecabecera = easyxf(
        'font: name Verdana, color-index black, bold on, height 150; pattern: pattern solid, fore_colour gray25; alignment: vert distributed, horiz centre; borders: left thin, right thin, top thin, bottom thin')
    fuentenormal = easyxf(
        'font: name Verdana, color-index black, height 150; borders: left thin, right thin, top thin, bottom thin')
    fuentenormalwrap = easyxf(
        'font: name Verdana, color-index black, height 150; borders: left thin, right thin, top thin, bottom thin')
    fuentenormalneg = easyxf(
        'font: name Verdana, color-index black, bold on , height 150; borders: left thin, right thin, top thin, bottom thin')
    fuentenormalnegrell = easyxf(
        'font: name Verdana, color-index black, bold on , height 150; borders: left thin, right thin, top thin, bottom thin; pattern: pattern solid, fore_colour gray25')
    fuentenormalwrap.alignment.wrap = True
    fuentenormalcent = easyxf(
        'font: name Verdana, color-index black, height 150; borders: left thin, right thin, top thin, bottom thin; alignment: horiz centre')
    fuentemoneda = easyxf(
        'font: name Verdana, color-index black, height 150; borders: left thin, right thin, top thin, bottom thin; alignment: horiz right',
        num_format_str=' "$" #,##0.00')
    fuentemonedaneg = easyxf(
        'font: name Verdana, color-index black, bold on, height 150; borders: left thin, right thin, top thin, bottom thin; alignment: horiz right; pattern: pattern solid, fore_colour gray25',
        num_format_str=' "$" #,##0.00')
    fuentefecha = easyxf(
        'font: name Verdana, color-index black, height 150; borders: left thin, right thin, top thin, bottom thin; alignment: horiz center',
        num_format_str='yyyy-mm-dd')
    fuentenumerodecimal = easyxf(
        'font: name Verdana, color-index black, height 150; borders: left thin, right thin, top thin, bottom thin; alignment: horiz right',
        num_format_str='#,##0.00')
    fuentenumeroentero = easyxf(
        'font: name Verdana, color-index black, height 150; borders: left thin, right thin, top thin, bottom thin; alignment: horiz right')

    font_style = XFStyle()
    font_style.font.bold = True
    font_style2 = XFStyle()
    font_style2.font.bold = False
    output_folder = os.path.join(os.path.join(SITE_STORAGE, 'media', 'arreglos'))

    libdestino = xlwt.Workbook()
    hojadestino = libdestino.add_sheet("Listado")

    hojadestino.write_merge(0, 0, 0, 12, 'UNIVERSIDAD ESTATAL DE MILAGRO', titulo)
    hojadestino.write_merge(1, 1, 0, 12, 'DIRECCIÓN DE INVESTIGACIÓN Y POSGRADO', titulo2)
    hojadestino.write_merge(2, 2, 0, 12, 'DETALLE DE MOVIMIENTOS MENSUALES DE VALORES DEL MES DE ' + meses[int(mes_actual) - 1].upper() + ' DEL ' + anio_actual, titulo2)

    fila = 4
    fechafinant = str(fechafinmesanterior.day) + "-" + meses[fechafinmesanterior.month - 1][:3].upper() + "-" + str(
        fechafinmesanterior.year)
    fechafinact = str(finmes.day) + "-" + meses[finmes.month - 1][:3].upper() + "-" + str(finmes.year)

    columnas = [
        (u"PROGRAMAS", 8000),
        (u"PROG.", 2500),
        (u"COHORTE", 2500),
        (u"FECHA PERIODO INICIAL", 3000),
        (u"FECHA PERIDO FINAL", 3000),
        (u"ESTUDIANTE", 10000),
        (u"IDENTIFICACIÓN", 3900),
        (u"SALDO INICIAL AL " + fechafinant, 4000),
        (u"FECHA CUOTA", 3000),
        (u"MONTO CUOTA", 4000),
        (u"FECHA PAGO", 3000),
        (u"MONTO PAGO", 4000),
        (u"SALDO FINAL AL " + fechafinact, 4000)
    ]

    for col_num in range(len(columnas)):
        hojadestino.write(fila, col_num, columnas[col_num][0], fuentecabecera)
        hojadestino.col(col_num).width = columnas[col_num][1]

    # periodos = Periodo.objects.values('id').filter(nivel__matricula__rubro__saldo__gt=0, nivel__matricula__rubro__fechavence__lt=datetime.now().date(), tipo__id__in=[3, 4]).distinct().order_by('id')
    # matriculas = Matricula.objects.filter(nivel__periodo__tipo__id__in=[3, 4], inscripcion__persona__cedula='0926476813').order_by('inscripcion__persona__apellido1', 'inscripcion__persona__apellido2', 'inscripcion__persona__nombres')


    # print("Ultimo dia mes anterior: ", fechafinmesanterior)
    # print("Primer dia mes actual: ", iniciomes, " Ultimo día mes actual: ", finmes)

    matriculas = Matricula.objects.filter(status=True, nivel__periodo__tipo__id__in=[3, 4]
                                          # inscripcion__persona__cedula='0916777014',
                                          # inscripcion__carrera__id=60,
                                          # nivel__periodo__id__in=[12, 13, 78, 84, 91]
                                          ).distinct().order_by('inscripcion__persona__apellido1', 'inscripcion__persona__apellido2', 'inscripcion__persona__nombres')

    # matriculas = Matricula.objects.filter(status=True, nivel__periodo__tipo__id__in=[3, 4]).distinct().order_by(
    #     'inscripcion__persona__apellido1', 'inscripcion__persona__apellido2', 'inscripcion__persona__nombres')

    totalmatriculas = matriculas.count()

    # print(totalmatriculas)
    c = 0

    horainicio = datetime.now()

    totalalumnos = 0

    totalsaldoinicial = 0
    totalrubros = 0
    totalpagado = 0
    totalsaldofinal = 0

    fila = 5
    cedula = ''
    for matricula in matriculas:
        c += 1
        print("Procesando ", c, " de ", totalmatriculas)


        # SALDO ANTERIOR
        totalrubrosanterior = Decimal(null_to_decimal(matricula.rubro_set.filter(status=True,
                                                                            fechavence__lt=iniciomes,

                                                                                 ).aggregate(valor=Sum('valortotal'))['valor'], 2)).quantize(Decimal('.01'))
        print("Total rubros anterior:", totalrubrosanterior)

        totalliquidado = Decimal(null_to_decimal(matricula.rubro_set.filter(status=True,
                                                                                 fechavence__lt=iniciomes,
                                                                            pago__pagoliquidacion__isnull=False
                                                                                 ).aggregate(valor=Sum('valortotal'))['valor'], 2)).quantize(Decimal('.01'))

        print("Total Liquidado ", totalliquidado)

        totalanulado = Decimal(null_to_decimal(Pago.objects.filter(
            status=True,
            rubro__matricula=matricula,
            rubro__status=True,
            rubro__fechavence__lte=finmes,
            factura__valida=False,
            factura__status=True
        ).aggregate(pagos=Sum('valortotal'))['pagos'], 2)).quantize(Decimal('.01'))

        print("total anulado: ", totalanulado)




        # PAGADO ANTERIOR ---- REVISAR BIEN ESTA TOMANDO PAGO DE RUBROS DE JULIO, AGOSTO
        totalpagosanterior = Decimal(null_to_decimal(Pago.objects.filter(
                                    fecha__lt=iniciomes,
                                    pagoliquidacion__isnull=True,
                                    status=True,
                                    rubro__matricula=matricula,
                                    rubro__status=True
                                    # rubro__fechavence__lte=finmes
                                    ).exclude(factura__valida=False).aggregate(pagos=Sum('valortotal'))['pagos'], 2)).quantize(Decimal('.01'))
        print("Total Pagado anterior: ", totalpagosanterior)


        totalvencimientosposterior = Decimal(null_to_decimal(Pago.objects.filter(
            # rubro__matricula__inscripcion__persona__cedula__in=cedulas,
            fecha__lt=iniciomes,
            pagoliquidacion__isnull=True,
            status=True,
            rubro__matricula__nivel__periodo__tipo__id__in=[3, 4],
            rubro__matricula=matricula,
            # rubro__matricula__inscripcion__carrera__id=carrera,
            # rubro__matricula__nivel__periodo__id__in=periodos,
            rubro__status=True,
            rubro__fechavence__gte=iniciomes
        ).exclude(factura__valida=False).aggregate(pagos=Sum('valortotal'))['pagos'], 2)).quantize(Decimal('.01'))



        saldoanterior = totalrubrosanterior - (totalpagosanterior + totalliquidado + totalanulado)
        saldoanterior += totalvencimientosposterior
        print("Saldo anterior: ", saldoanterior)


        # RUBROS DEL MES ACTUAL
        rubros = matricula.rubro_set.filter(status=True, fechavence__gte=iniciomes, fechavence__lte=finmes)

        # ESOS RUBROS DEL MES ACTUAL VERIFICAR SI FUERON PAGADOS EN MESES ANTERIORES Y SI SALDO = 0 NO SE DEBE MOSTRAR

        # CONSULTAR PAGOS DEL MES PERO QUE SON DE RUBROS POSTERIORES
        # Pagos del mes que corresponden a rubros de meses posteriores

        pagos_rubros_posteriores = Pago.objects.filter(
            # rubro__matricula__inscripcion__persona__cedula__in=cedulas,
            fecha__gte=iniciomes,
            fecha__lte=finmes,
            pagoliquidacion__isnull=True,
            status=True,
            rubro__matricula__nivel__periodo__tipo__id__in=[3, 4],
            rubro__matricula=matricula,
            # rubro__matricula__inscripcion__carrera__id=carrera,
            # rubro__matricula__nivel__periodo__id__in=periodos,
            rubro__status=True,
            rubro__fechavence__gt=finmes
        ).exclude(factura__valida=False)

        # PAGOS DEL MES ACTUAL
        pagos = Pago.objects.filter(fecha__gte=iniciomes, fecha__lte=finmes,
                                    pagoliquidacion__isnull=True,
                                    status=True,
                                    rubro__matricula=matricula,
                                    rubro__status=True
                                    # rubro__fechavence__lte=finmes
                                    ).exclude(factura__valida=False)

        print("Saldo anterior: ", saldoanterior)

        if saldoanterior != 0 or rubros or pagos or pagos_rubros_posteriores:
            totalrubroalumno = totalpagoalumno = 0
        # if rubros or pagos:
            totalalumnos += 1
            print(matricula.inscripcion.carrera.nombre)
            print(matricula.inscripcion.carrera.alias)
            print(matricula.nivel.periodo.cohorte)
            print(matricula.nivel.periodo.inicio)
            print(matricula.nivel.periodo.fin)
            print(matricula.inscripcion.persona.nombre_completo_inverso())
            print(matricula.inscripcion.persona.identificacion())

            if not cedula:
                cedula = matricula.inscripcion.persona.identificacion()

            if cedula != matricula.inscripcion.persona.identificacion():
                cedula = matricula.inscripcion.persona.identificacion()


            hojadestino.write(fila, 0, matricula.inscripcion.carrera.nombre, fuentenormal)
            hojadestino.write(fila, 1, matricula.inscripcion.carrera.alias, fuentenormalcent)
            hojadestino.write(fila, 2, matricula.nivel.periodo.cohorte, fuentenormalcent)
            hojadestino.write(fila, 3, matricula.nivel.periodo.inicio, fuentefecha)
            hojadestino.write(fila, 4, matricula.nivel.periodo.fin, fuentefecha)
            hojadestino.write(fila, 5, matricula.inscripcion.persona.nombre_completo_inverso(), fuentenormal)
            hojadestino.write(fila, 6, matricula.inscripcion.persona.identificacion(), fuentenormal)
            hojadestino.write(fila, 7, saldoanterior, fuentemoneda)


            # if matricula.inscripcion.persona.cedula == '0916853559':
            #     r = matricula.rubro_set.filter(status=True,
            #                                fechavence__lt='2021-06-01').order_by('fechavence')
            #     for ru in r:
            #         print(ru.id, ru.nombre, ru.status, ru.cancelado, ru.fechavence, ru.valortotal)
            #         if ru.esta_liquidado():
            #             print("Liquidado")
            #
            #
            # # REVISAR BIEN ESTA TOMANDO PAGO DE RUBROS DE JULIO, AGOSTO
            # p = Pago.objects.filter(fecha__lt=iniciomes,
            #                         pagoliquidacion__isnull=True,
            #                         status=True,
            #                         rubro__matricula=matricula,
            #                         rubro__status=True,
            #                         rubro__fechavence__lte=finmes
            #                         ).exclude(factura__valida=False, factura__status=True)
            # print("---IDPAGO--TOTAL PAGO---FECHA PAGO---RUBRO ID---FECHA RUBRO---")
            # cp = 0
            # tp = 0
            # for pa in p:
            #     cp += 1
            #     tp += pa.valortotal
            #     print("Pago #", cp, "-" , pa.id, pa.valortotal, pa.fecha, pa.rubro.id, pa.rubro.fechavence)
            # print("Total pagado hasta el ", fechafinmesanterior, " $ ", tp)

            print("SALDO INICIAL AL", fechafinmesanterior, " $: ", saldoanterior, " *********************")


            # Rubros del año y mes actual
            print("======RUBROS MES ACTUAL=======")
            totalrubrosmesactual = 0
            cantidad_rubros = 0
            for rubro in rubros:

                cantidad_rubros += 1

                print("FECHA CUOTA: ", rubro.fechavence, " MONTO CUOTA: ", rubro.valortotal, " PAGADO:", rubro.cancelado)
                # print(rubro.pagos()[0].fecha)

                # Preguntar si rubro fue pagado en meses anteriores
                totalpagadorubro = Decimal(null_to_decimal(Pago.objects.filter(
                    # rubro__matricula__inscripcion__persona__cedula__in=cedulas,
                    fecha__lt=iniciomes,
                    pagoliquidacion__isnull=True,
                    status=True,
                    rubro__matricula__nivel__periodo__tipo__id__in=[3, 4],
                    # rubro__matricula__inscripcion__carrera__id=carrera,
                    # rubro__matricula__nivel__periodo__id__in=periodos,
                    rubro__status=True,
                    rubro__fechavence__gte=iniciomes,
                    rubro__fechavence__lte=finmes,
                    rubro=rubro
                ).exclude(factura__valida=False).aggregate(pagos=Sum('valortotal'))['pagos'], 2)).quantize(
                    Decimal('.01'))

                valor_neto_rubro = rubro.valortotal - totalpagadorubro

                # totalrubrosmesactual += rubro.valortotal
                # totalrubroalumno += rubro.valortotal

                totalrubrosmesactual += valor_neto_rubro
                totalrubroalumno += valor_neto_rubro

                if valor_neto_rubro > 0:
                    if saldoanterior != 0:

                        if cantidad_rubros == 1:
                            hojadestino.write(fila, 8, "", fuentenormal)
                            hojadestino.write(fila, 9, "", fuentenormal)
                            hojadestino.write(fila, 10, "", fuentenormal)
                            hojadestino.write(fila, 11, "", fuentenormal)
                            hojadestino.write(fila, 12, "", fuentenormal)

                        fila += 1

                        hojadestino.write(fila, 0, matricula.inscripcion.carrera.nombre, fuentenormal)
                        hojadestino.write(fila, 1, matricula.inscripcion.carrera.alias, fuentenormalcent)
                        hojadestino.write(fila, 2, matricula.nivel.periodo.cohorte, fuentenormalcent)
                        hojadestino.write(fila, 3, matricula.nivel.periodo.inicio, fuentefecha)
                        hojadestino.write(fila, 4, matricula.nivel.periodo.fin, fuentefecha)
                        hojadestino.write(fila, 5, matricula.inscripcion.persona.nombre_completo_inverso(), fuentenormal)
                        hojadestino.write(fila, 6, matricula.inscripcion.persona.identificacion(), fuentenormal)
                        hojadestino.write(fila, 7, 0, fuentemoneda)
                        hojadestino.write(fila, 8, rubro.fechavence, fuentefecha)
                        # hojadestino.write(fila, 9, rubro.valortotal, fuentemoneda)
                        hojadestino.write(fila, 9, valor_neto_rubro, fuentemoneda)
                        hojadestino.write(fila, 10, "", fuentenormal)
                        hojadestino.write(fila, 11, "", fuentenormal)
                        hojadestino.write(fila, 12, "", fuentenormal)
                    else:
                        if cantidad_rubros > 1:
                            fila += 1
                            hojadestino.write(fila, 0, matricula.inscripcion.carrera.nombre, fuentenormal)
                            hojadestino.write(fila, 1, matricula.inscripcion.carrera.alias, fuentenormalcent)
                            hojadestino.write(fila, 2, matricula.nivel.periodo.cohorte, fuentenormalcent)
                            hojadestino.write(fila, 3, matricula.nivel.periodo.inicio, fuentefecha)
                            hojadestino.write(fila, 4, matricula.nivel.periodo.fin, fuentefecha)
                            hojadestino.write(fila, 5, matricula.inscripcion.persona.nombre_completo_inverso(),
                                              fuentenormal)
                            hojadestino.write(fila, 6, matricula.inscripcion.persona.identificacion(), fuentenormal)
                            hojadestino.write(fila, 7, 0, fuentemoneda)


                        # hojadestino.write(fila, 6, 0, fuentemoneda)
                        hojadestino.write(fila, 8, rubro.fechavence, fuentefecha)
                        # hojadestino.write(fila, 9, rubro.valortotal, fuentemoneda)
                        hojadestino.write(fila, 9, valor_neto_rubro, fuentemoneda)
                        hojadestino.write(fila, 10, "", fuentenormal)
                        hojadestino.write(fila, 11, "", fuentenormal)
                        hojadestino.write(fila, 12, "", fuentenormal)


            if not rubros:
                hojadestino.write(fila, 8, "", fuentenormal)
                hojadestino.write(fila, 9, "", fuentenormal)
                hojadestino.write(fila, 10, "", fuentenormal)
                hojadestino.write(fila, 11, "", fuentenormal)
                hojadestino.write(fila, 12, "", fuentenormal)



            for pago in pagos_rubros_posteriores:
                totalrubrosmesactual += pago.valortotal
                totalrubroalumno += pago.valortotal

                fila += 1
                hojadestino.write(fila, 0, matricula.inscripcion.carrera.nombre, fuentenormal)
                hojadestino.write(fila, 1, matricula.inscripcion.carrera.alias, fuentenormalcent)
                hojadestino.write(fila, 2, matricula.nivel.periodo.cohorte, fuentenormalcent)
                hojadestino.write(fila, 3, matricula.nivel.periodo.inicio, fuentefecha)
                hojadestino.write(fila, 4, matricula.nivel.periodo.fin, fuentefecha)
                hojadestino.write(fila, 5, matricula.inscripcion.persona.nombre_completo_inverso(), fuentenormal)
                hojadestino.write(fila, 6, matricula.inscripcion.persona.identificacion(), fuentenormal)
                hojadestino.write(fila, 7, 0, fuentemoneda)
                hojadestino.write(fila, 8, pago.fecha, fuentefecha)
                hojadestino.write(fila, 9, pago.valortotal, fuentemoneda)
                hojadestino.write(fila, 10, "", fuentenormal)
                hojadestino.write(fila, 11, "", fuentenormal)
                hojadestino.write(fila, 12, "", fuentenormal)



            # Pagos del año y mes actual
            print("=====PAGOS MES ACTUAL=====")
            totalpagosmesactual = 0
            for pago in pagos:
                print("FECHA PAGO: ", pago.fecha, " MONTO PAGO: ",  pago.valortotal, " FECHA VENCE RUBRO:", pago.rubro.fechavence)

                totalpagosmesactual += pago.valortotal
                totalpagoalumno += pago.valortotal

                fila += 1
                hojadestino.write(fila, 0, matricula.inscripcion.carrera.nombre, fuentenormal)
                hojadestino.write(fila, 1, matricula.inscripcion.carrera.alias, fuentenormalcent)
                hojadestino.write(fila, 2, matricula.nivel.periodo.cohorte, fuentenormalcent)
                hojadestino.write(fila, 3, matricula.nivel.periodo.inicio, fuentefecha)
                hojadestino.write(fila, 4, matricula.nivel.periodo.fin, fuentefecha)
                hojadestino.write(fila, 5, matricula.inscripcion.persona.nombre_completo_inverso(), fuentenormal)
                hojadestino.write(fila, 6, matricula.inscripcion.persona.identificacion(), fuentenormal)
                hojadestino.write(fila, 7, 0, fuentemoneda)
                hojadestino.write(fila, 8, "", fuentenormal)
                hojadestino.write(fila, 9, "", fuentenormal)
                hojadestino.write(fila, 10, pago.fecha, fuentefecha)
                hojadestino.write(fila, 11, pago.valortotal, fuentemoneda)
                hojadestino.write(fila, 12, "", fuentenormal)

            # if not pagos:
            #     hojadestino.write(fila, 10, "", fuentenormal)
            #     hojadestino.write(fila, 11, "", fuentenormal)
            #     hojadestino.write(fila, 12, "", fuentenormal)

            saldofinmes = (saldoanterior + totalrubrosmesactual) - totalpagosmesactual

            fila += 1
            hojadestino.write(fila, 0, "", fuentenormal)
            hojadestino.write(fila, 1, "", fuentenormal)
            hojadestino.write(fila, 2, "", fuentenormal)
            hojadestino.write(fila, 3, "", fuentenormal)
            hojadestino.write(fila, 4, "", fuentenormal)
            hojadestino.write(fila, 5, "TOTAL " + matricula.inscripcion.persona.nombre_completo_inverso(), fuentenormalnegrell)
            hojadestino.write(fila, 6, "", fuentenormal)
            hojadestino.write(fila, 7, saldoanterior, fuentemonedaneg)
            hojadestino.write(fila, 8, "", fuentenormal)
            hojadestino.write(fila, 9, totalrubroalumno, fuentemonedaneg)
            hojadestino.write(fila, 10, "", fuentenormal)
            hojadestino.write(fila, 11, totalpagoalumno, fuentemonedaneg)
            hojadestino.write(fila, 12, saldofinmes, fuentemonedaneg)



            print("TOTAL SALDO:", totalrubrosmesactual + saldoanterior)
            print("TOTAL PAGADO: ", totalpagosmesactual)


            print("SALDO FINAL AL ", finmes, " $: ", saldofinmes, " *********************")

            totalsaldoinicial += saldoanterior
            totalrubros += totalrubrosmesactual
            totalpagado += totalpagosmesactual
            totalsaldofinal += saldofinmes

            fila += 1

    hojadestino.write(fila, 5, "TOTAL GENERAL", fuentenormalnegrell)
    hojadestino.write(fila, 7, totalsaldoinicial, fuentemonedaneg)
    hojadestino.write(fila, 9, totalrubros, fuentemonedaneg)
    hojadestino.write(fila, 11, totalpagado, fuentemonedaneg)
    hojadestino.write(fila, 12, totalsaldofinal, fuentemonedaneg)

    print("Total alumnos para el reporte: ", totalalumnos)

    print("Total saldo anterior: ", totalsaldoinicial)
    print("Total rubros del mes: ", totalrubros)
    print("Total pagado del mes: ", totalpagado)
    print("Total saldo actual: ", totalsaldofinal)

    print("Inicio: ", horainicio)
    print("Fin: ", datetime.now())

    libdestino.save(output_folder + "/R1_DETALLE_MENSUAL_DICIEMBRE_2021.xls")
    print("Archivo creado. . .")


def reporte_vencimientos_mensuales():
    meses = ["Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio", "Julio", "Agosto", "Septiembre", "Octubre",
             "Noviembre", "Diciembre"]

    # En el combo debo seleccionar AÑO Y MES
    anio_actual = "2021"
    mes_actual = "12"
    ultimodia = str(calendar.monthrange(int(anio_actual), int(mes_actual))[1])
    primerdia = "1"

    # Fecha inicio de mes
    iniciomes = datetime.strptime(anio_actual + '-' + mes_actual + '-' + primerdia, '%Y-%m-%d').date()
    # Fecha fin de mes
    finmes = datetime.strptime(anio_actual + '-' + mes_actual + '-' + ultimodia, '%Y-%m-%d').date()
    # Fecha fin de mes anterior
    fechafinmesanterior = iniciomes - relativedelta(days=1)


    fuentenormal = easyxtitulo = easyxf(
        'font: name Times New Roman, color-index black, bold on , height 350; alignment: horiz centre')
    titulo = easyxf(
        'font: name Times New Roman, color-index black, bold on , height 350; alignment: horiz centre')
    titulo2 = easyxf(
        'font: name Times New Roman, color-index black, bold on , height 250; alignment: horiz centre')
    fuentecabecera = easyxf(
        'font: name Verdana, color-index black, bold on, height 150; pattern: pattern solid, fore_colour gray25; alignment: vert distributed, horiz centre; borders: left thin, right thin, top thin, bottom thin')
    fuentenormal = easyxf(
        'font: name Verdana, color-index black, height 150; borders: left thin, right thin, top thin, bottom thin')
    fuentenormalwrap = easyxf(
        'font: name Verdana, color-index black, height 150; borders: left thin, right thin, top thin, bottom thin')
    fuentenormalneg = easyxf(
        'font: name Verdana, color-index black, bold on , height 150; borders: left thin, right thin, top thin, bottom thin')
    fuentenormalnegrell = easyxf(
        'font: name Verdana, color-index black, bold on , height 150; borders: left thin, right thin, top thin, bottom thin; pattern: pattern solid, fore_colour gray25')
    fuentenormalwrap.alignment.wrap = True
    fuentenormalcent = easyxf(
        'font: name Verdana, color-index black, height 150; borders: left thin, right thin, top thin, bottom thin; alignment: horiz centre')
    fuentemoneda = easyxf(
        'font: name Verdana, color-index black, height 150; borders: left thin, right thin, top thin, bottom thin; alignment: horiz right',
        num_format_str=' "$" #,##0.00')
    fuentemonedaneg = easyxf(
        'font: name Verdana, color-index black, bold on, height 150; borders: left thin, right thin, top thin, bottom thin; alignment: horiz right; pattern: pattern solid, fore_colour gray25',
        num_format_str=' "$" #,##0.00')
    fuentefecha = easyxf(
        'font: name Verdana, color-index black, height 150; borders: left thin, right thin, top thin, bottom thin; alignment: horiz center',
        num_format_str='yyyy-mm-dd')
    fuentenumerodecimal = easyxf(
        'font: name Verdana, color-index black, height 150; borders: left thin, right thin, top thin, bottom thin; alignment: horiz right',
        num_format_str='#,##0.00')
    fuentenumeroentero = easyxf(
        'font: name Verdana, color-index black, height 150; borders: left thin, right thin, top thin, bottom thin; alignment: horiz right')

    font_style = XFStyle()
    font_style.font.bold = True
    font_style2 = XFStyle()
    font_style2.font.bold = False
    output_folder = os.path.join(os.path.join(SITE_STORAGE, 'media', 'arreglos'))

    libdestino = xlwt.Workbook()
    hojadestino = libdestino.add_sheet("Listado")

    hojadestino.write_merge(0, 0, 0, 8, 'UNIVERSIDAD ESTATAL DE MILAGRO', titulo)
    hojadestino.write_merge(1, 1, 0, 8, 'DIRECCIÓN DE INVESTIGACIÓN Y POSGRADO', titulo2)
    hojadestino.write_merge(2, 2, 0, 8, 'VENCIMIENTOS MENSUALES DEL MES DE ' + meses[int(mes_actual) - 1].upper() + ' DEL ' + anio_actual, titulo2)

    fila = 4

    columnas = [
        (u"PROGRAMA DE MAESTRÍA", 7000),
        (u"PROG.", 2500),
        (u"COHORTE", 3000),
        (u"FECHA PERIODO INICIAL", 3000),
        (u"FECHA PERIDO FINAL", 3000),
        (u"ESTUDIANTE", 10000),
        (u"IDENTIFICACIÓN", 5000),
        (u"FECHA CUOTA", 3000),
        (u"MONTO CUOTA", 3500)
    ]

    for col_num in range(len(columnas)):
        hojadestino.write(fila, col_num, columnas[col_num][0], fuentecabecera)
        hojadestino.col(col_num).width = columnas[col_num][1]

    # # En el combo debo seleccionar AÑO Y MES
    # anio_actual = "2021"
    # mes_actual = "6"
    # ultimodia = str(calendar.monthrange(int(anio_actual), int(mes_actual))[1])
    # primerdia = "1"
    #
    # # Fecha inicio de mes
    # iniciomes = datetime.strptime(anio_actual + '-' + mes_actual + '-' + primerdia, '%Y-%m-%d').date()
    # # Fecha fin de mes
    # finmes = datetime.strptime(anio_actual + '-' + mes_actual + '-' + ultimodia, '%Y-%m-%d').date()
    # # Fecha fin de mes anterior
    # fechafinmesanterior = iniciomes - relativedelta(days=1)

    matriculas = Matricula.objects.filter(status=True, nivel__periodo__tipo__id__in=[3, 4]
                                          # inscripcion__persona__cedula='0916777014',
                                          # inscripcion__carrera__id=60,
                                          # nivel__periodo__id__in=[12, 13, 78, 84, 91]
                                          ).distinct().order_by('inscripcion__persona__apellido1',
                                                                'inscripcion__persona__apellido2',
                                                                'inscripcion__persona__nombres')
    totalmatriculas = matriculas.count()

    # rubros_vencidos = Rubro.objects.filter(
    #     fechavence__gte=iniciomes,
    #     fechavence__lte=finmes,
    #     status=True,
    #     matricula__status=True,
    #     matricula__nivel__periodo__tipo__id__in=[3, 4],
    #     matricula__inscripcion__carrera__id=60,
    #     matricula__nivel__periodo__id__in=[12, 13, 78, 84, 91],
    #                                        # matricula__inscripcion__persona__cedula='1707325062',
    #                                        ).distinct().order_by(
    #     'matricula__inscripcion__persona__apellido1', 'matricula__inscripcion__persona__apellido2',
    #     'matricula__inscripcion__persona__nombres')
    #
    # # total = matriculas.count()
    # # print(total)
    # total2 = rubros_vencidos.count()
    # print(total2)
    # totalrubros = 0
    #
    # # for matricula in matriculas:
    # #     print(matricula.inscripcion.carrera.nombre)
    # #     print(matricula.inscripcion.carrera.alias)
    # #     print(matricula.nivel.periodo.cohorte)
    # #     print(matricula.nivel.periodo.inicio)
    # #     print(matricula.nivel.periodo.fin)
    # #     print(matricula.inscripcion.persona.nombre_completo_inverso())
    # #     print(matricula.inscripcion.persona.identificacion())

    fila = 5
    totalrubros = 0
    cont = 1
    for matricula in matriculas:
        print("Procesando ", cont, " de ", totalmatriculas)
        rubros = matricula.rubro_set.filter(status=True, fechavence__gte=iniciomes, fechavence__lte=finmes)

        pagos_rubros_posteriores = Pago.objects.filter(
            # rubro__matricula__inscripcion__persona__cedula__in=cedulas,
            fecha__gte=iniciomes,
            fecha__lte=finmes,
            pagoliquidacion__isnull=True,
            status=True,
            rubro__matricula__nivel__periodo__tipo__id__in=[3, 4],
            rubro__matricula=matricula,
            # rubro__matricula__inscripcion__carrera__id=carrera,
            # rubro__matricula__nivel__periodo__id__in=periodos,
            rubro__status=True,
            rubro__fechavence__gt=finmes
        ).exclude(factura__valida=False)

        if rubros or pagos_rubros_posteriores:

            for rubro in rubros:
                matricula = rubro.matricula
                # Preguntar si rubro fue pagado en meses anteriores
                totalpagadorubro = Decimal(null_to_decimal(Pago.objects.filter(
                    # rubro__matricula__inscripcion__persona__cedula__in=cedulas,
                    fecha__lt=iniciomes,
                    pagoliquidacion__isnull=True,
                    status=True,
                    rubro__matricula__nivel__periodo__tipo__id__in=[3, 4],
                    # rubro__matricula__inscripcion__carrera__id=carrera,
                    # rubro__matricula__nivel__periodo__id__in=periodos,
                    rubro__status=True,
                    rubro__fechavence__gte=iniciomes,
                    rubro__fechavence__lte=finmes,
                    rubro=rubro
                ).exclude(factura__valida=False).aggregate(pagos=Sum('valortotal'))['pagos'], 2)).quantize(
                    Decimal('.01'))

                valor_neto_rubro = rubro.valortotal - totalpagadorubro

                if valor_neto_rubro > 0:
                    print(matricula.inscripcion.carrera.nombre)
                    print(matricula.inscripcion.carrera.alias)
                    print(matricula.nivel.periodo.cohorte)
                    print(matricula.nivel.periodo.inicio)
                    print(matricula.nivel.periodo.fin)
                    print(matricula.inscripcion.persona.nombre_completo_inverso())
                    print(matricula.inscripcion.persona.identificacion())
                    print("Rubro: ", rubro.id)
                    print("Fecha vence:", rubro.fechavence)
                    print("Valor: ", valor_neto_rubro)
                    totalrubros += valor_neto_rubro

                    hojadestino.write(fila, 0, matricula.inscripcion.carrera.nombre, fuentenormal)
                    hojadestino.write(fila, 1, matricula.inscripcion.carrera.alias, fuentenormalcent)
                    hojadestino.write(fila, 2, matricula.nivel.periodo.cohorte, fuentenormalcent)
                    hojadestino.write(fila, 3, matricula.nivel.periodo.inicio, fuentefecha)
                    hojadestino.write(fila, 4, matricula.nivel.periodo.fin, fuentefecha)
                    hojadestino.write(fila, 5, matricula.inscripcion.persona.nombre_completo_inverso(), fuentenormal)
                    hojadestino.write(fila, 6, matricula.inscripcion.persona.identificacion(), fuentenormal)
                    hojadestino.write(fila, 7, rubro.fechavence, fuentefecha)
                    hojadestino.write(fila, 8, valor_neto_rubro, fuentemoneda)

                    fila += 1


            for pago in pagos_rubros_posteriores:
                matricula = pago.rubro.matricula

                print(matricula.inscripcion.carrera.nombre)
                print(matricula.inscripcion.carrera.alias)
                print(matricula.nivel.periodo.cohorte)
                print(matricula.nivel.periodo.inicio)
                print(matricula.nivel.periodo.fin)
                print(matricula.inscripcion.persona.nombre_completo_inverso())
                print(matricula.inscripcion.persona.identificacion())
                print("Rubro: ", pago.rubro.id)
                print("Fecha vence:", pago.fecha)
                print("Valor: ", pago.valortotal)
                totalrubros += pago.valortotal

                hojadestino.write(fila, 0, matricula.inscripcion.carrera.nombre, fuentenormal)
                hojadestino.write(fila, 1, matricula.inscripcion.carrera.alias, fuentenormalcent)
                hojadestino.write(fila, 2, matricula.nivel.periodo.cohorte, fuentenormalcent)
                hojadestino.write(fila, 3, matricula.nivel.periodo.inicio, fuentefecha)
                hojadestino.write(fila, 4, matricula.nivel.periodo.fin, fuentefecha)
                hojadestino.write(fila, 5, matricula.inscripcion.persona.nombre_completo_inverso(), fuentenormal)
                hojadestino.write(fila, 6, matricula.inscripcion.persona.identificacion(), fuentenormal)
                hojadestino.write(fila, 7, pago.fecha, fuentefecha)
                hojadestino.write(fila, 8, pago.valortotal, fuentemoneda)

                fila += 1

        cont += 1

    hojadestino.write_merge(fila, fila, 0, 7, 'TOTAL GENERAL', fuentenormalnegrell)
    hojadestino.write(fila, 8, totalrubros, fuentemonedaneg)
    print("Total rubros: ", totalrubros)

    libdestino.save(output_folder + "/R2_VENCIMIENTO_MENSUAL_DICIEMBRE_2021.xls")
    print("Archivo creado. . .")


def reporte_pagos_mensuales():
    meses = ["Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio", "Julio", "Agosto", "Septiembre", "Octubre",
             "Noviembre", "Diciembre"]

    anio_actual = "2021"
    mes_actual = "12"
    ultimodia = str(calendar.monthrange(int(anio_actual), int(mes_actual))[1])
    primerdia = "1"

    # Fecha inicio de mes
    iniciomes = datetime.strptime(anio_actual + '-' + mes_actual + '-' + primerdia, '%Y-%m-%d').date()
    # Fecha fin de mes
    finmes = datetime.strptime(anio_actual + '-' + mes_actual + '-' + ultimodia, '%Y-%m-%d').date()
    # Fecha fin de mes anterior
    fechafinmesanterior = iniciomes - relativedelta(days=1)

    fuentenormal = easyxtitulo = easyxf(
        'font: name Times New Roman, color-index black, bold on , height 350; alignment: horiz centre')
    titulo = easyxf(
        'font: name Times New Roman, color-index black, bold on , height 350; alignment: horiz centre')
    titulo2 = easyxf(
        'font: name Times New Roman, color-index black, bold on , height 250; alignment: horiz centre')
    fuentecabecera = easyxf(
        'font: name Verdana, color-index black, bold on, height 150; pattern: pattern solid, fore_colour gray25; alignment: vert distributed, horiz centre; borders: left thin, right thin, top thin, bottom thin')
    fuentenormal = easyxf(
        'font: name Verdana, color-index black, height 150; borders: left thin, right thin, top thin, bottom thin')
    fuentenormalnegrell = easyxf(
        'font: name Verdana, color-index black, bold on , height 150; borders: left thin, right thin, top thin, bottom thin; pattern: pattern solid, fore_colour gray25')
    fuentenormalwrap = easyxf(
        'font: name Verdana, color-index black, height 150; borders: left thin, right thin, top thin, bottom thin')
    fuentenormalwrap.alignment.wrap = True
    fuentenormalcent = easyxf(
        'font: name Verdana, color-index black, height 150; borders: left thin, right thin, top thin, bottom thin; alignment: horiz centre')
    fuentemoneda = easyxf(
        'font: name Verdana, color-index black, height 150; borders: left thin, right thin, top thin, bottom thin; alignment: horiz right',
        num_format_str=' "$" #,##0.00')
    fuentemonedaneg = easyxf(
        'font: name Verdana, color-index black, bold on, height 150; borders: left thin, right thin, top thin, bottom thin; alignment: horiz right; pattern: pattern solid, fore_colour gray25',
        num_format_str=' "$" #,##0.00')
    fuentefecha = easyxf(
        'font: name Verdana, color-index black, height 150; borders: left thin, right thin, top thin, bottom thin; alignment: horiz center',
        num_format_str='yyyy-mm-dd')
    fuentenumerodecimal = easyxf(
        'font: name Verdana, color-index black, height 150; borders: left thin, right thin, top thin, bottom thin; alignment: horiz right',
        num_format_str='#,##0.00')
    fuentenumeroentero = easyxf(
        'font: name Verdana, color-index black, height 150; borders: left thin, right thin, top thin, bottom thin; alignment: horiz right')

    font_style = XFStyle()
    font_style.font.bold = True
    font_style2 = XFStyle()
    font_style2.font.bold = False
    output_folder = os.path.join(os.path.join(SITE_STORAGE, 'media', 'arreglos'))

    libdestino = xlwt.Workbook()
    hojadestino = libdestino.add_sheet("Listado")

    hojadestino.write_merge(0, 0, 0, 8, 'UNIVERSIDAD ESTATAL DE MILAGRO', titulo)
    hojadestino.write_merge(1, 1, 0, 8, 'DIRECCIÓN DE INVESTIGACIÓN Y POSGRADO', titulo2)
    hojadestino.write_merge(2, 2, 0, 8, 'PAGOS MENSUALES DEL MES DE ' + meses[int(mes_actual) - 1].upper() + ' DEL ' + anio_actual, titulo2)

    fila = 4

    columnas = [
        (u"PROGRAMAS", 7000),
        (u"PROG.", 2500),
        (u"COHORTE", 3000),
        (u"FECHA PERIODO INICIAL", 3000),
        (u"FECHA PERIDO FINAL", 3000),
        (u"ESTUDIANTE", 10000),
        (u"IDENTIFICACIÓN", 5000),
        (u"FECHA PAGO", 3000),
        (u"MONTO PAGO", 3500)
    ]

    for col_num in range(len(columnas)):
        hojadestino.write(fila, col_num, columnas[col_num][0], fuentecabecera)
        hojadestino.col(col_num).width = columnas[col_num][1]



    rubros_pagados = Pago.objects.filter(fecha__gte=iniciomes,
                                         fecha__lte=finmes,
                                         status=True,
                                         pagoliquidacion__isnull=True,
                                         rubro__status=True,
                                         rubro__matricula__status=True,
                                         rubro__matricula__nivel__periodo__tipo__id__in=[3, 4]
                                         # rubro__matricula__inscripcion__carrera__id=60,
                                         # rubro__matricula__nivel__periodo__id__in=[12, 13, 78, 84, 91]
                                         # rubro__matricula__inscripcion__persona__cedula='0923002976'
                                         ).exclude(factura__valida=False).distinct().order_by(
        'rubro__matricula__inscripcion__persona__apellido1', 'rubro__matricula__inscripcion__persona__apellido2',
        'rubro__matricula__inscripcion__persona__nombres', 'fecha')

    totalpagos = rubros_pagados.count()
    print(totalpagos)
    totalpagado = 0
    fila = 5
    for pago in rubros_pagados:
        print("Procesando ", fila, " de ", totalpagos)
        matricula = pago.rubro.matricula

        hojadestino.write(fila, 0, matricula.inscripcion.carrera.nombre, fuentenormal)
        hojadestino.write(fila, 1, matricula.inscripcion.carrera.alias, fuentenormalcent)
        hojadestino.write(fila, 2, matricula.nivel.periodo.cohorte, fuentenormalcent)
        hojadestino.write(fila, 3, matricula.nivel.periodo.inicio, fuentefecha)
        hojadestino.write(fila, 4, matricula.nivel.periodo.fin, fuentefecha)
        hojadestino.write(fila, 5, matricula.inscripcion.persona.nombre_completo_inverso(), fuentenormal)
        hojadestino.write(fila, 6, matricula.inscripcion.persona.identificacion(), fuentenormal)
        hojadestino.write(fila, 7, pago.fecha, fuentefecha)
        hojadestino.write(fila, 8, pago.valortotal, fuentemoneda)
        totalpagado += pago.valortotal
        fila += 1

    hojadestino.write_merge(fila, fila, 0, 7, 'TOTAL GENERAL', fuentenormalnegrell)
    hojadestino.write(fila, 8, totalpagado, fuentemonedaneg)

    libdestino.save(output_folder + "/R3_PAGOS_MENSUALES_DICIEMBRE_2021.xls")
    print("Archivo creado. . .")


def reporte_resumenmensual():
    meses = ["Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio", "Julio", "Agosto", "Septiembre", "Octubre",
           "Noviembre", "Diciembre"]

    anio_actual = "2021"
    mes_actual = "12"
    ultimodia = str(calendar.monthrange(int(anio_actual), int(mes_actual))[1])
    primerdia = "1"

    # Fecha inicio de mes
    iniciomes = datetime.strptime(anio_actual + '-' + mes_actual + '-' + primerdia, '%Y-%m-%d').date()
    # Fecha fin de mes
    finmes = datetime.strptime(anio_actual + '-' + mes_actual + '-' + ultimodia, '%Y-%m-%d').date()
    # Fecha fin de mes anterior
    fechafinmesanterior = iniciomes - relativedelta(days=1)



    fuentenormal = easyxtitulo = easyxf(
        'font: name Times New Roman, color-index black, bold on , height 350; alignment: horiz centre')
    titulo = easyxf(
        'font: name Times New Roman, color-index black, bold on , height 350; alignment: horiz centre')
    titulo2 = easyxf(
        'font: name Times New Roman, color-index black, bold on , height 250; alignment: horiz centre')
    fuentecabecera = easyxf(
        'font: name Verdana, color-index black, bold on, height 150; pattern: pattern solid, fore_colour gray25; alignment: vert distributed, horiz centre; borders: left thin, right thin, top thin, bottom thin')
    fuentenormal = easyxf(
        'font: name Verdana, color-index black, height 150; borders: left thin, right thin, top thin, bottom thin')
    fuentenormalneg = easyxf(
        'font: name Verdana, color-index black, bold on , height 150; borders: left thin, right thin, top thin, bottom thin')
    fuentenormalnegrell = easyxf(
        'font: name Verdana, color-index black, bold on , height 150; borders: left thin, right thin, top thin, bottom thin; pattern: pattern solid, fore_colour gray25')
    fuentenormalwrap = easyxf(
        'font: name Verdana, color-index black, height 150; borders: left thin, right thin, top thin, bottom thin')
    fuentenormalwrap.alignment.wrap = True
    fuentenormalcent = easyxf(
        'font: name Verdana, color-index black, height 150; borders: left thin, right thin, top thin, bottom thin; alignment: horiz centre')
    fuentemoneda = easyxf(
        'font: name Verdana, color-index black, height 150; borders: left thin, right thin, top thin, bottom thin; alignment: horiz right',
        num_format_str=' "$" #,##0.00')
    fuentemonedaneg = easyxf(
        'font: name Verdana, color-index black, bold on, height 150; borders: left thin, right thin, top thin, bottom thin; alignment: horiz right; pattern: pattern solid, fore_colour gray25',
        num_format_str=' "$" #,##0.00')
    fuentefecha = easyxf(
        'font: name Verdana, color-index black, height 150; borders: left thin, right thin, top thin, bottom thin; alignment: horiz center',
        num_format_str='yyyy-mm-dd')
    fuentenumerodecimal = easyxf(
        'font: name Verdana, color-index black, height 150; borders: left thin, right thin, top thin, bottom thin; alignment: horiz right',
        num_format_str='#,##0.00')
    fuentenumeroentero = easyxf(
        'font: name Verdana, color-index black, height 150; borders: left thin, right thin, top thin, bottom thin; alignment: horiz right')

    font_style = XFStyle()
    font_style.font.bold = True
    font_style2 = XFStyle()
    font_style2.font.bold = False
    output_folder = os.path.join(os.path.join(SITE_STORAGE, 'media', 'arreglos'))

    libdestino = xlwt.Workbook()
    hojadestino = libdestino.add_sheet("Listado")

    hojadestino.write_merge(0, 0, 0, 6, 'UNIVERSIDAD ESTATAL DE MILAGRO', titulo)
    hojadestino.write_merge(1, 1, 0, 6, 'DIRECCIÓN DE INVESTIGACIÓN Y POSGRADO', titulo2)
    hojadestino.write_merge(2, 2, 0, 6, 'RESUMEN MENSUAL DE MOVIMIENTOS DEL MES DE '+meses[int(mes_actual)-1].upper()+ ' DEL '+anio_actual, titulo2)


    fila = 4
    fechafinant = str(fechafinmesanterior.day)+"-"+meses[fechafinmesanterior.month-1][:3].upper()+"-"+str(fechafinmesanterior.year)
    fechafinact = str(finmes.day)+"-"+meses[finmes.month-1][:3].upper()+"-"+str(finmes.year)

    # print(fechafinant)
    # print(fechafinact)

    columnas = [
        (u"PROGRAMAS", 15000),
        (u"PROG.", 2500),
        (u"COHORTE", 3000),
        (u"SALDO INICIAL AL "+fechafinant, 4000),
        (u"VENCIMIENTOS DEL MES", 4000),
        (u"PAGOS DEL MES", 4000),
        (u"SALDO FINAL AL "+fechafinact, 4000)
    ]

    for col_num in range(len(columnas)):
        hojadestino.write(fila, col_num, columnas[col_num][0], fuentecabecera)
        hojadestino.col(col_num).width = columnas[col_num][1]


    programas_maestria = Matricula.objects.values('inscripcion__carrera__id').filter(status=True,
                                                  # inscripcion__carrera__id=60,
                                                  # nivel__periodo__id__in=[12, 13, 78, 84, 91],
                                                  nivel__periodo__tipo__id__in=[3, 4]).annotate(carrera=F('inscripcion__carrera__nombre'),
                                                                                                carreraalias=F('inscripcion__carrera__alias'),
                                                                                                carreraid=F('inscripcion__carrera__id'),
                                                                                                periodo=F('nivel__periodo__nombre'),
                                                                                                periodoid=F('nivel__periodo__id'),
                                                                                                cohorte=F('nivel__periodo__cohorte')
                                                                                                ).distinct().order_by('carrera', 'cohorte')

    # print(programas_maestria)
    totalrubrosanterior = 0
    totalliquidado = 0
    totalanulado = 0
    totalpagosanterior = 0

    totalsaldosinicial = 0
    totalvencimientosmes = 0
    totalpagosmes = 0
    totalsaldosfinal = 0

    vencimientosmes = 0
    pagosmes = 0
    idcarrera = 0
    carrera = ""
    print("PROGRAMA======COHORTE------SALDO AL " + str(
        fechafinmesanterior) + "----VENCIMIENTOS MES-----PAGOS DEL MES------SALDO FINAL AL " + str(finmes))
    totalsaldoinicialprog = 0
    totalvencimientomesprog = 0
    totalpagomesprog = 0
    totalsaldofinalprog = 0

    fila = 5

    # for programa in programas_maestria:
    #     print(programa)
    #
    # return

    for programa in programas_maestria:
        print(programa)
        if not idcarrera:
            idcarrera = programa['carreraid']
            carrera = programa['carrera']

        if idcarrera != programa['carreraid']:
            if totalsaldoinicialprog != 0 or totalvencimientomesprog != 0 or totalpagomesprog != 0:
                # fila += 1
                hojadestino.write(fila, 0, "TOTAL " + carrera, fuentenormalnegrell)
                hojadestino.write(fila, 1, "", fuentenormalnegrell)
                hojadestino.write(fila, 2, "", fuentenormalnegrell)
                hojadestino.write(fila, 3, totalsaldoinicialprog, fuentemonedaneg)
                hojadestino.write(fila, 4, totalvencimientomesprog, fuentemonedaneg)
                hojadestino.write(fila, 5, totalpagomesprog, fuentemonedaneg)
                hojadestino.write(fila, 6, totalsaldofinalprog, fuentemonedaneg)
                fila += 1

                print("TOTAL PROGRAMA: ", totalsaldoinicialprog, "-", totalvencimientomesprog, "-", totalpagomesprog, "-", totalsaldofinalprog)
                print("=============================================================")

            idcarrera = programa['carreraid']
            carrera = programa['carrera']
            totalsaldoinicialprog = 0
            totalvencimientomesprog = 0
            totalpagomesprog = 0
            totalsaldofinalprog = 0

        # print(programa['carrera'] + "-" + programa['carreraalias'] + " " +str(programa['cohorte']) + " COHORTE")

        totalrubrosanterior = Decimal(null_to_decimal(Rubro.objects.filter(status=True,
                                                           fechavence__lt=iniciomes,
                                                           matricula__inscripcion__carrera__id=programa['carreraid'],
                                                           matricula__nivel__periodo__id=programa['periodoid']
                                                           ).aggregate(
            valor=Sum('valortotal'))['valor'], 2)).quantize(Decimal('.01'))



        totalliquidadoanterior = Decimal(null_to_decimal(Rubro.objects.filter(status=True,
                                                                           fechavence__lt=iniciomes,
                                                                           matricula__inscripcion__carrera__id=programa['carreraid'],
                                                                           matricula__nivel__periodo__id=programa['periodoid'],
                                                                      pago__pagoliquidacion__isnull=False
                                                                           ).aggregate(
            valor=Sum('valortotal'))['valor'], 2)).quantize(Decimal('.01'))

        totalanuladoanterior = Decimal(null_to_decimal(Pago.objects.filter(
            status=True,
            rubro__matricula__inscripcion__carrera__id=programa['carreraid'],
            rubro__matricula__nivel__periodo__id=programa['periodoid'],
            rubro__status=True,
            rubro__fechavence__lte=finmes,
            factura__valida=False,
            factura__status=True
        ).aggregate(pagos=Sum('valortotal'))['pagos'], 2)).quantize(Decimal('.01'))

        totalpagosanterior = Decimal(null_to_decimal(Pago.objects.filter(
            fecha__lt=iniciomes,
            pagoliquidacion__isnull=True,
            status=True,
            rubro__matricula__inscripcion__carrera__id=programa['carreraid'],
            rubro__matricula__nivel__periodo__id=programa['periodoid'],
            rubro__status=True
            # rubro__fechavence__lte=finmes
        ).exclude(factura__valida=False).aggregate(pagos=Sum('valortotal'))['pagos'], 2)).quantize(Decimal('.01'))

        totalvencimientosposterior = Decimal(null_to_decimal(Pago.objects.filter(
            # rubro__matricula__inscripcion__persona__cedula__in=cedulas,
            fecha__lt=iniciomes,
            pagoliquidacion__isnull=True,
            status=True,
            rubro__matricula__inscripcion__carrera__id=programa['carreraid'],
            rubro__matricula__nivel__periodo__id=programa['periodoid'],
            # rubro__matricula__inscripcion__carrera__id=carrera,
            # rubro__matricula__nivel__periodo__id__in=periodos,
            rubro__status=True,
            rubro__fechavence__gte=iniciomes
        ).exclude(factura__valida=False).aggregate(pagos=Sum('valortotal'))['pagos'], 2)).quantize(Decimal('.01'))


        vencimientosmes = Decimal(null_to_decimal(Rubro.objects.filter(status=True,
                                               fechavence__gte=iniciomes,
                                               fechavence__lte=finmes,
                                               matricula__inscripcion__carrera__id=programa['carreraid'],
                                               matricula__nivel__periodo__id=programa['periodoid']
                                               ).aggregate(
            valor=Sum('valortotal'))['valor'], 2)).quantize(Decimal('.01'))

        totalvencimientos2 = Decimal(null_to_decimal(Pago.objects.filter(
            # rubro__matricula__inscripcion__persona__cedula__in=cedulas,
            fecha__lt=iniciomes,
            pagoliquidacion__isnull=True,
            status=True,
            rubro__matricula__nivel__periodo__tipo__id__in=[3, 4],
            rubro__matricula__inscripcion__carrera__id=programa['carreraid'],
            rubro__matricula__nivel__periodo__id=programa['periodoid'],
            # rubro__matricula__inscripcion__carrera__id=carrera,
            # rubro__matricula__nivel__periodo__id__in=periodos,
            rubro__status=True,
            rubro__fechavence__gte=iniciomes,
            rubro__fechavence__lte=finmes
        ).exclude(factura__valida=False).aggregate(pagos=Sum('valortotal'))['pagos'], 2)).quantize(Decimal('.01'))

        # Pagos del mes que corresponden a rubros de meses posteriores
        totalvencimientos3 = Decimal(null_to_decimal(Pago.objects.filter(
            # rubro__matricula__inscripcion__persona__cedula__in=cedulas,
            fecha__gte=iniciomes,
            fecha__lte=finmes,
            pagoliquidacion__isnull=True,
            status=True,
            rubro__matricula__nivel__periodo__tipo__id__in=[3, 4],
            rubro__matricula__inscripcion__carrera__id=programa['carreraid'],
            rubro__matricula__nivel__periodo__id=programa['periodoid'],
            # rubro__matricula__inscripcion__carrera__id=carrera,
            # rubro__matricula__nivel__periodo__id__in=periodos,
            rubro__status=True,
            rubro__fechavence__gt=finmes
        ).exclude(factura__valida=False).aggregate(pagos=Sum('valortotal'))['pagos'], 2)).quantize(Decimal('.01'))

        vencimientosmes = (vencimientosmes - totalvencimientos2) + totalvencimientos3

        pagosmes = Decimal(null_to_decimal(Pago.objects.filter(fecha__gte=iniciomes, fecha__lte=finmes,
                                    pagoliquidacion__isnull=True,
                                    status=True,
                                    rubro__matricula__inscripcion__carrera__id=programa['carreraid'],
                                    rubro__matricula__nivel__periodo__id=programa['periodoid'],
                                    rubro__status=True
                                    ).exclude(factura__valida=False).aggregate(pagos=Sum('valortotal'))['pagos'], 2)).quantize(Decimal('.01'))

        saldoanterior = totalrubrosanterior - (totalpagosanterior + totalliquidadoanterior + totalanuladoanterior)
        saldoanterior += totalvencimientosposterior


        saldofinal = (saldoanterior + vencimientosmes) - pagosmes
        # print(saldoanterior)

        if saldoanterior == 0 and vencimientosmes == 0 and pagosmes == 0:
            continue

        totalsaldosinicial += saldoanterior
        totalvencimientosmes += vencimientosmes
        totalpagosmes += pagosmes
        totalsaldosfinal += saldofinal

        totalsaldoinicialprog += saldoanterior
        totalvencimientomesprog += vencimientosmes
        totalpagomesprog += pagosmes
        totalsaldofinalprog += saldofinal

        hojadestino.write(fila, 0, programa['carrera'], fuentenormal)
        hojadestino.write(fila, 1, programa['carreraalias'], fuentenormalcent)
        hojadestino.write(fila, 2, programa['cohorte'], fuentenormalcent)
        hojadestino.write(fila, 3, saldoanterior, fuentemoneda)
        hojadestino.write(fila, 4, vencimientosmes, fuentemoneda)
        print("Pagos del mes: ", pagosmes)
        hojadestino.write(fila, 5, pagosmes, fuentemoneda)
        hojadestino.write(fila, 6, saldofinal, fuentemoneda)

        fila += 1

        print(programa['carrera']+"-2222", "-", programa['cohorte'], "-$ ", saldoanterior, "- $ ", vencimientosmes, "- $ ", pagosmes, "- $", saldofinal)

    if totalsaldoinicialprog != 0 or totalvencimientomesprog != 0 or totalpagomesprog != 0:
        hojadestino.write(fila, 0, "TOTAL " + programa['carrera'], fuentenormalnegrell)
        hojadestino.write(fila, 1, "", fuentenormalnegrell)
        hojadestino.write(fila, 2, "", fuentenormalnegrell)
        hojadestino.write(fila, 3, totalsaldoinicialprog, fuentemonedaneg)
        hojadestino.write(fila, 4, totalvencimientomesprog, fuentemonedaneg)
        hojadestino.write(fila, 5, totalpagomesprog, fuentemonedaneg)
        hojadestino.write(fila, 6, totalsaldofinalprog, fuentemonedaneg)
        fila += 1

    hojadestino.write(fila, 0, "TOTAL GENERAL", fuentenormalnegrell)
    hojadestino.write(fila, 1, "", fuentenormalnegrell)
    hojadestino.write(fila, 2, "", fuentenormalnegrell)
    hojadestino.write(fila, 3, totalsaldosinicial, fuentemonedaneg)
    hojadestino.write(fila, 4, totalvencimientosmes, fuentemonedaneg)
    hojadestino.write(fila, 5, totalpagosmes, fuentemonedaneg)
    hojadestino.write(fila, 6, totalsaldosfinal, fuentemonedaneg)

    print("TOTAL GENERAL===================================")
    print(totalsaldosinicial, "-", totalvencimientosmes, "-", totalpagosmes, "-", totalsaldosfinal)

    libdestino.save(output_folder + "/R4_RESUMEN_MENSUAL_DICIEMBRE_2021.xls")
    print("Archivo creado. . .")


def reporte_edad_cartera_vencida():
    meses = ["Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio", "Julio", "Agosto", "Septiembre", "Octubre",
             "Noviembre", "Diciembre"]

    # En el combo debo seleccionar AÑO Y MES
    anio_actual = "2021"
    mes_actual = "12"
    ultimodia = str(calendar.monthrange(int(anio_actual), int(mes_actual))[1])
    primerdia = "1"

    # Fecha inicio de mes
    iniciomes = datetime.strptime(anio_actual + '-' + mes_actual + '-' + primerdia, '%Y-%m-%d').date()
    # Fecha fin de mes
    finmes = datetime.strptime(anio_actual + '-' + mes_actual + '-' + ultimodia, '%Y-%m-%d').date()
    # Fecha fin de mes anterior
    fechafinmesanterior = iniciomes - relativedelta(days=1)

    fuentenormal = easyxtitulo = easyxf(
        'font: name Times New Roman, color-index black, bold on , height 350; alignment: horiz centre')
    titulo = easyxf(
        'font: name Times New Roman, color-index black, bold on , height 350; alignment: horiz centre')
    titulo2 = easyxf(
        'font: name Times New Roman, color-index black, bold on , height 250; alignment: horiz centre')
    fuentecabecera = easyxf(
        'font: name Verdana, color-index black, bold on, height 150; pattern: pattern solid, fore_colour gray25; alignment: vert distributed, horiz centre; borders: left thin, right thin, top thin, bottom thin')
    fuentenormal = easyxf(
        'font: name Verdana, color-index black, height 150; borders: left thin, right thin, top thin, bottom thin')
    fuentenormalwrap = easyxf(
        'font: name Verdana, color-index black, height 150; borders: left thin, right thin, top thin, bottom thin')
    fuentenormalneg = easyxf(
        'font: name Verdana, color-index black, bold on , height 150; borders: left thin, right thin, top thin, bottom thin')
    fuentenormalnegrell = easyxf(
        'font: name Verdana, color-index black, bold on , height 150; borders: left thin, right thin, top thin, bottom thin; pattern: pattern solid, fore_colour gray25')
    fuentenormalwrap.alignment.wrap = True
    fuentenormalcent = easyxf(
        'font: name Verdana, color-index black, height 150; borders: left thin, right thin, top thin, bottom thin; alignment: horiz centre')
    fuentemoneda = easyxf(
        'font: name Verdana, color-index black, height 150; borders: left thin, right thin, top thin, bottom thin; alignment: horiz right',
        num_format_str=' "$" #,##0.00')
    fuentemonedaneg = easyxf(
        'font: name Verdana, color-index black, bold on, height 150; borders: left thin, right thin, top thin, bottom thin; alignment: horiz right; pattern: pattern solid, fore_colour gray25',
        num_format_str=' "$" #,##0.00')
    fuentefecha = easyxf(
        'font: name Verdana, color-index black, height 150; borders: left thin, right thin, top thin, bottom thin; alignment: horiz center',
        num_format_str='yyyy-mm-dd')
    fuentenumerodecimal = easyxf(
        'font: name Verdana, color-index black, height 150; borders: left thin, right thin, top thin, bottom thin; alignment: horiz right',
        num_format_str='#,##0.00')
    fuentenumeroentero = easyxf(
        'font: name Verdana, color-index black, height 150; borders: left thin, right thin, top thin, bottom thin; alignment: horiz right')
    fuenteporcentaje = easyxf(
        'font: name Verdana, color-index black, height 150; borders: left thin, right thin, top thin, bottom thin; alignment: horiz right',
        num_format_str='0%')
    fuenteporcentajeneg = easyxf(
        'font: name Verdana, color-index black, bold on, height 150; borders: left thin, right thin, top thin, bottom thin; alignment: horiz right; pattern: pattern solid, fore_colour gray25',
        num_format_str='0.00%')


    font_style = XFStyle()
    font_style.font.bold = True
    font_style2 = XFStyle()
    font_style2.font.bold = False
    output_folder = os.path.join(os.path.join(SITE_STORAGE, 'media', 'arreglos'))

    libdestino = xlwt.Workbook()
    hojadestino = libdestino.add_sheet("Listado")

    hojadestino.write_merge(0, 0, 0, 14, 'UNIVERSIDAD ESTATAL DE MILAGRO', titulo)
    hojadestino.write_merge(1, 1, 0, 14, 'DIRECCIÓN DE INVESTIGACIÓN Y POSGRADO', titulo2)
    hojadestino.write_merge(2, 2, 0, 14, 'EDAD DE LA CARTERA VENCIDA DEL MES DE ' + meses[
        int(mes_actual) - 1].upper() + ' DEL ' + anio_actual, titulo2)

    fila = 4
    fechafinant = str(fechafinmesanterior.day) + "-" + meses[fechafinmesanterior.month - 1][:3].upper() + "-" + str(
        fechafinmesanterior.year)
    fechafinact = str(finmes.day) + "-" + meses[finmes.month - 1][:3].upper() + "-" + str(finmes.year)

    hojadestino.row(fila).height_mismatch = True
    hojadestino.row(fila).height = 400
    hojadestino.row(fila+1).height_mismatch = True
    hojadestino.row(fila + 1).height = 400

    columnas = [
        (u"PROGRAMAS", 8000),
        (u"PROG.", 2500),
        (u"COHORTE", 2500),
        (u"FECHA PERIODO INICIAL", 3000),
        (u"FECHA PERIDO FINAL", 3000),
        (u"ESTUDIANTE", 10000),
        (u"IDENTIFICACIÓN", 3900),
        (u"VALOR TOTAL PROGRAMA", 4000),
        (u"VALOR COBRADO A LA FECHA", 4000),
        (u"SALDO VENCIDO AL " + fechafinant, 4000)
    ]

    for col_num in range(len(columnas)):
        hojadestino.write_merge(fila, fila + 1, col_num, col_num, columnas[col_num][0], fuentecabecera)
        # hojadestino.write(fila, col_num, columnas[col_num][0], fuentecabecera)
        hojadestino.col(col_num).width = columnas[col_num][1]

    hojadestino.write_merge(fila, fila, 10, 13, "EDAD DE LA CARTERA VENCIDA", fuentecabecera)
    hojadestino.write(fila+1, 10, "1 - 30", fuentecabecera)
    hojadestino.col(10).width = 4000
    hojadestino.write(fila + 1, 11, "31 - 60", fuentecabecera)
    hojadestino.col(11).width = 4000
    hojadestino.write(fila + 1, 12, "61 - 90", fuentecabecera)
    hojadestino.col(12).width = 4000
    hojadestino.write(fila + 1, 13, "+ 90", fuentecabecera)
    hojadestino.col(13).width = 4000
    hojadestino.write_merge(fila, fila + 1, 14, 14,"SALDO POR VENCER AL "+ fechafinact , fuentecabecera)
    hojadestino.col(14).width = 4000


    # periodos = Periodo.objects.values('id').filter(nivel__matricula__rubro__saldo__gt=0, nivel__matricula__rubro__fechavence__lt=datetime.now().date(), tipo__id__in=[3, 4]).distinct().order_by('id')
    # matriculas = Matricula.objects.filter(nivel__periodo__tipo__id__in=[3, 4], inscripcion__persona__cedula='0926476813').order_by('inscripcion__persona__apellido1', 'inscripcion__persona__apellido2', 'inscripcion__persona__nombres')

    # print("Ultimo dia mes anterior: ", fechafinmesanterior)
    # print("Primer dia mes actual: ", iniciomes, " Ultimo día mes actual: ", finmes)

    matriculas = Matricula.objects.filter(status=True, nivel__periodo__tipo__id__in=[3, 4]
                                          # inscripcion__persona__cedula='1207208016'
                                          # inscripcion__carrera__id=60,
                                          # nivel__periodo__id__in=[12, 13, 78, 84, 91]
                                          ).distinct().order_by('inscripcion__persona__apellido1',
                                                                'inscripcion__persona__apellido2',
                                                                'inscripcion__persona__nombres')

    # matriculas = Matricula.objects.filter(status=True, nivel__periodo__tipo__id__in=[3, 4]).distinct().order_by(
    #     'inscripcion__persona__apellido1', 'inscripcion__persona__apellido2', 'inscripcion__persona__nombres')

    totalmatriculas = matriculas.count()

    # print(totalmatriculas)
    c = 0

    horainicio = datetime.now()

    totalalumnos = 0

    totalsaldoinicial = 0
    totalrubros = 0
    totalpagado = 0
    totalsaldofinal = 0

    fila = 6
    cedula = ''

    totalprograma = 0
    totalcobrado = 0
    totalsaldovencido = 0
    totaledad1 = 0
    totaledad2 = 0
    totaledad3 = 0
    totaledad4 = 0
    totalsaldovencer = 0

    for matricula in matriculas:
        c += 1
        print("Procesando ", c, " de ", totalmatriculas)

        periodo = matricula.nivel.periodo
        costoprograma = Decimal(null_to_decimal(periodo.periodocarreracosto_set.filter(carrera=matricula.inscripcion.carrera, status=True).aggregate(costo=Sum('costo'))['costo'] ) ).quantize(Decimal('.01'))
        valordescontado = 0

        if matricula.matriculanovedad_set.filter(tipo=1).exists():
            novedad = matricula.matriculanovedad_set.filter(tipo=1)[0]
            motivo = '%s' % novedad.motivo
            porcentaje = Decimal(novedad.porcentajedescuento).quantize(Decimal('.01')) if novedad.porcentajedescuento else 0
            if porcentaje > 0:
                valordescontado = Decimal(null_to_decimal((costoprograma * porcentaje) / 100, 2)).quantize(
                    Decimal('.01'))

        valortotalprograma = costoprograma - valordescontado
        # SALDO ANTERIOR
        totalrubrosanterior = Decimal(null_to_decimal(matricula.rubro_set.filter(status=True,
                                                                                 fechavence__lt=iniciomes
                                                                                 ).aggregate(valor=Sum('valortotal'))[
                                                          'valor'], 2)).quantize(Decimal('.01'))
        print("Total rubros anterior:", totalrubrosanterior)

        totalliquidado = Decimal(null_to_decimal(matricula.rubro_set.filter(status=True,
                                                                            fechavence__lt=iniciomes,
                                                                            pago__pagoliquidacion__isnull=False
                                                                            ).aggregate(valor=Sum('valortotal'))[
                                                     'valor'], 2)).quantize(Decimal('.01'))

        print("Total Liquidado ", totalliquidado)

        totalanulado = Decimal(null_to_decimal(Pago.objects.filter(
            status=True,
            rubro__matricula=matricula,
            rubro__status=True,
            rubro__fechavence__lte=finmes,
            factura__valida=False,
            factura__status=True
        ).aggregate(pagos=Sum('valortotal'))['pagos'], 2)).quantize(Decimal('.01'))

        print("total anulado: ", totalanulado)

        # PAGADO ANTERIOR ---- REVISAR BIEN ESTA TOMANDO PAGO DE RUBROS DE JULIO, AGOSTO
        totalpagosanterior = Decimal(null_to_decimal(Pago.objects.filter(
            fecha__lt=iniciomes,
            pagoliquidacion__isnull=True,
            status=True,
            rubro__matricula=matricula,
            rubro__status=True
            # rubro__fechavence__lte=finmes
        ).exclude(factura__valida=False).aggregate(pagos=Sum('valortotal'))['pagos'], 2)).quantize(Decimal('.01'))
        print("Total Pagado anterior: ", totalpagosanterior)

        totalvencimientosposterior = Decimal(null_to_decimal(Pago.objects.filter(
            # rubro__matricula__inscripcion__persona__cedula__in=cedulas,
            fecha__lt=iniciomes,
            pagoliquidacion__isnull=True,
            status=True,
            rubro__matricula__nivel__periodo__tipo__id__in=[3, 4],
            rubro__matricula=matricula,
            # rubro__matricula__inscripcion__carrera__id=carrera,
            # rubro__matricula__nivel__periodo__id__in=periodos,
            rubro__status=True,
            rubro__fechavence__gte=iniciomes
        ).exclude(factura__valida=False).aggregate(pagos=Sum('valortotal'))['pagos'], 2)).quantize(Decimal('.01'))

        saldoanterior = totalrubrosanterior - (totalpagosanterior + totalliquidado + totalanulado)
        saldoanterior += totalvencimientosposterior

        print("Saldo anterior: ", saldoanterior)

        if saldoanterior != 0:
            totalprograma += valortotalprograma
            totalcobrado += totalpagosanterior
            totalsaldovencido += saldoanterior

            valoredad1 = 0
            valoredad2 = 0
            valoredad3 = 0
            valoredad4 = 0

            hojadestino.write(fila, 0, matricula.inscripcion.carrera.nombre, fuentenormal)
            hojadestino.write(fila, 1, matricula.inscripcion.carrera.alias, fuentenormalcent)
            hojadestino.write(fila, 2, matricula.nivel.periodo.cohorte, fuentenormalcent)
            hojadestino.write(fila, 3, matricula.nivel.periodo.inicio, fuentefecha)
            hojadestino.write(fila, 4, matricula.nivel.periodo.fin, fuentefecha)
            hojadestino.write(fila, 5, matricula.inscripcion.persona.nombre_completo_inverso(), fuentenormal)
            hojadestino.write(fila, 6, matricula.inscripcion.persona.identificacion(), fuentenormal)
            hojadestino.write(fila, 7, valortotalprograma, fuentemoneda)
            hojadestino.write(fila, 8, totalpagosanterior, fuentemoneda)
            hojadestino.write(fila, 9, saldoanterior, fuentemoneda)

            # ===== SALDOS 1-30, 31-60, 61-90, + 90 DIAS
            fechafincartera = fechafinmesanterior
            fechainiciocartera = datetime.strptime(str(fechafincartera.year) + '-' + str(fechafincartera.month) + '-' + primerdia, '%Y-%m-%d').date()

            columna = 10

            for n in range(1, 4):

                totalrubroscartera = Decimal(null_to_decimal(matricula.rubro_set.filter(status=True,
                                                                                         fechavence__gte=fechainiciocartera,
                                                                                         fechavence__lte=fechafincartera
                                                                                         ).aggregate(valor=Sum('valortotal'))[
                                                                  'valor'], 2)).quantize(Decimal('.01'))
                print("Total rubros anterior:", totalrubrosanterior)

                totalliquidadocartera = Decimal(null_to_decimal(matricula.rubro_set.filter(status=True,
                                                                                    fechavence__gte=fechainiciocartera,
                                                                                    fechavence__lte=fechafincartera,
                                                                                    pago__pagoliquidacion__isnull=False
                                                                                    ).aggregate(valor=Sum('valortotal'))[
                                                             'valor'], 2)).quantize(Decimal('.01'))

                print("Total Liquidado ", totalliquidado)

                totalanuladocartera = Decimal(null_to_decimal(Pago.objects.filter(
                    status=True,
                    rubro__matricula=matricula,
                    rubro__status=True,
                    rubro__fechavence__gte=fechainiciocartera,
                    rubro__fechavence__lte=fechafincartera,
                    factura__valida=False,
                    factura__status=True
                ).aggregate(pagos=Sum('valortotal'))['pagos'], 2)).quantize(Decimal('.01'))

                print("total anulado: ", totalanulado)

                # PAGADO ANTERIOR ---- REVISAR BIEN ESTA TOMANDO PAGO DE RUBROS DE JULIO, AGOSTO
                totalpagoscartera = Decimal(null_to_decimal(Pago.objects.filter(
                    fecha__lt=iniciomes,
                    pagoliquidacion__isnull=True,
                    status=True,
                    rubro__matricula=matricula,
                    rubro__status=True,
                    rubro__fechavence__gte=fechainiciocartera,
                    rubro__fechavence__lte=fechafincartera
                ).exclude(factura__valida=False).aggregate(pagos=Sum('valortotal'))['pagos'], 2)).quantize(Decimal('.01'))
                print("Total Pagado anterior: ", totalpagosanterior)
                saldoanteriorcartera = totalrubroscartera - (totalpagoscartera + totalliquidadocartera + totalanuladocartera)
                print("Saldo anterior 1-30 días:", saldoanteriorcartera)

                hojadestino.write(fila, columna, saldoanteriorcartera, fuentemoneda)

                if n == 1:
                    totaledad1 += saldoanteriorcartera
                    valoredad1 = saldoanteriorcartera
                elif n == 2:
                    totaledad2 += saldoanteriorcartera
                    valoredad2 = saldoanteriorcartera
                else:
                    totaledad3 += saldoanteriorcartera
                    valoredad3 = saldoanteriorcartera

                columna += 1

                fechafincartera = fechainiciocartera - relativedelta(days=1)
                fechainiciocartera = datetime.strptime(str(fechafincartera.year) + '-' + str(fechafincartera.month) + '-' + primerdia, '%Y-%m-%d').date()


            fechainiciocartera = fechafincartera + relativedelta(days=1)
            print("Fecha inicio de cartera:", fechainiciocartera)
            totalrubroscartera = Decimal(null_to_decimal(matricula.rubro_set.filter(status=True,
                                                                                     fechavence__lt=fechainiciocartera
                                                                                     ).aggregate(valor=Sum('valortotal'))[
                                                              'valor'], 2)).quantize(Decimal('.01'))
            print("Total rubros anterior:", totalrubroscartera)

            totalliquidadocartera = Decimal(null_to_decimal(matricula.rubro_set.filter(status=True,
                                                                                fechavence__lt=fechainiciocartera,
                                                                                pago__pagoliquidacion__isnull=False
                                                                                ).aggregate(valor=Sum('valortotal'))[
                                                         'valor'], 2)).quantize(Decimal('.01'))

            print("Total Liquidado ", totalliquidadocartera)

            totalanuladocartera = Decimal(null_to_decimal(Pago.objects.filter(
                status=True,
                rubro__matricula=matricula,
                rubro__status=True,
                rubro__fechavence__lt=fechainiciocartera,
                factura__valida=False,
                factura__status=True
            ).aggregate(pagos=Sum('valortotal'))['pagos'], 2)).quantize(Decimal('.01'))

            print("total anulado: ", totalanuladocartera)

            # PAGADO ANTERIOR ---- REVISAR BIEN ESTA TOMANDO PAGO DE RUBROS DE JULIO, AGOSTO
            totalpagoscartera = Decimal(null_to_decimal(Pago.objects.filter(
                fecha__lt=iniciomes,
                pagoliquidacion__isnull=True,
                status=True,
                rubro__matricula=matricula,
                rubro__status=True,
                rubro__fechavence__lt=fechainiciocartera
            ).exclude(factura__valida=False).aggregate(pagos=Sum('valortotal'))['pagos'], 2)).quantize(Decimal('.01'))
            print("Total Pagado anterior: ", totalpagoscartera)

            # saldoanteriorcartera = totalrubroscartera - (totalpagoscartera + totalliquidadocartera + totalanuladocartera)
            aux = totalrubroscartera - (totalpagoscartera + totalliquidadocartera + totalanuladocartera)
            saldoanteriorcartera = saldoanterior - (valoredad1 + valoredad2 + valoredad3)

            saldovencer = valortotalprograma - totalpagosanterior - saldoanterior
            print("Saldo anterior mayor a 90 días:", saldoanteriorcartera)
            hojadestino.write(fila, columna, saldoanteriorcartera, fuentemoneda)
            hojadestino.write(fila, columna + 1, saldovencer, fuentemoneda)

            totaledad4 += saldoanteriorcartera
            totalsaldovencer += saldovencer

            fila += 1

    hojadestino.write_merge(fila, fila, 0, 6, "TOTAL GENERAL", fuentenormalnegrell)
    hojadestino.write(fila, 7, totalprograma, fuentemonedaneg)
    hojadestino.write(fila, 8, totalcobrado, fuentemonedaneg)
    hojadestino.write(fila, 9, totalsaldovencido, fuentemonedaneg)
    hojadestino.write(fila, 10, totaledad1, fuentemonedaneg)
    hojadestino.write(fila, 11, totaledad2, fuentemonedaneg)
    hojadestino.write(fila, 12, totaledad3, fuentemonedaneg)
    hojadestino.write(fila, 13, totaledad4, fuentemonedaneg)
    hojadestino.write(fila, 14, totalsaldovencer, fuentemonedaneg)

    fila += 1
    hojadestino.write(fila, 9, 1, fuenteporcentajeneg)
    hojadestino.write(fila, 10, totaledad1 / totalsaldovencido, fuenteporcentajeneg)
    hojadestino.write(fila, 11, totaledad2 / totalsaldovencido, fuenteporcentajeneg)
    hojadestino.write(fila, 12, totaledad3 / totalsaldovencido, fuenteporcentajeneg)
    hojadestino.write(fila, 13, totaledad4 / totalsaldovencido, fuenteporcentajeneg)


    print("Total alumnos para el reporte: ", totalalumnos)
    print("Total saldo anterior: ", totalsaldoinicial)
    print("Total rubros del mes: ", totalrubros)
    print("Total pagado del mes: ", totalpagado)
    print("Total saldo actual: ", totalsaldofinal)

    print("Inicio: ", horainicio)
    print("Fin: ", datetime.now())

    libdestino.save(output_folder + "/R5_EDAD_CARTERA_VENCIDA_DICIEMBRE_2021.xls")
    print("Archivo creado. . .")


def reporte_proyeccion_cobros_posgrado():
    meses = ["Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio", "Julio", "Agosto", "Septiembre", "Octubre",
             "Noviembre", "Diciembre"]

    # En el combo debo seleccionar AÑO Y MES
    anio_actual = "2021"
    mes_actual = "12"
    ultimodia = str(calendar.monthrange(int(anio_actual), int(mes_actual))[1])
    primerdia = "1"

    # Fecha inicio de mes
    iniciomes = datetime.strptime(anio_actual + '-' + mes_actual + '-' + primerdia, '%Y-%m-%d').date()
    # Fecha fin de mes
    finmes = datetime.strptime(anio_actual + '-' + mes_actual + '-' + ultimodia, '%Y-%m-%d').date()
    # Fecha fin de mes anterior
    fechafinmesanterior = iniciomes - relativedelta(days=1)

    fuentenormal = easyxtitulo = easyxf(
        'font: name Times New Roman, color-index black, bold on , height 350; alignment: horiz centre')
    titulo = easyxf(
        'font: name Times New Roman, color-index black, bold on , height 350; alignment: horiz centre')
    titulo2 = easyxf(
        'font: name Times New Roman, color-index black, bold on , height 250; alignment: horiz centre')
    fuentecabecera = easyxf(
        'font: name Verdana, color-index black, bold on, height 150; pattern: pattern solid, fore_colour gray25; alignment: vert distributed, horiz centre; borders: left thin, right thin, top thin, bottom thin')
    fuentenormal = easyxf(
        'font: name Verdana, color-index black, height 150; borders: left thin, right thin, top thin, bottom thin')
    fuentenormalwrap = easyxf(
        'font: name Verdana, color-index black, height 150; borders: left thin, right thin, top thin, bottom thin')
    fuentenormalneg = easyxf(
        'font: name Verdana, color-index black, bold on , height 150; borders: left thin, right thin, top thin, bottom thin')
    fuentenormalnegrell = easyxf(
        'font: name Verdana, color-index black, bold on , height 150; borders: left thin, right thin, top thin, bottom thin; pattern: pattern solid, fore_colour gray25')
    fuentenormalwrap.alignment.wrap = True
    fuentenormalcent = easyxf(
        'font: name Verdana, color-index black, height 150; borders: left thin, right thin, top thin, bottom thin; alignment: horiz centre')
    fuentemoneda = easyxf(
        'font: name Verdana, color-index black, height 150; borders: left thin, right thin, top thin, bottom thin; alignment: horiz right',
        num_format_str=' "$" #,##0.00')
    fuentemonedaneg = easyxf(
        'font: name Verdana, color-index black, bold on, height 150; borders: left thin, right thin, top thin, bottom thin; alignment: horiz right; pattern: pattern solid, fore_colour gray25',
        num_format_str=' "$" #,##0.00')
    fuentefecha = easyxf(
        'font: name Verdana, color-index black, height 150; borders: left thin, right thin, top thin, bottom thin; alignment: horiz center',
        num_format_str='yyyy-mm-dd')
    fuentenumerodecimal = easyxf(
        'font: name Verdana, color-index black, height 150; borders: left thin, right thin, top thin, bottom thin; alignment: horiz right',
        num_format_str='#,##0.00')
    fuentenumeroentero = easyxf(
        'font: name Verdana, color-index black, height 150; borders: left thin, right thin, top thin, bottom thin; alignment: horiz right')
    fuenteporcentaje = easyxf(
        'font: name Verdana, color-index black, height 150; borders: left thin, right thin, top thin, bottom thin; alignment: horiz right',
        num_format_str='0%')
    fuenteporcentajeneg = easyxf(
        'font: name Verdana, color-index black, bold on, height 150; borders: left thin, right thin, top thin, bottom thin; alignment: horiz right; pattern: pattern solid, fore_colour gray25',
        num_format_str='0.00%')


    font_style = XFStyle()
    font_style.font.bold = True
    font_style2 = XFStyle()
    font_style2.font.bold = False
    output_folder = os.path.join(os.path.join(SITE_STORAGE, 'media', 'arreglos'))

    libdestino = xlwt.Workbook()
    hojadestino = libdestino.add_sheet("Listado")

    hojadestino.write_merge(0, 0, 0, 14, 'UNIVERSIDAD ESTATAL DE MILAGRO', titulo)
    hojadestino.write_merge(1, 1, 0, 14, 'DIRECCIÓN DE INVESTIGACIÓN Y POSGRADO', titulo2)
    hojadestino.write_merge(2, 2, 0, 14, 'PROYECCIÓN DE COBROS POSGRADO', titulo2)
    # hojadestino.write_merge(2, 2, 0, 14, 'EDAD DE LA CARTERA VENCIDA DEL MES DE ' + meses[
    #     int(mes_actual) - 1].upper() + ' DEL ' + anio_actual, titulo2)

    fila = 4
    fechafinant = str(fechafinmesanterior.day) + "-" + meses[fechafinmesanterior.month - 1][:3].upper() + "-" + str(
        fechafinmesanterior.year)
    fechafinact = str(finmes.day) + "-" + meses[finmes.month - 1][:3].upper() + "-" + str(finmes.year)

    hojadestino.row(fila).height_mismatch = True
    hojadestino.row(fila).height = 400
    hojadestino.row(fila+1).height_mismatch = True
    hojadestino.row(fila + 1).height = 400

    columnas = [
        (u"PROGRAMAS", 8000),
        (u"PROG.", 2500),
        (u"COHORTE", 2500),
        (u"FECHA PERIODO INICIAL", 3000),
        (u"FECHA PERIDO FINAL", 3000),
        (u"ESTUDIANTE", 10000),
        (u"IDENTIFICACIÓN", 3900),
        (u"VALOR TOTAL PROGRAMA", 4000),
        (u"VALOR COBRADO A LA FECHA", 4000),
        (u"SALDO VENCIDO AL " + fechafinant, 4000),
        (U"SALDO POR VENCER AL " + fechafinact, 4000)
    ]

    for col_num in range(len(columnas)):
        hojadestino.write_merge(fila, fila + 1, col_num, col_num, columnas[col_num][0], fuentecabecera)
        # hojadestino.write(fila, col_num, columnas[col_num][0], fuentecabecera)
        hojadestino.col(col_num).width = columnas[col_num][1]

    hojadestino.write_merge(fila, fila, 11, 14, "PROYECCIÓN DE COBROS", fuentecabecera)
    hojadestino.write(fila+1, 11, "1 - 30", fuentecabecera)
    hojadestino.col(11).width = 4000
    hojadestino.write(fila + 1, 12, "31 - 60", fuentecabecera)
    hojadestino.col(12).width = 4000
    hojadestino.write(fila + 1, 13, "61 - 90", fuentecabecera)
    hojadestino.col(13).width = 4000
    hojadestino.write(fila + 1, 14, "+ 90", fuentecabecera)
    hojadestino.col(14).width = 4000


    # periodos = Periodo.objects.values('id').filter(nivel__matricula__rubro__saldo__gt=0, nivel__matricula__rubro__fechavence__lt=datetime.now().date(), tipo__id__in=[3, 4]).distinct().order_by('id')
    # matriculas = Matricula.objects.filter(nivel__periodo__tipo__id__in=[3, 4], inscripcion__persona__cedula='0926476813').order_by('inscripcion__persona__apellido1', 'inscripcion__persona__apellido2', 'inscripcion__persona__nombres')

    # print("Ultimo dia mes anterior: ", fechafinmesanterior)
    # print("Primer dia mes actual: ", iniciomes, " Ultimo día mes actual: ", finmes)

    matriculas = Matricula.objects.filter(status=True, nivel__periodo__tipo__id__in=[3, 4]
                                          # inscripcion__persona__cedula__in=['0916362163', '0928477934','0916954613', '0919850255']
                                          # inscripcion__carrera__id=60,
                                          # nivel__periodo__id__in=[12, 13, 78, 84, 91],
                                          ).distinct().order_by('inscripcion__persona__apellido1',
                                                                'inscripcion__persona__apellido2',
                                                                'inscripcion__persona__nombres')

    # matriculas = Matricula.objects.filter(status=True, nivel__periodo__tipo__id__in=[3, 4]).distinct().order_by(
    #     'inscripcion__persona__apellido1', 'inscripcion__persona__apellido2', 'inscripcion__persona__nombres')

    totalmatriculas = matriculas.count()

    # print(totalmatriculas)
    c = 0

    horainicio = datetime.now()

    totalalumnos = 0

    totalsaldoinicial = 0
    totalrubros = 0
    totalpagado = 0
    totalsaldofinal = 0

    fila = 6
    cedula = ''

    totalprograma = 0
    totalcobrado = 0
    totalsaldovencido = 0
    totaledad1 = 0
    totaledad2 = 0
    totaledad3 = 0
    totaledad4 = 0
    totalsaldovencer = 0

    for matricula in matriculas:
        c += 1
        print("Procesando ", c, " de ", totalmatriculas)

        periodo = matricula.nivel.periodo
        costoprograma = Decimal(null_to_decimal(periodo.periodocarreracosto_set.filter(carrera=matricula.inscripcion.carrera, status=True).aggregate(costo=Sum('costo'))['costo'] ) ).quantize(Decimal('.01'))
        valordescontado = 0

        if matricula.matriculanovedad_set.filter(tipo=1).exists():
            novedad = matricula.matriculanovedad_set.filter(tipo=1)[0]
            motivo = '%s' % novedad.motivo
            porcentaje = Decimal(novedad.porcentajedescuento).quantize(Decimal('.01')) if novedad.porcentajedescuento else 0
            if porcentaje > 0:
                valordescontado = Decimal(null_to_decimal((costoprograma * porcentaje) / 100, 2)).quantize(
                    Decimal('.01'))

        valortotalprograma = costoprograma - valordescontado
        # SALDO ANTERIOR
        totalrubrosanterior = Decimal(null_to_decimal(matricula.rubro_set.filter(status=True,
                                                                                 fechavence__lt=iniciomes
                                                                                 ).aggregate(valor=Sum('valortotal'))[
                                                          'valor'], 2)).quantize(Decimal('.01'))
        print("Total rubros anterior:", totalrubrosanterior)

        totalliquidado = Decimal(null_to_decimal(matricula.rubro_set.filter(status=True,
                                                                            fechavence__lt=iniciomes,
                                                                            pago__pagoliquidacion__isnull=False
                                                                            ).aggregate(valor=Sum('valortotal'))[
                                                     'valor'], 2)).quantize(Decimal('.01'))

        print("Total Liquidado ", totalliquidado)

        totalanulado = Decimal(null_to_decimal(Pago.objects.filter(
            status=True,
            rubro__matricula=matricula,
            rubro__status=True,
            rubro__fechavence__lte=finmes,
            factura__valida=False,
            factura__status=True
        ).aggregate(pagos=Sum('valortotal'))['pagos'], 2)).quantize(Decimal('.01'))

        print("total anulado: ", totalanulado)

        # PAGADO ANTERIOR ---- REVISAR BIEN ESTA TOMANDO PAGO DE RUBROS DE JULIO, AGOSTO
        totalpagosanterior = Decimal(null_to_decimal(Pago.objects.filter(
            fecha__lt=iniciomes,
            pagoliquidacion__isnull=True,
            status=True,
            rubro__matricula=matricula,
            rubro__status=True
            # rubro__fechavence__lte=finmes
        ).exclude(factura__valida=False).aggregate(pagos=Sum('valortotal'))['pagos'], 2)).quantize(Decimal('.01'))
        print("Total Pagado anterior: ", totalpagosanterior)

        totalvencimientosposterior = Decimal(null_to_decimal(Pago.objects.filter(
            # rubro__matricula__inscripcion__persona__cedula__in=cedulas,
            fecha__lt=iniciomes,
            pagoliquidacion__isnull=True,
            status=True,
            rubro__matricula__nivel__periodo__tipo__id__in=[3, 4],
            rubro__matricula=matricula,
            # rubro__matricula__inscripcion__carrera__id=carrera,
            # rubro__matricula__nivel__periodo__id__in=periodos,
            rubro__status=True,
            rubro__fechavence__gte=iniciomes
        ).exclude(factura__valida=False).aggregate(pagos=Sum('valortotal'))['pagos'], 2)).quantize(Decimal('.01'))

        saldoanterior = totalrubrosanterior - (totalpagosanterior + totalliquidado + totalanulado)
        saldoanterior += totalvencimientosposterior

        print("Saldo anterior: ", saldoanterior)

        if saldoanterior != 0:
            totalprograma += valortotalprograma
            totalcobrado += totalpagosanterior
            totalsaldovencido += saldoanterior

            saldovencer = valortotalprograma - totalpagosanterior - saldoanterior

            hojadestino.write(fila, 0, matricula.inscripcion.carrera.nombre, fuentenormal)
            hojadestino.write(fila, 1, matricula.inscripcion.carrera.alias, fuentenormalcent)
            hojadestino.write(fila, 2, matricula.nivel.periodo.cohorte, fuentenormalcent)
            hojadestino.write(fila, 3, matricula.nivel.periodo.inicio, fuentefecha)
            hojadestino.write(fila, 4, matricula.nivel.periodo.fin, fuentefecha)
            hojadestino.write(fila, 5, matricula.inscripcion.persona.nombre_completo_inverso(), fuentenormal)
            hojadestino.write(fila, 6, matricula.inscripcion.persona.identificacion(), fuentenormal)
            hojadestino.write(fila, 7, valortotalprograma, fuentemoneda)
            hojadestino.write(fila, 8, totalpagosanterior, fuentemoneda)
            hojadestino.write(fila, 9, saldoanterior, fuentemoneda)
            hojadestino.write(fila, 10, saldovencer, fuentemoneda)

            # ===== SALDOS 1-30, 31-60, 61-90, + 90 DIAS
            fechainiciocartera = finmes + relativedelta(days=1)
            # ultimodia = str(fechainiciocartera.year, fechainiciocartera.month[1])

            ultimodia = str(calendar.monthrange(fechainiciocartera.year, fechainiciocartera.month)[1])

            fechafincartera = datetime.strptime(str(fechainiciocartera.year) + '-' + str(fechainiciocartera.month) + '-' + ultimodia, '%Y-%m-%d').date()

            columna = 11

            saldoanteriorcartera = 0
            valoredad1 = 0
            valoredad2 = 0
            valoredad3 = 0
            valoredad4 = 0

            if saldovencer > 0:

                for n in range(1, 4):

                    totalrubroscartera = Decimal(null_to_decimal(matricula.rubro_set.filter(status=True,
                                                                                             fechavence__gte=fechainiciocartera,
                                                                                             fechavence__lte=fechafincartera
                                                                                             ).aggregate(valor=Sum('valortotal'))[
                                                                      'valor'], 2)).quantize(Decimal('.01'))
                    print("Total rubros anterior:", totalrubrosanterior)

                    # totalliquidadocartera = Decimal(null_to_decimal(matricula.rubro_set.filter(status=True,
                    #                                                                     fechavence__gte=fechainiciocartera,
                    #                                                                     fechavence__lte=fechafincartera,
                    #                                                                     pago__pagoliquidacion__isnull=False
                    #                                                                     ).aggregate(valor=Sum('valortotal'))[
                    #                                              'valor'], 2)).quantize(Decimal('.01'))
                    #
                    # print("Total Liquidado ", totalliquidado)
                    #
                    # totalanuladocartera = Decimal(null_to_decimal(Pago.objects.filter(
                    #     status=True,
                    #     rubro__matricula=matricula,
                    #     rubro__status=True,
                    #     rubro__fechavence__gte=fechainiciocartera,
                    #     rubro__fechavence__lte=fechafincartera,
                    #     factura__valida=False,
                    #     factura__status=True
                    # ).aggregate(pagos=Sum('valortotal'))['pagos'], 2)).quantize(Decimal('.01'))
                    #
                    # print("total anulado: ", totalanulado)
                    #
                    # # PAGADO ANTERIOR ---- REVISAR BIEN ESTA TOMANDO PAGO DE RUBROS DE JULIO, AGOSTO
                    # totalpagoscartera = Decimal(null_to_decimal(Pago.objects.filter(
                    #     fecha__lt=iniciomes,
                    #     pagoliquidacion__isnull=True,
                    #     status=True,
                    #     rubro__matricula=matricula,
                    #     rubro__status=True,
                    #     rubro__fechavence__gte=fechainiciocartera,
                    #     rubro__fechavence__lte=fechafincartera
                    # ).exclude(factura__valida=False).aggregate(pagos=Sum('valortotal'))['pagos'], 2)).quantize(Decimal('.01'))
                    # print("Total Pagado anterior: ", totalpagosanterior)

                    # saldoanteriorcartera = totalrubroscartera - (totalpagoscartera + totalliquidadocartera + totalanuladocartera)
                    saldoanteriorcartera = totalrubroscartera

                    print("Saldo anterior 1-30 días:", saldoanteriorcartera)

                    hojadestino.write(fila, columna, saldoanteriorcartera, fuentemoneda)

                    if n == 1:
                        totaledad1 += saldoanteriorcartera
                        valoredad1 = saldoanteriorcartera
                    elif n == 2:
                        totaledad2 += saldoanteriorcartera
                        valoredad2 = saldoanteriorcartera
                    else:
                        totaledad3 += saldoanteriorcartera
                        valoredad3 = saldoanteriorcartera

                    columna += 1

                    fechainiciocartera = fechafincartera + relativedelta(days=1)
                    # ultimodia = str(fechainiciocartera.year, fechainiciocartera.month[1])

                    ultimodia = str(calendar.monthrange(fechainiciocartera.year, fechainiciocartera.month)[1])

                    fechafincartera = datetime.strptime(str(fechainiciocartera.year) + '-' + str(fechainiciocartera.month) + '-' + ultimodia,'%Y-%m-%d').date()

                    # fechafincartera = fechainiciocartera - relativedelta(days=1)
                    # fechainiciocartera = datetime.strptime(str(fechafincartera.year) + '-' + str(fechafincartera.month) + '-' + primerdia, '%Y-%m-%d').date()
            else:
                hojadestino.write(fila, columna, 0, fuentemoneda)
                hojadestino.write(fila, columna+1, 0, fuentemoneda)
                hojadestino.write(fila, columna+2, 0, fuentemoneda)
                hojadestino.write(fila, columna+3, 0, fuentemoneda)

            # fechainiciocartera = fechafincartera + relativedelta(days=1)

            if saldovencer > 0:
                fechainiciocartera = fechafincartera + relativedelta(days=1)

                print("Fecha inicio de cartera:", fechainiciocartera)
                totalrubroscartera = Decimal(null_to_decimal(matricula.rubro_set.filter(status=True,
                                                                                         fechavence__gte=fechainiciocartera
                                                                                         ).aggregate(valor=Sum('valortotal'))[
                                                                  'valor'], 2)).quantize(Decimal('.01'))
                print("Total rubros anterior:", totalrubroscartera)

                # totalliquidadocartera = Decimal(null_to_decimal(matricula.rubro_set.filter(status=True,
                #                                                                     fechavence__lt=fechainiciocartera,
                #                                                                     pago__pagoliquidacion__isnull=False
                #                                                                     ).aggregate(valor=Sum('valortotal'))[
                #                                              'valor'], 2)).quantize(Decimal('.01'))
                #
                # print("Total Liquidado ", totalliquidadocartera)
                #
                # totalanuladocartera = Decimal(null_to_decimal(Pago.objects.filter(
                #     status=True,
                #     rubro__matricula=matricula,
                #     rubro__status=True,
                #     rubro__fechavence__lt=fechainiciocartera,
                #     factura__valida=False,
                #     factura__status=True
                # ).aggregate(pagos=Sum('valortotal'))['pagos'], 2)).quantize(Decimal('.01'))
                #
                # print("total anulado: ", totalanuladocartera)
                #
                # # PAGADO ANTERIOR ---- REVISAR BIEN ESTA TOMANDO PAGO DE RUBROS DE JULIO, AGOSTO
                # totalpagoscartera = Decimal(null_to_decimal(Pago.objects.filter(
                #     fecha__lt=iniciomes,
                #     pagoliquidacion__isnull=True,
                #     status=True,
                #     rubro__matricula=matricula,
                #     rubro__status=True,
                #     rubro__fechavence__lt=fechainiciocartera
                # ).exclude(factura__valida=False).aggregate(pagos=Sum('valortotal'))['pagos'], 2)).quantize(Decimal('.01'))
                # print("Total Pagado anterior: ", totalpagoscartera)
                # saldoanteriorcartera = totalrubroscartera - (totalpagoscartera + totalliquidadocartera + totalanuladocartera)
                saldoanteriorcartera = saldovencer - (valoredad1 + valoredad2 + valoredad3)

                # saldovencer = valortotalprograma - totalpagosanterior - saldoanterior
                print("Saldo anterior mayor a 90 días:", saldoanteriorcartera)
                hojadestino.write(fila, columna, saldoanteriorcartera, fuentemoneda)
                # hojadestino.write(fila, columna + 1, saldovencer, fuentemoneda)


                totaledad4 += saldoanteriorcartera
                totalsaldovencer += saldovencer

            fila += 1

    hojadestino.write_merge(fila, fila, 0, 6, "TOTAL GENERAL", fuentenormalnegrell)
    hojadestino.write(fila, 7, totalprograma, fuentemonedaneg)
    hojadestino.write(fila, 8, totalcobrado, fuentemonedaneg)
    hojadestino.write(fila, 9, totalsaldovencido, fuentemonedaneg)
    hojadestino.write(fila, 10, totalsaldovencer, fuentemonedaneg)
    hojadestino.write(fila, 11, totaledad1, fuentemonedaneg)
    hojadestino.write(fila, 12, totaledad2, fuentemonedaneg)
    hojadestino.write(fila, 13, totaledad3, fuentemonedaneg)
    hojadestino.write(fila, 14, totaledad4, fuentemonedaneg)
    # hojadestino.write(fila, 14, totalsaldovencer, fuentemonedaneg)

    fila += 1

    if totalsaldovencer > 0:
        hojadestino.write(fila, 10, 1, fuenteporcentajeneg)
        hojadestino.write(fila, 11, totaledad1 / totalsaldovencer, fuenteporcentajeneg)
        hojadestino.write(fila, 12, totaledad2 / totalsaldovencer, fuenteporcentajeneg)
        hojadestino.write(fila, 13, totaledad3 / totalsaldovencer, fuenteporcentajeneg)
        hojadestino.write(fila, 14, totaledad4 / totalsaldovencer, fuenteporcentajeneg)


    print("Total alumnos para el reporte: ", totalalumnos)
    print("Total saldo anterior: ", totalsaldoinicial)
    print("Total rubros del mes: ", totalrubros)
    print("Total pagado del mes: ", totalpagado)
    print("Total saldo actual: ", totalsaldofinal)

    print("Inicio: ", horainicio)
    print("Fin: ", datetime.now())

    libdestino.save(output_folder + "/R6_PROYECCION_COBROS_POSGRADO_DICIEMBRE_2021.xls")
    print("Archivo creado. . .")


def reporte_indice_cartera_vencida():
    iniciomes = datetime.strptime('2021' + '-' + '12' + '-' + '1','%Y-%m-%d').date()
    finmes = datetime.strptime('2021' + '-' + '12' + '-' + '31','%Y-%m-%d').date()

    carrera = 60
    periodos = [12, 13, 78, 84, 91]
    cedulas = ['0302613658']

    # Rubros de meses anteriores
    totalrubrosanterior = Decimal(null_to_decimal(Rubro.objects.filter(status=True,
                                                                       # matricula__inscripcion__persona__cedula__in=cedulas,
                                                                       fechavence__lt=iniciomes,
                                                                       matricula__nivel__periodo__tipo__id__in=[3, 4]
                                                                       # matricula__inscripcion__carrera__id=carrera,
                                                                       # matricula__nivel__periodo__id__in=periodos
                                                                       ).aggregate(
        valor=Sum('valortotal'))['valor'], 2)).quantize(Decimal('.01'))


    # Liquidado de meses anteriores
    totalliquidadoanterior = Decimal(null_to_decimal(Rubro.objects.filter(status=True,
                                                                          # matricula__inscripcion__persona__cedula__in=cedulas,
                                                                          fechavence__lt=iniciomes,
                                                                          matricula__nivel__periodo__tipo__id__in=[3,
                                                                                                                    4],
                                                                          # matricula__inscripcion__carrera__id=carrera,
                                                                          # matricula__nivel__periodo__id__in=periodos,
                                                                          pago__pagoliquidacion__isnull=False
                                                                          ).aggregate(
        valor=Sum('valortotal'))['valor'], 2)).quantize(Decimal('.01'))

    # Anulado meses anteriores
    totalanuladoanterior = Decimal(null_to_decimal(Pago.objects.filter(
        status=True,
        # rubro__matricula__inscripcion__persona__cedula__in=cedulas,
        rubro__matricula__nivel__periodo__tipo__id__in=[3, 4],
        # rubro__matricula__inscripcion__carrera__id=carrera,
        # rubro__matricula__nivel__periodo__id__in=periodos,
        rubro__status=True,
        rubro__fechavence__lte=finmes,
        # rubro__fechavence__lt=iniciomes,
        factura__valida=False,
        factura__status=True
    ).aggregate(pagos=Sum('valortotal'))['pagos'], 2)).quantize(Decimal('.01'))

    # Pagos de meses anteriores
    totalpagosanterior = Decimal(null_to_decimal(Pago.objects.filter(
        fecha__lt=iniciomes,
        pagoliquidacion__isnull=True,
        status=True,
        # rubro__matricula__inscripcion__persona__cedula__in=cedulas,
        rubro__matricula__nivel__periodo__tipo__id__in=[3, 4],
        # rubro__matricula__inscripcion__carrera__id=carrera,
        # rubro__matricula__nivel__periodo__id__in=periodos,
        rubro__status=True
        # rubro__fechavence__lt=iniciomes
        # rubro__fechavence__lte=finmes # este es
    ).exclude(factura__valida=False).aggregate(pagos=Sum('valortotal'))['pagos'], 2)).quantize(Decimal('.01'))

    print("Total pagos anterior: ", totalpagosanterior)
    # Hacer ajustes para calcular bien saldo anterior :D
    # Pagos del mes que corresponden a rubros de meses posteriores
    totalvencimientosposterior = Decimal(null_to_decimal(Pago.objects.filter(
        # rubro__matricula__inscripcion__persona__cedula__in=cedulas,
        fecha__lt=iniciomes,
        pagoliquidacion__isnull=True,
        status=True,
        rubro__matricula__nivel__periodo__tipo__id__in=[3, 4],
        # rubro__matricula__inscripcion__carrera__id=carrera,
        # rubro__matricula__nivel__periodo__id__in=periodos,
        rubro__status=True,
        rubro__fechavence__gte=iniciomes
    ).exclude(factura__valida=False).aggregate(pagos=Sum('valortotal'))['pagos'], 2)).quantize(Decimal('.01'))

    # ========================================


    # Vencimientos del mes: rubros del mes estén pagados o no
    totalvencimientos = Decimal(null_to_decimal( Rubro.objects.filter(status=True,
                          # matricula__inscripcion__persona__cedula__in=cedulas,
                          matricula__nivel__periodo__tipo__id__in=[3, 4],
                          # matricula__inscripcion__carrera__id=carrera,
                          # matricula__nivel__periodo__id__in=periodos,
                          fechavence__gte=iniciomes,
                          fechavence__lte=finmes).aggregate(valor=Sum('valortotal'))[
                                                                  'valor'], 2)).quantize(Decimal('.01'))
    # Rubros del mes y que han sido pagados en meses anteriores
    totalvencimientos2 = 0
    totalvencimientos2 = Decimal(null_to_decimal(Pago.objects.filter(
        # rubro__matricula__inscripcion__persona__cedula__in=cedulas,
        fecha__lt=iniciomes,
        pagoliquidacion__isnull=True,
        status=True,
        rubro__matricula__nivel__periodo__tipo__id__in=[3, 4],
        # rubro__matricula__inscripcion__carrera__id=carrera,
        # rubro__matricula__nivel__periodo__id__in=periodos,
        rubro__status=True,
        rubro__fechavence__gte=iniciomes,
        rubro__fechavence__lte=finmes
    ).exclude(factura__valida=False).aggregate(pagos=Sum('valortotal'))['pagos'], 2)).quantize(Decimal('.01'))

    # Pagos del mes que corresponden a rubros de meses posteriores
    totalvencimientos3 = Decimal(null_to_decimal(Pago.objects.filter(
        # rubro__matricula__inscripcion__persona__cedula__in=cedulas,
        fecha__gte=iniciomes,
        fecha__lte=finmes,
        pagoliquidacion__isnull=True,
        status=True,
        rubro__matricula__nivel__periodo__tipo__id__in=[3, 4],
        # rubro__matricula__inscripcion__carrera__id=carrera,
        # rubro__matricula__nivel__periodo__id__in=periodos,
        rubro__status=True,
        rubro__fechavence__gt=finmes
    ).exclude(factura__valida=False).aggregate(pagos=Sum('valortotal'))['pagos'], 2)).quantize(Decimal('.01'))

    totalvencimientos = (totalvencimientos - totalvencimientos2) + totalvencimientos3


    # Cobros del mes
    totalcobros = Decimal(null_to_decimal(Pago.objects.filter(
        # rubro__matricula__inscripcion__persona__cedula__in=cedulas,
        fecha__gte=iniciomes,
        fecha__lte=finmes,
        pagoliquidacion__isnull=True,
        status=True,
        rubro__matricula__nivel__periodo__tipo__id__in=[3, 4],
        # rubro__matricula__inscripcion__carrera__id=carrera,
        # rubro__matricula__nivel__periodo__id__in=periodos,
        rubro__status=True
        # rubro__fechavence__lte=finmes
    ).exclude(factura__valida=False).aggregate(pagos=Sum('valortotal'))['pagos'], 2)).quantize(Decimal('.01'))


    saldoanterior = totalrubrosanterior - (totalpagosanterior + totalliquidadoanterior + totalanuladoanterior)

    saldoanterior += totalvencimientosposterior

    carteracobroperiodo = saldoanterior + totalvencimientos

    print("Saldo vencido inicio periodo: ", saldoanterior)
    print("Vencimientos del periodo: ", totalvencimientos)
    print("Cartera al cobro en el periodo: ", carteracobroperiodo)
    print("Cobros del periodo: ", totalcobros)
    print("Saldo final de periodo: ", carteracobroperiodo - totalcobros)


def reporte_indice_cartera_vencida_segun_auditor1():
    iniciomes = datetime.strptime('2021' + '-' + '04' + '-' + '1','%Y-%m-%d').date()
    finmes = datetime.strptime('2021' + '-' + '04' + '-' + '30','%Y-%m-%d').date()

    carrera = 60
    periodos = [91]
    cedulas = ['1206106237']

    totalrubrosanterior = Decimal(null_to_decimal(Rubro.objects.filter(status=True,
                                                                       matricula__inscripcion__persona__cedula__in=cedulas,
                                                                       fechavence__lt=iniciomes,
                                                                       matricula__nivel__periodo__tipo__id__in=[3, 4],
                                                                       matricula__inscripcion__carrera__id=carrera,
                                                                       matricula__nivel__periodo__id__in=periodos
                                                                       ).aggregate(
        valor=Sum('valortotal'))['valor'], 2)).quantize(Decimal('.01'))

    totalliquidadoanterior = Decimal(null_to_decimal(Rubro.objects.filter(status=True,
                                                                          matricula__inscripcion__persona__cedula__in=cedulas,
                                                                          fechavence__lt=iniciomes,
                                                                          matricula__nivel__periodo__tipo__id__in=[3,
                                                                                                                    4],
                                                                          matricula__inscripcion__carrera__id=carrera,
                                                                          matricula__nivel__periodo__id__in=periodos,
                                                                          pago__pagoliquidacion__isnull=False
                                                                          ).aggregate(
        valor=Sum('valortotal'))['valor'], 2)).quantize(Decimal('.01'))

    totalanuladoanterior = Decimal(null_to_decimal(Pago.objects.filter(
        status=True,
        rubro__matricula__inscripcion__persona__cedula__in=cedulas,
        rubro__matricula__nivel__periodo__tipo__id__in=[3, 4],
        rubro__matricula__inscripcion__carrera__id=carrera,
        rubro__matricula__nivel__periodo__id__in=periodos,
        rubro__status=True,
        rubro__fechavence__lte=finmes,
        # rubro__fechavence__lt=iniciomes,
        factura__valida=False,
        factura__status=True
    ).aggregate(pagos=Sum('valortotal'))['pagos'], 2)).quantize(Decimal('.01'))

    totalpagosanterior = Decimal(null_to_decimal(Pago.objects.filter(
        fecha__lt=iniciomes,
        pagoliquidacion__isnull=True,
        status=True,
        rubro__matricula__inscripcion__persona__cedula__in=cedulas,
        rubro__matricula__nivel__periodo__tipo__id__in=[3, 4],
        rubro__matricula__inscripcion__carrera__id=carrera,
        rubro__matricula__nivel__periodo__id__in=periodos,
        rubro__status=True,
        # rubro__fechavence__lt=iniciomes
        rubro__fechavence__lte=finmes # este es
    ).exclude(factura__valida=False).aggregate(pagos=Sum('valortotal'))['pagos'], 2)).quantize(Decimal('.01'))




    # Vencimientos del mes
    totalvencimientos = Decimal(null_to_decimal( Rubro.objects.filter(status=True,
                          matricula__inscripcion__persona__cedula__in=cedulas,
                          matricula__nivel__periodo__tipo__id__in=[3, 4],
                          matricula__inscripcion__carrera__id=carrera,
                          matricula__nivel__periodo__id__in=periodos,
                          fechavence__gte=iniciomes,
                          fechavence__lte=finmes).aggregate(valor=Sum('valortotal'))[
                                                                  'valor'], 2)).quantize(Decimal('.01'))

    # Cobros del mes
    totalcobros = Decimal(null_to_decimal(Pago.objects.filter(
        rubro__matricula__inscripcion__persona__cedula__in=cedulas,
        fecha__gte=iniciomes,
        fecha__lte=finmes,
        pagoliquidacion__isnull=True,
        status=True,
        rubro__matricula__nivel__periodo__tipo__id__in=[3, 4],
        rubro__matricula__inscripcion__carrera__id=carrera,
        rubro__matricula__nivel__periodo__id__in=periodos,
        rubro__status=True,
        rubro__fechavence__lte=finmes
    ).exclude(factura__valida=False).aggregate(pagos=Sum('valortotal'))['pagos'], 2)).quantize(Decimal('.01'))

    saldoanterior = totalrubrosanterior - (totalpagosanterior + totalliquidadoanterior + totalanuladoanterior)
    carteracobroperiodo = saldoanterior + totalvencimientos

    print("Saldo vencido inicio periodo: ", saldoanterior)
    print("Vencimientos del periodo: ", totalvencimientos)
    print("Cartera al cobro en el periodo: ", carteracobroperiodo)
    print("Cobros del periodo: ", totalcobros)
    print("Saldo final de periodo: ", carteracobroperiodo - totalcobros)


def reporte_indice_cartera_vencida_imsm():
    iniciomes = datetime.strptime('2021' + '-' + '03' + '-' + '1','%Y-%m-%d').date()
    finmes = datetime.strptime('2021' + '-' + '03' + '-' + '31','%Y-%m-%d').date()

    carrera = 60
    periodos = [91]
    cedulas = ['1206106237']

    totalrubrosanterior = Decimal(null_to_decimal(Rubro.objects.filter(status=True,
                                                                       matricula__inscripcion__persona__cedula__in=cedulas,
                                                                       fechavence__lt=iniciomes,
                                                                       matricula__nivel__periodo__tipo__id__in=[3, 4],
                                                                       matricula__inscripcion__carrera__id=carrera,
                                                                       matricula__nivel__periodo__id__in=periodos
                                                                       ).aggregate(
        valor=Sum('valortotal'))['valor'], 2)).quantize(Decimal('.01'))

    totalliquidadoanterior = Decimal(null_to_decimal(Rubro.objects.filter(status=True,
                                                                          matricula__inscripcion__persona__cedula__in=cedulas,
                                                                          fechavence__lt=iniciomes,
                                                                          matricula__nivel__periodo__tipo__id__in=[3,
                                                                                                                    4],
                                                                          matricula__inscripcion__carrera__id=carrera,
                                                                          matricula__nivel__periodo__id__in=periodos,
                                                                          pago__pagoliquidacion__isnull=False
                                                                          ).aggregate(
        valor=Sum('valortotal'))['valor'], 2)).quantize(Decimal('.01'))

    totalanuladoanterior = Decimal(null_to_decimal(Pago.objects.filter(
        status=True,
        rubro__matricula__inscripcion__persona__cedula__in=cedulas,
        rubro__matricula__nivel__periodo__tipo__id__in=[3, 4],
        rubro__matricula__inscripcion__carrera__id=carrera,
        rubro__matricula__nivel__periodo__id__in=periodos,
        rubro__status=True,
        rubro__fechavence__lte=finmes,
        # rubro__fechavence__lt=iniciomes,
        factura__valida=False,
        factura__status=True
    ).aggregate(pagos=Sum('valortotal'))['pagos'], 2)).quantize(Decimal('.01'))

    totalpagosanterior = Decimal(null_to_decimal(Pago.objects.filter(
        fecha__lt=iniciomes,
        pagoliquidacion__isnull=True,
        status=True,
        rubro__matricula__inscripcion__persona__cedula__in=cedulas,
        rubro__matricula__nivel__periodo__tipo__id__in=[3, 4],
        rubro__matricula__inscripcion__carrera__id=carrera,
        rubro__matricula__nivel__periodo__id__in=periodos,
        rubro__status=True
        # rubro__fechavence__lt=iniciomes
        # rubro__fechavence__lte=finmes # este es
    ).exclude(factura__valida=False).aggregate(pagos=Sum('valortotal'))['pagos'], 2)).quantize(Decimal('.01'))




    # Vencimientos del mes
    totalvencimientos = Decimal(null_to_decimal( Rubro.objects.filter(status=True,
                          matricula__inscripcion__persona__cedula__in=cedulas,
                          matricula__nivel__periodo__tipo__id__in=[3, 4],
                          matricula__inscripcion__carrera__id=carrera,
                          matricula__nivel__periodo__id__in=periodos,
                          fechavence__gte=iniciomes,
                          fechavence__lte=finmes).aggregate(valor=Sum('valortotal'))[
                                                                  'valor'], 2)).quantize(Decimal('.01'))

    # Cobros del mes
    totalcobros = Decimal(null_to_decimal(Pago.objects.filter(
        rubro__matricula__inscripcion__persona__cedula__in=cedulas,
        fecha__gte=iniciomes,
        fecha__lte=finmes,
        pagoliquidacion__isnull=True,
        status=True,
        rubro__matricula__nivel__periodo__tipo__id__in=[3, 4],
        rubro__matricula__inscripcion__carrera__id=carrera,
        rubro__matricula__nivel__periodo__id__in=periodos,
        rubro__status=True
        # rubro__fechavence__lte=finmes
    ).exclude(factura__valida=False).aggregate(pagos=Sum('valortotal'))['pagos'], 2)).quantize(Decimal('.01'))

    saldoanterior = totalrubrosanterior - (totalpagosanterior + totalliquidadoanterior + totalanuladoanterior)
    carteracobroperiodo = saldoanterior + totalvencimientos

    print("Saldo vencido inicio periodo: ", saldoanterior)
    print("Vencimientos del periodo: ", totalvencimientos)
    print("Cartera al cobro en el periodo: ", carteracobroperiodo)
    print("Cobros del periodo: ", totalcobros)
    print("Saldo final de periodo: ", carteracobroperiodo - totalcobros)


def generar_listado_matriculados_rubros():

    fuentenormal = easyxtitulo = easyxf(
        'font: name Times New Roman, color-index black, bold on , height 350; alignment: horiz centre')
    titulo = easyxf(
        'font: name Times New Roman, color-index black, bold on , height 350; alignment: horiz centre')
    titulo2 = easyxf(
        'font: name Times New Roman, color-index black, bold on , height 250; alignment: horiz centre')
    fuentecabecera = easyxf(
        'font: name Verdana, color-index black, bold on, height 150; pattern: pattern solid, fore_colour gray25; alignment: vert distributed, horiz centre; borders: left thin, right thin, top thin, bottom thin')
    fuentenormal = easyxf(
        'font: name Verdana, color-index black, height 150; borders: left thin, right thin, top thin, bottom thin')
    fuentenormalwrap = easyxf(
        'font: name Verdana, color-index black, height 150; borders: left thin, right thin, top thin, bottom thin')
    fuentenormalneg = easyxf(
        'font: name Verdana, color-index black, bold on , height 150; borders: left thin, right thin, top thin, bottom thin')
    fuentenormalnegrell = easyxf(
        'font: name Verdana, color-index black, bold on , height 150; borders: left thin, right thin, top thin, bottom thin; pattern: pattern solid, fore_colour gray25')
    fuentenormalwrap.alignment.wrap = True
    fuentenormalcent = easyxf(
        'font: name Verdana, color-index black, height 150; borders: left thin, right thin, top thin, bottom thin; alignment: horiz centre')
    fuentemoneda = easyxf(
        'font: name Verdana, color-index black, height 150; borders: left thin, right thin, top thin, bottom thin; alignment: horiz right',
        num_format_str=' "$" #,##0.00')
    fuentemonedaneg = easyxf(
        'font: name Verdana, color-index black, bold on, height 150; borders: left thin, right thin, top thin, bottom thin; alignment: horiz right; pattern: pattern solid, fore_colour gray25',
        num_format_str=' "$" #,##0.00')
    fuentefecha = easyxf(
        'font: name Verdana, color-index black, height 150; borders: left thin, right thin, top thin, bottom thin; alignment: horiz center',
        num_format_str='yyyy-mm-dd')
    fuentenumerodecimal = easyxf(
        'font: name Verdana, color-index black, height 150; borders: left thin, right thin, top thin, bottom thin; alignment: horiz right',
        num_format_str='#,##0.00')
    fuentenumeroentero = easyxf(
        'font: name Verdana, color-index black, height 150; borders: left thin, right thin, top thin, bottom thin; alignment: horiz right')
    fuenteporcentaje = easyxf(
        'font: name Verdana, color-index black, height 150; borders: left thin, right thin, top thin, bottom thin; alignment: horiz right',
        num_format_str='0%')
    fuenteporcentajeneg = easyxf(
        'font: name Verdana, color-index black, bold on, height 150; borders: left thin, right thin, top thin, bottom thin; alignment: horiz right; pattern: pattern solid, fore_colour gray25',
        num_format_str='0.00%')


    font_style = XFStyle()
    font_style.font.bold = True
    font_style2 = XFStyle()
    font_style2.font.bold = False
    # output_folder = os.path.join(os.path.join(SITE_STORAGE, 'media', 'arreglos'))
    output_folder = os.path.join(os.path.join(SITE_STORAGE, 'media'))

    libdestino = xlwt.Workbook()
    hojadestino = libdestino.add_sheet("Listado")

    hojadestino.write_merge(0, 0, 0, 14, 'UNIVERSIDAD ESTATAL DE MILAGRO', titulo)
    hojadestino.write_merge(1, 1, 0, 14, 'DIRECCIÓN DE INVESTIGACIÓN Y POSGRADO', titulo2)
    hojadestino.write_merge(2, 2, 0, 14, 'PROYECCIÓN DE COBROS POSGRADO', titulo2)
    # hojadestino.write_merge(2, 2, 0, 14, 'EDAD DE LA CARTERA VENCIDA DEL MES DE ' + meses[
    #     int(mes_actual) - 1].upper() + ' DEL ' + anio_actual, titulo2)

    fila = 4

    columnas = [
        (u"PROGRAMAS", 8000),
        (u"PROG.", 2500),
        (u" # COHORTE", 2500),
        (u"PERIODO", 8000),
        (u"FECHA PERIODO INICIAL", 3000),
        (u"FECHA PERIDO FINAL", 3000),
        (u"ESTUDIANTE", 10000),
        (u"IDENTIFICACIÓN", 3900),
        (u"ESTADO", 4000),
        (u"COSTO DEL PROGRAMA", 4000),
        (u"VALOR TOTAL PROGRAMA", 4000),
        (u"VALOR TOTAL DE RUBROS", 4000),
        (u"VALOR MÓDULO REPROBADO", 4000),
        (u"VALOR PRÓRROGA TITULACION", 4000),
        (u"SALDO ACTUAL", 4000),
        (u"OBSERVACIONES", 15000)
    ]

    for col_num in range(len(columnas)):
        hojadestino.write_merge(fila, fila + 1, col_num, col_num, columnas[col_num][0], fuentecabecera)
        # hojadestino.write(fila, col_num, columnas[col_num][0], fuentecabecera)
        hojadestino.col(col_num).width = columnas[col_num][1]

    # cedulas = ['0928364082', '0926475260', '0942191156','0919619122','0922875430']
    cedulas = ['0923605976']

    matriculas = Matricula.objects.filter(status=True, nivel__periodo__tipo__id__in=[3, 4]
                                          # inscripcion__persona__cedula__in=cedulas
                                          # inscripcion__persona__cedula__in=['0916362163', '0928477934','0916954613', '0919850255']
                                          # inscripcion__carrera__id=60,
                                          # nivel__periodo__id__in=[12, 13, 78, 84, 91],
                                          ).exclude(nivel__periodo__pk__in=[120, 128]).distinct().order_by('inscripcion__persona__apellido1',
                                                                'inscripcion__persona__apellido2',
                                                                'inscripcion__persona__nombres')


    totalmatriculas = matriculas.count()

    # print(totalmatriculas)
    c = 0

    horainicio = datetime.now()

    totalalumnos = 0

    totalsaldoinicial = 0
    totalrubros = 0
    totalpagado = 0
    totalsaldofinal = 0

    fila = 6
    cedula = ''

    totalprograma = 0
    totalcobrado = 0
    totalsaldovencido = 0
    totaledad1 = 0
    totaledad2 = 0
    totaledad3 = 0
    totaledad4 = 0
    totalsaldovencer = 0
    c = 1

    print(".:: GENERACIÓN DE LISTADO GENERAL DE MAESTRANTES PARA DETECTAR NOVEDADES EN RUBROS ::.")

    for matricula in matriculas:

        print("Procesando ",c, " de ", totalmatriculas)
        periodo = matricula.nivel.periodo
        costoprograma = Decimal(null_to_decimal(
            periodo.periodocarreracosto_set.filter(carrera=matricula.inscripcion.carrera,
                                                   status=True).aggregate(costo=Sum('costo'))[
                'costo'])).quantize(Decimal('.01'))
        valordescontado = 0

        if matricula.matriculanovedad_set.filter(tipo=1).exists():
            novedad = matricula.matriculanovedad_set.filter(tipo=1)[0]
            motivo = '%s' % novedad.motivo
            porcentaje = Decimal(novedad.porcentajedescuento).quantize(
                Decimal('.01')) if novedad.porcentajedescuento else 0
            if porcentaje > 0:
                valordescontado = Decimal(null_to_decimal((costoprograma * porcentaje) / 100, 2)).quantize(
                    Decimal('.01'))

        if matricula.descuentoposgradomatricula_set.filter(status=True, estado=2).exists():
            descuentoayuda = matricula.descuentoposgradomatricula_set.filter(status=True, estado=2)[0]
            porcentaje = Decimal(null_to_decimal(descuentoayuda.detalleconfiguraciondescuentoposgrado.configuraciondescuentoposgrado.porcentaje, 2))
            if porcentaje > 0:
                valordescontado = descuentoayuda.valordescuento
                # valorrubros = costoprograma - valordescontado
            else:
                valordescontado = Decimal(0)
                # porcentaje = round((valorrubros * 100) / costoprograma, 2)
                # valorrubros = costoprograma - valordescontado


        valornetoprograma = costoprograma - valordescontado

        if matricula.retirado_programa_maestria():
            print("Retirado", valornetoprograma, " - ", matricula.total_generado_alumno_retirado())
            print(matricula.inscripcion.persona.cedula)
            valornetoprograma = matricula.total_generado_alumno_retirado()
            valorsaldo = matricula.total_saldo_alumno_retirado()
        else:
            valorsaldo = matricula.total_saldo_rubrosinanular_rubro_maestria()

        valorubrosgenerados = matricula.total_generado_alumno_solo_rubros_maestria()

        valormoduloreprobado = Decimal(null_to_decimal(
            Rubro.objects.values_list('valor').filter(persona=matricula.inscripcion.persona, status=True, tipo__subtiporubro=2).aggregate(valor=Sum('valortotal'))[
                'valor'], 2)).quantize(Decimal('.01'))

        observacionreprobado = ""
        if Rubro.objects.values_list('valor').filter(persona=matricula.inscripcion.persona, matricula__isnull=True, status=True, tipo__subtiporubro=2).exists():
            observacionreprobado = "REGISTRA RUBRO POR MODULO REPROBADO PERO NO ESTÁ LIGADO A LA MATRÍCULA"


        valorprorroga = Decimal(null_to_decimal(
            Rubro.objects.values_list('valor').filter(persona=matricula.inscripcion.persona, status=True, tipo__subtiporubro=3).aggregate(valor=Sum('valortotal'))[
                'valor'], 2)).quantize(Decimal('.01'))
        observacionprorroga = ""
        if Rubro.objects.values_list('valor').filter(persona=matricula.inscripcion.persona, matricula__isnull=True, status=True, tipo__subtiporubro=3).exists():
            observacionprorroga = "REGISTRA RUBRO POR PRORROGA TITULACION PERO NO ESTÁ LIGADO A LA MATRÍCULA"


        hojadestino.write(fila, 0, matricula.inscripcion.carrera.nombre, fuentenormal)
        hojadestino.write(fila, 1, matricula.inscripcion.carrera.alias, fuentenormalcent)
        hojadestino.write(fila, 2, matricula.nivel.periodo.cohorte, fuentenormalcent)
        hojadestino.write(fila, 3, matricula.nivel.periodo.nombre, fuentenormal)
        hojadestino.write(fila, 4, matricula.nivel.periodo.inicio, fuentefecha)
        hojadestino.write(fila, 5, matricula.nivel.periodo.fin, fuentefecha)
        hojadestino.write(fila, 6, matricula.inscripcion.persona.nombre_completo_inverso(), fuentenormal)
        hojadestino.write(fila, 7, matricula.inscripcion.persona.identificacion(), fuentenormal)
        hojadestino.write(fila, 8, matricula.estado_inscripcion_maestria(), fuentenormal)
        hojadestino.write(fila, 9, costoprograma, fuentemoneda)
        hojadestino.write(fila, 10, valornetoprograma, fuentemoneda)
        hojadestino.write(fila, 11, valorubrosgenerados, fuentemoneda)
        hojadestino.write(fila, 12, valormoduloreprobado, fuentemoneda)
        hojadestino.write(fila, 13, valorprorroga, fuentemoneda)
        hojadestino.write(fila, 14, valorsaldo, fuentemoneda)

        observacion = ""
        if not matricula.retirado_programa_maestria():
            if matricula.inscripcion.carrera.id == 36 and matricula.nivel.periodo.id == 8:
                if abs(valornetoprograma - valorubrosgenerados) > 10:
                    observacion = "EL TOTAL DEL PROGRAMA Y DE LOS RUBROS NO SON IGUALES"
            else:
                if valornetoprograma != valorubrosgenerados:
                    observacion = "EL TOTAL DEL PROGRAMA Y DE LOS RUBROS NO SON IGUALES"
        else:
            if matricula.total_generado_alumno_retirado() > 0:
                if matricula.total_generado_alumno_solo_rubros_maestria() != matricula.total_generado_alumno_retirado():
                    observacion = "ALUMNO RETIRADO: EL TOTAL DEL PROGRAMA Y DE LOS RUBROS NO SON IGUALES"
            else:
                if matricula.inscripcion.persona.rubro_set.filter(status=True, cancelado=True, tipo__id=2845).exists():
                    observacion =  "ALUMNO RETIRADO: TIENE RUBRO MATRICULA PAGADO PERO NO ATADO A LA MATRICULA"

        if observacionreprobado:
            if observacion:
                observacion = observacion + "; " + observacionreprobado
            else:
                observacion = observacionreprobado

        if observacionprorroga:
            if observacion:
                observacion = observacion + "; " + observacionprorroga
            else:
                observacion = observacionprorroga

        hojadestino.write(fila, 15, observacion, fuentenormal)

        fila += 1
        c += 1



    print("Inicio: ", horainicio)
    print("Fin: ", datetime.now())

    libdestino.save(output_folder + "/POSGRADO_NOVEDADES_04052022.xls")
    print("Archivo creado. . .")

@transaction.atomic()
def generar_financiamiento_posgrado_pestania_data():
    guardar_en_base = True

    conexion = connections['epunemi']
    cnepunemi = conexion.cursor()
    try:
        fuentecabecera = easyxf(
            'font: name Verdana, color-index black, bold on, height 150; pattern: pattern solid, fore_colour gray25; alignment: vert distributed, horiz centre; borders: left thin, right thin, top thin, bottom thin')
        fuentenormal = easyxf(
            'font: name Verdana, color-index black, height 150; borders: left thin, right thin, top thin, bottom thin')
        fuentenormalwrap = easyxf(
            'font: name Verdana, color-index black, height 150; borders: left thin, right thin, top thin, bottom thin')
        fuentenormalneg = easyxf(
            'font: name Verdana, color-index black, bold on , height 150; borders: left thin, right thin, top thin, bottom thin')
        fuentenormalnegrell = easyxf(
            'font: name Verdana, color-index black, bold on , height 150; borders: left thin, right thin, top thin, bottom thin; pattern: pattern solid, fore_colour gray25')
        fuentenormalwrap.alignment.wrap = True
        fuentenormalcent = easyxf(
            'font: name Verdana, color-index black, height 150; borders: left thin, right thin, top thin, bottom thin; alignment: horiz centre')
        fuentemoneda = easyxf(
            'font: name Verdana, color-index black, height 150; borders: left thin, right thin, top thin, bottom thin; alignment: horiz right',
            num_format_str=' "$" #,##0.00')
        fuentemonedaneg = easyxf(
            'font: name Verdana, color-index black, bold on, height 150; borders: left thin, right thin, top thin, bottom thin; alignment: horiz right; pattern: pattern solid, fore_colour gray25',
            num_format_str=' "$" #,##0.00')
        fuentefecha = easyxf(
            'font: name Verdana, color-index black, height 150; borders: left thin, right thin, top thin, bottom thin; alignment: horiz center',
            num_format_str='yyyy-mm-dd')
        fuentenumerodecimal = easyxf(
            'font: name Verdana, color-index black, height 150; borders: left thin, right thin, top thin, bottom thin; alignment: horiz right',
            num_format_str='#,##0.00')
        fuentenumeroentero = easyxf(
            'font: name Verdana, color-index black, height 150; borders: left thin, right thin, top thin, bottom thin; alignment: horiz right')


        output_folder = os.path.join(os.path.join(SITE_STORAGE, 'media'))
        # output_folder = os.path.join(os.path.join(SITE_STORAGE, 'media', 'archivosparaprocesos'))
        # liborigen = xlrd.open_workbook(output_folder + '/POSGRADO_10.xlsx')
        liborigen = xlrd.open_workbook(output_folder + '/POSGRADO_20.xls')

        libdestino = xlwt.Workbook()
        hojadestino = libdestino.add_sheet("Listado")

        fil = 0

        columnas = [
            (u"Programa", 7000),
            (u"Cohorte", 2500),
            (u"Año", 2000),
            (u"Modalidad", 4000),
            (u"Cédula", 4500),
            (u"Estudiante", 9000),
            (u"Valor en Sistema", 4000),
            (u"Corrección", 4000),
            (u"Total a Amortizar", 4000),
            (u"# Cuotas", 4000),
            (u"Valor Cuota", 4000),
            (u"Total", 4000),
            (u"Desde", 3000),
            (u"Hasta", 3000),
            (u"Nombre de Rubro", 6000),
            (u"Observación", 9000),
            (u"Procesar", 2000),
            (u"IDRubroUnemi", 2000),
            (u"Valor", 3000),
            (u"Valor Total", 3000),
            (u"Saldo", 3000),
            (u"Cancelado", 3000),
            (u"Bloqueado Rubro", 3000)
        ]

        for col_num in range(len(columnas)):
            hojadestino.write(fil, col_num, columnas[col_num][0], fuentecabecera)
            hojadestino.col(col_num).width = columnas[col_num][1]

        print(".:: Bloqueando rubros en epunemi ::.")

        sheet = liborigen.sheet_by_index(0)

        c = 1
        filadest = 1
        matriculados = 0
        nomatriculados = 0
        matriculados = 0
        doblematricula = 0

        for fila in range(sheet.nrows):
            if fila >= 2:
                cols = sheet.row_values(fila)
                carrera = cols[0].strip()
                cohorte = cols[1].strip()
                anio = int(cols[2])
                modalidad = cols[3].strip()
                cedula = cols[4].strip() if type(cols[4]) == str else str(int(cols[4])).strip()
                nombres = cols[5].strip()
                valorensistema = Decimal(cols[6]).quantize(Decimal('.01'))
                correccion = Decimal(cols[7]).quantize(Decimal('.01'))
                totalamortizar = Decimal(cols[8]).quantize(Decimal('.01'))
                numerocuotas = int(cols[9])
                valorcuota = Decimal(cols[10]).quantize(Decimal('.01'))
                total = Decimal(cols[11]).quantize(Decimal('.01'))

                fechadesde = xlrd.xldate.xldate_as_datetime(cols[12], liborigen.datemode).date()
                fechahasta = xlrd.xldate.xldate_as_datetime(cols[13], liborigen.datemode).date()
                nombrerubro = cols[14].strip()

                rubro = cols[14].strip()
                # print("Procesando ", c)
                # print(cedula, " - ", nombres, "-", carrera)

                if cedula == '0502868862':
                    print("Revisar")

                hojadestino.write(filadest, 0, carrera, fuentenormal)
                hojadestino.write(filadest, 1, cohorte, fuentenormal)
                hojadestino.write(filadest, 2, anio, fuentenumeroentero)
                hojadestino.write(filadest, 3, modalidad, fuentenormal)
                hojadestino.write(filadest, 4, cedula, fuentenormal)
                hojadestino.write(filadest, 5, nombres, fuentenormal)
                hojadestino.write(filadest, 6, valorensistema, fuentemoneda)
                hojadestino.write(filadest, 7, correccion, fuentemoneda)
                hojadestino.write(filadest, 8, totalamortizar, fuentemoneda)
                hojadestino.write(filadest, 9, numerocuotas, fuentenumeroentero)
                hojadestino.write(filadest, 10, valorcuota, fuentemoneda)
                hojadestino.write(filadest, 11, total, fuentemoneda)
                hojadestino.write(filadest, 12, fechadesde, fuentefecha)
                hojadestino.write(filadest, 13, fechahasta, fuentefecha)
                hojadestino.write(filadest, 14, nombrerubro, fuentenormal)

                # Verifico si tiene matricula
                if Matricula.objects.filter(status=True, inscripcion__persona__cedula=cedula, nivel__periodo__tipo__id__in=[3, 4], retiradomatricula=False).exists():
                    # Verifico que tenga una sola matricula de posgrado
                    if Matricula.objects.filter(status=True, inscripcion__persona__cedula=cedula, nivel__periodo__tipo__id__in=[3, 4], retiradomatricula=False).count() == 1:
                        matricula = Matricula.objects.get(status=True, inscripcion__persona__cedula=cedula, nivel__periodo__tipo__id__in=[3, 4], retiradomatricula=False)
                        print(matricula)
                        matriculados += 1
                        total_rubros = 0

                        # Consulto rubro o rubros
                        for rubro in matricula.rubro_set.filter(status=True):
                            print(rubro.id)
                            print(rubro.tipo.nombre)
                            print(rubro.valortotal)
                            total_rubros += 1

                        print("Total rubros ", total_rubros)

                        # Si no tiene rubros
                        if total_rubros == 0:
                            hojadestino.write(filadest, 15, "NO TIENE ASIGNADO RUBRO", fuentenormal)
                            hojadestino.write(filadest, 16, "NO", fuentenormal)
                            hojadestino.write(filadest, 17, "", fuentenormal)
                            hojadestino.write(filadest, 18, "", fuentenormal)
                            hojadestino.write(filadest, 19, "", fuentenormal)
                            hojadestino.write(filadest, 20, "", fuentenormal)
                            hojadestino.write(filadest, 21, "", fuentenormal)
                            hojadestino.write(filadest, 22, "", fuentenormal)
                        elif total_rubros > 1:
                            hojadestino.write(filadest, 15, "YA TIENE ASIGNADO RUBROS POR FINANCIAMIENTO", fuentenormal)
                            hojadestino.write(filadest, 16, "NO", fuentenormal)
                            hojadestino.write(filadest, 17, "", fuentenormal)
                            hojadestino.write(filadest, 18, "", fuentenormal)
                            hojadestino.write(filadest, 19, "", fuentenormal)
                            hojadestino.write(filadest, 20, "", fuentenormal)
                            hojadestino.write(filadest, 21, "", fuentenormal)
                            hojadestino.write(filadest, 22, "", fuentenormal)
                        else:
                            # Verifico que exista en epunemi y tenga el mismo valor
                            rubro_unemi = matricula.rubro_set.filter(status=True)[0]

                            sql = """SELECT ru.id,ru.nombre,ru.valor,ru.valortotal,ru.saldo, ru.totalunemi, ru.observacion,ru.refinanciado,ru.bloqueado FROM sagest_rubro as ru WHERE ru.status=True AND ru.anulado=FALSE AND ru.idrubrounemi=%s;""" % (rubro_unemi.id)
                            cnepunemi.execute(sql)
                            rubroepunemi = cnepunemi.fetchone()
                            if rubroepunemi is not None:
                                # Comparo valores
                                print("ID epunemi:",rubroepunemi[0])
                                print("NOMBRE:", rubroepunemi[1])
                                print("VALOR EPUNEMI:", rubroepunemi[2], "-", rubro_unemi.valor)
                                print("VALOR TOTAL EPUNEMI:",rubroepunemi[3], "-", rubro_unemi.valortotal)
                                print("SALDO EPUNEMI:",rubroepunemi[4], "-", rubro_unemi.saldo)
                                print("TOTAL UNEMI:",rubroepunemi[5])
                                print("OBSERVACION:", rubroepunemi[6])
                                print("REFINANCIADO:",rubroepunemi[7])
                                print("BLOQUEADO:",rubroepunemi[8])

                                if cedula == '1310198096':
                                    print("Hey!!!")

                                valor_rubro_epunemi = rubroepunemi[2]
                                valor_rubro_total_epunemi = rubroepunemi[3]
                                valor_saldo_epunemi = rubroepunemi[4]
                                valor_pagado = rubro_unemi.valortotal - rubro_unemi.saldo

                                # Bloqueo el rubro en epunemi para evitar cobro
                                sql = """UPDATE sagest_rubro SET bloqueado=TRUE, bloqueadopornovedad=TRUE WHERE idrubrounemi=%s AND status=true""" % (rubro_unemi.id)
                                cnepunemi.execute(sql)

                                # Si los rubros no son diferentes
                                if rubroepunemi[2] == rubro_unemi.valor and rubroepunemi[3] == rubro_unemi.valortotal and rubroepunemi[4] == rubro_unemi.saldo:
                                    # Si lo pagado es igual al valor a corregir
                                    if valor_pagado == correccion:
                                        hojadestino.write(filadest, 15, "", fuentenormal)
                                        hojadestino.write(filadest, 16, "SI", fuentenormal)
                                        hojadestino.write(filadest, 17, rubro_unemi.id, fuentenumeroentero)
                                        hojadestino.write(filadest, 18, rubro_unemi.valor, fuentemoneda)
                                        hojadestino.write(filadest, 19, rubro_unemi.valortotal, fuentemoneda)
                                        hojadestino.write(filadest, 20, rubro_unemi.saldo, fuentemoneda)
                                        hojadestino.write(filadest, 21, rubro_unemi.cancelado, fuentenormal)
                                        hojadestino.write(filadest, 22, "RUBRO BLOQUEADO", fuentenormal)


                                        # Genero las fechas y valores de las cuotas
                                        print("Total amortizar:", totalamortizar)
                                        print("Cuotas:", numerocuotas)
                                        fecha = fechadesde
                                        sumacuotas = 0
                                        valorcuota = Decimal(null_to_decimal(totalamortizar / numerocuotas, 2)).quantize(Decimal('.01'))

                                        # Consulto tipo de rubro
                                        tiporubro = TipoOtroRubro.objects.get(nombre=nombrerubro)

                                        # Bloqueo el rubro en epunemi para evitar cobro
                                        sql = """UPDATE sagest_rubro SET bloqueado=TRUE, bloqueadopornovedad=TRUE WHERE idrubrounemi=%s AND status=true""" % (rubro_unemi.id)
                                        cnepunemi.execute(sql)

                                        if guardar_en_base:
                                            # Actualizo rubro original en unemi
                                            rubro_unemi.valor = correccion
                                            rubro_unemi.valortotal = correccion
                                            rubro_unemi.saldo = 0
                                            rubro_unemi.cancelado = True
                                            rubro_unemi.save()

                                            print(".:: Rubro actualizado en UNEMI ::.")

                                            # Guardo financiamiento
                                            financiamiento = FinanciamientoPosgrado(
                                                persona=matricula.inscripcion.persona,
                                                matricula=matricula,
                                                costoprograma=valorensistema,
                                                descuento=0,
                                                totalprograma=valorensistema,
                                                pagado=correccion,
                                                pendiente=totalamortizar,
                                                montofinanciar=totalamortizar,
                                                cantidadcuota=numerocuotas,
                                                observacion='SOLICITADO POR EXPERTA DE POSGRADO  VÍA E-MAIL EL 08/07/2022',
                                                legalizado=False
                                            )
                                            financiamiento.save()

                                            print(".:: Financiamiento creado en UNEMI ::.")

                                            # Consulto pagos del rubro
                                            pagosrubro = rubro_unemi.pago_set.filter(status=True).order_by('-fecha')
                                            fechapago = pagosrubro[0].fecha

                                            # Guardo primera cuota de financiamiento que fue pagada
                                            cuota_financiamiento = FinanciamientoPosgradoDetalle(
                                                financiamiento=financiamiento,
                                                rubro=rubro_unemi,
                                                valor=rubro_unemi.valortotal,
                                                fechaemite=rubro_unemi.fecha,
                                                fechavence=rubro_unemi.fechavence,
                                                fechapago=fechapago,
                                                pagado=True,
                                                totalpagado=rubro_unemi.valortotal,
                                                saldo=0,
                                                financiado=False
                                            )
                                            cuota_financiamiento.save()

                                            print(".:: Detalle de financiamiento creado en UNEMI ::.")

                                            # Actualizo rubro original en epunemi
                                            sql = """UPDATE sagest_rubro SET valor=%s, valortotal=%s, saldo=0, cancelado=TRUE, totalunemi=%s WHERE idrubrounemi=%s AND status=true""" % (correccion, correccion, correccion, rubro_unemi.id)
                                            cnepunemi.execute(sql)

                                            print(".:: Rubro actualizado en EPUNEMI ::.")

                                        for n in range(1, numerocuotas + 1):
                                            if n == numerocuotas:
                                                valorcuota = totalamortizar - sumacuotas
                                            else:
                                                sumacuotas += valorcuota

                                            print("Cuota ", n, " - ", fecha, " - ", valorcuota)
                                            print(tiporubro)

                                            if guardar_en_base:
                                                # Creo nuevo rubro en unemi
                                                nuevo_rubro_unemi = Rubro(fecha=datetime.now().date(),
                                                      valor=valorcuota,
                                                      valortotal=valorcuota,
                                                      saldo=valorcuota,
                                                      persona=matricula.inscripcion.persona,
                                                      matricula=matricula,
                                                      nombre=tiporubro.nombre,
                                                      tipo=tiporubro,
                                                      cancelado=False,
                                                      observacion='',
                                                      iva_id=1,
                                                      epunemi=True,
                                                      fechavence=fecha,
                                                      compromisopago=None,
                                                      bloqueado=False
                                                      )

                                                nuevo_rubro_unemi.save()

                                                print(".:: Rubro creado en UNEMI ::.")

                                                # Creo detalle de financiamiento con el nuevo rubro creado

                                                cuota_financiamiento = FinanciamientoPosgradoDetalle(
                                                    financiamiento=financiamiento,
                                                    rubro=nuevo_rubro_unemi,
                                                    valor=nuevo_rubro_unemi.valortotal,
                                                    fechaemite=nuevo_rubro_unemi.fecha,
                                                    fechavence=nuevo_rubro_unemi.fechavence,
                                                    fechapago=None,
                                                    pagado=False,
                                                    totalpagado=0,
                                                    saldo=nuevo_rubro_unemi.valortotal,
                                                    financiado=True
                                                )
                                                cuota_financiamiento.save()

                                                print(".:: Detalle de financiamiento creado en UNEMI ::.")

                                                # Consulto la persona por cedula en base de epunemi
                                                sql = """SELECT pe.id FROM sga_persona AS pe WHERE pe.cedula='%s' AND pe.status=TRUE;  """ % (cedula)
                                                cnepunemi.execute(sql)
                                                registro = cnepunemi.fetchone()
                                                codigoalumno = registro[0]

                                                # Consulto el tipo otro rubro en epunemi
                                                sql = """SELECT id FROM sagest_tipootrorubro WHERE idtipootrorubrounemi=%s; """ % (tiporubro.id)
                                                cnepunemi.execute(sql)
                                                registro = cnepunemi.fetchone()

                                                # Si existe
                                                if registro is not None:
                                                    tipootrorubro = registro[0]
                                                else:
                                                    # Debo crear ese tipo de rubro
                                                    # Consulto centro de costo
                                                    sql = """SELECT id FROM sagest_centrocosto WHERE status=True AND unemi=True AND tipo=%s;""" % (tiporubro.tiporubro)
                                                    cnepunemi.execute(sql)
                                                    centrocosto = cnepunemi.fetchone()
                                                    idcentrocosto = centrocosto[0]

                                                    # Consulto la cuenta contable
                                                    cuentacontable = CuentaContable.objects.get(partida=tiporubro.partida, status=True)

                                                    # Creo el tipo de rubro en epunemi
                                                    sql = """ Insert Into sagest_tipootrorubro (status, nombre, partida_id, valor, interface, activo, ivaaplicado_id, nofactura, exportabanco, cuentacontable_id, centrocosto_id, tiporubro, idtipootrorubrounemi, unemi)
                                                                        VALUES(TRUE, '%s', %s, %s, FALSE, TRUE, %s, FALSE, TRUE, %s, %s, 1, %s, TRUE); """ % (
                                                        tiporubro.nombre, cuentacontable.partida.id, tiporubro.valor,
                                                        tiporubro.ivaaplicado.id, cuentacontable.id, idcentrocosto,
                                                        tiporubro.id)
                                                    cnepunemi.execute(sql)

                                                    print(".:: Tipo de Rubro creado en EPUNEMI ::.")

                                                    # Obtengo el id recién creado del tipo de rubro
                                                    sql = """SELECT id FROM sagest_tipootrorubro WHERE idtipootrorubrounemi=%s; """ % (tiporubro.id)
                                                    cnepunemi.execute(sql)
                                                    registro = cnepunemi.fetchone()
                                                    tipootrorubro = registro[0]


                                                # Creo nuevo rubro en epunemi
                                                sql = """ INSERT INTO sagest_rubro (status, cuota, tipocuota, valoriva, tienenotacredito, valornotacredito, valordescuento, anulado, fecha, valor ,valortotal, saldo, persona_id, nombre, tipo_id, cancelado, observacion, iva_id, idrubrounemi, totalunemi, fechavence, compromisopago, bloqueado, refinanciado, bloqueadopornovedad, titularcambiado, coactiva, fecha_creacion, usuario_creacion_id) 
                                                          VALUES (TRUE, 0, 3, 0, FALSE, 0, 0, FALSE, NOW(),                   %s, %s,    %s, %s,     '%s', %s,   FALSE,    '',              1,   %s,        %s,     '/%s/',   %s, FALSE, FALSE, FALSE, FALSE, FALSE, NOW(), 1); """ \
                                                      % (valorcuota, valorcuota, valorcuota, codigoalumno, tiporubro.nombre, tipootrorubro, nuevo_rubro_unemi.id, valorcuota, fecha, 0)
                                                cnepunemi.execute(sql)

                                                print(".:: Rubro creado en EPUNEMI ::.")

                                            fecha = fechadesde + relativedelta(months=n)

                                        # Desbloqueo el rubro en epunemi
                                        sql = """UPDATE sagest_rubro SET bloqueado=FALSE, bloqueadopornovedad=FALSE WHERE idrubrounemi=%s AND status=true""" % (rubro_unemi.id)
                                        cnepunemi.execute(sql)
                                    else:
                                        # Bloqueo el rubro en epunemi para evitar que sigan cobrando y existan diferencias
                                        sql = """UPDATE sagest_rubro SET bloqueado=TRUE, bloqueadopornovedad=TRUE WHERE idrubrounemi=%s AND status=true""" % (rubro_unemi.id)
                                        cnepunemi.execute(sql)

                                        hojadestino.write(filadest, 15, "VALOR PAGADO Y DE CORRECCION NO SON IGUALES", fuentenormal)
                                        hojadestino.write(filadest, 16, "NO", fuentenormal)
                                        hojadestino.write(filadest, 17, rubro_unemi.id, fuentenumeroentero)
                                        hojadestino.write(filadest, 18, "", fuentenormal)
                                        hojadestino.write(filadest, 19, "", fuentenormal)
                                        hojadestino.write(filadest, 20, "", fuentenormal)
                                        hojadestino.write(filadest, 21, "", fuentenormal)
                                        hojadestino.write(filadest, 22, "RUBRO BLOQUEADO", fuentenormal)

                                else:
                                    hojadestino.write(filadest, 15, "DIFERENCIAS DE VALORES DE LOS RUBROS UNEMI-EPUNEMI", fuentenormal)
                                    hojadestino.write(filadest, 16, "NO", fuentenormal)
                                    hojadestino.write(filadest, 17, rubro_unemi.id, fuentenumeroentero)
                                    hojadestino.write(filadest, 18, "", fuentenormal)
                                    hojadestino.write(filadest, 19, "", fuentenormal)
                                    hojadestino.write(filadest, 20, "", fuentenormal)
                                    hojadestino.write(filadest, 21, "", fuentenormal)
                                    hojadestino.write(filadest, 22, "RUBRO BLOQUEADO", fuentenormal)
                            else:
                                hojadestino.write(filadest, 15, "NO EXISTE EN EPUNEMI", fuentenormal)
                                hojadestino.write(filadest, 16, "NO", fuentenormal)
                                hojadestino.write(filadest, 17, "", fuentenormal)
                                hojadestino.write(filadest, 18, "", fuentenormal)
                                hojadestino.write(filadest, 19, "", fuentenormal)
                                hojadestino.write(filadest, 20, "", fuentenormal)
                                hojadestino.write(filadest, 21, "", fuentenormal)
                                hojadestino.write(filadest, 22, "", fuentenormal)

                    else:
                        # print("Doble matricula")
                        # for m in Matricula.objects.filter(status=True, inscripcion__persona__cedula=cedula, nivel__periodo__tipo__id__in=[3, 4]):
                        #     print(m)
                        hojadestino.write(filadest, 15, "TIENE DOBLE MATRICULA", fuentenormal)
                        hojadestino.write(filadest, 16, "NO", fuentenormal)
                        hojadestino.write(filadest, 17, "", fuentenormal)
                        hojadestino.write(filadest, 18, "", fuentenormal)
                        hojadestino.write(filadest, 19, "", fuentenormal)
                        hojadestino.write(filadest, 20, "", fuentenormal)
                        hojadestino.write(filadest, 21, "", fuentenormal)
                        hojadestino.write(filadest, 22, "", fuentenormal)
                        doblematricula += 1
                else:
                    # print(cedula, " - ", nombres, "-", carrera)
                    # print("No existe la matrícula")
                    hojadestino.write(filadest, 15, "NO ESTÁ MATRICULADO", fuentenormal)
                    hojadestino.write(filadest, 16, "NO", fuentenormal)
                    hojadestino.write(filadest, 17, "", fuentenormal)
                    hojadestino.write(filadest, 18, "", fuentenormal)
                    hojadestino.write(filadest, 19, "", fuentenormal)
                    hojadestino.write(filadest, 20, "", fuentenormal)
                    hojadestino.write(filadest, 21, "", fuentenormal)
                    hojadestino.write(filadest, 22, "", fuentenormal)

                    nomatriculados += 1

                filadest += 1
                c += 1

        conexion.commit()
        cnepunemi.close()

        libdestino.save(output_folder + "/PROCESADOS_POSGRADO_20.xls")

        print("Matriculados:", matriculados)
        print("No matriculados:", nomatriculados)
        print("Doble matrícula:", doblematricula)
        print("Proceso finalizado. . .")
    except Exception as ex:
        transaction.set_rollback(True)
        msg = ex.__str__()
        print(msg)

@transaction.atomic()
def generar_financiamiento_posgrado_con_cuota_adicional():
    guardar_en_base = True

    conexion = connections['epunemi']
    cnepunemi = conexion.cursor()
    try:
        fuentecabecera = easyxf(
            'font: name Verdana, color-index black, bold on, height 150; pattern: pattern solid, fore_colour gray25; alignment: vert distributed, horiz centre; borders: left thin, right thin, top thin, bottom thin')
        fuentenormal = easyxf(
            'font: name Verdana, color-index black, height 150; borders: left thin, right thin, top thin, bottom thin')
        fuentenormalwrap = easyxf(
            'font: name Verdana, color-index black, height 150; borders: left thin, right thin, top thin, bottom thin')
        fuentenormalneg = easyxf(
            'font: name Verdana, color-index black, bold on , height 150; borders: left thin, right thin, top thin, bottom thin')
        fuentenormalnegrell = easyxf(
            'font: name Verdana, color-index black, bold on , height 150; borders: left thin, right thin, top thin, bottom thin; pattern: pattern solid, fore_colour gray25')
        fuentenormalwrap.alignment.wrap = True
        fuentenormalcent = easyxf(
            'font: name Verdana, color-index black, height 150; borders: left thin, right thin, top thin, bottom thin; alignment: horiz centre')
        fuentemoneda = easyxf(
            'font: name Verdana, color-index black, height 150; borders: left thin, right thin, top thin, bottom thin; alignment: horiz right',
            num_format_str=' "$" #,##0.00')
        fuentemonedaneg = easyxf(
            'font: name Verdana, color-index black, bold on, height 150; borders: left thin, right thin, top thin, bottom thin; alignment: horiz right; pattern: pattern solid, fore_colour gray25',
            num_format_str=' "$" #,##0.00')
        fuentefecha = easyxf(
            'font: name Verdana, color-index black, height 150; borders: left thin, right thin, top thin, bottom thin; alignment: horiz center',
            num_format_str='yyyy-mm-dd')
        fuentenumerodecimal = easyxf(
            'font: name Verdana, color-index black, height 150; borders: left thin, right thin, top thin, bottom thin; alignment: horiz right',
            num_format_str='#,##0.00')
        fuentenumeroentero = easyxf(
            'font: name Verdana, color-index black, height 150; borders: left thin, right thin, top thin, bottom thin; alignment: horiz right')


        output_folder = os.path.join(os.path.join(SITE_STORAGE, 'media'))
        liborigen = xlrd.open_workbook(output_folder + '/POSGRADO_8.xlsx')

        libdestino = xlwt.Workbook()
        hojadestino = libdestino.add_sheet("Listado")

        fil = 0

        columnas = [
            (u"Programa", 7000),
            (u"Cohorte", 2500),
            (u"Año", 2000),
            (u"Modalidad", 4000),
            (u"Cédula", 4500),
            (u"Estudiante", 9000),
            (u"Valor en Sistema", 4000),
            (u"Corrección", 4000),
            (u"Total a Amortizar", 4000),
            (u"# Cuotas", 4000),
            (u"Valor Cuota", 4000),
            (u"# Cuota Adicional", 4000),
            (u"Valor Cuota Adicional", 4000),
            (u"Total", 4000),
            (u"Desde", 3000),
            (u"Hasta", 3000),
            (u"Nombre de Rubro", 6000),
            (u"Observación", 9000),
            (u"Procesar", 2000),
            (u"IDRubroUnemi", 2000),
            (u"Valor", 3000),
            (u"Valor Total", 3000),
            (u"Saldo", 3000),
            (u"Cancelado", 3000),
            (u"Bloqueado Rubro", 3000)
        ]

        for col_num in range(len(columnas)):
            hojadestino.write(fil, col_num, columnas[col_num][0], fuentecabecera)
            hojadestino.col(col_num).width = columnas[col_num][1]


        sheet = liborigen.sheet_by_index(0)

        c = 1
        filadest = 1
        matriculados = 0
        nomatriculados = 0
        matriculados = 0
        doblematricula = 0

        for fila in range(sheet.nrows):
            if fila >= 2:
                cols = sheet.row_values(fila)
                carrera = cols[0].strip()
                cohorte = cols[1].strip()
                anio = int(cols[2])
                modalidad = cols[3].strip()
                cedula = cols[4].strip() if type(cols[4]) == str else str(int(cols[4])).strip()
                nombres = cols[5].strip()
                valorensistema = Decimal(cols[6]).quantize(Decimal('.01'))
                correccion = Decimal(cols[7]).quantize(Decimal('.01'))
                totalamortizar = Decimal(cols[8]).quantize(Decimal('.01'))
                numerocuotas = int(cols[9])
                valorcuota = Decimal(cols[10]).quantize(Decimal('.01'))
                numerocuotaadicional = int(cols[11]) if type(cols[11]) != str else 0
                valorcuotaadicional = Decimal(cols[12]).quantize(Decimal('.01')) if numerocuotaadicional > 0 else 0
                total = Decimal(cols[13]).quantize(Decimal('.01'))

                fechadesde = xlrd.xldate.xldate_as_datetime(cols[14], liborigen.datemode).date()
                fechahasta = xlrd.xldate.xldate_as_datetime(cols[15], liborigen.datemode).date()
                nombrerubro = cols[16].strip()

                # print("Procesando ", c)
                # print(cedula, " - ", nombres, "-", carrera)

                if cedula == '0502868862':
                    print("Revisar")

                hojadestino.write(filadest, 0, carrera, fuentenormal)
                hojadestino.write(filadest, 1, cohorte, fuentenormal)
                hojadestino.write(filadest, 2, anio, fuentenumeroentero)
                hojadestino.write(filadest, 3, modalidad, fuentenormal)
                hojadestino.write(filadest, 4, cedula, fuentenormal)
                hojadestino.write(filadest, 5, nombres, fuentenormal)
                hojadestino.write(filadest, 6, valorensistema, fuentemoneda)
                hojadestino.write(filadest, 7, correccion, fuentemoneda)
                hojadestino.write(filadest, 8, totalamortizar, fuentemoneda)
                hojadestino.write(filadest, 9, numerocuotas, fuentenumeroentero)
                hojadestino.write(filadest, 10, valorcuota, fuentemoneda)
                hojadestino.write(filadest, 11, numerocuotaadicional, fuentenumeroentero)
                hojadestino.write(filadest, 12, valorcuotaadicional, fuentemoneda)
                hojadestino.write(filadest, 13, total, fuentemoneda)
                hojadestino.write(filadest, 14, fechadesde, fuentefecha)
                hojadestino.write(filadest, 15, fechahasta, fuentefecha)
                hojadestino.write(filadest, 16, nombrerubro, fuentenormal)

                # Verifico si tiene matricula
                if Matricula.objects.filter(status=True, inscripcion__persona__cedula=cedula, nivel__periodo__tipo__id__in=[3, 4], retiradomatricula=False).exists():
                    # Verifico que tenga una sola matricula de posgrado
                    if Matricula.objects.filter(status=True, inscripcion__persona__cedula=cedula, nivel__periodo__tipo__id__in=[3, 4], retiradomatricula=False).count() == 1:
                        matricula = Matricula.objects.get(status=True, inscripcion__persona__cedula=cedula, nivel__periodo__tipo__id__in=[3, 4], retiradomatricula=False)
                        print(matricula)
                        matriculados += 1
                        total_rubros = 0

                        # Consulto rubro o rubros
                        for rubro in matricula.rubro_set.filter(status=True):
                            print(rubro.id)
                            print(rubro.tipo.nombre)
                            print(rubro.valortotal)
                            total_rubros += 1

                        print("Total rubros ", total_rubros)

                        # Si no tiene rubros
                        if total_rubros == 0:
                            hojadestino.write(filadest, 17, "NO TIENE ASIGNADO RUBRO", fuentenormal)
                            hojadestino.write(filadest, 18, "NO", fuentenormal)
                            hojadestino.write(filadest, 19, "", fuentenormal)
                            hojadestino.write(filadest, 20, "", fuentenormal)
                            hojadestino.write(filadest, 21, "", fuentenormal)
                            hojadestino.write(filadest, 22, "", fuentenormal)
                            hojadestino.write(filadest, 23, "", fuentenormal)
                            hojadestino.write(filadest, 24, "", fuentenormal)
                        elif total_rubros > 1:
                            hojadestino.write(filadest, 17, "YA TIENE ASIGNADO RUBROS POR FINANCIAMIENTO", fuentenormal)
                            hojadestino.write(filadest, 18, "NO", fuentenormal)
                            hojadestino.write(filadest, 19, "", fuentenormal)
                            hojadestino.write(filadest, 20, "", fuentenormal)
                            hojadestino.write(filadest, 21, "", fuentenormal)
                            hojadestino.write(filadest, 22, "", fuentenormal)
                            hojadestino.write(filadest, 23, "", fuentenormal)
                            hojadestino.write(filadest, 24, "", fuentenormal)
                        else:
                            # Verifico que exista en epunemi y tenga el mismo valor
                            rubro_unemi = matricula.rubro_set.filter(status=True)[0]

                            sql = """SELECT ru.id,ru.nombre,ru.valor,ru.valortotal,ru.saldo, ru.totalunemi, ru.observacion,ru.refinanciado,ru.bloqueado FROM sagest_rubro as ru WHERE ru.status=True AND ru.anulado=FALSE AND ru.idrubrounemi=%s;""" % (rubro_unemi.id)
                            cnepunemi.execute(sql)
                            rubroepunemi = cnepunemi.fetchone()
                            if rubroepunemi is not None:
                                # Comparo valores
                                print("ID epunemi:",rubroepunemi[0])
                                print("NOMBRE:", rubroepunemi[1])
                                print("VALOR EPUNEMI:", rubroepunemi[2], "-", rubro_unemi.valor)
                                print("VALOR TOTAL EPUNEMI:",rubroepunemi[3], "-", rubro_unemi.valortotal)
                                print("SALDO EPUNEMI:",rubroepunemi[4], "-", rubro_unemi.saldo)
                                print("TOTAL UNEMI:",rubroepunemi[5])
                                print("OBSERVACION:", rubroepunemi[6])
                                print("REFINANCIADO:",rubroepunemi[7])
                                print("BLOQUEADO:",rubroepunemi[8])

                                valor_rubro_epunemi = rubroepunemi[2]
                                valor_rubro_total_epunemi = rubroepunemi[3]
                                valor_saldo_epunemi = rubroepunemi[4]
                                valor_pagado = rubro_unemi.valortotal - rubro_unemi.saldo

                                # Bloqueo el rubro en epunemi para evitar cobro
                                sql = """UPDATE sagest_rubro SET bloqueado=TRUE, bloqueadopornovedad=TRUE WHERE idrubrounemi=%s AND status=true""" % (rubro_unemi.id)
                                cnepunemi.execute(sql)

                                # Si los rubros no son diferentes
                                if rubroepunemi[2] == rubro_unemi.valor and rubroepunemi[3] == rubro_unemi.valortotal and rubroepunemi[4] == rubro_unemi.saldo:
                                    # Si lo pagado es igual al valor a corregir
                                    if valor_pagado == correccion:
                                        hojadestino.write(filadest, 17, "", fuentenormal)
                                        hojadestino.write(filadest, 18, "SI", fuentenormal)
                                        hojadestino.write(filadest, 19, rubro_unemi.id, fuentenumeroentero)
                                        hojadestino.write(filadest, 20, rubro_unemi.valor, fuentemoneda)
                                        hojadestino.write(filadest, 21, rubro_unemi.valortotal, fuentemoneda)
                                        hojadestino.write(filadest, 22, rubro_unemi.saldo, fuentemoneda)
                                        hojadestino.write(filadest, 23, rubro_unemi.cancelado, fuentenormal)
                                        hojadestino.write(filadest, 24, "RUBRO BLOQUEADO", fuentenormal)


                                        # Genero las fechas y valores de las cuotas
                                        print("Total amortizar:", totalamortizar)
                                        print("Cuotas:", numerocuotas)
                                        fecha = fechadesde
                                        sumacuotas = 0
                                        # Valor cuota ya viene definido en el excel
                                        # valorcuota = Decimal(null_to_decimal(totalamortizar / numerocuotas, 2)).quantize(Decimal('.01'))

                                        # Consulto tipo de rubro
                                        tiporubro = TipoOtroRubro.objects.get(nombre=nombrerubro)

                                        # Bloqueo el rubro en epunemi para evitar cobro
                                        sql = """UPDATE sagest_rubro SET bloqueado=TRUE, bloqueadopornovedad=TRUE WHERE idrubrounemi=%s AND status=true""" % (rubro_unemi.id)
                                        cnepunemi.execute(sql)

                                        if guardar_en_base:
                                            # Actualizo rubro original en unemi
                                            rubro_unemi.valor = correccion
                                            rubro_unemi.valortotal = correccion
                                            rubro_unemi.saldo = 0
                                            rubro_unemi.cancelado = True
                                            rubro_unemi.save()

                                            print(".:: Rubro actualizado en UNEMI ::.")

                                            # Guardo financiamiento
                                            financiamiento = FinanciamientoPosgrado(
                                                persona=matricula.inscripcion.persona,
                                                matricula=matricula,
                                                costoprograma=valorensistema,
                                                descuento=0,
                                                totalprograma=valorensistema,
                                                pagado=correccion,
                                                pendiente=totalamortizar,
                                                montofinanciar=totalamortizar,
                                                cantidadcuota=numerocuotas+numerocuotaadicional,
                                                observacion='SOLICITADO POR EXPERTA DE LA DIP VÍA E-MAIL EL 18/03/2022',
                                                legalizado=False
                                            )
                                            financiamiento.save()

                                            print(".:: Financiamiento creado en UNEMI ::.")

                                            # Consulto pagos del rubro
                                            pagosrubro = rubro_unemi.pago_set.filter(status=True).order_by('-fecha')
                                            fechapago = pagosrubro[0].fecha

                                            # Guardo primera cuota de financiamiento que fue pagada
                                            cuota_financiamiento = FinanciamientoPosgradoDetalle(
                                                financiamiento=financiamiento,
                                                rubro=rubro_unemi,
                                                valor=rubro_unemi.valortotal,
                                                fechaemite=rubro_unemi.fecha,
                                                fechavence=rubro_unemi.fechavence,
                                                fechapago=fechapago,
                                                pagado=True,
                                                totalpagado=rubro_unemi.valortotal,
                                                saldo=0,
                                                financiado=False
                                            )
                                            cuota_financiamiento.save()

                                            print(".:: Detalle de financiamiento creado en UNEMI ::.")

                                            # Actualizo rubro original en epunemi
                                            sql = """UPDATE sagest_rubro SET valor=%s, valortotal=%s, saldo=0, cancelado=TRUE, totalunemi=%s WHERE idrubrounemi=%s AND status=true""" % (correccion, correccion, correccion, rubro_unemi.id)
                                            cnepunemi.execute(sql)

                                            print(".:: Rubro actualizado en EPUNEMI ::.")

                                        total_cuotas_generar = numerocuotas + numerocuotaadicional
                                        for n in range(1, total_cuotas_generar + 1):
                                            if n == total_cuotas_generar:
                                                if numerocuotaadicional == 0:
                                                    valorcuota = totalamortizar - sumacuotas
                                                else:
                                                    valorcuota = valorcuotaadicional
                                            else:
                                                sumacuotas += valorcuota

                                            print("Cuota ", n, " - ", fecha, " - ", valorcuota)
                                            print(tiporubro)

                                            if guardar_en_base:
                                                # Creo nuevo rubro en unemi
                                                nuevo_rubro_unemi = Rubro(fecha=datetime.now().date(),
                                                                          valor=valorcuota,
                                                                          valortotal=valorcuota,
                                                                          saldo=valorcuota,
                                                                          persona=matricula.inscripcion.persona,
                                                                          matricula=matricula,
                                                                          nombre=tiporubro.nombre,
                                                                          tipo=tiporubro,
                                                                          cancelado=False,
                                                                          observacion='',
                                                                          iva_id=1,
                                                                          epunemi=True,
                                                                          fechavence=fecha,
                                                                          compromisopago=None,
                                                                          bloqueado=False
                                                                          )

                                                nuevo_rubro_unemi.save()

                                                print(".:: Rubro creado en UNEMI ::.")

                                                # Creo detalle de financiamiento con el nuevo rubro creado

                                                cuota_financiamiento = FinanciamientoPosgradoDetalle(
                                                    financiamiento=financiamiento,
                                                    rubro=nuevo_rubro_unemi,
                                                    valor=nuevo_rubro_unemi.valortotal,
                                                    fechaemite=nuevo_rubro_unemi.fecha,
                                                    fechavence=nuevo_rubro_unemi.fechavence,
                                                    fechapago=None,
                                                    pagado=False,
                                                    totalpagado=0,
                                                    saldo=nuevo_rubro_unemi.valortotal,
                                                    financiado=True
                                                )
                                                cuota_financiamiento.save()

                                                print(".:: Detalle de financiamiento creado en UNEMI ::.")

                                                # Consulto la persona por cedula en base de epunemi
                                                sql = """SELECT pe.id FROM sga_persona AS pe WHERE pe.cedula='%s' AND pe.status=TRUE;  """ % (cedula)
                                                cnepunemi.execute(sql)
                                                registro = cnepunemi.fetchone()
                                                codigoalumno = registro[0]

                                                # Consulto el tipo otro rubro en epunemi
                                                sql = """SELECT id FROM sagest_tipootrorubro WHERE idtipootrorubrounemi=%s; """ % (tiporubro.id)
                                                cnepunemi.execute(sql)
                                                registro = cnepunemi.fetchone()

                                                # Si existe
                                                if registro is not None:
                                                    tipootrorubro = registro[0]
                                                else:
                                                    # Debo crear ese tipo de rubro
                                                    # Consulto centro de costo
                                                    sql = """SELECT id FROM sagest_centrocosto WHERE status=True AND unemi=True AND tipo=%s;""" % (tiporubro.tiporubro)
                                                    cnepunemi.execute(sql)
                                                    centrocosto = cnepunemi.fetchone()
                                                    idcentrocosto = centrocosto[0]

                                                    # Consulto la cuenta contable
                                                    cuentacontable = CuentaContable.objects.get(partida=tiporubro.partida, status=True)

                                                    # Creo el tipo de rubro en epunemi
                                                    sql = """ Insert Into sagest_tipootrorubro (status, nombre, partida_id, valor, interface, activo, ivaaplicado_id, nofactura, exportabanco, cuentacontable_id, centrocosto_id, tiporubro, idtipootrorubrounemi, unemi)
                                                                        VALUES(TRUE, '%s', %s, %s, FALSE, TRUE, %s, FALSE, TRUE, %s, %s, 1, %s, TRUE); """ % (
                                                        tiporubro.nombre, cuentacontable.partida.id, tiporubro.valor,
                                                        tiporubro.ivaaplicado.id, cuentacontable.id, idcentrocosto,
                                                        tiporubro.id)
                                                    cnepunemi.execute(sql)

                                                    print(".:: Tipo de Rubro creado en EPUNEMI ::.")

                                                    # Obtengo el id recién creado del tipo de rubro
                                                    sql = """SELECT id FROM sagest_tipootrorubro WHERE idtipootrorubrounemi=%s; """ % (tiporubro.id)
                                                    cnepunemi.execute(sql)
                                                    registro = cnepunemi.fetchone()
                                                    tipootrorubro = registro[0]


                                                # Creo nuevo rubro en epunemi
                                                sql = """ INSERT INTO sagest_rubro (status, cuota, tipocuota, valoriva, tienenotacredito, valornotacredito, valordescuento, anulado, fecha, valor ,valortotal, saldo, persona_id, nombre, tipo_id, cancelado, observacion, iva_id, idrubrounemi, totalunemi, fechavence, compromisopago, bloqueado, refinanciado, bloqueadopornovedad, titularcambiado, fecha_creacion, usuario_creacion_id) 
                                                          VALUES (TRUE, 0, 3, 0, FALSE, 0, 0, FALSE, NOW(),                   %s, %s,    %s, %s,     '%s', %s,   FALSE,    '',              1,   %s,        %s,     '/%s/',   %s, FALSE, FALSE, FALSE, FALSE, NOW(), 1); """ \
                                                      % (valorcuota, valorcuota, valorcuota, codigoalumno, tiporubro.nombre, tipootrorubro, nuevo_rubro_unemi.id, valorcuota, fecha, 0)
                                                cnepunemi.execute(sql)

                                                print(".:: Rubro creado en EPUNEMI ::.")

                                            fecha = fechadesde + relativedelta(months=n)

                                        # Desbloqueo el rubro en epunemi
                                        sql = """UPDATE sagest_rubro SET bloqueado=FALSE, bloqueadopornovedad=FALSE WHERE idrubrounemi=%s AND status=true""" % (rubro_unemi.id)
                                        cnepunemi.execute(sql)
                                    else:
                                        # Bloqueo el rubro en epunemi para evitar que sigan cobrando y existan diferencias
                                        sql = """UPDATE sagest_rubro SET bloqueado=TRUE, bloqueadopornovedad=TRUE WHERE idrubrounemi=%s AND status=true""" % (rubro_unemi.id)
                                        cnepunemi.execute(sql)

                                        hojadestino.write(filadest, 17, "VALOR PAGADO Y DE CORRECCION NO SON IGUALES", fuentenormal)
                                        hojadestino.write(filadest, 18, "NO", fuentenormal)
                                        hojadestino.write(filadest, 19, rubro_unemi.id, fuentenumeroentero)
                                        hojadestino.write(filadest, 20, "", fuentenormal)
                                        hojadestino.write(filadest, 21, "", fuentenormal)
                                        hojadestino.write(filadest, 22, "", fuentenormal)
                                        hojadestino.write(filadest, 23, "", fuentenormal)
                                        hojadestino.write(filadest, 24, "RUBRO BLOQUEADO", fuentenormal)

                                else:
                                    hojadestino.write(filadest, 17, "DIFERENCIAS DE VALORES DE LOS RUBROS UNEMI-EPUNEMI", fuentenormal)
                                    hojadestino.write(filadest, 18, "NO", fuentenormal)
                                    hojadestino.write(filadest, 19, rubro_unemi.id, fuentenumeroentero)
                                    hojadestino.write(filadest, 20, "", fuentenormal)
                                    hojadestino.write(filadest, 21, "", fuentenormal)
                                    hojadestino.write(filadest, 22, "", fuentenormal)
                                    hojadestino.write(filadest, 23, "", fuentenormal)
                                    hojadestino.write(filadest, 24, "RUBRO BLOQUEADO", fuentenormal)
                            else:
                                hojadestino.write(filadest, 17, "NO EXISTE EN EPUNEMI", fuentenormal)
                                hojadestino.write(filadest, 18, "NO", fuentenormal)
                                hojadestino.write(filadest, 19, "", fuentenormal)
                                hojadestino.write(filadest, 20, "", fuentenormal)
                                hojadestino.write(filadest, 21, "", fuentenormal)
                                hojadestino.write(filadest, 22, "", fuentenormal)
                                hojadestino.write(filadest, 23, "", fuentenormal)
                                hojadestino.write(filadest, 24, "", fuentenormal)

                    else:
                        # print("Doble matricula")
                        # for m in Matricula.objects.filter(status=True, inscripcion__persona__cedula=cedula, nivel__periodo__tipo__id__in=[3, 4]):
                        #     print(m)
                        hojadestino.write(filadest, 17, "TIENE DOBLE MATRICULA", fuentenormal)
                        hojadestino.write(filadest, 18, "NO", fuentenormal)
                        hojadestino.write(filadest, 19, "", fuentenormal)
                        hojadestino.write(filadest, 20, "", fuentenormal)
                        hojadestino.write(filadest, 21, "", fuentenormal)
                        hojadestino.write(filadest, 22, "", fuentenormal)
                        hojadestino.write(filadest, 23, "", fuentenormal)
                        hojadestino.write(filadest, 24, "", fuentenormal)
                        doblematricula += 1
                else:
                    # print(cedula, " - ", nombres, "-", carrera)
                    # print("No existe la matrícula")
                    hojadestino.write(filadest, 17, "NO ESTÁ MATRICULADO", fuentenormal)
                    hojadestino.write(filadest, 18, "NO", fuentenormal)
                    hojadestino.write(filadest, 19, "", fuentenormal)
                    hojadestino.write(filadest, 20, "", fuentenormal)
                    hojadestino.write(filadest, 21, "", fuentenormal)
                    hojadestino.write(filadest, 22, "", fuentenormal)
                    hojadestino.write(filadest, 23, "", fuentenormal)
                    hojadestino.write(filadest, 24, "", fuentenormal)

                    nomatriculados += 1

                filadest += 1
                c += 1

        conexion.commit()
        cnepunemi.close()

        libdestino.save(output_folder + "/PROCESADOS_POSGRADO_8.xls")

        print("Matriculados:", matriculados)
        print("No matriculados:", nomatriculados)
        print("Doble matrícula:", doblematricula)
        print("Proceso finalizado. . .")
    except Exception as ex:
        transaction.set_rollback(True)
        msg = ex.__str__()
        print(msg)

def eliminar_matriculas_posgrado_18_educacion_inicial_2c():
    try:
        codigos_matricula = [398609, 399132, 398610, 397748, 356961, 397746, 356960, 398611, 397749, 398612, 397750, 399128, 399129, 399130, 397745, 397752, 399131, 422978]
        matriculas = Matricula.objects.filter(pk__in=codigos_matricula).order_by('id')
        total = matriculas.count()
        noprocesados = 0
        procesados = 0
        c = 1

        for matricula in matriculas:
            print("Procesando", c, " de ", total)
            print(matricula.inscripcion.persona)
            print(matricula.inscripcion.carrera.nombre)
            print(matricula.nivel.periodo.nombre)

            rubro = Rubro.objects.filter(matricula=matricula, status=True).order_by('id')
            eliminar = True

            for r in rubro:
                if r.tiene_pagos():
                    print("No se puede eliminar matricula porque tiene rubros pagados")
                    noprocesados += 1
                    eliminar = False
                    break

            if eliminar:
                inscripcion = matricula.inscripcion
                for materiaasignada in matricula.materiaasignada_set.all():
                    materiaasignada.delete()

                # esta validacion esta para los de POSTGRADO, para que su convenio de pago sea desaprobado
                if Periodo.objects.values('id').filter(pk=matricula.nivel.periodo.id, nombre__icontains='IPEC').exists():
                    if DetalleConvenioPago.objects.values('id').filter(inscripcion=inscripcion, status=True).exists():
                        detalleconveniopago = DetalleConvenioPago.objects.filter(inscripcion=inscripcion, status=True)[0]
                        detalleconveniopago.aprobado = False
                        detalleconveniopago.save()

                matricula.delete()
                procesados += 1

            c += 1

        print("Eliminadas: ", procesados)
        print("No Eliminadas: ", noprocesados)
        print("Proceso terminado...")
    except Exception as ex:
        transaction.set_rollback(True)
        msg = ex.__str__()
        print(msg)

def eliminar_matriculas_posgrado_15():
    try:
        print("Eliminación 5 de Sistemas de Información, 9 de Educación Básica y 1 de Gestión Educativa")

        codigos_matricula = [
            356576
        ]

        matriculas = Matricula.objects.filter(pk__in=codigos_matricula).order_by('id')
        total = matriculas.count()
        noprocesados = 0
        procesados = 0
        c = 1

        for matricula in matriculas:
            print("Procesando", c, " de ", total)
            print(matricula.inscripcion.persona)
            print(matricula.inscripcion.carrera.nombre)
            print(matricula.nivel.periodo.nombre)

            rubro = Rubro.objects.filter(matricula=matricula, status=True).order_by('id')
            eliminar = True

            for r in rubro:
                if r.tiene_pagos():
                    print("No se puede eliminar matricula porque tiene rubros pagados")
                    noprocesados += 1
                    eliminar = False
                    break

            if eliminar:
                inscripcion = matricula.inscripcion
                for materiaasignada in matricula.materiaasignada_set.all():
                    materiaasignada.delete()

                # esta validacion esta para los de POSTGRADO, para que su convenio de pago sea desaprobado

                if Periodo.objects.values('id').filter(pk=matricula.nivel.periodo.id, nombre__icontains='IPEC').exists():
                    if DetalleConvenioPago.objects.values('id').filter(inscripcion=inscripcion, status=True).exists():
                        detalleconveniopago = DetalleConvenioPago.objects.filter(inscripcion=inscripcion, status=True)[0]
                        detalleconveniopago.aprobado = False
                        detalleconveniopago.save()

                matricula.delete()

                procesados += 1

            c += 1

        print("Eliminadas: ", procesados)
        print("No Eliminadas: ", noprocesados)
        print("Proceso terminado...")
    except Exception as ex:
        transaction.set_rollback(True)
        msg = ex.__str__()
        print(msg)

def eliminar_matriculas_posgrado_1_sistemainformacion():
    try:
        print("Eliminación 1 de Sistemas de Información")

        codigos_matricula = [
            332085
        ]

        matriculas = Matricula.objects.filter(pk__in=codigos_matricula).order_by('id')
        total = matriculas.count()
        noprocesados = 0
        procesados = 0
        c = 1

        for matricula in matriculas:
            print("Procesando", c, " de ", total)
            print(matricula.inscripcion.persona)
            print(matricula.inscripcion.carrera.nombre)
            print(matricula.nivel.periodo.nombre)

            rubro = Rubro.objects.filter(matricula=matricula, status=True).order_by('id')
            eliminar = True

            for r in rubro:
                if r.tiene_pagos():
                    print("No se puede eliminar matricula porque tiene rubros pagados")
                    noprocesados += 1
                    eliminar = False
                    break

            if eliminar:
                inscripcion = matricula.inscripcion
                for materiaasignada in matricula.materiaasignada_set.all():
                    materiaasignada.delete()

                # esta validacion esta para los de POSTGRADO, para que su convenio de pago sea desaprobado

                if Periodo.objects.values('id').filter(pk=matricula.nivel.periodo.id, nombre__icontains='IPEC').exists():
                    if DetalleConvenioPago.objects.values('id').filter(inscripcion=inscripcion, status=True).exists():
                        detalleconveniopago = DetalleConvenioPago.objects.filter(inscripcion=inscripcion, status=True)[0]
                        detalleconveniopago.aprobado = False
                        detalleconveniopago.save()

                matricula.delete()

                procesados += 1

            c += 1

        print("Eliminadas: ", procesados)
        print("No Eliminadas: ", noprocesados)
        print("Proceso terminado...")
    except Exception as ex:
        transaction.set_rollback(True)
        msg = ex.__str__()
        print(msg)

def eliminar_matriculas_17032022_1():
    try:
        print(".:: Eliminación 1 registro de matrícula ::.")

        codigos_matricula = [
            354945
        ]

        matriculas = Matricula.objects.filter(pk__in=codigos_matricula).order_by('id')
        total = matriculas.count()
        noprocesados = 0
        procesados = 0
        c = 1

        for matricula in matriculas:
            print("Procesando", c, " de ", total)
            print(matricula.inscripcion.persona)
            print(matricula.inscripcion.carrera.nombre)
            print(matricula.nivel.periodo.nombre)

            rubro = Rubro.objects.filter(matricula=matricula, status=True).order_by('id')
            eliminar = True

            for r in rubro:
                if r.tiene_pagos():
                    print("No se puede eliminar matricula porque tiene rubros pagados")
                    noprocesados += 1
                    eliminar = False
                    break

            if eliminar:
                inscripcion = matricula.inscripcion
                for materiaasignada in matricula.materiaasignada_set.all():
                    materiaasignada.delete()

                # esta validacion esta para los de POSTGRADO, para que su convenio de pago sea desaprobado

                if Periodo.objects.values('id').filter(pk=matricula.nivel.periodo.id, nombre__icontains='IPEC').exists():
                    if DetalleConvenioPago.objects.values('id').filter(inscripcion=inscripcion, status=True).exists():
                        detalleconveniopago = DetalleConvenioPago.objects.filter(inscripcion=inscripcion, status=True)[0]
                        detalleconveniopago.aprobado = False
                        detalleconveniopago.save()

                matricula.delete()

                procesados += 1

            c += 1

        print("Eliminadas: ", procesados)
        print("No Eliminadas: ", noprocesados)
        print("Proceso terminado...")
    except Exception as ex:
        transaction.set_rollback(True)
        msg = ex.__str__()
        print(msg)

def generar_numero_orden_detalle_evaluacion():
    evaluaciones = EvaluacionProyecto.objects.filter(status=True).order_by('id')
    for evaluacion in evaluaciones:
        print("Procesando evaluación:")
        print(evaluacion)
        orden = 1
        for detalle in evaluacion.evaluacionproyectodetalle_set.filter(status=True).order_by('id'):
            detalle.numero = orden
            detalle.save()
            print("Detalle actualizado")
            orden += 1

    print("Proces terminado...")


@transaction.atomic()
def inactivar_rubros_pendientes_aspirantes_posgrado():
    guardar_en_base = False

    conexion = connections['epunemi']
    cnepunemi = conexion.cursor()
    try:
        fuentecabecera = easyxf(
            'font: name Verdana, color-index black, bold on, height 150; pattern: pattern solid, fore_colour gray25; alignment: vert distributed, horiz centre; borders: left thin, right thin, top thin, bottom thin')
        fuentenormal = easyxf(
            'font: name Verdana, color-index black, height 150; borders: left thin, right thin, top thin, bottom thin')
        fuentenormalwrap = easyxf(
            'font: name Verdana, color-index black, height 150; borders: left thin, right thin, top thin, bottom thin')
        fuentenormalneg = easyxf(
            'font: name Verdana, color-index black, bold on , height 150; borders: left thin, right thin, top thin, bottom thin')
        fuentenormalnegrell = easyxf(
            'font: name Verdana, color-index black, bold on , height 150; borders: left thin, right thin, top thin, bottom thin; pattern: pattern solid, fore_colour gray25')
        fuentenormalwrap.alignment.wrap = True
        fuentenormalcent = easyxf(
            'font: name Verdana, color-index black, height 150; borders: left thin, right thin, top thin, bottom thin; alignment: horiz centre')
        fuentemoneda = easyxf(
            'font: name Verdana, color-index black, height 150; borders: left thin, right thin, top thin, bottom thin; alignment: horiz right',
            num_format_str=' "$" #,##0.00')
        fuentemonedaneg = easyxf(
            'font: name Verdana, color-index black, bold on, height 150; borders: left thin, right thin, top thin, bottom thin; alignment: horiz right; pattern: pattern solid, fore_colour gray25',
            num_format_str=' "$" #,##0.00')
        fuentefecha = easyxf(
            'font: name Verdana, color-index black, height 150; borders: left thin, right thin, top thin, bottom thin; alignment: horiz center',
            num_format_str='yyyy-mm-dd')
        fuentenumerodecimal = easyxf(
            'font: name Verdana, color-index black, height 150; borders: left thin, right thin, top thin, bottom thin; alignment: horiz right',
            num_format_str='#,##0.00')
        fuentenumeroentero = easyxf(
            'font: name Verdana, color-index black, height 150; borders: left thin, right thin, top thin, bottom thin; alignment: horiz right')


        output_folder = os.path.join(os.path.join(SITE_STORAGE, 'media'))
        liborigen = xlrd.open_workbook(output_folder + '/POSGRADO_15.xls')

        libdestino = xlwt.Workbook()
        hojadestino = libdestino.add_sheet("Listado")

        fil = 0

        columnas = [
            (u"Programa", 7000),
            (u"Cédula", 4500),
            (u"Estudiante", 9000),
            (u"Valor Rubro", 4000),
            (u"IDRubroUnemi1", 2000),
            (u"RubroUnemi1", 2000),
            (u"IdRubroEpunemi", 4500),
            (u"Valor Rubro 1", 4000),
            (u"IDRubroUnemi2", 2000),
            (u"RubroUnemi2", 2000),
            (u"IdRubroEpunemi", 4500),
            (u"Valor Rubro 2", 4000),
            (u"Observación", 9000),
            (u"Procesar", 2000)
        ]

        for col_num in range(len(columnas)):
            hojadestino.write(fil, col_num, columnas[col_num][0], fuentecabecera)
            hojadestino.col(col_num).width = columnas[col_num][1]


        sheet = liborigen.sheet_by_index(0)

        c = 1
        filadest = 1
        matriculados = 0
        nomatriculados = 0
        matriculados = 0
        doblematricula = 0

        procesar = noprocesar = 0

        for fila in range(sheet.nrows):
            if fila >= 1:
                print("Procesanso", c, " de 172")

                cols = sheet.row_values(fila)
                carrera = cols[11].strip()
                cedula = cols[1].strip() if type(cols[1]) == str else str(int(cols[1])).strip()
                nombres = cols[2].strip()
                valor = Decimal(cols[5]).quantize(Decimal('.01'))


                hojadestino.write(filadest, 0, carrera, fuentenormal)
                hojadestino.write(filadest, 1, cedula, fuentenormal)
                hojadestino.write(filadest, 2, nombres, fuentenormal)
                hojadestino.write(filadest, 3, valor, fuentemoneda)

                if Persona.objects.values("id").filter(cedula=cedula, status=True).exists():
                    persona = Persona.objects.get(cedula=cedula, status=True)
                else:
                    persona = Persona.objects.get(pasaporte=cedula, status=True)

                rubros = Rubro.objects.filter(persona=persona, status=True, cancelado=False, valortotal=valor, matricula__isnull=True)

                if rubros:
                    if rubros.count() == 1:
                        rubro = rubros[0]
                        hojadestino.write(filadest, 4, rubro.id, fuentenormal)
                        hojadestino.write(filadest, 5, rubro.nombre, fuentenormal)
                        hojadestino.write(filadest, 6, rubro.idrubroepunemi, fuentenormal)
                        hojadestino.write(filadest, 7, rubro.valortotal, fuentemoneda)

                        # Inactivo rubro en unemi
                        rubro.status = False
                        rubro.observacion = "INACTIVADO POR CON CONTINUAR CON PROCESO DE MATRICULACIÓN - CORREO DEL 11/07/2022 DIANA MACIAS"
                        rubro.save()

                        cancelado = False
                        if rubros[0].idrubroepunemi > 0:
                            idepunemi = rubros[0].idrubroepunemi

                            sql = """SELECT ru.id,ru.nombre,ru.valor,ru.valortotal,ru.saldo, ru.totalunemi, ru.observacion,ru.refinanciado,ru.bloqueado, ru.cancelado FROM sagest_rubro as ru WHERE ru.status=TRUE AND ru.anulado=FALSE AND ru.id=%s;""" % (idepunemi)
                            cnepunemi.execute(sql)
                            rubroepunemi = cnepunemi.fetchone()
                            if rubroepunemi is not None:
                                # Inactivar rubro en EPUNEMI
                                sql = """UPDATE sagest_rubro SET status=FALSE, fecha_modificacion=NOW(), usuario_modificacion_id=1, observacion='INACTIVADO POR CON CONTINUAR CON PROCESO DE MATRICULACIÓN - CORREO DEL 11/07/2022 DIANA MACIAS' WHERE id=%s""" % (idepunemi)
                                cnepunemi.execute(sql)


                        hojadestino.write(filadest, 12, "", fuentenormal)
                        hojadestino.write(filadest, 13, "SI", fuentenormal)
                        procesar += 1
                    else:
                        c2 = 0
                        for rubro in rubros:
                            if c2 == 0:
                                hojadestino.write(filadest, 4, rubro.id, fuentenormal)
                                hojadestino.write(filadest, 5, rubro.nombre, fuentenormal)
                                hojadestino.write(filadest, 6, rubro.idrubroepunemi, fuentenormal)
                                hojadestino.write(filadest, 7, rubro.valortotal, fuentemoneda)
                            else:
                                hojadestino.write(filadest, 8, rubro.id, fuentenormal)
                                hojadestino.write(filadest, 9, rubro.nombre, fuentenormal)
                                hojadestino.write(filadest, 10, rubro.idrubroepunemi, fuentenormal)
                                hojadestino.write(filadest, 11, rubro.valortotal, fuentemoneda)

                            # Inactivo rubro en unemi
                            rubro.status = False
                            rubro.observacion = "INACTIVADO POR CON CONTINUAR CON PROCESO DE MATRICULACIÓN - CORREO DEL 11/07/2022 DIANA MACIAS"
                            rubro.save()

                            idepunemi = rubro.idrubroepunemi

                            sql = """SELECT ru.id,ru.nombre,ru.valor,ru.valortotal,ru.saldo, ru.totalunemi, ru.observacion,ru.refinanciado,ru.bloqueado, ru.cancelado FROM sagest_rubro as ru WHERE ru.status=TRUE AND ru.anulado=FALSE AND ru.id=%s;""" % (idepunemi)
                            cnepunemi.execute(sql)
                            rubroepunemi = cnepunemi.fetchone()
                            if rubroepunemi is not None:
                                # Inactivar rubro en EPUNEMI
                                sql = """UPDATE sagest_rubro SET status=FALSE, fecha_modificacion=NOW(), usuario_modificacion_id=1, observacion='INACTIVADO POR CON CONTINUAR CON PROCESO DE MATRICULACIÓN - CORREO DEL 11/07/2022 DIANA MACIAS' WHERE id=%s""" % (idepunemi)
                                cnepunemi.execute(sql)

                            c2 += 1

                        hojadestino.write(filadest, 12, "EXISTEN MÁS DE 1 RUBRO", fuentenormal)
                        hojadestino.write(filadest, 13, "SI", fuentenormal)
                        procesar += 1
                else:
                    hojadestino.write(filadest, 4, "", fuentenormal)
                    hojadestino.write(filadest, 5, "", fuentenormal)
                    hojadestino.write(filadest, 6, "", fuentenormal)
                    hojadestino.write(filadest, 7, "", fuentenormal)
                    hojadestino.write(filadest, 8, "", fuentenormal)
                    hojadestino.write(filadest, 9, "", fuentenormal)
                    hojadestino.write(filadest, 12, "NO EXISTEN RUBROS", fuentenormal)
                    hojadestino.write(filadest, 13, "NO", fuentenormal)
                    noprocesar += 1

                filadest += 1
                c += 1

        conexion.commit()
        cnepunemi.close()

        libdestino.save(output_folder + "/PROCESADOS_POSGRADO_15.xls")

        print("Procesar: ", procesar)
        print("No Procesar: ", noprocesar)
        print("Proceso finalizado. . .")
    except Exception as ex:
        transaction.set_rollback(True)
        msg = ex.__str__()
        print(msg)

def verificar_psicologia():
    pass
    # matriculas = Matricula.objects.filter(inscripcion__carrera_id=113, nivel__periodo_id=101).order_by('inscripcion__persona__apellido1', 'inscripcion__persona__apellido2', 'inscripcion__persona__nombres')
    # c = 0
    # for matricula in matriculas:
    #     c += 1
    #     print(c)
    #     print(matricula)
    #     totalpagadomatricula = 0
    #     for rubro in matricula.rubro_set.filter(status=True, tipo__subtiporubro=1):
    #         # print(rubro)
    #         print(rubro.id,"-",rubro.valortotal,"-",rubro.saldo)
    #         totalpagadorubro = 0
    #         for pago in rubro.pagos():
    #             # print(pago.valortotal)
    #             totalpagadorubro += pago.valortotal
    #
    #         totalpagadomatricula += totalpagadorubro
    #
    #         print("Total rubro:", rubro.valortotal, " - Saldo:", rubro.saldo)
    #         print("Total pagado rubro:", totalpagadorubro)
    #         print("Otro saldo:", rubro.valortotal - totalpagadorubro)
    #
    #         if rubro.saldo != (rubro.valortotal - totalpagadorubro):
    #             print("Diferencias")
    #
    #     print("Total pagado matricula:", totalpagadomatricula)
    #     print("===================")

def simular_pago_posgrado():
    try:
        cedula = '0927061283'
        montopago = 166.67
        valorpagar = Decimal(montopago).quantize(Decimal('.01'))

        # matricula = Matricula.objects.get(pk=424189)
        matricula = Matricula.objects.get(inscripcion__persona__cedula=cedula, nivel__periodo__tipo=3)

        rubros = Rubro.objects.filter(status=True, matricula=matricula, cancelado=False).order_by('fechavence')

        for rubro in rubros:
            print("Disponible", valorpagar)

            if valorpagar == 0:
                break

            print("Rubro Saldo", rubro.saldo)



            saldorubro = rubro.saldo
            if valorpagar >= saldorubro:
                valorpago = saldorubro
                valorpagar -= valorpago
            else:
                valorpago = valorpagar
                valorpagar -= valorpago

            print("Pagado: ", valorpago)

            pagorubro = Pago(fecha=datetime.now().date(),
                         subtotal0=valorpago,
                         subtotaliva=0,
                         iva=0,
                         valordescuento=0,
                         valortotal=valorpago,
                         rubro=rubro,
                         efectivo=True,
                         sesion_id=100)
            pagorubro.save()

            rubro.save()

        print("Pagado con exito")
    except Exception as ex:
        msg = ex.__str__()
        print(msg)

def prueba_vencidos():
    matricula = Matricula.objects.get(pk=423804)
    # fechacorte = datetime.strptime('2022-04-19', '%Y-%m-%d').date()
    fechacorte = datetime.strptime('2022-01-31', '%Y-%m-%d').date()

    # datos = matricula.rubros_maestria_vencidos_detalle(fechacorte)
    datos = matricula.rubros_maestria_vencidos_detalle_version_final(fechacorte)

    print("Reporte del alumno")



    if not matricula.retirado_programa_maestria():
        print("NO RETIRADO")
        print("Totales Generales: ")
        print("Total Rubros:", datos['totalrubros'], "Total Pagado:", datos['totalpagado'], "Total Pendiente:", datos['totalpendiente'], "Total Vencido:", datos['totalvencido'])

        print("Totales No Vencido:")
        print("Total Rubros:", datos['totalrubrosnv'], "Total Pagado:", datos['totalpagadonv'], "Total Pendiente:", datos['totalpendientenv'], "Total Vencido:", datos['totalvencidonv'])

        print("Totales Vencidos:")
        print("Total Rubros:", datos['totalrubrosv'], "Total Pagado:", datos['totalpagadov'], "Total Pendiente:", datos['totalpendientev'], "Total Vencido:", datos['totalvencido'])

        print("Rubros no vencidos")
        for r in datos['rubrosnovencidos']:
            print("ID Rubros:", r[0], "Fecha vence:", r[1], "Total Rubro:", r[2], "Total Pagado:", r[3], "Total pendiente:", r[4], "Total vencido:", r[5], "Dias vencimiento:", r[6])

        print("Rubros vencidos")
        for r in datos['rubrosvencidos']:
            print("ID Rubros:", r[0], "Fecha vence:", r[1], "Total Rubro:", r[2], "Total Pagado:", r[3], "Total pendiente:", r[4], "Total vencido:", r[5], "Dias vencimiento:", r[6])
    else:
        print(".:: RETIRADO ::.")
        print("Totales Generales: ")
        print("Total Rubros:", datos['totalrubros'], "Total Pagado:", datos['totalpagado'], "Total Pendiente:", datos['totalpendiente'], "Total Vencido:", datos['totalvencido'], "Fecha vence:", datos['fechavence'], "Días vencidos:", datos['diasvencimiento'])



    print("Hola")

def prueba_vencidos_categoria():
    matricula = Matricula.objects.get(pk=479250)
    # fechacorte = datetime.strptime('2022-04-19', '%Y-%m-%d').date()
    fechacorte = datetime.strptime('2022-08-14', '%Y-%m-%d').date()

    # datos = matricula.rubros_maestria_vencidos_detalle(fechacorte)
    datos = matricula.rubros_maestria_vencidos_detalle_por_categoria_version_final(fechacorte, "C")

    print("Reporte del alumno")

    if not matricula.retirado_programa_maestria():
        print("NO RETIRADO")
        print("Totales Generales: ")
        print("Total Rubros:", datos['totalrubros'], "Total Pagado:", datos['totalpagado'], "Total Pendiente:", datos['totalpendiente'], "Total Vencido:", datos['totalvencido'])

        print("Totales No Vencido:")
        print("Total Rubros:", datos['totalrubrosnv'], "Total Pagado:", datos['totalpagadonv'], "Total Pendiente:", datos['totalpendientenv'], "Total Vencido:", datos['totalvencidonv'])

        print("Totales Vencidos:")
        print("Total Rubros:", datos['totalrubrosv'], "Total Pagado:", datos['totalpagadov'], "Total Pendiente:", datos['totalpendientev'], "Total Vencido:", datos['totalvencido'])

        print("Rubros no vencidos")
        for r in datos['rubrosnovencidos']:
            print("ID Rubros:", r[0], "Fecha vence:", r[1], "Total Rubro:", r[2], "Total Pagado:", r[3], "Total pendiente:", r[4], "Total vencido:", r[5], "Dias vencimiento:", r[6])

        print("Rubros vencidos")
        for r in datos['rubrosvencidos']:
            print("ID Rubros:", r[0], "Fecha vence:", r[1], "Total Rubro:", r[2], "Total Pagado:", r[3], "Total pendiente:", r[4], "Total vencido:", r[5], "Dias vencimiento:", r[6])
    else:
        print(".:: RETIRADO ::.")
        print("Totales Generales: ")
        print("Total Rubros:", datos['totalrubros'], "Total Pagado:", datos['totalpagado'], "Total Pendiente:", datos['totalpendiente'], "Total Vencido:", datos['totalvencido'], "Fecha vence:", datos['fechavence'], "Días vencidos:", datos['diasvencimiento'])



def prueba_vencidos_pagos():
    matricula = Matricula.objects.get(pk=423373)
    # fechacorte = datetime.strptime('2022-04-19', '%Y-%m-%d').date()
    fechacorte = datetime.strptime('2022-04-29', '%Y-%m-%d').date()
    fechapago = datetime.strptime('2022-04-29', '%Y-%m-%d').date()

    rubros = matricula.rubros_maestria_vencidos_vs_pagos(fechacorte, fechapago)

    print("Hola")

def prueba_vencidos_pagos_2():
    matricula = Matricula.objects.get(pk=424456)
    # fechacorte = datetime.strptime('2022-04-19', '%Y-%m-%d').date()
    fechacorte = datetime.strptime('2022-01-30', '%Y-%m-%d').date()
    fechapago = datetime.strptime('2022-04-30', '%Y-%m-%d').date()

    # fechacorte = datetime.strptime('2022-05-17', '%Y-%m-%d').date()
    # fechapago = datetime.strptime('2022-06-30', '%Y-%m-%d').date()

    # datos = matricula.rubros_maestria_vencidos_vs_pagos__detalle_2(fechacorte, fechapago)
    datos = matricula.rubros_maestria_vencidos_vs_pagos_detalle_version_final(fechacorte, fechapago)

    print("Reporte del alumno")

    if not matricula.retirado_programa_maestria():
        print("NO RETIRADO")
        print("Totales Generales: ")
        print("Total Rubros:", datos['totalrubros'], "Total Pagado:", datos['totalpagado'], "Total Pendiente:", datos['totalpendiente'], "Total Vencido:", datos['totalvencido'])

        print("Totales No Vencido:")
        print("Total Rubros:", datos['totalrubrosnv'], "Total Pagado:", datos['totalpagadonv'], "Total Pendiente:", datos['totalpendientenv'], "Total Vencido:", datos['totalvencidonv'])

        print("Totales Vencidos:")
        print("Total Rubros:", datos['totalrubrosv'], "Total Pagado:", datos['totalpagadov'], "Total Pendiente:", datos['totalpendientev'], "Total Vencido:", datos['totalvencido'])

        print("Rubros no vencidos")
        for r in datos['rubrosnovencidos']:
            print("ID Rubros:", r[0], "Fecha vence:", r[1], "Total Rubro:", r[2], "Total Pagado:", r[3], "Total pendiente:", r[4], "Total vencido:", r[5], "Dias vencimiento:", r[6])

        print("Rubros vencidos")
        for r in datos['rubrosvencidos']:
            print("ID Rubros:", r[0], "Fecha vence:", r[1], "Total Rubro:", r[2], "Total Pagado:", r[3], "Total pendiente:", r[4], "Total vencido:", r[5], "Dias vencimiento:", r[6], "Fecha cobro:", r[7], "Total cobro:", r[8], "Dias cobro:", r[9], "Vencimiento en curso:", r[10])

        print("Rubros vencimiento en curso")
        for r in datos['rubrosvencimientocurso']:
            print("ID Rubros:", r[0], "Fecha vence:", r[1], "Total Rubro:", r[2], "Total Pagado:", r[3], "Total pendiente:", r[4], "Total vencido:", r[5], "Dias vencimiento:", r[6], "Fecha cobro:", r[7], "Total cobro:", r[8], "Dias cobro:", r[9], "Vencimiento en curso:", r[10])
    else:
        print(".:: RETIRADO ::.")
        print("Totales Generales: ")
        print("Total Rubros:", datos['totalrubros'], "Total Pagado:", datos['totalpagado'], "Total Pendiente:", datos['totalpendiente'], "Total Vencido:", datos['totalvencido'], "Fecha vence:", datos['fechavence'], "Días vencidos:", datos['diasvencimiento'])


def test_moodle():
    cedula = '0703621953'
    cnmoodle = connections['moodle_pos'].cursor()

    matricula = Matricula.objects.get(inscripcion__persona__cedula=cedula, nivel__periodo__tipo=3)

    # Consulto usuario de moodle
    usermoodle = matricula.inscripcion.persona.idusermoodleposgrado

    print("Matricula bloqueada: ", matricula.bloqueomatricula)
    print("Usuario:", usermoodle)

    if usermoodle != 0:
        # Consulta en mooc_user
        sql = """Select id, username, deleted From mooc_user Where id=%s""" % (usermoodle)
        cnmoodle.execute(sql)
        registro = cnmoodle.fetchall()
        idusuario = registro[0][0]
        username = registro[0][1]
        deleted = registro[0][2]

        print(idusuario, "-", username, "- Bloqueado Moodle:", deleted)
    else:
        print("No tiene usuario moodle de posgrado")

def generar_listado_matriculados_posgrado():

    fuentenormal = easyxtitulo = easyxf(
        'font: name Times New Roman, color-index black, bold on , height 350; alignment: horiz centre')
    titulo = easyxf(
        'font: name Times New Roman, color-index black, bold on , height 350; alignment: horiz centre')
    titulo2 = easyxf(
        'font: name Times New Roman, color-index black, bold on , height 250; alignment: horiz centre')
    fuentecabecera = easyxf(
        'font: name Verdana, color-index black, bold on, height 150; pattern: pattern solid, fore_colour gray25; alignment: vert distributed, horiz centre; borders: left thin, right thin, top thin, bottom thin')
    fuentenormal = easyxf(
        'font: name Verdana, color-index black, height 150; borders: left thin, right thin, top thin, bottom thin')
    fuentenormalwrap = easyxf(
        'font: name Verdana, color-index black, height 150; borders: left thin, right thin, top thin, bottom thin')
    fuentenormalneg = easyxf(
        'font: name Verdana, color-index black, bold on , height 150; borders: left thin, right thin, top thin, bottom thin')
    fuentenormalnegrell = easyxf(
        'font: name Verdana, color-index black, bold on , height 150; borders: left thin, right thin, top thin, bottom thin; pattern: pattern solid, fore_colour gray25')
    fuentenormalwrap.alignment.wrap = True
    fuentenormalcent = easyxf(
        'font: name Verdana, color-index black, height 150; borders: left thin, right thin, top thin, bottom thin; alignment: horiz centre')
    fuentemoneda = easyxf(
        'font: name Verdana, color-index black, height 150; borders: left thin, right thin, top thin, bottom thin; alignment: horiz right',
        num_format_str=' "$" #,##0.00')
    fuentemonedaneg = easyxf(
        'font: name Verdana, color-index black, bold on, height 150; borders: left thin, right thin, top thin, bottom thin; alignment: horiz right; pattern: pattern solid, fore_colour gray25',
        num_format_str=' "$" #,##0.00')
    fuentefecha = easyxf(
        'font: name Verdana, color-index black, height 150; borders: left thin, right thin, top thin, bottom thin; alignment: horiz center',
        num_format_str='yyyy-mm-dd')
    fuentenumerodecimal = easyxf(
        'font: name Verdana, color-index black, height 150; borders: left thin, right thin, top thin, bottom thin; alignment: horiz right',
        num_format_str='#,##0.00')
    fuentenumeroentero = easyxf(
        'font: name Verdana, color-index black, height 150; borders: left thin, right thin, top thin, bottom thin; alignment: horiz right')
    fuenteporcentaje = easyxf(
        'font: name Verdana, color-index black, height 150; borders: left thin, right thin, top thin, bottom thin; alignment: horiz right',
        num_format_str='0%')
    fuenteporcentajeneg = easyxf(
        'font: name Verdana, color-index black, bold on, height 150; borders: left thin, right thin, top thin, bottom thin; alignment: horiz right; pattern: pattern solid, fore_colour gray25',
        num_format_str='0.00%')


    font_style = XFStyle()
    font_style.font.bold = True
    font_style2 = XFStyle()
    font_style2.font.bold = False
    # output_folder = os.path.join(os.path.join(SITE_STORAGE, 'media', 'arreglos'))
    output_folder = os.path.join(os.path.join(SITE_STORAGE, 'media'))

    libdestino = xlwt.Workbook()
    hojadestino = libdestino.add_sheet("Listado")

    hojadestino.write_merge(0, 0, 0, 10, 'UNIVERSIDAD ESTATAL DE MILAGRO', titulo)
    hojadestino.write_merge(1, 1, 0, 10, 'DIRECCIÓN DE INVESTIGACIÓN Y POSGRADO', titulo2)
    hojadestino.write_merge(2, 2, 0, 10, 'LISTADO DE MATRICULADOS A PROGRAMAS DE MAESTRÍA', titulo2)

    fila = 4

    columnas = [
        (u" # ID INSCRIPCIÓN", 2500),
        (u" # ID MATRÍCULA", 2500),
        (u"PROGRAMAS", 8000),
        (u" # COHORTE", 2500),
        (u"PERIODO", 8000),
        (u"FECHA PERIODO INICIAL", 3000),
        (u"FECHA PERIDO FINAL", 3000),
        (u"ESTUDIANTE", 10000),
        (u"IDENTIFICACIÓN", 3900),
        (u"FECHA MATRICULA", 3000),
        (u"ESTADO", 4000),
        (u"ESTADO CONFIRMADO", 4000),
    ]

    for col_num in range(len(columnas)):
        hojadestino.write_merge(fila, fila + 1, col_num, col_num, columnas[col_num][0], fuentecabecera)
        hojadestino.col(col_num).width = columnas[col_num][1]

    cedulas = ['0923605976']

    matriculas = Matricula.objects.filter(status=True, nivel__periodo__tipo__id__in=[3, 4]
                                          # fecha__lt='2020-08-03'
                                          # inscripcion__persona__cedula__in=cedulas
                                          # inscripcion__persona__cedula__in=['1205907601', '0928477934','0916954613', '0919850255']
                                          # inscripcion__carrera__id=60,
                                          # nivel__periodo__id__in=[12, 13, 78, 84, 91],
                                          ).exclude(nivel__periodo__pk__in=[120, 128]).distinct().order_by('inscripcion__persona__apellido1',
                                                                'inscripcion__persona__apellido2',
                                                                'inscripcion__persona__nombres')


    totalmatriculas = matriculas.count()

    # print(totalmatriculas)
    c = 0

    horainicio = datetime.now()

    totalalumnos = 0


    fila = 6
    cedula = ''


    c = 1

    print(".:: GENERACIÓN DE LISTADO GENERAL DE MATRICULADOS - ESTADOS RETIRADO, EGRESADO, GRADDUADO, ETC ::.")

    for matricula in matriculas:

        print("Procesando ",c, " de ", totalmatriculas)
        periodo = matricula.nivel.periodo

        hojadestino.write(fila, 0, matricula.inscripcion.id, fuentenormal)
        hojadestino.write(fila, 1, matricula.id, fuentenormal)
        hojadestino.write(fila, 2, matricula.inscripcion.carrera.nombre, fuentenormal)
        hojadestino.write(fila, 3, matricula.nivel.periodo.cohorte, fuentenormalcent)
        hojadestino.write(fila, 4, matricula.nivel.periodo.nombre, fuentenormal)
        hojadestino.write(fila, 5, matricula.nivel.periodo.inicio, fuentefecha)
        hojadestino.write(fila, 6, matricula.nivel.periodo.fin, fuentefecha)
        hojadestino.write(fila, 7, matricula.inscripcion.persona.nombre_completo_inverso(), fuentenormal)
        hojadestino.write(fila, 8, matricula.inscripcion.persona.identificacion(), fuentenormal)
        hojadestino.write(fila, 9, matricula.fecha, fuentefecha)
        hojadestino.write(fila, 10, matricula.estado_inscripcion_maestria(), fuentenormal)
        hojadestino.write(fila, 11, "", fuentenormal)


        fila += 1
        c += 1

    print("Inicio: ", horainicio)
    print("Fin: ", datetime.now())

    libdestino.save(output_folder + "/MATRICULADOS_GENERAL_04052022.xls")
    print("Archivo creado. . .")


def generar_listado_rubros_pagos():
    fuentenormal = easyxtitulo = easyxf(
        'font: name Times New Roman, color-index black, bold on , height 350; alignment: horiz centre')
    titulo = easyxf(
        'font: name Times New Roman, color-index black, bold on , height 350; alignment: horiz centre')
    titulo2 = easyxf(
        'font: name Times New Roman, color-index black, bold on , height 250; alignment: horiz centre')
    fuentecabecera = easyxf(
        'font: name Verdana, color-index black, bold on, height 150; pattern: pattern solid, fore_colour gray25; alignment: vert distributed, horiz centre; borders: left thin, right thin, top thin, bottom thin')
    fuentenormal = easyxf(
        'font: name Verdana, color-index black, height 150; borders: left thin, right thin, top thin, bottom thin')
    fuentenormalder = easyxf(
        'font: name Verdana, color-index black, height 150; borders: left thin, right thin, top thin, bottom thin; alignment: horiz right')
    fuentenormalwrap = easyxf(
        'font: name Verdana, color-index black, height 150; borders: left thin, right thin, top thin, bottom thin')
    fuentenormalneg = easyxf(
        'font: name Verdana, color-index black, bold on , height 150; borders: left thin, right thin, top thin, bottom thin')
    fuentenormalnegrell = easyxf(
        'font: name Verdana, color-index black, bold on , height 150; borders: left thin, right thin, top thin, bottom thin; pattern: pattern solid, fore_colour gray25')
    fuentenormalwrap.alignment.wrap = True
    fuentenormalcent = easyxf(
        'font: name Verdana, color-index black, height 150; borders: left thin, right thin, top thin, bottom thin; alignment: horiz centre')
    fuentemoneda = easyxf(
        'font: name Verdana, color-index black, height 150; borders: left thin, right thin, top thin, bottom thin; alignment: horiz right',
        num_format_str=' "$" #,##0.00')
    fuentemonedaneg = easyxf(
        'font: name Verdana, color-index black, bold on, height 150; borders: left thin, right thin, top thin, bottom thin; alignment: horiz right; pattern: pattern solid, fore_colour gray25',
        num_format_str=' "$" #,##0.00')
    fuentefecha = easyxf(
        'font: name Verdana, color-index black, height 150; borders: left thin, right thin, top thin, bottom thin; alignment: horiz center',
        num_format_str='yyyy-mm-dd')
    fuentenumerodecimal = easyxf(
        'font: name Verdana, color-index black, height 150; borders: left thin, right thin, top thin, bottom thin; alignment: horiz right',
        num_format_str='#,##0.00')
    fuentenumeroentero = easyxf(
        'font: name Verdana, color-index black, height 150; borders: left thin, right thin, top thin, bottom thin; alignment: horiz right')
    fuenteporcentaje = easyxf(
        'font: name Verdana, color-index black, height 150; borders: left thin, right thin, top thin, bottom thin; alignment: horiz right',
        num_format_str='0%')
    fuenteporcentajeneg = easyxf(
        'font: name Verdana, color-index black, bold on, height 150; borders: left thin, right thin, top thin, bottom thin; alignment: horiz right; pattern: pattern solid, fore_colour gray25',
        num_format_str='0.00%')

    font_style = XFStyle()
    font_style.font.bold = True
    font_style2 = XFStyle()
    font_style2.font.bold = False
    # output_folder = os.path.join(os.path.join(SITE_STORAGE, 'media', 'arreglos'))
    output_folder = os.path.join(os.path.join(SITE_STORAGE, 'media'))

    libdestino = xlwt.Workbook()
    hojadestino = libdestino.add_sheet("Listado")

    hojadestino.write_merge(0, 0, 0, 10, 'UNIVERSIDAD ESTATAL DE MILAGRO', titulo)
    hojadestino.write_merge(1, 1, 0, 10, 'DIRECCIÓN DE INVESTIGACIÓN Y POSGRADO', titulo2)
    hojadestino.write_merge(2, 2, 0, 10, 'LISTADO DE MATRICULADOS A PROGRAMAS DE MAESTRÍA - RUBROS - PAGOS', titulo2)

    fila = 4

    columnas = [
        (u" # ID INSCRIPCIÓN", 2500),
        (u" # ID MATRÍCULA", 2500),
        (u"PROGRAMAS", 8000),
        (u" # COHORTE", 2500),
        (u"PERIODO", 8000),
        (u"ESTUDIANTE", 10000),
        (u"IDENTIFICACIÓN", 3900),
        (u"ID RUBRO", 4000),
        (u"FECHA VENCIMIENTO", 4000),
        (u"TOTAL RUBRO", 4000),
        (u"ID PAGO", 4000),
        (u"FECHA PAGO", 4000),
        (u"VALOR PAGADO", 4000),
    ]

    for col_num in range(len(columnas)):
        hojadestino.write_merge(fila, fila + 1, col_num, col_num, columnas[col_num][0], fuentecabecera)
        hojadestino.col(col_num).width = columnas[col_num][1]

    matriculas = Matricula.objects.filter(status=True, nivel__periodo__tipo__id__in=[3, 4]).exclude(nivel__periodo__pk__in=[120, 128]).distinct().order_by('inscripcion__persona__apellido1',
                                                                                                           'inscripcion__persona__apellido2',
                                                                                                           'inscripcion__persona__nombres')

    totalmatriculas = matriculas.count()

    # print(totalmatriculas)
    c = 0

    horainicio = datetime.now()

    totalalumnos = 0

    fila = 6
    cedula = ''

    c = 1

    print(".:: GENERACIÓN DE LISTADO GENERAL DE MATRICULADOS - RUBROS - PAGOS ::.")

    for matricula in matriculas:
        print("Procesando", c, " de", totalmatriculas)

        hojadestino.write(fila, 0, matricula.inscripcion.id, fuentenormalder)
        hojadestino.write(fila, 1, matricula.id, fuentenormal)
        hojadestino.write(fila, 2, matricula.inscripcion.carrera.nombre, fuentenormal)
        hojadestino.write(fila, 3, matricula.nivel.periodo.cohorte, fuentenormalcent)
        hojadestino.write(fila, 4, matricula.nivel.periodo.nombre, fuentenormal)
        hojadestino.write(fila, 5, matricula.inscripcion.persona.nombre_completo_inverso(), fuentenormal)
        hojadestino.write(fila, 6, matricula.inscripcion.persona.identificacion(), fuentenormal)

        rubros = matricula.rubros_maestria()
        cr = 0

        # .:: Tiene rubros ::.
        if rubros:
            for rubro in rubros:
                cr += 1
                if cr > 1:
                    hojadestino.write(fila, 0, matricula.inscripcion.id, fuentenormalder)
                    hojadestino.write(fila, 1, matricula.id, fuentenormal)
                    hojadestino.write(fila, 2, matricula.inscripcion.carrera.nombre, fuentenormal)
                    hojadestino.write(fila, 3, matricula.nivel.periodo.cohorte, fuentenormalcent)
                    hojadestino.write(fila, 4, matricula.nivel.periodo.nombre, fuentenormal)
                    hojadestino.write(fila, 5, matricula.inscripcion.persona.nombre_completo_inverso(), fuentenormal)
                    hojadestino.write(fila, 6, matricula.inscripcion.persona.identificacion(), fuentenormal)

                hojadestino.write(fila, 7, rubro.id, fuentenormal)
                hojadestino.write(fila, 8, rubro.fechavence, fuentefecha)
                hojadestino.write(fila, 9, rubro.valortotal, fuentemoneda)

                pagos = None
                # cp = 0
                pagos = rubro.pago_set.filter(status=True, pagoliquidacion__isnull=True).exclude(factura__valida=False).order_by('fecha')

                # .:: TIENE PAGOS ::.
                cp = 0
                if pagos:
                    for pago in pagos:
                        cp += 1

                        if cp > 1:
                            hojadestino.write(fila, 0, matricula.inscripcion.id, fuentenormalder)
                            hojadestino.write(fila, 1, matricula.id, fuentenormal)
                            hojadestino.write(fila, 2, matricula.inscripcion.carrera.nombre, fuentenormal)
                            hojadestino.write(fila, 3, matricula.nivel.periodo.cohorte, fuentenormalcent)
                            hojadestino.write(fila, 4, matricula.nivel.periodo.nombre, fuentenormal)
                            hojadestino.write(fila, 5, matricula.inscripcion.persona.nombre_completo_inverso(), fuentenormal)
                            hojadestino.write(fila, 6, matricula.inscripcion.persona.identificacion(), fuentenormal)
                            hojadestino.write(fila, 7, rubro.id, fuentenormal)
                            hojadestino.write(fila, 8, rubro.fechavence, fuentefecha)
                            hojadestino.write(fila, 9, rubro.valortotal, fuentemoneda)

                        hojadestino.write(fila, 10, pago.id, fuentenormal)
                        hojadestino.write(fila, 11, pago.fecha, fuentefecha)
                        hojadestino.write(fila, 12, pago.valortotal, fuentemoneda)

                        fila += 1
                else:
                    hojadestino.write(fila, 10, "", fuentenormal)
                    hojadestino.write(fila, 11, "", fuentefecha)
                    hojadestino.write(fila, 12, "", fuentemoneda)

                    fila += 1
                # .:: TIENE PAGOS ::.


        else:
            hojadestino.write(fila, 7, "", fuentenormal)
            hojadestino.write(fila, 8, "", fuentefecha)
            hojadestino.write(fila, 9, "", fuentemoneda)
            fila += 1

        # .:: Tiene rubros ::.
        c += 1

    libdestino.save(output_folder + "/RUBROS_PAGOS_MAESTRIA.xls")
    print("Finalizado. . .")


def rubros_vencidos():
    fuentenormal = easyxtitulo = easyxf(
        'font: name Times New Roman, color-index black, bold on , height 350; alignment: horiz centre')
    titulo = easyxf(
        'font: name Times New Roman, color-index black, bold on , height 350; alignment: horiz centre')
    titulo2 = easyxf(
        'font: name Times New Roman, color-index black, bold on , height 250; alignment: horiz centre')
    fuentecabecera = easyxf(
        'font: name Verdana, color-index black, bold on, height 150; pattern: pattern solid, fore_colour gray25; alignment: vert distributed, horiz centre; borders: left thin, right thin, top thin, bottom thin')
    fuentenormal = easyxf(
        'font: name Verdana, color-index black, height 150; borders: left thin, right thin, top thin, bottom thin')
    fuentenormalder = easyxf(
        'font: name Verdana, color-index black, height 150; borders: left thin, right thin, top thin, bottom thin; alignment: horiz right')
    fuentenormalwrap = easyxf(
        'font: name Verdana, color-index black, height 150; borders: left thin, right thin, top thin, bottom thin')
    fuentenormalneg = easyxf(
        'font: name Verdana, color-index black, bold on , height 150; borders: left thin, right thin, top thin, bottom thin')
    fuentenormalnegrell = easyxf(
        'font: name Verdana, color-index black, bold on , height 150; borders: left thin, right thin, top thin, bottom thin; pattern: pattern solid, fore_colour gray25')
    fuentenormalwrap.alignment.wrap = True
    fuentenormalcent = easyxf(
        'font: name Verdana, color-index black, height 150; borders: left thin, right thin, top thin, bottom thin; alignment: horiz centre')
    fuentemoneda = easyxf(
        'font: name Verdana, color-index black, height 150; borders: left thin, right thin, top thin, bottom thin; alignment: horiz right',
        num_format_str=' "$" #,##0.00')
    fuentemonedaneg = easyxf(
        'font: name Verdana, color-index black, bold on, height 150; borders: left thin, right thin, top thin, bottom thin; alignment: horiz right; pattern: pattern solid, fore_colour gray25',
        num_format_str=' "$" #,##0.00')
    fuentefecha = easyxf(
        'font: name Verdana, color-index black, height 150; borders: left thin, right thin, top thin, bottom thin; alignment: horiz center',
        num_format_str='yyyy-mm-dd')
    fuentenumerodecimal = easyxf(
        'font: name Verdana, color-index black, height 150; borders: left thin, right thin, top thin, bottom thin; alignment: horiz right',
        num_format_str='#,##0.00')
    fuentenumeroentero = easyxf(
        'font: name Verdana, color-index black, height 150; borders: left thin, right thin, top thin, bottom thin; alignment: horiz right')
    fuenteporcentaje = easyxf(
        'font: name Verdana, color-index black, height 150; borders: left thin, right thin, top thin, bottom thin; alignment: horiz right',
        num_format_str='0%')
    fuenteporcentajeneg = easyxf(
        'font: name Verdana, color-index black, bold on, height 150; borders: left thin, right thin, top thin, bottom thin; alignment: horiz right; pattern: pattern solid, fore_colour gray25',
        num_format_str='0.00%')

    font_style = XFStyle()
    font_style.font.bold = True
    font_style2 = XFStyle()
    font_style2.font.bold = False
    # output_folder = os.path.join(os.path.join(SITE_STORAGE, 'media', 'arreglos'))
    output_folder = os.path.join(os.path.join(SITE_STORAGE, 'media'))

    libdestino = xlwt.Workbook()
    hojadestino = libdestino.add_sheet("Listado")

    hojadestino.write_merge(0, 0, 0, 10, 'UNIVERSIDAD ESTATAL DE MILAGRO', titulo)
    hojadestino.write_merge(1, 1, 0, 10, 'DIRECCIÓN DE INVESTIGACIÓN Y POSGRADO', titulo2)
    hojadestino.write_merge(2, 2, 0, 10, 'LISTADO DE MATRICULADOS A PROGRAMAS DE MAESTRÍA - RUBROS - PAGOS', titulo2)

    fila = 4

    columnas = [
        (u" # ID INSCRIPCIÓN", 2500),
        (u" # ID MATRÍCULA", 2500),
        (u"PROGRAMAS", 8000),
        (u" # COHORTE", 2500),
        (u"PERIODO", 8000),
        (u"ESTUDIANTE", 10000),
        (u"IDENTIFICACIÓN", 3900),
        (u"ID RUBRO", 4000),
        (u"FECHA VENCIMIENTO", 4000),
        (u"TOTAL RUBRO", 4000),
        (u"ID PAGO", 4000),
        (u"FECHA PAGO", 4000),
        (u"VALOR PAGADO", 4000),
    ]

    for col_num in range(len(columnas)):
        hojadestino.write_merge(fila, fila + 1, col_num, col_num, columnas[col_num][0], fuentecabecera)
        hojadestino.col(col_num).width = columnas[col_num][1]


@transaction.atomic()
def bloquear_rubros_proceso_coactiva():
    conexion = connections['epunemi']
    cnepunemi = conexion.cursor()
    try:
        fuentecabecera = easyxf(
            'font: name Verdana, color-index black, bold on, height 150; pattern: pattern solid, fore_colour gray25; alignment: vert distributed, horiz centre; borders: left thin, right thin, top thin, bottom thin')
        fuentenormal = easyxf(
            'font: name Verdana, color-index black, height 150; borders: left thin, right thin, top thin, bottom thin')
        fuentenormalwrap = easyxf(
            'font: name Verdana, color-index black, height 150; borders: left thin, right thin, top thin, bottom thin')
        fuentenormalneg = easyxf(
            'font: name Verdana, color-index black, bold on , height 150; borders: left thin, right thin, top thin, bottom thin')
        fuentenormalnegrell = easyxf(
            'font: name Verdana, color-index black, bold on , height 150; borders: left thin, right thin, top thin, bottom thin; pattern: pattern solid, fore_colour gray25')
        fuentenormalwrap.alignment.wrap = True
        fuentenormalcent = easyxf(
            'font: name Verdana, color-index black, height 150; borders: left thin, right thin, top thin, bottom thin; alignment: horiz centre')
        fuentemoneda = easyxf(
            'font: name Verdana, color-index black, height 150; borders: left thin, right thin, top thin, bottom thin; alignment: horiz right',
            num_format_str=' "$" #,##0.00')
        fuentemonedaneg = easyxf(
            'font: name Verdana, color-index black, bold on, height 150; borders: left thin, right thin, top thin, bottom thin; alignment: horiz right; pattern: pattern solid, fore_colour gray25',
            num_format_str=' "$" #,##0.00')
        fuentefecha = easyxf(
            'font: name Verdana, color-index black, height 150; borders: left thin, right thin, top thin, bottom thin; alignment: horiz center',
            num_format_str='yyyy-mm-dd')
        fuentenumerodecimal = easyxf(
            'font: name Verdana, color-index black, height 150; borders: left thin, right thin, top thin, bottom thin; alignment: horiz right',
            num_format_str='#,##0.00')
        fuentenumeroentero = easyxf(
            'font: name Verdana, color-index black, height 150; borders: left thin, right thin, top thin, bottom thin; alignment: horiz right')

        output_folder = os.path.join(os.path.join(SITE_STORAGE, 'media'))
        liborigen = xlrd.open_workbook(output_folder + '/BLOQUEORUBROSCOACTIVA1.xls')

        libdestino = xlwt.Workbook()
        hojadestino = libdestino.add_sheet("Listado")

        fil = 0

        columnas = [
            (u"Programa", 7000),
            (u"Cohorte", 7000),
            (u"Cédula", 4500),
            (u"Estudiante", 9000),
            (u"IDRubroUnemi", 2000),
            (u"IDRubroEpUnemi", 2000),
            (u"Observación", 9000),
            (u"Procesar", 2000)
        ]

        for col_num in range(len(columnas)):
            hojadestino.write(fil, col_num, columnas[col_num][0], fuentecabecera)
            hojadestino.col(col_num).width = columnas[col_num][1]

        sheet = liborigen.sheet_by_index(0)

        c = 1
        filadest = 1
        matriculas = 0

        for fila in range(sheet.nrows):
            if fila >= 2:
                observacion = ""
                print("Procesanso", c, " de 87")

                cols = sheet.row_values(fila)
                cedula = cols[3].strip() if type(cols[3]) == str else str(int(cols[3])).strip()
                cedula = cedula if len(cedula) == 10 else '0' + cedula
                print(cedula)

                # if Matricula.objects.values("id").filter(inscripcion__persona__cedula=cedula, nivel__periodo__tipo=3).count() > 1:
                #     print("Mas de una matricula:", cedula)
                #     matriculas += 1
                #
                if cedula == '0921632279':
                    matricula = Matricula.objects.get(inscripcion__persona__cedula=cedula, nivel__periodo__tipo=3, inscripcion__carrera__id=174)
                    programa = matricula.inscripcion.carrera.nombre
                    cohorte = matricula.nivel.periodo.cohorte
                    nombres = matricula.inscripcion.persona.nombre_completo_inverso()
                else:
                    if Matricula.objects.values("id").filter(inscripcion__persona__cedula=cedula, nivel__periodo__tipo=3).exists():
                        matricula = Matricula.objects.get(inscripcion__persona__cedula=cedula, nivel__periodo__tipo=3)
                        programa = matricula.inscripcion.carrera.nombre
                        cohorte = matricula.nivel.periodo.cohorte
                        nombres = matricula.inscripcion.persona.nombre_completo_inverso()
                    else:
                        inscripcion = Inscripcion.objects.get(persona__cedula=cedula, carrera__nombre__icontains='MAESTR')
                        programa = inscripcion.carrera.nombre
                        nombres = inscripcion.persona.nombre_completo_inverso()
                        cohorte = "NO VIGENTE"
                        observacion = "NO TIENE MATRICULA"

                rubros_posgrado = Rubro.objects.filter(status=True, persona__cedula=cedula, tipo__tiporubro__in=[1, 5], tipo__subtiporubro=1)
                codigos_unemi = ""
                codigos_epunemi = ""
                if rubros_posgrado:
                    procesar = "SI"
                    for rubro in rubros_posgrado:
                        codigos_unemi = codigos_unemi + str(rubro.id) + ","
                        codigos_epunemi = codigos_epunemi + str(rubro.idrubroepunemi) + ","
                        idepunemi = rubro.idrubroepunemi

                        # Bloqueo en unemi
                        rubro.bloqueado = True
                        rubro.save()

                        print("Bloqueado en UNEMI")

                        # Bloqueo en epunemi en caso de existir
                        if idepunemi > 0:
                            sql = """SELECT ru.id,ru.nombre,ru.valor,ru.valortotal,ru.saldo, ru.totalunemi, ru.observacion,ru.refinanciado,ru.bloqueado, ru.cancelado FROM sagest_rubro as ru WHERE ru.status=TRUE AND ru.anulado=FALSE AND ru.id=%s;""" % (idepunemi)
                            cnepunemi.execute(sql)
                            rubroepunemi = cnepunemi.fetchone()
                            if rubroepunemi is not None:
                                # Bloquer rubro en EPUNEMI
                                sql = """UPDATE sagest_rubro SET bloqueado=TRUE, bloqueadopornovedad=TRUE, fecha_modificacion=NOW(), usuario_modificacion_id=1, observacion='BLOQUEO POR ENCONTRARSE INMERSO EN PROCESO DE COACTIVA - E-MAIL 06/07/2022 MGILERH' WHERE id=%s""" % (idepunemi)
                                cnepunemi.execute(sql)

                                print("Bloqueado en EPUNEMI")

                else:
                    procesar = "NO"
                    observacion = 'NO TIENE RUBROS DE POSGRADO'

                hojadestino.write(filadest, 0, programa, fuentenormal)
                hojadestino.write(filadest, 1, cohorte, fuentenormal)
                hojadestino.write(filadest, 2, cedula, fuentenormal)
                hojadestino.write(filadest, 3, nombres, fuentenormal)
                hojadestino.write(filadest, 4, codigos_unemi, fuentenormal)
                hojadestino.write(filadest, 5, codigos_epunemi, fuentenormal)
                hojadestino.write(filadest, 6, observacion, fuentenormal)
                hojadestino.write(filadest, 7, procesar, fuentenormal)

                filadest += 1
                c += 1


        conexion.commit()
        cnepunemi.close()

        libdestino.save(output_folder + "/BLOQUEADOS_COACTIVA_1.xls")

        # print("Procesar: ", procesar)
        # print("No Procesar: ", noprocesar)
        print("Proceso finalizado. . .")
    except Exception as ex:
        transaction.set_rollback(True)
        msg = ex.__str__()
        print(msg)


def reporte_pagos_unemi_resumen():
    try:
        fuentecabecera = easyxf(
            'font: name Verdana, color-index black, bold on, height 150; pattern: pattern solid, fore_colour gray25; alignment: vert distributed, horiz centre; borders: left thin, right thin, top thin, bottom thin')
        fuentenormal = easyxf(
            'font: name Verdana, color-index black, height 150; borders: left thin, right thin, top thin, bottom thin')
        fuentenormalwrap = easyxf(
            'font: name Verdana, color-index black, height 150; borders: left thin, right thin, top thin, bottom thin')
        fuentenormalneg = easyxf(
            'font: name Verdana, color-index black, bold on , height 150; borders: left thin, right thin, top thin, bottom thin')
        fuentenormalnegrell = easyxf(
            'font: name Verdana, color-index black, bold on , height 150; borders: left thin, right thin, top thin, bottom thin; pattern: pattern solid, fore_colour gray25')
        fuentenormalwrap.alignment.wrap = True
        fuentenormalcent = easyxf(
            'font: name Verdana, color-index black, height 150; borders: left thin, right thin, top thin, bottom thin; alignment: horiz centre')
        fuentemoneda = easyxf(
            'font: name Verdana, color-index black, height 150; borders: left thin, right thin, top thin, bottom thin; alignment: horiz right',
            num_format_str=' "$" #,##0.00')
        fuentemonedaneg = easyxf(
            'font: name Verdana, color-index black, bold on, height 150; borders: left thin, right thin, top thin, bottom thin; alignment: horiz right; pattern: pattern solid, fore_colour gray25',
            num_format_str=' "$" #,##0.00')
        fuentefecha = easyxf(
            'font: name Verdana, color-index black, height 150; borders: left thin, right thin, top thin, bottom thin; alignment: horiz center',
            num_format_str='yyyy-mm-dd')
        fuentenumerodecimal = easyxf(
            'font: name Verdana, color-index black, height 150; borders: left thin, right thin, top thin, bottom thin; alignment: horiz right',
            num_format_str='#,##0.00')
        fuentenumeroentero = easyxf(
            'font: name Verdana, color-index black, height 150; borders: left thin, right thin, top thin, bottom thin; alignment: horiz right')

        output_folder = os.path.join(os.path.join(SITE_STORAGE, 'media'))
        # liborigen = xlrd.open_workbook(output_folder + '/BLOQUEORUBROSCOACTIVA1.xls')

        libdestino = xlwt.Workbook()
        hojadestino = libdestino.add_sheet("Listado")

        fil = 0

        columnas = [
            (u"Fecha", 3000),
            (u"Forma de Pago", 3000),
            (u"Cantidad", 3000),
            (u"Total", 3000)
        ]

        for col_num in range(len(columnas)):
            hojadestino.write(fil, col_num, columnas[col_num][0], fuentecabecera)
            hojadestino.col(col_num).width = columnas[col_num][1]


        filadest = 1

        iniciomes = datetime.strptime('2022' + '-' + '05' + '-' + '01', '%Y-%m-%d').date()
        fecha = iniciomes
        finmes = datetime.strptime('2022' + '-' + '07' + '-' + '12', '%Y-%m-%d').date()

        totalpagos = 0

        while fecha <= finmes:
            print(fecha)
            pagos = Pago.objects.filter(fecha=fecha,
                                        pagoliquidacion__isnull=True,
                                        status=True,
                                        rubro__matricula__nivel__periodo__tipo__id__in=[3, 4],
                                        rubro__tipo__subtiporubro=1,
                                        rubro__status=True,
                                        epunemipago=True
                                        ).exclude(factura__valida=False).order_by('fecha')

            limite = pagos.count()
            efectivou = 0
            totalpagos = 0


            cantidadCUENTAXCOBRAR = 0
            totalCUENTAXCOBRAR = 0
            cantidadNOTACREDITO = 0
            totalNOTACREDITO = 0
            cantidadEFECTIVO = 0
            totalEFECTIVO = 0
            cantidadTRANSFERENCIA = 0
            totalTRANSFERENCIA = 0
            cantidadDEPOSITO = 0
            totalDEPOSITO = 0
            cantidadTARJETA = 0
            totalTARJETA = 0
            cantidadCOMPROBANTE = 0
            totalCOMPROBANTE = 0

            totalpagado = 0
            if pagos:
                for pago in pagos:
                    # pago.pagoepunemi_set.all()[0].pagadocomo
                    totalpagos += 1
                    # print("Procesando ", totalpagos, " de ", limite)

                    tipopago = pago.tipo()

                    # print(pago.id, pago.fecha, pago.valortotal, tipopago)

                    if tipopago == 'EFECTIVO':
                        formapago = "EFECTIVO"
                        # print("EFECTIVO")
                    else:
                        formapago = pago.pagoepunemi_set.all()[0].pagadocomo
                        # print(formapago)

                    if formapago == 'CUENTAXCOBRAR':
                        cantidadCUENTAXCOBRAR += 1
                        totalCUENTAXCOBRAR += pago.valortotal
                    elif formapago == 'NOTACREDITO':
                        cantidadNOTACREDITO += 1
                        totalNOTACREDITO += pago.valortotal
                    elif formapago == 'EFECTIVO':
                        cantidadEFECTIVO += 1
                        totalEFECTIVO += pago.valortotal
                    elif formapago == 'TRANSFERENCIA':
                        cantidadTRANSFERENCIA += 1
                        totalTRANSFERENCIA += pago.valortotal
                    elif formapago == 'DEPOSITO':
                        cantidadDEPOSITO += 1
                        totalDEPOSITO += pago.valortotal
                    else:
                        cantidadTARJETA += 1
                        totalTARJETA += pago.valortotal

                    totalpagado += pago.valortotal


                comprobantessubidos = ComprobanteAlumno.objects.filter(status=True, fechapago=fecha)
                totalCOMPROBANTE = 0
                cantidadCOMPROBANTE = 0
                for comprobantes in comprobantessubidos:
                    cantidadCOMPROBANTE += 1
                    totalCOMPROBANTE += comprobantes.valor


                print("Total registros de pago:", totalpagos)
                print("Total pagado:", totalpagado)
                print("CUENTAXCOBRAR ", cantidadCUENTAXCOBRAR, " - $ ", totalCUENTAXCOBRAR )
                print("NOTACREDITO ", cantidadNOTACREDITO, " - $ ", totalNOTACREDITO )
                print("EFECTIVO ", cantidadEFECTIVO, " - $ ", totalEFECTIVO )
                print("TRANSFERENCIA ", cantidadTRANSFERENCIA, " - $ ", totalTRANSFERENCIA )
                print("DEPOSITO ", cantidadDEPOSITO, " - $ ", totalDEPOSITO )
                print("TARJETA ", cantidadTARJETA, " - $ ", totalTARJETA )

                hojadestino.write(filadest, 0, fecha, fuentefecha)
                hojadestino.write(filadest, 1, "CUENTAXCOBRAR", fuentenormal)
                hojadestino.write(filadest, 2, cantidadCUENTAXCOBRAR, fuentenormal)
                hojadestino.write(filadest, 3, totalCUENTAXCOBRAR, fuentemoneda)
                filadest += 1

                hojadestino.write(filadest, 0, fecha, fuentefecha)
                hojadestino.write(filadest, 1, "NOTACREDITO", fuentenormal)
                hojadestino.write(filadest, 2, cantidadNOTACREDITO, fuentenormal)
                hojadestino.write(filadest, 3, totalNOTACREDITO, fuentemoneda)
                filadest += 1

                hojadestino.write(filadest, 0, fecha, fuentefecha)
                hojadestino.write(filadest, 1, "EFECTIVO", fuentenormal)
                hojadestino.write(filadest, 2, cantidadEFECTIVO, fuentenormal)
                hojadestino.write(filadest, 3, totalEFECTIVO, fuentemoneda)
                filadest += 1

                hojadestino.write(filadest, 0, fecha, fuentefecha)
                hojadestino.write(filadest, 1, "TRANSFERENCIA", fuentenormal)
                hojadestino.write(filadest, 2, cantidadTRANSFERENCIA, fuentenormal)
                hojadestino.write(filadest, 3, totalTRANSFERENCIA, fuentemoneda)
                filadest += 1

                hojadestino.write(filadest, 0, fecha, fuentefecha)
                hojadestino.write(filadest, 1, "DEPOSITO", fuentenormal)
                hojadestino.write(filadest, 2, cantidadDEPOSITO, fuentenormal)
                hojadestino.write(filadest, 3, totalDEPOSITO, fuentemoneda)
                filadest += 1

                hojadestino.write(filadest, 0, fecha, fuentefecha)
                hojadestino.write(filadest, 1, "TARJETA", fuentenormal)
                hojadestino.write(filadest, 2, cantidadTARJETA, fuentenormal)
                hojadestino.write(filadest, 3, totalTARJETA, fuentemoneda)
                filadest += 1

                hojadestino.write(filadest, 0, fecha, fuentefecha)
                hojadestino.write(filadest, 1, "COMPROBANTES REGISTRADOS", fuentenormal)
                hojadestino.write(filadest, 2, cantidadCOMPROBANTE, fuentenormal)
                hojadestino.write(filadest, 3, totalCOMPROBANTE, fuentemoneda)
                filadest += 1



            fecha = fecha + relativedelta(days=1)
            filadest += 1


        libdestino.save(output_folder + "/REPORTE_PAGOS_UNEMI_EPUNEMI.xls")
        print("Proceso finalizado. . .")
    except Exception as ex:
        msg = ex.__str__()
        print(msg)


@transaction.atomic()
def crear_grupos_investigacion():

    try:
        fuentecabecera = easyxf(
            'font: name Verdana, color-index black, bold on, height 150; pattern: pattern solid, fore_colour gray25; alignment: vert distributed, horiz centre; borders: left thin, right thin, top thin, bottom thin')
        fuentenormal = easyxf(
            'font: name Verdana, color-index black, height 150; borders: left thin, right thin, top thin, bottom thin')
        fuentenormalwrap = easyxf(
            'font: name Verdana, color-index black, height 150; borders: left thin, right thin, top thin, bottom thin')
        fuentenormalneg = easyxf(
            'font: name Verdana, color-index black, bold on , height 150; borders: left thin, right thin, top thin, bottom thin')
        fuentenormalnegrell = easyxf(
            'font: name Verdana, color-index black, bold on , height 150; borders: left thin, right thin, top thin, bottom thin; pattern: pattern solid, fore_colour gray25')
        fuentenormalwrap.alignment.wrap = True
        fuentenormalcent = easyxf(
            'font: name Verdana, color-index black, height 150; borders: left thin, right thin, top thin, bottom thin; alignment: horiz centre')
        fuentemoneda = easyxf(
            'font: name Verdana, color-index black, height 150; borders: left thin, right thin, top thin, bottom thin; alignment: horiz right',
            num_format_str=' "$" #,##0.00')
        fuentemonedaneg = easyxf(
            'font: name Verdana, color-index black, bold on, height 150; borders: left thin, right thin, top thin, bottom thin; alignment: horiz right; pattern: pattern solid, fore_colour gray25',
            num_format_str=' "$" #,##0.00')
        fuentefecha = easyxf(
            'font: name Verdana, color-index black, height 150; borders: left thin, right thin, top thin, bottom thin; alignment: horiz center',
            num_format_str='yyyy-mm-dd')
        fuentenumerodecimal = easyxf(
            'font: name Verdana, color-index black, height 150; borders: left thin, right thin, top thin, bottom thin; alignment: horiz right',
            num_format_str='#,##0.00')
        fuentenumeroentero = easyxf(
            'font: name Verdana, color-index black, height 150; borders: left thin, right thin, top thin, bottom thin; alignment: horiz right')

        output_folder = os.path.join(os.path.join(SITE_STORAGE, 'media'))
        # output_folder = os.path.join(os.path.join(SITE_STORAGE, 'media', 'archivosparaprocesos'))
        # liborigen = xlrd.open_workbook(output_folder + '/POSGRADO_10.xlsx')
        liborigen = xlrd.open_workbook(output_folder + '/GRUPOS_INVESTIGACION_1.xls')

        libdestino = xlwt.Workbook()
        hojadestino = libdestino.add_sheet("Listado")

        fil = 0

        columnas = [
            (u"Nombres", 7000),
            (u"Cédula", 2500),
            (u"IdPersona", 2500),
            (u"IdGrupo", 2500),
            (u"RolGrupo", 2500),
            (u"Observación", 2000)
        ]

        for col_num in range(len(columnas)):
            hojadestino.write(fil, col_num, columnas[col_num][0], fuentecabecera)
            hojadestino.col(col_num).width = columnas[col_num][1]

        sheet = liborigen.sheet_by_index(0)

        c = 0
        creados = 0
        filadest = 1

        for fila in range(sheet.nrows):
            if fila >= 2:
                cols = sheet.row_values(fila)
                nombres = cols[0].strip()
                cedula = cols[1].strip()
                idgrupo = cols[2]
                rol = cols[3]

                print("Procesando", nombres)

                idpersona = None
                observacion = 'NO EXISTE'
                if cedula:
                    if Persona.objects.values("id").filter(cedula=cedula, status=True).exists():
                        idpersona = Persona.objects.filter(cedula=cedula, status=True)[0].id
                        observacion = ''
                    elif Persona.objects.values("id").filter(pasaporte=cedula, status=True).exists():
                        idpersona = Persona.objects.filter(pasaporte=cedula, status=True)[0].id
                        observacion = ''

                    if idpersona:
                        integrantegrupo = GrupoInvestigacionIntegrante(
                            grupo_id=idgrupo,
                            funcion=rol,
                            persona_id=idpersona
                        )
                        integrantegrupo.save()
                        creados += 1

                hojadestino.write(filadest, 0, nombres, fuentenormal)
                hojadestino.write(filadest, 1, cedula, fuentenormal)
                hojadestino.write(filadest, 2, idpersona, fuentenormal)
                hojadestino.write(filadest, 3, idgrupo, fuentenormal)
                hojadestino.write(filadest, 4, rol, fuentenormal)
                hojadestino.write(filadest, 5, observacion, fuentenormal)


                filadest += 1
                c += 1


        libdestino.save(output_folder + "/PROCESADOS_GRUPOINVESTIGACION_1.xls")

        print("Integrantes creados ", creados, " de ", c)
        print("Proceso finalizado. . .")
    except Exception as ex:
        transaction.set_rollback(True)
        msg = ex.__str__()
        print(msg)

def asignar_grupo():
    from django.contrib.auth.models import Group
    personaexterna = Externo.objects.get(persona__cedula='1756611045')

    user = personaexterna.persona.usuario

    g = Group.objects.get(pk=372)
    g.user_set.add(user)
    g.save()


@transaction.atomic()
def importar_publicaciones_orcid():
    import requests
    import json
    try:
        fechaactual = datetime.strptime('2022' + '-' + '11' + '-' + '20', '%Y-%m-%d').date()
        # fechaactual = datetime.now().date()
        totalnuevas = 0
        listado = []
        print(".:: Proceso de importación de publicaciones del sitio web ORCID ::.")

        # Proceso se debe ejecutar día DOMINGO
        if dia_semana_enletras_fecha(fechaactual).upper() == 'DOMINGO':
            redpersonas = RedPersona.objects.filter(status=True, tipo__id=1, verificada=True).order_by('persona__apellido1', 'persona__apellido2', 'persona__nombres')

            c = 1
            total = len(redpersonas)
            for redpersona in redpersonas:
                identificador = redpersona.identificador
                print("Procesando", c, "de", total)
                print("Inicio Consulta publicaciones para Orcid ID:", identificador, "-", redpersona.persona.nombre_completo_inverso())

                # Consulto las publicaciones por medio del orcid ID
                r = requests.get(f'https://pub.orcid.org/v3.0/{identificador}/works', headers={'accept': 'application/json'})

                registroorcid = r.json()
                publicaciones = registroorcid["group"]
                if publicaciones:
                    t = 0
                    pnuevap = 0
                    for publicacion in publicaciones:
                        print("--Work-Summary--")
                        resumenpublicacion = publicacion["work-summary"]

                        for resumen in resumenpublicacion:
                            idpublicacion = resumen["path"].split("/")[-1]
                            pathpublicacion = resumen["path"]
                            print("Procesando Publicación ID:", idpublicacion)

                            # Consulto el detalle de la publicación mediante el path
                            rpub = requests.get(f'https://pub.orcid.org/v3.0{pathpublicacion}', headers={'accept': 'application/json'})
                            publicacion = rpub.json()

                            fcrea = datetime.fromtimestamp(int(publicacion["created-date"]["value"]) / 1000)
                            fmodi = datetime.fromtimestamp(int(publicacion["last-modified-date"]["value"]) / 1000)

                            fechacreacion = fcrea.strftime("%Y-%m-%d %H:%M:%S")
                            fechaedicion = fmodi.strftime("%Y-%m-%d %H:%M:%S")
                            titulo = publicacion["title"]["title"]["value"]
                            subtitulo = publicacion["title"]["subtitle"]["value"] if publicacion["title"]["subtitle"] else None
                            titulorevista = publicacion["journal-title"]["value"] if publicacion["journal-title"] else None
                            descripcion = publicacion["short-description"] if publicacion["short-description"] else None
                            tipo = publicacion["type"]
                            aniopub = mespub = diapub = None

                            if publicacion["publication-date"]:
                                aniopub = int(publicacion["publication-date"]["year"]["value"]) if publicacion["publication-date"]["year"] else None
                                mespub = int(publicacion["publication-date"]["month"]["value"]) if publicacion["publication-date"]["month"] else None
                                diapub = int(publicacion["publication-date"]["day"]["value"]) if publicacion["publication-date"]["day"] else None

                            urlpub = publicacion["url"]["value"] if publicacion["url"] else None
                            colaboradores = None
                            contributors = publicacion["contributors"]["contributor"]
                            if contributors:
                                colaboradores = ",".join([contributor["credit-name"]["value"] for contributor in contributors])

                            print("Fecha de creación:", fechacreacion)
                            print("Fecha de modificación:", fechaedicion)
                            print("Título:", titulo)
                            print("Sub-Título:", subtitulo)
                            print("Título de la revista:", titulorevista)
                            print("Descripción:", descripcion)
                            print("Tipo:", tipo)
                            print("Año publicación:", aniopub)
                            print("Mes publicación:", mespub)
                            print("Día publicación:", diapub)
                            print("Url:", urlpub)
                            print("Colaboradores:", colaboradores)

                            # Si no existe la publicación la creo sino edito
                            if not PublicacionOrcid.objects.values("id").filter(status=True, redpersona=redpersona, codigo=idpublicacion).exists():
                                publicacionorcid = PublicacionOrcid(
                                    redpersona=redpersona,
                                    codigo=idpublicacion,
                                    fechacrea=fechacreacion,
                                    fechaedita=fechaedicion,
                                    titulo=titulo,
                                    subtitulo=subtitulo,
                                    titulorevista=titulorevista,
                                    descripcion=descripcion,
                                    tipo=tipo,
                                    anio=aniopub,
                                    mes=mespub,
                                    dia=diapub,
                                    url=urlpub,
                                    colaborador=colaboradores,
                                    procesada=False
                                )
                                publicacionorcid.save()

                                print("Registro de publicación creado...")
                                pnuevap += 1
                                totalnuevas += 1
                            else:
                                publicacionorcid = PublicacionOrcid.objects.get(status=True, redpersona=redpersona, codigo=idpublicacion)
                                publicacionorcid.fechacrea = fechacreacion
                                publicacionorcid.fechaedita = fechaedicion
                                publicacionorcid.titulo = titulo
                                publicacionorcid.subtitulo = subtitulo
                                publicacionorcid.titulorevista = titulorevista
                                publicacionorcid.descripcion = descripcion
                                publicacionorcid.tipo = tipo
                                publicacionorcid.anio = aniopub
                                publicacionorcid.mes = mespub
                                publicacionorcid.dia = diapub
                                publicacionorcid.url = urlpub
                                publicacionorcid.colaborador = colaboradores
                                publicacionorcid.save()

                                print("Registro de publicación actualizado...")

                            print("")
                            t += 1

                    print("Total publicaciones procesadas:", t)

                    # Si la persona tiene nuevas publicaciones la agrego a la lista
                    if pnuevap > 0:
                        listado.append(
                            {"identificacion": redpersona.persona.identificacion(),
                             "nombres": redpersona.persona.nombre_completo_inverso(),
                             "total": pnuevap}
                        )
                else:
                    print("NO TIENE PUBLICACIONES")

                print("Fin Consulta publicaciones para Orcid ID:", identificador)
                print("")
                print("================================")
                c += 1

            # Si se registraron nuevas publicaciones notificar por e-mail a la coordinación de investigación
            if totalnuevas > 0:
                # Obtengo la(s) cuenta(s) de correo desde la cual(es) se envía el e-mail
                listacuentascorreo = [0, 8, 9, 10, 11, 12, 13]  # sga@unemi.edu.ec, sga2@unemi.edu.ec, ..., sga7@unemi.edu.ec

                # Notificar por e-mail a la Coordinación de Investigación
                # lista_email_envio = ['investigacion.dip@unemi.edu.ec']
                lista_email_envio = ['isaltosm@unemi.edu.ec']
                lista_email_cco = ['ivan_saltos_medina@hotmail.com']
                lista_adjuntos = []

                fechaenvio = datetime.now().date()
                horaenvio = datetime.now().time()
                cuenta = cuenta_email_disponible_para_envio(listacuentascorreo)

                tituloemail = "Importación de Publicaciones del Sitio Web de ORCID"
                titulo = "Publicaciones Sitio Web ORCID"
                tiponotificacion = "REGCOORDINV"

                send_html_mail(tituloemail,
                               "emails/publicacionorcid.html",
                               {'sistema': u'SGA - UNEMI',
                                'titulo': titulo,
                                'fecha': fechaenvio,
                                'hora': horaenvio,
                                'tiponotificacion': tiponotificacion,
                                'saludo': 'Estimados',
                                'totalnuevas': totalnuevas,
                                'listado': listado
                                },
                               lista_email_envio,
                               lista_email_cco,
                               lista_adjuntos,
                               cuenta=CUENTAS_CORREOS[cuenta][1]
                               )
                print("Correo enviado a la Coordinación de Investigación...")

            print("Proceso de importación de publicaciones del sitio web ORCID finalizado. . .")
        else:
            print("ATENCIÓN: El proceso únicamente se ejecuta días DOMINGO...")

    except Exception as ex:
        transaction.set_rollback(True)
        msg = ex.__str__()
        print("Error: ", msg)


@transaction.atomic()
def importar_publicaciones_scopus():
    import requests
    import json
    try:
        # fechaactual = datetime.strptime('2022' + '-' + '12' + '-' + '04', '%Y-%m-%d').date()
        fechaactual = datetime.now().date()
        totalnuevas = 0
        listado = []
        print(".:: Proceso de importación de publicaciones del sitio web SCOPUS ::.")

        # Proceso se debe ejecutar día DOMINGO
        if dia_semana_enletras_fecha(fechaactual).upper() == 'JUEVES':
            perfilesscopus = RedPersona.objects.filter(status=True, tipo__id=4, verificada=True).order_by('persona__apellido1', 'persona__apellido2', 'persona__nombres')

            c = 1
            total = len(perfilesscopus)
            for perfilscopus in perfilesscopus:
                identificador = perfilscopus.identificador
                print("Procesando", c, "de", total)
                print("Inicio Consulta publicaciones para SCOPUS ID:", identificador, "-", perfilscopus.persona.nombre_completo_inverso())

                # Consulto las publicaciones por medio del Scopus ID
                listaCitas = []
                registro = requests.get(f'https://api.elsevier.com/content/search/scopus?query=AU-ID("{identificador}")&apiKey=cfa6f5b37a0e8a3f6a30c190da693411', headers={'accept': 'application/json'})

                objeto = registro.json()

                totalregistros = int(objeto["search-results"]["opensearch:totalResults"])

                # Si existen publicaciones
                if totalregistros > 0:
                    t = 0
                    pnuevap = 0

                    # Obtengo las publicaciones
                    publicaciones = objeto["search-results"]["entry"]

                    # Recorro las publicaciones
                    for publicacion in publicaciones:
                        print(":: PUBLICACION ::")

                        p1 = publicacion["dc:identifier"].index(":")
                        idpublicacion = publicacion["dc:identifier"][p1+1:]
                        url = None

                        for enlace in publicacion["link"]:
                            if enlace["@ref"] == 'scopus':
                                url = enlace["@href"]
                                break

                        eid = publicacion["eid"]
                        titulo = publicacion["dc:title"]
                        autor = publicacion["dc:creator"]
                        titulofuente = publicacion["prism:publicationName"]
                        issn = publicacion["prism:issn"] if "prism:issn" in publicacion else None
                        eissn = publicacion["prism:eIssn"] if "prism:eIssn" in publicacion else None
                        isbn = publicacion["prism:isbn"][0]["$"] if "prism:isbn" in publicacion else None
                        volumen = publicacion["prism:volume"] if "prism:volume" in publicacion else None
                        pagina = publicacion["prism:pageRange"]
                        fechapublica = publicacion["prism:coverDate"]
                        fechaportada = publicacion["prism:coverDisplayDate"]
                        doi = publicacion["prism:doi"] if "prism:doi" in publicacion else None
                        ccita = publicacion["citedby-count"]
                        tipofuente = publicacion["prism:aggregationType"]
                        codigotipo = publicacion["subtype"]
                        descripciontipo = publicacion["subtypeDescription"]

                        print("Url:", url)
                        print("Scopus ID:", idpublicacion)
                        print("Electronic ID:", eid)
                        print("Article Title:", titulo)
                        print("First Author:", autor)
                        print("Source Title:", titulofuente)
                        print("** Source Identifier ISSN:", issn)
                        print("** Source Identifier eISSN: ", eissn)
                        print("** Source Identifier ISBN:", isbn)
                        print("** Volume:", volumen)
                        print("Page:", pagina)
                        print("Publication Date:", fechapublica)
                        print("Publication Date(original text):", fechaportada)
                        print("Document Object Identifier(DOI):", doi)
                        print("Cited-by Count:", ccita)
                        print("Source Type:", tipofuente)
                        print("Document Type code:", codigotipo)
                        print("Document Type description:", descripciontipo)

                        listaCitas.append(int(publicacion["citedby-count"]))

                        # Si no existe la publicación la creo sino edito
                        if not PublicacionScopus.objects.values("id").filter(status=True, perfilacademico=perfilscopus, codigo=idpublicacion).exists():
                            publicacionscopus = PublicacionScopus(
                                perfilacademico=perfilscopus,
                                codigo=idpublicacion,
                                url=url,
                                eid=eid,
                                titulo=titulo,
                                autor=autor,
                                titulofuente=titulofuente,
                                issn=issn,
                                eissn=eissn,
                                isbn=isbn,
                                volumen=volumen,
                                pagina=pagina,
                                fechapublica=fechapublica,
                                fechaportada=fechaportada,
                                doi=doi,
                                ccita=ccita,
                                tipofuente=tipofuente,
                                codigotipo=codigotipo,
                                descripciontipo=descripciontipo,
                                procesada=False
                            )
                            publicacionscopus.save()

                            print("Registro de publicación creado...")
                            pnuevap += 1
                            totalnuevas += 1
                        else:
                            publicacionscopus = PublicacionScopus.objects.get(status=True, perfilacademico=perfilscopus, codigo=idpublicacion)
                            publicacionscopus.codigo = idpublicacion
                            publicacionscopus.url = url
                            publicacionscopus.eid = eid
                            publicacionscopus.titulo = titulo
                            publicacionscopus.autor = autor
                            publicacionscopus.titulofuente = titulofuente
                            publicacionscopus.issn = issn
                            publicacionscopus.eissn = eissn
                            publicacionscopus.isbn = isbn
                            publicacionscopus.volumen = volumen
                            publicacionscopus.pagina = pagina
                            publicacionscopus.fechapublica = fechapublica
                            publicacionscopus.fechaportada = fechaportada
                            publicacionscopus.doi = doi
                            publicacionscopus.ccita = ccita
                            publicacionscopus.tipofuente = tipofuente
                            publicacionscopus.codigotipo = codigotipo
                            publicacionscopus.descripciontipo = descripciontipo
                            publicacionscopus.save()

                            print("Registro de publicación actualizado...")

                        print("")
                        t += 1

                    print("Total publicaciones procesadas:", t)

                    print(".:: Metrics overview ::.")
                    print("Total documentos:", len(listaCitas))
                    print("Total citaciones:", sum(listaCitas))
                    print("Índice H:", obtenerIndiceH(listaCitas))

                    # Actualizo el registro de perfil académico SCOPUS
                    perfilscopus.ndocumento = len(listaCitas)
                    perfilscopus.ncita = sum(listaCitas)
                    perfilscopus.indiceh = obtenerIndiceH(listaCitas)
                    perfilscopus.save()

                    # Si la persona tiene nuevas publicaciones la agrego a la lista para el envío de correo
                    # if pnuevap > 0:
                    #     listado.append(
                    #         {"identificacion": perfilscopus.persona.identificacion(),
                    #          "nombres": perfilscopus.persona.nombre_completo_inverso(),
                    #          "total": pnuevap}
                    #     )


                    print("Si tiene publicaciones")
                else:
                    print("No tiene publicaciones")

                print("Fin Consulta publicaciones para SCOPUS ID:", identificador)
                print("")
                print("================================")
                c += 1

            # Si se registraron nuevas publicaciones notificar por e-mail a la coordinación de investigación
            # if totalnuevas > 0:
            #     # Obtengo la(s) cuenta(s) de correo desde la cual(es) se envía el e-mail
            #     listacuentascorreo = [0, 8, 9, 10, 11, 12, 13]  # sga@unemi.edu.ec, sga2@unemi.edu.ec, ..., sga7@unemi.edu.ec
            #
            #     # Notificar por e-mail a la Coordinación de Investigación
            #     # lista_email_envio = ['investigacion.dip@unemi.edu.ec']
            #     lista_email_envio = ['isaltosm@unemi.edu.ec']
            #     lista_email_cco = ['ivan_saltos_medina@hotmail.com']
            #     lista_adjuntos = []
            #
            #     fechaenvio = datetime.now().date()
            #     horaenvio = datetime.now().time()
            #     cuenta = cuenta_email_disponible_para_envio(listacuentascorreo)
            #
            #     tituloemail = "Importación de Publicaciones del Sitio Web de SCOPUS"
            #     titulo = "Publicaciones Sitio Web SCOPUS"
            #     tiponotificacion = "REGCOORDINV"
            #
            #     send_html_mail(tituloemail,
            #                    "emails/publicacionscopus.html",
            #                    {'sistema': u'SGA - UNEMI',
            #                     'titulo': titulo,
            #                     'fecha': fechaenvio,
            #                     'hora': horaenvio,
            #                     'tiponotificacion': tiponotificacion,
            #                     'saludo': 'Estimados',
            #                     'totalnuevas': totalnuevas,
            #                     'listado': listado
            #                     },
            #                    lista_email_envio,
            #                    lista_email_cco,
            #                    lista_adjuntos,
            #                    cuenta=CUENTAS_CORREOS[cuenta][1]
            #                    )
            #     print("Correo enviado a la Coordinación de Investigación...")

            print("Proceso de importación de publicaciones del sitio web SCOPUS finalizado. . .")
        else:
            print("ATENCIÓN: El proceso únicamente se ejecuta días DOMINGO...")

    except Exception as ex:
        transaction.set_rollback(True)
        msg = ex.__str__()
        print("Error: ", msg)


def obtenerIndiceH(listaCitas):
    if not listaCitas:
        return 0
    listaCitas.sort()
    for i in range(1,len(listaCitas)+1)[::-1]:
        if listaCitas[-i] >= i:
            return i
    return 0


def notificar_ejecucion_script():
    # Obtengo la(s) cuenta(s) de correo desde la cual(es) se envía el e-mail
    listacuentascorreo = [0, 8, 9, 10, 11, 12, 13]  # sga@unemi.edu.ec, sga2@unemi.edu.ec, ..., sga7@unemi.edu.ec

    # Notificar por e-mail
    lista_email_envio = ['isaltosm@unemi.edu.ec']
    lista_email_cco = []
    lista_adjuntos = []

    fechaenvio = datetime.now().date()
    horaenvio = datetime.now().time()
    cuenta = cuenta_email_disponible_para_envio(listacuentascorreo)

    tituloemail = "Ejecución automática de Script Posgrado-Investigación en el servidor"
    titulo = "Ejecución Script Posgrado-Investigación"
    tiponotificacion = "ANLDES1"

    send_html_mail(tituloemail,
                   "emails/publicacionscopus.html",
                   {'sistema': u'SGA - UNEMI',
                    'titulo': titulo,
                    'fecha': fechaenvio,
                    'hora': horaenvio,
                    'tiponotificacion': tiponotificacion
                    },
                   lista_email_envio,
                   lista_email_cco,
                   lista_adjuntos,
                   cuenta=CUENTAS_CORREOS[cuenta][1]
                   )


@transaction.atomic()
def migrar_proyectos_investigacion_2020():
    try:
        # Consulto los proyectos de Investigación con estado en ejecución de la convocatoria 2020
        proyectos = ProyectoInvestigacion.objects.filter(status=True, estado__valor=20, convocatoria_id=1).order_by('id')
        total = proyectos.count()
        c = 0
        for proyecto in proyectos:
            # Si no existe lo creo
            if not ProyectosInvestigacion.objects.values("id").filter(pinvestigacion=proyecto, status=True).exists():
                c += 1
                print("Procesando", c, " de ", total)
                print(proyecto, proyecto.estado.descripcion)

                # Crea el proyecto en la tabla del módulo antiguo
                proyecto_antiguo = ProyectosInvestigacion(
                    convocatoria=None,
                    programa=proyecto.programainvestigacion,
                    nombre=proyecto.titulo,
                    tipo=2,
                    fechainicio=proyecto.fechainicio,
                    fechaplaneado=proyecto.fechainicio,
                    fechareal=proyecto.fechainicio,
                    alcanceterritorial=None,
                    areaconocimiento=proyecto.areaconocimiento,
                    subareaconocimiento=proyecto.subareaconocimiento,
                    subareaespecificaconocimiento=proyecto.subareaespecificaconocimiento,
                    tipoproinstitucion=None,
                    tiempoejecucion=proyecto.tiempomes,
                    lineainvestigacion=proyecto.lineainvestigacion,
                    sublineainvestigacion=proyecto.sublineainvestigacion.all()[0],
                    valorpresupuestointerno=proyecto.montounemi,
                    valorpresupuestoexterno=proyecto.montootrafuente,
                    circuito=None,
                    distrito=None,
                    institucionbeneficiaria='',
                    sectorcoordenada='',
                    periodoejecuciondesde=None,
                    periodoejecucionhasta=None,
                    periodoejecucion='',
                    objetivoplannacional=None,
                    observaa=None,
                    cupo=None,
                    saldoo=None,
                    horas=None,
                    aprobacion=1,
                    archivo=None, # Habrá que copiar el archivo después,
                    presupuestototal=proyecto.montototal,
                    fechaplaneacion=proyecto.fechafinplaneado,
                    fechafin=proyecto.fechafinreal,
                    objetivos_PND='',
                    politicas_PND='',
                    linea_accion='',
                    estrategia_desarrollo='',
                    investigacion_institucional='',
                    necesidades_sociales='',
                    tiempo_duracion_horas=0,
                    linea_base=True,
                    fecha_aprobacion=proyecto.fechaaprobacion,
                    fecha_entrega=proyecto.fecha_creacion,
                    migrado=True,
                    pinvestigacion=proyecto
                )
                proyecto_antiguo.save()

                # Copio el archivo del proyecto
                rutaarchivo = SITE_STORAGE + proyecto.archivodocumento.url
                if os.path.exists(rutaarchivo):
                    nombrearchivo = generar_nombre('documento', 'documento.pdf')
                    # Aperturo el archivo generado
                    with open(rutaarchivo, 'rb') as f:
                        data = f.read()

                    buffer = io.BytesIO()
                    buffer.write(data)
                    pdfcopia = buffer.getvalue()
                    buffer.seek(0)
                    buffer.close()

                    # Extraigo el contenido
                    archivocopiado = ContentFile(pdfcopia)
                    archivocopiado.name = nombrearchivo

                    proyecto_antiguo.archivo = archivocopiado
                    proyecto_antiguo.save()

                    print("Archivo copiado")
                else:
                    print("No existe el archivo")

                # Creo los integrantes
                for integrante in proyecto.integrantes_proyecto():
                    print(integrante)
                    # No debo agregar los externos
                    if not integrante.externo:
                        participante_proyecto_antiguo = ParticipantesMatrices(
                            matrizevidencia_id=2,
                            proyecto=proyecto_antiguo,
                            inscripcion=integrante.inscripcion,
                            profesor=integrante.profesor,
                            tipoparticipante_id=4 if integrante.funcion == 1 else 3,
                            administrativo=integrante.administrativo,
                            estado=0
                        )
                        participante_proyecto_antiguo.save()

                ET.sleep(3)

        print("Proyectos procesados:", c)
        print("Proceso de migración finalizado...")
    except Exception as ex:
        transaction.set_rollback(True)
        msg = ex.__str__()
        print("Error: ", msg)


@transaction.atomic()
def copiar_documentos_proyectos_firmados():
    try:
        # Consulto los proyectos de Investigación de la convocatoria 2022
        proyectos = ProyectoInvestigacion.objects.filter(status=True, convocatoria_id=3).order_by('id')
        copiados = 0

        for proyecto in proyectos:
            if proyecto.archivodocumentofirmado:
                print(".:: Procesando ::.")
                print(proyecto)

                # Copio el archivo del proyecto
                rutaarchivo = SITE_STORAGE + proyecto.archivodocumentofirmado.url
                if os.path.exists(rutaarchivo):
                    # Crea el historial del archivo
                    historialarchivo = ProyectoInvestigacionHistorialArchivo(
                        proyecto=proyecto,
                        tipo=11,
                        archivo=proyecto.archivodocumentofirmado
                    )
                    historialarchivo.save()
                    print("Archivo copiado")
                    copiados += 1

                    ET.sleep(3)
                else:
                    print("No existe el archivo")

        print("Total archivos copiados:", copiados)
        print("Proceso finalizado...")
    except Exception as ex:
        transaction.set_rollback(True)
        msg = ex.__str__()
        print("Error: ", msg)


def notificar_proyectos_cambios_menores_y_evaluacion_adicional():
    print(".:: Proceso de notificación Proyectos con Modificaciones menores y Evaluaciones adicionales ::.")

    # fechaactual = datetime.strptime('2022' + '-' + '11' + '-' + '23', '%Y-%m-%d').date()
    fechaactual = datetime.now().date()

    # Proceso se debe ejecutar día DOMINGO, LUNES
    if dia_semana_enletras_fecha(fechaactual).upper() in ['MIERCOLES', 'JUEVES']:
        proyectos = ProyectoInvestigacion.objects.filter(status=True, estado__valor__in=[9, 15]).order_by('id')
        total = proyectos.count()
        procesados = 0

        for proyecto in proyectos:
            procesados += 1
            print("Procesando", procesados, "de", total)
            print(proyecto)

            # Obtengo la(s) cuenta(s) de correo desde la cual(es) se envía el e-mail
            listacuentascorreo = [29]  # investigacion.dip@unemi.edu.ec

            # Destinatarios
            destinatario = proyecto.profesor.persona
            lista_email_envio = []
            lista_email_envio = destinatario.lista_emails_envio()
            # lista_email_envio = []
            # lista_email_envio.append('investigacion.dip@unemi.edu.ec')
            # lista_email_envio.append('ivan_saltos_medina@hotmail.com')
            lista_email_cco = ['isaltosm@unemi.edu.ec']
            # lista_email_cco = ['ivan_saltos_medina@hotmail.com']
            lista_archivos_adjuntos = []

            fechaenvio = datetime.now().date()
            horaenvio = datetime.now().time()
            cuenta = cuenta_email_disponible_para_envio(listacuentascorreo)

            # Evaluacion interna adicional
            if proyecto.estado.valor == 9:
                print("Evaluacion adicional")
                tiponotificacion = "EVALINTADI"
                tituloemail = "Propuesta de Proyecto de Investigación requiere Evaluación Interna Adicional"
            else:
                print("Modificaciones menores")
                tiponotificacion = "EVALINTMODMENOR"
                tituloemail = "Propuesta de Proyecto de Investigación requiere Modificaciones Menores"

            titulo = "Proyectos de Investigación"
            send_html_mail(tituloemail,
                           "emails/propuestaproyectoinvestigacion.html",
                           {'sistema': u'SGA - UNEMI',
                            'titulo': titulo,
                            'fecha': fechaenvio,
                            'hora': horaenvio,
                            'tiponotificacion': tiponotificacion,
                            'saludo': 'Estimada' if proyecto.profesor.persona.sexo_id == 1 else 'Estimado',
                            'nombrepersona': proyecto.profesor.persona.nombre_completo_inverso(),
                            'observaciones': '',
                            'proyecto': proyecto
                            },
                           lista_email_envio,  # Destinatarioa
                           lista_email_cco,  # Copia oculta, poner [] para que no me envíe jaja
                           lista_archivos_adjuntos,  # Adjunto(s)
                           cuenta=CUENTAS_CORREOS[cuenta][1]
                           )

        print("Proceso de notificación Proyectos de Investigación finalizado. . .")
    else:
        print("El proceso no está disponible para ejecución al día actual...")


def notificar_proyectos_evaluacion_externa_superada():
    print(".:: Proceso de notificación Proyectos Aceptados para ir a CGA - Evaluación Externa Superada ::.")

    # fechaactual = datetime.strptime('2022' + '-' + '11' + '-' + '23', '%Y-%m-%d').date()
    fechaactual = datetime.now().date()

    # Proceso se debe ejecutar el .....
    if dia_semana_enletras_fecha(fechaactual).upper() in ['MARTES', 'MIERCOLES', 'JUEVES']:
        proyectos = ProyectoInvestigacion.objects.filter(status=True, estado__valor=13).order_by('id')
        total = proyectos.count()
        procesados = 0

        for proyecto in proyectos:
            procesados += 1
            print("Procesando", procesados, "de", total)
            print(proyecto)

            # Obtengo la(s) cuenta(s) de correo desde la cual(es) se envía el e-mail
            listacuentascorreo = [29]  # investigacion.dip@unemi.edu.ec

            # Destinatarios
            destinatario = proyecto.profesor.persona
            lista_email_envio = []
            lista_email_envio = destinatario.lista_emails_envio()
            # lista_email_envio = []
            # lista_email_envio.append('investigacion.dip@unemi.edu.ec')
            # lista_email_envio.append('ivan_saltos_medina@hotmail.com')
            # lista_email_cco = ['isaltosm@unemi.edu.ec']
            lista_email_cco = ['ivan_saltos_medina@hotmail.com']
            lista_archivos_adjuntos = []

            # Buscar el recorrido con el estado ACEPTADO
            recorrido = proyecto.proyectoinvestigacionrecorrido_set.filter(status=True, estado__valor=13)[0]
            fechaenvio = recorrido.fecha_creacion.date()
            horaenvio = recorrido.fecha_creacion.time()

            # fechaenvio = datetime.now().date()
            # horaenvio = datetime.now().time()
            cuenta = cuenta_email_disponible_para_envio(listacuentascorreo)

            tiponotificacion = "EVALEXTSUP"
            tituloemail = "Evaluación Externa de Propuesta de Proyecto de Investigación Superada"

            titulo = "Proyectos de Investigación"
            send_html_mail(tituloemail,
                           "emails/propuestaproyectoinvestigacion.html",
                           {'sistema': u'SGA - UNEMI',
                            'titulo': titulo,
                            'fecha': fechaenvio,
                            'hora': horaenvio,
                            'tiponotificacion': tiponotificacion,
                            'saludo': 'Estimada' if proyecto.profesor.persona.sexo_id == 1 else 'Estimado',
                            'nombrepersona': proyecto.profesor.persona.nombre_completo_inverso(),
                            'observaciones': '',
                            'proyecto': proyecto
                            },
                           lista_email_envio,  # Destinatarioa
                           lista_email_cco,  # Copia oculta, poner [] para que no me envíe jaja
                           lista_archivos_adjuntos,  # Adjunto(s)
                           cuenta=CUENTAS_CORREOS[cuenta][1]
                           )

        print("Proceso de notificación Proyectos de Investigación finalizado. . .")
    else:
        print("El proceso no está disponible para ejecución al día actual...")


@transaction.atomic()
def eliminar_notificaciones_vencidas():
    print(".:: Proceso de eliminación de Notificaciones vencidas ::.")
    fechaactual = datetime.now().date()
    # Consultar las notificaciones vencidas
    c = 0
    notificaciones = Notificacion.objects.filter(status=True, fecha_hora_visible__lt=fechaactual).order_by('id')[:700000]
    total = notificaciones.count()
    for notificacion in notificaciones:
        c += 1
        print("Eliminando ", c, " de ", total, " registros")
        notificacion.status = False
        notificacion.save()

    print("Total registros eliminados: ", c)
    print("Proceso finalizado...")

@transaction.atomic()
def actualizar_numeros_objetivos_proyectos():
    proyectos = ProyectoInvestigacion.objects.filter(status=True).order_by('id')
    c = 1
    total = len(proyectos)

    for proyecto in proyectos:
        print("Procesando", c, " de ", total)
        print(proyecto.titulo)

        numero = 1
        for objetivo in proyecto.objetivos_especificos():
            print("Actualizando objetivo ", numero)
            objetivo.numero = numero
            objetivo.save()
            numero += 1

        c += 1

    print("Proceso de actualización finalizado. . .")


def correcion_comite_solicitud_ponencia():
    solicitudes = SolicitudPublicacion.objects.filter(status=True, tiposolicitud=2, registrado=False, aprobado=False, integrantecomite__isnull=False).exclude(integrantecomite='').exclude(integrantecomite__contains='[{')
    print(solicitudes.count())
    for solicitud in solicitudes:
        # print(solicitud.id)
        # print(solicitud.integrantecomite)
        linea = solicitud.integrantecomite.split("|")

        cadena = "UPDATE sagest_solicitudpublicacion SET integrantecomite='"
        valores = ""
        for dato in linea:
            reg = dato.split(",")
            if not valores:
                valores = "[{''nombre'': ''" + reg[0] + "'', ''institucion'': ''" + reg[1] + "'', ''email'': " + reg[2] + "''}"
            else:
                valores = valores + ", {''nombre'': ''" + reg[0] + "'', ''institucion'': ''" + reg[1] + "'', ''email'': " + reg[2] + "''}"

        valores = valores + "]"
        # print("valores -> ", valores)

        cadena = cadena + valores + "' where id=" + str(solicitud.id) + ";"
        print(cadena)


def ejecutar_procesos():
    ejecutar = True

    if ejecutar:
        # print("Desa/ctivado")
        # importar_publicaciones_orcid()
        # Importación de publicaciones sitio web de Scopus
        # importar_publicaciones_scopus()

        # Notificar completar información de propuestas de proyectos de investigación
        # notificar_completar_proyectos()

        # Notificar confirmar postulacion obras de relevancia
        # notificar_confirmar_postulacion_obra_relevancia()

        # Migrar proyectos de investigación 2020 en ejecucion
        # migrar_proyectos_investigacion_2020()

        # notificar_proyectos_cambios_menores_y_evaluacion_adicional()
        # notificar_proyectos_evaluacion_externa_superada()
        # Cambiar el estado de los proyectos a EJECUCIÓN
        # actualizar_estado_proyecto()
        eliminar_notificaciones_vencidas()
        # actualizar_numeros_objetivos_proyectos()
        # importar_publicaciones_scopus()
    else:
        print("ATENCIÓN: No hay procesos por ejecutar.......")

    # Notificar ejecución del script en el cron
    notificar_ejecucion_script()


# actualizar_estado_proyecto()
# notificar_semana_vencimiento_evidencias()
# actualizar_estado_actividad_proyecto()
# rechazar_solicitudes_becas_sin_evidencias()
# rechazar_solicitudes_becas_situacion_economica()
# llenar_historial_archivo()
# crear_evaluaciones()

# reporte_detalle_mensual()
# reporte_vencimientos_mensuales()
# reporte_pagos_mensuales()
# reporte_resumenmensual()
# reporte_edad_cartera_vencida()
# reporte_proyeccion_cobros_posgrado()
# reporte_indice_cartera_vencida()

# reporte_indice_cartera_vencida_segun_auditor1()
# reporte_indice_cartera_vencida_imsm()

# generar_financiamiento_posgrado_con_cuota_adicional()

# eliminar_matriculas_posgrado_18_educacion_inicial_2c()
# eliminar_matriculas_posgrado_15()

# eliminar_matriculas_posgrado_1_sistemainformacion()

# eliminar_matriculas_17032022_1()
# notificar_completar_proyectos()
# generar_numero_orden_detalle_evaluacion()
# inactivar_rubros_pendientes_aspirantes_posgrado()
# verificar_psicologia()

# prueba_vencidos()

# prueba_vencidos_pagos()
# prueba_vencidos_pagos_2()

# simular_pago_posgrado()
# test_moodle()

# generar_listado_matriculados_rubros()
# generar_listado_matriculados_posgrado()

# generar_listado_rubros_pagos()

# generar_financiamiento_posgrado_pestania_data()
# bloquear_rubros_proceso_coactiva()
# crear_grupos_investigacion()
# prueba_vencidos_categoria()
# asignar_grupo()
# rubros_vencidos()
# reporte_pagos_unemi_resumen()

# importar_publicaciones_orcid()


# def consultar_distributivo_investigacion():
#     print("============================")
#     periodo = Periodo.objects.get(pk=153)
#     profesor = Persona.objects.get(cedula='0917189664').profesor()
#
#     print(periodo)
#     print(profesor.persona.nombre_completo_inverso())
#
#     distributivo = profesor.profesordistributivohoras_set.filter(status=True, periodo=periodo)[0]
#
#     # Verifico si tiene distributivo en el periodo
#     if distributivo:
#         print("SI TIENE DISTRIBUTIVO")
#
#         print("TOTAL HORAS INVESTIGACIÓN:", distributivo.horasinvestigacion)
#
#         detalleinvestigacion = distributivo.detalledistributivo_set.filter(status=True, criterioinvestigacionperiodo__isnull=False)
#
#         # Si tiene investigación
#         if detalleinvestigacion:
#             print("SI TIENE DETALLE EN EL DISTRIBUTIVO DE INVESTIGACIÓN")
#             print()
#
#             # Mostrar actividades
#             for actividad in detalleinvestigacion:
#                 print("---ACTIVIDAD: ", actividad.criterioinvestigacionperiodo.criterio.nombre)
#                 print("---HORAS ASIGNADAS: ", actividad.horas)
#                 print("---[ SUB ACTIVIDADES ]")
#
#                 # Mostrar Subactividades
#                 for subactividad in actividad.actividaddetalledistributivo_set.filter(status=True):
#                     print("------SUB ACTIVIDAD: ", subactividad.nombre)
#                     print("------INICIO: ", subactividad.desde)
#                     print("------FIN: ", subactividad.hasta)
#                     print("------HORAS: ", subactividad.horas)
#                     print("------VIGENTE: ", subactividad.vigente)
#
#         else:
#             print("NO TIENE DETALLE EN EL DISTRIBUTIVO DE INVESTIGACIÓN")
#
#     else:
#         print("NO TIENE DISTRIBUTIVO")

    # print("Consulta periodo vigente. BASADO EN EL CÓDIGO DEL commonviews.py")
    # # fechaactual = datetime.strptime('2023' + '-' + '04' + '-' + '13', '%Y-%m-%d').date()
    # fechaactual = datetime.now().date()
    #
    # # Consulto los id de periodos donde tiene distributivo el docente
    # periodosid = ProfesorDistributivoHoras.objects.values_list('periodo__id').filter(profesor=profesor, periodo__visible=True, periodo__status=True)
    # if periodosid:
    #     # Consulto los periodos
    #     periodosdocente = Periodo.objects.select_related('tipo').filter(id__in=periodosid).order_by('-inicio')
    #
    #     # Consulto el periodo vigente
    #     periodovigente = periodosdocente.filter(inicio__lte=fechaactual, fin__gte=fechaactual).order_by('-marcardefecto')[0] if periodosdocente.filter(inicio__lte=fechaactual, fin__gte=fechaactual).exists() else None
    #     print("Periodo vigente es:", periodovigente)
    #
    # else:
    #     print("No tiene registros de distributivo")

# def prueba_usuario_grupo():
#     persona = Persona.objects.filter(cedula='0101827806')[0]
#     print(persona)
#
#     usuario = persona.usuario
#
#     print(usuario)
#
#     from django.contrib.auth.models import Group
#     grupo = Group.objects.get(pk=335)
#     print(grupo)
#
#     # if not usuario.groups().filter(group=grupo):
#     #     print("No tiene grupo externo")
#     # else:
#     #     print("Si tiene grupo externo")
#
#     for g in usuario.groups.all():
#         print(g.id, g.name)
#
#     for g in usuario.groups.filter(id=335):
#         print(g.id, g.name)
#
#     if usuario.groups.filter(id=335):
#         print("SI TIENE ASIGNADO GRUPO INVESTIGACION EXTERNO 335")
#     else:
#         print("NO TIENE ASIGNADO GRUPO INVESTIGACION EXTERNO 335")
#
#         # esto agrega el grupo a l usuario
#         grupo.user_set.add(usuario)
#         grupo.save()

# consultar_distributivo_investigacion()

def consultar_scopus():
    import requests
    import json

    identificador = '57210847155'

    # Consulto por medio de la Api pública las publicaciones
    # registro = requests.get(f'https://api.elsevier.com/content/search/scopus?query=AU-ID("{identificador}")&apiKey=cfa6f5b37a0e8a3f6a30c190da693411', headers={'accept': 'application/json'})
    registro = requests.get(f'https://api.elsevier.com/content/author/author_id/{identificador}?apiKey=cfa6f5b37a0e8a3f6a30c190da693411', headers={'accept': 'application/json'})
    objeto = registro.json()

    if "author-retrieval-response" in objeto:
        print("si existe")

        print(".:: PERFIL SCOPUS ::.")

        print("prism:url -> ", objeto["author-retrieval-response"][0]["coredata"]["prism:url"])
        print("dc:identifier -> ", objeto["author-retrieval-response"][0]["coredata"]["dc:identifier"])
        print("document-count -> ", objeto["author-retrieval-response"][0]["coredata"]["document-count"])

        print("link")
        for link in objeto["author-retrieval-response"][0]["coredata"]["link"]:
            print(link["@href"], " - ", link["@rel"])

        print("Perfil")

        print("initials: ", objeto["author-retrieval-response"][0]["author-profile"]["preferred-name"]["initials"])
        print("indexed-name: ", objeto["author-retrieval-response"][0]["author-profile"]["preferred-name"]["indexed-name"])
        print("surname: ", objeto["author-retrieval-response"][0]["author-profile"]["preferred-name"]["surname"])
        print("given-name: ", objeto["author-retrieval-response"][0]["author-profile"]["preferred-name"]["given-name"])

        print(".:: CONSULTA DE PUBLICACIÓN POR ISSN ::.")
        issn = "09505849"
        publicacionISSN = requests.get(f'https://api.elsevier.com/content/serial/title?issn={issn}&apiKey=cfa6f5b37a0e8a3f6a30c190da693411', headers={'accept': 'application/json'})
        objetoPub = publicacionISSN.json()

        if not "error" in objetoPub["serial-metadata-response"]:
            print("Si existe la publicación")

            print("dc:title -> ", objetoPub["serial-metadata-response"]["entry"][0]["dc:title"])

        else:
            print("No existe la publicación")

        registro = requests.get(f'https://api.elsevier.com/content/search/scopus?query=AU-ID("{identificador}")&apiKey=cda54272672f749f4fb2bc2deec74c1e', headers={'accept': 'application/json'})

        print(registro)
        objeto = registro.json()

        totalregistros = int(objeto["search-results"]["opensearch:totalResults"])

        print(totalregistros)

        if totalregistros > 0:
            # Obtengo las publicaciones
            publicaciones = objeto["search-results"]["entry"]

            # Recorro las publicaciones
            for publicacion in publicaciones:
                print(":: PUBLICACION ::")

                p1 = publicacion["dc:identifier"].index(":")
                idpublicacion = publicacion["dc:identifier"][p1 + 1:]
                url = None

                for enlace in publicacion["link"]:
                    if enlace["@ref"] == 'scopus':
                        url = enlace["@href"]
                        break

                eid = publicacion["eid"]
                titulo = publicacion["dc:title"]
                autor = publicacion["dc:creator"]
                titulofuente = publicacion["prism:publicationName"]
                issn = publicacion["prism:issn"] if "prism:issn" in publicacion else None
                eissn = publicacion["prism:eIssn"] if "prism:eIssn" in publicacion else None
                isbn = publicacion["prism:isbn"][0]["$"] if "prism:isbn" in publicacion else None
                volumen = publicacion["prism:volume"] if "prism:volume" in publicacion else None
                pagina = publicacion["prism:pageRange"]
                fechapublica = publicacion["prism:coverDate"]
                fechaportada = publicacion["prism:coverDisplayDate"]
                doi = publicacion["prism:doi"] if "prism:doi" in publicacion else None
                ccita = publicacion["citedby-count"]
                tipofuente = publicacion["prism:aggregationType"]
                codigotipo = publicacion["subtype"]
                descripciontipo = publicacion["subtypeDescription"]
                autores = publicacion["author"]

                print("Url:", url)
                print("Scopus ID:", idpublicacion)
                print("Electronic ID:", eid)
                print("Article Title:", titulo)
                print("First Author:", autor)
                print("Source Title:", titulofuente)
                print("** Source Identifier ISSN:", issn)
                print("** Source Identifier eISSN: ", eissn)
                print("** Source Identifier ISBN:", isbn)
                print("** Volume:", volumen)
                print("Page:", pagina)
                print("Publication Date:", fechapublica)
                print("Publication Date(original text):", fechaportada)
                print("Document Object Identifier(DOI):", doi)
                print("Cited-by Count:", ccita)
                print("Source Type:", tipofuente)
                print("Document Type code:", codigotipo)
                print("Document Type description:", descripciontipo)
                print("Autores:", autores)

    else:
        print("no existe")

@transaction.atomic()
def crear_horarios_servicios_investigacion():
    try:
        output_folder = os.path.join(os.path.join(SITE_STORAGE, 'media', 'archivos_temporales'))
        liborigen = xlrd.open_workbook(output_folder + '/GestionesServiciosResponsables.xls')

        sheet = liborigen.sheet_by_index(2)

        diasferiados = [
            datetime.strptime("2024-05-03", '%Y-%m-%d').date(),
            datetime.strptime("2024-05-24", '%Y-%m-%d').date(),
            datetime.strptime("2024-08-09", '%Y-%m-%d').date(),
            datetime.strptime("2024-11-01", '%Y-%m-%d').date(),
            datetime.strptime("2024-12-25", '%Y-%m-%d').date()
                        ]

        for fila in range(sheet.nrows):
            if fila >= 1:
                cols = sheet.row_values(fila)
                servicios = cols[0].strip()
                desservicio = cols[1].strip()
                idpersona = cols[2].strip()
                responsable = cols[4].strip() + " " + cols[5].strip() + " " + cols[6].strip()
                desde = datetime.strptime(cols[7].strip(), '%Y-%m-%d').date()
                hasta = datetime.strptime(cols[8].strip(), '%Y-%m-%d').date()
                dialunes = cols[9].strip()
                turnoslunes = cols[10].strip()
                diamartes = cols[11].strip()
                turnosmartes = cols[12].strip()
                diamiercoles = cols[13].strip()
                turnosmiercoles = cols[14].strip()
                diajueves = cols[15].strip()
                turnosjueves = cols[16].strip()
                diaviernes = cols[17].strip()
                turnosviernes = cols[18].strip()
                diasabado = cols[19].strip()
                turnossabado = cols[20].strip()
                diadomingo = cols[21].strip()
                turnosdomingo = cols[22].strip()
                idbloque = cols[23].strip()
                idubicacion = cols[24].strip()
                oficina = cols[25].strip()
                piso = cols[26].strip()
                visible = cols[27].strip()

                print("Procesando......")
                print("Servicio: ", desservicio, "Responsable: ", responsable)
                print("Desde: ", desde, " Hasta: ", hasta)

                # Guardar en tabla
                responsableservicio = ResponsableServicio(
                    responsable_id=idpersona,
                    ubicacion_id=idubicacion,
                    bloque_id=idbloque,
                    oficina=oficina,
                    piso=piso,
                    desde=desde,
                    hasta=hasta,
                    lunes=dialunes == 'S',
                    martes=diamartes == 'S',
                    miercoles=diamiercoles == 'S',
                    jueves=diajueves == 'S',
                    viernes=diaviernes == 'S',
                    sabado=diasabado == 'S',
                    domingo=diadomingo == 'S',
                    observacion='REGISTRADO MEDIANTE PROCESO MASIVO'
                )
                responsableservicio.save()

                # Guardar los servicios del responsable
                for idservicio in servicios.split(","):
                    servicio = ServicioGestion.objects.get(pk=idservicio)
                    servicioresponsable = ServicioResponsableServicio(
                        responsableservicio=responsableservicio,
                        servicio=servicio,
                        vigente=True,
                        visiblesolicitante=visible == 'S'
                    )
                    servicioresponsable.save()

                # Crear los horarios con las fechas que estén dentro del rango
                fecha = desde
                while fecha <= hasta:
                    print(fecha)
                    diasemana = fecha.weekday() + 1
                    turnos = ""

                    if dialunes == 'S' and diasemana == 1:
                        observacion = "DÍA FERIADO" if fecha in diasferiados else ""
                        habilitado = not fecha in diasferiados
                        turnos = turnoslunes

                        print(observacion)
                        print(habilitado)
                    elif diamartes == 'S' and diasemana == 2:
                        observacion = "DÍA FERIADO" if fecha in diasferiados else ""
                        habilitado = not fecha in diasferiados
                        turnos = turnosmartes

                        print(observacion)
                        print(habilitado)
                    elif diamiercoles == 'S' and diasemana == 3:
                        observacion = "DÍA FERIADO" if fecha in diasferiados else ""
                        habilitado = not fecha in diasferiados
                        turnos = turnosmiercoles

                        print(observacion)
                        print(habilitado)
                    elif diajueves == 'S' and diasemana == 4:
                        observacion = "DÍA FERIADO" if fecha in diasferiados else ""
                        habilitado = not fecha in diasferiados
                        turnos = turnosjueves

                        print(observacion)
                        print(habilitado)
                    elif diaviernes == 'S' and diasemana == 5:
                        observacion = "DÍA FERIADO" if fecha in diasferiados else ""
                        habilitado = not fecha in diasferiados
                        turnos = turnosviernes

                        print(observacion)
                        print(habilitado)
                    elif diasabado == 'S' and diasemana == 6:
                        observacion = "DÍA FERIADO" if fecha in diasferiados else ""
                        habilitado = not fecha in diasferiados
                        turnos = turnossabado

                        print(observacion)
                        print(habilitado)
                    elif diadomingo == 'S' and diasemana == 7:
                        observacion = "DÍA FERIADO" if fecha in diasferiados else ""
                        habilitado = not fecha in diasferiados
                        turnos = turnosdomingo

                        print(observacion)
                        print(habilitado)

                    # Guardo el horario
                    if turnos:
                        for idturno in turnos.split(","):
                            turno = TurnoCita.objects.get(pk=idturno)
                            horarioresponsable = HorarioResponsableServicio(
                                responsableservicio=responsableservicio,
                                turno=turno,
                                dia=diasemana,
                                fecha=fecha,
                                comienza=turno.comienza,
                                termina=turno.termina,
                                ocupado=False,
                                habilitado=habilitado,
                                observacion=observacion
                            )
                            horarioresponsable.save()

                    print("Horario creado...")

                    fecha = fecha + timedelta(days=1)

        print("Proceso finalizado. . .")
    except Exception as ex:
        transaction.set_rollback(True)
        msg = ex.__str__()
        print("Error: ", msg)


def generar_reporte_encuesta():
    try:
        from dateutil import relativedelta
        fuentecabecera = easyxf(
            'font: name Verdana, color-index black, bold on, height 150; pattern: pattern solid, fore_colour gray25; alignment: vert distributed, horiz centre; borders: left thin, right thin, top thin, bottom thin')
        fuentenormal = easyxf(
            'font: name Verdana, color-index black, height 150; borders: left thin, right thin, top thin, bottom thin')
        fuentenormalwrap = easyxf(
            'font: name Verdana, color-index black, height 150; borders: left thin, right thin, top thin, bottom thin')
        fuentenormalneg = easyxf(
            'font: name Verdana, color-index black, bold on , height 150; borders: left thin, right thin, top thin, bottom thin')
        fuentenormalnegrell = easyxf(
            'font: name Verdana, color-index black, bold on , height 150; borders: left thin, right thin, top thin, bottom thin; pattern: pattern solid, fore_colour gray25')
        fuentenormalwrap.alignment.wrap = True
        fuentenormalcent = easyxf(
            'font: name Verdana, color-index black, height 150; borders: left thin, right thin, top thin, bottom thin; alignment: horiz centre')
        fuentemoneda = easyxf(
            'font: name Verdana, color-index black, height 150; borders: left thin, right thin, top thin, bottom thin; alignment: horiz right',
            num_format_str=' "$" #,##0.00')
        fuentemonedaneg = easyxf(
            'font: name Verdana, color-index black, bold on, height 150; borders: left thin, right thin, top thin, bottom thin; alignment: horiz right; pattern: pattern solid, fore_colour gray25',
            num_format_str=' "$" #,##0.00')
        fuentefecha = easyxf(
            'font: name Verdana, color-index black, height 150; borders: left thin, right thin, top thin, bottom thin; alignment: horiz center',
            num_format_str='yyyy-mm-dd')
        fuentenumerodecimal = easyxf(
            'font: name Verdana, color-index black, height 150; borders: left thin, right thin, top thin, bottom thin; alignment: horiz right',
            num_format_str='#,##0.00')
        fuentenumeroentero = easyxf(
            'font: name Verdana, color-index black, height 150; borders: left thin, right thin, top thin, bottom thin; alignment: horiz right')

        output_folder = os.path.join(os.path.join(SITE_STORAGE, 'media', 'archivos_temporales'))
        liborigen = xlrd.open_workbook(output_folder + '/ADMINISTRATIVOS.xls')

        libdestino = xlwt.Workbook()
        hojadestino = libdestino.add_sheet("Listado")

        fil = 0
        filadest = 1

        columnas = [
            (u"N°", 1000),
            (u"Tipo Universidad", 3500),
            (u"Género", 3500),
            (u"Posición", 3500),
            (u"Antiguedad", 3500),
        ]

        for col_num in range(len(columnas)):
            hojadestino.write(fil, col_num, columnas[col_num][0], fuentecabecera)
            hojadestino.col(col_num).width = columnas[col_num][1]

        sheet = liborigen.sheet_by_index(0)
        cont = 0

        texto_preguntas = ["Muy Bajo", "Bajo", "Moderado", "Alto", "Muy Alto"] # 1-2-4-5-6-9-12-13-14-16-17-18
        text_preguntas_2 = ["Comunicación efectiva", "Trabajo en equipo", "Liderazgo", "Resolución de conflictos"] # 3
        texto_preguntas_3 = ["Satisfacción laboral", "Compromiso organizacional", "Relaciones interpersonales", "Comunicación interna"] # 7
        texto_preguntas_4 = ["Muy Insatisfecho", "Insatisfecho", "Neutral", "Satisfecho", "Muy Satisfecho"] # 8,10
        texto_preguntas_5 = ["Comunicación efectiva", "Empatía", "Trabajo en equipo", "Liderazgo inspirador", "Gestión de conflictos", "Adaptabilidad", "Resolución de problemas"] # 11


        for fila in range(sheet.nrows):
            if fila == 0:
                cols = sheet.row_values(fila)
                col_num += 1
                for c in range(9, 27):
                    hojadestino.write(fila, col_num, cols[c].strip(), fuentecabecera)
                    col_num += 1
            else:
                cont += 1
                cols = sheet.row_values(fila)
                cedula = cols[2].strip()

                persona = Persona.objects.get(cedula=cedula, status=True)
                ingresopersona = persona.ingresopersonal_set.filter(status=True)[0]
                print(ingresopersona.fechaingreso)
                anios = relativedelta.relativedelta(datetime.now().date(), ingresopersona.fechaingreso).years

                print(persona.apellido1, cont)

                if anios < 1:
                    valor = "<1 año"
                elif anios <= 3:
                    valor = "1-3 años"
                elif anios <= 6:
                    valor = "4-6 años"
                elif anios <= 9:
                    valor = "7-9 años"
                else:
                    valor = "+ años"

                hojadestino.write(filadest, 0, cont, fuentenormal)
                hojadestino.write(filadest, 1, "PÚBLICA", fuentenormal)
                hojadestino.write(filadest, 2, persona.sexo.nombre, fuentenormal)
                hojadestino.write(filadest, 3, "DOCENTE", fuentenormal)
                hojadestino.write(filadest, 4, valor, fuentenormal)

                cols = sheet.row_values(fila)
                col_num = 5
                for c in range(9, 27):
                    preg = sheet.row_values(0)
                    pregunta = int(preg[c].split(")")[0])
                    resptexto = ""
                    respnumero = 0
                    if type(cols[c]) == str:
                        resptexto = cols[c].strip()
                    else:
                        respnumero = int(cols[c])

                    if pregunta in [1, 2, 4, 5, 6, 9, 12, 13, 14, 16, 17, 18]:
                        respuesta = texto_preguntas[respnumero-1]
                    elif pregunta == 3:
                        respuesta = text_preguntas_2[respnumero-1]
                    elif pregunta == 7:
                        respuesta = texto_preguntas_3[respnumero-1]
                    elif pregunta in [8, 10]:
                        respuesta = texto_preguntas_4[respnumero-1]
                    elif pregunta == 11:
                        respuesta = texto_preguntas_5[respnumero-1]
                    else:
                        respuesta = resptexto

                    hojadestino.write(filadest, col_num, respuesta, fuentenormal)
                    col_num += 1

                filadest += 1

        libdestino.save(output_folder + "/PROCESADOS_ADMINISTRATIVOS.xls")
        print("Proceso finalizado...")
    except Exception as ex:
        msg = ex.__str__()
        print("Error: ", msg)

ejecutar_procesos()
# consultar_scopus()

# crear_horarios_servicios_investigacion()
# generar_reporte_encuesta()

# periodos = Periodo.objects.annotate(duracion_meses=ExpressionWrapper(datetime.now().date() - F('inicio'), output_field=DurationField())). \
#                             filter(duracion_meses__lte=timedelta(days=365), status=True, tipo_id=2, visible=True).\
#                             exclude(Q(nombre__contains='REMEDIAL') | Q(nombre__contains='PLANIFIC')).order_by('-id')
# for periodo in periodos:
#     print(periodo.id, periodo.nombre)

