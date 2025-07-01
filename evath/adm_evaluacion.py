# -*- coding: UTF-8 -*-
import io
import random
import sys

import openpyxl
import xlsxwriter
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.db.models import Q
import xlwt
from django.forms import model_to_dict
from django.http import HttpResponse, HttpResponseRedirect, JsonResponse
from django.template import Context
from django.template.loader import get_template
from xlwt import *
from django.shortcuts import render, redirect
from decorators import secure_module, last_access
from sagest.forms import DepartamentoForm, IntegranteDepartamentoForm, ResponsableDepartamentoForm, \
    SeccionDepartamentoForm
from sagest.models import Departamento, SeccionDepartamento, OpcionSistema
from settings import EMAIL_DOMAIN
from sga.commonviews import adduserdata
from sga.templatetags.sga_extras import encrypt
from .forms import EvaluacionPreguntaForm, PersonaEvaluacionForm, EvaluacionForm, BancoPreguntasForm, \
    EvaluacionPreguntaEditForm
from sga.funciones import MiPaginador, log, generar_nombre, remover_caracteres_especiales_unicode
from sga.models import Administrativo, Persona
from .models import *
from django.db.models import Sum, Q, F, FloatField
from django.db.models.functions import Coalesce


@login_required(redirect_field_name='ret', login_url='/loginsga')
@secure_module
@last_access
@transaction.atomic()
def view(request):
    data = {}
    adduserdata(request, data)
    usuario = request.user
    if request.method == 'POST':
        res_json = []
        action = request.POST['action']

        if action == 'addevaluacion':
            try:
                f = EvaluacionForm(request.POST)
                if f.is_valid():
                    nombre_url = remover_caracteres_especiales_unicode(request.POST['nombre']).lower().replace('\t','').replace(' ', '_')
                    if Evaluacion.objects.filter(nombreurl=nombre_url).exists():
                        transaction.set_rollback(True)
                        return JsonResponse({"result": "bad", "mensaje": u"Ya existe una encuesta con ese nombre %s" % nombre_url})
                    filtro = Evaluacion(nombre=f.cleaned_data['nombre'],
                                     detalle=f.cleaned_data['detalle'],
                                     password=f.cleaned_data['password'],
                                     verresultados=f.cleaned_data['verresultados'],
                                     notamin=f.cleaned_data['notamin'],
                                     notamax=f.cleaned_data['notamax'],
                                     numpreguntas=f.cleaned_data['numpreguntas'],
                                     numintentos=f.cleaned_data['numintentos'],
                                     minevaluacion=f.cleaned_data['minevaluacion'],
                                     publicar =f.cleaned_data['publicar'])
                    filtro.nombreurl = nombre_url
                    filtro.save(request)
                    log(u'Adiciono Evaluación: %s' % filtro, request, "add")
                    return JsonResponse({"result": "ok"})
                else:
                    raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos. %s" % ex})

        if action == 'editevaluacion':
            try:
                f = EvaluacionForm(request.POST)
                if f.is_valid():
                    filtro = Evaluacion.objects.get(pk=int(request.POST['id']))
                    filtro.nombre=f.cleaned_data['nombre']
                    filtro.detalle = f.cleaned_data['detalle']
                    filtro.password = f.cleaned_data['password']
                    filtro.verresultados = f.cleaned_data['verresultados']
                    filtro.notamin = f.cleaned_data['notamin']
                    filtro.notamax = f.cleaned_data['notamax']
                    filtro.numpreguntas = f.cleaned_data['numpreguntas']
                    filtro.numintentos = f.cleaned_data['numintentos']
                    filtro.minevaluacion = f.cleaned_data['minevaluacion']
                    filtro.publicar = f.cleaned_data['publicar']
                    filtro.save(request)
                    log(u'Editó Evaluación: %s' % filtro, request, "add")
                    return JsonResponse({"result": "ok"})
                else:
                    raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos. %s" % ex})

        if action == 'delevaluacion':
            try:
                filtro = Evaluacion.objects.get(pk=request.POST['id'])
                filtro.status = False
                filtro.save(request)
                log(u'Elimino Evaluación: %s' % filtro, request, "del")
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al eliminar los datos."})

        if action == 'addpregunta':
            try:
                f = BancoPreguntasForm(request.POST)
                if f.is_valid():
                    filtro = BancoPreguntas(enunciado = f.cleaned_data['enunciado'],
                                            ayuda=f.cleaned_data['ayuda'],
                                            tiporespuesta =f.cleaned_data['tiporespuesta'])
                    filtro.save(request)
                    respuestas = request.POST.getlist('respuestas[]')
                    if respuestas:
                        count = 0
                        while count < len(respuestas):
                            detalle = respuestas[count]
                            correcta = True if respuestas[count+1] == '1' else False
                            resp = BancoPreguntasRespuestas(pregunta=filtro, detalle=detalle, es_correcta=correcta)
                            resp.save(request)
                            count += 2
                    log(u'Adiciono Nueva Pregunta: %s' % filtro, request, "add")
                    messages.success(request, 'Pregunta guardada con exito')
                    return JsonResponse({"result": "ok"})
                else:
                    raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos. %s" % ex})

        if action == 'editpregunta':
            try:
                f = BancoPreguntasForm(request.POST)
                if f.is_valid():
                    filtro = BancoPreguntas.objects.get(pk=int(request.POST['id']))
                    filtro.enunciado = f.cleaned_data['enunciado']
                    filtro.ayuda = f.cleaned_data['ayuda']
                    filtro.tiporespuesta = f.cleaned_data['tiporespuesta']
                    filtro.save(request)
                    respuestasedit = request.POST.getlist('respuestasedit[]')
                    idsevaluados = []
                    if respuestasedit:
                        countedit = 0
                        while countedit < len(respuestasedit):
                            id = respuestasedit[countedit]
                            detalle = respuestasedit[countedit+1]
                            correcta = True if respuestasedit[countedit+2] == '1' else False
                            resp = BancoPreguntasRespuestas.objects.get(pk=id)
                            resp.detalle=detalle
                            resp.es_correcta = correcta
                            resp.save(request)
                            countedit += 3
                            idsevaluados.append(id)
                    respuestasborrar = BancoPreguntasRespuestas.objects.filter(pregunta=filtro, status=True).exclude(pk__in=idsevaluados)
                    for respb in respuestasborrar:
                        respb.status = False
                        respb.save(request)
                    respuestas = request.POST.getlist('respuestas[]')
                    if respuestas:
                        count = 0
                        while count < len(respuestas):
                            detalle = respuestas[count]
                            correcta = True if respuestas[count+1] == '1' else False
                            resp = BancoPreguntasRespuestas(pregunta=filtro, detalle=detalle)
                            resp.es_correcta = correcta
                            resp.save(request)
                            count += 2
                    log(u'Editó Pregunta: %s' % filtro, request, "add")
                    return JsonResponse({"result": "ok"})
                else:
                    raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos. %s" % ex})

        if action == 'deletepregunta':
            try:
                with transaction.atomic():
                    instancia = BancoPreguntas.objects.get(pk=int(request.POST['id']))
                    instancia.status = False
                    instancia.save(request)
                    log(u'Elimino Pregunta del Banco de Preguntas Evaluación: %s' % instancia, request, "delete")
                    res_json = {"error": False}
            except Exception as ex:
                res_json = {'error': True, "message": "Error: {}".format(ex)}
            return JsonResponse(res_json, safe=False)

        if action == 'addpreguntaevaluacion':
            try:
                with transaction.atomic():
                    idcab = int(request.POST['id'])
                    cabpregunta = Evaluacion.objects.get(pk=idcab)
                    if EvaluacionPregunta.objects.filter(status=True, cab=cabpregunta, pregunta_id=int(request.POST['pregunta'])):
                        res_json.append({'result': True, "message": 'Pregunta ya existe'})
                        return JsonResponse(res_json, safe=False)
                    form = EvaluacionPreguntaForm(request.POST)
                    if form.is_valid():
                        if not form.cleaned_data['valor'] > 0:
                            transaction.set_rollback(True)
                            return JsonResponse({"result": True, "mensaje": "Valor de la pregunta debe ser mayor a cero."}, safe=False)
                        totalpreguntas = EvaluacionPregunta.objects.filter(cab=cabpregunta, status=True).aggregate(total=Coalesce(Sum(F('valor'), output_field=FloatField()), 0)).get('total') + form.cleaned_data['valor']
                        if totalpreguntas > cabpregunta.notamax:
                            transaction.set_rollback(True)
                            return JsonResponse({"result": True, "mensaje": "Valor de la pregunta excede el valor de nota maxima configurada."}, safe=False)
                        filtro = EvaluacionPregunta(cab=cabpregunta,
                                                    pregunta=form.cleaned_data['pregunta'],
                                                    valor=form.cleaned_data['valor'])
                        filtro.save(request)
                        log(u'Adiciono Pregunta a Evaluacón: %s' % filtro, request, "add")
                        return JsonResponse({"result": False}, safe=False)
                    else:
                        transaction.set_rollback(True)
                        return JsonResponse({"result": True, "mensaje": "Complete los datos requeridos."}, safe=False)
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": True, "mensaje": "Intentelo más tarde."}, safe=False)

        if action == 'editpreguntaevaluacion':
            try:
                with transaction.atomic():
                    idcab = int(request.POST['id'])
                    cabpregunta = EvaluacionPregunta.objects.get(pk=idcab)
                    form = EvaluacionPreguntaEditForm(request.POST)
                    if form.is_valid():
                        if not form.cleaned_data['valor'] > 0:
                            transaction.set_rollback(True)
                            return JsonResponse({"result": True, "mensaje": "Valor de la pregunta debe ser mayor a cero."}, safe=False)
                        cabpregunta.valor=form.cleaned_data['valor']
                        cabpregunta.save(request)
                        log(u'Edito Pregunta de Evaluación: %s' % cabpregunta, request, "add")
                        return JsonResponse({"result": False}, safe=False)
                    else:
                        transaction.set_rollback(True)
                        return JsonResponse({"result": True, "mensaje": "Complete los datos requeridos."}, safe=False)
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": True, "mensaje": "Intentelo más tarde."}, safe=False)

        if action == 'deletepreguntaevaluacion':
            try:
                with transaction.atomic():
                    instancia = EvaluacionPregunta.objects.get(pk=int(request.POST['id']))
                    instancia.status = False
                    instancia.save(request)
                    log(u'Elimino Pregunta de Evaluación %s' % instancia, request, "delete")
                    res_json = {"error": False}
            except Exception as ex:
                res_json = {'error': True, "message": "Error: {}".format(ex)}
            return JsonResponse(res_json, safe=False)

        if action == 'addevaluado':
            try:
                with transaction.atomic():
                    evaluacion = Evaluacion.objects.get(pk=request.POST['id'])
                    if PersonaEvaluacion.objects.filter(evaluacion=evaluacion, persona=request.POST['persona'], status=True).exists():
                        transaction.set_rollback(True)
                        return JsonResponse({'error': True, "message": 'Persona ya existe en muestra de evaluados.'}, safe=False)
                    form = PersonaEvaluacionForm(request.POST)
                    if form.is_valid():
                        instance = PersonaEvaluacion(evaluacion=evaluacion,
                                                     persona=form.cleaned_data['persona'],
                                                     numintentos=form.cleaned_data['numintentos'])
                        instance.save(request)
                        log(u'Adiciono Persona a Evaluación: %s' % instance, request, "add")
                        return JsonResponse({"result": False}, safe=False)
                    else:
                        return JsonResponse({'error': True, "form": [{k: v[0]} for k, v in form.errors.items()], "message": "Error en el formulario"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": True, "mensaje": "Intentelo más tarde."}, safe=False)

        if action == 'editevaluado':
            try:
                with transaction.atomic():
                    filtro = PersonaEvaluacion.objects.get(pk=request.POST['id'])
                    f = PersonaEvaluacionForm(request.POST)
                    if f.is_valid():
                        filtro.persona = f.cleaned_data['persona']
                        filtro.numintentos = f.cleaned_data['numintentos']
                        filtro.save(request)
                        log(u'Edito Empadronado a Periodo Electoal: %s' % filtro, request, "edit")
                        return JsonResponse({"result": False}, safe=False)
                    else:
                        return JsonResponse({'error': True, "form": [{k: v[0]} for k, v in f.errors.items()], "message": "Error en el formulario"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": True, "mensaje": "Intentelo más tarde."}, safe=False)

        if action == 'deleteevaluado':
            try:
                with transaction.atomic():
                    instancia = PersonaEvaluacion.objects.get(pk=int(request.POST['id']))
                    instancia.status = False
                    instancia.save(request)
                    log(u'Elimino Persona de Evaluación: %s' % instancia, request, "delete")
                    res_json = {"error": False}
            except Exception as ex:
                res_json = {'error': True, "message": "Error: {}".format(ex)}
            return JsonResponse(res_json, safe=False)

        return JsonResponse({"result": "bad", "mensaje": u"Solicitud Incorrecta."})
    else:
        if 'action' in request.GET:
            data['action'] = action = request.GET['action']

            if action == 'addevaluacion':
                try:
                    data['title'] = u'Adicionar Evaluación'
                    data['form'] = EvaluacionForm()
                    return render(request, "adm_evaluacion/addencuesta.html", data)
                except Exception as ex:
                    pass

            if action == 'editevaluacion':
                try:
                    data['title'] = u'Editar Evaluación'
                    data['filtro'] = filtro = Evaluacion.objects.get(pk=int(request.GET['id']))
                    data['form'] = EvaluacionForm(initial=model_to_dict(filtro))
                    return render(request, "adm_evaluacion/editencuesta.html", data)
                except Exception as ex:
                    pass

            if action == 'configuraciones':
                try:
                    data['title'] = u'Configuraciones'
                    data['bancopreguntas'] = BancoPreguntas.objects.filter(status=True).order_by('id')
                    return render(request, "adm_evaluacion/configuraciones.html", data)
                except Exception as ex:
                    pass

            if action == 'excelpreguntas':
                try:
                    data['bancopreguntas'] = bancopreguntas = BancoPreguntas.objects.filter(status=True).order_by('id')
                    __author__ = 'Unemi'

                    output = io.BytesIO()
                    workbook = xlsxwriter.Workbook(output)
                    ws = workbook.add_worksheet('Matriz_preguntas')

                    formatotitulo = workbook.add_format(
                        {'align': 'center', 'valign': 'vcenter', 'bold': 1, 'font_size': 20, 'border': 1,
                         'text_wrap': True, 'font_color': 'black', 'font_name': 'Calibri'})

                    formatosubtitulocolumna = workbook.add_format(
                        {'align': 'left', 'valign': 'vcenter', 'bold': 1, 'font_size': 14, 'border': 1,
                         'text_wrap': True, 'font_name': 'Calibri', 'font_color': 'black'})

                    formatocontenidocolumna = workbook.add_format(
                        {'align': 'left', 'valign': 'vcenter', 'font_size': 12, 'border': 1,
                         'text_wrap': True, 'font_name': 'Calibri', 'font_color': 'black'})
                    formatocontenidocolumnacorrecta = workbook.add_format(
                        {'align': 'left', 'valign': 'vcenter', 'font_size': 12, 'border': 1, 'bold': 1, 'fg_color': '#FFFF00',
                         'text_wrap': True, 'font_name': 'Calibri', 'font_color': 'black'})

                    ws.set_column(0, 0, 70)
                    ws.set_column(1, 6, 50)
                    # ####TITULOS
                    ws.merge_range('A1:M2', 'BANCO DE PREGUNTAS', formatotitulo)
                    # Pregunta
                    ws.write('A4', 'Pregunta', formatosubtitulocolumna)
                    ws.write('B4', 'Respuesta 1', formatosubtitulocolumna)
                    ws.write('C4', 'Respuesta 2', formatosubtitulocolumna)
                    ws.write('D4', 'Respuesta 3', formatosubtitulocolumna)
                    ws.write('E4', 'Respuesta 4', formatosubtitulocolumna)

                    ## contenido
                    LETTERS = ('B', 'C', 'D', 'E', 'F', 'G', 'H')
                    row = 5
                    for bp in bancopreguntas:
                        ws.write('A' + str(row), str(bp.enunciado), formatocontenidocolumna)
                        col = 0
                        for rp in bp.total_respuestas():
                            if not rp.es_correcta:
                                ws.write(str(LETTERS[col]+str(row)), str(rp.detalle), formatocontenidocolumna)
                            else:
                                ws.write(str(LETTERS[col] + str(row)), str(rp.detalle), formatocontenidocolumnacorrecta)
                            col += 1
                        row += 1
                    workbook.close()
                    output.seek(0)
                    filename = 'Matriz_preguntas_' + random.randint(1, 10000).__str__() + '.xlsx'
                    response = HttpResponse(output,
                                            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
                    response['Content-Disposition'] = 'attachment; filename=%s' % filename

                    return response
                except Exception as ex:
                    pass

            if action == 'addpregunta':
                try:
                    data['title'] = u'Adicionar Banco de Preguntas'
                    data['form'] = BancoPreguntasForm()
                    return render(request, "adm_evaluacion/addpregunta.html", data)
                except Exception as ex:
                    pass

            if action == 'editpregunta':
                try:
                    data['title'] = u'Editar Banco de Preguntas'
                    data['filtro'] = filtro = BancoPreguntas.objects.get(pk=int(request.GET['id']))
                    data['form'] = BancoPreguntasForm(initial=model_to_dict(filtro))
                    return render(request, "adm_evaluacion/editpregunta.html", data)
                except Exception as ex:
                    pass

            if action == 'preguntas':
                data['title'] = u'Preguntas'
                data['cab'] = cab = Evaluacion.objects.get(pk=request.GET['id'])
                data['titulo'] = 'Preguntas {}'.format(cab.nombre)
                data['preguntas'] = preguntas = EvaluacionPregunta.objects.filter(cab=cab, status=True).order_by('pk')
                data['valorpreguntas'] = valorpreguntas = preguntas.aggregate(total=Coalesce(Sum(F('valor'), output_field=FloatField()), 0)).get('total')
                data['puedeadicionar'] = puedeadicionar = valorpreguntas >= cab.notamax
                return render(request, 'adm_evaluacion/preguntas.html', data)

            if action == 'addpreguntaevaluacion':
                try:
                    data['id'] = id = int(request.GET['id'])
                    data['filtro'] = filtro = Evaluacion.objects.get(pk=id)
                    query = BancoPreguntas.objects.filter(status=True).order_by('pk')
                    form = EvaluacionPreguntaForm()
                    if EvaluacionPregunta.objects.filter(cab_id=id).exists():
                        query = query.exclude(pk__in=EvaluacionPregunta.objects.filter(cab_id=id, status=True).values_list('pregunta__pk',flat=True))
                    form.fields['pregunta'].queryset = query.order_by('pk')
                    data['form'] = form
                    template = get_template("adm_evaluacion/modal/formpregunta.html")
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    pass

            if action == 'editpreguntaevaluacion':
                try:
                    data['id'] = id = int(request.GET['id'])
                    data['filtro'] = filtro = EvaluacionPregunta.objects.get(pk=id)
                    form = EvaluacionPreguntaEditForm(initial=model_to_dict(filtro))
                    data['form'] = form
                    template = get_template("adm_evaluacion/modal/formpregunta.html")
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    pass

            if action == 'evaluado':
                data['title'] = u'Evaluados'
                id, search, filtros, url_vars = request.GET.get('id', ''),  request.GET.get('search', ''), Q(status=True), ''
                data['cab'] = cab = Evaluacion.objects.get(pk=id)
                if id:
                    data['id'] = int(id)
                    filtros = filtros & (Q(evaluacion_id=id))
                    url_vars += '&id={}'.format(id)
                if search:
                    data['search'] = search
                    s = search.split()
                    if len(s) == 1:
                        filtros = filtros & (Q(persona__apellido2__icontains=search) | Q(persona__cedula__icontains=search) | Q(persona__apellido1__icontains=search))
                    else:
                        filtros = filtros & (Q(persona__apellido1__icontains=s[0]) & Q(persona__apellido2__icontains=s[1]))
                    url_vars += '&search={}'.format(search)
                query = PersonaEvaluacion.objects.filter(filtros).order_by('persona__apellido1')
                data['listcount'] = query.count()
                url_vars += '&action={}'.format(action)
                data["url_vars"] = url_vars
                paging = MiPaginador(query, 25)
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
                data['lista'] = page.object_list
                return render(request, 'adm_evaluacion/evaluados.html', data)

            if action == 'addevaluado':
                try:
                    data['id'] = id = request.GET['id']
                    data['filtro'] = filtro = Evaluacion.objects.get(pk=id)
                    data['cabid'] = id
                    form = PersonaEvaluacionForm(initial={'numintentos': filtro.numintentos})
                    form.fields['persona'].queryset = Persona.objects.none()
                    data['form2'] = form
                    template = get_template("adm_evaluacion/modal/formpersonaevaluacion.html")
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    pass

            if action == 'editevaluado':
                try:
                    data['id'] = request.GET['id']
                    data['filtro'] = filtro = PersonaEvaluacion.objects.get(pk=request.GET['id'])
                    data['cabid'] = filtro.evaluacion.id
                    form = PersonaEvaluacionForm(initial=model_to_dict(filtro))
                    if filtro.persona:
                        form.fields['persona'].queryset = Persona.objects.filter(pk=filtro.persona.pk)
                    else:
                        form.fields['persona'].queryset = Persona.objects.none()
                    data['form2'] = form
                    template = get_template("adm_evaluacion/modal/formpersonaevaluacion.html")
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    pass

            if action == 'buscarpersonas':
                try:
                    id = request.GET['id']
                    q = request.GET['q'].upper().strip()
                    s = q.split(" ")
                    querybase = Persona.objects.filter(status=True)
                    if len(s) == 1:
                        per = querybase.filter((Q(nombres__icontains=q) | Q(apellido1__icontains=q) | Q(cedula__icontains=q) |  Q(apellido2__icontains=q) | Q(cedula__contains=q)), Q(status=True)).distinct()[:15]
                    elif len(s) == 2:
                        per = querybase.filter((Q(apellido1__contains=s[0]) & Q(apellido2__contains=s[1])) |
                                                       (Q(nombres__icontains=s[0]) & Q(nombres__icontains=s[1])) |
                                                       (Q(nombres__icontains=s[0]) & Q(apellido1__contains=s[1]))).filter(status=True).distinct()[:15]
                    else:
                        per = querybase.filter((Q(nombres__contains=s[0]) & Q(apellido1__contains=s[1]) & Q(apellido2__contains=s[2])) |
                                                       (Q(nombres__contains=s[0]) & Q(nombres__contains=s[1]) & Q(apellido1__contains=s[2]))).filter(status=True).distinct()[:15]
                    data = {"result": "ok", "results": [{"id": x.id, "name": "{} - {}".format(x.cedula, x.nombre_completo())} for x in per]}
                    return JsonResponse(data)
                except Exception as ex:
                    pass

            if action == 'verrespuestas':
                data['id'] = id = int(request.GET['id'])
                evaluacion = PersonaEvaluacionIntento.objects.get(pk=id)
                if evaluacion.estado == 2:
                    data['title'] = u'{}'.format(evaluacion.personaevaluada.evaluacion.nombre)
                    data['evapersona'] = evaluacion
                    data['preguntas'] = evaluacion.get_preguntas()
                    return render(request, 'adm_evaluacion/evaluado/verrespuestas.html', data)
                else:
                    messages.error(request, 'Intento aún no finaliza.'.format(evaluacion.numintento))
                    return redirect(request.path)

            if action == 'verintentos':
                data['title'] = u'Ver Intentos'
                data['id'] = id = int(request.GET['id'])
                data['persona'] = evaluacion = PersonaEvaluacion.objects.get(pk=id)
                data['listado'] = listado = PersonaEvaluacionIntento.objects.filter(status=True, personaevaluada=evaluacion, estado=2).order_by('-numintento')
                return render(request, 'adm_evaluacion/evaluado/verintentos.html', data)

        else:
            data['title'] = u'Evaluaciones'
            search, filtro, url_vars = request.GET.get('s', ''), Q(status=True), ''
            if search:
                filtro = filtro & Q(nombre__icontains=search)
                url_vars += '&s=' + search
                data['search'] = search
            listado = Evaluacion.objects.filter(filtro).order_by('-id')
            paging = MiPaginador(listado, 20)
            p = 1
            try:
                paginasesion = 1
                if 'paginador' in request.session:
                    paginasesion = int(request.session['paginador'])
                if 'page' in request.GET:
                    p = int(request.GET['page'])
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
            data["url_vars"] = url_vars
            data['listado'] = page.object_list
            data['totcount'] = listado.count()
            data['email_domain'] = EMAIL_DOMAIN
            return render(request, 'adm_evaluacion/view.html', data)