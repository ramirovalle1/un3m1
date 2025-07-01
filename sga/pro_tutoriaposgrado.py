# -*- coding: UTF-8 -*-
import io
import json
import os
import sys
from datetime import datetime

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.db.models import Q, Avg, Sum
from django.http import HttpResponse, HttpResponseRedirect, JsonResponse
from django.shortcuts import render
from django.template.loader import get_template
from xlwt import *

from posgrado.forms import FormDictamen, ArchivoInvitacionForm
from posgrado.models import Informe, Revision, SeccionRevision, PreguntaRevision, HistorialDocRevisionTribunal, \
    ConfiguraInformePrograma
from sga.commonviews import adduserdata
from sga.forms import ComplexivoCalificarPropuestaForm, \
    ComplexivoCalificacionSustentacionForm, TutoriaProfesorPosgradoForm, CalificarPropuestaPosgradoForm, \
    RevisarAvanceTutoriaPosgradoForm
from sga.funciones import log, generar_nombre, null_to_numeric, variable_valor, MiPaginador, \
    remover_caracteres_especiales_unicode, remover_caracteres_tildes_unicode
from sga.funciones_templatepdf import rubricatribunalcalificacionposgrado, acompanamientoposgrado, \
    acompanamientoposgradopareja, reporte_informe_tutoria_posgrado, reporte_informe_tutoria_posgrado_pareja, \
    informetribunaltitulacionposgrado
from sga.funcionesxhtml2pdf import conviert_html_to_pdf
from sga.models import ArchivoTitulacion, \
    MESES_CHOICES, CargoInstitucion, CalificacionRubricaTitulacion, CalificacionDetalleRubricaTitulacion, \
    ConfiguracionTitulacionPosgrado, TemaTitulacionPosgradoMatricula, \
    TutoriasTemaTitulacionPosgradoProfesor, RevisionTutoriasTemaTitulacionPosgradoProfesor, \
    ArchivoRevisionTutoriasTemaTitulacionPosgradoProfesor, TribunalTemaTitulacionPosgradoMatricula, \
    CalificacionTitulacionPosgrado, CalificacionDetalleRubricaTitulacionPosgrado, TIPO_RUBRICA, \
    RubricaTitulacionPosgrado, ModeloRubricaTitulacionPosgrado, DetalleRubricaTitulacionPosgrado, \
    CalificacionDetalleModeloRubricaTitulacionPosgrado, RubricaTitulacionCabPonderacionPosgrado, \
    TemaTitulacionPosArchivoFinal, TemaTitulacionPosgradoMatriculaCabecera, EtapaTemaTitulacionPosgrado, \
    TemaTitulacionPosgradoProfesor, IntegranteFirmaTemaTitulacionPosgradoMatricula
from sga.templatetags.sga_extras import encrypt
from core.firmar_documentos import obtener_posicion_x_y_saltolinea
from core.firmar_documentos_ec import JavaFirmaEc
from django.core.files.base import ContentFile

