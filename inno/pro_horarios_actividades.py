# -*- coding: latin-1 -*-
import json
from datetime import datetime, timedelta
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.http import HttpResponseRedirect, JsonResponse, HttpResponse
from django.shortcuts import render
from django.template.loader import get_template

from settings import TIEMPO_DEDICACION_TIEMPO_COMPLETO_ID
from sga.funciones import log, notificacion
from decorators import secure_module, last_access
from sga.commonviews import adduserdata
from inno.models import HorarioTutoriaAcademica
from django.db.models import Q, Sum
from sga.models import Clase, Sesion, DetalleDistributivo, ClaseActividad, ClaseActividadEstado, \
    ActividadDetalleDistributivo, Turno, ProfesorDistributivoHoras, Profesor, Notificacion, ProfesorMateria, MateriaAsignada, ComplexivoClase, Coordinacion, TurnoFacultad
from sga.funcionesxhtml2pdf import conviert_html_to_pdf

@login_required(redirect_field_name='ret', login_url='/loginsga')
@secure_module
@last_access
@transaction.atomic()
# @detect_mobile
def view(request):
    data = {}
    adduserdata(request, data)
    persona = request.session['persona']
    perfilprincipal = request.session['perfilprincipal']
    periodo = request.session['periodo']
    # if not ABRIR_CLASES_DISPOSITIVO_MOVIL and request.mobile:
    #     return HttpResponseRedirect("/?info=No se puede abrir clases desde un dispositivo movil.")
    if not perfilprincipal.es_profesor():
        return HttpResponseRedirect("/?info=Solo los perfiles de profesores pueden ingresar al modulo.")
    profesor = perfilprincipal.profesor
    if request.method == 'POST':
        action = request.POST['action']
        if action == 'horarioactividadespdf':
            try:
                data['title'] = u'Horarios de las Actividades del Profesor'
                data['profesor'] = profesor
                data['periodo'] = periodo = request.session['periodo']
                data['semana'] = [[1, 'Lunes'], [2, 'Martes'], [3, 'Miercoles'], [4, 'Jueves'], [5, 'Viernes'], [6, 'Sabado'], [7, 'Domingo']]
                hoy = datetime.now().date()

                ###data['misclases'] = clases = Clase.objects.filter(activo=True, fin__gte=hoy, materia__profesormateria__profesor=profesor, materia__profesormateria__principal=True, materia__profesormateria__activo=True,materia__profesormateria__status=True).order_by('inicio')
                # data['misclases'] = clases = Clase.objects.filter(activo=True, materia__profesormateria__profesor=profesor, materia__profesormateria__principal=True, materia__profesormateria__activo=True,materia__profesormateria__status=True).order_by('inicio')
                data['misclases'] = clases = Clase.objects.filter(activo=True, materia__profesormateria__profesor=profesor, materia__profesormateria__principal=True, materia__profesormateria__activo=True,materia__profesormateria__status=True).order_by('inicio')
                turnoclases = Turno.objects.filter(mostrar=True, clase__activo=True, clase__materia__nivel__periodo=periodo, clase__materia__profesormateria__profesor=profesor, clase__materia__profesormateria__principal=True).values_list('id', flat=True).distinct().order_by('comienza')
                if ClaseActividad.objects.filter(detalledistributivo__distributivo__periodo=periodo, detalledistributivo__distributivo__profesor=profesor).exists():
                    turnoactividades = Turno.objects.filter(status=True, mostrar=True, claseactividad__detalledistributivo__distributivo__periodo=periodo, claseactividad__detalledistributivo__distributivo__profesor=profesor).distinct().values_list('id', flat=True).order_by('comienza')
                else:
                    turnoactividades = Turno.objects.filter(status=True, mostrar=True, claseactividad__actividaddetalle__criterio__distributivo__periodo=periodo, claseactividad__actividaddetalle__criterio__distributivo__profesor=profesor).values_list('id', flat=True).distinct().order_by('comienza')

                idturnostutoria = []
                if HorarioTutoriaAcademica.objects.filter(status=True, profesor=profesor, periodo=periodo).exists():
                    idturnostutoria = HorarioTutoriaAcademica.objects.values_list('turno_id').filter(status=True,
                                                                                                     profesor=profesor,
                                                                                                     periodo=periodo).distinct()

                # turnosparatutoria = Turno.objects.filter(status=True, sesion_id=15,
                #                                          id__in=idturnostutoria).distinct().order_by('comienza')

                # data['turnos'] = turnoclases | turnoactividades |turnosparatutoria
                data['turnos'] = Turno.objects.filter(Q(status=True, mostrar=True), Q(id__in=turnoactividades) | Q(id__in=turnoclases)).distinct('comienza', 'termina')
                #data['sesiones'] = Sesion.objects.filter(turno__clase__in=clases).distinct()
                data['sesiones'] = Sesion.objects.filter(pk__in=[1, 4, 5, 7], status=True).distinct()
                return conviert_html_to_pdf(
                    'pro_horarios/actividades_pdf.html',
                    {
                        'pagesize': 'A4',
                        'data': data,
                    }
                )
            except Exception as ex:
                pass
        if action == 'addactividad':
            try:
                hoy = datetime.now().date()
                periodo = request.session['periodo']
                turno = Turno.objects.get(id=request.POST['idturno'])
                if turno:
                    detalle = DetalleDistributivo.objects.get(id=request.POST['idactividad'])
                    tutoria = True if request.POST['tipoactividad'] == '1' and detalle.criteriodocenciaperiodo.criterio.procesotutoriaacademica else False
                    turnotuto = verificar_turno_tutoria(periodo, request.POST['iddia'], profesor, turno.id) if tutoria else None
                    if tutoria and not turnotuto:
                        return JsonResponse({"result": "bad", "mensaje": "Lo sentimos este horario no está disponible para la actividad: <b>" +str(detalle.criteriodocenciaperiodo.criterio)+ "</b><br> intente con otro horario u otra actividad"})
                    elif tutoria and turnotuto:
                        turno = turnotuto
                    actividadesdia = ClaseActividad.objects.filter(status=True, detalledistributivo__distributivo__profesor=profesor, detalledistributivo__distributivo__periodo=periodo,
                                                                   dia=request.POST['iddia']).values('id', 'modalidad', 'turno__comienza')
                    clasesdia = Clase.objects.filter(profesor=profesor, materia__nivel__periodo__visible=True, materia__nivel__periodo=periodo, materia__nivel__periodo__visiblehorario=True, activo=True, dia=request.POST['iddia'], materia__profesormateria__profesor=profesor, materia__profesormateria__principal=True, materia__profesormateria__activo=True, materia__profesormateria__status=True, fin__gte=hoy).order_by('inicio')
                    critvencidos = turno.actividadesvencidasdia(periodo, request.POST['iddia'], profesor)
                    if actividadesdia.filter(Q(turno__comienza__range=(turno.comienza, turno.termina))| Q(turno__termina__range=(turno.comienza, turno.termina))).exists() or clasesdia.filter(Q(turno__comienza__range=(turno.comienza, turno.termina))| Q(turno__termina__range=(turno.comienza, turno.termina))).exists():
                            if not critvencidos:
                                return JsonResponse({"result": "bad", "mensaje": "Lo sentimos el horario que intenta elegir da conflicto con una o más horas de su horario, elija otro turno para continuar"})
                    detalledist = DetalleDistributivo.objects.get(id=request.POST['idactividad'])
                    actividad = ClaseActividad(detalledistributivo=detalledist,
                                               tipodistributivo=request.POST['tipoactividad'],
                                               # turno=turno[0], se comento para obtener el turno en caso de ser actividad de tutoria
                                               turno=turno,
                                               dia=request.POST['iddia'],
                                               inicio=detalledist.detalleactividadcriterio().desde,
                                               fin=detalledist.detalleactividadcriterio().hasta,
                                               estadosolicitud=1,
                                               modalidad=None,
                                               ordenmarcada = None,
                                               actividaddetallehorario=detalledist.detalleactividadcriterio()
                                               )

                    actividad.save(request)
                    tipo = actividad.tipodistributivo
                    if int(tipo) == 1:
                        tipodes = 'DOCENCIA'
                        des = actividad.detalledistributivo.criteriodocenciaperiodo.criterio.nombre
                    elif int(tipo) == 2:
                        tipodes = 'INVESTIGACION'
                        des = actividad.detalledistributivo.criterioinvestigacionperiodo.criterio.nombre
                    else:
                        tipodes = 'GESTION'
                        des = actividad.detalledistributivo.criteriogestionperiodo.criterio.nombre
                    # funcion para asignar marcadas a las actividades de gestion y verfificar el orden de cada marcada
                    # ordenar_marcada(periodo, request.POST['idactividad'], request.POST['iddia'], profesor)
                    log(u'Adicionó horario de actividad: %s - %s  turno: %s dia: %s' % (des, tipodes, str(actividad.turno),str(actividad.dia)),request, "add")

                    # para el boton de notificar
                    puedenotificar = True
                    horastotales = DetalleDistributivo.objects.filter(Q(distributivo__profesor=profesor, distributivo__periodo=periodo), Q(criteriodocenciaperiodo_id__isnull=False) | Q(criterioinvestigacionperiodo_id__isnull=False) | Q(criteriogestionperiodo_id__isnull=False)).exclude(criteriodocenciaperiodo__criterio_id__in=['15', '16', '17', '18', '20', '21', '27', '28', '30', '46', '7', '118']).aggregate(valor=Sum('horas'))['valor']

                    horastotalestodo = horastotales if horastotales else 0
                    if ClaseActividad.objects.filter(detalledistributivo__distributivo__profesor=profesor, detalledistributivo__distributivo__periodo=periodo).exists():
                        data['actividades'] = actividades = len(ClaseActividad.objects.filter(detalledistributivo__distributivo__profesor=profesor, detalledistributivo__distributivo__periodo=periodo).values('id'))
                    if horastotalestodo == actividades:
                        puedenotificar = True
                    return JsonResponse({"result": "ok", "codiactividad": actividad.id, 'actividades': actividades,'puedenotificar': puedenotificar})
                else:
                    JsonResponse({"result": "bad", "mensaje": "Error al guardar los datos."})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": "Error al guardar los datos."})

        if action == 'addactividaddetalle':
            try:
                periodo = request.session['periodo']
                actividad = ClaseActividad(actividaddetalle_id=request.POST['idactividad'],
                                           tipodistributivo=request.POST['tipoactividad'],
                                           turno_id=request.POST['idturno'],
                                           dia=request.POST['iddia'],
                                           inicio=periodo.inicio,
                                           fin=periodo.fin,
                                           estadosolicitud=1)
                actividad.save(request)
                return JsonResponse({"result": "ok", "codiactividad": actividad.id})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": "Error al guardar los datos."})

        if action == 'delactividad':
            try:
                periodo = request.session['periodo']
                actividad = ClaseActividad.objects.get(pk=request.POST['id'])
                idactividad = actividad.id
                tipo = actividad.tipodistributivo
                if actividad.detalledistributivo:
                    if tipo == 1:
                        des = actividad.detalledistributivo.criteriodocenciaperiodo.criterio.nombre
                        if actividad.detalledistributivo.criteriodocenciaperiodo.criterio.procesotutoriaacademica:
                            tuto = HorarioTutoriaAcademica.objects.filter(status=True, dia=actividad.dia, turno=actividad.turno, periodo=periodo, profesor=actividad.detalledistributivo.distributivo.profesor)
                            if tuto.exists():
                                if tuto.first().en_uso():
                                    return JsonResponse({"result": "bad", "mensaje": u"Lo sentimos esta actividad de tutoria tiene solicitudes y no se la puede eliminar"})
                    if tipo == 2:
                        des = actividad.detalledistributivo.criterioinvestigacionperiodo.criterio.nombre
                    if tipo == 3:
                        des = actividad.detalledistributivo.criteriogestionperiodo.criterio.nombre
                if actividad.actividaddetalle:
                    des = actividad.actividaddetalle.nombre
                turno = actividad.turno_id
                dia = actividad.dia
                return JsonResponse({"result": "ok", 'idactividad': idactividad, 'turno': turno, 'dia': dia, 'des': des})
            except Exception as ex:
                return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

        if action == 'eliminaractividad':
            try:
                periodo = request.session['periodo']
                actividad = ClaseActividad.objects.get(pk=request.POST['idactividad'])
                nomturno = actividad.turno
                nomdia = actividad.dia
                id = actividad.detalledistributivo_id
                if actividad.detalledistributivo:
                    if actividad.tipodistributivo == 1:
                        tipodes = 'DOCENCIA'
                        des = actividad.detalledistributivo.criteriodocenciaperiodo.criterio.nombre
                        if actividad.detalledistributivo.criteriodocenciaperiodo.criterio.procesotutoriaacademica:
                            tuto = HorarioTutoriaAcademica.objects.filter(status=True, dia=actividad.dia, turno=actividad.turno, periodo=periodo, profesor=actividad.detalledistributivo.distributivo.profesor)
                            if tuto.exists():
                                if tuto.first().en_uso():
                                    return JsonResponse({"result": "bad", "mensaje": u"Lo sentimos esta actividad de tutoria tiene solicitudes y no se la puede eliminar"})
                                else:
                                    tuto.first().delete()
                    if actividad.tipodistributivo == 2:
                        tipodes = 'INVESTIGACION'
                        des = actividad.detalledistributivo.criterioinvestigacionperiodo.criterio.nombre
                    if actividad.tipodistributivo == 3:
                        tipodes = 'GESTION'
                        des = actividad.detalledistributivo.criteriogestionperiodo.criterio.nombre
                if actividad.actividaddetalle:
                    tipodes = 'SUB ACTIVIDADES'
                    des = actividad.actividaddetalle.nombre
                actividad.delete()
                # ordenar_marcada(request.session['periodo'], id, nomdia, profesor)
                log(u'Eliminó horario de actividad: %s - %s  turno: %s dia: %s' % (des, tipodes, str(nomturno),str(nomdia)), request, "add")
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al eliminar los datos."})

        return JsonResponse({"result": "bad", "mensaje": u"Solicitud Incorrecta."})

    else:
        data = {}
        adduserdata(request, data)
        periodo = request.session['periodo']
        if 'action' in request.GET:
            action = request.GET['action']
            data['periodo'] = request.session['periodo']
            if 'listactividades' == action:
                try:
                    actidocencia = DetalleDistributivo.objects.filter(distributivo__profesor=profesor, distributivo__periodo=periodo, criteriodocenciaperiodo_id__isnull=False).exclude(criteriodocenciaperiodo__criterio_id__in=['15','16','17','18','20','21','27','28','30','46','7'])
                    actiinvestigacion = DetalleDistributivo.objects.filter(distributivo__profesor=profesor, distributivo__periodo=periodo, criterioinvestigacionperiodo_id__isnull=False)
                    actigestion = DetalleDistributivo.objects.filter(distributivo__profesor=profesor, distributivo__periodo=periodo, criteriogestionperiodo_id__isnull=False)
                    data['actividades'] = actidocencia | actiinvestigacion | actigestion
                    return render(request, "pro_horarios/actividadesdocentes.html", data)
                except Exception as ex:
                    pass

            if 'listactividadesdestalle' == action:
                try:
                    actidocencia = ActividadDetalleDistributivo.objects.filter(criterio__distributivo__profesor=profesor, criterio__distributivo__periodo=periodo, criterio__criteriodocenciaperiodo_id__isnull=False).exclude(criterio__criteriodocenciaperiodo__criterio_id__in=['15','16','17','18','20','21','27','28','19','30','46','7'])
                    actiinvestigacion = ActividadDetalleDistributivo.objects.filter(criterio__distributivo__profesor=profesor, criterio__distributivo__periodo=periodo, criterio__criterioinvestigacionperiodo_id__isnull=False)
                    actigestion = ActividadDetalleDistributivo.objects.filter(criterio__distributivo__profesor=profesor, criterio__distributivo__periodo=periodo, criterio__criteriogestionperiodo_id__isnull=False)
                    data['actividades'] = actidocencia | actiinvestigacion | actigestion
                    return render(request, "pro_horarios/detalleactividadesdocentes.html", data)
                except Exception as ex:
                    pass

            if action == 'notidirector':
                try:
                    distributivo = ProfesorDistributivoHoras.objects.filter(status=True, profesor=profesor, periodo=periodo)
                    if distributivo:
                        director = distributivo.first()
                        if director.carrera:
                            director = distributivo.first().carrera.get_director(periodo)
                            notificacion('Aprobación de horario de actividades', 'El docente {} le solicita la aprobación del horario de actividades'.format(profesor),
                                         director.persona, None, '/adm_criteriosactividadesdocente?action=horario&id={}&periodo={}'.format(profesor.pk, periodo.pk), profesor.pk,
                                         1, 'sga', Profesor, request)

                            return JsonResponse({"resp": True}, safe=False)
                        else:
                            raise NameError('Estimado docente usted no tiene asignado una carrera al distributivo')
                    else:
                        raise NameError('El docente no tiene asignado un distributivo')
                except Exception as e:
                    transaction.set_rollback(True)
                    return JsonResponse({"resp": False, "mensaje": str(e)})

            if action == 'buscarturnos':
                try:
                    dia = int(request.GET['dia'])
                    if periodo.tipo_id in [3, 4] or periodo.es_posgrado():
                        turnosadd = Turno.objects.filter(status=True, sesion_id__in=[19, 15], mostrar=True).order_by('comienza')
                    else:
                        turnosparatutoria = Turno.objects.filter(status=True, sesion_id=15, mostrar=True).distinct().order_by('comienza')
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
                        turnosadd = Turno.objects.filter(status=True, sesion_id=15).exclude(id__in=idturnosadd).distinct().order_by('comienza')
                    lista = []
                    for turno in turnosadd:
                        turnohora = Turno.objects.filter(comienza=turno.comienza, termina=turno.termina, sesion_id=17)
                        if turnohora.exists():
                            lista.append([turnohora[0].id, 'Turno de [{} a {}]'.format(turnohora[0].comienza.strftime("%H:%M %p"), turnohora[0].termina.strftime("%H:%M %p"))])
                    return JsonResponse({'result': 'ok', 'lista': lista})
                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})
            if action == 'buscarvencidas':
                try:
                    lista = []
                    dia = int(request.GET['dia'])
                    periodo = int(request.GET['periodo'])
                    profesor = int(request.GET['profesor'])
                    turno = int(request.GET['turno'])
                    turnomodel = Turno.objects.get(id=turno)
                    actividades = ClaseActividad.objects.filter(status=True, dia=dia, activo=True,
                                                                turno__comienza=turnomodel.comienza,
                                                                turno__termina=turnomodel.termina,
                                                                detalledistributivo__distributivo__profesor_id=profesor,
                                                                detalledistributivo__distributivo__periodo_id=periodo).exclude(
                        detalledistributivo__criteriodocenciaperiodo__criterio__procesotutoriaacademica=True).distinct().order_by(
                        'inicio')
                    for actividad in actividades:
                        if actividad.actividaddetallehorario:
                            if not actividad.actividaddetallehorario.criterio_vigente():
                                nombre = ''
                                if actividad.tipodistributivo in [1, 4]:
                                    nombre = actividad.detalledistributivo.criteriodocenciaperiodo.criterio.nombre
                                elif actividad.tipodistributivo == 2:
                                    nombre = actividad.detalledistributivo.criterioinvestigacionperiodo.criterio.nombre
                                elif actividad.tipodistributivo == 3:
                                    nombre = actividad.detalledistributivo.criteriogestionperiodo.criterio.nombre
                                lista.append([nombre, actividad.actividaddetallehorario.desde.strftime("%Y-%m-%d"), actividad.actividaddetallehorario.hasta.strftime("%Y-%m-%d")])
                    return JsonResponse({'result': 'ok', 'lista': lista})
                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})


        else:
            try:
                data['title'] = u'Horarios de las Actividades del Profesor'
                # clasesabiertas = LeccionGrupo.objects.filter(profesor=profesor, abierta=True).order_by('-fecha', '-horaentrada')
                # data['disponible'] = clasesabiertas.count() == 0
                # if clasesabiertas:
                #     data['claseabierta'] = clasesabiertas[0]
                # if not data['disponible']:
                #     if clasesabiertas.count() > 1:
                #         for clase in clasesabiertas[1:]:
                #             clase.abierta = False
                #             clase.save(request)
                    # data['lecciongrupo'] = LeccionGrupo.objects.filter(profesor=profesor, abierta=True)[0]
                data['profesor'] = profesor
                data['semana'] = [[1, 'Lunes'], [2, 'Martes'], [3, 'Miercoles'], [4, 'Jueves'], [5, 'Viernes'], [6, 'Sabado']]
                hoy = datetime.now().date()
                data['mostrar'] = 0
                # if ClaseActividadEstado.objects.filter(profesor=profesor, periodo=periodo, status=True).exists():
                #     data['mostrar'] = 1
                #     data['detalleestados'] = estadoactividad =vidad ClaseActividadEstado.objects.filter(profesor=profesor, periodo=periodo, status=True)
                #     data['estadoactividad'] = estadoactividad.all().order_by('-id')[0]
                # data['materiasnoprogramadas'] = ProfesorMateria.objects.filter(profesor=profesor, hasta__gt=hoy, activo=True, principal=True).exclude(materia__clase__id__isnull=False)
                elijedetalleactividad = False
                if profesor.profesormateria_set.filter(materia__nivel__periodo=request.session['periodo'], subactividadtutorvirtual=True, status=True).exists():
                    elijedetalleactividad = True
                data['elijedetalleactividad'] = elijedetalleactividad
                # data['misclases'] = clases = Clase.objects.filter(materia__nivel__periodo__visible=True, materia__nivel__periodo__visiblehorario=True, activo=True, fin__gte=hoy, materia__profesormateria__profesor=profesor, materia__profesormateria__principal=True, materia__profesormateria__activo=True,materia__profesormateria__status=True).order_by('inicio')
                data['sesiones'] = sesion= Sesion.objects.filter(pk__in=[1], status=True).distinct()
                # data['rango'] = Turno.objects.filter(sesion=sesion,status=True).distinct()

                # data['sesiones'] = Sesion.objects.filter(turno__clase__in=clases).distinct()
                data['periodo'] = request.session['periodo']
                if not request.session['periodo'].visible:
                    return HttpResponseRedirect("/?info=Periodo Inactivo.")

                data['semanatutoria'] = [[1, 'Lunes'], [2, 'Martes'], [3, 'Miercoles'], [4, 'Jueves'], [5, 'Viernes'], [6, 'Sábado']]
                data['sumaactividad'] = 0
                data['suma'] = 0
                actividades = 0

                claseactividad = ClaseActividad.objects.filter(detalledistributivo__distributivo__profesor=profesor, detalledistributivo__distributivo__periodo=periodo, status=True)
                if claseactividad.exists():
                    for actividad in claseactividad:
                        if not actividad.actividaddetallehorario:
                            actividad.actividaddetallehorario = actividad.detalledistributivo.detalleactividadcriterio()
                            actividad.save()
                        if actividad.actividaddetallehorario:
                            if actividad.actividaddetallehorario.criterio_vigente():
                                actividades += 1
                                # actividades = len(claseactividad)
                    data['suma'] = suma = len(claseactividad.filter(tipodistributivo=1, detalledistributivo__criteriodocenciaperiodo__criterio__procesotutoriaacademica=True))
                prof = ProfesorMateria.objects.filter(status=True, activo=True, materia__nivel__periodo=periodo, profesor=profesor, materia__nivel__periodo__visible=True,
                                                      materia__nivel__periodo__visiblehorario=True, principal=True).distinct().values_list('profesor_id', flat=True)


                clase = Clase.objects.filter(Q(status=True, activo=True, profesor=profesor, materia__nivel__periodo=periodo, materia__nivel__periodo__visible=True, materia__nivel__periodo__visiblehorario=True), Q(Q(inicio__lte=hoy), Q(fin__gte=hoy))).distinct().order_by('turno__inicio')
                clase = clase.filter(fin__gte=hoy)
                if clase.exists():
                    actividades += int(len(clase.values('dia', 'turno')))
                data['actividades'] = actividades
                # if ProfesorDistributivoHoras.objects.filter(profesor=profesor, periodo=periodo).exists():
                #     pdistri= ProfesorDistributivoHoras.objects.get(profesor=profesor, periodo=periodo)
                #     data['horastotales'] = horastotales= pdistri.total_horas_planificacion()
                horastotales = DetalleDistributivo.objects.filter(Q(distributivo__profesor=profesor, distributivo__periodo=periodo), Q(criteriodocenciaperiodo_id__isnull=False) | Q(criterioinvestigacionperiodo_id__isnull=False) |  Q(criteriogestionperiodo_id__isnull=False)).exclude(criteriodocenciaperiodo__criterio_id__in=['15', '16', '17', '18', '20', '21', '27', '28', '30', '46', '7']).aggregate(valor=Sum('horas'))['valor']


                data['horastotales'] = int(horastotales) if horastotales else 0

                # if DetalleDistributivo.objects.filter(distributivo__profesor=profesor, distributivo__periodo=periodo).exists():
                #     data['actividades'] = DetalleDistributivo.objects.filter(distributivo__profesor=profesor, distributivo__periodo=periodo).count()

                # if DetalleDistributivo.objects.filter(distributivo__profesor=profesor,
                #                                       distributivo__periodo=periodo,
                #                                       criteriodocenciaperiodo_id__in=[550, 562]).exists():
                if DetalleDistributivo.objects.filter(distributivo__profesor=profesor,
                                                      distributivo__periodo=periodo,
                                                      criteriodocenciaperiodo__criterio__procesotutoriaacademica=True).exists():
                    data['sumaactividad'] = sumaactividad = int(DetalleDistributivo.objects.filter(distributivo__profesor=profesor,
                                                                                   distributivo__periodo=periodo,
                                                                                   criteriodocenciaperiodo__criterio__procesotutoriaacademica=True).aggregate(
                        total=Sum('horas'))['total'])
                if horastotales == actividades:
                    data['puedenotificar'] = True
                data['director'] = None
                distributivo = ProfesorDistributivoHoras.objects.filter(status=True, profesor=profesor, periodo=periodo)
                if distributivo:
                    director = distributivo.first()
                    if director.carrera:
                        data['director'] = director = distributivo.first().carrera.get_director(periodo)
                if Notificacion.objects.filter(status=True, url='/adm_criteriosactividadesdocente?action=horario&id={}&periodo={}'.format(profesor.pk, periodo.pk)).exists():
                    data['notificado'] = True
                    data['notificacion'] = Notificacion.objects.filter(status=True, url='/adm_criteriosactividadesdocente?action=horario&id={}&periodo={}'.format(profesor.pk, periodo.pk)).last()
                # if HorarioTutoriaAcademica.objects.filter(status=True, profesor=profesor, periodo=periodo).exists():
                #     data['suma'] = int(HorarioTutoriaAcademica.objects.filter(status=True, profesor=profesor,
                #                                                               periodo=periodo).aggregate(
                #         total=Sum('turno__horas'))['total'])
                #
                # idturnostutoria = []
                # if HorarioTutoriaAcademica.objects.filter(status=True, profesor=profesor, periodo=periodo).exists():
                #     idturnostutoria = HorarioTutoriaAcademica.objects.values_list('turno_id').filter(status=True,
                #                                                                                      profesor=profesor,
                #                                                                                      periodo=periodo).distinct()
                #
                # turnosparatutoria = Turno.objects.filter(status=True, sesion_id=15,id__in=idturnostutoria).distinct().order_by('comienza')
                # data['turnostutoriacademica'] = turnosparatutoria

                carreraclase = clase.values_list('materia__asignaturamalla__malla__carrera', flat=True).distinct()

                factultadclase = Coordinacion.objects.filter(status=True, carrera__in=carreraclase).values_list('id', flat=True).distinct()

                turnosporfacultad = TurnoFacultad.objects.filter(status=True, coordinacion_id__in=factultadclase).values_list('turno_id', flat=True).distinct('turno_id')

                #
                turnosclases = clase.values_list('turno_id', flat=True)

                # if turnosporfacultad.exists():
                #     turnogeneral = Turno.objects.filter(Q(id__in=turnosporfacultad))
                # else:
                #     # clearturno = Turno.objects.filter(Q(sesion_id=17)).exclude(comienza__minute__gt=1).values_list('id', flat=True).distinct()
                turnogeneral = Turno.objects.filter(Q(sesion_id=17), Q(status=True), Q(mostrar=True))

                detalledist = DetalleDistributivo.objects.filter(distributivo__profesor=profesor, distributivo__periodo=periodo, criteriodocenciaperiodo__isnull=False)

                if detalledist.filter(criteriodocenciaperiodo__criterio__tipo=2, criteriodocenciaperiodo__criterio__vicevinculacion=True).exists():
                    turnogeneral = Turno.objects.filter(Q(sesion_id=17), Q(status=True), Q(id__lte=438))
                elif detalledist.filter(criteriodocenciaperiodo__criterio__tipo=2, criteriodocenciaperiodo__criterio__vicevinculacion=True).exists() and detalledist.filter(criteriodocenciaperiodo__criterio__tipo=1).exists():
                    turnogeneral = Turno.objects.filter(Q(sesion_id=17), Q(status=True), Q(mostrar=True)| Q(id__lte=438))
                data['turnogeneral'] = turnogeneral if persona.pk in (30, 27893) else turnogeneral.exclude(
                    id=475)  # se agrego una exclusion de un turno para el docente ARTEAGA MENDIETA FABRICIO RUPERTO y CHIFLA VILLON MARIO

                data['mostrar'] = True

                claseactividadestado = ClaseActividadEstado.objects.filter(profesor=profesor, periodo=periodo, status=True).order_by('-id')
                # if ClaseActividadEstado.objects.filter(profesor=profesor,periodo=periodo,estadosolicitud=2,status=True).exists():
                if profesor.profesordistributivohoras_set.filter(status=True, periodo=periodo).first().dedicacion_id == TIEMPO_DEDICACION_TIEMPO_COMPLETO_ID:
                    data['horas'] = 9
                else:
                    data['horas'] = 5
                if claseactividadestado:
                    if claseactividadestado[0].estadosolicitud == 2:
                        data['mostrar'] = False
                return render(request, "pro_horarios/horarios_actividades.html", data)
            except Exception as ex:
                pass


