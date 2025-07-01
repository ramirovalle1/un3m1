# -*- coding: UTF-8 -*-
from django.contrib.auth.decorators import login_required
from django.db import transaction
# from django.db.models import Q
from django.http import HttpResponseRedirect, JsonResponse, HttpResponse
from django.shortcuts import render
from decorators import secure_module
from sga.commonviews import adduserdata
from sga.funciones import MiPaginador, log, variable_valor, convertir_fecha_hora, convertir_fecha, convertir_hora, \
    convertir_fecha_hora_invertida, notificacion, generar_nombre, convertir_fecha_invertida
from inno.models import HorarioTutoriaAcademica, SolicitudTutoriaIndividual, SolicitudTutoriaIndividualTema, \
    ESTADO_SOLICITUD_TUTORIA, RegistroClaseTutoriaDocente, DetalleSolicitudHorarioTutoria
from sga.models import DetalleDistributivo, ClaseActividad, Turno, ComplexivoClase, Clase, ProfesorMateria, \
    MateriaAsignada, Materia, DetalleSilaboSemanalTema, Matricula, miinstitucion, Silabo, \
    UnidadResultadoProgramaAnalitico, CoordinadorCarrera, Periodo
from inno.forms import TutoriaManualForm, ProgramarTutoriasForm, ConvocarTutoriaManualForm, JustificarTutoriaForm
from django.db.models import Q, Sum
from datetime import datetime, timedelta, date
from django.template.loader import get_template
from sga.templatetags.sga_extras import encrypt
import json
from django.template import Context
from sga.tasks import send_html_mail, conectar_cuenta
from django.db.models.aggregates import Count
from django.db.models import Max, Min
from django.db import models, connection, connections
import io
import xlsxwriter
from typing import Any, Hashable, Iterable, Optional


def buscar_dicc(it: Iterable[dict], clave: Hashable, valor: Any) -> Optional[dict]:
    for dicc in it:
        if dicc[clave] == valor:
            return dicc
    return None


def daterange(start_date, end_date):
    for n in range(int((end_date - start_date).days)):
        yield start_date + timedelta(days=n)