@login_required(redirect_field_name='ret', login_url='/loginsga')
@transaction.atomic()
# @secure_module
def view(request):
    data = {}
    adduserdata(request, data)
    persona = request.session['persona']
    perfilprincipal = request.session['perfilprincipal']
    profesor = perfilprincipal.profesor

    # bordes
    borders = Borders()
    borders.left = 1
    borders.right = 1
    borders.top = 1
    borders.bottom = 1
    # estilos para los reportes
    title = easyxf('font: name Arial, bold on , height 200; alignment: horiz centre')
    subtitle = easyxf('font: name Arial, bold on , height 150; alignment: horiz centre')
    normaliz = easyxf('font: name Arial , height 150; align: wrap on,horiz left ')
    nnormal = easyxf('font: name Arial, bold on , height 150; align: wrap on,horiz right')
    normal = easyxf('font: name Arial , height 150; align: wrap on,horiz center ')
    stylebnotas = easyxf('font: name Arial, bold on , height 150; alignment: horiz centre')
    stylebnombre = easyxf('font: name Arial, bold on , height 150; align: wrap on, horiz left')
    stylebnotas.borders = borders
    normaliz.borders = borders

    hoy = datetime.now().date()
    if request.method == 'POST':
        res_json = []
        if 'action' in request.POST:
            action = request.POST['action']

            if action == 'addtutoria':
                try:
                    with transaction.atomic():
                        form = TutoriaProfesorPosgradoForm(request.POST, request.FILES)
                        if 'archivo' in request.FILES:
                            newfile = request.FILES['archivo']
                            if newfile:
                                if newfile.size > 52428800:
                                    return JsonResponse({"result": "bad", "mensaje": u"Error, archivo mayor a 12 Mb."})
                                elif newfile.size <= 0:
                                    return JsonResponse({"result": "bad", "mensaje": u"Error, el archivo esta vacío."})
                                else:
                                    newfilesd = newfile._name
                                    ext = newfilesd[newfilesd.rfind("."):]
                                    if ext == '.pdf':
                                        newfile._name = generar_nombre("tutoria_", newfile._name)
                                    else:
                                        return JsonResponse(
                                            {"result": "bad", "mensaje": u"Error, archivo solo en .pdf."})

                        if form.is_valid():
                            acompanamiento = TutoriasTemaTitulacionPosgradoProfesor()
                            if json.loads(request.POST['pareja']) == True:
                                grupo = TemaTitulacionPosgradoMatriculaCabecera.objects.get(pk=request.POST['grupo_id'])
                                acompanamiento.tematitulacionposgradomatriculacabecera = grupo
                            else:
                                grupo = TemaTitulacionPosgradoMatricula.objects.get(pk=request.POST['grupo_id'])
                                acompanamiento.tematitulacionposgradomatricula = grupo

                            if grupo.hora_registrada(form.cleaned_data['horainicio'],
                                                     form.cleaned_data['fecharegistro']):
                                return JsonResponse({'result': 'bad',
                                                     'mensaje': u'Ya se ha registrado un acompañamiento en estas horas.'})
                            if form.cleaned_data['horas'] > grupo.horas_restantes_fecha(
                                    form.cleaned_data['fecharegistro'], None):
                                return JsonResponse({'result': 'bad',
                                                     'mensaje': u'La cantidad de horas supera el maximo pèrmitido por día.'})

                            acompanamiento.fecharegistro = form.cleaned_data['fecharegistro']
                            acompanamiento.tutor = profesor
                            acompanamiento.horainicio = form.cleaned_data['horainicio']
                            acompanamiento.horafin = form.cleaned_data['horafin']
                            acompanamiento.horas = form.cleaned_data['horas']
                            acompanamiento.observacion = form.cleaned_data['titulo']
                            acompanamiento.detalle = form.cleaned_data['detalle']
                            acompanamiento.modalidad = form.cleaned_data['modalidad']
                            acompanamiento.enlace = form.cleaned_data['link_grabacion']
                            acompanamiento.programaetapatutoria = form.cleaned_data['programaetapatutoria']
                            if 'archivo' in request.FILES:
                                acompanamiento.archivo = newfile
                            acompanamiento.save(request)
                            log(u"Adicionó tutoría de posgrado %s" % acompanamiento, request, "add")

                        else:
                            transaction.set_rollback(True)
                            return JsonResponse({'result': True, "form": [{k: v[0]} for k, v in form.errors.items()],
                                                 "mensaje": "Error en el formulario"})

                        return JsonResponse({"result": False}, safe=False)
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": True, "mensaje": "Intentelo más tarde.".format(str(ex))}, safe=False)

            if action == 'edittutoria':
                try:
                    acompanamiento = TutoriasTemaTitulacionPosgradoProfesor.objects.get(pk=request.POST['id'])
                    with transaction.atomic():
                        form = TutoriaProfesorPosgradoForm(request.POST, request.FILES)
                        if 'archivo' in request.FILES:
                            newfile = request.FILES['archivo']
                            if newfile:
                                if newfile.size > 52428800:
                                    return JsonResponse({"result": "bad", "mensaje": u"Error, archivo mayor a 12 Mb."})
                                elif newfile.size <= 0:
                                    return JsonResponse({"result": "bad", "mensaje": u"Error, el archivo esta vacío."})
                                else:
                                    newfilesd = newfile._name
                                    ext = newfilesd[newfilesd.rfind("."):]
                                    if ext == '.pdf':
                                        newfile._name = generar_nombre("tutoria_", newfile._name)
                                    else:
                                        return JsonResponse(
                                            {"result": "bad", "mensaje": u"Error, archivo solo en .pdf."})

                        if form.is_valid():
                            if json.loads(request.POST['pareja']) == True:
                                grupo = acompanamiento.tematitulacionposgradomatriculacabecera
                            else:
                                grupo = acompanamiento.tematitulacionposgradomatricula

                            restantes = grupo.horas_restantes_fecha(form.cleaned_data['fecharegistro'], acompanamiento.id)
                            if form.cleaned_data['horas'] > restantes:
                                return JsonResponse({'result': 'bad',
                                                     'mensaje': u'la cantidad de horas supera el maximo pèrmitido por día.'})

                            acompanamiento.fecharegistro = form.cleaned_data['fecharegistro']
                            acompanamiento.tutor = profesor
                            acompanamiento.horainicio = form.cleaned_data['horainicio']
                            acompanamiento.horafin = form.cleaned_data['horafin']
                            acompanamiento.horas = form.cleaned_data['horas']
                            acompanamiento.observacion = form.cleaned_data['titulo']
                            acompanamiento.detalle = form.cleaned_data['detalle']
                            acompanamiento.modalidad = form.cleaned_data['modalidad']
                            acompanamiento.enlace = form.cleaned_data['link_grabacion']
                            acompanamiento.programaetapatutoria = form.cleaned_data['programaetapatutoria']
                            if 'archivo' in request.FILES:
                                acompanamiento.archivo = newfile
                            acompanamiento.save(request)
                            log(u"Editó tutoría de posgrado %s" % acompanamiento, request, "edit")

                        else:
                            transaction.set_rollback(True)
                            return JsonResponse({'result': True, "form": [{k: v[0]} for k, v in form.errors.items()],
                                                 "mensaje": "Error en el formulario"})

                        return JsonResponse({"result": False}, safe=False)
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": True, "mensaje": "Intentelo más tarde.".format(str(ex))}, safe=False)

            if action == 'subtemas':
                try:
                    grupo = TemaTitulacionPosgradoMatricula.objects.get(pk=request.POST['id'])
                    if grupo.tribunaltematitulacionposgradomatricula_set.filter(status=True).exists():
                        tribunal = TribunalTemaTitulacionPosgradoMatricula.objects.get(
                            tematitulacionposgradomatricula=grupo)
                        tribunal.subtema = request.POST['subtema'].strip()
                        tribunal.save(request)
                    else:
                        tribunal = TribunalTemaTitulacionPosgradoMatricula(tematitulacionposgradomatricula=grupo,
                                                                           subtema=request.POST['subtema'])
                        tribunal.save(request)
                    log(u"Adiciono el subtema de posgrado: %s" % (tribunal), request, "add")
                    return JsonResponse({"result": "ok"})
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos.(%s)" % ex})

            if action == 'subtemas_pareja':
                try:
                    grupo = TemaTitulacionPosgradoMatriculaCabecera.objects.get(pk=request.POST['id'])
                    if grupo.tribunaltematitulacionposgradomatricula_set.filter(status=True).exists():
                        tribunal = TribunalTemaTitulacionPosgradoMatricula.objects.get(
                            tematitulacionposgradomatriculacabecera=grupo)
                        tribunal.subtema = request.POST['subtema']
                        tribunal.save(request)
                    else:
                        tribunal = TribunalTemaTitulacionPosgradoMatricula(
                            tematitulacionposgradomatriculacabecera=grupo,
                            subtema=request.POST['subtema'])
                        tribunal.save(request)
                    log(u"Adiciono el tema asignado por el tutor: %s" % (tribunal), request, "add")
                    return JsonResponse({"result": "ok"})
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos.(%s)" % ex})

            if action == 'delete':
                try:
                    with transaction.atomic():
                        acompanamiento = TutoriasTemaTitulacionPosgradoProfesor.objects.get(pk=request.POST['id'])
                        acompanamiento.status = False
                        acompanamiento.save(request)
                        log(u"Elimino tutoría posgrado : %s" % acompanamiento, request, "delete")
                        res_json = {"error": False}
                except Exception as ex:
                    transaction.set_rollback(True)
                    res_json = {'error': True, "message": "Error: {}".format(ex)}
                return JsonResponse(res_json, safe=False)

            if action == 'cerraactaposgrado':
                try:
                    idmaestrantegrupo = TemaTitulacionPosgradoMatricula.objects.get(pk=request.POST['id'])
                    idmaestrantegrupo.cerraracta_posgrado()
                    return JsonResponse({"result": "ok"})
                except Exception as ex:
                    pass

            if action == 'aprobararchivo':
                try:
                    hoy = datetime.now().date()
                    archivocorrejido = TemaTitulacionPosArchivoFinal.objects.get(pk=request.POST['id'])
                    archivocorrejido.estado = 2
                    archivocorrejido.fechapersonaprueba = hoy
                    archivocorrejido.personaprueba = persona
                    archivocorrejido.save()
                    return JsonResponse({"result": "ok"})
                except Exception as ex:
                    pass

            if action == 'archivosustentacion':
                try:
                    f = ComplexivoCalificacionSustentacionForm(request.POST, request.FILES)
                    if f.is_valid():
                        grupo = CalificacionTitulacionPosgrado.objects.get(
                            tematitulacionposgradomatricula_id=request.POST['id'], juradocalificador=profesor)
                        if 'archivo' in request.FILES:
                            newfile = request.FILES['archivo']
                            newfile._name = generar_nombre("archivosustentacion_", newfile._name)
                            grupo.archivotribunal = newfile
                        # if grupo.calificacion < 70:
                        #     grupo.estado = 2
                        # else:
                        #     grupo.estado = 3
                        grupo.save(request)
                        log(u"Subio archivo de sustentación a %s" % (grupo), request, "add")
                        return JsonResponse({'result': 'ok'})
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({'result': 'bad', 'mensaje': u'Ocurrio un problema al subir archivo.'})

            if action == 'calificarurkundtitulacionfinalposgrado':
                try:
                    f = CalificarPropuestaPosgradoForm(request.POST, request.FILES)
                    newfile = None
                    newfilec = None
                    if 'archivo' in request.FILES:
                        newfile = request.FILES['archivo']
                        if newfile:
                            if newfile.size > 52428800:
                                return JsonResponse({"result": "bad", "mensaje": u"Error, archivo mayor a 12 Mb."})
                            elif newfile.size <= 0:
                                return JsonResponse(
                                    {"result": "bad", "mensaje": u"Error, el archivo Propuesta Práctica esta vacío."})
                            else:
                                newfilesd = newfile._name
                                ext = newfilesd[newfilesd.rfind("."):]
                                if ext == '.pdf':
                                    newfile._name = generar_nombre("urkund_", newfile._name)
                                else:
                                    return JsonResponse({"result": "bad",
                                                         "mensaje": u"Error, archivo de Propuesta Práctica solo en .doc, docx."})
                    if 'correccion' in request.FILES:
                        newfilec = request.FILES['correccion']
                        if newfilec:
                            if newfilec.size > 52428800:
                                return JsonResponse({"result": "bad", "mensaje": u"Error, archivo mayor a 12 Mb."})
                            elif newfilec.size <= 0:
                                return JsonResponse({"result": "bad",
                                                     "mensaje": u"Error, el archivo Propuesta Práctica (Desde introducción hasta conclusión) esta vacío."})
                            else:
                                newfilesd = newfilec._name
                                ext = newfilesd[newfilesd.rfind("."):]
                                if ext == '.doc' or ext == '.docx' or ext == '.pdf':
                                    newfilec._name = generar_nombre("correccion_", newfilec._name)
                                else:
                                    return JsonResponse({"result": "bad",
                                                         "mensaje": u"Error, archivo Propuesta Práctica Antiplagio solo en .doc, docx."})
                    if f.is_valid():
                        propuesta = RevisionTutoriasTemaTitulacionPosgradoProfesor.objects.get(pk=request.POST['id'])
                        if f.cleaned_data['aprobar']:
                            archivo = ArchivoRevisionTutoriasTemaTitulacionPosgradoProfesor(revisiontutoriastematitulacionposgradoprofesor=propuesta, archivo=newfile, tipo=3, fecha=datetime.now())
                            archivo.save(request)
                            log(u"Añade archivo antiplagio %s a revision[%s], posgrado" % (archivo, propuesta.id), request, "add")
                        else:
                            archivo = ArchivoRevisionTutoriasTemaTitulacionPosgradoProfesor(revisiontutoriastematitulacionposgradoprofesor=propuesta, archivo=newfilec, tipo=4, fecha=datetime.now())
                            archivo.save(request)
                            log(u"Añade archivo de correccion %s a revision[%s], posgrado" % (archivo, propuesta.id), request, "add")
                        propuesta.fecharevision = datetime.now()
                        propuesta.observacion = f.cleaned_data['observaciones']
                        propuesta.observacion = propuesta.observacion.upper()
                        if f.cleaned_data['rechazar']:
                            propuesta.estado = 3
                        if f.cleaned_data['aprobar']:
                            propuesta.porcentajeurkund = f.cleaned_data['plagio']
                            if float(f.cleaned_data['plagio']) <= 15:
                                propuesta.estado = 2
                            else:
                                propuesta.estado = 3
                        if not f.cleaned_data['rechazar'] and not f.cleaned_data['aprobar']:
                            propuesta.estado = 4
                        propuesta.save(request)
                        if json.loads(request.POST['pareja']) == True:
                             log(u"Aprobo/Reprobo a propuesta [%s] con línea de investigación: %s" % (propuesta.id, propuesta.tematitulacionposgradomatriculacabecera.propuestatema), request,"add")
                        else:
                            log(u"Aprobo/Reprobo a propuesta [%s] con línea de investigación: %s" % (propuesta.id, propuesta.tematitulacionposgradomatricula.propuestatema), request, "add")
                        return JsonResponse({'result': False})
                    else:
                        return JsonResponse({'result': 'bad', 'mensaje': u'Error, ar guardar los datos.'})
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({'result': 'bad', 'mensaje': u'Ocurrio un problema al subir archivo.'})

            if action == 'revisararchivoavancetutoria':
                try:
                    f = RevisarAvanceTutoriaPosgradoForm(request.POST, request.FILES)
                    newfilec = None
                    propuesta = RevisionTutoriasTemaTitulacionPosgradoProfesor.objects.get(pk=request.POST['id'])
                    if 'correccion' in request.FILES:
                        newfilec = request.FILES['correccion']
                        if newfilec:
                            if newfilec.size > 30000000:
                                return JsonResponse({"result": "bad", "mensaje": u"Error, archivo mayor a 30 Mb."})
                            elif newfilec.size <= 0:
                                return JsonResponse({"result": "bad", "mensaje": u"Error, el archivo esta vacío."})
                            else:
                                newfilesd = newfilec._name
                                ext = newfilesd[newfilesd.rfind("."):]
                                if ext == '.doc' or ext == '.docx' or ext == '.pdf':
                                    newfilec._name = generar_nombre("correccion_", newfilec._name)
                                else:
                                    return JsonResponse(
                                        {"result": "bad", "mensaje": u"Error, archivo solo en .doc, docx."})

                                archivo = ArchivoRevisionTutoriasTemaTitulacionPosgradoProfesor(
                                    revisiontutoriastematitulacionposgradoprofesor=propuesta, archivo=newfilec, tipo=4,
                                    fecha=datetime.now())
                                archivo.save(request)



                    if f.is_valid():
                        propuesta.fecharevision = datetime.now()
                        propuesta.observacion = f.cleaned_data['observaciones']
                        propuesta.save(request)

                        log(u"Reviso la tutoria [%s] " % (propuesta), request, "add")
                        return JsonResponse({'result': False})
                    else:
                        return JsonResponse({'result': 'bad', 'mensaje': u'Error, ar guardar los datos.'})
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({'result': 'bad', 'mensaje': u'Ocurrio un problema al subir archivo.'})

            if action == 'editarurkundtitulacionfinalposgrado':
                try:
                    f = CalificarPropuestaPosgradoForm(request.POST, request.FILES)
                    newfile = None
                    newfilec = None
                    if 'archivo' in request.FILES:
                        newfile = request.FILES['archivo']
                        if newfile:
                            if newfile.size > 52428800:
                                return JsonResponse({"result": "bad", "mensaje": u"Error, archivo mayor a 12 Mb."})
                            elif newfile.size <= 0:
                                return JsonResponse(
                                    {"result": "bad", "mensaje": u"Error, el archivo Urkund esta vacío."})
                            else:
                                newfilesd = newfile._name
                                ext = newfilesd[newfilesd.rfind("."):]
                                if ext == '.pdf':
                                    newfile._name = generar_nombre("urkund_", newfile._name)
                                else:
                                    return JsonResponse(
                                        {"result": "bad", "mensaje": u"Error, archivo Urkund solo en pdf."})
                    if 'correccion' in request.FILES:
                        newfilec = request.FILES['correccion']
                        if newfilec:
                            if newfilec.size > 52428800:
                                return JsonResponse({"result": "bad", "mensaje": u"Error, archivo mayor a 12 Mb."})
                            elif newfilec.size <= 0:
                                return JsonResponse(
                                    {"result": "bad", "mensaje": u"Error, el archivo correcciones esta vacío."})
                            else:
                                newfilesd = newfilec._name
                                ext = newfilesd[newfilesd.rfind("."):]
                                if ext == '.doc' or ext == '.docx' or ext == '.pdf':
                                    newfilec._name = generar_nombre("correccion_", newfilec._name)
                                else:
                                    return JsonResponse({"result": "bad",
                                                         "mensaje": u"Error, archivo correcciones solo en .doc, docx, pdf."})

                    if f.is_valid():
                        propuesta = RevisionTutoriasTemaTitulacionPosgradoProfesor.objects.get(pk=request.POST['id'])
                        if newfile:
                            if propuesta.get_urkund():
                                archivo = propuesta.get_urkund()
                                archivo.archivo = newfile
                            else:
                                archivo = ArchivoRevisionTutoriasTemaTitulacionPosgradoProfesor(
                                    revisiontutoriastematitulacionposgradoprofesor=propuesta, archivo=newfile, tipo=3,
                                    fecha=datetime.now())
                            archivo.save(request)
                            log(u"Añade archivo de correccion %s a revision[%s]" % (archivo, propuesta.id), request,
                                "edit")
                        if newfilec:
                            if propuesta.get_correccion():
                                archivo = propuesta.get_correccion()
                                archivo.archivo = newfilec
                            else:
                                archivo = ArchivoRevisionTutoriasTemaTitulacionPosgradoProfesor(
                                    revisiontutoriastematitulacionposgradoprofesor=propuesta, archivo=newfilec, tipo=4,
                                    fecha=datetime.now())
                            archivo.save(request)
                            log(u"Añade archivo de correccion %s a revision[%s]" % (archivo, propuesta.id), request,
                                "edit")
                        # propuesta.porcentajeurkund = f.cleaned_data['plagio']
                        propuesta.observacion = f.cleaned_data['observaciones']
                        if f.cleaned_data['rechazar']:
                            propuesta.estado = 3
                        if f.cleaned_data['aprobar']:
                            propuesta.porcentajeurkund = f.cleaned_data['plagio']
                            # if float(f.cleaned_data['plagio'])<= propuesta.grupo.tematica.periodo.porcentajeurkund:
                            # if float(f.cleaned_data['plagio'])<= propuesta.porcentajeurkund:
                            propuesta.estado = 2
                            # else:
                            #     propuesta.estado = 3
                        if not f.cleaned_data['rechazar'] and not f.cleaned_data['aprobar']:
                            propuesta.estado = 4
                        propuesta.save(request)

                        if json.loads(request.POST['pareja']) == True:
                             log(u"Aprobo/Reprobo a propuesta [%s] con línea de investigación: %s" % ( propuesta.id, propuesta.tematitulacionposgradomatriculacabecera.propuestatema), request, "add")
                        else:
                            log(u"Aprobo/Reprobo a propuesta [%s] con línea de investigación: %s" % (propuesta.id, propuesta.tematitulacionposgradomatricula.propuestatema), request, "add")

                        return JsonResponse({'result': False})
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({'result': 'bad', 'mensaje': u'Ocurrio un problema al subir archivo.'})

            if action == 'guardar_calificacion_sustentacion':
                try:
                    calificaciorubrica = CalificacionTitulacionPosgrado.objects.get(
                        pk=int(request.POST['id_calificacionrubrica']))
                    calificaciorubrica.confirmacalificacionrubricas = True
                    calificaciorubrica.save(request)
                    grupointegrante = TemaTitulacionPosgradoMatricula.objects.get(
                        pk=calificaciorubrica.tematitulacionposgradomatricula.id, status=True)
                    if calificaciorubrica.tipojuradocalificador == 1:
                        grupointegrante.calpresidente = calificaciorubrica.puntajerubricas
                    if calificaciorubrica.tipojuradocalificador == 2:
                        grupointegrante.calsecretaria = calificaciorubrica.puntajerubricas
                    if calificaciorubrica.tipojuradocalificador == 3:
                        grupointegrante.caldelegado = calificaciorubrica.puntajerubricas
                    grupointegrante.save(request)
                    if grupointegrante.get_todos_los_miembros_del_tribunal_calificaron_sustentacion():
                        if not CalificacionTitulacionPosgrado.objects.filter(tematitulacionposgradomatricula=grupointegrante, confirmacalificacionrubricas=False, status=True):
                            valorpuntaje = CalificacionTitulacionPosgrado.objects.filter( tematitulacionposgradomatricula=grupointegrante, status=True)
                            calificacion = round( null_to_numeric(valorpuntaje.aggregate(prom=Avg('puntajerubricas'))['prom']), 2)
                            grupointegrante.calificacion = calificacion
                            if calificacion < 70:
                                grupointegrante.estadotribunal = 3
                            else:
                                grupointegrante.estadotribunal = 2
                            grupointegrante.califico = True
                            grupointegrante.save(request)
                    return JsonResponse({"result": "ok", 'calificacion': grupointegrante.calificacion})
                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

            if action == 'guardar_calificacion_trabajoesrito':
                try:
                    calificaciorubrica = CalificacionTitulacionPosgrado.objects.get(pk=int(request.POST['id_calificacionrubrica']))
                    calificaciorubrica.confirmacalificaciontrabajo = True
                    calificaciorubrica.save(request)
                    grupointegrante = TemaTitulacionPosgradoMatricula.objects.get(pk=calificaciorubrica.tematitulacionposgradomatricula.id, status=True)
                    if calificaciorubrica.tipojuradocalificador == 1:
                        grupointegrante.calpresidente = calificaciorubrica.puntajerubricas
                    if calificaciorubrica.tipojuradocalificador == 2:
                        grupointegrante.calsecretaria = calificaciorubrica.puntajerubricas
                    if calificaciorubrica.tipojuradocalificador == 3:
                        grupointegrante.caldelegado = calificaciorubrica.puntajerubricas
                    grupointegrante.save(request)
                    if grupointegrante.get_todos_los_miembros_del_tribunal_calificaron_sustentacion():
                        if not CalificacionTitulacionPosgrado.objects.filter( tematitulacionposgradomatricula=grupointegrante, confirmacalificacionrubricas=False,status=True):
                            valorpuntaje = CalificacionTitulacionPosgrado.objects.filter(tematitulacionposgradomatricula=grupointegrante, status=True)
                            calificacion = round(null_to_numeric(valorpuntaje.aggregate(prom=Avg('puntajerubricas'))['prom']), 2)
                            grupointegrante.calificacion = calificacion
                            if calificacion < 70:
                                grupointegrante.estadotribunal = 3
                            else:
                                grupointegrante.estadotribunal = 2

                            grupointegrante.save(request)
                    return JsonResponse({"result": "ok", 'calificacion': grupointegrante.calificacion})
                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

            if action == 'guardar_calificacion_trabajoescrito_pareja':
                try:
                    calificaciorubrica = CalificacionTitulacionPosgrado.objects.get(pk=int(request.POST['id_calificacionrubrica']))
                    acompanantes = calificaciorubrica.tematitulacionposgradomatricula.cabeceratitulacionposgrado.obtener_parejas()
                    for acompanante in acompanantes:
                        calificar_acompanante = CalificacionTitulacionPosgrado.objects.filter(status=True,tematitulacionposgradomatricula=acompanante,juradocalificador=calificaciorubrica.juradocalificador)[0]
                        calificar_acompanante.confirmacalificaciontrabajo = True
                        calificar_acompanante.save(request)

                    return JsonResponse({"result": "ok"})
                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

            if action == 'updatecalificarrubricadetalle':
                try:
                    calificarricatitulacion = CalificacionTitulacionPosgrado.objects.get(
                        pk=int(request.POST['id_cabcalificarrubrica']))
                    calificarricatitulacion.confirmacalificacionrubricas = False
                    calificarricatitulacion.observacion = request.POST['id_descripcion']
                    calificarricatitulacion.save(request)
                    calificarricatitulacion.tematitulacionposgradomatricula.califico = False
                    calificarricatitulacion.tematitulacionposgradomatricula.save(request)
                    return JsonResponse({"result": "ok"})
                except Exception as ex:
                    transaction.set_rollback(True)
                    return HttpResponse(
                        json.dumps({"result": "bad", "mensaje": u"Error al eliminar los datos.(%s)" % ex}),
                        content_type="application/json")

            if action == 'updatecalificarrubricadetallepareja':
                try:
                    calificarrubicatitulacion = CalificacionTitulacionPosgrado.objects.get(pk=int(request.POST['id_cabcalificarrubrica']))
                    calificarrubicatitulacion.confirmacalificacionrubricas = False
                    calificarrubicatitulacion.observacion = request.POST['id_descripcion']
                    calificarrubicatitulacion.save(request)
                    calificarrubicatitulacion.tematitulacionposgradomatricula.califico = False
                    calificarrubicatitulacion.tematitulacionposgradomatricula.save(request)
                    # acompanante
                    acompanante =calificarrubicatitulacion.tematitulacionposgradomatricula.cabeceratitulacionposgrado.obtener_parejas()[1]
                    calificar_acompanante = CalificacionTitulacionPosgrado.objects.filter(status=True,tematitulacionposgradomatricula=acompanante,juradocalificador=calificarrubicatitulacion.juradocalificador)[0]
                    calificar_acompanante.confirmacalificacionrubricas = False
                    calificar_acompanante.observacion = request.POST['id_descripcion']
                    calificar_acompanante.save(request)
                    calificar_acompanante.tematitulacionposgradomatricula.califico = False
                    calificar_acompanante.tematitulacionposgradomatricula.save(request)
                    return JsonResponse({"result": "ok"})
                except Exception as ex:
                    transaction.set_rollback(True)
                    return HttpResponse(
                        json.dumps({"result": "bad", "mensaje": u"Error al guardar los datos.(%s)" % ex}),
                        content_type="application/json")

            if action == 'calificarrubricadetalle':
                try:
                    detallerubricatitulacion = CalificacionDetalleRubricaTitulacionPosgrado.objects.get(
                        pk=int(request.POST['id_calificardetallerubrica']))
                    detallerubricatitulacion.puntaje = request.POST['valornota']
                    detallerubricatitulacion.save(request)
                    detallerubricatitulacion.calificacionrubrica.confirmacalificacionrubricas = False

                    detallerubricatitulacion.calificacionrubrica.tematitulacionposgradomatricula.califico = False
                    detallerubricatitulacion.calificacionrubrica.tematitulacionposgradomatricula.save(request)
                    detallemodelorubrica = detallerubricatitulacion.calificacionrubrica.calificaciondetallemodelorubricatitulacionposgrado_set.filter(
                        status=True)
                    for detalle in detallemodelorubrica:
                        detallecalificacion = CalificacionDetalleRubricaTitulacionPosgrado.objects.filter(
                            calificacionrubrica=detalle.calificacionrubrica,
                            detallerubricatitulacionposgrado__modelorubrica=detalle.modelorubrica,
                            status=True).aggregate(valor=Sum('puntaje'))['valor']
                        detalle.puntaje = detallecalificacion
                        detalle.save()

                    detallerubricatitulacion.calificacionrubrica.puntajerubricas = \
                    detallerubricatitulacion.calificacionrubrica.calificacion_total()['calificaciontotal']
                    detallerubricatitulacion.calificacionrubrica.save(request)
                    return JsonResponse({"result": "ok", "calificacion_total":
                        detallerubricatitulacion.calificacionrubrica.calificacion_total()['calificaciontotal']})
                except Exception as ex:
                    transaction.set_rollback(True)
                    return HttpResponse(
                        json.dumps({"result": "bad", "mensaje": u"Error al eliminar los datos.(%s)" % ex}),
                        content_type="application/json")

            if action == 'calificarrubricadetallepareja':
                try:
                    # obtengo rubrica del primer integrante
                    detallerubricatitulacion = CalificacionDetalleRubricaTitulacionPosgrado.objects.get(pk=int(request.POST['id_calificardetallerubrica']))
                    detallerubricatitulacion.puntaje = request.POST['valornota']
                    detallerubricatitulacion.save(request)
                    detallerubricatitulacion.calificacionrubrica.confirmacalificacionrubricas = False

                    detallerubricatitulacion.calificacionrubrica.tematitulacionposgradomatricula.califico = False
                    detallerubricatitulacion.calificacionrubrica.tematitulacionposgradomatricula.save(request)
                    detallemodelorubrica = detallerubricatitulacion.calificacionrubrica.calificaciondetallemodelorubricatitulacionposgrado_set.filter(status=True)
                    for detalle in detallemodelorubrica:
                        detallecalificacion = CalificacionDetalleRubricaTitulacionPosgrado.objects.filter(
                            calificacionrubrica=detalle.calificacionrubrica,
                            detallerubricatitulacionposgrado__modelorubrica=detalle.modelorubrica,
                            status=True).aggregate(valor=Sum('puntaje'))['valor']
                        detalle.puntaje = detallecalificacion
                        detalle.save(request)

                    detallerubricatitulacion.calificacionrubrica.puntajerubricas = detallerubricatitulacion.calificacionrubrica.calificacion_total()['calificaciontotal']
                    detallerubricatitulacion.calificacionrubrica.save(request)

                    # obtengo al acompanante
                    acompanantes = detallerubricatitulacion.calificacionrubrica.tematitulacionposgradomatricula.cabeceratitulacionposgrado.obtener_parejas().exclude(pk = detallerubricatitulacion.calificacionrubrica.tematitulacionposgradomatricula_id)
                    for acompanante in acompanantes:
                        calificar_acompanante = CalificacionTitulacionPosgrado.objects.filter(status=True, tematitulacionposgradomatricula=acompanante,juradocalificador=detallerubricatitulacion.calificacionrubrica.juradocalificador)[0]
                        detallerubricatitulacionacompanante = calificar_acompanante.calificaciondetallerubricatitulacionposgrado_set.get(detallerubricatitulacionposgrado=detallerubricatitulacion.detallerubricatitulacionposgrado)
                        detallerubricatitulacionacompanante.puntaje = request.POST['valornota']
                        detallerubricatitulacionacompanante.save(request)
                        detallerubricatitulacionacompanante.calificacionrubrica.confirmacalificacionrubricas = False
                        detallerubricatitulacionacompanante.calificacionrubrica.tematitulacionposgradomatricula.califico = False
                        detallerubricatitulacionacompanante.calificacionrubrica.tematitulacionposgradomatricula.save(request)
                        detallemodelorubricaacompanante = detallerubricatitulacionacompanante.calificacionrubrica.calificaciondetallemodelorubricatitulacionposgrado_set.filter(status=True)
                        for detalle in detallemodelorubricaacompanante:
                            detallecalificacionacompanante = CalificacionDetalleRubricaTitulacionPosgrado.objects.filter(
                                calificacionrubrica=detalle.calificacionrubrica,
                                detallerubricatitulacionposgrado__modelorubrica=detalle.modelorubrica,
                                status=True).aggregate(valor=Sum('puntaje'))['valor']
                            detalle.puntaje = detallecalificacionacompanante
                            detalle.save(request)

                        detallerubricatitulacionacompanante.calificacionrubrica.puntajerubricas = detallerubricatitulacionacompanante.calificacionrubrica.calificacion_total()['calificaciontotal']
                        detallerubricatitulacionacompanante.calificacionrubrica.save(request)

                    return JsonResponse({"result": "ok", "calificacion_total":
                        detallerubricatitulacion.calificacionrubrica.calificacion_total()['calificaciontotal']})
                except Exception as ex:
                    transaction.set_rollback(True)
                    return HttpResponse(json.dumps({"result": "bad", "mensaje": u"Error al calificar.(%s)" % ex}),
                                        content_type="application/json")

            if action == 'actaacompanamiento_pdf':
                try:
                    actaposgrado = acompanamientoposgrado(request.POST['id'])
                    return actaposgrado
                except Exception as ex:
                    pass

            if action == 'informe_tribunal_pdf':
                try:
                    informe = informetribunaltitulacionposgrado(request.POST['id'])
                    return informe
                except Exception as ex:
                    pass

            if action == 'informe_final_tutoria_posgrado_pdf':
                try:
                    if request.POST['en_pareja'] == 'true':
                        informe_tutoria_posgrado = reporte_informe_tutoria_posgrado_pareja(request.POST['id'])
                    else:
                        informe_tutoria_posgrado = reporte_informe_tutoria_posgrado(request.POST['id'])
                    return informe_tutoria_posgrado
                except Exception as ex:
                    pass

            if action == 'actaacompanamientopareja_pdf':
                try:
                    actaposgrado = acompanamientoposgradopareja(request.POST['id'])
                    return actaposgrado
                except Exception as ex:
                    pass

            if action == 'actacalificacion_pdf':
                try:
                    if 'id' in request.POST:
                        data['grupo'] = grupo = TemaTitulacionPosgradoMatricula.objects.get(pk=int(request.POST['id']))
                        tribunal = grupo.tribunaltematitulacionposgradomatricula_set.filter(status=True)[0]
                        if grupo.tribunaltematitulacionposgradomatricula_set.filter(status=True)[
                            0].presidentepropuesta == profesor:
                            cargo = 'PRESIDENTE'
                        if grupo.tribunaltematitulacionposgradomatricula_set.filter(status=True)[
                            0].secretariopropuesta == profesor:
                            cargo = 'SECRETARIO'
                        if grupo.tribunaltematitulacionposgradomatricula_set.filter(status=True)[
                            0].delegadopropuesta == profesor:
                            cargo = 'DELEGADO'
                        data['cargo'] = cargo
                        data['profesor'] = profesor
                        periodo = grupo.matricula.nivel.periodo
                        carrera = grupo.matricula.inscripcion.carrera
                        data['configuracion'] = c = ConfiguracionTitulacionPosgrado.objects.get(periodo=periodo,
                                                                                                carrera=carrera,
                                                                                                status=True)
                        data['tiporubrica'] = TIPO_RUBRICA
                        data['acompanamientos'] = TutoriasTemaTitulacionPosgradoProfesor.objects.filter(status=True,
                                                                                                        tematitulacionposgradomatricula=grupo)
                        data['integrantes'] = integrantes = grupo
                        # valida = 0
                        # for listaintegrantes in integrantes:
                        #     if listaintegrantes.matricula.examen_complexivo():
                        #         if listaintegrantes.matricula.examen_complexivo().estado == 2 and listaintegrantes.matricula.examen_complexivo().matricula.estado == 9:
                        #             valida += 1
                        # if integrantes.count()<=valida:
                        #     valida = 1
                        # data['valida'] = valida
                        data['facultad'] = grupo.matricula.inscripcion.coordinacion
                        fecha = tribunal.fechadefensa
                        data['fecha'] = str(fecha.day) + " de " + str(
                            MESES_CHOICES[fecha.month - 1][1]).lower() + " del " + str(fecha.year)
                        data['secretariageneral'] = CargoInstitucion.objects.get(
                            pk=1).persona.nombre_completo_inverso() if CargoInstitucion.objects.get(pk=1) else None
                        return conviert_html_to_pdf('pro_tutoriaposgrado/actacalificacion_pdf.html',
                                                    {
                                                        'pagesize': 'A4',
                                                        'data': data,
                                                    }
                                                    )
                except Exception as ex:
                    pass

            if action == 'pdfrubricacalificacionesposgrado':
                try:
                    iddetallegrupo = request.POST['id']
                    rubricatribunal = rubricatribunalcalificacionposgrado(iddetallegrupo)
                    return rubricatribunal
                except Exception as ex:
                    pass

            if action == 'registrar_respuesta_informe':
               with transaction.atomic():
                    try:
                        pregunta = PreguntaRevision.objects.get(pk=request.POST['id_pregunta'])
                        pregunta.respuesta = request.POST['respuesta']
                        pregunta.save(request)
                        log(f"repuesta guardada en la pregunta: {pregunta} con respuesta: {pregunta.respuesta}" , request,"edit")
                        return JsonResponse({"result": "ok"})
                    except Exception as ex:
                        transaction.set_rollback(True)
                        return JsonResponse({'result': 'bad', 'mensaje': f'Error al guardar los datos. {ex}'})

            if action == 'registrar_respuesta_rubrica':
               with transaction.atomic():
                    try:
                        rubrica_id = int(request.POST['rubrica_id'])
                        modelorubrica_id = int(request.POST['modelorubrica_id'])
                        respuesta = request.POST['respuesta']
                        pareja = int(request.POST['pareja'])
                        tema_id = request.POST['tema_id']
                        puntaje = float(request.POST['puntaje'])
                        presidentepropuestacalificacionrubricatitulacion_id = int(request.POST['presidentepropuestacalificacionrubricatitulacion_id'])
                        secretariopropuestacalificacionrubricatitulacion_id = int(request.POST['secretariopropuestacalificacionrubricatitulacion_id'])
                        delegadopropuestapresidentepropuestacalificacionrubricatitulacion_id = int(request.POST['delegadopropuestapresidentepropuestacalificacionrubricatitulacion_id'])
                        detallerubricatitulacionposgrado_id = request.POST['detallerubricatitulacionposgrado_id']

                        if pareja == 1:
                            if respuesta == 'si':
                                puntaje = puntaje
                            else:
                                puntaje = 0
                                ###
                            eCalificacionTitulacionPosgrados = CalificacionTitulacionPosgrado.objects.filter(status=True, pk__in=[presidentepropuestacalificacionrubricatitulacion_id,secretariopropuestacalificacionrubricatitulacion_id,delegadopropuestapresidentepropuestacalificacionrubricatitulacion_id])
                            for eCalificacionTitulacionPosgrado in eCalificacionTitulacionPosgrados:
                                eCalificacionDetalleRubricaTitulacionPosgrado = CalificacionDetalleRubricaTitulacionPosgrado.objects.filter( status=True, calificacionrubrica=eCalificacionTitulacionPosgrado,detallerubricatitulacionposgrado_id=detallerubricatitulacionposgrado_id)
                                detallerubricatitulacion = eCalificacionDetalleRubricaTitulacionPosgrado.first()
                            # obtengo rubrica del primer integrante
                            # detallerubricatitulacion = CalificacionDetalleRubricaTitulacionPosgrado.objects.get(pk=int(request.POST['id_calificardetallerubrica']))
                                detallerubricatitulacion.puntaje = puntaje
                                detallerubricatitulacion.save(request)
                                detallerubricatitulacion.calificacionrubrica.confirmacalificacionrubricas = False

                                detallerubricatitulacion.calificacionrubrica.tematitulacionposgradomatricula.califico = False
                                detallerubricatitulacion.calificacionrubrica.tematitulacionposgradomatricula.save(request)
                                detallemodelorubrica = detallerubricatitulacion.calificacionrubrica.calificaciondetallemodelorubricatitulacionposgrado_set.filter(status=True)
                                for detalle in detallemodelorubrica:
                                    detallecalificacion = CalificacionDetalleRubricaTitulacionPosgrado.objects.filter(
                                        calificacionrubrica=detalle.calificacionrubrica,
                                        detallerubricatitulacionposgrado__modelorubrica=detalle.modelorubrica,
                                        status=True).aggregate(valor=Sum('puntaje'))['valor']
                                    detalle.puntaje = detallecalificacion
                                    detalle.save(request)

                                detallerubricatitulacion.calificacionrubrica.puntajerubricas = detallerubricatitulacion.calificacionrubrica.calificacion_total()['calificaciontotal']
                                detallerubricatitulacion.calificacionrubrica.save(request)

                                # obtengo al acompanante
                                acompanantes = detallerubricatitulacion.calificacionrubrica.tematitulacionposgradomatricula.cabeceratitulacionposgrado.obtener_parejas().exclude(pk=detallerubricatitulacion.calificacionrubrica.tematitulacionposgradomatricula_id)
                                for acompanante in acompanantes:
                                    calificar_acompanante = CalificacionTitulacionPosgrado.objects.filter(status=True,tematitulacionposgradomatricula=acompanante,juradocalificador=detallerubricatitulacion.calificacionrubrica.juradocalificador)[0]
                                    detallerubricatitulacionacompanante = calificar_acompanante.calificaciondetallerubricatitulacionposgrado_set.get(detallerubricatitulacionposgrado=detallerubricatitulacion.detallerubricatitulacionposgrado)
                                    detallerubricatitulacionacompanante.puntaje = puntaje
                                    detallerubricatitulacionacompanante.save(request)
                                    detallerubricatitulacionacompanante.calificacionrubrica.confirmacalificacionrubricas = False
                                    detallerubricatitulacionacompanante.calificacionrubrica.tematitulacionposgradomatricula.califico = False
                                    detallerubricatitulacionacompanante.calificacionrubrica.tematitulacionposgradomatricula.save(request)
                                    detallemodelorubricaacompanante = detallerubricatitulacionacompanante.calificacionrubrica.calificaciondetallemodelorubricatitulacionposgrado_set.filter(status=True)
                                    for detalle in detallemodelorubricaacompanante:
                                        detallecalificacionacompanante = CalificacionDetalleRubricaTitulacionPosgrado.objects.filter(calificacionrubrica=detalle.calificacionrubrica,detallerubricatitulacionposgrado__modelorubrica=detalle.modelorubrica,status=True).aggregate(valor=Sum('puntaje'))['valor']
                                        detalle.puntaje = detallecalificacionacompanante
                                        detalle.save(request)

                                    detallerubricatitulacionacompanante.calificacionrubrica.puntajerubricas = detallerubricatitulacionacompanante.calificacionrubrica.calificacion_total()['calificaciontotal']
                                    detallerubricatitulacionacompanante.calificacionrubrica.save(request)

                        else:
                            if respuesta == 'si':
                                puntaje = puntaje
                            else:
                                puntaje = 0

                            eCalificacionTitulacionPosgrados = CalificacionTitulacionPosgrado.objects.filter(status=True, pk__in=[presidentepropuestacalificacionrubricatitulacion_id, secretariopropuestacalificacionrubricatitulacion_id, delegadopropuestapresidentepropuestacalificacionrubricatitulacion_id])

                            for eCalificacionTitulacionPosgrado in eCalificacionTitulacionPosgrados:
                                eCalificacionDetalleRubricaTitulacionPosgrado =CalificacionDetalleRubricaTitulacionPosgrado.objects.filter(status=True,calificacionrubrica = eCalificacionTitulacionPosgrado,detallerubricatitulacionposgrado_id =detallerubricatitulacionposgrado_id)
                                detallerubricatitulacion =eCalificacionDetalleRubricaTitulacionPosgrado.first()
                                detallerubricatitulacion.puntaje = puntaje
                                detallerubricatitulacion.save(request)
                                detallerubricatitulacion.calificacionrubrica.confirmacalificacionrubricas = False
                                detallerubricatitulacion.calificacionrubrica.tematitulacionposgradomatricula.califico = False
                                detallerubricatitulacion.calificacionrubrica.tematitulacionposgradomatricula.save(request)
                                detallemodelorubrica = detallerubricatitulacion.calificacionrubrica.calificaciondetallemodelorubricatitulacionposgrado_set.filter(status=True)
                                for detalle in detallemodelorubrica:
                                    detallecalificacion = CalificacionDetalleRubricaTitulacionPosgrado.objects.filter(calificacionrubrica=detalle.calificacionrubrica,detallerubricatitulacionposgrado__modelorubrica=detalle.modelorubrica,status=True).aggregate(valor=Sum('puntaje'))['valor']
                                    detalle.puntaje = detallecalificacion
                                    detalle.save()

                                detallerubricatitulacion.calificacionrubrica.puntajerubricas = detallerubricatitulacion.calificacionrubrica.calificacion_total()['calificaciontotal']
                                detallerubricatitulacion.calificacionrubrica.save(request)

                        return JsonResponse({"result": "ok"})
                    except Exception as ex:
                        transaction.set_rollback(True)
                        return JsonResponse({'result': 'bad', 'mensaje': f'Error al guardar los datos. {ex}'})

            if action == 'registrar_obsevacion_seccion_informe':
               with transaction.atomic():
                    try:
                        seccion = SeccionRevision.objects.get(pk=request.POST['id_seccion'])
                        seccion.observacion = request.POST['observacion']
                        seccion.save(request)
                        log(f"repuesta guardada en la seccion: {seccion} con respuesta: {seccion.observacion}" , request,"edit")
                        return JsonResponse({"result": "ok"})
                    except Exception as ex:
                        transaction.set_rollback(True)
                        return JsonResponse({'result': 'bad', 'mensaje': f'Error al guardar los datos. {ex}'})

            if action == 'actualizar_observacion_artic':
               with transaction.atomic():
                    try:
                        pareja = int(request.POST['pareja'])
                        if pareja ==1:
                            calificarrubicatitulacion = CalificacionTitulacionPosgrado.objects.get(pk=int(request.POST['calificacionrubricatitulacion_id']))
                            calificarrubicatitulacion.confirmacalificacionrubricas = False
                            calificarrubicatitulacion.observacion = request.POST['observacion']
                            calificarrubicatitulacion.save(request)
                            calificarrubicatitulacion.tematitulacionposgradomatricula.califico = False
                            calificarrubicatitulacion.tematitulacionposgradomatricula.save(request)
                            # acompanante
                            acompanantes = calificarrubicatitulacion.tematitulacionposgradomatricula.cabeceratitulacionposgrado.obtener_parejas().exclude( pk=calificarrubicatitulacion.tematitulacionposgradomatricula_id)
                            for acompanante in acompanantes:
                                calificar_acompanante = CalificacionTitulacionPosgrado.objects.filter(status=True,tematitulacionposgradomatricula=acompanante,juradocalificador=calificarrubicatitulacion.juradocalificador)[0]
                                calificar_acompanante.observacion = request.POST['observacion']
                                calificar_acompanante.save(request)
                                calificar_acompanante.tematitulacionposgradomatricula.save(request)

                        else:
                            calificarricatitulacion = CalificacionTitulacionPosgrado.objects.get( pk=int(request.POST['calificacionrubricatitulacion_id']))
                            calificarricatitulacion.observacion = request.POST['observacion']
                            calificarricatitulacion.save(request)
                            calificarricatitulacion.tematitulacionposgradomatricula.save(request)


                        return JsonResponse({"result": "ok"})
                    except Exception as ex:
                        transaction.set_rollback(True)
                        return JsonResponse({'result': 'bad', 'mensaje': f'Error al guardar los datos. {ex}'})

            if action == 'guardar_revision_tribunal':
               with transaction.atomic():
                    try:
                        revision = Revision.objects.get(pk=request.POST['id'])

                        if revision.existen_preguntas_sin_responder():
                            return JsonResponse({'result': 'bad', 'mensaje': f'Responda todas las preguntas.'})

                        revision.observacion = request.POST['observacion']
                        revision.estado = request.POST['estado_revision']
                        revision.save(request)

                        historial = HistorialDocRevisionTribunal(
                            revision=revision,
                            persona = persona,
                            estado = revision.estado,
                            observacion=revision.observacion
                        )
                        historial.save(request)
                        log(f"revision guardada correctamente: {revision.get_estado_display()}" , request,"edit")
                        return JsonResponse({"result": "ok"})
                    except Exception as ex:
                        transaction.set_rollback(True)
                        return JsonResponse({'result': 'bad', 'mensaje': f'Error al guardar los datos. {ex}'})

            if action == 'guardar_calificacion_titulacion_artic':
               with transaction.atomic():
                    try:
                        pareja = int(request.POST['pareja'])
                        tema_id = int(request.POST['tema_id'])
                        modelorubrica_id = int(request.POST['modelorubrica_id'])

                        #puntajemodelorubrica
                        if pareja ==1:
                            eTemaTitulacionPosgradoMatriculaCabecera = TemaTitulacionPosgradoMatriculaCabecera.objects.get(pk=tema_id)
                            eTemaTitulacionPosgradoMatriculas = eTemaTitulacionPosgradoMatriculaCabecera.obtener_parejas()
                            for eTemaTitulacionPosgradoMatricula in eTemaTitulacionPosgradoMatriculas:
                                eModeloRubricaTitulacionPosgrado = ModeloRubricaTitulacionPosgrado.objects.get(pk=modelorubrica_id)
                                puntaje = eTemaTitulacionPosgradoMatricula.puntajemodelorubrica(eModeloRubricaTitulacionPosgrado)
                                if not puntaje == 70.0:
                                    eTemaTitulacionPosgradoMatricula.estadotribunal = 3
                                    eTemaTitulacionPosgradoMatricula.califico = False
                                else:
                                    eTemaTitulacionPosgradoMatricula.estadotribunal = 1
                                eTemaTitulacionPosgradoMatricula.save(request)

                        else:
                            eTemaTitulacionPosgradoMatricula = TemaTitulacionPosgradoMatricula.objects.get(pk=tema_id)
                            eModeloRubricaTitulacionPosgrado = ModeloRubricaTitulacionPosgrado.objects.get(pk=modelorubrica_id)
                            puntaje = eTemaTitulacionPosgradoMatricula.puntajemodelorubrica(eModeloRubricaTitulacionPosgrado)
                            if not puntaje == 70.0:
                                eTemaTitulacionPosgradoMatricula.estadotribunal = 3
                                eTemaTitulacionPosgradoMatricula.califico = False
                            else:
                                eTemaTitulacionPosgradoMatricula.estadotribunal = 1
                                eTemaTitulacionPosgradoMatricula.save(request)


                        return JsonResponse({"result": "ok","mensaje":"Calificación guardada con exito"})
                    except Exception as ex:
                        transaction.set_rollback(True)
                        return JsonResponse({'result': 'bad', 'mensaje': f'Error al guardar los datos. {ex}'})

            if action == 'editar_dictamen':
               with transaction.atomic():
                    try:
                        revision = Revision.objects.get(pk=request.POST['id'])
                        revision.estado = request.POST['dictamen']
                        revision.save(request)

                        historial = HistorialDocRevisionTribunal(
                            revision=revision,
                            persona = persona,
                            estado = revision.estado

                        )
                        historial.save(request)
                        log(f"edito dictamen de la revision: {revision.get_estado_display()}" , request,"edit")
                        return JsonResponse({'result': False, 'mensaje': u'Guardado con exito'})
                    except Exception as ex:
                        transaction.set_rollback(True)
                        return JsonResponse({'result': 'bad', 'mensaje': f'Error al guardar los datos. {ex}'})

            elif action == 'add':
                try:
                    tema = TemaTitulacionPosgradoMatricula.objects.get(pk=request.POST['id'])
                    temaprofesor = TemaTitulacionPosgradoProfesor(tematitulacionposgradomatricula=tema,
                                                                  profesor=profesor,
                                                                  fecharegistro=hoy)
                    temaprofesor.save(request)
                    log(u'Ingreso solicitud tema posgrado: %s' % temaprofesor, request, "add")
                    return JsonResponse({"result": "ok"})
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", "mensaje": u"Error al aprobar los datos. %s"%(ex.__str__())})

            elif action == 'addpareja':
                try:
                    tema = TemaTitulacionPosgradoMatriculaCabecera.objects.get(pk=request.POST['id'])
                    temaprofesor = TemaTitulacionPosgradoProfesor(tematitulacionposgradomatriculacabecera=tema,
                                                                  tematitulacionposgradomatricula=None,
                                                                  profesor=profesor,
                                                                  fecharegistro=hoy)
                    temaprofesor.save(request)
                    # # Guaddar Historial
                    # tematitulacionposgradomatriculahistorial = TemaTitulacionPosgradoProfesorHistorial(tematitulacionposgradoprofesor=temaprofesor,
                    #                                                                                    observacion='NINGUNA',
                    #                                                                                    estado=1)
                    # tematitulacionposgradomatriculahistorial.save(request)
                    log(u'Ingreso solicitud tema posgrado: %s' % temaprofesor, request, "add")
                    return JsonResponse({"result": "ok"})
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", "mensaje": u"Error al aprobar los datos. %s"%(ex.__str__())})

            elif action == 'firmar_acta_sustentacion_certificacion_por_archivo':
                try:
                    persona = request.session.get('persona')
                    tipo = int(request.POST.get('tipo', '0'))
                    ACTA_SUSTENTACION_NOTA = 10
                    CERTIFICACION_DEFENSA = 9
                    pk = request.POST.get('id', '0')

                    if pk == 0:
                        raise NameError("Parametro no encontrado")

                    eTemaTitulacionPosgradoMatricula = TemaTitulacionPosgradoMatricula.objects.get(pk=pk)


                    if tipo == CERTIFICACION_DEFENSA:
                        CARGO_PRESIDENTE = "PRESIDENTE/A DEL TRIBUNAL"
                        CARGO_VOCAL = "VOCAL"
                        CARGO_SECRETARIO = "SECRETARIO/A DEL TRIBUNAL"
                        observacion = f'Certificación de la defensa firmado por {persona}'
                        if variable_valor("PUEDE_FIRMAR_CERTIFICACION_DEFENSA_POR_ORDEN"):
                            puede, mensaje = eTemaTitulacionPosgradoMatricula.puede_firmar_integrante_segun_orden_por_tipo( persona, CERTIFICACION_DEFENSA)
                        else:
                            puede, mensaje = eTemaTitulacionPosgradoMatricula.integrante_ya_firmo_por_tipo(persona, CERTIFICACION_DEFENSA)

                        if puede:
                            integrante = eTemaTitulacionPosgradoMatricula.get_integrante_por_tipo(persona,CERTIFICACION_DEFENSA)
                            pdf = eTemaTitulacionPosgradoMatricula.get_documento_certificacion_defensa()

                            if integrante.ordenfirma_id == 4:#presidente
                                palabras = CARGO_PRESIDENTE
                            if integrante.ordenfirma_id == 5:#vocal
                                palabras = CARGO_VOCAL
                            if integrante.ordenfirma_id == 6:#secretario
                                palabras = CARGO_SECRETARIO


                            #palabras = u"%s" % integrante.persona.nombres
                            firma = request.FILES.get("firma")
                            passfirma = request.POST.get('palabraclave')
                            bytes_certificado = firma.read()
                            extension_certificado = os.path.splitext(firma.name)[1][1:]
                            x, y, numpaginafirma = obtener_posicion_x_y_saltolinea(pdf.url, palabras)
                            datau = JavaFirmaEc(
                                archivo_a_firmar=pdf, archivo_certificado=bytes_certificado,
                                extension_certificado=extension_certificado,
                                password_certificado=passfirma,
                                page=int(numpaginafirma), reason='', lx=x + 60, ly=y + 30
                            ).sign_and_get_content_bytes()

                            documento_a_firmar = io.BytesIO()
                            documento_a_firmar.write(datau)
                            documento_a_firmar.seek(0)
                            orden_firma = f'_firm_orden_{str(integrante.ordenfirma.orden)}'
                            eTemaTitulacionPosgradoMatricula.get_documento_certificacion_defensa().save( f'{eTemaTitulacionPosgradoMatricula.get_documento_certificacion_defensa().name.split("/")[-1].replace(".pdf", "")}{orden_firma}.pdf', ContentFile(documento_a_firmar.read()))
                            integrante.firmo = True
                            integrante.save(request)
                            eTemaTitulacionPosgradoMatricula.save(request)

                            eTemaTitulacionPosgradoMatricula.guardar_historial_firma_titulacion_pos_mat_certificacion_defensa(request,observacion,eTemaTitulacionPosgradoMatricula.get_documento_certificacion_defensa())
                            eTemaTitulacionPosgradoMatricula.notificar_integrantes_a_firmar_certificacion_defensa(request)
                            log(u"Firmo CERTIFICACION_DEFENSA", request, 'edit')


                        else:
                            raise NameError(f"{mensaje}")
                    if tipo == ACTA_SUSTENTACION_NOTA:
                        CARGO_PRESIDENTE = "PRESIDENTE/A DEL TRIBUNAL"
                        CARGO_VOCAL = "VOCAL"
                        CARGO_SECRETARIO = "SECRETARIO/A DEL TRIBUNAL"
                        CARGO_MAGISTER = "MAGÍSTER"
                        observacion = f'Acta sustentación con notas firmado por {persona}'
                        if variable_valor("PUEDE_FIRMAR_ACTA_SUSTENTACION_POR_ORDEN"):
                            puede, mensaje = eTemaTitulacionPosgradoMatricula.puede_firmar_integrante_segun_orden_por_tipo( persona, ACTA_SUSTENTACION_NOTA)
                        else:
                            puede, mensaje = eTemaTitulacionPosgradoMatricula.integrante_ya_firmo_por_tipo(persona, ACTA_SUSTENTACION_NOTA)

                        if puede:
                            integrante = eTemaTitulacionPosgradoMatricula.get_integrante_por_tipo(persona,ACTA_SUSTENTACION_NOTA)
                            pdf = eTemaTitulacionPosgradoMatricula.get_documento_acta_sustentacion_nota()
                            if integrante.ordenfirma_id == 7:#presidente
                                palabras = CARGO_PRESIDENTE
                            if integrante.ordenfirma_id == 8:# secretario
                                palabras = CARGO_SECRETARIO
                            if integrante.ordenfirma_id == 9:#vocal
                                palabras = CARGO_VOCAL
                            if integrante.ordenfirma_id == 10:#maestrante
                                palabras = CARGO_MAGISTER
                            #palabras = u"%s" % integrante.persona.nombres
                            firma = request.FILES.get("firma")
                            passfirma = request.POST.get('palabraclave')
                            bytes_certificado = firma.read()
                            extension_certificado = os.path.splitext(firma.name)[1][1:]
                            x, y, numpaginafirma = obtener_posicion_x_y_saltolinea(pdf.url, palabras)
                            datau = JavaFirmaEc(
                                archivo_a_firmar=pdf, archivo_certificado=bytes_certificado,
                                extension_certificado=extension_certificado,
                                password_certificado=passfirma,
                                page=int(numpaginafirma), reason='', lx=x + 50, ly=y + 30
                            ).sign_and_get_content_bytes()

                            documento_a_firmar = io.BytesIO()
                            documento_a_firmar.write(datau)
                            documento_a_firmar.seek(0)
                            orden_firma = f'_firm_orden_{str(integrante.ordenfirma.orden)}'
                            eTemaTitulacionPosgradoMatricula.get_documento_acta_sustentacion_nota().save( f'{eTemaTitulacionPosgradoMatricula.get_documento_acta_sustentacion_nota().name.split("/")[-1].replace(".pdf", "")}{orden_firma}.pdf', ContentFile(documento_a_firmar.read()))
                            integrante.firmo = True
                            integrante.save(request)
                            eTemaTitulacionPosgradoMatricula.save(request)

                            eTemaTitulacionPosgradoMatricula.guardar_historial_firma_titulacion_pos_mat_acta_sustentacion_nota(request,observacion,eTemaTitulacionPosgradoMatricula.get_documento_acta_sustentacion_nota())
                            eTemaTitulacionPosgradoMatricula.notificar_integrantes_a_firmar_acta_sustentacion(request)
                            log(u"Firmo ACTA_SUSTENTACION_NOTA", request, 'edit')
                        else:
                            raise NameError(f"{mensaje}")
                    messages.success(request, "Firmado correctamente.")
                    return JsonResponse({"result": "ok"})
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", "mensaje": u"%s" % ex})

            elif action == 'firmar_acta_sustentacion_certificacion_por_token':
                try:
                    persona = request.session.get('persona')
                    tipo = int(request.POST.get('tipo', '0'))
                    ACTA_SUSTENTACION_NOTA = 10
                    CERTIFICACION_DEFENSA = 9
                    pk = request.POST.get('id', '0')

                    if pk == 0:
                        raise NameError("Parametro no encontrado")

                    eTemaTitulacionPosgradoMatricula = TemaTitulacionPosgradoMatricula.objects.get(pk=pk)

                    if tipo == CERTIFICACION_DEFENSA:
                        observacion = f'Doc. Certificación de la defensa firmado por {persona}'
                        if variable_valor("PUEDE_FIRMAR_CERTIFICACION_DEFENSA_POR_ORDEN"):
                            puede, mensaje = eTemaTitulacionPosgradoMatricula.puede_firmar_integrante_segun_orden_por_tipo( persona, CERTIFICACION_DEFENSA)
                        else:
                            puede, mensaje = eTemaTitulacionPosgradoMatricula.integrante_ya_firmo_por_tipo(persona, CERTIFICACION_DEFENSA)
                        if puede:
                            integrante = eTemaTitulacionPosgradoMatricula.get_integrante_por_tipo(persona,CERTIFICACION_DEFENSA)
                            f = ArchivoInvitacionForm(request.POST, request.FILES)
                            if f.is_valid() and request.FILES.get('archivo', None):
                                newfile = request.FILES.get('archivo')
                                if newfile:
                                    if newfile.size > 6291456:
                                        return JsonResponse({"result": "bad", "mensaje": u"Error, archivo mayor a 6 Mb."})
                                    else:
                                        newfilesd = newfile._name
                                        ext = newfilesd[newfilesd.rfind("."):].lower()
                                        if ext == '.pdf':
                                            _name = generar_nombre(f"{eTemaTitulacionPosgradoMatricula.get_documento_certificacion_defensa().__str__().split('/')[-1].replace('.pdf', '_')}",'')
                                            _name = remover_caracteres_tildes_unicode( remover_caracteres_especiales_unicode(_name)).lower().replace(' ','_').replace('-', '_')
                                            newfile._name = f"{_name}.pdf"

                                            eTemaTitulacionPosgradoMatricula.archivo_certificacion_defensa = newfile
                                            integrante.firmo = True
                                            integrante.save(request)
                                            eTemaTitulacionPosgradoMatricula.save(request)

                                            eTemaTitulacionPosgradoMatricula.guardar_historial_firma_titulacion_pos_mat_certificacion_defensa(request, observacion,eTemaTitulacionPosgradoMatricula.get_documento_certificacion_defensa())
                                            eTemaTitulacionPosgradoMatricula.notificar_integrantes_a_firmar_certificacion_defensa(request)
                                            log(u"Firmo CERTIFICACION_DEFENSA POR DESCARGA", request, 'edit')
                                        else:
                                            return JsonResponse({"result": "bad", "mensaje": u"Error, Solo archivos PDF"})

                        else:
                            raise NameError(f"{mensaje}")

                    if tipo == ACTA_SUSTENTACION_NOTA:

                        observacion = f'Doc. Acta sustentación con notas firmado por {persona}'
                        if variable_valor("PUEDE_FIRMAR_ACTA_SUSTENTACION_POR_ORDEN"):
                            puede, mensaje = eTemaTitulacionPosgradoMatricula.puede_firmar_integrante_segun_orden_por_tipo( persona, ACTA_SUSTENTACION_NOTA)
                        else:
                            puede, mensaje = eTemaTitulacionPosgradoMatricula.integrante_ya_firmo_por_tipo(persona, ACTA_SUSTENTACION_NOTA)

                        if puede:
                            integrante = eTemaTitulacionPosgradoMatricula.get_integrante_por_tipo(persona,ACTA_SUSTENTACION_NOTA)

                            f = ArchivoInvitacionForm(request.POST, request.FILES)
                            if f.is_valid() and request.FILES.get('archivo', None):
                                newfile = request.FILES.get('archivo')
                                if newfile:
                                    if newfile.size > 6291456:
                                        return JsonResponse(
                                            {"result": "bad", "mensaje": u"Error, archivo mayor a 6 Mb."})
                                    else:
                                        newfilesd = newfile._name
                                        ext = newfilesd[newfilesd.rfind("."):].lower()
                                        if ext == '.pdf':
                                            _name = generar_nombre(f"{eTemaTitulacionPosgradoMatricula.get_documento_acta_sustentacion_nota().__str__().split('/')[-1].replace('.pdf', '_')}", '')
                                            _name = remover_caracteres_tildes_unicode(remover_caracteres_especiales_unicode(_name)).lower().replace(' ','_').replace('-', '_')
                                            newfile._name = f"{_name}.pdf"

                                            eTemaTitulacionPosgradoMatricula.archivo_acta_sustentacion = newfile
                                            integrante.firmo = True
                                            integrante.save(request)
                                            eTemaTitulacionPosgradoMatricula.save(request)

                                            eTemaTitulacionPosgradoMatricula.guardar_historial_firma_titulacion_pos_mat_acta_sustentacion_nota(request, observacion,eTemaTitulacionPosgradoMatricula.get_documento_acta_sustentacion_nota())
                                            eTemaTitulacionPosgradoMatricula.notificar_integrantes_a_firmar_acta_sustentacion(request)
                                            log(u"Firmo ACTA_SUSTENTACION_NOTA por descarga", request, 'edit')
                                        else:
                                            return JsonResponse(
                                                {"result": "bad", "mensaje": u"Error, Solo archivos PDF"})

                        else:
                            raise NameError(f"{mensaje}")
                    messages.success(request, "Firmado correctamente.")
                    return JsonResponse({"result": "ok"})
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", "mensaje": u"%s" % ex})

        return JsonResponse({"result": "bad", "mensaje": u"Solicitud Incorrecta."})

    else:
        if 'action' in request.GET:
            action = request.GET['action']
            if action == 'acompanamiento':
                try:
                    data['title'] = u"Detalle Tutorías"
                    data['perid'] = int(encrypt(request.GET['perid']))
                    data['grupo'] = grupo = TemaTitulacionPosgradoMatricula.objects.get(
                        pk=int(encrypt(request.GET['id'])), status=True)
                    data['detalles'] = grupo.tutoriastematitulacionposgradoprofesor_set.filter(status=True).order_by(
                        'id')
                    c = ConfiguracionTitulacionPosgrado.objects.get(pk=int(encrypt(request.GET['perid'])))
                    bandera = False
                    if hoy >= c.fechainiciotutoria and hoy <= c.fechafintutoria:
                        bandera = True
                    data['bandera'] = bandera
                    return render(request, "pro_tutoriaposgrado/acompanamiento.html", data)
                except Exception as ex:
                    pass

            if action == 'calificarrubricasustentacion':
                try:
                    data['title'] = u"Detalle de Calificación"
                    data['detalle'] = complexivodetallegrupo = TemaTitulacionPosgradoMatricula.objects.get(
                        pk=int(encrypt(request.GET['id'])))

                    if complexivodetallegrupo.tribunaltematitulacionposgradomatricula_set.filter(status=True)[
                        0].presidentepropuesta == profesor:
                        juradocalificador = 1
                    if complexivodetallegrupo.tribunaltematitulacionposgradomatricula_set.filter(status=True)[
                        0].secretariopropuesta == profesor:
                        juradocalificador = 2
                    if complexivodetallegrupo.tribunaltematitulacionposgradomatricula_set.filter(status=True)[
                        0].delegadopropuesta == profesor:
                        juradocalificador = 3
                    data['grupo'] = grupo = \
                    complexivodetallegrupo.tribunaltematitulacionposgradomatricula_set.filter(status=True)[0]

                    if not CalificacionTitulacionPosgrado.objects.filter(
                            tematitulacionposgradomatricula=complexivodetallegrupo, juradocalificador=profesor,
                            status=True):
                        calificacionrubrica = CalificacionTitulacionPosgrado(
                            tematitulacionposgradomatricula=complexivodetallegrupo,
                            observacion='',
                            juradocalificador=profesor,
                            tipojuradocalificador=juradocalificador,
                            puntajerubricas=0)
                        calificacionrubrica.save(request)

                        rubricatitulacion = DetalleRubricaTitulacionPosgrado.objects.filter(
                            rubricatitulacionposgrado=complexivodetallegrupo.rubrica, status=True).order_by('id')
                        modelorubricatitulacion = ModeloRubricaTitulacionPosgrado.objects.filter(
                            rubrica=complexivodetallegrupo.rubrica, status=True).order_by('id')
                        complexivodetallegrupo.rubrica = complexivodetallegrupo.rubrica
                        complexivodetallegrupo.save()
                        for rubmodelo in modelorubricatitulacion:
                            calificacionmodelorubrica = CalificacionDetalleModeloRubricaTitulacionPosgrado(
                                calificacionrubrica=calificacionrubrica,
                                modelorubrica=rubmodelo,
                                puntaje=0)
                            calificacionmodelorubrica.save(request)
                        for rub in rubricatitulacion:
                            calificaciondetallerubrica = CalificacionDetalleRubricaTitulacionPosgrado(
                                calificacionrubrica=calificacionrubrica,
                                detallerubricatitulacionposgrado=rub,
                                puntaje=0)
                            calificaciondetallerubrica.save(request)

                    data[
                        'calificacionrubricatitulacion'] = calificacionrubricatitulacion = CalificacionTitulacionPosgrado.objects.get(
                        tematitulacionposgradomatricula=complexivodetallegrupo, juradocalificador=profesor, status=True)
                    data[
                        'calificaciondetallerubricatitulacion'] = calificacionrubricatitulacion.calificaciondetallerubricatitulacionposgrado_set.filter(
                        status=True).order_by('detallerubricatitulacionposgrado__modelorubrica__orden',
                                              'detallerubricatitulacionposgrado__orden')
                    data[
                        'calificaciondetallemodelorubricatitulacion'] = calificacionrubricatitulacion.calificaciondetallemodelorubricatitulacionposgrado_set.filter(
                        status=True).order_by('modelorubrica__orden')
                    data['ponderacionesrubrica'] = RubricaTitulacionCabPonderacionPosgrado.objects.filter(
                        rubrica=calificacionrubricatitulacion.tematitulacionposgradomatricula.rubrica,
                        status=True).order_by('orden')

                    return render(request, 'pro_tutoriaposgrado/calificarrubricasustentacion.html', data)
                except Exception as ex:
                    transaction.set_rollback(True)
                    pass

            if action == 'calificardefensaoral':
                try:
                    data['title'] = u"Detalle de Calificación"
                    c = ConfiguracionTitulacionPosgrado.objects.get(pk=int(encrypt(request.GET['perid'])))
                    data['detalle'] = complexivodetallegrupo = TemaTitulacionPosgradoMatricula.objects.get(
                        pk=int(encrypt(request.GET['id'])))

                    if \
                    complexivodetallegrupo.cabeceratitulacionposgrado.tribunaltematitulacionposgradomatricula_set.filter(
                            status=True)[0].presidentepropuesta == profesor:
                        juradocalificador = 1
                    if \
                    complexivodetallegrupo.cabeceratitulacionposgrado.tribunaltematitulacionposgradomatricula_set.filter(
                            status=True)[0].secretariopropuesta == profesor:
                        juradocalificador = 2
                    if \
                    complexivodetallegrupo.cabeceratitulacionposgrado.tribunaltematitulacionposgradomatricula_set.filter(
                            status=True)[0].delegadopropuesta == profesor:
                        juradocalificador = 3
                    data['grupo'] = grupo = \
                    complexivodetallegrupo.cabeceratitulacionposgrado.tribunaltematitulacionposgradomatricula_set.filter(
                        status=True)[0]

                    if not CalificacionTitulacionPosgrado.objects.filter(
                            tematitulacionposgradomatricula=complexivodetallegrupo, juradocalificador=profesor,
                            status=True):
                        calificacionrubrica = CalificacionTitulacionPosgrado(
                            tematitulacionposgradomatricula=complexivodetallegrupo,
                            observacion='',
                            juradocalificador=profesor,
                            tipojuradocalificador=juradocalificador,
                            puntajerubricas=0)
                        calificacionrubrica.save(request)

                        rubricatitulacion = DetalleRubricaTitulacionPosgrado.objects.filter(
                            rubricatitulacionposgrado=complexivodetallegrupo.rubrica, status=True).order_by('id')
                        modelorubricatitulacion = ModeloRubricaTitulacionPosgrado.objects.filter(
                            rubrica=complexivodetallegrupo.rubrica, status=True).order_by('id')
                        complexivodetallegrupo.rubrica = complexivodetallegrupo.rubrica
                        complexivodetallegrupo.save()
                        for rubmodelo in modelorubricatitulacion:
                            calificacionmodelorubrica = CalificacionDetalleModeloRubricaTitulacionPosgrado(
                                calificacionrubrica=calificacionrubrica,
                                modelorubrica=rubmodelo,
                                puntaje=0)
                            calificacionmodelorubrica.save(request)
                        for rub in rubricatitulacion:
                            calificaciondetallerubrica = CalificacionDetalleRubricaTitulacionPosgrado(
                                calificacionrubrica=calificacionrubrica,
                                detallerubricatitulacionposgrado=rub,
                                puntaje=0)
                            calificaciondetallerubrica.save(request)

                    data[
                        'calificacionrubricatitulacion'] = calificacionrubricatitulacion = CalificacionTitulacionPosgrado.objects.get(
                        tematitulacionposgradomatricula=complexivodetallegrupo, juradocalificador=profesor, status=True)
                    data[
                        'calificaciondetallerubricatitulacion'] = calificacionrubricatitulacion.calificaciondetallerubricatitulacionposgrado_set.filter(
                        status=True).order_by('detallerubricatitulacionposgrado__modelorubrica__orden',
                                              'detallerubricatitulacionposgrado__orden')
                    data[
                        'calificaciondetallemodelorubricatitulacion'] = calificacionrubricatitulacion.calificaciondetallemodelorubricatitulacionposgrado_set.filter(
                        status=True).order_by('modelorubrica__orden')
                    data['ponderacionesrubrica'] = RubricaTitulacionCabPonderacionPosgrado.objects.filter(
                        rubrica=calificacionrubricatitulacion.tematitulacionposgradomatricula.rubrica,
                        status=True).order_by('orden')

                    return render(request, 'pro_tutoriaposgrado/calificarrubricasustentacionpareja.html', data)
                except Exception as ex:
                    transaction.set_rollback(True)
                    pass

            if action == 'calificartrabajotitulacion':
                # ESTA FUNCION SIRVE PARA CALIFICAR LA RUBRICA SOLO DE TRABAJO DE TITULACION EN PAREJA ES DECIR LA MISMA NOTA PARA LOS DOS INTEGRANTES
                try:
                    data['title'] = u"Detalle de Calificación"
                    c = ConfiguracionTitulacionPosgrado.objects.get(pk=int(encrypt(request.GET['perid'])))
                    data['detalle'] = complexivodetallegrupo = TemaTitulacionPosgradoMatriculaCabecera.objects.get(
                        pk=int(encrypt(request.GET['id'])))

                    if complexivodetallegrupo.tribunaltematitulacionposgradomatricula_set.filter(status=True)[
                        0].presidentepropuesta == profesor:
                        juradocalificador = 1
                    if complexivodetallegrupo.tribunaltematitulacionposgradomatricula_set.filter(status=True)[
                        0].secretariopropuesta == profesor:
                        juradocalificador = 2
                    if complexivodetallegrupo.tribunaltematitulacionposgradomatricula_set.filter(status=True)[
                        0].delegadopropuesta == profesor:
                        juradocalificador = 3
                    data['grupo'] = grupo = \
                    complexivodetallegrupo.tribunaltematitulacionposgradomatricula_set.filter(status=True)[0]
                    # Se obtiene al primer integrante del grupo para posteriormente presentar y guardar lo mismo al otro participante
                    data['primer_integrante'] = primer_integrante = complexivodetallegrupo.obtener_parejas()[0]
                    # se crean las rubricas para calificacion individual para los integrantes del grupo
                    for participante in complexivodetallegrupo.obtener_parejas():
                        if not CalificacionTitulacionPosgrado.objects.filter(
                                tematitulacionposgradomatricula=participante, juradocalificador=profesor, status=True):
                            calificacionrubrica = CalificacionTitulacionPosgrado(
                                tematitulacionposgradomatricula=participante,
                                observacion='',
                                juradocalificador=profesor,
                                tipojuradocalificador=juradocalificador,
                                puntajerubricas=0)
                            calificacionrubrica.save(request)

                            rubricatitulacion = DetalleRubricaTitulacionPosgrado.objects.filter(
                                rubricatitulacionposgrado=participante.rubrica, status=True).order_by('id')
                            modelorubricatitulacion = ModeloRubricaTitulacionPosgrado.objects.filter(
                                rubrica=participante.rubrica, status=True).order_by('id')
                            participante.rubrica = participante.rubrica
                            participante.save()
                            for rubmodelo in modelorubricatitulacion:
                                calificacionmodelorubrica = CalificacionDetalleModeloRubricaTitulacionPosgrado(
                                    calificacionrubrica=calificacionrubrica,
                                    modelorubrica=rubmodelo,
                                    puntaje=0)
                                calificacionmodelorubrica.save(request)
                            for rub in rubricatitulacion:
                                calificaciondetallerubrica = CalificacionDetalleRubricaTitulacionPosgrado(
                                    calificacionrubrica=calificacionrubrica,
                                    detallerubricatitulacionposgrado=rub,
                                    puntaje=0)
                                calificaciondetallerubrica.save(request)
                    # presento la rubrica del primer integrante para posterior guardar en los dos participantes
                    data[
                        'calificacionrubricatitulacion'] = calificacionrubricatitulacion = CalificacionTitulacionPosgrado.objects.get(
                        tematitulacionposgradomatricula=complexivodetallegrupo.obtener_parejas()[0],
                        juradocalificador=profesor, status=True)
                    data[
                        'calificaciondetallerubricatitulacion'] = calificacionrubricatitulacion.calificaciondetallerubricatitulacionposgrado_set.filter(
                        status=True).order_by('detallerubricatitulacionposgrado__modelorubrica__orden',
                                              'detallerubricatitulacionposgrado__orden')
                    data[
                        'calificaciondetallemodelorubricatitulacion'] = calificacionrubricatitulacion.calificaciondetallemodelorubricatitulacionposgrado_set.filter(
                        status=True).order_by('modelorubrica__orden')
                    data['ponderacionesrubrica'] = RubricaTitulacionCabPonderacionPosgrado.objects.filter(
                        rubrica=primer_integrante.rubrica, status=True).order_by('orden')

                    return render(request, 'pro_tutoriaposgrado/calificartrabajotitulacionpos.html', data)
                except Exception as ex:
                    transaction.set_rollback(True)
                    pass

            if action == 'addtutoriaporetapa':
                try:
                    programa_etapa_id = int(encrypt(request.GET['programa_etapa_id']))
                    pareja = json.loads(request.GET['pareja'])
                    if pareja == True:
                        grupo = TemaTitulacionPosgradoMatriculaCabecera.objects.get(pk=int(encrypt(request.GET['id'])))

                    else:
                        grupo = TemaTitulacionPosgradoMatricula.objects.get(pk=int(encrypt(request.GET['id'])))
                    form = TutoriaProfesorPosgradoForm()
                    form.addtutoriaporetapa(programa_etapa_id,grupo.convocatoria_id,grupo.mecanismotitulacionposgrado_id)
                    data['perid'] = int(encrypt(request.GET['perid']))


                    data['pareja'] = request.GET['pareja']
                    data['form'] = form
                    data['grupo'] = grupo
                    data['action'] = 'addtutoria'
                    template = get_template("pro_tutoriaposgrado/modal/formaddtutoria.html")
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    pass

            if action == 'edittutoria':
                try:
                    data['detalle'] = detalle = TutoriasTemaTitulacionPosgradoProfesor.objects.get( pk=int(encrypt(request.GET['id'])))
                    if json.loads(request.GET['pareja']) == True:
                        data['grupo'] = grupo =  detalle.tematitulacionposgradomatriculacabecera
                    else:
                        data['grupo'] = grupo = detalle.tematitulacionposgradomatricula

                    data['perid'] = int(encrypt(request.GET['perid']))
                    data['action'] = 'edittutoria'
                    data['pareja'] = request.GET['pareja']
                    form = TutoriaProfesorPosgradoForm(initial={
                        'fecharegistro': detalle.fecharegistro,
                        'horainicio': detalle.horainicio.strftime('%H:%M'),
                        'horas': detalle.horas,
                        'horafin': detalle.horafin.strftime('%H:%M') if detalle.horafin else None,
                        'titulo': detalle.observacion,
                        'detalle': detalle.detalle,
                        'modalidad': detalle.modalidad,
                        'link_grabacion': detalle.enlace
                    })
                    form.edittutoriaporetapa(detalle.programaetapatutoria_id,detalle.programaetapatutoria.convocatoria_id,grupo.mecanismotitulacionposgrado_id)
                    data['form'] = form
                    template = get_template("pro_tutoriaposgrado/modal/formaddtutoria.html")
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    pass

            if action == 'deletepareja':
                try:
                    data['title'] = u"Eliminar Registro Tutoría"
                    data['detalle'] = detalle = TutoriasTemaTitulacionPosgradoProfesor.objects.get(pk=request.GET['id'])
                    data['grupo'] = detalle.tematitulacionposgradomatriculacabecera
                    data['perid'] = int(encrypt(request.GET['perid']))
                    return render(request, 'pro_tutoriaposgrado/deleteacompanamientopareja.html', data)
                except Exception as ex:
                    pass

            if action == 'sustentacion':
                try:
                    data['title'] = u"Calificar Defensa"
                    data['profesor'] = profesor
                    data['grupo'] = grupo = TribunalTemaTitulacionPosgradoMatricula.objects.get(
                        pk=int(encrypt(request.GET['id'])),
                        tematitulacionposgradomatricula_id=int(encrypt(request.GET['idt'])), status=True)
                    puedegeneraracta = False
                    data['puedegeneraracta'] = puedegeneraracta
                    estudiante = []
                    cronogramaactivo = True
                    data['puedecalificar'] = False
                    estudiante.append(
                        [grupo.tematitulacionposgradomatricula.matricula.inscripcion.persona.nombre_completo_inverso()])
                    data['faltamalla'] = estudiante
                    data['cronogramaactivo'] = cronogramaactivo
                    data['integrante'] = integrantegrupo = grupo.tematitulacionposgradomatricula
                    carrera = integrantegrupo.matricula.inscripcion.carrera
                    periodo = integrantegrupo.matricula.nivel.periodo
                    c = ConfiguracionTitulacionPosgrado.objects.filter(carrera=carrera, periodo=periodo, status=True)[0]
                    data['perid'] = c.id
                    puedecerraracta = True
                    data['puedecerraracta'] = puedecerraracta
                    notalfinalgraduado = 0
                    if grupo.tematitulacionposgradomatricula.actacerrada:
                        notalfinalgraduado = null_to_numeric(((integrantegrupo.calificacion + integrantegrupo.matricula.inscripcion.promedio_record()) / 2),2)
                    data['notalfinalgraduado'] = notalfinalgraduado
                    archivocorrecion = None
                    if TemaTitulacionPosArchivoFinal.objects.filter(
                            tematitulacionposgradomatricula_id=int(encrypt(request.GET['idt']))):
                        archivocorrecion = TemaTitulacionPosArchivoFinal.objects.filter(
                            tematitulacionposgradomatricula_id=int(encrypt(request.GET['idt'])))[0]
                    data['archivocorrecion'] = archivocorrecion

                    return render(request, 'pro_tutoriaposgrado/calificatribunal.html', data)
                except Exception as ex:
                    pass

            if action == 'revisiontrabajotitulacionportribunal':
                try:
                    data['title'] = u"Revisión del trabajo de titulación"
                    data['profesor'] = profesor
                    tribunal = TribunalTemaTitulacionPosgradoMatricula.objects.get(pk=int(encrypt(request.GET['id'])))
                    tiene_rubrica = True
                    pareja = 1
                    archivocorrecion = None
                    if tribunal.tematitulacionposgradomatriculacabecera:
                        tema = tribunal.tematitulacionposgradomatriculacabecera
                        pareja = 1
                        if not tema.rubrica_pareja(): tiene_rubrica=False
                        if TemaTitulacionPosArchivoFinal.objects.filter(tematitulacionposgradomatriculacabecera=tema):
                            archivocorrecion = TemaTitulacionPosArchivoFinal.objects.filter(tematitulacionposgradomatriculacabecera=tema)[0]
                    else:
                        pareja = 0
                        tema = tribunal.tematitulacionposgradomatricula
                        if not tema.rubrica: tiene_rubrica = False
                        if TemaTitulacionPosArchivoFinal.objects.filter(tematitulacionposgradomatricula=tema):
                            archivocorrecion = TemaTitulacionPosArchivoFinal.objects.filter(tematitulacionposgradomatricula=tema)[0]

                    data['archivocorrecion'] = archivocorrecion
                    data['tiene_rubrica']=tiene_rubrica

                    revisiones = Revision.objects.filter(status=True, tribunal =tribunal)
                    #filtro  los informes que estan configurados para el programa y mecanismo
                    configuracion_programa_mecanismo_informe = ConfiguraInformePrograma.objects.filter(status=True, mecanismotitulacionposgrado = tema.mecanismotitulacionposgrado,programa= tema.convocatoria.carrera, estado = True)
                    if configuracion_programa_mecanismo_informe.exists():
                        informe_configurado = configuracion_programa_mecanismo_informe.first()
                        informe_activo = informe_configurado.informe
                    else:
                        if not revisiones.exists():
                            if str(tema.mecanismotitulacionposgrado_id) in variable_valor('ID_MECANISMO_ARTICULOS'):
                                return HttpResponseRedirect(f"/pro_tutoriaposgrado?action=revisiontrabajotitulacionportribunalarticulos&id={tribunal.pk}")

                            return HttpResponseRedirect(f"/pro_tutoriaposgrado?info=No existe un informe configurado para el programa: {tema.convocatoria.carrera} y mecanismo: {tema.mecanismotitulacionposgrado}.")
                    #crear primera revision que es la que el tutor aprueba y el tribunal tiene que revisar
                    if not revisiones.exists():
                        with transaction.atomic():
                            try:
                                informe = informe_activo
                                revision = Revision(
                                    tribunal=tribunal
                                )
                                revision.save(request)

                                archivo_para_revision = None
                                if revision.tribunal.tematitulacionposgradomatriculacabecera:
                                    revision_por_tutor = RevisionTutoriasTemaTitulacionPosgradoProfesor.objects.filter(
                                        status=True, estado=2,
                                        tematitulacionposgradomatriculacabecera=revision.tribunal.tematitulacionposgradomatriculacabecera)
                                    if revision_por_tutor.exists():
                                        if str(tema.mecanismotitulacionposgrado_id) in variable_valor('ID_MECANISMO_ARTICULOS'):
                                            archivo_para_revision = revision_por_tutor[0].get_borrador_articulo().archivo
                                        else:
                                            archivo_para_revision = revision_por_tutor[0].get_propuesta().archivo
                                else:
                                    revision_por_tutor = RevisionTutoriasTemaTitulacionPosgradoProfesor.objects.filter(
                                        status=True, estado=2,
                                        tematitulacionposgradomatricula=revision.tribunal.tematitulacionposgradomatricula)
                                    if revision_por_tutor.exists():
                                        if str(tema.mecanismotitulacionposgrado_id) in variable_valor('ID_MECANISMO_ARTICULOS'):
                                            archivo_para_revision = revision_por_tutor[0].get_borrador_articulo().archivo
                                        else:
                                            archivo_para_revision = revision_por_tutor[0].get_propuesta().archivo

                                revision.archivo = archivo_para_revision
                                revision.save(request)

                                revision.crear_estructura_informe(informe, request)
                            except Exception as ex:
                                transaction.set_rollback(True)
                                raise NameError(f'ha ocurrido un error al generar la estructura de la revisión')
                                pass

                            revisiones = Revision.objects.filter(status=True, tribunal=tribunal)

                    #fin primera revision
                    debe_subir_correccion = True if revisiones.filter(estado = 3).exists() else False

                    if revisiones.filter(estado__in = [2,3]).exists():
                        revision_aceptada = revisiones.filter(estado__in = [2,3])[0]
                    else:
                        revision_aceptada = revisiones.filter(estado__in = [2,3]).exists()

                    disponible_revisar_por_cronograma = True

                    if not  datetime.now().date() <= tribunal.fechafincalificaciontrabajotitulacion and datetime.now().date() >= tribunal.fechainiciocalificaciontrabajotitulacion:
                        disponible_revisar_por_cronograma = False

                    if datetime.now().date() == tribunal.fechadefensa:
                        disponible_revisar_por_cronograma = True

                    data['debe_subir_correccion'] = debe_subir_correccion
                    data['revision_aceptada'] = revision_aceptada
                    data['disponible_revisar_por_cronograma'] = disponible_revisar_por_cronograma
                    data['pareja'] = pareja
                    data['perid'] = tema.convocatoria.id
                    data['tribunal'] = tribunal
                    data['tema'] = tema
                    data['revisiones'] = revisiones

                    return render(request, 'pro_tutoriaposgrado/revisiontrabajotitulacionportribunal.html', data)
                except Exception as ex:
                    pass

            if action == 'revisiontrabajotitulacionportribunalarticulos':
                try:
                    data['title'] = u"Revisión del trabajo de titulación"
                    data['profesor'] = profesor
                    tribunal = TribunalTemaTitulacionPosgradoMatricula.objects.get(pk=int(request.GET['id']))
                    tiene_rubrica = True
                    mirubrica = None
                    pareja = 1
                    if tribunal.tematitulacionposgradomatriculacabecera:
                        tema = tribunal.tematitulacionposgradomatriculacabecera
                        pareja = 1
                        if not tema.rubrica_pareja(): tiene_rubrica=False
                        if tiene_rubrica:
                            mirubrica = tema.rubrica_pareja()
                            if mirubrica:
                                data['detalle'] = complexivodetallegrupo = tema
                                presidentepropuesta = complexivodetallegrupo.tribunaltematitulacionposgradomatricula_set.filter(status=True)[0].presidentepropuesta
                                secretariopropuesta = complexivodetallegrupo.tribunaltematitulacionposgradomatricula_set.filter(status=True)[0].secretariopropuesta
                                delegadopropuesta = complexivodetallegrupo.tribunaltematitulacionposgradomatricula_set.filter(status=True)[0].delegadopropuesta
                                data['grupo'] = grupo =complexivodetallegrupo.tribunaltematitulacionposgradomatricula_set.filter(status=True)[0]
                                # Se obtiene al primer integrante del grupo para posteriormente presentar y guardar lo mismo al otro participante
                                data['primer_integrante'] = primer_integrante =  complexivodetallegrupo.obtener_parejas()[0]
                                # se crean las rubricas para calificacion individual para los integrantes del grupo
                                for participante in complexivodetallegrupo.obtener_parejas():
                                    if not CalificacionTitulacionPosgrado.objects.filter(tematitulacionposgradomatricula=participante, juradocalificador=presidentepropuesta, status=True):
                                        calificacionrubrica = CalificacionTitulacionPosgrado(
                                            tematitulacionposgradomatricula=participante,
                                            observacion='',
                                            juradocalificador=presidentepropuesta,
                                            tipojuradocalificador=1,
                                            puntajerubricas=0)
                                        calificacionrubrica.save(request)

                                        rubricatitulacion = DetalleRubricaTitulacionPosgrado.objects.filter(
                                            rubricatitulacionposgrado=participante.rubrica, status=True).order_by('id')
                                        modelorubricatitulacion = ModeloRubricaTitulacionPosgrado.objects.filter(
                                            rubrica=participante.rubrica, status=True).order_by('id')
                                        participante.rubrica = participante.rubrica
                                        participante.save()
                                        for rubmodelo in modelorubricatitulacion:
                                            calificacionmodelorubrica = CalificacionDetalleModeloRubricaTitulacionPosgrado(
                                                calificacionrubrica=calificacionrubrica,
                                                modelorubrica=rubmodelo,
                                                puntaje=0)
                                            calificacionmodelorubrica.save(request)
                                        for rub in rubricatitulacion:
                                            calificaciondetallerubrica = CalificacionDetalleRubricaTitulacionPosgrado(
                                                calificacionrubrica=calificacionrubrica,
                                                detallerubricatitulacionposgrado=rub,
                                                puntaje=0)
                                            calificaciondetallerubrica.save(request)
                                    if not CalificacionTitulacionPosgrado.objects.filter(tematitulacionposgradomatricula=participante, juradocalificador=secretariopropuesta, status=True):
                                        calificacionrubrica = CalificacionTitulacionPosgrado(
                                            tematitulacionposgradomatricula=participante,
                                            observacion='',
                                            juradocalificador=secretariopropuesta,
                                            tipojuradocalificador=2,
                                            puntajerubricas=0)
                                        calificacionrubrica.save(request)

                                        rubricatitulacion = DetalleRubricaTitulacionPosgrado.objects.filter(
                                            rubricatitulacionposgrado=participante.rubrica, status=True).order_by('id')
                                        modelorubricatitulacion = ModeloRubricaTitulacionPosgrado.objects.filter(
                                            rubrica=participante.rubrica, status=True).order_by('id')
                                        participante.rubrica = participante.rubrica
                                        participante.save()
                                        for rubmodelo in modelorubricatitulacion:
                                            calificacionmodelorubrica = CalificacionDetalleModeloRubricaTitulacionPosgrado(
                                                calificacionrubrica=calificacionrubrica,
                                                modelorubrica=rubmodelo,
                                                puntaje=0)
                                            calificacionmodelorubrica.save(request)
                                        for rub in rubricatitulacion:
                                            calificaciondetallerubrica = CalificacionDetalleRubricaTitulacionPosgrado(
                                                calificacionrubrica=calificacionrubrica,
                                                detallerubricatitulacionposgrado=rub,
                                                puntaje=0)
                                            calificaciondetallerubrica.save(request)
                                    if not CalificacionTitulacionPosgrado.objects.filter(tematitulacionposgradomatricula=participante,juradocalificador=delegadopropuesta, status=True):
                                        calificacionrubrica = CalificacionTitulacionPosgrado(
                                            tematitulacionposgradomatricula=participante,
                                            observacion='',
                                            juradocalificador=delegadopropuesta,
                                            tipojuradocalificador=3,
                                            puntajerubricas=0)
                                        calificacionrubrica.save(request)

                                        rubricatitulacion = DetalleRubricaTitulacionPosgrado.objects.filter(
                                            rubricatitulacionposgrado=participante.rubrica, status=True).order_by('id')
                                        modelorubricatitulacion = ModeloRubricaTitulacionPosgrado.objects.filter(
                                            rubrica=participante.rubrica, status=True).order_by('id')
                                        participante.rubrica = participante.rubrica
                                        participante.save()
                                        for rubmodelo in modelorubricatitulacion:
                                            calificacionmodelorubrica = CalificacionDetalleModeloRubricaTitulacionPosgrado(
                                                calificacionrubrica=calificacionrubrica,
                                                modelorubrica=rubmodelo,
                                                puntaje=0)
                                            calificacionmodelorubrica.save(request)
                                        for rub in rubricatitulacion:
                                            calificaciondetallerubrica = CalificacionDetalleRubricaTitulacionPosgrado(
                                                calificacionrubrica=calificacionrubrica,
                                                detallerubricatitulacionposgrado=rub,
                                                puntaje=0)
                                            calificaciondetallerubrica.save(request)

                                if profesor == presidentepropuesta:
                                    # presento la rubrica del primer integrante para posterior guardar en los dos participantes
                                    data['calificacionrubricatitulacion'] = calificacionrubricatitulacion = CalificacionTitulacionPosgrado.objects.get(tematitulacionposgradomatricula=complexivodetallegrupo.obtener_parejas()[0],juradocalificador=presidentepropuesta, status=True)
                                    data['calificaciondetallerubricatitulacion'] = calificacionrubricatitulacion.calificaciondetallerubricatitulacionposgrado_set.filter(status=True,detallerubricatitulacionposgrado__modelorubrica__orden= 1).order_by('detallerubricatitulacionposgrado__modelorubrica__orden', 'detallerubricatitulacionposgrado__orden')
                                    data[ 'calificaciondetallemodelorubricatitulacion'] = calificacionrubricatitulacion.calificaciondetallemodelorubricatitulacionposgrado_set.filter(status=True).order_by('modelorubrica__orden')

                                if profesor == secretariopropuesta:
                                    # presento la rubrica del primer integrante para posterior guardar en los dos participantes
                                    data['calificacionrubricatitulacion'] = calificacionrubricatitulacion = CalificacionTitulacionPosgrado.objects.get(tematitulacionposgradomatricula=complexivodetallegrupo.obtener_parejas()[0],juradocalificador=secretariopropuesta, status=True)
                                    data['calificaciondetallerubricatitulacion'] = calificacionrubricatitulacion.calificaciondetallerubricatitulacionposgrado_set.filter(status=True,detallerubricatitulacionposgrado__modelorubrica__orden= 1).order_by('detallerubricatitulacionposgrado__modelorubrica__orden', 'detallerubricatitulacionposgrado__orden')
                                    data[ 'calificaciondetallemodelorubricatitulacion'] = calificacionrubricatitulacion.calificaciondetallemodelorubricatitulacionposgrado_set.filter(status=True).order_by('modelorubrica__orden')

                                if profesor == delegadopropuesta:
                                    # presento la rubrica del primer integrante para posterior guardar en los dos participantes
                                    data['calificacionrubricatitulacion'] = calificacionrubricatitulacion = CalificacionTitulacionPosgrado.objects.get(tematitulacionposgradomatricula=complexivodetallegrupo.obtener_parejas()[0],juradocalificador=delegadopropuesta, status=True)
                                    data['calificaciondetallerubricatitulacion'] = calificacionrubricatitulacion.calificaciondetallerubricatitulacionposgrado_set.filter(status=True,detallerubricatitulacionposgrado__modelorubrica__orden= 1).order_by('detallerubricatitulacionposgrado__modelorubrica__orden', 'detallerubricatitulacionposgrado__orden')
                                    data[ 'calificaciondetallemodelorubricatitulacion'] = calificacionrubricatitulacion.calificaciondetallemodelorubricatitulacionposgrado_set.filter(status=True).order_by('modelorubrica__orden')

                                data['presidentepropuestacalificacionrubricatitulacion'] = presidentepropuestacalificacionrubricatitulacion =CalificacionTitulacionPosgrado.objects.get(
                                    tematitulacionposgradomatricula=complexivodetallegrupo.obtener_parejas()[0],
                                    juradocalificador=presidentepropuesta, status=True)

                                data['secretariopropuestacalificacionrubricatitulacion'] = secretariopropuestacalificacionrubricatitulacion =  CalificacionTitulacionPosgrado.objects.get(
                                    tematitulacionposgradomatricula=complexivodetallegrupo.obtener_parejas()[0],
                                    juradocalificador=secretariopropuesta, status=True)

                                data['delegadopropuestapresidentepropuestacalificacionrubricatitulacion'] =  delegadopropuestapresidentepropuestacalificacionrubricatitulacion = CalificacionTitulacionPosgrado.objects.get(
                                    tematitulacionposgradomatricula=complexivodetallegrupo.obtener_parejas()[0],
                                    juradocalificador=delegadopropuesta, status=True)
                    else:
                        pareja = 0
                        tema = tribunal.tematitulacionposgradomatricula
                        if not tema.rubrica: tiene_rubrica = False
                        if tiene_rubrica:
                            mirubrica = tema.rubrica
                            if mirubrica:
                                data['detalle'] = complexivodetallegrupo = tema

                                presidentepropuesta = complexivodetallegrupo.tribunaltematitulacionposgradomatricula_set.filter(status=True)[0].presidentepropuesta
                                secretariopropuesta =  complexivodetallegrupo.tribunaltematitulacionposgradomatricula_set.filter(status=True)[0].secretariopropuesta
                                delegadopropuesta = complexivodetallegrupo.tribunaltematitulacionposgradomatricula_set.filter(status=True)[0].delegadopropuesta
                                data['grupo'] = grupo =  complexivodetallegrupo.tribunaltematitulacionposgradomatricula_set.filter(status=True)[0]

                                if not CalificacionTitulacionPosgrado.objects.filter(tematitulacionposgradomatricula=complexivodetallegrupo, juradocalificador=presidentepropuesta, status=True):
                                    calificacionrubrica = CalificacionTitulacionPosgrado(
                                        tematitulacionposgradomatricula=complexivodetallegrupo,
                                        observacion='',
                                        juradocalificador=presidentepropuesta,
                                        tipojuradocalificador=1,
                                        puntajerubricas=0)
                                    calificacionrubrica.save(request)

                                    rubricatitulacion = DetalleRubricaTitulacionPosgrado.objects.filter( rubricatitulacionposgrado=complexivodetallegrupo.rubrica, status=True).order_by('id')
                                    modelorubricatitulacion = ModeloRubricaTitulacionPosgrado.objects.filter( rubrica=complexivodetallegrupo.rubrica, status=True).order_by('id')
                                    complexivodetallegrupo.rubrica = complexivodetallegrupo.rubrica
                                    complexivodetallegrupo.save()
                                    for rubmodelo in modelorubricatitulacion:
                                        calificacionmodelorubrica = CalificacionDetalleModeloRubricaTitulacionPosgrado(
                                            calificacionrubrica=calificacionrubrica,
                                            modelorubrica=rubmodelo,
                                            puntaje=0)
                                        calificacionmodelorubrica.save(request)
                                    for rub in rubricatitulacion:
                                        calificaciondetallerubrica = CalificacionDetalleRubricaTitulacionPosgrado(
                                            calificacionrubrica=calificacionrubrica,
                                            detallerubricatitulacionposgrado=rub,
                                            puntaje=0)
                                        calificaciondetallerubrica.save(request)
                                if not CalificacionTitulacionPosgrado.objects.filter(tematitulacionposgradomatricula=complexivodetallegrupo, juradocalificador=secretariopropuesta, status=True):
                                    calificacionrubrica = CalificacionTitulacionPosgrado(
                                        tematitulacionposgradomatricula=complexivodetallegrupo,
                                        observacion='',
                                        juradocalificador=secretariopropuesta,
                                        tipojuradocalificador=2,
                                        puntajerubricas=0)
                                    calificacionrubrica.save(request)
                                    rubricatitulacion = DetalleRubricaTitulacionPosgrado.objects.filter(
                                        rubricatitulacionposgrado=complexivodetallegrupo.rubrica, status=True).order_by(
                                        'id')
                                    modelorubricatitulacion = ModeloRubricaTitulacionPosgrado.objects.filter(
                                        rubrica=complexivodetallegrupo.rubrica, status=True).order_by('id')
                                    complexivodetallegrupo.rubrica = complexivodetallegrupo.rubrica
                                    complexivodetallegrupo.save()
                                    for rubmodelo in modelorubricatitulacion:
                                        calificacionmodelorubrica = CalificacionDetalleModeloRubricaTitulacionPosgrado(
                                            calificacionrubrica=calificacionrubrica,
                                            modelorubrica=rubmodelo,
                                            puntaje=0)
                                        calificacionmodelorubrica.save(request)
                                    for rub in rubricatitulacion:
                                        calificaciondetallerubrica = CalificacionDetalleRubricaTitulacionPosgrado(
                                            calificacionrubrica=calificacionrubrica,
                                            detallerubricatitulacionposgrado=rub,
                                            puntaje=0)
                                        calificaciondetallerubrica.save(request)
                                if not CalificacionTitulacionPosgrado.objects.filter(tematitulacionposgradomatricula=complexivodetallegrupo,juradocalificador=delegadopropuesta, status=True):
                                    calificacionrubrica = CalificacionTitulacionPosgrado(
                                        tematitulacionposgradomatricula=complexivodetallegrupo,
                                        observacion='',
                                        juradocalificador=delegadopropuesta,
                                        tipojuradocalificador=3,
                                        puntajerubricas=0)
                                    calificacionrubrica.save(request)
                                    rubricatitulacion = DetalleRubricaTitulacionPosgrado.objects.filter(
                                        rubricatitulacionposgrado=complexivodetallegrupo.rubrica, status=True).order_by(
                                        'id')
                                    modelorubricatitulacion = ModeloRubricaTitulacionPosgrado.objects.filter(
                                        rubrica=complexivodetallegrupo.rubrica, status=True).order_by('id')
                                    complexivodetallegrupo.rubrica = complexivodetallegrupo.rubrica
                                    complexivodetallegrupo.save()
                                    for rubmodelo in modelorubricatitulacion:
                                        calificacionmodelorubrica = CalificacionDetalleModeloRubricaTitulacionPosgrado(
                                            calificacionrubrica=calificacionrubrica,
                                            modelorubrica=rubmodelo,
                                            puntaje=0)
                                        calificacionmodelorubrica.save(request)
                                    for rub in rubricatitulacion:
                                        calificaciondetallerubrica = CalificacionDetalleRubricaTitulacionPosgrado(
                                            calificacionrubrica=calificacionrubrica,
                                            detallerubricatitulacionposgrado=rub,
                                            puntaje=0)
                                        calificaciondetallerubrica.save(request)
                                if profesor == presidentepropuesta:
                                    data['calificacionrubricatitulacion'] = calificacionrubricatitulacion = CalificacionTitulacionPosgrado.objects.get(tematitulacionposgradomatricula=complexivodetallegrupo, juradocalificador=presidentepropuesta, status=True)
                                    data['calificaciondetallerubricatitulacion'] = calificacionrubricatitulacion.calificaciondetallerubricatitulacionposgrado_set.filter(status=True,detallerubricatitulacionposgrado__modelorubrica__orden= 1).order_by('detallerubricatitulacionposgrado__modelorubrica__orden', 'detallerubricatitulacionposgrado__orden')
                                    data['calificaciondetallemodelorubricatitulacion'] = calificacionrubricatitulacion.calificaciondetallemodelorubricatitulacionposgrado_set.filter(status=True).order_by('modelorubrica__orden')

                                if profesor == secretariopropuesta:
                                    data['calificacionrubricatitulacion'] = calificacionrubricatitulacion = CalificacionTitulacionPosgrado.objects.get(tematitulacionposgradomatricula=complexivodetallegrupo, juradocalificador=secretariopropuesta, status=True)
                                    data['calificaciondetallerubricatitulacion'] = calificacionrubricatitulacion.calificaciondetallerubricatitulacionposgrado_set.filter(status=True,detallerubricatitulacionposgrado__modelorubrica__orden= 1).order_by('detallerubricatitulacionposgrado__modelorubrica__orden', 'detallerubricatitulacionposgrado__orden')
                                    data['calificaciondetallemodelorubricatitulacion'] = calificacionrubricatitulacion.calificaciondetallemodelorubricatitulacionposgrado_set.filter(status=True).order_by('modelorubrica__orden')
                                if profesor == delegadopropuesta:
                                    data['calificacionrubricatitulacion'] = calificacionrubricatitulacion = CalificacionTitulacionPosgrado.objects.get(tematitulacionposgradomatricula=complexivodetallegrupo, juradocalificador=delegadopropuesta, status=True)
                                    data['calificaciondetallerubricatitulacion'] = calificacionrubricatitulacion.calificaciondetallerubricatitulacionposgrado_set.filter(status=True,detallerubricatitulacionposgrado__modelorubrica__orden= 1).order_by('detallerubricatitulacionposgrado__modelorubrica__orden', 'detallerubricatitulacionposgrado__orden')
                                    data['calificaciondetallemodelorubricatitulacion'] = calificacionrubricatitulacion.calificaciondetallemodelorubricatitulacionposgrado_set.filter(status=True).order_by('modelorubrica__orden')

                                data['presidentepropuestacalificacionrubricatitulacion'] = presidentepropuestacalificacionrubricatitulacion = CalificacionTitulacionPosgrado.objects.get(tematitulacionposgradomatricula=complexivodetallegrupo, juradocalificador=presidentepropuesta, status=True)
                                data['secretariopropuestacalificacionrubricatitulacion'] = secretariopropuestacalificacionrubricatitulacion = CalificacionTitulacionPosgrado.objects.get(tematitulacionposgradomatricula=complexivodetallegrupo, juradocalificador=secretariopropuesta, status=True)
                                data['delegadopropuestapresidentepropuestacalificacionrubricatitulacion'] = delegadopropuestapresidentepropuestacalificacionrubricatitulacion = CalificacionTitulacionPosgrado.objects.get(tematitulacionposgradomatricula=complexivodetallegrupo, juradocalificador=delegadopropuesta, status=True)



                    data['tiene_rubrica'] = tiene_rubrica
                    data['mirubrica'] = mirubrica
                    rubrica_calificacion= None

                    documentos_articulos = tribunal.get_documentos_cargados_titulacion()




                    disponible_revisar_por_cronograma = True

                    if not  datetime.now().date() <= tribunal.fechafincalificaciontrabajotitulacion and datetime.now().date() >= tribunal.fechainiciocalificaciontrabajotitulacion:
                        disponible_revisar_por_cronograma = False

                    if datetime.now().date() == tribunal.fechadefensa:
                        disponible_revisar_por_cronograma = True

                    data['disponible_revisar_por_cronograma'] = disponible_revisar_por_cronograma
                    data['pareja'] = pareja
                    data['perid'] = tema.convocatoria.id
                    data['tribunal'] = tribunal
                    data['tema'] = tema
                    data['documentos_articulos'] = documentos_articulos
                    return render(request, 'pro_tutoriaposgrado/tribunal/revisiontrabajotitulacionportribunalarticulos.html', data)
                except Exception as ex:
                    pass

            if action == 'sustentacionpareja':
                try:
                    data['title'] = u"Calificar Defensa"
                    data['profesor'] = profesor
                    data['grupo'] = grupo = TribunalTemaTitulacionPosgradoMatricula.objects.get(
                        pk=int(encrypt(request.GET['id'])),
                        tematitulacionposgradomatriculacabecera_id=int(encrypt(request.GET['idt'])), status=True)
                    configuracion = grupo.tematitulacionposgradomatriculacabecera.convocatoria
                    data['configuracion'] = configuracion
                    archivocorrecion = None
                    if TemaTitulacionPosArchivoFinal.objects.filter(
                            tematitulacionposgradomatriculacabecera_id=int(encrypt(request.GET['idt']))):
                        archivocorrecion = TemaTitulacionPosArchivoFinal.objects.filter(
                            tematitulacionposgradomatriculacabecera_id=int(encrypt(request.GET['idt'])))[0]
                    data['archivocorrecion'] = archivocorrecion

                    return render(request, 'pro_tutoriaposgrado/calificartribunalpareja.html', data)
                except Exception as ex:
                    pass

            if action == 'archivosustentacion':
                try:
                    data['title'] = u"Detalle de Calificación"
                    data['detalle'] = d = TribunalTemaTitulacionPosgradoMatricula.objects.get(
                        pk=int(encrypt(request.GET['idg'])),
                        tematitulacionposgradomatricula_id=int(encrypt(request.GET['id'])), status=True)
                    # data['grupo']= d.grupo
                    data['form'] = ComplexivoCalificacionSustentacionForm()
                    return render(request, 'pro_tutoriaposgrado/sustentacion.html', data)
                except Exception as ex:
                    pass

            if action == 'calificarurkundtitulacionfinalposgrado':
                try:
                    data['title'] = u"Calificar popuesta de titulación"
                    propuesta = RevisionTutoriasTemaTitulacionPosgradoProfesor.objects.get(pk=int(encrypt(request.GET['id'])))
                    if json.loads(request.GET['pareja'])== True:
                        grupo = propuesta.tematitulacionposgradomatriculacabecera
                    else:
                        grupo = propuesta.tematitulacionposgradomatricula

                    form = CalificarPropuestaPosgradoForm()
                    data['form'] = form
                    data['propuesta'] = propuesta
                    data['grupo'] = grupo
                    data['pareja'] = request.GET['pareja']
                    data['action'] = 'calificarurkundtitulacionfinalposgrado'
                    data['perid'] = int(encrypt(request.GET['perid']))

                    template = get_template("pro_tutoriaposgrado/modal/formsubirurkund.html")
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    pass

            if action == 'editarurkundtitulacionfinalposgrado':
                try:
                    data['title'] = u"Editar Calificación Propuesta Tutoría"
                    propuesta = RevisionTutoriasTemaTitulacionPosgradoProfesor.objects.get(pk=int(encrypt(request.GET['id'])))
                    if json.loads(request.GET['pareja']) == True:
                        grupo = propuesta.tematitulacionposgradomatriculacabecera
                    else:
                        grupo = propuesta.tematitulacionposgradomatricula

                    data['grupo'] = grupo
                    data['propuesta'] = propuesta
                    data['perid'] = int(encrypt(request.GET['perid']))
                    data['form'] = CalificarPropuestaPosgradoForm(initial={'plagio': propuesta.porcentajeurkund,
                                                                           'observaciones': propuesta.observacion,
                                                                           'aprobar': True if propuesta.estado == 2 else False,
                                                                           'rechazar': True if propuesta.estado == 3 else False})

                    data['action'] = 'editarurkundtitulacionfinalposgrado'
                    data['pareja'] = request.GET['pareja']
                    template = get_template("pro_tutoriaposgrado/modal/formeditarurkund.html")
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    pass

            if action == 'propuesta':
                try:
                    data['title'] = u'Seguimiento de tutorias'
                    data['perid'] = int(encrypt(request.GET['perid']))
                    data['grupo'] = grupo = TemaTitulacionPosgradoMatricula.objects.get( pk=int(encrypt(request.GET['id'])))
                    data['propuestas'] = RevisionTutoriasTemaTitulacionPosgradoProfesor.objects.filter(tematitulacionposgradomatricula=grupo, status=True).order_by('id')
                    configuracion = ConfiguracionTitulacionPosgrado.objects.get(pk=grupo.convocatoria_id)
                    bandera = False
                    hoy = datetime.now().date()
                    if hoy >= configuracion.fechainiciotutoria and hoy <= configuracion.fechafintutoria:
                        bandera = True
                    data['bandera'] = bandera
                    data['cronograma'] = configuracion
                    data['detalles'] = grupo.tutoriastematitulacionposgradoprofesor_set.filter(status=True).order_by('id')
                    if variable_valor('HABILITAR_TUTORIA_POR_MECANISMO'):
                        etapas =configuracion.obtener_etapas_de_tutorias(grupo.mecanismotitulacionposgrado_id)
                    else:
                        etapas =etapas =configuracion.obtener_etapas_de_tutorias_antiguo()
                    data['configuracion_programa_etapa'] = etapas
                    return render(request, "pro_tutoriaposgrado/propuesta.html", data)
                except Exception as ex:
                    pass

            if action == 'propuestapareja':
                try:
                    data['title'] = u'Seguimiento de tutorias'
                    data['perid'] = int(encrypt(request.GET['perid']))
                    data['grupo'] = grupo = TemaTitulacionPosgradoMatriculaCabecera.objects.get(
                        pk=int(encrypt(request.GET['id'])))
                    data['propuestas'] = RevisionTutoriasTemaTitulacionPosgradoProfesor.objects.filter(
                        tematitulacionposgradomatriculacabecera=grupo, status=True).order_by('id')
                    configuracion = ConfiguracionTitulacionPosgrado.objects.get(pk=grupo.convocatoria_id)
                    bandera = False
                    hoy = datetime.now().date()
                    if hoy >= configuracion.fechainiciotutoria and hoy <= configuracion.fechafintutoria:
                        bandera = True
                    data['bandera'] = bandera
                    data['cronograma'] = configuracion
                    data['detalles'] = grupo.tutoriastematitulacionposgradoprofesor_set.filter(status=True).order_by(
                        'id')

                    if variable_valor('HABILITAR_TUTORIA_POR_MECANISMO'):
                        etapas = configuracion.obtener_etapas_de_tutorias(grupo.mecanismotitulacionposgrado_id)
                    else:
                        etapas = etapas = configuracion.obtener_etapas_de_tutorias_antiguo()
                    data['configuracion_programa_etapa'] = etapas
                    return render(request, "pro_tutoriaposgrado/propuesta_pareja.html", data)
                except Exception as ex:
                    pass

            if action == 'revisartrabajofinaltitulacion':
                try:
                    data['title'] = u'Seguimiento de tutorias'
                    data['tema'] = tema = TemaTitulacionPosgradoMatricula.objects.get(pk=request.GET['id'])
                    data['propuestas'] = RevisionTutoriasTemaTitulacionPosgradoProfesor.objects.filter(
                        tematitulacionposgradomatricula=tema, status=True).order_by('-id')
                    return render(request, "pro_tutoriaposgrado/revisartrabajofinaltitulacionposgrado.html", data)
                except Exception as ex:
                    pass

            if action == 'revisararchivoavancetutoria':
                try:
                    id = int(encrypt(request.GET['id']))
                    data['title'] = u'Revisión de avance de tutoria'

                    data['revision_tutoria'] = revision_tutoria = RevisionTutoriasTemaTitulacionPosgradoProfesor.objects.get(pk=id)
                    archivo = revision_tutoria.get_correccion()
                    if archivo:
                        form = RevisarAvanceTutoriaPosgradoForm(initial={
                            'observaciones': revision_tutoria.observacion,
                            'correccion':archivo.archivo
                        })
                    else:
                        form = RevisarAvanceTutoriaPosgradoForm(initial={
                            'observaciones': revision_tutoria.observacion
                        })

                    data['form'] = form
                    data['action'] = 'revisararchivoavancetutoria'
                    template = get_template("pro_tutoriaposgrado/modal/formrevisaravancetutoria.html")
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    pass

            if action == 'revisartrabajofinaltitulacionpareja':
                try:
                    data['title'] = u'Seguimiento de tutorias'
                    data['tema'] = tema = TemaTitulacionPosgradoMatriculaCabecera.objects.get(pk=request.GET['id'])
                    data['propuestas'] = RevisionTutoriasTemaTitulacionPosgradoProfesor.objects.filter(
                        tematitulacionposgradomatriculacabecera=tema, status=True).order_by('-id')
                    return render(request, "pro_tutoriaposgrado/revisartrabajofinaltitulacionposgradopareja.html", data)
                except Exception as ex:
                    pass

            if action == 'detalletutoriaposgrado':
                try:
                    data['tutoria'] = TutoriasTemaTitulacionPosgradoProfesor.objects.get(pk=request.GET['id'])
                    template = get_template("pro_tutoriaposgrado/modal/detalletutoriaposgrado.html")
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    pass

            if action == 'detalle_maestrante_tutoria':
                try:
                    data['detalle'] = TemaTitulacionPosgradoMatricula.objects.get(pk=request.GET['id'])
                    template = get_template("pro_tutoriaposgrado/modal/detalle_maestrante_tutoria.html")
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    pass

            if action == 'detalle_maestrante_pareja_tutoria':
                try:
                    data['detalle'] = TemaTitulacionPosgradoMatriculaCabecera.objects.get(pk=request.GET['id'])
                    template = get_template("pro_tutoriaposgrado/modal/detalle_maestrante_pareja_tutoria.html")
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    pass

            if action == 'detalle_maestrante_sustentacion':
                try:

                    data['grupo'] = tribunal = TribunalTemaTitulacionPosgradoMatricula.objects.get(pk=request.GET['id'])
                    if tribunal.tematitulacionposgradomatriculacabecera:
                        template = get_template("pro_tutoriaposgrado/modal/detalle_sustentacion_tribunal_pareja.html")
                    else:
                        template = get_template("pro_tutoriaposgrado/modal/detalle_sustentacion_tribunal.html")
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    pass

            if action == 'informe_revision_por_tribunal':
                try:
                    data['title'] = u"Informe del tribunal"
                    revision = Revision.objects.get(pk=request.GET['id'])


                    data['revision'] = revision
                    return render(request, 'pro_tutoriaposgrado/informe_tribunal.html', data)
                except Exception as ex:
                    pass

            if action == 'historial_revision_tribunal':
                try:

                    revision = Revision.objects.get(pk=request.GET['id'])
                    revisiones= revision.obtener_historial_de_revisiones()
                    data['revisiones'] = revisiones
                    template = get_template("pro_tutoriaposgrado/modal/historial_revision_tribunal.html")
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    pass

            if action =='ver_revision_tribunal':
                try:
                    id = request.GET['id']
                    if json.loads(request.GET['pareja']) == True:
                        tema = TemaTitulacionPosgradoMatriculaCabecera.objects.get(pk=id)
                    else:
                        tema = TemaTitulacionPosgradoMatricula.objects.get(pk=id)
                    tribunal = tema.obtener_tribunal() #funcion en modelo cabecera e individual -> obtener_tribunal()
                    revisiones = Revision.objects.filter(status=True,tribunal=tribunal)
                    data['revisiones'] = revisiones
                    template = get_template("pro_tutoriaposgrado/modal/detalle_revision_tribunal.html")
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    pass

            if action == 'calificar_trabajo_titulacion':
                try:
                    data['title'] = u"Calificar trabajo de titulación"
                    grupo = None

                    if int(request.GET['pareja'])==1:

                        data['detalle'] = complexivodetallegrupo = TemaTitulacionPosgradoMatriculaCabecera.objects.get(pk=int(request.GET['id']))

                        if complexivodetallegrupo.tribunaltematitulacionposgradomatricula_set.filter(status=True)[0].presidentepropuesta == profesor:
                            juradocalificador = 1
                        if complexivodetallegrupo.tribunaltematitulacionposgradomatricula_set.filter(status=True)[0].secretariopropuesta == profesor:
                            juradocalificador = 2
                        if complexivodetallegrupo.tribunaltematitulacionposgradomatricula_set.filter(status=True)[0].delegadopropuesta == profesor:
                            juradocalificador = 3
                        data['grupo'] = grupo =complexivodetallegrupo.tribunaltematitulacionposgradomatricula_set.filter(status=True)[0]
                        # Se obtiene al primer integrante del grupo para posteriormente presentar y guardar lo mismo al otro participante
                        data['primer_integrante'] = primer_integrante = complexivodetallegrupo.obtener_parejas()[0]
                        # se crean las rubricas para calificacion individual para los integrantes del grupo
                        for participante in complexivodetallegrupo.obtener_parejas():
                            if not CalificacionTitulacionPosgrado.objects.filter( tematitulacionposgradomatricula=participante, juradocalificador=profesor, status=True):
                                calificacionrubrica = CalificacionTitulacionPosgrado(
                                    tematitulacionposgradomatricula=participante,
                                    observacion='',
                                    juradocalificador=profesor,
                                    tipojuradocalificador=juradocalificador,
                                    puntajerubricas=0)
                                calificacionrubrica.save(request)

                                rubricatitulacion = DetalleRubricaTitulacionPosgrado.objects.filter(
                                    rubricatitulacionposgrado=participante.rubrica, status=True).order_by('id')
                                modelorubricatitulacion = ModeloRubricaTitulacionPosgrado.objects.filter(
                                    rubrica=participante.rubrica, status=True).order_by('id')
                                participante.rubrica = participante.rubrica
                                participante.save()
                                for rubmodelo in modelorubricatitulacion:
                                    calificacionmodelorubrica = CalificacionDetalleModeloRubricaTitulacionPosgrado(
                                        calificacionrubrica=calificacionrubrica,
                                        modelorubrica=rubmodelo,
                                        puntaje=0)
                                    calificacionmodelorubrica.save(request)
                                for rub in rubricatitulacion:
                                    calificaciondetallerubrica = CalificacionDetalleRubricaTitulacionPosgrado(
                                        calificacionrubrica=calificacionrubrica,
                                        detallerubricatitulacionposgrado=rub,
                                        puntaje=0)
                                    calificaciondetallerubrica.save(request)
                        # presento la rubrica del primer integrante para posterior guardar en los dos participantes
                        data[
                            'calificacionrubricatitulacion'] = calificacionrubricatitulacion = CalificacionTitulacionPosgrado.objects.get(tematitulacionposgradomatricula=complexivodetallegrupo.obtener_parejas()[0],juradocalificador=profesor, status=True)
                        data[
                            'calificaciondetallerubricatitulacion'] = calificacionrubricatitulacion.calificaciondetallerubricatitulacionposgrado_set.filter(status=True).order_by('detallerubricatitulacionposgrado__modelorubrica__orden','detallerubricatitulacionposgrado__orden')
                        data[
                            'calificaciondetallemodelorubricatitulacion'] = calificacionrubricatitulacion.calificaciondetallemodelorubricatitulacionposgrado_set.filter(status=True).order_by('modelorubrica__orden')
                        data['ponderacionesrubrica'] = RubricaTitulacionCabPonderacionPosgrado.objects.filter(rubrica=primer_integrante.rubrica, status=True).order_by('orden')
                        data['archivo_final_titulacion'] = grupo.obtener_archivo_titulacion_final()
                        return render(request, 'pro_tutoriaposgrado/calificartrabajotitulacionpos.html', data)
                    else:
                        data['detalle'] = complexivodetallegrupo = TemaTitulacionPosgradoMatricula.objects.get( pk=int(request.GET['id']))

                        if complexivodetallegrupo.tribunaltematitulacionposgradomatricula_set.filter(status=True)[0].presidentepropuesta == profesor:
                            juradocalificador = 1
                        if complexivodetallegrupo.tribunaltematitulacionposgradomatricula_set.filter(status=True)[0].secretariopropuesta == profesor:
                            juradocalificador = 2
                        if complexivodetallegrupo.tribunaltematitulacionposgradomatricula_set.filter(status=True)[0].delegadopropuesta == profesor:
                            juradocalificador = 3
                        data['grupo'] = grupo = complexivodetallegrupo.tribunaltematitulacionposgradomatricula_set.filter(status=True)[0]

                        if not CalificacionTitulacionPosgrado.objects.filter(tematitulacionposgradomatricula=complexivodetallegrupo, juradocalificador=profesor,status=True):
                            calificacionrubrica = CalificacionTitulacionPosgrado(
                                tematitulacionposgradomatricula=complexivodetallegrupo,
                                observacion='',
                                juradocalificador=profesor,
                                tipojuradocalificador=juradocalificador,
                                puntajerubricas=0)
                            calificacionrubrica.save(request)

                            rubricatitulacion = DetalleRubricaTitulacionPosgrado.objects.filter(rubricatitulacionposgrado=complexivodetallegrupo.rubrica, status=True).order_by('id')
                            modelorubricatitulacion = ModeloRubricaTitulacionPosgrado.objects.filter(rubrica=complexivodetallegrupo.rubrica, status=True).order_by('id')
                            complexivodetallegrupo.rubrica = complexivodetallegrupo.rubrica
                            complexivodetallegrupo.save()
                            for rubmodelo in modelorubricatitulacion:
                                calificacionmodelorubrica = CalificacionDetalleModeloRubricaTitulacionPosgrado(
                                    calificacionrubrica=calificacionrubrica,
                                    modelorubrica=rubmodelo,
                                    puntaje=0)
                                calificacionmodelorubrica.save(request)
                            for rub in rubricatitulacion:
                                calificaciondetallerubrica = CalificacionDetalleRubricaTitulacionPosgrado(
                                    calificacionrubrica=calificacionrubrica,
                                    detallerubricatitulacionposgrado=rub,
                                    puntaje=0)
                                calificaciondetallerubrica.save(request)

                        data['calificacionrubricatitulacion'] = calificacionrubricatitulacion = CalificacionTitulacionPosgrado.objects.get(tematitulacionposgradomatricula=complexivodetallegrupo, juradocalificador=profesor, status=True)
                        data['calificaciondetallerubricatitulacion'] = calificacionrubricatitulacion.calificaciondetallerubricatitulacionposgrado_set.filter(status=True).order_by('detallerubricatitulacionposgrado__modelorubrica__orden','detallerubricatitulacionposgrado__orden')
                        data['calificaciondetallemodelorubricatitulacion'] = calificacionrubricatitulacion.calificaciondetallemodelorubricatitulacionposgrado_set.filter(status=True).order_by('modelorubrica__orden')
                        data['ponderacionesrubrica'] = RubricaTitulacionCabPonderacionPosgrado.objects.filter(rubrica=calificacionrubricatitulacion.tematitulacionposgradomatricula.rubrica,status=True).order_by('orden')
                        data['archivo_final_titulacion'] = grupo.obtener_archivo_titulacion_final()
                        return render(request, 'pro_tutoriaposgrado/calificar_trabajo_titulacion.html', data)

                except Exception as ex:
                    pass

            if action == 'editar_dictamen':
                try:
                    id = request.GET['id']
                    revision = Revision.objects.get(pk=id)
                    form = FormDictamen(
                        initial={
                            'dictamen': revision.estado,
                        }
                    )
                    data['form']= form
                    data['revision'] = revision
                    template = get_template("pro_tutoriaposgrado/modal/formdictamen.html")
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    pass

            elif action == 'solicitudes':
                try:
                    request.session['viewactivetitu'] = 4
                    data['title'] = u"Seguimiento de tutorías posgrado"
                    url_vars = '&action=solicitudes'
                    data['title'] = u'Solicitud de temas titulación'
                    data['aprobar'] = variable_valor('APROBAR_SILABO')
                    data['rechazar'] = variable_valor('RECHAZAR_SILABO')
                    data['pendiente'] = variable_valor('PENDIENTE_SILABO')
                    idexcluir = TemaTitulacionPosgradoProfesor.objects.values_list('tematitulacionposgradomatricula__id',
                                                                                   flat=True).filter(status=True,
                                                                                                     profesor=profesor).exclude(
                        tematitulacionposgradomatricula__isnull=True)
                    idexcluir_pareja = TemaTitulacionPosgradoProfesor.objects.values_list(
                        'tematitulacionposgradomatriculacabecera__id', flat=True).filter(status=True,
                                                                                         profesor=profesor).exclude(
                        tematitulacionposgradomatriculacabecera__isnull=True)
                    solicitures = TemaTitulacionPosgradoProfesor.objects.filter(profesor=profesor, status=True)
                    solicitudindividual = solicitures.filter(tematitulacionposgradomatriculacabecera__isnull=True)
                    solicitudpareja = solicitures.filter(tematitulacionposgradomatricula__isnull=True)

                    paging = MiPaginador(solicitudindividual, 25)
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
                    data['solicitudes'] = page.object_list
                    data['url_vars'] = url_vars

                    paging2 = MiPaginador(solicitudpareja, 25)

                    p2 = 1
                    try:
                        paginasesion2 = 1
                        if 'paginador2' in request.session:
                            paginasesion2 = int(request.session['paginador2'])
                        if 'page2' in request.GET:
                            p2 = int(request.GET['page2'])
                        else:
                            p2 = paginasesion2
                        try:
                            page2 = paging2.page(p2)
                        except:
                            p2 = 1
                        page2 = paging2.page(p2)
                    except:
                        page2 = paging2.page(p2)
                    request.session['paginador2'] = p2
                    data['paging2'] = paging2
                    data['rangospaging2'] = paging2.rangos_paginado(p2)
                    data['page2'] = page2
                    data['solicitudespareja'] = page2.object_list

                    return render(request, "pro_tutoriaposgrado/viewsolicitudtitu.html", data)
                except Exception as ex:
                    line_err = f"Error en la linea {sys.exc_info()[-1].tb_lineno}"
                    err_ = f"Ocurrio un error, {ex.__str__()}. {line_err}"
                    return HttpResponseRedirect(f"{request.path}?info={err_}")

            elif action == 'firmardocumentostitulacionposgrado':
                try:
                    request.session['viewactivetitu'] = 5
                    tipo = request.GET['tipo']
                    ACTA_SUSTENTACION_CON_NOTA = 10
                    CERTIFICACION_DEFENSA = 9
                    if tipo == 'actasustentacion':
                        data['tipo'] = tipo
                        data['title'] = u"Firma de documentos"
                        filtros, url_vars = Q(status=True),'?action=firmardocumentostitulacionposgrado&tipo=actasustentacion'
                        eIntegranteFirmaTemaTitulacionPosgradoMatricula_ACTA_SUSTENTACION_CON_NOTA = IntegranteFirmaTemaTitulacionPosgradoMatricula.objects.filter(ordenfirma__tipo_acta_id = ACTA_SUSTENTACION_CON_NOTA).filter(status=True, persona_id=persona.id).values_list('tematitulacionposmat_id',flat=True)

                        if pk := request.GET.get('pk', ''):
                            filtros &= Q(pk=pk)
                            url_vars += "&pk={}".format(pk)

                        listadoactas = TemaTitulacionPosgradoMatricula.objects.filter(filtros).filter(pk__in=eIntegranteFirmaTemaTitulacionPosgradoMatricula_ACTA_SUSTENTACION_CON_NOTA).distinct().order_by('tribunaltematitulacionposgradomatricula__fechadefensa')
                        INTEGRANTE_LOGEADO = None



                        for acta in listadoactas:
                            esintegrante = acta.get_es_integrante_por_tipo(persona,ACTA_SUSTENTACION_CON_NOTA)
                            if esintegrante:
                                if not INTEGRANTE_LOGEADO:
                                    INTEGRANTE_LOGEADO = esintegrante
                                    break

                        paging = MiPaginador(listadoactas.distinct(), 15)
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
                        data['actas'] = page.object_list
                        data['url_vars'] = url_vars
                        data['canti'] = listadoactas.count()
                        data['persona'] = request.session.get('persona')
                        return render(request, "pro_tutoriaposgrado/tribunal/viewfirmardocumento.html", data)
                    elif tipo == 'certificaciondefensa':
                        data['title'] = u"Firma de documentos"
                        data['tipo'] = tipo
                        filtros, url_vars = Q(status=True), '?action=firmardocumentostitulacionposgrado&tipo=certificaciondefensa'
                        eIntegranteFirmaTemaTitulacionPosgradoMatricula_CERTIFICACION_DEFENSA = IntegranteFirmaTemaTitulacionPosgradoMatricula.objects.filter(status=True, persona_id=persona.id).filter(ordenfirma__tipo_acta_id=CERTIFICACION_DEFENSA).values_list('tematitulacionposmat_id', flat=True)

                        if pk := request.GET.get('pk', ''):
                            filtros &= Q(pk=pk)
                            url_vars += "&pk={}".format(pk)

                        listadoactas = TemaTitulacionPosgradoMatricula.objects.filter(filtros).filter(pk__in=eIntegranteFirmaTemaTitulacionPosgradoMatricula_CERTIFICACION_DEFENSA).distinct().order_by('tribunaltematitulacionposgradomatricula__fechadefensa')
                        INTEGRANTE_LOGEADO = None
                        for acta in listadoactas:
                            esintegrante = acta.get_es_integrante_por_tipo(persona,CERTIFICACION_DEFENSA)
                            if esintegrante:
                                if not INTEGRANTE_LOGEADO:
                                    INTEGRANTE_LOGEADO = esintegrante
                                    break

                        paging = MiPaginador(listadoactas.distinct(), 15)
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
                        data['actas'] = page.object_list
                        data['url_vars'] = url_vars
                        data['canti'] = listadoactas.count()
                        data['persona'] = request.session.get('persona')
                        return render(request, "pro_tutoriaposgrado/tribunal/viewfirmarcertificaciondefensa.html", data)
                    else:
                        raise NameError("Tipo de documento no encontrado")
                except Exception as ex:
                    line_err = f"Error en la linea {sys.exc_info()[-1].tb_lineno}"
                    err_ = f"Ocurrio un error, {ex.__str__()}. {line_err}"
                    return HttpResponseRedirect(f"{request.path}?info={err_}")


            elif action == 'revision':
                try:
                    request.session['viewactivetitu'] = 2
                    data['title'] = u"Seguimiento de tutorías posgrado"
                    temas_tribunal = TribunalTemaTitulacionPosgradoMatricula.objects.filter(Q(status=True),
                                                                                            Q(presidentepropuesta__persona=persona) |
                                                                                            Q(secretariopropuesta__persona=persona) |
                                                                                            Q(delegadopropuesta__persona=persona)).order_by('-fechadefensa', '-horadefensa')

                    data['temas_revision_tribunal'] = temas_tribunal
                    return render(request, "pro_tutoriaposgrado/viewrevision.html", data)
                except Exception as ex:
                    line_err = f"Error en la linea {sys.exc_info()[-1].tb_lineno}"
                    err_ = f"Ocurrio un error, {ex.__str__()}. {line_err}"
                    return HttpResponseRedirect(f"{request.path}?info={err_}")

            elif action == 'sustentaciones':
                try:
                    request.session['viewactivetitu'] = 3
                    data['title'] = u"Seguimiento de tutorías posgrado"
                    temas_tribunal = TribunalTemaTitulacionPosgradoMatricula.objects.filter(Q(status=True),
                                                                                            Q(presidentepropuesta__persona=persona) |
                                                                                            Q(secretariopropuesta__persona=persona) |
                                                                                            Q(delegadopropuesta__persona=persona)).order_by(
                        '-fechadefensa', '-horadefensa')
                    sustentaciones = []
                    for tribunal in temas_tribunal:
                        if tribunal.tematitulacionposgradomatriculacabecera:
                            participante = tribunal.tematitulacionposgradomatriculacabecera.obtener_parejas()[0]
                        else:
                            participante = tribunal.tematitulacionposgradomatricula

                        detallecalificacion = participante.calificaciontitulacionposgrado_set.filter(
                            status=True).order_by('tipojuradocalificador')
                        if detallecalificacion.exists():
                            promediopuntajetrabajointegral = \
                            detallecalificacion.values_list('puntajetrabajointegral').aggregate(
                                promedio=Avg('puntajetrabajointegral'))['promedio']
                            promediodefensaoral = detallecalificacion.values_list('puntajedefensaoral').aggregate(
                                promedio=Avg('puntajedefensaoral'))['promedio']
                            promediofinal = detallecalificacion.values_list('puntajerubricas').aggregate(
                                promedio=Avg('puntajerubricas'))['promedio']
                            if str(participante.mecanismotitulacionposgrado_id) in variable_valor('ID_MECANISMO_ARTICULOS'):
                                if promediofinal >= 70:
                                    sustentaciones.append(tribunal)
                            else:
                                if promediofinal > 0:
                                    sustentaciones.append(tribunal)
                    data['sustentaciones'] = sustentaciones
                    # data['temas_revision_tribunal'] = temas_tribunal
                    return render(request, "pro_tutoriaposgrado/viewsustentacion.html", data)
                except Exception as ex:
                    line_err = f"Error en la linea {sys.exc_info()[-1].tb_lineno}"
                    err_ = f"Ocurrio un error, {ex.__str__()}. {line_err}"
                    return HttpResponseRedirect(f"{request.path}?info={err_}")

            elif action == 'masinformacion':
                try:
                    if 'id' in request.GET:
                        data['solicitud'] = solicitures = TemaTitulacionPosgradoProfesor.objects.get(pk=request.GET['id'])
                        template = get_template("pro_titulacionposgrado/masinformacion.html")
                        return JsonResponse({"result": 'ok', 'data': template.render(data)})
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos. %s"%(ex.__str__())})

            elif action == 'masinformacionpareja':
                try:
                    if 'id' in request.GET:
                        data['solicitud'] = solicitures = TemaTitulacionPosgradoProfesor.objects.get(pk=request.GET['id'])
                        template = get_template("pro_titulacionposgrado/masinformacionpareja.html")
                        return JsonResponse({"result": 'ok', 'data': template.render(data)})
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

            elif action == 'postulatedocente':
                try:
                    url_vars = '&action=postulatedocente'
                    hoy = datetime.now().date()
                    data['title'] = u'Postúlate'

                    data['aprobar'] = variable_valor('APROBAR_SILABO')
                    data['rechazar'] = variable_valor('RECHAZAR_SILABO')
                    data['pendiente'] = variable_valor('PENDIENTE_SILABO')
                    temasperiodo = None
                    idexcluir = TemaTitulacionPosgradoProfesor.objects.values_list(
                        'tematitulacionposgradomatricula__id', flat=True).filter(status=True,
                                                                                 profesor=profesor).exclude(
                        tematitulacionposgradomatricula__isnull=True)
                    idexcluir_pareja = TemaTitulacionPosgradoProfesor.objects.values_list(
                        'tematitulacionposgradomatriculacabecera__id', flat=True).filter(status=True,
                                                                                         profesor=profesor).exclude(
                        tematitulacionposgradomatriculacabecera__isnull=True)
                    temas = TemaTitulacionPosgradoMatricula.objects.filter(tutor__isnull=True, aprobado=True,
                                                                           matricula__nivel__periodo__configuraciontitulacionposgrado__fechainiciopostulacion__lte=hoy,
                                                                           matricula__nivel__periodo__configuraciontitulacionposgrado__fechafinpostulacion__gte=hoy,
                                                                           status=True).exclude(
                        mecanismotitulacionposgrado_id__in = [15,21]).distinct().order_by('-id')
                    temasperiodo = temas.filter(cabeceratitulacionposgrado__isnull=True).exclude(id__in=idexcluir)
                    temas_pareja_id = temas.filter(cabeceratitulacionposgrado__isnull=False).values_list(
                        'cabeceratitulacionposgrado', flat=True).order_by(
                        'cabeceratitulacionposgrado').distinct().exclude(
                        cabeceratitulacionposgrado_id__in=idexcluir_pareja)
                    temasperiodogrupo = TemaTitulacionPosgradoMatriculaCabecera.objects.filter(pk__in=temas_pareja_id)

                    paging = MiPaginador(temasperiodo, 25)
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
                    data['temasperiodo'] = page.object_list
                    data['url_vars'] = url_vars

                    paging2 = MiPaginador(temasperiodogrupo, 25)

                    p2 = 1
                    try:
                        paginasesion2 = 1
                        if 'paginador2' in request.session:
                            paginasesion2 = int(request.session['paginador2'])
                        if 'page2' in request.GET:
                            p2 = int(request.GET['page2'])
                        else:
                            p2 = paginasesion2
                        try:
                            page2 = paging2.page(p2)
                        except:
                            p2 = 1
                        page2 = paging2.page(p2)
                    except:
                        page2 = paging2.page(p2)
                    request.session['paginador2'] = p2
                    data['paging2'] = paging2
                    data['rangospaging2'] = paging2.rangos_paginado(p2)
                    data['page2'] = page2
                    data['temasperiodogrupo'] = page2.object_list

                    return render(request, "pro_tutoriaposgrado/postulardocente.html", data)
                except Exception as ex:
                    pass

            elif action == 'masinformacionaperturado':
                try:
                    if 'id' in request.GET:
                        data['temaindividualapertura'] = temas = TemaTitulacionPosgradoMatricula.objects.get(
                            pk=request.GET['id'])
                        template = get_template("pro_titulacionposgrado/masinformacionaperturado.html")
                        return JsonResponse({"result": 'ok', 'data': template.render(data)})
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

            elif action == 'masinformacionaperturadopareja':
                try:
                    if 'id' in request.GET:
                        data['pareja'] = parejaaperturado = TemaTitulacionPosgradoMatriculaCabecera.objects.get(pk=request.GET['id'])
                        template = get_template("pro_titulacionposgrado/masinformacionaperturadopareja.html")
                        return JsonResponse({"result": 'ok', 'data': template.render(data)})
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

            elif action == 'add':
                try:
                    data['title'] = u'Solicitar tema titulación'
                    data['tema'] = TemaTitulacionPosgradoMatricula.objects.get(pk=request.GET['id'])
                    return render(request, "pro_titulacionposgrado/add.html", data)
                except Exception as ex:
                    pass

            elif action == 'addpareja':
                try:
                    data['title'] = u'Solicitar tema titulación'
                    data['tema'] = TemaTitulacionPosgradoMatriculaCabecera.objects.get(pk=request.GET['id'])
                    return render(request, "pro_titulacionposgrado/addpareja.html", data)
                except Exception as ex:
                    pass

            elif action == 'verificar_turno_para_firmar':
                try:
                    ACTA_SUSTENTACION_CON_NOTA = 10
                    CERTIFICACION_DEFENSA = 9
                    pk = int(request.GET.get('id', '0'))
                    tipo_documento = int(request.GET.get('tipo_documento', '0'))
                    if pk == 0:
                        raise NameError("Parametro no encontrado")
                    if tipo_documento == 0:
                        raise NameError("Parametro no encontrado")

                    if tipo_documento == ACTA_SUSTENTACION_CON_NOTA:
                        tematitulacionposgradomatricula = TemaTitulacionPosgradoMatricula.objects.get(pk=pk)
                        if variable_valor("PUEDE_FIRMAR_ACTA_SUSTENTACION_POR_ORDEN"):
                            puede, mensaje = tematitulacionposgradomatricula.puede_firmar_integrante_segun_orden_por_tipo(persona,ACTA_SUSTENTACION_CON_NOTA)
                        else:
                            puede, mensaje = tematitulacionposgradomatricula.integrante_ya_firmo_por_tipo(persona,ACTA_SUSTENTACION_CON_NOTA)
                    if tipo_documento == CERTIFICACION_DEFENSA:
                        tematitulacionposgradomatricula = TemaTitulacionPosgradoMatricula.objects.get(pk=pk)
                        if variable_valor("PUEDE_FIRMAR_CERTIFICACION_DEFENSA_POR_ORDEN"):
                            puede, mensaje = tematitulacionposgradomatricula.puede_firmar_integrante_segun_orden_por_tipo(persona,CERTIFICACION_DEFENSA)
                        else:
                            puede, mensaje = tematitulacionposgradomatricula.integrante_ya_firmo_por_tipo(persona,CERTIFICACION_DEFENSA)

                    return JsonResponse({"result": True, "puede": puede, "mensaje": mensaje})
                except Exception as ex:
                    pass

            elif action == 'firmar_acta_sustentacion_certificacion_por_archivo':
                try:
                    tipo =request.GET['tipo']
                    tematitulacionposgradomatricula = TemaTitulacionPosgradoMatricula.objects.get(pk=request.GET['id'])
                    data['id'] = tematitulacionposgradomatricula.pk
                    data['tipo'] = tipo
                    data['action'] = action
                    template = get_template("adm_firmardocumentos/modal/firmardocumento.html")
                    json_content = template.render(data)
                    return JsonResponse({"result": "ok", 'data': json_content})
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

            elif action == 'firmar_acta_sustentacion_certificacion_por_token':
                try:
                    tipo =request.GET['tipo']
                    tematitulacionposgradomatricula = TemaTitulacionPosgradoMatricula.objects.get(pk=request.GET['id'])
                    data['id'] = tematitulacionposgradomatricula.pk
                    data['tipo'] = tipo
                    data['action'] = action
                    data['form2'] = ArchivoInvitacionForm()
                    template = get_template("pro_tutoriaposgrado/tribunal/formmodal.html")
                    json_content = template.render(data)
                    return JsonResponse({"result": "ok", 'data': json_content})
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

            return HttpResponseRedirect(request.path)

        else:
            try:
                request.session['viewactivetitu'] = 1
                data['title'] = u"Seguimiento de tutorías posgrado"
                periodotitulacion = int(encrypt(request.GET['per'])) if 'per' in request.GET else 0
                temas_tribunal = TribunalTemaTitulacionPosgradoMatricula.objects.filter(Q(status=True), Q(presidentepropuesta__persona=persona) | Q(secretariopropuesta__persona=persona) | Q( delegadopropuesta__persona=persona)).order_by( '-fechadefensa', '-horadefensa')
                mis_temas_tutoria_pareja = TemaTitulacionPosgradoMatriculaCabecera.objects.filter(tutor=profesor,status=True).distinct()
                mis_temas_tutoria_individuales = TemaTitulacionPosgradoMatricula.objects.filter(tutor=profesor,status=True).distinct()
                data['docente'] = profesor

                id_periodo_tema_individuales = TemaTitulacionPosgradoMatricula.objects.values_list('convocatoria__id',flat=True).filter( tutor=profesor, status=True).distinct()
                id_periodo_tema_pareja = TemaTitulacionPosgradoMatricula.objects.values_list('convocatoria__id', flat=True).filter( status=True, cabeceratitulacionposgrado_id__in=mis_temas_tutoria_pareja.values_list('id')).distinct()
                id_periodo_tema = id_periodo_tema_individuales | id_periodo_tema_pareja
                periodos = ConfiguracionTitulacionPosgrado.objects.filter(status=True, id__in=id_periodo_tema).distinct().order_by('-id')

                if periodotitulacion > 0:
                    data['perid'] = c = ConfiguracionTitulacionPosgrado.objects.get(pk=periodotitulacion)
                    mis_temas_tutoria_individuales = mis_temas_tutoria_individuales.filter( matricula__nivel__periodo_id=c.periodo.id,cabeceratitulacionposgrado__isnull=True)
                    mis_temas_tutoria_pareja = mis_temas_tutoria_pareja.filter(convocatoria__periodo_id=c.periodo.id)
                else:
                    data['perid'] = []
                    if periodos:
                        data['perid'] = periodos.order_by('-id')[0]
                        mis_temas_tutoria_individuales = mis_temas_tutoria_individuales.filter(matricula__nivel__periodo=periodos[0].periodo.id, cabeceratitulacionposgrado__isnull=True)
                        mis_temas_tutoria_pareja = mis_temas_tutoria_pareja.filter(
                            convocatoria__periodo=periodos[0].periodo.id)
                mis_tutorias = []
                mis_tutorias.append({
                    'individual': mis_temas_tutoria_individuales,
                    'pareja': mis_temas_tutoria_pareja,
                })

                sustentaciones  = []
                for tribunal in temas_tribunal:
                    if tribunal.tematitulacionposgradomatriculacabecera:
                        participante = tribunal.tematitulacionposgradomatriculacabecera.obtener_parejas()[0]
                    else:
                        participante = tribunal.tematitulacionposgradomatricula

                    detallecalificacion = participante.calificaciontitulacionposgrado_set.filter(status=True).order_by('tipojuradocalificador')
                    if detallecalificacion.exists():
                        promediopuntajetrabajointegral = detallecalificacion.values_list('puntajetrabajointegral').aggregate(promedio=Avg('puntajetrabajointegral'))['promedio']
                        promediodefensaoral = detallecalificacion.values_list('puntajedefensaoral').aggregate(promedio=Avg('puntajedefensaoral'))['promedio']
                        promediofinal = detallecalificacion.values_list('puntajerubricas').aggregate(promedio=Avg('puntajerubricas'))['promedio']
                        if promediofinal > 0:
                            sustentaciones.append(tribunal)




                    # if tribunal.tiene_revision_aprobada():
                    #     sustentaciones.append(tribunal)
                    # else:
                    #     if tribunal.tematitulacionposgradomatriculacabecera:
                    #         pass
                    #     else:
                    #         participante = tribunal.tematitulacionposgradomatricula
                    #         detallecalificacion = participante.calificaciontitulacionposgrado_set.filter(status=True).order_by('tipojuradocalificador')
                    #         promediopuntajetrabajointegral= detallecalificacion.values_list('puntajetrabajointegral').aggregate(promedio=Avg('puntajetrabajointegral'))['promedio']
                    #         promediodefensaoral = detallecalificacion.values_list('puntajedefensaoral').aggregate(promedio=Avg('puntajedefensaoral'))['promedio']
                    #         promediofinal = detallecalificacion.values_list('puntajerubricas').aggregate(promedio=Avg('puntajerubricas'))['promedio']
                    #         if promediofinal > 0:
                    #             sustentaciones.append(tribunal)



                data['sustentaciones'] = sustentaciones
                data['grupos'] = mis_tutorias
                data['temas_revision_tribunal'] = temas_tribunal
                data['persona'] = persona
                data['titperiodos'] = periodos

                return render(request, "pro_tutoriaposgrado/view.html", data)
            except Exception as ex:
                pass

# def adicionar_nota_complexivo(idgraduado, nota, fecha, request):
#     if ExamenComlexivoGraduados.objects.filter(graduado_id=idgraduado, itemexamencomplexivo_id=2).exists():
#         itendetalle = ExamenComlexivoGraduados.objects.get(graduado_id=idgraduado, itemexamencomplexivo_id=2)
#         itendetalle.examen = nota
#         itendetalle.ponderacion = null_to_decimal((nota / 2), 2)
#         itendetalle.fecha = fecha
#         log(u'Adicionó Examen Complexivo graduado: %s' % itendetalle, request, "edit")
#     else:
#         itendetalle = ExamenComlexivoGraduados(graduado_id=idgraduado,
#                                                itemexamencomplexivo_id=2,
#                                                examen=nota,
#                                                ponderacion=null_to_decimal((nota / 2), 2),
#                                                fecha=fecha
#                                                )
#         log(u'Adicionó Examen Complexivo graduado por tribunal: %s' % itendetalle, request, "add")
#     itendetalle.save(request)
