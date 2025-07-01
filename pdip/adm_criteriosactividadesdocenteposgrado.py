import sys
from datetime import datetime

from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.db.models import F, IntegerField, Q, Sum
from django.db.models.functions import Concat
from django.http import HttpResponseRedirect, JsonResponse
from django.shortcuts import render

from decorators import last_access, secure_module
from inno.models import HorarioTutoriaAcademica
from inno.pro_horarios import turno_turoria, verificar_limite_dia
from pdip.models import HorarioPlanificacionContrato
from settings import DEBUG, TIEMPO_DEDICACION_TIEMPO_COMPLETO_ID
from sga.commonviews import adduserdata
from sga.funciones import notificacion, log
from sga.models import Profesor, ProfesorDistributivoHoras, DetalleDistributivo, Turno, ClaseActividad, Clase, \
    ClaseActividadEstado, ProfesorMateria
from sga.templatetags.sga_extras import convertir_tipo_oracion


@login_required(redirect_field_name='ret', login_url='/loginsga')
# @secure_module
@last_access
@transaction.atomic()
def view(request):
    global ex
    data = {}
    adduserdata(request, data)
    periodo = request.session['periodo']
    persona = request.session['persona']
    user = request.user
    SESION_ID = [19, 15] if periodo.clasificacion == 2 else [15]

    dominio_sistema = 'https://sga.unemi.edu.ec'
    if DEBUG:
        dominio_sistema = 'http://localhost:8000'
    data["DOMINIO_DEL_SISTEMA"] = dominio_sistema

    if request.method == 'POST':
        action = request.POST['action']
        if action == 'addactividadclase':
            try:
                from inno.pro_horarios_actividades import verificar_turno_tutoria
                data['id'] = id = request.POST['idprofesor']
                distri = ProfesorDistributivoHoras.objects.get(status=True,id=id)
                data['profesor'] = profesor = distri.profesor
                hoy = datetime.now().date()
                periodo = request.session['periodo']
                dia = request.POST['iddia']
                idactividad = request.POST['idactividad']
                turno = Turno.objects.get(id=request.POST['idturno'])
                if turno:
                    detalle = DetalleDistributivo.objects.get(id=request.POST['idactividad'])
                    tutoria = detalle.criteriodocenciaperiodo.criterio.procesotutoriaacademica if detalle.criteriodocenciaperiodo else False
                    if tutoria:
                        if not verificar_turno_tutoria(periodo, dia, profesor, turno.id):
                            return JsonResponse({"result": "bad", "mensaje": "Lo sentimos este horario no está disponible para la actividad: <b>" + str(convertir_tipo_oracion(
                                                         detalle.criteriodocenciaperiodo.criterio.nombre)) + "</b><br> intente en con un dia y hora diferente"})
                    actividadesdia = ClaseActividad.objects.filter(status=True,
                                                                   detalledistributivo__distributivo__profesor=profesor,
                                                                   dia=dia).values('id', 'modalidad', 'turno__comienza')
                    clasesdia = Clase.objects.filter(profesor=profesor, materia__nivel__periodo__visible=True,
                                                     materia__nivel__periodo__visiblehorario=True, activo=True,
                                                     dia=request.POST['iddia'],
                                                     materia__profesormateria__profesor=profesor,
                                                     materia__profesormateria__principal=True,
                                                     materia__profesormateria__activo=True,
                                                     materia__profesormateria__status=True, fin__gte=hoy).order_by('inicio')
                    critvencidos = turno.actividadesvencidasdia(periodo, dia, profesor)
                    if actividadesdia.filter(Q(turno__comienza__range=(turno.comienza, turno.termina)) | Q(
                            turno__termina__range=(turno.comienza, turno.termina))).exists() or clasesdia.filter(
                        Q(turno__comienza__range=(turno.comienza, turno.termina)) | Q(
                            turno__termina__range=(turno.comienza, turno.termina))).exists():
                        if not critvencidos:
                            return JsonResponse({"result": "bad", "mensaje": "Lo sentimos el horario que intenta elegir da conflicto con una o más horas de su horario, elija otro turno para continuar"})
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
                    log(u'Adicionó horario de actividad: %s - %s  turno: %s dia: %s' % (des, tipodes, str(turno), str(dia)), request, "add")
                    return JsonResponse({"result": "ok"})
                else:
                    JsonResponse({"result": "bad", "mensaje": "Lo sentimos el turno no existe"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": "Error al guardar los datos. {}".format(ex)})

        elif action == 'delactividadclase':
            try:
                data['id'] = id = request.POST['idprofesor']
                distri = ProfesorDistributivoHoras.objects.get(status=True,id=id)
                data['profesor'] = profesor = distri.profesor
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
                                    return JsonResponse({"result": "bad","mensaje": u"Lo sentimos esta actividad de tutoria tiene solicitudes y no se la puede eliminar"})
                turno = actividad.turno_id
                dia = actividad.dia
                profesor = actividad.detalledistributivo.distributivo.profesor
                des = actividad.detalledistributivo.nombre()
                actividadquery.delete()
                log(u'Eliminó actividad {} del horario del profesor: %s - %s  turno: %s dia: %s' % (des, profesor, str(turno), str(dia)), request, "del")
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos. {}".format(ex)})

        elif action == 'saveactivities':
            try:
                data['id'] = id = request.POST['idprofesor']
                distri = ProfesorDistributivoHoras.objects.get(status=True,id=id)
                data['profesor'] = profesor = distri.profesor
                onlyclass = False
                actvidades = ClaseActividad.objects.filter(status=True, detalledistributivo__distributivo__profesor=profesor,
                                                           detalledistributivo__distributivo__periodo=periodo).update(estadosolicitud=2)
                actvidades = ClaseActividad.objects.filter(status=True, detalledistributivo__distributivo__profesor=profesor,
                                                           detalledistributivo__distributivo__periodo=periodo,estadosolicitud=2)
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
                log('Guardó su horario de actividades el docente: {}'.format(profesor.persona), request, "add")
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error en la transaccion. {}".format(ex)})

    else:
        if 'action' in request.GET:
            data['action'] = action = request.GET['action']

            if action == 'horarioclases':
                try:
                    data['title'] = 'Gestión de horarios'
                    data['id']=id =request.GET['id']
                    distri = ProfesorDistributivoHoras.objects.get(status=True,id=int(id))
                    data['profesor'] = profesor = distri.profesor
                    materia = distri.materia
                    data['periodo'] = periodo = request.session['periodo']
                    if not periodo.visible:
                        return HttpResponseRedirect("/adm_criteriosactividadesdocente?info=Lo sentimos, este periodo no se encuentra activo.")
                    distributivo = ProfesorDistributivoHoras.objects.filter(status=True, profesor=profesor,
                                                                            periodo=periodo).first()
                    if not distributivo:
                        return HttpResponseRedirect("/adm_criteriosactividadesdocente?info=Lo sentimos, usted no se encuentra registrado en el distributivo de docentes del periodo actual")
                    todaslasactividades = DetalleDistributivo.objects.filter(distributivo__profesor=profesor,
                                                                             distributivo__periodo=periodo)
                    if not todaslasactividades:
                        return HttpResponseRedirect("/adm_criteriosactividadesdocente?info=Lo sentimos, usted no tiene asignados criterios en su distributivo, comuniquese con GTA.")
                    data['criterio'] = criterio = request.GET['criterio'] if 'criterio' in request.GET else None
                    if criterio:
                        try:
                            criterio = int(criterio)
                        except:
                            criterio = None
                    data['todaslasactividades'] = todaslasactividades
                    data['criterio'] = criterio = todaslasactividades.first().id if not criterio and len(todaslasactividades) > 0 else criterio
                    detactiorien = DetalleDistributivo.objects.get(status=True,id=criterio)
                    data['actividadorientacion'] = detactiorien.criteriodocenciaperiodo.actividad if detactiorien.criteriodocenciaperiodo else 0
                    data['ultimocriterio'] = todaslasactividades[len(todaslasactividades) - 1].id if len(todaslasactividades) > 0 else 0
                    data['turnos'] = turnos = Turno.objects.filter(status=True, sesion_id=19)
                    data['semana'] = [[1, 'Lunes'], [2, 'Martes'], [3, 'Miercoles'], [4, 'Jueves'], [5, 'Viernes'], [6, 'Sabado'],[7, 'Domingo']]
                    hoy = datetime.now().date()
                    data['horariocontrato'] = horariocontrato = HorarioPlanificacionContrato.objects.filter(Q(inicio__lte=hoy)&Q(fin__gte=hoy),status=True,contrato__persona__id=profesor.persona.id)\
                        .annotate(diaturno=Concat(F('dia'),F('turno__id'),output_field=IntegerField())).values_list('diaturno',flat=True)

                    data['sumaactividad'] = 0
                    data['suma'] = 0
                    bloquear = todaslasactividades.filter(id=criterio).first().total_claseactividades() == 0
                    block_act = False
                    actividades = 0
                    actividades_dia_turno = []
                    actividades_marcadas_criterio = []
                    detalleimpartir = todaslasactividades.filter(criteriodocenciaperiodo__criterio_id=118).values('id').first()
                    data['detalleimpartir'] = detalleimpartir = detalleimpartir['id'] if detalleimpartir else 0
                    detalletutoria = todaslasactividades.filter(criteriodocenciaperiodo__criterio_id=124).values('id').first()
                    data['detalletutoria'] = detalletutoria['id'] if detalletutoria else 0
                    claseactividad = ClaseActividad.objects.filter(detalledistributivo__distributivo__profesor=profesor,
                                                                   detalledistributivo__distributivo__periodo=periodo,
                                                                   status=True)
                    if claseactividad.exists():
                        for actividad in claseactividad:
                            if not actividad.actividaddetallehorario:
                                actividad.actividaddetallehorario = actividad.detalledistributivo.detalleactividadcriterio()
                                actividad.save()
                            if actividad.actividaddetallehorario:
                                if actividad.actividaddetallehorario.criterio_vigente():
                                    actividades += 1
                                    if criterio == actividad.detalledistributivo.id:
                                        actividades_marcadas_criterio.append(int('{}{}'.format(actividad.dia, actividad.turno_id)))
                                    else:
                                        actividades_dia_turno.append(int('{}{}'.format(actividad.dia, actividad.turno_id)))
                        data['suma'] = suma = len(claseactividad.filter(tipodistributivo=1,
                                                                        detalledistributivo__criteriodocenciaperiodo__criterio__procesotutoriaacademica=True))
                    clase = Clase.objects.filter(
                        Q(status=True, activo=True, profesor=profesor, materia__nivel__periodo=periodo,materia=materia,
                          materia__nivel__periodo__visible=True, materia__nivel__periodo__visiblehorario=True),
                        Q(Q(fin__gte=hoy))).distinct().order_by('turno__inicio')
                    if clase.exists():
                        actividades += int(len(clase.values('dia', 'turno')))
                        for cl in clase.values('dia', 'turno').distinct():
                            if criterio == detalleimpartir:
                                bloquear = True
                                actividades_marcadas_criterio.append(int('{}{}'.format(cl['dia'], cl['turno'])))
                            else:
                                actividades_dia_turno.append(int('{}{}'.format(cl['dia'], cl['turno'])))
                    data['profesormateria'] =profesormateria= ProfesorMateria.objects.filter(profesor=profesor, materia=distri.materia).first()
                    if HorarioTutoriaAcademica.objects.filter(status=True, profesor=profesor, periodo=periodo,profesormateria=profesormateria).exists():
                        horarios = HorarioTutoriaAcademica.objects.filter(status=True, profesor=profesor,periodo=periodo,profesormateria=profesormateria)
                        for cl in horarios.values('dia', 'turno').distinct():
                            # turno = Turno.objects.get(id=cl['turno'])
                            # dia = cl['dia']
                            # actividadesdia = ClaseActividad.objects.filter(status=True,
                            #                                                detalledistributivo__distributivo__profesor=profesor,
                            #                                                dia=dia).values('id', 'modalidad',
                            #                                                                'turno__comienza')
                            # clasesdia = Clase.objects.filter(profesor=profesor, materia__nivel__periodo__visible=True,
                            #                                  materia__nivel__periodo__visiblehorario=True, activo=True,
                            #                                  dia=dia,
                            #                                  materia__profesormateria__profesor=profesor,
                            #                                  materia__profesormateria__principal=True,
                            #                                  materia__profesormateria__activo=True,
                            #                                  materia__profesormateria__status=True,
                            #                                  fin__gte=hoy).order_by('inicio')
                            #
                            # critvencidos = turno.actividadesvencidasdia(periodo, dia, profesor)
                            # if actividadesdia.filter(Q(turno__comienza__range=(turno.comienza, turno.termina)) | Q(
                            #         turno__termina__range=(
                            #         turno.comienza, turno.termina))).exists() or clasesdia.filter(
                            #     Q(turno__comienza__range=(turno.comienza, turno.termina)) | Q(
                            #         turno__termina__range=(turno.comienza, turno.termina))).exists():
                            #     if not critvencidos:
                            #         pass
                            # else:
                            #     detalledist = DetalleDistributivo.objects.get(id=criterio)
                            #     actividad = ClaseActividad(detalledistributivo=detalledist,
                            #                                turno=turno,
                            #                                dia=dia,
                            #                                inicio=detalledist.detalleactividadcriterio().desde,
                            #                                fin=detalledist.detalleactividadcriterio().hasta,
                            #                                estadosolicitud=1,
                            #                                modalidad=None,
                            #                                ordenmarcada=None,
                            #                                actividaddetallehorario=detalledist.detalleactividadcriterio()
                            #                                )
                            #     actividad.save(request)
                            #     tipodes = actividad.detalledistributivo.tipo_nombre()
                            #     des = actividad.detalledistributivo.nombre
                            #     log(u'Adicionó horario de actividad: %s - %s  turno: %s dia: %s' % (des, tipodes, str(turno), str(dia)), request, "add")
                            actividades += 1
                            if criterio == 177793:
                                bloquear = True
                                block_act = True
                                actividades_marcadas_criterio.append(int('{}{}'.format(cl['dia'], cl['turno'])))
                            else:
                                actividades_dia_turno.append(int('{}{}'.format(cl['dia'], cl['turno'])))
                    materias_transversal = profesor.profesormateria_set.filter(materia__nivel__periodo=periodo,
                                                                               materia__modeloevaluativo_id=27,
                                                                               hasta__gte=hoy, activo=True)
                    if materias_transversal:
                        if not clase.filter(materia__modeloevaluativo_id=27):
                            actividades += int(materias_transversal.aggregate(total=Sum('hora'))['total'])
                    if criterio == detalletutoria and not bloquear:
                        actividades_dia_turno += turno_turoria(periodo, profesor)
                    data['actividades'] = actividades
                    horastotales = DetalleDistributivo.objects.filter(
                        Q(distributivo__profesor=profesor, distributivo__periodo=periodo),
                        Q(criteriodocenciaperiodo_id__isnull=False) |
                        Q(criterioinvestigacionperiodo_id__isnull=False) |
                        Q(criteriogestionperiodo_id__isnull=False)).aggregate(valor=Sum('horas'))['valor']
                    data['horastotales'] = int(horastotales) if horastotales else 0
                    data['completo'] = horastotales == actividades
                    data['director'] = distributivo.carrera.get_director(periodo) if distributivo.carrera else None
                    data['aprobado'] = ClaseActividadEstado.objects.filter(profesor=profesor, periodo=periodo,status=True, estadosolicitud=2).order_by('-id').exists()
                    data['finalizado'] = claseactividad.exists() and not claseactividad.filter(finalizado=False).exists() or distributivo.horariofinalizado
                    data['horas'] = horas = 9 if distributivo.dedicacion_id == TIEMPO_DEDICACION_TIEMPO_COMPLETO_ID else 5
                    actividades_dia_turno += verificar_limite_dia(claseactividad, horas)
                    data['bloquear'] = bloquear
                    data['blocks_act'] = block_act
                    data['actividades_dia_turno'] = list(set(actividades_dia_turno))
                    data['actividades_marcadas_criterio'] = list(set(actividades_marcadas_criterio))
                    data['actividadesfinales'] = claseactividad
                    return render(request,'adm_criteriosactividadesdocentepos/horarioclasepos.html', data)
                except Exception as ex:
                    return HttpResponseRedirect(f"/adm_criteriosactividadesdocente?info={ex.__str__()}({sys.exc_info()[-1].tb_lineno})")

            return HttpResponseRedirect("/adm_criteriosactividadesdocente")
        else:
            try:
                return HttpResponseRedirect("/adm_criteriosactividadesdocente")
            except Exception as ex:
                return HttpResponseRedirect(f"/adm_criteriosactividadesdocente?info={ex.__str__()}({sys.exc_info()[-1].tb_lineno})")