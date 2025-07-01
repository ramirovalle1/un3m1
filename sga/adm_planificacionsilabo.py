# -*- coding: UTF-8 -*-
import datetime
from pydoc import plain
from django.db.models import Q
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.http import HttpResponseRedirect, JsonResponse
from django.forms import model_to_dict
from django.contrib import messages
from django.shortcuts import render
from decorators import secure_module, last_access
from sga.commonviews import adduserdata
from sga.forms import TipoPlanificacionClaseSilaboForm, PlanificacionClaseSilaboForm, PeriodoFechasRecuperacionForm, \
    PeriodoFechasTutoriasForm, PeriodoFechasLimitActForm
from sga.funciones import log, generar_nombre, remover_caracteres_especiales_unicode, MiPaginador
from sga.models import Materia, TipoPlanificacionClaseSilabo, PlanificacionClaseSilabo, PlanificacionClaseSilabo_Materia, Nivel, Periodo, Modalidad
from inno.models import FormatoPlanificacionRecurso
from inno.forms import FormatoPlanificacionRecursoForm
from django.template.loader import get_template

from sga.templatetags.sga_extras import encrypt

unicode = str


def daterange(start_date, end_date):
    for n in range(int((end_date - start_date).days)):
        yield start_date + datetime.timedelta(days=n)


