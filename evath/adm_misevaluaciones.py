# -*- coding: UTF-8 -*-
import json
import random
import sys
from datetime import datetime, timedelta

import openpyxl
import requests
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


def procesarEvaluacion(request, intento, persona):
    try:
        with transaction.atomic():
            fechaactual, fechahoraactual, horaactual = datetime.now(), datetime.now().date(), datetime.now().time()
            intento = PersonaEvaluacionIntento.objects.get(pk=intento.pk)
            intento.fechafin = fechaactual
            intento.estado = 2
            calificacion = 0
            preguntas = intento.personaevaluacionpregunta_set.filter(status=True, respondido=True   ).order_by('pk')
            for pre in preguntas:
                if pre.get_respuesta().respuesta.es_correcta:
                    pre.valor = pre.pregunta.valor
                    pre.save(request)
                    calificacion += pre.pregunta.valor
            intento.calificacion = calificacion
            intento.save(request)
            return True
    except Exception as ex:
        transaction.set_rollback(True)
        return False


@login_required(redirect_field_name='ret', login_url='/loginsga')
@secure_module
@last_access
@transaction.atomic()
def view(request):
    data = {}
    adduserdata(request, data)
    usuario = request.user
    persona = request.session['persona']
    fechaactual = datetime.now()
    fechahoraactual = datetime.now().date()
    horaactual = datetime.now().time()
    if request.method == 'POST':
        res_json = []
        action = request.POST['action']

        if action == 'realizar':
            try:
                with transaction.atomic():
                    idcab = int(encrypt(request.POST['id']))
                    evaluacion = PersonaEvaluacion.objects.get(pk=idcab)
                    password = request.POST['password']
                    if evaluacion.evaluacion.password == password:
                        if evaluacion.evaluacion.publicar:
                            if not evaluacion.permiteintento():
                                numintento = evaluacion.intentosrealizados() + 1
                                fechahoraactual = datetime.now()
                                horaterminar = (datetime.now() + timedelta(minutes=evaluacion.evaluacion.minevaluacion))
                                cabevaluacion = PersonaEvaluacionIntento(personaevaluada=evaluacion,
                                                                         numintento=numintento, estado=1,
                                                                         fechainicio=fechaactual,
                                                                         fechaexpira=horaterminar)
                                cabevaluacion.save(request)
                                eval = Evaluacion.objects.get(pk=evaluacion.evaluacion.pk)
                                preguntas = EvaluacionPregunta.objects.filter(cab=eval, status=True).order_by('?')[
                                            :eval.numpreguntas]
                                for pre in preguntas:
                                    pregunta = PersonaEvaluacionPregunta(cab=cabevaluacion, pregunta=pre)
                                    pregunta.save(request)
                                log(u'Inicio Evaluación: %s' % cabevaluacion, request, "add")
                                return JsonResponse({"result": False, "to": "{}?action=evaluacion&id={}".format(request.path, encrypt(cabevaluacion.pk))}, safe=False)
                            else:
                                transaction.set_rollback(True)
                                return JsonResponse(
                                    {"result": True, "mensaje": "Usted ya no cuenta con intentos disponibles."},
                                    safe=False)
                        else:
                            transaction.set_rollback(True)
                            return JsonResponse({"result": True, "mensaje": "Evaluación ya no esta disponible."},
                                                safe=False)
                    else:
                        transaction.set_rollback(True)
                        return JsonResponse({"result": True, "mensaje": "Contraseña Incorrecta."}, safe=False)
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": True, "mensaje": "Intentelo más tarde."}, safe=False)

        if action == 'finalizarEvaluacion':
            try:
                with transaction.atomic():
                    idcab = int(encrypt(request.POST['id']))
                    evaluacion = PersonaEvaluacionIntento.objects.get(pk=idcab)
                    if evaluacion.personaevaluacionpregunta_set.filter(status=True, respondido=False).exists():
                        transaction.set_rollback(True)
                        return JsonResponse({"result": True, "mensaje": "Debe responder todas las preguntas para finalizar."}, safe=False)
                    validador = procesarEvaluacion(request, evaluacion, persona)
                    if validador:
                        log(u'Finalizo Intento Evaluación: %s' % validador, request, "add")
                        return JsonResponse({"result": False, "to": "{}?action=verrespuestas&id={}".format(request.path, encrypt(evaluacion.pk))}, safe=False)
                    else:
                        transaction.set_rollback(True)
                        return JsonResponse({"result": True, "mensaje": "Intentelo más tarde."}, safe=False)
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": True, "mensaje": "Intentelo más tarde."}, safe=False)

        if action == 'terminarExpiracion':
            try:
                with transaction.atomic():
                    idcab = int(encrypt(request.POST['id']))
                    evaluacion = PersonaEvaluacionIntento.objects.get(pk=idcab)
                    validador = procesarEvaluacion(request, evaluacion, persona)
                    if validador:
                        log(u'Finalizo Intento Evaluación por falta de tiempo: %s' % validador, request, "add")
                        return JsonResponse({"error": False, "to": "{}?action=verrespuestas&id={}".format(request.path, encrypt(evaluacion.pk))}, safe=False)
                    else:
                        transaction.set_rollback(True)
                        return JsonResponse({"error": True, "mensaje": "Intentelo más tarde."}, safe=False)
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"error": True, "mensaje": "Intentelo más tarde."}, safe=False)

        if action == 'marcarrespuesta':
            try:
                with transaction.atomic():
                    values = json.loads(request.POST.get('data'))
                    idpregunta = int(values['pregunta'])
                    idrespuesta = int(values['respuesta'])
                    pregunta = PersonaEvaluacionPregunta.objects.get(pk=idpregunta)
                    if pregunta.cab.personaevaluada.evaluacion.publicar:
                        respuesta = BancoPreguntasRespuestas.objects.get(pk=idrespuesta)
                        if PersonaEvaluacionRespuesta.objects.filter(pregunta=pregunta, status=True).exists():
                            respregunta = PersonaEvaluacionRespuesta.objects.filter(pregunta=pregunta,
                                                                                    status=True).first()
                        else:
                            respregunta = PersonaEvaluacionRespuesta(pregunta=pregunta)
                        respregunta.respuesta = respuesta
                        respregunta.save(request)
                        pregunta.respondido = True
                        pregunta.save(request)
                        log(u'Respondio Pregunta: %s' % pregunta, request, "add")
                        response = JsonResponse({'resp': True})
                    else:
                        response = JsonResponse({'resp': False, 'msg': 'Tiempo para realizar evaluación ya finalizo.'})
                    return HttpResponse(response.content)
            except Exception as ex:
                response = JsonResponse({'resp': False, 'msg': str(ex)})
                return HttpResponse(response.content)

        return JsonResponse({"result": "bad", "mensaje": u"Solicitud Incorrecta."})
    else:
        if 'action' in request.GET:
            data['action'] = action = request.GET['action']

            if action == 'realizar':
                data['title'] = u'Iniciar Evaluación'
                data['id'] = id = int(encrypt(request.GET['id']))
                evaluacion = PersonaEvaluacion.objects.get(pk=id)
                if evaluacion.persona == persona:
                    if evaluacion.evaluacion.publicar:
                        if not evaluacion.permiteintento():
                            data['evapersona'] = evaluacion
                            data['evaluacion'] = evaluacion.evaluacion
                            data['numerointento'] = evaluacion.intentosrealizados() + 1
                            return render(request, 'adm_misevaluaciones/evaluacion.html', data)
                        else:
                            messages.error(request, 'Ya no cuenta con intentos disponibles')
                            return redirect(request.path)
                    else:
                        messages.error(request, 'Evaluación ya terminó')
                        return redirect(request.path)
                else:
                    return redirect(request.path)

            if action == 'evaluacion':
                data['id'] = id = int(encrypt(request.GET['id']))
                evaluacion = PersonaEvaluacionIntento.objects.get(pk=id)
                if evaluacion.estado == 1:
                    if evaluacion.personaevaluada.evaluacion.publicar:
                        data['title'] = u'{}'.format(evaluacion.personaevaluada.evaluacion.nombre)
                        data["date_comienzo"] = fecha_actual = datetime.now()
                        date_fin = "{} {}".format(evaluacion.fechaexpira.strftime('%Y-%m-%d'),
                                                  evaluacion.fechaexpira.strftime('%H:%M:%S'))
                        data["date_fin"] = fecha_fin = datetime.strptime(date_fin, '%Y-%m-%d %H:%M:%S')
                        data["minutos_que_faltan"] = minutos_que_faltan = (fecha_actual - fecha_fin).min
                        data["date_comienzo_str"] = fecha_actual.strftime('%Y-%m-%d %H:%M:%S')
                        data["date_fin_str"] = fecha_fin.strftime('%Y-%m-%d %H:%M:%S')
                        data['evapersona'] = evaluacion
                        data['preguntas'] = evaluacion.get_preguntas()
                        data['primerapregunta'] = evaluacion.get_preguntas().first()
                        if fechaactual > fecha_fin:
                            validador = procesarEvaluacion(request, evaluacion, persona)
                            if validador:
                                messages.error(request, 'Tiempo de evaluación ya finalizo')
                                return redirect('{}?action=verrespuestas&id={}'.format(request.path, encrypt(evaluacion.pk)))
                            else:
                                messages.error(request, 'Intentelo más tarde')
                                return redirect(request.path)
                        return render(request, 'adm_misevaluaciones/confirmacionintento.html', data)
                    else:
                        messages.error(request, 'Evaluación ya terminó')
                        return redirect(request.path)
                else:
                    messages.error(request, 'Intento #{} ya finalizo.'.format(evaluacion.numintento))
                    return redirect(request.path)

            if action == 'traerPregunta':
                try:
                    data['id'] = id = int(encrypt(request.GET['id']))
                    data['num'] = num = request.GET['num']
                    data['pregunta'] = filtro = PersonaEvaluacionPregunta.objects.get(pk=id)
                    template = get_template("adm_misevaluaciones/pregunta.html")
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    pass

            if action == 'finalizarEvaluacion':
                try:
                    data['id'] = id = int(encrypt(request.GET['id']))
                    data['filtro'] = filtro = PersonaEvaluacionIntento.objects.get(pk=id)
                    data['preguntas'] = filtro.get_preguntas()
                    template = get_template("adm_misevaluaciones/finalizar.html")
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    pass

            if action == 'verrespuestas':
                data['id'] = id = int(encrypt(request.GET['id']))
                evaluacion = PersonaEvaluacionIntento.objects.get(pk=id)
                if evaluacion.estado == 2:
                    data['title'] = u'{}'.format(evaluacion.personaevaluada.evaluacion.nombre)
                    data['evapersona'] = evaluacion
                    data['preguntas'] = evaluacion.get_preguntas()
                    return render(request, 'adm_misevaluaciones/verrespuestas.html', data)
                else:
                    messages.error(request, 'Intento aún no finaliza.'.format(evaluacion.numintento))
                    return redirect(request.path)

            if action == 'verintentos':
                data['title'] = u'Ver Intentos'
                data['id'] = id = int(encrypt(request.GET['id']))
                data['persona'] = evaluacion = PersonaEvaluacion.objects.get(pk=id)
                data['listado'] = listado = PersonaEvaluacionIntento.objects.filter(status=True, personaevaluada=evaluacion, estado=2).order_by('-numintento')
                return render(request, 'adm_misevaluaciones/verintentos.html', data)

        else:
            data['title'] = u'Mis Evaluaciones'
            search, filtro, url_vars = request.GET.get('s', ''), Q(status=True), ''
            listado = PersonaEvaluacion.objects.filter(persona=persona).filter(filtro).order_by('-evaluacion__pk')
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
            return render(request, 'adm_misevaluaciones/view.html', data)
