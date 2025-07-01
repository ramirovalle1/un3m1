# -*- coding: latin-1 -*-
from datetime import datetime, timedelta, date
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.db.models import Q, Sum, Count
from django.http import HttpResponseRedirect, JsonResponse
from django.shortcuts import render
from django.template.loader import get_template
from mobi.decorators import detect_mobile
from decorators import secure_module, last_access, get_client_ip
from faceid.functions import calculando_marcadasotro
from sagest.models import LogDia, LogMarcada, MarcadasDia, RegistroMarcada, MarcadaActividad
from settings import TIEMPO_DEDICACION_TIEMPO_COMPLETO_ID, DEBUG
from sga.commonviews import adduserdata
from django.template.context import Context
from sga.funciones import variable_valor, convertir_fecha, log, convertir_fecha_hora, convertir_fecha_hora_invertida, \
    notificacion
from sga.models import Clase, Sesion, LeccionGrupo, ProfesorMateria, ComplexivoClase, ComplexivoLeccion, Profesor, \
    Turno, ClaseSincronica, Materia, SesionZoom, DesactivarSesionZoom, DetalleDistributivo, DiasNoLaborable, Persona, \
    ClaseActividad, ProfesorDistributivoHoras, ClaseActividadEstado, MateriaAsignada, Modalidad
from sga.funcionesxhtml2pdf import conviert_html_to_pdf
from inno.models import HorarioTutoriaAcademica, RegistroClaseTutoriaDocente, SolicitudTutoriaIndividual, \
    PeriodoAcademia
from sga.templatetags.sga_extras import encrypt, convertir_tipo_oracion
from inno.funciones import actualiza_vigencia_criterios_docente