# def ordenar_marcada(periodo, idactividad, iddia, profesor):
#     p = profesor.pk
#     pk = None
#     actividadesdia = ClaseActividad.objects.filter(status=True, detalledistributivo__distributivo__profesor_id=p, detalledistributivo__distributivo__periodo=periodo,
#                                                    dia=iddia).values('id', 'modalidad', 'turno__comienza')
#     clasesdia = Clase.objects.filter(materia__nivel__periodo__visible=True, materia__nivel__periodo=periodo, materia__nivel__periodo__visiblehorario=True, activo=True, dia=iddia, materia__profesormateria__profesor_id=p, materia__profesormateria__principal=True, materia__profesormateria__activo=True, materia__profesormateria__status=True).order_by('inicio')
#     for actividadt in ClaseActividad.objects.filter(status=True, detalledistributivo__distributivo__profesor_id=p, detalledistributivo__distributivo__periodo_id=126, dia=iddia).order_by('turno__comienza'):
#         changeorden = 2
#         antecesor = ClaseActividad.objects.get(id=pk) if pk else None
#         actividadvirtualdespues = actividadesdia.filter(tipodistributivo=3, turno__comienza__gt=actividadt.turno.termina).exists()
#         actividadotrasdespues = actividadesdia.filter(tipodistributivo__lt=3, turno__comienza__gt=actividadt.turno.termina).exclude(id=actividadt.pk).exists()
#         esgestion = True if actividadt.tipodistributivo == 3 else False
#         actividadt.ordenmarcada = 2
#         if not actividadt.ordenmarcada == 1:
#             if not esgestion:
#                 changeorden = None
#             if antecesor:
#                 clasesintermedias = clasesdia.filter(turno__comienza__gte=antecesor.turno.termina, turno__termina__lte=actividadt.turno.comienza)
#                 if antecesor.tipodistributivo == 3 and not esgestion and not antecesor.ordenmarcada == 1 and not actividadvirtualdespues or (clasesintermedias and antecesor.tipodistributivo == 3):
#                     antecesor.ordenmarcada = 3 if not antecesor.ordenmarcada == 1 else 1
#                     if esgestion:
#                         changeorden = 1
#                 elif esgestion and not antecesor.tipodistributivo == 3 or clasesintermedias:
#                     changeorden = 1
#                 elif esgestion and antecesor.tipodistributivo == 3 and not actividadvirtualdespues:
#                     changeorden = 3
#                 elif antecesor.tipodistributivo == 3 and not esgestion and not antecesor.ordenmarcada == 1:
#                     antecesor.ordenmarcada = 3
#                 antecesor.save()
#             elif esgestion:
#                 changeorden = 1
#             actividadt.ordenmarcada = changeorden
#             actividadt.save()
#         pk = actividadt.pk