@login_required(redirect_field_name='ret', login_url='/loginsga')
@secure_module
@last_access
@transaction.atomic()
def view(request):
    data = {}
    adduserdata(request, data)
    persona = request.session['persona']
    perfilprincipal = request.session['perfilprincipal']
    periodo = request.session['periodo']
    if request.method == 'POST':
        if 'action' in request.POST:
            action = request.POST['action']
            if action == 'addtipoplanificacion':
                try:
                    form = TipoPlanificacionClaseSilaboForm(request.POST)
                    if form.is_valid():
                        tipopla = TipoPlanificacionClaseSilabo(nombre=form.cleaned_data['tipoplanificacion'], periodo=periodo)
                        tipopla.save(request)
                        log(u'Adiciono Tipo de planificación de Silabo: %s' % tipopla, request, "addtipoplanificacion")
                        return JsonResponse({"result": False}, safe=False)
                    else:
                        raise NameError('Error')
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

            elif action == 'edittipoplanificacion':
                try:
                    form = TipoPlanificacionClaseSilaboForm(request.POST)
                    if form.is_valid():
                        planificacion = TipoPlanificacionClaseSilabo.objects.get(pk=int(encrypt(request.POST['id'])))
                        planificacion.nombre = form.cleaned_data['tipoplanificacion']
                        planificacion.save(request)
                        log(u'Edito la  Planificación %s:' % planificacion, request, "edit")
                        return JsonResponse({"result": False}, safe=False)
                    else:
                        raise NameError('Error')
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

            elif action == 'delplanificacion':
                try:
                    planificacion = TipoPlanificacionClaseSilabo.objects.get(pk=int(encrypt(request.POST['id'])), periodo=periodo)
                    if planificacion.planificacionclasesilabo_materia_set.filter(status=True).exists():
                        for materia in planificacion.planificacionclasesilabo_materia_set.filter(status=True):
                            log(u'Eliminó la materia %s de la planificacion : %s' % (materia, planificacion), request, "del")
                            materia = planificacion.planificacionclasesilabo_materia_set.all()
                            materia.delete()
                    if planificacion.planificacionclasesilabo_set.filter(status=True).exists():
                        for semana in planificacion.planificacionclasesilabo_set.filter(status=True):
                            log(u'Eliminó la semana %s de la Planificacion la semana  %s' % (semana, planificacion), request, "del")
                            semana.delete()
                    log(u'Eliminó Planificación de Silabo: %s del periodo %s' % (planificacion, periodo), request, "del")
                    planificacion.delete()
                    res_json = {"error": False}
                except Exception as ex:
                    res_json = {'error': True, "message": "Error: {}".format(ex)}
                return JsonResponse(res_json, safe=False)

            elif action == 'addplanificacionsemana':
                try:
                    form = PlanificacionClaseSilaboForm(request.POST)
                    if form.is_valid():
                        # if int(request.POST['semana']) < 1:
                        if form.cleaned_data['fechainicio'] > form.cleaned_data['fechafin']:
                            return JsonResponse({"result": "bad", "mensaje": u"La fecha de inicio debe ser menor a la fecha fin."})
                        # if int(request.POST['semana']) < 1:
                        #     return JsonResponse({"result": "bad","mensaje": u"El Numero de Semana debe ser mayor a 0."})
                        if PlanificacionClaseSilabo.objects.filter(tipoplanificacion_id=int(encrypt(request.POST['id'])), semana=form.cleaned_data['semana']).exclude(semana=0).exists():
                            return JsonResponse({"result": "bad", "mensaje": u"El Numero de Semana ya a sido ingresado en está Planificación."})
                        if PlanificacionClaseSilabo.objects.filter(Q(tipoplanificacion_id=int(encrypt(request.POST['id']))), (Q(fechainicio=form.cleaned_data['fechainicio']) | Q(fechafin=form.cleaned_data['fechafin']))).exists():
                            itemplan = PlanificacionClaseSilabo.objects.get(Q(tipoplanificacion_id=int(encrypt(request.POST['id']))), Q(fechainicio=form.cleaned_data['fechainicio']) | Q(fechafin=form.cleaned_data['fechafin']))
                            return JsonResponse({"result": "bad", "mensaje": u"Las Fechas ingresadas ya existen en la Planificación Numero de Semana: %s" % itemplan.semana})
                        orden = PlanificacionClaseSilabo.objects.filter(status=True, tipoplanificacion_id=int(encrypt(request.POST['id']))).order_by('fechainicio').count() + 1
                        planificacionsemanal = PlanificacionClaseSilabo(tipoplanificacion_id=int(encrypt(request.POST['id'])),
                                                                        fechainicio=form.cleaned_data['fechainicio'],
                                                                        fechafin=form.cleaned_data['fechafin'],
                                                                        semana=form.cleaned_data['semana'],
                                                                        parcial=form.cleaned_data['parcial'],
                                                                        obejetivosemanal=form.cleaned_data['obejetivosemanal'],
                                                                        orden=orden)
                        planificacionsemanal.save(request)
                        log(u'Adiciono una Semana de Planificación de Silabo: %s' % planificacionsemanal, request, "add")
                        return JsonResponse({"result": False}, safe=False)
                    else:
                        raise NameError('Error')
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

            elif action == 'editplanificacionsemanal':
                try:
                    form = PlanificacionClaseSilaboForm(request.POST)
                    if form.is_valid():
                        planificacion = PlanificacionClaseSilabo.objects.get(pk=int(encrypt(request.POST['id'])))
                        if form.cleaned_data['fechainicio'] > form.cleaned_data['fechafin']:
                            return JsonResponse({"result": "bad", "mensaje": u"La fecha de inicio debe ser menor a la fecha fin."})
                        # if int(form.cleaned_data['semana'])<1:
                        #     return JsonResponse({"result": "bad","mensaje": u"El Numero de Semana debe ser mayor a 0."})
                        if PlanificacionClaseSilabo.objects.filter(tipoplanificacion_id=planificacion.tipoplanificacion.id, semana=form.cleaned_data['semana']).exclude(pk=planificacion.id).exclude(semana=0).exists():
                            return JsonResponse({"result": "bad", "mensaje": u"El Numero de Semana ya a sido ingresado en está Planificación."})
                        if PlanificacionClaseSilabo.objects.filter(Q(tipoplanificacion_id=planificacion.tipoplanificacion.id), (Q(fechainicio=form.cleaned_data['fechainicio']) | Q(fechafin=form.cleaned_data['fechafin']))).exclude(pk=planificacion.id).exists():
                            return JsonResponse({"result": "bad", "mensaje": u"Las Fechas ingresadas ya existen en la Planificación Numero de Semana: %s" % planificacion.semana})
                        planificacion.fechainicio = form.cleaned_data['fechainicio']
                        planificacion.examen = form.cleaned_data['examen']
                        planificacion.fechafin = form.cleaned_data['fechafin']
                        planificacion.semana = form.cleaned_data['semana']
                        planificacion.parcial = form.cleaned_data['parcial']
                        planificacion.obejetivosemanal = form.cleaned_data['obejetivosemanal']
                        planificacion.save(request)
                        log(u'Edito la semana: %s de Planificación %s:' % (planificacion.semana, planificacion), request, "add")
                        return JsonResponse({'result': False, 'mensaje': 'Edicion Exitosa'})
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

            elif action == 'delplanificacionsemanal':
                try:
                    planificacion = PlanificacionClaseSilabo.objects.get(pk=int(encrypt(request.POST['id'])))
                    log(u'Eliminó la Planificación %s de la semana  %s' % (planificacion, planificacion.semana), request, "del")
                    planificacion.delete()
                    res_json = {"error": False}
                except Exception as ex:
                    res_json = {'error': True, "message": "Error: {}".format(ex)}
                return JsonResponse(res_json, safe=False)

            elif action == 'materias':
                try:
                    planificacion = TipoPlanificacionClaseSilabo.objects.get(pk=int(encrypt(request.POST['id'])))
                    materias = Materia.objects.filter(id__in=[int(x) for x in request.POST['listamaterias'].split(',')])
                    for materia in materias:
                        if not planificacion.planificacionclasesilabo_materia_set.filter(materia_id=materia.id).exists():
                            plani = PlanificacionClaseSilabo_Materia(tipoplanificacion=planificacion, materia=materia)
                            plani.save(request)
                            log(u'Adicionó nueva planificacion de silabo: %s' % plani, request, "add")
                    if planificacion.planificacionclasesilabo_materia_set.all().exclude(materia_id__in=materias).exists():
                        for materia in planificacion.planificacionclasesilabo_materia_set.all().exclude(materia_id__in=materias):
                            log(u'Eliminó Bibliografia complentaria: %s' % materia, request, "del")
                        planificacion.planificacionclasesilabo_materia_set.all().exclude(materia_id__in=materias).delete()

                    return JsonResponse({"result": "ok"})
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

            elif action == 'editfechaexamenrecuperacion':
                try:
                    form = PeriodoFechasRecuperacionForm(request.POST)
                    if not form.is_valid():
                        # [(k, v[0]) for k, v in f.errors.items()]
                        for k, v in form.errors.items():
                            raise NameError(v[0])
                    periodo = Periodo.objects.get(pk=int(encrypt(request.POST['id'])))
                    periodo.fecha_recuperacion_inicio = form.cleaned_data['fecha_recuperacion_inicio']
                    periodo.fecha_recuperacion_fin = form.cleaned_data['fecha_recuperacion_fin']
                    periodo.save(request)
                    log(u'Editar Fechas de Examen de Recuperacion del Periodo %s:' % periodo.nombre, request, "edit")
                    return JsonResponse({"result": False}, safe=False)
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

            elif action == 'editfechalimiteingresoact':
                try:
                    from inno.models import PeriodoAcademia
                    form = PeriodoFechasLimitActForm(request.POST)
                    if not form.is_valid():
                        # [(k, v[0]) for k, v in f.errors.items()]
                        for k, v in form.errors.items():
                            raise NameError(v[0])
                    periodoacademia = PeriodoAcademia.objects.get(periodo_id=int(encrypt(request.POST['id'])))
                    periodoacademia.fecha_limite_ingreso_act = form.cleaned_data['fecha_limite_ingresoact']
                    periodoacademia.save(request)
                    log(u'Editar Fechas limite de ingreso de actividades del Periodo %s:' % periodoacademia, request, "edit")
                    return JsonResponse({"result": False}, safe=False)
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

            elif action == 'editperiodoacademicofechastutoria':
                try:
                    form = PeriodoFechasTutoriasForm(request.POST)
                    if not form.is_valid():
                        # [(k, v[0]) for k, v in f.errors.items()]
                        for k, v in form.errors.items():
                            raise NameError(v[0])
                    periodo_academico = periodo.get_periodoacademia()
                    periodo_academico.fecha_limite_horario_tutoria = form.cleaned_data['fecha_limite_horario_tutoria']
                    periodo_academico.fecha_fin_horario_tutoria = form.cleaned_data['fecha_fin_horario_tutoria']
                    periodo_academico.fecha_maxima_solicitud = form.cleaned_data['fecha_maxima_solicitud']
                    periodo_academico.save(request)
                    #periodo_academico.actualizar_fechas_tutorias()
                    log(u'Editar Fechas  de Tutorias del Periodo Academico %s:' % periodo_academico, request, "edit")
                    return JsonResponse({"result": "ok"})
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", "mensaje": u"Error: %s" % str(ex)})

            if action == 'crearperiodoacademia':
                from inno.models import PeriodoAcademia
                planid = request.POST['id']
                plan = TipoPlanificacionClaseSilabo.objects.get(id=planid)
                for p in plan.detalle_planificacion():
                    if p.semana == 3:
                        if PeriodoAcademia.objects.filter(periodo=request.session['periodo']).exists():
                            periodoacademia = PeriodoAcademia.objects.get(periodo=request.session['periodo'])
                            if not periodoacademia.fecha_limite_horario_tutoria == p.fechafin:
                                periodoacademia.fecha_limite_horario_tutoria = p.fechafin
                                periodoacademia.save()
                        else:
                            periodoacademia = PeriodoAcademia(periodo=request.session['periodo'], fecha_limite_horario_tutoria=p.fechafin)
                            periodoacademia.save()
                        return JsonResponse({"result": "ok"})

            elif action == 'addformatorecurso':
                try:
                    form = FormatoPlanificacionRecursoForm(request.POST)
                    if form.is_valid():
                        registro = FormatoPlanificacionRecurso(
                            descripcion=form.cleaned_data['descripcion'],
                            activo=form.cleaned_data['activo']
                        )
                        registro.save(request)
                        modalidades = request.POST.getlist('modalidad')
                        if modalidades:
                            modalidades = Modalidad.objects.filter(pk__in=modalidades)
                            for m in modalidades:
                                registro.modalidad.add(m)
                        if 'archivo' in request.FILES:
                            newfile = request.FILES['archivo']
                            newfile._name = generar_nombre('formato_{}'.format(remover_caracteres_especiales_unicode(registro.descripcion.lower())), newfile._name)
                            registro.archivo = newfile
                            registro.save(request)
                        log(u'Adicionó Formato Planificacion Recurso: %s' % (registro), request, "add")
                        messages.success(request, 'Registro guardado con éxito.')
                        return JsonResponse({"result": False}, safe=False)
                    else:
                        return JsonResponse({'result': True, "form": [{k: v[0]} for k, v in form.errors.items()], "mensaje": "Error en el formulario"})
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": True, "mensaje": '%s' % ex}, safe=False)

            elif action == 'editformatorecurso':
                try:
                    registro = FormatoPlanificacionRecurso.objects.get(pk=request.POST['id'])
                    form = FormatoPlanificacionRecursoForm(request.POST)
                    if form.is_valid():
                        registro.descripcion = form.cleaned_data['descripcion']
                        registro.activo = form.cleaned_data['activo']
                        modalidades = request.POST.getlist('modalidad')
                        if modalidades:
                            registro.modalidad.clear()
                            modalidades = Modalidad.objects.filter(pk__in=modalidades)
                            for m in modalidades:
                                registro.modalidad.add(m)
                        if 'archivo' in request.FILES:
                            newfile = request.FILES['archivo']
                            newfile._name = generar_nombre('formato_{}'.format(remover_caracteres_especiales_unicode(registro.descripcion.lower())), newfile._name)
                            registro.archivo = newfile
                        registro.save(request)
                        log(u'Editó Formato Planificacion Recurso: %s' % registro, request, "edit")
                        messages.success(request, 'Registro editado con éxito.')
                        return JsonResponse({"result": False}, safe=False)
                    else:
                        return JsonResponse({'result': True, "form": [{k: v[0]} for k, v in form.errors.items()], "message": "Error en el formulario"})
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": True, "mensaje": "Intentelo más tarde."}, safe=False)

            elif action == 'delformatorecurso':
                try:
                    registro = FormatoPlanificacionRecurso.objects.get(pk=int(encrypt(request.POST['id'])))
                    registro.status = False
                    registro.save(request)
                    log(u'Elimino Formato Planificacion Recurso: %s' % registro, request, "del")
                    messages.success(request, 'Registro eliminado con éxito.')
                    res_json = {"error": False}
                except Exception as ex:
                    transaction.set_rollback(True)
                    res_json = {'error': True, "message": "Error: {}".format(ex)}
                return JsonResponse(res_json, safe=False)

            return JsonResponse({"result": "bad", "mensaje": u"Solicitud Incorrecta."})
    else:
        if 'action' in request.GET:
            action = request.GET['action']

            if action == 'addtipoplanificacion':
                try:
                    form = TipoPlanificacionClaseSilaboForm()
                    data['form'] = form
                    template = get_template("adm_planificacionsilabo/addtipoplanificacion.html")
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    pass

            elif action == 'edittipoplanificacion':
                try:
                    data['tipoplanificacion'] = planificacion = TipoPlanificacionClaseSilabo.objects.get(pk=int(encrypt(request.GET['id'])))
                    data['form'] = TipoPlanificacionClaseSilaboForm(initial={'tipoplanificacion': planificacion.nombre})
                    template = get_template("adm_planificacionsilabo/edittipoplanificacion.html")
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    pass

            elif action == 'addplanificacionsemana':
                try:
                    data['tipoplanificacion'] = tipo = TipoPlanificacionClaseSilabo.objects.get(pk=int(encrypt(request.GET['id'])))
                    form = PlanificacionClaseSilaboForm(initial={'tipoplanificacion': tipo.nombre})
                    form.adicionar()
                    data['form'] = form
                    template = get_template("adm_planificacionsilabo/addplanificacionsemana.html")
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    pass

            elif action == 'editplanificacionsemanal':
                try:
                    data['title'] = u'Editar semana de Planificación de Clase'
                    data['planificacion'] = planificacion = PlanificacionClaseSilabo.objects.get(pk=int(encrypt(request.GET['id'])))
                    form = PlanificacionClaseSilaboForm(initial={'tipoplanificacion': planificacion.tipoplanificacion,
                                                                 'fechainicio': planificacion.fechainicio,
                                                                 'fechafin': planificacion.fechafin,
                                                                 'semana': planificacion.semana,
                                                                 'parcial': planificacion.parcial,
                                                                 'examen': planificacion.examen,
                                                                 'obejetivosemanal': planificacion.obejetivosemanal})
                    form.adicionar()
                    data['form'] = form
                    template = get_template("adm_planificacionsilabo/editplanificacionsemanal.html")
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    pass

            elif action == 'delplanificacionsemanal':
                try:
                    data['title'] = u'Eliminar de Planificación se de semana de Clase'
                    data['planificacion'] = PlanificacionClaseSilabo.objects.get(pk=int(encrypt(request.GET['id'])))
                    return render(request, "adm_planificacionsilabo/delplanificacionsemanal.html", data)
                except Exception as ex:
                    pass

            if action == 'materias':
                try:
                    data['title'] = u'Selección de materias'
                    data['planificacion'] = plani = TipoPlanificacionClaseSilabo.objects.get(pk=int(encrypt(request.GET['id'])))
                    data['niveles'] = Nivel.objects.filter(periodo=plani.periodo).order_by('nivellibrecoordinacion__coordinacion')
                    # tipo = TipoPlanificacionClaseSilabo.objects.get(id=25)
                    # for plaa in tipo.planificacionclasesilabo_materia_set.filter(status=True):
                    #     if not plaa.materia.cerrado and plaa.materia.silabo_actual().silabosemanal_set.filter(status=True).exists() and plaa.materia.tipomateria==2:
                    #         # planificacionsilaboact = PlanificacionClaseSilabo.objects.filter(tipoplanificacion__planificacionclasesilabo_materia__materia=plaa.materia, status=True).exclude(semana=0).order_by('-orden')
                    #         planificacionsilaboact = tipo.planificacionclasesilabo_set.filter(tipoplanificacion__planificacionclasesilabo_materia__materia=plaa.materia,status=True).exclude(semana=0).order_by('-orden')
                    #         for p in planificacionsilaboact:
                    #             if plaa.materia.silabo_actual().silabosemanal_set.filter( numsemana=p.orden, status=True).exists():
                    #                 semana = plaa.materia.silabo_actual().silabosemanal_set.get( numsemana=p.orden, status=True)
                    #                 if semana:
                    #                     if semana.fechainiciosemana != p.fechainicio or semana.fechafinciosemana != p.fechafin:
                    #                         semana.fechainiciosemana = p.fechainicio
                    #                         semana.fechafinciosemana = p.fechafin
                    #                         semana.save()
                    return render(request, "adm_planificacionsilabo/materia.html", data)
                except Exception as ex:
                    pass

            if action == 'editfechaexamenrecuperacion':
                try:
                    data['tipoplanificacion'] = periodo = Periodo.objects.get(pk=int(periodo.id))
                    inicio, fin = periodo.fecha_recuperacion_inicio, periodo.fecha_recuperacion_fin
                    if periodo.fecha_recuperacion_inicio is None or periodo.fecha_recuperacion_fin is None:
                        inicio = datetime.datetime.now().date()
                        fin = datetime.datetime.now().date()
                    form = PeriodoFechasRecuperacionForm(initial={'fecha_recuperacion_inicio': inicio, 'fecha_recuperacion_fin': fin})
                    data['form'] = form
                    template = get_template("adm_planificacionsilabo/editperiodofechasrecuperacion.html")
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    pass

            if action == 'editfechalimiteingresoact':
                try:
                    from inno.models import PeriodoAcademia
                    data['periodoacademia'] = periodoacademi = PeriodoAcademia.objects.get(periodo_id=int(periodo.id))
                    # inicio, fin = periodo.fecha_recuperacion_inicio, periodo.fecha_recuperacion_fin
                    fecha_limite = periodoacademi.fecha_limite_ingreso_act
                    if fecha_limite is None:
                        fecha_limite = datetime.datetime.now().date()
                    form = PeriodoFechasLimitActForm(initial={'fecha_limite_ingresoact': fecha_limite})
                    data['form'] = form
                    template = get_template("adm_planificacionsilabo/editfechalimiteingresoact.html")
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    pass

            if action == 'editperiodoacademicofechastutoria':
                try:
                    data['title'] = u'Configuración Fechas Tutorias'
                    data['ePeriodoAcademia'] = ePeriodoAcademia = periodo.get_periodoacademia()
                    inicio, fin, maxima = ePeriodoAcademia.fecha_limite_horario_tutoria, ePeriodoAcademia.fecha_fin_horario_tutoria, ePeriodoAcademia.fecha_maxima_solicitud
                    if inicio is None or fin is None:
                        inicio = datetime.datetime.now().date()
                        fin = datetime.datetime.now().date()
                        maxima = datetime.datetime.now().date()
                    data['form'] = PeriodoFechasTutoriasForm(initial={'fecha_limite_horario_tutoria': inicio,'fecha_fin_horario_tutoria': fin, 'fecha_maxima_solicitud':maxima})
                    return render(request, "adm_planificacionsilabo/editperiodoacademicofechastutoria.html", data)
                except Exception as ex:
                    pass

            elif action == 'viewformatorecurso':
                try:
                    data['title'] = u'Formato Planificación Recurso'
                    data['subtitle'] = u'Listado de formatos para planificación de recursos'
                    data['action'] = action
                    ids = None
                    search, filtro, url_vars = request.GET.get('s', ''), Q(status=True), f'?action={action}'

                    if search:
                        data['s'] = search = request.GET['s'].strip()
                        ss = search.split(' ')
                        url_vars += f"&s={search}"
                        if search:
                            filtro = filtro & (Q(descripcion__icontains=search) | Q(modalidad__nombre__icontains=search))

                    if 'id' in request.GET:
                        ids = int(request.GET['id'])
                        filtro = filtro & (Q(status=True))

                    registros = FormatoPlanificacionRecurso.objects.filter(filtro).order_by('descripcion').distinct()
                    paging = MiPaginador(registros, 10)

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
                    data['ids'] = ids if ids else ""
                    data['listado'] = page.object_list
                    data['totalregistros'] = registros.count()
                    data['url_vars'] = url_vars
                    return render(request, "adm_planificacionsilabo/viewformatoplanificacion.html", data)
                except Exception as ex:
                    pass

            elif action == 'addformatorecurso':
                try:
                    data['action'] = request.GET['action']
                    data['title'] = u'Adicionar registro'
                    form = FormatoPlanificacionRecursoForm()
                    form.fields['archivo'].required = True
                    data['form'] = form
                    template = get_template("adm_planificacionsilabo/modal/formplanificacion.html")
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    return JsonResponse({"result": False, "mensaje": u"Error al obtener los datos."})

            elif action == 'editformatorecurso':
                try:
                    data['title'] = u'Editar registro'
                    data['action'] = request.GET['action']
                    data['id'] = id = int(encrypt(request.GET['id']))
                    if id > 0:
                        data['registro'] = registro = FormatoPlanificacionRecurso.objects.get(pk=id)
                        form = FormatoPlanificacionRecursoForm(initial=model_to_dict(registro))
                        data['form'] = form
                        template = get_template("adm_planificacionsilabo/modal/formplanificacion.html")
                        return JsonResponse({"result": True, 'data': template.render(data)})
                    else:
                        return JsonResponse({"result": False, "mensaje": u"Problemas al obtener los datos. Intente nuevamente más tarde."})
                except Exception as ex:
                    return JsonResponse({"result": False, "mensaje": u"Error al obtener los datos."})
            return HttpResponseRedirect(request.path)

        else:
            from inno.models import PeriodoAcademia
            data['title'] = u'Planificación de Sílabo'
            data['persona'] = persona
            data['periodo'] = periodo
            data['tipoplanificaciones'] = planificaciones = TipoPlanificacionClaseSilabo.objects.filter(status=True, periodo=periodo).distinct().order_by('nombre')
            # mayormaterias = 0
            # for s in planificaciones:
            #     if s.detalle_planificacion:
            #         count = PlanificacionClaseSilabo_Materia.objects.filter(tipoplanificacion=s).count()
            #         if count > mayormaterias:
            #             mayormaterias = count
            #             data['planmayor'] = s.id
            return render(request, "adm_planificacionsilabo/view.html", data)
