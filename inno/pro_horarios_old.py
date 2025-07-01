# -*- coding: latin-1 -*-
from datetime import datetime, timedelta, date
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.db.models import Q
from django.http import HttpResponseRedirect, JsonResponse
from django.shortcuts import render
from django.template.loader import get_template
from mobi.decorators import detect_mobile
from decorators import secure_module, last_access
from sga.commonviews import adduserdata
from django.template.context import Context
from sga.funciones import variable_valor, convertir_fecha, log,convertir_fecha_hora,convertir_fecha_hora_invertida
from sga.models import Clase, Sesion, LeccionGrupo, ProfesorMateria, ComplexivoClase, ComplexivoLeccion, Profesor, \
    Turno, ClaseSincronica, Materia, SesionZoom, DesactivarSesionZoom,DetalleDistributivo,DiasNoLaborable
from sga.funcionesxhtml2pdf import conviert_html_to_pdf
from inno.models import HorarioTutoriaAcademica , RegistroClaseTutoriaDocente,SolicitudTutoriaIndividual

@login_required(redirect_field_name='ret', login_url='/loginsga')
# @secure_module
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
    if request.method == 'POST':
        action = request.POST['action']
        if action == 'pdf_horarios':
            data = {}
            data['periodo'] = periodo
            if not periodo.visible:
                return HttpResponseRedirect("/?info=No tiene permiso para imprimir en el periodo seleccionado.")
            data['profesor'] = profesor = Profesor.objects.filter().distinct().get(pk=request.POST['profesor'])
            data['semana'] = [[1, 'Lunes'], [2, 'Martes'], [3, 'Miercoles'], [4, 'Jueves'], [5, 'Viernes'],[6, 'Sabado'], [7, 'Domingo']]
            turnosyclases = profesor.extrae_turnos_y_clases_docente(periodo)
            # turnoclases = Turno.objects.filter(clase__activo=True, clase__materia__nivel__periodo=periodo,
            #                                    clase__materia__profesormateria__profesor=profesor,
            #                                    clase__materia__profesormateria__principal=True).distinct().order_by(
            #     'comienza')
            turnoactividades = Turno.objects.filter(status=True, mostrar=True, claseactividad__detalledistributivo__distributivo__periodo=periodo, claseactividad__detalledistributivo__distributivo__profesor=profesor).distinct().order_by('comienza')
            data['turnos'] = turnosyclases[1] | turnoactividades
            data['puede_ver_horario'] = request.user.has_perm('sga.puede_visible_periodo') or (periodo.visible == True and periodo.visiblehorario == True)
            return conviert_html_to_pdf(
                'docentes/horario_pfd.html',
                {
                    'pagesize': 'A4',
                    'data': data,
                }
            )

        elif action == 'addclaseasincronica':
            try:
                from Moodle_Funciones import CrearForosClaseMoodle
                CrearForosClaseMoodle(request.POST['codclase'], persona, request.POST['observacion'], request.POST['enlace2'], request.POST['enlace3'], request.POST['coddia'])
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})
                pass

        elif action == 'addvideovirtual':
            try:
                from Moodle_Funciones import CrearClaseVirtualClaseMoodle
                CrearClaseVirtualClaseMoodle(request.POST['codclase'], persona, request.POST['observacion'], request.POST['enlace2'], request.POST['enlace3'], request.POST['coddia'])
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})
                pass

        elif action == 'addclasesincronica':
            try:
                hoy = datetime.now().date()
                # hoy2 = date(2020, 6, 16)

                # f = hoy2.days
                diaactual = hoy.isocalendar()[2]
                clase = Clase.objects.get(pk=request.POST['codclase'])
                # diaclase = clase.dia
                if not ClaseSincronica.objects.filter(clase=clase, clase__dia=diaactual, numerosemana=datetime.today().isocalendar()[1], status=True):
                    clasesincronica = ClaseSincronica(clase=clase,
                                                       numerosemana=datetime.today().isocalendar()[1])
                    clasesincronica.save(request)
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})
                pass

        elif action == 'segmento':
            try:
                data['materia'] = materia = Materia.objects.get(pk=request.POST['id'])

                asistodo = []
                for asignadomateria in materia.asignados_a_esta_materia():
                    asis = []
                    cantasis = 0
                    porcentaje = 0
                    for fechas in materia.lecciones_zoom():

                        if SesionZoom.objects.filter(materiaasignada=asignadomateria,fecha=fechas.fecha).exists():
                            asistencia = SesionZoom.objects.filter(materiaasignada=asignadomateria, fecha=fechas.fecha).first()
                        else:
                            asistencia = False
                            cantasis +=1

                        porcentaje = round((materia.lecciones_zoom().count() * 100) / cantasis, 0)
                        asis.append(asistencia)
                    asistodo.append([asignadomateria, asis, porcentaje])
                data['asistodo'] = asistodo
                template = get_template("pro_horarios/segmento.html")
                json_content = template.render(data)
                return JsonResponse({"result": "ok", "data": json_content})
            except Exception as ex:
                return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

        elif action == 'addclasetutoria':
            try:
                horario=HorarioTutoriaAcademica.objects.get(id=request.POST['id'])
                horario_todos=HorarioTutoriaAcademica.objects.filter(status=True,periodo=horario.periodo,profesor=horario.profesor,  dia=horario.dia, turno__comienza__gte=horario.turno.comienza).order_by('turno__comienza')
                for horario_insertar in horario_todos:
                    if not RegistroClaseTutoriaDocente.objects.filter(horario=horario_insertar, numerosemana=datetime.today().isocalendar()[1], status=True,fecha__date=datetime.now().date()):
                        clasetutoria = RegistroClaseTutoriaDocente(horario=horario_insertar, numerosemana=datetime.today().isocalendar()[1],fecha=datetime.now())
                        clasetutoria.save(request)
                tutorias_programadas_hoy = SolicitudTutoriaIndividual.objects.values('tipotutoria', 'fechatutoria',
                                                          'tutoriacomienza',
                                                          'tutoriatermina').filter(status=True,
                                                                                   estado=2,fechatutoria__date=datetime.now().date(),
                                                                                   tipotutoria__in=[2, 3],
                                                                                   profesor=profesor,
                                                                                   materiaasignada__matricula__nivel__periodo=periodo
                                                                                   ).distinct()

                for tuto_programada in tutorias_programadas_hoy:
                    if not RegistroClaseTutoriaDocente.objects.filter(numerosemana=datetime.today().isocalendar()[1],
                                                                      fecha=convertir_fecha_hora_invertida(u"%s %s" % (
                                                                      tuto_programada['fechatutoria'].date(),
                                                                      tuto_programada['tutoriacomienza'])),
                                                                      tipotutoria=tuto_programada['tipotutoria'],
                                                                      status=True,periodo=periodo,
                                                                       profesor=profesor):
                        clasetutoria = RegistroClaseTutoriaDocente(numerosemana=datetime.today().isocalendar()[1],
                                                                   fecha=convertir_fecha_hora_invertida(u"%s %s" % (
                                                                   tuto_programada['fechatutoria'].date(),
                                                                   tuto_programada['tutoriacomienza'])),
                                                                   tipotutoria=tuto_programada['tipotutoria'],periodo=periodo,
                                                                       profesor=profesor)
                        clasetutoria.save(request)

                return JsonResponse({"result": "ok"})
            except Exception as ex:
                return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})
                pass

        return JsonResponse({"result": "bad", "mensaje": u"Solicitud Incorrecta."})
    else:
        if 'action' in request.GET:
            action = request.GET['action']

            if action == 'asistencia':
                try:
                    data['title'] = u'Asistencias de alumnos'
                    data['materias'] = materias = Materia.objects.db_manager("sga_select").filter(nivel__periodo=periodo,
                    profesormateria__profesor=profesor,cerrado=False).distinct()
                    if not materias:
                        return HttpResponseRedirect("/?info=No tiene materias en el periodo seleccionado")
                    if periodo.versionasistencia == 2:
                        if 'codigomat' in request.GET:
                            primeramateria = materias.get(pk=request.GET['codigomat'])
                        else:
                            primeramateria = materias[0]
                        data['primeramateria'] = primeramateria

                        #fecha = date.today()

                        # for fecha in primeramateria.lecciones_zoom():
                        #     if not DiasNoLaborable.objects.values('id').filter(fecha=fecha.fecha, periodo_id=primeramateria.nivel.periodo_id).exists():
                        #         clases = Clase.objects.filter(materia=primeramateria)
                        #         clasesid = Clase.objects.values_list('id').filter(materia=primeramateria)
                        #         for cl in clases:
                        #             for asignadomateria in primeramateria.asignados_a_esta_materia():
                        #                 if SesionZoom.objects.filter(fecha=fecha.fecha, clase=cl, clase__materia=primeramateria, modulo=1).exists():
                        #                     if not SesionZoom.objects.select_related().filter(materiaasignada=asignadomateria,modulo=1,clase__materia=primeramateria, fecha=fecha.fecha, clase=cl).exists():
                        #                         asistencia = SesionZoom(materiaasignada=asignadomateria,
                        #                                                                modulo=1,
                        #                                                                fecha=fecha.fecha,
                        #                                                                hora=cl.turno.comienza,
                        #                                                                clase_id=cl.id,
                        #                                                                activo=False
                        #                                                                )
                        #                         asistencia.save()
                        #                         obser = DesactivarSesionZoom(sesion=asistencia,
                        #                                                      observacion="NO ASISTIÓ")
                        #                         obser.save()
                        #                     else:
                        #                         sesiones2 = SesionZoom.objects.select_related().filter( materiaasignada=asignadomateria,clase__materia__asignatura=primeramateria.asignatura, modulo=1,fecha=fecha.fecha, status=True).exclude(clase_id__in=clasesid)
                        #                         for a in sesiones2:
                        #                             desactivar = DesactivarSesionZoom.objects.filter(sesion=a)
                        #                             a.status = False
                        #                             a.save()
                        #                             for d in desactivar:
                        #                                 d.status = False
                        #                                 d.save()
                        #
                        #                         if SesionZoom.objects.filter(materiaasignada=asignadomateria,
                        #                                                   modulo=1, fecha=fecha.fecha,
                        #                                                   clase=cl).count()>1:
                        #
                        #                             if SesionZoom.objects.select_related().filter(
                        #                                     materiaasignada=asignadomateria,
                        #                                     fecha=fecha.fecha, clase=cl, activo=True).exists():
                        #
                        #                                 excluir = SesionZoom.objects.select_related().filter(
                        #                                     materiaasignada=asignadomateria,
                        #                                     fecha=fecha.fecha, clase=cl, activo=True).first()
                        #                             else:
                        #                                 excluir = SesionZoom.objects.select_related().filter(
                        #                                     materiaasignada=asignadomateria,
                        #                                     fecha=fecha.fecha, clase=cl).first()
                        #
                        #                             sesiones = SesionZoom.objects.select_related().filter(materiaasignada=asignadomateria,modulo=1, fecha=fecha.fecha,status=True,clase=cl).exclude(pk=excluir.pk)
                        #                             for a in sesiones:
                        #                                 desactivar = DesactivarSesionZoom.objects.filter(sesion=a)
                        #                                 a.status = False
                        #                                 a.save()
                        #                                 for d in desactivar:
                        #                                     d.status = False
                        #                                     d.save()

                        asistodo = []
                        for asignadomateria in primeramateria.asignados_a_esta_materia():
                            por = 0

                            if asignadomateria.asistencias_zoom_valida() > 0:
                                por = round(((asignadomateria.asistencias_zoom_valida() * 100) / asignadomateria.cantidad_asistencias_zoom()),0)
                            asistodo.append([asignadomateria, asignadomateria.asistencias_zoom(),por])
                            # if not primeramateria.cerrado:
                            #     asis = []
                            #     nuevo = 0
                            #     actual = 0
                            #     procentaje_zoom=0
                            #     if asignadomateria.asistencias_zoom_valida() > 0:
                            #         asistvalida = asignadomateria.asistencias_zoom_valida()
                            #         asistotal = asignadomateria.cantidad_asistencias_zoom()
                            #         asisfaltantes = asistotal - asistvalida
                            #         procentaje_zoom = round(((asistvalida * 100) / asistotal), 0)
                            #         if procentaje_zoom >= 69.5 and procentaje_zoom < 70:
                            #             procentaje_zoom = 70
                            #             print(asignadomateria, procentaje_zoom)
                            #     if asignadomateria.asistenciafinal != procentaje_zoom and not asignadomateria.cerrado and procentaje_zoom > asignadomateria.asistenciafinal:
                            #         asignadomateria.asistenciafinal = procentaje_zoom
                            #         asignadomateria.save()
                        data['asistodo'] = asistodo
                        data['contador'] = asistodo[0]

                        return render(request, "pro_horarios/segmento.html", data)

                except Exception as ex:
                    transaction.set_rollback(True)
                    pass

            if action == 'cambiaasistencia':
                try:
                    activo = True
                    observacion = request.GET['observacion'].strip().upper()
                    asistencia = SesionZoom.objects.get(pk=request.GET['id'])
                    if asistencia.activo:
                        asistencia.activo = False
                        activo = False
                        if not observacion:
                            #observacion="DESACTIVADA POR DOCENTE"
                            return JsonResponse({"result": "bad",
                                                 "mensaje": u"Ingrese observación"})
                    else:
                        # if date.today()<= asistencia.fecha+timedelta(days=1):
                        asistencia.activo = True
                        activo = True
                        if not observacion:
                            return JsonResponse({"result": "bad",
                                                     "mensaje": u"Ingrese observación"})
                                #observacion = "ACTIVADA POR DOCENTE"
                        # else:
                        #     return JsonResponse({"result": "bad", "mensaje": u"Sólo puede activar asistencia dentro de las 24 horas posteriores a su clase."})
                    asistencia.save(request)
                    obser = DesactivarSesionZoom(sesion=asistencia, observacion=observacion)
                    obser.save(request)
                    por = 0
                    id = asistencia.materiaasignada.pk
                    if asistencia.materiaasignada.asistencias_zoom_valida() > 0:
                        por = round(((asistencia.materiaasignada.asistencias_zoom_valida() * 100) / asistencia.materiaasignada.cantidad_asistencias_zoom()),0)
                    # asistencia.materiaasignada.asistenciafinal = por
                    # asistencia.materiaasignada.save()


                    log(u'Cambió asistencia: %s ' % asistencia, request, "edit")

                    return JsonResponse({"result": "ok","activo":activo,"por":por,"id":id})
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})


            return HttpResponseRedirect(request.path)


        else:
            try:
                data['title'] = u'Horario de profesor UNEMI'
                ID_DOCENTE_VIRTUAL = 7
                clasesabiertas = LeccionGrupo.objects.filter(status=True, profesor=profesor, abierta=True).order_by('-fecha', '-horaentrada')
                clasesabiertasCount = clasesabiertas.count()
                data['disponible'] = clasesabiertasCount == 0
                if clasesabiertas:
                    data['claseabierta'] = clasesabiertas[0]
                    # ------VERIFICA QUE AL MENDOS TENGA UN PROFESOR DE CLASE NO VALIDA HORARIO---------
                    mislecciones = clasesabiertas[0].mis_leciones()
                    if mislecciones.count() > 1:
                        if not clasesabiertas[0].verificar_profemate_novalidahor():
                            mislecciones = None
                    else:
                        mislecciones = None
                    data['leccionclases'] = mislecciones
                    # --------------------------------------------------------------------
                if not data['disponible']:
                    if clasesabiertasCount > 1:
                        for clase in clasesabiertas[1:]:
                            clase.abierta = False
                            clase.save()
                    data['lecciongrupo'] = LeccionGrupo.objects.filter(status=True, profesor=profesor, abierta=True)[0]
                data['profesor'] = profesor
                data['semana'] = [[1, 'Lunes'], [2, 'Martes'], [3, 'Miercoles'], [4, 'Jueves'], [5, 'Viernes'], [6, 'Sabado'], [7, 'Domingo']]
                data['semanatutoria'] = [[1, 'Lunes'], [2, 'Martes'], [3, 'Miercoles'], [4, 'Jueves'], [5, 'Viernes'], [6, 'Sábado']]
                hoy = datetime.now().date()
                data['fechaactual'] = hoy
                data['horaactual'] = datetime.now().time()
                #data['materiasnoprogramadas'] = ProfesorMateria.objects.filter(profesor=profesor, materia__nivel__periodo__visible=True, tipoprofesor_id=TIPO_DOCENTE_TEORIA, hasta__gt=hoy, activo=True, principal=True).exclude(materia__clase__id__isnull=False)
                data['materiasnoprogramadas'] = ProfesorMateria.objects.filter(status=True, profesor_id=profesor.id,
                                                                               materia__nivel__periodo__visible=True,
                                                                               materia__nivel__periodo__visiblehorario=True,
                                                                               materia__nivel__periodo=periodo,
                                                                               tipoprofesor_id__in=[11,12,1, 5, 8, 7, 10, 14, 15, 17], hasta__gt=hoy,
                                                                               activo=True, principal=True)
                # .exclude(materia__clase__id__isnull=False)
                clases = Clase.objects.filter(status=True, activo=True, materia__fechafinasistencias__gte=hoy, fin__gte=hoy,
                                              materia__nivel__periodo=periodo,
                                              materia__nivel__periodo__visible=True,
                                              materia__nivel__periodo__visiblehorario=True,
                                              materia__profesormateria__profesor=profesor,
                                              materia__profesormateria__principal=True,
                                              materia__profesormateria__tipoprofesor_id__in=[11,12,1, 5, 8, 7, 10, 14, 15, 17],
                                              tipoprofesor_id__in=[11,12,1, 5, 8, 7, 10, 14, 15, 17]).order_by('inicio')
                clasesayudante = Clase.objects.values_list('id').filter(status=True, activo=True,
                                                                        materia__fechafinasistencias__gte=hoy, fin__gte=hoy,
                                                                        materia__nivel__periodo=periodo,
                                                                        materia__nivel__periodo__visible=True,
                                                                        materia__nivel__periodo__visiblehorario=True,
                                                                        materia__profesormateria__profesor_id=profesor.id,
                                                                        profesorayudante_id=profesor.id,
                                                                        materia__profesormateria__principal=True).order_by('inicio')




                clases_turnos = profesor.extraer_clases_y_turnos_practica(datetime.now().date(), periodo)
                clases = Clase.objects.filter(Q(pk__in=clases.values_list('id')) | Q(pk__in=clasesayudante) | Q(pk__in=clases_turnos[0].values_list('id'))).distinct()
                data['misclases'] = clases

                idturnostutoria = []
                if DetalleDistributivo.objects.filter(distributivo__profesor=profesor,
                                                          distributivo__periodo=periodo,
                                                          criteriodocenciaperiodo__criterio_id__in=[7]).exists():
                    if HorarioTutoriaAcademica.objects.filter(status=True, profesor=profesor, periodo=periodo).exists():
                        idturnostutoria = HorarioTutoriaAcademica.objects.values_list('turno_id').filter(status=True,
                                                                                                         profesor=profesor,
                                                                                                         periodo=periodo).distinct()

                # data['sesiones'] = Sesion.objects.filter(turno__clase__in=clases).distinct()
                data['clasecomplexivo'] = complexivo = ComplexivoClase.objects.filter(status=True, activo=True, materia__profesor__profesorTitulacion_id=profesor.id, materia__status=True)
                data['sesiones'] = Sesion.objects.filter(Q(turno__id__in=clases.values_list('turno__id').distinct())
                                                         | Q(turno__complexivoclase__in=complexivo)
                                                         | Q(turno__id__in=idturnostutoria)).distinct()
                complexivoabierto = ComplexivoLeccion.objects.filter(status=True, abierta=True, clase__materia__profesor__profesorTitulacion_id=profesor.id)
                data['disponiblecomplexivo'] = complexivoabierto.count() == 0
                # if complexivoabierto:
                #     data['disponiblecomplexivo'] = complexivoabierto.count()
                lis = []
                data['numerosemanaactual'] = datetime.today().isocalendar()[1]
                data['fechainicio'] = datetime.today() - timedelta(days=datetime.today().isoweekday() % 7)
                for cumple in complexivoabierto:
                    if complexivoabierto:
                        lis.append(cumple.id)
                if len(lis)>0:
                    data['claseabiertacomplexivo'] = complexivoabierto
                    # data['claseabiertacomplexivo'] = complexivoabierto[0]
                return render(request, "pro_horarios/view_old.html", data)
            except Exception as ex:
                return HttpResponseRedirect("/?info=Error. %s" % ex)
