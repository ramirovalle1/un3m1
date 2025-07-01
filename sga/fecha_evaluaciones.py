# -*- coding: latin-1 -*-
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.http import HttpResponseRedirect, JsonResponse
from django.shortcuts import render
from decorators import secure_module, last_access
from sga.commonviews import adduserdata
from sga.forms import FechaPeriodoEvaluacionesForm, CronoramaCalificacionesForm
from sga.funciones import log
from sga.models import ModeloEvaluativo, FechaEvaluacionCampoModelo, CronogramaEvaluacionModelo, Nivel, Materia


@login_required(redirect_field_name='ret', login_url='/loginsga')
@secure_module
@last_access
@transaction.atomic()
def view(request):
    data = {}
    adduserdata(request, data)
    periodo = request.session['periodo']
    if request.method == 'POST':
        action = request.POST['action']

        if action == 'edit':
            try:
                periodoevaluaciones = FechaEvaluacionCampoModelo.objects.get(pk=request.POST['id'])
                f = FechaPeriodoEvaluacionesForm(request.POST)
                if f.is_valid():
                    if f.cleaned_data['califdesde'] > f.cleaned_data['califhasta']:
                        return JsonResponse({"result": "bad", "mensaje": u"La fecha inicio debe ser menor que la fecha fin."})
                    periodoevaluaciones.inicio = f.cleaned_data['califdesde']
                    periodoevaluaciones.fin = f.cleaned_data['califhasta']
                    periodoevaluaciones.save(request)
                    log(u'Modifico campo de cronorama de calificaciones: %s' % periodoevaluaciones, request, "edit")
                    return JsonResponse({"result": "ok"})
                else:
                     raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        if action == 'delcronograma':
            try:
                cronograma = CronogramaEvaluacionModelo.objects.get(pk=request.POST['id'])
                log(u'Elimino cronorama de calificaciones: %s' % cronograma, request, "del")
                cronograma.delete()
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al eliminar los datos."})

        if action == 'addcronograma':
            try:
                modeloevaluativo = ModeloEvaluativo.objects.get(pk=request.POST['id'])
                f = CronoramaCalificacionesForm(request.POST)
                if f.is_valid():
                    periodo = request.session['periodo']
                    cronograma = CronogramaEvaluacionModelo(periodo=periodo,
                                                            modelo=modeloevaluativo,
                                                            nombre=f.cleaned_data['nombre'])
                    cronograma.save(request)
                    for campo in modeloevaluativo.campos():
                        fechaevaluacion = FechaEvaluacionCampoModelo(cronograma=cronograma,
                                                                     campo=campo,
                                                                     inicio=periodo.inicio,
                                                                     fin=periodo.fin)
                        fechaevaluacion.save(request)
                    log(u'Adiciono cronograma de calificaciones: %s' % cronograma, request, "edit")
                    return JsonResponse({"result": "ok"})
                else:
                     raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        if action == 'materias':
            try:
                cronograma = CronogramaEvaluacionModelo.objects.get(pk=request.POST['id'])
                log(u'Elimino materias del cronograma de calificaciones: %s' % cronograma, request, "del")
                cronograma.materias.clear()
                for materia in Materia.objects.filter(id__in=[int(x) for x in request.POST['listamaterias'].split(',')],status=True):
                    if materia.cronogramaevaluacionmodelo_set.filter(periodo=cronograma.periodo).exists():
                        for c in materia.cronogramaevaluacionmodelo_set.filter(periodo=cronograma.periodo):
                            c.materias.remove(materia)
                    cronograma.materias.add(materia)
                    # if not materia.nivel.cerrado:
                    #     materia.cerrado = False
                    #     materia.save(request)
                    #     materia.materiaasignada_set.update(cerrado=False)
                    log(u'Adiciono materias al cronograma de calificaciones: %s - %s' % (cronograma, materia.nombre_completo()), request, "add")
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        return JsonResponse({"result": "bad", "mensaje": u"Solicitud Incorrecta."})
    else:
        if 'action' in request.GET:
            action = request.GET['action']

            if action == 'edit':
                try:
                    periodoevaluaciones = FechaEvaluacionCampoModelo.objects.get(pk=request.GET['id'])
                    data['title'] = u'Editar fecha del campo: ' + periodoevaluaciones.campo.nombre
                    data['periodoevaluaciones'] = periodoevaluaciones
                    data['form'] = FechaPeriodoEvaluacionesForm(initial={'califdesde': periodoevaluaciones.inicio,
                                                                         'califhasta': periodoevaluaciones.fin})
                    return render(request, "fecha_evaluaciones/edit.html", data)
                except Exception as ex:
                    pass

            if action == 'materias':
                try:
                    data['title'] = u'Selección de materias del cronograma'
                    data['cronograma'] = cronograma = CronogramaEvaluacionModelo.objects.get(pk=request.GET['id'])
                    data['niveles'] = Nivel.objects.filter(periodo=cronograma.periodo).order_by('nivellibrecoordinacion__coordinacion')
                    return render(request, "fecha_evaluaciones/materias.html", data)
                except Exception as ex:
                    pass

            if action == 'delcronograma':
                try:
                    data['title'] = u'Eliminar cronograma'
                    data['cronograma'] = CronogramaEvaluacionModelo.objects.get(pk=request.GET['id'])
                    return render(request, "fecha_evaluaciones/delcronograma.html", data)
                except Exception as ex:
                    pass

            if action == 'addcronograma':
                try:
                    data['title'] = u'Nuevo cronograma de calificaciones'
                    data['modeloevaluativo'] = ModeloEvaluativo.objects.get(pk=request.GET['id'])
                    data['form'] = CronoramaCalificacionesForm()
                    return render(request, "fecha_evaluaciones/addcronograma.html", data)
                except Exception as ex:
                    pass

            return HttpResponseRedirect(request.path)
        else:
            data['title'] = u'Cronograma de evaluaciones - modelos evaluativos'
            data['modelo_evaluativo'] = ModeloEvaluativo.objects.filter(materia__nivel__periodo=periodo).distinct()
            return render(request, "fecha_evaluaciones/view.html", data)