@login_required(redirect_field_name='ret', login_url='/loginsga')
@secure_module
@last_access
@transaction.atomic()
@detect_mobile
def view(request):
    data = {}
    adduserdata(request, data)
    persona = request.session['persona']
    periodo = request.session['periodo']
    perfilprincipal = request.session['perfilprincipal']
    # if not ABRIR_CLASES_DISPOSITIVO_MOVIL and request.mobile:
    #     return HttpResponseRedirect("/?info=No se puede abrir clases desde un dispositivo movil.")
    if not perfilprincipal.es_profesor():
        return HttpResponseRedirect("/?info=Solo los perfiles de profesores pueden ingresar al modulo.")
    profesor = perfilprincipal.profesor
    hoy = datetime.now().date()
    horaactual = datetime.now().time()
    numerosemanaactual = datetime.today().isocalendar()[1]
    ePeriodoAcademia = periodo.get_periodoacademia()

    if request.method == 'POST':
        action = request.POST['action']

        if action == 'pdf_horarios':
            data = {}
            data['periodo'] = periodo
            if not periodo.visible:
                return HttpResponseRedirect("/?info=No tiene permiso para imprimir en el periodo seleccionado.")
            data['profesor'] = profesor = Profesor.objects.filter().distinct().get(pk=request.POST['profesor'])
            data['aprobado'] = profesor.claseactividadestado_set.filter(status=True, periodo=periodo, estadosolicitud=2).exists()
            data['semana'] = [[1, 'Lunes'], [2, 'Martes'], [3, 'Miercoles'], [4, 'Jueves'], [5, 'Viernes'],
                              [6, 'Sabado'], [7, 'Domingo']]
            turnosyclases = profesor.extrae_turnos_y_clases_docente(periodo)
            # turnoclases = Turno.objects.filter(clase__activo=True, clase__materia__nivel__periodo=periodo,
            #                                    clase__materia__profesormateria__profesor=profesor,
            #                                    clase__materia__profesormateria__principal=True).distinct().order_by(
            #     'comienza')
            turnoactividades = Turno.objects.filter(status=True,
                                                    claseactividad__detalledistributivo__distributivo__periodo=periodo,
                                                    claseactividad__detalledistributivo__distributivo__profesor=profesor).distinct(
                'comienza').order_by('comienza')
            data['turnos'] = turnosyclases[1] | turnoactividades
            data['puede_ver_horario'] = request.user.has_perm('sga.puede_visible_periodo') or (periodo.visible and periodo.visiblehorario)
            data['aprobado'] = profesor.claseactividadestado_set.filter(status=True, periodo=periodo, estadosolicitud=2).exists()
            return conviert_html_to_pdf(
                'docentes/horario_pfd.html',
                {
                    'pagesize': 'A4',
                    'data': data,
                }
            )

        elif action == 'addVideoVirtualActividad':
            try:
                url1 = request.POST.get('link_1', None)

                if not url1: raise NameError(u"Parametro de enlace 1 de la clase no encontrado")

                horario = HorarioTutoriaAcademica.objects.get(id=request.POST.get('id'))
                if registro := RegistroClaseTutoriaDocente.objects.filter((Q(horario__profesor=profesor) | Q(profesor=profesor)) & (Q(periodo=periodo) | Q(horario__periodo=periodo)), numerosemana=datetime.today().isocalendar()[1], status=True).order_by('-id').first():
                    if not registro.enlaceuno:
                        registro.enlaceuno = url1
                        registro.save(request)
                    else:
                        raise NameError('El video ya a sido cargado')
                else:
                    raise NameError('No existe una clase registrada para esta tutoría, por favor justifiquela y vuelva a ingresar.')

                return JsonResponse({"result": "ok", "mensaje": u"Video de la actividad subido correctamente"})
            except Exception as ex:
                return JsonResponse({"result": "bad", "mensaje": ex.__str__()})

        elif action == 'addVideoVirtual':
            try:
                from Moodle_Funciones import CrearClaseVirtualClaseMoodle, CrearClaseSincronicaMoodle, \
                    CrearClaseAsincronicaMoodle
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
                if not request.POST['link_1']:
                    raise NameError(u"Enlace de la grabación 1 es obligatorio")
                idc = int(request.POST['idc'])
                link_1 = request.POST['link_1']
                link_2 = request.POST['link_2']
                link_3 = request.POST['link_3']
                dia = request.POST['dia']
                clase = Clase.objects.get(pk=idc)
                materia = clase.materia
                coordinacion = materia.coordinacion()
                modalidad = materia.asignaturamalla.malla.modalidad
                if materia.modeloevaluativo_id in [27, 64] and materia.asignaturamalla.transversal:
                    modalidad = Modalidad.objects.get(id=3)
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
                                    CrearClaseVirtualClaseMoodle(idc, persona, link_1, link_2, link_3, dia)
                            elif modalidad.id in [3]:
                                if clase.tipohorario in [2, 8]:
                                    CrearClaseSincronicaMoodle(idc, persona, link_1, link_2, link_3, dia)
                                elif clase.tipohorario in [7, 9]:
                                    CrearClaseAsincronicaMoodle(idc, persona, link_1, link_2, link_3, dia)
                elif coordinacion.id in [9]:
                    # CrearClaseVirtualClaseMoodle(idc, persona, link_1, link_2, link_3, dia)
                    if clase.tipohorario == 1:
                        raise NameError(u"Clase de tipo presencial no se sube video")
                    elif clase.tipohorario in [2, 7, 8, 9]:
                        if clase.tipohorario in [2, 8]:
                            CrearClaseSincronicaMoodle(idc, persona, link_1, link_2, link_3, dia)
                        elif clase.tipohorario in [7, 9]:
                            CrearClaseAsincronicaMoodle(idc, persona, link_1, link_2, link_3, dia)
                elif coordinacion.id in [7, 10]:
                    CrearClaseVirtualClaseMoodle(idc, persona, link_1, link_2, link_3, dia)
                return JsonResponse({"result": "ok", "mensaje": u"Video de la clase subido correctamente"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos. %s" % ex.__str__()})

        elif action == 'addForoVirtual':
            try:
                from Moodle_Funciones import CrearForosClaseMoodle
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
                if not request.POST['link_1']:
                    raise NameError(u"Enlace de la grabación 1 es obligatorio")
                idc = int(request.POST['idc'])
                link_1 = request.POST['link_1']
                link_2 = request.POST['link_2']
                link_3 = request.POST['link_3']
                dia = request.POST['dia']
                CrearForosClaseMoodle(idc, persona, link_1, link_2, link_3, dia)
                return JsonResponse({"result": "ok", "mensaje": u"Foro de la clase subido correctamente"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos. %s" % ex.__str__()})

        elif action == 'addClaseTutoria':
            try:
                if not 'id' in request.POST:
                    raise NameError(u"Parametro de tutoria no encontrada")
                if not HorarioTutoriaAcademica.objects.filter(pk=request.POST['id']).exists():
                    raise NameError(u"Tutoria no encontrada")
                horario = HorarioTutoriaAcademica.objects.get(id=request.POST['id'])
                horario_todos = HorarioTutoriaAcademica.objects.filter(status=True, periodo=horario.periodo,
                                                                       profesor=horario.profesor, dia=horario.dia,
                                                                       turno__comienza__gte=horario.turno.comienza).order_by(
                    'turno__comienza')
                for horario_insertar in horario_todos:
                    if not RegistroClaseTutoriaDocente.objects.filter(horario=horario_insertar,
                                                                      numerosemana=datetime.today().isocalendar()[1],
                                                                      status=True, fecha__date=datetime.now().date()):
                        clasetutoria = RegistroClaseTutoriaDocente(horario=horario_insertar,
                                                                   numerosemana=datetime.today().isocalendar()[1],
                                                                   fecha=datetime.now())
                        clasetutoria.save(request)
                tutorias_programadas_hoy = SolicitudTutoriaIndividual.objects.values('tipotutoria', 'fechatutoria',
                                                                                     'tutoriacomienza',
                                                                                     'tutoriatermina').filter(
                    status=True, estado=2, fechatutoria__date=datetime.now().date(), tipotutoria__in=[2, 3],
                    profesor=profesor, materiaasignada__matricula__nivel__periodo=periodo).distinct()

                for tuto_programada in tutorias_programadas_hoy:
                    if not RegistroClaseTutoriaDocente.objects.filter(numerosemana=datetime.today().isocalendar()[1],
                                                                      fecha=convertir_fecha_hora_invertida(u"%s %s" % (
                                                                              tuto_programada['fechatutoria'].date(),
                                                                              tuto_programada['tutoriacomienza'])),
                                                                      tipotutoria=tuto_programada['tipotutoria'],
                                                                      status=True, periodo=periodo, profesor=profesor):
                        clasetutoria = RegistroClaseTutoriaDocente(numerosemana=datetime.today().isocalendar()[1],
                                                                   fecha=convertir_fecha_hora_invertida(u"%s %s" % (
                                                                       tuto_programada['fechatutoria'].date(),
                                                                       tuto_programada['tutoriacomienza'])),
                                                                   tipotutoria=tuto_programada['tipotutoria'],
                                                                   periodo=periodo,
                                                                   profesor=profesor)
                        clasetutoria.save(request)

                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos. %s" % ex.__str__()})

        elif action == 'asistenciaactividad':
            try:
                marcada = None
                user = request.user
                if Persona.objects.values("id").filter(usuario=user).exists():
                    persona = Persona.objects.filter(usuario=user)[0]
                    if persona.perfilusuario_set.values("id").filter(administrativo__isnull=False,
                                                                     status=True) or persona.perfilusuario_set.values(
                        "id").filter(profesor__isnull=False, status=True):
                        # if persona.distributivopersona_set.filter(estadopuesto_id=1, status=True).exists():
                        fecha = datetime.now().date()
                        time = datetime.now()
                        horaactual = datetime.now().time().hour
                        minutoactual = datetime.now().time().minute
                        segundoactual = datetime.now().time().second
                        if persona.logdia_set.values("id").filter(fecha=fecha).exists():
                            logdia = persona.logdia_set.filter(fecha=fecha)[0]
                            logdia.cantidadmarcadas += 1
                            logdia.procesado = False
                        else:
                            logdia = LogDia(persona=persona,
                                            fecha=fecha,
                                            cantidadmarcadas=1)
                        logdia.save(request)
                        if not logdia.logmarcada_set.values("id").filter(time=time).exists():
                            registro = LogMarcada(logdia=logdia,
                                                  time=time,
                                                  secuencia=logdia.cantidadmarcadas,
                                                  tipomarcada=2,
                                                  ipmarcada=get_client_ip(request))
                            registro.save(request)
                            marcada = registro
                        for l in LogDia.objects.filter(persona=persona, status=True, procesado=False).order_by("fecha"):
                            cm = l.logmarcada_set.filter(status=True).count()
                            MarcadasDia.objects.filter(persona=l.persona, fecha=l.fecha).delete()
                            l.cantidadmarcadas = cm
                            if (cm % 2) == 0:
                                marini = 1
                                for dl in l.logmarcada_set.filter(status=True).order_by("time"):
                                    if marini == 2:
                                        salida = dl.time
                                        marini = 1
                                        if l.persona.marcadasdia_set.values("id").filter(fecha=l.fecha).exists():
                                            marcadadia = l.persona.marcadasdia_set.filter(fecha=l.fecha)[0]
                                        else:
                                            marcadadia = MarcadasDia(persona=l.persona,
                                                                     fecha=l.fecha,
                                                                     logdia=l,
                                                                     segundos=0)
                                            marcadadia.save(request)
                                        if not marcadadia.registromarcada_set.values("id").filter(
                                                entrada=entrada).exists():
                                            registro = RegistroMarcada(marcada=marcadadia,
                                                                       entrada=entrada,
                                                                       salida=salida,
                                                                       segundos=(salida - entrada).seconds)
                                            registro.save(request)
                                        marcadadia.actualizar_marcadas()
                                    else:
                                        entrada = dl.time
                                        marini += 1
                                l.procesado = True
                            else:
                                l.cantidadmarcadas = 0
                            l.save(request)
                            # if l.procesado:
                            #     calculando_marcadas(request, l.fecha, l.fecha, l.persona)
                        calculando_marcadasotro(fecha, fecha, persona)
                        nombres = persona.apellido1 + ' ' + persona.apellido2 + ' ' + persona.nombres
                        mensaje = '{} acaba de marcar el dia: {} a las:  {}:{}:{}'.format(persona, fecha, horaactual,
                                                                                          minutoactual, segundoactual)
                        if marcada is not None:
                            actividad = ClaseActividad.objects.get(id=request.POST['actividad'])
                            for act in ClaseActividad.objects.filter(dia=actividad.dia,
                                                                     detalledistributivo__distributivo__profesor=actividad.detalledistributivo.distributivo.profesor,
                                                                     detalledistributivo__distributivo__periodo=actividad.detalledistributivo.distributivo.periodo).order_by(
                                'turno__comienza'):
                                if not MarcadaActividad.objects.filter(claseactividad=act,
                                                                       logmarcada__logdia__fecha=datetime.now().date()) or act.marcada_doble():
                                    if act.tipodistributivo == 3 or act.tipodistributivo == '3':
                                        if act.id == actividad.id:
                                            detalle = MarcadaActividad(logmarcada=marcada, claseactividad=act)
                                            detalle.save(request)
                                        elif not act.modalidad == 1 and not act.ordenmarcada == 3 and not act.ordenmarcada == 1:
                                            detalle = MarcadaActividad(logmarcada=marcada, claseactividad=act)
                                            detalle.save(request)
                        return JsonResponse({"result": "ok", "mensaje": mensaje})
            except Exception as e:
                transaction.set_rollback(True)
                # print(e)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar la marcada"})

        elif action == 'addactividad':
            try:
                hoy = datetime.now().date()
                periodo = request.session['periodo']
                dia = request.POST['iddia']
                idactividad = request.POST['idactividad']
                turno = Turno.objects.get(id=request.POST['idturno'])
                if turno:
                    detalle = DetalleDistributivo.objects.get(id=request.POST['idactividad'])
                    tutoria = detalle.criteriodocenciaperiodo.criterio.procesotutoriaacademica if detalle.criteriodocenciaperiodo else False
                    if tutoria:
                        if not verificar_turno_tutoria(dia, periodo, profesor, turno.id):
                            return JsonResponse({"result": "bad", "mensaje": "Lo sentimos este horario no está disponible para la actividad: <b>" + str(convertir_tipo_oracion(
                                                         detalle.criteriodocenciaperiodo.criterio.nombre)) + "</b><br> intente en con un dia y hora diferente"})
                    actividadesdia = ClaseActividad.objects.filter(status=True,
                                                                   detalledistributivo__distributivo__profesor=profesor,
                                                                   detalledistributivo__distributivo__periodo=periodo,
                                                                   dia=dia).values('id', 'modalidad', 'turno__comienza')
                    clasesdia = Clase.objects.filter(profesor=profesor, materia__nivel__periodo__visible=True,
                                                     materia__nivel__periodo=periodo,
                                                     materia__nivel__periodo__visiblehorario=True, activo=True,
                                                     dia=request.POST['iddia'],
                                                     materia__profesormateria__profesor=profesor,
                                                     materia__profesormateria__principal=True,
                                                     materia__profesormateria__activo=True,
                                                     materia__profesormateria__status=True, fin__gte=hoy).order_by(
                        'inicio')
                    critvencidos = turno.actividadesvencidasdia(periodo, dia, profesor)
                    if actividadesdia.filter(Q(turno__comienza__range=(turno.comienza, turno.termina)) | Q(
                            turno__termina__range=(turno.comienza, turno.termina))).exists() or clasesdia.filter(
                        Q(turno__comienza__range=(turno.comienza, turno.termina)) | Q(
                            turno__termina__range=(turno.comienza, turno.termina))).exists():
                        if not critvencidos:
                            return JsonResponse({"result": "bad",
                                                 "mensaje": "Lo sentimos el horario que intenta elegir da conflicto con una o más horas de su horario, elija otro turno para continuar"})
                    detalledist = DetalleDistributivo.objects.get(id=idactividad)
                    actividad = ClaseActividad(detalledistributivo=detalledist,
                                               turno=turno,
                                               dia=dia,
                                               inicio=detalledist.detalleactividadcriterio().desde,
                                               fin=detalledist.detalleactividadcriterio().hasta,
                                               estadosolicitud=1,
                                               modalidad=None,
                                               ordenmarcada=None,
                                               actividaddetallehorario=detalledist.detalleactividadcriterio()
                                               )

                    actividad.save(request)
                    tipodes = actividad.detalledistributivo.tipo_nombre()
                    des = actividad.detalledistributivo.nombre
                    log(u'Adicionó horario de actividad: %s - %s  turno: %s dia: %s' % (
                        des, tipodes, str(turno), str(dia)), request, "add")
                    return JsonResponse({"result": "ok"})
                else:
                    JsonResponse({"result": "bad", "mensaje": "Lo sentimos el turno no existe"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": "Error al guardar los datos. {}".format(ex)})

        elif action == 'delactividad':
            try:
                periodo = request.session['periodo']
                dia = request.POST['iddia']
                idactividad = request.POST['idactividad']
                turno = Turno.objects.get(id=request.POST['idturno'])
                actividadquery = ClaseActividad.objects.filter(detalledistributivo=idactividad, turno=turno, dia=dia)
                actividad = actividadquery.first()
                if not actividad:
                    raise NameError('Lo sentimos, no pudimos encontrar la actividad que intentas eliminar')
                if actividad.finalizado:
                    raise NameError('Lo sentimos, esta actividad ya no se puede eliminar')
                tipo = actividad.tipodistributivo
                if actividad.detalledistributivo:
                    if tipo == 1:
                        if actividad.detalledistributivo.criteriodocenciaperiodo.criterio.procesotutoriaacademica:
                            tuto = HorarioTutoriaAcademica.objects.filter(status=True, dia=actividad.dia,
                                                                          turno=actividad.turno, periodo=periodo,
                                                                          profesor=actividad.detalledistributivo.distributivo.profesor).first()
                            if tuto:
                                if tuto.en_uso():
                                    return JsonResponse({"result": "bad",
                                                         "mensaje": u"Lo sentimos esta actividad de tutoria tiene solicitudes y no se la puede eliminar"})
                turno = actividad.turno_id
                dia = actividad.dia
                profesor = actividad.detalledistributivo.distributivo.profesor
                des = actividad.detalledistributivo.nombre()
                actividadquery.delete()
                log(u'Eliminó actividad {} del horario del profesor: %s - %s  turno: %s dia: %s' % (
                    des, profesor, str(turno), str(dia)), request, "del")
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos. {}".format(ex)})

        elif action == 'saveactivities':
            try:
                aprobado = ClaseActividadEstado.objects.filter(profesor=profesor, periodo=periodo, status=True, estadosolicitud=2).order_by('-id').exists()
                onlyclass = False
                if aprobado:
                    raise NameError('El horario de actividades ya se encuentra aprobado')
                actvidades = ClaseActividad.objects.filter(status=True, detalledistributivo__distributivo__profesor=profesor,
                                                           detalledistributivo__distributivo__periodo=periodo)
                if not actvidades.exists():
                    if not Clase.objects.filter(Q(status=True, activo=True, profesor=profesor, materia__nivel__periodo=periodo,
                                           materia__nivel__periodo__visible=True,
                                                  materia__nivel__periodo__visiblehorario=True)).distinct().order_by('turno__inicio').exists():
                        raise NameError('Actividades no encontradas')
                    onlyclass = True
                distributivo = ProfesorDistributivoHoras.objects.filter(status=True, profesor=profesor, periodo=periodo).first()
                if not distributivo:
                    raise NameError('Docente no se encuentra registrado en el distributivo')
                if not actvidades.filter(finalizado=False).exists():
                    if distributivo.horariofinalizado:
                        raise NameError('Horario de actividades ya fue guardado!')
                if not onlyclass:
                    actvidades.filter(finalizado=False).update(finalizado=True)
                distributivo.horariofinalizado = True
                distributivo.save(request, update_fields=['horariofinalizado'])
                if distributivo.carrera:
                    director = distributivo.carrera.get_director(periodo)
                    if director:
                        notificacion('Aprobación de horario de actividades',
                                     'El docente {} le solicita la aprobación del horario de actividades'.format(profesor),
                                     director.persona, None,
                                     '/adm_criteriosactividadesdocente?action=horario&id={}&periodo={}'.format(profesor.pk, periodo.pk), profesor.pk, 1, 'sga', Profesor, request)
                log('Guardó su horario de actividades el docente: {}'.format(profesor.persona), request, "add")
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error en la transaccion. {}".format(ex)})

        return JsonResponse({"result": "bad", "mensaje": u"Solicitud Incorrecta."})
    else:
        if 'action' in request.GET:
            action = request.GET['action']
            try:
                if action == 'actividades':
                    try:
                        data['periodo'] = periodo = request.session['periodo']
                        if not periodo.visible:
                            return HttpResponseRedirect("/pro_horarios?info=Lo sentimos, este periodo no se encuentra activo.")
                        distributivo = ProfesorDistributivoHoras.objects.filter(status=True, profesor=profesor, periodo=periodo).first()
                        if not distributivo:
                            return HttpResponseRedirect("/pro_horarios?info=Lo sentimos, usted no se encuentra registrado en el distributivo de docentes del periodo actual")
                        todaslasactividades = DetalleDistributivo.objects.filter(distributivo__profesor=profesor, distributivo__periodo=periodo)
                        if not todaslasactividades:
                            return HttpResponseRedirect("/pro_horarios?info=Lo sentimos, usted no tiene asignados criterios en su distributivo, comuniquese con GTA.")
                        data['sindirector'] = not distributivo.carrera
                        data['criterio'] = criterio = request.GET['criterio'] if 'criterio' in request.GET else None
                        if criterio:
                            try:
                                criterio = int(criterio)
                            except:
                                criterio = None
                        data['title'] = u'Adicionar Actividades'
                        data['profesor'] = profesor
                        data['todaslasactividades'] = todaslasactividades
                        data['criterio'] = criterio = todaslasactividades.first().id if not criterio and len(todaslasactividades) > 0 else criterio
                        data['ultimocriterio'] = todaslasactividades[len(todaslasactividades) - 1].id if len(todaslasactividades) > 0 else 0
                        data['turnos'] = turnos = Turno.objects.filter(status=True, mostrar=True, sesion_id=20)
                        data['semana'] = [[1, 'Lunes'], [2, 'Martes'], [3, 'Miercoles'], [4, 'Jueves'], [5, 'Viernes'], [6, 'Sabado']]
                        hoy = datetime.now().date()
                        data['sumaactividad'] = 0
                        data['suma'] = 0
                        bloquear = todaslasactividades.filter(id=criterio).first().total_claseactividades() == 0
                        actividades = 0
                        actividades_dia_turno = []
                        actividades_marcadas_criterio = []
                        detalleimpartir = todaslasactividades.filter(criteriodocenciaperiodo__criterio_id=118).values('id').first()
                        banderaimpartir = detalleimpartir and criterio == detalleimpartir['id']
                        detalletecnicotransversal = todaslasactividades.filter(criteriodocenciaperiodo__criterio_id=185).values('id').first()
                        banderatecnicotransversal = detalletecnicotransversal and criterio == detalletecnicotransversal['id']
                        data['detalleimpartir'] = detalleimpartir = detalleimpartir['id'] if banderaimpartir else detalletecnicotransversal['id'] if banderatecnicotransversal else 0
                        detalletutoria = todaslasactividades.filter(criteriodocenciaperiodo__criterio_id=124).values('id').first()
                        data['detalletutoria'] = detalletutoria['id'] if detalletutoria else 0

                        if claseactividad := ClaseActividad.objects.filter(detalledistributivo__distributivo__profesor=profesor,
                                                                       detalledistributivo__distributivo__periodo=periodo,
                                                                       status=True):
                            for actividad in claseactividad:
                                if not actividad.actividaddetallehorario:
                                    actividad.actividaddetallehorario = actividad.detalledistributivo.detalleactividadcriterio()
                                    actividad.save()
                                if actividad.actividaddetallehorario:
                                    if actividad.actividaddetallehorario.criterio_vigente():
                                        actividades += 1
                                        if criterio == actividad.detalledistributivo.id:
                                            actividades_marcadas_criterio.append(
                                                int('{}{}'.format(actividad.dia, actividad.turno_id)))
                                        else:
                                            actividades_dia_turno.append(
                                                int('{}{}'.format(actividad.dia, actividad.turno_id)))

                            data['suma'] = suma = claseactividad.filter(tipodistributivo=1,
                                                                            detalledistributivo__criteriodocenciaperiodo__criterio__procesotutoriaacademica=True).distinct().count()
                        clase = Clase.objects.filter(
                            Q(status=True, activo=True, profesor=profesor, materia__nivel__periodo=periodo,
                              materia__nivel__periodo__visible=True, materia__nivel__periodo__visiblehorario=True),
                            Q(Q(fin__gte=hoy))).exclude(tipoprofesor_id=5).distinct().order_by('turno__inicio')
                        if distributivo.carrera and distributivo.carrera.mi_coordinacion2() == 1:
                            clase = Clase.objects.filter(status=True, activo=True, profesor=profesor, materia__nivel__periodo__visible=True, materia__nivel__periodo__visiblehorario=True, fin__gte=datetime.now().date()).distinct().order_by('turno__inicio')
                        clase = clase.filter(fin__gte=datetime.now().date()).exclude(tipoprofesor_id=5).exclude(materia__asignaturamalla__malla__carrera__coordinacion=7).exclude(materia__inicio__gt=datetime.now().date())
                        actividades += int(clase.values('dia', 'turno').distinct().count())
                        if banderatecnicotransversal:
                            clase = clase.filter(Q(tipoprofesor_id=22) | Q(materia__asignaturamalla__transversal=True))
                        for cl in clase.values('dia', 'turno').exclude().distinct():
                            if criterio == detalleimpartir:
                                bloquear = True
                                actividades_marcadas_criterio.append(int('{}{}'.format(cl['dia'], cl['turno'])))
                            else:
                                actividades_dia_turno.append(int('{}{}'.format(cl['dia'], cl['turno'])))

                        # materias_transversal = profesor.profesormateria_set.filter(materia__nivel__periodo=periodo,
                        #                                                            materia__modeloevaluativo_id__in=[27,64],
                        #                                                            hasta__gte=hoy, activo=True)
                        # if materias_transversal:
                        #     if not clase.filter(materia__modeloevaluativo_id__in=[27,64]):
                        #         actividades += int(materias_transversal.aggregate(total=Sum('hora'))['total'])
                        if detalletutoria and criterio == detalletutoria['id'] and not bloquear:
                            actividades_dia_turno += turno_turoria(periodo, profesor)
                        data['actividades'] = actividades
                        horastotales = DetalleDistributivo.objects.filter(
                            Q(distributivo__profesor=profesor, distributivo__periodo=periodo),
                            Q(criteriodocenciaperiodo_id__isnull=False) | Q(
                                criterioinvestigacionperiodo_id__isnull=False) | Q(
                                criteriogestionperiodo_id__isnull=False)).exclude(
                            criteriodocenciaperiodo__criterio_id__in=['15', '16', '17', '18', '20', '21', '27', '28', '30',
                                                                      '46', '7']).values('horas').aggregate(valor=Sum('horas'))['valor']

                        data['horastotales'] = int(horastotales) if horastotales else 0
                        data['completo'] = horastotales >= actividades if distributivo.carrera.mi_coordinacion2() == 1 else horastotales == actividades
                        data['director'] = distributivo.carrera.get_director(periodo) if distributivo.carrera else None
                        data['aprobado'] = ClaseActividadEstado.objects.filter(profesor=profesor, periodo=periodo, status=True, estadosolicitud=2).order_by('-id').exists()
                        data['finalizado'] = claseactividad.exists() and not claseactividad.filter(finalizado=False).exists() or distributivo.horariofinalizado
                        data['horas'] = horas = 9 if distributivo.dedicacion_id == TIEMPO_DEDICACION_TIEMPO_COMPLETO_ID else 5
                        actividades_dia_turno += verificar_limite_dia(claseactividad, horas)
                        data['bloquear'] = bloquear
                        data['actividades_dia_turno'] = list(set(actividades_dia_turno))
                        data['actividades_marcadas_criterio'] = list(set(actividades_marcadas_criterio))
                        data['actividadesfinales'] = claseactividad
                        actualiza_vigencia_criterios_docente(distributivo)
                        return render(request, "pro_horarios/addhorarioactividades.html", data)
                    except Exception as ex:
                        return HttpResponseRedirect("/?info=Error en la transaccion. {}".format(ex))
            except Exception as ex:
                return JsonResponse({"result": "bad", "mensj": u"Error en la transaccion. {}".format(ex)})
            return HttpResponseRedirect("/")
        else:
            try:
                data['title'] = u'Horario de clases'
                data['profesor'] = profesor
                # if not PeriodoAcademia.objects.values("id").filter(periodo=periodo, status=True).exists():
                #     raise NameError(u"Periodo académico no configurado")
                data['DEBUG'] = DEBUG
                return render(request, "pro_horarios/view.html", data)
            except Exception as ex:
                data['msg_error'] = ex.__str__()
                return render(request, "pro_horarios/error.html", data)


def get_all_day_turn():
    try:
        dias_turnos = []
        turnos = Turno.objects.filter(status=True, sesion_id=20, mostrar=True).distinct().order_by('comienza')
        for dia in range(1, 6):
            for turno in turnos:
                dias_turnos.append(int('{}{}'.format(dia, turno.id)))
        return dias_turnos
    except:
        return []


def turno_turoria(periodo, profesor):
    try:
        todos_turnos_dia = get_all_day_turn()
        turnosparatutoria = Turno.objects.filter(status=True, sesion_id=20, mostrar=True).distinct().order_by(
            'comienza')
        idturnos = []
        idturnoscomplexivo = []
        idturnoactividades = []
        idturnostutoria = []
        idmatriculas = []
        idmaterias_matricula = []
        idturnos_matricula = []
        profesormaterias = ProfesorMateria.objects.filter(profesor=profesor, materia__nivel__periodo=periodo,
                                                          activo=True).distinct()
        idmaterias = profesormaterias.values_list('materia_id')
        for dia in range(1, 6):
            if dia == 5:
                print(1)
            for profemate in profesormaterias:
                idmatriculas += MateriaAsignada.objects.values_list('matricula_id').filter(
                    materia=profemate.materia,
                    status=True, estado_id=3,
                    materia__asignaturamalla__nivelmalla=profemate.materia.asignaturamalla.nivelmalla).exclude(
                    materia__asignaturamalla__malla_id__in=[353, 22]).distinct()
                idmaterias_matricula = MateriaAsignada.objects.values_list('materia_id').filter(
                    matricula_id__in=idmatriculas,
                    status=True, estado_id=3,
                    materia__asignaturamalla__nivelmalla=profemate.materia.asignaturamalla.nivelmalla).exclude(
                    materia__asignaturamalla__malla_id__in=[353, 22]).distinct().distinct()

            if Clase.objects.values_list('turno__id').filter(status=True, activo=True,
                                                             materia__nivel__periodo=periodo,
                                                             materia_id__in=idmaterias_matricula, dia=dia).exists():
                idturnos_matricula = Clase.objects.values_list('turno__id').filter(status=True, activo=True,
                                                                                   materia__nivel__periodo=periodo,
                                                                                   materia_id__in=idmaterias_matricula,
                                                                                   dia=dia).distinct()

            if Clase.objects.values_list('turno__id').filter(status=True, activo=True,
                                                             materia__nivel__periodo=periodo,
                                                             materia_id__in=idmaterias, dia=dia).exists():
                idturnos = Clase.objects.values_list('turno__id').filter(status=True, activo=True,
                                                                         materia__nivel__periodo=periodo,
                                                                         materia_id__in=idmaterias, dia=dia).distinct()

            if ComplexivoClase.objects.values_list('turno__id').filter(activo=True,
                                                                       materia__profesor__profesorTitulacion=profesor,
                                                                       materia__status=True, dia=dia).exists():
                idturnoscomplexivo = ComplexivoClase.objects.values_list('turno__id').filter(activo=True,
                                                                                             materia__profesor__profesorTitulacion=profesor,
                                                                                             materia__status=True,
                                                                                             dia=dia).distinct()

            if ClaseActividad.objects.filter(detalledistributivo__distributivo__periodo=periodo,
                                             detalledistributivo__distributivo__profesor=profesor, dia=dia).exists():
                idturnoactividades = ClaseActividad.objects.values_list('turno__id').filter(
                    detalledistributivo__distributivo__periodo=periodo,
                    detalledistributivo__distributivo__profesor=profesor, dia=dia).distinct()
            else:
                if ClaseActividad.objects.values_list('turno__id').filter(
                        actividaddetalle__criterio__distributivo__periodo=periodo,
                        actividaddetalle__criterio__distributivo__profesor=profesor, dia=dia).exists():
                    idturnoactividades = ClaseActividad.objects.values_list('turno__id').filter(
                        actividaddetalle__criterio__distributivo__periodo=periodo,
                        actividaddetalle__criterio__distributivo__profesor=profesor, dia=dia).distinct()
            if HorarioTutoriaAcademica.objects.filter(status=True, dia=dia, profesor=profesor,
                                                      periodo=periodo).exists():
                idturnostutoria = HorarioTutoriaAcademica.objects.values_list('turno_id').filter(status=True, dia=dia,
                                                                                                 profesor=profesor,
                                                                                                 periodo=periodo).distinct()
            turnoclases = Turno.objects.filter(Q(id__in=idturnos) |
                                               Q(id__in=idturnoscomplexivo) |
                                               Q(id__in=idturnoactividades) |
                                               Q(id__in=idturnostutoria) |
                                               Q(id__in=idturnos_matricula)
                                               ).distinct().values_list('id', flat=True)
            for dt in turnosparatutoria.exclude(id__in=turnoclases).values_list('id', flat=True):
                todos_turnos_dia.remove(int('{}{}'.format(dia, dt)))

        return todos_turnos_dia
    except:
        return []


def verificar_turno_tutoria(dia, periodo, profesor, turno_id):
    try:
        turnosparatutoria = Turno.objects.filter(status=True, sesion_id=20, mostrar=True).distinct().order_by('comienza')
        idturnos = []
        idturnoscomplexivo = []
        idturnoactividades = []
        idturnostutoria = []
        idmatriculas = []
        idmaterias_matricula = []
        idturnos_matricula = []
        profesormaterias = ProfesorMateria.objects.filter(profesor=profesor, materia__nivel__periodo=periodo,
                                                          activo=True).distinct()
        idmaterias = profesormaterias.values_list('materia_id')
        for profemate in profesormaterias:
            idmatriculas += MateriaAsignada.objects.values_list('matricula_id').filter(
                materia=profemate.materia,
                status=True, estado_id=3,
                materia__asignaturamalla__nivelmalla=profemate.materia.asignaturamalla.nivelmalla).exclude(
                materia__asignaturamalla__malla_id__in=[353, 22]).distinct()
            idmaterias_matricula = MateriaAsignada.objects.values_list('materia_id').filter(
                matricula_id__in=idmatriculas,
                status=True, estado_id=3,
                materia__asignaturamalla__nivelmalla=profemate.materia.asignaturamalla.nivelmalla).exclude(
                materia__asignaturamalla__malla_id__in=[353, 22]).distinct().distinct()

        if Clase.objects.values_list('turno__id').filter(status=True, activo=True,
                                                         materia__nivel__periodo=periodo,
                                                         materia_id__in=idmaterias_matricula, dia=dia).exists():
            idturnos_matricula = Clase.objects.values_list('turno__id').filter(status=True, activo=True,
                                                                               materia__nivel__periodo=periodo,
                                                                               materia_id__in=idmaterias_matricula,
                                                                               dia=dia).distinct()

        if Clase.objects.values_list('turno__id').filter(status=True, activo=True,
                                                         materia__nivel__periodo=periodo,
                                                         materia_id__in=idmaterias, dia=dia).exists():
            idturnos = Clase.objects.values_list('turno__id').filter(status=True, activo=True,
                                                                     materia__nivel__periodo=periodo,
                                                                     materia_id__in=idmaterias, dia=dia).distinct()

        if ComplexivoClase.objects.values_list('turno__id').filter(activo=True,
                                                                   materia__profesor__profesorTitulacion=profesor,
                                                                   materia__status=True, dia=dia).exists():
            idturnoscomplexivo = ComplexivoClase.objects.values_list('turno__id').filter(activo=True,
                                                                                         materia__profesor__profesorTitulacion=profesor,
                                                                                         materia__status=True,
                                                                                         dia=dia).distinct()

        if ClaseActividad.objects.filter(detalledistributivo__distributivo__periodo=periodo,
                                         detalledistributivo__distributivo__profesor=profesor, dia=dia).exists():
            idturnoactividades = ClaseActividad.objects.values_list('turno__id').filter(
                detalledistributivo__distributivo__periodo=periodo,
                detalledistributivo__distributivo__profesor=profesor, dia=dia).distinct()
        else:
            if ClaseActividad.objects.values_list('turno__id').filter(
                    actividaddetalle__criterio__distributivo__periodo=periodo,
                    actividaddetalle__criterio__distributivo__profesor=profesor, dia=dia).exists():
                idturnoactividades = ClaseActividad.objects.values_list('turno__id').filter(
                    actividaddetalle__criterio__distributivo__periodo=periodo,
                    actividaddetalle__criterio__distributivo__profesor=profesor, dia=dia).distinct()
        if HorarioTutoriaAcademica.objects.filter(status=True, dia=dia, profesor=profesor,
                                                  periodo=periodo).exists():
            idturnostutoria = HorarioTutoriaAcademica.objects.values_list('turno_id').filter(status=True, dia=dia,
                                                                                             profesor=profesor,
                                                                                             periodo=periodo).distinct()
        turnoclases = Turno.objects.filter(Q(id__in=idturnos) |
                                           Q(id__in=idturnoscomplexivo) |
                                           Q(id__in=idturnoactividades) |
                                           Q(id__in=idturnostutoria) |
                                           Q(id__in=idturnos_matricula)
                                           ).distinct().values_list('id', flat=True)
        return turnosparatutoria.filter(id=turno_id).exclude(id__in=turnoclases).values_list('id', flat=True).exists()
    except:
        return False


def verificar_limite_dia(query, limite):
    try:
        claseactividad = query.values('dia').annotate(total=Count('id')).exclude(total__lt=limite)
        if not claseactividad:
            return []
        dias_turnos = []
        turnos = Turno.objects.filter(status=True, sesion_id=20, mostrar=True).distinct().order_by('comienza')
        for dia in claseactividad:
            for turno in turnos:
                dias_turnos.append(int('{}{}'.format(dia['dia'], turno.id)))
        return dias_turnos
    except:
        return []