def verificar_turno_tutoria(periodo, dia, profesor, turno_id):
    if periodo.tipo_id in [3, 4] or periodo.es_posgrado():
        turnosadd = Turno.objects.filter(status=True, sesion_id__in=[19, 15]).order_by('comienza')
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
        if HorarioTutoriaAcademica.objects.filter(status=True, dia=dia, profesor=profesor, periodo=periodo).exists():
            idturnostutoria = HorarioTutoriaAcademica.objects.values_list('turno_id').filter(status=True, dia=dia,
                                                                                             profesor=profesor,
                                                                                             periodo=periodo).distinct()
        turnoclases = Turno.objects.filter(Q(id__in=idturnos) |
                                           Q(id__in=idturnoscomplexivo) |
                                           Q(id__in=idturnoactividades) |
                                           Q(id__in=idturnostutoria) |
                                           Q(id__in=idturnos_matricula)
                                           ).distinct().order_by('comienza')

        idturnosadd = []
        for turnotutoria in turnosadd:
            for turnoclase in turnoclases:
                if turnotutoria.comienza <= turnoclase.termina and turnotutoria.termina >= turnoclase.comienza:
                    idturnosadd.append(turnotutoria.id)
        turnosadd = Turno.objects.filter(status=True, sesion_id__in=[19, 15]).exclude(id__in=idturnosadd).values_list('id',
                                                                                                            flat=True).distinct().order_by(
            'comienza')
        turno_cl = Turno.objects.filter(id=turno_id)
        turno_tuto = Turno.objects.filter(comienza=turno_cl.first().comienza, termina=turno_cl.first().termina,
                                          sesion_id__in=[19, 15])
        if turno_tuto:
            return turno_tuto.first() if turno_tuto.first().id in turnosadd else None
        return None
    else:
        turnosparatutoria = Turno.objects.filter(status=True, sesion_id=15).distinct().order_by('comienza')
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
        turnosadd = Turno.objects.filter(status=True, sesion_id=15).exclude(id__in=idturnosadd).values_list('id', flat=True).distinct().order_by('comienza')
        turno_cl = Turno.objects.filter(id=turno_id)
        turno_tuto = Turno.objects.filter(comienza=turno_cl.first().comienza, termina=turno_cl.first().termina, sesion_id=15)
        if turno_tuto:
            return turno_tuto.first() if turno_tuto.first().id in turnosadd else None
        return None
