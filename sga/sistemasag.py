# -*- coding: UTF-8 -*-
import random
import json
import sys
from itertools import chain
import xlrd as xlrd

import xlsxwriter
from urllib.request import urlopen
import io
from django.contrib.admin.templatetags.admin_list import results
from django.db.models import Sum, Count, F
from django.template.defaulttags import ifchanged
from django.template.loader import get_template
from reportlab.lib.enums import TA_LEFT
from reportlab.lib import colors
import xlwt
from xlwt import *
from django.contrib.auth.decorators import login_required
from django.db import transaction, connection
from django.db.models.query_utils import Q
from django.http import HttpResponseRedirect, HttpResponse, JsonResponse
from django.shortcuts import render
from django.template import Context

from decorators import secure_module, last_access
from sagest.models import ExperienciaLaboral, CapInscritoIpec
from settings import ARCHIVO_TIPO_GENERAL
from sga.commonviews import adduserdata,traerNotificaciones
from sga.excelbackground import reportegraduadosfiltro, reporte_exportaencuestadosporencuesta,Reporte_EncuestaEdCom
from sga.forms import SagEncuestasFrom, PreguntasEncuestasForm, PeriodoSagForm, \
    SagPreguntaFrom, SagGrupoFrom, SagIndicadoresFrom, SagProyectosFrom, \
    SagMuestraPeriodoCarreraForm, SagInformeForm, SagActividadForm, SagImportarMuestraForm, SagPredecesorForm, \
    SagPredecesor2Form, SagMuestraForm
from sga.funciones import MiPaginador, log, generar_nombre, convertir_fecha, convertir_fecha_invertida, \
    puede_realizar_accion_afirmativo, null_to_decimal
from sga.models import Inscripcion, Graduado, Carrera, Persona, SagPeriodo, SagEncuesta, \
    SagPreguntaEncuesta, SagPregunta, SagGrupoPregunta, SagPreguntaTipo, SagEncuestaItem, SagEncuestaCarrera, \
    SagResultadoEncuesta, SagResultadoEncuestaDetalle, SagIndicador, SagProyecto, SagIndicadorEncuesta, \
    SagIndicadorProyecto, SagMuestraPeriodoCarreraDetalle, SagMuestraPeriodoCarrera, Coordinacion, Sexo, SagInformes, \
    PersonaDatosFamiliares, PersonaEstadoCivil, NivelTitulacion, Capacitacion, SagActividades, SagVisita, Matricula, \
    Archivo, SagMuestraEncuesta, Inscripcion, Notificacion
from sga.funcionesxhtml2pdf import conviert_html_to_pdf, add_titulo_reportlab, generar_pdf_reportlab, \
    add_tabla_reportlab, add_graficos_barras_reportlab
from django.db.models.functions import ExtractYear
from django.forms import model_to_dict
from datetime import datetime, timedelta

from sga.templatetags.sga_extras import encrypt, sumar_cm, sumar_ch, sumar_tm, sumar_th,\
    suma, sumar_fm, sumar_fh


