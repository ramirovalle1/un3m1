# -*- coding: latin-1 -*-
import io
import json
import time
import redis as Redis
from datetime import datetime, timedelta, date
from django.contrib.auth.decorators import login_required
from django.contrib.contenttypes.models import ContentType
from django.core.cache import cache
from django.core.exceptions import ObjectDoesNotExist
from django.core.paginator import Paginator
from django.db import transaction, connections
from decimal import Decimal
import xlwt
from django.db.models import Q, Max
from django.http import HttpResponse, HttpResponseRedirect, JsonResponse
from django.shortcuts import render
from django.utils.crypto import get_random_string

from decorators import inhouse_check, secure_module, last_access, get_client_ip, f_tiene_solicitud_apertura_clase
from inno.pro_aperturaclase import extraer_dias
from settings import DATOS_ESTRICTO, ARCHIVO_TIPO_DEBERES, FICHA_MEDICA_ESTRICTA, \
    NOTIFICACION_DEBERES, CLASES_HORARIO_ESTRICTO, PAGO_OBLIGATORIO_PRIMERACUOTA, VER_FOTO_LECCION, PAGO_ESTRICTO, \
    USA_PLANIFICACION, CLASES_APERTURA_ANTES, CLASES_APERTURA_DESPUES, ASISTENCIA_EN_GRUPO, VALIDATE_IPS, REDIS_HOST, \
    REDIS_PASSWORD, REDIS_PORT, REDIS_BD, DEBUG
from sga.clases_threading import ActualizaAsistencia
from sga.commonviews import adduserdata, actualizar_contenido, actualizar_asistencia
from sga.forms import ArchivoDeberForm, ContenidoAcademicoForm
from sga.funciones import generar_nombre, convertir_fecha, log, variable_valor, dia_semana_ennumero_fecha, \
    null_to_numeric, puede_realizar_accion
from sga.models import Clase, Leccion, AsistenciaLeccion, EvaluacionLeccion, Turno, Aula, LeccionGrupo, Materia, \
    TipoIncidencia, Incidencia, Archivo, miinstitucion, SolicitudAperturaClase, ProfesorReemplazo, RegistraLeccion, \
    TemaAsistencia, SubTemaAsistencia, CUENTAS_CORREOS, SubTemaAdicionalAsistencia, ProfesorMateria, \
    PlanificacionClaseSilabo, DiasNoLaborable, Carrera, Coordinacion, MateriaAsignada, Notificacion, \
    PracticaPreProfesional, ParticipantePracticaPreProfesional, DetalleSilaboSemanalTema, DetalleSilaboSemanalSubtema, \
    SubtemaUnidadResultadoProgramaAnalitico, ClaseAsincronica, ClaseSincronica, SolicitudJustificacionAsistencia, \
    Modalidad, SilaboSemanal
from inno.models import PeriodoAcademia, AsistenciaLeccionObservacion
from sga.tasks import send_html_mail, conectar_cuenta
from sga.templatetags.sga_extras import encrypt
from django.template.context import Context
from django.template.loader import get_template
from sga.funcionesxhtml2pdf import download_html_to_pdf


def daterange(start_date, end_date):
    for n in range(int((end_date - start_date).days)):
        yield start_date + timedelta(n)


