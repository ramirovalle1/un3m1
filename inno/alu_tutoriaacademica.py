# -*- coding: UTF-8 -*-
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.db.models import Q
from django.http import HttpResponseRedirect, JsonResponse
from django.shortcuts import render
from decorators import secure_module, last_access
from sga.commonviews import adduserdata
from sga.funciones import MiPaginador, log, puede_realizar_accion, variable_valor
from inno.models import SolicitudTutoriaIndividual, HorarioTutoriaAcademica, SolicitudTutoriaIndividualTema, PeriodoAcademia
from sga.models import Profesor, Turno, Clase, Materia, DetalleSilaboSemanalTema, MateriaAsignada, Matricula, \
    miinstitucion, Notificacion,DetalleDistributivo
from inno.forms import SolicitudTutoriaIndividualForm,SolicitudTutoriaGrupalForm
from django.db.models import Q, Sum
from datetime import datetime, timedelta, date
from sga.templatetags.sga_extras import encrypt, solo_caracteres
from django.forms import model_to_dict
from sga.tasks import send_html_mail, conectar_cuenta
from django.contrib.contenttypes.models import ContentType
from django.template.loader import get_template
from django.template import Context
@login_required(redirect_field_name='ret', login_url='/loginsga')
@secure_module
@last_access
@transaction.atomic()
def view(request):
    data = {}
    adduserdata(request, data)
    periodo = request.session['periodo']
    persona = request.session['persona']
    perfilprincipal = request.session['perfilprincipal']
    if not perfilprincipal.es_estudiante():
        return HttpResponseRedirect("/?info=Solo los perfiles de estudiantes pueden ingresar al modulo.")
    data['inscripcion']= inscripcion = perfilprincipal.inscripcion
    if inscripcion.matricula_periodo_actual(periodo):
        data['matricula']= matricula = inscripcion.matricula_periodo_actual(periodo)[0]
    else:
        return HttpResponseRedirect("/?info=Solo estudiantes matriculados pueden ingresar al modulo.")

    cordinacionid = inscripcion.carrera.coordinacion_carrera().id
    if cordinacionid in [9]:
        return HttpResponseRedirect("/?info=Estimado aspirante, este módulo esta habilitado solo para estudiantes de pregrado")

    if request.method == 'POST':
        action = request.POST['action']

        if action == 'addsolicitud':
            try:
                if int(request.POST['topico']) == 0:
                    return JsonResponse({"result": "bad", "mensaje": u"Debe seleccionar tópico."})
                if int(request.POST['horario']) == 0:
                    return JsonResponse({"result": "bad", "mensaje": u"Debe seleccionar horario."})
                horariotutoria = HorarioTutoriaAcademica.objects.get(id=request.POST['horario'])
                if matricula:
                    turnoclases=None
                    if matricula.nivel.periodo.tipo_id in [3,4]:
                        hoy = datetime.now().date()
                        lismaterias = MateriaAsignada.objects.values_list('materia_id').filter(matricula=matricula, materia__nivel__periodo=periodo, materia__inicio__lte=hoy, materia__fin__gte=hoy, retiramateria=False).distinct()
                        if Clase.objects.filter(activo=True, materia__materiaasignada__matricula=matricula,materia__materiaasignada__materia_id__in=lismaterias, materia__materiaasignada__retiramateria=False,dia=horariotutoria.dia).exists():
                            idturnos = Clase.objects.values_list('turno__id').filter(activo=True, materia__materiaasignada__matricula=matricula, materia__materiaasignada__materia_id__in=lismaterias,materia__materiaasignada__retiramateria=False,dia=horariotutoria.dia).distinct()
                            turnoclases = Turno.objects.filter(Q(id__in=idturnos)).distinct().order_by('comienza')

                        numerodia = horariotutoria.dia

                    else:
                        if Clase.objects.filter(activo=True, materia__materiaasignada__matricula=matricula, materia__materiaasignada__retiramateria=False,dia=horariotutoria.dia).exists():
                            idturnos = Clase.objects.values_list('turno__id').filter(activo=True, materia__materiaasignada__matricula=matricula, materia__materiaasignada__retiramateria=False,dia=horariotutoria.dia).distinct()
                            turnoclases = Turno.objects.filter(Q(id__in=idturnos)).distinct().order_by('comienza')

                            for turnoclase in turnoclases:
                                if horariotutoria.turno.comienza <= turnoclase.termina and horariotutoria.turno.termina >= turnoclase.comienza:
                                    return JsonResponse({"result": "bad", "mensaje": u"Ud no puede seleccionar este horario, ud tiene clases."})

                        hoy = datetime.now().date()
                        numerodia = horariotutoria.dia
                        if hoy.isoweekday() == numerodia:
                            return JsonResponse( {"result": "bad", "mensaje": u"No puede solicitar una tutoria en un horario del mismo día, por favor intentelo con otro horario o al siguiente día."})

                    materiaasinada=MateriaAsignada.objects.get(materia=request.POST['materia'],matricula= matricula,retiramateria=False)
                    if int(request.POST['topico']) == 1:
                        if SolicitudTutoriaIndividualTema.objects.filter(status=True,solicitud__status=True,
                                                                               solicitud__profesor_id=request.POST['profesor'],
                                                                               solicitud__materiaasignada=materiaasinada,
                                                                               solicitud__estado__in=[1,2],
                                                                               solicitud__topico=1,
                                                                               tema_id=request.POST['tema']).exists():
                            return JsonResponse({"result": "bad", "mensaje": u"Ud no puede solicitar tutoría con el mismo tema."})
                    elif int(request.POST['topico']) == 2:
                        if SolicitudTutoriaIndividual.objects.filter(status=True,profesor_id=request.POST['profesor'],
                                                                     materiaasignada=materiaasinada,
                                                                     topico=2,
                                                                     estado__in=[1,2]).exists():
                            return JsonResponse({"result": "bad", "mensaje": u"Ud no puede solicitar tutoría hasta que se haya ejecutado la actual."})
                    solicitud = SolicitudTutoriaIndividual(profesor_id=request.POST['profesor'],
                                                          materiaasignada=materiaasinada,
                                                          horario=horariotutoria,
                                                          estado=1,
                                                          topico=request.POST['topico'],
                                                          fechasolicitud=datetime.now(),tipo=1,
                                                          observacion_estudiante=request.POST['observacion_estudiante'],tipotutoria=1)
                    solicitud.save(request)
                    if int(request.POST['topico']) == 1:
                        if not SolicitudTutoriaIndividualTema.objects.filter(solicitud=solicitud,tema_id=request.POST['tema']).exists():
                            tema=SolicitudTutoriaIndividualTema(solicitud=solicitud,tema_id=request.POST['tema'])
                            tema.save(request)
                    send_html_mail("Solicitud de tutoría",
                                   "emails/solicitudtutoriaestudiante.html",
                                   {'sistema': u'SGA - UNEMI',
                                    'fecha': datetime.now().date(),
                                    'hora': datetime.now().time(),
                                    'solicitud': solicitud,
                                    't': miinstitucion()
                                    },
                                   solicitud.profesor.persona.lista_emails_interno(),
                                   [],
                                   cuenta=variable_valor('CUENTAS_CORREOS')[0]
                                   )

                    # notificacion = Notificacion(titulo='Solicitud de tutoría No. %s - (%s)'%(solicitud.id, solicitud.get_tipo_display()),
                    #                             cuerpo='El %s ha solicitado una sesión de tutoría (%s)' % (solicitud.materiaasignada.matricula.inscripcion.persona, solicitud.get_tipo_display()),
                    #                             destinatario=solicitud.profesor.persona,
                    #                             url=("/pro_tutoriaacademica"),
                    #                             content_type=ContentType.objects.get(app_label='inno',
                    #                                                                  model='solicitudtutoriaindividual'),
                    #                             object_id=solicitud.id,
                    #                             prioridad=1,
                    #                             app_label='sga',
                    #                             fecha_hora_visible=datetime.now() + timedelta(days=3),
                    #                             )
                    # notificacion.save(request)
                    log(u'Adiciono solicitud de tutoria academica: %s' % solicitud, request, "add")
                    return JsonResponse({"result": "ok"})
                else:
                    pass
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'editsolicitud':
            try:
                if int(request.POST['topico']) == 0:
                    return JsonResponse({"result": "bad", "mensaje": u"Debe seleccionar tópico."})
                if int(request.POST['horario']) == 0:
                    return JsonResponse({"result": "bad", "mensaje": u"Debe seleccionar horario."})
                if matricula:
                    turnoclases = None
                    solicitud = SolicitudTutoriaIndividual.objects.get(id=request.POST['id'])
                    horariotutoria = HorarioTutoriaAcademica.objects.get(id=request.POST['horario'])
                    if matricula.nivel.periodo.tipo_id in [3, 4]:
                        hoy = datetime.now().date()
                        lismaterias = MateriaAsignada.objects.values_list('materia_id').filter(matricula=matricula, materia__nivel__periodo=periodo, materia__inicio__lte=hoy, materia__fin__gte=hoy, retiramateria=False).distinct()
                        if Clase.objects.filter(activo=True, materia__materiaasignada__matricula=matricula,materia__materiaasignada__materia_id__in=lismaterias, materia__materiaasignada__retiramateria=False,dia=horariotutoria.dia).exists():
                            idturnos = Clase.objects.values_list('turno__id').filter(activo=True, materia__materiaasignada__matricula=matricula, materia__materiaasignada__materia_id__in=lismaterias,materia__materiaasignada__retiramateria=False,dia=horariotutoria.dia).distinct()
                            turnoclases = Turno.objects.filter(Q(id__in=idturnos)).distinct().order_by('comienza')

                        numerodia = horariotutoria.dia
                    else:
                        if Clase.objects.filter(activo=True, materia__materiaasignada__matricula=matricula,
                                                materia__materiaasignada__retiramateria=False,dia=horariotutoria.dia).exists():
                            idturnos = Clase.objects.values_list('turno__id').filter(activo=True,
                                                                                     materia__materiaasignada__matricula=matricula,
                                                                                     materia__materiaasignada__retiramateria=False,dia=horariotutoria.dia).distinct()
                            turnoclases = Turno.objects.filter(Q(id__in=idturnos)).distinct().order_by('comienza')

                            for turnoclase in turnoclases:
                                if horariotutoria.turno.comienza <= turnoclase.termina and horariotutoria.turno.termina >= turnoclase.comienza:
                                    return JsonResponse({"result": "bad", "mensaje": u"Ud no puede seleccionar este horario, tiene clases."})
                    if int(request.POST['topico']) == 1:
                        if SolicitudTutoriaIndividualTema.objects.filter(status=True,solicitud__status=True,
                                                                               solicitud__profesor_id=request.POST['profesor'],
                                                                               solicitud__materiaasignada=solicitud.materiaasignada,
                                                                               solicitud__estado__in=[1,2],
                                                                               solicitud__topico=1,
                                                                               tema_id=request.POST['tema']).exclude(solicitud_id=solicitud.id).exists():
                            return JsonResponse({"result": "bad", "mensaje": u"Ud no puede solicitar tutoría con el mismo tema."})
                    elif int(request.POST['topico']) == 2:
                        if SolicitudTutoriaIndividual.objects.filter(status=True,profesor_id=request.POST['profesor'],
                                                                     materiaasignada=solicitud.materiaasignada,
                                                                     topico=2,
                                                                     estado__in=[1,2]).exclude(id=solicitud.id).exists():
                            return JsonResponse({"result": "bad", "mensaje": u"Ud no puede solicitar tutoría hasta que se haya ejecutado la actual."})



                    if solicitud.materiaasignada.materia.id!=int(request.POST['materia']):
                        materiaasinada = MateriaAsignada.objects.get(materia=request.POST['materia'], matricula=matricula, retiramateria=False)
                        solicitud.materiaasignada = materiaasinada
                    if solicitud.profesor_id!=int(request.POST['profesor']):
                        solicitud.profesor_id = request.POST['profesor']
                    if solicitud.horario!=horariotutoria:
                        solicitud.horario = horariotutoria
                    if solicitud.topico!=int(request.POST['topico']):
                        solicitud.topico = request.POST['topico']
                    solicitud.save(request)
                    if int(request.POST['topico']) == 1:
                        if not SolicitudTutoriaIndividualTema.objects.filter(solicitud=solicitud,tema_id=request.POST['tema']).exists():
                            if SolicitudTutoriaIndividualTema.objects.filter(solicitud=solicitud).exists():
                                tema=SolicitudTutoriaIndividualTema.objects.get(solicitud=solicitud)
                                tema.tema_id=request.POST['tema']
                                tema.save(request)
                            else:
                                tema = SolicitudTutoriaIndividualTema(solicitud=solicitud,tema_id=request.POST['tema'])
                                tema.save(request)
                    elif int(request.POST['topico']) == 2:
                        if SolicitudTutoriaIndividualTema.objects.filter(solicitud=solicitud).exists():
                            SolicitudTutoriaIndividualTema.objects.filter(solicitud=solicitud).update(status=False)

                    log(u'Editó solicitud de tutoria academica: %s' % solicitud, request, "add")
                    return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'addsolicitudgrupal':
            try:
                if int(request.POST['topico']) == 0:
                    return JsonResponse({"result": "bad", "mensaje": u"Debe seleccionar tópico."})
                estudiantes = request.POST.getlist('estudiantes')
                if estudiantes.__len__() <= 1:
                    return JsonResponse({"result": "bad", "mensaje": u"Debe seleccionar más de un estudiante para tutoria grupal."})

                if int(request.POST['topico']) == 1 and int(request.POST['tema'])<=0:
                    return JsonResponse({"result": "bad", "mensaje": u"Debe seleccionar al menos un tema."})
                horariotutoria = HorarioTutoriaAcademica.objects.get(id=request.POST['horario'])
                for matriculaid in estudiantes:
                    matriculagrupo = Matricula.objects.get(id=int(matriculaid))
                    if matriculagrupo:
                        turnoclases=None
                        if matriculagrupo.nivel.periodo.tipo_id in [3, 4]:
                            hoy = datetime.now().date()
                            lismaterias = MateriaAsignada.objects.values_list('materia_id').filter(matricula=matriculagrupo, materia__nivel__periodo=periodo, materia__inicio__lte=hoy, materia__fin__gte=hoy, retiramateria=False).distinct()
                            if Clase.objects.filter(activo=True, materia__materiaasignada__matricula=matriculagrupo,
                                                    materia__materiaasignada__materia_id__in=lismaterias,
                                                    materia__materiaasignada__retiramateria=False,
                                                    dia=horariotutoria.dia).exists():
                                idturnos = Clase.objects.values_list('turno__id').filter(activo=True,
                                                                                         materia__materiaasignada__matricula=matriculagrupo,
                                                                                         materia__materiaasignada__materia_id__in=lismaterias,
                                                                                         materia__materiaasignada__retiramateria=False,
                                                                                         dia=horariotutoria.dia).distinct()
                                turnoclases = Turno.objects.filter(Q(id__in=idturnos)).distinct().order_by('comienza')

                            materiaasinada=None
                            materiaasinada=MateriaAsignada.objects.get(materia=request.POST['materia'],matricula= matriculagrupo,retiramateria=False)
                        else:
                            if Clase.objects.filter(activo=True, materia__materiaasignada__matricula=matriculagrupo, materia__materiaasignada__retiramateria=False,dia=horariotutoria.dia).exists():
                                idturnos = Clase.objects.values_list('turno__id').filter(activo=True, materia__materiaasignada__matricula=matriculagrupo, materia__materiaasignada__retiramateria=False,dia=horariotutoria.dia).distinct()
                                turnoclases = Turno.objects.filter(Q(id__in=idturnos)).distinct().order_by('comienza')

                                for turnoclase in turnoclases:
                                    if horariotutoria.turno.comienza <= turnoclase.termina and horariotutoria.turno.termina >= turnoclase.comienza:
                                        return JsonResponse({"result": "bad", "mensaje": u"%s no puede seleccionar este horario, ud tiene clases."%matriculagrupo.inscripcion})
                            materiaasinada=None
                            materiaasinada=MateriaAsignada.objects.get(materia=request.POST['materia'],matricula= matriculagrupo,retiramateria=False)
                        if int(request.POST['topico']) == 1:
                            if SolicitudTutoriaIndividualTema.objects.filter(status=True,solicitud__status=True,
                                                                                   solicitud__profesor_id=request.POST['profesor'],
                                                                                   solicitud__materiaasignada=materiaasinada,
                                                                                   solicitud__estado__in=[1,2],
                                                                                   solicitud__topico=1,
                                                                                   tema_id=request.POST['tema']).exists():
                                return JsonResponse({"result": "bad", "mensaje": u"%s ya tiene una solicitud de tutoría con el mismo tema."%matriculagrupo.inscripcion})
                        elif int(request.POST['topico']) == 2:
                            if SolicitudTutoriaIndividual.objects.filter(status=True,profesor_id=request.POST['profesor'],
                                                                         materiaasignada=materiaasinada,
                                                                         topico=2,
                                                                         estado__in=[1,2]).exists():
                                return JsonResponse({"result": "bad", "mensaje": u"%s tiene una solicitud de tutoría programada."%matriculagrupo.inscripcion})
                        solicitud = SolicitudTutoriaIndividual(profesor_id=request.POST['profesor'],
                                                              materiaasignada=materiaasinada,
                                                              horario=horariotutoria,
                                                              estado=1,
                                                              topico=request.POST['topico'],
                                                              fechasolicitud=datetime.now(),tipo=2,
                                                            observacion_estudiante=request.POST['observacion_estudiante'], tipotutoria=1)
                        solicitud.save(request)
                        if int(request.POST['topico']) == 1:
                            if not SolicitudTutoriaIndividualTema.objects.filter(solicitud=solicitud,tema_id=request.POST['tema']).exists():
                                tema=SolicitudTutoriaIndividualTema(solicitud=solicitud,tema_id=request.POST['tema'])
                                tema.save(request)
                    else:
                        pass
                solicitudautor=None
                materiaasinada = MateriaAsignada.objects.get(materia=request.POST['materia'], matricula=matricula, retiramateria=False)
                solicitudautor=SolicitudTutoriaIndividual.objects.filter(status=True, materiaasignada=materiaasinada, estado=1,
                                                                                           profesor_id=request.POST['profesor']).latest('id')
                if solicitudautor:
                    send_html_mail("Solicitud de tutoría",
                                   "emails/solicitudtutoriaestudiante.html",
                                   {'sistema': u'SGA - UNEMI',
                                    'fecha': datetime.now().date(),
                                    'hora': datetime.now().time(),
                                    'solicitud': solicitudautor,
                                    't': miinstitucion()
                                    },
                                   solicitudautor.profesor.persona.lista_emails_interno(),
                                   [],
                                   cuenta=variable_valor('CUENTAS_CORREOS')[0]
                                   )

                    # notificacion = Notificacion(titulo='Solicitud de tutoría No. %s - (%s)' % (solicitudautor.id, solicitudautor.get_tipo_display()),
                    #                             cuerpo='El %s ha solicitado una sesión de tutoría (%s)' % (
                    #                             solicitudautor.materiaasignada.matricula.inscripcion.persona,
                    #                             solicitudautor.get_tipo_display()),
                    #                             destinatario=solicitudautor.profesor.persona,
                    #                             url=("/pro_tutoriaacademica"),
                    #                             content_type=ContentType.objects.get(app_label='inno',
                    #                                                                  model='solicitudtutoriaindividual'),
                    #                             object_id=solicitudautor.id,
                    #                             prioridad=1,
                    #                             app_label='sga',
                    #                             fecha_hora_visible=datetime.now() + timedelta(days=3),
                    #                             )
                    # notificacion.save(request)
                log(u'Adiciono solicitud de tutoria academica grupal: %s' % matricula, request, "add")
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'buscarprofesor':
            try:
                materia = Materia.objects.get(pk=request.POST['id'])
                lista = []
                listaestudiantes = []
                # for profesormateria in materia.profesormateria_set.filter(status=True,activo=True,tipoprofesor_id__in=[9,12,11,1,14,15]):
                for profesormateria in materia.profesormateria_set.filter(status=True,activo=True).exclude(tipoprofesor_id__in=[16]).distinct('profesor_id'):
                    if DetalleDistributivo.objects.filter(distributivo__profesor=profesormateria.profesor,
                                                              distributivo__periodo=periodo,
                                                              criteriodocenciaperiodo__criterio__procesotutoriaacademica=True).exists():
                        lista.append([profesormateria.profesor.id, profesormateria.profesor.persona.nombre_completo_inverso()])

                for materiaasig in MateriaAsignada.objects.filter(status=True,materia=materia).distinct().order_by('matricula__inscripcion__persona'):
                    listaestudiantes.append([materiaasig.matricula.id, u'%s'% materiaasig.matricula])

                return JsonResponse({'result': 'ok', 'lista': lista, 'listaestudiantes': listaestudiantes})
            except Exception as ex:
                return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

        elif action == 'buscarhorario':
            try:
                idprofesor=int(request.POST['id'])
                idmateria=int(request.POST['idmateria'])
                profesor=Profesor.objects.get(id=idprofesor)
                materia=Materia.objects.get(id=idmateria)
                lista = []
                listatema = []
                horariotutoria=None
                if HorarioTutoriaAcademica.objects.filter(status=True,profesor=profesor,periodo=periodo).exists():
                    horariotutoria = HorarioTutoriaAcademica.objects.filter(status=True,profesor=profesor,periodo=periodo).distinct().order_by('dia')
                    for horario in horariotutoria:
                        lista.append([horario.id, u'%s - %s' % (horario.get_dia_display() if not horario.dia == 0 else 'DOMINGO', horario.turno)])

                for tema in DetalleSilaboSemanalTema.objects.filter(status=True,
                                                                    silabosemanal__silabo__materia=materia,
                                                                    # silabosemanal__silabo__profesor=profesor,
                                                                    silabosemanal__silabo__status=True,
                                                                    silabosemanal__fechainiciosemana__lte=datetime.now().date()).distinct():
                    listatema.append([tema.id, u'Sem: %s - %s (%s / %s)' % (tema.silabosemanal.numsemana,
                                                                       tema.temaunidadresultadoprogramaanalitico.descripcion,
                                                                       tema.silabosemanal.fechainiciosemana,
                                                                       tema.silabosemanal.fechafinciosemana,)])
                return JsonResponse({'result': 'ok', 'lista': lista, 'listatema': listatema})
            except Exception as ex:
                return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

        elif action == 'buscartema':
            try:
                materia = Materia.objects.get(pk=request.POST['idmateria'])
                profesor = Profesor.objects.get(pk=request.POST['id'])
                listatema = []
                for tema in DetalleSilaboSemanalTema.objects.filter(status=True,
                                                                    silabosemanal__silabo__materia=materia,
                                                                    silabosemanal__silabo__profesor=profesor,
                                                                    silabosemanal__silabo__status=True,
                                                                    silabosemanal__fechainiciosemana__lte=datetime.now().date()).distinct():
                    listatema.append([tema.id, u'Sem: %s - %s (%s / %s)' % (tema.silabosemanal.numsemana,
                                                                       tema.temaunidadresultadoprogramaanalitico.descripcion,
                                                                       tema.silabosemanal.fechainiciosemana,
                                                                       tema.silabosemanal.fechafinciosemana,)])
                return JsonResponse({'result': 'ok', 'listatema': listatema})
            except Exception as ex:
                return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

        elif action == 'delsolicitud':
            try:
                solicitud = SolicitudTutoriaIndividual.objects.get(pk=int(encrypt(request.POST['id'])))
                if solicitud.estado==1:
                    solicitud.status=False
                    solicitud.save(request)
                    log(u'Eliminó solicitud de tutoria academica: %s' % solicitud, request, "del")
                    return JsonResponse({'result': 'ok'})
                else:
                    return JsonResponse({"result": "bad", "mensaje": u"Error la solicitud ya esta programada."})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

        elif action == 'addclasetutoria':
            try:
                solicitud=SolicitudTutoriaIndividual.objects.get(id=request.POST['id'])
                if not solicitud.asistencia:
                    solicitud.asistencia=True
                    solicitud.estado=3
                    solicitud.save(request)
                    log(u'Registro de asistencia tutorían académica: %s' % solicitud, request, "edit")
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})
                pass

        elif action == 'encuestasatisfaccion':
            try:
                data['solicitud'] = SolicitudTutoriaIndividual.objects.get(pk=int(request.POST['id']))
                template = get_template("alu_tutoriaacademica/rating.html")
                json_content = template.render(data)
                return JsonResponse({"result": "ok", 'html': json_content})
            except Exception as ex:
                return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

        elif action == 'guardarrespuestaencuesta':
            try:
                solicitud= SolicitudTutoriaIndividual.objects.get(pk=int(request.POST['id']))
                respuesta=int(request.POST['respuesta'])
                solicitud.resultadoencuesta=respuesta
                solicitud.save(request)
                log(u'Realiza encuesta se satisfación tutoria: %s' % solicitud, request, "edit")
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

        return JsonResponse({"result": "bad", "mensaje": u"Solicitud Incorrecta."})
    else:
        if 'action' in request.GET:
            action = request.GET['action']

            if action == 'addsolicitud':
                try:
                    data['title'] = u'Solicitar tutoria'
                    form = SolicitudTutoriaIndividualForm()
                    form.iniciar(periodo,matricula)
                    data['form'] = form
                    return render(request, "alu_tutoriaacademica/addsolicitud.html", data)
                except Exception as ex:
                    pass

            elif action == 'editsolicitud':
                try:
                    data['title'] = u'Editar solicitud'
                    data['solicitud'] = solicitud = SolicitudTutoriaIndividual.objects.get(pk=int(encrypt(request.GET['id'])))
                    form = SolicitudTutoriaIndividualForm(initial={'materia':solicitud.materiaasignada.materia,
                                                                   'profesor':solicitud.profesor,
                                                                   'horario':solicitud.horario,
                                                                   'topico':solicitud.topico,
                                                                   'tema':solicitud.temas()[0].tema if solicitud.temas() else None})
                    form.editar(periodo,matricula,solicitud)
                    data['form'] = form
                    data['temaid']=solicitud.temas()[0].tema.id if solicitud.temas() else 0
                    return render(request, "alu_tutoriaacademica/editsolicitud.html", data)
                except Exception as ex:
                    pass

            elif action == 'delsolicitud':
                try:
                    data['title'] = u'Eliminar solicitud'
                    data['solicitud'] = SolicitudTutoriaIndividual.objects.get(pk=int(encrypt(request.GET['id'])))
                    return render(request, "alu_tutoriaacademica/delsolicitud.html", data)
                except Exception as ex:
                    pass

            elif action == 'addsolicitudgrupal':
                try:
                    data['title'] = u'Solicitar tutoria grupal'
                    form = SolicitudTutoriaGrupalForm()
                    form.iniciar(periodo,matricula)
                    data['form'] = form
                    data['matriculaid']=matricula.id
                    return render(request, "alu_tutoriaacademica/addsolicitudgrupal.html", data)
                except Exception as ex:
                    pass

            return HttpResponseRedirect(request.path)

        else:
            try:
                data['title'] = u'Tutorías académicas'
                search = None
                ids = None
                if 's' in request.GET:
                    search = request.GET['s']
                if search:
                    solicitudes = SolicitudTutoriaIndividual.objects.filter(Q(materiaasignada__materia__asignatura__nombre__icontains=search) |
                                                           Q(materiaasignada__materia__paralelomateria__nombre__icontains=search),materiaasignada__matricula=matricula)
                elif 'id' in request.GET:
                    ids = request.GET['id']
                    solicitudes = SolicitudTutoriaIndividual.objects.filter(id=ids,materiaasignada__matricula=matricula)
                else:
                    solicitudes = SolicitudTutoriaIndividual.objects.filter(status=True,materiaasignada__matricula=matricula)
                paging = MiPaginador(solicitudes, 20)
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
                data['rangospaging'] = paging.rangos_paginado(p)
                data['page'] = page
                data['search'] = search if search else ""
                data['ids'] = ids if ids else ""
                data['solicitudes'] = page.object_list
                data['periodoacademia']=periodo.get_periodoacademia()

                return render(request, "alu_tutoriaacademica/view.html", data)
            except Exception as ex:
                pass