@login_required(redirect_field_name='ret', login_url='/loginsga')
@secure_module
@last_access
@transaction.atomic()
def view(request):
    data = {}
    adduserdata(request, data)
    persona = request.session['persona']
    miscarreras = persona.mis_carreras()
    if request.method == 'POST':
        action = request.POST['action']

        if action == 'addencuestapreguntas':
            try:
                if request.POST['idresponder'] == 'True':
                    responder = True
                else:
                    responder = False
                actividad = SagPreguntaEncuesta(sagpregunta_id=request.POST['idpregunta'],
                                                sagencuesta_id=request.POST['idencuesta'],
                                                observacion=request.POST['idobservacion'],
                                                orden=request.POST['idorden'],
                                                grupo_id=request.POST['idsaggrupopregunta'],
                                                tipo_id=request.POST['idtipo'],
                                                responder=responder,
                                                estado=True)
                actividad.save(request)
                log(u'Adiciono nuevo encuestapregunta: %s' % actividad, request, "add")
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": "Error al guardar los datos."})

        elif action == 'additemencuesta':
            try:
                encuestaitem = SagEncuestaItem(preguntaencuesta_id=request.POST['itemsidrespuesta'],
                                               nombre=request.POST['nomobservacion'],
                                               valor=request.POST['nomvalor'],
                                               orden=request.POST['nomorden'])
                encuestaitem.save(request)
                log(u'Adiciono nuevo item de encuesta: %s' % encuestaitem, request, "add")
                # listarespuestas = SagEncuestaItem.objects.filter(preguntaencuesta=encuestaitem.preguntaencuesta, status=True).order_by('orden')
                # lista = []
                # for listarespuesta in listarespuestas:
                #     datadoc = {}
                #     datadoc['id'] = listarespuesta.id
                #     datadoc['nombre'] = listarespuesta.nombre
                #     datadoc['valor'] = listarespuesta.valor
                #     datadoc['orden'] = listarespuesta.orden
                #     lista.append(datadoc)
                # return JsonResponse({'result': 'ok', 'lista': lista})
                return JsonResponse({'result': 'ok'})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": "Error al guardar los datos."})

        elif action == 'addencuesta':
            try:
                encuesta = SagEncuesta(sagperiodo_id=request.POST['idperiodo'],
                                       nombre=request.POST['idnombre'],
                                       descripcion=request.POST['iddescripcion'],
                                       estado=request.POST['idestado'],
                                       orden=request.POST['idorden'])
                encuesta.save(request)
                log(u'Adiciono nueva encuesta: %s' % encuesta, request, "add")
                return JsonResponse({'result': 'ok'})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": "Error al guardar los datos."})

        elif action == 'deleencuesta':
            try:
                if SagEncuesta.objects.filter(pk=request.POST['id'], status=True):
                    encuesta = SagEncuesta.objects.get(pk=request.POST['id'], status=True)
                    encuesta.delete()
                    log(u'Elimino una encuesta: %s' % encuesta, request, "del")
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'editencuestapreguntas':
            try:
                # if SagPreguntaEncuesta.objects.filter(sagpregunta_id=request.POST['codigopregunta'], sagencuesta_id=request.POST['idencuesta'], status=True).exists():
                #     return JsonResponse({"result": "bad", "mensaje": "Error la pregunta ya se encuestra ingresada."})
                preguntasencuestas = SagPreguntaEncuesta.objects.get(pk=request.POST['codigoitem'], status=True)
                preguntasencuestas.orden = request.POST['codigoorden']
                preguntasencuestas.observacion = request.POST['codigoobservacion']
                preguntasencuestas.sagpregunta_id = request.POST['codigopregunta']
                preguntasencuestas.grupo_id = request.POST['codigogrupo']
                preguntasencuestas.tipo_id = request.POST['codigotipo']
                if request.POST['preguntaobligatoria'] == 'True':
                    preguntasencuestas.responder = True
                else:
                    preguntasencuestas.responder = False
                preguntasencuestas.save(request)
                log(u'modifico preguntas de encuestas: %s' % preguntasencuestas, request, "edit")
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": "Error al guardar los datos."})

        elif action == 'delpreguntarespuesta':
            try:
                if SagEncuestaItem.objects.filter(pk=request.POST['idrespuesta'], status=True):
                    respuestapreguntas = SagEncuestaItem.objects.get(pk=request.POST['idrespuesta'], status=True)
                    if respuestapreguntas.predecesora.count()==0:
                        respuestapreguntas.delete()
                    else:
                        return JsonResponse({"result": "bad", "mensaje": "Error. \nEl item que desea eliminar tiene preguntas predecesoras."})
                    log(u'Elimino respuesta de pregunta: %s' % respuestapreguntas, request, "del")
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": "Error al eliminar los datos."})

        elif action == 'delencuestapregunta':
            try:
                if SagPreguntaEncuesta.objects.filter(pk=request.POST['idepregunta'], status=True):
                    preguntaencuesta = SagPreguntaEncuesta.objects.get(pk=request.POST['idepregunta'], status=True)
                    preguntaencuesta.delete()
                    log(u'Elimino pregunta de encuesta: %s' % preguntaencuesta, request, "del")
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": "Error al eliminar los datos."})

        elif action == 'add_est_muestra':
            try:
                inscripcion_id = int(request.POST['inscripcion'])
                sagperiodo_id = int(encrypt(request.POST['sagperiodo']))
                inscrito = Inscripcion.objects.get(id=inscripcion_id)
                if not SagMuestraEncuesta.objects.filter(inscripcion_id=inscripcion_id, sagperiodo_id=sagperiodo_id, status=True):
                    sagmuestraencuesta = SagMuestraEncuesta(inscripcion_id=inscripcion_id, sagperiodo_id=sagperiodo_id)
                    sagmuestraencuesta.save()
                    log(u'Agregó un estudiante a la muestra: %s' % sagmuestraencuesta, request, "add")
                    return JsonResponse({"result": "ok"})
                else:
                    return JsonResponse({"result": "bad", "mensaje": "El inscrito %s - %s %s %s ya tiene la muestra de esta encuesta." % (inscrito.persona.cedula, inscrito.persona.nombres, inscrito.persona.apellido1, inscrito.persona.apellido2)})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": "Error al guardar los datos."})

        elif action == 'adicionarencuestacarrera':
            try:
                valor = 0
                if SagEncuestaCarrera.objects.filter(sagecuesta_id=request.POST['encuestaid'], carrera_id= request.POST['carreraid'], status=True):
                    encuesta = SagEncuestaCarrera.objects.get(sagecuesta_id=request.POST['encuestaid'], carrera_id=request.POST['carreraid'], status=True)
                    encuesta.delete()
                    log(u'Elimino una carrera de encuesta: %s' % encuesta, request, "add")
                else:
                    encuesta = SagEncuestaCarrera(sagecuesta_id=int(request.POST['encuestaid']),
                                                  carrera_id=int(request.POST['carreraid']))
                    encuesta.save(request)
                    valor = 1
                    log(u'Agrego una carrera a encuesta: %s' % encuesta, request, "add")
                return JsonResponse({"result": "ok", "valor": valor})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": "Error al eliminar los datos."})

        elif action == 'addindicadorencuesta':
            try:
                valor = 0
                if SagIndicadorEncuesta.objects.filter(indicador_id=request.POST['idindicador'], preguntaencuesta_id= request.POST['idpregunta'], status=True).exists():
                    indi = SagIndicadorEncuesta.objects.get(indicador_id=request.POST['idindicador'], preguntaencuesta_id= request.POST['idpregunta'], status=True)
                    indi.delete()
                    log(u'elimino un registro de indicador a encuesta: %s' % indi, request, "del")
                else:
                    indi = SagIndicadorEncuesta(indicador_id=request.POST['idindicador'],
                                                preguntaencuesta_id=request.POST['idpregunta'])
                    indi.save(request)
                    valor = 1
                    log(u'agrego una registro de indicador a encuesta: %s' % indi, request, "add")
                return JsonResponse({"result": "ok", "valor": valor})

            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": "Error al eliminar los datos."})

        elif action == 'addindicadorproyecto':
            try:
                valor = 0
                if SagIndicadorProyecto.objects.filter(indicador_id=request.POST['idindicador'],periodo_id= request.POST['idperiodo'], proyecto_id= request.POST['idproyecto'] , status=True):
                    proyec = SagIndicadorProyecto.objects.get(indicador_id=request.POST['idindicador'], periodo_id= request.POST['idperiodo'], proyecto_id= request.POST['idproyecto'], status=True)
                    proyec.delete()
                    log(u'elimino un registro de indicador a proyecto: %s' % proyec, request, "del")
                else:
                    proyec = SagIndicadorProyecto(indicador_id=request.POST['idindicador'],
                                                  periodo_id=request.POST['idperiodo'],
                                                  proyecto_id=request.POST['idproyecto'])
                    proyec.save(request)
                    valor = 1
                    log(u'agrego una registro de indicador a proyecto: %s' % proyec, request, "add")
                return JsonResponse({"result": "ok", "valor": valor})

            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": "Error al eliminar los datos."})

        elif action == 'editpreguntarespuesta':
            try:
                respuestapreguntas = SagEncuestaItem.objects.get(pk=request.POST['editidrespue'], status=True)
                respuestapreguntas.nombre = request.POST['resdescripcion']
                respuestapreguntas.valor = request.POST['resvalor']
                respuestapreguntas.orden = request.POST['resorden']
                respuestapreguntas.save(request)
                log(u'edito  pregunta de respuesta: %s' % respuestapreguntas, request, "edit")
                return JsonResponse({"result": "ok", "nombre": request.POST['resdescripcion'], "resvalor": request.POST['resvalor'], "resorden": request.POST['resorden'] })
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": "Error al eliminar los datos."})

        elif action == 'conpreguntarespuesta':
            try:
                respuestapreguntas = SagEncuestaItem.objects.get(pk=request.POST['idres'], status=True)
                nombre = respuestapreguntas.nombre
                return JsonResponse({"result": "ok","nombre": nombre })
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": "Error al eliminar los datos."})

        elif action == 'conpreguntaencuesta':
            try:
                preguntaencuesta = SagPreguntaEncuesta.objects.get(pk=request.POST['idepreg'], status=True)
                nombre = preguntaencuesta.sagpregunta.nombre
                return JsonResponse({"result": "ok","nombre": nombre })
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": "Error al eliminar los datos."})

        elif action == 'conpreguntarespuestaitem':
            try:
                respuestapreguntas = SagEncuestaItem.objects.get(pk=request.POST['idres'], status=True)
                codigo = respuestapreguntas.id
                nombre = respuestapreguntas.nombre
                valor = respuestapreguntas.valor
                orden = respuestapreguntas.orden
                return JsonResponse({"result": "ok", "codigo": codigo, "nombre": nombre, "valor": valor, "orden": orden })
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": "Error al eliminar los datos."})

        elif action == 'editpreguntasencuestas':
            try:
                encuesta = SagEncuesta.objects.get(pk=request.POST['id'])
                f = SagEncuestasFrom(request.POST)
                if f.is_valid():
                    encuesta.nombre = f.cleaned_data['nombre']
                    encuesta.descripcion = f.cleaned_data['descripcion']
                    encuesta.orden = f.cleaned_data['orden']
                    encuesta.estado = f.cleaned_data['estado']
                    encuesta.save(request)
                    log(u'Edito SagEncuesta: %s' % encuesta, request, "edit")
                    return JsonResponse({"result": "ok"})
                else:
                    raise NameError('Error')

            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'editmostrarpreguntaencuesta':
            try:
                encuestapreguntas = SagPreguntaEncuesta.objects.get(pk=request.POST['idencuestapreguntas'])
                return JsonResponse({"result": "ok", "idpregunta": encuestapreguntas.sagpregunta.id,
                                     "obserbacion": encuestapreguntas.observacion,
                                     "numorden": encuestapreguntas.orden,
                                     "idgrupo": encuestapreguntas.grupo.id,
                                     "idresponder": encuestapreguntas.responder,
                                     "idtipo": encuestapreguntas.tipo.id})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": "Error al guardar los datos."})

        elif action == 'editperiodosag':
            try:
                sagperiodo = SagPeriodo.objects.get(pk=request.POST['id'])
                f = PeriodoSagForm(request.POST)
                if f.is_valid():
                    sagperiodo.nombre = f.cleaned_data['nombre'].strip().upper()
                    sagperiodo.descripcion = f.cleaned_data['descripcion'].strip().upper()
                    sagperiodo.fechainicio = f.cleaned_data['fechainicio']
                    sagperiodo.fechafin = f.cleaned_data['fechafin']
                    sagperiodo.tienemuestra = f.cleaned_data['tienemuestra']
                    sagperiodo.primeravez = f.cleaned_data['primeravez']
                    sagperiodo.aplicacurso = f.cleaned_data['aplicacurso']
                    sagperiodo.estado = f.cleaned_data['estado']
                    sagperiodo.tipo_sagperiodo = f.cleaned_data['tipo']
                    sagperiodo.save(request)
                    if 'archivo' in request.FILES:
                        nfile = request.FILES['archivo']
                        nfile._name = generar_nombre("soporte_", nfile._name)
                        sagperiodo.archivo=nfile
                        sagperiodo.save(request)
                    log(u'Edito un periodo: %s' % sagperiodo, request, "edit")
                    return JsonResponse({"result": "ok"})
                else:
                    raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'addperiodo':
            try:
                f = PeriodoSagForm(request.POST)
                if f.is_valid():
                    periodo = SagPeriodo(nombre=f.cleaned_data['nombre'].strip().upper(),
                                         descripcion=f.cleaned_data['descripcion'].strip().upper(),
                                         fechainicio=f.cleaned_data['fechainicio'],
                                         fechafin=f.cleaned_data['fechafin'],
                                         archivo='',
                                         tienemuestra=f.cleaned_data['tienemuestra'],
                                         primeravez=f.cleaned_data['primeravez'],
                                         aplicacurso=f.cleaned_data['aplicacurso'],
                                         estado=f.cleaned_data['estado'],
                                         tipo_sagperiodo=f.cleaned_data['tipo'])
                    periodo.save(request)
                    if 'archivo' in request.FILES:
                        nfile = request.FILES['archivo']
                        nfile._name = generar_nombre("soporte_", nfile._name)
                        periodo.archivo=nfile
                        periodo.save(request)
                    log(u'Agrego un nuevo periodo: %s' % periodo, request, "add")
                    return JsonResponse({"result": "ok"})
                else:
                    raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'deleperiodo':
            try:
                if SagPeriodo.objects.filter(pk=request.POST['id'], status=True):
                    periodo = SagPeriodo.objects.get(pk=request.POST['id'], status=True)
                    periodo.delete()
                    log(u'Elimino un periodo: %s' % periodo, request, "del")
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'addpregunta':
            try:
                f = SagPreguntaFrom(request.POST)
                if f.is_valid():
                    pregunta = SagPregunta(nombre=f.cleaned_data['nombre'],
                                           descripcion=f.cleaned_data['descripcion'])
                    pregunta.save(request)
                    log(u'Agrego una nueva pregunta: %s' % pregunta, request, "add")
                    return JsonResponse({"result": "ok"})
                else:
                    raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'editpregunta':
            try:
                pregunta = SagPregunta.objects.get(pk=request.POST['id'])
                f = SagPreguntaFrom(request.POST)
                if f.is_valid():
                    pregunta.nombre = f.cleaned_data['nombre']
                    pregunta.descripcion = f.cleaned_data['descripcion']
                    pregunta.save(request)
                    log(u'Edito una pregunta: %s' % pregunta, request, "edit")
                    return JsonResponse({"result": "ok"})
                else:
                    raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'delepregunta':
            try:
                if SagPregunta.objects.filter(pk=request.POST['id'], status=True):
                    pregunta = SagPregunta.objects.get(pk=request.POST['id'], status=True)
                    pregunta.delete()
                    log(u'Elimino una pregunta: %s' % pregunta, request, "del")
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'addgrupo':
            try:
                f = SagGrupoFrom(request.POST)
                if f.is_valid():
                    grupo = SagGrupoPregunta(descripcion=f.cleaned_data['descripcion'],
                                             orden=f.cleaned_data['orden'],
                                             grupo=f.cleaned_data['grupo'],
                                             observacion=f.cleaned_data['observacion'],
                                             estado=f.cleaned_data['estado'],
                                             agrupado=f.cleaned_data['agrupado']
                                             )
                    grupo.save(request)
                    log(u'Agrego un Grupo: %s' % grupo, request, "add")
                    return JsonResponse({"result": "ok"})
                else:
                    raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'editgrupo':
            try:
                grupos = SagGrupoPregunta.objects.get(pk=request.POST['id'])
                f = SagGrupoFrom(request.POST)
                if f.is_valid():
                    grupos.descripcion = f.cleaned_data['descripcion']
                    grupos.orden = f.cleaned_data['orden']
                    grupos.grupo = f.cleaned_data['grupo']
                    grupos.observacion = f.cleaned_data['observacion']
                    grupos.estado = f.cleaned_data['estado']
                    grupos.agrupado = f.cleaned_data['agrupado']
                    grupos.save(request)
                    log(u'Edita un grupo: %s' % grupos, request, "edit")
                    return JsonResponse({"result": "ok"})
                else:
                    raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'delegrupo':
            try:
                if SagGrupoPregunta.objects.filter(pk=request.POST['id'], status=True):
                    grupo = SagGrupoPregunta.objects.get(pk=request.POST['id'], status=True)
                    grupo.delete()
                    log(u'Elimino un grupo: %s' % grupo, request, "del")
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'addindicador':
            try:
                f = SagIndicadoresFrom(request.POST)
                if f.is_valid():
                    indicador = SagIndicador(codigo=f.cleaned_data['codigo'],
                                             nombre=f.cleaned_data['nombre'],
                                             descripcion=f.cleaned_data['descripcion'],
                                             vigente=f.cleaned_data['vigente'],
                                             )
                    indicador.save(request)
                    log(u'Agrego un indicador: %s' % indicador, request, "add")
                    return JsonResponse({"result": "ok"})
                else:
                    raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'editindicador':
            try:
                indicador = SagIndicador.objects.get(pk=request.POST['id'])
                f = SagIndicadoresFrom(request.POST)
                if f.is_valid():
                    indicador.codigo = f.cleaned_data['codigo']
                    indicador.nombre = f.cleaned_data['nombre']
                    indicador.descripcion = f.cleaned_data['descripcion']
                    indicador.vigente = f.cleaned_data['vigente']
                    indicador.save(request)
                    log(u'Edito un indicador: %s' % indicador, request, "edit")
                    return JsonResponse({"result": "ok"})
                else:
                    raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'deleindicador':
            try:
                if SagIndicador.objects.filter(pk=request.POST['id'], status=True):
                    indicador = SagIndicador.objects.get(pk=request.POST['id'], status=True)
                    indicador.delete()
                    log(u'Elimino un indicador: %s' % indicador, request, "del")
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'addproyecto':
            try:
                f = SagProyectosFrom(request.POST)
                if f.is_valid():
                    proyecto = SagProyecto(codigo=f.cleaned_data['codigo'],
                                           nombre=f.cleaned_data['nombre'],
                                           vigente=f.cleaned_data['vigente'])
                    proyecto.save(request)
                    log(u'Agrego un proyecto: %s' % proyecto, request, "add")
                    return JsonResponse({"result": "ok"})
                else:
                    raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'editproyecto':
            try:
                proyecto = SagProyecto.objects.get(pk=request.POST['id'])
                f = SagProyectosFrom(request.POST)
                if f.is_valid():
                    proyecto.codigo = f.cleaned_data['codigo']
                    proyecto.nombre = f.cleaned_data['nombre']
                    proyecto.vigente = f.cleaned_data['vigente']
                    proyecto.save(request)
                    log(u'Edita un proyecto: %s' % proyecto, request, "edit")
                    return JsonResponse({"result": "ok"})
                else:
                    raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'deleproyecto':
            try:
                if SagProyecto.objects.filter(pk=request.POST['id'], status=True):
                    proyecto = SagProyecto.objects.get(pk=request.POST['id'], status=True)
                    proyecto.delete()
                    log(u'Elimino un proyecto: %s' % proyecto, request, "del")
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'addestadistica':
            try:
                f = SagMuestraPeriodoCarreraForm(request.POST)
                det=request.POST['listamuestras']
                idperiodo=int(request.POST['idperiodo'])
                if f.is_valid():
                    cabecera = SagMuestraPeriodoCarrera(periodo_id=idperiodo,
                                                        carrera=f.cleaned_data['carrera'])
                    cabecera.save(request)
                    if len(request.POST['listamuestras']):
                        items = request.POST['listamuestras']
                        for d in items.split(';'):
                            detalle = SagMuestraPeriodoCarreraDetalle(muestraperiodocarrera=cabecera,
                                                                      aniograduacion=int(d.split(':')[0]),
                                                                      universo=int(d.split(':')[1]),
                                                                      muestreo=int(d.split(':')[2]))
                            detalle.save(request)
                    log(u'Adiciono una nueva muestra: %s' % cabecera, request, "add")
                    return JsonResponse({"result": "ok"})
                else:
                    raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u'Error al guardar los datos'})

        elif action == 'editestadistica':
            try:
                cabecera = SagMuestraPeriodoCarrera.objects.get(pk=request.POST['id'])
                idperiodo = int(request.POST['idperiodo'])
                f = SagMuestraPeriodoCarreraForm(request.POST)
                if f.is_valid():
                    detallemanipulado = request.POST['detallemanipulado']
                    cabecera.periodo_id = idperiodo
                    cabecera.carrera = f.cleaned_data['carrera']
                    cabecera.save(request)
                    if detallemanipulado == 'SI':
                        # Si hay items a eliminar
                        if len(request.POST['listaeliminar']):
                            itemsborrar = request.POST['listaeliminar']
                            for ib in itemsborrar.split(';'):
                                anioid = ib.split(':')[0]
                                # anioid = ib[0]
                                muestradetalle = cabecera.sagmuestraperiodocarreradetalle_set.get(aniograduacion=int(anioid), status=True)
                                muestradetalle.delete()
                        # Si hay items en el detalle
                        if len(request.POST['listamuestras']):
                            items = request.POST['listamuestras']
                            for d in items.split(';'):
                                acciondetalle = d.split(':')[3]
                                # Si accion es Insert
                                if acciondetalle == "I":
                                    muestradetalle = SagMuestraPeriodoCarreraDetalle(muestraperiodocarrera=cabecera,
                                                                                     aniograduacion=int(d.split(':')[0]),
                                                                                     universo=int(d.split(':')[1]),
                                                                                     muestreo=int(d.split(':')[2]))
                                    muestradetalle.save(request)
                                else:
                                    muestradetalle = cabecera.sagmuestraperiodocarreradetalle_set.get(aniograduacion=int(d.split(':')[0]),
                                                                                                      status=True)
                                    muestradetalle.aniograduacion = d.split(':')[0]
                                    muestradetalle.universo = d.split(':')[1]
                                    muestradetalle.muestreo = d.split(':')[2]
                                    muestradetalle.save(request)
                    log(u'Actualizo un Muestra: %s' % cabecera, request, "edit")
                    return JsonResponse({"result": "ok"})
                else:
                    raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": "Error al guardar los datos"})

        elif action == 'deleteestadistica':
            try:
                muestra = SagMuestraPeriodoCarrera.objects.get(pk=request.POST['id'])
                muestra.sagmuestraperiodocarreradetalle_set.all().delete()
                muestra.delete()
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": "Error al eliminar los datos."})

        elif action == 'exportarmuestra':
            try:
                data['idperiodo'] = idperiodo = int(request.POST['idperiodo'])
                data['nombperiodo'] = nombperiodo = request.POST['nombperiodo']
                data['id'] = id = request.POST['id']
                data['totencuestados'] = totencuestados =int( request.POST['totencuestados'])
                data['totporcentaje'] = totporcentaje = int(request.POST['totporcentaje'])
                data['idcarrera'] = idcarrera =request.POST['idcarrera']
                data['muestras'] = muestra = SagMuestraPeriodoCarrera.objects.get(pk=id, periodo_id=idperiodo,
                                                                                  status=True)
                data['cantidadm'] = cantidadm = muestra.cantidad_muestra_asociados() + 1
                data['cantidad'] = cantidad = muestra.cantidad_muestra_asociados()
                data['facultad'] = facultad = muestra.saca_facultad()
                return conviert_html_to_pdf('sagadministracion/informemuestraxacarrera_pdf.html',
                                            {'pagesize': 'A4',
                                             'idperiodo': idperiodo,
                                             'nombperiodo': nombperiodo,
                                             'id': id,
                                             'idcarrera':idcarrera,
                                             'muestras': muestra,
                                             'cantidadm': cantidadm,
                                             'cantidad': cantidad,
                                             'facultad': facultad,
                                             'totencuestados': totencuestados,
                                             'totporcentaje': totporcentaje})
            except Exception as ex:
                pass

        elif action == 'generar_reporte':
            try:
                data['idp'] = request.POST['idp']
                feini = None
                fefin = None
                if 'fini' in request.POST:
                    feini = request.POST['fini']
                    fefin = request.POST['ffin']
                    fechainicio = request.POST['fini'] + ' 00:00:00'
                    fechafin = request.POST['ffin'] + ' 23:59:59.999999'
                    data['periodoeval'] = periodoeval = SagPeriodo.objects.get(pk=data['idp'])
                    cursor = connection.cursor()
                    if not 'ano' in  request.POST:
                        sql = "select c.nombre, (ca.nombre ||  CASE WHEN ca.mencion is null THEN ' CON MENCION EN ' || ca.mencion " \
                              "ELSE '' END) AS carrera, EXTRACT(YEAR FROM g.fechagraduado) as anio, " \
                              "sum(case when p.sexo_id=1 then 1 else 0 end) as mujer,  " \
                              "sum(case when p.sexo_id=2 then 1 else 0 end) as hombre " \
                              "from sga_sagresultadoencuesta r " \
                              "inner join sga_inscripcion i on r.inscripcion_id=i.id " \
                              "inner join sga_graduado g on g.inscripcion_id=i.id and g.status=true " \
                              "inner join sga_persona p on p.id=i.persona_id " \
                              "inner join sga_coordinacion c on c.id=i.coordinacion_id " \
                              "inner join sga_carrera ca on ca.id=i.carrera_id " \
                              "where c.id NOT IN(7) AND r.status AND r.sagperiodo_id=" + data['idp'] + \
                              " AND r.fecha_creacion BETWEEN '"+fechainicio+"' and '"+fechafin+"' " \
                                                                                               " group by c.nombre, carrera, anio " \
                                                                                               " order by c.nombre, carrera, anio desc"
                    else:
                        ano = request.POST['ano']
                        sql = "select c.nombre, (ca.nombre ||  CASE WHEN ca.mencion is null THEN ' CON MENCION EN ' || ca.mencion " \
                              "ELSE '' END) AS carrera, EXTRACT(YEAR FROM g.fechagraduado) as anio, " \
                              "sum(case when p.sexo_id=1 then 1 else 0 end) as mujer,  " \
                              "sum(case when p.sexo_id=2 then 1 else 0 end) as hombre " \
                              "from sga_sagresultadoencuesta r " \
                              "inner join sga_inscripcion i on r.inscripcion_id=i.id " \
                              "inner join sga_graduado g on g.inscripcion_id=i.id and g.status=true " \
                              "inner join sga_persona p on p.id=i.persona_id " \
                              "inner join sga_coordinacion c on c.id=i.coordinacion_id " \
                              "inner join sga_carrera ca on ca.id=i.carrera_id " \
                              "where c.id NOT IN(7) AND r.status AND r.sagperiodo_id=" + data['idp'] + \
                              " AND EXTRACT(YEAR FROM r.fecha_creacion)=" +ano+ " group by c.nombre, carrera, anio " \
                                                                                " order by c.nombre, carrera, anio desc"
                    cursor.execute(sql)
                    data['data'] = cursor.fetchall()
                    # connection.close()
                return conviert_html_to_pdf('sagadministracion/informe_pdf.html',
                                            {'pagesize': 'A4', 'data': data,
                                             'feini': feini,
                                             'fefin': fefin})
            except Exception as ex:
                pass
        elif action == 'generar_reporte2':
            try:
                data['idp'] = request.POST['idp']
                feini = None
                fefin = None
                if 'fini' in request.POST:
                    feini = request.POST['fini']
                    fefin = request.POST['ffin']
                    fechainicio = request.POST['fini'] + ' 00:00:00'
                    fechafin = request.POST['ffin'] + ' 23:59:59.999999'
                    data['periodoeval'] = periodoeval = SagPeriodo.objects.get(pk=data['idp'])
                    cursor = connection.cursor()
                    if not 'ano' in  request.POST:
                        sql = "select c.nombre, (ca.nombre ||  CASE WHEN ca.mencion is null THEN ' CON MENCION EN ' || ca.mencion " \
                              "ELSE '' END) AS carrera, EXTRACT(YEAR FROM g.fechagraduado) as anio, " \
                              "sum(case when p.sexo_id=1 then 1 else 0 end) as mujer,  " \
                              "sum(case when p.sexo_id=2 then 1 else 0 end) as hombre " \
                              "from sga_sagresultadoencuesta r " \
                              "inner join sga_inscripcion i on r.inscripcion_id=i.id " \
                              "inner join sga_graduado g on g.inscripcion_id=i.id and g.status=true " \
                              "inner join sga_persona p on p.id=i.persona_id " \
                              "inner join sga_coordinacion c on c.id=i.coordinacion_id " \
                              "inner join sga_carrera ca on ca.id=i.carrera_id " \
                              "where c.id not in(7) AND r.status and r.sagperiodo_id=" + data['idp'] + \
                              " AND r.fecha_creacion BETWEEN '"+fechainicio+"' and '"+fechafin+"' " \
                                                                                               " group by c.nombre, carrera, anio " \
                                                                                               " order by c.nombre, carrera, anio desc"
                    else:
                        ano = request.POST['ano']
                        sql = "select c.nombre, (ca.nombre ||  CASE WHEN ca.mencion is null THEN ' CON MENCION EN ' || ca.mencion " \
                              "ELSE '' END) AS carrera, EXTRACT(YEAR FROM g.fechagraduado) as anio, " \
                              "sum(case when p.sexo_id=1 then 1 else 0 end) as mujer,  " \
                              "sum(case when p.sexo_id=2 then 1 else 0 end) as hombre " \
                              "from sga_sagresultadoencuesta r " \
                              "inner join sga_inscripcion i on r.inscripcion_id=i.id " \
                              "inner join sga_graduado g on g.inscripcion_id=i.id and g.status=true " \
                              "inner join sga_persona p on p.id=i.persona_id " \
                              "inner join sga_coordinacion c on c.id=i.coordinacion_id " \
                              "inner join sga_carrera ca on ca.id=i.carrera_id " \
                              "where c.id not in(7) AND r.status and  r.sagperiodo_id=" + data['idp'] + \
                              " AND EXTRACT(YEAR FROM r.fecha_creacion)=" +ano+ " group by c.nombre, carrera, anio " \
                                                                                " order by c.nombre, carrera, anio desc"
                    cursor.execute(sql)
                    data['data'] = cursor.fetchall()
                    # connection.close()
                    __author__ = 'Unemi'

                    output = io.BytesIO()
                    workbook = xlsxwriter.Workbook(output)
                    ws = workbook.add_worksheet('encuestados SAG')
                    formatotitulo = workbook.add_format({'text_wrap': True,'border': 1,'bold':True,
                                                         'align': 'center', 'font_name':"Times New Roman"})
                    formatosubtitulo = workbook.add_format({'text_wrap': True, 'border': 1, 'bold': True,
                                                            'align': 'left', 'font_name': "Times New Roman"})
                    formatosubtitulo2 = workbook.add_format({'text_wrap': True, 'border': 1,
                                                            'align': 'center', 'font_name': "Times New Roman"})

                    formatoceldatitulo = workbook.add_format({'text_wrap': True,'border': 1,'bold':True,
                                                              'align': 'left', 'font_name':"Times New Roman",
                                                              'font_color':'#FFFFFF','bg_color':"#283747"})
                    formatoceldasubtitulo = workbook.add_format({'text_wrap': True,'border': 1,'bold':True,
                                                                 'align': 'center', 'font_name':"Times New Roman",
                                                                 'font_color':'#FFFFFF','bg_color':"#283747"})


                    logunemiurl = 'https://sga.unemi.edu.ec/static/images/LOGO-UNEMI-2020.png'
                    logunemi = io.BytesIO(urlopen(logunemiurl).read())

                    ws.merge_range('A1:B2', '', formatotitulo)
                    ws.insert_image('A1', logunemiurl, {'x_scale': 0.12, 'y_scale': 0.10, 'image_data': logunemi})
                    ws.merge_range('C1:I1',"Encuestados SAG - "+str(data['periodoeval'].nombre),formatotitulo)
                    ws.merge_range('C2:I2',"Fecha de Emisión de Reporte:  Desde:"+str(feini)+" Hasta: " +str(fefin),formatotitulo)
                    ws.merge_range('A5:F5',"FACULTAD / CARRERA / AÑOS",formatosubtitulo)
                    ws.merge_range('G4:H4',"SEXO",formatotitulo)
                    ws.write("G5","F",formatotitulo)
                    ws.write("H5", "M", formatotitulo)
                    ws.write("I5", "TOTAL", formatotitulo)
                    i = 6
                    val =5
                    tr =""
                    sum=0
                    sumh=0
                    sumf=0
                    for fa in data['data']:
                        if fa[0]==tr:
                            ws.merge_range("B%s:F%s" % (i, i), str(fa[1]),formatosubtitulo)
                            if sumar_cm(fa,data['data'])>=0:
                                res3 = sumar_cm(fa,data['data'])
                                ws.write_number("G%s" % (i), float(res3),formatotitulo)
                            if sumar_ch(fa,data['data'])>=0:
                                res4 = sumar_ch(fa,data['data'])
                                ws.write_number("H%s" % (i), float(res4), formatotitulo)
                            if res3+res4>=0:
                                total1 = float(res3)+float(res4)
                                ws.write_number("I%s" % (i), float(total1), formatotitulo)
                            ws.merge_range("B%s:F%s" % (i+1, i+1), str(int(fa[2])),formatosubtitulo2)
                            if fa[3]>=0:
                                ws.write_number("G%s" % (i+1), float(fa[3]), formatotitulo)
                            if fa[4]>=0:
                                ws.write_number("H%s" % (i+1), float(fa[4]), formatotitulo)

                                ws.write_number("I%s" % (i+1), float(fa[3]+fa[4]), formatotitulo)
                            i += 1

                        else:
                            ws.merge_range("A%s:F%s" % (i, i), str(fa[0]), formatoceldatitulo)
                            if sumar_fm(fa[0], data['data']) >= 0:
                                res = sumar_fm(fa[0], data['data'])
                                sumf+=res
                                ws.write_number("G%s" % (i), int(res), formatoceldasubtitulo)
                            if sumar_fh(fa[0], data['data']) >= 0:
                                res2 = sumar_fh(fa[0], data['data'])
                                sumh+=res2
                                ws.write_number("H%s" % (i), int(res2), formatoceldasubtitulo)
                            if res+res2>=0:
                                total = int(res) + int(res2)
                                sum+=total
                                ws.write_number("I%s" % (i), int(total), formatoceldasubtitulo)
                            ws.merge_range("B%s:F%s" % (i+1, i+1), str(fa[1]), formatosubtitulo)
                            if sumar_cm(fa, data['data']) >=0:
                                res3 = sumar_cm(fa, data['data'])
                                ws.write_number("G%s" % (i+1), float(res3), formatotitulo)
                            if sumar_ch(fa, data['data']) >= 0:
                                res4 = sumar_ch(fa, data['data'])
                                ws.write_number("H%s" % (i+1), float(res4), formatotitulo)
                            if res3+res4>=0:
                                total1 = float(res3) + float(res4)
                                ws.write_number("I%s" % (i+1), float(total1), formatotitulo)

                            ws.merge_range("B%s:F%s" % (i + 2, i + 2), str(int(fa[2])), formatosubtitulo2)
                            if fa[3] >= 0:
                                ws.write_number("G%s" % (i + 2), float(fa[3]), formatotitulo)
                            if fa[4] >= 0:
                                ws.write_number("H%s" % (i + 2), float(fa[4]), formatotitulo)

                                ws.write_number("I%s" % (i + 2), float(fa[3] + fa[4]), formatotitulo)
                            i += 2

                            tr =fa[0]
                        i+=1
                    ws.merge_range("A%s:F%s" % (i, i), "TOTAL", formatoceldatitulo)
                    ws.write_number("G%s" % (i), int(sumf), formatoceldasubtitulo)
                    ws.write_number("H%s" % (i), int(sumh), formatoceldasubtitulo)
                    ws.write_number("I%s" % (i), int(sum), formatoceldasubtitulo)



                    workbook.close()
                    output.seek(0)
                    filename = 'plantilla' + random.randint(1, 10000).__str__() + '.xlsx'
                    response = HttpResponse(output, content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
                    response['Content-Disposition'] = 'attachment; filename=%s' % filename

                return response
            except Exception as ex:

                pass

        elif action == 'generar_reporte_ejecucion':
            try:
                data['idp'] = idp = request.POST['idp']
                feini = None
                fefin = None
                if 'fini' in request.POST:
                    feini = request.POST['fini']
                    fefin = request.POST['ffin']
                    fechainicio = request.POST['fini'] + ' 00:00:00'
                    fechafin = request.POST['ffin'] + ' 23:59:59.999999'
                facultades = Coordinacion.objects.filter(status=True, excluir=False)
                auxiliar = Coordinacion.objects.get(pk=4, status=True, excluir=False)
                auxiliar1 = SagMuestraPeriodoCarrera.objects.get(pk=5, status=True)
                totmuestras =SagMuestraPeriodoCarreraDetalle.objects.filter(status=True,muestraperiodocarrera__periodo_id=idp).aggregate(summues=Sum('muestreo'))[
                    'summues']
                return conviert_html_to_pdf('sagadministracion/reportedejecucion_pdf.html',
                                            {'pagesize': 'A4 landscape',
                                             'data': data,
                                             'feini': feini,
                                             'fefin': fefin,
                                             'idp': idp,
                                             'facultades': facultades,
                                             'fechainicio': fechainicio,
                                             'fechafin': fechafin,
                                             'totmuestras': totmuestras,
                                             'auxiliar': auxiliar,
                                             'auxiliar1': auxiliar1
                                             })
            except Exception as ex:
                pass

        elif action == 'reseteardatos':
            try:
                y = Persona.objects.filter(inscripcion__graduado__status=True).order_by('apellido1', 'apellido2',
                                                                                        'nombres')
                for x in y:
                    x.datosactualizados = 0
                    x.save(request)
                log(u'Reseteo de actualizacion de datos: %s' % y, request, "edit")
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'addinforme':
            try:
                f = SagInformeForm(request.POST)
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
                if ext == '.pdf':
                    a = 1
                else:
                    return JsonResponse({"result": "bad", "mensaje": u"Error, solo archivos .pdf."})
                if d.size > 6291456:
                    return JsonResponse({"result": "bad", "mensaje": u"Error, archivo mayor a 6 Mb."})
                if f.is_valid():
                    newfile = None
                    if 'archivo' in request.FILES:
                        newfile = request.FILES['archivo']
                        newfile._name = generar_nombre("informe_sag", newfile._name)
                    idperiodo = request.POST['idperiodo']
                    fechainicio = convertir_fecha(request.POST['fechainicio'])
                    fechafin = convertir_fecha(request.POST['fechafin'])
                    informe = SagInformes(sagperiodo_id=idperiodo,
                                          nombre=f.cleaned_data['nombre'],
                                          archivo=newfile,
                                          estado=1,
                                          elabora=persona,
                                          fechainicio=fechainicio,
                                          fechafin=fechafin)
                    informe.save(request)
                    log(u'Agrego un Informe sag: %s %s %s' % (informe,fechainicio,fechafin ), request, "add")
                    return JsonResponse({"result": "ok"})
                else:
                    raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'editinforme':
            try:
                informe = SagInformes.objects.get(pk=request.POST['id'])
                f = SagInformeForm(request.POST)
                if 'archivo' in request.FILES:
                    d = request.FILES['archivo']
                    if d.size > 6291456:
                        return JsonResponse({"result": "bad", "mensaje": u"Error, archivo mayor a 6 Mb."})
                    else:
                        newfiles = request.FILES['archivo']
                        newfilesd = newfiles._name
                        ext = newfilesd[newfilesd.rfind("."):]
                        if ext == '.pdf':
                            a = 1
                        else:
                            return JsonResponse({"result": "bad", "mensaje": u"Error, solo archivos .pdf."})
                if f.is_valid():
                    idperiodo = request.POST['idperiodo']
                    informe.sagperiodo_id = idperiodo
                    informe.nombre = f.cleaned_data['nombre']
                    informe.fechainicio = f.cleaned_data['fechainicio']
                    informe.fechafin = f.cleaned_data['fechafin']
                    informe.save(request)
                    if 'archivo' in request.FILES:
                        newfile = request.FILES['archivo']
                        newfile._name = generar_nombre("carta_compromiso_", newfile._name)
                        informe.archivo = newfile
                        informe.save(request)
                    log(u'Edita un informe: %s' % informe, request, "edit")
                    return JsonResponse({"result": "ok"})
                else:
                    raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'deleinforme':
            try:
                if SagInformes.objects.filter(pk=request.POST['id'], status=True):
                    informe = SagInformes.objects.get(pk=request.POST['id'], status=True)
                    informe.delete()
                    log(u'Elimino un informe: %s' % informe, request, "del")
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'addactividad':
            try:
                f = SagActividadForm(request.POST)
                if f.is_valid():
                    actividad = SagActividades(nombre=f.cleaned_data['nombre'], codigo=f.cleaned_data['codigo'])
                    actividad.save(request)
                    log(u'Agrego una actividad: %s' % actividad, request, "add")
                    return JsonResponse({"result": "ok"})
                else:
                    raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'editactividad':
            try:
                actividad = SagActividades.objects.get(pk=request.POST['id'])
                f = SagActividadForm(request.POST)
                if f.is_valid():
                    actividad.nombre = f.cleaned_data['nombre']
                    actividad.vigente = f.cleaned_data['vigente']
                    actividad.codigo = f.cleaned_data['codigo'] if f.cleaned_data['codigo'] else actividad.codigo
                    actividad.save(request)
                    log(u'Edita una actividad: %s' % actividad, request, "edit")
                    return JsonResponse({"result": "ok"})
                else:
                    raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'editmuestra':
            try:
                muestra = SagMuestraEncuesta.objects.get(pk=request.POST['id'])
                f = SagMuestraForm(request.POST)
                if f.is_valid():
                    inscripcion = Inscripcion.objects.get(pk=f.cleaned_data['inscripcion'])
                    muestra.inscripcion = inscripcion
                    muestra.save(request)
                    log(u'Edita una muestra encuesta: %s' % muestra, request, "edit")
                    return JsonResponse({"result": "ok"})
                else:
                    raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'deleactividad':
            try:
                if SagActividades.objects.filter(pk=request.POST['id'], status=True):
                    actividad = SagActividades.objects.get(pk=request.POST['id'], status=True)
                    actividad.status=False
                    actividad.save(request)
                    log(u'Elimino un grupo: %s' % actividad, request, "del")
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'deletemuestra':
            try:
                if SagMuestraEncuesta.objects.filter(pk=request.POST['id'], status=True):
                    muestra = SagMuestraEncuesta.objects.get(pk=request.POST['id'], status=True)
                    muestra.status=False
                    muestra.save(request)
                    log(u'Elimino una muestra encuesta: %s' % muestra, request, "del")
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'informeservicios':
            mensaje = "Problemas al generar el informe de servicios."
            try:
                fini = convertir_fecha_invertida(request.POST['fini'])
                ffin = convertir_fecha_invertida(request.POST['ffin'])
                fecha_inicio_corte = convertir_fecha_invertida(request.POST['fecha_inicio_corte'])
                fecha_fin_corte = convertir_fecha_invertida(request.POST['fecha_fin_corte'])
                graduados = Graduado.objects.filter(Q(status=True) & Q(fechagraduado__gte=fecha_inicio_corte) & Q(fechagraduado__lte=fecha_fin_corte))
                nograduados = graduados.values_list('id').count()
                personagraduados = graduados.values_list('inscripcion__persona__id', flat=True)
                inscritocurso = CapInscritoIpec.objects.filter(Q(status=True) & Q( participante__id__in=personagraduados) &
                                                               Q(fecha_creacion__gte=fini)& Q(fecha_creacion__lte=ffin))
                noinscritocurso = inscritocurso.values_list('id').count()
                maestrias = Matricula.objects.filter(Q(status=True) & Q(inscripcion__coordinacion__id=7)& Q(fecha__gte=fini) &
                                                     Q(fecha__lte=ffin)& Q(inscripcion__persona__id__in=personagraduados)).order_by('fecha')
                nomaestrias = maestrias.values_list('id').count()
                totalgraduados=noinscritocurso+nomaestrias
                porcentaje = (totalgraduados*100)/nograduados

                return conviert_html_to_pdf('sagadministracion/informeservicios.html',
                                            {'pagesize': 'A4',
                                             'maestrias': maestrias,
                                             'persona': persona,
                                             'inscritocurso':inscritocurso,
                                             'fechainicio':fini,'fechafin':ffin, 'fecha_inicio_corte':fecha_inicio_corte,
                                             'fecha_fin_corte':fecha_fin_corte, 'nograduado':nograduados,
                                             'porcentaje':porcentaje,'totalgraduados':totalgraduados
                                             })
            except Exception as ex:
                return HttpResponseRedirect("/sistemasag?info=%s" % mensaje)

        elif action == 'importarmuestra':
            try:
                form = SagImportarMuestraForm(request.POST, request.FILES)
                if form.is_valid():
                    nfile = request.FILES['archivo']
                    nfile._name = generar_nombre("importacion_", nfile._name)
                    archivo = Archivo(nombre='IMPORTACION MUESTRAS SAG',
                                      fecha=datetime.now().date(),
                                      archivo=nfile,
                                      tipo_id=ARCHIVO_TIPO_GENERAL)
                    archivo.save(request)
                    sagperiodo = SagPeriodo.objects.get(pk=int(encrypt(request.POST['id'])))
                    workbook = xlrd.open_workbook(archivo.archivo.file.name)
                    sheet = workbook.sheet_by_index(0)
                    linea = 1
                    cedulas = ''
                    for rowx in range(sheet.nrows):
                        puntosalva = transaction.savepoint()
                        try:
                            if linea > 1:
                                cols = sheet.row_values(rowx)
                                #se verifica si el numero de cedula tiene inscripcion en graduados, y se escoge la ultima inscripcion
                                if cols[0] != None and str(cols[0]) != '':
                                    graduado = Graduado.objects.filter(status=True, inscripcion__persona__cedula=str(cols[0])).order_by('-inscripcion')
                                    if graduado:
                                        idinscripcion = graduado[0].inscripcion.id
                                        if not SagMuestraEncuesta.objects.filter(inscripcion_id=idinscripcion, sagperiodo=sagperiodo).exists():
                                            inscripcion = Inscripcion.objects.get(id=idinscripcion)
                                            muestra = SagMuestraEncuesta(inscripcion=inscripcion, sagperiodo=sagperiodo)
                                            muestra.save(request)
                                        transaction.savepoint_commit(puntosalva)
                                    else:
                                        cedulas = cedulas + str(cols[0]) + ", "
                            linea += 1
                        except Exception as ex:
                            transaction.savepoint_rollback(puntosalva)
                            return JsonResponse({"result": "bad", "mensaje": u"Error al ingresar la linea: %s" % linea})
                    if cedulas != '':
                        transaction.savepoint_rollback(puntosalva)
                        return JsonResponse({"result": "bad", "mensaje": u"Los siguientes número de cedula no estan graduados, eliminelos del archivo de excel o ingreselos en graduados: %s" % cedulas})
                    log(u'Importo muestra-periodo sag: %s' % sagperiodo, request, "add")
                    return JsonResponse({"result": "ok"})
                else:
                    raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'informeencuestas':
            mensaje = "Problemas al generar el informe."
            try:
                fini = convertir_fecha_invertida(request.POST['fini'])
                ffin = convertir_fecha_invertida(request.POST['ffin'])
                fecha_inicio_corte = convertir_fecha_invertida(request.POST['fecha_inicio_corte'])
                fecha_fin_corte = convertir_fecha_invertida(request.POST['fecha_fin_corte'])
                graduados = Graduado.objects.filter(Q(status=True) & Q(fechagraduado__gte=fecha_inicio_corte) & Q(fechagraduado__lte=fecha_fin_corte))
                nograduados = graduados.values_list('id').count()
                personagraduados = graduados.values_list('inscripcion__persona__id', flat=True)
                inscritocurso = CapInscritoIpec.objects.filter(Q(status=True) & Q( participante__id__in=personagraduados) &
                                                               Q(fecha_creacion__gte=fini)& Q(fecha_creacion__lte=ffin))
                noinscritocurso = inscritocurso.values_list('id').count()
                maestrias = Matricula.objects.filter(Q(status=True) & Q(inscripcion__coordinacion__id=7)& Q(fecha__gte=fini) &
                                                     Q(fecha__lte=ffin)& Q(inscripcion__persona__id__in=personagraduados)).order_by('fecha')
                nomaestrias = maestrias.values_list('id').count()
                totalgraduados=noinscritocurso+nomaestrias
                porcentaje = (totalgraduados*100)/nograduados

                return conviert_html_to_pdf('sagadministracion/informeservicios.html',
                                            {'pagesize': 'A4',
                                             'maestrias': maestrias,
                                             'persona': persona,
                                             'inscritocurso':inscritocurso,
                                             'fechainicio':fini,'fechafin':ffin, 'fecha_inicio_corte':fecha_inicio_corte,
                                             'fecha_fin_corte':fecha_fin_corte, 'nograduado':nograduados,
                                             'porcentaje':porcentaje,'totalgraduados':totalgraduados
                                             })
            except Exception as ex:
                return HttpResponseRedirect("/sistemasag?info=%s" % mensaje)

        elif action == 'addpredecesora':
            try:
                predecesoras = json.loads(request.POST['lista_items1'])

                # f = SagPredecesorForm(request.POST)
                f = SagPredecesor2Form(request.POST)
                if f.is_valid():
                    item = SagEncuestaItem.objects.get(id=request.POST['id'])

                    # if not f.cleaned_data['predecesora']:
                    #     item.tienepredecesora = False
                    # else:
                    #     item.tienepredecesora=True
                    # item.save(request)
                    # item.predecesora = f.cleaned_data['predecesora']



                    if predecesoras:
                        item.tienepredecesora = True
                    else:
                        item.tienepredecesora = False
                    item.save(request)

                    item.predecesora.clear()

                    for prede in predecesoras:
                        idpreg= int(prede['id'])
                        preguntapredecesora = SagPregunta.objects.get(pk=idpreg)
                        item.predecesora.add(preguntapredecesora)

                    log(u'agrego predecesoraa item: %s' % item, request, "add")
                    return JsonResponse({"result": "ok"})
                else:
                    raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'reportegrafica':
            try:
                periodo = SagPeriodo.objects.get(pk=int(request.POST['idperiodo']))
                respuestascabecera = SagResultadoEncuesta.objects.filter(status=True, inscripcion__graduado__status=True,sagperiodo=periodo)
                grupo = None
                encuesta = None
                carrera = None
                facultad = None
                if 'facultad' in request.POST and request.POST['facultad'] != "":
                    if int(request.POST['facultad']) >0:
                        facultad = Coordinacion.objects.get(id=int(request.POST['facultad']))
                        respuestascabecera = respuestascabecera.filter(inscripcion__carrera__coordinacion=facultad)
                if 'carrera' in request.POST and request.POST['carrera'] != "":
                    if int(request.POST['carrera']) > 0:
                        carrera = Carrera.objects.get(id=int(request.POST['carrera']) )
                        respuestascabecera = respuestascabecera.filter(inscripcion__carrera=carrera)
                id_respuestascabecera = respuestascabecera.values_list('id', flat=True)
                respuestas = SagResultadoEncuestaDetalle.objects.filter(status=True,
                                                                        preguntaencuesta__status=True,
                                                                        valor__gte=0,
                                                                        sagresultadoencuesta__id__in=id_respuestascabecera
                                                                        ).exclude(preguntaencuesta__tipo__id__in=[1, 5]).extra({'valor': "valor::INTEGER"})
                if 'encuesta' in request.POST and request.POST['encuesta'] != "":
                    if int(request.POST['encuesta']) > 0:
                        encuesta = SagEncuesta.objects.get(id=int(request.POST['encuesta']))
                        respuestas = respuestas.filter(preguntaencuesta__sagencuesta=encuesta)
                if 'grupo' in request.POST and request.POST['grupo'] != "":
                    if int(request.POST['grupo']) > 0:
                        grupo = SagGrupoPregunta.objects.get(id=int(request.POST['grupo']))
                        respuestas = respuestas.filter(preguntaencuesta__grupo=grupo)
                totalencuestados = respuestascabecera.values_list('id').count()
                add_titulo_reportlab(descripcion=" VICERRECTORADO DE VINCULACIÓN", tamano=12, espacios=19)
                # add_titulo_reportlab(descripcion=" GESTIÓN ACADÉMICA", tamano=12, espacios=19)
                add_titulo_reportlab(descripcion=" SEGUIMIENTO A GRADUADOS", tamano=12, espacios=19)
                add_titulo_reportlab(descripcion=str(periodo.nombre), tamano=12, espacios=19, alineacion=TA_LEFT)
                add_titulo_reportlab(descripcion=str(periodo.descripcion), tamano=12, espacios=19, alineacion=TA_LEFT)
                if facultad or carrera:
                    add_titulo_reportlab(descripcion=str(facultad.nombre) if facultad else '', tamano=12, espacios=19, alineacion=TA_LEFT)
                    add_titulo_reportlab(descripcion=str(carrera) if carrera else '', tamano=12, espacios=19, alineacion=TA_LEFT)
                if encuesta or grupo:
                    add_titulo_reportlab(descripcion=str(encuesta.nombre) if encuesta else '', tamano=12, espacios=19, alineacion=TA_LEFT)
                    add_titulo_reportlab(descripcion=str(grupo) if grupo else '', tamano=12, espacios=19, alineacion=TA_LEFT)
                add_titulo_reportlab(descripcion=str('Total de encuestados: %s' % totalencuestados) , tamano=12, espacios=19, alineacion=TA_LEFT)
                add_titulo_reportlab(descripcion=
                                     "Con base a las encuestas realizadas durante el "
                                     +periodo.nombre+
                                     " descritos se detalla la información del análisis estadístico, "
                                     "que comprende todas las preguntas inmersas dentro de la encuesta de seguimiento a graduados"
                                     + (" por " +str(carrera) if carrera else ''), tamano=12, espacios=19, alineacion=TA_LEFT,tipoletra='Helvetica')

                add_titulo_reportlab(descripcion= "Análisis Individual", tamano=12, espacios=19,alineacion=TA_LEFT, tipoletra='Helvetica')
                lista_grupos = []
                for resp in respuestas.values_list('preguntaencuesta__id', flat=True).order_by('preguntaencuesta__orden').distinct():
                    preguntaencuesta = SagPreguntaEncuesta.objects.get(id=resp)

                    if not preguntaencuesta.grupo.id in lista_grupos:
                        add_titulo_reportlab(descripcion=str(preguntaencuesta.grupo.descripcion), tamano=12,espacios=19, alineacion=TA_LEFT)
                        lista_grupos.append(preguntaencuesta.grupo.id)
                    if preguntaencuesta.tipo.id in [2, 3, 4, 6, 8]:
                        preguntaencuesta = SagPreguntaEncuesta.objects.get(id=resp)

                        add_titulo_reportlab(descripcion=str(preguntaencuesta.orden) +".-"+ preguntaencuesta.sagpregunta.nombre, tamano=12, espacios=19, alineacion=TA_LEFT, tipoletra='Helvetica')
                        detalle = []
                        datanombres = []
                        datavalor = []
                        if preguntaencuesta.tipo.id == 2:
                            respuestasportipo = respuestas.filter(preguntaencuesta__tipo__id=2, preguntaencuesta=preguntaencuesta)
                            acumulado = 0
                            for item in preguntaencuesta.listado_respuesta():
                                totalporopcion = respuestasportipo.filter(valor=item.id).count()
                                porcentaje = null_to_decimal(((totalporopcion * 100) / float(respuestasportipo.count())), 2)
                                datavalor.append(porcentaje)
                                datanombres.append(str(item.nombre))
                                acumulado += porcentaje
                                detalle.append([item.nombre, str(totalporopcion), str(porcentaje)+' %', str(null_to_decimal(acumulado,2))+' %'])
                            listaveridica = []
                            listaveridica.append(datavalor)
                            add_tabla_reportlab(encabezado=[('Respuesta', 'Frecuencia', 'Porcentaje ', 'Porcentaje Acumulado')],detalles=detalle, anchocol=[250, 100, 70, 70], cabecera_left_center=[False, True, True, True], detalle_left_center=[False, True, True, True])
                            titulo = str(preguntaencuesta.orden) +".-"+ preguntaencuesta.sagpregunta.nombre.__str__() + " total(" + str(respuestasportipo.count()) + ")"
                            add_graficos_barras_reportlab(datavalor=listaveridica,
                                                          datanombres=datanombres,
                                                          decimal=True,
                                                          anchografico=500, altografico=125, tamanoletra=6, posiciongrafico_x=25, posiciongrafico_y=30,
                                                          titulo='', tamanotitulo=8, ubicaciontitulo_x=225, ubicaciontitulo_y=17,colores=[colors.HexColor("#d6e0f5")],
                                                          posicionleyenda_x=430, mostrarleyenda=False, barra_vertical_horizontal=True, presentar_nombre_o_numero=True)
                        elif preguntaencuesta.tipo.id==4:
                            respuestasportipo = respuestas.filter(preguntaencuesta__tipo__id=4, preguntaencuesta=preguntaencuesta)
                            acumulado = 0
                            for item in preguntaencuesta.listado_respuesta():
                                totalporopcion = respuestasportipo.filter(valor=item.id).count()
                                porcentaje = null_to_decimal((( totalporopcion * 100) / float(respuestasportipo.count())), 2)
                                datavalor.append(porcentaje)
                                datanombres.append(str(item.nombre))
                                acumulado += porcentaje
                                detalle.append([item.nombre, str(totalporopcion), str(porcentaje)+' %', str(null_to_decimal(acumulado,2))+' %'])
                            listaveridica = []
                            listaveridica.append(datavalor)
                            add_tabla_reportlab(encabezado=[('Respuesta', 'Frecuencia', 'Porcentaje ', 'Porcentaje Acumulado')],detalles=detalle, anchocol=[250, 100, 70, 70], cabecera_left_center=[False, True, True, True], detalle_left_center=[False, True, True, True])
                            titulo = str(preguntaencuesta.orden) +".-"+ preguntaencuesta.sagpregunta.nombre.__str__() + " total(" + str( totalencuestados) + ")"
                            add_graficos_barras_reportlab(datavalor=listaveridica,
                                                          datanombres=datanombres,
                                                          decimal=True,
                                                          anchografico=500, altografico=125, tamanoletra=6,
                                                          posiciongrafico_x=25, posiciongrafico_y=30,
                                                          titulo='', tamanotitulo=8,
                                                          ubicaciontitulo_x=225, ubicaciontitulo_y=17,
                                                          posicionleyenda_x=430, mostrarleyenda=False,
                                                          barra_vertical_horizontal=True, presentar_nombre_o_numero=True)
                        elif preguntaencuesta.tipo.id == 3 or preguntaencuesta.tipo.id == 8:
                            opciones = [1, 2, 3, 4, 5, 6, 7]
                            respuestasportipo = respuestas.filter(preguntaencuesta__tipo__id__in=[3, 8], preguntaencuesta=preguntaencuesta)
                            acumulado = 0
                            for item in opciones:
                                totalporopcion = respuestasportipo.filter(valor=item).count()
                                porcentaje = null_to_decimal(((totalporopcion * 100) / float(respuestasportipo.count())), 2)
                                datavalor.append(porcentaje)
                                datanombres.append(str(item))
                                acumulado += porcentaje
                                detalle.append([item, str(totalporopcion), str(porcentaje) + ' %', str(null_to_decimal(acumulado,2)) + ' %'])
                            listaveridica = []
                            listaveridica.append(datavalor)
                            add_tabla_reportlab(encabezado=[('Respuesta', 'Frecuencia', 'Porcentaje ', 'Porcentaje Acumulado')], detalles=detalle,
                                                anchocol=[250, 100, 70, 70], cabecera_left_center=[False, True, True, True],
                                                detalle_left_center=[False, True, True, True])
                            titulo = str(preguntaencuesta.orden) +".-"+ preguntaencuesta.sagpregunta.nombre.__str__() + " total(" + str(respuestasportipo.count()) + ")"
                            add_graficos_barras_reportlab(datavalor=listaveridica,
                                                          datanombres=datanombres,
                                                          decimal=True,
                                                          anchografico=500, altografico=125, tamanoletra=6,
                                                          posiciongrafico_x=25, posiciongrafico_y=30,
                                                          titulo='',
                                                          tamanotitulo=8,
                                                          ubicaciontitulo_x=225, ubicaciontitulo_y=17,colores=[colors.HexColor("#d6e0f5")],
                                                          posicionleyenda_x=430, mostrarleyenda=False,
                                                          barra_vertical_horizontal=True, presentar_nombre_o_numero=True)
                        elif preguntaencuesta.tipo.id == 6:
                            listaopciones = ['0','1-3','4-6','7-10','>=10']
                            i=0
                            # for item in respuestas.values_list('valor', flat=True).distinct():
                            respuestasportipo1 = respuestas.filter(preguntaencuesta__tipo__id=6, preguntaencuesta=preguntaencuesta)
                            # respuestasportipo = list(map(int,respuestasportipo1))
                            acumulado = 0
                            for item in listaopciones:
                                i=i+1
                                totalporopcion = 0
                                # if i == 1:
                                #     totalporopcion = respuestasportipo.count(0)
                                # elif i == 2:
                                #     totalporopcion = respuestasportipo.count(1) + respuestasportipo.count(2) + respuestasportipo.count(3)
                                # elif i == 3:
                                #     totalporopcion = respuestasportipo.count(4) + respuestasportipo.count(5) + respuestasportipo.count(6)
                                # elif i == 4:
                                #     totalporopcion = respuestasportipo.count(7) + respuestasportipo.count(8) + respuestasportipo.count(9)
                                # elif i == 5:
                                #     totalporopcion = respuestasportipo.count(10) + respuestasportipo.count(3) + respuestasportipo.count(4)

                                if i == 1:
                                    totalporopcion = respuestasportipo1.filter(valor=0).count()
                                elif i == 2:
                                    totalporopcion = respuestasportipo1.filter(valor__in=[1,2,3]).count()
                                elif i == 3:
                                    totalporopcion = respuestasportipo1.filter(valor__in=[4,5,6]).count()
                                elif i == 4:
                                    totalporopcion = respuestasportipo1.filter(valor__in=[7,8,9]).count()
                                elif i == 5:
                                    totalporopcion = respuestasportipo1.exclude(valor__in=[0,1,2,3,4,5,6,7,8,9]).count()
                                porcentaje = null_to_decimal(((totalporopcion * 100) / float(respuestasportipo1.count())), 2)
                                datavalor.append(porcentaje)
                                datanombres.append(str(item))
                                acumulado += porcentaje
                                detalle.append([item, str(totalporopcion), str(porcentaje)+' %', str(null_to_decimal(acumulado,2))+' %'])
                            listaveridica = []
                            listaveridica.append(datavalor)
                            add_tabla_reportlab(encabezado=[('Respuesta', 'Frecuencia', 'Porcentaje ', 'Porcentaje Acumulado')],detalles=detalle, anchocol=[250, 100, 70, 70], cabecera_left_center=[False, True, True, True], detalle_left_center=[False, True, True, True])
                            titulo = str(preguntaencuesta.orden) +".-"+ preguntaencuesta.sagpregunta.nombre.__str__() +" total("+ str(respuestasportipo1.count())+")"
                            add_graficos_barras_reportlab(datavalor=listaveridica,
                                                          datanombres=datanombres,
                                                          decimal=True,
                                                          anchografico=500, altografico=125, tamanoletra=6,
                                                          posiciongrafico_x=25, posiciongrafico_y=30,
                                                          titulo=titulo,
                                                          tamanotitulo=8,
                                                          ubicaciontitulo_x=225, ubicaciontitulo_y=17,colores=[colors.HexColor("#d6e0f5")],
                                                          posicionleyenda_x=430, mostrarleyenda=False,
                                                          barra_vertical_horizontal=True, presentar_nombre_o_numero=True)
                        add_titulo_reportlab(descripcion='<br/><br/><br/>', tamano=10, espacios=19, alineacion=TA_LEFT)
                        # add_titulo_reportlab(descripcion="Descripción", tamano=12, espacios=19,alineacion=TA_LEFT)
                        # espaciodigitar = []
                        # espaciodigitar.append([''])
                        # add_tabla_reportlab(
                        #     encabezado=espaciodigitar,
                        #     detalles=[],
                        #     anchocol=[500], cabecera_left_center=[False],
                        #     detalle_left_center=[False],anchofila=100)

                add_titulo_reportlab(descripcion="FIRMAS ", tamano=12, espacios=19, alineacion=TA_LEFT)
                detallefirmas=[]
                detallefirmas.append(["ELABORADO POR: <br/> Jessica Guim Espinoza <br/> ANALISTA DE VINCULACION 1", "                ", "                "])
                # detallefirmas.append(["ELABORADO POR: <br/> %s <br/> ANALISTA DE VINCULACION 1" % (persona.nombre_completo_inverso()), "                ", "                "])
                detallefirmas.append(["REVISADO Y APROBADO POR: <br/> Jaime Andocilla Cabrera <br/>   DIRECCIÓN DE VINCULACIÓN", "                ", "                "])
                # detallefirmas.append(["APROBADO POR: ", "Richard Ramírez Anormaliza \n Vicerrector Académico y de Investigación", "                "])
                add_tabla_reportlab(encabezado=[('ROL/CARGO','FECHA/HORA','FIRMA')],
                                    detalles=detallefirmas,
                                    anchocol=[150, 150, 150], cabecera_left_center=[False, True, True],
                                    detalle_left_center=[False, True, True])
                add_titulo_reportlab(descripcion='<br/><br/><br/> FECHA: ' + str(datetime.now().date()), tamano=10, espacios=19, alineacion=TA_LEFT)
                return generar_pdf_reportlab(topmargin=62)
            except Exception as ex:
                return HttpResponseRedirect("/sistemasag?action=listareportes&idperiodo=%s&info=%s" % (periodo.id, 'Error al generar reporte.'))

        elif action == 'buscarcarrera':
            try:
                listacarreras = []
                idcor = int(request.POST['id'])
                idper = int(request.POST['idper'])
                if idcor > 0:
                    coordinacion = Coordinacion.objects.get(id=idcor)
                    carreras = Carrera.objects.filter(coordinacion=coordinacion, status=True)
                    listadoencuesta = SagEncuestaCarrera.objects.values_list('sagecuesta_id','sagecuesta__nombre').filter(status=True, carrera__coordinacion=coordinacion, sagecuesta__sagperiodo_id=idper).distinct()
                    listaencuesta = []
                    for x in listadoencuesta:
                        listaencuesta.append([x[0], x[1]])
                else:
                    carreras = Carrera.objects.filter(status=True)
                for carrera in carreras:
                    listacarreras.append([carrera.id, carrera.nombre_completo().__str__()])
                return JsonResponse({'result': 'ok','lista': listacarreras,'listaencuesta': listaencuesta})
            except Exception as ex:
                return JsonResponse({"result": "bad", 'mensaje': u'Error al obtener los datos.'})

        elif action == 'buscarencuesta':
            try:
                listacarreras = []
                idcar = int(request.POST['id'])
                idper = int(request.POST['idper'])
                if idcar > 0:
                    listadoencuesta = SagEncuestaCarrera.objects.values_list('sagecuesta_id','sagecuesta__nombre').filter(status=True, carrera_id=idcar, sagecuesta__sagperiodo_id=idper).distinct()
                    listaencuesta = []
                    for x in listadoencuesta:
                        listaencuesta.append([x[0], x[1]])
                else:
                    carreras = Carrera.objects.filter(status=True)
                return JsonResponse({'result': 'ok','listaencuesta': listaencuesta})
            except Exception as ex:
                return JsonResponse({"result": "bad", 'mensaje': u'Error al obtener los datos.'})

        elif action == 'buscargrupo':
            try:
                listagrupos = []
                idencuesta = int(request.POST['id'])
                if idencuesta > 0:
                    encuesta =  SagEncuesta.objects.get(id=idencuesta)
                    grupid= SagPreguntaEncuesta.objects.values_list('grupo', flat=True).filter(status=True, sagencuesta=encuesta)
                    grupos = SagGrupoPregunta.objects.filter(status=True, id__in=grupid).order_by('orden')
                else:
                    grupos = SagGrupoPregunta.objects.filter(status=True).order_by('orden')
                for grupo in grupos:
                    listagrupos.append([grupo.id, grupo.descripcion.__str__()])
                return JsonResponse({'result': 'ok','lista': listagrupos})
            except Exception as ex:
                return JsonResponse({"result": "bad", 'mensaje': u'Error al obtener los datos.'})

        elif action == 'exportarinscritoseducacioncontinua':
            ide = request.POST.getlist('ide[]')
            idf = int(request.POST['idf'])
            idanio = request.POST['idanio']
            anio = int(idanio) if idanio else datetime.now().year
            try:
                notifi = Notificacion(cuerpo='Generación de reporte de excel en progreso',
                                      titulo='Reporte de inscritos a un curso o diplomado',
                                      destinatario=persona,
                                      url='',
                                      prioridad=1, app_label='SGA',
                                      fecha_hora_visible=datetime.now() + timedelta(days=1), tipo=2,
                                      en_proceso=True)
                notifi.save(request)
                Reporte_EncuestaEdCom(request=request, notiid=notifi.id,encuesta=ide,tiporeporte=idf,anio=anio).start()
                return JsonResponse({"result": True,"mensaje": f"El reporte de inscritos a un curso o diplomado está en proceso. Por favor, verifique el apartado de notificaciones después de unos minutos.","btn_notificaciones": traerNotificaciones(request, data, persona)})
            except Exception as ex:
                pass

        if action == 'deleteencuestado':
            try:
                filtro = SagResultadoEncuesta.objects.get(id=int(encrypt(request.POST['id'])))
                filtro.status = False
                filtro.save(request)
                log(u'Eliminó encuesta: %s' % filtro, request, "delete")
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        return JsonResponse({"result": "bad", "mensaje": u"Solicitud Incorrecta."})
    else:
        if 'action' in request.GET:
            action = request.GET['action']
            if action == 'graficas':
                try:
                    data['title'] = u'Graficas por pregunta'
                    data['nombperiodo'] = request.GET['nombperiodo']
                    # data['idencuesta']=idencuesta = request.GET['idencuesta']
                    listacarreras=[]
                    data['listadocoordinaciones'] = Coordinacion.objects.filter(status=True, alias__icontains='FA')
                    data['idperiodo'] =idperiodo= request.GET['idperiodo']
                    data['carreras'] =carreras=Carrera.objects.filter(status=True,coordinacion__excluir=False)
                    # carreras=SagResultadoEncuesta.objects.filter(status=True,sagperiodo=idperiodo,
                    #                                                       inscripcion__carrera__coordinacion__excluir=False,
                    #                                                       inscripcion__carrera__status=True)
                    # i=0
                    # for x in carreras:
                    #     a = x.inscripcion.carrera.nombre_completo()
                    #     if i == 0:
                    #         listacarreras.append(a)
                    #         i += 1
                    #     elif a not in listacarreras:
                    #         listacarreras.append([x.inscripcion.carrera.id, a])
                    # data['carreras'] = listacarreras
                    data['encuestas'] = SagEncuesta.objects.filter(status=True,sagperiodo=idperiodo)
                    data['preguntas'] =a= SagPreguntaEncuesta.objects.filter(status=True,
                                                                             sagencuesta__sagperiodo__id=idperiodo,
                                                                             sagpregunta__status=True).exclude(tipo__in=[1,5]).order_by("orden")
                    # listagrad = Graduado.objects.filter(inscripcion__carrera__in=miscarreras)
                    # listanio = []
                    # i = 0
                    # for x in listagrad:
                    #     a = x.fechagraduado.year
                    #     if i == 0:
                    #         listanio.append(a)
                    #         i += 1
                    #     else:
                    #         if a not in listanio:
                    #             listanio.append(a)
                    # listanio.sort()
                    # data['anios'] = listanio
                    data['anios'] = Graduado.objects.filter(status=True, inscripcion__carrera__in=miscarreras, fechagraduado__isnull=False).annotate(Year=ExtractYear('fechagraduado')).values_list('Year', flat=True).order_by('Year').distinct()
                    return render(request, "sagadministracion/graficas.html", data)
                except Exception as ex:
                    pass

            elif action == 'listacombos':
                try:
                    if 'opc' in request.GET:
                        data['opc'] = opc = request.GET['opc']
                        listanio=[]
                        if opc == '1':
                            data['idperiodo'] = idp = request.GET['idperiodo']
                            data['idcar'] = idcar= request.GET['idcar']
                            carrera = SagEncuestaCarrera.objects.filter(status=True,carrera=idcar,sagecuesta__sagperiodo=idp)
                            lista = []
                            for x in carrera:
                                lista.append([x.sagecuesta.id, x.sagecuesta.nombre])
                            # listagrad = Graduado.objects.filter(inscripcion__carrera__id=idcar)
                            # listanio = []
                            # i = 0
                            # for x in listagrad:
                            #     a = x.fechagraduado.year
                            #     if i == 0:
                            #         listanio.append(a)
                            #         i += 1
                            #     else:
                            #         if a not in listanio:
                            #             listanio.append(a)
                            listanios = Graduado.objects.filter(status=True, inscripcion__carrera__id=idcar,
                                                                fechagraduado__isnull=False).annotate(
                                Year=ExtractYear('fechagraduado')).values_list('Year', flat=True).order_by(
                                'Year').distinct()
                            for x in listanios:
                                listanio.append([x])
                        elif opc == '2':
                            data['idperiodo'] = idp = request.GET['idperiodo']
                            encuestas = SagEncuesta.objects.filter(status=True, sagperiodo=idp)
                            lista = []
                            for x in encuestas:
                                lista.append([x.id, x.nombre])
                            # listagrad = Graduado.objects.filter(inscripcion__carrera__in=miscarreras)
                            # listanio = []
                            # i = 0
                            # for x in listagrad:
                            #     a = x.fechagraduado.year
                            #     if i == 0:
                            #         listanio.append(a)
                            #         i += 1
                            #     else:
                            #         if a not in listanio:
                            #             listanio.append(a)
                            # listanio.sort()

                            listanios = Graduado.objects.filter(status=True, inscripcion__carrera__in=miscarreras,
                                                                fechagraduado__isnull=False).annotate(
                                Year=ExtractYear('fechagraduado')).values_list('Year', flat=True).order_by(
                                'Year').distinct()
                            for x in listanios:
                                listanio.append([x])
                        elif opc == '3':
                            data['idperiodo'] = idp = request.GET['idperiodo']
                            data['idencu'] = idencu = request.GET['idencu']
                            preguntas = SagPreguntaEncuesta.objects.filter(status=True,sagencuesta=idencu, sagencuesta__sagperiodo=idp, sagpregunta__status=True).exclude(tipo__in=[1,5]).order_by('orden')
                            lista = []
                            for x in preguntas:
                                lista.append([x.sagpregunta.id, x.sagpregunta.nombre, x.orden, x.tipo.id,x.responder ])
                        elif opc == '4':
                            data['idperiodo'] = idp = request.GET['idperiodo']
                            preguntas = SagPreguntaEncuesta.objects.filter(status=True,
                                                                           sagencuesta__sagperiodo=idp,
                                                                           sagpregunta__status=True).exclude(tipo__in=[1,5])
                            lista = []
                            for x in preguntas:
                                lista.append([x.sagpregunta.id, x.sagpregunta.nombre, x.orden, x.tipo.id , x.responder])
                        elif opc == '5':
                            data['idperiodo'] = idp = request.GET['idperiodo']
                            data['idpreg'] = idpreg= request.GET['idpreg']
                            encuestas = SagPreguntaEncuesta.objects.filter(status=True, sagpregunta=idpreg,
                                                                           sagencuesta__sagperiodo=idp,
                                                                           sagpregunta__status=True)
                            lista = []
                            for x in encuestas:
                                lista.append([x.sagencuesta.id, x.sagencuesta.nombre])
                        elif opc == '6':
                            data['idperiodo'] = idp = request.GET['idperiodo']
                            encuestas = SagPreguntaEncuesta.objects.filter(status=True,
                                                                           sagencuesta__sagperiodo=idp,
                                                                           sagpregunta__status=True)
                            lista = []
                            for x in encuestas:
                                lista.append([x.sagencuesta.id, x.sagencuesta.nombre])

                        elif opc == '7':
                            data['idfac'] = idfac = request.GET['idfac']
                            listacarrera = Carrera.objects.filter(coordinacion__excluir=False,coordinacion=idfac)
                            lista = []
                            for x in listacarrera:
                                if x.mencion:
                                    carrera=x.nombre+' CON MENCIÓN EN '+ x.mencion
                                else:
                                    carrera = x.nombre
                                lista.append([x.id,carrera])
                        elif opc == '8':
                            lista = []
                            listacarrera = Carrera.objects.filter(coordinacion__excluir=False,status=True)
                            for x in listacarrera:
                                if x.mencion:
                                    carrera = x.nombre + ' CON MENCIÓN EN ' + x.mencion
                                else:
                                    carrera = x.nombre
                                lista.append([x.id, carrera])

                        return JsonResponse({'result': 'ok', 'lista': lista,'listanio':listanio})
                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

            elif action == 'sacarresultados':
                try:
                    data['idpreg'] = idpreg = request.GET['idpreg']
                    data['idper'] = idper = request.GET['idper']
                    data['idencuesta'] = idencuesta = request.GET['idencuesta']
                    data['tipo'] = tipo = int(request.GET['tipo'])
                    data['idcar'] = idcar = int(request.GET['idcar'])
                    data['idanio'] = idanio = int(request.GET['idanio'])
                    if idcar>0 and idanio>0:
                        totalfin = SagResultadoEncuesta.objects.filter(sagperiodo=idper, status=True,
                                                                       inscripcion__graduado__status=True,
                                                                       inscripcion__carrera=idcar,
                                                                       inscripcion__graduado__fechagraduado__year=idanio
                                                                       ).aggregate(total=Count('id'))['total']
                    elif idcar>0:
                        totalfin = SagResultadoEncuesta.objects.filter(sagperiodo=idper, status=True,
                                                                       inscripcion__graduado__status=True,
                                                                       inscripcion__carrera=idcar,
                                                                       ).aggregate(total=Count('id'))['total']
                    elif idanio>0:
                        totalfin = SagResultadoEncuesta.objects.filter(sagperiodo=idper, status=True,
                                                                       inscripcion__graduado__status=True,
                                                                       inscripcion__graduado__fechagraduado__year=idanio
                                                                       ).aggregate(total=Count('id'))['total']
                    else:
                        totalfin = SagResultadoEncuesta.objects.filter(sagperiodo=idper, status=True,
                                                                       inscripcion__graduado__status=True).aggregate(
                            total=Count('id'))['total']
                    listado = []
                    listacantidades = []
                    listadocompleto = []
                    if tipo ==6:
                        listresp = []
                        porcentajes = []
                        if idcar > 0 and idanio > 0:
                            respuestas = SagResultadoEncuestaDetalle.objects.filter(status=True,
                                                                                    preguntaencuesta__status=True,
                                                                                    preguntaencuesta__sagpregunta__id=idpreg,
                                                                                    preguntaencuesta__tipo__id=tipo,
                                                                                    preguntaencuesta__sagencuesta__id=idencuesta,
                                                                                    sagresultadoencuesta__status=True,
                                                                                    sagresultadoencuesta__inscripcion__carrera=idcar,
                                                                                    sagresultadoencuesta__inscripcion__graduado__status=True,
                                                                                    sagresultadoencuesta__inscripcion__graduado__fechagraduado__year=idanio,
                                                                                    sagresultadoencuesta__sagperiodo__id=idper).exclude(valor="")
                            respuestasnull = SagResultadoEncuestaDetalle.objects.filter(status=True, valor='',
                                                                                        preguntaencuesta__status=True,
                                                                                        preguntaencuesta__tipo__id=tipo,
                                                                                        preguntaencuesta__sagpregunta__id=idpreg,
                                                                                        preguntaencuesta__sagencuesta__id=idencuesta,
                                                                                        sagresultadoencuesta__status=True,
                                                                                        sagresultadoencuesta__sagperiodo__id=idper,
                                                                                        sagresultadoencuesta__inscripcion__carrera=idcar,
                                                                                        sagresultadoencuesta__inscripcion__graduado__status=True,
                                                                                        sagresultadoencuesta__inscripcion__graduado__fechagraduado__year=idanio)
                        elif idcar > 0:
                            respuestas = SagResultadoEncuestaDetalle.objects.filter(status=True,
                                                                                    preguntaencuesta__status=True,
                                                                                    preguntaencuesta__sagpregunta__id=idpreg,
                                                                                    preguntaencuesta__tipo__id=tipo,
                                                                                    preguntaencuesta__sagencuesta__id=idencuesta,
                                                                                    sagresultadoencuesta__status=True,
                                                                                    sagresultadoencuesta__inscripcion__carrera=idcar,
                                                                                    sagresultadoencuesta__inscripcion__graduado__status=True,
                                                                                    sagresultadoencuesta__sagperiodo__id=idper).exclude(valor="")
                            respuestasnull = SagResultadoEncuestaDetalle.objects.filter(status=True, valor='',
                                                                                        preguntaencuesta__status=True,
                                                                                        preguntaencuesta__tipo__id=tipo,
                                                                                        preguntaencuesta__sagpregunta__id=idpreg,
                                                                                        preguntaencuesta__sagencuesta__id=idencuesta,
                                                                                        sagresultadoencuesta__status=True,
                                                                                        sagresultadoencuesta__sagperiodo__id=idper,
                                                                                        sagresultadoencuesta__inscripcion__carrera=idcar,
                                                                                        sagresultadoencuesta__inscripcion__graduado__status=True)
                        elif idanio > 0:
                            respuestas = SagResultadoEncuestaDetalle.objects.filter(status=True,
                                                                                    preguntaencuesta__status=True,
                                                                                    preguntaencuesta__sagpregunta__id=idpreg,
                                                                                    preguntaencuesta__tipo__id=tipo,
                                                                                    preguntaencuesta__sagencuesta__id=idencuesta,
                                                                                    sagresultadoencuesta__status=True,
                                                                                    sagresultadoencuesta__inscripcion__graduado__fechagraduado__year=idanio,
                                                                                    sagresultadoencuesta__inscripcion__graduado__status=True,
                                                                                    sagresultadoencuesta__sagperiodo__id=idper).exclude(valor="")
                            respuestasnull = SagResultadoEncuestaDetalle.objects.filter(status=True, valor='',
                                                                                        preguntaencuesta__status=True,
                                                                                        preguntaencuesta__tipo__id=tipo,
                                                                                        preguntaencuesta__sagpregunta__id=idpreg,
                                                                                        preguntaencuesta__sagencuesta__id=idencuesta,
                                                                                        sagresultadoencuesta__status=True,
                                                                                        sagresultadoencuesta__sagperiodo__id=idper,
                                                                                        sagresultadoencuesta__inscripcion__graduado__fechagraduado__year=idanio,
                                                                                        sagresultadoencuesta__inscripcion__graduado__status=True)
                        else:
                            respuestas = SagResultadoEncuestaDetalle.objects.filter(status=True,
                                                                                    preguntaencuesta__status=True,
                                                                                    preguntaencuesta__sagpregunta__id=idpreg,
                                                                                    preguntaencuesta__tipo__id=tipo,
                                                                                    preguntaencuesta__sagencuesta__id=idencuesta,
                                                                                    sagresultadoencuesta__status=True,
                                                                                    sagresultadoencuesta__sagperiodo__id=idper,
                                                                                    sagresultadoencuesta__inscripcion__graduado__status=True).exclude(valor="")
                            respuestasnull = SagResultadoEncuestaDetalle.objects.filter(status=True,valor='',
                                                                                        preguntaencuesta__status=True,
                                                                                        preguntaencuesta__tipo__id=tipo,
                                                                                        preguntaencuesta__sagpregunta__id=idpreg,
                                                                                        preguntaencuesta__sagencuesta__id=idencuesta,
                                                                                        sagresultadoencuesta__status=True,
                                                                                        sagresultadoencuesta__sagperiodo__id=idper,
                                                                                        sagresultadoencuesta__inscripcion__graduado__status=True)
                        # totalfin=respuestas.count()+respuestasnull.count()
                        if respuestasnull.count()>0:
                            totalnull = respuestasnull.count()
                            totnull = round(((totalnull * 100) / float(totalfin)), 2)
                            lista = {}
                            lista['nombre'] = "Vacios"
                            lista['porcentaje'] = totnull
                            listado.append(lista)
                            listaca = {}
                            listaca['nombre'] = "Vacios"
                            listaca['porcentaje'] = totnull
                            listaca['cantidad'] = totalnull
                            listadocompleto.append(listaca)
                        i = 0
                        for x in respuestas:
                            a=int(x.valor)
                            a = abs(a)
                            if i == 0:
                                listresp.append(a)
                                i += 1
                            elif a not in listresp and a >= 0:
                                listresp.append(a)
                        listresp.sort()
                        for f in listresp:
                            opc2 = f * -1
                            opc3="0"+str(f)
                            totopc = respuestas.filter(Q(valor=f) | Q(valor=opc2) | Q(valor=opc3)).count()
                            totporc = round(((totopc * 100) / float(totalfin)), 2)
                            porcentajes.append(totporc)
                            listacantidades.append(totopc)
                        z = 0
                        for y in listresp:
                            lista = {}
                            lista['nombre'] = y
                            lista['porcentaje'] = porcentajes[z]
                            listado.append(lista)
                            z += 1
                    elif tipo ==2 :
                        listresp = []
                        porcentajes = []
                        if idcar > 0 and idanio > 0:
                            respuestast2 = SagResultadoEncuestaDetalle.objects.filter(status=True,
                                                                                      sagresultadoencuesta__status=True,
                                                                                      sagresultadoencuesta__inscripcion__graduado__status=True,
                                                                                      sagresultadoencuesta__sagperiodo__id=idper,
                                                                                      sagresultadoencuesta__inscripcion__carrera=idcar,
                                                                                      sagresultadoencuesta__inscripcion__graduado__fechagraduado__year=idanio,
                                                                                      preguntaencuesta__status=True,
                                                                                      valor__gte=0,
                                                                                      preguntaencuesta__sagpregunta__id=idpreg,
                                                                                      preguntaencuesta__sagencuesta__id=idencuesta,
                                                                                      preguntaencuesta__tipo__id=tipo,
                                                                                      ).extra({'valor_as_int': "valor::INTEGER"})
                        elif idanio > 0:
                            respuestast2 = SagResultadoEncuestaDetalle.objects.filter(status=True,
                                                                                      sagresultadoencuesta__status=True,
                                                                                      sagresultadoencuesta__inscripcion__graduado__status=True,
                                                                                      sagresultadoencuesta__sagperiodo__id=idper,
                                                                                      sagresultadoencuesta__inscripcion__graduado__fechagraduado__year=idanio,
                                                                                      preguntaencuesta__status=True,
                                                                                      valor__gte=0,
                                                                                      preguntaencuesta__sagpregunta__id=idpreg,
                                                                                      preguntaencuesta__sagencuesta__id=idencuesta,
                                                                                      preguntaencuesta__tipo__id=tipo,
                                                                                      ).extra({'valor_as_int': "valor::INTEGER"})
                        elif idcar > 0:
                            respuestast2 = SagResultadoEncuestaDetalle.objects.filter(status=True, sagresultadoencuesta__status=True,
                                                                                      sagresultadoencuesta__inscripcion__graduado__status=True,
                                                                                      sagresultadoencuesta__sagperiodo__id=idper,
                                                                                      sagresultadoencuesta__inscripcion__carrera=idcar,
                                                                                      preguntaencuesta__status=True,
                                                                                      valor__gte=0,
                                                                                      preguntaencuesta__sagpregunta__id=idpreg,
                                                                                      preguntaencuesta__sagencuesta__id=idencuesta,
                                                                                      preguntaencuesta__tipo__id=tipo,
                                                                                      ).extra({'valor_as_int': "valor::INTEGER"})
                        else:
                            respuestast2 = SagResultadoEncuestaDetalle.objects.filter(status=True,valor__gte=0,
                                                                                      sagresultadoencuesta__status=True,
                                                                                      sagresultadoencuesta__inscripcion__graduado__status=True,
                                                                                      preguntaencuesta__status=True,
                                                                                      preguntaencuesta__sagpregunta__id=idpreg,
                                                                                      preguntaencuesta__sagencuesta__id=idencuesta,
                                                                                      preguntaencuesta__tipo__id=tipo,
                                                                                      sagresultadoencuesta__sagperiodo__id=idper).extra({'valor_as_int': "valor::INTEGER"})
                        totalfin =respuestast2.count()
                        resitem = SagEncuestaItem.objects.filter(status=True,preguntaencuesta__sagpregunta__id=idpreg)
                        # ver la division para cero
                        if totalfin !=0:
                            for res in resitem:
                                item = res.nombre
                                listresp.append(item)
                                totopct2 = respuestast2.filter(valor=res.id).count()
                                totporct2 = round(((totopct2 * 100) / float(totalfin)), 2)
                                porcentajes.append(totporct2)
                                listacantidades.append(totopct2)
                            g = 0
                            for y in listresp:
                                lista = {}
                                lista['nombre'] = y
                                lista['porcentaje'] = porcentajes[g]
                                listado.append(lista)
                                g += 1
                    elif  tipo == 4:
                        listresp = []
                        porcentajes = []
                        if idcar > 0 and idanio > 0:
                            respuestast2 = SagResultadoEncuestaDetalle.objects.filter(status=True,
                                                                                      sagresultadoencuesta__status=True,
                                                                                      sagresultadoencuesta__inscripcion__graduado__status=True,
                                                                                      sagresultadoencuesta__sagperiodo__id=idper,
                                                                                      sagresultadoencuesta__inscripcion__carrera=idcar,
                                                                                      sagresultadoencuesta__inscripcion__graduado__fechagraduado__year=idanio,
                                                                                      preguntaencuesta__status=True,
                                                                                      valor__gte=0,
                                                                                      preguntaencuesta__sagpregunta__id=idpreg,
                                                                                      preguntaencuesta__sagencuesta__id=idencuesta,
                                                                                      preguntaencuesta__tipo__id=tipo,
                                                                                      ).extra({'valor_as_int': "valor::INTEGER"})
                        elif idcar > 0:
                            respuestast2 = SagResultadoEncuestaDetalle.objects.filter(status=True, sagresultadoencuesta__status=True,
                                                                                      sagresultadoencuesta__inscripcion__graduado__status=True,
                                                                                      sagresultadoencuesta__sagperiodo__id=idper,
                                                                                      sagresultadoencuesta__inscripcion__carrera=idcar,
                                                                                      preguntaencuesta__status=True,
                                                                                      valor__gte=0,
                                                                                      preguntaencuesta__sagpregunta__id=idpreg,
                                                                                      preguntaencuesta__sagencuesta__id=idencuesta,
                                                                                      preguntaencuesta__tipo__id=tipo,
                                                                                      ).extra({'valor_as_int': "valor::INTEGER"})
                        elif idanio > 0:
                            respuestast2 = SagResultadoEncuestaDetalle.objects.filter(status=True, sagresultadoencuesta__status=True,
                                                                                      sagresultadoencuesta__inscripcion__graduado__status=True,
                                                                                      sagresultadoencuesta__sagperiodo__id=idper,
                                                                                      sagresultadoencuesta__inscripcion__graduado__fechagraduado__year=idanio,
                                                                                      preguntaencuesta__status=True,
                                                                                      valor__gte=0,
                                                                                      preguntaencuesta__sagpregunta__id=idpreg,
                                                                                      preguntaencuesta__sagencuesta__id=idencuesta,
                                                                                      preguntaencuesta__tipo__id=tipo,
                                                                                      ).extra({'valor_as_int': "valor::INTEGER"})
                        else:
                            respuestast2 = SagResultadoEncuestaDetalle.objects.filter(status=True,valor__gte=0,
                                                                                      sagresultadoencuesta__status=True,
                                                                                      sagresultadoencuesta__inscripcion__graduado__status=True,
                                                                                      preguntaencuesta__status=True,
                                                                                      preguntaencuesta__sagpregunta__id=idpreg,
                                                                                      preguntaencuesta__sagencuesta__id=idencuesta,
                                                                                      preguntaencuesta__tipo__id=tipo,
                                                                                      sagresultadoencuesta__sagperiodo__id=idper).distinct().extra({'valor_as_int': "valor::INTEGER"})
                        resitem = SagEncuestaItem.objects.filter(status=True,preguntaencuesta__sagpregunta__id=idpreg)
                        totalfin = respuestast2.count()
                        for res in resitem:
                            item = res.nombre
                            listresp.append(item)
                            totopct2 = respuestast2.filter(valor=res.id).count()
                            totporct2 = round(((totopct2 * 100) / float(totalfin)), 2)
                            porcentajes.append(totporct2)
                            listacantidades.append(totopct2)
                        g = 0
                        for y in listresp:
                            lista = {}
                            lista['nombre'] = y
                            lista['porcentaje'] = porcentajes[g]
                            listado.append(lista)
                            g += 1
                    elif tipo == 3 or tipo == 8:
                        listresp = [1, 2, 3, 4, 5, 6, 7]
                        # listrespt3 = []
                        porcentajes = []
                        if idcar > 0 and idanio > 0:
                            respuestast3 = SagResultadoEncuestaDetalle.objects.filter(status=True, valor__gte=0,
                                                                                      sagresultadoencuesta__status=True,
                                                                                      sagresultadoencuesta__sagperiodo__id=idper,
                                                                                      sagresultadoencuesta__inscripcion__carrera=idcar,
                                                                                      sagresultadoencuesta__inscripcion__graduado__fechagraduado__year=idanio,
                                                                                      sagresultadoencuesta__inscripcion__graduado__status=True,
                                                                                      preguntaencuesta__status=True,
                                                                                      preguntaencuesta__tipo__id=tipo,
                                                                                      preguntaencuesta__sagpregunta__id=idpreg,
                                                                                      preguntaencuesta__sagencuesta__id=idencuesta
                                                                                      ).extra({'valor_as_int': "valor::INTEGER"})
                        elif idcar > 0:
                            respuestast3 = SagResultadoEncuestaDetalle.objects.filter(status=True,valor__gte=0,
                                                                                      sagresultadoencuesta__status=True,
                                                                                      sagresultadoencuesta__sagperiodo__id=idper,
                                                                                      sagresultadoencuesta__inscripcion__carrera=idcar,
                                                                                      sagresultadoencuesta__inscripcion__graduado__status=True,
                                                                                      preguntaencuesta__status=True,
                                                                                      preguntaencuesta__tipo__id=tipo,
                                                                                      preguntaencuesta__sagpregunta__id=idpreg,
                                                                                      preguntaencuesta__sagencuesta__id=idencuesta
                                                                                      ).extra({'valor_as_int': "valor::INTEGER"})
                        elif idanio > 0:
                            respuestast3 = SagResultadoEncuestaDetalle.objects.filter(status=True,valor__gte=0,
                                                                                      sagresultadoencuesta__status=True,
                                                                                      sagresultadoencuesta__sagperiodo__id=idper,
                                                                                      sagresultadoencuesta__inscripcion__graduado__fechagraduado__year=idanio,
                                                                                      sagresultadoencuesta__inscripcion__graduado__status=True,
                                                                                      preguntaencuesta__status=True,
                                                                                      preguntaencuesta__tipo__id=tipo,
                                                                                      preguntaencuesta__sagpregunta__id=idpreg,
                                                                                      preguntaencuesta__sagencuesta__id=idencuesta
                                                                                      ).extra({'valor_as_int': "valor::INTEGER"})
                        else:
                            respuestast3 = SagResultadoEncuestaDetalle.objects.filter(status=True,valor__gte=0,
                                                                                      sagresultadoencuesta__status=True,
                                                                                      sagresultadoencuesta__sagperiodo__id=idper,
                                                                                      sagresultadoencuesta__inscripcion__graduado__status=True,
                                                                                      preguntaencuesta__status=True,
                                                                                      preguntaencuesta__tipo__id=tipo,
                                                                                      preguntaencuesta__sagpregunta__id=idpreg,
                                                                                      preguntaencuesta__sagencuesta__id=idencuesta).extra({'valor_as_int': "valor::INTEGER"})
                        totalfin = respuestast3.count()
                        if totalfin != 0:
                            for f in listresp:
                                totopc = respuestast3.filter(valor=f).count()
                                totporc = round(((totopc * 100) / float(totalfin)), 2)
                                porcentajes.append(totporc)
                                listacantidades.append(totopc)
                            s=0
                            for y in listresp:
                                lista = {}
                                lista['nombre'] = y
                                lista['porcentaje'] = porcentajes[s]
                                listado.append(lista)
                                s += 1
                    s=0
                    if porcentajes and listacantidades:
                        for h in listresp:
                            listaca = {}
                            listaca['nombre'] = h
                            listaca['porcentaje'] = porcentajes[s]
                            listaca['cantidad'] = listacantidades[s]
                            listadocompleto.append(listaca)
                            s += 1
                        data['resultados'] = listadocompleto
                        data['total'] = totalfin
                        if tipo == 4:
                            data['total'] = respuestast2.count()
                    template = get_template("sagadministracion/tablapie.html")
                    json_content = template.render(data)
                    return JsonResponse({"result": "ok","html":json_content,"lista": listado, "total": totalfin})
                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

            elif action == 'sacarresultadosm1':
                try:
                    data['idpreg'] = idpreg = request.GET['idpreg']
                    data['idper'] = idper = request.GET['idper']
                    data['idencuesta'] = idencuesta = request.GET['idencuesta']
                    data['tipo'] = tipo = int(request.GET['tipo'])
                    data['idcar'] = idcar = int(request.GET['idcar'])
                    data['idanio'] = idanio = int(request.GET['idanio'])
                    listado=[]
                    listresp=[1, 2, 3, 4, 5, 6, 7]
                    if tipo == 7 :
                        if idcar > 0 and idanio > 0:
                            respuestas = SagResultadoEncuestaDetalle.objects.filter(status=True,valor__gte=0,
                                                                                    sagresultadoencuesta__status=True,
                                                                                    sagresultadoencuesta__inscripcion__carrera=idcar,
                                                                                    sagresultadoencuesta__sagperiodo__id=idper,
                                                                                    sagresultadoencuesta__inscripcion__graduado__status=True,
                                                                                    sagresultadoencuesta__inscripcion__graduado__fechagraduado__year=idanio,
                                                                                    preguntaencuesta__status=True,
                                                                                    preguntaencuesta__tipo__id=tipo,
                                                                                    preguntaencuesta__sagencuesta__id=idencuesta,
                                                                                    preguntaencuesta__sagpregunta__id=idpreg
                                                                                    ).extra({'valor_as_int': "valor::INTEGER"})
                            totalcedulas = SagResultadoEncuesta.objects.filter(sagperiodo=idper, status=True,
                                                                               inscripcion__graduado__status=True,
                                                                               inscripcion__carrera=idcar,
                                                                               inscripcion__graduado__fechagraduado__year=idanio
                                                                               ).aggregate(total=Count('id'))['total']
                        elif idanio > 0:
                            respuestas = SagResultadoEncuestaDetalle.objects.filter(status=True,valor__gte=0,
                                                                                    sagresultadoencuesta__status=True,
                                                                                    sagresultadoencuesta__inscripcion__graduado__status=True,
                                                                                    sagresultadoencuesta__inscripcion__graduado__fechagraduado__year=idanio,
                                                                                    preguntaencuesta__status=True,
                                                                                    preguntaencuesta__tipo__id=tipo,
                                                                                    preguntaencuesta__sagencuesta__id=idencuesta,
                                                                                    preguntaencuesta__sagpregunta__id=idpreg,
                                                                                    sagresultadoencuesta__sagperiodo__id=idper
                                                                                    ).extra({'valor_as_int': "valor::INTEGER"})
                            totalcedulas= SagResultadoEncuesta.objects.filter(sagperiodo=idper, status=True,
                                                                              inscripcion__graduado__status=True,
                                                                              inscripcion__graduado__fechagraduado__year=idanio
                                                                              ).aggregate(total=Count('id'))['total']
                        elif idcar > 0:
                            respuestas = SagResultadoEncuestaDetalle.objects.filter(status=True,
                                                                                    sagresultadoencuesta__status=True,
                                                                                    sagresultadoencuesta__inscripcion__graduado__status=True,
                                                                                    preguntaencuesta__status=True, valor__gte=0,
                                                                                    preguntaencuesta__tipo__id=tipo,
                                                                                    preguntaencuesta__sagencuesta__id=idencuesta,
                                                                                    preguntaencuesta__sagpregunta__id=idpreg,
                                                                                    sagresultadoencuesta__inscripcion__carrera=idcar,
                                                                                    sagresultadoencuesta__sagperiodo__id=idper
                                                                                    ).extra({'valor_as_int': "valor::INTEGER"})
                            totalcedulas= SagResultadoEncuesta.objects.filter(sagperiodo=idper, status=True,
                                                                              inscripcion__graduado__status=True,
                                                                              inscripcion__carrera=idcar
                                                                              ).aggregate(total=Count('id'))['total']
                        else:
                            respuestas = SagResultadoEncuestaDetalle.objects.filter(status=True,
                                                                                    sagresultadoencuesta__status=True,
                                                                                    sagresultadoencuesta__inscripcion__graduado__status=True,
                                                                                    preguntaencuesta__status=True,
                                                                                    valor__gte=0,
                                                                                    preguntaencuesta__sagencuesta__id=idencuesta,
                                                                                    preguntaencuesta__tipo__id=tipo,
                                                                                    preguntaencuesta__sagpregunta__id=idpreg,
                                                                                    sagresultadoencuesta__sagperiodo__id=idper
                                                                                    ).extra({'valor_as_int': "valor::INTEGER"})
                            totalcedulas = SagResultadoEncuesta.objects.filter(sagperiodo=idper, status=True,
                                                                               inscripcion__graduado__status=True
                                                                               ).aggregate(total=Count('id'))['total']

                        # totalcedulas =totalcedulas.count()
                        for f in listresp:
                            lista = {}
                            total = respuestas.filter(valor=f).count()
                            if total==0:
                                porcb=0
                                porcc=0
                            else:
                                a = respuestas.filter(valor=f)
                                b = a.filter(numero='1').count()
                                c = a.filter(numero='2').count()
                                porcb = round(((b * 100) / float(total)), 2)
                                porcc = round(((c * 100) / float(total)), 2)
                            lista['u'] = porcb
                            lista['e'] = porcc
                            listado.append(lista)
                        data['resultados']=listado
                    template = get_template("sagadministracion/tablam1.html")
                    templateporc = get_template("sagadministracion/tablaporc.html")
                    json_content = template.render(data)
                    json_contentporc = templateporc.render(data)
                    return JsonResponse({"result": "ok", 'html': json_content,'porc':json_contentporc,"total":totalcedulas})
                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

            elif action == 'listainformes':
                try:
                    data['title'] = u'Informes'
                    data['idperiodo'] = request.GET['idperiodo']
                    data['nombperiodo'] = request.GET['nombperiodo']
                    data['facultades']=Coordinacion.objects.filter(status=True,excluir=False)
                    data['carreras'] = Carrera.objects.filter(status=True, coordinacion__excluir=False)
                    return render(request, "sagadministracion/informes.html", data)
                except Exception as ex:
                    pass

            elif action == 'resultadosinformeconsolidado':
                try:
                    data = {}
                    data['opc'] = opc = int(request.GET['opc'])
                    data['indicadorc'] =indicadorc= SagIndicadorEncuesta.objects.filter(Q(indicador__codigo__icontains='C'),
                                                                                        status=True,
                                                                                        indicador__vigente=True).order_by(
                        "indicador__codigo")
                    data['indicadore'] = indicadore=SagIndicadorEncuesta.objects.filter(Q(indicador__codigo__icontains='E'),
                                                                                        status=True,
                                                                                        indicador__vigente=True).exclude(
                        Q(indicador__codigo__icontains='PE')).order_by("indicador__codigo")
                    data['indicadorpe'] =indicadorpe= SagIndicadorEncuesta.objects.filter(Q(indicador__codigo__icontains='PE'),
                                                                                          status=True,
                                                                                          indicador__vigente=True).exclude(Q(indicador__codigo__icontains='PE11') | Q(indicador__codigo__icontains='PE12')).order_by(
                        "indicador__codigo")
                    data['indicadorpe11'] = indicadorpe11 = SagIndicadorEncuesta.objects.filter(Q(indicador__codigo__icontains='PE11'), status=True, indicador__vigente=True).order_by("preguntaencuesta__orden")
                    data['indicadorpe12'] = indicadorpe12 = SagIndicadorEncuesta.objects.filter(Q(indicador__codigo__icontains='PE12'), status=True, indicador__vigente=True).order_by("indicador__codigo")
                    if opc == 1:
                        template = get_template("sagadministracion/resultadosinformeconsolidado.html")
                        json_content = template.render(data)
                        return JsonResponse({"result": "ok", 'html': json_content})
                    elif opc == 2:
                        data['nombperiodo'] = nombperiodo = request.GET['nombperiodo']
                        return conviert_html_to_pdf('sagadministracion/informe_consolidado_pdf.html',
                                                    {'pagesize': 'A4', 'data': data, 'indicadorc': indicadorc,
                                                     'indicadore': indicadore, 'indicadorpe': indicadorpe,
                                                     'indicadorpe11': indicadorpe11,'nombperiodo':nombperiodo,
                                                     'indicadorpe12': indicadorpe12})
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

            elif action == 'generar_informe_cosolidado_excel':
                try:
                    font_style = XFStyle()
                    font_style.font.bold = True
                    font_style2 = XFStyle()
                    font_style2.font.bold = False
                    wb = Workbook(encoding='utf-8')
                    indicadorpr = SagIndicadorEncuesta.objects.filter(
                        Q(indicador__codigo__icontains='PR'),
                        status=True, indicador__vigente=True,
                        preguntaencuesta__status=True).order_by(
                        "indicador__codigo")
                    for x in indicadorpr:
                        pestania=x.indicador.codigo+'-'+x.preguntaencuesta.orden.__str__()+'-'+x.preguntaencuesta.sagpregunta.id.__str__()
                        ws = wb.add_sheet(pestania)
                        response = HttpResponse(content_type="application/ms-excel")
                        response[
                            'Content-Disposition'] = 'attachment; filename=informe_consolidado_indicador_pr' + random.randint(
                            1, 10000).__str__() + '.xls'
                        columns = [
                            (u"Código Indicador.", 1500),
                            (u"No. Pregunta Encuesta", 6000),
                            (u"Indicador", 6000),
                            (u"Resultados", 3000)
                        ]
                        row_num = 1
                        for col_num in range(len(columns)):
                            ws.write(row_num, col_num, columns[col_num][0], font_style)
                            ws.col(col_num).width = columns[col_num][1]
                        date_format = xlwt.XFStyle()
                        date_format.num_format_str = 'yyyy/mm/dd'
                        listarespuestas=x.resultadogeneraltexto(0)
                        row_num = 2
                        for r in listarespuestas:
                            campo1 = x.indicador.codigoindicador()
                            campo2 = x.preguntaencuesta.orden.__str__() +' '+ x.preguntaencuesta.sagpregunta.nombre.__str__()
                            campo3 = x.indicador.nombreindicador()
                            campo4 = r
                            ws.write(row_num, 0, campo1, font_style2)
                            ws.write(row_num, 1, campo2, font_style2)
                            ws.write(row_num, 2, campo3, font_style2)
                            ws.write(row_num, 3, campo4, font_style2)
                            row_num += 1
                    wb.save(response)
                    return response
                except Exception as ex:
                    pass

            elif action == 'resultadosinformecarrera':
                try:
                    data = {}
                    pe12 = None
                    data['idcarr'] = idcarr = int(request.GET['idcarr'])
                    data['opc'] = opc = int(request.GET['opc'])
                    data['carrera'] =carrera= Carrera.objects.get(pk=idcarr)
                    data['indicadorc'] = indicadorc=SagIndicadorEncuesta.objects.filter(Q(indicador__codigo__icontains='C'),
                                                                                        status=True,
                                                                                        indicador__vigente=True).order_by(
                        "indicador__codigo")
                    data['indicadore'] =indicadore= SagIndicadorEncuesta.objects.filter(Q(indicador__codigo__icontains='E'),
                                                                                        status=True,
                                                                                        indicador__vigente=True).exclude(
                        Q(indicador__codigo__icontains='PE')).order_by("indicador__codigo")
                    data['indicadorpe'] = indicadorpe=SagIndicadorEncuesta.objects.filter(Q(indicador__codigo__icontains='PE'),
                                                                                          status=True,
                                                                                          indicador__vigente=True).exclude(
                        Q(indicador__codigo__icontains='PE11') | Q(indicador__codigo__icontains='PE12')).order_by(
                        "indicador__codigo")
                    data['indicadorpe11'] = indicadorpe11=SagIndicadorEncuesta.objects.filter(Q(indicador__codigo__icontains='PE11'), status=True, indicador__vigente=True).order_by("preguntaencuesta__orden")
                    encuestacarrera = SagEncuestaCarrera.objects.filter(carrera__id=idcarr, status=True).exclude(sagecuesta__id=1)
                    todo = None
                    if encuestacarrera.__len__() > 0:
                        for x in encuestacarrera:
                            pe12 = SagIndicadorEncuesta.objects.filter(Q(indicador__codigo__icontains='PE12'),
                                                                       status=True, indicador__vigente=True,
                                                                       preguntaencuesta__sagencuesta=x.sagecuesta).order_by("preguntaencuesta__orden")
                            if todo:
                                todo = list(chain(todo, pe12))
                            else:
                                todo = pe12
                    data['indicadorpe12'] = todo
                    data['indicadorpr'] = indicadorpr = SagIndicadorEncuesta.objects.filter(
                        Q(indicador__codigo__icontains='PR'), status=True, indicador__vigente=True,
                        preguntaencuesta__status=True).order_by("indicador__codigo")
                    if opc == 1:
                        template = get_template("sagadministracion/resultadosinformecarrera.html")
                        json_content = template.render(data)
                        return JsonResponse({"result": "ok", 'html': json_content})
                    elif opc == 2:
                        data['nombperiodo'] = nombperiodo = request.GET['nombperiodo']
                        return conviert_html_to_pdf('sagadministracion/informe_carrera_pdf.html',
                                                    {'pagesize': 'A4', 'data': data, 'indicadorc': indicadorc,
                                                     'indicadore': indicadore, 'indicadorpe': indicadorpe,
                                                     'indicadorpe11': indicadorpe11, 'indicadorpr': indicadorpr,
                                                     'indicadorpe12': todo, 'idcarr': idcarr, 'carrera': carrera,
                                                     'nombperiodo': nombperiodo})
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

            elif action == 'generar_informe_carrera_excel':
                try:
                    idcarr = int(request.GET['idcarr'])
                    carrera=Carrera.objects.get(pk=idcarr)
                    font_style = XFStyle()
                    font_style.font.bold = True
                    font_style2 = XFStyle()
                    font_style2.font.bold = False
                    wb = Workbook(encoding='utf-8')
                    indicadorpr = SagIndicadorEncuesta.objects.filter(Q(indicador__codigo__icontains='PR'),status=True, indicador__vigente=True,preguntaencuesta__status=True).order_by("indicador__codigo")
                    for x in indicadorpr:
                        pestania=x.indicador.codigo+'-'+x.preguntaencuesta.orden.__str__()+'-'+x.preguntaencuesta.sagpregunta.id.__str__()
                        ws = wb.add_sheet(pestania)
                        response = HttpResponse(content_type="application/ms-excel")
                        response['Content-Disposition'] = 'attachment; filename=informe_indicador_carrera_pr' + random.randint(1, 10000).__str__() + '.xls'
                        columns = [
                            (u"Carrera", 1500),
                            (u"Código Indicador.", 1500),
                            (u"No. Pregunta Encuesta", 6000),
                            (u"Indicador", 6000),
                            (u"Resultados", 3000)
                        ]
                        row_num = 1
                        for col_num in range(len(columns)):
                            ws.write(row_num, col_num, columns[col_num][0], font_style)
                            ws.col(col_num).width = columns[col_num][1]
                        date_format = xlwt.XFStyle()
                        date_format.num_format_str = 'yyyy/mm/dd'
                        listarespuestas=x.resultadogeneraltexto(idcarr)
                        row_num = 2
                        for r in listarespuestas:
                            campo1 = x.indicador.codigoindicador()
                            campo2 = x.preguntaencuesta.orden.__str__() +' '+ x.preguntaencuesta.sagpregunta.nombre.__str__()
                            campo3 = x.indicador.nombreindicador()
                            campo4 = r
                            campo5 = carrera.nombre_completo()
                            ws.write(row_num, 0, campo5, font_style2)
                            ws.write(row_num, 1, campo1, font_style2)
                            ws.write(row_num, 2, campo2, font_style2)
                            ws.write(row_num, 3, campo3, font_style2)
                            ws.write(row_num, 4, campo4, font_style2)
                            row_num += 1
                    wb.save(response)
                    return response
                except Exception as ex:
                    pass

            elif action == 'resultadosindicadorproyecto':
                try:
                    data = {}
                    pe12 = None
                    data['idcarr'] = idcarr = int(request.GET['idcarr'])
                    data['periodo'] = periodo=SagPeriodo.objects.get(pk=int(request.GET['idperiodo']))
                    data['opc'] = opc = int(request.GET['opc'])
                    data['estadocivil'] =estadocivil= PersonaEstadoCivil.objects.filter(status=True)
                    data['genero'] =genero= Sexo.objects.filter(status=True)
                    data['nivel'] =nivel= NivelTitulacion.objects.filter(status=True)
                    data['carrera'] =carrera= Carrera.objects.get(pk=idcarr)
                    data['indiproyc'] = indiproyc=SagIndicadorEncuesta.objects.filter(Q(indicador__codigo__icontains='C'),
                                                                                      status=True,
                                                                                      indicador__vigente=True).order_by(
                        "indicador__codigo")
                    data['indiproye'] =indiproye= SagIndicadorEncuesta.objects.filter(Q(indicador__codigo__icontains='E'),
                                                                                      status=True,
                                                                                      indicador__vigente=True).exclude(
                        Q(indicador__codigo__icontains='PE')).order_by("indicador__codigo")
                    data['indiproype'] =indiproype= SagIndicadorEncuesta.objects.filter(Q(indicador__codigo__icontains='PE'),
                                                                                        status=True,
                                                                                        indicador__vigente=True).exclude(
                        Q(indicador__codigo__icontains='PE11') | Q(indicador__codigo__icontains='PE12')).order_by(
                        "indicador__codigo")
                    data['indiproypr'] =indiproypr= SagIndicadorEncuesta.objects.filter(Q(indicador__codigo__icontains='PR'),
                                                                                        status=True,
                                                                                        indicador__vigente=True).order_by(
                        "indicador__codigo")
                    data['indiproype11'] =indiproype11= SagIndicadorEncuesta.objects.filter(
                        Q(indicador__codigo__icontains='PE11'), status=True, indicador__vigente=True).order_by(
                        "preguntaencuesta__orden")
                    if opc == 1:
                        template = get_template("sagadministracion/resultadosindicadorproyecto.html")
                        json_content = template.render(data)
                        return JsonResponse({"result": "ok", 'html': json_content})
                    elif opc == 2:
                        data['nombperiodo'] = nombperiodo = request.GET['nombperiodo']
                        return conviert_html_to_pdf('sagadministracion/informe_indicadorproyecto_pdf.html',
                                                    {'pagesize': 'A4', 'data': data, 'indiproyc': indiproyc,
                                                     'indiproye': indiproye, 'indiproype': indiproype,
                                                     'indiproypr': indiproypr, 'indiproype11': indiproype11,
                                                     'idcarr': idcarr, 'carrera': carrera,'estadocivil':estadocivil,
                                                     'nombperiodo': nombperiodo,'genero':genero,'nivel':nivel,'periodo':periodo})

                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

            elif action == 'resultadosmejoracontinua':
                try:
                    data = {}
                    pe12 = None
                    data['idcarr'] = idcarr = int(request.GET['idcarr'])
                    data['opc'] = opc = int(request.GET['opc'])
                    data['carrera'] =carrera= Carrera.objects.get(pk=idcarr)
                    data['mejorac'] = mejorac=SagIndicadorEncuesta.objects.filter(Q(indicador__codigo__icontains='C12'),
                                                                                  status=True,
                                                                                  indicador__vigente=True).order_by(
                        "indicador__codigo")
                    data['mejorae'] =mejorae= SagIndicadorEncuesta.objects.filter(Q(indicador__id=8) | Q(indicador__id=10),
                                                                                  status=True,
                                                                                  indicador__vigente=True).order_by(
                        "indicador__codigo")
                    data['mejorape'] =mejorape= SagIndicadorEncuesta.objects.filter(Q(indicador__codigo__icontains='PE'),
                                                                                    status=True,
                                                                                    indicador__vigente=True).exclude(
                        Q(indicador__codigo__icontains='PE11') | Q(indicador__codigo__icontains='PE12')).order_by(
                        "indicador__codigo")
                    data['mejorapr'] =mejorapr= SagIndicadorEncuesta.objects.filter(Q(indicador__codigo__icontains='PR'),
                                                                                    status=True,
                                                                                    indicador__vigente=True).order_by(
                        "indicador__codigo")
                    data['mejorape11'] =mejorape11= SagIndicadorEncuesta.objects.filter(
                        Q(indicador__codigo__icontains='PE11'), status=True, indicador__vigente=True).order_by(
                        "preguntaencuesta__orden")
                    encuestacarrera = SagEncuestaCarrera.objects.filter(carrera__id=idcarr, status=True).exclude(sagecuesta__id=1)
                    todo = None
                    if encuestacarrera.__len__() > 0:
                        for x in encuestacarrera:
                            pe12 = SagIndicadorEncuesta.objects.filter(Q(indicador__codigo__icontains='PE12'),
                                                                       status=True, indicador__vigente=True,
                                                                       preguntaencuesta__sagencuesta=x.sagecuesta).order_by("indicador__codigo")
                            if todo:
                                todo = list(chain(todo, pe12))
                            else:
                                todo = pe12
                    data['mejorape12'] = todo
                    if opc == 1:
                        template = get_template("sagadministracion/resultadosmejoracontinua.html")
                        json_content = template.render(data)
                        return JsonResponse({"result": "ok", 'html': json_content})
                    elif opc == 2:
                        data['nombperiodo'] = nombperiodo = request.GET['nombperiodo']
                        return conviert_html_to_pdf('sagadministracion/informe_mejoracontinua_pdf.html',
                                                    {'pagesize': 'A4', 'data': data, 'mejorac': mejorac,
                                                     'mejorae': mejorae, 'mejorape': mejorape,
                                                     'mejorapr': mejorapr, 'mejorape11': mejorape11,
                                                     'mejorape12': todo, 'idcarr': idcarr, 'carrera': carrera,
                                                     'nombperiodo': nombperiodo})

                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

            elif action == 'resultadosunemiempleo':
                try:
                    data = {}
                    pe12 = None
                    data['idcarr'] = idcarr = int(request.GET['idcarr'])
                    data['carrera'] = carrera=Carrera.objects.get(pk=idcarr)
                    data['opc'] = opc = int(request.GET['opc'])
                    data['unemiec'] =unemiec= SagIndicadorEncuesta.objects.filter(
                        Q(indicador__codigo__icontains='C5') | Q(indicador__codigo__icontains='C6') | Q(
                            indicador__codigo__icontains='C11'), status=True, indicador__vigente=True).order_by(
                        "indicador__codigo")
                    data['unemiee'] = unemiee=SagIndicadorEncuesta.objects.filter(Q(indicador__codigo__icontains='E'),
                                                                                  status=True, indicador__vigente=True).exclude(
                        Q(indicador__codigo__icontains='PE')).order_by("indicador__codigo")
                    data['unemiepe'] = unemiepe=SagIndicadorEncuesta.objects.filter(
                        Q(indicador__codigo__icontains='PE2') | Q(indicador__codigo__icontains='PE3'), status=True,
                        indicador__vigente=True).order_by("indicador__codigo")
                    data['unemiepr'] = unemiepr=SagIndicadorEncuesta.objects.filter(Q(indicador__codigo__icontains='PR'),
                                                                                    status=True,
                                                                                    indicador__vigente=True).order_by(
                        "indicador__codigo")
                    data['unemiepe11'] = unemiepe11=SagIndicadorEncuesta.objects.filter(
                        Q(indicador__codigo__icontains='PE11'), status=True, indicador__vigente=True).order_by(
                        "preguntaencuesta__orden")
                    encuestacarrera = SagEncuestaCarrera.objects.filter(carrera__id=idcarr, status=True).exclude(
                        sagecuesta__id=1)
                    todo = None
                    if encuestacarrera.__len__() > 0:
                        for x in encuestacarrera:
                            pe12 = SagIndicadorEncuesta.objects.filter(Q(indicador__codigo__icontains='PE12'),
                                                                       status=True, indicador__vigente=True,
                                                                       preguntaencuesta__sagencuesta=x.sagecuesta).order_by(
                                "indicador__codigo")
                            if todo:
                                todo = list(chain(todo, pe12))
                            else:
                                todo = pe12
                    data['unemiepe12'] = todo
                    if opc == 1:
                        template = get_template("sagadministracion/resultadosunemiempleo.html")
                        json_content = template.render(data)
                        return JsonResponse({"result": "ok", 'html': json_content})
                    elif opc == 2:
                        data['nombperiodo'] = nombperiodo = request.GET['nombperiodo']
                        return conviert_html_to_pdf('sagadministracion/informe_unemiempleo_pdf.html',
                                                    {'pagesize': 'A4', 'data': data, 'unemiec': unemiec,
                                                     'unemiee': unemiee, 'unemiepe': unemiepe,
                                                     'unemiepr': unemiepr, 'unemiepe11': unemiepe11,
                                                     'unemiepe12': todo, 'idcarr': idcarr, 'carrera': carrera,
                                                     'nombperiodo': nombperiodo})
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

            elif action == 'resultadosunemiformacioncontinua':
                try:
                    data = {}
                    pe12 = None
                    data['idcarr'] = idcarr = int(request.GET['idcarr'])
                    data['opc'] = opc = int(request.GET['opc'])
                    data['carrera'] = carrera=Carrera.objects.get(pk=idcarr)
                    data['formconc'] =formconc= SagIndicadorEncuesta.objects.filter(
                        Q(indicador__codigo__icontains='C4') | Q(indicador__codigo__icontains='C5'), status=True,
                        indicador__vigente=True).order_by("indicador__codigo")
                    data['formcone'] = formcone=SagIndicadorEncuesta.objects.filter(
                        Q(indicador__codigo__icontains='E2') | Q(indicador__codigo__icontains='E5') | Q(
                            indicador__codigo__icontains='E9') | Q(indicador__codigo__icontains='E12') | Q(
                            indicador__codigo__icontains='E13') | Q(indicador__codigo__icontains='E14'), status=True,
                        indicador__vigente=True).exclude(Q(indicador__codigo__icontains='PE')).order_by(
                        "indicador__codigo")
                    data['formconpe11'] = formconpe11=SagIndicadorEncuesta.objects.filter(Q(indicador__codigo__icontains='PE11'),
                                                                                          status=True,
                                                                                          indicador__vigente=True).order_by(
                        "preguntaencuesta__orden")
                    encuestacarrera = SagEncuestaCarrera.objects.filter(carrera__id=idcarr, status=True).exclude(
                        sagecuesta__id=1)
                    todo = None
                    if encuestacarrera.__len__() > 0:
                        for x in encuestacarrera:
                            pe12 = SagIndicadorEncuesta.objects.filter(Q(indicador__codigo__icontains='PE12'),
                                                                       status=True, indicador__vigente=True,
                                                                       preguntaencuesta__sagencuesta=x.sagecuesta).order_by(
                                "preguntaencuesta__orden")
                            if todo:
                                todo = list(chain(todo, pe12))
                            else:
                                todo = pe12
                    data['formconpe12'] = todo
                    data['formconpr'] = formconpr=SagIndicadorEncuesta.objects.filter(Q(indicador__codigo__icontains='PR'),
                                                                                      status=True,
                                                                                      indicador__vigente=True).order_by(
                        "indicador__codigo")
                    if opc == 1:
                        template = get_template("sagadministracion/resultadosunemiformacioncontinua.html")
                        json_content = template.render(data)
                        return JsonResponse({"result": "ok", 'html': json_content})
                    elif opc == 2:
                        data['nombperiodo'] = nombperiodo = request.GET['nombperiodo']
                        return conviert_html_to_pdf('sagadministracion/informe_formacioncontinua_pdf.html',
                                                    {'pagesize': 'A4', 'data': data, 'formconc': formconc,
                                                     'formcone': formcone,'formconpr': formconpr, 'formconpe11': formconpe11,
                                                     'formconpe12': todo, 'idcarr': idcarr, 'carrera': carrera,
                                                     'nombperiodo': nombperiodo})
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

            elif action == 'listareportes':
                try:
                    data['title'] = u'Reportes'
                    data['periodoe'] =periodo = SagPeriodo.objects.get(id=int(request.GET['idperiodo']))
                    feini = None
                    fefin = None
                    data['fechainicio'] = feini if feini else ""
                    data['fechafin'] = fefin if fefin else ""
                    data['facultades'] = Coordinacion.objects.filter(status=True, alias__icontains='FA')
                    data['carreras'] = Carrera.objects.filter(status=True, coordinacion__excluir=False)
                    data['encuestas'] = SagEncuesta.objects.filter(status=True,sagperiodo=periodo).order_by('orden')
                    data['grupos'] = SagGrupoPregunta.objects.filter(status=True).order_by('orden')
                    return render(request, "sagadministracion/reporte_periodo.html", data)
                except Exception as ex:
                    pass

            elif action == 'excelencuestados':
                try:
                    __author__ = 'Unemi'
                    style0 = easyxf('font: name Times New Roman, color-index blue, bold off', num_format_str='#,##0.00')
                    style_nb = easyxf('font: name Times New Roman, color-index blue, bold on', num_format_str='#,##0.00')
                    style_sb = easyxf('font: name Times New Roman, color-index blue, bold on')
                    title = easyxf('font: name Times New Roman, color-index blue, bold on , height 350; alignment: horiz centre')
                    style1 = easyxf(num_format_str='D-MMM-YY')
                    font_style = XFStyle()
                    font_style.font.bold = True
                    font_style2 = XFStyle()
                    font_style2.font.bold = False
                    wb = Workbook(encoding='utf-8')
                    ws = wb.add_sheet('encuestados')
                    # ws.write_merge(0, 0, 0, 10, 'UNIVERSIDAD ESTATAL DE MILAGRO', title)
                    response = HttpResponse(content_type="application/ms-excel")
                    response[
                        'Content-Disposition'] = 'attachment; filename=Encuestados' + random.randint(
                        1, 10000).__str__() + '.xls'

                    columns = [
                        (u"N.", 1500),
                        (u"FACULTAD", 8000),
                        (u"CARRERA", 8000),
                        (u"CEDULA", 3000),
                        (u"APELLIDOS Y NOMBRES", 12000),
                        (u"FECHA ENCUESTA", 3000),
                        (u"TELEFONO", 4000),
                        (u"TELEFONO CONVENCIONAL", 4000),
                        (u"EMAIL", 5000),
                        (u"EMAIL INSTITUCIONAL", 5000),
                        (u"SEXO", 2500),
                        (u"FECHA GRADUACIÓN", 5000),
                        (u"AÑO GRADUACIÓN", 5000),
                        (u"Codigo", 5000),
                    ]
                    row_num = 0
                    for col_num in range(len(columns)):
                        ws.write(row_num, col_num, columns[col_num][0], font_style)
                        ws.col(col_num).width = columns[col_num][1]
                    date_format = xlwt.XFStyle()
                    date_format.num_format_str = 'yyyy/mm/dd'
                    if request.GET['x']=='2':
                        listadoencuestados = SagResultadoEncuesta.objects.select_related().filter(
                            sagperiodo=request.GET['idperiodo'], status=True,inscripcion__graduado__status=True).order_by('-fecha_creacion')
                    else:
                        fechainicio = request.GET['fechainicio'] + ' 00:00'
                        fechafin = request.GET['fechafin'] + ' 23:59:59'
                        if request.GET['fechainicio'] and request.GET['fechafin']:
                            listadoencuestados = SagResultadoEncuesta.objects.select_related().filter(
                                fecha_creacion__gte=fechainicio, fecha_creacion__lte=fechafin,
                                sagperiodo=request.GET['idperiodo'], status=True,inscripcion__graduado__status=True).order_by('-fecha_creacion')
                        else:
                            listadoencuestados = SagResultadoEncuesta.objects.select_related().filter(
                                sagperiodo=request.GET['idperiodo'], status=True,inscripcion__graduado__status=True).order_by('-fecha_creacion')
                    row_num = 1
                    i = 0
                    for listado in listadoencuestados:
                        campo1 = listado.inscripcion.coordinacion.nombre
                        if(listado.inscripcion.carrera.mencion):
                            campo2 = listado.inscripcion.carrera.nombre + ' CON MENCION EN  ' + listado.inscripcion.carrera.mencion
                        else:
                            campo2 = listado.inscripcion.carrera.nombre
                        campo3 = listado.inscripcion.persona.apellido1 + ' ' + listado.inscripcion.persona.apellido2 + ' ' + listado.inscripcion.persona.nombres
                        campo4 = listado.fecha_creacion
                        campo5 = listado.inscripcion.persona.cedula
                        campo6 = listado.inscripcion.persona.telefono
                        campo7 = listado.inscripcion.persona.telefono_conv
                        campo8 = listado.inscripcion.persona.email
                        campo9 = listado.inscripcion.persona.emailinst
                        campo10 = listado.inscripcion.persona.sexo.nombre
                        fechagra = Graduado.objects.filter(inscripcion=listado.inscripcion)[0].fechagraduado if Graduado.objects.filter(inscripcion=listado.inscripcion).exists() else ""
                        campo11 = fechagra
                        campo12 = fechagra.year if fechagra else ""
                        campo13 = listado.inscripcion.id
                        i += 1
                        ws.write(row_num, 0, i, font_style2)
                        ws.write(row_num, 1, campo1, font_style2)
                        ws.write(row_num, 2, campo2, font_style2)
                        ws.write(row_num, 3, campo5, font_style2)
                        ws.write(row_num, 4, campo3, font_style2)
                        ws.write(row_num, 5, campo4, date_format)
                        ws.write(row_num, 6, campo6, font_style2)
                        ws.write(row_num, 7, campo7, font_style2)
                        ws.write(row_num, 8, campo8, font_style2)
                        ws.write(row_num, 9, campo9, font_style2)
                        ws.write(row_num, 10, campo10, font_style2)
                        ws.write(row_num, 11, campo11, date_format)
                        ws.write(row_num, 12, campo12, font_style2)
                        ws.write(row_num, 13, campo13, font_style2)
                        row_num += 1
                    wb.save(response)
                    return response
                except Exception as ex:
                    pass

            elif action == 'excelreportegraduados':
                try:
                    idp = request.GET['idperiodo']
                    __author__ = 'Unemi'
                    style0 = easyxf('font: name Times New Roman, color-index blue, bold off', num_format_str='#,##0.00')
                    style_nb = easyxf('font: name Times New Roman, color-index blue, bold on',
                                      num_format_str='#,##0.00')
                    style_sb = easyxf('font: name Times New Roman, color-index blue, bold on')
                    title = easyxf(
                        'font: name Times New Roman, color-index blue, bold on , height 350; alignment: horiz centre')
                    style1 = easyxf(num_format_str='D-MMM-YY')
                    font_style = XFStyle()
                    font_style.font.bold = True
                    font_style2 = XFStyle()
                    font_style2.font.bold = False
                    wb = Workbook(encoding='utf-8')
                    ws = wb.add_sheet('exp_xls_post_part')
                    ws.write_merge(0, 0, 0, 6, 'UNIVERSIDAD ESTATAL DE MILAGRO', title)
                    response = HttpResponse(content_type="application/ms-excel")
                    response[
                        'Content-Disposition'] = 'attachment; filename=graduados_encuestados_noencuestados' + random.randint(
                        1, 10000).__str__() + '.xls'
                    columns = [
                        (u"No.", 1500),
                        (u"FACULTAD", 6000),
                        (u"CARRERA", 6000),
                        (u"CEDULA", 3000),
                        (u"ALUMNO", 6000),
                        (u"ENCUESTA", 6000),
                        (u"FECHA DE ENCUESTA", 3000),
                        (u"INICIO PRIMER NIVEL", 3000),
                        (u"FECHA GRADUACION", 3000),
                        (u"NOTA FINAL", 6000),
                        (u"PAIS", 6000),
                        (u"PROVINCIA", 6000),
                        (u"CANTON", 6000),
                        (u"PARROQUIA", 6000),
                        (u"CALLE PRINCIPAL", 6000),
                        (u"CALLE SECUNDARIA", 6000),
                        (u"EMAIL", 6000),
                        (u"EMAIL INSTITUCIONAL", 6000),
                        (u"TELEFONO", 4000),
                        (u"TELEFONO CONVENCIONAL", 4000),
                        (u"SEXO", 6000),
                        (u"LGBTI", 3000),
                        (u"INICIO CONVALIDACION", 3000)
                    ]
                    row_num = 3
                    for col_num in range(len(columns)):
                        ws.write(row_num, col_num, columns[col_num][0], font_style)
                        ws.col(col_num).width = columns[col_num][1]
                    cursor = connection.cursor()
                    date_format = xlwt.XFStyle()
                    date_format.num_format_str = 'yyyy/mm/dd'
                    sql = "select co.nombre as Facultad, (ca.nombre||' '||ca.mencion) as Carrera,  " \
                          "p.cedula,(p.apellido1||' '||p.apellido2||' '||p.nombres) as alumno,  " \
                          "(case when res.fecha_creacion IS NULL  then 'NO ENCUESTADO' else 'ENCUESTADO' end) as encuestado,  " \
                          "res.fecha_creacion as fechaencuesta,i.fechainicioprimernivel,gr.fechagraduado, gr.notafinal, " \
                          "(select nombre from sga_pais where id=p.pais_id) as pais, (select nombre from sga_provincia where id=p.provincia_id) as provincia, " \
                          "(select nombre from sga_canton where id=p.canton_id) as canton,(select nombre from sga_parroquia where id=p.parroquia_id) as parroquia, " \
                          "p.direccion,p.direccion2,p.email,p.emailinst,p.telefono,p.telefono_conv, (select nombre from sga_sexo sexo where sexo.id=p.sexo_id ) as sexo, " \
                          "p.lgtbi,i.fechainicioconvalidacion " \
                          "from sga_persona p  join sga_inscripcion i on i.persona_id=p.id " \
                          "join sga_graduado gr on gr.inscripcion_id=i.id " \
                          "join sga_carrera ca on i.carrera_id=ca.id " \
                          "join sga_coordinacion_carrera cc on cc.carrera_id=ca.id " \
                          "join sga_coordinacion co on co.id = cc.coordinacion_id left join sga_sagresultadoencuesta res on res.inscripcion_id=i.id  " \
                          " and res.sagperiodo_id="  + idp +\
                          " where co.id not in(7)order by co.nombre,ca.nombre,gr.fechagraduado "
                    cursor.execute(sql)
                    results = cursor.fetchall()
                    row_num = 4
                    i = 0
                    for r in results:
                        campo1 = r[0]
                        campo2 = r[1]
                        campo3 = r[2]
                        campo4 = r[3]
                        campo5 = r[4]
                        if r[5]:
                            campo6 = r[5]
                        else:
                            campo6 = ''
                        campo7 = r[6]
                        campo8 = r[7]
                        campo9 = r[8]
                        campo10 = r[9]
                        campo11 = r[10]
                        campo12 = r[11]
                        campo13 = r[12]
                        campo14 = r[13]
                        campo15 = r[14]
                        campo16 = r[15]
                        campo17 = r[16]
                        campo18 = r[17]
                        campo19 = r[18]
                        campo20 = r[19]
                        if r[20]:
                            campo21 = 'SI'
                        else:
                            campo21 = 'NO'
                        campo22 = r[21]
                        i += 1
                        ws.write(row_num, 0, i, font_style2)
                        ws.write(row_num, 1, campo1, font_style2)
                        ws.write(row_num, 2, campo2, font_style2)
                        ws.write(row_num, 3, campo3, font_style2)
                        ws.write(row_num, 4, campo4, font_style2)
                        ws.write(row_num, 5, campo5, font_style2)
                        ws.write(row_num, 6, campo6, style1)
                        ws.write(row_num, 7, campo7, date_format)
                        ws.write(row_num, 8, campo8, style1)
                        ws.write(row_num, 9, campo9, font_style2)
                        ws.write(row_num, 10, campo10, font_style2)
                        ws.write(row_num, 11, campo11, font_style2)
                        ws.write(row_num, 12, campo12, font_style2)
                        ws.write(row_num, 13, campo13, font_style2)
                        ws.write(row_num, 14, campo14, font_style2)
                        ws.write(row_num, 15, campo15, font_style2)
                        ws.write(row_num, 16, campo16, font_style2)
                        ws.write(row_num, 17, campo17, font_style2)
                        ws.write(row_num, 18, campo18, font_style2)
                        ws.write(row_num, 19, campo19, font_style2)
                        ws.write(row_num, 20, campo20, font_style2)
                        ws.write(row_num, 21, campo21, font_style2)
                        ws.write(row_num, 22, campo22, date_format)
                        row_num += 1
                    wb.save(response)
                    connection.close()
                    return response
                except Exception as ex:
                    pass

            elif action == 'resultadoencuesta':
                try:
                    idp = request.GET['idperiodo']
                    __author__ = 'Unemi'
                    style0 = easyxf('font: name Times New Roman, color-index blue, bold off', num_format_str='#,##0.00')
                    style_nb = easyxf('font: name Times New Roman, color-index blue, bold on',
                                      num_format_str='#,##0.00')
                    style_sb = easyxf('font: name Times New Roman, color-index blue, bold on')
                    title = easyxf(
                        'font: name Times New Roman, color-index blue, bold on , height 350; alignment: horiz centre')
                    style1 = easyxf(num_format_str='D-MMM-YY')
                    font_style = XFStyle()
                    font_style.font.bold = True
                    font_style2 = XFStyle()
                    font_style2.font.bold = False
                    wb = Workbook(encoding='utf-8')
                    coordinaciones=Coordinacion.objects.filter(status=True, excluir=False)
                    for x in coordinaciones:
                        for c in Carrera.objects.filter(status=True, coordinacion=x).order_by('nombre'):
                            cursor = connection.cursor()
                            sql = "select coor.nombre as facultad, carr.nombre AS carrera,  CASE WHEN carr.mencion!='' THEN carr.mencion ELSE '' END as mencion, " \
                                  " cab.fecha_creacion as fechaencuesta,gra.fechagraduado,sexo.nombre as sexo,per.cedula,  per.apellido1 || ' ' || per.apellido2 || ' ' || per.nombres as nombres, " \
                                  " encu.nombre as encuesta,pren.orden,preg.nombre as pregunta,pregti.nombre as tipopregunta,   det.valor as respuesta,pregti.id as tipo,  " \
                                  " (select ite.nombre from sga_sagencuestaitem ite   where ite.preguntaencuesta_id=pren.id and pren.tipo_id in(2,4)  and pren.id=det.preguntaencuesta_id " \
                                  "and ite.id=cast(det.valor as numeric)) as respuesta_seleccionada ,det.numero as matriz  " \
                                  " from sga_sagresultadoencuestadetalle det  left join sga_sagresultadoencuesta cab on cab.id=det.sagresultadoencuesta_id  " \
                                  " left join sga_inscripcion ins on ins.id=cab.inscripcion_id   left join sga_coordinacion coor on coor.id=ins.coordinacion_id  " \
                                  "left join sga_carrera carr on carr.id=ins.carrera_id  left join sga_persona per on per.id=ins.persona_id  " \
                                  " left join sga_sagpreguntaencuesta pren on pren.id=det.preguntaencuesta_id  left join sga_sagencuesta encu on encu.id=pren.sagencuesta_id  " \
                                  " left join sga_sagpregunta preg on preg.id=pren.sagpregunta_id   left join sga_sagpreguntatipo pregti on pregti.id=pren.tipo_id  " \
                                  "left join sga_sexo sexo on sexo.id=per.sexo_id   left join sga_graduado gra on gra.inscripcion_id=ins.id  " \
                                  " where det.status=True and coor.id not in(7) and cab.status=True  and  coor.id= " + str(x.id) + " and carr.id=" + str(c.id) + " and cab.sagperiodo_id= " + idp + "  order by per.apellido1,pren.orden "
                            cursor.execute(sql)
                            results = cursor.fetchall()
                            if results:
                                pest=c.alias+" "+str(c.id)
                                ws = wb.add_sheet(pest)
                                response = HttpResponse(content_type="application/ms-excel")
                                response[
                                    'Content-Disposition'] = 'attachment; filename=resultados_encuesta' + random.randint(
                                    1, 10000).__str__() + '.xls'
                                columns = [
                                    (u"No.", 1500),
                                    (u"FACULTAD", 6000),
                                    (u"CARRERA", 6000),
                                    (u"FECHA ENCUESTA", 3000),
                                    (u"FECHA GRADUADO", 3000),
                                    (u"SEXO", 3000),
                                    (u"CÉDULA", 3000),
                                    (u"NOMBRES", 6000),
                                    (u"ENCUESTA", 6000),
                                    (u"ORDEN", 2000),
                                    (u"PREGUNTA", 6000),
                                    (u"TIPO PREGUNTA", 3000),
                                    (u"RESPUESTA", 3000),
                                    (u"TIPO", 6000),
                                    (u"RESPUESTA SELECCIONADA", 6000)
                                ]
                                row_num = 1
                                for col_num in range(len(columns)):
                                    ws.write(row_num, col_num, columns[col_num][0], font_style)
                                    ws.col(col_num).width = columns[col_num][1]
                                date_format = xlwt.XFStyle()
                                date_format.num_format_str = 'yyyy/mm/dd'
                                row_num = 2
                                i = 0
                                for r in results:
                                    campo1 = r[0]
                                    campo2 = r[1] + ' ' + r[2]
                                    campo3 = r[3]
                                    campo4 = r[4]
                                    campo5 = r[5]
                                    campo6 = r[6]
                                    campo7 = r[7]
                                    campo8 = r[8]
                                    campo9 = r[9]
                                    campo10 = r[10]
                                    campo11 = r[11]
                                    campo12 = r[12]
                                    campo13 = r[13]
                                    campo14 = r[14]
                                    i += 1
                                    ws.write(row_num, 0, i, font_style2)
                                    ws.write(row_num, 1, campo1, font_style2)
                                    ws.write(row_num, 2, campo2, font_style2)
                                    ws.write(row_num, 3, campo3, date_format)
                                    ws.write(row_num, 4, campo4, date_format)
                                    ws.write(row_num, 5, campo5, font_style2)
                                    ws.write(row_num, 6, campo6, font_style2)
                                    ws.write(row_num, 7, campo7, font_style2)
                                    ws.write(row_num, 8, campo8, font_style2)
                                    ws.write(row_num, 9, campo9, font_style2)
                                    ws.write(row_num, 10, campo10, font_style2)
                                    ws.write(row_num, 11, campo11, font_style2)
                                    ws.write(row_num, 12, campo12, font_style2)
                                    ws.write(row_num, 13, campo13, font_style2)
                                    ws.write(row_num, 14, campo14, font_style2)
                                    row_num += 1
                    wb.save(response)
                    connection.close()
                    return response
                except Exception as ex:
                    pass

            elif action == 'resultadoencuestageneral':
                try:
                    idp = request.GET['idperiodo']
                    __author__ = 'Unemi'
                    style0 = easyxf('font: name Times New Roman, color-index blue, bold off', num_format_str='#,##0.00')
                    style_nb = easyxf('font: name Times New Roman, color-index blue, bold on', num_format_str='#,##0.00')
                    style_sb = easyxf('font: name Times New Roman, color-index blue, bold on')
                    title = easyxf('font: name Times New Roman, color-index blue, bold on , height 350; alignment: horiz centre')
                    style1 = easyxf(num_format_str='D-MMM-YY')
                    font_style = XFStyle()
                    font_style.font.bold = True
                    font_style2 = XFStyle()
                    font_style2.font.bold = False
                    # bordes
                    borders = Borders()
                    borders.left = 1
                    borders.right = 1
                    borders.top = 1
                    borders.bottom = 1
                    title = easyxf('font: name Arial, bold on , height 200; alignment: horiz centre')
                    subtitle = easyxf('font: name Arial, bold on , height 150; alignment: horiz centre')
                    normaliz = easyxf('font: name Arial , height 150; align: wrap on,horiz left ')
                    nnormal = easyxf('font: name Arial, bold on , height 150; align: wrap on,horiz right')
                    normal = easyxf('font: name Arial , height 150; align: wrap on,horiz center ')
                    stylebnotas = easyxf('font: name Arial, bold on , height 150; alignment: horiz centre')
                    stylebnombre = easyxf('font: name Arial, bold on , height 150; align: wrap on, horiz left')
                    stylebnotas.borders = borders
                    wb = Workbook(encoding='utf-8')
                    coordinaciones=Coordinacion.objects.filter(status=True, excluir=False)
                    cursor = connection.cursor()
                    for x in coordinaciones:
                        for c in Carrera.objects.filter(status=True, coordinacion=x).order_by('nombre'):
                            preguntas_aux = SagPreguntaEncuesta.objects.filter(status=True, sagencuesta__sagperiodo__id=int(idp) , sagencuesta__sagencuestacarrera__carrera_id=c.id, sagencuesta__status=True).distinct().order_by('orden','id')
                            preguntas = []
                            cantidadp = 0
                            for pre1 in preguntas_aux:
                                preguntas.append([pre1.sagpregunta.nombre, pre1.id,pre1.orden,pre1.sagencuesta.nombre])
                                cantidadp += 1
                                if 'matriz 2' in pre1.tipo.nombre:
                                    preguntas.append([pre1.sagpregunta.nombre, pre1.id, pre1.orden,pre1.sagencuesta.nombre])
                                    cantidadp += 1
                            sql=""
                            lista=[]
                            sql = "select coor.nombre as facultad, carr.nombre AS carrera,  CASE WHEN carr.mencion!='' THEN carr.mencion ELSE '' END as mencion, " \
                                  " cab.fecha_creacion as fechaencuesta,gra.fechagraduado,sexo.nombre as sexo,per.cedula,  per.apellido1 || ' ' || per.apellido2 || ' ' || per.nombres as nombres, " \
                                  " encu.nombre as encuesta,pren.orden,preg.nombre as pregunta,pregti.nombre as tipopregunta,   det.valor as respuesta,pregti.id as tipo,  " \
                                  " (select ite.nombre from sga_sagencuestaitem ite   where ite.preguntaencuesta_id=pren.id and pren.tipo_id in(2,4)  and pren.id=det.preguntaencuesta_id " \
                                  "and ite.id=cast(det.valor as numeric)) as respuesta_seleccionada ,det.numero as matriz,pren.id  " \
                                  " from sga_sagresultadoencuestadetalle det  left join sga_sagresultadoencuesta cab on cab.id=det.sagresultadoencuesta_id  " \
                                  " left join sga_inscripcion ins on ins.id=cab.inscripcion_id   left join sga_coordinacion coor on coor.id=ins.coordinacion_id  " \
                                  "left join sga_carrera carr on carr.id=ins.carrera_id  left join sga_persona per on per.id=ins.persona_id  " \
                                  " left join sga_sagpreguntaencuesta pren on pren.id=det.preguntaencuesta_id  left join sga_sagencuesta encu on encu.id=pren.sagencuesta_id  " \
                                  " left join sga_sagpregunta preg on preg.id=pren.sagpregunta_id   left join sga_sagpreguntatipo pregti on pregti.id=pren.tipo_id  " \
                                  "left join sga_sexo sexo on sexo.id=per.sexo_id   left join sga_graduado gra on gra.inscripcion_id=ins.id  " \
                                  " where det.status=True and coor.id not in(7)  and cab.status=True  and  coor.id= " + str(x.id) + " and carr.id=" + str(c.id) + " and cab.sagperiodo_id= " + idp + "  order by nombres,pren.orden, pren.id "
                            cursor.execute(sql)
                            results = cursor.fetchall()
                            cc = 1
                            # cantidadp = preguntas.count()
                            arregloorden = []
                            for pre in preguntas:
                                arregloorden.append([pre[1], pre[2]])
                            variable=[]
                            ccaux = 0
                            for re in results:
                                while ccaux <= cantidadp-1:
                                    if re[16] == arregloorden[ccaux][0] and re[9] == arregloorden[ccaux][1]:
                                        ccaux += 1
                                        ccaux2 = ccaux
                                        ccaux = cantidadp + 1
                                        # variable.append([re[9],re[14]])
                                        variable.append([re[14]])
                                    else:
                                        ccaux += 1
                                        ccaux2 = ccaux
                                        variable.append([''])
                                ccaux = ccaux2

                                if ccaux > cantidadp-1:
                                    lista.append([re[0], re[1], re[3], re[4], re[5], re[6], re[7], re[8],variable])
                                    cc=0
                                    ccaux = 0
                                    variable=[]
                                cc += 1

                            if lista:
                                pest=c.alias+" "+str(c.id)
                                ws = wb.add_sheet(pest)
                                response = HttpResponse(content_type="application/ms-excel")
                                response['Content-Disposition'] = 'attachment; filename=resultados_encuesta_general' + random.randint(1, 10000).__str__() + '.xls'
                                fila = 1
                                ws.write(fila, 0, 'No', stylebnotas)
                                ws.write(fila, 1, 'FACULTAD', stylebnotas)
                                ws.write(fila, 2, 'CARRERA', stylebnotas)
                                ws.write(fila, 3, 'FECHA ENCUESTA', stylebnotas)
                                ws.write(fila, 4, 'FECHA GRADUADO', stylebnotas)
                                ws.write(fila, 5, 'SEXO', stylebnotas)
                                ws.write(fila, 6, 'CÉDULA', stylebnotas)
                                ws.write(fila, 7, 'NOMBRES', stylebnotas)
                                ws.write(fila, 8, 'ENCUESTA', stylebnotas)
                                cc = 9
                                veces = 0
                                for pre in preguntas:
                                    if cc < 256:
                                        ws.write(fila, cc, pre[0], stylebnotas)
                                        nombreencuesta = pre[3]
                                        veces += 1
                                    cc += 1
                                row_num = 1
                                date_format = xlwt.XFStyle()
                                date_format.num_format_str = 'yyyy/mm/dd'
                                row_num = 2
                                i = 0
                                for r in lista:
                                    campo1 = r[0]
                                    campo2 = r[1]
                                    campo3 = r[2]
                                    campo4 = r[3]
                                    campo5 = r[4]
                                    campo6 = r[5]
                                    campo7 = r[6]
                                    campo8 = nombreencuesta
                                    i += 1
                                    ws.write(row_num, 0, i, font_style2)
                                    ws.write(row_num, 1, campo1, font_style2)
                                    ws.write(row_num, 2, campo2, font_style2)
                                    ws.write(row_num, 3, campo3, date_format)
                                    ws.write(row_num, 4, campo4, date_format)
                                    ws.write(row_num, 5, campo5, font_style2)
                                    ws.write(row_num, 6, campo6, font_style2)
                                    ws.write(row_num, 7, campo7, font_style2)
                                    ws.write(row_num, 8, campo8, font_style2)
                                    tt = 0
                                    # for pre in preguntas:
                                    #     ws.write(row_num, tt + 9, v, font_style2)
                                    #     tt += 1
                                    for v in r[8]:
                                        ws.write(row_num, tt+9, v[0], font_style2)
                                        tt += 1
                                    row_num += 1
                            lista = []
                    wb.save(response)
                    connection.close()
                    return response
                except Exception as ex:
                    pass


            elif action == 'resultadoencuestageneral2':
                try:
                    idp = request.GET['idperiodo']
                    __author__ = 'Unemi'
                    style0 = easyxf('font: name Times New Roman, color-index blue, bold off', num_format_str='#,##0.00')
                    style_nb = easyxf('font: name Times New Roman, color-index blue, bold on', num_format_str='#,##0.00')
                    style_sb = easyxf('font: name Times New Roman, color-index blue, bold on')
                    title = easyxf('font: name Times New Roman, color-index blue, bold on , height 350; alignment: horiz centre')
                    style1 = easyxf(num_format_str='D-MMM-YY')
                    font_style = XFStyle()
                    font_style.font.bold = True
                    font_style2 = XFStyle()
                    font_style2.font.bold = False
                    # bordes
                    borders = Borders()
                    borders.left = 1
                    borders.right = 1
                    borders.top = 1
                    borders.bottom = 1
                    title = easyxf('font: name Arial, bold on , height 200; alignment: horiz centre')
                    subtitle = easyxf('font: name Arial, bold on , height 150; alignment: horiz centre')
                    normaliz = easyxf('font: name Arial , height 150; align: wrap on,horiz left ')
                    nnormal = easyxf('font: name Arial, bold on , height 150; align: wrap on,horiz right')
                    normal = easyxf('font: name Arial , height 150; align: wrap on,horiz center ')
                    stylebnotas = easyxf('font: name Arial, bold on , height 150; alignment: horiz centre')
                    stylebnombre = easyxf('font: name Arial, bold on , height 150; align: wrap on, horiz left')
                    stylebnotas.borders = borders
                    wb = Workbook(encoding='utf-8')
                    coordinaciones=Coordinacion.objects.filter(status=True, excluir=False)
                    cursor = connection.cursor()
                    for x in coordinaciones:
                        for c in Carrera.objects.filter(status=True, coordinacion=x).order_by('nombre'):
                            preguntas_aux = SagPreguntaEncuesta.objects.filter(status=True, sagencuesta__sagperiodo__id=int(idp) , sagencuesta__sagencuestacarrera__carrera_id=c.id, sagencuesta__status=True).distinct().order_by('orden','id')
                            preguntas = []
                            cantidadp = 0
                            for pre1 in preguntas_aux:
                                preguntas.append([pre1.sagpregunta.nombre, pre1.id,pre1.orden,pre1.sagencuesta.nombre,pre1.tipo.numeromatriz])
                                cantidadp += 1
                                # if 'matriz 2' in pre1.tipo.nombre:
                                #     preguntas.append([pre1.sagpregunta.nombre, pre1.id, pre1.orden,pre1.sagencuesta.nombre,pre1.tipo.numeromatriz])
                                #     cantidadp += 1
                            sql=""
                            lista=[]
                            listaverifica=[]
                            sql = "select * from( select coor.nombre as facultad, carr.nombre AS carrera,  " \
                                  "CASE WHEN carr.mencion!='' THEN carr.mencion ELSE '' END as mencion,  " \
                                  "cab.fecha_creacion as fechaencuesta,gra.fechagraduado,sexo.nombre as sexo,per.cedula, " \
                                  " per.apellido1 || ' ' || per.apellido2 || ' ' || per.nombres as nombres,  encu.nombre as encuesta," \
                                  " pren.orden,preg.nombre as pregunta,pregti.nombre as tipopregunta,   det.valor as respuesta," \
                                  " pregti.id as tipo,   (select ite.nombre from sga_sagencuestaitem ite   " \
                                  " where ite.preguntaencuesta_id=pren.id and pren.tipo_id in(2,4)  and pren.id=det.preguntaencuesta_id " \
                                  " and ite.id=cast(det.valor as numeric)) as respuesta_seleccionada ,det.numero as matriz,pren.id  " \
                                  " from sga_sagresultadoencuestadetalle det  " \
                                  " left join sga_sagresultadoencuesta cab on cab.id=det.sagresultadoencuesta_id   " \
                                  " left join sga_inscripcion ins on ins.id=cab.inscripcion_id   " \
                                  " left join sga_coordinacion coor on coor.id=ins.coordinacion_id  " \
                                  " left join sga_carrera carr on carr.id=ins.carrera_id  " \
                                  " left join sga_persona per on per.id=ins.persona_id   " \
                                  " left join sga_sagpreguntaencuesta pren on pren.id=det.preguntaencuesta_id  " \
                                  " left join sga_sagencuesta encu on encu.id=pren.sagencuesta_id   " \
                                  " left join sga_sagpregunta preg on preg.id=pren.sagpregunta_id   " \
                                  " left join sga_sagpreguntatipo pregti on pregti.id=pren.tipo_id  " \
                                  " left join sga_sexo sexo on sexo.id=per.sexo_id   " \
                                  " left join sga_graduado gra on gra.inscripcion_id=ins.id   " \
                                  " where det.status=True and coor.id not in(7)   " \
                                  " and cab.status=True   " \
                                  " and  coor.id= " + str(x.id) + " and carr.id=" + str(c.id) + " and cab.sagperiodo_id= " + idp + "  " \
                                  " and pregti.id not in(4,7) " \
                                  " union all " \
                            "  select facultad,carrera,mencion,fechaencuesta,fechagraduado,sexo, " \
                            "       cedula,nombres,encuesta,orden,pregunta,tipopregunta, " \
                            "       '0'::varchar as respuesta,tipo,array_agg(respuesta_seleccionada)::varchar as respuesta_seleccionada,'0'::int matriz,id from ( " \
                            "       select coor.nombre as facultad, carr.nombre AS carrera, " \
                            "       CASE WHEN carr.mencion!='' THEN carr.mencion ELSE '' END as mencion, " \
                            "       cab.fecha_creacion as fechaencuesta,gra.fechagraduado,sexo.nombre as sexo,per.cedula, " \
                            "       per.apellido1 || ' ' || per.apellido2 || ' ' || per.nombres as nombres,  encu.nombre as encuesta, " \
                            "       pren.orden,preg.nombre as pregunta,pregti.nombre as tipopregunta,   det.valor as respuesta, " \
                            "       pregti.id as tipo,   CASE WHEN (select ite.nombre from sga_sagencuestaitem ite " \
                            "       where ite.preguntaencuesta_id=pren.id and pren.tipo_id in(2,4)  and pren.id=det.preguntaencuesta_id " \
                            "       and ite.id=cast(det.valor as numeric)) is null then det.valor " \
                            "       ELSE (select ite.nombre from sga_sagencuestaitem ite " \
                            "       where ite.preguntaencuesta_id=pren.id and pren.tipo_id in(2,4)  and pren.id=det.preguntaencuesta_id " \
                            "       and ite.id=cast(det.valor as numeric)) " \
                            "       END as respuesta_seleccionada ,det.numero as matriz,pren.id " \
                            "       from sga_sagresultadoencuestadetalle det " \
                            "       left join sga_sagresultadoencuesta cab on cab.id=det.sagresultadoencuesta_id " \
                            "       left join sga_inscripcion ins on ins.id=cab.inscripcion_id " \
                            "       left join sga_coordinacion coor on coor.id=ins.coordinacion_id " \
                            "       left join sga_carrera carr on carr.id=ins.carrera_id " \
                            "       left join sga_persona per on per.id=ins.persona_id " \
                            "       left join sga_sagpreguntaencuesta pren on pren.id=det.preguntaencuesta_id " \
                            "       left join sga_sagencuesta encu on encu.id=pren.sagencuesta_id " \
                            "       left join sga_sagpregunta preg on preg.id=pren.sagpregunta_id " \
                            "       left join sga_sagpreguntatipo pregti on pregti.id=pren.tipo_id " \
                            "       left join sga_sexo sexo on sexo.id=per.sexo_id " \
                            "       left join sga_graduado gra on gra.inscripcion_id=ins.id " \
                            "       where det.status=True and coor.id not in(7)" \
                            "       and cab.status=True " \
                            "       and coor.id= " + str(x.id) + " and carr.id=" + str(c.id) + " and cab.sagperiodo_id= " + idp + "  " \
                            "       and pregti.id in(4,7)) as d " \
                                    " group by facultad,carrera,mencion,fechaencuesta,fechagraduado,sexo," \
                                    "cedula,nombres,encuesta,orden,pregunta,tipopregunta, " \
                                    "tipo,id ) as tabla order by nombres,orden, id "
                            cursor.execute(sql)
                            results = cursor.fetchall()
                            cc = 1
                            # cantidadp = preguntas.count()
                            arregloorden = []
                            for pre in preguntas:
                                arregloorden.append([pre[1], pre[2], pre[4]])
                            variable=[]
                            ccaux = 0
                            for re in results:
                                while ccaux <= cantidadp-1:
                                    if re[16] == arregloorden[ccaux][0]  and re[9] == arregloorden[ccaux][1]:
                                        ccaux += 1
                                        ccaux2 = ccaux
                                        ccaux = cantidadp + 1
                                        # variable.append([re[9],re[14]])
                                        if re[13] == 2 or re[13] == 4 or re[13] == 7:
                                            variable.append([re[14]])
                                        else:
                                            variable.append([re[12]])
                                    else:
                                        ccaux += 1
                                        ccaux2 = ccaux
                                        variable.append([''])
                                ccaux = ccaux2

                                if ccaux > cantidadp-1:
                                    if re[6] not in listaverifica:
                                        lista.append([re[0], re[1], re[3], re[4], re[5], re[6], re[7], re[8],variable])
                                    cc=0
                                    ccaux = 0
                                    variable=[]
                                    listaverifica.append( re[6])
                                cc += 1

                            if lista:
                                pest=c.alias+" "+str(c.id)
                                ws = wb.add_sheet(pest)
                                response = HttpResponse(content_type="application/ms-excel")
                                response['Content-Disposition'] = 'attachment; filename=resultados_encuesta_general' + random.randint(1, 10000).__str__() + '.xls'
                                fila = 1
                                ws.write(fila, 0, 'No', stylebnotas)
                                ws.write(fila, 1, 'FACULTAD', stylebnotas)
                                ws.write(fila, 2, 'CARRERA', stylebnotas)
                                ws.write(fila, 3, 'FECHA ENCUESTA', stylebnotas)
                                ws.write(fila, 4, 'FECHA GRADUADO', stylebnotas)
                                ws.write(fila, 5, 'SEXO', stylebnotas)
                                ws.write(fila, 6, 'CÉDULA', stylebnotas)
                                ws.write(fila, 7, 'NOMBRES', stylebnotas)
                                ws.write(fila, 8, 'ENCUESTA', stylebnotas)
                                cc = 9
                                veces = 0
                                for pre in preguntas:
                                    if cc < 256:
                                        ws.write(fila, cc, pre[0], stylebnotas)
                                        nombreencuesta = pre[3]
                                        veces += 1
                                    cc += 1
                                row_num = 1
                                date_format = xlwt.XFStyle()
                                date_format.num_format_str = 'yyyy/mm/dd'
                                row_num = 2
                                i = 0
                                for r in lista:
                                    campo1 = r[0]
                                    campo2 = r[1]
                                    campo3 = r[2]
                                    campo4 = r[3]
                                    campo5 = r[4]
                                    campo6 = r[5]
                                    campo7 = r[6]
                                    campo8 = nombreencuesta
                                    i += 1
                                    ws.write(row_num, 0, i, font_style2)
                                    ws.write(row_num, 1, campo1, font_style2)
                                    ws.write(row_num, 2, campo2, font_style2)
                                    ws.write(row_num, 3, campo3, date_format)
                                    ws.write(row_num, 4, campo4, date_format)
                                    ws.write(row_num, 5, campo5, font_style2)
                                    ws.write(row_num, 6, campo6, font_style2)
                                    ws.write(row_num, 7, campo7, font_style2)
                                    ws.write(row_num, 8, campo8, font_style2)
                                    tt = 0
                                    # for pre in preguntas:
                                    #     ws.write(row_num, tt + 9, v, font_style2)
                                    #     tt += 1
                                    for v in r[8]:
                                        ws.write(row_num, tt+9, v[0], font_style2)
                                        tt += 1
                                    row_num += 1
                            lista = []
                    wb.save(response)
                    connection.close()
                    return response
                except Exception as ex:
                    pass

            elif action == 'resultadoencuestageneralconsolidado':
                try:
                    idp = request.GET['idperiodo']
                    __author__ = 'Unemi'
                    style0 = easyxf('font: name Times New Roman, color-index blue, bold off', num_format_str='#,##0.00')
                    style_nb = easyxf('font: name Times New Roman, color-index blue, bold on', num_format_str='#,##0.00')
                    style_sb = easyxf('font: name Times New Roman, color-index blue, bold on')
                    title = easyxf('font: name Times New Roman, color-index blue, bold on , height 350; alignment: horiz centre')
                    style1 = easyxf(num_format_str='D-MMM-YY')
                    font_style = XFStyle()
                    font_style.font.bold = True
                    font_style2 = XFStyle()
                    font_style2.font.bold = False
                    # bordes
                    borders = Borders()
                    borders.left = 1
                    borders.right = 1
                    borders.top = 1
                    borders.bottom = 1
                    title = easyxf('font: name Arial, bold on , height 200; alignment: horiz centre')
                    subtitle = easyxf('font: name Arial, bold on , height 150; alignment: horiz centre')
                    normaliz = easyxf('font: name Arial , height 150; align: wrap on,horiz left ')
                    nnormal = easyxf('font: name Arial, bold on , height 150; align: wrap on,horiz right')
                    normal = easyxf('font: name Arial , height 150; align: wrap on,horiz center ')
                    stylebnotas = easyxf('font: name Arial, bold on , height 150; alignment: horiz centre')
                    stylebnombre = easyxf('font: name Arial, bold on , height 150; align: wrap on, horiz left')
                    stylebnotas.borders = borders
                    wb = Workbook(encoding='utf-8')
                    ws = wb.add_sheet('reporte')
                    response = HttpResponse(content_type="application/ms-excel")
                    response[
                        'Content-Disposition'] = 'attachment; filename=resultados_encuesta_consolidado' + random.randint(1,
                                                                                                                     10000).__str__() + '.xls'
                    fila = 1
                    cc = 9
                    row_num = 3

                    coordinaciones=Coordinacion.objects.filter(status=True, excluir=False)
                    cursor = connection.cursor()
                    for x in coordinaciones:
                        for c in Carrera.objects.filter(status=True, coordinacion=x).order_by('nombre'):
                            preguntas_aux = SagPreguntaEncuesta.objects.filter(status=True, sagencuesta__sagperiodo__id=int(idp) , sagencuesta__sagencuestacarrera__carrera_id=c.id, sagencuesta__status=True).distinct().order_by('orden','id')
                            preguntas = []
                            cantidadp = 0
                            for pre1 in preguntas_aux:
                                preguntas.append([pre1.sagpregunta.nombre, pre1.id,pre1.orden,pre1.sagencuesta.nombre,pre1.tipo.numeromatriz])
                                cantidadp += 1
                                # if 'matriz 2' in pre1.tipo.nombre:
                                #     preguntas.append([pre1.sagpregunta.nombre, pre1.id, pre1.orden,pre1.sagencuesta.nombre,pre1.tipo.numeromatriz])
                                #     cantidadp += 1
                            sql=""
                            lista=[]
                            listaverifica=[]
                            sql = "select * from( select coor.nombre as facultad, carr.nombre AS carrera,  " \
                                  "CASE WHEN carr.mencion!='' THEN carr.mencion ELSE '' END as mencion,  " \
                                  "cab.fecha_creacion as fechaencuesta,gra.fechagraduado,sexo.nombre as sexo,per.cedula, " \
                                  " per.apellido1 || ' ' || per.apellido2 || ' ' || per.nombres as nombres,  encu.nombre as encuesta," \
                                  " pren.orden,preg.nombre as pregunta,pregti.nombre as tipopregunta,   det.valor as respuesta," \
                                  " pregti.id as tipo,   (select ite.nombre from sga_sagencuestaitem ite   " \
                                  " where ite.preguntaencuesta_id=pren.id and pren.tipo_id in(2,4)  and pren.id=det.preguntaencuesta_id " \
                                  " and ite.id=cast(det.valor as numeric)) as respuesta_seleccionada ,det.numero as matriz,pren.id  " \
                                  " from sga_sagresultadoencuestadetalle det  " \
                                  " left join sga_sagresultadoencuesta cab on cab.id=det.sagresultadoencuesta_id   " \
                                  " left join sga_inscripcion ins on ins.id=cab.inscripcion_id   " \
                                  " left join sga_coordinacion coor on coor.id=ins.coordinacion_id  " \
                                  " left join sga_carrera carr on carr.id=ins.carrera_id  " \
                                  " left join sga_persona per on per.id=ins.persona_id   " \
                                  " left join sga_sagpreguntaencuesta pren on pren.id=det.preguntaencuesta_id  " \
                                  " left join sga_sagencuesta encu on encu.id=pren.sagencuesta_id   " \
                                  " left join sga_sagpregunta preg on preg.id=pren.sagpregunta_id   " \
                                  " left join sga_sagpreguntatipo pregti on pregti.id=pren.tipo_id  " \
                                  " left join sga_sexo sexo on sexo.id=per.sexo_id   " \
                                  " left join sga_graduado gra on gra.inscripcion_id=ins.id   " \
                                  " where det.status=True and coor.id not in(7)   " \
                                  " and cab.status=True   " \
                                  " and  coor.id= " + str(x.id) + " and carr.id=" + str(
                                c.id) + " and cab.sagperiodo_id= " + idp + "  " \
                                                                           " and pregti.id not in(4,7) " \
                                                                           " union all " \
                                                                           "  select facultad,carrera,mencion,fechaencuesta,fechagraduado,sexo, " \
                                                                           "       cedula,nombres,encuesta,orden,pregunta,tipopregunta, " \
                                                                           "       '0'::varchar as respuesta,tipo,array_agg(respuesta_seleccionada)::varchar as respuesta_seleccionada,'0'::int matriz,id from ( " \
                                                                           "       select coor.nombre as facultad, carr.nombre AS carrera, " \
                                                                           "       CASE WHEN carr.mencion!='' THEN carr.mencion ELSE '' END as mencion, " \
                                                                           "       cab.fecha_creacion as fechaencuesta,gra.fechagraduado,sexo.nombre as sexo,per.cedula, " \
                                                                           "       per.apellido1 || ' ' || per.apellido2 || ' ' || per.nombres as nombres,  encu.nombre as encuesta, " \
                                                                           "       pren.orden,preg.nombre as pregunta,pregti.nombre as tipopregunta,   det.valor as respuesta, " \
                                                                           "       pregti.id as tipo,   CASE WHEN (select ite.nombre from sga_sagencuestaitem ite " \
                                                                           "       where ite.preguntaencuesta_id=pren.id and pren.tipo_id in(2,4)  and pren.id=det.preguntaencuesta_id " \
                                                                           "       and ite.id=cast(det.valor as numeric)) is null then det.valor " \
                                                                           "       ELSE (select ite.nombre from sga_sagencuestaitem ite " \
                                                                           "       where ite.preguntaencuesta_id=pren.id and pren.tipo_id in(2,4)  and pren.id=det.preguntaencuesta_id " \
                                                                           "       and ite.id=cast(det.valor as numeric)) " \
                                                                           "       END as respuesta_seleccionada ,det.numero as matriz,pren.id " \
                                                                           "       from sga_sagresultadoencuestadetalle det " \
                                                                           "       left join sga_sagresultadoencuesta cab on cab.id=det.sagresultadoencuesta_id " \
                                                                           "       left join sga_inscripcion ins on ins.id=cab.inscripcion_id " \
                                                                           "       left join sga_coordinacion coor on coor.id=ins.coordinacion_id " \
                                                                           "       left join sga_carrera carr on carr.id=ins.carrera_id " \
                                                                           "       left join sga_persona per on per.id=ins.persona_id " \
                                                                           "       left join sga_sagpreguntaencuesta pren on pren.id=det.preguntaencuesta_id " \
                                                                           "       left join sga_sagencuesta encu on encu.id=pren.sagencuesta_id " \
                                                                           "       left join sga_sagpregunta preg on preg.id=pren.sagpregunta_id " \
                                                                           "       left join sga_sagpreguntatipo pregti on pregti.id=pren.tipo_id " \
                                                                           "       left join sga_sexo sexo on sexo.id=per.sexo_id " \
                                                                           "       left join sga_graduado gra on gra.inscripcion_id=ins.id " \
                                                                           "       where det.status=True and coor.id not in(7)" \
                                                                           "       and cab.status=True " \
                                                                           "       and coor.id= " + str(
                                x.id) + " and carr.id=" + str(c.id) + " and cab.sagperiodo_id= " + idp + "  " \
                                                                                                         "       and pregti.id in(4,7)) as d " \
                                                                                                         " group by facultad,carrera,mencion,fechaencuesta,fechagraduado,sexo," \
                                                                                                         "cedula,nombres,encuesta,orden,pregunta,tipopregunta, " \
                                                                                                         "tipo,id ) as tabla order by nombres,orden, id "
                            cursor.execute(sql)
                            results = cursor.fetchall()
                            cc = 1
                            # cantidadp = preguntas.count()
                            arregloorden = []
                            for pre in preguntas:
                                arregloorden.append([pre[1], pre[2], pre[4]])
                            variable=[]
                            ccaux = 0
                            for re in results:
                                while ccaux <= cantidadp-1:
                                    if re[16] == arregloorden[ccaux][0]  and re[9] == arregloorden[ccaux][1]:
                                        ccaux += 1
                                        ccaux2 = ccaux
                                        ccaux = cantidadp + 1
                                        # variable.append([re[9],re[14]])
                                        if re[13] == 2 or re[13] == 4 or re[13] == 7:
                                            variable.append([re[14]])
                                        else:
                                            variable.append([re[12]])
                                    else:
                                        ccaux += 1
                                        ccaux2 = ccaux
                                        variable.append([''])
                                ccaux = ccaux2

                                if ccaux > cantidadp-1:
                                    if re[6] not in listaverifica:
                                        lista.append([re[0], re[1], re[3], re[4], re[5], re[6], re[7], re[8],variable])
                                    cc=0
                                    ccaux = 0
                                    variable=[]
                                    listaverifica.append( re[6])
                                cc += 1

                            if lista:
                                ws.write(fila, 0, 'No', stylebnotas)
                                ws.write(fila, 1, 'FACULTAD', stylebnotas)
                                ws.write(fila, 2, 'CARRERA', stylebnotas)
                                ws.write(fila, 3, 'FECHA ENCUESTA', stylebnotas)
                                ws.write(fila, 4, 'FECHA GRADUADO', stylebnotas)
                                ws.write(fila, 5, 'SEXO', stylebnotas)
                                ws.write(fila, 6, 'CÉDULA', stylebnotas)
                                ws.write(fila, 7, 'NOMBRES', stylebnotas)
                                ws.write(fila, 8, 'ENCUESTA', stylebnotas)
                                cc = 9
                                veces = 0
                                for pre in preguntas:
                                    if cc < 256:
                                        ws.write(fila, cc, pre[0], stylebnotas)
                                        nombreencuesta = pre[3]
                                        veces += 1
                                    cc += 1
                                fila += 1
                                date_format = xlwt.XFStyle()
                                date_format.num_format_str = 'yyyy/mm/dd'
                                i = 0
                                row_num = fila + 1

                                for r in lista:
                                    campo1 = r[0]
                                    campo2 = r[1]
                                    campo3 = r[2]
                                    campo4 = r[3]
                                    campo5 = r[4]
                                    campo6 = r[5]
                                    campo7 = r[6]
                                    campo8 = nombreencuesta
                                    i += 1
                                    ws.write(row_num, 0, i, font_style2)
                                    ws.write(row_num, 1, campo1, font_style2)
                                    ws.write(row_num, 2, campo2, font_style2)
                                    ws.write(row_num, 3, campo3, date_format)
                                    ws.write(row_num, 4, campo4, date_format)
                                    ws.write(row_num, 5, campo5, font_style2)
                                    ws.write(row_num, 6, campo6, font_style2)
                                    ws.write(row_num, 7, campo7, font_style2)
                                    ws.write(row_num, 8, campo8, font_style2)
                                    tt = 9
                                    for v in r[8]:
                                        ws.write(row_num, tt, v[0], font_style2)
                                        tt += 1
                                    row_num += 1
                                    fila = row_num + 1
                            lista = []
                    wb.save(response)
                    connection.close()
                    return response
                except Exception as ex:
                    print('Error on line {}'.format(sys.exc_info()[-1].tb_lineno))
                    pass


            # elif action == 'resultadoencuestageneral2':
            #     try:
            #         idp = request.GET['idperiodo']
            #         __author__ = 'Unemi'
            #         style0 = easyxf('font: name Times New Roman, color-index blue, bold off', num_format_str='#,##0.00')
            #         style_nb = easyxf('font: name Times New Roman, color-index blue, bold on', num_format_str='#,##0.00')
            #         style_sb = easyxf('font: name Times New Roman, color-index blue, bold on')
            #         title = easyxf('font: name Times New Roman, color-index blue, bold on , height 350; alignment: horiz centre')
            #         style1 = easyxf(num_format_str='D-MMM-YY')
            #         font_style = XFStyle()
            #         font_style.font.bold = True
            #         font_style2 = XFStyle()
            #         font_style2.font.bold = False
            #         # bordes
            #         borders = Borders()
            #         borders.left = 1
            #         borders.right = 1
            #         borders.top = 1
            #         borders.bottom = 1
            #         title = easyxf('font: name Arial, bold on , height 200; alignment: horiz centre')
            #         subtitle = easyxf('font: name Arial, bold on , height 150; alignment: horiz centre')
            #         normaliz = easyxf('font: name Arial , height 150; align: wrap on,horiz left ')
            #         nnormal = easyxf('font: name Arial, bold on , height 150; align: wrap on,horiz right')
            #         normal = easyxf('font: name Arial , height 150; align: wrap on,horiz center ')
            #         stylebnotas = easyxf('font: name Arial, bold on , height 150; alignment: horiz centre')
            #         stylebnombre = easyxf('font: name Arial, bold on , height 150; align: wrap on, horiz left')
            #         stylebnotas.borders = borders
            #         wb = Workbook(encoding='utf-8')
            #         coordinaciones=Coordinacion.objects.filter(pk=4,status=True, excluir=False)
            #         cursor = connection.cursor()
            #         for x in coordinaciones:
            #             for c in Carrera.objects.filter(pk=24,status=True, coordinacion=x).order_by('nombre'):
            #                 preguntas_aux = SagPreguntaEncuesta.objects.filter(status=True, sagencuesta__sagperiodo__id=int(idp) , sagencuesta__sagencuestacarrera__carrera_id=c.id, sagencuesta__status=True).distinct().order_by('orden','id')
            #                 preguntas = []
            #                 cantidadp = 0
            #                 for pre1 in preguntas_aux:
            #                     preguntas.append([pre1.sagpregunta.nombre, pre1.id,pre1.orden,pre1.sagencuesta.nombre,pre1.tipo.numeromatriz])
            #                     cantidadp += 1
            #                     # if 'matriz 2' in pre1.tipo.nombre:
            #                     #     preguntas.append([pre1.sagpregunta.nombre, pre1.id, pre1.orden,pre1.sagencuesta.nombre,pre1.tipo.numeromatriz])
            #                     #     cantidadp += 1
            #                 sql=""
            #                 lista=[]
            #                 sql = "select * from( select coor.nombre as facultad, carr.nombre AS carrera,  " \
            #                       "CASE WHEN carr.mencion!='' THEN carr.mencion ELSE '' END as mencion,  " \
            #                       "cab.fecha_creacion as fechaencuesta,gra.fechagraduado,sexo.nombre as sexo,per.cedula, " \
            #                       " per.apellido1 || ' ' || per.apellido2 || ' ' || per.nombres as nombres,  encu.nombre as encuesta," \
            #                       " pren.orden,preg.nombre as pregunta,pregti.nombre as tipopregunta,   det.valor as respuesta," \
            #                       " pregti.id as tipo,   (select ite.nombre from sga_sagencuestaitem ite   " \
            #                       " where ite.preguntaencuesta_id=pren.id and pren.tipo_id in(2,4)  and pren.id=det.preguntaencuesta_id " \
            #                       " and ite.id=cast(det.valor as numeric)) as respuesta_seleccionada ,det.numero as matriz,pren.id  " \
            #                       " from sga_sagresultadoencuestadetalle det  " \
            #                       " left join sga_sagresultadoencuesta cab on cab.id=det.sagresultadoencuesta_id   " \
            #                       " left join sga_inscripcion ins on ins.id=cab.inscripcion_id   " \
            #                       " left join sga_coordinacion coor on coor.id=ins.coordinacion_id  " \
            #                       " left join sga_carrera carr on carr.id=ins.carrera_id  " \
            #                       " left join sga_persona per on per.id=ins.persona_id   " \
            #                       " left join sga_sagpreguntaencuesta pren on pren.id=det.preguntaencuesta_id  " \
            #                       " left join sga_sagencuesta encu on encu.id=pren.sagencuesta_id   " \
            #                       " left join sga_sagpregunta preg on preg.id=pren.sagpregunta_id   " \
            #                       " left join sga_sagpreguntatipo pregti on pregti.id=pren.tipo_id  " \
            #                       " left join sga_sexo sexo on sexo.id=per.sexo_id   " \
            #                       " left join sga_graduado gra on gra.inscripcion_id=ins.id   " \
            #                       " where det.status=True   " \
            #                       " and cab.status=True   " \
            #                       " and  coor.id= " + str(x.id) + " and carr.id=" + str(c.id) + " and cab.sagperiodo_id= " + idp + "  " \
            #                       " and pregti.id not in(4,7) " \
            #                       " union all " \
            #                 "  select facultad,carrera,mencion,fechaencuesta,fechagraduado,sexo, " \
            #                 "       cedula,nombres,encuesta,orden,pregunta,tipopregunta, " \
            #                 "       '0'::varchar as respuesta,tipo,array_agg(respuesta_seleccionada)::varchar as respuesta_seleccionada,'0'::int matriz,id from ( " \
            #                 "       select coor.nombre as facultad, carr.nombre AS carrera, " \
            #                 "       CASE WHEN carr.mencion!='' THEN carr.mencion ELSE '' END as mencion, " \
            #                 "       cab.fecha_creacion as fechaencuesta,gra.fechagraduado,sexo.nombre as sexo,per.cedula, " \
            #                 "       per.apellido1 || ' ' || per.apellido2 || ' ' || per.nombres as nombres,  encu.nombre as encuesta, " \
            #                 "       pren.orden,preg.nombre as pregunta,pregti.nombre as tipopregunta,   det.valor as respuesta, " \
            #                 "       pregti.id as tipo,   CASE WHEN (select ite.nombre from sga_sagencuestaitem ite " \
            #                 "       where ite.preguntaencuesta_id=pren.id and pren.tipo_id in(2,4)  and pren.id=det.preguntaencuesta_id " \
            #                 "       and ite.id=cast(det.valor as numeric)) is null then det.valor " \
            #                 "       ELSE (select ite.nombre from sga_sagencuestaitem ite " \
            #                 "       where ite.preguntaencuesta_id=pren.id and pren.tipo_id in(2,4)  and pren.id=det.preguntaencuesta_id " \
            #                 "       and ite.id=cast(det.valor as numeric)) " \
            #                 "       END as respuesta_seleccionada ,det.numero as matriz,pren.id " \
            #                 "       from sga_sagresultadoencuestadetalle det " \
            #                 "       left join sga_sagresultadoencuesta cab on cab.id=det.sagresultadoencuesta_id " \
            #                 "       left join sga_inscripcion ins on ins.id=cab.inscripcion_id " \
            #                 "       left join sga_coordinacion coor on coor.id=ins.coordinacion_id " \
            #                 "       left join sga_carrera carr on carr.id=ins.carrera_id " \
            #                 "       left join sga_persona per on per.id=ins.persona_id " \
            #                 "       left join sga_sagpreguntaencuesta pren on pren.id=det.preguntaencuesta_id " \
            #                 "       left join sga_sagencuesta encu on encu.id=pren.sagencuesta_id " \
            #                 "       left join sga_sagpregunta preg on preg.id=pren.sagpregunta_id " \
            #                 "       left join sga_sagpreguntatipo pregti on pregti.id=pren.tipo_id " \
            #                 "       left join sga_sexo sexo on sexo.id=per.sexo_id " \
            #                 "       left join sga_graduado gra on gra.inscripcion_id=ins.id " \
            #                 "       where det.status=True " \
            #                 "       and cab.status=True " \
            #                 "       and coor.id= " + str(x.id) + " and carr.id=" + str(c.id) + " and cab.sagperiodo_id= " + idp + "  " \
            #                 "       and pregti.id in(4,7)) as d " \
            #                         " group by facultad,carrera,mencion,fechaencuesta,fechagraduado,sexo," \
            #                         "cedula,nombres,encuesta,orden,pregunta,tipopregunta, " \
            #                         "tipo,id ) as tabla order by nombres,orden, id "
            #                 # sql = "select coor.nombre as facultad, carr.nombre AS carrera,  CASE WHEN carr.mencion!='' THEN carr.mencion ELSE '' END as mencion, " \
            #                 #       " cab.fecha_creacion as fechaencuesta,gra.fechagraduado,sexo.nombre as sexo,per.cedula,  per.apellido1 || ' ' || per.apellido2 || ' ' || per.nombres as nombres, " \
            #                 #       " 'ss' as encuesta,pren.orden,preg.nombre as pregunta,pregti.nombre as tipopregunta,   det.valor as respuesta,pregti.id as tipo,  " \
            #                 #       " (select ite.nombre from sga_sagencuestaitem ite   where ite.preguntaencuesta_id=pren.id and pren.tipo_id in(2,4)  and pren.id=det.preguntaencuesta_id " \
            #                 #       "and ite.id=cast(det.valor as numeric)) as respuesta_seleccionada ,det.numero as matriz,pren.id  " \
            #                 #       " from sga_sagresultadoencuestadetalle det  left join sga_sagresultadoencuesta cab on cab.id=det.sagresultadoencuesta_id  " \
            #                 #       " left join sga_inscripcion ins on ins.id=cab.inscripcion_id   left join sga_coordinacion coor on coor.id=ins.coordinacion_id  " \
            #                 #       "left join sga_carrera carr on carr.id=ins.carrera_id  left join sga_persona per on per.id=ins.persona_id  " \
            #                 #       " left join sga_sagpreguntaencuesta pren on pren.id=det.preguntaencuesta_id  left join sga_sagencuesta encu on encu.id=pren.sagencuesta_id  " \
            #                 #       " left join sga_sagpregunta preg on preg.id=pren.sagpregunta_id   left join sga_sagpreguntatipo pregti on pregti.id=pren.tipo_id  " \
            #                 #       "left join sga_sexo sexo on sexo.id=per.sexo_id   left join sga_graduado gra on gra.inscripcion_id=ins.id  " \
            #                 #       " where det.status=True   and cab.status=True and per.cedula='0922561501'   and  coor.id= " + str(x.id) + " and carr.id=" + str(c.id) + " and cab.sagperiodo_id= " + idp + "  order by nombres,pren.orden, pren.id "
            #                 cursor.execute(sql)
            #                 results = cursor.fetchall()
            #                 cc = 1
            #                 # cantidadp = preguntas.count()
            #                 arregloorden = []
            #                 for pre in preguntas:
            #                     arregloorden.append([pre[1], pre[2], pre[4]])
            #                 variable=[]
            #                 ccaux = 0
            #                 for re in results:
            #                     while ccaux <= cantidadp-1:
            #                         if re[16] == arregloorden[ccaux][0]  and re[9] == arregloorden[ccaux][1]:
            #                             ccaux += 1
            #                             ccaux2 = ccaux
            #                             ccaux = cantidadp + 1
            #                             # variable.append([re[9],re[14]])
            #                             if re[13] == 2 or re[13] == 4 or re[13] == 7:
            #                                 variable.append([re[14]])
            #                             else:
            #                                 variable.append([re[12]])
            #                         else:
            #                             ccaux += 1
            #                             ccaux2 = ccaux
            #                             variable.append([''])
            #                     ccaux = ccaux2
            #
            #                     if ccaux > cantidadp-1:
            #                         lista.append([re[0], re[1], re[3], re[4], re[5], re[6], re[7], re[8],variable])
            #                         cc=0
            #                         ccaux = 0
            #                         variable=[]
            #                     cc += 1
            #
            #                 if lista:
            #                     pest=c.alias+" "+str(c.id)
            #                     ws = wb.add_sheet(pest)
            #                     response = HttpResponse(content_type="application/ms-excel")
            #                     response['Content-Disposition'] = 'attachment; filename=resultados_encuesta_general' + random.randint(1, 10000).__str__() + '.xls'
            #                     fila = 1
            #                     ws.write(fila, 0, 'No', stylebnotas)
            #                     ws.write(fila, 1, 'FACULTAD', stylebnotas)
            #                     ws.write(fila, 2, 'CARRERA', stylebnotas)
            #                     ws.write(fila, 3, 'FECHA ENCUESTA', stylebnotas)
            #                     ws.write(fila, 4, 'FECHA GRADUADO', stylebnotas)
            #                     ws.write(fila, 5, 'SEXO', stylebnotas)
            #                     ws.write(fila, 6, 'CÉDULA', stylebnotas)
            #                     ws.write(fila, 7, 'NOMBRES', stylebnotas)
            #                     ws.write(fila, 8, 'ENCUESTA', stylebnotas)
            #                     cc = 9
            #                     veces = 0
            #                     for pre in preguntas:
            #                         if cc < 256:
            #                             ws.write(fila, cc, pre[0], stylebnotas)
            #                             nombreencuesta = pre[3]
            #                             veces += 1
            #                         cc += 1
            #                     row_num = 1
            #                     date_format = xlwt.XFStyle()
            #                     date_format.num_format_str = 'yyyy/mm/dd'
            #                     row_num = 2
            #                     i = 0
            #                     for r in lista:
            #                         campo1 = r[0]
            #                         campo2 = r[1]
            #                         campo3 = r[2]
            #                         campo4 = r[3]
            #                         campo5 = r[4]
            #                         campo6 = r[5]
            #                         campo7 = r[6]
            #                         campo8 = nombreencuesta
            #                         i += 1
            #                         ws.write(row_num, 0, i, font_style2)
            #                         ws.write(row_num, 1, campo1, font_style2)
            #                         ws.write(row_num, 2, campo2, font_style2)
            #                         ws.write(row_num, 3, campo3, date_format)
            #                         ws.write(row_num, 4, campo4, date_format)
            #                         ws.write(row_num, 5, campo5, font_style2)
            #                         ws.write(row_num, 6, campo6, font_style2)
            #                         ws.write(row_num, 7, campo7, font_style2)
            #                         ws.write(row_num, 8, campo8, font_style2)
            #                         tt = 0
            #                         # for pre in preguntas:
            #                         #     ws.write(row_num, tt + 9, v, font_style2)
            #                         #     tt += 1
            #                         for v in r[8]:
            #                             ws.write(row_num, tt+9, v[0], font_style2)
            #                             tt += 1
            #                         row_num += 1
            #                 lista = []
            #         wb.save(response)
            #         connection.close()
            #         return response
            #     except Exception as ex:
            #         pass

            elif action == 'informacionlaboral':
                try:
                    idp = request.GET['idperiodo']
                    __author__ = 'Unemi'
                    style0 = easyxf('font: name Times New Roman, color-index blue, bold off', num_format_str='#,##0.00')
                    style_nb = easyxf('font: name Times New Roman, color-index blue, bold on',
                                      num_format_str='#,##0.00')
                    style_sb = easyxf('font: name Times New Roman, color-index blue, bold on')
                    title = easyxf(
                        'font: name Times New Roman, color-index blue, bold on , height 350; alignment: horiz centre')
                    style1 = easyxf(num_format_str='D-MMM-YY')
                    font_style = XFStyle()
                    font_style.font.bold = True
                    font_style2 = XFStyle()
                    font_style2.font.bold = False
                    wb = Workbook(encoding='utf-8')
                    coordinaciones=Coordinacion.objects.filter(status=True, excluir=False)
                    for x in coordinaciones:
                        for c in Carrera.objects.filter(status=True, coordinacion=x).order_by('nombre'):
                            resultado=SagResultadoEncuesta.objects.filter(status=True,inscripcion__carrera=c)
                            if resultado:
                                pest=c.alias+" "+str(c.id)
                                ws = wb.add_sheet(pest)
                                response = HttpResponse(content_type="application/ms-excel")
                                response[
                                    'Content-Disposition'] = 'attachment; filename=informacion_laboral' + random.randint(
                                    1, 10000).__str__() + '.xls'
                                columns = [
                                    (u"No.", 1500),
                                    (u"FACULTAD", 6000),
                                    (u"CARRERA", 6000),
                                    (u"CÉDULA", 3000),
                                    (u"NOMBRES", 6000),
                                    (u"TIPO INSTITUCIÓN", 6000),
                                    (u"INSTITUCIÓN", 2000),
                                    (u"CARGO", 6000),
                                    (u"DEPARTAMENTO", 3000),
                                    (u"PAIS", 3000),
                                    (u"PROVINCIA", 6000),
                                    (u"CANTÓN", 6000),
                                    (u"PARROQUIA", 6000),
                                    (u"FECHA INICIO", 6000),
                                    (u"FECHA FIN", 6000),
                                    (u"MOTIVO SALIDA", 6000),
                                    (u"REGIMEN LABORAL", 6000),
                                    (u"HORAS SEMANALES", 6000),
                                    (u"DEDICACIÓN LABORAL", 6000),
                                    (u"ACTIVIDAD LABORAL", 6000),
                                    (u"OBSERVACIONES", 6000)
                                ]
                                row_num = 1
                                for col_num in range(len(columns)):
                                    ws.write(row_num, col_num, columns[col_num][0], font_style)
                                    ws.col(col_num).width = columns[col_num][1]
                                date_format = xlwt.XFStyle()
                                date_format.num_format_str = 'yyyy/mm/dd'
                                row_num = 2
                                i = 0
                                for resul in resultado:
                                    experiencia=ExperienciaLaboral.objects.filter(persona=resul.inscripcion.persona)
                                    if experiencia:
                                        for r in experiencia:
                                            campo1 = x.nombre
                                            campo2 = c.nombre +' '+c.alias
                                            campo3 = r.persona.cedula
                                            campo4 = r.persona.nombre_completo_inverso()
                                            campo5 = str(r.get_tipoinstitucion_display()) if r.tipoinstitucion else ""
                                            campo6 = r.institucion if r.institucion else ""
                                            campo7 = r.cargo if r.cargo else ""
                                            campo8 = r.departamento if r.departamento else ""
                                            campo9 = r.pais.nombre  if r.pais else ""
                                            campo10 = r.provincia.nombre if r.provincia else ""
                                            campo11 = r.canton.nombre if r.canton else ""
                                            campo12 = r.parroquia.nombre if r.parroquia else ""
                                            campo13 = r.fechainicio
                                            campo14 = r.fechafin
                                            campo15 = r.motivosalida.nombre if r.motivosalida else ""
                                            campo16 = r.regimenlaboral.nombre if r.regimenlaboral else ""
                                            campo17 = r.horassemanales
                                            campo18 = r.dedicacionlaboral.nombre if r.dedicacionlaboral else ""
                                            campo19 = r.dedicacionlaboral.nombre if r.dedicacionlaboral else ""
                                            campo20 = r.observaciones if r.observaciones else ""
                                            i += 1
                                            ws.write(row_num, 0, i, font_style2)
                                            ws.write(row_num, 1, campo1, font_style2)
                                            ws.write(row_num, 2, campo2, font_style2)
                                            ws.write(row_num, 3, campo3, font_style2)
                                            ws.write(row_num, 4, campo4, font_style2)
                                            ws.write(row_num, 5, campo5, font_style2)
                                            ws.write(row_num, 6, campo6, font_style2)
                                            ws.write(row_num, 7, campo7, font_style2)
                                            ws.write(row_num, 8, campo8, font_style2)
                                            ws.write(row_num, 9, campo9, font_style2)
                                            ws.write(row_num, 10, campo10, font_style2)
                                            ws.write(row_num, 11, campo11, font_style2)
                                            ws.write(row_num, 12, campo12, font_style2)
                                            ws.write(row_num, 13, campo13, date_format)
                                            ws.write(row_num, 14, campo14, date_format)
                                            ws.write(row_num, 15, campo15, font_style2)
                                            ws.write(row_num, 16, campo16, font_style2)
                                            ws.write(row_num, 17, campo17, font_style2)
                                            ws.write(row_num, 18, campo18, font_style2)
                                            ws.write(row_num, 19, campo19, font_style2)
                                            ws.write(row_num, 20, campo20, font_style2)
                                            row_num += 1
                                    else:
                                        campo1 = x.nombre
                                        campo2 = c.nombre + ' ' + c.alias
                                        campo3 = resul.inscripcion.persona.cedula
                                        campo4 = resul.inscripcion.persona.nombre_completo_inverso()
                                        campo5 = ""
                                        campo6 = ""
                                        campo7 = ""
                                        campo8 = ""
                                        campo9 = ""
                                        campo10 = ""
                                        campo11 = ""
                                        campo12 = ""
                                        campo13 = ""
                                        campo14 = ""
                                        campo15 = ""
                                        campo16 = ""
                                        campo17 = ""
                                        campo18 = ""
                                        campo19 = ""
                                        campo20 = ""
                                        i += 1
                                        ws.write(row_num, 0, i, font_style2)
                                        ws.write(row_num, 1, campo1, font_style2)
                                        ws.write(row_num, 2, campo2, font_style2)
                                        ws.write(row_num, 3, campo3, font_style2)
                                        ws.write(row_num, 4, campo4, font_style2)
                                        ws.write(row_num, 5, campo5, font_style2)
                                        ws.write(row_num, 6, campo6, font_style2)
                                        ws.write(row_num, 7, campo7, font_style2)
                                        ws.write(row_num, 8, campo8, font_style2)
                                        ws.write(row_num, 9, campo9, font_style2)
                                        ws.write(row_num, 10, campo10, font_style2)
                                        ws.write(row_num, 11, campo11, font_style2)
                                        ws.write(row_num, 12, campo12, font_style2)
                                        ws.write(row_num, 13, campo13, font_style2)
                                        ws.write(row_num, 14, campo14, font_style2)
                                        ws.write(row_num, 15, campo15, font_style2)
                                        ws.write(row_num, 16, campo16, font_style2)
                                        ws.write(row_num, 17, campo17, font_style2)
                                        ws.write(row_num, 18, campo18, font_style2)
                                        ws.write(row_num, 19, campo19, font_style2)
                                        ws.write(row_num, 20, campo20, font_style2)
                                        row_num += 1
                    wb.save(response)
                    return response
                except Exception as ex:
                    pass

            elif action == 'informacionpersonal':
                try:
                    idp = request.GET['idperiodo']
                    __author__ = 'Unemi'
                    style0 = easyxf('font: name Times New Roman, color-index blue, bold off', num_format_str='#,##0.00')
                    style_nb = easyxf('font: name Times New Roman, color-index blue, bold on',
                                      num_format_str='#,##0.00')
                    style_sb = easyxf('font: name Times New Roman, color-index blue, bold on')
                    title = easyxf(
                        'font: name Times New Roman, color-index blue, bold on , height 350; alignment: horiz centre')
                    style1 = easyxf(num_format_str='D-MMM-YY')
                    font_style = XFStyle()
                    font_style.font.bold = True
                    font_style2 = XFStyle()
                    font_style2.font.bold = False
                    wb = Workbook(encoding='utf-8')
                    coordinaciones=Coordinacion.objects.filter(status=True, excluir=False)
                    for x in coordinaciones:
                        for c in Carrera.objects.filter(status=True, coordinacion=x).order_by('nombre'):
                            resultado=SagResultadoEncuesta.objects.filter(status=True,inscripcion__carrera=c)
                            if resultado:
                                pest=c.alias+" "+str(c.id)
                                ws = wb.add_sheet(pest)
                                response = HttpResponse(content_type="application/ms-excel")
                                response[
                                    'Content-Disposition'] = 'attachment; filename=informacion_personal' + random.randint(
                                    1, 10000).__str__() + '.xls'
                                columns = [
                                    (u"No.", 1500),
                                    (u"FACULTAD", 6000),
                                    (u"CARRERA", 6000),
                                    (u"CÉDULA", 3000),
                                    (u"NOMBRES", 6000),
                                    (u"DIRECCIÓN", 6000),
                                    (u"CIUDAD", 2000),
                                    (u"PROVINCIA", 6000),
                                    (u"PAÍS", 3000),
                                    (u"EMAIL INSTITUCIONAL", 3000),
                                    (u"EMAIL PERSONAL", 3000),
                                    (u"CELULAR", 6000),
                                    (u"FIJO", 6000),
                                    (u"OTRO CONTACTO", 6000),
                                    (u"ESTADO CIVIL", 6000),
                                    (u"NÚMERO DE HIJOS", 6000),
                                    (u"ETNIA", 6000)
                                ]
                                row_num = 1
                                for col_num in range(len(columns)):
                                    ws.write(row_num, col_num, columns[col_num][0], font_style)
                                    ws.col(col_num).width = columns[col_num][1]
                                date_format = xlwt.XFStyle()
                                date_format.num_format_str = 'yyyy/mm/dd'
                                row_num = 2
                                i = 0
                                for resul in resultado:
                                    campo1 = x.nombre
                                    campo2 = c.nombre +' '+c.alias
                                    campo3 = resul.inscripcion.persona.cedula
                                    campo4 = resul.inscripcion.persona.nombre_completo_inverso()
                                    campo5 = resul.inscripcion.persona.direccion_completa()
                                    campo6 = resul.inscripcion.persona.canton.nombre if resul.inscripcion.persona.canton else ""
                                    campo7 = resul.inscripcion.persona.provincia.nombre if resul.inscripcion.persona.provincia else ""
                                    campo8 = resul.inscripcion.persona.pais.nombre if resul.inscripcion.persona.pais else ""
                                    campo9 = resul.inscripcion.persona.email
                                    campo10 = resul.inscripcion.persona.emailinst
                                    campo11 = resul.inscripcion.persona.telefono
                                    campo12 = resul.inscripcion.persona.telefono_conv
                                    campo13 = resul.inscripcion.persona.datos_extension()
                                    campo13 = str(campo13.contactoemergencia) + " " + str(campo13.telefonoemergencia)
                                    campo14 = str(resul.inscripcion.persona.estado_civil().nombre) if resul.inscripcion.persona.estado_civil() else ""
                                    campo15=PersonaDatosFamiliares.objects.values("id").filter(Q(parentesco=11) | Q(parentesco=14),status=True,persona=resul.inscripcion.persona).count()
                                    campo16 = resul.inscripcion.persona.mi_perfil()
                                    raza=campo16.raza.nombre if campo16.raza else ""
                                    nacionalidad=campo16.nacionalidadindigena.nombre if campo16.nacionalidadindigena else ""
                                    campo16= raza +" "+ nacionalidad
                                    i += 1
                                    ws.write(row_num, 0, i, font_style2)
                                    ws.write(row_num, 1, campo1, font_style2)
                                    ws.write(row_num, 2, campo2, font_style2)
                                    ws.write(row_num, 3, campo3, font_style2)
                                    ws.write(row_num, 4, campo4, font_style2)
                                    ws.write(row_num, 5, campo5, font_style2)
                                    ws.write(row_num, 6, campo6, font_style2)
                                    ws.write(row_num, 7, campo7, font_style2)
                                    ws.write(row_num, 8, campo8, font_style2)
                                    ws.write(row_num, 9, campo9, font_style2)
                                    ws.write(row_num, 10, campo10, font_style2)
                                    ws.write(row_num, 11, campo11, font_style2)
                                    ws.write(row_num, 12, campo12, font_style2)
                                    ws.write(row_num, 16, campo16, font_style2)
                                    ws.write(row_num, 13, campo13, font_style2)
                                    ws.write(row_num, 14, campo14, font_style2)
                                    ws.write(row_num, 15, campo15, font_style2)
                                    row_num += 1
                    wb.save(response)
                    return response
                except Exception as ex:
                    pass

            elif action == 'listadoencuestas':
                try:
                    data['title'] = u'Listado Encuestas'
                    data['periodoeval'] = periodoeval = SagPeriodo.objects.get(pk=request.GET['idperiodo'])
                    data['idperiodo'] = request.GET['idperiodo']
                    form = SagEncuestasFrom()
                    data['formencuesta'] = form
                    search = None
                    ids = None
                    if 's' in request.GET:
                        search = request.GET['s']
                        listadoencuesta = SagEncuesta.objects.select_related().filter(Q(nombre__icontains=search) | Q(descripcion__icontains=search), sagperiodo=periodoeval, status=True).order_by("orden")
                    else:
                        listadoencuesta= SagEncuesta.objects.filter(sagperiodo=periodoeval, status=True).order_by('orden')
                    paging = MiPaginador(listadoencuesta, 5)
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
                    data['page'] = page
                    data['rangospaging'] = paging.rangos_paginado(p)
                    data['encuestasperiodos'] = page.object_list
                    data['search'] = search if search else ""
                    data['ids'] = ids if ids else ""
                    return render(request, "sagadministracion/listadoencuestas.html", data)
                except Exception as ex:
                    pass

            elif action == 'deleencuesta':
                try:
                    data['title'] = u'Eliminar Encuesta'
                    data['idperiodo'] = request.GET['idperiodo']
                    data['encuesta'] = SagEncuesta.objects.get(pk=int(request.GET['id']))
                    return render(request, "sagadministracion/deleteencuesta.html", data)
                except Exception as ex:
                    pass

            elif action == 'listadoencuestados':
                try:
                    data['title'] = u'Listado Encuestados'
                    search = None
                    fechainicio = None
                    fechafin = None
                    feini = None
                    fefin = None
                    idcar = None
                    idgen = None
                    idanio = None
                    data['periodoencuesta'] = periodoencuesta = SagPeriodo.objects.get(pk=request.GET['idperiodo'])
                    if 's' in request.GET:
                        search = request.GET['s'].strip()
                        ss = search.split(' ')
                        if len(ss) == 1:
                            encuestados = SagResultadoEncuesta.objects.select_related().filter(Q(inscripcion__persona__nombres__icontains=search) |
                                                                                               Q(inscripcion__persona__apellido1__icontains=search) |
                                                                                               Q(inscripcion__persona__apellido2__icontains=search)|
                                                                                               Q(inscripcion__persona__cedula__icontains=search)|
                                                                                               Q(inscripcion__coordinacion__nombre__icontains=search)|
                                                                                               Q(inscripcion__carrera__nombre__icontains=search,
                                                                                                 inscripcion__graduado__status=True), status=True, sagperiodo=periodoencuesta)
                        else:
                            encuestados = SagResultadoEncuesta.objects.select_related().filter(Q(inscripcion__persona__apellido1__icontains=ss[0]) &
                                                                                               Q(inscripcion__persona__apellido2__icontains=ss[1],
                                                                                                 inscripcion__graduado__status=True), status=True, sagperiodo=periodoencuesta).distinct()
                    elif 'fini' in request.GET:
                        feini = request.GET['fini']
                        fefin = request.GET['ffin']
                        fechainicio = request.GET['fini'] + ' 00:00'
                        fechafin = request.GET['ffin'] + ' 23:59:59'
                        encuestados = SagResultadoEncuesta.objects.select_related().filter(fecha_creacion__gte=fechainicio,fecha_creacion__lte=fechafin, sagperiodo=periodoencuesta, status=True,
                                                                                           inscripcion__graduado__status=True).order_by('-fecha_creacion')
                    elif 'idcar' in request.GET and 'idgen' in request.GET and 'idanio' in request.GET:
                        idcar = request.GET['idcar']
                        idgen = request.GET['idgen']
                        idanio = request.GET['idanio']
                        encuestados = SagResultadoEncuesta.objects.filter(sagperiodo=periodoencuesta,
                                                                          status=True,
                                                                          inscripcion__graduado__status=True,
                                                                          inscripcion__graduado__fechagraduado__year=idanio,
                                                                          inscripcion__carrera__id=idcar,
                                                                          inscripcion__persona__sexo__id=idgen).order_by('-fecha_creacion')
                        data['carreraselect'] = int(request.GET['idcar'])
                        data['sexselec'] = int(request.GET['idgen'])
                        data['aniselec'] = int(request.GET['idanio'])
                    elif 'idcar' in request.GET and 'idgen' in request.GET:
                        idcar = request.GET['idcar']
                        idgen = request.GET['idgen']
                        encuestados = SagResultadoEncuesta.objects.filter(sagperiodo=periodoencuesta,
                                                                          status=True,
                                                                          inscripcion__graduado__status=True,
                                                                          inscripcion__carrera__id=idcar,
                                                                          inscripcion__persona__sexo__id=idgen).order_by('-fecha_creacion')
                        data['carreraselect'] = int(request.GET['idcar'])
                        data['sexselec'] = int(request.GET['idgen'])
                    elif 'idcar' in request.GET and 'idanio' in request.GET:
                        idcar = request.GET['idcar']
                        idanio = request.GET['idanio']
                        encuestados = SagResultadoEncuesta.objects.filter(sagperiodo=periodoencuesta,
                                                                          status=True,
                                                                          inscripcion__graduado__status=True,
                                                                          inscripcion__graduado__fechagraduado__year=idanio,
                                                                          inscripcion__carrera__id=idcar).order_by('-fecha_creacion')
                        data['carreraselect'] = int(request.GET['idcar'])
                        data['aniselec'] = int(request.GET['idanio'])
                    elif 'idgen' in request.GET and 'idanio' in request.GET:
                        idgen = request.GET['idgen']
                        idanio = request.GET['idanio']
                        encuestados = SagResultadoEncuesta.objects.filter(sagperiodo=periodoencuesta,
                                                                          status=True,
                                                                          inscripcion__graduado__status=True,
                                                                          inscripcion__graduado__fechagraduado__year=idanio,
                                                                          inscripcion__persona__sexo__id=idgen).order_by('-fecha_creacion')
                        data['sexselec'] = int(request.GET['idgen'])
                        data['aniselec'] = int(request.GET['idanio'])
                    elif 'idcar' in request.GET:
                        idcar = request.GET['idcar']
                        encuestados = SagResultadoEncuesta.objects.filter(sagperiodo=periodoencuesta,
                                                                          status=True,
                                                                          inscripcion__graduado__status=True,
                                                                          inscripcion__carrera__id=idcar).order_by(
                            '-fecha_creacion')
                        data['carreraselect'] = int(request.GET['idcar'])
                    elif 'idgen' in request.GET:
                        idgen = request.GET['idgen']
                        encuestados = SagResultadoEncuesta.objects.filter(sagperiodo=periodoencuesta,
                                                                          status=True,
                                                                          inscripcion__graduado__status=True,
                                                                          inscripcion__persona__sexo__id=idgen).order_by('-fecha_creacion')
                        data['sexselec'] = int(request.GET['idgen'])
                    elif 'idanio' in request.GET:
                        idanio = request.GET['idanio']
                        encuestados = SagResultadoEncuesta.objects.filter(sagperiodo=periodoencuesta,
                                                                          status=True,
                                                                          inscripcion__graduado__status=True,
                                                                          inscripcion__graduado__fechagraduado__year=idanio).order_by('-fecha_creacion')
                        data['aniselec'] = int(request.GET['idanio'])

                    else:       encuestados = SagResultadoEncuesta.objects.select_related().filter(sagperiodo=periodoencuesta, status=True,inscripcion__graduado__status=True).order_by('-fecha_creacion')
                    paging = MiPaginador(encuestados, 25)
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
                    data['page'] = page
                    data['rangospaging'] = paging.rangos_paginado(p)
                    data['encuestados'] = page.object_list
                    data['search'] = search if search else ""
                    data['fechainicio'] = feini if feini else ""
                    data['fechafin'] = fefin if fefin else ""
                    data['idcar'] = idcar if idcar else ""
                    data['idgen'] = idgen if idgen else ""
                    data['idanio'] = idanio if idanio else ""
                    data['carreras'] = Carrera.objects.filter(status=True, coordinacion__excluir=False).order_by( 'nombre')
                    data['sexo'] = Sexo.objects.filter(status=True)
                    # listagrad = Graduado.objects.filter(inscripcion__carrera__in=miscarreras)
                    # listanio = []
                    # i = 0
                    # for x in listagrad:
                    #     a = x.fechagraduado.year
                    #     if i == 0:
                    #         listanio.append(a)
                    #         i += 1
                    #     else:
                    #         if a not in listanio:
                    #             listanio.append(a)
                    data['anios'] = Graduado.objects.filter(status=True,inscripcion__carrera__in=miscarreras, fechagraduado__isnull=False).annotate(Year=ExtractYear('fechagraduado')).values_list('Year', flat=True).order_by('Year').distinct()
                    return render(request, "sagadministracion/listadoencuestados.html", data)
                except Exception as ex:
                    pass

            elif action == 'listadoencuestascarreras':
                try:
                    data['title'] = u'Listado Carreras'
                    data['encuesta'] = encuesta = SagEncuesta.objects.get(pk=request.GET['idencuesta'])
                    data['periodoeval'] = encuesta.sagperiodo
                    is_pre_pos = encuesta.sagperiodo.tipo_sagperiodo
                    data['encuestascarreras'] = listacarreras = SagEncuestaCarrera.objects.filter(sagecuesta=encuesta,status=True)
                    listacarreras = listacarreras.values_list('carrera')
                    if is_pre_pos == 1:
                        data['listacarreras'] = miscarreras.exclude(pk__in=listacarreras).order_by('nombre')
                    else:
                        data['listacarreras'] = miscarreras.filter(coordinacion__id=7).exclude(pk__in=listacarreras).order_by('nombre')
                    form = SagEncuestasFrom()
                    data['formencuesta'] = form
                    return render(request, "sagadministracion/listadoencuestascarreras.html", data)
                except Exception as ex:
                    pass

            elif action == 'editperiodosag':
                try:
                    data['title'] = u'Editar Periodo'
                    data['sagperiodo'] = sagperiodo = SagPeriodo.objects.get(pk=request.GET['id'])
                    form = PeriodoSagForm(initial={'nombre': sagperiodo.nombre,
                                                   'descripcion': sagperiodo.descripcion,
                                                   'fechainicio': sagperiodo.fechainicio,
                                                   'fechafin': sagperiodo.fechafin,
                                                   'archivo': sagperiodo.archivo,
                                                   'tienemuestra': sagperiodo.tienemuestra,
                                                   'primeravez': sagperiodo.primeravez,
                                                   'aplicacurso': sagperiodo.aplicacurso,
                                                   'estado': sagperiodo.estado,
                                                   'tipo': sagperiodo.tipo_sagperiodo,
                                                   })
                    data['form'] = form
                    return render(request, "sagadministracion/editperiodosag.html", data)
                except Exception as ex:
                    pass

            elif action == 'addperiodo':
                try:
                    data['title'] = u'Agregar Periodo'
                    form = PeriodoSagForm()
                    if not persona.usuario.is_superuser:
                        if puede_realizar_accion_afirmativo(request,'posgrado.es_gestor_de_seguimiento_a_graduados_posgrado'):
                            form.tipo_posgrado()
                        else:
                            form.tipo_pregrado()

                    data['form'] = form
                    return render(request, "sagadministracion/addperiodo.html", data)
                except Exception as ex:
                    pass

            elif action == 'deleperiodo':
                try:
                    data['title'] = u'Eliminar Periodo'
                    data['periodo'] = SagPeriodo.objects.get(pk=int(request.GET['id']))
                    return render(request, "sagadministracion/deleteperiodo.html", data)
                except Exception as ex:
                    pass

            elif action == 'listadopreguntas':
                try:
                    data['title'] = u'Editar Encuesta'
                    data['idperiodoeval'] = request.GET['idperiodoeval']
                    data['encuestas'] = encuesta = SagEncuesta.objects.get(pk=request.GET['idencuesta'])
                    data['preguntas'] = SagPregunta.objects.filter(status=True)
                    data['grupos'] = SagGrupoPregunta.objects.filter(status=True)
                    data['tipopreguntas'] = SagPreguntaTipo.objects.filter(status=True)
                    formulario = PreguntasEncuestasForm()
                    formulario.adicionar(encuesta.id)
                    data['formpreguntasencuestas'] = formulario
                    form = SagEncuestasFrom(initial={'nombre': encuesta.nombre,
                                                     'descripcion': encuesta.descripcion,
                                                     'orden': encuesta.orden,
                                                     'estado': encuesta.estado
                                                     })
                    data['form'] = form
                    search = None
                    ids = None
                    if 's' in request.GET:
                        search = request.GET['s']
                        listadopreguntas = SagPreguntaEncuesta.objects.select_related().filter(Q(grupo__descripcion__icontains=search) |
                                                                                               Q(sagpregunta__nombre__icontains=search)|
                                                                                               Q(orden__icontains=search) ,
                                                                                               sagencuesta=encuesta,
                                                                                               status=True, sagpregunta__status=True)
                    else:
                        listadopreguntas = SagPreguntaEncuesta.objects.filter(sagencuesta=encuesta,status=True).order_by('orden')
                    paging = MiPaginador(listadopreguntas, 25)
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
                    data['page'] = page
                    data['rangospaging'] = paging.rangos_paginado(p)
                    data['listapreguntas'] = page.object_list
                    data['search'] = search if search else ""
                    data['ids'] = ids if ids else ""
                    return render(request, "sagadministracion/editencuesta.html", data)
                except Exception as ex:
                    pass

            elif action == 'listadopreguntasinscripcion':
                try:
                    data['title'] = u'Preguntas'
                    data['inscripcion'] = inscripcion = Inscripcion.objects.get(pk=request.GET['inscripcionid'])
                    data['periodoid'] = periodoid = request.GET['id']
                    data['resultados'] = SagResultadoEncuestaDetalle.objects.filter(sagresultadoencuesta__inscripcion=inscripcion,sagresultadoencuesta__sagperiodo__id=periodoid,status=True)
                    data['listaencuestas'] = SagEncuesta.objects.filter(sagperiodo_id=periodoid, estado=True,sagencuestacarrera__carrera=inscripcion.carrera,sagencuestacarrera__status=True,status=True).order_by('orden')
                    return render(request, "sagadministracion/encuestaestudiantes.html", data)
                except Exception as ex:
                    pass

            elif action == 'listarpreguntas':
                try:
                    data['title'] = u'Gestión de Preguntas '
                    data['idencuesta'] = request.GET['idencuesta']
                    data['idperiodoeval'] = request.GET['idperiodoeval']
                    search = None
                    ids = None
                    if 's' in request.GET:
                        search = request.GET['s']
                        if search.isdigit():
                            listadopreguntas = SagPregunta.objects.select_related().filter(pk=search, status=True).order_by("id")
                        else:
                            listadopreguntas = SagPregunta.objects.select_related().filter(Q(nombre__icontains=search) |
                                                                                           Q(descripcion__icontains=search),
                                                                                           status=True).order_by("id")
                    elif 'id' in request.GET:
                        ids = request.GET['id']
                        listadopreguntas = SagPregunta.objects.filter(id=ids)
                    else:
                        listadopreguntas = SagPregunta.objects.filter( status=True).order_by("id")
                    paging = MiPaginador(listadopreguntas, 10)
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
                    data['page'] = page
                    data['rangospaging'] = paging.rangos_paginado(p)
                    data['listadopreguntas'] = page.object_list
                    data['search'] = search if search else ""
                    data['ids'] = ids if ids else ""
                    return render(request, "sagadministracion/listapregunta.html", data)
                except Exception as ex:
                    pass

            elif action == 'editpregunta':
                try:
                    data['title'] = u'Editar Pregunta'
                    data['idencuesta'] = request.GET['idencuesta']
                    data['idperiodoeval'] = request.GET['idperiodoeval']
                    data['pregunta'] = pregunta = SagPregunta.objects.get(pk=int(request.GET['id']))
                    form = SagPreguntaFrom(initial={'nombre': pregunta.nombre,
                                                    'descripcion': pregunta.descripcion})
                    data['form'] = form
                    return render(request, "sagadministracion/editpregunta.html", data)
                except Exception as ex:
                    pass

            elif action == 'addpregunta':
                try:
                    data['title'] = u'Agregar Pregunta'
                    data['idencuesta'] = request.GET['idencuesta']
                    data['idperiodoeval'] = request.GET['idperiodoeval']
                    data['nombre'] = request.GET['nombre']
                    form = SagPreguntaFrom()
                    data['form'] = form
                    return render(request, "sagadministracion/addpregunta.html", data)
                except Exception as ex:
                    pass

            elif action == 'delepregunta':
                try:
                    data['title'] = u'Eliminar Pregunta'
                    data['idencuesta'] = request.GET['idencuesta']
                    data['idperiodoeval'] = request.GET['idperiodoeval']
                    data['pregunta'] = SagPregunta.objects.get(pk=int(request.GET['id']))
                    return render(request, "sagadministracion/deletepregunta.html", data)
                except Exception as ex:
                    pass

            elif action == 'listarpreguntas1':
                try:
                    data['title'] = u'Gestión de Preguntas '
                    search = None
                    ids = None
                    if 's' in request.GET:
                        search = request.GET['s']
                        if search.isdigit():
                            listadopreguntas = SagPregunta.objects.select_related().filter(pk=search, status=True).order_by("id")
                        else:
                            listadopreguntas = SagPregunta.objects.select_related().filter(Q(nombre__icontains=search) |
                                                                                           Q(descripcion__icontains=search),
                                                                                           status=True).order_by("id")
                    elif 'id' in request.GET:
                        ids = request.GET['id']
                        listadopreguntas = SagPregunta.objects.filter(id=ids)
                    else:
                        listadopreguntas = SagPregunta.objects.filter( status=True).order_by("id")
                    paging = MiPaginador(listadopreguntas, 10)
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
                    data['page'] = page
                    data['rangospaging'] = paging.rangos_paginado(p)
                    data['listadopreguntas'] = page.object_list
                    data['search'] = search if search else ""
                    data['ids'] = ids if ids else ""
                    return render(request, "sagadministracion/listapregunta1.html", data)
                except Exception as ex:
                    pass

            elif action == 'editpregunta1':
                try:
                    data['title'] = u'Editar Pregunta'
                    data['pregunta'] = pregunta = SagPregunta.objects.get(pk=int(request.GET['id']))
                    form = SagPreguntaFrom(initial={'nombre': pregunta.nombre,
                                                    'descripcion': pregunta.descripcion})
                    data['form'] = form
                    return render(request, "sagadministracion/editpregunta1.html", data)
                except Exception as ex:
                    pass

            elif action == 'addpregunta1':
                try:
                    data['title'] = u'Agregar Pregunta'
                    form = SagPreguntaFrom()
                    data['form'] = form
                    return render(request, 'sagadministracion/addpregunta1.html', data)
                except Exception as ex:
                    pass

            elif action == 'delepregunta1':
                try:
                    data['title'] = u'Eliminar Pregunta'
                    data['pregunta'] = SagPregunta.objects.get(pk=int(request.GET['id']))
                    return render(request, "sagadministracion/deletepregunta1.html", data)
                except Exception as ex:
                    pass

            elif action == 'listargruposencuesta':
                try:
                    data['title'] = u'Gestión de Grupos '
                    search = None
                    ids = None
                    if 's' in request.GET:
                        search = request.GET['s']
                        if search.isdigit():
                            listadogrupos = SagGrupoPregunta.objects.select_related().filter(pk=search, status=True).order_by("id")
                        else:
                            listadogrupos = SagGrupoPregunta.objects.select_related().filter(Q(descripcion__icontains=search) |
                                                                                             Q(orden__icontains=search) |
                                                                                             Q(observacion__icontains=search),
                                                                                             status=True).order_by("id")
                    elif 'id' in request.GET:
                        ids = request.GET['id']
                        listadogrupos = SagGrupoPregunta.objects.filter(id=ids)
                    else:
                        listadogrupos = SagGrupoPregunta.objects.filter( status=True).order_by("id")
                    paging = MiPaginador(listadogrupos, 5)
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
                    data['page'] = page
                    data['rangospaging'] = paging.rangos_paginado(p)
                    data['listadogrupos'] = page.object_list
                    data['search'] = search if search else ""
                    data['ids'] = ids if ids else ""
                    return render(request, "sagadministracion/listagrupos.html", data)
                except Exception as ex:
                    pass

            elif action == 'addgrupo':
                try:
                    data['title'] = u'Agregar Grupo'
                    form = SagGrupoFrom()
                    data['form'] = form
                    return render(request, "sagadministracion/addgrupos.html", data)
                except Exception as ex:
                    pass

            elif action == 'editgrupo':
                try:
                    data['title'] = u'Editar Grupos'
                    data['grupos'] = grupos = SagGrupoPregunta.objects.get(pk=int(request.GET['id']))
                    form = SagGrupoFrom(initial={'descripcion': grupos.descripcion,
                                                 'orden': grupos.orden,
                                                 'grupo': grupos.grupo,
                                                 'observacion': grupos.observacion,
                                                 'estado': grupos.estado,
                                                 'agrupado': grupos.agrupado,})
                    data['form'] = form
                    return render(request, "sagadministracion/editgrupo.html", data)
                except Exception as ex:
                    pass

            elif action == 'delegrupos':
                try:
                    data['title'] = u'Eliminar Grupo'
                    data['grupo'] = SagGrupoPregunta.objects.get(pk=int(request.GET['id']))
                    return render(request, "sagadministracion/deletegrupo.html", data)
                except Exception as ex:
                    pass

            elif action == 'listarindicadores':
                try:
                    data['title'] = u'Gestión de Indicadores'
                    search = None
                    ids = None
                    if 's' in request.GET:
                        search = request.GET['s']
                        if search.isdigit():
                            indicador = SagIndicador.objects.select_related().filter(pk=search,status=True,vigente='True').order_by("codigo")
                        else:
                            indicador = SagIndicador.objects.select_related().filter(
                                Q(nombre__icontains=search) |
                                Q(descripcion__icontains=search)|
                                Q(codigo__icontains=search) , status=True,vigente='True').order_by("codigo")
                    elif 'id' in request.GET:
                        ids = request.GET['id']
                        indicador = SagIndicador.objects.filter(id=ids,vigente='True')
                    else:
                        indicador = SagIndicador.objects.filter(status=True,vigente='True').order_by("codigo")
                    paging = MiPaginador(indicador, 10)
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
                    data['page'] = page
                    data['rangospaging'] = paging.rangos_paginado(p)
                    data['listaindicador'] = page.object_list
                    data['search'] = search if search else ""
                    data['ids'] = ids if ids else ""
                    return render(request, "sagadministracion/listaindicadores.html", data)
                except Exception as ex:
                    pass

            elif action == 'addindicador':
                try:
                    data['title'] = u'Agregar Indicador'
                    form = SagIndicadoresFrom()
                    data['form'] = form
                    return render(request, "sagadministracion/addindicador.html", data)
                except Exception as ex:
                    pass

            elif action == 'editindicador':
                try:
                    data['title'] = u'Editar Indicador'
                    data['indicador'] = indicador = SagIndicador.objects.get(pk=int(request.GET['id']))
                    form = SagIndicadoresFrom(initial={'codigo': indicador.codigo,
                                                       'nombre': indicador.nombre,
                                                       'descripcion': indicador.descripcion,
                                                       'vigente': indicador.vigente })
                    data['form'] = form
                    return render(request, "sagadministracion/editindicador.html", data)
                except Exception as ex:
                    pass

            elif action == 'deleindicador':
                try:
                    data['title'] = u'Eliminar Indicador'
                    data['indicador'] = SagIndicador.objects.get(pk=int(request.GET['id']))
                    return render(request, "sagadministracion/deleteindicador.html", data)
                except Exception as ex:
                    pass

            elif action == 'listarproyectos':
                try:
                    data['title'] = u'Gestión de Proyectos'
                    search = None
                    ids = None
                    if 's' in request.GET:
                        search = request.GET['s']
                        if search.isdigit():
                            proyecto = SagProyecto.objects.filter(pk=search,status=True,vigente='True').order_by("id")
                        else:
                            proyecto = SagProyecto.objects.select_related().filter(
                                Q(nombre__icontains=search)  , status=True,vigente='True').order_by("id")

                    elif 'id' in request.GET:
                        ids = request.GET['id']
                        proyecto = SagProyecto.objects.filter(id=ids,vigente='True')
                    else:
                        proyecto = SagProyecto.objects.filter(status=True,vigente='True').order_by("id")
                    paging = MiPaginador(proyecto, 5)
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
                    data['page'] = page
                    data['rangospaging'] = paging.rangos_paginado(p)
                    data['listarproyecto'] = page.object_list
                    data['search'] = search if search else ""
                    data['ids'] = ids if ids else ""
                    return render(request, "sagadministracion/listaproyectos.html", data)
                except Exception as ex:
                    pass

            elif action == 'addproyecto':
                try:
                    data['title'] = u'Agregar Proyectos'
                    form = SagProyectosFrom()
                    data['form'] = form
                    return render(request, "sagadministracion/addproyecto.html", data)
                except Exception as ex:
                    pass

            elif action == 'editproyecto':
                try:
                    data['title'] = u'Editar Proyecto'
                    data['proyecto'] = proyecto = SagProyecto.objects.get(pk=int(request.GET['id']))
                    form = SagProyectosFrom(initial={'codigo': proyecto.codigo,
                                                     'nombre': proyecto.nombre,
                                                     'vigente': proyecto.vigente })
                    data['form'] = form
                    return render(request, "sagadministracion/editproyecto.html", data)
                except Exception as ex:
                    pass

            elif action == 'deleproyecto':
                try:
                    data['title'] = u'Eliminar Proyecto'
                    data['proyecto'] = SagProyecto.objects.get(pk=int(request.GET['id']))
                    return render(request, "sagadministracion/deleteproyecto.html", data)
                except Exception as ex:
                    pass

            elif action == 'listarindicadorencuesta':
                try:
                    data['title'] = u'Gestión de Indicador y Encuestas'
                    data['idencuesta'] = request.GET['idencuesta']
                    encuesta = request.GET['idencuesta']
                    data['idperiodoeval'] = request.GET['idperiodoeval']
                    data['nombre'] = request.GET['nombre']
                    data['indicadores'] =   SagIndicador.objects.filter(status='True',vigente='True').order_by("codigo")
                    search = None
                    ids = None
                    if 's' in request.GET:
                        search = request.GET['s']
                        data['listadopreguntas'] = SagPreguntaEncuesta.objects.select_related().filter( Q(orden__icontains=search) |
                                                                                                        Q(sagpregunta__nombre__icontains=search) |
                                                                                                        Q(sagpregunta__descripcion__icontains=search) |
                                                                                                        Q(sagpregunta__descripcion__icontains=search),
                                                                                                        status=True, sagencuesta=encuesta).order_by("id")
                    else:
                        data['listadopreguntas'] = SagPreguntaEncuesta.objects.filter(sagencuesta=encuesta,status=True).order_by('id')

                    data['search'] = search if search else ""
                    data['ids'] = ids if ids else ""

                    return render(request, "sagadministracion/listaindencsta.html", data)

                except Exception as ex:
                    pass

            elif action == 'listarindicadorencuesta1':
                try:
                    data['title'] = u'Gestión de Indicador y Encuestas'
                    data['nompregunta'] = request.GET['nompregunta']
                    data['nomencuesta'] = request.GET['nomencuesta']
                    data['idencuestapreg'] =  request.GET['idencuestapreg']
                    data['idencuesta'] =  request.GET['idencuesta']
                    data['idperiodoeval'] =  request.GET['idperiodoeval']
                    search = None
                    ids = None
                    if 's' in request.GET:
                        search = request.GET['s']
                        data['indicadores'] = SagIndicador.objects.select_related().filter( Q(nombre__icontains=search) |
                                                                                            Q(descripcion__icontains=search) |
                                                                                            Q(codigo__icontains=search) ,
                                                                                            status=True, vigente=True).order_by("codigo")
                    else:
                        data['indicadores'] = SagIndicador.objects.filter(status=True,vigente=True).order_by("codigo")

                    data['search'] = search if search else ""
                    data['ids'] = ids if ids else ""

                    return render(request, "sagadministracion/listaindencsta1.html", data)
                except Exception as ex:
                    pass

            elif action == 'listarindicadorproyecto':
                try:
                    data['title'] = u'Gestión de Indicador y Proyectos'
                    data['idperiodoeval'] = request.GET['idperiodoeval']
                    data['indicadores'] =   SagIndicador.objects.filter(status='True',vigente='True').order_by("codigo")
                    search = None
                    ids = None
                    if 's' in request.GET:
                        search = request.GET['s']
                        if search.isdigit():
                            data['listadoproyecto'] = SagProyecto.objects.select_related().filter(Q(codigo__icontains=search),
                                                                                                  pk=search,
                                                                                                  vigente=True,
                                                                                                  status=True).order_by('id')
                        else:
                            data['listadoproyecto'] = SagProyecto.objects.select_related().filter( Q(nombre__icontains=search) |
                                                                                                   Q(codigo__icontains=search) ,
                                                                                                   status=True, vigente=True).order_by("id")
                    else:
                        data['listadoproyecto'] = SagProyecto.objects.filter(vigente=True,status=True).order_by('id')

                    data['search'] = search if search else ""
                    data['ids'] = ids if ids else ""

                    return render(request, "sagadministracion/listaindproy.html", data)

                except Exception as ex:
                    pass

            elif action == 'listarestadistica':
                try:
                    data['title'] = u'Gestión de Muestras'
                    data['idperiodo'] = idperiodo =request.GET['idperiodo']
                    data['nombperiodo'] = request.GET['nombperiodo']
                    search = None
                    ids = None
                    if 's' in request.GET:
                        search = request.GET['s']
                        estadistica = SagMuestraPeriodoCarrera.objects.select_related().filter(Q(periodo__nombre__icontains=search)|
                                                                                               Q(carrera__nombre__icontains=search)|
                                                                                               Q(carrera__coordinacion__nombre__icontains=search),status='True'
                                                                                               , periodo=idperiodo).order_by("carrera__nombre")
                    else:
                        estadistica = SagMuestraPeriodoCarrera.objects.select_related().filter(status=True,periodo=idperiodo).order_by("carrera__nombre")
                    paging = MiPaginador(estadistica, 10)
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
                    data['page'] = page
                    data['rangospaging'] = paging.rangos_paginado(p)
                    data['listarestadistica'] = page.object_list
                    data['search'] = search if search else ""
                    data['ids'] = ids if ids else ""
                    return render(request, "sagadministracion/listaestadistica.html", data)
                except Exception as ex:
                    pass

            elif action == 'listacarrera1':
                try:
                    data['idperiodo'] = idp= request.GET['idperiodo']
                    data['nombperiodo'] = request.GET['nombperiodo']
                    todo=request.GET['todo']
                    try:
                        if todo == '1':
                            idfac = request.GET['idfacultad']
                            carrusada = SagMuestraPeriodoCarrera.objects.values_list('carrera', flat=True).filter(
                                periodo=idp, status=True).order_by('id')
                            listacarrera = Carrera.objects.filter(coordinacion__excluir=False,coordinacion=idfac).exclude(pk__in=carrusada)
                            # listacarrera.nombre_completo()
                        elif todo=='3':
                            id=request.GET['id']
                            idfac = request.GET['idfacultad']
                            muestra = SagMuestraPeriodoCarrera.objects.get(pk=id)
                            carrusada = SagMuestraPeriodoCarrera.objects.values_list('carrera', flat=True).filter(
                                periodo=idp, status=True).exclude(carrera=muestra.carrera_id).order_by('id')
                            listacarrera = Carrera.objects.filter(coordinacion__excluir=False,coordinacion=idfac).exclude(pk__in=carrusada)
                        else:
                            carrusada = SagMuestraPeriodoCarrera.objects.values_list('carrera', flat=True).filter(
                                periodo=idp, status=True).order_by('id')
                            listacarrera = Carrera.objects.filter(coordinacion__excluir=False).exclude(pk__in=carrusada)
                            # listacarrera.nombre_completo()
                        lista = []
                        for x in listacarrera:
                            lista.append([x.id, x.nombre,x.mencion])
                        return JsonResponse({'result': 'ok', 'lista': lista})
                    except Exception as ex:
                        return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})
                except Exception as ex:
                    pass

            elif action == 'addestadistica':
                try:
                    data['title'] = u'Añadir Muestras de Graduados'
                    data['idperiodo'] = id= request.GET['idperiodo']
                    data['nombperiodo'] = request.GET['nombperiodo']
                    form = SagMuestraPeriodoCarreraForm()
                    form.fields['periodo'].queryset = SagPeriodo.objects.filter(id=id, status=True)
                    form.fields['periodo'].initial=id
                    form.listaCarreraUsada(id)
                    form.bloquear()
                    data['form'] = form

                    return render(request, 'sagadministracion/addestadistica.html', data)
                except Exception as ex:
                    pass

            elif action == 'editestadistica':
                try:
                    data['title'] = u'Modificar Muestras'
                    data['idperiodo'] = id = request.GET['idperiodo']
                    data['nombperiodo'] = request.GET['nombperiodo']
                    data['muestras'] = muestra = SagMuestraPeriodoCarrera.objects.get(pk=request.GET['id'])
                    carrusada = SagMuestraPeriodoCarrera.objects.values_list('carrera', flat=True).filter(
                        periodo=id, status=True).exclude(carrera=muestra.carrera_id).order_by('id')
                    facultad = Coordinacion.objects.values_list().filter(status=True, excluir=False, carrera=muestra.carrera_id)
                    form = SagMuestraPeriodoCarreraForm()
                    form.fields['periodo'].queryset = SagPeriodo.objects.filter(id=id, status=True)
                    form.fields['carrera'].queryset = Carrera.objects.filter(coordinacion__excluir=False,coordinacion=facultad[0][0]).exclude(pk__in=carrusada)
                    form.fields['periodo'].initial = id
                    form.fields['carrera'].initial = muestra.carrera_id
                    form.fields['facultad'].initial = facultad[0][0]
                    form.bloquear()
                    data['form'] = form
                    return render(request, 'sagadministracion/editestadistica.html', data)
                except Exception as ex:
                    pass

            elif action == 'deleteestadistica':
                try:
                    data['title'] = u'Eliminar Muestras'
                    data['idperiodo'] = idperiodo = request.GET['idperiodo']
                    data['nombperiodo'] = request.GET['nombperiodo']
                    data['muestras'] = SagMuestraPeriodoCarrera.objects.get(pk=request.GET['id'])
                    return render(request, 'sagadministracion/deleteestadistica.html', data)
                except Exception as ex:
                    pass

            elif action == 'tablamuestras':
                try:
                    data['title'] = u'Detalles de Muestras'
                    data['idperiodo'] = idperiodo = int(request.GET['idperiodo'])
                    data['nombperiodo'] = request.GET['nombperiodo']
                    data['idcarrera'] = request.GET['idcarrera']
                    data['id'] = id= request.GET['id']
                    data['muestras'] = muestra = SagMuestraPeriodoCarrera.objects.get(pk=id,periodo_id=idperiodo,status=True)
                    data['cantidadm']=muestra.cantidad_muestra_asociados()+1
                    data['cantidad']=muestra.cantidad_muestra_asociados()
                    data['facultad']=muestra.saca_facultad()

                    # data['lista'] = SagMuestraPeriodoCarrera.objects.get(pk=request.GET['id'],periodo_id=idperiodo, status=True)
                    # data['x']=Inscripcion.objects.filter(status=True,carrera_id=15,graduado__fechagraduado__year=2015).__len__()
                    # muestra.cantencuestados(13,2015)
                    return render(request, "sagadministracion/detallemuestras.html", data)
                except Exception as ex:
                    pass

            elif action == 'ingresoinformes':
                try:
                    data['title'] = u'Ingreso Informes Trimestrales y Anuales'
                    data['idperiodo'] = request.GET['idperiodo']
                    data['nombperiodo'] = request.GET['nombperiodo']
                    search = None
                    ids = None
                    if 's' in request.GET:
                        search = request.GET['s']
                        if not search.isdigit():
                            informes = SagInformes.objects.filter(Q(nombre__icontains=search), status=True).order_by("id")
                    elif 'id' in request.GET:
                        ids = request.GET['id']
                        informes = SagInformes.objects.filter(status=True,id=ids).order_by("nombre")
                    else:
                        informes = SagInformes.objects.filter(status=True).order_by("nombre")
                    paging = MiPaginador(informes, 5)
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
                    data['page'] = page
                    data['rangospaging'] = paging.rangos_paginado(p)
                    data['informes'] = page.object_list
                    data['search'] = search if search else ""
                    data['ids'] = ids if ids else ""
                    return render(request, "sagadministracion/ingresoinformes.html", data)
                except Exception as ex:
                    pass

            elif action == 'addinforme':
                try:
                    data['title'] = u'Agregar Informe'
                    data['idperiodo'] = request.GET['idperiodo']
                    data['nombperiodo'] = request.GET['nombperiodo']
                    data['form'] = SagInformeForm()
                    return render(request, "sagadministracion/addinforme.html", data)
                except Exception as ex:
                    pass

            elif action == 'editinforme':
                try:
                    data['title'] = u'Editar Informe'
                    data['idperiodo'] = request.GET['idperiodo']
                    data['nombperiodo'] = request.GET['nombperiodo']
                    data['informe'] = informe = SagInformes.objects.get(pk=int(request.GET['id']))
                    form = SagInformeForm(initial={'nombre': informe.nombre,
                                                   'fechainicio': informe.fechainicio,
                                                   'fechafin': informe.fechafin})
                    data['form'] = form
                    return render(request, "sagadministracion/editinforme.html", data)
                except Exception as ex:
                    pass

            elif action == 'deleinforme':
                try:
                    data['title'] = u'Eliminar Informe'
                    data['idperiodo'] = request.GET['idperiodo']
                    data['nombperiodo'] = request.GET['nombperiodo']
                    data['informe'] = SagInformes.objects.get(pk=int(request.GET['id']))
                    return render(request, "sagadministracion/deleinforme.html", data)
                except Exception as ex:
                    pass

            elif action == 'actividades':
                try:
                    data['title'] = u'Gestión de Actividades '
                    search = None
                    ids = None
                    if 's' in request.GET:
                        search = request.GET['s']
                        if search.isdigit():
                            actividades = SagActividades.objects.select_related().filter(pk=search, status=True).order_by("id")
                        else:
                            actividades = SagActividades.objects.select_related().filter(Q(nombre__icontains=search),
                                                                                         status=True).order_by("id")
                    elif 'id' in request.GET:
                        ids = request.GET['id']
                        actividades = SagActividades.objects.filter(id=ids)
                    else:
                        actividades = SagActividades.objects.filter(status=True).order_by("id")
                    paging = MiPaginador(actividades, 5)
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
                    data['page'] = page
                    data['rangospaging'] = paging.rangos_paginado(p)
                    data['actividades'] = page.object_list
                    data['search'] = search if search else ""
                    data['ids'] = ids if ids else ""
                    return render(request, "sagadministracion/listaactividades.html", data)
                except Exception as ex:
                    pass

            elif action == 'addactividad':
                try:
                    data['title'] = u'Agregar Actividad'
                    form = SagActividadForm()
                    form.adicionar(persona)
                    data['form'] = form
                    return render(request, "sagadministracion/addactividad.html", data)
                except Exception as ex:
                    pass

            elif action == 'editactividad':
                try:
                    data['title'] = u'Editar Actividad'
                    data['actividad'] = actividad = SagActividades.objects.get(pk=int(request.GET['id']))
                    initial = model_to_dict(actividad)
                    form = SagActividadForm(initial=initial)
                    form.editar(persona)
                    data['form'] = form
                    return render(request, "sagadministracion/editactividad.html", data)
                except Exception as ex:
                    pass

            elif action == 'editmuestra':
                try:
                    data['title'] = u'Editar Muestra'
                    data['muestra'] = muestra = SagMuestraEncuesta.objects.get(pk=int(request.GET['id']))
                    initial = model_to_dict(muestra)
                    form = SagMuestraForm(initial=initial)
                    form.editar(muestra)
                    data['form'] = form
                    return render(request, "sagadministracion/editmuestra.html", data)
                except Exception as ex:
                    pass

            elif action == 'deleactividad':
                try:
                    data['title'] = u'Eliminar Actividad'
                    data['actividad'] = SagActividades.objects.get(pk=int(request.GET['id']))
                    return render(request, "sagadministracion/deleteactividad.html", data)
                except Exception as ex:
                    pass

            elif action == 'deletemuestra':
                try:
                    data['title'] = u'Eliminar Muestra'
                    data['muestra'] = SagMuestraEncuesta.objects.get(pk=int(request.GET['id']))
                    return render(request, "sagadministracion/deletemuestra.html", data)
                except Exception as ex:
                    pass

            elif action == 'vervisitas':
                try:
                    data['title'] = u'Visitas al modulo'
                    search = None
                    ids = None
                    if 's' in request.GET:
                        search = request.GET['s']
                        visitas = SagVisita.objects.select_related().filter(Q(inscripcion__persona__nombres__icontains=search) |
                                                                            Q(inscripcion__persona__apellido1__icontains=search) |
                                                                            Q(inscripcion__persona__apellido2__icontains=search) |
                                                                            Q(inscripcion__persona__cedula__icontains=search) |
                                                                            Q(inscripcion__persona__pasaporte__icontains=search), status=True).order_by("fecha")
                    elif 'id' in request.GET:
                        ids = request.GET['id']
                        visitas = SagVisita.objects.filter(id=ids).order_by("fecha")
                    else:
                        visitas = SagVisita.objects.filter(status=True).order_by("fecha")
                    paging = MiPaginador(visitas, 5)
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
                    data['page'] = page
                    data['rangospaging'] = paging.rangos_paginado(p)
                    data['visitas'] = page.object_list
                    data['search'] = search if search else ""
                    data['ids'] = ids if ids else ""
                    return render(request, "sagadministracion/vervisitas.html", data)
                except Exception as ex:
                    pass

            elif action == 'importarmuestra':
                try:
                    data['title'] = u'Importar Muestra %s' % data['periodo'].nombre
                    data['periodo'] = SagPeriodo.objects.get(pk=int(encrypt(request.GET['id'])))
                    data['form'] = SagImportarMuestraForm()
                    return render(request, "sagadministracion/importarmuestra.html", data)
                except Exception as ex:
                    pass
            elif action == 'add_est_muestra':
                try:
                    data['periodo'] = SagPeriodo.objects.get(pk=int(encrypt(request.GET['id'])))
                    data['title'] = u'Añadir Estudiante a la muestra %s' % data['periodo'].nombre
                    return render(request, "sagadministracion/addestudiantemuestra.html", data)
                except Exception as ex:
                    pass
            elif action == 'duplicar':
                try:
                    #DUPLICO PERIODO
                    periodo = SagPeriodo.objects.get(pk=request.GET['id'])
                    du_periodo = SagPeriodo(    nombre=periodo.nombre+ '_DUPLICADO',
                                                descripcion = periodo.descripcion,
                                                fechainicio = periodo.fechainicio,
                                                fechafin = periodo.fechafin,
                                                archivo = periodo.archivo,
                                                estado = periodo.estado,
                                                tienemuestra = periodo.tienemuestra,
                                                primeravez =periodo.primeravez)
                    du_periodo.save()
                    #DUPLICO ENCUESTA DEL PERIODO
                    encuesta = SagEncuesta.objects.filter(sagperiodo=periodo)

                    for e in encuesta:
                        du_sga_encuesta = SagEncuesta(
                            sagperiodo=du_periodo,
                            nombre=e.nombre,
                            descripcion=e.descripcion,
                            estado=e.estado,
                            orden=e.orden
                        )

                        du_sga_encuesta.save()
                        #DUPLICO CARRERAS ENCUESTAS
                        encuesta_carrera = SagEncuestaCarrera.objects.filter(sagecuesta=e)
                        for carrera in encuesta_carrera:
                            du_encuesta_carrera = SagEncuestaCarrera(sagecuesta=du_sga_encuesta,
                                                                     carrera=carrera.carrera)
                            du_encuesta_carrera.save(request)

                        # DUPLICO PREGUNTAS ENCUESTAS
                        pregunta_encuesta = SagPreguntaEncuesta.objects.filter(sagencuesta=e)
                        for pregunta in pregunta_encuesta:
                            du_preguntaencuesta = SagPreguntaEncuesta(sagpregunta=pregunta.sagpregunta,
                                                               sagencuesta=du_sga_encuesta,
                                                               observacion=pregunta.observacion,
                                                               orden=pregunta.orden,
                                                               grupo=pregunta.grupo,
                                                               tipo=pregunta.tipo,
                                                               responder=pregunta.responder,
                                                               estado=pregunta.estado)
                            du_preguntaencuesta.save()

                            #DUPLICO ITEMS DE PREGUNTAS
                            encuestaitem = SagEncuestaItem.objects.filter(preguntaencuesta=pregunta)

                            for item in encuestaitem:
                                du_encuestaitem = SagEncuestaItem(preguntaencuesta=du_preguntaencuesta,
                                                               nombre=item.nombre,
                                                               valor=item.valor,
                                                               orden=item.orden,
                                                               tienepredecesora =item.tienepredecesora)
                                du_encuestaitem.save(request)
                                if item.tienepredecesora:
                                    for prede in item.predecesora.all():
                                        # idpreg = int(prede['id'])
                                        du_encuestaitem.predecesora.add(prede)

                            # DUPLICO INDICADOR ENCUESTA
                            indicador = SagIndicadorEncuesta.objects.filter(preguntaencuesta=pregunta)
                            for indi in indicador:
                                du_indi = SagIndicadorEncuesta(indicador=indi.indicador,
                                                            preguntaencuesta=du_preguntaencuesta)
                                du_indi.save(request)


                    #DUPLICO INDICADOR PROYECTO
                    indicador_proyecto = SagIndicadorProyecto.objects.filter(periodo=periodo)
                    for indicador in indicador_proyecto:
                        du_indicador_proyecto = SagIndicadorProyecto(indicador=indicador.indicador,
                                                                     periodo=du_periodo,
                                                                     proyecto = indicador.proyecto)

                        du_indicador_proyecto.save(request)

                    sag_muestra_periodo_carrera = SagMuestraPeriodoCarrera.objects.filter(periodo = periodo)

                    for muestra_periodo_carrer in sag_muestra_periodo_carrera:
                        du_sag_muestra_periodo_carrera = SagMuestraPeriodoCarrera(periodo=du_periodo,
                                                                                  carrera=muestra_periodo_carrer.carrera)
                        du_sag_muestra_periodo_carrera.save(request)


                        # sag_muestraperiodo_carrera_detalle =SagMuestraPeriodoCarreraDetalle.objects.filter(muestraperiodocarrera=sag_muestra_periodo_carrera)
                        #
                        # for detalle in sag_muestraperiodo_carrera_detalle:
                        #     du_sag_muestraperiodo_carrera_detalle = SagMuestraPeriodoCarreraDetalle(muestraperiodocarrera=sag_muestraperiodo_carrera_detalle,
                        #                                                         aniograduacion=detalle.aniograduacion,
                        #                                                         universo=detalle.universo,
                        #                                                         muestreo=detalle.muestreo)
                        #     du_sag_muestraperiodo_carrera_detalle.save(request)



                    return JsonResponse({"result": "ok"})
                except Exception as ex:
                    transaction.set_rollback(True)
                    pass
            elif action == 'vermuestra':
                try:
                    data['title'] = u'Muestras'
                    search = None
                    ids = None
                    idp = int(encrypt(request.GET['idp']))
                    data['periodo'] = periodo = SagPeriodo.objects.get(id=idp)
                    if 's' in request.GET:
                        search = request.GET['s']
                        muestras = SagMuestraEncuesta.objects.select_related().filter(Q(inscripcion__persona__nombres__icontains=search) |
                                                                                      Q(inscripcion__persona__apellido1__icontains=search) |
                                                                                      Q(inscripcion__persona__apellido2__icontains=search) |
                                                                                      Q(inscripcion__persona__cedula__icontains=search) |
                                                                                      Q(inscripcion__persona__pasaporte__icontains=search), status=True, sagperiodo=periodo).order_by("inscripcion")
                    elif 'id' in request.GET:
                        ids = request.GET['id']
                        muestras = SagMuestraEncuesta.objects.filter(status=True, id=ids, sagperiodo=periodo).order_by("inscripcion")
                    else:
                        muestras = SagMuestraEncuesta.objects.filter(status=True, sagperiodo=periodo).order_by("inscripcion")
                    paging = MiPaginador(muestras, 25)
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
                    data['page'] = page
                    data['rangospaging'] = paging.rangos_paginado(p)
                    data['muestras'] = page.object_list
                    data['search'] = search if search else ""
                    data['ids'] = ids if ids else ""
                    return render(request, "sagadministracion/vermuestra.html", data)
                except Exception as ex:
                    pass

            elif action == 'listarespuestapreguntas':
                try:
                    data['title'] = "Opciones de pregunta"
                    data['sagpreguntaencuesta'] = sagpreguntaencuesta = SagPreguntaEncuesta.objects.get(id=request.GET['idpreguntaencuesta'])
                    data['listarespuestas'] = listarespuestas = SagEncuestaItem.objects.filter(preguntaencuesta=sagpreguntaencuesta, status=True).order_by('orden')
                    data['preguntas'] = SagPregunta.objects.filter(status=True)
                    return render(request, "sagadministracion/listarespuestapreguntas.html", data)
                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

            elif action == 'addpredecesora':
                try:
                    data['item'] = item = SagEncuestaItem.objects.get(pk=request.GET['id'])

                    # form = SagPredecesorForm(initial={'predecesora': item.predecesora.all()})
                    form = SagPredecesor2Form()

                    data['title'] = u'Agregar preguntas [%s]' % item.nombre

                    # form.listar(item.preguntaencuesta.sagencuesta)

                    preguntas = []

                    preg = SagPreguntaEncuesta.objects.filter(status=True, sagencuesta=item.preguntaencuesta.sagencuesta).order_by('orden')
                    predecesoras = item.predecesora.all()
                    pred = [p.id for p in predecesoras]

                    for p in preg:
                        preguntas.append([p.sagpregunta.id, p.orden, True if p.sagpregunta.id in pred else False, p.sagpregunta.nombre, p.grupo.id, p.grupo.descripcion])

                    data['preguntas'] = preguntas

                    data['form'] = form
                    return render(request, "sagadministracion/addpredecesora.html", data)
                except Exception as ex:
                    pass

            elif action == 'verlistadopreguntas':
                try:
                    data['title'] = u'Preguntas'
                    muestra = SagMuestraEncuesta.objects.get(pk=request.GET['id'])
                    data['inscripcion'] = inscripcion = muestra.inscripcion
                    data['periodoid'] = periodoid = muestra.sagperiodo.id
                    # if SagResultadoEncuesta.objects.filter(sagperiodo_id=periodoid, inscripcion=inscripcion,status=True):
                    #     return HttpResponseRedirect("/sistemasag")
                    data['listaencuestas'] = listaencuestas = SagEncuesta.objects.filter(sagperiodo_id=periodoid,estado=True,sagencuestacarrera__carrera=inscripcion.carrera,status=True,sagencuestacarrera__status=True).order_by('orden')
                    grupose = []
                    cont = 0
                    for l in listaencuestas:
                        for g in l.listado_gruposencuestas():
                            cont += 1
                            grupose.append((cont, g.get('grupo__id')))
                    data['grupose'] = grupose
                    data['totalgrupo'] = cont
                    preguntass = []
                    for x in listaencuestas:
                        for p in x.listado_preguntas_todo():
                            for res in p.listado_respuesta_predecesoras():
                                listapredecesora = []
                                for predec in res.predecesora.all():
                                    listapredecesora.append([predec.id, predec.grupopredecesora(x).grupo_id])
                                preguntass.append([p.sagpregunta.id, res.id, listapredecesora, p.responder])
                    data['preguntass'] = json.dumps(preguntass)
                    # data['preguntass'] = preguntass
                    # if SagActividades.objects.filter(Q(codigo__icontains='ACT2'), vigente=True, status=True).exists():
                    #     actividad = SagActividades.objects.filter(Q(codigo__icontains='ACT2'), vigente=True, status=True)[0]
                    #     if not SagVisita.objects.filter(status=True, inscripcion=inscripcion, actividad=actividad,fecha=hoy).exists():
                    #         visita = SagVisita(inscripcion=inscripcion, actividad=actividad, fecha=hoy)
                    #         visita.save(request)
                    #     else:
                    #         visita = SagVisita.objects.filter(status=True, inscripcion=inscripcion, actividad=actividad,fecha=hoy)[0]
                    #         visita.numero = visita.numero + 1
                    #         visita.save(request)
                    return render(request, "sagadministracion/verlistadopreguntas.html", data)
                except Exception as ex:
                    pass

            elif action == 'vistaprevia':
                try:
                    data['title'] = u'Preguntas'
                    data['periodo'] = periodo = SagPeriodo.objects.get(pk=request.GET['idperiodo'])
                    data['carrid'] = carrera = int(request.GET['idcarrera'])
                    data['carreras'] = SagEncuestaCarrera.objects.filter(status=True,sagecuesta__sagperiodo=periodo).distinct()
                    data['listaencuestas'] = listaencuestas = SagEncuesta.objects.filter(sagperiodo_id=periodo,estado=True,sagencuestacarrera__carrera_id= carrera,status=True,sagencuestacarrera__status=True).order_by('orden')
                    grupose = []
                    cont = 0
                    for l in listaencuestas:
                        for g in l.listado_gruposencuestas():
                            cont += 1
                            grupose.append((cont, g.get('grupo__id')))
                    data['grupose'] = grupose
                    data['totalgrupo'] = cont
                    preguntass = []
                    for x in listaencuestas:
                        for p in x.listado_preguntas_todo():
                            for res in p.listado_respuesta_predecesoras():
                                listapredecesora = []
                                for predec in res.predecesora.all():
                                    listapredecesora.append([predec.id, predec.grupopredecesora(x).grupo_id])
                                preguntass.append([p.sagpregunta.id, res.id, listapredecesora, p.responder])
                    data['preguntass'] = json.dumps(preguntass)

                    return render(request, "sagadministracion/vistaprevia.html", data)
                except Exception as ex:
                    pass

            elif action == 'reportevistaprevia':
                try:
                    data['title'] = u'Preguntas'
                    periodo = SagPeriodo.objects.get(pk=request.GET['idperiodo'])
                    listaencuestas = SagEncuesta.objects.filter(sagperiodo_id=periodo,estado=True,status=True,sagencuestacarrera__status=True).order_by('orden').distinct()
                    grupose = []
                    cont = 0
                    for l in listaencuestas:
                        for g in l.listado_gruposencuestas():
                            cont += 1
                            grupose.append((cont, g.get('grupo__id')))
                    preguntass = []
                    for x in listaencuestas:
                        for p in x.listado_preguntas_todo():
                            for res in p.listado_respuesta_predecesoras():
                                listapredecesora = []
                                for predec in res.predecesora.all():
                                    listapredecesora.append([predec.id, predec.grupopredecesora(x).grupo_id])
                                preguntass.append([p.sagpregunta.id, res.id, listapredecesora, p.responder])

                    return conviert_html_to_pdf('sagadministracion/reportevistaprevia.html',
                                                {'pagesize': 'A4',
                                                 'periodo': periodo,
                                                 'listaencuestas': listaencuestas,
                                                 'grupose': grupose,
                                                 'totalgrupo': cont,
                                                 'preguntass': json.dumps(preguntass),
                                                 })
                except Exception as ex:
                    pass

            elif action == 'vergraduados':
                try:
                    data['title'] = u'Listado de Graduados'
                    hoy = datetime.now()
                    semana = hoy - timedelta(days=7)
                    querybase = Graduado.objects.filter(status=True,inscripcion__carrera__coordinacion__lte=5).order_by('-id')
                    anio = request.GET.get('anio', '')
                    carrera = request.GET.get('idcar', '')
                    desde = request.GET.get('desde', '')
                    hasta = request.GET.get('hasta', '')
                    search = request.GET.get('search', '')
                    genero = request.GET.get('idg', '')
                    filtros = Q(status=True)
                    url_vars = ''

                    if carrera:
                        data['idcar'] = carrera
                        url_vars += "&idcar={}".format(carrera)
                        filtros = filtros & Q(inscripcion__carrera_id=carrera)
                    if genero:
                        data['idg'] = int(genero)
                        url_vars += "&idg={}".format(genero)
                        filtros = filtros & Q(inscripcion__persona__sexo_id=genero)
                    if search:
                        data['search'] = search
                        s = search.split()
                        url_vars += "&search={}".format(search)
                        filtros = filtros & (Q(inscripcion__persona__apellido1__icontains=search) |
                                             Q(inscripcion__persona__apellido2__icontains=search) |
                                             Q(inscripcion__persona__nombres__icontains=search) |
                                             Q(inscripcion__persona__cedula__icontains=search) |
                                             Q(inscripcion__persona__pasaporte__icontains=search))
                    if desde:
                        data['desde'] = desde
                        url_vars += "&desde={}".format(desde)
                        filtros = filtros & Q(fechaactagrado__gte=desde)
                    if hasta:
                        data['hasta'] = hasta
                        url_vars += "&hasta={}".format(hasta)
                        filtros = filtros & Q(fechaactagrado__lte=hasta)
                    if anio:
                        data['anio'] = anio
                        url_vars += "&anio={}".format(anio)
                        filtros = filtros & Q(fechagraduado__year=anio)

                    data['url_vars'] = url_vars
                    query = querybase.filter(filtros).order_by('pk','inscripcion__carrera__nombre')
                    data['listcount'] = query.count()
                    data['count_hombres'] = query.filter(inscripcion__persona__sexo_id=2).count()
                    data['count_mujeres'] = query.filter(inscripcion__persona__sexo_id=1).count()
                    filtroanio = Q(fechagraduado__year=anio) if anio else Q(status=True)
                    topgraduados = querybase.filter(filtroanio).annotate(carrera=F('inscripcion__carrera__nombre')).values('carrera').annotate(count=Count('inscripcion__carrera')).order_by('-count')
                    data['carrera_mas_graduado'] = topgraduados.first() #se filtra unicamente por año
                    data['carrera_menos_graduado'] = topgraduados.last() #se filtra unicamente por año
                    data['listcarreras'] = carreras = miscarreras.filter(status=True, activa=True,inscripcion__carrera__coordinacion__lte=5).order_by('nombre')
                    data['anios'] = Graduado.objects.filter(status=True, inscripcion__carrera__in=carreras,fechagraduado__isnull=False).annotate(Year=ExtractYear('fechagraduado')).values_list('Year', flat=True).order_by('Year').distinct()
                    data['genero'] = Sexo.objects.filter(status=True)
                    data['ultimosgraduados'] = query.filter(fechagraduado__gte=semana,fechagraduado__lte=hoy)
                    encuesta_anio = anio if anio else hoy.year
                    data['encuestas'] = SagResultadoEncuesta.objects.filter(status=True,sagperiodo__tipo_sagperiodo=1, sagperiodo__fecha_creacion__year=encuesta_anio).distinct('sagperiodo')
                    paging = MiPaginador(query, 30)
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
                    data['page'] = page
                    data['rangospaging'] = paging.rangos_paginado(p)
                    data['graduados'] = page.object_list
                    data['search'] = search if search else ""
                    return render(request, "sagadministracion/vergraduados.html", data)
                except Exception as ex:
                    pass

            elif action == 'exportargraduados':
                try:
                    anio = request.GET.get('anio', '')
                    carrera = request.GET.get('idcar', '')
                    desde = request.GET.get('desde', '')
                    hasta = request.GET.get('hasta', '')
                    search = request.GET.get('search', '')
                    genero = request.GET.get('idg', '')
                    filtros = Q(status=True,inscripcion__carrera__coordinacion__lte=5)
                    if carrera:
                        filtros = filtros & Q(inscripcion__carrera_id=carrera)
                    if genero:
                        filtros = filtros & Q(inscripcion__persona__sexo_id=genero)
                    if search:
                        filtros = filtros & (Q(inscripcion__persona__apellido1__icontains=search) |
                                             Q(inscripcion__persona__apellido2__icontains=search) |
                                             Q(inscripcion__persona__nombres__icontains=search) |
                                             Q(inscripcion__persona__cedula__icontains=search) |
                                             Q(inscripcion__persona__pasaporte__icontains=search))
                    if desde:
                        filtros = filtros & Q(fechaactagrado__gte=desde)
                    if hasta:
                        filtros = filtros & Q(fechaactagrado__lte=hasta)
                    if anio:
                        filtros = filtros & Q(fechagraduado__year=anio)

                    notifi = Notificacion(cuerpo='Generación de reporte de excel en progreso',
                                          titulo='Reporte de graduado para seguimiento',
                                          destinatario=persona,
                                          url='',
                                          prioridad=1, app_label='SGA',
                                          fecha_hora_visible=datetime.now() + timedelta(days=1), tipo=2,
                                          en_proceso=True)
                    notifi.save(request)
                    reportegraduadosfiltro(request=request, notiid=notifi.id,query=filtros).start()
                    return JsonResponse({"result": True,"mensaje": u"El reporte de graduados se está generando. Por favor, verifique su apartado de notificaciones después de unos minutos.","btn_notificaciones": traerNotificaciones(request, data, persona)})
                except Exception as ex:
                    pass

            elif action == 'vertotalencuesta':
                ide = request.GET.get('ide','')
                ida = request.GET.get('anio','')
                anio = int(ida) if ida else datetime.now().year
                try:
                    graduados = set(Graduado.objects.filter(fechagraduado__year=anio,inscripcion__carrera__coordinacion__lte=5).values_list('inscripcion_id', flat=True))
                    if not ida and not ide:
                        encuesta = SagPeriodo.objects.filter(status=True,fecha_creacion__year=anio, primeravez=True,tipo_sagperiodo=1).first()
                        if encuesta is None:
                            return JsonResponse({'result': False, 'mensaje': f'No hay encuesta disponible el periodo {anio}'})
                        encuestados = set(SagResultadoEncuesta.objects.filter(sagperiodo=encuesta.id, status=True,inscripcion__graduado__status=True,sagperiodo__tipo_sagperiodo=1).values_list('inscripcion_id', flat=True))
                        sinencuesta = graduados - encuestados
                        return JsonResponse({'result': True, 'totalencuestados': len(encuestados), 'totalnoencuestados': len(sinencuesta),'encuesta':encuesta.nombre })
                    elif ide:
                        encuesta = SagPeriodo.objects.get(pk=ide)
                        encuestados = set(SagResultadoEncuesta.objects.filter(sagperiodo=encuesta, status=True,inscripcion__graduado__status=True,sagperiodo__tipo_sagperiodo=1).values_list('inscripcion_id', flat=True))
                        if encuesta.tienemuestra:
                            graduados = set(encuesta.sagmuestraencuesta_set.filter(status=True,inscripcion__graduado__status=True,sagperiodo__tipo_sagperiodo=1).values_list('inscripcion_id', flat=True))
                            sinencuesta = graduados - encuestados
                            return JsonResponse({'result': True, 'totalencuestados': len(encuestados),'totalnoencuestados': len(sinencuesta),'encuesta':encuesta.nombre })
                        else:
                            sinencuesta = graduados - encuestados
                            return JsonResponse({'result': True, 'totalencuestados': len(encuestados),'totalnoencuestados': len(sinencuesta),'encuesta':encuesta.nombre })
                    elif ida:
                        encuesta = SagPeriodo.objects.filter(status=True, fecha_creacion__year=anio, tipo_sagperiodo=1)
                        if not encuesta:
                            return JsonResponse({'result': False, 'mensaje': f'No hay encuesta disponible el periodo {ida}'})
                        encuestados = set(SagResultadoEncuesta.objects.filter(sagperiodo=encuesta[0], status=True,inscripcion__graduado__status=True,sagperiodo__tipo_sagperiodo=1).values_list('inscripcion_id', flat=True))
                        sinencuesta = graduados - encuestados
                        return JsonResponse({'result': True, 'totalencuestados': len(encuestados),'totalnoencuestados': len(sinencuesta),'encuesta':encuesta[0].nombre })
                except Exception as ex:
                    return JsonResponse({'result': False, 'mensaje': 'Error al cargar datos de encuesta'})

            # REUTILIZAR esta funcion para multiples reportes de encuestados y sin encuestas
            elif action == 'exportaencuestadosporencuesta':
                ide = request.GET.get('ide', '')
                ida = request.GET.get('ida', '')
                anio = ida if ida else datetime.now().year
                encuesta = SagPeriodo.objects.get(pk=ide)
                try:
                    notifi = Notificacion(cuerpo='Generación de reporte de excel en progreso',
                                          titulo=f'Reporte de encuestados/no encuestados - Encuesta: {encuesta.nombre}',
                                          destinatario=persona,
                                          url='',
                                          prioridad=1, app_label='SGA',
                                          fecha_hora_visible=datetime.now() + timedelta(days=1), tipo=2,
                                          en_proceso=True)
                    notifi.save(request)
                    reporte_exportaencuestadosporencuesta(request=request, notiid=notifi.id,encuesta=ide,anio=anio).start()
                    return JsonResponse({"result": True,"mensaje": f"El reporte de los encuestados/no encuestados está en proceso. Por favor, verifique el apartado de notificaciones después de unos minutos.","btn_notificaciones": traerNotificaciones(request, data, persona)})
                except Exception as ex:
                    pass

            elif action == 'MuestraEncuestaEdCom':
                ida = request.GET.get('idanio', '')
                anio = int(ida) if ida else datetime.now().year
                try:
                    encuesta = SagPeriodo.objects.filter(status=True, tipo_sagperiodo=1, tienemuestra=True,fecha_creacion__year=anio)
                    list_periodo = [{'id': periodo.id, 'nombre': periodo.nombre, 'aplicacurso': periodo.aplicacurso} for periodo in encuesta]
                    return JsonResponse({'result': True, 'data': list_periodo})
                except Exception as ex:
                    return JsonResponse({'result': False, 'mensaje': str(ex)})

            return HttpResponseRedirect(request.path)
        else:
            try:
                eSagEncuestaCarrera_ids = SagEncuestaCarrera.objects.values_list('sagecuesta__sagperiodo_id', flat=True).filter(status=True, carrera__in=miscarreras).distinct()

                data['title'] = u'Listado de Periodos'
                search = None
                ids = None
                if 'id' in request.GET:
                    ids = request.GET['id']
                    periodo = SagPeriodo.objects.filter(pk=ids).order_by('nombre', status=True)
                elif 's' in request.GET:
                    search = request.GET['s']
                    if search.isdigit():
                        periodo = SagPeriodo.objects.select_related().filter(pk=search, status=True)
                    else:
                        periodo = SagPeriodo.objects.select_related().filter(Q(nombre__icontains=search)|
                                                                             Q(descripcion__icontains=search) |
                                                                             Q(fechainicio__icontains=search) |
                                                                             Q(fechafin__icontains=search) , status=True)
                else:
                    periodo = SagPeriodo.objects.select_related().filter(status=True).order_by('-fechainicio')

                if persona.usuario.is_superuser:
                    queryset_union = periodo.filter(pk__in=eSagEncuestaCarrera_ids).union(periodo.filter(sagencuesta__isnull=True))
                else:
                    if puede_realizar_accion_afirmativo(request,'posgrado.es_gestor_de_seguimiento_a_graduados_posgrado'):
                        queryset_union = periodo.filter(pk__in=eSagEncuestaCarrera_ids, tipo_sagperiodo=2).union(periodo.filter(sagencuesta__isnull=True, tipo_sagperiodo=2))
                    else:
                        queryset_union = periodo.filter(pk__in=eSagEncuestaCarrera_ids, tipo_sagperiodo=1).union(periodo.filter(sagencuesta__isnull=True, tipo_sagperiodo=1))


                paging = MiPaginador(queryset_union.order_by('-fechainicio'), 5)
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
                data['page'] = page
                data['rangospaging'] = paging.rangos_paginado(p)
                data['periodograduados'] = page.object_list
                data['search'] = search if search else ""
                data['ids'] = ids if ids else ""
                data['puede_configurar'] = puede_realizar_accion_afirmativo(request, 'sga.puede_configurar_sag')
                return render(request, "sagadministracion/view.html", data)
            except Exception as ex:
                return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})