@login_required(redirect_field_name='ret', login_url='/loginsga')
@secure_module
@last_access
# @transaction.atomic()
def view(request):
    data = {}
    adduserdata(request, data)
    estareemplazo = False
    periodo = request.session['periodo']
    capippriva = request.session['capippriva'] if 'capippriva' in request.session else ''
    calcula_procentaje_apertura = variable_valor('ACTUALIZA_ASISTENCIA_APERTURA')
    persona = request.session['persona']
    if 'reemplazo' not in request.POST:
        perfilprincipal = request.session['perfilprincipal']
    else:
        hoy = datetime.now().date()
        if 'apertura' not in request.POST:
            reemplazo = ProfesorReemplazo.objects.get(desde__lte=hoy, hasta__gte=hoy, reemplaza__persona=request.session['persona'])
        else:
            reemplazo = ProfesorReemplazo.objects.filter(desde__lte=hoy, reemplaza__persona=request.session['persona'])[0]
        idreemplazo = reemplazo.reemplaza
        perfiles = reemplazo.reemplaza.persona.mis_perfilesusuarios_app('sga')
        perfilprincipal = reemplazo.reemplaza.persona.perfilusuario_principal(perfiles, 'sga')
        estareemplazo = True
    if not perfilprincipal.es_profesor():
        return HttpResponseRedirect("/?info=Solo los perfiles de profesores pueden ingresar al modulo.")
    profesor = perfilprincipal.profesor
    tiene_solicitud_apertura_clase = f_tiene_solicitud_apertura_clase(profesor, periodo)
    ePeriodoAcademia = periodo.get_periodoacademia()

    if request.method == 'POST':
        if 'action' in request.POST:
            action = request.POST['action']

            if action == 'nuevaleccion':
                with transaction.atomic():
                    try:
                        # redis = None
                        solicitada = False
                        lecciongrupo = None
                        # if ePeriodoAcademia:
                        #     if ePeriodoAcademia.utiliza_asistencia_redis:
                        #         redis = Redis.StrictRedis(host=REDIS_HOST, password=REDIS_PASSWORD, port=REDIS_PORT, db=REDIS_BD)

                        fecha = datetime.now().date()
                        if LeccionGrupo.objects.values('id').filter(status=True, profesor=profesor, abierta=True).exists() and not 'cerrada' in request.POST:
                            return JsonResponse({"result": "bad", "mensaje": u"Existe una clase abierta, verificar en el módulo Mis Horarios -> botón Continuar y proceda a cerrar la clase."})
                        if 'solicitud' in request.POST:
                            solicitud = SolicitudAperturaClase.objects.get(pk=request.POST['solicitud'])
                            solicitada = True
                            solicitud.aperturada = True
                            solicitud.save(request, update_fields=['aperturada'])
                            try:
                                notificaciones = Notificacion.objects.filter(destinatario=persona, content_type=ContentType.objects.get_for_model(solicitud),object_id=solicitud.id)
                                if notificaciones.values("id").exists():
                                    notificaciones.update(leido=True, fecha_hora_leido=datetime.now(), usuario_modificacion_id=persona.usuario.id)
                            except Exception:
                                pass
                            fecha = solicitud.fecha
                            clases = Clase.objects.filter(materia=solicitud.materia, turno=solicitud.turno, dia=solicitud.fecha.isoweekday(), activo=True, inicio__lte=fecha, fin__gte=fecha, profesor=profesor)

                            # SE VERIFICA SI YA TIENE UNA CLASE REGISTRADA EN EL MISMO TURNO
                            grupoleccion = LeccionGrupo.objects.filter(profesor=profesor, turno=solicitud.turno, fecha=solicitud.fecha)
                            if grupoleccion.values('id').filter(status=False).exists():
                                lecciongrupo = grupoleccion[0]
                                lecciongrupo.abierta = True
                                lecciongrupo.status = True
                                lecciongrupo.usuario_creacion_id = persona.usuario.id
                                lecciongrupo.horaentrada = solicitud.turno.comienza
                                lecciongrupo.save(request, update_fields=['abierta', 'status', 'usuario_creacion_id', 'horaentrada'])
                                client_address = get_client_ip(request)
                                log(u'Se abrio grupo leccion para la toma de asistencia: %s - ip: %s' % (lecciongrupo, client_address), request, "edit")
                                for leccion in lecciongrupo.mis_leciones().filter(clase__id__in=clases.values_list('id')):
                                    leccion.status = True
                                    leccion.abierta = True
                                    leccion.horaentrada = lecciongrupo.horaentrada
                                    leccion.usuario_creacion_id = persona.usuario.id
                                    leccion.save(request, update_fields=['status', 'abierta', 'horaentrada', 'usuario_creacion_id'])
                                    leccion.asistencialeccion_set.all().update(status=True, usuario_creacion_id=persona.usuario.id)
                            elif grupoleccion.values('id').filter(status=True).exists():
                                if grupoleccion[0].mis_leciones().values('id').filter(clase__id__in=clases.values_list('id')).exists():
                                    return JsonResponse({"result": "bad", "mensaje": u"Ya existe una clase registrada para esa fecha en ese turno."})
                                elif grupoleccion[0].verificar_profemate_novalidahor(clases):
                                    lecciongrupo = grupoleccion[0]
                                    lecciongrupo.abierta = True
                                    lecciongrupo.status = True
                                    lecciongrupo.horaentrada = solicitud.turno.comienza
                                    lecciongrupo.usuario_creacion_id = persona.usuario.id
                                    lecciongrupo.save(request, update_fields=['abierta', 'status', 'horaentrada', 'usuario_creacion_id'])
                                    client_address = get_client_ip(request)
                                    log(u'Se abrio grupo leccion para la toma de asistencia: %s - ip: %s' % (lecciongrupo, client_address), request, "edit")
                        else:
                            clases = Clase.objects.filter(id__in=[int(x) for x in request.POST['clases'].split(',')])
                        if clases.values("id").exists():
                            aula = clases[0].aula
                            if ePeriodoAcademia.valida_asistencia_in_home and not tiene_solicitud_apertura_clase:
                                if aula and aula.bloque and aula.bloque.in_home:
                                    if not inhouse_check(request):
                                        transaction.set_rollback(True)
                                        return JsonResponse({"result": "bad", "mensaje": u"La clase no puede ser abierta fuera de UNEMI"})

                        isCerrada = False
                        if 'cerrada' in request.POST:
                            isCerrada = int(request.POST['cerrada']) == 1

                        turno = Turno.objects.get(pk=clases[0].turno.id)
                        aula = Aula.objects.get(pk=clases[0].aula.id)
                        dia = clases[0].dia
                        ids = []
                        if not solicitada and not isCerrada:
                            #if CLASES_HORARIO_ESTRICTO:
                            if ePeriodoAcademia.valida_clases_horario_estricto:
                                hoy = datetime.now().date()
                                if not (datetime(hoy.year, hoy.month, hoy.day, turno.comienza.hour, turno.comienza.minute, turno.comienza.second) - timedelta(minutes=ePeriodoAcademia.min_clases_apertura_antes_pro) <= datetime.now() <= datetime(hoy.year, hoy.month, hoy.day, turno.comienza.hour, turno.comienza.minute, turno.comienza.second) + timedelta(minutes=ePeriodoAcademia.min_clases_apertura_despues_pro)):
                                    transaction.set_rollback(True)
                                    return JsonResponse({"result": "bad", "mensaje": u"EL turno no es el correspondiente a la hora o el tiempo limite de aperturar la clases culmino."})
                                # elif not (datetime(hoy.year, hoy.month, hoy.day, turno.comienza.hour, turno.comienza.minute, turno.comienza.second) - timedelta(minutes=CLASES_APERTURA_ANTES) <= datetime.now() <= datetime(hoy.year, hoy.month, hoy.day, turno.comienza.hour, turno.comienza.minute, turno.comienza.second) + timedelta(minutes=CLASES_APERTURA_DESPUES)):
                                #     transaction.set_rollback(True)
                                #     return JsonResponse({"result": "bad", "mensaje": u"EL turno no es el correspondiente a la hora."})
                        if not lecciongrupo:
                            if 'fecha' in request.POST:
                                fecha = convertir_fecha(request.POST['fecha'])
                            if LeccionGrupo.objects.values('id').filter(status=True, profesor=profesor, turno=turno, fecha=fecha).exists():
                                if isCerrada:
                                    lg = LeccionGrupo.objects.filter(profesor=profesor, turno=turno, fecha=fecha)[0]
                                    lg.status = True
                                    lg.usuario_creacion_id = persona.usuario.id
                                    lg.save(request, update_fields=['status', 'usuario_creacion_id'])
                                    ids = []
                                    for leccion in lg.mis_leciones():
                                        leccion.status=True
                                        leccion.usuario_creacion_id = persona.usuario.id
                                        leccion.asistencialeccion_set.all().update(status=True, usuario_creacion_id = persona.usuario.id)
                                        leccion.save(request, update_fields=['status', 'usuario_creacion_id'])
                                        ids.append(leccion.id)
                                    return JsonResponse({"result": "ok", "lg": lg.id, "idlec": encrypt(ids[len(ids) - 1]) if ids else None})
                                if LeccionGrupo.objects.filter(status=True, profesor=profesor,lecciones__clase__id__in=clases.values_list('id'), turno=turno, fecha=fecha).exists():
                                    LeccionGrupo.objects.filter(status=True, profesor=profesor,lecciones__clase__id__in=clases.values_list('id'), turno=turno, fecha=fecha)[0].puede_eliminar_lecciongrupo(request)
                                # if LeccionGrupo.objects.values('id').filter(status=True, profesor=profesor, turno=turno, fecha=fecha).exists():
                                #     transaction.set_rollback(True)
                                #     return JsonResponse({"result": "bad", "mensaje": u"Existe una clase registrada en esa fecha en el turno seleccionado."})
                            client_address = get_client_ip(request)
                            if LeccionGrupo.objects.values('id').filter(status=False, profesor=profesor, turno=turno, fecha=fecha).exists():
                                lecciongrupo = LeccionGrupo.objects.filter(status=False, profesor=profesor, turno=turno, fecha=fecha)[0]
                                lecciongrupo.dia = dia
                                lecciongrupo.horaentrada = datetime.now().time() if not solicitada else turno.comienza
                                lecciongrupo.abierta = True
                                lecciongrupo.status = True
                                lecciongrupo.solicitada = solicitada
                                lecciongrupo.ipingreso = capippriva
                                lecciongrupo.ipexterna = client_address
                                lecciongrupo.usuario_creacion_id = persona.usuario.id
                                lecciongrupo.save(request, update_fields=['dia', 'horaentrada', 'abierta', 'status', 'solicitada', 'ipingreso', 'ipexterna', 'usuario_creacion_id'])
                            else:
                                if LeccionGrupo.objects.values('id').filter(status=True, profesor=profesor, turno=turno, fecha=fecha).exists():
                                    lecciongrupo = LeccionGrupo.objects.filter(status=True, profesor=profesor, turno=turno, fecha=fecha)[0]
                                    lecciongrupo.dia = dia
                                    lecciongrupo.horaentrada = datetime.now().time() if not solicitada else turno.comienza
                                    lecciongrupo.abierta = True
                                    lecciongrupo.status = True
                                    lecciongrupo.solicitada = solicitada
                                    lecciongrupo.ipingreso = capippriva
                                    lecciongrupo.ipexterna = client_address
                                    lecciongrupo.usuario_creacion_id = persona.usuario.id
                                    lecciongrupo.save(request, update_fields=['dia', 'horaentrada', 'abierta', 'status', 'solicitada', 'ipingreso', 'ipexterna', 'usuario_creacion_id'])
                                else:
                                    lecciongrupo = LeccionGrupo(profesor=profesor,
                                                                turno=turno,
                                                                aula=aula,
                                                                dia=dia,
                                                                fecha=fecha,
                                                                horaentrada=datetime.now().time() if not solicitada else turno.comienza,
                                                                abierta=True,
                                                                solicitada=solicitada,
                                                                contenido='SIN CONTENIDO',
                                                                estrategiasmetodologicas='SIN CONTENIDO',
                                                                observaciones='SIN OBSERVACIONES',
                                                                ipingreso=capippriva,
                                                                ipexterna=get_client_ip(request))

                            if isCerrada:
                                lecciongrupo.abierta = False
                            lecciongrupo.save(request)
                            log(u'Nueva lección grupo: %s - ip: %s' % (lecciongrupo, client_address), request, "add")

                        if estareemplazo:
                            registraleccion = RegistraLeccion(lecciongrupo=lecciongrupo, profesor=idreemplazo)
                            registraleccion.save(request)
                        for clase in clases:
                            if lecciongrupo.mis_leciones().values("id").filter(clase_id=clase.id).exists():
                                leccion = lecciongrupo.mis_leciones().filter(clase_id=clase.id)[0]
                                leccion.clase = clase
                                leccion.fecha = lecciongrupo.fecha
                                leccion.horaentrada = lecciongrupo.horaentrada
                                leccion.abierta = True
                                leccion.contenido = lecciongrupo.contenido
                                leccion.estrategiasmetodologicas = lecciongrupo.estrategiasmetodologicas
                                leccion.observaciones = lecciongrupo.observaciones
                                leccion.ipingreso = capippriva
                                leccion.ipexterna = get_client_ip(request)
                                leccion.aperturaleccion = True
                                leccion.solicitada = solicitada
                                leccion.status = True
                                leccion.usuario_creacion_id = persona.usuario.id
                                leccion.save(request, update_fields=['clase', 'fecha', 'horaentrada', 'abierta', 'contenido', 'estrategiasmetodologicas', 'observaciones', 'ipingreso', 'ipexterna', 'aperturaleccion', 'solicitada', 'status', 'usuario_creacion_id'])
                            else:
                                leccion = Leccion(clase=clase,
                                                  fecha=lecciongrupo.fecha,
                                                  horaentrada=lecciongrupo.horaentrada,
                                                  abierta=True,
                                                  contenido=lecciongrupo.contenido,
                                                  estrategiasmetodologicas=lecciongrupo.estrategiasmetodologicas,
                                                  observaciones=lecciongrupo.observaciones,
                                                  ipingreso=capippriva,
                                                  ipexterna=get_client_ip(request),
                                                  aperturaleccion=True,
                                                  solicitada=solicitada)
                            if isCerrada:
                                leccion.abierta = False

                            leccion.save(request)
                            log(u'Nueva lección: %s' % leccion, request, "add")
                            lecciongrupo.lecciones.add(leccion)
                            materia = clase.materia
                            # asignadas = materia.materiaasignada_set.all()
                            # if variable_valor('VALIDA_ASISTENCIA_PAGO'):
                            #     asignadas = asignadas.filter(matricula__estado_matricula__in=[2,3])

                            eMateriaAsignadas = MateriaAsignada.objects.none()
                            # SE FILTRA SI LA MATERIA TIENE TIPO DE PROFESOR PRACTICA Y LA CLASE TAMBIEN
                            # 1 => CLASE PRESENCIAL
                            # 2 => CLASE VIRTUAL SINCRÓNICA
                            # 8 => CLASE REFUERZO SINCRÓNICA
                            practicapreprofesional = None
                            if clase.tipoprofesor.id in [2, 13] and clase.tipohorario in [1, 2, 8]:
                                if clase.grupoprofesor:
                                    if clase.grupoprofesor.paralelopractica:
                                        # grupoprofesor_id = clase.grupoprofesor.id
                                        if clase.grupoprofesor.listado_inscritos_grupos_practicas().exists():
                                            listado_alumnos_practica = clase.grupoprofesor.listado_inscritos_grupos_practicas()
                                            if ePeriodoAcademia.valida_asistencia_pago:
                                                eMateriaAsignadas = MateriaAsignada.objects.filter(pk__in=listado_alumnos_practica.values_list('materiaasignada_id', flat=True), matricula__estado_matricula__in=[2,3]).distinct()
                                            else:
                                                eMateriaAsignadas = MateriaAsignada.objects.filter(pk__in=listado_alumnos_practica.values_list('materiaasignada_id', flat=True)).distinct()
                                            if leccion.leccion_es_practica_salud():
                                                if leccion.fecha_clase_verbose():
                                                    lecciongrupo.fecha = leccion.fecha_clase_verbose()
                                                    lecciongrupo.horaentrada = leccion.clase.turno.comienza
                                                    lecciongrupo.horasalida = leccion.clase.turno.termina
                                                    lecciongrupo.save(request, update_fields=['fecha', 'horaentrada', 'horasalida'])
                                                    leccion.fecha = lecciongrupo.fecha
                                                    leccion.horaentrada = lecciongrupo.horaentrada
                                                    leccion.horasalida = lecciongrupo.horasalida
                                                    leccion.status = True
                                                    leccion.usuario_creacion_id = persona.usuario.id
                                                    leccion.save(request, update_fields=['fecha', 'horaentrada', 'horasalida', 'status', 'usuario_creacion_id'])
                                                practicapreprofesional = PracticaPreProfesional(materia=materia,
                                                                                                profesor=clase.grupoprofesor.profesormateria.profesor,
                                                                                                lugar=u"SIN LUGAR DE PRÁCTICA",
                                                                                                horas=int(clase.turno.horas),
                                                                                                fecha=leccion.fecha_clase_verbose() if leccion.fecha_clase_verbose() else leccion.fecha,
                                                                                                objetivo=u'SIN OBJETIVO',
                                                                                                cerrado=False,
                                                                                                grupopractica=clase.grupoprofesor,
                                                                                                leccion=leccion)
                                                practicapreprofesional.save(request)
                                                log(u'Registro Guia de Práctica : %s' % practicapreprofesional, request, "add")

                                        else:
                                            lista = ['gestionacademica@unemi.edu.ec',
                                                     'planificacionacademica@unemi.edu.ec',
                                                     'kromanc1@unemi.edu.ec', ]
                                            send_html_mail("Docente si grupo de práctica",
                                                           "pro_clases/emails/notificacion_sin_alumnos_grupo_practica.html",
                                                           {'sistema': request.session['nombresistema'],
                                                            'persona': persona,
                                                            'clase': clase,
                                                            't': miinstitucion(),
                                                            }, lista, [],
                                                           cuenta=CUENTAS_CORREOS[0][1])

                                            raise NameError(u"Clase de tipo práctica no tiene alumnos. Favor comunicarse con Gestión Técnica o Soporte Informático")

                                    else:
                                        lista = ['gestionacademica@unemi.edu.ec',
                                                 'planificacionacademica@unemi.edu.ec',
                                                 'kromanc1@unemi.edu.ec', ]
                                        send_html_mail("Docente si grupo de práctica",
                                                       "pro_clases/emails/notificacion_sin_paralelo_grupo_practica.html",
                                                       {'sistema': request.session['nombresistema'],
                                                        'persona': persona,
                                                        'clase': clase,
                                                        't': miinstitucion(),
                                                        }, lista, [],
                                                       cuenta=CUENTAS_CORREOS[0][1])
                                        raise NameError(u"Clase de tipo práctica no tiene paralelos. Favor comunicarse con Gestión Técnica o Soporte Informático")
                                else:
                                    lista = ['gestionacademica@unemi.edu.ec',
                                             'planificacionacademica@unemi.edu.ec',
                                             'kromanc1@unemi.edu.ec', ]
                                    send_html_mail("Docente si grupo de práctica",
                                                   "pro_clases/emails/notificacion_sin_grupo_practica.html",
                                                   {'sistema': request.session['nombresistema'],
                                                    'persona': persona,
                                                    'clase': clase,
                                                    't': miinstitucion(),
                                                    }, lista, [],
                                                   cuenta=CUENTAS_CORREOS[0][1])
                                    raise NameError(u"Clase de tipo práctica no tiene grupos. Favor comunicarse con Gestión Técnica o Soporte Informático")
                            else:
                                eMateriaAsignadas = materia.asignados_a_esta_materia()
                            if ePeriodoAcademia:
                                if ePeriodoAcademia.utiliza_asistencia_redis:
                                    for leccion in lecciongrupo.mis_leciones():
                                        key_cache_leccion = f'data_asistencias_leccion_id_{encrypt(leccion.id)}'
                                        d = leccion.fecha
                                        d2 = datetime(d.year, d.month, d.day, turno.comienza.hour, turno.comienza.minute)
                                        time_life_token = (time.mktime((datetime(d.year, d.month, d.day, turno.termina.hour, turno.termina.minute)).timetuple()) - time.mktime(d2.timetuple()))
                                        """NO CAMBIAR, SI SE DESEA HACER PRUEBAS; PONGA SU MAQUINA EN AMBIENTE PRODUCCIÓN."""
                                        # redis.setex(key_alumno, int(time_life_token), json.dumps(aData))
                                        cache.set(key_cache_leccion, [], int(time_life_token))
                            for eMateriaAsignada in eMateriaAsignadas:
                                try:
                                    asistencialeccion = AsistenciaLeccion.objects.get(leccion_id=leccion.id, materiaasignada_id=eMateriaAsignada.id)
                                    asistencialeccion.status = True
                                    asistencialeccion.usuario_creacion_id = persona.usuario.id
                                    asistencialeccion.save(request, update_fields=['status', 'usuario_creacion_id'])
                                except ObjectDoesNotExist:
                                    asistencialeccion = AsistenciaLeccion(leccion=leccion,
                                                                          materiaasignada=eMateriaAsignada,
                                                                          asistio=False,
                                                                          virtual=False,
                                                                          virtual_fecha=None,
                                                                          virtual_hora=None,
                                                                          ip_private=None,
                                                                          ip_public=None,
                                                                          browser=None,
                                                                          ops=None,
                                                                          screen_size=None,
                                                                          )
                                    asistencialeccion.save(request)
                                if variable_valor('ACTUALIZA_ASISTENCIA') and variable_valor('ACTUALIZA_ASISTENCIA_APERTURA'):
                                    if not asistencialeccion.materiaasignada.sinasistencia:
                                        ActualizaAsistencia(asistencialeccion.materiaasignada.id)
                                if practicapreprofesional:
                                    participantepractica = ParticipantePracticaPreProfesional(practica=practicapreprofesional,
                                                                                              materiaasignada=eMateriaAsignada,
                                                                                              nota=0,
                                                                                              asistencia=asistencialeccion.asistio,
                                                                                              observacion='',
                                                                                              asistencialeccion=asistencialeccion)
                                    participantepractica.save(request)
                                    log(u'Adiciono Alumno %s a la Guia de Práctica : %s' % (participantepractica.materiaasignada.matricula.inscripcion.persona, practicapreprofesional), request, "add")
                                if ePeriodoAcademia:
                                    if ePeriodoAcademia.utiliza_asistencia_redis:
                                        key_alumno = f'{encrypt(leccion.clase.id)}{encrypt(turno.id)}{encrypt(eMateriaAsignada.matricula.inscripcion.persona.usuario.id)}{encrypt(dia)}{leccion.fecha.strftime("%d%m%Y")}'
                                        aData = {
                                            'user_id': eMateriaAsignada.matricula.inscripcion.persona.usuario.id,
                                            'clase_id': leccion.clase.id,
                                            'dia': dia,
                                            'turno_id': turno.id,
                                            "fecha": leccion.fecha.strftime("%d-%m-%Y"),
                                            "leccion_id": leccion.id,
                                            "leccion_grupo_id": lecciongrupo.id,
                                        }
                                        # d = datetime.now()
                                        d = leccion.fecha
                                        d2 = datetime(d.year, d.month, d.day, turno.comienza.hour, turno.comienza.minute)
                                        time_life_token = (time.mktime((datetime(d.year, d.month, d.day, turno.termina.hour, turno.termina.minute)).timetuple()) - time.mktime(d2.timetuple()))
                                        """NO CAMBIAR, SI SE DESEA HACER PRUEBAS; PONGA SU MAQUINA EN AMBIENTE PRODUCCIÓN."""
                                        # redis.setex(key_alumno, int(time_life_token), json.dumps(aData))
                                        cache.set(key_alumno, aData, int(time_life_token))
                            ids.append(leccion.id)
                        lecciongrupo.save(request)
                        return JsonResponse({"result": "ok", "lg": lecciongrupo.id, "idlec": encrypt(ids[len(ids) - 1]) if ids else None})
                    except Exception as ex:
                        transaction.set_rollback(True)
                        return JsonResponse({"result": "bad", "mensaje": u"Error al abrir la clase. %s" % ex.__str__()})

            elif action == 'asistencia':
                with transaction.atomic():
                    try:
                        result = actualizar_asistencia(request, calcula_procentaje_apertura)
                        result['materiaasignada'] = None
                        return JsonResponse(result)
                    except Exception as ex:
                        transaction.set_rollback(True)
                        return JsonResponse({"result": "bad"})

            elif action == 'asistenciagrupo':
                with transaction.atomic():
                    try:
                        lecciongrupo = LeccionGrupo.objects.get(pk=request.POST['id'])
                        asistieron = [int(x) for x in request.POST['lista'].split(',')]
                        asistencias = AsistenciaLeccion.objects.filter(leccion__lecciongrupo=lecciongrupo, leccion__lecciongrupo__status=True)
                        for asistencia in asistencias:
                            if asistencia.puede_tomar_asistencia():
                                asistencia.asistio = (asistencia.id in asistieron)
                                asistencia.save(request, update_fields=['asistio'])
                                if not asistencia.leccion.abierta:
                                    calcula_procentaje_apertura = True
                                asistencia.materiaasignada.save(actualiza=calcula_procentaje_apertura)
                                # if asistencia.asistio != (asistencia.id in asistieron):
                                #     asistencia.asistio = (asistencia.id in asistieron)
                                #     asistencia.save(request, update_fields=['asistio'])
                                #     asistencia.materiaasignada.save(actualiza=True)
                                # else:
                                #     asistencia.asistio = False
                                #     asistencia.save(request, update_fields=['asistio'])
                                #     asistencia.materiaasignada.save(actualiza=True)

                        return JsonResponse({"result": "ok"})
                    except Exception as ex:
                        transaction.set_rollback(True)
                        return JsonResponse({"result": "bad"})

            elif action == 'asistenciageneral':
                with transaction.atomic():
                    try:
                        lecciongrupo = LeccionGrupo.objects.get(pk=request.POST['id'])
                        lecciones = lecciongrupo.lecciones.all()
                        for leccion in lecciones:
                            asistencias = leccion.asistencialeccion_set.all()
                            for asistencia in asistencias:
                                if asistencia.puede_tomar_asistencia():
                                    asistencia.asistio = True
                                    estado = 'presente'
                                else:
                                    asistencia.asistio = False
                                    estado = 'falta'
                                asistencia.save(request, update_fields=['asistio'])
                                if not asistencia.leccion.abierta:
                                    calcula_procentaje_apertura = True
                                asistencia.materiaasignada.save(actualiza=calcula_procentaje_apertura)
                                log(u'Asistencia en clase: %s - %s - %s, estado: %s' % (asistencia.materiaasignada.materia.asignatura.nombre, asistencia.materiaasignada.matricula.inscripcion.persona.nombre_completo_inverso(), asistencia.leccion.fecha.strftime("%Y-%m-%d"), estado), request, "edit")
                        return JsonResponse({"result": "ok"})
                    except Exception as ex:
                        transaction.set_rollback(True)
                        return JsonResponse({"result": "bad"})

            elif action == 'addincidencia':
                with transaction.atomic():
                    try:
                        lecciongrupo = LeccionGrupo.objects.get(pk=request.POST['lecciongrupo'])
                        tipo = TipoIncidencia.objects.get(pk=request.POST['tipo'])
                        incidencia = Incidencia(lecciongrupo=lecciongrupo,
                                                tipo=tipo,
                                                contenido=request.POST['contenido'],
                                                cerrada=False)
                        incidencia.save(request)
                        incidencia.mail_nuevo(request.session['nombresistema'])
                        log(u'Adiciono incidencia en clase: %s' % incidencia, request, "add")
                        return JsonResponse({"result": "ok", "tipo": tipo.nombre, "contenido": incidencia.contenido})
                    except Exception as ex:
                        transaction.set_rollback(True)
                        return JsonResponse({"result": "bad"})

            elif action == 'evaluar':
                with transaction.atomic():
                    try:
                        valor, observacion = float(request.POST['val']), request.POST.get('obs', '').strip()
                        asistencialeccion = AsistenciaLeccion.objects.get(pk=request.POST['id'])
                        evaluacionleccion = EvaluacionLeccion(leccion=asistencialeccion.leccion,
                                                              materiaasignada=asistencialeccion.materiaasignada,
                                                              evaluacion=valor,
                                                              observacion=observacion)
                        evaluacionleccion.save(request)
                        log(u'Adicionó nueva nota: %s' % evaluacionleccion, request, "add")
                        return JsonResponse({"result": "ok", "evalid": evaluacionleccion.id, "promedio": int(asistencialeccion.promedio_evaluacion()), 'total': temp.totalevaluacion if (temp := asistencialeccion.evaluaciones()) else 0})
                    except Exception as ex:
                        transaction.set_rollback(True)
                        return JsonResponse({"result": "bad"})

            elif action == "borrarevaluacion":
                with transaction.atomic():
                    try:
                        asistencialeccion = AsistenciaLeccion.objects.get(pk=request.POST['asisid'])
                        lastlesson = asistencialeccion.evaluaciones().order_by('-fecha_creacion').first()
                        # evaluacion = EvaluacionLeccion.objects.get(pk=request.POST['evalid'])
                        log(u'Eliminó Evaluación: %s' % lastlesson, request, "del")
                        lastlesson.delete()
                        return JsonResponse({"result": "ok", "promedio": int(asistencialeccion.promedio_evaluacion()), "total": temp.totalevaluacion if (temp := asistencialeccion.evaluaciones()) else 0})
                    except Exception as ex:
                        transaction.set_rollback(True)
                        return JsonResponse({"result": "bad"})

            elif action == 'contenido':
                with transaction.atomic():
                    try:
                        result = actualizar_contenido(request)
                        return JsonResponse(result)
                    except Exception as ex:
                        transaction.set_rollback(True)
                        return JsonResponse({"result": "bad"})

            elif action == 'verificarcontinuaabierta':
                with transaction.atomic():
                    try:
                        lecciongrupo = LeccionGrupo.objects.get(pk=request.POST['id'])
                        asistencias = []
                        if not ePeriodoAcademia.utiliza_asistencia_ws:
                            for leccion in lecciongrupo.mis_leciones():
                                for asistencia in leccion.mis_asistencias():
                                    asistencias.append({"id": asistencia.id,
                                                        "leccion_id": asistencia.leccion.id,
                                                        "materiaasignada": asistencia.materiaasignada.id,
                                                        "asistenciafinal": null_to_numeric(asistencia.materiaasignada.asistenciafinal, 0),
                                                        "porciento_requerido": asistencia.materiaasignada.porciento_requerido(),
                                                        "asistenciajustificada": asistencia.asistenciajustificada,
                                                        "asistio": asistencia.asistio,
                                                        "virtual": asistencia.virtual,
                                                        "virtual_fecha": asistencia.virtual_fecha.__str__() if asistencia.virtual_fecha else None,
                                                        "virtual_hora": asistencia.virtual_hora.strftime("%H:%M:%S") if asistencia.virtual_hora else None,
                                                        "ip_private": asistencia.ip_private,
                                                        "ip_public": asistencia.ip_public,
                                                        "browser": asistencia.browser,
                                                        "ops": asistencia.ops,
                                                        "screen_size": asistencia.screen_size,
                                                        })
                        otraslecciones = LeccionGrupo.objects.filter(profesor=lecciongrupo.profesor, abierta=True).exclude(id=lecciongrupo.id)
                        otrasleccionesid = 0
                        if otraslecciones:
                            otrasleccionesid = otraslecciones[0].id
                        return JsonResponse({"result": "ok", "abierta": lecciongrupo.abierta, "puede_cerrar_leccion_grupo": lecciongrupo.puede_cerrar_leccion_grupo(), "otras": otrasleccionesid, "asistencias": asistencias})
                    except Exception as ex:
                        # transaction.set_rollback(True)
                        return JsonResponse({"result": "bad", "mensaje": "Ocurrio un error al cargar los datos: % " % ex.__str__()})

            elif action == 'observaciones':
                with transaction.atomic():
                    try:
                        l = Leccion.objects.get(pk=int(request.POST['id']))
                        lecciongrupo = l.leccion_grupo()
                        lecciongrupo.contenido = request.POST['val']
                        lecciongrupo.save(request)
                        for leccion in lecciongrupo.mis_leciones():
                            leccion.observaciones = request.POST['val']
                            leccion.save(request, update_fields=['observaciones'])
                        return JsonResponse({"result": "ok"})
                    except Exception as ex:
                        transaction.set_rollback(True)
                        return JsonResponse({"result": "bad"})

            elif action == 'lugarpractica':
                with transaction.atomic():
                    try:
                        l = Leccion.objects.get(pk=int(request.POST['id']))
                        if not l.leccion_es_practica_salud():
                            raise NameError(u'No es práctica de salud')
                        if l.tiene_registro_practica():
                            practica = l.mi_registro_practica()
                            practica.lugar = request.POST['val']
                            practica.cerrado = not l.abierta
                            practica.save(request, update_fields=['lugar', 'cerrado'])
                            log(u'Modifico lugar de la practica preprofesional: %s' % practica, request, "edit")
                        else:
                            practicapreprofesional = PracticaPreProfesional(materia=l.clase.materia,
                                                                            profesor=l.clase.grupoprofesor.profesormateria.profesor,
                                                                            lugar=request.POST['val'],
                                                                            horas=l.clase.turno.horas,
                                                                            fecha=l.fecha_clase_verbose() if l.fecha_clase_verbose() else l.fecha,
                                                                            objetivo=u'SIN OBJETIVO',
                                                                            cerrado=not l.abierta,
                                                                            grupopractica=l.clase.grupoprofesor,
                                                                            leccion=l)
                            practicapreprofesional.save(request)
                            log(u'Registro Guia de Práctica : %s' % practicapreprofesional, request, "add")
                            for asistencialeccion in l.asistencialeccion_set.prefetch_related().filter(status=True):
                                if not ParticipantePracticaPreProfesional.objects.values("id").filter(asistencialeccion=asistencialeccion).exists():
                                    participantepractica = ParticipantePracticaPreProfesional(practica=practicapreprofesional,
                                                                                              materiaasignada=asistencialeccion.materiaasignada,
                                                                                              nota=0,
                                                                                              asistencia=asistencialeccion.asistio,
                                                                                              observacion='',
                                                                                              asistencialeccion=asistencialeccion)
                                    participantepractica.save(request)
                                    log(u'Adiciono Alumno %s a la Guia de Práctica : %s' % (participantepractica.materiaasignada.matricula.inscripcion.persona, practicapreprofesional), request, "add")
                        return JsonResponse({"result": "ok"})
                    except Exception as ex:
                        transaction.set_rollback(True)
                        return JsonResponse({"result": "bad"})

            elif action == 'objetivopractica':
                with transaction.atomic():
                    try:
                        l = Leccion.objects.get(pk=int(request.POST['id']))
                        if not l.leccion_es_practica_salud():
                            raise NameError(u'No es práctica de salud')
                        if l.tiene_registro_practica():
                            practica = l.mi_registro_practica()
                            practica.objetivo = request.POST['val']
                            practica.cerrado = not l.abierta
                            practica.save(request, update_fields=['objetivo', 'cerrado'])
                            log(u'Modifico objetivo de la practica preprofesional: %s' % practica, request, "edit")
                        else:
                            practicapreprofesional = PracticaPreProfesional(materia=l.clase.materia,
                                                                            profesor=l.clase.grupoprofesor.profesormateria.profesor,
                                                                            lugar=u"SIN LUGAR DE PRÁCTICA",
                                                                            horas=l.clase.turno.horas,
                                                                            fecha=l.fecha_clase_verbose() if l.fecha_clase_verbose() else l.fecha,
                                                                            objetivo=request.POST['val'],
                                                                            cerrado=not l.abierta,
                                                                            grupopractica=l.clase.grupoprofesor,
                                                                            leccion=l)
                            practicapreprofesional.save(request)
                            log(u'Registro Guia de Práctica : %s' % practicapreprofesional, request, "add")
                            for asistencialeccion in l.asistencialeccion_set.prefetch_related().filter(status=True):
                                if not ParticipantePracticaPreProfesional.objects.values("id").filter(asistencialeccion=asistencialeccion).exists():
                                    participantepractica = ParticipantePracticaPreProfesional(practica=practicapreprofesional,
                                                                                              materiaasignada=asistencialeccion.materiaasignada,
                                                                                              nota=0,
                                                                                              asistencia=asistencialeccion.asistio,
                                                                                              observacion='',
                                                                                              asistencialeccion=asistencialeccion)
                                    participantepractica.save(request)
                                    log(u'Adiciono Alumno %s a la Guia de Práctica : %s' % (participantepractica.materiaasignada.matricula.inscripcion.persona, practicapreprofesional), request, "add")
                        return JsonResponse({"result": "ok"})
                    except Exception as ex:
                        transaction.set_rollback(True)
                        return JsonResponse({"result": "bad"})

            elif action == 'estrategiasmetodologicas':
                with transaction.atomic():
                    try:
                        lecciongrupo = Leccion.objects.get(pk=int(request.POST['id']))
                        lecciongrupo.estrategiasmetodologicas = request.POST['val']
                        lecciongrupo.save(request, update_fields=['estrategiasmetodologicas'])
                        return JsonResponse({"result": "ok"})
                    except Exception as ex:
                        transaction.set_rollback(True)
                        return JsonResponse({"result": "bad"})

            elif action == 'cerrar':
                with transaction.atomic():
                    try:
                        lecciongrupo = LeccionGrupo.objects.get(pk=request.POST['id'])
                        turno = lecciongrupo.turno
                        if not lecciongrupo.contenido:
                            transaction.set_rollback(True)
                            return JsonResponse({"result": "bad", "motivo": "contenido"})
                        if lecciongrupo.abierta:
                            lecciongrupo.abierta = False
                            lecciongrupo.horasalida = datetime.now().time()
                            if lecciongrupo.solicitada:
                                # lecciongrupo.horaentrada = turno.comienza
                                lecciongrupo.horasalida = turno.termina
                            lecciongrupo.save(request, update_fields=['abierta', 'horasalida'])
                            for leccion in lecciongrupo.lecciones.all():
                                leccion.abierta = False
                                leccion.horasalida = datetime.now().time()
                                if lecciongrupo.solicitada:
                                    # leccion.horaentrada = turno.comienza
                                    leccion.horasalida = turno.termina
                                leccion.save(request, update_fields=['abierta', 'horasalida'])
                                log(u'Editó nueva nota: %s' % leccion, request, "edit")
                                if leccion.tiene_registro_practica():
                                    practica = leccion.mi_registro_practica()
                                    practica.cerrado = True
                                    practica.save(request, update_fields=['cerrado'])
                                    log(u'Cierro la practica preprofesional: %s' % practica, request, "edit")
                                materia = leccion.clase.materia
                                materiaasignadas = materia.materiaasignada_set.filter(status=True, retiramateria=False)
                                for eMateriaAsignada in materiaasignadas:
                                    if not calcula_procentaje_apertura:
                                        eMateriaAsignada.save(actualiza=True)
                                    key_alumno = f'{encrypt(leccion.clase.id)}{encrypt(leccion.clase.turno.id)}{encrypt(eMateriaAsignada.matricula.inscripcion.persona.usuario.id)}{encrypt(lecciongrupo.dia)}{leccion.fecha.strftime("%d%m%Y")}'
                                    if cache.has_key(key_alumno):
                                        cache.delete(key_alumno)
                        return JsonResponse({"result": "ok"})
                    except Exception as ex:
                        transaction.set_rollback(True)
                        return JsonResponse({"result": "bad"})

            elif action == 'cerrarclaseindividual':
                with transaction.atomic():
                    try:
                        leccion = Leccion.objects.get(pk=int(encrypt(request.POST['id'])))
                        if leccion.tiene_registro_practica():
                            practica = leccion.mi_registro_practica()
                            practica.cerrado = True
                            practica.save(request, update_fields=['cerrado'])
                            log(u'Cierro la practica preprofesional: %s' % practica, request, "edit")
                        grupoleccion = leccion.leccion_grupo()
                        turno = grupoleccion.turno
                        if not grupoleccion.contenido:
                            transaction.set_rollback(True)
                            return JsonResponse({"result": "bad", "motivo": "contenido"})
                        if leccion.abierta:
                            leccion.abierta = False
                            # leccion.horaentrada = turno.comienza
                            leccion.horasalida = turno.termina
                            leccion.save(request, update_fields=['abierta', 'horasalida'])
                            log(u'Cerro la clase: %s' % leccion, request, "edit")
                            if grupoleccion.abierta:
                                if not grupoleccion.existen_lecciones_abiertas():
                                    grupoleccion.abierta = False
                                    grupoleccion.horasalida = turno.termina
                                    grupoleccion.save(request, update_fields=['abierta', 'horasalida'])
                                    log(u'Cerro la leccion grupo porque no tiene lecciones abiertas: %s' % grupoleccion, request, "edit")
                            materia = leccion.clase.materia
                            materiaasignadas = materia.materiaasignada_set.filter(status=True, retiramateria=False)
                            for eMateriaAsignada in materiaasignadas:
                                key_alumno = f'{encrypt(leccion.clase.id)}{encrypt(leccion.clase.turno.id)}{encrypt(eMateriaAsignada.matricula.inscripcion.persona.usuario.id)}{encrypt(grupoleccion.dia)}{leccion.fecha.strftime("%d%m%Y")}'
                                if cache.has_key(key_alumno):
                                    cache.delete(key_alumno)
                        return JsonResponse({"result": "ok"})
                    except Exception as ex:
                        transaction.set_rollback(True)
                        return JsonResponse({"result": "bad"})

            elif action == 'detallesolicitud':
                try:
                    data['solicitud'] = soli = SolicitudJustificacionAsistencia.objects.get(pk=int(request.POST['id']))
                    data['solicitado'] = variable_valor('SOLICITUD_JUSTIFICACION_ASISTENCIA')
                    data['aprobado'] = variable_valor('APROBADO_JUSTIFICACION_ASISTENCIA')
                    data['rechazado'] = variable_valor('RECHAZADO_JUSTIFICACION_ASISTENCIA')
                    materias = soli.matricula.materiaasignada_set.all()
                    data['materias'] = materias
                    data['no_atendido'] = variable_valor('SOLICITUD_JUSTIFICACION_ASISTENCIA_NO_ATENDIDA')
                    template = get_template("alu_solicitudjustificacionasistencia/detallesolicitud.html")
                    json_content = template.render(data)
                    return JsonResponse({"result": "ok", 'data': json_content})
                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

            elif action == 'adddeberes':
                with transaction.atomic():
                    try:
                        form = ArchivoDeberForm(request.POST, request.FILES)
                        if form.is_valid():
                            lecciongrupo = LeccionGrupo.objects.get(pk=request.POST['lecciongrupo'])
                            lecciones = lecciongrupo.mis_leciones()
                            newfile = request.FILES['archivo']
                            newfile._name = generar_nombre("deber_", newfile._name)
                            for leccion in lecciones:
                                archivo = Archivo(nombre=form.cleaned_data['nombre'],
                                                  materia=leccion.clase.materia,
                                                  lecciongrupo=lecciongrupo,
                                                  fecha=datetime.now().date(),
                                                  archivo=newfile,
                                                  tipo_id=ARCHIVO_TIPO_DEBERES)
                                archivo.save()
                                log(u'Adicionar nueva archivo: %s' % archivo, request, "add")
                                if NOTIFICACION_DEBERES:
                                    en_materia = []
                                    # if variable_valor('VALIDA_ASISTENCIA_PAGO'):
                                    #     for asignadomateria in leccion.clase.materia.materiaasignada_set.filter(matricula__estado_matricula__in=[2,3]):
                                    #         en_materia.extend(asignadomateria.matricula.inscripcion.persona.lista_emails_envio())
                                    # else:
                                    #     for asignadomateria in leccion.clase.materia.materiaasignada_set.all():
                                    #         en_materia.extend(asignadomateria.matricula.inscripcion.persona.lista_emails_envio())
                                    materiaasignadas = leccion.clase.materia.materiaasignada_set.filter(status=True, retiramateria=False)
                                    if ePeriodoAcademia.valida_asistencia_pago:
                                        for asignadomateria in materiaasignadas:
                                            if not asignadomateria.matricula.estado_matricula == 1:
                                                en_materia.extend(asignadomateria.matricula.inscripcion.persona.lista_emails_envio())
                                    else:
                                        for asignadomateria in materiaasignadas:
                                            en_materia.extend(asignadomateria.matricula.inscripcion.persona.lista_emails_envio())

                                    send_html_mail("Nuevo deber en Clase", "emails/deber.html", {'sistema': request.session['nombresistema'], 'nombrearchivo': archivo.nombre, 't': miinstitucion(), 'f': lecciongrupo.fecha, 'd': leccion.clase.materia.profesor_actual(), 'contenido': 'Su profesor le ha asignado un deber el cual debe descargar desde el sistema de gestion academica'}, en_materia, [], cuenta=CUENTAS_CORREOS[3][1])
                            return JsonResponse({"result": "ok"})
                        else:
                            raise NameError('Error')
                    except Exception as ex:
                        transaction.set_rollback(True)
                        return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

            elif action == 'contenidoacademico':
                with transaction.atomic():
                    try:
                        form = ContenidoAcademicoForm(request.POST)
                        if form.is_valid():
                            leccion = Leccion.objects.get(pk=int(encrypt(request.POST['id'])))
                            # leccion.contenido = form.cleaned_data['contenido']
                            # leccion.estrategiasmetodologicas = form.cleaned_data['estrategiasmetodologicas']
                            leccion.observaciones = form.cleaned_data['observaciones']
                            leccion.save(request, update_fields=['observaciones'])
                            if not leccion.aperturaleccion:
                                lecciongrupo = leccion.leccion_grupo()
                                lecciongrupo.observaciones = form.cleaned_data['observaciones']
                                lecciongrupo.save(request, update_fields=['observaciones'])
                            log(u'Editó Contenido Academico: %s' % leccion, request, "add")
                            return JsonResponse({"result": "ok"})
                        else:
                            raise NameError('Error')
                    except Exception as ex:
                        transaction.set_rollback(True)
                        return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

            elif action == 'updatefecha':
                with transaction.atomic():
                    try:
                        lecciongrupo = LeccionGrupo.objects.get(pk=request.POST['id'])
                        fecha = convertir_fecha(request.POST['fecha'])
                        for leccion in lecciongrupo.lecciones.all():
                            if fecha > leccion.clase.fin or fecha < leccion.clase.inicio:
                                return JsonResponse({"result": "bad", "mensaje": u"Fecha incorrecta."})
                        lecciongrupo.fecha = fecha
                        lecciongrupo.save(request, update_fields=['fecha'])
                        for leccion in lecciongrupo.lecciones.all():
                            leccion.fecha = fecha
                            leccion.save(request, update_fields=['fecha'])
                        return JsonResponse({"result": "ok"})
                    except Exception as ex:
                        transaction.set_rollback(True)
                        return JsonResponse({'result': 'bad'})

            elif action == 'delleccion':
                with transaction.atomic():
                    try:
                        leccion = Leccion.objects.get(pk=request.POST['id'])
                        if leccion.leccion_es_practica_salud() and leccion.tiene_registro_practica():
                            practicas = PracticaPreProfesional.objects.filter(leccion=leccion)
                            for practica in practicas:
                                practica.delete()
                                log(u'Elimino practica de campo de salud: %s ' % practica, request, "del")
                        solicitudes = leccion.solicitud_apertura()
                        if leccion.tiene_solicitud_apertura():
                            for solicitud in solicitudes:
                                solicitud.aperturada = False
                                solicitud.save(request, update_fields=['aperturada'])
                        lecciongrupo = leccion.leccion_grupo()
                        leccion.asistencialeccion_set.all().delete()
                        materia = leccion.clase.materia
                        log(u'Elimino leccion clase: %s ' % leccion, request, "del")
                        leccion.delete()
                        # if variable_valor('VALIDA_ASISTENCIA_PAGO'):
                        materiaasignadas = materia.materiaasignada_set.filter(status=True, retiramateria=False)
                        if ePeriodoAcademia.valida_asistencia_pago:
                            for materiaasignada in materiaasignadas:
                                if not materiaasignada.matricula.estado_matricula == 1:
                                    materiaasignada.save(actualiza=True)
                                    materiaasignada.actualiza_notafinal()
                        else:
                            for materiaasignada in materiaasignadas:
                                materiaasignada.save(actualiza=True)
                                materiaasignada.actualiza_notafinal()
                        if lecciongrupo:
                            lecciongrupo.puede_eliminar_lecciongrupo(request)
                        for eMateriaAsignada in materiaasignadas:
                            key_alumno = f'{encrypt(leccion.clase.id)}{encrypt(leccion.clase.turno.id)}{encrypt(eMateriaAsignada.matricula.inscripcion.persona.usuario.id)}{encrypt(lecciongrupo.dia)}{leccion.fecha.strftime("%d%m%Y")}'
                            if cache.has_key(key_alumno):
                                cache.delete(key_alumno)
                        return JsonResponse({"result": "ok"})
                    except Exception as ex:
                        transaction.set_rollback(True)
                        return JsonResponse({"result": "bad", "mensaje": u"Error al eliminar los datos."})

            elif action == 'selecttema':
                with transaction.atomic():
                    try:
                        lista, checked = [], False
                        l = Leccion.objects.get(pk=int(request.POST['idl']))
                        detallesilabosemanaltema = DetalleSilaboSemanalTema.objects.get(pk=request.POST['idt'])
                        temaunidadresultadoprogramaanalitico = detallesilabosemanaltema.temaunidadresultadoprogramaanalitico
                        numsemana = detallesilabosemanaltema.silabosemanal.numsemana
                        semana = detallesilabosemanaltema.silabosemanal.semana
                        materia = l.clase.materia

                        lecciongrupo = l.leccion_grupo()
                        for leccion in lecciongrupo.mis_leciones():
                            leccion_id = leccion.id
                            if not TemaAsistencia.objects.filter(leccion__clase__materia=materia, tema=detallesilabosemanaltema, status=True).exists():
                                tema = TemaAsistencia(leccion_id=leccion_id, tema=detallesilabosemanaltema, fecha=datetime.now().date())
                                tema.save(request)
                                log(u'Seleccionó tema de la planificacion: %s' % tema, request, "add")
                                filtrosubtema = Q(subtemaunidadresultadoprogramaanalitico__temaunidadresultadoprogramaanalitico=temaunidadresultadoprogramaanalitico, subtemaunidadresultadoprogramaanalitico__status=True,subtemaunidadresultadoprogramaanalitico__temaunidadresultadoprogramaanalitico__isnull=False,subtemaunidadresultadoprogramaanalitico__temaunidadresultadoprogramaanalitico__status=True, status=True)
                                for subtema in detallesilabosemanaltema.silabosemanal.detallesilabosemanalsubtema_set.filter(filtrosubtema):
                                    if not subtema.subtemaasistencia_set.filter(tema__tema=detallesilabosemanaltema, status=True):
                                        sub = SubTemaAsistencia(tema=tema, subtema=subtema, fecha=datetime.now().date())
                                        sub.save(request)
                                        log(u'Seleccionó subtema de la planificacion: %s' % sub, request, "add")
                                        lista.append(subtema.pk)

                                checked = True
                            else:
                                for tema in TemaAsistencia.objects.filter(leccion__clase__materia=materia, tema=detallesilabosemanaltema, status=True):
                                    for subtemaasistencia in tema.subtemaasistencia_set.filter(status=True):
                                        lista.append(subtemaasistencia.subtema.id)
                                        subtemaasistencia.delete()

                                    log(u'Eliminar tema  de la planificación: %s' % tema, request, "del")
                                    tema.delete()
                        return JsonResponse({"result": "ok", 'lista': lista, 'checked': checked})
                    except Exception as ex:
                        transaction.set_rollback(True)
                        return JsonResponse({"result": "bad", "mensaje": u"Error al guardar el tema. %s" % ex})

            elif action == 'selectsubtema':
                with transaction.atomic():
                    try:
                        l = Leccion.objects.get(pk=int(request.POST['idl']))
                        eDetalleSilaboSemanalTema = DetalleSilaboSemanalTema.objects.get(pk=request.POST['idt'])
                        eDetalleSilaboSemanalSubTema = DetalleSilaboSemanalSubtema.objects.get(pk=request.POST['ids'])
                        temaunidadresultadoprogramaanalitico = eDetalleSilaboSemanalTema.temaunidadresultadoprogramaanalitico
                        subtemaunidadresultadoprogramaanalitico = eDetalleSilaboSemanalSubTema.subtemaunidadresultadoprogramaanalitico
                        numsemana = eDetalleSilaboSemanalTema.silabosemanal.numsemana
                        semana = eDetalleSilaboSemanalTema.silabosemanal.semana
                        marcartema = 0
                        materia = l.clase.materia
                        lecciongrupo = l.leccion_grupo()

                        for indice, leccion in enumerate(lecciongrupo.mis_leciones()):
                            if eDetalleSilaboSemanalTemas := DetalleSilaboSemanalTema.objects.filter(silabosemanal__silabo__materia=leccion.clase.materia, temaunidadresultadoprogramaanalitico=temaunidadresultadoprogramaanalitico, silabosemanal__numsemana=numsemana, silabosemanal__semana=semana,silabosemanal__status=True, status=True):
                                eDetalleSilaboSemanalSubTemas = DetalleSilaboSemanalSubtema.objects.filter(silabosemanal__silabo__materia=leccion.clase.materia, subtemaunidadresultadoprogramaanalitico=subtemaunidadresultadoprogramaanalitico, silabosemanal__numsemana=numsemana, silabosemanal__semana=semana, status=True)

                                # No filtra por lección porque se les dió plazo de 1 a 2 semanas para marcar el tema.
                                temamarcado = TemaAsistencia.objects.filter(leccion__clase__materia=materia, tema=eDetalleSilaboSemanalTemas[0]).order_by('fecha_creacion').first()
                                if not temamarcado:
                                    temamarcado = TemaAsistencia(leccion_id=leccion.id, tema=eDetalleSilaboSemanalTemas[0], fecha=datetime.now().date())
                                    temamarcado.save(request)
                                    marcartema = 1
                                    log(u'Seleccionó tema de la planificacion: %s' % temamarcado, request, "add")

                                subtemasmarcados = SubTemaAsistencia.objects.filter(tema__leccion__clase__materia=materia, subtema=eDetalleSilaboSemanalSubTemas[0], status=True)
                                if not subtemasmarcados.exists():
                                    sub = SubTemaAsistencia(tema=temamarcado, subtema=eDetalleSilaboSemanalSubTemas[0], fecha=datetime.now().date())
                                    sub.save(request)
                                    log(u'Seleccionó subtema de la planificacion: %s' % sub, request, "add")
                                else:
                                    log(u'Eliminó subtema de la planificacion: %s' % subtemasmarcados, request, "del")
                                    subtemasmarcados.delete()

                                    # Si ya no quedan subtemas marcados de ese tema eliminamos tambien el tema
                                    if not SubTemaAsistencia.objects.filter(tema__leccion__clase__materia=materia, tema__tema=eDetalleSilaboSemanalTemas[0], status=True).values('id').exists():
                                        TemaAsistencia.objects.filter(leccion__clase__materia=materia, tema=eDetalleSilaboSemanalTemas[0]).delete()
                                        log(u'Eliminó tema de la planificacion: %s' % temamarcado, request, "del")
                                        marcartema = 2

                        return JsonResponse({"result": "ok", 'marcartema': marcartema})
                    except Exception as ex:
                        transaction.set_rollback(True)
                        return JsonResponse({"result": "bad", "mensaje": f"Error al guardar los temas. {ex.__str__()}"})

            elif action == 'selectsubtemaadicional':
                with transaction.atomic():
                    try:
                        stema=0
                        l = Leccion.objects.get(pk=int(request.POST['idl']))
                        lecciongrupo = l.leccion_grupo()
                        for leccion in lecciongrupo.mis_leciones():
                            materia = leccion.clase.materia
                            leccion_id = leccion.id
                            if not TemaAsistencia.objects.filter(leccion_id=leccion_id, tema_id=request.POST['idt']).exists():
                                tema = TemaAsistencia(leccion_id=leccion_id, tema_id=request.POST['idt'], fecha=datetime.now().date())
                                tema.save(request)
                                log(u'Seleccionó tema de la planificacion: %s' % tema, request, "add")
                                # stema= tema.tema.id
                                suba=SubTemaAdicionalAsistencia(tema=tema, subtema_id=int(request.POST['ids']), fecha=datetime.now().date())
                                suba.save(request)
                                log(u'Seleccionó subtema de la planificacion: %s' % suba, request, "add")
                            else:
                                tema = TemaAsistencia.objects.get(leccion_id=leccion_id,tema_id=int(request.POST['idt']))
                                if not tema.subtemaadicionalasistencia_set.filter(subtema_id=int(request.POST['ids'])).exists():
                                    suba = SubTemaAdicionalAsistencia(tema_id=tema.id, subtema_id=request.POST['ids'],fecha=datetime.now().date())
                                    suba.save(request)
                                    log(u'Seleccionó subtema de la planificacion: %s' % suba, request, "add")
                                else:
                                    sub = SubTemaAdicionalAsistencia.objects.get(tema_id=tema.id, subtema_id=request.POST['ids'])
                                    log(u'Eliminó subtema de la planificacion: %s' % sub, request, "del")
                                    sub.delete()
                        return JsonResponse({"result": "ok", 'tem': tema.tema.id})
                    except Exception as ex:
                        transaction.set_rollback(True)
                        return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los temas."})

            elif action == 'missubtemas':
                with transaction.atomic():
                    try:
                        lecciongrupo = LeccionGrupo.objects.get(pk=int(request.POST['idl']))
                        materia = lecciongrupo.lecciones.all()[0].clase.materia
                        tema = TemaAsistencia.objects.get(leccion__clase__materia_id=materia.id, tema_id=int(request.POST['idt']))
                        subtemas = tema.subtemaasistencia_set.filter(status=True)
                        lista = []
                        for subtema in subtemas:
                            lista.append([subtema.subtema.id])
                        # data =
                        return JsonResponse({"results": "ok", "lista": lista})
                    except Exception as ex:
                        transaction.set_rollback(True)
                        return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los temas."})

            elif action == 'leccion_silabo':
                try:
                    clase = int(request.POST['idc'])
                    abierta = True if request.POST['abierta'] == 'True' else False
                    data['abierta'] = abierta
                    data['materia'] = materia = Materia.objects.get(pk=int(request.POST['idm']))
                    data['temas'] = temas = TemaAsistencia.objects.filter(leccion__clase__materia_id=materia.id, leccion__clase_id=clase, status=True).distinct().order_by('tema__temaunidadresultadoprogramaanalitico__orden')
                    data['subtemas'] = subt = SubTemaAsistencia.objects.filter(tema_id__in=temas).distinct().order_by('subtema__subtemaunidadresultadoprogramaanalitico__orden')
                    data['subtemasad'] = subtad = SubTemaAdicionalAsistencia.objects.filter(tema_id__in=temas).distinct()
                    vizualizar = False
                    if temas:
                        fecha = temas.order_by('-id')[0].fecha
                        if fecha.month == datetime.now().month and fecha.day == datetime.now().day:
                            vizualizar = True
                    if subt:
                        fechasub = subt.order_by('-id')[0].fecha
                        if fechasub.month == datetime.now().month and fechasub.day == datetime.now().day:
                            vizualizar = True
                    data['vizualizar'] = vizualizar

                    data['lecciongrupo'] = lecciongrupo = LeccionGrupo.objects.get(pk=request.POST['idl'])
                    # data['leccion'] = lecciongrupo.lecciones.db_manager("sga_select").all()[0]
                    data['leccion'] = lecciongrupo.lecciones.filter(clase_id=clase)[0]
                    data['ePeriodoAcademia'] = ePeriodoAcademia

                    if variable_valor('VERSION_REGISTRO_ASISTENCIA') == 2:
                        template = get_template("pro_clases/leccion_silabo_v2.html")
                    else:
                        template = get_template("pro_clases/leccion_silabo.html")
                    json_content = template.render(data)
                    return JsonResponse({"results": "ok", "html": json_content})
                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los temas."})

            elif action == 'leccion_silabo_practica_salud':
                try:
                    clase = int(request.POST['idc'])
                    data['abierta'] = True if request.POST['abierta'] == 'True' else False
                    data['materia'] = materia = Materia.objects.db_manager("sga_select").get(pk=int(request.POST['idm']))
                    data['leccion'] = materia = Materia.objects.db_manager("sga_select").get(pk=int(request.POST['idm']))
                    data['temas'] = temas = TemaAsistencia.objects.db_manager("sga_select").filter(leccion__clase__materia_id=materia.id, leccion__clase_id=clase, status=True).distinct().order_by('tema__temaunidadresultadoprogramaanalitico__orden')
                    data['subtemas'] = subt = SubTemaAsistencia.objects.db_manager("sga_select").filter(tema_id__in=temas).distinct().order_by('subtema__subtemaunidadresultadoprogramaanalitico__orden')
                    data['subtemasad'] = subtad = SubTemaAdicionalAsistencia.objects.db_manager("sga_select").filter(tema_id__in=temas).distinct()
                    vizualizar = False
                    if temas:
                        fecha = temas.order_by('-id')[0].fecha
                        if fecha.month == datetime.now().month and fecha.day == datetime.now().day:
                            vizualizar = True
                    if subt:
                        fechasub = subt.order_by('-id')[0].fecha
                        if fechasub.month == datetime.now().month and fechasub.day == datetime.now().day:
                            vizualizar = True
                    data['vizualizar'] = vizualizar

                    data['lecciongrupo'] = lecciongrupo = LeccionGrupo.objects.db_manager("sga_select").get(pk=request.POST['idl'])
                    data['leccion'] = lecciongrupo.lecciones.db_manager("sga_select").all()[0]

                    template = get_template("pro_clases/leccion_silabo_practica_salud.html")
                    json_content = template.render(data)
                    return JsonResponse({"results": "ok", "html": json_content})
                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los temas."})

            elif action == 'addVideoVirtual':
                with transaction.atomic():
                    try:
                        from Moodle_Funciones import CrearClaseVirtualClaseMoodleDiferido, CrearClaseSincronicaMoodleDiferido, CrearClaseAsincronicaMoodleDiferido
                        if not 'idc' in request.POST:
                            raise NameError(u"Parametro de clase no encontrado")
                        if not 'link_1' in request.POST:
                            raise NameError(u"Parametro de enlace 1  de la clase no encontrado")
                        if not 'link_2' in request.POST:
                            raise NameError(u"Parametro de enlace 2 de la clase no encontrado")
                        if not 'link_3' in request.POST:
                            raise NameError(u"Parametro de enlace 3 de la clase no encontrado")
                        if not 'dia' in request.POST:
                            raise NameError(u"Parametro de día de la clase no encontrado")
                        if not 'num_semana' in request.POST:
                            raise NameError(u"Parametro de numero de la semana de la clase no encontrado")
                        if not 'fecha_subida' in request.POST:
                            raise NameError(u"Parametro de fecha de la clase no encontrado")
                        if not request.POST['link_1']:
                            raise NameError(u"Enlace de la grabación 1 es obligatorio")
                        idc = int(encrypt(request.POST['idc']))
                        link_1 = request.POST['link_1']
                        link_2 = request.POST['link_2']
                        link_3 = request.POST['link_3']
                        dia = request.POST['dia']
                        num_semana = request.POST['num_semana']
                        fecha_subida = request.POST['fecha_subida']
                        clase = Clase.objects.get(pk=idc)
                        leccion = Leccion.objects.filter(clase=clase, fecha=fecha_subida).values('id')
                        if not leccion.exists():
                            raise NameError(u"No existe lección para la clase, debe registrar la clase en el módulo de Registro de asistencias por diferido")
                        materia = clase.materia
                        coordinacion = materia.coordinacion()
                        modalidad = materia.asignaturamalla.malla.modalidad
                        if materia.modeloevaluativo_id in [27,64] and materia.asignaturamalla.transversal:
                            modalidad = Modalidad.objects.get(id=3)
                        num_semana_actual = datetime.now().isocalendar()[1]
                        es_diferido = num_semana_actual != int(num_semana)
                        if coordinacion is None:
                            raise NameError(u"Clase no tiene coordinación configurada")
                        if not coordinacion.id in [1, 2, 3, 4, 5, 9, 7, 10, 12]:
                            raise NameError(u"Coordinación: %s no esta configurada en horario" % coordinacion.__str__())
                        if coordinacion.id in [1, 2, 3, 4, 5, 12]:
                            if clase.tipohorario == 1:
                                raise NameError(u"Clase de tipo presencial no se sube video")
                            elif clase.tipohorario in [2, 7, 8, 9]:
                                if modalidad:
                                    if modalidad.id in [1, 2]:
                                        if clase.tipohorario in [2, 8]:
                                            CrearClaseVirtualClaseMoodleDiferido(idc, persona, link_1, link_2, link_3, dia, num_semana, fecha_subida)
                                    elif modalidad.id in [3]:
                                        if clase.tipohorario in [2, 8]:
                                            CrearClaseSincronicaMoodleDiferido(idc, persona, link_1, link_2, link_3, dia, num_semana, fecha_subida)
                                        elif clase.tipohorario in [7, 9]:
                                            CrearClaseAsincronicaMoodleDiferido(idc, persona, link_1, link_2, link_3, dia, num_semana, fecha_subida)
                        elif coordinacion.id in [9]:
                            # CrearClaseVirtualClaseMoodleDiferido(idc, persona, link_1, link_2, link_3, dia, num_semana, fecha_subida)
                            if clase.tipohorario == 1:
                                raise NameError(u"Clase de tipo presencial no se sube video")
                            elif clase.tipohorario in [2, 7, 8, 9]:
                                if clase.tipohorario in [2, 8]:
                                    CrearClaseSincronicaMoodleDiferido(idc, persona, link_1, link_2, link_3, dia, num_semana, fecha_subida)
                                elif clase.tipohorario in [7, 9]:
                                    CrearClaseAsincronicaMoodleDiferido(idc, persona, link_1, link_2, link_3, dia, num_semana, fecha_subida)
                        elif coordinacion.id in [7, 10]:
                            CrearClaseVirtualClaseMoodleDiferido(idc, persona, link_1, link_2, link_3, dia, num_semana, fecha_subida)
                        return JsonResponse({"result": "ok", "mensaje": u"Se subio correctamente la información de la clase"})
                    except Exception as ex:
                        transaction.set_rollback(True)
                        return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos. %s" % ex.__str__()})
            elif action == 'editVideoVirtual':
                with transaction.atomic():
                    try:
                        from Moodle_Funciones import EditarClaseAsincronicaMoodleDiferido, EditarClaseSincronicaMoodleDiferido
                        if not 'idca' in request.POST:
                            raise NameError(u"Parametro de clase de video no encontrado")
                        if not 'fecha' in request.POST:
                            raise NameError(u"Parametro de fecha no encontrado")
                        if not 'idc' in request.POST:
                            raise NameError(u"Parametro de clase no encontrado")
                        if not 'link_1' in request.POST:
                            raise NameError(u"Parametro de enlace 1  de la clase no encontrado")
                        if not 'link_2' in request.POST:
                            raise NameError(u"Parametro de enlace 2 de la clase no encontrado")
                        if not 'link_3' in request.POST:
                            raise NameError(u"Parametro de enlace 3 de la clase no encontrado")
                        idc = int(encrypt(request.POST['idc']))
                        link_1 = request.POST['link_1']
                        link_2 = request.POST['link_2']
                        link_3 = request.POST['link_3']
                        idca = int(encrypt(request.POST['idca']))
                        fecha = request.POST['fecha']
                        clase = Clase.objects.get(pk=idc)
                        obj = None
                        leccion = Leccion.objects.filter(clase=clase, fecha=fecha).exists()
                        if not leccion:
                            raise NameError(u"No existe lección para la clase, debe registrar la clase en el módulo de Registro de asistencias por diferido")
                        materia = clase.materia
                        coordinacion = materia.coordinacion()
                        modalidad = materia.asignaturamalla.malla.modalidad
                        if materia.modeloevaluativo_id in [27,64] and materia.asignaturamalla.transversal:
                            modalidad = Modalidad.objects.get(id=3)
                        if not coordinacion:
                            raise NameError(u"Clase no tiene coordinación configurada")
                        if not coordinacion.id in [1, 2, 3, 4, 5, 9, 7, 10, 12]:
                            raise NameError(u"Coordinación: %s no esta configurada en horario" % coordinacion.__str__())
                        if coordinacion.id in [1, 2, 3, 4, 5, 12]:
                            if clase.tipohorario == 1:
                                raise NameError(u"Clase de tipo presencial no se sube video")
                            elif clase.tipohorario in [2, 7]:
                                if modalidad:
                                    if modalidad.id in [1, 2]:
                                        if clase.tipohorario in [2]:
                                            obj = EditarClaseSincronicaMoodleDiferido(idca, idc, link_1, link_2, link_3)
                                    elif modalidad.id in [3]:
                                        if clase.tipohorario in [2]:
                                            obj = EditarClaseSincronicaMoodleDiferido(idca, idc, link_1, link_2, link_3)
                                        elif clase.tipohorario in [7]:
                                            obj = EditarClaseAsincronicaMoodleDiferido(idca, idc, link_1, link_2, link_3)
                        elif coordinacion.id in [9]:
                            if clase.tipohorario == 1:
                                raise NameError(u"Clase de tipo presencial no se sube video")
                            elif clase.tipohorario in [2, 7]:
                                if clase.tipohorario in [2]:
                                    obj = EditarClaseSincronicaMoodleDiferido(idca, idc, link_1, link_2, link_3)
                                elif clase.tipohorario in [7]:
                                    obj = EditarClaseAsincronicaMoodleDiferido(idca, idc, link_1, link_2, link_3)
                        if not obj:
                                raise NameError(u"No se pudo actualizar la clase")
                        return JsonResponse({"result": "ok", "mensaje": u"Se subio correctamente la información de la clase"})
                    except Exception as ex:
                        transaction.set_rollback(True)
                        return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos. %s" % ex.__str__()})

            elif action == 'editclass':
                with transaction.atomic():
                    try:
                        if not 'idca' in request.POST:
                            raise NameError(u"Parametro de clase de video no encontrado")
                        if not 'idc' in request.POST:
                            raise NameError(u"Parametro de clase no encontrado")
                        if not 'fecha' in request.POST:
                            raise NameError(u"Parametro de fecha no encontrado")
                        idc = int(encrypt(request.POST['idc']))
                        idca = int(encrypt(request.POST['idca']))
                        fecha = request.POST['fecha']
                        clase = Clase.objects.get(pk=idc)
                        leccion = Leccion.objects.filter(clase=clase, fecha=fecha).values('id')
                        if not leccion.exists():
                            raise NameError(u"No existe lección para la clase, debe registrar la clase en el módulo de Registro de asistencias por diferido")
                        materia = clase.materia
                        coordinacion = materia.coordinacion()
                        modalidad = materia.asignaturamalla.malla.modalidad
                        obj = None
                        if materia.modeloevaluativo_id in [27,64] and materia.asignaturamalla.transversal:
                            modalidad = Modalidad.objects.get(id=3)
                        if not coordinacion:
                            raise NameError(u"Clase no tiene coordinación configurada")
                        if not coordinacion.id in [1, 2, 3, 4, 5, 9, 7, 10, 12]:
                            raise NameError(u"Coordinación: %s no esta configurada en horario" % coordinacion.__str__())
                        if coordinacion.id in [1, 2, 3, 4, 5, 12]:
                            if clase.tipohorario == 1:
                                raise NameError(u"Clase de tipo presencial no se sube video")
                            elif clase.tipohorario in [2, 7]:
                                if modalidad:
                                    if modalidad.id in [1, 2]:
                                        if clase.tipohorario in [2]:
                                            obj = ClaseSincronica.objects.get(id=idca)
                                    elif modalidad.id in [3]:
                                        if clase.tipohorario in [2]:
                                            obj = ClaseSincronica.objects.get(id=idca)
                                        elif clase.tipohorario in [7]:
                                            obj = ClaseAsincronica.objects.get(id=idca)
                        elif coordinacion.id in [9]:
                            if clase.tipohorario == 1:
                                raise NameError(u"Clase de tipo presencial no se sube video")
                            elif clase.tipohorario in [2, 7]:
                                if clase.tipohorario in [2]:
                                    obj = ClaseSincronica.objects.get(id=idca)
                                elif clase.tipohorario in [7]:
                                    obj = ClaseAsincronica.objects.get(id=idca)
                        if not obj:
                            raise NameError(u"La clase no existe")
                        return JsonResponse({"result": "ok", "obj": {'enlace1': obj.enlaceuno, 'enlace2': obj.enlacedos, 'enlace3': obj.enlacetres}})
                    except Exception as ex:
                        transaction.set_rollback(True)
                        return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos. %s" % ex.__str__()})

            elif action == 'viewAsistenciaObservaciones':
                try:
                    if not 'type' in request.POST:
                        raise NameError(u"Parametro de tipo no encontrado")

                    if not 'id' in request.POST:
                        raise NameError(u"Parametro de asistencia no encontrado")

                    if not AsistenciaLeccion.objects.values("id").filter(pk=int(request.POST['id'])).exists():
                        raise NameError(u"Asistencia no encontrada")
                    asistencia = AsistenciaLeccion.objects.get(pk=int(request.POST['id']))
                    data['asistencia'] = asistencia
                    data['type'] = request.POST['type']
                    template = get_template("pro_clases/view_observaciones.html")
                    json_content = template.render(data)
                    return JsonResponse({"result": "ok", "html": json_content})
                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos. %s" % ex.__str__()})

            elif action == 'saveAsistenciaObservacion':
                with transaction.atomic():
                    try:
                        if not 'type' in request.POST:
                            raise NameError(u"Parametro de tipo no encontrado")
                        if not 'ida' in request.POST:
                            raise NameError(u"Parametro de asistencia no encontrado")
                        if not 'ido' in request.POST:
                            raise NameError(u"Parametro de observacion no encontrado")

                        if texto := request.POST.get('observacion', '').strip():
                            ido = int(request.POST.get('ido', 0))
                            if not AsistenciaLeccion.objects.values("id").filter(pk=int(request.POST['ida'])).exists():
                                raise NameError(u"Asistencia no encontrada")
                            asistencia = AsistenciaLeccion.objects.get(pk=int(request.POST['ida']))
                            # NUEVO
                            if ido == 0:
                                observacion = AsistenciaLeccionObservacion(asistencia=asistencia,
                                                                           observacion=texto,
                                                                           fecha=datetime.now().date(),
                                                                           hora=datetime.now().time())
                                observacion.save(request)
                                log(u'Se agrego observación a la asistencia: %s' % observacion, request, "add")
                            else:
                                # Editar
                                if not AsistenciaLeccionObservacion.objects.values("id").filter(pk=ido).exists():
                                    raise NameError(u"Observación de asistencia no encontrada")
                                observacion = AsistenciaLeccionObservacion.objects.get(pk=ido)
                                observacion.observacion = texto
                                observacion.save(request, update_fields=['observacion'])
                                log(u'Se edito observación a la asistencia: %s' % observacion, request, "edit")
                        else:
                            raise NameError(u"Parametro del texto de la observacion no encontrado")

                        data['asistencia'] = asistencia
                        data['type'] = request.POST['type']
                        template = get_template("pro_clases/view_observaciones.html")
                        json_content = template.render(data)
                        num_observaciones = asistencia.num_observacion()
                        return JsonResponse({"result": "ok", "mensaje": u"Se guardo correctamente la observación", "html": json_content, "num_observaciones": num_observaciones})
                    except Exception as ex:
                        transaction.set_rollback(True)
                        return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos. %s" % ex.__str__()})

            elif action == 'deleteAsistenciaObservacion':
                with transaction.atomic():
                    try:
                        if not 'type' in request.POST:
                            raise NameError(u"Parametro de tipo no encontrado")
                        if not 'ida' in request.POST:
                            raise NameError(u"Parametro de asistencia no encontrado")
                        if not 'ido' in request.POST:
                            raise NameError(u"Parametro de observacion no encontrado")
                        ido = int(request.POST.get('ido', 0))
                        if not AsistenciaLeccion.objects.values("id").filter(pk=int(request.POST['ida'])).exists():
                            raise NameError(u"Asistencia no encontrada")
                        asistencia = AsistenciaLeccion.objects.get(pk=int(request.POST['ida']))
                        if not AsistenciaLeccionObservacion.objects.values("id").filter(pk=ido).exists():
                            raise NameError(u"Observación de asistencia no encontrada")
                        observacion = AsistenciaLeccionObservacion.objects.get(pk=ido)
                        d = observacion
                        observacion.delete()
                        log(u'Se elimino observación a la asistencia: %s' % d, request, "del")
                        data['asistencia'] = asistencia
                        data['type'] = request.POST['type']
                        template = get_template("pro_clases/view_observaciones.html")
                        json_content = template.render(data)
                        num_observaciones = asistencia.num_observacion()
                        return JsonResponse({"result": "ok", "mensaje": u"Se elimino correctamente la observación", "html": json_content, "num_observaciones": num_observaciones})
                    except Exception as ex:
                        transaction.set_rollback(True)
                        return JsonResponse({"result": "bad", "mensaje": u"Error al eliminar el dato. %s" % ex.__str__()})

            elif action == 'DeleteclassAsynchronous':
                with transaction.atomic():
                    try:
                        puede_realizar_accion(request, 'sga.puede_eliminar_link_clase_sincronica_asincronica_docente')
                        if not 'id' in request.POST:
                            raise NameError(u"Parametro de asincrónica no encontrado")
                        clase = ClaseAsincronica.objects.get(pk=int(encrypt(request.POST['id'])))
                        clase.status = False
                        clase.save(request, update_fields=['status'])
                        log(u'Elimino clase asincrónica: %s' % clase, request, "del")
                        return JsonResponse({"result": "ok"})
                    except Exception as ex:
                        transaction.set_rollback(True)
                        return JsonResponse({"result": "bad", "mensaje": u"Error al eliminar el dato. %s" % ex.__str__()})

            elif action == 'DeleteclassSynchronous':
                with transaction.atomic():
                    try:
                        puede_realizar_accion(request, 'sga.puede_eliminar_link_clase_sincronica_asincronica_docente')
                        if not 'id' in request.POST:
                            raise NameError(u"Parametro de clase sincrónica no encontrado")
                        clase = ClaseSincronica.objects.get(pk=int(encrypt(request.POST['id'])))
                        clase.status = False
                        clase.save(request, update_fields=['status'])
                        log(u'Elimino clase sincrónica: %s' % clase, request, "del")
                        return JsonResponse({"result": "ok"})
                    except Exception as ex:
                        transaction.set_rollback(True)
                        return JsonResponse({"result": "bad", "mensaje": u"Error al eliminar el dato. %s" % ex.__str__()})

            elif action == 'edit-actuacion-clase':
                try:
                    eval = EvaluacionLeccion.objects.get(id=request.POST['id'])
                    eval.evaluacion  = float(request.POST['val'])
                    eval.observacion = request.POST.get('obs', '').strip()
                    eval.save(request)

                    asistencia = AsistenciaLeccion.objects.get(id=request.POST['ida'])
                    return JsonResponse({'result': 'ok', 'promedio': asistencia.promedio_evaluacion()})
                except Exception as ex:
                    return JsonResponse({'result': 'bad', 'mensaje': ex.__str__()})

            elif action == 'del-actuacion-clase':
                try:
                    eval = EvaluacionLeccion.objects.get(id=request.POST['id'])
                    eval.delete()

                    asistencia = AsistenciaLeccion.objects.get(id=request.POST['ida'])
                    return JsonResponse({'result': 'ok', 'promedio': asistencia.promedio_evaluacion()})
                except Exception as ex:
                    return JsonResponse({'result': 'bad', 'mensaje': ex.__str__()})

            elif action == 'download-log-marcadas':
                try:
                    from xhtml2pdf import pisa

                    html = request.POST['html']

                    # Crea un buffer de bytes para recibir el PDF
                    pdf_buffer = io.BytesIO()

                    # Usa pisa para convertir el HTML a PDF
                    pisa_status = pisa.CreatePDF(io.StringIO(html), dest=pdf_buffer)

                    if pisa_status.err:
                        raise NameError('Hubo un error al generar el PDF')

                    # Obtén el contenido del PDF desde el buffer
                    pdf_buffer.seek(0)
                    pdf = pdf_buffer.getvalue()
                    pdf_buffer.close()

                    response = HttpResponse(pdf, content_type='application/pdf')
                    response['Content-Disposition'] = f"attachment; filename=archivo_log_marcadas.pdf"
                    return response
                except Exception as ex:
                    return HttpResponse(ex.__str__(), status=400)


        return JsonResponse({"result": "bad", "mensaje": u"Solicitud Incorrecta."})
    else:

        if 'action' in request.GET:
            action = request.GET['action']

            if action == 'view-actuaciones':
                try:
                    data['asistencia'] = asistencia = AsistenciaLeccion.objects.get(pk=request.GET['id'])
                    data['actuaciones'] = EvaluacionLeccion.objects.filter(leccion=asistencia.leccion, materiaasignada=asistencia.materiaasignada, status=True)
                    data['puede_editar_actuaciones'] = request.GET.get('type', 1) == '2'
                    template = get_template("pro_clases/view-actuaciones.html")
                    json_content = template.render(data)
                    return JsonResponse({"result": "ok", "html": json_content})
                except Exception as ex:
                    pass

            if action == 'view':
                try:
                    data['title'] = u'Asistencias de la clase'
                    now = datetime.now()
                    data['lecciongrupo'] = lecciongrupo = LeccionGrupo.objects.db_manager("sga_select").get(pk=request.GET['id'])
                    if 'idl' in request.GET:
                        lecciones = lecciongrupo.leccion_segun_id(int(encrypt(request.GET['idl'])))
                    else:
                        lecciones = lecciongrupo.lecciones.db_manager("sga_select").all()
                    data['lecciones'] = lecciones
                    data['tiposincidencias'] = TipoIncidencia.objects.db_manager("sga_select").all()
                    data['incidencias'] = lecciongrupo.incidencia_set.db_manager("sga_select").all()
                    if lecciongrupo.archivo_set.exists():
                        data['deber'] = lecciongrupo.archivo_set.db_manager("sga_select").all()[0]
                    else:
                        data['deber'] = None
                    data['incluyedatos'] = DATOS_ESTRICTO
                    data['incluyedatosmedicos'] = FICHA_MEDICA_ESTRICTA
                    # data['clases_horario_estricto'] = CLASES_HORARIO_ESTRICTO
                    data['clases_horario_estricto'] = ePeriodoAcademia.valida_clases_horario_estricto
                    data['pagoestricto'] = PAGO_ESTRICTO
                    data['cuota1_obligatoria'] = PAGO_OBLIGATORIO_PRIMERACUOTA
                    data['verfoto'] = VER_FOTO_LECCION
                    data['usa_planificacion'] = USA_PLANIFICACION
                    data['asistencia_en_grupo'] = ASISTENCIA_EN_GRUPO
                    clase = lecciones[0].clase
                    data['clase'] = clase
                    url = None
                    if clase.materia.tieneurlwebex(clase.profesor):
                        url = f"https://unemi.webex.com/meet/{clase.profesor.persona.usuario}"
                    elif clase.profesor.urlzoom:
                        url = clase.profesor.urlzoom
                    data['url'] = url
                    data['turno'] = clase.turno
                    data['materia'] = materia = clase.materia
                    data['idl'] = lecciones[0].id
                    fecha = lecciones[0].fecha
                    mensaje = ""
                    data['mensaje'] = mensaje
                    data['abierta'] = lecciones[0].abierta
                    contar_llenos = 0
                    data['key_room'] = key_room = f'{lecciongrupo.turno.id}{lecciongrupo.profesor.id}{lecciongrupo.dia}{lecciongrupo.fecha.strftime("%d%m%Y")}' if ePeriodoAcademia.utiliza_asistencia_ws else ""
                    data['ePeriodoAcademia'] = ePeriodoAcademia
                    utiliza_zoom = True
                    if ePeriodoAcademia.valida_asistencia_in_home and not tiene_solicitud_apertura_clase:
                        if clase.aula and clase.aula.bloque and clase.aula.bloque.in_home:
                            utiliza_zoom = inhouse_check(request, valida_clase=True)
                    data['utiliza_zoom'] = utiliza_zoom
                    data['contar_llenos'] = contar_llenos
                    data['DEBUG'] = DEBUG
                    data['autorizado_clase_virtual'] = profesor.solicitudaperturaclasevirtual_set.filter(status=True, estadosolicitud=2, periodo=periodo).exists() or variable_valor('TODAS_LAS_CLASES_VIRTUALES')
                    puede_registrar_temas = True
                    if clase.tipoprofesor and clase.tipoprofesor.pk == 2:
                        puede_registrar_temas = materia.profesormateria_set.filter(profesor__persona=persona, tipoprofesor=1, activo=True, status=True).exists()
                    data['silabosemanal'] = SilaboSemanal.objects.filter(silabo__materia=materia, fechainiciosemana__lte=fecha, fechafinciosemana__gte=fecha, status=True).first()
                    if variable_valor('VERSION_REGISTRO_ASISTENCIA') == 2:
                        data['puede_registrar_temas'] = puede_registrar_temas
                        data['temas'] = TemaAsistencia.objects.values_list('tema_id', flat=True).filter(leccion__clase__materia=materia, status=True).order_by('tema__temaunidadresultadoprogramaanalitico__orden').distinct()
                        data['subtemas'] = SubTemaAsistencia.objects.values_list('subtema_id', flat=True).filter(tema__leccion__clase__materia=materia, status=True).order_by('subtema__subtemaunidadresultadoprogramaanalitico__orden').distinct()
                        data['leccion'] = lecciongrupo.lecciones.filter(clase_id=clase).first()
                        return render(request, "pro_clases/leccion_v2.html", data)
                    return render(request, "pro_clases/leccion.html", data)
                except Exception as ex:
                    return HttpResponseRedirect(f"{request.path}?info={ex.__str__()}")

            elif action == 'cerrarclaseindividual':
                try:
                    data['title'] = u'Cerrar clase'
                    data['leccion'] = Leccion.objects.get(pk=int(encrypt(request.GET['id'])))
                    return render(request, "niveles/confirmarcerrarclaseindividual.html", data)
                except Exception as ex:
                    pass

            elif action == 'adddeberes':
                try:
                    data['title'] = u'Adicionar deberes'
                    data['lecciongrupo'] = LeccionGrupo.objects.get(pk=request.GET['id'])
                    data['form'] = ArchivoDeberForm(initial={'nombre': 'Deber leccion'})
                    return render(request, "pro_clases/adddeberes.html", data)
                except Exception as ex:
                    pass

            elif action == 'contenidoacademico':
                try:
                    data['title'] = u'Contenido academico'
                    data['leccion'] = leccion = Leccion.objects.get(pk=int(encrypt(request.GET['id'])))
                    data['lecciongrupo'] = leccion.leccion_grupo()
                    # data['form'] = ContenidoAcademicoForm(initial={'contenido': leccion.contenido,
                    #                                                'estrategiasmetodologicas': leccion.estrategiasmetodologicas,
                    #                                                'observaciones': leccion.observaciones})
                    return render(request, "pro_clases/editarcontenidoacademico.html", data)
                except Exception as ex:
                    pass

            elif action == 'deldeber':
                with transaction.atomic():
                    try:
                        lecciongrupo = LeccionGrupo.objects.get(pk=request.GET['id'])
                        archivo = Archivo.objects.filter(lecciongrupo=lecciongrupo)
                        log(u'Elimino deber de clase: %s' % lecciongrupo, request, "del")
                        archivo.delete()
                    except Exception as ex:
                        transaction.set_rollback(True)
                        pass
                return HttpResponseRedirect("/pro_clases?action=view&id=" + request.GET['id'])

            # elif action == 'delleccion':
            #     try:
            #         data['title'] = u'Eliminar lección'
            #         data['lecciongrupo'] = LeccionGrupo.objects.get(pk=request.GET['id'])
            #         return render(request, "pro_clases/delleccion.html", data)
            #     except Exception as ex:
            #         pass

            elif action == 'delleccion':
                try:
                    data['title'] = u'Eliminar lección'
                    data['leccion'] = Leccion.objects.get(pk=request.GET['id'])
                    return render(request, "pro_clases/delleccionclase.html", data)
                except Exception as ex:
                    pass

            elif action == 'detalle_clases':
                try:
                    data['title'] = u'Detalle clases sincrónicas y asincrónicas'
                    data['hoy'] = hoy = datetime.now().date()
                    listaasistencias = []
                    cursor = connections['default'].cursor()
                    sql = "select distinct ten.codigoclase,ten.dia,ten.turno_id,ten.inicio,ten.fin,ten.materia_id,ten.tipohorario, " \
                          "ten.horario,ten.rangofecha, " \
                          "ten.rangodia,sincronica.fecha as sincronica,asincronica.fechaforo as asincronica, asignatura, paralelo,asincronica.idforomoodle as idforomoodle,ten.comienza,ten.termina,nolaborables.fecha,nolaborables.observaciones,ten.nivelmalla,ten.idnivelmalla,ten.idcarrera,ten.idcoordinacion " \
                          "from ( " \
                          "select distinct cla.id as codigoclase, " \
                          "cla.dia,cla.turno_id,cla.inicio,cla.fin,cla.materia_id, " \
                          "cla.tipohorario, " \
                          "case " \
                          "WHEN cla.tipohorario in(2,8)  THEN 2 " \
                          "WHEN cla.tipohorario in(7,9)  THEN 7 " \
                          "end as horario, " \
                          "CURRENT_DATE + generate_series(cla.inicio- CURRENT_DATE, cla.fin - CURRENT_DATE ) as rangofecha, " \
                          "EXTRACT (isodow  FROM  CURRENT_DATE + generate_series(cla.inicio- CURRENT_DATE, cla.fin - CURRENT_DATE )) as rangodia,asig.nombre as asignatura, mate.paralelo as paralelo,tur.comienza,tur.termina,nimalla.nombre as nivelmalla,nimalla.id as idnivelmalla,malla.carrera_id as idcarrera,coorcar.coordinacion_id as idcoordinacion " \
                          "from sga_clase cla , sga_materia mate, sga_asignaturamalla asimalla,sga_asignatura asig,sga_turno tur,sga_nivel niv,sga_nivelmalla nimalla,sga_malla malla,sga_carrera carre, sga_coordinacion_carrera coorcar " \
                          "where cla.profesor_id=" + str(profesor.id) + " and cla.materia_id = mate.id and mate.asignaturamalla_id = asimalla.id and asimalla.malla_id=malla.id and asimalla.asignatura_id = asig.id and cla.turno_id=tur.id and asimalla.nivelmalla_id=nimalla.id and malla.carrera_id=carre.id and coorcar.carrera_id=carre.id " \
                                                                        "AND cla.tipohorario IN (8, 9, 2, 7) and mate.nivel_id=niv.id and niv.periodo_id=" + str(periodo.id) + "  " \
                                                                                                                                                                               ") as ten " \
                                                                                                                                                                               "left join " \
                                                                                                                                                                               "( " \
                                                                                                                                                                               "select clas.materia_id,asi.fecha_creacion::timestamp::date as fecha,asi.fecha_creacion as fecharegistro " \
                                                                                                                                                                               "from sga_clasesincronica asi, sga_clase clas " \
                                                                                                                                                                               "where asi.clase_id=clas.id and clas.profesor_id=" + str(profesor.id) + " " \
                                                                                                                                                                                                                                                       ") as sincronica on ten.rangofecha=fecha and ten.horario=2 " \
                                                                                                                                                                                                                                                       "left join " \
                                                                                                                                                                                                                                                       "( " \
                                                                                                                                                                                                                                                       "select  clas.materia_id,asi.fechaforo,asi.idforomoodle " \
                                                                                                                                                                                                                                                       "from sga_claseasincronica asi, sga_clase clas " \
                                                                                                                                                                                                                                                       "where asi.clase_id=clas.id " \
                                                                                                                                                                                                                                                       ") as asincronica on asincronica.materia_id=ten.materia_id and ten.rangofecha=asincronica.fechaforo and ten.horario=7 " \
                                                                                                                                                                                                                                                       "left join " \
                                                                                                                                                                                                                                                       "(select nolab.observaciones, nolab.fecha from sga_diasnolaborable nolab " \
                                                                                                                                                                                                                                                       "where nolab.periodo_id=" + str(periodo.id) + ") as nolaborables on nolaborables.fecha = ten.rangofecha " \
                                                                                                                                                                                                                                                                                                     "where ten.dia=ten.rangodia and ten.rangofecha <='"+ str(hoy) +"' order by ten.rangofecha,materia_id,ten.turno_id,tipohorario"
                    cursor.execute(sql)
                    results = cursor.fetchall()
                    totalsincronica = 0
                    totalasincronica = 0
                    totalplansincronica = 0
                    totalplanasincronica = 0
                    for cuentamarcadas in results:
                        sinasistencia = False
                        if periodo.diasnolaborable_set.filter(coordinacion_id=cuentamarcadas[22],carrera_id=cuentamarcadas[21],nivelmalla_id=cuentamarcadas[20], status=True).exists():
                            if periodo.diasnolaborable_set.filter(coordinacion_id=cuentamarcadas[22],carrera_id=cuentamarcadas[21],nivelmalla_id=cuentamarcadas[20], fecha=cuentamarcadas[8], status=True).exists():
                                sinasistencia = True
                        else:
                            if periodo.diasnolaborable_set.filter(coordinacion_id=cuentamarcadas[22], carrera_id=cuentamarcadas[21], nivelmalla_id__isnull=True, status=True).exists():
                                if periodo.diasnolaborable_set.filter(coordinacion_id=cuentamarcadas[22], carrera_id=cuentamarcadas[21], nivelmalla_id__isnull=True, fecha=cuentamarcadas[8], status=True).exists():
                                    sinasistencia = True
                            else:
                                if periodo.diasnolaborable_set.filter(coordinacion_id=cuentamarcadas[22], carrera_id__isnull=True, nivelmalla_id__isnull=True, status=True).exists():
                                    if periodo.diasnolaborable_set.filter(coordinacion_id=cuentamarcadas[22], carrera_id__isnull=True, nivelmalla_id__isnull=True, fecha=cuentamarcadas[8], status=True).exists():
                                        sinasistencia = True
                                else:
                                    if periodo.diasnolaborable_set.filter(coordinacion_id__isnull=True, carrera_id__isnull=True, nivelmalla_id__isnull=True, status=True).exists():
                                        if periodo.diasnolaborable_set.filter(coordinacion_id__isnull=True, carrera_id__isnull=True, nivelmalla_id__isnull=True, fecha=cuentamarcadas[8], status=True).exists():
                                            sinasistencia = True
                        listaasistencias.append([cuentamarcadas[0], cuentamarcadas[1], cuentamarcadas[2], cuentamarcadas[3],
                                                 cuentamarcadas[4], cuentamarcadas[5], cuentamarcadas[6], cuentamarcadas[7],
                                                 cuentamarcadas[8], cuentamarcadas[9], cuentamarcadas[10], cuentamarcadas[11],
                                                 cuentamarcadas[12], cuentamarcadas[13], cuentamarcadas[14], cuentamarcadas[15],
                                                 cuentamarcadas[16], cuentamarcadas[17], cuentamarcadas[18], cuentamarcadas[19],
                                                 sinasistencia])


                        if cuentamarcadas[7] == 2:
                            totalsincronica += 1
                        if cuentamarcadas[7] == 7:
                            totalasincronica += 1
                        # if cuentamarcadas[10]:
                        #     totalplansincronica += 1
                        totalplansincronica += 1
                        if cuentamarcadas[11]:
                            totalplanasincronica += 1
                    data['listaasistencias'] = listaasistencias
                    data['totalsincronica'] = totalsincronica
                    data['totalasincronica'] = totalasincronica
                    data['totalplansincronica'] = totalplansincronica
                    data['totalplanasincronica'] = totalplanasincronica
                    # data['procentajesincronica'] = (totalplansincronica * 100) / totalsincronica
                    # data['procentajeasincronica'] = (totalplanasincronica * 100) / totalasincronica
                    data['profesor'] = profesor
                    return render(request, "pro_clases/detalleclases.html", data)
                except Exception as ex:
                    pass

            # elif action == 'detalle_clasesvideo_old':
            #     try:
            #         data['title'] = u'Detalle clases sincrónicas y asincrónicas'
            #         data['hoy'] = hoy = datetime.now().date()
            #         listaasistencias = []
            #         cursor = connections['default'].cursor()
            #         sql = f"""
            #             SELECT DISTINCT
            #                 ten.codigoclase, ten.dia, ten.turno_id,
            #                 ten.inicio, ten.fin, ten.materia_id,
            #                 ten.tipohorario, ten.horario, ten.rangofecha,
            #                 ten.rangodia, sincronica.fecha AS sincronica, asincronica.fechaforo AS asincronica,
            #                 asignatura, paralelo,
            #                 CASE
            #                     WHEN asincronica.idforomoodle IS NOT  NULL THEN asincronica.idforomoodle
            #                     ELSE sincronica.idforomoodle
            #                 END  idforomoodle, ten.comienza, ten.termina,
            #                 nolaborables.fecha, nolaborables.observaciones, ten.nivelmalla,
            #                 ten.idnivelmalla, ten.idcarrera, ten.idcoordinacion,
            #                 ten.tipoprofesor_id,EXTRACT(week FROM ten.rangofecha::date) AS numerosemana,ten.tipoprofesor
            #             FROM ( SELECT DISTINCT
            #                         cla.tipoprofesor_id,cla.id AS	codigoclase,
            #                         cla.dia,cla.turno_id,cla.inicio,cla.fin,cla.materia_id, cla.tipohorario,
            #                         CASE WHEN cla.tipohorario IN(2,8)  THEN 2 WHEN cla.tipohorario in(7,9)  THEN 7 END AS horario,
            #                         CURRENT_DATE + GENERATE_SERIES(cla.inicio- CURRENT_DATE, cla.fin - CURRENT_DATE ) AS rangofecha,
            #                         EXTRACT (isodow  FROM  CURRENT_DATE + GENERATE_SERIES(cla.inicio- CURRENT_DATE,
            #                         cla.fin - CURRENT_DATE )) AS rangodia,asig.nombre AS asignatura, mate.paralelo AS paralelo,
            #                         tur.comienza,tur.termina,nimalla.nombre AS nivelmalla,nimalla.id AS idnivelmalla,
            #                         malla.carrera_id AS idcarrera,coorcar.coordinacion_id AS idcoordinacion,
            #                         tipro.nombre AS tipoprofesor
            #                     FROM sga_clase cla , sga_materia mate,
            #                      sga_asignaturamalla asimalla,sga_asignatura asig,
            #                      sga_turno tur,sga_nivel niv,sga_nivelmalla nimalla,
            #                      sga_malla malla,sga_carrera carre,
            #                      sga_coordinacion_carrera coorcar,
            #                      sga_tipoprofesor tipro
            #                     WHERE
            #                         cla.profesor_id={profesor.id} AND
            #                         cla.materia_id = mate.id AND mate.asignaturamalla_id = asimalla.id AND
            #                         asimalla.malla_id=malla.id AND asimalla.asignatura_id = asig.id AND
            #                         cla.turno_id=tur.id AND asimalla.nivelmalla_id=nimalla.id AND
            #                         malla.carrera_id=carre.id AND	 coorcar.carrera_id=carre.id AND
            #                         cla.tipohorario IN (8, 9, 2, 7) AND mate.nivel_id=niv.id AND
            #                         cla.activo=True AND cla.tipoprofesor_id=tipro.id AND niv.periodo_id={periodo.id}) AS ten
            #                 LEFT JOIN(  SELECT
            #                                 clas.id  clase_id, clas.materia_id,asi.fecha_creacion::timestamp::date AS fecha, clas.tipoprofesor_id,
            #                                 asi.fecha_creacion AS fecharegistro, asi.fechaforo AS fechaforo, asi.idforomoodle idforomoodle
            #                             FROM sga_clasesincronica asi, sga_clase clas
            #                             WHERE asi.clase_id=clas.id AND asi.status=true AND clas.profesor_id={profesor.id}) AS sincronica
            #                     ON (ten.rangofecha=fechaforo AND ten.horario=2 AND sincronica.materia_id=ten.materia_id  AND sincronica.tipoprofesor_id=ten.tipoprofesor_id)OR
            #                        (sincronica.materia_id=ten.materia_id AND sincronica.fechaforo=ten.rangofecha AND EXTRACT(dow from  sincronica.fechaforo)=ten.rangodia AND sincronica.tipoprofesor_id=ten.tipoprofesor_id)
            #                 LEFT JOIN(  SELECT
            #                                 clas.id  clase_id,  clas.materia_id,asi.fechaforo,asi.idforomoodle, clas.tipoprofesor_id
            #                             FROM sga_claseasincronica asi, sga_clase clas
            #                             WHERE asi.clase_id=clas.id AND asi.status=true) AS asincronica
            #                     ON (asincronica.materia_id=ten.materia_id AND ten.rangofecha=asincronica.fechaforo AND	ten.horario=2  AND asincronica.tipoprofesor_id=ten.tipoprofesor_id)OR
            #                         (asincronica.materia_id=ten.materia_id  AND	 asincronica.fechaforo=ten.rangofecha AND  EXTRACT(dow from  asincronica.fechaforo)=ten.rangodia AND asincronica.tipoprofesor_id=ten.tipoprofesor_id)
            #                 LEFT JOIN (SELECT
            #                             nolab.observaciones, nolab.fecha
            #                             FROM sga_diasnolaborable nolab
            #                             WHERE nolab.periodo_id={periodo.id}) AS nolaborables ON nolaborables.fecha = ten.rangofecha
            #             WHERE
            #                 ten.dia=ten.rangodia AND
            #                 ten.rangofecha <'{hoy}'
            #             ORDER BY ten.rangofecha,materia_id,ten.turno_id,tipohorario
            #         """
            #         cursor.execute(sql)
            #         results = cursor.fetchall()
            #         totalsincronica = 0
            #         totalasincronica = 0
            #         totalplansincronica = 0
            #         totalplanasincronica = 0
            #         for cuentamarcadas in results:
            #             moodle_url = None
            #             materia = None
            #             permite_ver_video_sinc_asinc_global = None
            #             if Materia.objects.values("id").filter(pk=cuentamarcadas[5]).exists():
            #                 materia = Materia.objects.get(pk=cuentamarcadas[5])
            #                 mi_coordinacion = materia.coordinacion()
            #                 if mi_coordinacion:
            #                     if mi_coordinacion.id == 9:
            #                         moodle_url = f'https://aulanivelacion.unemi.edu.ec/mod/url/view.php?id={cuentamarcadas[14]}'
            #                     elif mi_coordinacion.id in [1,2,3,4,5]:
            #                         moodle_url = f'https://aulagrado.unemi.edu.ec/mod/url/view.php?id={cuentamarcadas[14]}'
            #                         permite_ver_video_sinc_asinc_global = variable_valor('VER_SUBIR_VIDEO_SINCRONICO_ASINCRONICO_PREGRADO')
            #             sinasistencia = periodo.tiene_dias_nolaborables(fecha=cuentamarcadas[8], materia=materia)
            #             dianolaborable = periodo.dias_nolaborables(fecha=cuentamarcadas[8], materia=materia)
            #             hoy = datetime.now().date()
            #             codigoclase = cuentamarcadas[0]
            #             clase = Clase.objects.get(pk=codigoclase)
            #
            #             permite_subirenlace = clase.subirenlace
            #             clases = Clase.objects.filter(materia=clase.materia, dia=clase.dia, tipoprofesor=clase.tipoprofesor, tipohorario=clase.tipohorario)
            #             if clases.exists():
            #                 clases = clases.order_by('-id')
            #                 clasetrue = clases.filter(inicio__lte=hoy, fin__gte=hoy)
            #                 if clasetrue.exists():
            #                     clasetrue = clasetrue.order_by('-turno__comienza')[0]
            #                 else:
            #                     clasetrue = clases.order_by('-turno__comienza')[0]
            #                 codigoclase = clasetrue.id
            #                 permite_subirenlace = clasetrue.subirenlace
            #
            #             if permite_ver_video_sinc_asinc_global is not None:
            #                 permite_subirenlace = permite_subirenlace and permite_ver_video_sinc_asinc_global
            #
            #             # sinasistencia = False
            #             # if periodo.diasnolaborable_set.filter(coordinacion_id=cuentamarcadas[22],carrera_id=cuentamarcadas[21],nivelmalla_id=cuentamarcadas[20], status=True).exists():
            #             #     if periodo.diasnolaborable_set.filter(coordinacion_id=cuentamarcadas[22],carrera_id=cuentamarcadas[21],nivelmalla_id=cuentamarcadas[20], fecha=cuentamarcadas[8], status=True).exists():
            #             #         sinasistencia = True
            #             # else:
            #             #     if periodo.diasnolaborable_set.filter(coordinacion_id=cuentamarcadas[22], carrera_id=cuentamarcadas[21], nivelmalla_id__isnull=True, status=True).exists():
            #             #         if periodo.diasnolaborable_set.filter(coordinacion_id=cuentamarcadas[22], carrera_id=cuentamarcadas[21], nivelmalla_id__isnull=True, fecha=cuentamarcadas[8], status=True).exists():
            #             #             sinasistencia = True
            #             #     else:
            #             #         if periodo.diasnolaborable_set.filter(coordinacion_id=cuentamarcadas[22], carrera_id__isnull=True, nivelmalla_id__isnull=True, status=True).exists():
            #             #             if periodo.diasnolaborable_set.filter(coordinacion_id=cuentamarcadas[22], carrera_id__isnull=True, nivelmalla_id__isnull=True, fecha=cuentamarcadas[8], status=True).exists():
            #             #                 sinasistencia = True
            #             #         else:
            #             #             if periodo.diasnolaborable_set.filter(coordinacion_id__isnull=True, carrera_id__isnull=True, nivelmalla_id__isnull=True, status=True).exists():
            #             #                 if periodo.diasnolaborable_set.filter(coordinacion_id__isnull=True, carrera_id__isnull=True, nivelmalla_id__isnull=True, fecha=cuentamarcadas[8], status=True).exists():
            #             #                     sinasistencia = True
            #             listaasistencias.append([codigoclase, cuentamarcadas[1], cuentamarcadas[2], cuentamarcadas[3],
            #                                      cuentamarcadas[4], cuentamarcadas[5], cuentamarcadas[6], cuentamarcadas[7],
            #                                      cuentamarcadas[8], cuentamarcadas[9], cuentamarcadas[10], cuentamarcadas[11],
            #                                      cuentamarcadas[12], cuentamarcadas[13], cuentamarcadas[14], cuentamarcadas[15],
            #                                      cuentamarcadas[16], cuentamarcadas[17], cuentamarcadas[18], cuentamarcadas[19],
            #                                      sinasistencia, cuentamarcadas[24], cuentamarcadas[25], dianolaborable,
            #                                      moodle_url, permite_subirenlace, clase])
            #
            #             if cuentamarcadas[7] == 2:
            #                 totalsincronica += 1
            #             if cuentamarcadas[7] == 7:
            #                 totalasincronica += 1
            #             # if cuentamarcadas[10]:
            #             #     totalplansincronica += 1
            #             totalplansincronica += 1
            #             if cuentamarcadas[11]:
            #                 totalplanasincronica += 1
            #         data['listaasistencias'] = listaasistencias
            #         data['totalsincronica'] = totalsincronica
            #         data['totalasincronica'] = totalasincronica
            #         data['totalplansincronica'] = totalplansincronica
            #         data['totalplanasincronica'] = totalplanasincronica
            #         # data['procentajesincronica'] = (totalplansincronica * 100) / totalsincronica
            #         # data['procentajeasincronica'] = (totalplanasincronica * 100) / totalasincronica
            #         data['profesor'] = profesor
            #         data['debug'] = DEBUG
            #         # profesoresingresar = [1459,1450]
            #
            #         # puedeingresar = False
            #         # if profesor.id in profesoresingresar:
            #         #     puedeingresar = True
            #         #     fechainiplan = '2020-11-28'
            #         #     fechafinplan = '2021-03-05'
            #         # else:
            #         #     fechainiplan = '2021-01-14'
            #         #     fechafinplan = '2021-01-14'
            #         # data['puedeingresar'] = puedeingresar
            #         # data['fechainicio'] = date(int(fechainiplan[0:4]), int(fechainiplan[5:7]), int(fechainiplan[8:10]))
            #         # data['fechafinal'] = date(int(fechafinplan[0:4]), int(fechafinplan[5:7]), int(fechafinplan[8:10]))
            #         return render(request, "pro_clases/detalle_clasesvideo.html", data)
            #     except Exception as ex:
            #         pass

            elif action == 'detalle_clasesvideo':
                try:
                    data['title'] = u'Detalle clases sincrónicas y asincrónicas'
                    data['hoy'] = hoy = datetime.now().date()
                    cursor = connections['default'].cursor()
                    sql = profesor.get_sql_query_clase_sincronica_y_asincronica(periodo)
                    cursor.execute(sql)
                    results = cursor.fetchall()
                    totalsincronica = 0
                    totalasincronica = 0
                    totalplansincronica = 0
                    totalplanasincronica = 0
                    listaasistencias = []
                    for cuentamarcadas in results:
                        clase = Clase.objects.get(pk=cuentamarcadas[0])
                        clase.__setattr__('sinasistencia', periodo.tiene_dias_nolaborables(fecha=cuentamarcadas[8], materia=clase.materia))
                        clase.__setattr__('dianolaborable', periodo.dias_nolaborables(fecha=cuentamarcadas[8], materia=clase.materia))
                        clase.__setattr__('numerosemana', cuentamarcadas[24])
                        clase.__setattr__('rangofecha', cuentamarcadas[8])
                        clase.__setattr__('rangodia', cuentamarcadas[9])
                        clase.__setattr__('claseultima', clase.get_clase_continua_ultimo_turno(clase.rangodia, clase.rangofecha))
                        clase_ids = (",".join([str(x.id) for x in clase.turno.horario_profesor_actual_horario(clase.rangodia, profesor, periodo, False, False)]))
                        clase.__setattr__('clase_ids', clase_ids)
                        clase.__setattr__('idforomoodle_clas', cuentamarcadas[14])
                        clase.__setattr__('sincronica', cuentamarcadas[10])
                        clase.__setattr__('asincronica', cuentamarcadas[11])
                        clase.__setattr__('fecha_feriado', cuentamarcadas[17])
                        clase.__setattr__('observacion_feriado', cuentamarcadas[18])
                        clase.__setattr__('tipo_ti', cuentamarcadas[25])
                        moodle_url, permite_subirenlace = clase.get_moodle_enlace_con_permiso_subir_enlaces(cuentamarcadas[14])
                        permite_subirenlace = (clase.claseultima.subirenlace and permite_subirenlace) if permite_subirenlace is not None else clase.claseultima.subirenlace
                        clase.__setattr__('puede_subir_video', permite_subirenlace)
                        clase.__setattr__('link_moodle', moodle_url)
                        totalsincronica += 1 if cuentamarcadas[7] == 2 else 0
                        totalasincronica += 1 if cuentamarcadas[7] == 7 else 0
                        totalplansincronica += 1
                        totalplanasincronica += 1 if cuentamarcadas[11] else 0

                        coordinacion = clase.materia.coordinacion()
                        modalidad = clase.materia.asignaturamalla.malla.modalidad
                        if clase.materia.modeloevaluativo_id in [27,64] and clase.materia.asignaturamalla.transversal:
                            modalidad = Modalidad.objects.get(id=3)
                        datajson = {
                            'clases': clase_ids,
                            'codigoclase': encrypt(clase.claseultima.id),
                            'codigodia': int(clase.rangodia),
                            'codigonumsemana': int(clase.numerosemana),
                            'fechasubida': clase.rangofecha.strftime("%Y-%m-%d"),
                            'fechasubida_invertida': clase.rangofecha.strftime("%d-%m-%Y"),
                            'asignatura': clase.materia.asignatura.__str__(),
                        }
                        if coordinacion.id in [1, 2, 3, 4, 5, 12]:
                            # 2 => CLASE VIRTUAL SINCRÓNICA
                            # 8 => CLASE REFUERZO SINCRÓNICA
                            # 7 => CLASE VIRTUAL ASINCRÓNICA
                            # 9 => CLASE REFUERZO ASINCRÓNICA
                            if clase.tipohorario in [2, 7, 8, 9]:
                                if modalidad:
                                    if modalidad.id in [1, 2]:
                                        """
                                            EN MODALIDAD PRESENCIAL Y SEMIPRESENCIAL 
                                            * LAS CLASES SINCRONICAS SE APERTURA Y LUEGO SE SUBE EL VIDEO QUE SE CONVIERTE EN CLASE ASINCRONICA
                                        """
                                        if clase.tipohorario in [2, 8]:
                                            datajson['action_button'] = 'open_class_sincronica'

                                    elif modalidad.id in [3]:
                                        """
                                            EN MODALIDAD EN LINEA 
                                            * LAS CLASES SINCRONICAS SE APERTURA LA CLASE Y LUEGO SE SUBE EL VIDEO QUE SE MANTIENE EN CLASE SINCRONICA
                                            * LAS CLASES ASINCRONICAS SE SUBE EL VIDEO EN CLASE ASINCRONICA SE APERTURA LA CLASE, EL ESTUDIANTE PUEDE INGRESAR A VER EL VIDEO DURANTE LA SEMANA
                                        """
                                        if clase.tipohorario in [2, 8]:
                                            datajson['action_button'] = 'open_class_sincronica'
                                        elif clase.tipohorario in [7, 9]:
                                            datajson['action_button'] = 'open_class_asincronica'

                        elif coordinacion.id in [9]:
                            # clase.__setattr__('action_button', 'open_class_asincronica')
                            if clase.tipohorario in [2, 7, 8, 9]:
                                if clase.tipohorario in [2, 8]:
                                    datajson['action_button'] = 'open_class_sincronica'
                                elif clase.tipohorario in [7, 9]:
                                    datajson['action_button'] = 'open_class_asincronica'
                        elif coordinacion.id in [7, 10]:
                            clase.__setattr__('action_button', 'open_class_asincronica')
                        clase.__setattr__('datajson_object', datajson)
                        clase.__setattr__('datajson', json.dumps(datajson))
                        listaasistencias.append(clase)
                    data['listaasistencias'] = listaasistencias
                    data['totalsincronica'] = totalsincronica
                    data['totalasincronica'] = totalasincronica
                    data['totalplansincronica'] = totalplansincronica
                    data['totalplanasincronica'] = totalplanasincronica
                    # data['procentajesincronica'] = (totalplansincronica * 100) / totalsincronica
                    # data['procentajeasincronica'] = (totalplanasincronica * 100) / totalasincronica
                    data['profesor'] = profesor
                    data['debug'] = DEBUG
                    return render(request, "pro_clases/detalle_clasesvideo_new.html", data)
                except Exception as ex:
                    pass

            elif action == 'registro_asistencia':
                data['title'] = u'Asistencias Docentes en el periodo'
                listas_clases_resultados = profesor.asistencia_profesor_segun_periodo(periodo)
                clases = listas_clases_resultados['lista_clases']
                resultado = listas_clases_resultados['lista_resultado']
                inicio = listas_clases_resultados['fechainicio']
                fin = listas_clases_resultados['fechafin']
                if 'excel' in request.GET:
                    try:
                        response = HttpResponse(content_type="application/ms-excel")
                        response['Content-Disposition'] = 'attachment; filename=listado.xls'
                        wb = xlwt.Workbook()
                        ws = wb.add_sheet('Sheetname')
                        estilo = xlwt.easyxf('font: height 350, name Arial, colour_index black, bold on, italic on; align: wrap on, vert centre, horiz center;')
                        ws.write_merge(0, 0, 0, 9, 'UNIVERSIDAD ESTATAL DE MILAGRO', estilo)
                        ws.col(0).width = 1000
                        ws.col(1).width = 11000
                        ws.col(2).width = 11000
                        ws.col(3).width = 27000
                        ws.col(4).width = 3000
                        ws.col(5).width = 5000
                        ws.col(6).width = 3000
                        ws.col(7).width = 2000
                        ws.col(8).width = 3000
                        ws.col(9).width = 4000
                        ws.write(4, 0, 'N.')
                        ws.write(4, 1, 'CARRERA')
                        ws.write(4, 2, 'PROFESOR')
                        ws.write(4, 3, 'CLASE')
                        ws.write(4, 4, 'FECHA')
                        ws.write(4, 5, 'TURNO')
                        ws.write(4, 6, 'APERTURA')
                        ws.write(4, 7, 'AULA')
                        ws.write(4, 8, 'ASISTENCIA')
                        ws.write(4, 9, 'ESTADO')
                        ws.write(4, 10, 'ORIGEN')
                        a = 4
                        date_format = xlwt.XFStyle()
                        date_format.num_format_str = 'yyyy/mm/dd'
                        for cla in clases:
                            a += 1
                            ws.write(a, 0, a - 4)
                            ws.write(a, 1, cla[1].materia.asignaturamalla.malla.carrera.__str__())
                            ws.write(a, 2, cla[0].__str__())
                            ws.write(a, 3, cla[1].materia.nombre_completo())
                            ws.write(a, 4, cla[4], date_format)
                            ws.write(a, 5, cla[1].turno.nombre_horario())
                            h = ''
                            if cla[3]:
                                h = cla[3].horaentrada.strftime("%H:%M")
                            ws.write(a, 6, h)
                            ws.write(a, 7, cla[1].aula.nombre)
                            asis = ''
                            if cla[2] == 1 or cla[2] == 2:
                                if cla[6] == 1:
                                    asis = u"%s/%s (%s%s)" % (
                                        round(cla[3].asistencia_real(), 2), round(cla[3].asistencia_plan(), 2),
                                        round(cla[3].porciento_asistencia(), 2), "%")
                                else:
                                    asis = u"%s/%s (%s%s)" % (
                                        round(cla[7].registrados_asistieron(), 2), round(cla[7].registrados(), 2),
                                        round(cla[7].porciento_asistencia(), 2), "%")
                            ws.write(a, 8, asis)
                            ws.write(a, 9, cla[11])
                            ws.write(a, 10, cla[5])

                        wb.save(response)
                        return response
                    except Exception as ex:
                        pass

                if not periodo.visible:
                    return HttpResponseRedirect("/?info=Periodo Inactivo.")
                data['clases'] = clases
                data['resultado'] = resultado
                data['profesor'] = profesor
                data['hoy'] = datetime.now().date() == inicio and datetime.now().date() == fin
                data['descargar_reporte'] = True
                data['atras'] = 'pro_clases'
                return render(request, "pro_clases/asistencia.html", data)

            elif action == 'registroasistencia':
                try:
                    data['title'] = u'Registro de asistencias de la clase'
                    if not 'id' in request.GET:
                        raise NameError(u"No se encontro parametro de lección")
                    if not Leccion.objects.values("id").filter(pk=int(encrypt(request.GET['id']))).exists():
                        raise NameError(u"Lección/Clase no encontrada")
                    leccion = Leccion.objects.filter(pk=int(encrypt(request.GET['id'])))[0]
                    asistencias = leccion.mis_asistencias()
                    materia = leccion.clase.materia
                    data['presentes'] = asistencias.filter(asistio=True).count()
                    data['ausentes'] = asistencias.filter(asistio=False).count()
                    data['totalasistencias'] = asistencias.count()
                    data['ePeriodoAcademia'] = ePeriodoAcademia
                    data['registro_hasta'] = leccion.fecha + timedelta(days=ePeriodoAcademia.num_dias_cambiar_asistencia_clase)
                    data['leccion'] = leccion
                    data['verfoto'] = VER_FOTO_LECCION
                    data['silabosemanal'] = SilaboSemanal.objects.filter(silabo__materia=materia, fechainiciosemana__lte=leccion.fecha, fechafinciosemana__gte=leccion.fecha, status=True).first()
                    data['temas'] = TemaAsistencia.objects.values_list('tema_id', flat=True).filter(leccion__clase__materia=materia, status=True).order_by('tema__temaunidadresultadoprogramaanalitico__orden').distinct()
                    data['subtemas'] = SubTemaAsistencia.objects.values_list('subtema_id', flat=True).filter(tema__leccion__clase__materia=materia, status=True).order_by('subtema__subtemaunidadresultadoprogramaanalitico__orden').distinct()
                    data['materia'] = materia
                    if variable_valor('VERSION_REGISTRO_ASISTENCIA') == 2:
                        return render(request, "pro_clases/registro_asistencia_v2.html", data)
                    else:
                        return render(request, "pro_clases/registro_asistencia.html", data)
                except Exception as ex:
                    return HttpResponseRedirect(f"{request.path}?info={ex.__str__()}")

            elif action == 'loadDetailClassSynchronousAsynchronous':
                try:
                    if not 'id' in request.GET:
                        raise NameError(u"No se encontro parametro de lección")
                    if not 'num_semana' in request.GET:
                        raise NameError(u"Parametro de numero de la semana de la clase no encontrado")
                    clase = Clase.objects.filter(pk=int(encrypt(request.GET['id']))).first()
                    numero_semana = request.GET['num_semana']
                    if clase is None:
                        raise NameError(u"Lección/Clase no encontrada")

                    clases_sincronicas = clase.clasesincronica_set.filter(numerosemana=numero_semana, status=True)
                    clases_asincronicas = clase.claseasincronica_set.filter(numerosemana=numero_semana, status=True)

                    data['clase'] = clase
                    data['num_semana'] = numero_semana
                    data['title'] = u'Clase %s'%(clase)
                    data['clases_sincronicas'] = clases_sincronicas
                    data['clases_asincronicas'] = clases_asincronicas
                    template = get_template(f"pro_clases/listadoclase_sincronicas_asincronicas.html")
                    json_content = template.render(data, request=request)
                    return JsonResponse({"result": "ok", 'html': json_content, 'title': data['title']})
                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos. %s" % ex.__str__()})

            elif action == 'mismarcadas':
                try:
                    data['title'] = "Mis temas y subtemas marcados del periodo"

                    filtro = Q(profesor=profesor, materia__nivel__periodo=periodo, status=True)
                    order_by = ['materia__asignaturamalla__asignatura__nombre', 'materia__paralelo']
                    distinct = ['materia', 'materia__asignaturamalla__asignatura__nombre', 'materia__paralelo']
                    profesormateria = ProfesorMateria.objects.filter(filtro).distinct(*distinct).order_by(*order_by).exclude(materia__asignaturamalla__tipomateria=3)
                    data['profesormateria'] = profesormateria
                    cursor = connections['sga_select'].cursor()
                    if 'id' in request.GET:
                        if request.GET['id'].isdigit() and int(request.GET['id']):
                            filtro &= Q(id=request.GET['id'])
                            data['materiaasignada'] = int(request.GET['id'])

                    if request.GET.get('s', ''):
                        data['s'] = request.GET['s']
                        filtro &= Q(Q(materia__asignaturamalla__malla__carrera__coordinacion__nombre__icontains=request.GET['s']) | Q(materia__asignaturamalla__asignatura__nombre__icontains=request.GET['s']))

                    dataset2 = []
                    ahora = datetime.now().date()
                    semanasferiado = list(set([f.isocalendar()[1] for f in periodo.diasnolaborable_set.filter(status=True, activo=True).values_list('fecha', flat=True)]))
                    for pm in ProfesorMateria.objects.filter(filtro).distinct(*distinct).order_by(*order_by).exclude(materia__asignaturamalla__tipomateria=3):
                        dataset1 = []
                        temasmarcados, subtemasmarcados = 0, 0
                        temasplanificados, subtemasplanificados = 0, 0
                        for silabosemanal in SilaboSemanal.objects.filter(silabo=pm.materia.silabo_actual(), fechainiciosemana__lte=ahora, status=True).order_by('numsemana'):
                            fechainicio, fechafin = silabosemanal.fechainiciosemana, silabosemanal.fechafinciosemana + timedelta(weeks=1)
                            if fechainicio.isocalendar()[1] in semanasferiado:
                                fechafin += timedelta(weeks=1)

                            # Para saber si tenia clases de esa materia en el día
                            debe_justificar_marcadas = True
                            # for fecha in daterange(silabosemanal.fechainiciosemana, silabosemanal.fechafinciosemana + timedelta(1)):
                            #     if pm.desde <= fecha <= pm.hasta and fecha.isoweekday() in dias_clase_materia:
                            #         debe_justificar_marcadas = True

                            temas = silabosemanal.detallesilabosemanaltema_set.filter(temaunidadresultadoprogramaanalitico__status=True, status=True).order_by('fecha_creacion').distinct()
                            listatemassubtemas = []
                            for tema in temas:
                                marcada, fechamarcada = '-', None
                                if debe_justificar_marcadas:
                                    marcada = 0
                                    if temaasistencia := tema.temaasistencia_set.values_list('id', 'fecha', 'usuario_creacion', 'fecha_creacion', 'leccion__solicitada', 'usuario_creacion__username').filter(tema__silabosemanal=silabosemanal, status=True).order_by('fecha', 'fecha_creacion').first():
                                        temaasistenciapk, fechamarcada, usuario_creacion, fecha_creacion, diferido, username_creacion = temaasistencia
                                        if fechamarcada and fechamarcada < fechafin:
                                            marcada = 100
                                            temasmarcados += 1
                                            auditoria = f'Usuario creación: {username_creacion}'
                                            if not usuario_creacion == 1 and fecha_creacion:
                                                descripcion = f"{tema.temaunidadresultadoprogramaanalitico.descripcion}".upper()
                                                sql = f"""
                                                    select change_message from django_admin_log 
                                                    where (
                                                        user_id = {usuario_creacion}
                                                        and change_message ilike '%{descripcion}%'
                                                        and (action_time)::DATE = '{fecha_creacion.date()}'
                                                        and extract(hour from action_time) = {fecha_creacion.hour}
                                                        and extract(minute from action_time) = {fecha_creacion.minute}
                                                        and action_flag = 1
                                                    )
                                                    limit 1
                                                """
                                                cursor.execute(sql)
                                                if change_message := cursor.fetchone():
                                                    change_message = change_message[0]
                                                    if msg := change_message[change_message.find('--IP'):]:
                                                        auditoria += f" - Conectado desde {msg}" if len(msg) > 5 else ''
                                            auditoria += f' - REGISTRO POR DIFERIDO' if diferido else ''
                                            tema.__setattr__('mensaje', auditoria)
                                        tema.__setattr__('idmarcada', temaasistenciapk)
                                    temasplanificados += 1
                                tema.__setattr__('marcada', marcada)
                                tema.__setattr__('fechamarcada', fechamarcada)
                                subtemas = silabosemanal.detallesilabosemanalsubtema_set.filter(subtemaunidadresultadoprogramaanalitico__temaunidadresultadoprogramaanalitico=tema.temaunidadresultadoprogramaanalitico, subtemaunidadresultadoprogramaanalitico__status=True,subtemaunidadresultadoprogramaanalitico__temaunidadresultadoprogramaanalitico__isnull=False,subtemaunidadresultadoprogramaanalitico__temaunidadresultadoprogramaanalitico__status=True, status=True).order_by('fecha_creacion').distinct()
                                for subtema in subtemas:
                                    marcada, fechamarcada = '-', None
                                    if debe_justificar_marcadas:
                                        marcada = 0
                                        if subtemaasistencia := subtema.subtemaasistencia_set.values_list('id', 'fecha', 'usuario_creacion', 'fecha_creacion', 'tema__leccion__solicitada', 'usuario_creacion__username').filter(subtema__silabosemanal=silabosemanal, status=True).order_by('fecha', 'fecha_creacion').first():
                                            subtemaasistenciapk, fechamarcada, usuario_creacion, fecha_creacion, diferido, username_creacion = subtemaasistencia
                                            if fechamarcada < fechafin:
                                                marcada = 100
                                                subtemasmarcados += 1
                                                auditoria = f'Usuario creación: {username_creacion}'
                                                if not usuario_creacion == 1 and fecha_creacion:
                                                    descripcion = f"{subtema.subtemaunidadresultadoprogramaanalitico.descripcion}".upper()
                                                    sql = f"""
                                                            select change_message from django_admin_log 
                                                            where (
                                                                user_id = {usuario_creacion}
                                                                and change_message ilike '%{descripcion}%'
                                                                and (action_time)::DATE = '{fecha_creacion.date()}'
                                                                and extract(hour from action_time) = {fecha_creacion.hour}
                                                                and extract(minute from action_time) = {fecha_creacion.minute}
                                                                and action_flag = 1
                                                            )
                                                            limit 1
                                                        """
                                                    cursor.execute(sql)
                                                    if change_message := cursor.fetchone():
                                                        change_message = change_message[0]
                                                        if msg := change_message[change_message.find('--IP'):]:
                                                            auditoria += f" - Conectado desde {msg}" if len(msg) > 5 else ''
                                                auditoria += f' - REGISTRO POR DIFERIDO' if diferido else ''
                                                subtema.__setattr__('mensaje', f"{auditoria}")
                                            subtema.__setattr__('idmarcada', subtemaasistenciapk)
                                        subtemasplanificados += 1
                                    subtema.__setattr__('marcada', marcada)
                                    subtema.__setattr__('fechamarcada', fechamarcada)
                                listatemassubtemas.append({'tema': tema, 'subtemas': subtemas})
                            debe_justificar_marcadas and dataset1.append({'silabosemanal': silabosemanal, 'contenido': listatemassubtemas, 'plazomaximo': fechafin})
                        porcentaje = 0
                        try:
                            totalmarcados, totalplanificados = temasmarcados + subtemasmarcados, temasplanificados + subtemasplanificados
                            porcentaje = (totalmarcados / totalplanificados) * 100
                        except ZeroDivisionError as ex:
                            ...
                        dataset2.append({'materia': pm.materia, 'contenido': dataset1, 'porcentajetotal': f"{porcentaje:.2f}"})
                    data['dataset'] = dataset2
                    return render(request, "pro_clases/mismarcadas.html", data)
                except Exception as ex:
                    pass


            return HttpResponseRedirect(request.path)
        else:
            try:
                data['title'] = u'Registros de asistencia a clase'
                hoy = datetime.now().date()
                if not request.session['periodo'].visible:
                    raise NameError(u"Periodo Inactivo.")
                # materias = Materia.objects.filter(nivel__periodo__fin__gte=hoy, nivel__cerrado=False, profesormateria__profesor=profesor, profesormateria__principal=True)
                materia_n = Materia.objects.select_related().filter(profesormateria__profesor=profesor, profesormateria__principal=True, nivel__periodo=periodo, status=True, profesormateria__activo=True, profesormateria__status=True)
                materia_r = Materia.objects.select_related().filter(profesormateria__tipoprofesor_id=6, profesormateria__profesor=profesor, nivel__periodo=periodo, status=True, profesormateria__activo=True, profesormateria__status=True)
                materias = None
                if materia_n:
                    if materia_r:
                        materias = materia_n | materia_r
                    else:
                        materias = materia_n
                else:
                    if materia_r:
                        materias = materia_r

                materia = None
                if 'id' in request.GET:
                    materia = materias.filter(pk=request.GET['id'])[0]
                    lecciones = Leccion.objects.select_related().filter(clase__materia=materia, status=True, clase__profesor=profesor).distinct().order_by('-fecha', '-horaentrada')
                else:
                    if materia_n or materia_r:
                        lecciones = Leccion.objects.select_related().filter(clase__materia__in=materias, status=True, clase__profesor=profesor).distinct().order_by('-fecha', '-horaentrada')
                    else:
                        lecciones = []
                fechainicio = None
                fechafin = None
                if 'fi' in request.GET and 'ff' in request.GET:
                    inicio = fechainicio = convertir_fecha(request.GET['fi'])
                    fin = fechafin = convertir_fecha(request.GET['ff'])
                    if inicio > fin:
                        return HttpResponseRedirect("/pro_clases?info=No puede ser mayor la fecha de inicio que la fecha fin.")
                    lecciones = lecciones.filter(fecha__gte=inicio, fecha__lte=fin)
                paging = Paginator(lecciones, 25)
                p = 1
                try:
                    paginasesion = 1
                    if 'paginador' in request.session:
                        paginasesion = int(request.session['paginador'])
                    if 'page' in request.GET:
                        p = int(request.GET['page'])
                    else:
                        p = paginasesion
                    try:
                        page = paging.page(p)
                    except:
                        p = 1
                    page = paging.page(p)
                except:
                    page = paging.page(p)
                request.session['paginador'] = p
                data['paging'] = paging
                data['page'] = page
                data['lecciones'] = page.object_list
                data['ids'] = materia.id if materia else None
                if periodo.ocultarmateria:
                    materias = False
                data['materias'] = materias
                # data['clases_horario_estricto'] = CLASES_HORARIO_ESTRICTO
                data['clases_horario_estricto'] = ePeriodoAcademia.valida_clases_horario_estricto
                data['periodo'] = periodo
                data['ePeriodoAcademia'] = ePeriodoAcademia
                data['tienemateria'] = profesor.cantidad_materiastodas(periodo)
                data['inicio'] = fechainicio
                data['fin'] = fechafin
                data['debug'] = DEBUG
                data['profesor'] = profesor
                data['VER_OPCION_ELIMINAR_CLASES_EN_PROFESOR'] = variable_valor('VER_OPCION_ELIMINAR_CLASES_EN_PROFESOR')
                return render(request, "pro_clases/view.html", data)
            except Exception as ex:
                return HttpResponseRedirect(f"/?info={ex.__str__()}")