@login_required(redirect_field_name='ret', login_url='/loginsga')
@secure_module
@transaction.atomic()
def view(request):
    data = {}
    adduserdata(request, data)
    data['periodo'] = periodo = request.session['periodo']
    persona = request.session['persona']
    perfilprincipal = request.session['perfilprincipal']
    if not perfilprincipal.es_profesor():
        return HttpResponseRedirect("/?info=Solo los perfiles de profesores pueden ingresar al modulo.")
    data['profesor'] = profesor = perfilprincipal.profesor
    data['fecha_actual'] = hoy = datetime.now().date()
    data['hora_actual'] = datetime.now().time()
    if ProfesorMateria.objects.filter(status=True, profesor=profesor,
                                      materia__nivel__periodo=periodo,
                                      activo=True).exists():
        cant1 = ProfesorMateria.objects.values('id').filter(status=True, profesor=profesor,
                                                            materia__nivel__periodo=periodo,
                                                            activo=True,
                                                            tipoprofesor__id__in=[8]).count()
        cant2 = ProfesorMateria.objects.values('id').filter(status=True, profesor=profesor,
                                                            materia__nivel__periodo=periodo,
                                                            activo=True).count()
        if cant1 == cant2:
            return HttpResponseRedirect("/?info=Solo profesores que no sean Tutores Virtual pueden acceder a este módulo.")
    else:
        return HttpResponseRedirect("/?info=Solo profesores que tengan asignado materias pueden acceder a este módulo.")

    if not DetalleDistributivo.objects.filter(distributivo__profesor=profesor,
                                              distributivo__periodo=periodo,
                                              criteriodocenciaperiodo__criterio__procesotutoriaacademica=True).exists():
        return HttpResponseRedirect("/?info=SOLO LOS DOCENTES QUE TENGAN LA ACTIVIDAD DE:  ORIENTAR Y ACOMPAÑAR A ESTUDIANTES A TRAVÉS DE TUTORÍAS INDIVIDUALES O GRUPALES EN LAS MODALIDADES DE ESTUDIO QUE LA IES CONSIDERE PERTINENTE.")

    if request.method == 'POST':
        data['action'] = action = request.POST['action']

        if action == 'buscarturnos':
            try:
                profmaterias = None

                if not request.POST.get('dia'):
                    return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos. Dia incorrecto"})

                dia = int(request.POST['dia'])
                if periodo.tipo_id in [3, 4]:
                    turnosadd = Turno.objects.filter(status=True, sesion_id__in=(15, 19)).order_by('comienza')
                    profmaterias = ProfesorMateria.objects.filter(status=True, profesor=profesor, materia__nivel__periodo=periodo, activo=True)
                else:
                    turnosparatutoria = Turno.objects.filter(status=True, sesion_id__in=(15, 19)).distinct().order_by('comienza')
                    idturnos = []
                    idturnoscomplexivo = []
                    idturnoactividades = []
                    idturnostutoria = []
                    idmatriculas = []
                    idmaterias_matricula = []
                    idturnos_matricula = []
                    profesormaterias = ProfesorMateria.objects.filter(profesor=profesor, materia__nivel__periodo=periodo, activo=True).distinct()
                    idmaterias = profesormaterias.values_list('materia_id')

                    for profemate in profesormaterias:
                        idmatriculas += MateriaAsignada.objects.values_list('matricula_id').filter(
                            materia=profemate.materia,
                            status=True, estado_id=3,
                            materia__asignaturamalla__nivelmalla=profemate.materia.asignaturamalla.nivelmalla).exclude(materia__asignaturamalla__malla_id__in=[353, 22]).distinct()
                        idmaterias_matricula = MateriaAsignada.objects.values_list('materia_id').filter(
                            matricula_id__in=idmatriculas,
                            status=True, estado_id=3,
                            materia__asignaturamalla__nivelmalla=profemate.materia.asignaturamalla.nivelmalla).exclude(materia__asignaturamalla__malla_id__in=[353, 22]).distinct().distinct()

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
                                                                                                     materia__status=True, dia=dia).distinct()

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
                    if HorarioTutoriaAcademica.objects.filter(status=True, dia=dia, profesor=profesor, periodo=periodo).exists():
                        idturnostutoria = HorarioTutoriaAcademica.objects.values_list('turno_id').filter(status=True, dia=dia, profesor=profesor, periodo=periodo).distinct()
                    turnoclases = Turno.objects.filter(Q(id__in=idturnos) |
                                                       Q(id__in=idturnoscomplexivo) |
                                                       Q(id__in=idturnoactividades) |
                                                       Q(id__in=idturnostutoria) |
                                                       Q(id__in=idturnos_matricula)
                                                       ).distinct().order_by('comienza')

                    idturnosadd = []
                    for turnotutoria in turnosparatutoria:
                        for turnoclase in turnoclases:
                            if turnotutoria.comienza <= turnoclase.termina and turnotutoria.termina >= turnoclase.comienza:
                                idturnosadd.append(turnotutoria.id)

                    turnosadd = Turno.objects.filter(status=True, sesion_id__in=(15, 19)).exclude(id__in=idturnosadd).distinct().order_by('comienza')

                lista, lista_materias = [], []

                for turno in turnosadd:
                    turno_comienza, turno_termina = turno.comienza.strftime("%H:%M %p"), turno.termina.strftime("%H:%M %p")
                    if periodo.tipo_id in [3, 4]:
                        if turno.sesion_id == 19:
                            lista.append([turno.id, f'Turno {turno.turno} [{turno_comienza} a {turno_termina}]'])
                    else:
                        lista.append([turno.id, f'Turno {turno.turno} [{turno_comienza} a {turno_termina}]'])

                for profmateria in profmaterias:
                    lista_materias.append([profmateria.id, profmateria.materia.nombre_mostrar_solo()])

                return JsonResponse({'result': 'ok', 'lista': lista, 'lista_materias':lista_materias})
            except Exception as ex:
                return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

        elif action == 'edithorariotutoria':
            try:
                pm = ProfesorMateria.objects.get(pk=request.POST['idprofmate'])

                fi = request.POST.get('fi', '')
                ff = request.POST.get('ff', '')

                if not fi or not ff:
                    return JsonResponse({'result': 'bad', 'mensaje': u'Algunos campos se encuentran vacíos.'})

                fi = convertir_fecha_invertida(fi)
                ff = convertir_fecha_invertida(ff)

                if not ff >= fi:
                    return JsonResponse({'result': 'bad', 'mensaje': u'La fecha fin no puede ser menor que la fecha de inicio.'})

                fecha_min_limite = pm.materia.inicio
                fecha_max_limite = periodo.get_periodoacademia().fecha_fin_horario_tutoria if periodo.get_periodoacademia().fecha_fin_horario_tutoria else pm.materia.fin

                if fi < fecha_min_limite:
                    return JsonResponse({'result': 'bad',
                                         'mensaje': u'La fecha de inicio ingresada es menor a la fecha (%s) que corresponde al inicio de la materia.' % fecha_min_limite.strftime('%d-%m-%Y')})

                if ff > fecha_max_limite:
                    return JsonResponse({'result': 'bad',
                                         'mensaje': u'La fecha fin ingresada es mayor a la fecha (%s) que corresponde a la fecha fin de la tutoría académica.' % fecha_max_limite.strftime('%d-%m-%Y')})


                horario = HorarioTutoriaAcademica.objects.get(pk=request.POST['id_tutoria'])
                if not HorarioTutoriaAcademica.objects.values('id').filter(dia=horario.dia, turno=horario.turno, profesormateria=pm, fecha_inicio_horario_tutoria=fi, fecha_fin_horario_tutoria=ff, status=True).exists():
                    horario.fecha_inicio_horario_tutoria, horario.fecha_fin_horario_tutoria = fi, ff
                    horario.profesormateria = pm
                    horario.save()
                    return JsonResponse({"result": "ok"})
                else:
                    return JsonResponse({'result': 'bad',
                                         'mensaje': u'Ya existe un horario de tutoría registrado en esta fecha.'})


            except Exception as ex:
                pass

        elif action == 'addhorariotutoria':
            try:
                iddia = int(request.POST['iddia'])
                turno = Turno.objects.get(id=request.POST['idturno'])
                promateria = ProfesorMateria.objects.get(id=request.POST['idprofmate'])
                fi = request.POST.get('fi', '')
                ff = request.POST.get('ff', '')

                if not fi or not ff:
                    return JsonResponse({'result': 'bad', 'mensaje': f"El campo {'fecha inicio' if not fi else 'fecha fin'} se encuentra vacíos."})

                fi = convertir_fecha_invertida(fi)
                ff = convertir_fecha_invertida(ff)

                if not ff > fi:
                    return JsonResponse({'result': 'bad', 'mensaje': u'La fecha fin no puede ser menor que la fecha de inicio.'})

                fecha_min_limite = promateria.materia.inicio
                fecha_max_limite = periodo.get_periodoacademia().fecha_fin_horario_tutoria if periodo.get_periodoacademia().fecha_fin_horario_tutoria else promateria.materia.fin

                if fi < fecha_min_limite:
                    return JsonResponse({'result':'bad', 'mensaje':u'La fecha de inicio ingresada es menor a la fecha [%s] que corresponde al inicio de la materia.' % fecha_min_limite.strftime('%d-%m-%Y')})

                if ff > fecha_max_limite:
                    return JsonResponse({'result':'bad', 'mensaje':u'La fecha fin ingresada es mayor a la fecha [%s] que corresponde a la fecha fin de la tutoría académica.' % fecha_max_limite.strftime('%d-%m-%Y')})

                # suma = 0a
                # sumaactividad = 2
                if not HorarioTutoriaAcademica.objects.filter(status=True, profesor=profesor, periodo=periodo, dia=iddia, turno__comienza=turno.comienza, turno__termina=turno.termina, profesormateria=promateria, fecha_inicio_horario_tutoria=fi, fecha_fin_horario_tutoria=ff).exists():
                    # if HorarioTutoriaAcademica.objects.filter(status=True, profesor=profesor, periodo=periodo, profesormateria=promateria).exists():
                    #     suma = HorarioTutoriaAcademica.objects.filter(status=True, profesor=profesor, periodo=periodo, profesormateria=promateria).aggregate(total=Sum('turno__horas'))['total']
                    # if DetalleDistributivo.objects.filter(distributivo__profesor=profesor,
                    #                                       distributivo__periodo=periodo,
                    #                                       criteriodocenciaperiodo__criterio_id__in=[7]).exists():
                    #     sumaactividad = DetalleDistributivo.objects.filter(distributivo__profesor=profesor,
                    #                                                        distributivo__periodo=periodo,
                    #                                                        criteriodocenciaperiodo__criterio_id__in=[7]).aggregate(total=Sum('horas'))['total']
                    #
                    # if int(suma) < int(sumaactividad):
                    horario = HorarioTutoriaAcademica(profesor=profesor,
                                                      periodo=periodo,
                                                      dia=iddia,
                                                      turno=turno,
                                                      profesormateria=promateria,
                                                      fecha_inicio_horario_tutoria=fi,
                                                      fecha_fin_horario_tutoria=ff)
                    horario.save(request)
                    log(u'Ingreso un horario de tutoría académica: %s' % horario, request, "add")
                    return JsonResponse({"result": "ok"})
                    # else:
                    #     return JsonResponse({"result": "bad", "mensaje": u"Ya cumple con sus horas de tutoria planificada."})
                else:
                    return JsonResponse({"result": "bad", "mensaje": u"Ya existe un horario ingresado."})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'delhorario':
            try:
                horario = HorarioTutoriaAcademica.objects.get(id=int(encrypt(request.POST['id'])))
                exed = True if 'max' in request.POST and request.POST['max'] == '1' else False
                if horario.en_uso() and not exed:
                    return JsonResponse({"result": "bad", "mensaje": u"Ya existen horario creado."})
                horario.status = False
                horario.save(request)
                log(u'Eliminó un horario de tutoría académica: %s' % horario, request, "add")
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'buscarhorario':
            try:
                idmateria = int(request.POST['idmateria'])
                materia = Materia.objects.get(id=idmateria)
                lista = []
                listatema = []
                for tema in DetalleSilaboSemanalTema.objects.filter(status=True,
                                                                    silabosemanal__silabo__materia=materia,
                                                                    # silabosemanal__silabo__profesor=profesor,
                                                                    silabosemanal__silabo__status=True,
                                                                    silabosemanal__fechainiciosemana__lte=datetime.now().date()).distinct():
                    listatema.append([tema.id, u'Sem: %s - %s (%s / %s)' % (tema.silabosemanal.numsemana,
                                                                            tema.temaunidadresultadoprogramaanalitico.descripcion,
                                                                            tema.silabosemanal.fechainiciosemana,
                                                                            tema.silabosemanal.fechafinciosemana,)])

                for materiaasig in MateriaAsignada.objects.filter(status=True, materia=materia).distinct().order_by('matricula__inscripcion__persona'):
                    lista.append([materiaasig.matricula.id, u'%s' % materiaasig.matricula])

                return JsonResponse({'result': 'ok', 'lista': lista, 'listatema': listatema})
            except Exception as ex:
                return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

        elif action == 'agregartutoriamanual':
            try:
                if int(request.POST['topico']) == 0:
                    return JsonResponse({"result": "bad", "mensaje": u"Debe seleccionar topico."})
                if int(request.POST['tipo']) == 0:
                    return JsonResponse({"result": "bad", "mensaje": u"Debe seleccionar el tipo de tutoría."})
                estudiantes = None
                materiaasignadas = None
                todos = 'off'
                if 'todos' in request.POST:
                    todos = request.POST['todos']

                if todos == 'off':
                    estudiantes = request.POST.getlist('estudiantes')
                    if int(request.POST['tipo']) == 1 and estudiantes.__len__() <= 0:
                        return JsonResponse({"result": "bad", "mensaje": u"Debe seleccionar al menos un estudiante para tutoria individual ."})

                    if int(request.POST['tipo']) == 1 and estudiantes.__len__() > 1:
                        return JsonResponse({"result": "bad", "mensaje": u"Tiene más de un estudiante seleccionado, le recomendamos que seleccione tipo de tutoría grupal."})
                    if int(request.POST['tipo']) == 2 and estudiantes.__len__() <= 1:
                        return JsonResponse({"result": "bad", "mensaje": u"Debe seleccionar más de un estudiante para tutoria grupal ."})
                elif todos == 'on':
                    if int(request.POST['tipo']) == 1:
                        return JsonResponse({"result": "bad", "mensaje": u"Le recomendamos que seleccione tipo de tutoría grupal, ya que selecciono todos los matriculados en la asignatura."})
                    materiaasignadas = MateriaAsignada.objects.filter(status=True, matricula__nivel__periodo=periodo, materia=request.POST['materia'], retiramateria=False)
                if int(request.POST['topico']) == 1 and int(request.POST['tema']) <= 0:
                    return JsonResponse({"result": "bad", "mensaje": u"Debe seleccionar al menos un tema ."})

                if todos == 'off':
                    for matriculaid in estudiantes:
                        matricula = Matricula.objects.get(id=int(matriculaid))
                        if MateriaAsignada.objects.filter(status=True, matricula=matricula, materia=request.POST['materia']).exists():
                            materiaasignada = MateriaAsignada.objects.get(status=True, matricula=matricula, materia=request.POST['materia'])
                            solicitud = SolicitudTutoriaIndividual(
                                profesor=profesor, estado=3,
                                materiaasignada=materiaasignada,
                                topico=request.POST['topico'],
                                fechatutoria=convertir_fecha_hora(u"%s %s" % (request.POST['fechatutoria'], request.POST['hora'])),
                                asistencia=True,
                                observacion=request.POST['observacion'],
                                tipo=request.POST['tipo'], manual=True, tipotutoria=4)
                            solicitud.save(request)

                            if int(request.POST['topico']) == 1:
                                if not SolicitudTutoriaIndividualTema.objects.filter(solicitud=solicitud, tema_id=request.POST['tema']).exists():
                                    tema = SolicitudTutoriaIndividualTema(solicitud=solicitud,
                                                                          tema_id=request.POST['tema'])
                                    tema.save(request)
                elif todos == 'on':
                    for materiaasignada in materiaasignadas:
                        solicitud = SolicitudTutoriaIndividual(
                            profesor=profesor, estado=3,
                            materiaasignada=materiaasignada,
                            topico=request.POST['topico'],
                            fechatutoria=convertir_fecha_hora(
                                u"%s %s" % (request.POST['fechatutoria'], request.POST['hora'])),
                            asistencia=True,
                            observacion=request.POST['observacion'],
                            tipo=request.POST['tipo'], manual=True, tipotutoria=4)
                        solicitud.save(request)

                        if int(request.POST['topico']) == 1:
                            if not SolicitudTutoriaIndividualTema.objects.filter(solicitud=solicitud,
                                                                                 tema_id=request.POST['tema']).exists():
                                tema = SolicitudTutoriaIndividualTema(solicitud=solicitud,
                                                                      tema_id=request.POST['tema'])
                                tema.save(request)
                log(u'Adiciono solicitud de tutoria academica el docente:', request, "add")
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'delsolicitud':
            try:
                solicitud = SolicitudTutoriaIndividual.objects.get(pk=int(encrypt(request.POST['id'])))
                if solicitud.manual:
                    solicitud.status = False
                    solicitud.save(request)
                    log(u'Eliminó solicitud de tutoria academica manual: %s' % solicitud, request, "edit")
                    return JsonResponse({'result': 'ok'})
                else:
                    return JsonResponse({"result": "bad", "mensaje": u"Error, la solicitud no se puede eliminar."})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

        elif action == 'validafecha':
            try:
                horario = HorarioTutoriaAcademica.objects.get(pk=int(request.POST['horario']))
                fecha = convertir_fecha(request.POST['fecha'])
                if horario.dia != fecha.isoweekday():
                    return JsonResponse({"result": "bad", "mensaje": u"No puede seleccionar esta fecha, no coincide el día."})
                else:
                    return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

        elif action == 'validahora':
            try:
                horario = HorarioTutoriaAcademica.objects.get(pk=int(request.POST['horario']))
                tutoriacomienza = convertir_hora(request.POST['tutoriacomienza'])
                tutoriatermina = convertir_hora(request.POST['tutoriatermina'])
                if tutoriacomienza <= horario.turno.termina and tutoriatermina >= horario.turno.comienza:
                    return JsonResponse({"result": "ok"})
                else:
                    return JsonResponse({"result": "bad",
                                         "mensaje": u"No puede seleccionar ese horario, no esta dentro del horario de las solicitudes."})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

        elif action == 'programarsolicitudes':
            try:
                solicitudes = SolicitudTutoriaIndividual.objects.filter(id__in=[int(x) for x in request.POST['ids'].split(',')])
                horario = solicitudes[0].horario
                tutoriacomienza = convertir_hora(request.POST['tutoriacomienza'])
                tutoriatermina = convertir_hora(request.POST['tutoriatermina'])
                fecha = convertir_fecha(request.POST['fechatutoria'])
                if horario.dia != fecha.isoweekday():
                    raise NameError(u"No puede seleccionar esta fecha, no coincide el día.")
                if tutoriacomienza >= horario.turno.comienza and tutoriatermina <= horario.turno.termina and tutoriatermina > tutoriacomienza:
                    for solicitud in solicitudes:
                        solicitud.fechatutoria = fecha
                        if solicitud.estado != 2:
                            solicitud.estado = 2
                        solicitud.tutoriacomienza = tutoriacomienza
                        solicitud.tutoriatermina = tutoriatermina
                        solicitud.save(request)
                        send_html_mail("Solicitud de tutoría",
                                       "emails/programadasolicitudtutoriaestudiante.html",
                                       {'sistema': u'SGA - UNEMI',
                                        'fecha': datetime.now().date(),
                                        'hora': datetime.now().time(),
                                        'solicitud': solicitud,
                                        't': miinstitucion()
                                        },
                                       solicitud.materiaasignada.matricula.inscripcion.persona.lista_emails_envio(),
                                       [],
                                       cuenta=variable_valor('CUENTAS_CORREOS')[0]
                                       )
                        log(u'Programo tutorías masivo: %s' % solicitud, request, "edit")
                    return JsonResponse({'result': 'ok'})
                else:
                    return JsonResponse({"result": "bad", "mensaje": u"No puede seleccionar ese horario, no esta dentro del horario de las solicitudes."})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos. %s" % ex})
        elif action == 'reprogramarsolicitudes':
            try:
                solicitudes = SolicitudTutoriaIndividual.objects.filter(id__in=[int(x) for x in request.POST['ids'].split(',')])
                if solicitudes[0].tipotutoria == 1:
                    horario = solicitudes[0].horario
                    tutoriacomienza = convertir_hora(request.POST['tutoriacomienza'])
                    tutoriatermina = convertir_hora(request.POST['tutoriatermina'])
                    fecha = convertir_fecha(request.POST['fechatutoria'])
                    if horario.dia != fecha.isoweekday():
                        return JsonResponse({"result": "bad", "mensaje": u"No puede seleccionar esta fecha, no coincide el día."})
                    if tutoriacomienza >= horario.turno.comienza and tutoriatermina <= horario.turno.termina and tutoriatermina > tutoriacomienza:
                        for solicitud in solicitudes:
                            solicitud.fechatutoria = fecha
                            if solicitud.estado != 2:
                                solicitud.estado = 2
                            solicitud.tutoriacomienza = tutoriacomienza
                            solicitud.tutoriatermina = tutoriatermina
                            solicitud.save(request)
                            send_html_mail("Reprogramacion de solicitud de tutoría",
                                           "emails/reprogramadasolicitudtutoriaestudiante.html",
                                           {'sistema': u'SGA - UNEMI',
                                            'fecha': datetime.now().date(),
                                            'hora': datetime.now().time(),
                                            'solicitud': solicitud,
                                            't': miinstitucion()
                                            },
                                           solicitud.materiaasignada.matricula.inscripcion.persona.lista_emails_envio(),
                                           [],
                                           cuenta=variable_valor('CUENTAS_CORREOS')[0]
                                           )
                            log(u'Programo tutorías masivo: %s' % solicitud, request, "edit")
                        return JsonResponse({'result': 'ok'})
                    else:
                        return JsonResponse({"result": "bad", "mensaje": u"No puede seleccionar ese horario, no esta dentro del horario de las solicitudes."})
                else:
                    tutoriacomienza = convertir_hora(request.POST['tutoriacomienza'])
                    tutoriatermina = convertir_hora(request.POST['tutoriatermina'])
                    fecha = convertir_fecha(request.POST['fechatutoria'])
                    for solicitud in solicitudes:
                        solicitud.fechatutoria = fecha
                        solicitud.tutoriacomienza = tutoriacomienza
                        solicitud.tutoriatermina = tutoriatermina
                        solicitud.save(request)
                        send_html_mail("Reprogramacion de solicitud de tutoría",
                                       "emails/reprogramadasolicitudtutoriaestudiante.html",
                                       {'sistema': u'SGA - UNEMI',
                                        'fecha': datetime.now().date(),
                                        'hora': datetime.now().time(),
                                        'solicitud': solicitud,
                                        't': miinstitucion()
                                        },
                                       solicitud.materiaasignada.matricula.inscripcion.persona.lista_emails_envio(),
                                       [],
                                       cuenta=variable_valor('CUENTAS_CORREOS')[0]
                                       )
                        log(u'Programo tutorías masivo: %s' % solicitud, request, "edit")
                    return JsonResponse({'result': 'ok'})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

        elif action == 'cancelarsolicitud':
            try:
                solicitud = SolicitudTutoriaIndividual.objects.get(pk=request.POST['id'])
                solicitud.estado = 4
                solicitud.observacion = request.POST['id_observacion']
                solicitud.save(request)
                log(u"cambia estado a programado tutoria: %s" % solicitud, request, "edit")
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al cancelar solicitud."})

        elif action == 'ingresarobservacion':
            try:
                solicitud = SolicitudTutoriaIndividual.objects.get(pk=request.POST['id_solicitud'])
                solicitud.observacion = request.POST['id_observacion']
                solicitud.respuestapregunta = True if int(request.POST['id_respuestapregunta']) == 1 else False
                solicitud.save(request)
                # if int(request.POST['id_respuestapregunta']) == 1:
                #     lista = []
                #     lista.append("jplacesc@unemi.edu.ec")
                #     send_html_mail("Solicitud de tutoría",
                #                    "emails/programadasolicitudtutoriaestudiante.html",
                #                    {'sistema': u'SGA - UNEMI',
                #                     'fecha': datetime.now().date(),
                #                     'hora': datetime.now().time(),
                #                     'solicitud': solicitud,
                #                     't': miinstitucion()
                #                     },
                #                    # persona.lista_emails_envio(),
                #                    lista,
                #                    [],
                #                    cuenta=variable_valor('CUENTAS_CORREOS')[0]
                #                    )

                log(u"Ingresa observación en tutoria ejecutada: %s" % solicitud, request, "edit")
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al eliminar los datos."})

        elif action == 'establecer_fechas':
            try:
                horario = HorarioTutoriaAcademica.objects.get(id=int(request.POST['id_horario']))
                hoy = fechaestimada = datetime.now().date()
                numerodia = horario.dia
                horaactual = datetime.now().time()
                horahorario = horario.turno.comienza
                carga = 0
                if hoy.isoweekday() == numerodia:
                    if horaactual.hour <= horahorario.hour:
                        carga = 1
                if hoy.isoweekday() != numerodia or carga == 0:
                    for days in range(8):
                        hoy = hoy + timedelta(days=1)
                        if hoy.isoweekday() == numerodia:
                            fechaestimada = hoy
                            break
                return JsonResponse({'result': 'ok', 'fechaestimada': fechaestimada,
                                     'comienza': horario.turno.comienza,
                                     'termina': horario.turno.termina})
            except Exception as ex:
                return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

        elif action == 'convocartutoriamanual':
            try:
                if int(request.POST['topico']) == 0:
                    raise NameError(u"Debe seleccionar topico.")
                if int(request.POST['tipo']) == 0:
                    raise NameError(u"Debe seleccionar el tipo de tutoría.")
                fecha = convertir_fecha(request.POST['fechatutoria'])
                if fecha < hoy:
                    raise NameError(u"No puede seleccionar uan fecha menor a la de hoy.")
                estudiantes = None
                materiaasignadas = None
                todos = 'off'
                if 'todos' in request.POST:
                    todos = request.POST['todos']

                if todos == 'off':
                    estudiantes = request.POST.getlist('estudiantes')
                    if int(request.POST['tipo']) == 1 and estudiantes.__len__() <= 0:
                        raise NameError(u"Debe seleccionar al menos un estudiante para tutoria individual.")

                    if int(request.POST['tipo']) == 1 and estudiantes.__len__() > 1:
                        raise NameError(u"Tiene más de un estudiante seleccionado, le recomendamos que seleccione tipo de tutoría grupal.")

                    if int(request.POST['tipo']) == 2 and estudiantes.__len__() <= 1:
                        raise NameError(u"Debe seleccionar más de un estudiante para tutoria grupal.")

                elif todos == 'on':
                    if int(request.POST['tipo']) == 1:
                        raise NameError(u"Le recomendamos que seleccione tipo de tutoría grupal, ya que selecciono todos los matriculados en la asignatura.")
                    materiaasignadas = MateriaAsignada.objects.filter(status=True, matricula__nivel__periodo=periodo, materia=request.POST['materia'], retiramateria=False)
                if int(request.POST['topico']) == 1 and int(request.POST['tema']) <= 0:
                    raise NameError(u"Debe seleccionar al menos un tema.")
                tutoriacomienza = convertir_hora(request.POST['tutoriacomienza'])
                tutoriatermina = convertir_hora(request.POST['tutoriatermina'])

                if todos == 'off':
                    for matriculaid in estudiantes:
                        matriculagrupo = Matricula.objects.get(id=int(matriculaid))
                        materiaasignada = None
                        if MateriaAsignada.objects.filter(status=True, matricula=matriculagrupo, materia=request.POST['materia'], retiramateria=False).exists():
                            materiaasignada = MateriaAsignada.objects.get(status=True, matricula=matriculagrupo, materia=request.POST['materia'])
                            solicitud = SolicitudTutoriaIndividual(
                                profesor=profesor,
                                materiaasignada=materiaasignada,
                                estado=2,
                                topico=request.POST['topico'],
                                fechatutoria=fecha,
                                tutoriacomienza=tutoriacomienza,
                                tutoriatermina=tutoriatermina,
                                asistencia=False,
                                tipo=request.POST['tipo'],
                                manual=True, tipotutoria=2)
                            solicitud.save(request)

                            if int(request.POST['topico']) == 1:
                                if not SolicitudTutoriaIndividualTema.objects.filter(solicitud=solicitud, tema_id=request.POST['tema']).exists():
                                    tema = SolicitudTutoriaIndividualTema(solicitud=solicitud,
                                                                          tema_id=request.POST['tema'])
                                    tema.save(request)
                elif todos == 'on':
                    for materiaasignada in materiaasignadas:
                        solicitud = SolicitudTutoriaIndividual(
                            profesor=profesor,
                            materiaasignada=materiaasignada,
                            estado=2,
                            topico=request.POST['topico'],
                            fechatutoria=fecha,
                            tutoriacomienza=tutoriacomienza,
                            tutoriatermina=tutoriatermina,
                            asistencia=False,
                            tipo=request.POST['tipo'],
                            manual=True, tipotutoria=2)
                        solicitud.save(request)

                        if int(request.POST['topico']) == 1:
                            if not SolicitudTutoriaIndividualTema.objects.filter(solicitud=solicitud,
                                                                                 tema_id=request.POST['tema']).exists():
                                tema = SolicitudTutoriaIndividualTema(solicitud=solicitud,
                                                                      tema_id=request.POST['tema'])
                                tema.save(request)

                log(u'Adiciono solicitud de tutoria academica el docente:', request, "add")
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos. %s" % ex})

        elif action == 'addclasetutoria':
            try:
                d = datetime.now()
                tutoria_seleccionada = SolicitudTutoriaIndividual.objects.get(id=int(request.POST['idtuto']))
                if not RegistroClaseTutoriaDocente.objects.filter(numerosemana=datetime.today().isocalendar()[1],
                                                                  fecha=convertir_fecha_hora_invertida(u"%s %s" % (tutoria_seleccionada.fechatutoria.date(), tutoria_seleccionada.tutoriacomienza)),
                                                                  tipotutoria=tutoria_seleccionada.tipotutoria,
                                                                  status=True, periodo=periodo,
                                                                  profesor=profesor):
                    clasetutoria = RegistroClaseTutoriaDocente(numerosemana=datetime.today().isocalendar()[1],
                                                               fecha=convertir_fecha_hora_invertida(u"%s %s" % (tutoria_seleccionada.fechatutoria.date(), tutoria_seleccionada.tutoriacomienza)),
                                                               tipotutoria=tutoria_seleccionada.tipotutoria, periodo=periodo,
                                                               profesor=profesor)
                    clasetutoria.save(request)

                horario_todos = HorarioTutoriaAcademica.objects.filter(status=True, periodo=periodo,
                                                                       profesor=profesor, dia=d.isoweekday()).order_by('turno__comienza')
                for horario_insertar in horario_todos:
                    if not RegistroClaseTutoriaDocente.objects.filter(horario=horario_insertar,
                                                                      numerosemana=datetime.today().isocalendar()[1],
                                                                      status=True, fecha__date=datetime.now().date()):
                        clasetutoria = RegistroClaseTutoriaDocente(horario=horario_insertar,
                                                                   numerosemana=datetime.today().isocalendar()[1],
                                                                   fecha=datetime.now())
                        clasetutoria.save(request)
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})
                pass

        elif action == 'matriculados':
            try:
                data['materia'] = materia = Materia.objects.get(pk=int(request.POST['id']))
                try:
                    data['silabocab'] = silabocab = Silabo.objects.get(status=True, codigoqr=True, materia=materia)
                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje": u"La asignatura no tiene silabo."})
                lista = request.POST['lista']
                data['temas'] = DetalleSilaboSemanalTema.objects.filter(status=True, silabosemanal__status=True,
                                                                        silabosemanal__silabo__status=True, id__in=[int(x) for x in lista.split(',')],
                                                                        silabosemanal__silabo=silabocab).order_by('silabosemanal__numsemana', 'temaunidadresultadoprogramaanalitico__unidadresultadoprogramaanalitico__orden', 'temaunidadresultadoprogramaanalitico__orden')
                data['materiasasignadas'] = materia.materiaasignada_set.filter(status=True, retiramateria=False).order_by('matricula__inscripcion__persona__apellido1', 'matricula__inscripcion__persona__apellido2', 'matricula__inscripcion__persona__nombres')
                # data['materiasasignadas']=materia.materiaasignada_set.filter(status=True,retiramateria=False)[:5]
                template = get_template("pro_tutoriaacademica/matriculados.html")
                json_content = template.render(data)
                return JsonResponse({"result": "ok", 'html': json_content})
            except Exception as ex:
                return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

        elif action == 'buscartemas':
            try:
                data['materia'] = materia = Materia.objects.get(pk=int(request.POST['id']))
                try:
                    data['silabocab'] = silabocab = Silabo.objects.get(status=True, codigoqr=True, materia=materia)
                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje": u"La asignatura no tiene silabo aprobado por el director."})
                data['unidades'] = unidades = UnidadResultadoProgramaAnalitico.objects.filter(id__in=silabocab.unidades_seleccionadas()).distinct().order_by('orden')
                # data['temas'] = DetalleSilaboSemanalTema.objects.filter(status=True, silabosemanal__status=True,
                #                                         silabosemanal__silabo__status=True,
                #                                                         silabosemanal__silabo=silabocab).order_by('silabosemanal__numsemana','temaunidadresultadoprogramaanalitico__unidadresultadoprogramaanalitico__orden','temaunidadresultadoprogramaanalitico__orden')
                template = get_template("pro_tutoriaacademica/tema.html")
                json_content = template.render(data)
                return JsonResponse({"result": "ok", 'html': json_content})
            except Exception as ex:
                return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

        elif action == 'ver_actividades_tema':
            try:
                data['detalle'] = DetalleSilaboSemanalTema.objects.get(pk=int(request.POST['id']))
                template = get_template("pro_tutoriaacademica/ver_actividades_tema.html")
                json_content = template.render(data)
                return JsonResponse({"result": "ok", 'html': json_content})
            except Exception as ex:
                return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

        elif action == 'guardatutoriacalculada':
            try:
                if not 'lista' in request.POST:
                    return JsonResponse({"result": "bad", "mensaje": u"Debe seleccionar al menos un estudiante."})
                lista = json.loads(request.POST['lista'])
                tutoriacomienza = convertir_hora(request.POST['tutoriacomienza'])
                tutoriatermina = convertir_hora(request.POST['tutoriatermina'])
                fecha = convertir_fecha(request.POST['fechatutoria'])
                if fecha < datetime.now().date():
                    return JsonResponse({"result": "bad", "mensaje": u"Debe seleccionar una fecha mayor o igual a la fecha actual."})
                if tutoriacomienza == tutoriatermina:
                    return JsonResponse({"result": "bad", "mensaje": u"La hora que inicia la tutoría no debe ser igual la hora que finaliza la tutoría."})
                aux = 0
                solicitud = None
                for elemento in lista:
                    idma = int(elemento['idma'])
                    idprom = float(elemento['idprom'])
                    if idma != aux:
                        aux = int(elemento['idma'])
                        materiaasignada = MateriaAsignada.objects.get(id=idma)
                        if not SolicitudTutoriaIndividual.objects.filter(status=True,
                                                                         profesor=profesor,
                                                                         materiaasignada=materiaasignada,
                                                                         estado=2, topico=1,
                                                                         fechatutoria=fecha,
                                                                         tutoriacomienza=tutoriacomienza,
                                                                         tutoriatermina=tutoriatermina, tipotutoria=3).exists():
                            solicitud = SolicitudTutoriaIndividual(
                                profesor=profesor,
                                materiaasignada=materiaasignada,
                                estado=2, topico=1,
                                fechatutoria=fecha,
                                tutoriacomienza=tutoriacomienza,
                                tutoriatermina=tutoriatermina,
                                asistencia=False,
                                tipo=2,
                                manual=True, tipotutoria=3, promedio_actividad=idprom)
                            solicitud.save(request)
                        else:
                            transaction.set_rollback(True)
                            return JsonResponse({"result": "bad", "mensaje": u"No puede seleccionar el estudiante %s ya que tiene una tutoría programada en la misma fecha" % materiaasignada.matricula.inscripcion.persona})
                    if solicitud:
                        if not SolicitudTutoriaIndividualTema.objects.filter(solicitud=solicitud, tema_id=int(elemento['idtema'])).exists():
                            tema = SolicitudTutoriaIndividualTema(solicitud=solicitud,
                                                                  tema_id=int(elemento['idtema']))
                            tema.save(request)

                log(u'Realiza acción de convocar tutoría calculada:', request, "add")
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'verestudiantes':
            try:
                fecha = request.POST['fecha']
                tipo = request.POST['idtipo']
                data['estudiantes'] = SolicitudTutoriaIndividual.objects.values('materiaasignada__matricula__inscripcion__persona__nombres', 'materiaasignada__matricula__inscripcion__persona__apellido1', 'materiaasignada__matricula__inscripcion__persona__apellido2').filter(status=True,
                                                                                                                                                                                                                                                                                  estado=2,
                                                                                                                                                                                                                                                                                  tipotutoria=tipo,
                                                                                                                                                                                                                                                                                  profesor=profesor,
                                                                                                                                                                                                                                                                                  materiaasignada__matricula__nivel__periodo=periodo, fechatutoria=convertir_fecha(fecha)).distinct()
                template = get_template("pro_tutoriaacademica/verestudiantes.html")
                json_content = template.render(data)
                return JsonResponse({"result": "ok", 'html': json_content})
            except Exception as ex:
                return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

        elif action == 'modificar_tutoria_calculada':
            try:
                valor = int(request.POST['valor'])
                solicitud = SolicitudTutoriaIndividual.objects.get(status=True, id=int(request.POST['idtutoria']))
                if valor == 1:
                    solicitud.estado = 4
                elif valor == 2:
                    solicitud.estado = 3
                    solicitud.asistencia = True
                solicitud.save(request)
                log(u'Modifica tutoria calculada: %s' % solicitud, request, "edit")
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'asitenciamanual':
            try:
                pk = int(encrypt(request.POST['pk']))
                solictud = SolicitudTutoriaIndividual.objects.get(id=pk)
                solictud.asistencia = True
                solictud.asistenciamanual = True
                solictud.justificacionasistencia = str(request.POST['justificacion']).upper()
                solictud.estado = 3
                solictud.save(request)
                log(u'Ingreso asistencia manual: %s' % solictud, request, "edit")
                return JsonResponse({"result": "ok"})
            except Exception as e:
                return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos. %s" % str(e)})

        elif action == 'asitenciamanualmasivo':
            try:
                listadosolicitudes = SolicitudTutoriaIndividual.objects.filter(status=True, profesor=profesor, materiaasignada__matricula__nivel__periodo=periodo, estado=4).order_by('estado', '-fecha_creacion')
                for listado in listadosolicitudes:
                    listado.asistencia = True
                    listado.asistenciamanual = True
                    listado.justificacionasistencia = str(request.POST['justificacion']).upper()
                    listado.estado = 3
                    listado.save(request)
                log(u'Ingreso asistencia masiva: %s' % listado, request, "edit")
                return JsonResponse({"result": "ok"})
            except Exception as e:
                return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos. %s" % str(e)})

        elif action == 'addsolicitudhorario':
            try:
                director = request.POST['iddirector']
                if not DetalleSolicitudHorarioTutoria.objects.filter(periodo=periodo, profesor=profesor, director=director, estadosolicitud=1).exists():
                    solicitudhorario = DetalleSolicitudHorarioTutoria(periodo=periodo, profesor=profesor, director_id=director, observacion=request.POST['observacion'])
                    solicitudhorario.save(request)
                    asunto = u"SOLICITUD DE HORARIO DE TUTORIA ACADEMICA "
                    observacion = 'Se le comunica que el docente: {} de la carrera: {} en el periodo {} le ha solicitado una nueva fecha para cargar el horario de tutoria. Para acceder debe selecionar el periodo correspondiente y el perfil administrativo'.format(
                        profesor.persona, solicitudhorario.director.carrera, periodo.nombre)
                    notificacion(asunto, observacion, solicitudhorario.director.persona, None,
                                 '/adm_criteriosactividadesdocente?s=' + str(solicitudhorario.profesor.persona.apellido1) + '%20' + str(solicitudhorario.profesor.persona.apellido2) + '&idc=0',
                                 solicitudhorario.pk, 1, 'sga', DetalleSolicitudHorarioTutoria, request)
                    log(u'Ingreso solicitud para subir horario de tutorias: %s' % solicitudhorario, request, "add")
                    return JsonResponse({"result": "ok"})
                return JsonResponse({"result": "bad", "mensaje": u"Ya existe una solicitud pendiente de este docente."})
            except Exception as e:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos. %s" % str(e)})

        elif action == 'justificartutoria':
            try:
                form = JustificarTutoriaForm(request.POST)
                nfileDocumento = None
                eFiles = request.FILES
                if 'archivoevidencia' in eFiles:
                    nfileDocumento = eFiles['archivoevidencia']
                    extensionDocumento = nfileDocumento._name.split('.')
                    tamDocumento = len(extensionDocumento)
                    exteDocumento = extensionDocumento[tamDocumento - 1]
                    if nfileDocumento.size > 15000000:
                        raise NameError(u"Error al cargar, el archivo es mayor a 15 Mb.")
                    if not exteDocumento.lower() == 'pdf':
                        raise NameError(u"Error al cargar, solo se permiten archivos .pdf")
                    nfileDocumento._name = generar_nombre("evidencia_justificacion_tutoria", nfileDocumento._name)
                if form.is_valid():
                    fecha = convertir_fecha(request.POST['fecha'])
                    actividadestutoria = ClaseActividad.objects.filter(status=True,
                                                                       detalledistributivo__distributivo__profesor=profesor,
                                                                       detalledistributivo__distributivo__periodo=periodo,
                                                                       detalledistributivo__criteriodocenciaperiodo__isnull=False,
                                                                       detalledistributivo__criteriodocenciaperiodo__criterio__procesotutoriaacademica=True)
                    # for horario in HorarioTutoriaAcademica.objects.filter(status=True, id__in=request.POST['horario']):
                    for horario in form.cleaned_data['horario']:
                        if horario.dia == fecha.isoweekday():
                            cantasissemana = RegistroClaseTutoriaDocente.objects.filter(numerosemana=fecha.isocalendar()[1], horario__profesor=profesor, horario__periodo=periodo).aggregate(total=Count('id'))['total']
                            if len(actividadestutoria) > cantasissemana or not RegistroClaseTutoriaDocente.objects.filter(horario=horario, numerosemana=fecha.isocalendar()[1], fecha__date=fecha).exists():
                                clasetutoria = RegistroClaseTutoriaDocente(horario=horario, numerosemana=fecha.isocalendar()[1], fecha=fecha, justificacionasistencia=form.cleaned_data['justificacionasistencia'], archivoevidencia=nfileDocumento, estadojustificacion=1)
                                clasetutoria.save()
                                log(u'Agregó justificación de asitencia en tutoria : %s' % clasetutoria, request, "add")
                    return JsonResponse({"error": False})
                else:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})
            except Exception as e:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": f"{e}"})

        elif action == 'editvideotutoriaacademica':
            try:
                r = RegistroClaseTutoriaDocente.objects.get(pk=request.POST.get('pk'))
                r.enlaceuno = request.POST.get('enlace1')
                r.save(request, update_fields=['enlaceuno'])

                return JsonResponse({'result': 'ok'})
            except Exception as ex:
                pass

        return JsonResponse({"result": "bad", "mensaje": u"Solicitud Incorrecta."})
    else:
        if 'action' in request.GET:
            data['action'] = action = request.GET['action']

            if action == 'get_materia_date':
                try:
                    pm = ProfesorMateria.objects.get(pk=request.GET['pk'])
                    return JsonResponse({'result': 'ok', 'fi': pm.materia.inicio, 'ff': pm.materia.fin})
                except Exception as ex:
                    pass

            if action == 'registrarhorario':
                try:
                    data['title'] = u'Horario de profesor'
                    nivel = periodo.nivel_set.filter(status=True).first()
                    es_posgrado = False
                    if nivel and nivel.coordinacion():
                        es_posgrado = nivel.coordinacion().id == 7

                    semana = [[1, 'Lunes'], [2, 'Martes'], [3, 'Miercoles'], [4, 'Jueves'], [5, 'Viernes'], [6, 'Sábado']]
                    if es_posgrado or periodo.es_posgrado():
                        semana.append([7, 'Domingo'])

                    data['semana'] = semana
                    data['sumaactividad'] = 0
                    data['suma'] = 0
                    if periodo.clasificacion != 2:
                        return HttpResponseRedirect("/?info=Esta opción está disponible solo para docentes en periodo de posgrado.")
                    periodoacademia = periodo.periodo_academia()
                    if DetalleDistributivo.objects.filter(distributivo__profesor=profesor,
                                                          distributivo__periodo=periodo,
                                                          criteriodocenciaperiodo__criterio_id__in=[7]).exists():
                        data['sumaactividad'] = int(DetalleDistributivo.objects.filter(distributivo__profesor=profesor,
                                                                                       distributivo__periodo=periodo,
                                                                                       criteriodocenciaperiodo__criterio_id__in=[7]).aggregate(total=Sum('horas'))['total'])
                    idturnostutoria = []
                    turnosparatutoria = None
                    if HorarioTutoriaAcademica.objects.filter(status=True, profesor=profesor, periodo=periodo).exists():
                        horarios = HorarioTutoriaAcademica.objects.filter(status=True, profesor=profesor, periodo=periodo)
                        data['suma'] = int(horarios.aggregate(total=Sum('turno__horas'))['total'])
                        idturnostutoria = horarios.values_list('turno_id').distinct()
                        turnosparatutoria = Turno.objects.filter(status=True, sesion_id__in=(15, 19), id__in=idturnostutoria).distinct().order_by('comienza')
                    data['turnos'] = turnosparatutoria
                    data['puede_ver_horario'] = periodo.visible == True and periodo.visiblehorario == True
                    data['puede_registrar'] = False
                    data['solicitud'] = solicitud = periodo.solicitud_horario_tutoria_docente(profesor)
                    carrera = profesor.profesordistributivohoras_set.filter(periodo=periodo).first()
                    data['director'] = CoordinadorCarrera.objects.filter(carrera=carrera.carrera, periodo=periodo, tipo=3).first()
                    if periodo.periodo_academia():
                        fecha_limite_tutoria = periodo.periodo_academia().fecha_limite_horario_tutoria
                        if fecha_limite_tutoria:
                            data['puede_registrar'] = datetime.now().date() <= fecha_limite_tutoria
                        elif solicitud:
                            if solicitud.fecha and (solicitud.fecha >= datetime.now().date() and solicitud.estadosolicitud == 1):
                                data['puede_registrar'] = True
                            elif solicitud.fecha and (solicitud.fecha <= datetime.now().date() and solicitud.estadosolicitud == 1):
                                data['solicitud_caduca'] = True

                    data['diahoy'] = datetime.now().date().isoweekday()
                    return render(request, "pro_tutoriaacademica/registrarhorario.html", data)
                except Exception as ex:
                    import sys
                    return HttpResponseRedirect(f"{request.path}?info={ex.__str__()}. Line {sys.exc_info()[-1].tb_lineno}")

            elif action == 'delhorario':
                try:
                    data['title'] = u'Eliminar horario'
                    data['horario'] = HorarioTutoriaAcademica.objects.get(pk=int(encrypt(request.GET['id'])), status=True)
                    data['max'] = 1 if 'max' in request.GET and request.GET['max'] == '1' else 0
                    return render(request, "pro_tutoriaacademica/delhorario.html", data)
                except Exception as ex:
                    pass

            elif action == 'agregartutoriamanual':
                try:
                    data['title'] = u'Registrar tutorias manual'
                    form = TutoriaManualForm()
                    form.iniciar(periodo, profesor)
                    if 'd' in request.GET:
                        form.initial['fechatutoria'] = convertir_fecha(encrypt(request.GET['d']))
                        form.fields['materia'].initial = [int(encrypt(request.GET['m']))]
                        data['exit'] = 'verregistrotutorias&materia=%s' %(int(encrypt(request.GET['m'])))
                    data['form'] = form
                    return render(request, "pro_tutoriaacademica/agregartutoriamanual.html", data)
                except Exception as ex:
                    pass


            elif action == 'verregistrotutorias':
                try:
                    data['title'] = u'Ver registro de tutorias no ejecutadas'
                    form = TutoriaManualForm()
                    form.iniciar(periodo, profesor)
                    url_vars = ''
                    if not 'materia' in request.GET:
                        data['materia'] = materia = Materia.objects.filter(id__in=ProfesorMateria.objects.values_list('materia_id').filter(profesor=profesor, materia__nivel__periodo=periodo).distinct()).exclude(asignaturamalla__malla_id__in=[353, 22]).first()
                    else:
                        url_vars = "&materia={}".format(request.GET['materia'])
                        data['materia'] = materia = Materia.objects.get(pk=int((request.GET['materia'])))

                    listanoejecutadas = periodo.tutoriasdocenteposgrado_v2(profesor, materia)

                    if listanoejecutadas:
                        data['listaFecha'] = listanoejecutadas[3]
                    else:
                        data['msg'] = True

                    form.fields['materia'].initial = [materia.id]
                    data['form'] = form
                    data['url_vars'] = url_vars
                    return render(request, "pro_tutoriaacademica/verregistrotutorias.html", data)
                except Exception as ex:
                    return HttpResponseRedirect("/pro_tutoriaacademica?info=%s" % ex.__str__())

            elif action == 'programarsolicitudes':
                try:
                    data['title'] = u'SOLICITUDES A PROGRAMAR'
                    data['solicitudes'] = solicitudes = SolicitudTutoriaIndividual.objects.filter(id__in=[int(x) for x in request.GET['listasolicitudes'].split(',')])
                    if solicitudes.values_list('horario_id', flat=True).distinct().count() > 1:
                        return HttpResponseRedirect("/pro_tutoriaacademica?info=Debe seleccionar solicitudes de estudiantes con un mismo horario.")
                    if solicitudes.values_list('topico', flat=True).distinct().count() > 1:
                        return HttpResponseRedirect("/pro_tutoriaacademica?info=Debe seleccionar solicitudes de estudiantes con un mismo tópico.")
                    if SolicitudTutoriaIndividualTema.objects.values_list('tema_id', flat=True).filter(solicitud_id__in=solicitudes.values('id')).distinct().count() > 1:
                        return HttpResponseRedirect("/pro_tutoriaacademica?info=Debe seleccionar solicitudes de estudiantes con un mismo tema.")
                    if solicitudes.values_list('materiaasignada__materia', flat=True).distinct().count() > 1:
                        return HttpResponseRedirect("/pro_tutoriaacademica?info=Debe seleccionar solicitudes de estudiantes de una asignatura.")

                    form = ProgramarTutoriasForm(initial={'horario': solicitudes[0].horario,
                                                          'tema': solicitudes[0].temas()[0].tema if solicitudes[0].temas() else None,
                                                          'tutoriacomienza': solicitudes[0].horario.turno.comienza,
                                                          'tutoriatermina': solicitudes[0].horario.turno.termina,
                                                          'fechatutoria': solicitudes[0].fechatutoria,
                                                          })
                    form.iniciar(solicitudes)
                    data['form'] = form
                    data['listasolicitudes'] = request.GET['listasolicitudes']
                    return render(request, "pro_tutoriaacademica/programarsolicitudes.html", data)
                except Exception as ex:
                    return HttpResponseRedirect("/pro_tutoriaacademica?info=%s" % ex.__str__())

            elif action == 'reprogramarsolicitudes':
                try:
                    data['title'] = u'SOLICITUDES A REPROGRAMAR'
                    data['solicitudes'] = solicitudes = SolicitudTutoriaIndividual.objects.filter(id__in=[int(x) for x in request.GET['listasolicitudes'].split(',')])
                    if solicitudes.values_list('horario_id', flat=True).distinct().count() > 1:
                        return HttpResponseRedirect("/pro_tutoriaacademica?info=Debe seleccionar solicitudes de estudiantes con un mismo horario.")
                    if solicitudes.values_list('topico', flat=True).distinct().count() > 1:
                        return HttpResponseRedirect("/pro_tutoriaacademica?info=Debe seleccionar solicitudes de estudiantes con un mismo tópico.")
                    if SolicitudTutoriaIndividualTema.objects.values_list('tema_id', flat=True).filter(solicitud_id__in=solicitudes.values('id')).distinct().count() > 1:
                        return HttpResponseRedirect("/pro_tutoriaacademica?info=Debe seleccionar solicitudes de estudiantes con un mismo tema.")
                    if solicitudes.values_list('materiaasignada__materia', flat=True).distinct().count() > 1:
                        return HttpResponseRedirect("/pro_tutoriaacademica?info=Debe seleccionar solicitudes de estudiantes de una asignatura.")
                    if solicitudes[0].tipotutoria == 1:
                        form = ProgramarTutoriasForm(initial={'horario': solicitudes[0].horario,
                                                              'tema': solicitudes[0].temas()[0].tema if solicitudes[0].temas() else None,
                                                              'tutoriacomienza': solicitudes[0].horario.turno.comienza,
                                                              'tutoriatermina': solicitudes[0].horario.turno.termina,
                                                              'fechatutoria': solicitudes[0].fechatutoria,
                                                              })
                        form.iniciar(solicitudes)
                    else:
                        form = ProgramarTutoriasForm(initial={'tema': solicitudes[0].temas()[0].tema if solicitudes[0].temas() else None,
                                                              'fechatutoria': solicitudes[0].fechatutoria,
                                                              })
                        form.iniciarsinhorario(solicitudes)
                    # form.iniciar(solicitudes)
                    data['form'] = form
                    data['listasolicitudes'] = request.GET['listasolicitudes']
                    return render(request, "pro_tutoriaacademica/reprogramarsolicitudes.html", data)
                except Exception as ex:
                    pass

            elif action == 'delsolicitud':
                try:
                    data['title'] = u'Eliminar solicitud'
                    data['solicitud'] = SolicitudTutoriaIndividual.objects.get(pk=int(encrypt(request.GET['id'])))
                    return render(request, "pro_tutoriaacademica/delsolicitud.html", data)
                except Exception as ex:
                    pass

            # elif action == 'finalizar':
            #     try:
            #         data['title'] = u'Finalizar solicitud'
            #         data['solicitud'] = SolicitudTutoriaIndividual.objects.get(pk=int(encrypt(request.GET['id'])))
            #         return render(request, "pro_tutoriaacademica/finalizar.html", data)
            #     except Exception as ex:
            #         pass

            elif action == 'convocartutoriamanual':
                try:
                    data['title'] = u'Convocar tutorias'
                    form = ConvocarTutoriaManualForm()
                    form.iniciar(periodo, profesor)
                    data['form'] = form
                    return render(request, "pro_tutoriaacademica/convocartutoriamanual.html", data)
                except Exception as ex:
                    pass

            elif action == 'tutoriacalculada':
                try:
                    data['title'] = u'Tutorías calculada'
                    data['materias'] = Materia.objects.filter(id__in=ProfesorMateria.objects.values_list('materia_id').filter(
                        profesor=profesor,
                        materia__nivel__periodo=periodo,
                    ).distinct()).exclude(asignaturamalla__malla_id__in=[353, 22])
                    return render(request, "pro_tutoriaacademica/tutoriacalculada.html", data)
                except Exception as ex:
                    return HttpResponseRedirect("/?info=Error. %s" % ex)

            elif action == 'vertutoriaconvocada':
                try:
                    data['title'] = 'Ver tutorías convocadas'
                    data['profesor'] = profesor
                    data['periodo'] = periodo
                    data['tutorias'] = SolicitudTutoriaIndividual.objects.values('tipotutoria', 'fechatutoria',
                                                                                 'tutoriacomienza',
                                                                                 'tutoriatermina').filter(status=True,
                                                                                                          estado=2,
                                                                                                          tipotutoria__in=[2, 3],
                                                                                                          profesor=profesor,
                                                                                                          materiaasignada__matricula__nivel__periodo=periodo
                                                                                                          ).annotate(total=Count('id')).annotate(id=Max('id')).order_by('tipotutoria', 'fechatutoria').distinct()

                    return render(request, "pro_tutoriaacademica/vertutoriaconvocada.html", data)
                except Exception as ex:
                    return HttpResponseRedirect("/?info=Error. %s" % ex)

            elif action == 'buscaralumnos':
                try:
                    if not 'lista' in request.GET:
                        return JsonResponse({"result": "bad", "mensaje": u"Debe seleccionar al menos un estudiante."})
                    lista = json.loads(request.GET['lista'])
                    listama = []
                    materiaasignada = None
                    for elemento in lista:
                        listama.append(int(elemento['idma']))
                    data['materiaasignadas'] = MateriaAsignada.objects.filter(id__in=listama)
                    template = get_template("pro_tutoriaacademica/buscaralumnos.html")
                    json_content = template.render(data)
                    return JsonResponse({"result": "ok", 'html': json_content})
                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

            elif action == 'ver_detalle_calculo':
                try:
                    data['materiaasignada'] = MateriaAsignada.objects.get(id=request.GET['idma'])
                    data['tema'] = DetalleSilaboSemanalTema.objects.get(id=request.GET['idtema'])
                    template = get_template("pro_tutoriaacademica/ver_detalle_calculo.html")
                    json_content = template.render(data)
                    return JsonResponse({"result": "ok", 'html': json_content})
                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

            elif action == 'cargar_periodo':
                try:
                    lista = []
                    periodos = Periodo.objects.filter(status=True).distinct()

                    for periodo in periodos:
                        if not buscar_dicc(lista, 'id', periodo.id):
                            lista.append({'id': periodo.id, 'nombre': periodo.nombre})
                    return JsonResponse({'result': 'ok', 'lista': lista})
                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})


            elif action == 'reportetutoria':
                try:
                    __author__ = 'Unemi'

                    output = io.BytesIO()
                    workbook = xlsxwriter.Workbook(output)
                    ws = workbook.add_worksheet('tutorias')
                    ws.set_column(0, 0, 30)
                    ws.set_column(1, 1, 20)
                    ws.set_column(2, 2, 45)
                    ws.set_column(3, 3, 60)
                    ws.set_column(4, 4, 25)
                    ws.set_column(5, 5, 20)

                    #                   ws.columm_dimensions['A'].width = 20

                    # formatotitulo = workbook.add_format(
                    #     {'bold': 1, 'text_wrap': True, 'border': 1, 'align': 'center', 'valign': 'middle',
                    #      'fg_color': '#A2D0EC'})
                    formatotitulo_filtros = workbook.add_format(
                        {'bold': 1, 'text_wrap': True, 'border': 1, 'fg_color': '#EBF5FB'})

                    formatoceldacab = workbook.add_format(
                        {'align': 'center', 'bold': 1, 'border': 1, 'text_wrap': True, 'fg_color': '#EBF5FB'})
                    formatoceldaleft = workbook.add_format(
                        {'text_wrap': True, 'align': 'center', 'valign': 'vcenter', 'border': 1})

                    ws.write(0, 0, 'CARRERA', formatoceldacab)
                    ws.write(0, 1, 'CEDULA', formatoceldacab)
                    ws.write(0, 2, 'DOCENTE', formatoceldacab)
                    ws.write(0, 3, 'ASIGNATURA', formatoceldacab)
                    ws.write(0, 4, 'IDENTIFICACIÓN ESTUDIANTE', formatoceldacab)
                    ws.write(0, 5, 'ESTUDIANTE', formatoceldacab)
                    ws.write(0, 6, 'ESTADO', formatoceldacab)

                    periodo = request.GET['periodo']
                    # periodo_nombre = request.GET['periodo_nombre']

                    #                    periodo = Periodo.objects.get(id=119)
                    #                     estado = 3

                    estado = request.GET['estado']

                    solicitudes = SolicitudTutoriaIndividual.objects.filter(status=True, estado=estado,
                                                                            materiaasignada__matricula__nivel__periodo_id=periodo,
                                                                            profesor=profesor).order_by(
                        'profesor__persona__nombres',
                        'profesor__persona__apellido1',
                        'profesor__persona__apellido2',
                        'materiaasignada__materia__asignatura__nombre',
                        'materiaasignada__materia__identificacion',
                        'materiaasignada__materia__paralelo')
                    filas_recorridas = 2
                    for solicitud in solicitudes:
                        est = ""
                        if solicitud.estado == 1:
                            est = "SOLICITADO"
                        if solicitud.estado == 2:
                            est = "PROGRAMADO"
                        if solicitud.estado == 3:
                            est = "EJECUTADO"
                        if solicitud.estado == 4:
                            est = "CANCELADO"

                        ws.write('A%s' % filas_recorridas, str(solicitud.materiaasignada.matricula.inscripcion.carrera), formatoceldaleft)
                        ws.write('B%s' % filas_recorridas, str(solicitud.profesor.persona.identificacion()), formatoceldaleft)
                        ws.write('C%s' % filas_recorridas, str(solicitud.profesor.persona.nombre_completo_inverso()), formatoceldaleft)
                        ws.write('D%s' % filas_recorridas, str(solicitud.materiaasignada.materia.asignatura.nombre + ' - ' + solicitud.materiaasignada.materia.identificacion + ' - ' + solicitud.materiaasignada.materia.paralelo), formatoceldaleft)
                        ws.write('E%s' % filas_recorridas, str(solicitud.materiaasignada.matricula.inscripcion.persona.identificacion()), formatoceldaleft)
                        ws.write('F%s' % filas_recorridas, str(solicitud.materiaasignada.matricula.inscripcion.persona.nombre_completo_inverso()), formatoceldaleft)
                        ws.write('G%s' % filas_recorridas, str(est), formatoceldaleft)

                        filas_recorridas += 1

                    workbook.close()
                    output.seek(0)
                    filename = 'ReporteDeTutorias.xlsx'
                    response = HttpResponse(output,
                                            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
                    response['Content-Disposition'] = 'attachment; filename=%s' % filename
                    return response
                except Exception as ex:
                    pass

            elif action == 'verasistencias':
                try:
                    data['title'] = 'REGISTRO DE CLASES DE TUTORÍAS'
                    data['profesor'] = profesor
                    data['periodo'] = periodo
                    horarios = HorarioTutoriaAcademica.objects.filter(status=True, profesor=profesor, periodo=periodo)
                    if horarios.exists():
                        data['hoy'] = hoy = datetime.now().date()

                        ff_tutoria = periodo.fin
                        if (ff := periodo.get_periodoacademia()) and ff.fecha_fin_horario_tutoria:
                            ff_tutoria = ff.fecha_fin_horario_tutoria
                        elif horarios[0].fecha_fin_horario_tutoria:
                            ff_tutoria = horarios[0].fecha_fin_horario_tutoria

                        data['fecha_inicia_tutoria_horario'] = fecha_inicia_tutoria_horario = periodo.inicio
                        data['fecha_fin_horario_tutoria'] = ff_tutoria
                        data['desde'] = desde = datetime.strptime(request.GET['desde'], '%Y-%m-%d').date() if 'desde' in request.GET else fecha_inicia_tutoria_horario
                        data['hasta'] = hasta = datetime.strptime(request.GET['hasta'], '%Y-%m-%d').date() if 'hasta' in request.GET else ff_tutoria
                        diasnolaborales = periodo.diasnolaborable_set.filter(status=True, activo=True).values_list('fecha', flat=True)
                        data['diasnolaborales'] = []
                        for dia in diasnolaborales:
                            data['diasnolaborales'].append(dia.strftime('%Y-%m-%d'))
                        if hoy >= fecha_inicia_tutoria_horario:
                            cursor = connection.cursor()
                            listadias = horarios.values_list('dia', flat=True)
                            sql = """  SELECT tabla1.fecha,tabla1.dias, 
                                        (
                                        SELECT tab.totalhoras FROM (SELECT dia,COUNT(dia) totalhoras
                                        FROM "inno_horariotutoriaacademica"
                                        INNER JOIN "sga_profesor" ON ("inno_horariotutoriaacademica"."profesor_id" = "sga_profesor"."id")
                                        INNER JOIN "sga_persona" ON ("sga_profesor"."persona_id" = "sga_persona"."id")
                                        WHERE ("inno_horariotutoriaacademica"."periodo_id" = %s AND "inno_horariotutoriaacademica"."profesor_id" = %s AND "inno_horariotutoriaacademica"."status" = TRUE)
                                        GROUP BY dia) AS tab
                                        WHERE dia = tabla1.dias
                                        ) AS totalhoras
                                        FROM (
                                        SELECT fecha, extract(dow from fecha) AS dias FROM (
                                        SELECT 
                                        CURRENT_DATE + generate_series('%s'- CURRENT_DATE, '%s' - CURRENT_DATE ) AS fecha 
                                        ) AS tabla
                                        WHERE extract(dow from fecha) IN %s
                                        ) AS tabla1  """ % (periodo.id, profesor.id,
                                                            # convertir_fecha("28-06-2021"),
                                                            # convertir_fecha("28-06-2021"),
                                                            desde,
                                                            hasta,
                                                            tuple(listadias) if len(listadias) > 1 else u"(%s)" % listadias[0])
                            cursor.execute(sql)
                            data['results'] = cursor.fetchall()
                    data['registroclases'] = RegistroClaseTutoriaDocente.objects.filter((Q(horario__profesor=profesor) | Q(profesor=profesor)) & (Q(periodo=periodo) | Q(horario__periodo=periodo)), status=True).distinct().order_by('fecha', 'numerosemana')
                    data['tienehorario'] = horarios.exists()
                    return render(request, "pro_tutoriaacademica/verasistencias.html", data)
                except Exception as ex:
                    return HttpResponseRedirect("/?info=Error. %s" % ex)

            elif action == 'justificartutoria':
                try:
                    data['fecha'] = fecha = convertir_fecha(request.GET['fecha'])
                    data['dia'] = dia = request.GET['dia']
                    data['horarios'] = horarios = HorarioTutoriaAcademica.objects.filter(status=True, profesor=profesor,
                                                                                         periodo=periodo, dia=dia)
                    if RegistroClaseTutoriaDocente.objects.filter(status=True, horario__profesor=profesor, fecha=fecha).exists():
                        asisatencias = RegistroClaseTutoriaDocente.objects.filter(status=True, horario__profesor=profesor, fecha=fecha).values_list('horario_id')
                        horarios = horarios.exclude(id__in=asisatencias)
                    form = JustificarTutoriaForm()
                    form.asignar_horarios(horarios)
                    data['form'] = form
                    data['action'] = action
                    template = get_template("pro_tutoriaacademica/modal/justificartutoria.html")
                    json_content = template.render(data)
                    return JsonResponse({"result": True, 'html': json_content})
                except Exception as e:
                    print(e)

            return HttpResponseRedirect(request.path)

        else:
            try:
                data['title'] = u'Tutorías académicas'
                search2 = None
                search3 = None
                search4 = None
                solicitudes_a_cancelar = SolicitudTutoriaIndividual.objects.filter(status=True, profesor=profesor,
                                                                                   materiaasignada__matricula__nivel__periodo=periodo,
                                                                                   fechatutoria__date__lt=datetime.now().date(), estado=2).order_by('estado', '-fecha_creacion')

                for tuto_cance in solicitudes_a_cancelar:
                    if tuto_cance.estado != 4 and tuto_cance.estado == 2:
                        tuto_cance.estado = 4
                        tuto_cance.save(request)

                solicitudes = SolicitudTutoriaIndividual.objects.filter(status=True, profesor=profesor,
                                                                        materiaasignada__matricula__nivel__periodo=periodo).order_by(
                    'estado', '-fecha_creacion')
                data['solicitudes_estado1'] = solicitudes.filter(estado=1)
                solicitudes_estado2 = solicitudes.filter(estado=2)
                solicitudes_estado3 = solicitudes.filter(estado=3)
                solicitudes_estado4 = solicitudes.filter(estado=4)

                # PAGINACION PARA ESTADO 2
                if 's2' in request.GET:
                    search2 = request.GET['s2'].strip()
                    ss = search2.split(' ')
                    if len(ss) == 1:
                        solicitudes_estado2 = solicitudes_estado2.filter(
                            Q(materiaasignada__materia__asignatura__nombre__icontains=search2) |
                            Q(materiaasignada__matricula__inscripcion__persona__nombres__icontains=search2) |
                            Q(materiaasignada__matricula__inscripcion__persona__apellido1__icontains=search2) |
                            Q(materiaasignada__matricula__inscripcion__persona__apellido2__icontains=search2),
                            profesor=profesor, status=True).order_by('estado', '-fecha_creacion')
                    else:
                        solicitudes_estado2 = solicitudes_estado2.filter(
                            Q(materiaasignada__matricula__inscripcion__persona__apellido1__icontains=ss[0]) |
                            Q(materiaasignada__matricula__inscripcion__persona__apellido2__icontains=ss[1]),
                            profesor=profesor, status=True).order_by('estado', '-fecha_creacion')
                paging_estado2 = MiPaginador(solicitudes_estado2, 20)
                p2 = 1
                try:
                    paginasesion2 = 1
                    if 'paginador2' in request.session:
                        paginasesion2 = int(request.session['paginador2'])
                    else:
                        p2 = paginasesion2
                    if 'page_estado2' in request.GET:
                        p2 = int(request.GET['page_estado2'])
                    else:
                        p2 = paginasesion2
                    try:
                        page2 = paging_estado2.page(p2)
                    except:
                        p2 = 1
                    page2 = paging_estado2.page(p2)
                except:
                    page2 = paging_estado2.page(p2)
                request.session['paginador2'] = p2
                data['paging_estado2'] = paging_estado2
                data['rangospaging'] = paging_estado2.rangos_paginado(p2)
                data['page_estado2'] = page2
                data['search2'] = search2 if search2 else ""
                data['solicitudes_estado2'] = page2.object_list

                # PAGINACION PARA ESTADO 3
                if 's3' in request.GET:
                    search3 = request.GET['s3'].strip()
                    ss3 = search3.split(' ')
                    if len(ss3) == 1:
                        solicitudes_estado3 = solicitudes_estado3.filter(
                            Q(materiaasignada__materia__asignatura__nombre__icontains=search3) |
                            Q(materiaasignada__matricula__inscripcion__persona__nombres__icontains=search3) |
                            Q(materiaasignada__matricula__inscripcion__persona__apellido1__icontains=search3) |
                            Q(materiaasignada__matricula__inscripcion__persona__apellido2__icontains=search3),
                            profesor=profesor, status=True).order_by('estado', '-fecha_creacion')
                    else:
                        solicitudes_estado3 = solicitudes_estado3.filter(
                            Q(materiaasignada__matricula__inscripcion__persona__apellido1__icontains=ss3[0]) |
                            Q(materiaasignada__matricula__inscripcion__persona__apellido2__icontains=ss3[1]),
                            profesor=profesor, status=True).order_by('estado', '-fecha_creacion')
                paging_estado3 = MiPaginador(solicitudes_estado3, 20)
                p3 = 1
                try:
                    paginasesion3 = 1
                    if 'paginador3' in request.session:
                        paginasesion3 = int(request.session['paginador3'])
                    else:
                        p3 = paginasesion3
                    if 'page_estado3' in request.GET:
                        p3 = int(request.GET['page_estado3'])
                    else:
                        p3 = paginasesion3
                    try:
                        page3 = paging_estado3.page(p3)
                    except:
                        p3 = 1
                    page3 = paging_estado3.page(p3)
                except:
                    page3 = paging_estado3.page(p3)
                request.session['paginador3'] = p3
                data['paging_estado3'] = paging_estado3
                data['rangospaging'] = paging_estado3.rangos_paginado(p3)
                data['page_estado3'] = page3
                data['search3'] = search3 if search3 else ""
                data['solicitudes_estado3'] = page3.object_list

                # PAGINACION PARA ESTADO 4
                if 's4' in request.GET:
                    search4 = request.GET['s4'].strip()
                    ss4 = search4.split(' ')
                    if len(ss4) == 1:
                        solicitudes_estado4 = solicitudes_estado4.filter(
                            Q(materiaasignada__materia__asignatura__nombre__icontains=search4) |
                            Q(materiaasignada__matricula__inscripcion__persona__nombres__icontains=search4) |
                            Q(materiaasignada__matricula__inscripcion__persona__apellido1__icontains=search4) |
                            Q(materiaasignada__matricula__inscripcion__persona__apellido2__icontains=search4),
                            profesor=profesor, status=True).order_by('estado', '-fecha_creacion')
                    else:
                        solicitudes_estado4 = solicitudes_estado4.filter(
                            Q(materiaasignada__matricula__inscripcion__persona__apellido1__icontains=ss4[0]) |
                            Q(materiaasignada__matricula__inscripcion__persona__apellido2__icontains=ss4[1]),
                            profesor=profesor, status=True).order_by('estado', '-fecha_creacion')
                paging_estado4 = MiPaginador(solicitudes_estado4, 20)
                p4 = 1
                try:
                    paginasesion4 = 1
                    if 'paginador4' in request.session:
                        paginasesion4 = int(request.session['paginador4'])
                    else:
                        p4 = paginasesion4
                    if 'page_estado4' in request.GET:
                        p4 = int(request.GET['page_estado4'])
                    else:
                        p4 = paginasesion4
                    try:
                        page4 = paging_estado4.page(p4)
                    except:
                        p4 = 1
                    page4 = paging_estado4.page(p4)
                except:
                    page4 = paging_estado4.page(p4)
                request.session['paginador4'] = p4
                data['paging_estado4'] = paging_estado4
                data['rangospaging'] = paging_estado4.rangos_paginado(p4)
                data['page_estado4'] = page4
                data['search4'] = search4 if search4 else ""
                data['solicitudes_estado4'] = page4.object_list
                return render(request, "pro_tutoriaacademica/view.html", data)

            except Exception as ex:
                return HttpResponseRedirect("/?info=Error. %s" % ex)
