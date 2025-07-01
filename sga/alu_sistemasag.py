# -*- coding: UTF-8 -*-
from datetime import datetime, timedelta
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.db.models.query_utils import Q
from django.http import HttpResponseRedirect, JsonResponse
from django.shortcuts import render
from decorators import secure_module, last_access
from sagest.forms import DatosPersonalesForm, EtniaForm, DatosDomicilioForm, DatosNacimientoForm, TitulacionPersonaForm, \
    ArchivoTitulacionForm, FamiliarForm, ExperienciaLaboralForm, ArchivoExperienciaForm
from sagest.models import ExperienciaLaboral, CapEventoPeriodoIpec, CapInscritoIpec, MOTIVOCANCELACIONCUPO, \
    HistorialInscripcionEventoPeriodoIpec
from sga.commonviews import adduserdata, obtener_reporte
from sga.forms import SagEncuestasFrom, PeriodoSagForm
from sga.funciones import generar_nombre, log, MiPaginador
from sga.models import Graduado, Carrera, SagPeriodo, SagEncuesta, \
    SagPreguntaEncuesta, SagEncuestaItem, SagEncuestaCarrera, \
    SagResultadoEncuesta, SagResultadoEncuestaDetalle, Egresado, Persona, NivelTitulacion, Titulacion, \
    PersonaDatosFamiliares, SagVisita, SagActividades, SagMuestraEncuesta, MateriaAsignada
from sga.funcionesxhtml2pdf import conviert_html_to_pdf
import json
from django.core.cache import cache
from sga.templatetags.sga_extras import encrypt


