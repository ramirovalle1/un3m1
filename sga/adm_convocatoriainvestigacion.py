# -*- coding: UTF-8 -*-
from django.db import transaction
from django.http import HttpResponseRedirect, JsonResponse
from django.shortcuts import render
from django.template.loader import get_template
from django.template.context import Context
from django.contrib.auth.decorators import login_required
from decorators import secure_module, last_access
from sga.commonviews import adduserdata, obtener_reporte
from sga.forms import ConvocatoriaInvestigacionForm
from sga.funciones import log
from sga.models import ConvocatoriaInvestigacion, ConvocatoriaInvestigacionSublinea, PropuestaLineaInvestigacion, \
    PropuestaSubLineaInvestigacion


@login_required(redirect_field_name='ret', login_url='/loginsga')
@transaction.atomic()
@secure_module
@last_access
def view(request):
    data = {}
    adduserdata(request, data)
    periodo = request.session['periodo']
    if request.method == 'POST':
        if 'action' in request.POST:
            action = request.POST['action']

            if action == 'add':
                    try:
                        form = ConvocatoriaInvestigacionForm(request.POST)
                        if form.is_valid():
                            convocatoria = ConvocatoriaInvestigacion(periodo=periodo,
                                                            nombre=form.cleaned_data['nombre'],
                                                            objetivo=form.cleaned_data['objetivo'],
                                                            duracion=form.cleaned_data['duracion'],
                                                            duracionmeses=form.cleaned_data['duracionmeses'],
                                                            presupuesto=form.cleaned_data['presupuesto'],
                                                            presupuestodesde=form.cleaned_data['presupuestodesde'],
                                                            presupuestohasta=form.cleaned_data['presupuestohasta'],
                                                            fechainicio=form.cleaned_data['fechainicio'],
                                                            fechafin=form.cleaned_data['fechafin'],
                                                            nota=form.cleaned_data['nota'],
                                                            compromiso=form.cleaned_data['compromiso'],
                                                            evaluacion=form.cleaned_data['evaluacion'],
                                                            publicar=form.cleaned_data['publicar'])
                            convocatoria.save(request)
                            log(u'Agrego Convocatoria de Investigación: %s' % convocatoria, request, "add")
                            return JsonResponse({"result": "ok"})
                        else:
                             raise NameError('Error')
                    except Exception as ex:
                        transaction.set_rollback(True)
                        return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

            elif action == 'edit':
                    try:
                        form = ConvocatoriaInvestigacionForm(request.POST)
                        if form.is_valid():
                            convocatoria = ConvocatoriaInvestigacion.objects.get(id=int(request.POST['id']))
                            convocatoria.nombre = form.cleaned_data['nombre']
                            convocatoria.objetivo = form.cleaned_data['objetivo']
                            convocatoria.duracion = form.cleaned_data['duracion']
                            convocatoria.duracionmeses = form.cleaned_data['duracionmeses']
                            convocatoria.presupuesto = form.cleaned_data['presupuesto']
                            convocatoria.presupuestodesde = form.cleaned_data['presupuestodesde']
                            convocatoria.presupuestohasta = form.cleaned_data['presupuestohasta']
                            convocatoria.fechainicio = form.cleaned_data['fechainicio']
                            convocatoria.fechafin = form.cleaned_data['fechafin']
                            convocatoria.publicar = form.cleaned_data['publicar']
                            convocatoria.nota = form.cleaned_data['nota']
                            convocatoria.compromiso = form.cleaned_data['compromiso']
                            convocatoria.evaluacion = form.cleaned_data['evaluacion']
                            convocatoria.save(request)
                            log(u'Edito Convocatoria en Investigación: %s' % convocatoria, request, "edit")
                            return JsonResponse({"result": "ok"})
                        else:
                             raise NameError('Error')
                    except Exception as ex:
                        transaction.set_rollback(True)
                        return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

            elif action == 'del':
                    try:
                        convocatoria = ConvocatoriaInvestigacion.objects.get(id=int(request.POST['id']))
                        # if ParticipanteGrupoInvestigacion.objects.filter(rol=rol).exists():
                        #     return JsonResponse({"result": "bad","mensaje": u"No puede eliminar, se esta utilizando en Participante."})
                        log(u'Elimino Convocatoria en Investigación: %s' % convocatoria, request, "del")
                        convocatoria.delete()
                        return JsonResponse({"result": "ok"})
                    except Exception as ex:
                        transaction.set_rollback(True)
                        return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

            elif action == 'addsublinea':
                try:
                    valor = 0
                    sublinea=ConvocatoriaInvestigacionSublinea.objects.filter(sublinea_id=request.POST['sublinea'],convocatoria_id=request.POST['id'], status=True)
                    if sublinea.exists():
                        log(u'elimino una sublinea de convocatoria investigacion: %s' % sublinea[0], request, "del")
                        sublinea[0].delete()
                    else:
                        sublinea = ConvocatoriaInvestigacionSublinea(sublinea_id=request.POST['sublinea'],convocatoria_id=request.POST['id'])
                        sublinea.save(request)
                        valor = 1
                        log(u'adiciono una sublinea de convocatoria investigacion: %s' % sublinea, request, "add")
                    return JsonResponse({"result": "ok", "valor": valor})

                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", "mensaje": "Error al eliminar los datos."})

            elif action == 'publicacion':
                try:
                    convocatoria = ConvocatoriaInvestigacion.objects.get(pk=int(request.POST['id']))
                    convocatoria.publicar = True if request.POST['val'] == 'y' else False
                    convocatoria.save(request)
                    return JsonResponse({"result": "ok"})
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad"})

            return JsonResponse({"result": "bad", "mensaje": u"Solicitud Incorrecta."})

    else:
        if 'action' in request.GET:
            action = request.GET['action']

            if action == 'add':
                    try:
                        data['title'] = u"Adicionar convocatoria"
                        data['form'] = ConvocatoriaInvestigacionForm()
                        return render(request, "adm_convocatoriainvestigacion/add.html", data)
                    except Exception as ex:
                        pass

            elif action == 'edit':
                try:
                    data['title'] = u"Editar convocatoria"
                    data['convocatoria'] = convocatoria = ConvocatoriaInvestigacion.objects.get(id=int(request.GET['id']))
                    data['form'] = ConvocatoriaInvestigacionForm(initial={'nombre': convocatoria.nombre,
                                                                          'fechainicio':convocatoria.fechainicio,
                                                                          'fechafin':convocatoria.fechafin,
                                                                          'objetivo':convocatoria.objetivo,
                                                                          'duracion':convocatoria.duracion,
                                                                          'duracionmeses':convocatoria.duracionmeses,
                                                                          'presupuesto':convocatoria.presupuesto,
                                                                          'presupuestodesde':convocatoria.presupuestodesde,
                                                                          'presupuestohasta':convocatoria.presupuestohasta,
                                                                          'nota': convocatoria.nota,
                                                                          'compromiso': convocatoria.compromiso,
                                                                          'evaluacion': convocatoria.evaluacion,
                                                                          'publicar':convocatoria.publicar})
                    return render(request, "adm_convocatoriainvestigacion/edit.html", data)
                except Exception as ex:
                    pass

            elif action == 'del':
                try:
                    data['title'] = u'Eliminar convocatoria'
                    data['convocatoria'] = ConvocatoriaInvestigacion.objects.get(pk=int(request.GET['id']))
                    return render(request, "adm_convocatoriainvestigacion/del.html", data)
                except Exception as ex:
                    pass

            elif action == 'sublinea':
                try:
                    data['title'] = u'Línea de investigación'
                    search = None
                    ids = None
                    data['convocatoria'] = convocatoria =  ConvocatoriaInvestigacion.objects.get(pk=int(request.GET['id']))
                    if 's' in request.GET:
                        search = request.GET['s']
                        listasub = PropuestaSubLineaInvestigacion.objects.values_list('linea__id').filter(nombre__icontains=search,status=True).distinct()
                        linea=PropuestaLineaInvestigacion.objects.filter(pk__in=listasub,status=True).order_by('nombre')
                    else:
                        linea = PropuestaLineaInvestigacion.objects.filter(status=True).order_by('nombre')
                    data['search'] = search if search else ""
                    data['ids'] = ids if ids else ""
                    data['lineas'] = linea
                    return render(request, "adm_convocatoriainvestigacion/sublinea.html", data)
                except Exception as ex:
                    pass

            if action == 'verdetalle':
                try:
                    data = {}
                    convocatoria = ConvocatoriaInvestigacion.objects.get(pk=int(request.GET['id']))
                    data['convocatoria'] = convocatoria
                    template = get_template("adm_convocatoriainvestigacion/detalle.html")
                    json_content = template.render(data)
                    return JsonResponse({"result": "ok", 'data': json_content})
                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

            return HttpResponseRedirect(request.path)

        else:
            data['title'] = u"Convocatoria de investigación"
            data['convocatorias'] =ConvocatoriaInvestigacion.objects.filter(periodo=periodo).order_by('fechainicio')
            data['reporte_0'] = obtener_reporte('convocatoria_investigacion')
            return render(request, "adm_convocatoriainvestigacion/view.html", data)

