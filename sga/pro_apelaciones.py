# -*- coding: latin-1 -*-
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.db.models import Avg
from django.http import HttpResponseRedirect, JsonResponse
from django.shortcuts import render
from django.template import Context
from django.template.loader import get_template
from decorators import secure_module, last_access
from sga.commonviews import adduserdata
from sga.forms import EvidenciaapelacionForm
from sga.funciones import log, generar_nombre
from sga.models import RespuestaRubrica, null_to_numeric, ApelacionEvaluacion, ApelacionEvaluacionRubrica


@login_required(redirect_field_name='ret', login_url='/loginsga')
@secure_module
@last_access
@transaction.atomic()
def view(request):
    data = {}
    adduserdata(request, data)
    data['title'] = u'Autoevaluación del docente'
    persona = request.session['persona']
    perfilprincipal = request.session['perfilprincipal']
    if not perfilprincipal.es_profesor():
        return HttpResponseRedirect("/?info=Solo los perfiles de profesores pueden ingresar al modulo.")
    data['profesor'] = profesor = perfilprincipal.profesor
    data['periodo'] = periodo = request.session['periodo']
    data['proceso'] = proceso = periodo.proceso_evaluativo()
    data['materias'] = materias = profesor.materias_imparte_periodo(periodo)
    data['evaluacion'] = None
    if request.method == 'POST':
        if 'action' in request.POST:
            action = request.POST['action']

            if action == 'addapelacion':
                try:
                    apelacion = ApelacionEvaluacion(observacion=request.POST['observacion'],
                                                    profesor=profesor,
                                                    periodo=periodo,
                                                    tipoinstrumento=request.POST['tipoinstrumento'],
                                                    tipocriterio=request.POST['tipocriterio'])
                    apelacion.save(request)
                    log(u'Adiciono apelación: %s' % apelacion, request, "add")
                    return JsonResponse({"result": "ok"})
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

            elif action == 'consultarapelacion':
                try:
                    apelacion = ApelacionEvaluacion.objects.get(pk=request.POST['idobs'])
                    obs = apelacion.observacion
                    return JsonResponse({"result": "ok","obs": obs})
                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

            elif action == 'editapelacion':
                try:
                    apelacion = ApelacionEvaluacion.objects.get(pk=request.POST['idobs'])
                    apelacion.observacion = request.POST['observacion']
                    apelacion.save(request)
                    return JsonResponse({"result": "ok"})
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

            elif action == 'addevidenciasapelaciones':
                try:
                    f = EvidenciaapelacionForm(request.POST, request.FILES)
                    # 2.5MB - 2621440
                    # 5MB - 5242880
                    # 10MB - 10485760
                    # 20MB - 20971520
                    # 50MB - 5242880
                    # 100MB 104857600
                    # 250MB - 214958080
                    # 500MB - 429916160
                    d = request.FILES['archivo']
                    newfilesd = d._name
                    ext = newfilesd[newfilesd.rfind("."):]
                    if not ext == '.pdf':
                        return JsonResponse({"result": "bad", "mensaje": u"Error, solo archivos .pdf."})
                    if d.size > 2621440:
                        return JsonResponse({"result": "bad", "mensaje": u"Error, archivo mayor a 2 Mb."})
                    if f.is_valid():
                        newfile = None
                        if 'archivo' in request.FILES:
                            newfile = request.FILES['archivo']
                            newfile._name = generar_nombre("apelacion_", newfile._name)
                        if ApelacionEvaluacionRubrica.objects.filter(respuestarubrica_id=request.POST['itemrubrica'], apelacion_id=request.POST['idapel']).exists():
                            apelacion = ApelacionEvaluacionRubrica.objects.get(respuestarubrica_id=request.POST['itemrubrica'], apelacion_id=request.POST['idapel'])
                            apelacion.observacion = f.cleaned_data['descripciones']
                            apelacion.archivo = newfile
                            apelacion.save(request)
                            log(u'Adicionó evidencias de apelaciones: %s' % apelacion, request, "add")
                        else:
                            apelacion = ApelacionEvaluacionRubrica(respuestarubrica_id=request.POST['itemrubrica'],
                                                                   apelacion_id=request.POST['idapel'],
                                                                   observacion=f.cleaned_data['descripciones'],
                                                                   archivo=newfile)
                            apelacion.save(request)
                            log(u'Adicionó evidencias de apelaciones: %s' % apelacion, request, "add")
                        return JsonResponse({"result": "ok"})
                    else:
                         raise NameError('Error')
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})


        return JsonResponse({"result": "bad", "mensaje": u"Solicitud Incorrecta."})
    else:
        if 'action' in request.GET:
            action = request.GET['action']

            if action == 'addevidenciasapelaciones':
                try:
                    data['title'] = u'Subir Evidencia'
                    data['form'] = EvidenciaapelacionForm
                    data['itemrubrica'] = request.GET['itemrubrica']
                    data['idapel'] = request.GET['idapel']
                    template = get_template("pro_apelaciones/add_evidenciaapelacion.html")
                    json_content = template.render(data)
                    return JsonResponse({"result": "ok", 'data': json_content, 'title': data['title']})
                except Exception as ex:
                    pass

            return HttpResponseRedirect(request.path)
        else:
            data['title'] = u'Resultados de la evaluación integral del desempeño docente'
            # data['distributivo'] = distributivo = profesor.distributivohoras(periodo)
            data['rubricaparesdocente'] = paresdocente = RespuestaRubrica.objects.filter(
                respuestaevaluacion__proceso__periodo_id=periodo, respuestaevaluacion__tipoinstrumento=3,
                respuestaevaluacion__profesor_id=profesor, rubrica__informativa=False, rubrica__tipo_criterio=1,
                respuestaevaluacion__proceso__periodo=periodo).distinct().order_by('rubrica__tipo_criterio')
            data['promparesdocente'] = round(null_to_numeric(paresdocente.aggregate(prom=Avg('valor'))['prom']), 2)
            apelpardocente = None
            if ApelacionEvaluacion.objects.filter(periodo=periodo,profesor=profesor,tipoinstrumento=3,tipocriterio=1).exists():
                apelpardocente = ApelacionEvaluacion.objects.get(periodo=periodo,profesor=profesor,tipoinstrumento=3,tipocriterio=1)
            data['apelpardocente'] = apelpardocente
            data['rubricaparesinves'] = paresinves = RespuestaRubrica.objects.filter(
                respuestaevaluacion__proceso__periodo_id=periodo, respuestaevaluacion__tipoinstrumento=3,
                respuestaevaluacion__profesor_id=profesor, rubrica__informativa=False, rubrica__tipo_criterio=2,
                respuestaevaluacion__proceso__periodo=periodo).distinct().order_by('rubrica__tipo_criterio')
            data['promparesinves'] = round(null_to_numeric(paresinves.aggregate(prom=Avg('valor'))['prom']), 2)
            apelparinve = None
            if ApelacionEvaluacion.objects.filter(periodo=periodo, profesor=profesor, tipoinstrumento=3, tipocriterio=2).exists():
                apelparinve = ApelacionEvaluacion.objects.get(periodo=periodo, profesor=profesor, tipoinstrumento=3, tipocriterio=2)
            data['apelparinve'] = apelparinve
            data['rubricaparesgestion'] = paresgestion = RespuestaRubrica.objects.filter(
                respuestaevaluacion__proceso__periodo_id=periodo, respuestaevaluacion__tipoinstrumento=3,
                respuestaevaluacion__profesor_id=profesor, rubrica__informativa=False, rubrica__tipo_criterio=3,
                respuestaevaluacion__proceso__periodo=periodo).distinct().order_by('rubrica__tipo_criterio')
            data['promparesgestion'] = round(null_to_numeric(paresgestion.aggregate(prom=Avg('valor'))['prom']), 2)
            apelparges = None
            if ApelacionEvaluacion.objects.filter(periodo=periodo, profesor=profesor, tipoinstrumento=3, tipocriterio=3).exists():
                apelparges = ApelacionEvaluacion.objects.get(periodo=periodo, profesor=profesor, tipoinstrumento=3, tipocriterio=3)
            data['apelparges'] = apelparges
            data['rubricadirdocente'] = dirdocente = RespuestaRubrica.objects.filter(
                respuestaevaluacion__proceso__periodo_id=periodo, respuestaevaluacion__tipoinstrumento=4,
                respuestaevaluacion__profesor_id=profesor, rubrica__informativa=False, rubrica__tipo_criterio=1,
                respuestaevaluacion__proceso__periodo=periodo).distinct().order_by('rubrica__tipo_criterio')
            data['promdirdocente'] = round(null_to_numeric(dirdocente.aggregate(prom=Avg('valor'))['prom']), 2)
            apeldirdoc = None
            if ApelacionEvaluacion.objects.filter(periodo=periodo, profesor=profesor, tipoinstrumento=4, tipocriterio=1).exists():
                apeldirdoc = ApelacionEvaluacion.objects.get(periodo=periodo, profesor=profesor, tipoinstrumento=4, tipocriterio=1)
            data['apeldirdoc'] = apeldirdoc
            data['rubricadirinves'] = dirinve = RespuestaRubrica.objects.filter(
                respuestaevaluacion__proceso__periodo_id=periodo, respuestaevaluacion__tipoinstrumento=4,
                respuestaevaluacion__profesor_id=profesor, rubrica__informativa=False, rubrica__tipo_criterio=2,
                respuestaevaluacion__proceso__periodo=periodo).distinct().order_by('rubrica__tipo_criterio')
            data['promdirinve'] = round(null_to_numeric(dirinve.aggregate(prom=Avg('valor'))['prom']), 2)
            apeldirinv = None
            if ApelacionEvaluacion.objects.filter(periodo=periodo, profesor=profesor, tipoinstrumento=4, tipocriterio=2).exists():
                apeldirinv = ApelacionEvaluacion.objects.get(periodo=periodo, profesor=profesor, tipoinstrumento=4, tipocriterio=2)
            data['apeldirinv'] = apeldirinv
            data['rubricadirgestion'] = dirgestion = RespuestaRubrica.objects.filter(
                respuestaevaluacion__proceso__periodo_id=periodo, respuestaevaluacion__tipoinstrumento=4,
                respuestaevaluacion__profesor_id=profesor, rubrica__informativa=False, rubrica__tipo_criterio=3,
                respuestaevaluacion__proceso__periodo=periodo).distinct().order_by('rubrica__tipo_criterio')
            data['promdirgestion'] = round(null_to_numeric(dirgestion.aggregate(prom=Avg('valor'))['prom']), 2)
            apeldirges = None
            if ApelacionEvaluacion.objects.filter(periodo=periodo, profesor=profesor, tipoinstrumento=4, tipocriterio=3).exists():
                apeldirges = ApelacionEvaluacion.objects.get(periodo=periodo, profesor=profesor, tipoinstrumento=4, tipocriterio=3)
            data['apeldirges'] = apeldirges
            return render(request, "pro_apelaciones/view.html", data)