@login_required(redirect_field_name='ret', login_url='/loginsga')
@secure_module
@last_access
@transaction.atomic()
def view(request):
    data = {}
    adduserdata(request, data)
    persona = request.session['persona']
    perfilprincipal = request.session['perfilprincipal']
    if not perfilprincipal.es_estudiante():
        return HttpResponseRedirect("/?info=Solo los perfiles de estudiantes pueden ingresar al modulo.")
    inscripcion = perfilprincipal.inscripcion
    miscarreras = persona.mis_carreras()
    hoy = datetime.now().date()
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
                listarespuestas = SagEncuestaItem.objects.filter(preguntaencuesta=encuestaitem.preguntaencuesta,
                                                                 status=True).order_by('orden')
                lista = []
                for listarespuesta in listarespuestas:
                    datadoc = {}
                    datadoc['id'] = listarespuesta.id
                    datadoc['nombre'] = listarespuesta.nombre
                    datadoc['valor'] = listarespuesta.valor
                    datadoc['orden'] = listarespuesta.orden
                    lista.append(datadoc)
                return JsonResponse({'result': 'ok', 'lista': lista})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": "Error al guardar los datos."})

        elif action == 'pdfcertificado':
            try:
                data = {}
                data['periodoencuesta'] = SagPeriodo.objects.get(pk=request.POST['periodoencuesta'])
                data['inscripcion'] = inscripcion
                return conviert_html_to_pdf(
                    'alu_sistemasag/certificado_pdf.html',
                    {
                        'pagesize': 'A4',
                        'data': data,
                    }
                )
            except Exception as ex:
                pass

        elif action == 'addrespuestaencuesta':
            try:
                TIEMPO_ENCACHE = 60 * 60 * 60
                datos = request.POST['cadenaitems']
                resultado = SagResultadoEncuesta(inscripcion=inscripcion,
                                                 sagperiodo_id=request.POST['periodoid'])
                resultado.save(request)
                cadenadatos = datos.split('&')
                for cadena in cadenadatos:
                    if cadena:
                        liscadena = cadena.split('_')
                        numerotipo = liscadena[1]
                        pregunta = liscadena[2].split('=')
                        spe = SagPreguntaEncuesta.objects.filter(id=int(pregunta[0]))[0].sagpregunta.nombre
                        if (str(pregunta[1]).isnumeric() and int(pregunta[1]) < 0):
                            transaction.set_rollback(True)
                            return JsonResponse({"result": "bad",
                                                 "mensaje": "Los valores numéricos que ingresó no deben ser negativos. %s = %s" % (
                                                     spe, pregunta[1])})
                        resultadovalores = SagResultadoEncuestaDetalle(sagresultadoencuesta=resultado,
                                                                       preguntaencuesta_id=pregunta[0],
                                                                       valor=str(int(pregunta[1]) if str(
                                                                           pregunta[1]).isnumeric() else pregunta[1]),
                                                                       numero=numerotipo)
                        resultadovalores.save(request)
                cache.delete(f"encuestaegresado_por_contestar_alumnos_panel_{encrypt(inscripcion.id)}")
                cache.set(f"encuestaegresado_por_contestar_alumnos_panel_{encrypt(inscripcion.id)}", [{"id": 1, "pendiente": False}], TIEMPO_ENCACHE)
                # if SagActividades.objects.filter(Q(codigo__icontains='ACT3'), vigente=True ,status=True).exists():
                #     actividad = SagActividades.objects.filter(Q(codigo__icontains='ACT3'), vigente=True ,status=True)[0]
                #     if not SagVisita.objects.filter(status=True, inscripcion=inscripcion, actividad=actividad, fecha=hoy).exists():
                #         visita =  SagVisita(inscripcion=inscripcion, actividad=actividad, fecha=hoy)
                #         visita.save(request)
                #     else:
                #         visita = SagVisita.objects.filter(status=True, inscripcion=inscripcion, actividad=actividad, fecha=hoy)[0]
                #         visita.numero=visita.numero+1
                #         visita.save(request)
                succes_url = 'ret' if resultado.sagperiodo.aplicacurso else 'ok'
                return JsonResponse({"result": f"{succes_url}"})
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
                return JsonResponse({'result': 'ok'})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": "Error al guardar los datos."})

        elif action == 'listarespuestapreguntas':
            try:
                listarespuestas = SagEncuestaItem.objects.select_related().filter(
                    preguntaencuesta_id=request.POST['idpreguntaencuesta'], status=True).order_by('orden')
                lista = []
                for listarespuesta in listarespuestas:
                    datadoc = {}
                    datadoc['id'] = listarespuesta.id
                    datadoc['nombre'] = listarespuesta.nombre
                    datadoc['valor'] = listarespuesta.valor
                    datadoc['orden'] = listarespuesta.orden
                    lista.append(datadoc)
                return JsonResponse({'result': 'ok', 'lista': lista})
            except Exception as ex:
                return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

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
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": "Error al guardar los datos."})

        elif action == 'delpreguntarespuesta':
            try:
                respuestapreguntas = SagEncuestaItem.objects.get(pk=request.POST['idrespuesta'], status=True)
                respuestapreguntas.status = False
                respuestapreguntas.save(request)
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": "Error al eliminar los datos."})

        elif action == 'delencuestapregunta':
            try:
                preguntaencuesta = SagPreguntaEncuesta.objects.get(pk=request.POST['idepregunta'], status=True)
                preguntaencuesta.status = False
                preguntaencuesta.save(request)
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": "Error al eliminar los datos."})

        elif action == 'adicionarencuestacarrera':
            try:
                valor = 0
                if SagEncuestaCarrera.objects.filter(sagecuesta_id=request.POST['encuestaid'],
                                                     carrera_id=request.POST['carreraid'], status=True):
                    encuesta = SagEncuestaCarrera.objects.get(sagecuesta=request.POST['encuestaid'],
                                                              carrera_id=request.POST['carreraid'], status=True)
                    encuesta.status = False
                    encuesta.save(request)
                else:
                    encuesta = SagEncuestaCarrera(sagecuesta_id=request.POST['encuestaid'],
                                                  carrera_id=request.POST['carreraid'])
                    encuesta.save(request)
                    valor = 1
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
                return JsonResponse(
                    {"result": "ok", "nombre": request.POST['resdescripcion'], "resvalor": request.POST['resvalor'],
                     "resorden": request.POST['resorden']})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": "Error al eliminar los datos."})

        elif action == 'conpreguntarespuesta':
            try:
                respuestapreguntas = SagEncuestaItem.objects.get(pk=request.POST['idres'], status=True)
                nombre = respuestapreguntas.nombre
                return JsonResponse({"result": "ok", "nombre": nombre})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": "Error al eliminar los datos."})

        elif action == 'conpreguntaencuesta':
            try:
                preguntaencuesta = SagPreguntaEncuesta.objects.get(pk=request.POST['idepreg'], status=True)
                nombre = preguntaencuesta.sagpregunta.nombre
                return JsonResponse({"result": "ok", "nombre": nombre})
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
                return JsonResponse(
                    {"result": "ok", "codigo": codigo, "nombre": nombre, "valor": valor, "orden": orden})
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
                    sagperiodo.nombre = f.cleaned_data['nombre']
                    sagperiodo.descripcion = f.cleaned_data['descripcion']
                    sagperiodo.fechainicio = f.cleaned_data['fechainicio']
                    sagperiodo.fechafin = f.cleaned_data['fechafin']
                    sagperiodo.save(request)
                    return JsonResponse({"result": "ok"})
                else:
                    raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'datospersonales':
            try:
                persona = request.session['persona']
                f = DatosPersonalesForm(request.POST)
                if f.is_valid():
                    persona.pasaporte = f.cleaned_data['pasaporte']
                    persona.anioresidencia = f.cleaned_data['anioresidencia']
                    persona.nacimiento = f.cleaned_data['nacimiento']
                    persona.telefonoextension = f.cleaned_data['extension']
                    persona.nacionalidad = f.cleaned_data['nacionalidad']
                    persona.sexo = f.cleaned_data['sexo']
                    persona.lgtbi = f.cleaned_data['lgtbi']
                    persona.email = f.cleaned_data['email']
                    persona.libretamilitar = f.cleaned_data['libretamilitar']
                    persona.save(request)
                    personaextension = persona.datos_extension()
                    personaextension.estadocivil = f.cleaned_data['estadocivil']
                    personaextension.save(request)
                    request.session['personales'] = 1
                    if Graduado.objects.filter(status=True, inscripcion__persona__id=persona.id).exists():
                        datos = Persona.objects.get(status=True, id=persona.id)
                        if 'personales' in request.session and 'nacimiento' in request.session and 'domicilio' in request.session and 'etnia' in request.session and 'instruccion' in request.session and datos.datosactualizados == 0:
                            if request.session['personales'] == 1 and request.session['nacimiento'] == 1 and \
                                    request.session['domicilio'] == 1 and request.session['etnia'] == 1 and \
                                    request.session['instruccion'] == 1 and datos.datosactualizados == 0:
                                datos.datosactualizados = 1
                                datos.save(request)
                    log(u'Modifico datos personales: %s' % persona, request, "edit")
                    return JsonResponse({'result': 'ok'})
                else:
                    raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({'result': 'bad', 'mensaje': u'Error al guardar los datos'})

        elif action == 'datosnacimiento':
            try:
                persona = request.session['persona']
                f = DatosNacimientoForm(request.POST)
                if f.is_valid():
                    persona.paisnacimiento = f.cleaned_data['paisnacimiento']
                    persona.provincianacimiento = f.cleaned_data['provincianacimiento']
                    persona.cantonnacimiento = f.cleaned_data['cantonnacimiento']
                    persona.parroquianacimiento = f.cleaned_data['parroquianacimiento']
                    persona.save(request)
                    request.session['nacimiento'] = 1
                    if Graduado.objects.filter(status=True, inscripcion__persona__id=persona.id).exists():
                        datos = Persona.objects.get(status=True, id=persona.id)
                        if 'personales' in request.session and 'nacimiento' in request.session and 'domicilio' in request.session and 'etnia' in request.session and 'instruccion' in request.session and datos.datosactualizados == 0:
                            if request.session['personales'] == 1 and request.session['nacimiento'] == 1 and \
                                    request.session['domicilio'] == 1 and request.session['etnia'] == 1 and \
                                    request.session['instruccion'] == 1 and datos.datosactualizados == 0:
                                datos.datosactualizados = 1
                                datos.save(request)
                    log(u'Modifico datos de nacimiento: %s' % persona, request, "edit")
                    return JsonResponse({'result': 'ok'})
                else:
                    raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({'result': 'bad', 'mensaje': u'Error al guardar los datos'})

        elif action == 'datosdomicilio':
            try:
                if 'archivocroquis' in request.FILES:
                    newfile = request.FILES['archivocroquis']
                    if newfile.size > 2194304:
                        return JsonResponse(
                            {"result": "bad", "mensaje": u"Error, Tamaño de archivo Maximo permitido es de 2Mb"})
                persona = request.session['persona']
                f = DatosDomicilioForm(request.POST)
                if f.is_valid():
                    newfile = None
                    persona.pais = f.cleaned_data['pais']
                    persona.provincia = f.cleaned_data['provincia']
                    persona.canton = f.cleaned_data['canton']
                    persona.parroquia = f.cleaned_data['parroquia']
                    persona.direccion = f.cleaned_data['direccion']
                    persona.direccion2 = f.cleaned_data['direccion2']
                    persona.num_direccion = f.cleaned_data['num_direccion']
                    persona.telefono_conv = f.cleaned_data['telefono_conv']
                    persona.telefono = f.cleaned_data['telefono']
                    persona.tipocelular = f.cleaned_data['tipocelular']
                    persona.referencia = f.cleaned_data['referencia']
                    persona.sector = f.cleaned_data['sector']
                    persona.save(request)
                    if 'archivocroquis' in request.FILES:
                        newfile = request.FILES['archivocroquis']
                        newfile._name = generar_nombre("croquis_", newfile._name)
                        persona.archivocroquis = newfile
                        persona.save(request)
                    request.session['domicilio'] = 1
                    if Graduado.objects.filter(status=True, inscripcion__persona__id=persona.id).exists():
                        datos = Persona.objects.get(status=True, id=persona.id)
                        if 'personales' in request.session and 'nacimiento' in request.session and 'domicilio' in request.session and 'etnia' in request.session and 'instruccion' in request.session and datos.datosactualizados == 0:
                            if request.session['personales'] == 1 and request.session['nacimiento'] == 1 and \
                                    request.session['domicilio'] == 1 and request.session['etnia'] == 1 and \
                                    request.session['instruccion'] == 1 and datos.datosactualizados == 0:
                                datos.datosactualizados = 1
                                datos.save(request)
                    log(u'Modifico datos de domicilio: %s' % persona, request, "edit")
                    return JsonResponse({'result': 'ok'})
                else:
                    raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({'result': 'bad', 'mensaje': u'Error al guardar los datos'})

        elif action == 'etnia':
            try:
                persona = request.session['persona']
                f = EtniaForm(request.POST)
                if f.is_valid():
                    perfil = persona.mi_perfil()
                    perfil.raza = f.cleaned_data['raza']
                    perfil.nacionalidadindigena = f.cleaned_data['nacionalidadindigena']
                    perfil.save(request)
                    request.session['etnia'] = 1
                    if Graduado.objects.filter(status=True, inscripcion__persona__id=persona.id).exists():
                        datos = Persona.objects.get(status=True, id=persona.id)
                        if 'personales' in request.session and 'nacimiento' in request.session and 'domicilio' in request.session and 'etnia' in request.session and 'instruccion' in request.session and datos.datosactualizados == 0:
                            if request.session['personales'] == 1 and request.session['nacimiento'] == 1 and \
                                    request.session['domicilio'] == 1 and request.session['etnia'] == 1 and \
                                    request.session['instruccion'] == 1 and datos.datosactualizados == 0:
                                datos.datosactualizados = 1
                                datos.save(request)
                    log(u'Modifico etnia: %s' % persona, request, "edit")
                    return JsonResponse({'result': 'ok'})
                else:
                    raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({'result': 'bad', 'mensaje': u'Error al guardar los datos'})

        elif action == 'addfamiliar':
            try:
                persona = request.session['persona']
                f = FamiliarForm(request.POST)
                if f.is_valid():
                    if persona.personadatosfamiliares_set.filter(
                            identificacion=f.cleaned_data['identificacion']).exists():
                        return JsonResponse({'result': 'bad', 'mensaje': u'El familiar se encuentra registrado.'})
                    familiar = PersonaDatosFamiliares(persona=persona,
                                                      identificacion=f.cleaned_data['identificacion'],
                                                      nombre=f.cleaned_data['nombre'],
                                                      fallecido=f.cleaned_data['fallecido'],
                                                      nacimiento=f.cleaned_data['nacimiento'],
                                                      parentesco=f.cleaned_data['parentesco'],
                                                      tienediscapacidad=f.cleaned_data['tienediscapacidad'],
                                                      telefono=f.cleaned_data['telefono'],
                                                      telefono_conv=f.cleaned_data['telefono_conv'],
                                                      niveltitulacion=f.cleaned_data['niveltitulacion'],
                                                      ingresomensual=f.cleaned_data['ingresomensual'],
                                                      formatrabajo=f.cleaned_data['formatrabajo'],
                                                      trabajo=f.cleaned_data['trabajo'],
                                                      convive=f.cleaned_data['convive'],
                                                      sustentohogar=f.cleaned_data['sustentohogar'])
                    familiar.save(request)
                    log(u'Adiciono familiar: %s' % persona, request, "add")
                    return JsonResponse({'result': 'ok'})
                else:
                    raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({'result': 'bad', 'mensaje': u'Error al guardar los datos'})

        elif action == 'editfamiliar':
            try:
                persona = request.session['persona']
                f = FamiliarForm(request.POST)
                if f.is_valid():
                    familiar = PersonaDatosFamiliares.objects.get(pk=int(request.POST['id']))
                    if persona.personadatosfamiliares_set.filter(
                            identificacion=f.cleaned_data['identificacion']).exclude(id=familiar.id).exists():
                        return JsonResponse({'result': 'bad', 'mensaje': u'El familiar se encuentra registrado.'})
                    familiar.identificacion = f.cleaned_data['identificacion']
                    familiar.nombre = f.cleaned_data['nombre']
                    familiar.fallecido = f.cleaned_data['fallecido']
                    familiar.nacimiento = f.cleaned_data['nacimiento']
                    familiar.parentesco = f.cleaned_data['parentesco']
                    familiar.tienediscapacidad = f.cleaned_data['tienediscapacidad']
                    familiar.telefono = f.cleaned_data['telefono']
                    familiar.telefono_conv = f.cleaned_data['telefono_conv']
                    familiar.trabajo = f.cleaned_data['trabajo']
                    familiar.niveltitulacion = f.cleaned_data['niveltitulacion']
                    familiar.ingresomensual = f.cleaned_data['ingresomensual']
                    familiar.formatrabajo = f.cleaned_data['formatrabajo']
                    familiar.convive = f.cleaned_data['convive']
                    familiar.sustentohogar = f.cleaned_data['sustentohogar']
                    familiar.save(request)
                    log(u'Modifico familiar: %s' % persona, request, "edit")
                    return JsonResponse({'result': 'ok'})
                else:
                    raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({'result': 'bad', 'mensaje': u'Error al guardar los datos'})

        elif action == 'delfamiliar':
            try:
                persona = request.session['persona']
                familiar = PersonaDatosFamiliares.objects.get(pk=int(request.POST['id']))
                familiar.delete()
                log(u'Elimino familiar: %s' % persona, request, "del")
                return JsonResponse({'result': 'ok'})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({'result': 'bad', 'mensaje': u'Error al eliminar los datos'})

        elif action == 'addtitulacion':
            try:
                persona = request.session['persona']
                f = TitulacionPersonaForm(request.POST, request.FILES)
                if f.is_valid():
                    titulacion = Titulacion(persona=persona,
                                            titulo=f.cleaned_data['titulo'],
                                            areatitulo=f.cleaned_data['areatitulo'],
                                            fechainicio=f.cleaned_data['fechainicio'],
                                            fechaobtencion=f.cleaned_data['fechaobtencion'],
                                            fechaegresado=f.cleaned_data['fechaegresado'],
                                            registro=f.cleaned_data['registro'],
                                            # areaconocimiento=f.cleaned_data['areaconocimiento'],
                                            # subareaconocimiento=f.cleaned_data['subareaconocimiento'],
                                            # subareaespecificaconocimiento=f.cleaned_data['subareaespecificaconocimiento'],
                                            pais=f.cleaned_data['pais'],
                                            provincia=f.cleaned_data['provincia'],
                                            canton=f.cleaned_data['canton'],
                                            parroquia=f.cleaned_data['parroquia'],
                                            educacionsuperior=f.cleaned_data['educacionsuperior'],
                                            institucion=f.cleaned_data['institucion'],
                                            colegio=f.cleaned_data['colegio'],
                                            anios=f.cleaned_data['anios'],
                                            semestres=f.cleaned_data['semestres'],
                                            cursando=f.cleaned_data['cursando'],
                                            aplicobeca=f.cleaned_data['aplicobeca'],
                                            tipobeca=f.cleaned_data['tipobeca'] if f.cleaned_data[
                                                'aplicobeca'] else None,
                                            financiamientobeca=f.cleaned_data['financiamientobeca'] if f.cleaned_data[
                                                'aplicobeca'] else None,
                                            valorbeca=f.cleaned_data['valorbeca'] if f.cleaned_data[
                                                'aplicobeca'] else 0)
                    titulacion.save(request)
                    if not titulacion.cursando:
                        if 'archivo' in request.FILES:
                            newfile = request.FILES['archivo']
                            if newfile:
                                newfile._name = generar_nombre("titulacion_", newfile._name)
                                titulacion.archivo = newfile
                                titulacion.save(request)
                    request.session['instruccion'] = 1
                    if Graduado.objects.filter(status=True, inscripcion__persona__id=persona.id).exists():
                        datos = Persona.objects.get(status=True, id=persona.id)
                        if 'personales' in request.session and 'nacimiento' in request.session and 'domicilio' in request.session and 'etnia' in request.session and 'instruccion' in request.session and datos.datosactualizados == 0:
                            if request.session['personales'] == 1 and request.session['nacimiento'] == 1 and \
                                    request.session['domicilio'] == 1 and request.session['etnia'] == 1 and \
                                    request.session['instruccion'] == 1 and datos.datosactualizados == 0:
                                datos.datosactualizados = 1
                                datos.save(request)
                    log(u'Adiciono titulacion: %s' % persona, request, "add")
                    return JsonResponse({'result': 'ok'})
                else:
                    raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({'result': 'bad', 'mensaje': u'Error al guardar los datos'})

        elif action == 'addarchivotitulacion':
            try:
                persona = request.session['persona']
                f = ArchivoTitulacionForm(request.POST, request.FILES)
                if f.is_valid():
                    titulacion = Titulacion.objects.get(pk=int(request.POST['id']))
                    newfile = request.FILES['archivo']
                    newfile._name = generar_nombre("titulacion_", newfile._name)
                    titulacion.archivo = newfile
                    titulacion.save(request)
                    request.session['instruccion'] = 1
                    if Graduado.objects.filter(status=True, inscripcion__persona__id=persona.id).exists():
                        datos = Persona.objects.get(status=True, id=persona.id)
                        if 'personales' in request.session and 'nacimiento' in request.session and 'domicilio' in request.session and 'etnia' in request.session and 'instruccion' in request.session and datos.datosactualizados == 0:
                            if request.session['personales'] == 1 and request.session['nacimiento'] == 1 and \
                                    request.session['domicilio'] == 1 and request.session['etnia'] == 1 and \
                                    request.session['instruccion'] == 1 and datos.datosactualizados == 0:
                                datos.datosactualizados = 1
                                datos.save(request)
                    log(u'Adiciono archivo de titulacion: %s' % persona, request, "add")
                    return JsonResponse({'result': 'ok'})
                else:
                    raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({'result': 'bad', 'mensaje': u'Error al guardar los datos'})

        elif action == 'edittitulacion':
            try:
                persona = request.session['persona']
                f = TitulacionPersonaForm(request.POST, request.FILES)
                if f.is_valid():
                    titulacion = Titulacion.objects.get(pk=int(request.POST['id']))
                    titulacion.titulo = f.cleaned_data['titulo']
                    titulacion.areatitulo = f.cleaned_data['areatitulo']
                    titulacion.fechainicio = f.cleaned_data['fechainicio']
                    titulacion.fechaobtencion = f.cleaned_data['fechaobtencion']
                    titulacion.fechaegresado = f.cleaned_data['fechaegresado']
                    titulacion.registro = f.cleaned_data['registro']
                    # titulacion.areaconocimiento = f.cleaned_data['areaconocimiento']
                    # titulacion.subareaconocimiento = f.cleaned_data['subareaconocimiento']
                    # titulacion.subareaespecificaconocimiento = f.cleaned_data['subareaespecificaconocimiento']
                    titulacion.pais = f.cleaned_data['pais']
                    titulacion.provincia = f.cleaned_data['provincia']
                    titulacion.canton = f.cleaned_data['canton']
                    titulacion.parroquia = f.cleaned_data['parroquia']
                    titulacion.educacionsuperior = f.cleaned_data['educacionsuperior']
                    titulacion.institucion = f.cleaned_data['institucion']
                    titulacion.colegio = f.cleaned_data['colegio']
                    titulacion.anios = f.cleaned_data['anios']
                    titulacion.semestres = f.cleaned_data['semestres']
                    titulacion.cursando = f.cleaned_data['cursando']
                    titulacion.aplicobeca = f.cleaned_data['aplicobeca']
                    titulacion.tipobeca = f.cleaned_data['tipobeca'] if f.cleaned_data['aplicobeca'] else None
                    titulacion.financiamientobeca = f.cleaned_data['financiamientobeca'] if f.cleaned_data[
                        'aplicobeca'] else None
                    titulacion.valorbeca = f.cleaned_data['valorbeca'] if f.cleaned_data['aplicobeca'] else 0
                    titulacion.save(request)
                    if 'archivo' in request.FILES:
                        newfile = request.FILES['archivo']
                        newfile._name = generar_nombre("titulacion_", newfile._name)
                        titulacion.archivo = newfile
                        titulacion.save(request)
                    request.session['instruccion'] = 1
                    if Graduado.objects.filter(status=True, inscripcion__persona__id=persona.id).exists():
                        datos = Persona.objects.get(status=True, id=persona.id)
                        if 'personales' in request.session and 'nacimiento' in request.session and 'domicilio' in request.session and 'etnia' in request.session and 'instruccion' in request.session and datos.datosactualizados == 0:
                            if request.session['personales'] == 1 and request.session['nacimiento'] == 1 and \
                                    request.session['domicilio'] == 1 and request.session['etnia'] == 1 and \
                                    request.session['instruccion'] == 1 and datos.datosactualizados == 0:
                                datos.datosactualizados = 1
                                datos.save(request)
                    log(u'Modifico titulacion: %s' % persona, request, "edit")
                    return JsonResponse({'result': 'ok'})
                else:
                    raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({'result': 'bad', 'mensaje': u'Error al guardar los datos'})

        elif action == 'deltitulacion':
            try:
                persona = request.session['persona']
                titulacion = Titulacion.objects.get(pk=int(request.POST['id']))
                if titulacion.verificado:
                    return JsonResponse({'result': 'bad', 'mensaje': u'No puede eliminar el titulo.'})
                log(u'Elimino titulacion: %s' % titulacion, request, "del")
                titulacion.delete()
                request.session['instruccion'] = 1
                if Graduado.objects.filter(status=True, inscripcion__persona__id=persona.id).exists():
                    datos = Persona.objects.get(status=True, id=persona.id)
                    if 'personales' in request.session and 'nacimiento' in request.session and 'domicilio' in request.session and 'etnia' in request.session and 'instruccion' in request.session and datos.datosactualizados == 0:
                        if request.session['personales'] == 1 and request.session['nacimiento'] == 1 and \
                                request.session['domicilio'] == 1 and request.session['etnia'] == 1 and \
                                request.session['instruccion'] == 1 and datos.datosactualizados == 0:
                            datos.datosactualizados = 1
                            datos.save(request)
                return JsonResponse({'result': 'ok'})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({'result': 'bad', 'mensaje': u'Error al eliminar los datos'})

        elif action == 'addexperiencia':
            try:
                persona = request.session['persona']
                form = ExperienciaLaboralForm(request.POST, request.FILES)
                if form.is_valid():
                    experiencialaboral = ExperienciaLaboral(persona=persona,
                                                            tipoinstitucion=form.cleaned_data[
                                                                'tipoinstitucion'],
                                                            institucion=form.cleaned_data['institucion'],
                                                            cargo=form.cleaned_data['cargo'],
                                                            departamento=form.cleaned_data['departamento'],
                                                            pais=form.cleaned_data['pais'],
                                                            provincia=form.cleaned_data['provincia'],
                                                            canton=form.cleaned_data['canton'],
                                                            parroquia=form.cleaned_data['parroquia'],
                                                            fechainicio=form.cleaned_data['fechainicio'],
                                                            fechafin=form.cleaned_data['fechafin'],
                                                            motivosalida=form.cleaned_data['motivosalida'],
                                                            regimenlaboral=form.cleaned_data['regimenlaboral'],
                                                            horassemanales=form.cleaned_data['horassemanales'],
                                                            dedicacionlaboral=form.cleaned_data[
                                                                'dedicacionlaboral'],
                                                            actividadlaboral=form.cleaned_data[
                                                                'actividadlaboral'],
                                                            observaciones=form.cleaned_data['observaciones'])
                    experiencialaboral.save(request)
                    if 'archivo' in request.FILES:
                        newfile = request.FILES['archivo']
                        newfile._name = generar_nombre("experiencialaboral_", newfile._name)
                        experiencialaboral.archivo = newfile
                        experiencialaboral.save(request)
                    log(u'Adiciono experiencia laboral: %s' % experiencialaboral, request, "add")
                    return JsonResponse({'result': 'ok'})
                else:
                    raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({'result': 'bad', 'mensaje': u'Error al guardar los datos'})

        elif action == 'editexperiencia':
            try:
                persona = request.session['persona']
                form = ExperienciaLaboralForm(request.POST, request.FILES)
                if form.is_valid():
                    experiencialaboral = ExperienciaLaboral.objects.get(pk=int(request.POST['id']))
                    experiencialaboral.tipoinstitucion = form.cleaned_data['tipoinstitucion']
                    experiencialaboral.institucion = form.cleaned_data['institucion']
                    experiencialaboral.cargo = form.cleaned_data['cargo']
                    experiencialaboral.departamento = form.cleaned_data['departamento']
                    experiencialaboral.pais = form.cleaned_data['pais']
                    experiencialaboral.provincia = form.cleaned_data['provincia']
                    experiencialaboral.canton = form.cleaned_data['canton']
                    experiencialaboral.parroquia = form.cleaned_data['parroquia']
                    experiencialaboral.fechainicio = form.cleaned_data['fechainicio']
                    experiencialaboral.fechafin = form.cleaned_data['fechafin']
                    experiencialaboral.motivosalida = form.cleaned_data['motivosalida']
                    experiencialaboral.regimenlaboral = form.cleaned_data['regimenlaboral']
                    experiencialaboral.horassemanales = form.cleaned_data['horassemanales']
                    experiencialaboral.dedicacionlaboral = form.cleaned_data['dedicacionlaboral']
                    experiencialaboral.actividadlaboral = form.cleaned_data['actividadlaboral']
                    experiencialaboral.observaciones = form.cleaned_data['observaciones']
                    experiencialaboral.save(request)
                    if 'archivo' in request.FILES:
                        newfile = request.FILES['archivo']
                        newfile._name = generar_nombre("experiencialaboral_", newfile._name)
                        experiencialaboral.archivo = newfile
                        experiencialaboral.save(request)
                    log(u'Modifico experiencia laboral: %s' % experiencialaboral, request, "add")
                    return JsonResponse({'result': 'ok'})
                else:
                    raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({'result': 'bad', 'mensaje': u'Error al guardar los datos'})

        elif action == 'delexperiencia':
            try:
                experiencia = ExperienciaLaboral.objects.get(pk=request.POST['id'])
                log(u"Elimino experiencia laboral: %s" % experiencia, request, "del")
                experiencia.delete()
                return JsonResponse({'result': 'ok'})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({'result': 'bad', 'mensaje': u'Error al eliminar los datos'})

        elif action == 'addarchivoexperiencia':
            try:
                persona = request.session['persona']
                f = ArchivoExperienciaForm(request.POST, request.FILES)
                if f.is_valid():
                    titulacion = ExperienciaLaboral.objects.get(pk=int(request.POST['id']))
                    newfile = request.FILES['archivo']
                    newfile._name = generar_nombre("experiencialaboral_", newfile._name)
                    titulacion.archivo = newfile
                    titulacion.save(request)
                    log(u'Adiciono archivo de referncia laboral: %s' % persona, request, "add")
                    return JsonResponse({'result': 'ok'})
                else:
                    raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({'result': 'bad', 'mensaje': u'Error al guardar los datos'})
                # data['title'] = u'Encuesta'
                # search = None
                # ids = None
                # inscripcionid = None
                # data['periodossag'] = SagPeriodo.objects.filter(estado=True, status=True)
                # return render(request, "alu_sistemasag/view.html", data)
                # # return JsonResponse({"result": "bad", "mensaje": u"Solicitud Incorrecta."})

        elif action == 'addvisitacertificado':
            try:
                if SagActividades.objects.filter(Q(codigo__icontains='ACT4'), vigente=True, status=True).exists():
                    actividad = SagActividades.objects.filter(Q(codigo__icontains='ACT4'), vigente=True, status=True)[0]
                    if not SagVisita.objects.filter(status=True, inscripcion=inscripcion, actividad=actividad,
                                                    fecha=hoy).exists():
                        visita = SagVisita(inscripcion=inscripcion, actividad=actividad, fecha=hoy)
                        visita.save(request)
                    else:
                        visita = \
                            SagVisita.objects.filter(status=True, inscripcion=inscripcion, actividad=actividad, fecha=hoy)[
                                0]
                        visita.numero = visita.numero + 1
                        visita.save(request)
                return JsonResponse({'result': 'ok'})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({'result': 'bad', 'mensaje': u'Error al guardar los datos'})

        elif action == 'inscripciongraduado':
            try:
                participante = Persona.objects.get(pk=request.POST['idestudiante'])
                curso = CapEventoPeriodoIpec.objects.get(pk=request.POST['cursoid'])
                if CapInscritoIpec.objects.filter(status=True,capeventoperiodo__seguimientograduado=True, capeventoperiodo__fechainicioinscripcion__year=datetime.now().year, participante=participante).exists():
                    return JsonResponse({"result": "bad", "mensaje": u"Usted ya se encuentra inscrito en un curso."})
                if not curso.hay_cupo_inscribir():
                    return JsonResponse({"result": "bad", "mensaje": u"No hay cupo para continuar adicionando"})
                if not CapInscritoIpec.objects.filter(status=True, participante=participante, capeventoperiodo=curso).exists():
                    inscripcioncurso = CapInscritoIpec(status=True, participante=participante, capeventoperiodo=curso, personalunemi=True)
                    fecha = curso.fechainicio - timedelta(days=2)
                    if fecha <= datetime.now().date():
                        return JsonResponse({'result': 'bad', "mensaje": u" El tiempo límite de inscripción es 48h antes del inicio del curso."})
                    else:
                        inscripcioncurso.save(request)
                        return JsonResponse({'result': 'ok'})

                return JsonResponse({'result': 'bad', "mensaje": u"Usted ya se encuentra matriculado en el curso."})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al inscribirse, Consulte al encargado" })

        elif action == 'cancelarinscripcion':
            try:
                idmotivo = int(request.POST['idmotivo'])
                otromotivo = request.POST['otromotivo']
                curso = CapEventoPeriodoIpec.objects.get(pk=request.POST['cursoid'])
                inscrito = CapInscritoIpec.objects.get(participante=persona, capeventoperiodo_id=curso.id, status=True)
                if inscrito:
                    fecha = curso.fechainicio - timedelta(days=2)
                    if fecha >= datetime.now().date():
                        inscrito.status=False
                        inscrito.save()
                        if idmotivo > 0:
                            cancelacion = HistorialInscripcionEventoPeriodoIpec(capeventoperiodo=curso,participante=inscripcion.persona,cancelacupo=True, motivos=idmotivo)
                            cancelacion.save(request)
                        else:
                            cancelacion = HistorialInscripcionEventoPeriodoIpec(capeventoperiodo=curso,participante=inscripcion.persona,cancelacupo=True, otromotivo=otromotivo)
                            cancelacion.save(request)
                        log(u'Elimino correctamente del curso: %s' % persona, request, "del")
                        return JsonResponse({'result':True, "mensaje": u"Se elimino correctamente del Curso."})
                    else:
                        return JsonResponse({'result': False,"mensaje": 'No se puede eiliminar despues de las 48 Horas al inscribirse.'})
                else:
                    return JsonResponse({'result': 'bad', "mensaje": u"No puede eliminarse del curso."})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "bad": u"Error al eliminar inscripcion, %s" % ex})

        return HttpResponseRedirect(request.path)

    else:

        if 'action' in request.GET:
            action = request.GET['action']

            if action == 'listadoencuestas':
                try:
                    data['title'] = u'Listado Encuestas'
                    data['periodoeval'] = periodoeval = SagPeriodo.objects.get(pk=request.GET['idperiodo'])
                    data['encuestasperiodos'] = SagEncuesta.objects.filter(sagperiodo=periodoeval,
                                                                           status=True).order_by('orden')
                    form = SagEncuestasFrom()
                    data['formencuesta'] = form
                    return render(request, "sagadministracion/listadoencuestas.html", data)
                except Exception as ex:
                    pass

            elif action == 'listadoencuestascarreras':
                try:
                    data['title'] = u'Listado Carreras'
                    data['encuesta'] = encuesta = SagEncuesta.objects.get(pk=request.GET['idencuesta'])
                    data['periodoeval'] = encuesta.sagperiodo
                    data['encuestascarreras'] = listacarreras = SagEncuestaCarrera.objects.filter(sagecuesta=encuesta,
                                                                                                  status=True)
                    listacarreras = listacarreras.values_list('carrera')
                    data['listacarreras'] = Carrera.objects.filter(activa=True, status=True).exclude(
                        pk__in=listacarreras).exclude(
                        Q(nombre__icontains='MAESTRIA') | Q(nombre__icontains='MODULO') | Q(
                            nombre__icontains='ADMISIÓN')).order_by('nombre')
                    form = SagEncuestasFrom()
                    data['formencuesta'] = form
                    return render(request, "sagadministracion/listadoencuestascarreras.html", data)
                except Exception as ex:
                    pass

            elif action == 'listadopreguntas':
                try:
                    data['title'] = u'Preguntas'
                    data['inscripcion'] = inscripcion
                    data['periodoid'] = periodoid = int(encrypt(request.GET['id']))
                    if SagResultadoEncuesta.objects.filter(sagperiodo_id=periodoid, inscripcion=inscripcion,
                                                           status=True):
                        return HttpResponseRedirect("/alu_sistemasag")
                    data['listaencuestas'] = listaencuestas = SagEncuesta.objects.filter(sagperiodo_id=periodoid,
                                                                                         estado=True,
                                                                                         sagencuestacarrera__carrera=inscripcion.carrera,
                                                                                         status=True,
                                                                                         sagencuestacarrera__status=True).order_by(
                        'orden')
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
                    return render(request, "alu_sistemasag/encuestaestudiantes.html", data)
                except Exception as ex:
                    pass

            elif action == 'llenarformulario':
                try:
                    data['title'] = u'A. FICHA DEL GRADUADO'
                    data['inscripcion'] = inscripcion
                    data['niveltitulo'] = NivelTitulacion.objects.filter(status=True).order_by('-rango')
                    data['perfil'] = persona.mi_perfil()
                    data['idper'] = idper = request.GET['idper']
                    if 'personales' not in request.session:
                        data['personales'] = 0
                    else:
                        data['personales'] = request.session['personales']

                    if 'nacimiento' not in request.session:
                        data['nacimiento'] = 0
                    else:
                        data['nacimiento'] = request.session['nacimiento']

                    if 'domicilio' not in request.session:
                        data['domicilio'] = 0
                    else:
                        data['domicilio'] = request.session['domicilio']

                    if 'etnia' not in request.session:
                        data['etnia'] = 0
                    else:
                        data['etnia'] = request.session['etnia']

                    if 'instruccion' not in request.session:
                        data['instruccion'] = 0
                    else:
                        data['instruccion'] = request.session['instruccion']

                    f = Persona.objects.get(status=True, id=persona.id)
                    if f.datosactualizados == 1:
                        data['fuera'] = "/alu_sistemasag"
                    else:
                        data['fuera'] = "/alu_sistemasag?action=llenarformulario&idinsc=" + str(
                            inscripcion.id) + "&idper=" + str(idper) + ""
                    data['datosactualizados'] = f.datosactualizados
                    data['reporte_0'] = obtener_reporte('certificado_encuestasag')
                    return render(request, "alu_sistemasag/llenarformulario.html", data)
                except Exception as ex:
                    pass

            elif action == 'datospersonales':
                try:
                    data['title'] = u'Datos personales'
                    form = DatosPersonalesForm(initial={'nombres': persona.nombres,
                                                        'apellido1': persona.apellido1,
                                                        'apellido2': persona.apellido2,
                                                        'cedula': persona.cedula,
                                                        'pasaporte': persona.pasaporte,
                                                        'extension': persona.telefonoextension,
                                                        'sexo': persona.sexo,
                                                        'lgtbi': persona.lgtbi,
                                                        'anioresidencia': persona.anioresidencia,
                                                        'nacimiento': persona.nacimiento,
                                                        'nacionalidad': persona.nacionalidad,
                                                        'email': persona.email,
                                                        'estadocivil': persona.estado_civil(),
                                                        'libretamilitar': persona.libretamilitar})
                    form.editar()
                    data['form'] = form
                    data['idins'] = inscripcion.id
                    data['idper'] = request.GET['idper']
                    return render(request, "alu_sistemasag/datospersonales.html", data)
                except Exception as ex:
                    pass

            elif action == 'datosnacimiento':
                try:
                    data['title'] = u'Datos de nacimiento'
                    form = DatosNacimientoForm(initial={'paisnacimiento': persona.paisnacimiento,
                                                        'provincianacimiento': persona.provincianacimiento,
                                                        'cantonnacimiento': persona.cantonnacimiento,
                                                        'parroquianacimiento': persona.parroquianacimiento})
                    form.editar(persona)
                    data['form'] = form
                    data['idins'] = inscripcion.id
                    data['idper'] = request.GET['idper']
                    return render(request, "alu_sistemasag/datosnacimiento.html", data)
                except Exception as ex:
                    pass

            elif action == 'datosdomicilio':
                try:
                    data['title'] = u'Datos de domicilio'
                    form = DatosDomicilioForm(initial={'pais': persona.pais,
                                                       'provincia': persona.provincia,
                                                       'canton': persona.canton,
                                                       'parroquia': persona.parroquia,
                                                       'direccion': persona.direccion,
                                                       'direccion2': persona.direccion2,
                                                       'num_direccion': persona.num_direccion,
                                                       'referencia': persona.referencia,
                                                       'telefono': persona.telefono,
                                                       'telefono_conv': persona.telefono_conv,
                                                       'tipocelular': persona.tipocelular,
                                                       'sector': persona.sector})
                    form.editar(persona)
                    data['form'] = form
                    data['idins'] = inscripcion.id
                    data['idper'] = request.GET['idper']
                    return render(request, "alu_sistemasag/datosdomicilio.html", data)
                except Exception as ex:
                    pass

            elif action == 'etnia':
                try:
                    data['title'] = u'Etnia'
                    perfil = persona.mi_perfil()
                    form = EtniaForm(initial={'raza': perfil.raza, 'nacionalidadindigena': perfil.nacionalidadindigena})
                    data['form'] = form
                    data['idins'] = inscripcion.id
                    data['idper'] = request.GET['idper']
                    return render(request, "alu_sistemasag/etnia.html", data)
                except Exception as ex:
                    pass

            elif action == 'addfamiliar':
                try:
                    data['title'] = u'Adicionar familiar'
                    data['form'] = f = FamiliarForm()
                    f.fields['parentesco'].initial = 11
                    data['idins'] = inscripcion.id
                    data['idper'] = request.GET['idper']
                    return render(request, "alu_sistemasag/addfamiliar.html", data)
                except:
                    pass

            elif action == 'editfamiliar':
                try:
                    data['title'] = u'Editar familiar'
                    data['familiar'] = familiar = PersonaDatosFamiliares.objects.get(pk=int(request.GET['id']))
                    data['idins'] = inscripcion.id
                    data['idper'] = request.GET['idper']
                    data['form'] = FamiliarForm(initial={'identificacion': familiar.identificacion,
                                                         'parentesco': familiar.parentesco,
                                                         'nombre': familiar.nombre,
                                                         'nacimiento': familiar.nacimiento,
                                                         'fallecido': familiar.fallecido,
                                                         'tienediscapacidad': familiar.tienediscapacidad,
                                                         'telefono': familiar.telefono,
                                                         'niveltitulacion': familiar.niveltitulacion,
                                                         'ingresomensual': familiar.ingresomensual,
                                                         'formatrabajo': familiar.formatrabajo,
                                                         'telefono_conv': familiar.telefono_conv,
                                                         'trabajo': familiar.trabajo,
                                                         'convive': familiar.convive,
                                                         'sustentohogar': familiar.sustentohogar})
                    return render(request, "alu_sistemasag/editfamiliar.html", data)
                except:
                    pass

            elif action == 'delfamiliar':
                try:
                    data['title'] = u'Eliminar familiar'
                    data['familiar'] = familiar = PersonaDatosFamiliares.objects.get(pk=int(request.GET['id']))
                    data['idins'] = inscripcion.id
                    data['idper'] = request.GET['idper']
                    return render(request, "alu_sistemasag/delfamiliar.html", data)
                except:
                    pass

            elif action == 'addtitulacion':
                try:
                    data['title'] = u'Adicionar titulación'
                    form = TitulacionPersonaForm()
                    form.adicionar()
                    data['form'] = form
                    data['idins'] = inscripcion.id
                    data['idper'] = request.GET['idper']
                    return render(request, "alu_sistemasag/addtitulacion.html", data)
                except Exception as ex:
                    pass

            elif action == 'addarchivotitulacion':
                try:
                    data['title'] = u'Adicionar archivo de titulación'
                    data['titulacion'] = titulacion = Titulacion.objects.get(pk=int(request.GET['id']))
                    data['form'] = ArchivoTitulacionForm()
                    data['idins'] = inscripcion.id
                    data['idper'] = request.GET['idper']
                    return render(request, "alu_sistemasag/addarchivotitulacion.html", data)
                except:
                    pass

            elif action == 'edittitulacion':
                try:
                    data['title'] = u'Editar titulación'
                    data['titulacion'] = titulacion = Titulacion.objects.get(pk=int(request.GET['id']))
                    form = TitulacionPersonaForm(initial={'titulo': titulacion.titulo,
                                                          'areatitulo': titulacion.areatitulo,
                                                          'fechainicio': titulacion.fechainicio,
                                                          'educacionsuperior': titulacion.educacionsuperior,
                                                          'institucion': titulacion.institucion,
                                                          'colegio': titulacion.colegio,
                                                          'cursando': titulacion.cursando,
                                                          'fechaobtencion': titulacion.fechaobtencion if not titulacion.cursando else datetime.now().date(),
                                                          'fechaegresado': titulacion.fechaegresado if not titulacion.cursando else datetime.now().date(),
                                                          'registro': titulacion.registro,
                                                          # 'areaconocimiento': titulacion.areaconocimiento,
                                                          # 'subareaconocimiento': titulacion.subareaconocimiento,
                                                          # 'subareaespecificaconocimiento': titulacion.subareaespecificaconocimiento,
                                                          'pais': titulacion.pais,
                                                          'provincia': titulacion.provincia,
                                                          'canton': titulacion.canton,
                                                          'parroquia': titulacion.parroquia,
                                                          'anios': titulacion.anios,
                                                          'semestres': titulacion.semestres,
                                                          'aplicobeca': titulacion.aplicobeca,
                                                          'tipobeca': titulacion.tipobeca,
                                                          'financiamientobeca': titulacion.financiamientobeca,
                                                          'valorbeca': titulacion.valorbeca})
                    form.editar(titulacion)
                    data['form'] = form
                    data['idins'] = inscripcion.id
                    data['idper'] = request.GET['idper']
                    return render(request, "alu_sistemasag/edittitulacion.html", data)
                except:
                    pass

            elif action == 'deltitulacion':
                try:
                    data['title'] = u'Eliminar titulación'
                    data['titulacion'] = titulacion = Titulacion.objects.get(pk=int(request.GET['id']))
                    data['idins'] = inscripcion.id
                    data['idper'] = request.GET['idper']
                    return render(request, "alu_sistemasag/deltitulacion.html", data)
                except:
                    pass

            elif action == 'addexperiencia':
                try:
                    data['title'] = u'Adicionar experiencia'
                    form = ExperienciaLaboralForm()
                    form.adicionar()
                    data['form'] = form
                    data['idins'] = inscripcion.id
                    data['idper'] = request.GET['idper']
                    return render(request, "alu_sistemasag/addexperiencia.html", data)
                except Exception as ex:
                    pass

            elif action == 'editexperiencia':
                try:
                    data['title'] = u'Editar experiencia'
                    data['experiencia'] = experiencia = ExperienciaLaboral.objects.get(pk=int(request.GET['id']))
                    if experiencia.motivosalida.id == 7:
                        vig = True
                    else:
                        vig = False
                    data['form'] = ExperienciaLaboralForm(initial={'tipoinstitucion': experiencia.tipoinstitucion,
                                                                   'institucion': experiencia.institucion,
                                                                   'cargo': experiencia.cargo,
                                                                   'departamento': experiencia.departamento,
                                                                   'pais': experiencia.pais,
                                                                   'provincia': experiencia.provincia,
                                                                   'canton': experiencia.canton,
                                                                   'parroquia': experiencia.parroquia,
                                                                   'fechainicio': experiencia.fechainicio,
                                                                   'fechafin': experiencia.fechafin,
                                                                   'vigente': vig,
                                                                   'motivosalida': experiencia.motivosalida,
                                                                   'regimenlaboral': experiencia.regimenlaboral,
                                                                   'horassemanales': experiencia.horassemanales,
                                                                   'dedicacionlaboral': experiencia.dedicacionlaboral,
                                                                   'actividadlaboral': experiencia.actividadlaboral,
                                                                   'observaciones': experiencia.observaciones})
                    data['idins'] = inscripcion.id
                    data['idper'] = request.GET['idper']
                    return render(request, "alu_sistemasag/editexperiencia.html", data)
                except:
                    pass

            elif action == 'delexperiencia':
                try:
                    data['title'] = u'Eliminar experiencia'
                    data['experiencia'] = experiencia = ExperienciaLaboral.objects.get(pk=int(request.GET['id']))
                    data['idins'] = inscripcion.id
                    data['idper'] = request.GET['idper']
                    return render(request, "alu_sistemasag/delexperiencia.html", data)
                except:
                    pass

            elif action == 'addarchivoexperiencia':
                try:
                    data['title'] = u'Adicionar archivo de referencia laboral'
                    data['experiencia'] = experiencia = ExperienciaLaboral.objects.get(pk=int(request.GET['id']))
                    data['form'] = ArchivoExperienciaForm()
                    data['idins'] = inscripcion.id
                    data['idper'] = request.GET['idper']
                    return render(request, "alu_sistemasag/addarchivoexperiencia.html", data)
                except:
                    pass

            return HttpResponseRedirect(request.path)
        else:
            try:
                data['title'] = u'Sistema de Seguimiento y Acompañamiento a Graduados'
                hoy = datetime.now().date()
                data['inscripcion'] = inscripcion
                graduado = inscripcion.graduado()
                egresado = inscripcion.egresado()
                if request.session['periodo'].tipo_id == 3:
                    if not graduado:
                        return HttpResponseRedirect("/?info=Sólo los alumnos egresados ó graduados pueden ingresar al módulo.")
                elif not egresado or not graduado:
                        return HttpResponseRedirect("/?info=Sólo los alumnos egresados ó graduados pueden ingresar al módulo.")
                data['reporte_0'] = obtener_reporte('certificado_encuestasag')
                tiposagperiodo = 2 if inscripcion.coordinacion_id == 7 else 1
                periodos = SagPeriodo.objects.filter(estado=True, status=True, tipo_sagperiodo=tiposagperiodo)
                encuestas_realizadas = SagResultadoEncuesta.objects.filter(inscripcion=inscripcion, status=True).values_list( 'sagperiodo_id', flat=True)
                encuesta_muestra = SagMuestraEncuesta.objects.values_list('sagperiodo_id',flat=True).filter(inscripcion=inscripcion, status=True)
                encuestas_estudiante = [p.id for p in periodos if (p.primeravez and p.id not in encuestas_realizadas and p.fechainicio <= graduado[0].fechagraduado <= p.fechafin) or (p.id in encuesta_muestra and p.id not in encuestas_realizadas)]
                encuesta_pendiente = periodos.filter(id__in=encuestas_estudiante).last()
                periodos_total = SagPeriodo.objects.filter(id__in=encuestas_realizadas, estado=True, status=True)
                """ JSON PARA CURSOS DE SEGUIMIENTO GRADUADO"""
                inscripcioncurso = []
                usuario_inscrito = False
                eventos = CapEventoPeriodoIpec.objects.filter(fechainicioinscripcion__lte=hoy,fechafininscripcion__gte=hoy, publicarinscripcion=True,status=True, seguimientograduado=True)
                _inscritoT = CapInscritoIpec.objects.filter(status=True, capeventoperiodo__seguimientograduado=True,participante=persona,fecha_creacion__year=hoy.year).exists()
                for e in eventos:
                    _inscrito = CapInscritoIpec.objects.filter( status=True,capeventoperiodo=e,participante=persona,fecha_creacion__year=hoy.year).exists()
                    if _inscrito:
                        usuario_inscrito = True
                    inscripcion_data = {
                        'imagen': e.archivo.url if e.archivo else 'wp-content/uploads/2022/07/GESTION-EDUCATIVA-CON-MENCION-EN-ORGANIZACION-INNOVACION-Y-DIRECCION.png',
                        'nombre': e.capevento.nombre,
                        'objetivo': e.objetivo,
                        'modalidad': e.get_modalidad_display,
                        'horas': e.horas,
                        'inicia': e.fechainicio.strftime('%d %b %Y'),
                        'cursoid': e.id,
                        'elimina': _inscrito,
                        'aplica': not _inscrito
                    }
                    inscripcioncurso.append(inscripcion_data)
                data['inscripcioncurso'] = inscripcioncurso
                data['usuario_inscrito'] = usuario_inscrito
                data['inscritoT'] = _inscritoT
                paging = MiPaginador(inscripcioncurso, 8)
                page_num = request.GET.get('page', request.session.get('paginador', 1))
                try:
                    page = paging.page(page_num)
                except Exception:
                    page = paging.page(1)
                request.session['paginador'] = page.number
                data['paging'] = paging
                data['rangospaging'] = paging.rangos_paginado(page.number)
                data['page'] = page
                data['periodossag'] = periodos.filter(id__in=encuestas_estudiante)
                data['encuesta_pendiente'] = encuesta_pendiente
                data['periodos_total'] = SagPeriodo.objects.filter(id__in=encuestas_realizadas)
                data['motivocancelacion'] = MOTIVOCANCELACIONCUPO
                succes_url = 'seguimientograduado.html' if periodos_total and periodos_total[0].aplicacurso or (encuesta_pendiente and not encuesta_pendiente.primeravez) else 'view.html'
                return render(request, f"alu_sistemasag/{succes_url}", data)
            except:
                pass

            # try:
            #     data['title'] = u'sistema de seguimiento y acompañamiento a graduados'
            #     search = none
            #     ids = none
            #     muestra = none
            #     egre = 0
            #     hoy = datetime.now().date()
            #     inscripcionid = none
            #     data['inscripcion'] = inscripcion
            #     if egresado.objects.filter(inscripcion=inscripcion, status=true):
            #         egre = 1
            #     if graduado.objects.filter(inscripcion=inscripcion, status=true):
            #         egre = 1
            #     if egre == 0:
            #         return httpresponseredirect("/?info=sólo los alumnos egresados ó graduados pueden ingresar al módulo.")
            #     data['reporte_0'] = obtener_reporte('certificado_encuestasag')
            #     graduado = inscripcion.graduado().order_by('-fechaactagrado')
            #     periodos = sagperiodo.objects.none()
            #     encuestas_realizadas = list(sagresultadoencuesta.objects.filter(inscripcion=inscripcion, status=true).values_list('sagperiodo_id', flat=true))
            #
            #     encuesta_muestra = list(sagmuestraencuesta.objects.filter(inscripcion=inscripcion, status=true).values_list('sagperiodo_id', flat=true))
            #
            #     if graduado.count() > 0:
            #         periodos = sagperiodo.objects.filter(estado=true, status=true)
            #
            #     encuestas_estudiante = []
            #
            #     for p in periodos:
            #         if p.primeravez:  # si esta encuesta es sólo para estudiantes que nunca la han realizado
            #             if not p.id in encuestas_realizadas and p.fechainicio <= graduado[0].fechaactagrado <= p.fechafin:  # si el estudiante nunca a realizado la encuesta y su fecha de graduación está entre la fechainicio y fin
            #                 encuestas_estudiante.append(p)
            #         elif p.id in encuesta_muestra and not p.id in encuestas_realizadas:  # si el estudiante está en la muestra
            #             encuestas_estudiante.append(p)
            #         # elif p.fechainicio <= datetime.now().date() <= p.fechafin and not p.id in encuestas_realizadas:  # si la encuesta está en vigencia según la fecha de inicio y fin
            #         #     encuestas_estudiante.append(p)
            #
            #     periodos_total = sagperiodo.objects.filter(id__in=encuestas_realizadas, estado=true, status=true)  # encuestas realizadas
            #     # if sagactividades.objects.filter(q(codigo__icontains='act1'), vigente=true ,status=true).exists():
            #     #     actividad = sagactividades.objects.filter(q(codigo__icontains='act1'), vigente=true ,status=true)[0]
            #     #     if not sagvisita.objects.filter(status=true, inscripcion=inscripcion, actividad=actividad, fecha=hoy).exists():
            #     #         visita =  sagvisita(inscripcion=inscripcion, actividad=actividad, fecha=hoy)
            #     #         visita.save(request)
            #     #     else:
            #     #         visita = sagvisita.objects.filter(status=true, inscripcion=inscripcion, actividad=actividad, fecha=hoy)[0]
            #     #         visita.numero=visita.numero+1
            #     #         visita.save(request)
            #     data['periodossag'] = encuestas_estudiante
            #     data['periodos_total'] = periodos_total
            #     return render(request, "alu_sistemasag/view.html", data)
            # except exception as ex:
            #     pass
        # else:
        #     try:
        #         data['title'] = u'Sistema de Seguimiento y Acompañamiento a Graduados'
        #         search = None
        #         ids = None
        #         muestra = None
        #         egre = 0
        #         TIEMPO_ENCACHE = 60 * 60 * 60
        #         hoy = datetime.now().date()
        #         inscripcionid = None
        #         data['inscripcion'] = inscripcion
        #         # if Egresado.objects.filter(inscripcion=inscripcion, status=True):
        #         #     egre = 1
        #         # if Graduado.objects.filter(inscripcion=inscripcion, status=True):
        #         #     egre = 1
        #         # if egre == 0:
        #         #     return HttpResponseRedirect("/?info=Sólo los alumnos egresados ó graduados pueden ingresar al módulo.")
        #         # data['reporte_0'] = obtener_reporte('certificado_encuestasag')
        #         # graduado = inscripcion.graduado().order_by('-fechaactagrado')
        #         # periodos = SagPeriodo.objects.none()
        #         # encuestas_realizadas = list(SagResultadoEncuesta.objects.filter(inscripcion=inscripcion, status=True).values_list('sagperiodo_id', flat=True))
        #         #
        #         # encuesta_muestra = list(SagMuestraEncuesta.objects.filter(inscripcion=inscripcion, status=True).values_list('sagperiodo_id',flat=True))
        #         #
        #         # if graduado.count() > 0:
        #         #     periodos = SagPeriodo.objects.filter(estado=True, status=True)
        #         #
        #         # encuestas_estudiante = []
        #
        #         data['reporte_0'] = obtener_reporte('certificado_encuestasag')
        #         periodos = SagPeriodo.objects.none()
        #         encuestas_realizadas = list(SagResultadoEncuesta.objects.filter(inscripcion=inscripcion, status=True).values_list('sagperiodo_id', flat=True))
        #
        #         encuesta_muestra = list(SagMuestraEncuesta.objects.filter(inscripcion=inscripcion, status=True).values_list('sagperiodo_id', flat=True))
        #
        #         periodos = SagPeriodo.objects.filter(estado=True, status=True)
        #
        #         encuestas_estudiante = []
        #         if not periodos:
        #             cache.delete(f"encuestaegresado_por_contestar_alumnos_panel_{encrypt(inscripcion.id)}")
        #             cache.set(f"encuestaegresado_por_contestar_alumnos_panel_{encrypt(inscripcion.id)}", [{"id": 1, "pendiente": False}], TIEMPO_ENCACHE)
        #         for p in periodos:
        #             # if p.primeravez:  # si esta encuesta es sólo para estudiantes que nunca la han realizado
        #             #     if not p.id in encuestas_realizadas and p.fechainicio <= graduado[0].fechaactagrado <= p.fechafin:  # si el estudiante nunca a realizado la encuesta y su fecha de graduación está entre la fechainicio y fin
        #             #         encuestas_estudiante.append(p)
        #             # elif p.id in encuesta_muestra and not p.id in encuestas_realizadas:  # si el estudiante está en la muestra
        #             #     encuestas_estudiante.append(p)
        #             if p.primeravez:  # si esta encuesta es sólo para estudiantes que nunca la han realizado
        #                 mimalla = inscripcion.mi_malla()
        #                 ultimonivel = mimalla.ultimo_nivel_malla()
        #                 if MateriaAsignada.objects.values("id").filter(matricula__inscripcion_id=inscripcion.id, materia__asignaturamalla__nivelmalla=ultimonivel, status=True).exists():
        #                     periodoalumno = MateriaAsignada.objects.filter(matricula__inscripcion_id=inscripcion.id, materia__asignaturamalla__nivelmalla=ultimonivel, status=True)[0].materia.nivel.periodo
        #                     if not p.id in encuestas_realizadas and p.fechainicio <= periodoalumno.inicio <= p.fechafin:  # si el estudiante nunca a realizado la encuesta y su fecha de periodo lectivo está entre la fechainicio y fin
        #                         encuestas_estudiante.append(p)
        #             elif p.id in encuesta_muestra and not p.id in encuestas_realizadas:  # si el estudiante está en la muestra
        #                 encuestas_estudiante.append(p)
        #         periodos_total = SagPeriodo.objects.filter(id__in=encuestas_realizadas, estado=True, status=True)  # encuestas realizadas
        #         # if SagActividades.objects.filter(Q(codigo__icontains='ACT1'), vigente=True ,status=True).exists():
        #         #     actividad = SagActividades.objects.filter(Q(codigo__icontains='ACT1'), vigente=True ,status=True)[0]
        #         #     if not SagVisita.objects.filter(status=True, inscripcion=inscripcion, actividad=actividad, fecha=hoy).exists():
        #         #         visita =  SagVisita(inscripcion=inscripcion, actividad=actividad, fecha=hoy)
        #         #         visita.save(request)
        #         #     else:
        #         #         visita = SagVisita.objects.filter(status=True, inscripcion=inscripcion, actividad=actividad, fecha=hoy)[0]
        #         #         visita.numero=visita.numero+1
        #         #         visita.save(request)
        #         data['periodossag'] = encuestas_estudiante
        #         data['periodos_total'] = periodos_total
        #         return render(request, "alu_sistemasag/view.html", data)
        #     except Exception as ex:
        #         pass
