# -*- coding: latin-1 -*-
import json
import os
import sys
from datetime import datetime, timedelta, date
import calendar
from dateutil.rrule import MONTHLY, rrule, YEARLY
import pyqrcode
import zipfile
from django.contrib.auth.decorators import login_required
from django.db import transaction, connection
from django.forms import model_to_dict
from django.db.models import Q, Sum, F, Func, Value, CharField, Exists, OuterRef, Count
from django.http import HttpResponseRedirect, HttpResponse, JsonResponse
from django.shortcuts import render
import random
import xlwt
from django.template.context import Context
from django.template.loader import get_template
from xlwt import *

from Moodle_Funciones import CrearTareasTEMoodle
from decorators import secure_module, last_access
from sagest.models import Departamento
from settings import ARCHIVO_TIPO_SYLLABUS, SITE_STORAGE, MEDIA_ROOT
from sga.commonviews import adduserdata, traerNotificaciones
from sga.funcionesxhtml2pdf import conviert_html_to_pdf, conviert_html_to_pdfsaveqrcertificado, \
    conviert_html_to_pdfsaveqrsilabo, download_html_to_pdf, conviert_html_to_pdfsaveqrcertificado_generico
from sga.forms import ArchivoForm, CompendioPlagioForm
from inno.forms import TipoRecursoForm, ConfiguracionRecursoForm, ListaVerificacionForm
from sga.funciones import MiPaginador, log, variable_valor, generar_nombre, null_to_decimal, numeroactividadesdinamico, \
    ultimocodigoactividaddinamico, convertirfecha2, convertir_fecha, convertir_fecha_invertida
from sga.models import Archivo, ProfesorMateria, Carrera, Materia, Silabo, \
    Malla, NivelMalla, ContenidoResultadoProgramaAnalitico, ObjetivoProgramaAnaliticoAsignatura, \
    MetodologiaProgramaAnaliticoAsignatura, ProcedimientoEvaluacionProgramaAnalitico, ResultadoAprendizajeRac, \
    ResultadoAprendizajeRai, AprobarSilabo, \
    DetalleSilaboSemanalTema, DetalleSilaboSemanalSubtema, TemaUnidadResultadoProgramaAnalitico, \
    SubtemaUnidadResultadoProgramaAnalitico, ReactivoMateria, GPGuiaPracticaSemanal, EstadoGuiaPractica, \
    ESTADO_APROBACION_GUIAPRACTICA, Periodo, TareaSilaboSemanal, HistorialaprobacionTarea, ForoSilaboSemanal, \
    HistorialaprobacionForo, HistorialaprobacionTest, TestSilaboSemanal, GuiaEstudianteSilaboSemanal, \
    HistorialaprobacionGuiaEstudiante, GuiaDocenteSilaboSemanal, HistorialaprobacionGuiaDocente, \
    DiapositivaSilaboSemanal, HistorialaprobacionDiapositiva, CompendioSilaboSemanal, HistorialaprobacionCompendio, \
    MaterialAdicionalSilaboSemanal, HistorialaprobacionMaterial, CUENTAS_CORREOS, Persona, miinstitucion, \
    CoordinadorCarrera, Coordinacion, Profesor, UnidadesPeriodo, LineamientoRecursoPeriodo, TareaPracticaSilaboSemanal, \
    HistorialaprobacionTareaPractica, DetalleItemRubricaMoodle, SilaboSemanal, EvaluacionComponente, \
    EvaluacionAprendizajeComponente, EvaluacionAprendizajeTema, COLORES_ACTIVIDADES, Asignatura, \
    VideoMagistralSilaboSemanal, HistorialaprobacionVideoMagistral, RubricaMoodleHistorial, SilaboFirmas, \
    TestSilaboSemanalAdmision, Paralelo, Notificacion, PlanificacionClaseSilabo_Materia, PlanificacionClaseSilabo, AsignaturaMalla, ProgramaAnaliticoAsignaturaMalla, ProgramaAnaliticoAsignatura
from sga.tasks import conectar_cuenta, send_html_mail
from sga.templatetags.sga_extras import encrypt
from inno.models import TipoRecurso, ConfiguracionRecurso, FormatoArchivo, ListaVerificacion, \
    DetalleListaVerificacionTarea, \
    DetalleListaVerificacionForo, DetalleListaVerificacionTest, DetalleListaVerificacionDiapositiva, \
    DetalleListaVerificacionGuiaEstudiante, DetalleListaVerificacionGuiaDocente, \
    DetalleListaVerificacionMaterialAdicional, DetalleListaVerificacionTareaPractica, DetalleListaVerificacionCompendio, \
    DetalleListaVerificacionVideoMagistral, HistorialDetalleListaVerificacionTarea, \
    HistorialDetalleListaVerificacionForo, HistorialDetalleListaVerificacionTest, \
    HistorialDetalleListaVerificacionGuiaEstudiante, HistorialDetalleListaVerificacionGuiaDocente, \
    HistorialDetalleListaVerificacionDiapositiva, HistorialDetalleListaVerificacionCompendio, \
    HistorialDetalleListaVerificacionMaterialAdicional, \
    HistorialDetalleListaVerificacionTareaPractica
from sga.excelbackground import reporte_recurso_aprendizaje_background, reporte_cumplimiento_background, reporte_cumplimiento_background_v3, genera_zip_silabos_background

@login_required(redirect_field_name='ret', login_url='/loginsga')
@secure_module
@last_access
@transaction.atomic()
def view(request):
    global ex
    data = {}
    adduserdata(request, data)
    data['persona'] = persona = request.session['persona']
    data['periodo'] = periodo = request.session['periodo']
    miscarreras = Carrera.objects.filter(coordinadorcarrera__in=persona.gruposcarrera(periodo)).distinct()
    miscoordinaciones = Carrera.objects.filter(grupocoordinadorcarrera__group__in=persona.grupos()).distinct()
    if request.method == 'POST':
        if 'action' in request.POST:
            action = request.POST['action']

            if action == 'aprobarsilabo':
                try:
                    form = ArchivoForm(request.POST)
                    if form.is_valid():
                        materia = Archivo.objects.filter(pk=request.POST['id'])[0].materia
                        profesor = materia.profesormateria_set.filter(status=True, principal=True)[0].profesor
                        materia.actualizarhtml = True
                        materia.save()
                        Archivo.objects.filter(materia=materia).update(aprobado=False)
                        archivopdf = \
                            Archivo.objects.filter(materia=materia, tipo_id=ARCHIVO_TIPO_SYLLABUS, profesor=profesor,
                                                   archivo__contains='.pdf').order_by('-id')[0]
                        archivopdf.aprobado = form.cleaned_data['aprobado']
                        archivopdf.observacion = form.cleaned_data['observacion']
                        archivopdf.save(request)
                        archivoword = \
                            Archivo.objects.filter(materia=materia, tipo_id=ARCHIVO_TIPO_SYLLABUS, profesor=profesor,
                                                   archivo__contains='.doc').order_by('-id')[0]
                        archivoword.aprobado = form.cleaned_data['aprobado']
                        archivoword.observacion = form.cleaned_data['observacion']
                        archivoword.save(request)
                        log(u'Aprobo silabo: %s' % materia, request, "edit")
                        return JsonResponse({"result": "ok"})
                    else:
                        raise NameError('Error')
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

            elif action == 'mostrarsilabodigital':
                try:
                    if 'idm' in request.POST:
                        silabo = Silabo.objects.get(pk=int(request.POST['ids']), status=True)
                        if silabo.materia.asignaturamalla.malla.carrera.modalidad == 3:
                            return conviert_html_to_pdf(
                                'pro_planificacion/silabo_virtual3_pdf.html' if periodo.id >= 112 else 'pro_planificacion/silabo_virtual2_pdf.html' if periodo.id >= 95 else 'pro_planificacion/silabo_virtual_pdf.html',
                                {
                                    'pagesize': 'A4',
                                    'data': silabo.silabo_virtual2_pdf() if periodo.id >= 95 else silabo.silabo_virtual_pdf(),
                                }
                            )
                        else:
                            return conviert_html_to_pdf(
                                'pro_planificacion/silabo_2_pdf.html' if periodo.id >= 112 else 'pro_planificacion/silabo_pdf.html',
                                {
                                    'pagesize': 'A4',
                                    'data': silabo.silabo_pdf(),
                                }
                            )
                except Exception as ex:
                    pass

            elif action == 'silaboverdos_pdf':
                try:
                    data['silabo'] = silabo = Silabo.objects.get(pk=int(encrypt(request.POST['id'])), status=True)
                    return conviert_html_to_pdf(
                        'pro_planificacion/silabovs2_pdf.html',
                        {
                            'pagesize': 'A4',
                            'datos': silabo.silabodetalletemas_pdf(),
                            'data': silabo.silabovdos_pdf(),
                        }
                    )
                except Exception as ex:
                    pass

            elif action == 'programaanalitico_pdf':
                try:
                    materia = Materia.objects.get(pk=request.POST['id'])
                    data['proanalitico'] = pro = \
                        materia.asignaturamalla.programaanaliticoasignatura_set.filter(status=True, activo=True)[0]
                    return conviert_html_to_pdf(
                        'mallas/programanalitico_pdf.html',
                        {
                            'pagesize': 'A4',
                            'data': pro.plananalitico_pdf(periodo),
                            'materia': materia, 'periodo': periodo
                        }
                    )
                except Exception as ex:
                    pass

            elif action == 'programanaliticoposgrado_pdf':
                try:
                    materia = Materia.objects.get(pk=request.POST['id'])
                    qrname = 'qr_programaanalitico_' + str(encrypt(materia.id))
                    folder = os.path.join(os.path.join(SITE_STORAGE, 'media', 'qrcode', 'programaanalitico', 'qr'))
                    try:
                        os.stat(folder)
                    except:
                        os.makedirs(folder)
                    rutapdf = folder + os.sep + qrname + '.pdf'
                    rutaimg = folder + os.sep + qrname + '.png'
                    if os.path.isfile(rutapdf):
                        os.remove(rutapdf)
                    if os.path.isfile(rutaimg):
                        os.remove(rutaimg)
                    url = pyqrcode.create('https://sga.unemi.edu.ec/media/qrcode/programaanalitico/qr/' + qrname + '.pdf')
                    # url = pyqrcode.create('http://127.0.0.1:8000/media/qrcode/programaanalitico/qr/' + qrname + '.pdf')
                    imageqr = url.png(folder + os.sep + qrname + '.png', 16, '#000000')
                    imagenqr = qrname
                    data['proanalitico'] = pro = materia.asignaturamalla.programaanaliticoasignatura_set.filter(status=True, activo=True)[0]
                    valida = conviert_html_to_pdfsaveqrcertificado_generico(request,
                        'mallas/programanaliticoposgrado_pdf.html',
                        {
                            'pagesize': 'A4',
                            'data':pro.plananalitico_pdf(periodo),
                            'imprimeqr':True,
                            'qrname':imagenqr
                        },folder, qrname + '.pdf'
                    )
                    if valida:
                        os.remove(rutaimg)
                        return HttpResponse(valida[2].getvalue(), content_type='application/pdf')
                except Exception as ex:
                    pass

            elif action == 'aprobar_silabo':
                try:
                    if 'id' in request.POST and 'st' in request.POST and 'obs' in request.POST:
                        coordinadorprograma = None
                        coordinadoracademico = None
                        silabo = Silabo.objects.get(pk=int(request.POST['id']))
                        carrera = silabo.materia.asignaturamalla.malla.carrera
                        if silabo.materia.nivel.periodo.tipo.id in [1, 2]:
                            cp = CoordinadorCarrera.objects.filter(periodo=periodo, carrera=carrera, tipo=3)
                            if cp:
                                coordinadorprograma = cp[0].persona
                            ca = Departamento.objects.filter(status=True, nombre__icontains='POSTGRADO')
                            if ca:
                                coordinadoracademico = ca[0].responsable
                            aprobars = AprobarSilabo(silabo=silabo,
                                                     observacion=request.POST['obs'],
                                                     persona=persona,
                                                     fecha=datetime.now(),
                                                     estadoaprobacion=request.POST['st'])
                            aprobars.save(request)
                            if not silabo.silabofirmas_set.filter(status=True):
                                silabofirmas = SilaboFirmas(silabo=silabo,
                                                            coordinadorprograma=coordinadorprograma,
                                                            coordinadoracademico=coordinadoracademico)
                                silabofirmas.save(request)
                            else:
                                silabofirmas = SilaboFirmas.objects.filter(silabo_id=silabo, status=True)[0]
                                silabofirmas.coordinadorprograma = coordinadorprograma
                                silabofirmas.coordinadoracademico = coordinadoracademico
                                silabofirmas.save(request)
                        if silabo.materia.asignaturamalla.malla.carrera.coordinacion_carrera().id == 7:
                            cp = CoordinadorCarrera.objects.filter(periodo=periodo, carrera=carrera, tipo=3)
                            coorpos = silabo.materia.asignaturamalla.malla.carrera.coordinacion_carrera().responsablecoordinacion_set.filter(periodo=periodo, tipo=1)
                            if cp:
                                coordinadorprograma = cp[0].persona
                            if coorpos:
                                coordinadoracademico = coorpos[0].persona
                            fecha = datetime.now()
                            if 'fechaaprobacion' in request.POST:
                                if request.POST['fechaaprobacion'] != '':
                                    fecha = convertirfecha2(request.POST['fechaaprobacion'])
                            aprobars = AprobarSilabo(silabo=silabo,
                                                     observacion=request.POST['obs'],
                                                     persona=persona,
                                                     fecha=fecha,
                                                     estadoaprobacion=request.POST['st'])
                            aprobars.save(request)
                            if not silabo.silabofirmas_set.filter(status=True):
                                silabofirmas = SilaboFirmas(silabo=silabo,
                                                            coordinadorprograma=coordinadorprograma,
                                                            coordinadoracademico=coordinadoracademico)
                                silabofirmas.save(request)
                            else:
                                silabofirmas = SilaboFirmas.objects.filter(silabo_id=silabo, status=True)[0]
                                silabofirmas.coordinadorprograma = coordinadorprograma
                                silabofirmas.coordinadoracademico = coordinadoracademico
                                silabofirmas.save(request)

                        if variable_valor('APROBAR_SILABO') == int(request.POST['st']):
                            materia = silabo.materia
                            materia.actualizarhtml = True
                            materia.save()
                            if silabo.versionsilabo == 2 and silabo.materia.nivel.periodo.tipo.id in [1, 2]:
                                qrname = 'qr_silabo_' + str(encrypt(silabo.id))
                                folder = os.path.join(os.path.join(SITE_STORAGE, 'media', 'qrcode', 'silabodocente', 'qr'))
                                rutapdf = folder + qrname + '.pdf'
                                rutaimg = folder + qrname + '.png'
                                if os.path.isfile(rutapdf):
                                    os.remove(rutapdf)
                                if os.path.isfile(rutaimg):
                                    os.remove(rutaimg)
                                url = pyqrcode.create('http://sga.unemi.edu.ec//media/qrcode/silabodocente/' + qrname + '.pdf')
                                # url = pyqrcode.create('http://127.0.0.1:8000//media/qrcode/silabodocente/' + qrname + '.pdf')
                                imageqr = url.png(folder + qrname + '.png', 16, '#000000')
                                imagenqr = 'qr' + qrname
                                valida = conviert_html_to_pdfsaveqrsilabo(
                                    'pro_planificacion/silabovs2_pdf.html',
                                    {'datos': silabo.silabodetalletemas_pdf(),
                                     'data': silabo.silabovdos_pdf(),
                                     'imprimeqr': True,
                                     'qrname': imagenqr
                                     }, qrname + '.pdf'
                                )
                                if valida:
                                    os.remove(rutaimg)
                                    silabo.codigoqr = True
                                    silabo.save()

                                if PlanificacionClaseSilabo_Materia.objects.filter(materia=silabo.materia, status=True):
                                    listaplanificacion = PlanificacionClaseSilabo_Materia.objects.filter(materia=silabo.materia, status=True)[0]
                                    listaplanclase = PlanificacionClaseSilabo.objects.filter(tipoplanificacion=listaplanificacion.tipoplanificacion, status=True)
                                    for lis in listaplanclase:
                                        silasemanal = silabo.silabosemanal_set.filter(status=True)
                                        for semanal in silasemanal:
                                            if semanal.numsemana == lis.semana:
                                                semanal.parcial = lis.parcial
                                                semanal.save()

                            if silabo.versionsilabo == 2 and silabo.materia.asignaturamalla.malla.carrera.coordinacion_carrera().id == 7:
                                det_modeloevaluativo = silabo.materia.modeloevaluativo.detallemodeloevaluativo_set.filter(status=True,migrarmoodle=True)
                                qrname = 'qr_silabo_' + str(encrypt(silabo.id))
                                folder = os.path.join(os.path.join(SITE_STORAGE, 'media', 'qrcode', 'silabodocente', 'qr'))
                                rutapdf = folder + qrname + '.pdf'
                                rutaimg = folder + qrname + '.png'
                                if os.path.isfile(rutapdf):
                                    os.remove(rutapdf)
                                if os.path.isfile(rutaimg):
                                    os.remove(rutaimg)
                                url = pyqrcode.create('http://sga.unemi.edu.ec//media/qrcode/silabodocente/' + qrname + '.pdf')
                                # url = pyqrcode.create('http://127.0.0.1:8000//media/qrcode/silabodocente/' + qrname + '.pdf')
                                imageqr = url.png(folder + qrname + '.png', 16, '#000000')
                                imagenqr = 'qr' + qrname
                                dat_ = silabo.silabo_virtual_posgrado_pdf()
                                dat_['modelo_evaluativo'] = det_modeloevaluativo
                                valida = conviert_html_to_pdfsaveqrsilabo(
                                    'pro_planificacion/silabo_virtual_posgrado_pdf.html',
                                    {'data': dat_,
                                     'imprimeqr': True,
                                     'qrname': imagenqr
                                     }, qrname + '.pdf'
                                )
                                if valida:
                                    os.remove(rutaimg)
                                    silabo.codigoqr = True
                                    silabo.save()

                                silabo.aprobado = True
                                silabo.save(request)

                            log(u'Aprobó el sílabo %s el director: %s' % (silabo, persona), request, "add")
                            # silabo.materia.crear_actualizar_silabo_curso()
                        else:
                            silabo.codigoqr = False
                            silabo.save()
                            log(u'Rechazó el sílabo %s el director: %s' % (silabo, persona), request, "add")
                        return JsonResponse({"result": "ok", "idm": silabo.materia.id})
                except Exception as ex:
                    error = "%s - %s" %(sys.exc_info()[-1].tb_lineno,ex)
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos. %s" % error})

            elif action == 'detalleaprobacion':
                try:
                    data['silabo'] = silabo = Silabo.objects.get(pk=int(request.POST['id']))
                    data['historialaprobacion'] = silabo.aprobarsilabo_set.filter(status=True).order_by('-id').exclude(
                        estadoaprobacion=variable_valor('PENDIENTE_SILABO'))
                    data['aprobar'] = variable_valor('APROBAR_SILABO')
                    data['rechazar'] = variable_valor('RECHAZAR_SILABO')
                    data['pendiente'] = variable_valor('PENDIENTE_SILABO')
                    template = get_template("aprobar_silabo/detalleaprobacion.html")
                    json_content = template.render(data)
                    return JsonResponse({"result": "ok", 'data': json_content})
                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})
                    pass

            elif action == 'confirmarreactivo':
                try:
                    materia = Materia.objects.get(pk=request.POST['id'])
                    iddetalle = request.POST['iddetalle']
                    reactivomateria = ReactivoMateria(materia=materia,
                                                      fecha=datetime.now(),
                                                      persona=persona,
                                                      detallemodelo_id=iddetalle)
                    reactivomateria.save(request)
                    log(u'Confirmo Reactivo: %s' % reactivomateria, request, "add")
                    return JsonResponse({"result": "ok"})
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", "mensaje": "Error al guardar los datos."})

            elif action == 'eliminarconfirmacion':
                try:
                    materia = Materia.objects.get(pk=request.POST['id'])
                    iddetalle = request.POST['iddetalle']
                    reactivomateria = ReactivoMateria.objects.filter(materia=materia, detallemodelo_id=iddetalle)
                    log(u'Elimino Confirmacion Reactivo: %s' % reactivomateria, request, "del")
                    reactivomateria.delete()
                    return JsonResponse({"result": "ok"})
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", "mensaje": "Error al guardar los datos."})

            elif action == 'practicapdf':
                try:
                    silabo = Silabo.objects.get(pk=int(request.POST['ids']))
                    data['practicas'] = GPGuiaPracticaSemanal.objects.filter(status=True,
                                                                             silabosemanal__silabo=silabo).order_by(
                        'silabosemanal__numsemana')
                    data['decano'] = silabo.materia.coordinacion_materia().responsable_periododos(
                        silabo.materia.nivel.periodo,
                        1) if silabo.materia.coordinacion_materia().responsable_periododos(silabo.materia.nivel.periodo,
                                                                                           1) else None
                    data['director'] = silabo.materia.asignaturamalla.malla.carrera.coordinador(
                        silabo.materia.nivel.periodo,
                        silabo.profesor.coordinacion.sede).persona.nombre_completo_inverso() if silabo.materia.asignaturamalla.malla.carrera.coordinador(
                        silabo.materia.nivel.periodo, silabo.profesor.coordinacion.sede) else None
                    return conviert_html_to_pdf(
                        'pro_planificacion/practica_pdf.html',
                        {
                            'pagesize': 'A4',
                            'data': data,
                        }
                    )
                except Exception as ex:
                    pass

            elif action == 'practica_indpdf':
                try:
                    practica = GPGuiaPracticaSemanal.objects.get(status=True, pk=int(request.POST['id']))
                    data['practicas'] = GPGuiaPracticaSemanal.objects.filter(status=True, id=practica.id)
                    data[
                        'decano'] = practica.silabosemanal.silabo.materia.coordinacion_materia().responsable_periododos(
                        practica.silabosemanal.silabo.materia.nivel.periodo,
                        1) if practica.silabosemanal.silabo.materia.coordinacion_materia().responsable_periododos(
                        practica.silabosemanal.silabo.materia.nivel.periodo, 1) else None
                    data['director'] = practica.silabosemanal.silabo.materia.asignaturamalla.malla.carrera.coordinador(
                        practica.silabosemanal.silabo.materia.nivel.periodo,
                        practica.silabosemanal.silabo.profesor.coordinacion.sede).persona.nombre_completo_inverso() if practica.silabosemanal.silabo.materia.asignaturamalla.malla.carrera.coordinador(
                        practica.silabosemanal.silabo.materia.nivel.periodo,
                        practica.silabosemanal.silabo.profesor.coordinacion.sede) else None
                    return conviert_html_to_pdf(
                        'pro_planificacion/practica_pdf.html',
                        {
                            'pagesize': 'A4',
                            'data': data,
                        }
                    )
                except Exception as ex:
                    pass

            elif action == 'revisarpractica':
                try:
                    if 'id' in request.POST and 'observacion' in request.POST and 'estado' in request.POST:
                        if int(request.POST['id']) > 0 and int(request.POST['estado']) > 0:
                            estado = EstadoGuiaPractica(guipractica_id=request.POST['id'],
                                                        observacion=request.POST['observacion'],
                                                        fecha=datetime.now().date(), persona=persona,
                                                        estado=request.POST['estado'])
                            estado.save(request)
                            log(u'Rechazo %s la guía de práctica: %s de la materia %s' % (
                                persona, estado.guipractica, estado.guipractica.silabosemanal.silabo.materia), request,
                                "rech")
                            return JsonResponse({"result": "ok", 'idestadogp': estado.estado,
                                                 'estadogp': estado.guipractica.nombre_estado_guiapractica()})
                        else:
                            return JsonResponse({"result": "bad", "mensaje": "Es obligatorio el estado."})
                    else:
                        return JsonResponse({"result": "bad", "mensaje": "Error al guardar los datos."})
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", "mensaje": "Error al guardar los datos."})

            elif action == 'detallerevicion':
                try:
                    data['title'] = u'Detalle de revisión de guías de práctica'
                    practica = GPGuiaPracticaSemanal.objects.get(pk=request.POST['id'])
                    data['revisiones'] = practica.estadoguiapractica_set.filter(status=True).order_by('-fecha')
                    template = get_template("aprobar_silabo/detallerevision.html")
                    json_content = template.render(data)
                    return JsonResponse({"result": "ok", 'data': json_content})
                except Exception as ex:
                    pass

            elif action == 'aprobarguiapractica':
                try:
                    if 'id' in request.POST:
                        practicas = GPGuiaPracticaSemanal.objects.values_list('id').filter(
                            silabosemanal__silabo__materia__profesormateria__profesor__coordinacion__carrera__in=persona.mis_carreras(),
                            silabosemanal__silabo__materia__nivel__periodo__id=request.POST['id'],
                            estadoguiapractica__estado=2).distinct().order_by('silabosemanal__silabo', 'silabosemanal')
                        for p in practicas:
                            if not EstadoGuiaPractica.objects.values('id').filter(pk=p[0], estado=3).exists():
                                estado = EstadoGuiaPractica(guipractica_id=p[0], fecha=datetime.now().date(),
                                                            persona=persona, estado=3)
                                estado.save(request)
                                log(u'Aprobó, %s la guía de práctica: %s de la materia %s' % (
                                    persona, estado.guipractica, estado.guipractica.silabosemanal.silabo.materia), request,
                                    "aprob")
                        return JsonResponse({"result": "ok"})
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", "mensaje": "Error al guardar los datos."})

            elif action == 'silaboposgradopdf':
                try:
                    silabo = Silabo.objects.get(pk=int(request.POST['ids']), status=True)
                    return conviert_html_to_pdf(
                        'aprobar_silabo/silabo_virtual_posgrado_pdf.html',
                        {
                            'pagesize': 'A4',
                            'data': silabo.silabo_virtual_posgrado_pdf(),
                        }
                    )
                except Exception as ex:
                    pass

            elif action == 'detalletarea':
                try:
                    tipo = int(request.POST['codtipo'])
                    if tipo == 1:
                        data['tarea'] = tarea = TareaSilaboSemanal.objects.get(pk=int(request.POST['idtar']))
                        data['historialaprobacion'] = tarea.historialaprobaciontarea_set.filter(status=True).order_by(
                            'id')
                        data['tiene_rubrica'] = False
                        if tarea.rubricamoodle:
                            data['tiene_rubrica'] = True
                            arreglo = []
                            arreglosumatoria = []
                            arreglo_aux = []
                            data['rubrica'] = r = tarea.rubricamoodle
                            data['criterios'] = criterios = r.itemrubricamoodle_set.filter(status=True).order_by(
                                'orden')
                            detalles = DetalleItemRubricaMoodle.objects.filter(status=True, item__rubrica=r)
                            ordenmaximo = detalles.order_by('-orden')[0].orden
                            i = 1
                            while i <= ordenmaximo:
                                sumatoria = int(null_to_decimal(
                                    detalles.filter(orden=i).aggregate(sumatoria=Sum('valor'))['sumatoria'], 0))
                                arreglosumatoria.append(sumatoria)
                                i += 1

                            for c in criterios:
                                arreglo_aux.append([c.item, ''])
                                for d in c.detalleitemrubricamoodle_set.filter(status=True).order_by('orden'):
                                    arreglo_aux.append([d.descripcion, d.valor])
                                arreglo.append(arreglo_aux)
                                arreglo_aux = []
                            data['arreglo'] = arreglo
                            data['arreglosumatoria'] = arreglosumatoria
                        template = get_template("aprobar_silabo/detalletarea.html")
                    if tipo == 2:
                        data['foro'] = foro = ForoSilaboSemanal.objects.get(pk=int(request.POST['idtar']))
                        data['historialaprobacion'] = foro.historialaprobacionforo_set.filter(status=True).order_by(
                            'id')
                        template = get_template("aprobar_silabo/detalleforo.html")
                    if tipo == 3:
                        data['test'] = test = TestSilaboSemanalAdmision.objects.get(pk=int(request.POST['idtar']))
                        data['historialaprobacion'] = test.historialaprobaciontestadmision_set.filter(status=True).order_by(
                            'id')
                        template = get_template("aprobar_silabo/detalletest.html")
                    if tipo == 4:
                        data['guiaestudiante'] = guiaestudiante = GuiaEstudianteSilaboSemanal.objects.get(pk=int(request.POST['idtar']))
                        data['historialaprobacion'] = guiaestudiante.historialaprobacionguiaestudiante_set.filter(status=True).order_by('id')
                        data['formatos'] = guiaestudiante.mis_formatos(periodo)
                        template = get_template("aprobar_silabo/detalleguiaestudiante.html")
                    if tipo == 5:
                        data['guiadocente'] = guiadocente = GuiaDocenteSilaboSemanal.objects.get(
                            pk=int(request.POST['idtar']))
                        data['historialaprobacion'] = guiadocente.historialaprobacionguiadocente_set.filter(
                            status=True).order_by('id')
                        template = get_template("aprobar_silabo/detalleguiadocente.html")
                    if tipo == 6:
                        data['diapositiva'] = diapositiva = DiapositivaSilaboSemanal.objects.get(
                            pk=int(request.POST['idtar']))
                        data['historialaprobacion'] = diapositiva.historialaprobaciondiapositiva_set.filter(
                            status=True).order_by('id')
                        data['formatos'] = diapositiva.mis_formatos(periodo)
                        template = get_template("aprobar_silabo/detallediapositiva.html")
                    if tipo == 7:
                        data['title'] = u'Evidencia Practicas'
                        data['compendio'] = compendio = CompendioSilaboSemanal.objects.get(pk=int(request.POST['idtar']))
                        if compendio.estado.id in [1, 2, 3]:
                            data['form'] = CompendioPlagioForm
                        data['formatos'] = compendio.mis_formatos(periodo)
                        data['historialaprobacion'] = compendio.historialaprobacioncompendio_set.filter(status=True).order_by('id')
                        template = get_template("aprobar_silabo/detallecompendio.html")
                    if tipo == 8:
                        data['material'] = material = MaterialAdicionalSilaboSemanal.objects.get(
                            pk=int(request.POST['idtar']))
                        data['historialaprobacion'] = material.historialaprobacionmaterial_set.filter(
                            status=True).order_by('id')
                        template = get_template("aprobar_silabo/detallematerial.html")
                    if tipo == 9:
                        data['practica'] = practica = TareaPracticaSilaboSemanal.objects.get(
                            pk=int(request.POST['idtar']))
                        data['historialaprobacion'] = practica.historialaprobaciontareapractica_set.filter(
                            status=True).order_by('id')
                        data['tiene_rubrica'] = False
                        if practica.rubricamoodle:
                            data['tiene_rubrica'] = True
                            arreglo = []
                            arreglosumatoria = []
                            arreglo_aux = []
                            data['rubrica'] = r = practica.rubricamoodle
                            data['criterios'] = criterios = r.itemrubricamoodle_set.filter(status=True).order_by(
                                'orden')
                            detalles = DetalleItemRubricaMoodle.objects.filter(status=True, item__rubrica=r)
                            ordenmaximo = detalles.order_by('-orden')[0].orden
                            i = 1
                            while i <= ordenmaximo:
                                sumatoria = int(null_to_decimal(
                                    detalles.filter(orden=i).aggregate(sumatoria=Sum('valor'))['sumatoria'], 0))
                                arreglosumatoria.append(sumatoria)
                                i += 1

                            for c in criterios:
                                arreglo_aux.append([c.item, ''])
                                for d in c.detalleitemrubricamoodle_set.filter(status=True).order_by('orden'):
                                    arreglo_aux.append([d.descripcion, d.valor])
                                arreglo.append(arreglo_aux)
                                arreglo_aux = []
                            data['arreglo'] = arreglo
                            data['arreglosumatoria'] = arreglosumatoria
                        template = get_template("aprobar_silabo/detalletareapractica.html")
                    if tipo == 10:
                        data['videomagistral'] = videomagistral = VideoMagistralSilaboSemanal.objects.get(pk=int(request.POST['idtar']))
                        data['historialaprobacion'] = videomagistral.historialaprobacionvideomagistral_set.filter(status=True).order_by('id')
                        template = get_template("aprobar_silabo/detallevideomagistral.html")
                    json_content = template.render(data)
                    return JsonResponse({"result": "ok", 'data': json_content})
                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})
                    pass

            elif action == 'detalletarea_pregrado':
                try:
                    tipo = int(request.POST['codtipo'])

                    if tipo == 1:
                        data['tarea'] = tarea = TareaSilaboSemanal.objects.get(pk=int(request.POST['idtar']))
                        data['historialaprobacion'] = tarea.historialaprobaciontarea_set.filter(status=True).order_by(
                            'id')
                        data['tiene_rubrica'] = False
                        # data['tiporecurso'] = tiporecurso = TipoRecurso.objects.get(pk=int(request.GET['id']))
                        data['listasverificacion'] = listaverificacion = ListaVerificacion.objects.filter(status=True, tiporecurso=tarea.tiporecurso)
                        # data['detallelista'] = DetalleListaVerificacion.objects.filter(status=True,tareasilabosemanal=tarea.id)
                        # data['ultimoestado'] = HistorialaprobacionTarea.objects.filter(status=True, tarea=tarea.id).last()

                        if tarea.rubricamoodle:
                            data['tiene_rubrica'] = True
                            arreglo = []
                            arreglosumatoria = []
                            arreglo_aux = []
                            data['rubrica'] = r = tarea.rubricamoodle
                            data['criterios'] = criterios = r.itemrubricamoodle_set.filter(status=True).order_by(
                                'orden')
                            detalles = DetalleItemRubricaMoodle.objects.filter(status=True, item__rubrica=r)
                            ordenmaximo = detalles.order_by('-orden')[0].orden
                            i = 1
                            while i <= ordenmaximo:
                                sumatoria = int(null_to_decimal(
                                    detalles.filter(orden=i).aggregate(sumatoria=Sum('valor'))['sumatoria'], 0))
                                arreglosumatoria.append(sumatoria)
                                i += 1

                            for c in criterios:
                                arreglo_aux.append([c.item, ''])
                                for d in c.detalleitemrubricamoodle_set.filter(status=True).order_by('orden'):
                                    arreglo_aux.append([d.descripcion, d.valor])
                                arreglo.append(arreglo_aux)
                                arreglo_aux = []
                            data['arreglo'] = arreglo
                            data['arreglosumatoria'] = arreglosumatoria

                        mostrar = False
                        if listaverificacion:
                            mostrar = True
                        template = get_template("aprobar_silabo/detalletareavdos.html")

                    if tipo == 2:
                        data['foro'] = foro = ForoSilaboSemanal.objects.get(pk=int(request.POST['idtar']))
                        data['historialaprobacion'] = foro.historialaprobacionforo_set.filter(status=True).order_by(
                            'id')
                        data['listasverificacion'] = listaverificacion = ListaVerificacion.objects.filter(status=True,
                                                                                                          tiporecurso=foro.tiporecurso)
                        mostrar = False
                        if listaverificacion:
                            mostrar = True
                        template = get_template("aprobar_silabo/detalleforovdos.html")

                    if tipo == 3:
                        data['test'] = test = TestSilaboSemanal.objects.get(pk=int(request.POST['idtar']))
                        data['historialaprobacion'] = test.historialaprobaciontest_set.filter(status=True).order_by(
                            'id')
                        data['listasverificacion'] = listaverificacion = ListaVerificacion.objects.filter(status=True,
                                                                                                          tiporecurso=test.tiporecurso)
                        mostrar = False
                        if listaverificacion:
                            mostrar = True
                        template = get_template("aprobar_silabo/detalletestvdos.html")

                    if tipo == 4:
                        data['guiaestudiante'] = guiaestudiante = GuiaEstudianteSilaboSemanal.objects.get(pk=int(request.POST['idtar']))
                        data['historialaprobacion'] = guiaestudiante.historialaprobacionguiaestudiante_set.filter(status=True).order_by('id')
                        data['formatos'] = guiaestudiante.mis_formatos(periodo)
                        data['listasverificacion'] = listaverificacion = ListaVerificacion.objects.filter(status=True,
                                                                                                          tiporecurso=guiaestudiante.tiporecurso)
                        mostrar = False
                        if listaverificacion:
                            mostrar = True
                        template = get_template("aprobar_silabo/detalleguiaestudiantevdos.html")

                    if tipo == 5:
                        data['guiadocente'] = guiadocente = GuiaDocenteSilaboSemanal.objects.get(
                            pk=int(request.POST['idtar']))
                        data['historialaprobacion'] = guiadocente.historialaprobacionguiadocente_set.filter(
                            status=True).order_by('id')
                        data['listasverificacion'] = listaverificacion = ListaVerificacion.objects.filter(status=True,
                                                                                                          tiporecurso=guiadocente.tiporecurso)
                        mostrar = False
                        if listaverificacion:
                            mostrar = True
                        template = get_template("aprobar_silabo/detalleguiadocentevdos.html")

                    if tipo == 6:
                        data['diapositiva'] = diapositiva = DiapositivaSilaboSemanal.objects.get(
                            pk=int(request.POST['idtar']))
                        data['historialaprobacion'] = diapositiva.historialaprobaciondiapositiva_set.filter(
                            status=True).order_by('id')
                        data['formatos'] = diapositiva.mis_formatos(periodo)
                        data['listasverificacion'] = listaverificacion = ListaVerificacion.objects.filter(status=True,
                                                                                                          tiporecurso=diapositiva.tiporecurso)
                        mostrar = False
                        if listaverificacion:
                            mostrar = True
                        template = get_template("aprobar_silabo/detallediapositivavdos.html")

                        # template = get_template("aprobar_silabo/detallediapositiva.html")

                    if tipo == 7:
                        data['title'] = u'Evidencia Practicas'
                        data['compendio'] = compendio = CompendioSilaboSemanal.objects.get(pk=int(request.POST['idtar']))
                        data['formatos'] = compendio.mis_formatos(periodo)
                        data['historialaprobacion'] = compendio.historialaprobacioncompendio_set.filter(status=True).order_by('id')
                        data['listasverificacion'] = listaverificacion = ListaVerificacion.objects.filter(status=True,
                                                                                                          tiporecurso=compendio.tiporecurso)

                        data['mostrar'] = mostrar = 'False'
                        if compendio.estado.id in [1, 3] and listaverificacion:
                            data['form'] = CompendioPlagioForm
                            data['mostrar'] = mostrar = 'True'
                            # mostrar = False
                        # if listaverificacion:
                        #     data['mostrar'] = mostrar = True
                        # mostrar = True
                        template = get_template("aprobar_silabo/detallecompendiovdos.html")

                    if tipo == 8:
                        data['material'] = material = MaterialAdicionalSilaboSemanal.objects.get(
                            pk=int(request.POST['idtar']))
                        data['historialaprobacion'] = material.historialaprobacionmaterial_set.filter(
                            status=True).order_by('id')

                        data['listasverificacion'] = listaverificacion = ListaVerificacion.objects.filter(status=True,
                                                                                                          tiporecurso=material.tiporecursos)
                        mostrar = False
                        if listaverificacion:
                            mostrar = True
                        template = get_template("aprobar_silabo/detallematerialvdos.html")

                    if tipo == 9:
                        data['practica'] = practica = TareaPracticaSilaboSemanal.objects.get(
                            pk=int(request.POST['idtar']))
                        data['historialaprobacion'] = practica.historialaprobaciontareapractica_set.filter(
                            status=True).order_by('id')
                        data['tiene_rubrica'] = False
                        data['listasverificacion'] = listaverificacion = ListaVerificacion.objects.filter(status=True,
                                                                                                          tiporecurso=practica.tiporecurso)
                        if practica.rubricamoodle:
                            data['tiene_rubrica'] = True
                            arreglo = []
                            arreglosumatoria = []
                            arreglo_aux = []
                            data['rubrica'] = r = practica.rubricamoodle
                            data['criterios'] = criterios = r.itemrubricamoodle_set.filter(status=True).order_by(
                                'orden')
                            detalles = DetalleItemRubricaMoodle.objects.filter(status=True, item__rubrica=r)
                            ordenmaximo = detalles.order_by('-orden')[0].orden
                            i = 1
                            while i <= ordenmaximo:
                                sumatoria = int(null_to_decimal(
                                    detalles.filter(orden=i).aggregate(sumatoria=Sum('valor'))['sumatoria'], 0))
                                arreglosumatoria.append(sumatoria)
                                i += 1

                            for c in criterios:
                                arreglo_aux.append([c.item, ''])
                                for d in c.detalleitemrubricamoodle_set.filter(status=True).order_by('orden'):
                                    arreglo_aux.append([d.descripcion, d.valor])
                                arreglo.append(arreglo_aux)
                                arreglo_aux = []
                            data['arreglo'] = arreglo
                            data['arreglosumatoria'] = arreglosumatoria

                        mostrar = False
                        if listaverificacion:
                            mostrar = True
                        template = get_template("aprobar_silabo/detalletareapracticavdos.html")

                    if tipo == 10:
                        data['videomagistral'] = videomagistral = VideoMagistralSilaboSemanal.objects.get(pk=int(request.POST['idtar']))
                        data['historialaprobacion'] = videomagistral.historialaprobacionvideomagistral_set.filter(status=True).order_by('id')
                        mostrar = True
                        template = get_template("aprobar_silabo/detallevideomagistral.html")

                    # if tipo == 10:
                    #     data['videomagistral'] = videomagistral = VideoMagistralSilaboSemanal.objects.get(pk=int(request.POST['idtar']))
                    #     data['historialaprobacion'] = videomagistral.historialaprobacionvideomagistral_set.filter(status=True).order_by('id')
                    #     data['listasverificacion'] = listaverificacion = ListaVerificacion.objects.filter(status=True,
                    #                                                                                       tiporecurso=videomagistral.tiporecursos)
                    #     mostrar = False
                    #     if listaverificacion:
                    #         mostrar = True

                    json_content = template.render(data)
                    return JsonResponse({"result": "ok", "mostrar": False, 'data': json_content})
                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})
                    pass

            elif action == 'detallehistorialtarea':
                try:
                    data['historialaprobacion'] = historialaprobacion = HistorialaprobacionTarea.objects.get(pk=int(request.POST['id']))
                    data['historialdettarea'] = HistorialDetalleListaVerificacionTarea.objects.filter(status=True, historialaprobaciontarea=historialaprobacion.id)

                    template = get_template("aprobar_silabo/detallehistorialtarea.html")

                    json_content = template.render(data)
                    return JsonResponse({"result": "ok", 'html': json_content})
                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})
                    pass

            elif action == 'detallehistorialforo':
                try:
                    data['historialaprobacion'] = historialaprobacion = HistorialaprobacionForo.objects.get(pk=int(request.POST['id']))
                    data['historialdetforo'] = HistorialDetalleListaVerificacionForo.objects.filter(status=True, historialaprobacionforo=historialaprobacion.id)

                    template = get_template("aprobar_silabo/detallehistorialforo.html")

                    json_content = template.render(data)
                    return JsonResponse({"result": "ok", 'html': json_content})
                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})
                    pass

            elif action == 'detallehistorialtest':
                try:
                    data['historialaprobacion'] = historialaprobacion = HistorialaprobacionTest.objects.get(pk=int(request.POST['id']))
                    data['historialdettest'] = HistorialDetalleListaVerificacionTest.objects.filter(status=True, historialaprobaciontest=historialaprobacion.id)

                    template = get_template("aprobar_silabo/detallehistorialtest.html")

                    json_content = template.render(data)
                    return JsonResponse({"result": "ok", 'html': json_content})
                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})
                    pass

            elif action == 'detallehistorialguiaestudiante':
                try:
                    data['historialaprobacion'] = historialaprobacion = HistorialaprobacionGuiaEstudiante.objects.get(pk=int(request.POST['id']))
                    data['historialdetguiaest'] = HistorialDetalleListaVerificacionGuiaEstudiante.objects.filter(status=True, historialaprobacionguiaestudiante=historialaprobacion.id)

                    template = get_template("aprobar_silabo/detallehistorialguiaestudiante.html")

                    json_content = template.render(data)
                    return JsonResponse({"result": "ok", 'html': json_content})
                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})
                    pass

            elif action == 'detallehistorialguiadocente':
                try:
                    data['historialaprobacion'] = historialaprobacion = HistorialaprobacionGuiaDocente.objects.get(pk=int(request.POST['id']))
                    data['historialdetguiadoc'] = HistorialDetalleListaVerificacionGuiaDocente.objects.filter(status=True, historialaprobacionguiadocente=historialaprobacion.id)

                    template = get_template("aprobar_silabo/detallehistorialguiadocente.html")

                    json_content = template.render(data)
                    return JsonResponse({"result": "ok", 'html': json_content})
                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})
                    pass

            elif action == 'detallehistorialdiapositiva':
                try:
                    data['historialaprobacion'] = historialaprobacion = HistorialaprobacionDiapositiva.objects.get(pk=int(request.POST['id']))
                    data['historialdetdiap'] = HistorialDetalleListaVerificacionDiapositiva.objects.filter(status=True, historialaprobaciondiapositiva=historialaprobacion.id)

                    template = get_template("aprobar_silabo/detallehistorialdiapositiva.html")

                    json_content = template.render(data)
                    return JsonResponse({"result": "ok", 'html': json_content})
                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})
                    pass

            elif action == 'detallehistorialcompendio':
                try:
                    data['historialaprobacion'] = historialaprobacion = HistorialaprobacionCompendio.objects.get(pk=int(request.POST['id']))
                    data['historialdetcompendio'] = HistorialDetalleListaVerificacionCompendio.objects.filter(status=True, historialaprobacioncompendio=historialaprobacion.id)

                    template = get_template("aprobar_silabo/detallehistorialcompendio.html")

                    json_content = template.render(data)
                    return JsonResponse({"result": "ok", 'html': json_content})
                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})
                    pass

            elif action == 'detallehistorialmaterial':
                try:
                    data['historialaprobacion'] = historialaprobacion = HistorialaprobacionMaterial.objects.get(pk=int(request.POST['id']))
                    data['historialdetmaterial'] = HistorialDetalleListaVerificacionMaterialAdicional.objects.filter(status=True, historialaprobacionmaterial=historialaprobacion.id)

                    template = get_template("aprobar_silabo/detallehistorialmaterial.html")

                    json_content = template.render(data)
                    return JsonResponse({"result": "ok", 'html': json_content})
                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})
                    pass

            elif action == 'detallehistorialtareapractica':
                try:
                    data['historialaprobacion'] = historialaprobacion = HistorialaprobacionTareaPractica.objects.get(pk=int(request.POST['id']))
                    data['historialdettareap'] = HistorialDetalleListaVerificacionTareaPractica.objects.filter(status=True, historialaprobaciontareapractica=historialaprobacion.id)

                    template = get_template("aprobar_silabo/detallehistorialtareapractica.html")

                    json_content = template.render(data)
                    return JsonResponse({"result": "ok", 'html': json_content})
                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})
                    pass

            elif action == 'addplagiocompendio':
                try:
                    f = CompendioPlagioForm(request.POST, request.FILES)
                    if f.is_valid():
                        compendio = CompendioSilaboSemanal.objects.get(pk=request.POST['id'])
                        compendio.porcentaje = f.cleaned_data['porcentaje']
                        if 'archivo' in request.FILES:
                            newfilwcompendio_plagio = request.FILES['archivo']
                            if newfilwcompendio_plagio.size > 20971520:
                                return JsonResponse({"result": "bad", "mensaje": u"Error, archivo mayor a 20 Mb."})
                            else:
                                newfilesrubd = newfilwcompendio_plagio._name
                                ext = newfilesrubd[newfilesrubd.rfind("."):]
                                if ext == ".doc" or ext == ".docx" or ext == ".xls" or ext == ".xlsx" or ext == ".DOC" or ext == ".DOCX" or ext == ".XLS" or ext == ".XLSX" or ext == ".zip" or ext == ".rar" or ext == ".pdf" or ext == ".PDF":
                                    newfilwcompendio_plagio._name = generar_nombre("archivoplagio_", newfilwcompendio_plagio._name)
                                    compendio.archivoplagio = newfilwcompendio_plagio
                                else:
                                    return JsonResponse({"result": "bad",
                                                         "mensaje": u"Error, archivo de archivo plagio solo en .doc, docx, xls, xlsx, zip, rar, pdf"})

                        lista_formato = []
                        nombre_carrera = compendio.silabosemanal.silabo.materia.asignaturamalla.malla.carrera.nombre_completo()
                        if compendio.mis_formatos(periodo):
                            for format in compendio.mis_formatos(periodo):
                                lista_formato.append(format.nombre)
                        if lista_formato and 'word' in lista_formato and f.cleaned_data['estado'].id == 2:
                            id_estado = 5
                            lista_cor = []
                            lista_cor.append('sop_docencia_crai@unemi.edu.ec')
                            send_html_mail("SGA - REVISIÓN DE RECURSOS - %s" % nombre_carrera,
                                           "emails/sop_doc_crai_recursos.html",
                                           {'sistema': u'SGA - UNEMI',
                                            'fecha': datetime.now().date(),
                                            'hora': datetime.now().time(),
                                            'recurso': compendio,
                                            'nombrecarrera': nombre_carrera,
                                            'tipo': 1,
                                            't': miinstitucion()
                                            },
                                           lista_cor,
                                           [],
                                           cuenta=variable_valor('CUENTAS_CORREOS')[0]
                                           )
                        else:
                            id_estado = f.cleaned_data['estado'].id

                        compendio.estado_id = id_estado
                        compendio.save(request)
                        historial = HistorialaprobacionCompendio(compendio=compendio,
                                                                 estado=f.cleaned_data['estado'],
                                                                 observacion=f.cleaned_data['observacion'])
                        historial.save(request)
                        return JsonResponse({"result": "ok"})
                    else:
                        raise NameError('Error')
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

            elif action == 'addplagiocompendio_pregrado':
                try:
                    f = CompendioPlagioForm(request.POST, request.FILES)
                    lista_1 = json.loads(request.POST['lista_items2'])
                    if f.is_valid():
                        compendio = CompendioSilaboSemanal.objects.get(pk=request.POST['id'])
                        compendio.porcentaje = f.cleaned_data['porcentaje']
                        if 'archivo' in request.FILES:
                            newfilwcompendio_plagio = request.FILES['archivo']
                            if newfilwcompendio_plagio.size > 20971520:
                                return JsonResponse({"result": "bad", "mensaje": u"Error, archivo mayor a 20 Mb."})
                            else:
                                newfilesrubd = newfilwcompendio_plagio._name
                                ext = newfilesrubd[newfilesrubd.rfind("."):]
                                if ext == ".doc" or ext == ".docx" or ext == ".xls" or ext == ".xlsx" or ext == ".DOC" or ext == ".DOCX" or ext == ".XLS" or ext == ".XLSX" or ext == ".zip" or ext == ".rar" or ext == ".pdf" or ext == ".PDF":
                                    newfilwcompendio_plagio._name = generar_nombre("archivoplagio_", newfilwcompendio_plagio._name)
                                    compendio.archivoplagio = newfilwcompendio_plagio
                                else:
                                    return JsonResponse({"result": "bad",
                                                         "mensaje": u"Error, archivo de archivo plagio solo en .doc, docx, xls, xlsx, zip, rar, pdf"})

                        lista_formato = []
                        if compendio.mis_formatos(periodo):
                            for format in compendio.mis_formatos(periodo):
                                lista_formato.append(format.nombre)
                        if lista_formato and 'word' in lista_formato and f.cleaned_data['estado'].id == 2:
                            id_estado = 5
                            nombre_carrera = compendio.silabosemanal.silabo.materia.asignaturamalla.malla.carrera.nombre_completo()
                            lista_cor = []
                            lista_cor.append('sop_docencia_crai@unemi.edu.ec')
                            send_html_mail("SGA - REVISIÓN DE RECURSOS - %s" % nombre_carrera,
                                           "emails/sop_doc_crai_recursos.html",
                                           {'sistema': u'SGA - UNEMI',
                                            'fecha': datetime.now().date(),
                                            'hora': datetime.now().time(),
                                            'recurso': compendio,
                                            'nombrecarrera': nombre_carrera,
                                            'tipo': 1,
                                            't': miinstitucion()
                                            },
                                           lista_cor,
                                           [],
                                           cuenta=variable_valor('CUENTAS_CORREOS')[0]
                                           )
                        else:
                            id_estado = f.cleaned_data['estado'].id

                        compendio.estado_id = id_estado
                        compendio.save(request)
                        historial = HistorialaprobacionCompendio(compendio=compendio,
                                                                 estado=f.cleaned_data['estado'],
                                                                 observacion=f.cleaned_data['observacion'])
                        historial.save(request)

                        aux = False
                        excluir = []
                        for dato in lista_1:
                            lista = ListaVerificacion.objects.get(pk=int(dato['id']))
                            excluir.append(int(dato['id']))
                            historialdetallecompendio = HistorialDetalleListaVerificacionCompendio(
                                historialaprobacioncompendio=historial,
                                compendiosilabosemanal=compendio,
                                listaverificacion=lista,
                                observacion=dato['obs']
                            )
                            historialdetallecompendio.save(request)

                            # for lista in ListaVerificacion.objects.filter(status=True,tiporecurso=tarea.tiporecurso):
                            # if lista.id==int(dato['id']):
                            if not DetalleListaVerificacionCompendio.objects.filter(status=True,
                                                                                    compendiosilabosemanal=compendio,
                                                                                    listaverificacion=lista).exists():
                                det = DetalleListaVerificacionCompendio(
                                    compendiosilabosemanal=compendio,
                                    listaverificacion=lista,
                                    cumple=False, observacion=dato['obs']
                                )
                                det.save(request)
                            else:
                                det = DetalleListaVerificacionCompendio.objects.filter(status=True,
                                                                                       compendiosilabosemanal=compendio,
                                                                                       listaverificacion=lista)[0]
                                det.cumple = False
                                det.observacion = dato['obs']
                                det.save(request)

                        for lista in ListaVerificacion.objects.filter(status=True,
                                                                      tiporecurso=compendio.tiporecurso).exclude(
                            id__in=excluir):

                            if not DetalleListaVerificacionCompendio.objects.filter(status=True,
                                                                                    compendiosilabosemanal=compendio,
                                                                                    listaverificacion=lista).exists():
                                det = DetalleListaVerificacionCompendio(
                                    compendiosilabosemanal=compendio,
                                    listaverificacion=lista,
                                    cumple=True
                                )
                                det.save(request)
                            else:
                                # det=DetalleListaVerificacion.objects.filter(status=True,tareasilabosemanal=tarea, listaverificacion=lista)[0]
                                det = DetalleListaVerificacionCompendio.objects.get(status=True,
                                                                                    compendiosilabosemanal=compendio,
                                                                                    listaverificacion=lista)
                                det.cumple = True
                                det.observacion = ""
                                det.save(request)

                        return JsonResponse({"result": "ok"})
                    else:
                        raise NameError('Error')
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

            elif action == 'tareaestado_pregrado':
                try:
                    nombrerecurso = ""
                    estado = ""
                    semana = ""
                    nombredocente = ""
                    materia_nombre = ""
                    correo = None
                    id_codtipo = int(request.POST['id_codtipo'])
                    id_observacion = request.POST['id_observacion']
                    id_estadosolicitud = int(request.POST['id_estadosolicitud'])
                    if id_codtipo != 10:
                        tareas = json.loads(request.POST['tareas'])
                    # id_observaciones = request.POST['id_observaciones']
                    cuenta = CUENTAS_CORREOS[3][1]
                    if id_codtipo == 1:
                        tarea = TareaSilaboSemanal.objects.get(pk=int(request.POST['idcodigotarea']))
                        if tarea.rubricamoodle:
                            if not tarea.rubricamoodle.estado:
                                tarea.rubricamoodle.estado = True
                                tarea.rubricamoodle.save(request)

                                historial = RubricaMoodleHistorial(rubrica=tarea.rubricamoodle,
                                                                   observacion="APROBACIÓN AUTOMÁTICA AL APROBAR EL RECURSO",
                                                                   estado=2)
                                historial.save(request)
                        materia_nombre = tarea.silabosemanal.silabo.materia.nombre_mostrar_sin_profesor()
                        if id_estadosolicitud == 2:
                            # tarea.estado_id = 4
                            # tarea.save(request)
                            from Moodle_Funciones import CrearTareasMoodle
                            personacrea = Persona.objects.get(usuario_id=tarea.usuario_creacion_id, status=True)
                            value, msg = CrearTareasMoodle(tarea.id, personacrea)
                            if not value:
                                raise NameError(msg)
                            id_estadosolicitud = 4
                            historial = HistorialaprobacionTarea(tarea_id=int(request.POST['idcodigotarea']),
                                                                 estado_id=2,
                                                                 observacion=id_observacion)
                            historial.save(request)
                        else:
                            tarea.estado_id = id_estadosolicitud
                            tarea.save(request)
                        historial = HistorialaprobacionTarea(tarea_id=int(request.POST['idcodigotarea']),
                                                             estado_id=id_estadosolicitud,
                                                             observacion=id_observacion)
                        historial.save(request)
                        nombredocente = Persona.objects.get(usuario_id=tarea.usuario_creacion_id, status=True)

                        correo = nombredocente.lista_emails_envio()
                        if CoordinadorCarrera.objects.filter(
                                carrera=tarea.silabosemanal.silabo.materia.asignaturamalla.malla.carrera,
                                periodo=periodo, sede=1, tipo=3):
                            coordinadordecarrera = CoordinadorCarrera.objects.filter(
                                carrera=tarea.silabosemanal.silabo.materia.asignaturamalla.malla.carrera,
                                periodo=periodo, sede=1, tipo=3)[0]
                            correo = correo + coordinadordecarrera.persona.lista_emails_envio()
                        nombrerecurso = 'TAREA'
                        estado = tarea.estado.nombre
                        semana = tarea.silabosemanal.numsemana
                        aux = False
                        excluir = []
                        for dato in tareas:
                            lista = ListaVerificacion.objects.get(pk=int(dato['id']))
                            excluir.append(int(dato['id']))
                            historialdetalletarea = HistorialDetalleListaVerificacionTarea(
                                historialaprobaciontarea=historial,
                                tareasilabosemanal=tarea,
                                listaverificacion=lista,
                                observacion=dato['obs']
                            )
                            historialdetalletarea.save(request)
                            # for lista in ListaVerificacion.objects.filter(status=True,tiporecurso=tarea.tiporecurso):
                            # if lista.id==int(dato['id']):
                            if not DetalleListaVerificacionTarea.objects.filter(status=True, tareasilabosemanal=tarea, listaverificacion=lista).exists():
                                det = DetalleListaVerificacionTarea(
                                    tareasilabosemanal=tarea,
                                    listaverificacion=lista,
                                    cumple=False, observacion=dato['obs']
                                )
                                det.save(request)
                            else:
                                det = DetalleListaVerificacionTarea.objects.filter(status=True, tareasilabosemanal=tarea, listaverificacion=lista)[0]
                                det.cumple = False
                                det.observacion = dato['obs']
                                det.save(request)

                        for lista in ListaVerificacion.objects.filter(status=True, tiporecurso=tarea.tiporecurso).exclude(id__in=excluir):

                            if not DetalleListaVerificacionTarea.objects.filter(status=True, tareasilabosemanal=tarea, listaverificacion=lista).exists():
                                det = DetalleListaVerificacionTarea(
                                    tareasilabosemanal=tarea,
                                    listaverificacion=lista,
                                    cumple=True
                                )
                                det.save(request)
                            else:
                                # det=DetalleListaVerificacion.objects.filter(status=True,tareasilabosemanal=tarea, listaverificacion=lista)[0]
                                det = DetalleListaVerificacionTarea.objects.get(status=True, tareasilabosemanal=tarea, listaverificacion=lista)
                                det.cumple = True
                                det.observacion = ""
                                det.save(request)

                        log(u'Aprobo tarea: %s - %s' % (tarea, tarea.silabosemanal), request, "edit")
                    if id_codtipo == 2:
                        foro = ForoSilaboSemanal.objects.get(pk=int(request.POST['idcodigotarea']))
                        if foro.calificar:
                            if not foro.detallemodelo:
                                transaction.set_rollback(True)
                                return JsonResponse(
                                    {"result": "bad", "mensaje": u"No tiene configurado modelo de calificacion."})
                        materia_nombre = foro.silabosemanal.silabo.materia.nombre_mostrar_sin_profesor()
                        if id_estadosolicitud == 2:
                            # foro.estado_id = 4
                            # foro.save(request)
                            from Moodle_Funciones import CrearForosMoodle
                            personacrea = Persona.objects.get(usuario_id=foro.usuario_creacion_id, status=True)
                            value, msg = CrearForosMoodle(foro.id, personacrea)
                            if not value:
                                raise NameError(msg)
                            id_estadosolicitud = 4
                            historial = HistorialaprobacionForo(foro_id=int(request.POST['idcodigotarea']),
                                                                estado_id=2,
                                                                observacion=id_observacion)
                            historial.save(request)
                        else:
                            foro.estado_id = id_estadosolicitud
                            foro.save(request)
                        historial = HistorialaprobacionForo(foro_id=int(request.POST['idcodigotarea']),
                                                            estado_id=id_estadosolicitud,
                                                            observacion=id_observacion)
                        historial.save(request)
                        nombredocente = Persona.objects.get(usuario_id=foro.usuario_creacion_id, status=True)
                        correo = nombredocente.lista_emails_envio()
                        if CoordinadorCarrera.objects.filter(status=True,
                                                             carrera=foro.silabosemanal.silabo.materia.asignaturamalla.malla.carrera,
                                                             periodo=periodo, sede=1, tipo=3):
                            coordinadordecarrera = CoordinadorCarrera.objects.filter(status=True,
                                                                                     carrera=foro.silabosemanal.silabo.materia.asignaturamalla.malla.carrera,
                                                                                     periodo=periodo, sede=1, tipo=3)[0]
                            correo = correo + coordinadordecarrera.persona.lista_emails_envio()
                        nombrerecurso = 'FORO'
                        estado = foro.estado.nombre
                        semana = foro.silabosemanal.numsemana

                        aux = False
                        excluir = []
                        for dato in tareas:
                            lista = ListaVerificacion.objects.get(pk=int(dato['id']))
                            excluir.append(int(dato['id']))
                            historialdetalleforo = HistorialDetalleListaVerificacionForo(
                                historialaprobacionforo=historial,
                                forosilabosemanal=foro,
                                listaverificacion=lista,
                                observacion=dato['obs']
                            )
                            historialdetalleforo.save(request)
                            # for lista in ListaVerificacion.objects.filter(status=True,tiporecurso=tarea.tiporecurso):
                            # if lista.id==int(dato['id']):
                            if not DetalleListaVerificacionForo.objects.filter(status=True, forosilabosemanal=foro,
                                                                               listaverificacion=lista).exists():
                                det = DetalleListaVerificacionForo(
                                    forosilabosemanal=foro,
                                    listaverificacion=lista,
                                    cumple=False, observacion=dato['obs']
                                )
                                det.save(request)
                            else:
                                det = DetalleListaVerificacionForo.objects.filter(status=True, forosilabosemanal=foro,
                                                                                  listaverificacion=lista)[0]
                                det.cumple = False
                                det.observacion = dato['obs']
                                det.save(request)

                        for lista in ListaVerificacion.objects.filter(status=True, tiporecurso=foro.tiporecurso).exclude(id__in=excluir):

                            if not DetalleListaVerificacionForo.objects.filter(status=True, forosilabosemanal=foro,
                                                                               listaverificacion=lista).exists():
                                det = DetalleListaVerificacionForo(
                                    forosilabosemanal=foro,
                                    listaverificacion=lista,
                                    cumple=True
                                )
                                det.save(request)
                            else:
                                # det=DetalleListaVerificacion.objects.filter(status=True,tareasilabosemanal=tarea, listaverificacion=lista)[0]
                                det = DetalleListaVerificacionForo.objects.get(status=True, forosilabosemanal=foro,
                                                                               listaverificacion=lista)
                                det.cumple = True
                                det.observacion = ""
                                det.save(request)
                        log(u'Aprobo foro: %s - %s' % (foro, foro.silabosemanal), request, "edit")
                    if id_codtipo == 3:
                        nombrerecurso = 'TEST'
                        test = TestSilaboSemanal.objects.get(pk=int(request.POST['idcodigotarea']))
                        if test.calificar:
                            if not test.detallemodelo:
                                transaction.set_rollback(True)
                                return JsonResponse(
                                    {"result": "bad", "mensaje": u"No tiene configurado modelo de calificacion."})
                        materia_nombre = test.silabosemanal.silabo.materia.nombre_mostrar_sin_profesor()
                        if id_estadosolicitud == 2:
                            # test.estado_id = 4
                            # test.save(request)
                            personacrea = Persona.objects.get(usuario_id=test.usuario_creacion_id, status=True)
                            if test.silabosemanal.examen:
                                nombrerecurso = 'EXAMEN'
                                from Moodle_Funciones import CrearExamenMoodle
                                value, msg = CrearExamenMoodle(test.id, personacrea)
                                if not value:
                                    raise NameError(msg)
                            else:
                                from Moodle_Funciones import CrearTestMoodle
                                value, msg = CrearTestMoodle(test.id, personacrea)
                                if not value:
                                    raise NameError(msg)
                            id_estadosolicitud = 4
                            historial = HistorialaprobacionTest(test_id=int(request.POST['idcodigotarea']),
                                                                estado_id=2,
                                                                observacion=id_observacion)
                            historial.save(request)

                        else:
                            test.estado_id = id_estadosolicitud
                            test.save(request)
                        historial = HistorialaprobacionTest(test_id=int(request.POST['idcodigotarea']),
                                                            estado_id=id_estadosolicitud,
                                                            observacion=id_observacion)
                        historial.save(request)
                        nombredocente = Persona.objects.get(usuario_id=test.usuario_creacion_id, status=True)
                        correo = nombredocente.lista_emails_envio()
                        if CoordinadorCarrera.objects.filter(status=True,
                                                             carrera=test.silabosemanal.silabo.materia.asignaturamalla.malla.carrera,
                                                             periodo=periodo, sede=1, tipo=3):
                            coordinadordecarrera = CoordinadorCarrera.objects.filter(status=True,
                                                                                     carrera=test.silabosemanal.silabo.materia.asignaturamalla.malla.carrera,
                                                                                     periodo=periodo, sede=1, tipo=3)[0]
                            correo = correo + coordinadordecarrera.persona.lista_emails_envio()

                        estado = test.estado.nombre
                        semana = test.silabosemanal.numsemana

                        aux = False
                        excluir = []
                        for dato in tareas:
                            lista = ListaVerificacion.objects.get(pk=int(dato['id']))
                            excluir.append(int(dato['id']))
                            historialdetalletest = HistorialDetalleListaVerificacionTest(
                                historialaprobaciontest=historial,
                                testsilabosemanal=test,
                                listaverificacion=lista,
                                observacion=dato['obs']
                            )
                            historialdetalletest.save(request)
                            # for lista in ListaVerificacion.objects.filter(status=True,tiporecurso=tarea.tiporecurso):
                            # if lista.id==int(dato['id']):
                            if not DetalleListaVerificacionTest.objects.filter(status=True, testsilabosemanal=test,
                                                                               listaverificacion=lista).exists():
                                det = DetalleListaVerificacionTest(
                                    testsilabosemanal=test,
                                    listaverificacion=lista,
                                    cumple=False, observacion=dato['obs']
                                )
                                det.save(request)
                            else:
                                det = DetalleListaVerificacionTest.objects.filter(status=True, testsilabosemanal=test,
                                                                                  listaverificacion=lista)[0]
                                det.cumple = False
                                det.observacion = dato['obs']
                                det.save(request)

                        for lista in ListaVerificacion.objects.filter(status=True,
                                                                      tiporecurso=test.tiporecurso).exclude(
                            id__in=excluir):

                            if not DetalleListaVerificacionTest.objects.filter(status=True, testsilabosemanal=test,
                                                                               listaverificacion=lista).exists():
                                det = DetalleListaVerificacionTest(
                                    testsilabosemanal=test,
                                    listaverificacion=lista,
                                    cumple=True
                                )
                                det.save(request)
                            else:
                                # det=DetalleListaVerificacion.objects.filter(status=True,tareasilabosemanal=tarea, listaverificacion=lista)[0]
                                det = DetalleListaVerificacionTest.objects.get(status=True, testsilabosemanal=test,
                                                                               listaverificacion=lista)
                                det.cumple = True
                                det.observacion = ""
                                det.save(request)
                        log(u'Aprobo test: %s - %s' % (test, test.silabosemanal), request, "edit")
                    if id_codtipo == 4:
                        guiaestudiante = GuiaEstudianteSilaboSemanal.objects.get(pk=int(request.POST['idcodigotarea']))
                        lista_formato = []
                        if guiaestudiante.mis_formatos(periodo):
                            for format in guiaestudiante.mis_formatos(periodo):
                                lista_formato.append(format.nombre)
                        materia_nombre = guiaestudiante.silabosemanal.silabo.materia.nombre_mostrar_sin_profesor()
                        if lista_formato and 'word' in lista_formato and id_estadosolicitud == 2:
                            guiaestudiante.estado_id = 5
                            guiaestudiante.save(request)
                            lista_cor = []
                            nombre_carrera = guiaestudiante.silabosemanal.silabo.materia.asignaturamalla.malla.carrera.nombre_completo()
                            lista_cor.append('sop_docencia_crai@unemi.edu.ec')
                            send_html_mail("SGA - REVISIÓN DE RECURSOS - %s" % nombre_carrera,
                                           "emails/sop_doc_crai_recursos.html",
                                           {'sistema': u'SGA - UNEMI',
                                            'fecha': datetime.now().date(),
                                            'hora': datetime.now().time(),
                                            'recurso': guiaestudiante,
                                            'tipo': 2,
                                            'nombrecarrera': nombre_carrera,
                                            't': miinstitucion()
                                            },
                                           lista_cor,
                                           [],
                                           cuenta=variable_valor('CUENTAS_CORREOS')[0]
                                           )
                        else:
                            guiaestudiante.estado_id = id_estadosolicitud
                            guiaestudiante.save(request)
                            materia = guiaestudiante.silabosemanal.silabo.materia
                            materia.actualizarhtml = True
                            materia.save()
                        historial = HistorialaprobacionGuiaEstudiante(
                            guiaestudiante_id=int(request.POST['idcodigotarea']),
                            estado_id=id_estadosolicitud,
                            observacion=id_observacion)
                        historial.save(request)
                        nombredocente = Persona.objects.get(usuario_id=guiaestudiante.usuario_creacion_id, status=True)
                        correo = nombredocente.lista_emails_envio()
                        if CoordinadorCarrera.objects.filter(status=True,
                                                             carrera=guiaestudiante.silabosemanal.silabo.materia.asignaturamalla.malla.carrera,
                                                             periodo=periodo, sede=1, tipo=3):
                            coordinadordecarrera = CoordinadorCarrera.objects.filter(status=True,
                                                                                     carrera=guiaestudiante.silabosemanal.silabo.materia.asignaturamalla.malla.carrera,
                                                                                     periodo=periodo, sede=1, tipo=3)[0]
                            correo = correo + coordinadordecarrera.persona.lista_emails_envio()
                        nombrerecurso = 'GUIA ESTUDIANTIL'
                        estado = guiaestudiante.estado.nombre
                        semana = guiaestudiante.silabosemanal.numsemana

                        aux = False
                        excluir = []
                        for dato in tareas:
                            lista = ListaVerificacion.objects.get(pk=int(dato['id']))
                            excluir.append(int(dato['id']))
                            historialdetalleguiaestudiante = HistorialDetalleListaVerificacionGuiaEstudiante(
                                historialaprobacionguiaestudiante=historial,
                                guiaestudiantesilabosemanal=guiaestudiante,
                                listaverificacion=lista,
                                observacion=dato['obs']
                            )
                            historialdetalleguiaestudiante.save(request)
                            # for lista in ListaVerificacion.objects.filter(status=True,tiporecurso=tarea.tiporecurso):
                            # if lista.id==int(dato['id']):
                            if not DetalleListaVerificacionGuiaEstudiante.objects.filter(status=True, guiaestudiantesilabosemanal=guiaestudiante,
                                                                                         listaverificacion=lista).exists():
                                det = DetalleListaVerificacionGuiaEstudiante(
                                    guiaestudiantesilabosemanal=guiaestudiante,
                                    listaverificacion=lista,
                                    cumple=False, observacion=dato['obs']
                                )
                                det.save(request)
                            else:
                                det = DetalleListaVerificacionGuiaEstudiante.objects.filter(status=True, guiaestudiantesilabosemanal=guiaestudiante,
                                                                                            listaverificacion=lista)[0]
                                det.cumple = False
                                det.observacion = dato['obs']
                                det.save(request)

                        for lista in ListaVerificacion.objects.filter(status=True,
                                                                      tiporecurso=guiaestudiante.tiporecurso).exclude(
                            id__in=excluir):

                            if not DetalleListaVerificacionGuiaEstudiante.objects.filter(status=True, guiaestudiantesilabosemanal=guiaestudiante,
                                                                                         listaverificacion=lista).exists():
                                det = DetalleListaVerificacionGuiaEstudiante(
                                    guiaestudiantesilabosemanal=guiaestudiante,
                                    listaverificacion=lista,
                                    cumple=True
                                )
                                det.save(request)
                            else:
                                # det=DetalleListaVerificacion.objects.filter(status=True,tareasilabosemanal=tarea, listaverificacion=lista)[0]
                                det = DetalleListaVerificacionGuiaEstudiante.objects.get(status=True, guiaestudiantesilabosemanal=guiaestudiante,
                                                                                         listaverificacion=lista)
                                det.cumple = True
                                det.observacion = ""
                                det.save(request)
                        log(u'Aprobo guia de estudiante: %s - %s' % (guiaestudiante, guiaestudiante.silabosemanal), request, "edit")
                    if id_codtipo == 5:
                        guiadocente = GuiaDocenteSilaboSemanal.objects.get(pk=int(request.POST['idcodigotarea']))
                        guiadocente.estado_id = id_estadosolicitud
                        guiadocente.save(request)
                        materia_nombre = guiadocente.silabosemanal.silabo.materia.nombre_mostrar_sin_profesor()
                        materia = guiadocente.silabosemanal.silabo.materia
                        materia.actualizarhtml = True
                        materia.save()
                        historial = HistorialaprobacionGuiaDocente(guiadocente_id=int(request.POST['idcodigotarea']),
                                                                   estado_id=id_estadosolicitud,
                                                                   observacion=id_observacion)
                        historial.save(request)
                        nombredocente = Persona.objects.get(usuario_id=guiadocente.usuario_creacion_id, status=True)
                        correo = nombredocente.lista_emails_envio()
                        if CoordinadorCarrera.objects.filter(status=True,
                                                             carrera=guiadocente.silabosemanal.silabo.materia.asignaturamalla.malla.carrera,
                                                             periodo=periodo, sede=1, tipo=3):
                            coordinadordecarrera = CoordinadorCarrera.objects.filter(status=True,
                                                                                     carrera=guiadocente.silabosemanal.silabo.materia.asignaturamalla.malla.carrera,
                                                                                     periodo=periodo, sede=1, tipo=3)[0]
                            correo = correo + coordinadordecarrera.persona.lista_emails_envio()
                        nombrerecurso = 'GUIA DOCENTE'
                        estado = guiadocente.estado.nombre
                        semana = guiadocente.silabosemanal.numsemana

                        aux = False
                        excluir = []
                        for dato in tareas:
                            lista = ListaVerificacion.objects.get(pk=int(dato['id']))
                            excluir.append(int(dato['id']))
                            historialdetalleguiadocente = HistorialDetalleListaVerificacionGuiaDocente(
                                historialaprobacionguiadocente=historial,
                                guiadocentesilabosemanal=guiadocente,
                                listaverificacion=lista,
                                observacion=dato['obs']
                            )
                            historialdetalleguiadocente.save(request)
                            # for lista in ListaVerificacion.objects.filter(status=True,tiporecurso=tarea.tiporecurso):
                            # if lista.id==int(dato['id']):
                            if not DetalleListaVerificacionGuiaDocente.objects.filter(status=True, guiadocentesilabosemanal=guiadocente,
                                                                                      listaverificacion=lista).exists():
                                det = DetalleListaVerificacionGuiaDocente(
                                    guiadocentesilabosemanal=guiadocente,
                                    listaverificacion=lista,
                                    cumple=False, observacion=dato['obs']
                                )
                                det.save(request)
                            else:
                                det = DetalleListaVerificacionGuiaDocente.objects.filter(status=True, guiadocentesilabosemanal=guiadocente,
                                                                                         listaverificacion=lista)[0]
                                det.cumple = False
                                det.observacion = dato['obs']
                                det.save(request)

                        for lista in ListaVerificacion.objects.filter(status=True,
                                                                      tiporecurso=guiadocente.tiporecurso).exclude(
                            id__in=excluir):

                            if not DetalleListaVerificacionGuiaDocente.objects.filter(status=True, guiadocentesilabosemanal=guiadocente,
                                                                                      listaverificacion=lista).exists():
                                det = DetalleListaVerificacionGuiaDocente(
                                    guiadocentesilabosemanal=guiadocente,
                                    listaverificacion=lista,
                                    cumple=True
                                )
                                det.save(request)
                            else:
                                # det=DetalleListaVerificacion.objects.filter(status=True,tareasilabosemanal=tarea, listaverificacion=lista)[0]
                                det = DetalleListaVerificacionGuiaDocente.objects.get(status=True, guiadocentesilabosemanal=guiadocente,
                                                                                      listaverificacion=lista)
                                det.cumple = True
                                det.observacion = ""
                                det.save(request)
                        log(u'Aprobo guia de docente: %s - %s' % (guiadocente, guiadocente.silabosemanal), request, "edit")
                    if id_codtipo == 6:
                        diapositiva = DiapositivaSilaboSemanal.objects.get(pk=int(request.POST['idcodigotarea']))
                        lista_formato = []
                        materia_nombre = diapositiva.silabosemanal.silabo.materia.nombre_mostrar_sin_profesor()
                        if diapositiva.mis_formatos(periodo):
                            for format in diapositiva.mis_formatos(periodo):
                                lista_formato.append(format.nombre)
                        if lista_formato and 'word' in lista_formato and id_estadosolicitud == 2:
                            diapositiva.estado_id = 5
                            diapositiva.save(request)
                            # correo
                        else:
                            if id_estadosolicitud == 2:
                                # diapositiva.estado_id = 4
                                # diapositiva.save(request)

                                from Moodle_Funciones import CrearRecursoMoodle
                                personacrea = Persona.objects.get(usuario_id=diapositiva.usuario_creacion_id, status=True)
                                value, msg = CrearRecursoMoodle(diapositiva.id, personacrea)
                                if not value:
                                    raise NameError(msg)
                            else:
                                diapositiva.estado_id = id_estadosolicitud
                                diapositiva.save(request)

                        historial = HistorialaprobacionDiapositiva(diapositiva_id=int(request.POST['idcodigotarea']),
                                                                   estado_id=id_estadosolicitud,
                                                                   observacion=id_observacion)
                        historial.save(request)
                        nombredocente = Persona.objects.get(usuario_id=diapositiva.usuario_creacion_id, status=True)
                        correo = nombredocente.lista_emails_envio()
                        if CoordinadorCarrera.objects.filter(status=True,
                                                             carrera=diapositiva.silabosemanal.silabo.materia.asignaturamalla.malla.carrera,
                                                             periodo=periodo, sede=1, tipo=3):
                            coordinadordecarrera = CoordinadorCarrera.objects.filter(status=True,
                                                                                     carrera=diapositiva.silabosemanal.silabo.materia.asignaturamalla.malla.carrera,
                                                                                     periodo=periodo, sede=1, tipo=3)[0]
                            correo = correo + coordinadordecarrera.persona.lista_emails_envio()
                        nombrerecurso = 'DIAPOSITIVA'
                        estado = diapositiva.estado.nombre
                        semana = diapositiva.silabosemanal.numsemana

                        aux = False
                        excluir = []
                        for dato in tareas:
                            lista = ListaVerificacion.objects.get(pk=int(dato['id']))
                            excluir.append(int(dato['id']))
                            historialdetallediapositiva = HistorialDetalleListaVerificacionDiapositiva(
                                historialaprobaciondiapositiva=historial,
                                diapositivasilabosemanal=diapositiva,
                                listaverificacion=lista,
                                observacion=dato['obs']
                            )
                            historialdetallediapositiva.save(request)
                            # for lista in ListaVerificacion.objects.filter(status=True,tiporecurso=tarea.tiporecurso):
                            # if lista.id==int(dato['id']):
                            if not DetalleListaVerificacionDiapositiva.objects.filter(status=True, diapositivasilabosemanal=diapositiva,
                                                                                      listaverificacion=lista).exists():
                                det = DetalleListaVerificacionDiapositiva(
                                    diapositivasilabosemanal=diapositiva,
                                    listaverificacion=lista,
                                    cumple=False, observacion=dato['obs']
                                )
                                det.save(request)
                            else:
                                det = DetalleListaVerificacionDiapositiva.objects.filter(status=True, diapositivasilabosemanal=diapositiva,
                                                                                         listaverificacion=lista)[0]
                                det.cumple = False
                                det.observacion = dato['obs']
                                det.save(request)

                        for lista in ListaVerificacion.objects.filter(status=True,
                                                                      tiporecurso=diapositiva.tiporecurso).exclude(
                            id__in=excluir):

                            if not DetalleListaVerificacionDiapositiva.objects.filter(status=True, diapositivasilabosemanal=diapositiva,
                                                                                      listaverificacion=lista).exists():
                                det = DetalleListaVerificacionDiapositiva(
                                    diapositivasilabosemanal=diapositiva,
                                    listaverificacion=lista,
                                    cumple=True
                                )
                                det.save(request)
                            else:
                                # det=DetalleListaVerificacion.objects.filter(status=True,tareasilabosemanal=tarea, listaverificacion=lista)[0]
                                det = DetalleListaVerificacionDiapositiva.objects.get(status=True, diapositivasilabosemanal=diapositiva,
                                                                                      listaverificacion=lista)
                                det.cumple = True
                                det.observacion = ""
                                det.save(request)
                        log(u'Aprobo presentación: %s - %s' % (diapositiva, diapositiva.silabosemanal), request, "edit")
                    if id_codtipo == 7:
                        compendio = CompendioSilaboSemanal.objects.get(pk=int(request.POST['idcodigotarea']))
                        materia_nombre = compendio.silabosemanal.silabo.materia.nombre_mostrar_sin_profesor()
                        lista_formato = []
                        if compendio.mis_formatos(periodo):
                            for format in compendio.mis_formatos(periodo):
                                lista_formato.append(format.nombre)
                        if lista_formato and 'word' in lista_formato and id_estadosolicitud == 2:
                            compendio.estado_id = 5
                            compendio.save(request)
                            lista_cor = []
                            nombre_carrera = guiaestudiante.silabosemanal.silabo.materia.asignaturamalla.malla.carrera.nombre_completo()
                            lista_cor.append('sop_docencia_crai@unemi.edu.ec')
                            send_html_mail("SGA - REVISIÓN DE RECURSOS - %s" % nombre_carrera,
                                           "emails/sop_doc_crai_recursos.html",
                                           {'sistema': u'SGA - UNEMI',
                                            'fecha': datetime.now().date(),
                                            'hora': datetime.now().time(),
                                            'recurso': compendio,
                                            'tipo': 2,
                                            'nombrecarrera': nombre_carrera,
                                            't': miinstitucion()
                                            },
                                           lista_cor,
                                           [],
                                           cuenta=variable_valor('CUENTAS_CORREOS')[0]
                                           )
                        else:
                            compendio.estado_id = id_estadosolicitud
                            compendio.save(request)
                            materia = compendio.silabosemanal.silabo.materia
                            materia.actualizarhtml = True
                            materia.save()
                        historial = HistorialaprobacionCompendio(compendio_id=int(request.POST['idcodigotarea']),
                                                                 estado_id=id_estadosolicitud,
                                                                 observacion=id_observacion)
                        historial.save(request)
                        nombredocente = Persona.objects.get(usuario_id=compendio.usuario_creacion_id, status=True)
                        correo = nombredocente.lista_emails_envio()
                        if CoordinadorCarrera.objects.filter(status=True,
                                                             carrera=compendio.silabosemanal.silabo.materia.asignaturamalla.malla.carrera,
                                                             periodo=periodo, sede=1, tipo=3):
                            coordinadordecarrera = CoordinadorCarrera.objects.filter(status=True,
                                                                                     carrera=compendio.silabosemanal.silabo.materia.asignaturamalla.malla.carrera,
                                                                                     periodo=periodo, sede=1, tipo=3)[0]
                            correo = correo + coordinadordecarrera.persona.lista_emails_envio()
                        nombrerecurso = 'COMPENDIO'
                        estado = compendio.estado.nombre
                        semana = compendio.silabosemanal.numsemana

                        aux = False
                        excluir = []
                        for dato in tareas:
                            lista = ListaVerificacion.objects.get(pk=int(dato['id']))
                            excluir.append(int(dato['id']))
                            historialdetallecompendio = HistorialDetalleListaVerificacionCompendio(
                                historialaprobacioncompendio=historial,
                                compendiosilabosemanal=compendio,
                                listaverificacion=lista,
                                observacion=dato['obs']
                            )
                            historialdetallecompendio.save(request)
                            # for lista in ListaVerificacion.objects.filter(status=True,tiporecurso=tarea.tiporecurso):
                            # if lista.id==int(dato['id']):
                            if not DetalleListaVerificacionCompendio.objects.filter(status=True,
                                                                                    compendiosilabosemanal=compendio,
                                                                                    listaverificacion=lista).exists():
                                det = DetalleListaVerificacionCompendio(
                                    compendiosilabosemanal=compendio,
                                    listaverificacion=lista,
                                    cumple=False, observacion=dato['obs']
                                )
                                det.save(request)
                            else:
                                det = DetalleListaVerificacionCompendio.objects.filter(status=True,
                                                                                       compendiosilabosemanal=compendio,
                                                                                       listaverificacion=lista)[0]
                                det.cumple = False
                                det.observacion = dato['obs']
                                det.save(request)

                        for lista in ListaVerificacion.objects.filter(status=True,
                                                                      tiporecurso=compendio.tiporecurso).exclude(
                            id__in=excluir):

                            if not DetalleListaVerificacionCompendio.objects.filter(status=True,
                                                                                    compendiosilabosemanal=compendio,
                                                                                    listaverificacion=lista).exists():
                                det = DetalleListaVerificacionCompendio(
                                    compendiosilabosemanal=compendio,
                                    listaverificacion=lista,
                                    cumple=True
                                )
                                det.save(request)
                            else:
                                # det=DetalleListaVerificacion.objects.filter(status=True,tareasilabosemanal=tarea, listaverificacion=lista)[0]
                                det = DetalleListaVerificacionCompendio.objects.get(status=True,
                                                                                    compendiosilabosemanal=compendio,
                                                                                    listaverificacion=lista)
                                det.cumple = True
                                det.observacion = ""
                                det.save(request)
                        log(u'Aprobo compendio: %s - %s' % (compendio, compendio.silabosemanal), request, "edit")
                    if id_codtipo == 8:
                        material = MaterialAdicionalSilaboSemanal.objects.get(pk=int(request.POST['idcodigotarea']))
                        material.estado_id = id_estadosolicitud
                        material.save(request)
                        materia_nombre = material.silabosemanal.silabo.materia.nombre_mostrar_sin_profesor()
                        if id_estadosolicitud == 2:
                            # material.estado_id = 4
                            # material.save(request)
                            from Moodle_Funciones import CrearMaterialesMoodle
                            personacrea = Persona.objects.get(usuario_id=material.usuario_creacion_id, status=True)
                            value, msg = CrearMaterialesMoodle(material.id, personacrea)
                            if not value:
                                raise NameError(msg)
                            id_estadosolicitud = 4
                            historial = HistorialaprobacionMaterial(material_id=int(request.POST['idcodigotarea']),
                                                                    estado_id=2,
                                                                    observacion=id_observacion)
                            historial.save(request)

                        historial = HistorialaprobacionMaterial(material_id=int(request.POST['idcodigotarea']),
                                                                estado_id=id_estadosolicitud,
                                                                observacion=id_observacion)
                        historial.save(request)
                        nombredocente = Persona.objects.get(usuario_id=material.usuario_creacion_id, status=True)
                        correo = nombredocente.lista_emails_envio()
                        if CoordinadorCarrera.objects.filter(status=True,
                                                             carrera=material.silabosemanal.silabo.materia.asignaturamalla.malla.carrera,
                                                             periodo=periodo, sede=1, tipo=3):
                            coordinadordecarrera = CoordinadorCarrera.objects.filter(status=True,
                                                                                     carrera=material.silabosemanal.silabo.materia.asignaturamalla.malla.carrera,
                                                                                     periodo=periodo, sede=1, tipo=3)[0]
                            correo = correo + coordinadordecarrera.persona.lista_emails_envio()
                        nombrerecurso = 'MATERIAL COMPLEMENTARIO'
                        estado = material.estado.nombre
                        semana = material.silabosemanal.numsemana

                        aux = False
                        excluir = []
                        for dato in tareas:
                            lista = ListaVerificacion.objects.get(pk=int(dato['id']))
                            excluir.append(int(dato['id']))
                            historialdetallematerialadicional = HistorialDetalleListaVerificacionMaterialAdicional(
                                historialaprobacionmaterial=historial,
                                materialadicionalsilabosemanal=material,
                                listaverificacion=lista,
                                observacion=dato['obs']
                            )
                            historialdetallematerialadicional.save(request)
                            # for lista in ListaVerificacion.objects.filter(status=True,tiporecurso=tarea.tiporecurso):
                            # if lista.id==int(dato['id']):
                            if not DetalleListaVerificacionMaterialAdicional.objects.filter(status=True,
                                                                                            materialadicionalsilabosemanal=material,
                                                                                            listaverificacion=lista).exists():
                                det = DetalleListaVerificacionMaterialAdicional(
                                    materialadicionalsilabosemanal=material,
                                    listaverificacion=lista,
                                    cumple=False, observacion=dato['obs']
                                )
                                det.save(request)
                            else:
                                det = DetalleListaVerificacionMaterialAdicional.objects.filter(status=True,
                                                                                               materialadicionalsilabosemanal=material,
                                                                                               listaverificacion=lista)[0]
                                det.cumple = False
                                det.observacion = dato['obs']
                                det.save(request)

                        for lista in ListaVerificacion.objects.filter(status=True,
                                                                      tiporecurso=material.tiporecursos).exclude(
                            id__in=excluir):

                            if not DetalleListaVerificacionMaterialAdicional.objects.filter(status=True,
                                                                                            materialadicionalsilabosemanal=material,
                                                                                            listaverificacion=lista).exists():
                                det = DetalleListaVerificacionMaterialAdicional(
                                    materialadicionalsilabosemanal=material,
                                    listaverificacion=lista,
                                    cumple=True
                                )
                                det.save(request)
                            else:
                                # det=DetalleListaVerificacion.objects.filter(status=True,tareasilabosemanal=tarea, listaverificacion=lista)[0]
                                det = DetalleListaVerificacionMaterialAdicional.objects.get(status=True,
                                                                                            materialadicionalsilabosemanal=material,
                                                                                            listaverificacion=lista)
                                det.cumple = True
                                det.observacion = ""
                                det.save(request)
                        log(u'Aprobo material adicional: %s - %s' % (material, material.silabosemanal), request, "edit")
                    if id_codtipo == 9:
                        tareapractica = TareaPracticaSilaboSemanal.objects.get(pk=int(request.POST['idcodigotarea']))
                        materia_nombre = tareapractica.silabosemanal.silabo.materia.nombre_mostrar_sin_profesor()
                        if tareapractica.rubricamoodle:
                            if not tareapractica.rubricamoodle.estado:
                                tareapractica.rubricamoodle.estado = True
                                tareapractica.rubricamoodle.save(request)

                                historial = RubricaMoodleHistorial(rubrica=tareapractica.rubricamoodle,
                                                                   observacion="APROBACIÓN AUTOMÁTICA AL APROBAR EL RECURSO",
                                                                   estado=2)
                                historial.save(request)
                        if id_estadosolicitud == 2:
                            # tareapractica.estado_id = 4
                            # tareapractica.save(request)
                            from Moodle_Funciones import CrearPracticasTareasMoodle
                            personacrea = Persona.objects.get(usuario_id=tareapractica.usuario_creacion_id, status=True)
                            value, msg = CrearPracticasTareasMoodle(tareapractica.id, personacrea)
                            if not value:
                                raise NameError(msg)
                            id_estadosolicitud = 4
                            historial = HistorialaprobacionTareaPractica(
                                tareapractica_id=int(request.POST['idcodigotarea']),
                                estado_id=2,
                                observacion=id_observacion)
                            historial.save(request)

                        else:
                            tareapractica.estado_id = id_estadosolicitud
                            tareapractica.save(request)
                        historial = HistorialaprobacionTareaPractica(
                            tareapractica_id=int(request.POST['idcodigotarea']),
                            estado_id=id_estadosolicitud,
                            observacion=id_observacion)
                        historial.save(request)
                        nombredocente = Persona.objects.get(usuario_id=tareapractica.usuario_creacion_id, status=True)

                        correo = nombredocente.lista_emails_envio()
                        if CoordinadorCarrera.objects.filter(
                                carrera=tareapractica.silabosemanal.silabo.materia.asignaturamalla.malla.carrera,
                                periodo=periodo, sede=1, tipo=3):
                            coordinadordecarrera = CoordinadorCarrera.objects.filter(
                                carrera=tareapractica.silabosemanal.silabo.materia.asignaturamalla.malla.carrera,
                                periodo=periodo, sede=1, tipo=3)[0]
                            correo = correo + coordinadordecarrera.persona.lista_emails_envio()
                        nombrerecurso = 'TAREA'
                        estado = tareapractica.estado.nombre
                        semana = tareapractica.silabosemanal.numsemana

                        aux = False
                        excluir = []
                        for dato in tareas:
                            lista = ListaVerificacion.objects.get(pk=int(dato['id']))
                            excluir.append(int(dato['id']))
                            historialdetalletareapractica = HistorialDetalleListaVerificacionTareaPractica(
                                historialaprobaciontareapractica=historial,
                                tareapracticasilabosemanal=tareapractica,
                                listaverificacion=lista,
                                observacion=dato['obs']
                            )
                            historialdetalletareapractica.save(request)
                            # for lista in ListaVerificacion.objects.filter(status=True,tiporecurso=tarea.tiporecurso):
                            # if lista.id==int(dato['id']):
                            if not DetalleListaVerificacionTareaPractica.objects.filter(status=True,
                                                                                        tareapracticasilabosemanal=tareapractica,
                                                                                        listaverificacion=lista).exists():
                                det = DetalleListaVerificacionTareaPractica(
                                    tareapracticasilabosemanal=tareapractica,
                                    listaverificacion=lista,
                                    cumple=False, observacion=dato['obs']
                                )
                                det.save(request)
                            else:
                                det = DetalleListaVerificacionTareaPractica.objects.filter(status=True,
                                                                                           tareapracticasilabosemanal=tareapractica,
                                                                                           listaverificacion=lista)[
                                    0]
                                det.cumple = False
                                det.observacion = dato['obs']
                                det.save(request)

                        for lista in ListaVerificacion.objects.filter(status=True,
                                                                      tiporecurso=tareapractica.tiporecurso).exclude(
                            id__in=excluir):

                            if not DetalleListaVerificacionTareaPractica.objects.filter(status=True,
                                                                                        tareapracticasilabosemanal=tareapractica,
                                                                                        listaverificacion=lista).exists():
                                det = DetalleListaVerificacionTareaPractica(
                                    tareapracticasilabosemanal=tareapractica,
                                    listaverificacion=lista,
                                    cumple=True
                                )
                                det.save(request)
                            else:
                                # det=DetalleListaVerificacion.objects.filter(status=True,tareasilabosemanal=tarea, listaverificacion=lista)[0]
                                det = DetalleListaVerificacionTareaPractica.objects.get(status=True,
                                                                                        tareapracticasilabosemanal=tareapractica,
                                                                                        listaverificacion=lista)
                                det.cumple = True
                                det.observacion = ""
                                det.save(request)
                        log(u'Aprobo tarea practica: %s - %s' % (tareapractica, tareapractica.silabosemanal), request, "edit")
                    if id_codtipo == 10:
                        video = VideoMagistralSilaboSemanal.objects.get(id=int(request.POST['idcodigotarea']))
                        materia_nombre = video.silabosemanal.silabo.materia.nombre_mostrar_sin_profesor()
                        if id_estadosolicitud == 2:
                            video.presentacion_validado = True
                            video.save(request)
                            nombrerecurso = 'VIDEO MAGISTRAL'
                            list_correo = []
                            list_correo.append('sop_docencia_crai@unemi.edu.ec')
                            semana = video.silabosemanal.numsemana
                            nombre_carrera = video.silabosemanal.silabo.materia.asignaturamalla.malla.carrera.nombre_completo()
                            cuenta = CUENTAS_CORREOS[0][1]
                            send_html_mail("SGA - REVISIÓN DE VIDEOS - %s" % nombre_carrera, "emails/ingresovideomagistral.html",
                                           {'sistema': request.session['nombresistema'], 'nombredocente': video.silabosemanal.silabo.materia.profesor_principal(),
                                            'nombrerecurso': nombrerecurso, 'semana': semana, 'nombrecarrera': nombre_carrera,
                                            'vidmagistral': video, 't': miinstitucion()}, list_correo, [],
                                           cuenta=cuenta)
                        elif id_estadosolicitud == 3:
                            video.estado_id = 3
                            video.presentacion_validado = False
                            video.save(request)

                        log(u'Aprobo video magistral: %s - %s' % (video, video.silabosemanal), request, "edit")
                    if correo:
                        # correo.append('jplacesc@unemi.edu.ec')
                        # send_html_mail("SGA - PLANIFICACIÓN DE RECURSOS.", "emails/recursoaprobacionindividual.html",
                        #                {'sistema': request.session['nombresistema'], 'nombredocente': nombredocente,
                        #                 'nombrerecurso': nombrerecurso, 'estado': estado, 'semana': semana,
                        #                 't': miinstitucion()}, correo, [], coneccion=coneccion)

                        send_html_mail("SGA - PLANIFICACIÓN DE RECURSOS.",
                                       "emails/recursoaprobacionindividual.html",
                                       {'sistema': u'SGA - UNEMI',
                                        'nombredocente': nombredocente,
                                        'nombrerecurso': nombrerecurso,
                                        'estado': estado,
                                        'semana': semana,
                                        'materia': materia_nombre,
                                        't': miinstitucion()
                                        },
                                       correo,
                                       [],
                                       cuenta=cuenta
                                       )

                    return JsonResponse({"result": "ok"})
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos. %s " % ex})

            elif action == 'tareaestado':
                try:
                    id_codtipo = int(request.POST['id_codtipo'])
                    id_observacion = request.POST['id_observacion']
                    id_estadosolicitud = int(request.POST['id_estadosolicitud'])
                    # tareas = json.loads(request.POST['tareas'])
                    # id_observaciones = request.POST['id_observaciones']
                    cuenta = CUENTAS_CORREOS[3][1]
                    if id_codtipo == 1:
                        tarea = TareaSilaboSemanal.objects.get(pk=int(request.POST['idcodigotarea']))
                        if id_estadosolicitud == 2:

                            from Moodle_Funciones import CrearTareasMoodle
                            personacrea = Persona.objects.get(usuario_id=tarea.usuario_creacion_id, status=True)
                            value, msg = CrearTareasMoodle(tarea.id, personacrea)
                            if not value:
                                raise NameError(msg)
                            id_estadosolicitud = 4
                            historial = HistorialaprobacionTarea(tarea_id=int(request.POST['idcodigotarea']),
                                                                 estado_id=2,
                                                                 observacion=id_observacion)
                            historial.save(request)
                        else:
                            tarea.estado_id = id_estadosolicitud
                            tarea.save(request)
                        historial = HistorialaprobacionTarea(tarea_id=int(request.POST['idcodigotarea']),
                                                             estado_id=id_estadosolicitud,
                                                             observacion=id_observacion)
                        historial.save(request)
                        nombredocente = Persona.objects.get(usuario_id=tarea.usuario_creacion_id, status=True)

                        correo = nombredocente.lista_emails_envio()
                        if CoordinadorCarrera.objects.filter(
                                carrera=tarea.silabosemanal.silabo.materia.asignaturamalla.malla.carrera,
                                periodo=periodo, sede=1, tipo=3):
                            coordinadordecarrera = CoordinadorCarrera.objects.filter(
                                carrera=tarea.silabosemanal.silabo.materia.asignaturamalla.malla.carrera,
                                periodo=periodo, sede=1, tipo=3)[0]
                            correo = correo + coordinadordecarrera.persona.lista_emails_envio()
                        nombrerecurso = 'TAREA'
                        estado = tarea.estado.nombre
                        semana = tarea.silabosemanal.numsemana

                    if id_codtipo == 2:
                        foro = ForoSilaboSemanal.objects.get(pk=int(request.POST['idcodigotarea']))
                        if foro.calificar:
                            if not foro.detallemodelo:
                                transaction.set_rollback(True)
                                return JsonResponse(
                                    {"result": "bad", "mensaje": u"No tiene configurado modelo de calificacion."})
                        if id_estadosolicitud == 2:

                            from Moodle_Funciones import CrearForosMoodle
                            personacrea = Persona.objects.get(usuario_id=foro.usuario_creacion_id, status=True)
                            value, msg = CrearForosMoodle(foro.id, personacrea)
                            if not value:
                                raise NameError(msg)
                            id_estadosolicitud = 4
                            historial = HistorialaprobacionForo(foro_id=int(request.POST['idcodigotarea']),
                                                                estado_id=2,
                                                                observacion=id_observacion)
                            historial.save(request)
                        else:
                            foro.estado_id = id_estadosolicitud
                            foro.save(request)
                        historial = HistorialaprobacionForo(foro_id=int(request.POST['idcodigotarea']),
                                                            estado_id=id_estadosolicitud,
                                                            observacion=id_observacion)
                        historial.save(request)
                        nombredocente = Persona.objects.get(usuario_id=foro.usuario_creacion_id, status=True)
                        correo = nombredocente.lista_emails_envio()
                        if CoordinadorCarrera.objects.filter(status=True,
                                                             carrera=foro.silabosemanal.silabo.materia.asignaturamalla.malla.carrera,
                                                             periodo=periodo, sede=1, tipo=3):
                            coordinadordecarrera = CoordinadorCarrera.objects.filter(status=True,
                                                                                     carrera=foro.silabosemanal.silabo.materia.asignaturamalla.malla.carrera,
                                                                                     periodo=periodo, sede=1, tipo=3)[0]
                            correo = correo + coordinadordecarrera.persona.lista_emails_envio()
                        nombrerecurso = 'FORO'
                        estado = foro.estado.nombre
                        semana = foro.silabosemanal.numsemana

                    if id_codtipo == 3:
                        test = TestSilaboSemanalAdmision.objects.get(pk=int(request.POST['idcodigotarea']))
                        # if test.calificar:
                        #     if not test.detallemodelo:
                        #         transaction.set_rollback(True)
                        #         return JsonResponse(
                        #             {"result": "bad", "mensaje": u"No tiene configurado modelo de calificacion."})
                        if id_estadosolicitud == 2:
                            from Moodle_Funciones import CrearTestMoodleAdmision
                            personacrea = Persona.objects.get(usuario_id=test.usuario_creacion_id, status=True)
                            value, msg = CrearTestMoodleAdmision(test.id, personacrea)
                            if not value:
                                raise NameError(msg)
                            id_estadosolicitud = 4
                            historial = HistorialaprobacionTest(test_id=int(request.POST['idcodigotarea']),
                                                                estado_id=2,
                                                                observacion=id_observacion)
                            historial.save(request)

                        else:
                            test.estado_id = id_estadosolicitud
                            test.save(request)
                        historial = HistorialaprobacionTest(test_id=int(request.POST['idcodigotarea']),
                                                            estado_id=id_estadosolicitud,
                                                            observacion=id_observacion)
                        historial.save(request)
                        nombredocente = Persona.objects.get(usuario_id=test.usuario_creacion_id, status=True)
                        correo = nombredocente.lista_emails_envio()
                        if CoordinadorCarrera.objects.filter(status=True,
                                                             carrera=test.silabosemanal.silabo.materia.asignaturamalla.malla.carrera,
                                                             periodo=periodo, sede=1, tipo=3):
                            coordinadordecarrera = CoordinadorCarrera.objects.filter(status=True,
                                                                                     carrera=test.silabosemanal.silabo.materia.asignaturamalla.malla.carrera,
                                                                                     periodo=periodo, sede=1, tipo=3)[0]
                            correo = correo + coordinadordecarrera.persona.lista_emails_envio()
                        nombrerecurso = 'TEST'
                        estado = test.estado.nombre
                        semana = test.silabosemanal.numsemana
                    if id_codtipo == 4:
                        guiaestudiante = GuiaEstudianteSilaboSemanal.objects.get(pk=int(request.POST['idcodigotarea']))
                        lista_formato = []
                        if guiaestudiante.mis_formatos(periodo):
                            for format in guiaestudiante.mis_formatos(periodo):
                                lista_formato.append(format.nombre)
                        if lista_formato and 'word' in lista_formato and id_estadosolicitud == 2:
                            guiaestudiante.estado_id = 5
                            guiaestudiante.save(request)
                            lista_cor = []
                            nombre_carrera = guiaestudiante.silabosemanal.silabo.materia.asignaturamalla.malla.carrera.nombre_completo()
                            lista_cor.append('sop_docencia_crai@unemi.edu.ec')
                            send_html_mail("SGA - REVISIÓN DE RECURSOS - %s" % nombre_carrera,
                                           "emails/sop_doc_crai_recursos.html",
                                           {'sistema': u'SGA - UNEMI',
                                            'fecha': datetime.now().date(),
                                            'hora': datetime.now().time(),
                                            'recurso': guiaestudiante,
                                            'tipo': 2,
                                            'nombrecarrera': nombre_carrera,
                                            't': miinstitucion()
                                            },
                                           lista_cor,
                                           [],
                                           cuenta=variable_valor('CUENTAS_CORREOS')[0]
                                           )
                        else:
                            guiaestudiante.estado_id = id_estadosolicitud
                            guiaestudiante.save(request)
                            materia = guiaestudiante.silabosemanal.silabo.materia
                            materia.actualizarhtml = True
                            materia.save()
                        historial = HistorialaprobacionGuiaEstudiante(
                            guiaestudiante_id=int(request.POST['idcodigotarea']),
                            estado_id=id_estadosolicitud,
                            observacion=id_observacion)
                        historial.save(request)
                        nombredocente = Persona.objects.get(usuario_id=guiaestudiante.usuario_creacion_id, status=True)
                        correo = nombredocente.lista_emails_envio()
                        if CoordinadorCarrera.objects.filter(status=True,
                                                             carrera=guiaestudiante.silabosemanal.silabo.materia.asignaturamalla.malla.carrera,
                                                             periodo=periodo, sede=1, tipo=3):
                            coordinadordecarrera = CoordinadorCarrera.objects.filter(status=True,
                                                                                     carrera=guiaestudiante.silabosemanal.silabo.materia.asignaturamalla.malla.carrera,
                                                                                     periodo=periodo, sede=1, tipo=3)[0]
                            correo = correo + coordinadordecarrera.persona.lista_emails_envio()
                        nombrerecurso = 'GUIA ESTUDIANTIL'
                        estado = guiaestudiante.estado.nombre
                        semana = guiaestudiante.silabosemanal.numsemana
                    if id_codtipo == 5:
                        guiadocente = GuiaDocenteSilaboSemanal.objects.get(pk=int(request.POST['idcodigotarea']))
                        guiadocente.estado_id = id_estadosolicitud
                        guiadocente.save(request)
                        materia = guiadocente.silabosemanal.silabo.materia
                        materia.actualizarhtml = True
                        materia.save()
                        historial = HistorialaprobacionGuiaDocente(guiadocente_id=int(request.POST['idcodigotarea']),
                                                                   estado_id=id_estadosolicitud,
                                                                   observacion=id_observacion)
                        historial.save(request)
                        nombredocente = Persona.objects.get(usuario_id=guiadocente.usuario_creacion_id, status=True)
                        correo = nombredocente.lista_emails_envio()
                        if CoordinadorCarrera.objects.filter(status=True,
                                                             carrera=guiadocente.silabosemanal.silabo.materia.asignaturamalla.malla.carrera,
                                                             periodo=periodo, sede=1, tipo=3):
                            coordinadordecarrera = CoordinadorCarrera.objects.filter(status=True,
                                                                                     carrera=guiadocente.silabosemanal.silabo.materia.asignaturamalla.malla.carrera,
                                                                                     periodo=periodo, sede=1, tipo=3)[0]
                            correo = correo + coordinadordecarrera.persona.lista_emails_envio()
                        nombrerecurso = 'GUIA DOCENTE'
                        estado = guiadocente.estado.nombre
                        semana = guiadocente.silabosemanal.numsemana
                    if id_codtipo == 6:
                        diapositiva = DiapositivaSilaboSemanal.objects.get(pk=int(request.POST['idcodigotarea']))
                        lista_formato = []
                        if diapositiva.mis_formatos(periodo):
                            for format in diapositiva.mis_formatos(periodo):
                                lista_formato.append(format.nombre)
                        if lista_formato and 'word' in lista_formato and id_estadosolicitud == 2:
                            diapositiva.estado_id = 5
                            diapositiva.save(request)
                            # correo
                        else:
                            if id_estadosolicitud == 2:
                                from Moodle_Funciones import CrearRecursoMoodle
                                personacrea = Persona.objects.get(usuario_id=diapositiva.usuario_creacion_id, status=True)
                                CrearRecursoMoodle(diapositiva.id, personacrea)
                            else:
                                diapositiva.estado_id = id_estadosolicitud
                                diapositiva.save(request)

                        historial = HistorialaprobacionDiapositiva(diapositiva_id=int(request.POST['idcodigotarea']),
                                                                   estado_id=id_estadosolicitud,
                                                                   observacion=id_observacion)
                        historial.save(request)
                        nombredocente = Persona.objects.get(usuario_id=diapositiva.usuario_creacion_id, status=True)
                        correo = nombredocente.lista_emails_envio()
                        if CoordinadorCarrera.objects.filter(status=True,
                                                             carrera=diapositiva.silabosemanal.silabo.materia.asignaturamalla.malla.carrera,
                                                             periodo=periodo, sede=1, tipo=3):
                            coordinadordecarrera = CoordinadorCarrera.objects.filter(status=True,
                                                                                     carrera=diapositiva.silabosemanal.silabo.materia.asignaturamalla.malla.carrera,
                                                                                     periodo=periodo, sede=1, tipo=3)[0]
                            correo = correo + coordinadordecarrera.persona.lista_emails_envio()
                        nombrerecurso = 'DIAPOSITIVA'
                        estado = diapositiva.estado.nombre
                        semana = diapositiva.silabosemanal.numsemana
                    if id_codtipo == 7:
                        compendio = CompendioSilaboSemanal.objects.get(pk=int(request.POST['idcodigotarea']))
                        lista_formato = []
                        if compendio.mis_formatos(periodo):
                            for format in compendio.mis_formatos(periodo):
                                lista_formato.append(format.nombre)
                        if lista_formato and 'word' in lista_formato and id_estadosolicitud == 2:
                            compendio.estado_id = 5
                            compendio.save(request)
                            # correo
                        else:
                            compendio.estado_id = id_estadosolicitud
                            compendio.save(request)
                            materia = compendio.silabosemanal.silabo.materia
                            materia.actualizarhtml = True
                            materia.save()
                        historial = HistorialaprobacionCompendio(compendio_id=int(request.POST['idcodigotarea']),
                                                                 estado_id=id_estadosolicitud,
                                                                 observacion=id_observacion)
                        historial.save(request)
                        nombredocente = Persona.objects.get(usuario_id=compendio.usuario_creacion_id, status=True)
                        correo = nombredocente.lista_emails_envio()
                        if CoordinadorCarrera.objects.filter(status=True,
                                                             carrera=compendio.silabosemanal.silabo.materia.asignaturamalla.malla.carrera,
                                                             periodo=periodo, sede=1, tipo=3):
                            coordinadordecarrera = CoordinadorCarrera.objects.filter(status=True,
                                                                                     carrera=compendio.silabosemanal.silabo.materia.asignaturamalla.malla.carrera,
                                                                                     periodo=periodo, sede=1, tipo=3)[0]
                            correo = correo + coordinadordecarrera.persona.lista_emails_envio()
                        nombrerecurso = 'COMPENDIO'
                        estado = compendio.estado.nombre
                        semana = compendio.silabosemanal.numsemana
                    if id_codtipo == 8:
                        material = MaterialAdicionalSilaboSemanal.objects.get(pk=int(request.POST['idcodigotarea']))
                        material.estado_id = id_estadosolicitud
                        material.save(request)
                        if id_estadosolicitud == 2:
                            from Moodle_Funciones import CrearMaterialesMoodle
                            personacrea = Persona.objects.get(usuario_id=material.usuario_creacion_id, status=True)
                            CrearMaterialesMoodle(material.id, personacrea)
                            historial = HistorialaprobacionMaterial(material_id=int(request.POST['idcodigotarea']),
                                                                    estado_id=2,
                                                                    observacion=id_observacion)
                            historial.save(request)

                        historial = HistorialaprobacionMaterial(material_id=int(request.POST['idcodigotarea']),
                                                                estado_id=id_estadosolicitud,
                                                                observacion=id_observacion)
                        historial.save(request)
                        nombredocente = Persona.objects.get(usuario_id=material.usuario_creacion_id, status=True)
                        correo = nombredocente.lista_emails_envio()
                        if CoordinadorCarrera.objects.filter(status=True,
                                                             carrera=material.silabosemanal.silabo.materia.asignaturamalla.malla.carrera,
                                                             periodo=periodo, sede=1, tipo=3):
                            coordinadordecarrera = CoordinadorCarrera.objects.filter(status=True,
                                                                                     carrera=material.silabosemanal.silabo.materia.asignaturamalla.malla.carrera,
                                                                                     periodo=periodo, sede=1, tipo=3)[0]
                            correo = correo + coordinadordecarrera.persona.lista_emails_envio()
                        nombrerecurso = 'MATERIAL COMPLEMENTARIO'
                        estado = material.estado.nombre
                        semana = material.silabosemanal.numsemana
                    if id_codtipo == 9:
                        tareapractica = TareaPracticaSilaboSemanal.objects.get(pk=int(request.POST['idcodigotarea']))
                        if id_estadosolicitud == 2:
                            from Moodle_Funciones import CrearPracticasTareasMoodle
                            personacrea = Persona.objects.get(usuario_id=tareapractica.usuario_creacion_id, status=True)
                            value, msg = CrearPracticasTareasMoodle(tareapractica.id, personacrea)
                            if not value:
                                raise NameError(msg)
                            id_estadosolicitud = 4
                            historial = HistorialaprobacionTareaPractica(
                                tareapractica_id=int(request.POST['idcodigotarea']),
                                estado_id=2,
                                observacion=id_observacion)
                            historial.save(request)

                        else:
                            tareapractica.estado_id = id_estadosolicitud
                            tareapractica.save(request)
                        historial = HistorialaprobacionTareaPractica(
                            tareapractica_id=int(request.POST['idcodigotarea']),
                            estado_id=id_estadosolicitud,
                            observacion=id_observacion)
                        historial.save(request)
                        nombredocente = Persona.objects.get(usuario_id=tareapractica.usuario_creacion_id, status=True)

                        correo = nombredocente.lista_emails_envio()
                        if CoordinadorCarrera.objects.filter(
                                carrera=tareapractica.silabosemanal.silabo.materia.asignaturamalla.malla.carrera,
                                periodo=periodo, sede=1, tipo=3):
                            coordinadordecarrera = CoordinadorCarrera.objects.filter(
                                carrera=tareapractica.silabosemanal.silabo.materia.asignaturamalla.malla.carrera,
                                periodo=periodo, sede=1, tipo=3)[0]
                            correo = correo + coordinadordecarrera.persona.lista_emails_envio()
                        nombrerecurso = 'TAREA'
                        estado = tareapractica.estado.nombre
                        semana = tareapractica.silabosemanal.numsemana

                    if id_codtipo == 10:
                        video = VideoMagistralSilaboSemanal.objects.get(id=int(request.POST['idcodigotarea']))
                        if id_estadosolicitud == 2:
                            video.presentacion_validado = True
                            video.save(request)
                            nombrerecurso = 'VIDEO MAGISTRAL'
                            list_correo = []
                            list_correo.append('sop_docencia_crai@unemi.edu.ec')
                            semana = video.silabosemanal.numsemana
                            nombre_carrera = video.silabosemanal.silabo.materia.asignaturamalla.malla.carrera.nombre_completo()
                            cuenta = CUENTAS_CORREOS[0][1]
                            send_html_mail("SGA - REVISIÓN DE VIDEOS - %s" % nombre_carrera, "emails/ingresovideomagistral.html",
                                           {'sistema': request.session['nombresistema'], 'nombredocente': video.silabosemanal.silabo.materia.profesor_principal(),
                                            'nombrerecurso': nombrerecurso, 'semana': semana, 'nombrecarrera': nombre_carrera,
                                            'vidmagistral': video, 't': miinstitucion()}, list_correo, [],
                                           cuenta=cuenta)
                        elif id_estadosolicitud == 3:
                            video.estado_id = 3
                            video.presentacion_validado = False
                            video.save(request)

                    # send_html_mail("SGA - PLANIFICACIÓN DE RECURSOS.", "emails/recursoaprobacionindividual.html",
                    #                {'sistema': request.session['nombresistema'], 'nombredocente': nombredocente,
                    #                 'nombrerecurso': nombrerecurso, 'estado': estado, 'semana': semana,
                    #                 't': miinstitucion()}, correo, [], coneccion=coneccion)

                    return JsonResponse({"result": "ok"})
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

            elif action == 'estadoingresado':
                try:
                    silabosemanal = SilaboSemanal.objects.get(pk=request.POST['idsilabosemana'])
                    for listarea in silabosemanal.tareasilabosemanal_set.filter(status=True).exclude(estado_id=4):
                        listarea.estado_id = 1
                        listarea.save(request)
                    for listarea in silabosemanal.forosilabosemanal_set.filter(status=True).exclude(estado_id=4):
                        listarea.estado_id = 1
                        listarea.save(request)
                    if periodo.clasificacion == 3:
                        for listarea in silabosemanal.testsilabosemanaladmision_set.filter(status=True).exclude(estado_id=4):
                            listarea.estado_id = 1
                            listarea.save(request)
                    else:
                        for listarea in silabosemanal.testsilabosemanal_set.filter(status=True).exclude(estado_id=4):
                            listarea.estado_id = 1
                            listarea.save(request)
                    for listarea in silabosemanal.guiaestudiantesilabosemanal_set.filter(status=True).exclude(estado_id=4):
                        listarea.estado_id = 1
                        listarea.save(request)
                    for listarea in silabosemanal.guiadocentesilabosemanal_set.filter(status=True).exclude(estado_id=4):
                        listarea.estado_id = 1
                        listarea.save(request)
                    for listarea in silabosemanal.diapositivasilabosemanal_set.filter(status=True).exclude(estado_id=4):
                        listarea.estado_id = 1
                        listarea.save(request)
                    for listarea in silabosemanal.compendiosilabosemanal_set.filter(status=True).exclude(estado_id=4):
                        listarea.estado_id = 1
                        listarea.save(request)
                    for listarea in silabosemanal.materialadicionalsilabosemanal_set.filter(status=True).exclude(estado_id=4):
                        listarea.estado_id = 1
                        listarea.save(request)
                    for listarea in silabosemanal.tareapracticasilabosemanal_set.filter(status=True).exclude(estado_id=4):
                        listarea.estado_id = 1
                        listarea.save(request)
                    log(u'Cambia a estado ingresado semana: %s ' % (silabosemanal), request, "edit")
                    return JsonResponse({"result": "ok"})
                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})
                    pass

            elif action == 'aprobacionmasivarecurso':
                try:
                    listatarea = json.loads(request.POST['listatarea'])
                    listatareapractica = json.loads(request.POST['listatareapractica'])
                    listaforo = json.loads(request.POST['listaforo'])
                    listatest = json.loads(request.POST['listatest'])
                    listaguiaestudiante = json.loads(request.POST['listaguiaestudiante'])
                    listaguiadocente = json.loads(request.POST['listaguiadocente'])
                    listadiapositiva = json.loads(request.POST['listadiapositiva'])
                    listacompendio = json.loads(request.POST['listacompendio'])
                    listamaterial = json.loads(request.POST['listamaterial'])
                    # listatareatalleexpo = json.loads(request.POST['listatareatalleexpo'])
                    idusuario = 0
                    lista_errores = []
                    if listatarea:
                        from Moodle_Funciones import CrearTareasMoodle
                        for lista in listatarea:
                            codigotarea = TareaSilaboSemanal.objects.get(pk=lista)
                            personacrea = Persona.objects.get(usuario_id=codigotarea.usuario_creacion_id, status=True)
                            if codigotarea.actividad.categoriamoodle == 3:
                                try:
                                    value, msg = CrearTareasMoodle(codigotarea.id, personacrea)
                                    if not value:
                                        raise NameError(msg)
                                    else:
                                        materia = codigotarea.silabosemanal.silabo.materia
                                        materia.actualizarhtml = True
                                        materia.save()
                                        historialt1 = HistorialaprobacionTarea(tarea=codigotarea,
                                                                               estado_id=2,
                                                                               observacion='APROBADO')
                                        historialt1.save(request)
                                        historialt2 = HistorialaprobacionTarea(tarea=codigotarea,
                                                                               estado_id=4,
                                                                               observacion='MIGRADO A MOODLE')
                                        historialt2.save(request)
                                        log(u'Aprobo masivo tarea: %s - %s' % (codigotarea, codigotarea.silabosemanal), request, "edit")
                                except Exception as ex:
                                    lista_errores.append({"actividad": "Tarea", "nombre": codigotarea.nombre, "error": ex.__str__()})

                            if codigotarea.actividad.categoriamoodle == 4:
                                try:
                                    value, msg = CrearTareasTEMoodle(codigotarea.id, personacrea)
                                    if not value:
                                        raise NameError(msg)
                                    else:
                                        materia = codigotarea.silabosemanal.silabo.materia
                                        materia.actualizarhtml = True
                                        materia.save()
                                        historialt1 = HistorialaprobacionTarea(tarea=codigotarea,
                                                                               estado_id=2,
                                                                               observacion='APROBADO')
                                        historialt1.save(request)
                                        historialt2 = HistorialaprobacionTarea(tarea=codigotarea,
                                                                               estado_id=4,
                                                                               observacion='MIGRADO A MOODLE')
                                        historialt2.save(request)
                                        log(u'Aprobo masivo tarea: %s - %s' % (codigotarea, codigotarea.silabosemanal), request, "edit")
                                except Exception as ex:
                                    lista_errores.append({"actividad": "Tarea", "nombre": codigotarea.nombre, "error": ex.__str__()})
                    if listatareapractica:
                        from Moodle_Funciones import CrearPracticasTareasMoodle
                        for lista in listatareapractica:
                            codigotarea = TareaPracticaSilaboSemanal.objects.get(pk=lista)
                            personacrea = Persona.objects.get(usuario_id=codigotarea.usuario_creacion_id, status=True)
                            try:
                                value, msg = CrearPracticasTareasMoodle(codigotarea.id, personacrea)
                                if not value:
                                    raise NameError(msg)
                                else:
                                    materia = codigotarea.silabosemanal.silabo.materia
                                    materia.actualizarhtml = True
                                    materia.save()
                                    historialt3 = HistorialaprobacionTareaPractica(tareapractica=codigotarea,
                                                                                   estado_id=2,
                                                                                   observacion='APROBADO')
                                    historialt3.save(request)
                                    historialt4 = HistorialaprobacionTareaPractica(tareapractica=codigotarea,
                                                                                   estado_id=4,
                                                                                   observacion='MIGRADO A MOODLE')
                                    historialt4.save(request)
                                    log(u'Aprobo masivo tarea práctica: %s - %s' % (codigotarea, codigotarea.silabosemanal), request, "edit")
                            except Exception as ex:
                                lista_errores.append({"actividad": "Tarea", "nombre": codigotarea.nombre, "error": ex.__str__()})

                    if listaforo:
                        from Moodle_Funciones import CrearForosMoodle
                        for lista in listaforo:
                            codigoforo = ForoSilaboSemanal.objects.get(pk=lista)
                            personacrea = Persona.objects.get(usuario_id=codigoforo.usuario_creacion_id, status=True)
                            if codigoforo.calificar:
                                if not codigoforo.detallemodelo:
                                    raise NameError(u"No tiene configurado modelo de calificacion, [%s]." % (codigoforo.nombre))
                            try:
                                value, msg = CrearForosMoodle(codigoforo.id, personacrea)
                                if not value:
                                    raise NameError(msg)
                                else:
                                    materia = codigoforo.silabosemanal.silabo.materia
                                    materia.actualizarhtml = True
                                    materia.save()
                                    historialf1 = HistorialaprobacionForo(foro=codigoforo,
                                                                          estado_id=2,
                                                                          observacion='APROBADO')
                                    historialf1.save(request)
                                    historialf2 = HistorialaprobacionForo(foro=codigoforo,
                                                                          estado_id=4,
                                                                          observacion='MIGRADO A MOODLE')
                                    historialf2.save(request)
                                    log(u'Aprobo masivo foro: %s - %s' % (codigoforo, codigoforo.silabosemanal), request, "edit")
                            except Exception as ex:
                                lista_errores.append({"actividad": "Foro", "nombre": codigoforo.nombre, "descripcion": codigoforo.__str__(), "error": ex.__str__()})

                    if listatest:
                        from Moodle_Funciones import CrearTestMoodle
                        for lista in listatest:
                            codigotest = TestSilaboSemanal.objects.get(pk=lista)
                            personacrea = Persona.objects.get(usuario_id=codigotest.usuario_creacion_id, status=True)
                            if codigotest.calificar:
                                if not codigotest.detallemodelo:
                                    raise NameError(u"No tiene configurado modelo de calificacion, [%s]." % (codigotest.instruccion))
                            try:
                                value, msg = CrearTestMoodle(codigotest.id, personacrea)
                                if not value:
                                    raise NameError(msg)
                                else:
                                    materia = codigotest.silabosemanal.silabo.materia
                                    materia.actualizarhtml = True
                                    materia.save()
                                    historialt1 = HistorialaprobacionTest(test=codigotest,
                                                                          estado_id=2,
                                                                          observacion='APROBADO')
                                    historialt1.save(request)
                                    historialt2 = HistorialaprobacionTest(test=codigotest,
                                                                          estado_id=4,
                                                                          observacion='MIGRADO A MOODLE')
                                    historialt2.save(request)
                                    log(u'Aprobo masivo test: %s - %s' % (codigotest, codigotest.silabosemanal), request, "edit")
                            except Exception as ex:
                                lista_errores.append({"actividad": "Test", "nombre": codigotest.nombretest, "descripcion": codigotest.__str__(), "error": ex.__str__()})
                    if listaguiaestudiante:
                        from Moodle_Funciones import CrearGuiaestudianteMoodle
                        for lista in listaguiaestudiante:
                            codigoguiaestudiante = GuiaEstudianteSilaboSemanal.objects.get(pk=lista)
                            personacrea = Persona.objects.get(usuario_id=codigoguiaestudiante.usuario_creacion_id, status=True)
                            try:
                                value, msg = CrearGuiaestudianteMoodle(codigoguiaestudiante.id, personacrea)
                                if not value:
                                    raise NameError(msg)
                                else:
                                    materia = codigoguiaestudiante.silabosemanal.silabo.materia
                                    materia.actualizarhtml = True
                                    materia.save()
                                    historialg1 = HistorialaprobacionGuiaEstudiante(guiaestudiante=codigoguiaestudiante,
                                                                                    estado_id=2,
                                                                                    observacion='APROBADO')
                                    historialg1.save(request)
                                    historialg2 = HistorialaprobacionGuiaEstudiante(guiaestudiante=codigoguiaestudiante,
                                                                                    estado_id=4,
                                                                                    observacion='MIGRADO A MOODLE')
                                    historialg2.save(request)
                                    log(u'Aprobo masivo guia de estudiante: %s - %s' % (codigoguiaestudiante, codigoguiaestudiante.silabosemanal), request, "edit")
                            except Exception as ex:
                                lista_errores.append({"actividad": "Guía de estudiante", "observacion": codigoguiaestudiante.__str__(), "error": ex.__str__()})

                    if listaguiadocente:
                        from Moodle_Funciones import CrearGuiadocenteMoodle
                        for lista in listaguiadocente:
                            codigoguiadocente = GuiaDocenteSilaboSemanal.objects.get(pk=lista)
                            personacrea = Persona.objects.get(usuario_id=codigoguiadocente.usuario_creacion_id, status=True)
                            try:
                                value, msg = CrearGuiadocenteMoodle(codigoguiadocente.id, personacrea)
                                if not value:
                                    raise NameError(msg)
                                else:
                                    materia = codigoguiadocente.silabosemanal.silabo.materia
                                    materia.actualizarhtml = True
                                    materia.save()
                                    historialg1 = HistorialaprobacionGuiaDocente(guiadocente=codigoguiadocente,
                                                                                 estado_id=2,
                                                                                 observacion='APROBADO')
                                    historialg1.save(request)
                                    historialg2 = HistorialaprobacionGuiaDocente(guiadocente=codigoguiadocente,
                                                                                 estado_id=4,
                                                                                 observacion='MIGRADO A MOODLE')
                                    historialg2.save(request)
                                    log(u'Aprobo masivo guia de docente: %s - %s' % (codigoguiadocente, codigoguiadocente.silabosemanal), request, "edit")
                            except Exception as ex:
                                lista_errores.append({"actividad": "Guía de estudiante", "observacion": codigoguiadocente.__str__(), "error": ex.__str__()})

                    if listadiapositiva:
                        from Moodle_Funciones import CrearRecursoMoodle
                        for lista in listadiapositiva:
                            codigodiapositiva = DiapositivaSilaboSemanal.objects.get(pk=lista)
                            personacrea = Persona.objects.get(usuario_id=codigodiapositiva.usuario_creacion_id, status=True)
                            try:
                                value, msg = CrearRecursoMoodle(codigodiapositiva.id, personacrea)
                                if not value:
                                    raise NameError(msg)
                                else:
                                    materia = codigodiapositiva.silabosemanal.silabo.materia
                                    materia.actualizarhtml = True
                                    materia.save()
                                    historialr1 = HistorialaprobacionDiapositiva(diapositiva=codigodiapositiva,
                                                                                 estado_id=2,
                                                                                 observacion='APROBADO')
                                    historialr1.save(request)
                                    historialr2 = HistorialaprobacionDiapositiva(diapositiva=codigodiapositiva,
                                                                                 estado_id=4,
                                                                                 observacion='MIGRADO A MOODLE')
                                    historialr2.save(request)
                                    log(u'Aprobo masivo presentación : %s - %s' % (codigodiapositiva, codigodiapositiva.silabosemanal), request, "edit")
                            except Exception as ex:
                                lista_errores.append({"actividad": "Presentación", "nombre": codigodiapositiva.nombre, "descripcion": codigodiapositiva.__str__(), "error": ex.__str__()})

                    if listacompendio:
                        from Moodle_Funciones import CrearCompendioMoodle
                        for lista in listacompendio:
                            codigocompendio = CompendioSilaboSemanal.objects.get(pk=lista)
                            personacrea = Persona.objects.get(usuario_id=codigocompendio.usuario_creacion_id, status=True)
                            try:
                                value, msg = CrearCompendioMoodle(codigocompendio.id, personacrea)
                                if not value:
                                    raise NameError(msg)
                                else:
                                    materia = codigocompendio.silabosemanal.silabo.materia
                                    materia.actualizarhtml = True
                                    materia.save()
                                    historialc1 = HistorialaprobacionCompendio(compendio=codigocompendio,
                                                                               estado_id=2,
                                                                               observacion='APROBADO')
                                    historialc1.save(request)
                                    historialc2 = HistorialaprobacionCompendio(compendio=codigocompendio,
                                                                               estado_id=4,
                                                                               observacion='MIGRADO A MOODLE')
                                    historialc2.save(request)
                                    log(u'Aprobo masivo compendio : %s - %s' % (codigocompendio, codigocompendio.silabosemanal), request, "edit")

                            except Exception as ex:
                                lista_errores.append({"actividad": "Compendio", "descripcion": codigocompendio.__str__(), "error": ex.__str__()})

                    if listamaterial:
                        from Moodle_Funciones import CrearMaterialesMoodle
                        for lista in listamaterial:
                            codigomaterial = MaterialAdicionalSilaboSemanal.objects.get(pk=lista)
                            personacrea = Persona.objects.get(usuario_id=codigomaterial.usuario_creacion_id, status=True)
                            try:
                                value, msg = CrearMaterialesMoodle(codigomaterial.id, personacrea)
                                if not value:
                                    raise NameError(msg)
                                else:
                                    materia = codigomaterial.silabosemanal.silabo.materia
                                    materia.actualizarhtml = True
                                    materia.save()
                                    historialm1 = HistorialaprobacionMaterial(material=codigomaterial,
                                                                              estado_id=2,
                                                                              observacion='APROBADO')
                                    historialm1.save(request)
                                    historialm2 = HistorialaprobacionMaterial(material=codigomaterial,
                                                                              estado_id=4,
                                                                              observacion='MIGRADO A MOODLE')
                                    historialm2.save(request)
                                    log(u'Aprobo masivo material adicional : %s - %s' % (codigomaterial, codigomaterial.silabosemanal), request, "edit")
                            except Exception as ex:
                                lista_errores.append({"actividad": "Material complementario", "nombre": codigomaterial.nombre, "descripcion": codigomaterial.__str__(), "error": ex.__str__()})

                    # if idusuario > 0:
                    #     nombredocente = Persona.objects.get(usuario_id=idusuario, status=True)
                    #     correo = nombredocente.lista_emails_envio()
                    #     estado = 'APROBADO'
                    #     cuenta=CUENTAS_CORREOS[3][1]
                    #     send_html_mail("SGA - PLANIFICACIÓN DE RECURSOS.", "emails/recursoaprobacionindividual.html",
                    #                    {'sistema': request.session['nombresistema'], 'nombredocente': nombredocente,
                    #                     'estado': estado, 't': miinstitucion()}, correo, [], coneccion=coneccion)
                    return JsonResponse({"result": "ok", "errores": lista_errores})
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos. %s" % ex})

            elif action == 'aprobacionmasivarecurso_pregrado':
                try:
                    listatarea = json.loads(request.POST['listatarea'])
                    listatareapractica = json.loads(request.POST['listatareapractica'])
                    listaforo = json.loads(request.POST['listaforo'])
                    listatest = json.loads(request.POST['listatest'])
                    listaguiaestudiante = json.loads(request.POST['listaguiaestudiante'])
                    listaguiadocente = json.loads(request.POST['listaguiadocente'])
                    listadiapositiva = json.loads(request.POST['listadiapositiva'])
                    listacompendio = json.loads(request.POST['listacompendio'])
                    listamaterial = json.loads(request.POST['listamaterial'])
                    # listatareatalleexpo = json.loads(request.POST['listatareatalleexpo'])
                    lista_errores = []
                    if listatarea:
                        from Moodle_Funciones import CrearTareasMoodle
                        for lista in listatarea:
                            codigotarea = TareaSilaboSemanal.objects.get(pk=lista)
                            personacrea = Persona.objects.get(usuario_id=codigotarea.usuario_creacion_id, status=True)
                            if codigotarea.actividad.categoriamoodle == 3:
                                try:
                                    value, msg = CrearTareasMoodle(codigotarea.id, personacrea)
                                    if not value:
                                        raise NameError(msg)
                                    else:
                                        materia = codigotarea.silabosemanal.silabo.materia
                                        materia.actualizarhtml = True
                                        materia.save()
                                        if codigotarea.rubricamoodle:
                                            if not codigotarea.rubricamoodle.estado:
                                                codigotarea.rubricamoodle.estado = True
                                                codigotarea.rubricamoodle.save(request)
                                                historial = RubricaMoodleHistorial(rubrica=codigotarea.rubricamoodle,
                                                                                   observacion="APROBACIÓN AUTOMÁTICA AL APROBAR EL RECURSO",
                                                                                   estado=2)
                                                historial.save(request)
                                        historialt1 = HistorialaprobacionTarea(tarea=codigotarea,
                                                                               estado_id=2,
                                                                               observacion='APROBADO')
                                        historialt1.save(request)
                                        historialt2 = HistorialaprobacionTarea(tarea=codigotarea,
                                                                               estado_id=4,
                                                                               observacion='MIGRADO A MOODLE')
                                        historialt2.save(request)
                                        for lista in ListaVerificacion.objects.filter(status=True,
                                                                                      tiporecurso=codigotarea.tiporecurso):
                                            if not DetalleListaVerificacionTarea.objects.filter(status=True,
                                                                                                tareasilabosemanal=codigotarea,
                                                                                                listaverificacion=lista).exists():
                                                det = DetalleListaVerificacionTarea(
                                                    tareasilabosemanal=codigotarea,
                                                    listaverificacion=lista,
                                                    cumple=True
                                                )
                                                det.save(request)
                                            else:
                                                det = DetalleListaVerificacionTarea.objects.get(status=True,
                                                                                                tareasilabosemanal=codigotarea,
                                                                                                listaverificacion=lista)
                                                det.cumple = True
                                                det.observacion = ""
                                                det.save(request)

                                        log(u'Aprobo masivo tarea: %s - %s' % (codigotarea, codigotarea.silabosemanal), request, "edit")
                                except Exception as ex:
                                    lista_errores.append({"actividad": "Tarea", "nombre": codigotarea.nombre, "error": ex.__str__()})

                            if codigotarea.actividad.categoriamoodle == 4:
                                try:
                                    value, msg = CrearTareasTEMoodle(codigotarea.id, personacrea)
                                    if not value:
                                        raise NameError(msg)
                                    else:
                                        materia = codigotarea.silabosemanal.silabo.materia
                                        materia.actualizarhtml = True
                                        materia.save()
                                        if codigotarea.rubricamoodle:
                                            if not codigotarea.rubricamoodle.estado:
                                                codigotarea.rubricamoodle.estado = True
                                                codigotarea.rubricamoodle.save(request)
                                                historial = RubricaMoodleHistorial(rubrica=codigotarea.rubricamoodle,
                                                                                   observacion="APROBACIÓN AUTOMÁTICA AL APROBAR EL RECURSO",
                                                                                   estado=2)
                                                historial.save(request)
                                        historialt1 = HistorialaprobacionTarea(tarea=codigotarea,
                                                                               estado_id=2,
                                                                               observacion='APROBADO')
                                        historialt1.save(request)
                                        historialt2 = HistorialaprobacionTarea(tarea=codigotarea,
                                                                               estado_id=4,
                                                                               observacion='MIGRADO A MOODLE')
                                        historialt2.save(request)
                                        for lista in ListaVerificacion.objects.filter(status=True,
                                                                                      tiporecurso=codigotarea.tiporecurso):
                                            if not DetalleListaVerificacionTarea.objects.filter(status=True,
                                                                                                tareasilabosemanal=codigotarea,
                                                                                                listaverificacion=lista).exists():
                                                det = DetalleListaVerificacionTarea(
                                                    tareasilabosemanal=codigotarea,
                                                    listaverificacion=lista,
                                                    cumple=True
                                                )
                                                det.save(request)
                                            else:
                                                det = DetalleListaVerificacionTarea.objects.get(status=True,
                                                                                                tareasilabosemanal=codigotarea,
                                                                                                listaverificacion=lista)
                                                det.cumple = True
                                                det.observacion = ""
                                                det.save(request)

                                        log(u'Aprobo masivo tarea: %s - %s' % (codigotarea, codigotarea.silabosemanal), request, "edit")
                                except Exception as ex:
                                    lista_errores.append({"actividad": "Tarea", "nombre": codigotarea.nombre, "descripcion": codigotarea.__str__(), "error": ex.__str__()})

                    if listatareapractica:
                        from Moodle_Funciones import CrearPracticasTareasMoodle
                        for lista in listatareapractica:
                            codigotarea = TareaPracticaSilaboSemanal.objects.get(pk=lista)
                            personacrea = Persona.objects.get(usuario_id=codigotarea.usuario_creacion_id, status=True)
                            try:
                                value, msg = CrearPracticasTareasMoodle(codigotarea.id, personacrea)
                                if not value:
                                    raise NameError(msg)
                                else:
                                    materia = codigotarea.silabosemanal.silabo.materia
                                    materia.actualizarhtml = True
                                    materia.save()
                                    historialp1 = HistorialaprobacionTareaPractica(tareapractica=codigotarea,
                                                                                   estado_id=2,
                                                                                   observacion='APROBADO')
                                    historialp1.save(request)
                                    historialp2 = HistorialaprobacionTareaPractica(tareapractica=codigotarea,
                                                                                   estado_id=4,
                                                                                   observacion='MIGRADO A MOODLE')
                                    historialp2.save(request)
                                    for lista in ListaVerificacion.objects.filter(status=True,
                                                                                  tiporecurso=codigotarea.tiporecurso):

                                        if not DetalleListaVerificacionTareaPractica.objects.filter(status=True,
                                                                                                    tareapracticasilabosemanal=codigotarea,
                                                                                                    listaverificacion=lista).exists():
                                            det = DetalleListaVerificacionTareaPractica(
                                                tareapracticasilabosemanal=codigotarea,
                                                listaverificacion=lista,
                                                cumple=True
                                            )
                                            det.save(request)
                                        else:
                                            det = DetalleListaVerificacionTareaPractica.objects.get(status=True,
                                                                                                    tareapracticasilabosemanal=codigotarea,
                                                                                                    listaverificacion=lista)
                                            det.cumple = True
                                            det.observacion = ""
                                            det.save(request)

                                    log(u'Aprobo masivo tarea práctica: %s - %s' % (codigotarea, codigotarea.silabosemanal), request, "edit")
                            except Exception as ex:
                                lista_errores.append({"actividad": "Tarea práctica", "nombre": codigotarea.nombre, "descripcion": codigotarea.__str__(), "error": ex.__str__()})

                    if listaforo:
                        from Moodle_Funciones import CrearForosMoodle
                        for lista in listaforo:
                            codigoforo = ForoSilaboSemanal.objects.get(pk=lista)
                            personacrea = Persona.objects.get(usuario_id=codigoforo.usuario_creacion_id, status=True)
                            if codigoforo.calificar:
                                if not codigoforo.detallemodelo:
                                    raise NameError(u"No tiene configurado modelo de calificacion, [%s]." % (codigoforo.nombre))
                            try:
                                value, msg = CrearForosMoodle(codigoforo.id, personacrea)
                                if not value:
                                    raise NameError(msg)
                                else:
                                    materia = codigoforo.silabosemanal.silabo.materia
                                    materia.actualizarhtml = True
                                    materia.save()
                                    historialf1 = HistorialaprobacionForo(foro=codigoforo,
                                                                          estado_id=2,
                                                                          observacion='APROBADO')
                                    historialf1.save(request)
                                    historialf2 = HistorialaprobacionForo(foro=codigoforo,
                                                                          estado_id=4,
                                                                          observacion='MIGRADO A MOODLE')
                                    historialf2.save(request)
                                    for lista in ListaVerificacion.objects.filter(status=True, tiporecurso=codigoforo.tiporecurso):

                                        if not DetalleListaVerificacionForo.objects.filter(status=True, forosilabosemanal=codigoforo,
                                                                                           listaverificacion=lista).exists():
                                            det = DetalleListaVerificacionForo(
                                                forosilabosemanal=codigoforo,
                                                listaverificacion=lista,
                                                cumple=True
                                            )
                                            det.save(request)
                                        else:
                                            det = DetalleListaVerificacionForo.objects.get(status=True, forosilabosemanal=codigoforo,
                                                                                           listaverificacion=lista)
                                            det.cumple = True
                                            det.observacion = ""
                                            det.save(request)
                                    log(u'Aprobo masivo foro: %s - %s' % (codigoforo, codigoforo.silabosemanal), request, "edit")
                            except Exception as ex:
                                lista_errores.append({"actividad": "Foro", "nombre": codigoforo.nombre, "descripcion": codigoforo.__str__(), "error": ex.__str__()})

                    if listatest:
                        from Moodle_Funciones import CrearTestMoodle
                        for lista in listatest:
                            codigotest = TestSilaboSemanal.objects.get(pk=lista)
                            personacrea = Persona.objects.get(usuario_id=codigotest.usuario_creacion_id, status=True)
                            if codigotest.calificar:
                                if not codigotest.detallemodelo:
                                    raise NameError(u"No tiene configurado modelo de calificacion, [%s]." % (codigotest.instruccion))
                            try:
                                value=True
                                if codigotest.silabosemanal.examen:
                                    nombrerecurso = 'EXAMEN'
                                    from Moodle_Funciones import CrearExamenMoodle
                                    value, msg = CrearExamenMoodle(codigotest.id, personacrea)
                                    if not value:
                                        raise NameError(msg)
                                else:
                                    from Moodle_Funciones import CrearTestMoodle
                                    value, msg = CrearTestMoodle(codigotest.id, personacrea)
                                    if not value:
                                        raise NameError(msg)

                                if value:
                                    materia = codigotest.silabosemanal.silabo.materia
                                    materia.actualizarhtml = True
                                    materia.save()
                                    historialt1 = HistorialaprobacionTest(test=codigotest,
                                                                          estado_id=2,
                                                                          observacion='APROBADO')
                                    historialt1.save(request)
                                    historialt2 = HistorialaprobacionTest(test=codigotest,
                                                                          estado_id=4,
                                                                          observacion='MIGRADO A MOODLE')
                                    historialt2.save(request)
                                    for lista in ListaVerificacion.objects.filter(status=True, tiporecurso=codigotest.tiporecurso):
                                        if not DetalleListaVerificacionTest.objects.filter(status=True, testsilabosemanal=codigotest,
                                                                                           listaverificacion=lista).exists():
                                            det = DetalleListaVerificacionTest(
                                                testsilabosemanal=codigotest,
                                                listaverificacion=lista,
                                                cumple=True
                                            )
                                            det.save(request)
                                        else:
                                            det = DetalleListaVerificacionTest.objects.get(status=True, testsilabosemanal=codigotest,
                                                                                           listaverificacion=lista)
                                            det.cumple = True
                                            det.observacion = ""
                                            det.save(request)
                                    log(u'Aprobo masivo test: %s - %s' % (codigotest, codigotest.silabosemanal), request, "edit")
                            except Exception as ex:
                                lista_errores.append({"actividad": "Test", "nombre": codigotest.nombretest, "descripcion": codigotest.__str__(), "error": ex.__str__()})

                    if listaguiaestudiante:
                        from Moodle_Funciones import CrearGuiaestudianteMoodle
                        for lista in listaguiaestudiante:
                            codigoguiaestudiante = GuiaEstudianteSilaboSemanal.objects.get(pk=lista)
                            materia = codigoguiaestudiante.silabosemanal.silabo.materia
                            materia.actualizarhtml = True
                            materia.save()
                            lista_formato = []
                            if codigoguiaestudiante.mis_formatos(periodo):
                                for format in codigoguiaestudiante.mis_formatos(periodo):
                                    lista_formato.append(format.nombre)
                            if lista_formato and 'word' in lista_formato:
                                codigoguiaestudiante.estado_id = 5
                                codigoguiaestudiante.save(request)
                                historialg1 = HistorialaprobacionGuiaEstudiante(guiaestudiante=codigoguiaestudiante,
                                                                                estado_id=5,
                                                                                observacion='APROBADO PARA REVISIÓN CRAI')
                                historialg1.save(request)
                                lista_cor = []
                                nombre_carrera = codigoguiaestudiante.silabosemanal.silabo.materia.asignaturamalla.malla.carrera.nombre_completo()
                                lista_cor.append('sop_docencia_crai@unemi.edu.ec')
                                send_html_mail("SGA - REVISIÓN DE RECURSOS - %s" % nombre_carrera,
                                               "emails/sop_doc_crai_recursos.html",
                                               {'sistema': u'SGA - UNEMI',
                                                'fecha': datetime.now().date(),
                                                'hora': datetime.now().time(),
                                                'recurso': codigoguiaestudiante,
                                                'tipo': 2,
                                                'nombrecarrera': nombre_carrera,
                                                't': miinstitucion()
                                                },
                                               lista_cor,
                                               [],
                                               cuenta=variable_valor('CUENTAS_CORREOS')[0]
                                               )
                                for lista in ListaVerificacion.objects.filter(status=True, tiporecurso=codigoguiaestudiante.tiporecurso):
                                    if not DetalleListaVerificacionGuiaEstudiante.objects.filter(status=True,
                                                                                                 guiaestudiantesilabosemanal=codigoguiaestudiante,
                                                                                                 listaverificacion=lista).exists():
                                        det = DetalleListaVerificacionGuiaEstudiante(
                                            guiaestudiantesilabosemanal=codigoguiaestudiante,
                                            listaverificacion=lista,
                                            cumple=True
                                        )
                                        det.save(request)
                                    else:
                                        det = DetalleListaVerificacionGuiaEstudiante.objects.get(status=True,
                                                                                                 guiaestudiantesilabosemanal=codigoguiaestudiante,
                                                                                                 listaverificacion=lista)
                                        det.cumple = True
                                        det.observacion = ""
                                        det.save(request)
                                log(u'Aprobo masivo guia de estudiante: %s - %s' % (codigoguiaestudiante, codigoguiaestudiante.silabosemanal), request, "edit")
                            else:
                                personacrea = Persona.objects.get(usuario_id=codigoguiaestudiante.usuario_creacion_id, status=True)
                                try:
                                    value, msg = CrearGuiaestudianteMoodle(codigoguiaestudiante.id, personacrea)
                                    if not value:
                                        raise NameError(msg)
                                    else:
                                        historialg1 = HistorialaprobacionGuiaEstudiante(guiaestudiante=codigoguiaestudiante,
                                                                                        estado_id=2,
                                                                                        observacion='APROBADO')
                                        historialg1.save(request)
                                        historialg2 = HistorialaprobacionGuiaEstudiante(guiaestudiante=codigoguiaestudiante,
                                                                                        estado_id=4,
                                                                                        observacion='MIGRADO A MOODLE')
                                        historialg2.save(request)
                                        for lista in ListaVerificacion.objects.filter(status=True,
                                                                                      tiporecurso=codigoguiaestudiante.tiporecurso):

                                            if not DetalleListaVerificacionGuiaEstudiante.objects.filter(status=True,
                                                                                                         guiaestudiantesilabosemanal=codigoguiaestudiante,
                                                                                                         listaverificacion=lista).exists():
                                                det = DetalleListaVerificacionGuiaEstudiante(
                                                    guiaestudiantesilabosemanal=codigoguiaestudiante,
                                                    listaverificacion=lista,
                                                    cumple=True
                                                )
                                                det.save(request)
                                            else:
                                                det = DetalleListaVerificacionGuiaEstudiante.objects.get(status=True,
                                                                                                         guiaestudiantesilabosemanal=codigoguiaestudiante,
                                                                                                         listaverificacion=lista)
                                                det.cumple = True
                                                det.observacion = ""
                                                det.save(request)

                                        log(u'Aprobo masivo guia de estudiante: %s - %s' % (codigoguiaestudiante, codigoguiaestudiante.silabosemanal), request, "edit")
                                except Exception as ex:
                                    lista_errores.append({"actividad": "Guía de estudiante", "observacion": codigoguiaestudiante.__str__(), "error": ex.__str__()})

                    if listaguiadocente:
                        from Moodle_Funciones import CrearGuiadocenteMoodle
                        for lista in listaguiadocente:
                            codigoguiadocente = GuiaDocenteSilaboSemanal.objects.get(pk=lista)
                            personacrea = Persona.objects.get(usuario_id=codigoguiadocente.usuario_creacion_id, status=True)
                            try:
                                value, msg = CrearGuiadocenteMoodle(codigoguiadocente.id, personacrea)
                                if not value:
                                    raise NameError(msg)
                                else:
                                    materia = codigoguiadocente.silabosemanal.silabo.materia
                                    materia.actualizarhtml = True
                                    materia.save()
                                    historiald1 = HistorialaprobacionGuiaDocente(guiadocente=codigoguiadocente,
                                                                                 estado_id=2,
                                                                                 observacion='APROBADO')
                                    historiald1.save(request)
                                    historiald2 = HistorialaprobacionGuiaDocente(guiadocente=codigoguiadocente,
                                                                                 estado_id=4,
                                                                                 observacion='MIGRADO A MOODLE')
                                    historiald2.save(request)
                                    for lista in ListaVerificacion.objects.filter(status=True,
                                                                                  tiporecurso=codigoguiadocente.tiporecurso):

                                        if not DetalleListaVerificacionGuiaDocente.objects.filter(status=True,
                                                                                                  guiadocentesilabosemanal=codigoguiadocente,
                                                                                                  listaverificacion=lista).exists():
                                            det = DetalleListaVerificacionGuiaDocente(
                                                guiadocentesilabosemanal=codigoguiadocente,
                                                listaverificacion=lista,
                                                cumple=True
                                            )
                                            det.save(request)
                                        else:
                                            det = DetalleListaVerificacionGuiaDocente.objects.get(status=True,
                                                                                                  guiadocentesilabosemanal=codigoguiadocente,
                                                                                                  listaverificacion=lista)
                                            det.cumple = True
                                            det.observacion = ""
                                            det.save(request)
                                    log(u'Aprobo masivo guia de docente: %s - %s' % (codigoguiadocente, codigoguiadocente.silabosemanal), request, "edit")
                            except Exception as ex:
                                lista_errores.append({"actividad": "Guía de docente", "observacion": codigoguiadocente.__str__(), "error": ex.__str__()})

                    if listadiapositiva:
                        from Moodle_Funciones import CrearRecursoMoodle
                        for lista in listadiapositiva:
                            codigodiapositiva = DiapositivaSilaboSemanal.objects.get(pk=lista)
                            personacrea = Persona.objects.get(usuario_id=codigodiapositiva.usuario_creacion_id, status=True)
                            try:
                                value, msg = CrearRecursoMoodle(codigodiapositiva.id, personacrea)
                                if not value:
                                    raise NameError(msg)
                                else:
                                    materia = codigodiapositiva.silabosemanal.silabo.materia
                                    materia.actualizarhtml = True
                                    materia.save()
                                    historialdi1 = HistorialaprobacionDiapositiva(diapositiva=codigodiapositiva,
                                                                                  estado_id=2,
                                                                                  observacion='APROBADO')
                                    historialdi1.save(request)
                                    historialdi2 = HistorialaprobacionDiapositiva(diapositiva=codigodiapositiva,
                                                                                  estado_id=4,
                                                                                  observacion='MIGRADO A MOODLE')
                                    historialdi2.save(request)
                                    for lista in ListaVerificacion.objects.filter(status=True, tiporecurso=codigodiapositiva.tiporecurso):

                                        if not DetalleListaVerificacionDiapositiva.objects.filter(status=True,
                                                                                                  diapositivasilabosemanal=codigodiapositiva,
                                                                                                  listaverificacion=lista).exists():
                                            det = DetalleListaVerificacionDiapositiva(
                                                diapositivasilabosemanal=codigodiapositiva,
                                                listaverificacion=lista,
                                                cumple=True
                                            )
                                            det.save(request)
                                        else:
                                            det = DetalleListaVerificacionDiapositiva.objects.get(status=True,
                                                                                                  diapositivasilabosemanal=codigodiapositiva,
                                                                                                  listaverificacion=lista)
                                            det.cumple = True
                                            det.observacion = ""
                                            det.save(request)
                                    log(u'Aprobo masivo presentación : %s - %s' % (codigodiapositiva, codigodiapositiva.silabosemanal), request, "edit")
                            except Exception as ex:
                                lista_errores.append({"actividad": "Presentación", "nombre": codigodiapositiva.nombre, "descripcion": codigodiapositiva.__str__(), "error": ex.__str__()})

                    if listacompendio:
                        from Moodle_Funciones import CrearCompendioMoodle
                        for lista in listacompendio:
                            codigocompendio = CompendioSilaboSemanal.objects.get(pk=lista)
                            materia = codigocompendio.silabosemanal.silabo.materia
                            materia.actualizarhtml = True
                            materia.save()
                            lista_formato = []
                            if codigocompendio.mis_formatos(periodo):
                                for format in codigocompendio.mis_formatos(periodo):
                                    lista_formato.append(format.nombre)
                            if lista_formato and 'word' in lista_formato:
                                codigocompendio.estado_id = 5
                                codigocompendio.save(request)
                                historialc1 = HistorialaprobacionCompendio(compendio=codigocompendio,
                                                                           estado_id=5,
                                                                           observacion='APROBADO PRA REVISIÓN CRAI')
                                historialc1.save(request)
                                lista_cor = []
                                nombre_carrera = codigocompendio.silabosemanal.silabo.materia.asignaturamalla.malla.carrera.nombre_completo()
                                lista_cor.append('sop_docencia_crai@unemi.edu.ec')
                                send_html_mail("SGA - REVISIÓN DE RECURSOS - %s" % nombre_carrera,
                                               "emails/sop_doc_crai_recursos.html",
                                               {'sistema': u'SGA - UNEMI',
                                                'fecha': datetime.now().date(),
                                                'hora': datetime.now().time(),
                                                'recurso': codigocompendio,
                                                'tipo': 1,
                                                'nombrecarrera': nombre_carrera,
                                                't': miinstitucion()
                                                },
                                               lista_cor,
                                               [],
                                               cuenta=variable_valor('CUENTAS_CORREOS')[0]
                                               )
                                for lista in ListaVerificacion.objects.filter(status=True, tiporecurso=codigocompendio.tiporecurso):
                                    if not DetalleListaVerificacionGuiaEstudiante.objects.filter(status=True,
                                                                                                 guiaestudiantesilabosemanal=codigocompendio,
                                                                                                 listaverificacion=lista).exists():
                                        det = DetalleListaVerificacionGuiaEstudiante(
                                            guiaestudiantesilabosemanal=codigocompendio,
                                            listaverificacion=lista,
                                            cumple=True
                                        )
                                        det.save(request)
                                    else:
                                        det = DetalleListaVerificacionGuiaEstudiante.objects.get(status=True,
                                                                                                 guiaestudiantesilabosemanal=codigocompendio,
                                                                                                 listaverificacion=lista)
                                        det.cumple = True
                                        det.observacion = ""
                                        det.save(request)
                            else:
                                personacrea = Persona.objects.get(usuario_id=codigocompendio.usuario_creacion_id, status=True)
                                try:
                                    value, msg = CrearCompendioMoodle(codigocompendio.id, personacrea)
                                    if not value:
                                        raise NameError(msg)
                                    else:
                                        historialc1 = HistorialaprobacionCompendio(compendio=codigocompendio,
                                                                                   estado_id=2,
                                                                                   observacion='APROBADO')
                                        historialc1.save(request)
                                        historialc2 = HistorialaprobacionCompendio(compendio=codigocompendio,
                                                                                   estado_id=4,
                                                                                   observacion='MIGRADO A MOODLE')
                                        historialc2.save(request)
                                        for lista in ListaVerificacion.objects.filter(status=True, tiporecurso=codigocompendio.tiporecurso):
                                            if not DetalleListaVerificacionGuiaEstudiante.objects.filter(status=True,
                                                                                                         guiaestudiantesilabosemanal=codigocompendio,
                                                                                                         listaverificacion=lista).exists():
                                                det = DetalleListaVerificacionGuiaEstudiante(
                                                    guiaestudiantesilabosemanal=codigocompendio,
                                                    listaverificacion=lista,
                                                    cumple=True
                                                )
                                                det.save(request)
                                            else:
                                                det = DetalleListaVerificacionGuiaEstudiante.objects.get(status=True,
                                                                                                         guiaestudiantesilabosemanal=codigocompendio,
                                                                                                         listaverificacion=lista)
                                                det.cumple = True
                                                det.observacion = ""
                                                det.save(request)
                                except Exception as ex:
                                    lista_errores.append({"actividad": "Compendio", "descripcion": codigocompendio.__str__(), "error": ex.__str__()})
                            log(u'Aprobo masivo compendio : %s - %s' % (codigocompendio, codigocompendio.silabosemanal), request, "edit")

                    if listamaterial:
                        from Moodle_Funciones import CrearMaterialesMoodle
                        for lista in listamaterial:
                            codigomaterial = MaterialAdicionalSilaboSemanal.objects.get(pk=lista)
                            personacrea = Persona.objects.get(usuario_id=codigomaterial.usuario_creacion_id, status=True)
                            try:
                                value, msg = CrearMaterialesMoodle(codigomaterial.id, personacrea)
                                if not value:
                                    raise NameError(msg)
                                else:
                                    materia = codigomaterial.silabosemanal.silabo.materia
                                    materia.actualizarhtml = True
                                    materia.save()
                                    historialm1 = HistorialaprobacionMaterial(material=codigomaterial,
                                                                              estado_id=2,
                                                                              observacion='APROBADO')
                                    historialm1.save(request)
                                    historialm2 = HistorialaprobacionMaterial(material=codigomaterial,
                                                                              estado_id=4,
                                                                              observacion='MIGRADO A MOODLE')
                                    historialm2.save(request)
                                    for lista in ListaVerificacion.objects.filter(status=True, tiporecurso=codigomaterial.tiporecursos):
                                        if not DetalleListaVerificacionMaterialAdicional.objects.filter(status=True,
                                                                                                        materialadicionalsilabosemanal=codigomaterial,
                                                                                                        listaverificacion=lista).exists():
                                            det = DetalleListaVerificacionMaterialAdicional(
                                                materialadicionalsilabosemanal=codigomaterial,
                                                listaverificacion=lista,
                                                cumple=True
                                            )
                                            det.save(request)
                                        else:
                                            det = DetalleListaVerificacionMaterialAdicional.objects.get(status=True,
                                                                                                        materialadicionalsilabosemanal=codigomaterial,
                                                                                                        listaverificacion=lista)
                                            det.cumple = True
                                            det.observacion = ""
                                            det.save(request)
                                    log(u'Aprobo masivo material adicional : %s - %s' % (codigomaterial, codigomaterial.silabosemanal), request, "edit")
                            except Exception as ex:
                                lista_errores.append({"actividad": "Material complementario", "nombre": codigomaterial.nombre, "descripcion": codigomaterial.__str__(), "error": ex.__str__()})

                    # if idusuario > 0:
                    #     nombredocente = Persona.objects.get(usuario_id=idusuario, status=True)
                    #     correo = nombredocente.lista_emails_envio()
                    #     estado = 'APROBADO'
                    #     cuenta=CUENTAS_CORREOS[3][1]
                    #     send_html_mail("SGA - PLANIFICACIÓN DE RECURSOS.", "emails/recursoaprobacionindividual.html",
                    #                    {'sistema': request.session['nombresistema'], 'nombredocente': nombredocente,
                    #                     'estado': estado, 't': miinstitucion()}, correo, [], coneccion=coneccion)
                    return JsonResponse({"result": "ok", "errores": lista_errores})
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos. %s" % ex})



            elif action == 'reporterecursoscumfac':
                try:
                    listado = []
                    data['fechaactual'] = datetime.now().date()
                    data['id_fini'] = fechaini = request.POST['id_fini_autor']
                    data['id_fin'] = fechafin = request.POST['id_ffin_autor']
                    data['coordinacion'] = coordinacion = Coordinacion.objects.get(pk=request.POST['cod_facultad'])

                    responsableccordinacion = '-'
                    if coordinacion.responsable_periodo(periodo):
                        responsableccordinacion = coordinacion.responsable_periodo(periodo).persona
                    data['responsableccordinacion'] = responsableccordinacion
                    # materiassilabos = Silabo.objects.filter(pk=14611,materia__nivel__periodo=periodo, materia__asignaturamalla__malla__carrera__coordinacion=coordinacion, materia__status=True, status=True).order_by('materia__asignaturamalla__malla__carrera_id', 'materia__asignaturamalla__nivelmalla_id')
                    materiassilabos = Silabo.objects.filter(materia__nivel__periodo=periodo,
                                                            materia__asignaturamalla__malla__carrera__coordinacion=coordinacion,
                                                            materia__status=True, status=True).order_by(
                        'materia__asignaturamalla__malla__carrera_id', 'materia__asignaturamalla__nivelmalla_id')
                    usucreacion = None
                    to_promedio_to = 0.0
                    for mate in materiassilabos:
                        listadocompendios = []
                        listadodiapositiva = []
                        listadoguiadocente = []
                        listadoguiaestudiante = []
                        listadotareas = []
                        listadoforos = []
                        listadotest = []
                        if mate.tiene_recursos:
                            if TareaSilaboSemanal.objects.filter(silabosemanal__silabo=mate):
                                usucreacion = TareaSilaboSemanal.objects.filter(silabosemanal__silabo=mate)[0].usuario_creacion_id
                            if ForoSilaboSemanal.objects.filter(silabosemanal__silabo=mate):
                                usucreacion = ForoSilaboSemanal.objects.filter(silabosemanal__silabo=mate)[0].usuario_creacion_id
                            if TestSilaboSemanal.objects.filter(silabosemanal__silabo=mate):
                                usucreacion = TestSilaboSemanal.objects.filter(silabosemanal__silabo=mate)[0].usuario_creacion_id
                            if not usucreacion:
                                profesormateria = ProfesorMateria.objects.filter(tipoprofesor_id=1, materia_id=mate.materia_id, status=True).exclude(tipoprofesor_id=10)[0]
                            else:
                                if ProfesorMateria.objects.filter(profesor__persona__usuario_id=usucreacion, materia_id=mate.materia_id, status=True).exclude(tipoprofesor_id=10).exists():
                                    profesormateria = ProfesorMateria.objects.filter(profesor__persona__usuario_id=usucreacion, materia_id=mate.materia_id, status=True).exclude(tipoprofesor_id=10)[0]
                                else:
                                    if ProfesorMateria.objects.filter(tipoprofesor_id=1, materia_id=mate.materia_id, status=True).exclude(tipoprofesor_id=10).exists():
                                        profesormateria = ProfesorMateria.objects.filter(tipoprofesor_id=1, materia_id=mate.materia_id, status=True).exclude(tipoprofesor_id=10)[0]
                                    else:
                                        profesormateria = ProfesorMateria.objects.filter(materia_id=mate.materia_id, status=True).exclude(tipoprofesor_id=10)[0]

                            unidades = UnidadesPeriodo.objects.filter(
                                Q(fechainicio__range=(fechaini, fechafin)) | Q(fechafin__range=(fechaini, fechafin)),
                                tipoprofesor=profesormateria.tipoprofesor, periodo=periodo, status=True)
                            # cantidadunidades = unidades.values_list('orden').distinct().count()
                            cantidadunidades = unidades.count()
                            totalrecursos = 0
                            totalaprobadas = 0
                            totalesporcentaje = 0
                            listalineamiento = LineamientoRecursoPeriodo.objects.filter(periodo=periodo,
                                                                                        tipoprofesor_id=profesormateria.tipoprofesor.id,
                                                                                        status=True)
                            for linea in listalineamiento:
                                if linea.tiporecurso == 1:
                                    listacompendio = CompendioSilaboSemanal.objects.values_list('id', 'fecha_creacion',
                                                                                                'silabosemanal_id').filter(
                                        fecha_creacion__range=(fechaini, fechafin),
                                        silabosemanal__silabo__materia=mate.materia, status=True, estado_id__in=[2, 4])
                                    for reccompendio in listacompendio:
                                        unicompendio = DetalleSilaboSemanalTema.objects.values_list(
                                            'temaunidadresultadoprogramaanalitico__unidadresultadoprogramaanalitico__orden',
                                            flat=True).filter(silabosemanal_id=reccompendio[2])[0]
                                        for comunidades in unidades:
                                            if unicompendio == comunidades.orden and reccompendio[1].date() > comunidades.fechafin:
                                                listadocompendios.append(reccompendio[0])
                                    totalescompendio = listacompendio.count() - len(listadocompendios)
                                    # if listacompendio.count() >= (linea.cantidad * cantidadunidades):
                                    if totalescompendio >= (linea.cantidad * cantidadunidades):
                                        totalaprobadas = totalaprobadas + (linea.cantidad * cantidadunidades)
                                    else:
                                        totalaprobadas = totalaprobadas + totalescompendio

                                if linea.tiporecurso == 2:
                                    listapresentacion = DiapositivaSilaboSemanal.objects.values_list('id',
                                                                                                     'fecha_creacion',
                                                                                                     'silabosemanal_id').filter(fecha_creacion__range=(fechaini, fechafin), silabosemanal__silabo__materia=mate.materia, status=True, estado_id__in=[2, 4])
                                    for recpresentacion in listapresentacion:
                                        unipresentacion = DetalleSilaboSemanalTema.objects.values_list(
                                            'temaunidadresultadoprogramaanalitico__unidadresultadoprogramaanalitico__orden',
                                            flat=True).filter(silabosemanal_id=recpresentacion[2])[0]
                                        for diaunidades in unidades:
                                            if unipresentacion == diaunidades.orden and recpresentacion[1].date() > diaunidades.fechafin:
                                                listadodiapositiva.append(recpresentacion[0])
                                    totalesdiapositiva = listapresentacion.count() - len(listadodiapositiva)
                                    if totalesdiapositiva >= (linea.cantidad * cantidadunidades):
                                        totalaprobadas = totalaprobadas + (linea.cantidad * cantidadunidades)
                                    else:
                                        totalaprobadas = totalaprobadas + totalesdiapositiva

                                if linea.tiporecurso == 3:
                                    listaguiadocente = GuiaDocenteSilaboSemanal.objects.values_list('id',
                                                                                                    'fecha_creacion',
                                                                                                    'silabosemanal_id').filter(fecha_creacion__range=(fechaini, fechafin), silabosemanal__silabo__materia=mate.materia, status=True, estado_id__in=[2, 4])
                                    for recdocente in listaguiadocente:
                                        uniguiadocente = DetalleSilaboSemanalTema.objects.values_list(
                                            'temaunidadresultadoprogramaanalitico__unidadresultadoprogramaanalitico__orden',
                                            flat=True).filter(silabosemanal_id=recdocente[2])[0]
                                        for docunidades in unidades:
                                            if uniguiadocente == docunidades.orden and recdocente[1].date() > docunidades.fechafin:
                                                listadoguiadocente.append(recdocente[0])
                                    totalesguiadocente = listaguiadocente.count() - len(listadoguiadocente)
                                    if totalesguiadocente >= (linea.cantidad * cantidadunidades):
                                        totalaprobadas = totalaprobadas + (linea.cantidad * cantidadunidades)
                                    else:
                                        totalaprobadas = totalaprobadas + totalesguiadocente

                                if linea.tiporecurso == 4:
                                    listaguiaestudiante = GuiaEstudianteSilaboSemanal.objects.values_list('id',
                                                                                                          'fecha_creacion',
                                                                                                          'silabosemanal_id').filter(fecha_creacion__range=(fechaini, fechafin), silabosemanal__silabo__materia=mate.materia, status=True, estado_id__in=[2, 4])
                                    for recestudiante in listaguiaestudiante:
                                        uniguiaestudiante = DetalleSilaboSemanalTema.objects.values_list(
                                            'temaunidadresultadoprogramaanalitico__unidadresultadoprogramaanalitico__orden',
                                            flat=True).filter(silabosemanal_id=recestudiante[2])[0]
                                        for estunidades in unidades:
                                            if uniguiaestudiante == estunidades.orden and recestudiante[1].date() > estunidades.fechafin:
                                                listadoguiaestudiante.append(recestudiante[0])
                                    totalesguiaestudiante = listaguiaestudiante.count() - len(listadoguiaestudiante)
                                    if totalesguiaestudiante >= (linea.cantidad * cantidadunidades):
                                        totalaprobadas = totalaprobadas + (linea.cantidad * cantidadunidades)
                                    else:
                                        totalaprobadas = totalaprobadas + totalesguiaestudiante

                                if linea.tiporecurso == 5:
                                    listatarea = TareaSilaboSemanal.objects.values_list('id', 'fecha_creacion',
                                                                                        'silabosemanal_id').filter(fecha_creacion__range=(fechaini, fechafin), silabosemanal__silabo__materia=mate.materia, status=True, estado_id__in=[2, 4])
                                    for rectarea in listatarea:
                                        unitarea = DetalleSilaboSemanalTema.objects.values_list(
                                            'temaunidadresultadoprogramaanalitico__unidadresultadoprogramaanalitico__orden',
                                            flat=True).filter(silabosemanal_id=rectarea[2])[0]
                                        for tareaunidades in unidades:
                                            if unitarea == tareaunidades.orden and rectarea[1].date() > tareaunidades.fechafin:
                                                listadotareas.append(rectarea[0])
                                    totalestareas = listatarea.count() - len(listadotareas)
                                    if totalestareas >= (linea.cantidad * cantidadunidades):
                                        totalaprobadas = totalaprobadas + (linea.cantidad * cantidadunidades)
                                    else:
                                        totalaprobadas = totalaprobadas + totalestareas

                                if linea.tiporecurso == 6:
                                    listaforo = ForoSilaboSemanal.objects.values_list('id', 'fecha_creacion',
                                                                                      'silabosemanal_id').filter(fecha_creacion__range=(fechaini, fechafin), silabosemanal__silabo__materia=mate.materia, status=True, estado_id__in=[2, 4])
                                    for recforo in listaforo:
                                        uniforo = DetalleSilaboSemanalTema.objects.values_list(
                                            'temaunidadresultadoprogramaanalitico__unidadresultadoprogramaanalitico__orden',
                                            flat=True).filter(silabosemanal_id=recforo[2])[0]
                                        for forounidades in unidades:
                                            if uniforo == forounidades.orden and recforo[1].date() > forounidades.fechafin:
                                                listadoforos.append(recforo[0])
                                    totalesforos = listaforo.count() - len(listadoforos)
                                    if totalesforos >= (linea.cantidad * cantidadunidades):
                                        totalaprobadas = totalaprobadas + (linea.cantidad * cantidadunidades)
                                    else:
                                        totalaprobadas = totalaprobadas + totalesforos

                                if linea.tiporecurso == 7:
                                    listatest = TestSilaboSemanal.objects.values_list('id', 'fecha_creacion',
                                                                                      'silabosemanal_id').filter(fecha_creacion__range=(fechaini, fechafin), silabosemanal__silabo__materia=mate.materia, status=True, estado_id__in=[2, 4])
                                    for rectest in listatest:
                                        unitest = DetalleSilaboSemanalTema.objects.values_list('temaunidadresultadoprogramaanalitico__unidadresultadoprogramaanalitico__orden',
                                                                                               flat=True).filter(silabosemanal_id=rectest[2])[0]
                                        for testunidades in unidades:
                                            if unitest == testunidades.orden and rectest[1].date() > testunidades.fechafin:
                                                listadotest.append(rectest[0])
                                    totalestest = listatest.count() - len(listadotest)
                                    if totalestest >= (linea.cantidad * cantidadunidades):
                                        totalaprobadas = totalaprobadas + (linea.cantidad * cantidadunidades)
                                    else:
                                        totalaprobadas = totalaprobadas + totalestest
                            #
                            suma = listalineamiento.aggregate(valor=Sum('cantidad'))
                            if cantidadunidades > 0:
                                if suma['valor']:
                                    totalrecursos = suma['valor'] * cantidadunidades
                                    totalesporcentaje = (totalaprobadas / totalrecursos) * 100
                                else:
                                    totalrecursos = 0
                                    totalesporcentaje = 0
                            else:
                                totalrecursos = 0
                        totalesfaltantes = len(listadocompendios) + len(listadodiapositiva) + len(
                            listadoguiadocente) + len(listadoguiaestudiante) + len(listadotareas) + len(
                            listadoforos) + len(listadotest)
                        to_promedio_to += totalesporcentaje
                        listado.append([profesormateria, cantidadunidades, totalrecursos, totalaprobadas, totalesporcentaje, mate.id, totalesfaltantes])
                    data['listadorecurso'] = [[1, 'TAREA'], [2, 'FORO'], [3, 'TEST'], [4, 'COMPENDIO'],
                                              [5, 'GUÍA DEL DOCENTE'], [6, 'GUÍA DEL ESTUDIANTE'],
                                              [7, 'MATERIALES COMPLEMENTARIOS'], [8, 'PRESENTACIÓN']]
                    return conviert_html_to_pdf(
                        'aprobar_silabo/recursosilabocumplimientofac_pdf.html',
                        {
                            'pagesize': 'A4',
                            'data': data,
                            'listado': listado,
                            'total_promedio': (to_promedio_to / len(listado)),
                        }
                    )
                except Exception as ex:
                    pass

            elif action == 'reporterecursoscumfacv2':
                try:
                    listado = []
                    data['fechaactual'] = datetime.now().date()
                    data['codcarrera'] = codcarrera = request.POST['codcarrera'] if 'codcarrera' in request.POST else 0
                    data['id_fini'] = fechaini = request.POST['id_fini_autor']
                    data['id_fin'] = fechafin = request.POST['id_ffin_autor']
                    data['coordinacion'] = coordinacion = Coordinacion.objects.get(pk=request.POST['cod_facultad'])
                    responsableccordinacion = '-'
                    if coordinacion.responsable_periodo(periodo):
                        responsableccordinacion = coordinacion.responsable_periodo(periodo).persona
                    data['responsableccordinacion'] = responsableccordinacion
                    # materiassilabos = Silabo.objects.filter(materia_id=39942,materia__nivel__periodo=periodo, materia__asignaturamalla__malla__carrera__coordinacion=coordinacion, materia__status=True, status=True).order_by('profesor__persona__apellido1','profesor__persona__apellido2')
                    # materiassilabos = Silabo.objects.filter(materia_id=41662,materia__nivel__periodo=periodo, materia__asignaturamalla__malla__carrera__coordinacion=coordinacion, materia__status=True, status=True).order_by('profesor__persona__apellido1','profesor__persona__apellido2')
                    if coordinacion.id == 1:
                        materiassilabos = Silabo.objects.filter(materia__nivel__periodo=periodo, materia__asignaturamalla__malla__carrera__coordinacion=coordinacion, materia__asignaturamalla__nivelmalla_id__in=[1, 2, 3, 4, 5], materia__status=True, status=True).order_by('profesor__persona__apellido1', 'profesor__persona__apellido2')
                    else:
                        materiassilabos = Silabo.objects.filter(materia__nivel__periodo=periodo, materia__asignaturamalla__malla__carrera__coordinacion=coordinacion, materia__status=True, status=True).order_by('profesor__persona__apellido1', 'profesor__persona__apellido2')

                    if int(codcarrera) > 0:
                        materiassilabos = materiassilabos.filter(materia__asignaturamalla__malla__carrera_id=codcarrera)
                    c = 0
                    usucreacion = None
                    to_promedio_to = 0.0
                    listadonomostrar = [2, 5, 8, 10]
                    for mate in materiassilabos[0:5]:
                        print(c)
                        # print(mate.materia_id)
                        # print(mate.materia)
                        totalpresentacionesaprobadas = 0
                        totalmaterialesaprobadas = 0
                        totaltestaprobadas = 0
                        totaltareasaprobadas = 0
                        totaltareasaprobadasa = 0
                        totalforosaprobadas = 0
                        totalpracticasaprobadas = 0
                        totalcompendiosaprobadas = 0
                        totalguiasestudiantesaprobadas = 0
                        totalvidmagistralaprobadas = 0
                        listadodiapositiva = []
                        listadotareatest = []
                        listadoforotarea = []
                        listadopexperimental = []
                        listadoguiadocente = []
                        listadomaterial = []
                        listadovidmagistral = []
                        listadoguiaestudiante = []
                        if mate.tiene_recursos and mate.materia.profesormateria_set.filter(status=True):
                            if TareaSilaboSemanal.objects.filter(silabosemanal__silabo=mate) and not usucreacion:
                                usucreacion = TareaSilaboSemanal.objects.filter(silabosemanal__silabo=mate)[0].usuario_creacion_id
                            if ForoSilaboSemanal.objects.filter(silabosemanal__silabo=mate) and not usucreacion:
                                usucreacion = ForoSilaboSemanal.objects.filter(silabosemanal__silabo=mate)[0].usuario_creacion_id
                            if TestSilaboSemanal.objects.filter(silabosemanal__silabo=mate) and not usucreacion:
                                usucreacion = TestSilaboSemanal.objects.filter(silabosemanal__silabo=mate)[0].usuario_creacion_id
                            if not usucreacion:
                                profesormateria = ProfesorMateria.objects.filter(tipoprofesor_id=1, materia_id=mate.materia_id, status=True).exclude(tipoprofesor_id__in=[4, 10])[0]
                            else:
                                if ProfesorMateria.objects.filter(profesor__persona__usuario_id=usucreacion, materia_id=mate.materia_id, status=True).exclude(tipoprofesor_id__in=[4, 10]).exists():
                                    profesormateria = ProfesorMateria.objects.filter(profesor__persona__usuario_id=usucreacion, materia_id=mate.materia_id, status=True).exclude(tipoprofesor_id__in=[4, 10])[0]
                                    if profesormateria.tipoprofesor_id in listadonomostrar:
                                        if ProfesorMateria.objects.filter(materia_id=mate.materia_id, status=True).exclude(tipoprofesor_id__in=[2, 5, 4, 8, 10]):
                                            profesormateria = ProfesorMateria.objects.filter(materia_id=mate.materia_id, status=True).exclude(tipoprofesor_id__in=[2, 5, 4, 8, 10])[0]
                                        else:
                                            profesormateria = None
                                else:
                                    if ProfesorMateria.objects.filter(tipoprofesor_id=1, materia_id=mate.materia_id, status=True).exclude(tipoprofesor_id__in=[4, 10]).exists():
                                        profesormateria = ProfesorMateria.objects.filter(tipoprofesor_id=1, materia_id=mate.materia_id, status=True).exclude(tipoprofesor_id__in=[4, 10])[0]
                                    else:
                                        profesormateria = ProfesorMateria.objects.filter(materia_id=mate.materia_id, status=True).exclude(tipoprofesor_id__in=[4, 10])[0]
                                        if profesormateria.tipoprofesor_id in listadonomostrar:
                                            if ProfesorMateria.objects.filter(materia_id=mate.materia_id, status=True).exclude(tipoprofesor_id__in=[2, 4, 5, 8, 10]):
                                                profesormateria = ProfesorMateria.objects.filter(materia_id=mate.materia_id, status=True).exclude(tipoprofesor_id__in=[2, 4, 5, 8, 10])[0]
                                            else:
                                                profesormateria = None
                            if profesormateria:
                                unidades = UnidadesPeriodo.objects.filter(Q(fechainicio__range=(fechaini, fechafin)) | Q(fechafin__range=(fechaini, fechafin)), tipoprofesor=profesormateria.tipoprofesor, periodo=periodo, status=True)
                                # cantidadunidades = unidades.values_list('orden').distinct().count()
                                cantidadparciales = unidades.values_list('parcial').distinct().count()
                                cantidadunidades = unidades.count()
                                totalrecursos = 0
                                totalaprobadas = 0
                                totalesporcentaje = 0
                                textoape = ''
                                if int(mate.materia.asignaturamalla.horasapesemanal) == 0:
                                    listalineamiento = LineamientoRecursoPeriodo.objects.filter(periodo=periodo, tipoprofesor_id=profesormateria.tipoprofesor.id, status=True).exclude(tiporecurso=10)
                                else:
                                    textoape = '(APE)'
                                    listalineamiento = LineamientoRecursoPeriodo.objects.filter(periodo=periodo, tipoprofesor_id=profesormateria.tipoprofesor.id, status=True)
                                for linea in listalineamiento:
                                    if linea.tiporecurso == 1:
                                        consulatacompendio = HistorialaprobacionCompendio.objects.values_list('compendio_id', 'compendio__silabosemanal_id', 'compendio__silabosemanal__detallesilabosemanaltema__temaunidadresultadoprogramaanalitico__unidadresultadoprogramaanalitico__orden').filter(fecha_creacion__date__range=(fechaini, fechafin), compendio__silabosemanal__silabo__materia=mate.materia, compendio__status=True, status=True, estado_id__in=[2, 4]).annotate(
                                            formatted_date=Func(F('fecha_creacion'), Value('yyyy-MM-dd'), function='to_char', output_field=CharField())).distinct('compendio_id')
                                        listacompendio = consulatacompendio.filter(fecha_creacion__date__range=(fechaini, fechafin))
                                        totalcompendiosaprobadas = consulatacompendio.count()
                                        totalescompendio = listacompendio.count()
                                        # if totalescompendio >= (linea.cantidad * cantidadunidades):
                                        #     totalaprobadas = totalaprobadas + (linea.cantidad * cantidadunidades)
                                        # else:
                                        #     totalaprobadas = totalaprobadas + totalescompendio
                                        for diaunidades in unidades:
                                            cuentacompendio = consulatacompendio.filter(compendio__silabosemanal__detallesilabosemanaltema__temaunidadresultadoprogramaanalitico__unidadresultadoprogramaanalitico__orden=diaunidades.orden, fecha_creacion__date__lte=diaunidades.fechafin).count()
                                            if cuentacompendio > linea.cantidad:
                                                totalaprobadas = totalaprobadas + linea.cantidad
                                            else:
                                                totalaprobadas = totalaprobadas + cuentacompendio

                                    if linea.tiporecurso == 2:
                                        consulatadiapositiva = HistorialaprobacionDiapositiva.objects.values_list('diapositiva_id', 'diapositiva__silabosemanal_id', 'diapositiva__silabosemanal__detallesilabosemanaltema__temaunidadresultadoprogramaanalitico__unidadresultadoprogramaanalitico__orden').filter(fecha_creacion__date__lte=fechafin, diapositiva__silabosemanal__silabo__materia=mate.materia, status=True, diapositiva__status=True, estado_id__in=[2]).annotate(
                                            formatted_date=Func(F('fecha_creacion'), Value('yyyy-MM-dd'), function='to_char', output_field=CharField())).distinct('diapositiva_id')
                                        listapresentacion = consulatadiapositiva.filter(fecha_creacion__date__range=(fechaini, fechafin))
                                        totalpresentacionesaprobadas = consulatadiapositiva.count()
                                        totalesdiapositiva = listapresentacion.count()

                                        # for recpresentacion in listapresentacion:
                                        # unipresentacion = DetalleSilaboSemanalTema.objects.values_list('temaunidadresultadoprogramaanalitico__unidadresultadoprogramaanalitico__orden', flat=True).filter(silabosemanal_id=recpresentacion[2])[0]
                                        for diaunidades in unidades:
                                            cuentadiapositiva = consulatadiapositiva.filter(diapositiva__silabosemanal__detallesilabosemanaltema__temaunidadresultadoprogramaanalitico__unidadresultadoprogramaanalitico__orden=diaunidades.orden, fecha_creacion__date__lte=diaunidades.fechafin).count()
                                            if cuentadiapositiva > linea.cantidad:
                                                totalaprobadas = totalaprobadas + linea.cantidad
                                            else:
                                                totalaprobadas = totalaprobadas + cuentadiapositiva
                                        # if totalesdiapositiva >= (linea.cantidad * cantidadunidades):
                                        #     totalaprobadas = totalaprobadas + (linea.cantidad * cantidadunidades)
                                        # else:
                                        #     totalaprobadas = totalaprobadas + totalesdiapositiva

                                    if linea.tiporecurso == 3:
                                        listaguiadocente = GuiaDocenteSilaboSemanal.objects.values_list('id', 'fecha_creacion', 'silabosemanal_id').filter(fecha_creacion__range=(fechaini, fechafin), silabosemanal__silabo__materia=mate.materia, status=True, estado_id__in=[2, 4])
                                        for recdocente in listaguiadocente:
                                            uniguiadocente = DetalleSilaboSemanalTema.objects.values_list('temaunidadresultadoprogramaanalitico__unidadresultadoprogramaanalitico__orden', flat=True).filter(silabosemanal_id=recdocente[2])[0]
                                            for docunidades in unidades:
                                                if uniguiadocente == docunidades.orden and recdocente[1].date() > docunidades.fechafin:
                                                    listadoguiadocente.append(recdocente[0])
                                        totalesguiadocente = listaguiadocente.count() - len(listadoguiadocente)
                                        if totalesguiadocente >= (linea.cantidad * cantidadunidades):
                                            totalaprobadas = totalaprobadas + (linea.cantidad * cantidadunidades)
                                        else:
                                            totalaprobadas = totalaprobadas + totalesguiadocente

                                    if linea.tiporecurso == 4:
                                        consulataguiaestudiante = HistorialaprobacionGuiaEstudiante.objects.values_list('guiaestudiante_id', 'guiaestudiante__silabosemanal_id', 'guiaestudiante__silabosemanal__detallesilabosemanaltema__temaunidadresultadoprogramaanalitico__unidadresultadoprogramaanalitico__orden').filter(fecha_creacion__date__lte=fechafin, guiaestudiante__silabosemanal__silabo__materia=mate.materia, status=True, guiaestudiante__status=True, estado_id__in=[2]).annotate(
                                            formatted_date=Func(F('fecha_creacion'), Value('yyyy-MM-dd'), function='to_char', output_field=CharField())).distinct('guiaestudiante_id')
                                        listaguiaestudiante = consulataguiaestudiante.filter(fecha_creacion__date__range=(fechaini, fechafin))
                                        totalguiasestudiantesaprobadas = consulataguiaestudiante.count()
                                        totalesguiaestudiante = listaguiaestudiante.count()

                                        for diaunidades in unidades:
                                            cuentaguiaestudiante = consulataguiaestudiante.filter(guiaestudiante__silabosemanal__detallesilabosemanaltema__temaunidadresultadoprogramaanalitico__unidadresultadoprogramaanalitico__orden=diaunidades.orden, fecha_creacion__date__lte=diaunidades.fechafin).count()
                                            if cuentaguiaestudiante > linea.cantidad:
                                                totalaprobadas = totalaprobadas + linea.cantidad
                                            else:
                                                totalaprobadas = totalaprobadas + cuentaguiaestudiante
                                        # if totalesguiaestudiante >= (linea.cantidad * cantidadunidades):
                                        #     totalaprobadas = totalaprobadas + (linea.cantidad * cantidadunidades)
                                        # else:
                                        #     totalaprobadas = totalaprobadas + totalesguiaestudiante

                                    if linea.tiporecurso == 8:  # ACD
                                        consulatatest = HistorialaprobacionTest.objects.values_list('test_id', 'test__silabosemanal_id', 'test__silabosemanal__detallesilabosemanaltema__temaunidadresultadoprogramaanalitico__unidadresultadoprogramaanalitico__orden').filter(fecha_creacion__date__lte=fechafin, test__silabosemanal__silabo__materia=mate.materia, status=True, test__status=True, estado_id__in=[2]).annotate(
                                            formatted_date=Func(F('fecha_creacion'), Value('yyyy-MM-dd'), function='to_char', output_field=CharField())).distinct('test_id')
                                        listatest = consulatatest.filter(fecha_creacion__date__range=(fechaini, fechafin))
                                        totaltestaprobadas = consulatatest.count()
                                        # totalestest = listatest.count()

                                        consulatatarea = HistorialaprobacionTarea.objects.values_list('tarea_id', 'tarea__silabosemanal_id', 'tarea__silabosemanal__detallesilabosemanaltema__temaunidadresultadoprogramaanalitico__unidadresultadoprogramaanalitico__orden').filter(fecha_creacion__date__lte=fechafin, tarea__silabosemanal__silabo__materia=mate.materia, status=True, tarea__status=True, tarea__actividad_id__in=[2, 3], estado_id__in=[2]).annotate(
                                            formatted_date=Func(F('fecha_creacion'), Value('yyyy-MM-dd'), function='to_char', output_field=CharField())).distinct('tarea_id')
                                        listatarea = consulatatarea.filter(fecha_creacion__date__range=(fechaini, fechafin))
                                        totaltareasaprobadas = consulatatarea.count()
                                        # totalestareas = listatarea.count()

                                        # totaltesttarea = totalestest + totalestareas
                                        # if totaltesttarea >= (linea.cantidad * cantidadunidades):
                                        #     totalaprobadas = totalaprobadas + (linea.cantidad * cantidadunidades)
                                        # else:
                                        #     totalaprobadas = totalaprobadas + totaltesttarea
                                        for diaunidades in unidades:
                                            cuentatest = consulatatest.filter(test__silabosemanal__detallesilabosemanaltema__temaunidadresultadoprogramaanalitico__unidadresultadoprogramaanalitico__orden=diaunidades.orden, fecha_creacion__date__lte=diaunidades.fechafin).count()
                                            cuentatarea = consulatatarea.filter(tarea__silabosemanal__detallesilabosemanaltema__temaunidadresultadoprogramaanalitico__unidadresultadoprogramaanalitico__orden=diaunidades.orden, fecha_creacion__date__lte=diaunidades.fechafin).count()
                                            totaltesttarea = cuentatest + cuentatarea
                                            if totaltesttarea > linea.cantidad:
                                                totalaprobadas = totalaprobadas + linea.cantidad
                                            else:
                                                totalaprobadas = totalaprobadas + totaltesttarea

                                    if linea.tiporecurso == 9:  # AA
                                        consulaforo = HistorialaprobacionForo.objects.values_list('foro_id', 'foro__silabosemanal_id', 'foro__silabosemanal__detallesilabosemanaltema__temaunidadresultadoprogramaanalitico__unidadresultadoprogramaanalitico__orden').filter(fecha_creacion__date__lte=fechafin, foro__silabosemanal__silabo__materia=mate.materia, status=True, foro__status=True, estado_id__in=[2]).annotate(
                                            formatted_date=Func(F('fecha_creacion'), Value('yyyy-MM-dd'), function='to_char', output_field=CharField())).distinct('foro_id')
                                        listaforo = consulaforo.filter(fecha_creacion__date__range=(fechaini, fechafin))
                                        totalforosaprobadas = consulaforo.count()
                                        # totalesforos = listaforo.count()

                                        consulatatareaa = HistorialaprobacionTarea.objects.values_list('tarea_id', 'tarea__silabosemanal_id', 'tarea__silabosemanal__detallesilabosemanaltema__temaunidadresultadoprogramaanalitico__unidadresultadoprogramaanalitico__orden').filter(fecha_creacion__date__lte=fechafin, tarea__silabosemanal__silabo__materia=mate.materia, status=True, tarea__status=True, tarea__actividad_id__in=[5, 7, 8], estado_id__in=[2]).annotate(
                                            formatted_date=Func(F('fecha_creacion'), Value('yyyy-MM-dd'), function='to_char', output_field=CharField())).distinct('tarea_id')
                                        listatareaa = consulatatareaa.filter(fecha_creacion__date__range=(fechaini, fechafin))
                                        totaltareasaprobadasa = consulatatareaa.count()
                                        # totalestareasa = listatareaa.count()

                                        # totalforotarea = totalesforos + totalestareasa
                                        # if totalforotarea >= (linea.cantidad * cantidadunidades):
                                        #     totalaprobadas = totalaprobadas + (linea.cantidad * cantidadunidades)
                                        # else:
                                        #     totalaprobadas = totalaprobadas + totalforotarea

                                        for diaunidades in unidades:
                                            cuentaforo = consulaforo.filter(foro__silabosemanal__detallesilabosemanaltema__temaunidadresultadoprogramaanalitico__unidadresultadoprogramaanalitico__orden=diaunidades.orden, fecha_creacion__date__lte=diaunidades.fechafin).count()
                                            cuentatareaa = consulatatareaa.filter(tarea__silabosemanal__detallesilabosemanaltema__temaunidadresultadoprogramaanalitico__unidadresultadoprogramaanalitico__orden=diaunidades.orden, fecha_creacion__date__lte=diaunidades.fechafin).count()
                                            totalforotarea = cuentaforo + cuentatareaa
                                            if totalforotarea > linea.cantidad:
                                                totalaprobadas = totalaprobadas + linea.cantidad
                                            else:
                                                totalaprobadas = totalaprobadas + totalforotarea

                                    if linea.tiporecurso == 10:  # APE
                                        consulatatpractica = HistorialaprobacionTareaPractica.objects.values_list('tareapractica_id', 'tareapractica__silabosemanal_id', 'tareapractica__silabosemanal__detallesilabosemanaltema__temaunidadresultadoprogramaanalitico__unidadresultadoprogramaanalitico__orden').filter(fecha_creacion__date__lte=fechafin, tareapractica__silabosemanal__silabo__materia=mate.materia, status=True, tareapractica__status=True, estado_id__in=[2]).annotate(
                                            formatted_date=Func(F('fecha_creacion'), Value('yyyy-MM-dd'), function='to_char', output_field=CharField())).distinct('tareapractica_id')
                                        listapracticaesperimental = consulatatpractica.filter(fecha_creacion__date__range=(fechaini, fechafin))
                                        totalpracticasaprobadas = consulatatpractica.count()

                                        fechap1 = None
                                        fechap2 = None
                                        cuentapracticap1 = 0
                                        cuentapracticap2 = 0
                                        for diaunidades in unidades:
                                            if int(diaunidades.parcial) == 1:
                                                fechap1 = diaunidades.fechafin
                                            if int(diaunidades.parcial) == 2:
                                                fechap2 = diaunidades.fechafin
                                        if fechap1:
                                            cuentapracticap1 = consulatatpractica.filter(tareapractica__silabosemanal__detallesilabosemanaltema__temaunidadresultadoprogramaanalitico__unidadresultadoprogramaanalitico__orden__in=[1, 2], fecha_creacion__date__lte=fechap1).count()
                                        if fechap2:
                                            cuentapracticap2 = consulatatpractica.filter(tareapractica__silabosemanal__detallesilabosemanaltema__temaunidadresultadoprogramaanalitico__unidadresultadoprogramaanalitico__orden__in=[3, 4], fecha_creacion__date__lte=fechap2).count()

                                        if cuentapracticap1 > 1:
                                            totalaprobadas = totalaprobadas + 1
                                        else:
                                            totalaprobadas = totalaprobadas + cuentapracticap1

                                        if cuentapracticap2 > 1:
                                            totalaprobadas = totalaprobadas + 1
                                        else:
                                            totalaprobadas = totalaprobadas + cuentapracticap2

                                        # totalpexperimental = listapracticaesperimental.count()
                                        #
                                        # if totalpexperimental >= (linea.cantidad * cantidadparciales):
                                        #     totalaprobadas = totalaprobadas + (linea.cantidad * cantidadparciales)
                                        # else:
                                        #     totalaprobadas = totalaprobadas + totalpexperimental

                                    if linea.tiporecurso == 11:
                                        consultamateriales = HistorialaprobacionMaterial.objects.values_list('material_id', 'material__silabosemanal_id', 'material__silabosemanal__detallesilabosemanaltema__temaunidadresultadoprogramaanalitico__unidadresultadoprogramaanalitico__orden').filter(fecha_creacion__date__lte=fechafin, material__silabosemanal__silabo__materia=mate.materia, status=True, material__status=True, estado_id__in=[2]).annotate(
                                            formatted_date=Func(F('fecha_creacion'), Value('yyyy-MM-dd'), function='to_char', output_field=CharField())).distinct('material_id')
                                        listamaterial = consultamateriales.filter(fecha_creacion__date__range=(fechaini, fechafin))
                                        totalmaterialesaprobadas = consultamateriales.count()
                                        for diaunidades in unidades:
                                            cuentamateriales = consultamateriales.filter(material__silabosemanal__detallesilabosemanaltema__temaunidadresultadoprogramaanalitico__unidadresultadoprogramaanalitico__orden=diaunidades.orden, fecha_creacion__date__lte=diaunidades.fechafin).count()
                                            if cuentamateriales > linea.cantidad:
                                                totalaprobadas = totalaprobadas + linea.cantidad
                                            else:
                                                totalaprobadas = totalaprobadas + cuentamateriales
                                        # totalmateriales = listamaterial.count()
                                        #
                                        # if totalmateriales >= (linea.cantidad * cantidadunidades):
                                        #     totalaprobadas = totalaprobadas + (linea.cantidad * cantidadunidades)
                                        # else:
                                        #     totalaprobadas = totalaprobadas + totalmateriales

                                    if linea.tiporecurso == 12:
                                        consultavidmagistral = HistorialaprobacionVideoMagistral.objects.values_list('material_id', 'material__silabosemanal_id', 'material__silabosemanal__detallesilabosemanaltema__temaunidadresultadoprogramaanalitico__unidadresultadoprogramaanalitico__orden').filter(fecha_creacion__date__lte=fechafin, material__silabosemanal__silabo__materia=mate.materia, status=True, material__status=True, estado_id__in=[2]).annotate(
                                            formatted_date=Func(F('fecha_creacion'), Value('yyyy-MM-dd'), function='to_char', output_field=CharField())).distinct('material_id')
                                        vidmagistral = consultavidmagistral.filter(fecha_creacion__date__range=(fechaini, fechafin))
                                        totalvidmagistralaprobadas = consultavidmagistral.count()
                                        # totalvidmagistral = vidmagistral.count()
                                        #
                                        # if totalvidmagistral >= (linea.cantidad * cantidadunidades):
                                        #     totalaprobadas = totalaprobadas + (linea.cantidad * cantidadunidades)
                                        # else:
                                        #     totalaprobadas = totalaprobadas + totalvidmagistral

                                        for diaunidades in unidades:
                                            cuentavidmagistral = consultavidmagistral.filter(material__silabosemanal__detallesilabosemanaltema__temaunidadresultadoprogramaanalitico__unidadresultadoprogramaanalitico__orden=diaunidades.orden, fecha_creacion__date__lte=diaunidades.fechafin).count()
                                            if cuentavidmagistral > linea.cantidad:
                                                totalaprobadas = totalaprobadas + linea.cantidad
                                            else:
                                                totalaprobadas = totalaprobadas + cuentavidmagistral

                                suma = listalineamiento.aggregate(valor=Sum('cantidad'))
                                if cantidadunidades > 0:
                                    if suma['valor']:
                                        if int(mate.materia.asignaturamalla.horasapesemanal) == 0:
                                            totalrecursos = (suma['valor'] * cantidadunidades)
                                        else:
                                            totalrecursos = (suma['valor'] * cantidadunidades) - 2

                                        totalesporcentaje = (totalaprobadas / totalrecursos) * 100
                                    else:
                                        totalrecursos = 0
                                        totalesporcentaje = 0
                                else:
                                    totalrecursos = 0

                            else:
                                totalesporcentaje = 0
                                cantidadunidades = 0
                                totalrecursos = 0
                                totalaprobadas = 0
                                textoape = '-'
                                totalesporcentaje = 0
                        else:
                            totalesporcentaje = 0
                            profesormateria = None
                            cantidadunidades = 0
                            totalrecursos = 0
                            totalaprobadas = 0
                            textoape = ''
                            totalesporcentaje
                        totalesfaltantes = totalcompendiosaprobadas + totalpresentacionesaprobadas + totalguiasestudiantesaprobadas + totalmaterialesaprobadas + totaltestaprobadas + totaltareasaprobadas + totalforosaprobadas + totaltareasaprobadasa + totalpracticasaprobadas + totalvidmagistralaprobadas
                        to_promedio_to += totalesporcentaje
                        c +=1
                        listado.append([profesormateria, cantidadunidades, totalrecursos, totalaprobadas, totalesporcentaje, mate.id, totalesfaltantes, textoape, mate])
                    data['listadorecurso'] = [[1, 'TAREA'], [2, 'FORO'], [3, 'TEST'], [4, 'COMPENDIO'],
                                              [5, 'GUÍA DEL DOCENTE'], [6, 'GUÍA DEL ESTUDIANTE'],
                                              [7, 'MATERIALES COMPLEMENTARIOS'], [8, 'PRESENTACIÓN']]
                    return conviert_html_to_pdf(
                        'aprobar_silabo/recursosilabocumplimientofacv2_pdf.html',
                        {
                            'pagesize': 'A4',
                            'data': data,
                            'listado': listado,
                            'total_promedio': (to_promedio_to / len(listado)),
                        }
                    )
                except Exception as ex:
                    pass

            elif action == 'reporterecursosfac':
                try:
                    data['fechaactual'] = datetime.now().date()
                    data['coordinacion'] = coordinacion = Coordinacion.objects.get(pk=request.POST['id_facultad'])
                    responsableccordinacion = '-'
                    if coordinacion.responsable_periodo(periodo):
                        responsableccordinacion = coordinacion.responsable_periodo(periodo).persona
                    data['responsableccordinacion'] = responsableccordinacion
                    data['materiassilabos'] = Silabo.objects.filter(materia__nivel__periodo=periodo,
                                                                    materia__asignaturamalla__malla__carrera__coordinacion=coordinacion,
                                                                    materia__status=True, status=True).order_by(
                        'materia__asignaturamalla__malla__carrera_id', 'materia__asignaturamalla__nivelmalla_id')
                    data['listadorecurso'] = [[1, 'TAREA'], [2, 'FORO'], [3, 'TEST'], [4, 'COMPENDIO'],
                                              [5, 'GUÍA DEL DOCENTE'], [6, 'GUÍA DEL ESTUDIANTE'],
                                              [7, 'MATERIALES COMPLEMENTARIOS'], [8, 'PRESENTACIÓN'], [9, 'EXPOSICIÓN'], [10, 'TALLER'], [11, 'ANÁLISIS DE CASOS'],
                                              [12, 'TRABAJO DE INVESTIGACIÓN'], [13, 'TRABAJO PRÁCTICO EXPERIMENTAL']]
                    return conviert_html_to_pdf(
                        'aprobar_silabo/recursosilabofac_pdf.html',
                        {
                            'pagesize': 'A4',
                            'data': data,
                        }
                    )
                except Exception as ex:
                    pass

            elif action == 'reporteaprobacionsilabopoa':
                try:
                    data['fechaactual'] = datetime.now().date()
                    data['periodo'] = periodo = Periodo.objects.get(id=request.POST['periodoid'])
                    fechacorte = convertirfecha2(request.POST['fecha']) if 'fecha' in request.POST and request.POST['fecha'] else None
                    # fechadesde = convertirfecha2(request.POST['fechadesde']) if 'fechadesde' in request.POST and request.POST['fechadesde'] else None
                    id_facultad = request.POST['id_facultad'] if 'id_facultad' in request.POST and request.POST['id_facultad'] else None
                    # if not fechadesde:
                    #     raise NameError('fecha no encontrada')
                    if not fechacorte:
                        raise NameError('fecha no encontrada')
                    if not id_facultad or not Coordinacion.objects.filter(pk=id_facultad).exists():
                        raise NameError('facultad no encontrada')
                    # fechadesde = datetime(fechadesde.year, fechadesde.month, fechadesde.day, 23, 59, 59)
                    fechacorte = datetime(fechacorte.year, fechacorte.month, fechacorte.day, 23, 59, 59)

                    data['coordinacion'] = coordinacion = Coordinacion.objects.get(pk=request.POST['id_facultad'])
                    responsableccordinacion = '-'
                    if coordinacion.responsable_periodo(periodo):
                        responsableccordinacion = coordinacion.responsable_periodo(periodo).persona
                    data['responsableccordinacion'] = responsableccordinacion
                    materias = Materia.objects.filter(status=True, nivel__periodo=periodo, nivel__nivellibrecoordinacion__coordinacion=coordinacion, profesormateria__principal=True).exclude(asignaturamalla__malla_id__in=[353, 22])
                    asignaturas = Asignatura.objects.filter(pk__in=materias.values_list('asignatura_id', flat=True).distinct())
                    arrSilabos = []
                    porcentaje_aprobados = 0.0
                    porcentaje_pendientes = 0.0
                    total_materias_aux = 0
                    total_x = 0.0
                    total_y = 0.0
                    for asignatura in asignaturas:
                        # if asignatura.nombre == 'FISICA':
                        #     print("pasa")
                        materias_asignatura = materias.filter(asignatura=asignatura).distinct()
                        materias_silabos = Silabo.objects.filter(materia__in=materias_asignatura, programaanaliticoasignatura__activo=True, status=True)
                        total_materias = materias_asignatura.count()
                        # total_silabos = materias_silabos.filter(fecha_creacion__gte=fechadesde, fecha_creacion__lte=fechacorte).count()
                        total_silabos = materias_silabos.filter(fecha_creacion__lte=fechacorte).count()
                        total_silabos_aprobados = 0
                        porcentaje_silabos_aprobados = 0.0
                        total_silabos_pendientes = 0
                        porcentaje_silabos_pendientes = 0.0
                        # for silabo in materias_silabos.filter(fecha_creacion__gte=fechadesde, fecha_creacion__lte=fechacorte):
                        for silabo in materias_silabos.filter(fecha_creacion__lte=fechacorte):
                            if silabo.versionsilabo == 1:
                                # detalle = silabo.aprobarsilabo_set.filter(fecha__gte=fechadesde, fecha__lte=fechacorte).order_by('-fecha')
                                detalle = silabo.aprobarsilabo_set.filter(fecha__lte=fechacorte).order_by('-fecha')
                                if detalle.exists():
                                    estadoaprobacion = detalle.first().estadoaprobacion
                                    if estadoaprobacion == 2:
                                        total_silabos_aprobados += 1
                            if silabo.versionsilabo == 2:
                                if silabo.codigoqr:
                                    total_silabos_aprobados += 1
                        if total_silabos != total_materias:
                            total_silabos = total_materias
                        total_silabos_pendientes = total_silabos - total_silabos_aprobados
                        try:
                            porcentaje_silabos_aprobados = (total_silabos_aprobados * 100) / total_silabos
                        except:
                            porcentaje_silabos_aprobados = 0
                        porcentaje_silabos_pendientes = 100 - porcentaje_silabos_aprobados

                        arrSilabos.append({"asignatura": asignatura.nombre,
                                           "total_materias": total_materias,
                                           "total_silabos": total_silabos,
                                           "total_aprobados": total_silabos_aprobados,
                                           "porcentaje_silabos_aprobados": null_to_decimal(porcentaje_silabos_aprobados, 2),
                                           "total_pendientes": total_silabos_pendientes,
                                           "porcentaje_silabos_pendientes": null_to_decimal(porcentaje_silabos_pendientes, 2),
                                           })
                        total_materias_aux = total_materias_aux + total_materias
                        total_x = total_x + porcentaje_silabos_aprobados
                        total_y = total_y + porcentaje_silabos_pendientes
                    try:
                        porcentaje_aprobados = null_to_decimal((total_x / len(arrSilabos)), 2)
                    except:
                        porcentaje_aprobados = 0

                    try:
                        porcentaje_pendientes = null_to_decimal((total_y / len(arrSilabos)), 2)
                    except:
                        porcentaje_pendientes = 0
                    data['silabos'] = arrSilabos
                    data['total'] = total_materias_aux
                    data['porcentaje_aprobados'] = porcentaje_aprobados
                    data['porcentaje_pendientes'] = porcentaje_pendientes
                    data['fecha_corte'] = fechacorte
                    # data['desde_fecha_corte'] = fechadesde
                    return conviert_html_to_pdf(
                        'aprobar_silabo/reporteaprobacionsilabospoafacultad_pdf.html',
                        {
                            'pagesize': 'A4',
                            'data': data,
                        }
                    )
                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al ejecutar el error, %s" % ex})

            elif action == 'reporterecursos':
                try:
                    data['fechaactual'] = datetime.now().date()
                    data['carrera'] = carrera = Carrera.objects.get(pk=request.POST['idcarrera'])
                    coordinacion = '-'
                    if carrera.coordinador(periodo, 1):
                        coordinacion = carrera.coordinador(periodo, 1).persona
                    data['coordinacion'] = coordinacion
                    data['materiassilabos'] = Silabo.objects.filter(materia__nivel__periodo=periodo,
                                                                    materia__asignaturamalla__malla__carrera_id=carrera,
                                                                    materia__status=True, status=True).order_by(
                        'materia__asignaturamalla__nivelmalla_id')
                    data['listadorecurso'] = [[1, 'TAREA'], [2, 'FORO'], [3, 'TEST'], [4, 'COMPENDIO'],
                                              [5, 'GUÍA DEL DOCENTE'], [6, 'GUÍA DEL ESTUDIANTE'],
                                              [7, 'MATERIALES COMPLEMENTARIOS'], [8, 'PRESENTACIÓN'], [9, 'EXPOSICIÓN'], [10, 'TALLER'], [11, 'ANÁLISIS DE CASOS'],
                                              [12, 'TRABAJO DE INVESTIGACIÓN'], [13, 'TRABAJO PRÁCTICO EXPERIMENTAL']]
                    return conviert_html_to_pdf(
                        'aprobar_silabo/recursosilabo_pdf.html',
                        {
                            'pagesize': 'A4',
                            'data': data,
                        }
                    )
                except Exception as ex:
                    pass

            elif action == 'opcionvideomagistral':
                try:
                    silabo = Silabo.objects.get(pk=request.POST['id'])
                    if silabo.videomagistral:
                        texto = "Desactivado"
                        silabo.videomagistral = False
                    else:
                        texto = "Activado"
                        silabo.videomagistral = True
                    silabo.save(request)

                    log(u'Actualizó estado de video magistral en el silabo a : %s - %s' % (silabo.id, texto), request,
                        "edit")
                    return JsonResponse({"result": "ok"})
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

            elif action == 'addtiporecurso':
                try:
                    f = TipoRecursoForm(request.POST)
                    if f.is_valid():
                        if not TipoRecurso.objects.filter(status=True, descripcion=f.cleaned_data['descripcion'].upper()).exists():
                            tiporecurso = TipoRecurso(descripcion=f.cleaned_data['descripcion'])
                            tiporecurso.save(request)
                            log(u'Adiciono Tipo de recurso: %s' % tiporecurso.descripcion, request, "add")
                            return JsonResponse({"result": "ok"})
                        else:
                            return JsonResponse({"result": "bad", "mensaje": "Registro Repetido."})
                    else:
                        raise NameError('Error')
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

            elif action == 'edittiporecursos':
                try:
                    tiporecurso = TipoRecurso.objects.get(pk=request.POST['id'])
                    f = TipoRecursoForm(request.POST)
                    if f.is_valid():
                        if not TipoRecurso.objects.filter(status=True, descripcion=f.cleaned_data['descripcion'].upper()).exclude(pk=request.POST['id']).exists():
                            tiporecurso.descripcion = f.cleaned_data['descripcion']
                            tiporecurso.save(request)
                            log(u'Modificó Tipo de recurso: %s' % tiporecurso, request, "edit")
                            return JsonResponse({"result": "ok"})
                        else:
                            return JsonResponse({"result": "bad", "mensaje": "Registro Repetido."})
                    else:
                        raise NameError('Error')
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

            elif action == 'deletetiporecursos':
                try:
                    tiporecurso = TipoRecurso.objects.get(pk=request.POST['id'])
                    tiporecurso.status = False
                    tiporecurso.save(request)
                    log(u'Edito el estado de Tipo de Recurso: %s' % tiporecurso, request, "edit")
                    return JsonResponse({"result": "ok"})
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", "mensaje": u"Error al eliminar los datos."})

            elif action == 'addconfiguracionrecursos':
                try:
                    f = ConfiguracionRecursoForm(request.POST)
                    if f.is_valid():
                        if not ConfiguracionRecurso.objects.filter(tiporecurso=f.cleaned_data['tiporecurso'],
                                                                   carrera=f.cleaned_data['carrera'],
                                                                   periodo=f.cleaned_data['periodo']).exists():
                            configuracion = ConfiguracionRecurso(tiporecurso=f.cleaned_data['tiporecurso'],
                                                                 carrera=f.cleaned_data['carrera'],
                                                                 periodo=f.cleaned_data['periodo'])
                            configuracion.save(request)
                            for format in f.cleaned_data['formato']:
                                configuracion.formato.add(format)
                            configuracion.save(request)
                            # configuracion.formato = f.cleaned_data['formato']

                            log(u'Adiciono configuracion de recurso: %s' % configuracion, request, "add")
                            return JsonResponse({"result": "ok"})
                        else:
                            return JsonResponse({"result": "bad", "mensaje": u"Ya existe un registro con los datos ingresados."})
                    else:
                        raise NameError('Error')
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

            elif action == 'editconfiguracionrecursos':
                try:
                    configuracion = ConfiguracionRecurso.objects.get(pk=request.POST['id'])
                    f = ConfiguracionRecursoForm(request.POST)
                    if f.is_valid():
                        if not ConfiguracionRecurso.objects.filter(tiporecurso=f.cleaned_data['tiporecurso'],
                                                                   carrera=f.cleaned_data['carrera'],
                                                                   periodo=f.cleaned_data['periodo']).exclude(id=configuracion.id).exists():
                            configuracion.tiporecurso = f.cleaned_data['tiporecurso']
                            configuracion.carrera = f.cleaned_data['carrera']
                            configuracion.periodo = f.cleaned_data['periodo']
                            configuracion.formato.clear()
                            configuracion.save(request)
                            for format in f.cleaned_data['formato']:
                                configuracion.formato.add(format)
                            configuracion.save(request)
                            # configuracion.formato = f.cleaned_data['formato']
                            log(u'Modificó Configuracion de recurso: %s' % configuracion, request, "edit")
                            return JsonResponse({"result": "ok"})
                        else:
                            return JsonResponse({"result": "bad", "mensaje": u"Ya existe un registro con los datos ingresados."})
                    else:
                        raise NameError('Error')
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

            elif action == 'deleteconfiguracionrecursos':
                try:
                    configuracion = ConfiguracionRecurso.objects.get(pk=request.POST['id'])
                    configuracion.status = False
                    configuracion.save(request)
                    log(u'Edito el estado de Tipo de Recurso: %s' % configuracion, request, "edit")
                    return JsonResponse({"result": "ok"})
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", "mensaje": u"Error al eliminar los datos."})

            elif action == 'addlistaverificacion':
                try:
                    f = ListaVerificacionForm(request.POST)
                    if f.is_valid():
                        if not ListaVerificacion.objects.filter(
                                tiporecurso_id=request.POST['id'],
                                descripcion=f.cleaned_data['descripcion']).exists():
                            listaverificacion = ListaVerificacion(
                                tiporecurso_id=request.POST['id'],
                                descripcion=f.cleaned_data['descripcion'])
                            listaverificacion.save(request)
                            log(u'Adiciono tipo lista - verificación: %s' % listaverificacion, request, "add")
                            return JsonResponse({"result": "ok"})
                        else:
                            return JsonResponse(
                                {"result": "bad", "mensaje": u"Ya existe un registro con los datos ingresados."})
                    else:
                        raise NameError('Error')
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})


            elif action == 'editlistaverificacion':
                try:
                    listaverificacion = ListaVerificacion.objects.get(pk=request.POST['id'])
                    f = ListaVerificacionForm(request.POST)

                    if f.is_valid():
                        if not ListaVerificacion.objects.filter(
                                tiporecurso=listaverificacion.tiporecurso,
                                descripcion=f.cleaned_data['descripcion']).exclude(pk=request.POST['id']).exists():
                            listaverificacion.descripcion = f.cleaned_data['descripcion']
                            listaverificacion.save(request)

                            log(u'Modificó tipo lista - verificación: %s' % listaverificacion, request, "add")
                            return JsonResponse({"result": "ok"})
                        else:
                            return JsonResponse(
                                {"result": "bad",
                                 "mensaje": u"Ya existe un registro con los datos ingresados en esta lista."})
                    else:
                        raise NameError('Error')
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})


            elif action == 'deletelistaverificacion':
                try:
                    listaverificacion = ListaVerificacion.objects.get(pk=request.POST['id'])
                    log(u'Eliminó lista - verificación: %s' % listaverificacion, request, "del")
                    listaverificacion.status = False
                    listaverificacion.save(request)
                    return JsonResponse({"result": "ok"})
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", "mensaje": u"Error al eliminar los datos."})


            elif action == 'delformato':
                try:
                    configuracion = ConfiguracionRecurso.objects.get(pk=request.POST['id'])
                    formato = FormatoArchivo.objects.get(pk=request.POST['idf'])
                    configuracion.formato.remove(formato)
                    configuracion.save()
                    log(u'Elimino formato de archivo: %s' % configuracion, request, "del")
                    return JsonResponse({"result": "ok"})
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

            elif action == 'importar_conf_recursos':
                try:
                    periodo_origen = Periodo.objects.filter(status=True, id=request.POST['idpo']).first()
                    for config in ConfiguracionRecurso.objects.filter(status=True, periodo=periodo_origen):
                        if not ConfiguracionRecurso.objects.filter(status=True, periodo=periodo,
                                                                   tiporecurso=config.tiporecurso, carrera=config.carrera).exists():
                            formatos = config.formato.all()
                            formato_destino = config
                            formato_destino.periodo = periodo
                            formato_destino.pk = None
                            formato_destino.save(request)
                            formato_destino.formato.set(formatos)
                    log(u'Importa formatos de recuros del periodo %s: al periodo %s' % (periodo_origen, periodo), request, "edit")
                    return JsonResponse({"result": "ok"})
                except Exception as ex:
                    msg = ex.__str__()
                    transaction.set_rollback(True)
                    return JsonResponse(
                        {"result": "bad", "mensaje": u"Error al importar: %s" % (msg)})

            elif action == 'carrerascoordinacion':
                try:
                    facultad = Coordinacion.objects.get(pk=request.POST['id'])
                    lista = []
                    idcarreras = ProfesorMateria.objects.values_list('materia__asignaturamalla__malla__carrera_id', flat=True).filter(tipoprofesor_id__in=[1, 14], materia__nivel__periodo=periodo, materia__asignaturamalla__malla__carrera__coordinacion=facultad, materia__status=True, status=True).exclude(materia_id__in=Materia.objects.values_list('id').filter(asignaturamalla__malla__carrera_id__in=[1, 3], asignaturamalla__nivelmalla_id__in=[7, 8, 9], nivel__periodo=periodo, status=True))
                    carreras = Carrera.objects.filter(pk__in=idcarreras)
                    for carrera in carreras:
                        lista.append([carrera.id, carrera.__str__()])
                    return JsonResponse({'result': 'ok', 'lista': lista})
                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

            elif action == 'niveles_carrera':
                try:
                    carrera = Carrera.objects.get(pk=request.POST['id'])
                    lista = []
                    niveles = NivelMalla.objects.filter(pk__in=Materia.objects.values_list('asignaturamalla__nivelmalla').filter(status=True,
                                                                                                 nivel__periodo=periodo,
                                                                                                 asignaturamalla__malla__carrera=carrera,
                                                                                                 materiaasignada__status=True).distinct()).distinct()
                    for nivel in niveles:
                        lista.append([nivel.id, nivel.__str__()])
                    return JsonResponse({'result': 'ok', 'lista': lista})
                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

            elif action == 'paralelos_carrera':
                try:
                    carrera = Carrera.objects.get(pk=request.POST['idcarrera'])
                    nivel = NivelMalla.objects.get(pk=request.POST['idnivel'])
                    lista = []
                    paralelos = Paralelo.objects.filter(pk__in=Materia.objects.values_list('paralelomateria').filter(status=True,
                                                                                                 nivel__periodo=periodo,
                                                                                                 asignaturamalla__malla__carrera=carrera,
                                                                                                 asignaturamalla__nivelmalla=nivel,
                                                                                                 materiaasignada__status=True,).distinct()).distinct()
                    for paralelo in paralelos:
                        lista.append([paralelo.id, paralelo.__str__()])
                    return JsonResponse({'result': 'ok', 'lista': lista})
                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

            elif action == 'generarreporteseguimientosilabo':
                from sga.models import TipoProfesor
                try:
                    __author__ = 'Unemi'
                    facultad = int(request.POST['idfacultad']) if request.POST['idfacultad'] else 0
                    carrera = int(request.POST['idcarrera']) if request.POST['idcarrera'] else 0
                    semestre = int(request.POST['idnivel']) if request.POST['idnivel'] else 0
                    paralelo = int(request.POST['idparalelo']) if request.POST['idparalelo'] else 0
                    style0 = easyxf('font: name Times New Roman, color-index blue, bold off', num_format_str='#,##0.00')
                    style_nb = easyxf('font: name Times New Roman, color-index blue, bold on',
                                      num_format_str='#,##0.00')
                    style_sb = easyxf('font: name Times New Roman, color-index blue, bold on')
                    title = easyxf('font: name Times New Roman, color-index blue, bold on , height 350; alignment: horiz centre')
                    style1 = easyxf(num_format_str='D-MMM-YY')
                    font_style = XFStyle()
                    font_style.font.bold = True
                    font_style2 = XFStyle()
                    font_style2.font.bold = False
                    wb = Workbook(encoding='utf-8')
                    ws = wb.add_sheet('Hoja1')
                    # ws.write_merge(0, 0, 0, 10, 'UNIVERSIDAD ESTATAL DE MILAGRO', title)
                    response = HttpResponse(content_type="application/ms-excel")
                    response['Content-Disposition'] = 'attachment; filename=seguimiento_silabo' + random.randint(1, 10000).__str__() + '.xls'
                    columns = [
                        (u"FACULTAD", 8000),
                        (u"CARRERA", 8000),
                        (u"NIVEL", 8000),
                        (u"MATERIA", 8000),
                        (u"PARALELO", 10000),
                        (u"DOCENTE", 8000),
                        (u"SILABO", 2000),
                        (u"PROGRAMA ANALÍTICO", 2000),
                        (u"PORCENTAJE CUMPLIMIENTO", 2000),
                    ]
                    row_num = 0
                    for col_num in range(len(columns)):
                        ws.write(row_num, col_num, columns[col_num][0], font_style)
                        ws.col(col_num).width = columns[col_num][1]
                    date_format = xlwt.XFStyle()
                    date_format.num_format_str = 'yyyy/mm/dd'
                    if facultad != 0:
                        materias = Materia.objects.filter(asignaturamalla__malla__carrera__coordinacion__id=facultad,nivel__periodo=periodo,status=True,materiaasignada__status=True)[:10]
                    if carrera != 0:
                        materias = Materia.objects.filter(asignaturamalla__malla__carrera_id=carrera,nivel__periodo=periodo,status=True,materiaasignada__status=True)[:10]
                    if semestre != 0:
                        materias = Materia.objects.filter(asignaturamalla__malla__carrera_id=carrera,asignaturamalla__nivelmalla_id=semestre,nivel__periodo=periodo,status=True,materiaasignada__status=True)[:10]
                    if paralelo != 0:
                        materias = Materia.objects.filter(asignaturamalla__malla__carrera_id=carrera,asignaturamalla__nivelmalla_id=semestre,paralelomateria_id=paralelo,nivel__periodo=periodo,status=True,materiaasignada__status=True)[:10]
                    row_num = 1
                    for materia in materias:
                        if int(periodo.id) < 153:
                            if int(facultad) == 1:
                                puntajecumplimiento = str(100) + ' %'
                            else:
                                if materia.silabo_actual():
                                    puntajecumplimiento = str(materia.silabo_actual().estado_planificacion_clases()) + ' %'
                                else:
                                    puntajecumplimiento = str(0) + ' %'
                        else:
                            if materia.silabo_actual():
                                puntajecumplimiento = str(materia.silabo_actual().estado_planificacion_clases()) + ' %'
                            else:
                                puntajecumplimiento = str(0) + ' %'

                        ws.write(row_num, 0, u"%s" % materia.asignaturamalla.malla.carrera.mi_coordinacion(), font_style2)
                        ws.write(row_num, 1, u"%s" % materia.asignaturamalla.malla.carrera, font_style2)
                        ws.write(row_num, 2, u"%s" % materia.asignaturamalla.nivelmalla, font_style2)
                        ws.write(row_num, 3, u"%s" % materia.asignatura, font_style2)
                        ws.write(row_num, 4, u"%s" % materia.paralelomateria, font_style2)
                        ws.write(row_num, 5, u"%s" % materia.profesores_materia_segun_tipoprofesor(TipoProfesor.objects.get(id=1)).first().persona.nombre_completo_inverso(), font_style2)
                        ws.write(row_num, 6, u"SI" if materia.tiene_silabo_digital() else "NO", font_style2)
                        ws.write(row_num, 7, u"SI" if materia.asignaturamalla.tiene_programaanalitico() else "NO", font_style2)
                        # ws.write(row_num, 8, f"{materia.silabo_actual().porcentaje_planificacion_impartida_seguimiento() if materia.silabo_actual() else 0} %", font_style2)
                        ws.write(row_num, 8, puntajecumplimiento, font_style2)
                        row_num += 1
                    wb.save(response)
                    return response
                except Exception as ex:
                    pass

            elif action == 'generarreporteseguimientosilabopdf':
                try:
                    data = {}
                    facultad = int(request.POST['idfacultad']) if request.POST['idfacultad'] else 0
                    carrera = int(request.POST['idcarrera']) if request.POST['idcarrera'] else 0
                    semestre = int(request.POST['idnivel']) if request.POST['idnivel'] else 0
                    paralelo = int(request.POST['idparalelo']) if request.POST['idparalelo'] else 0
                    # materias = Materia.objects.filter(nivel__periodo=periodo, status=True, materiaasignada__status=True)
                    materias = Materia.objects.filter(nivel__periodo=periodo, status=True).order_by('paralelo')
                    if facultad != 0:
                        materias = materias.filter(asignaturamalla__malla__carrera__coordinacion__id=facultad)
                    if carrera != 0:
                        materias = materias.filter(asignaturamalla__malla__carrera_id=carrera)
                    if semestre != 0:
                        materias = materias.filter(asignaturamalla__nivelmalla_id=semestre)
                    if paralelo != 0:
                        materias = materias.filter(paralelomateria_id=paralelo)
                    data['materias'] = materias
                    data['coordinacion'] = coordinacion = Coordinacion.objects.get(pk=facultad)
                    data['carrera'] = Carrera.objects.get(pk=carrera)
                    nivelmalla = None
                    if NivelMalla.objects.values('id').filter(pk=semestre).exists():
                        nivelmalla = NivelMalla.objects.filter(pk=semestre)[0]
                    data['nivelmalla'] = nivelmalla
                    data['nomperiodo'] = periodo
                    coordinadorcarrera = None
                    if CoordinadorCarrera.objects.values('id').filter(carrera=carrera, periodo=periodo, sede_id=1, tipo=3).exists():
                        coordinadorcarrera = CoordinadorCarrera.objects.filter(carrera=carrera, periodo=periodo, sede_id=1, tipo=3)[0].persona
                    data['coordinadorcarrera'] = coordinadorcarrera

                    directorfacultad = None
                    if coordinacion.responsablecoordinacion_set.filter(periodo=periodo, tipo=1).exists():
                        directorfacultad = coordinacion.responsablecoordinacion_set.filter(periodo=periodo, tipo=1)[0].persona
                    data['directorfacultad'] = directorfacultad

                    # directorcarrera = None

                    # if CoordinadorCarrera.objects.values('id').filter(carrera=carrera, periodo=periodo, sede_id=1, tipo=1).exists():
                    #     directorcarrera = CoordinadorCarrera.objects.filter(carrera=carrera, periodo=periodo, sede_id=1, tipo=1)[0]
                    # data['directorcarrera'] = directorcarrera
                    return download_html_to_pdf('aprobar_silabo/seguimientosilabo_pdf.html', {'pagesize': 'A4', 'data': data })
                except Exception as ex:
                    return HttpResponseRedirect("/aprobar_silabo?info=%s" % ex)

        return JsonResponse({"result": "bad", "mensaje": u"Solicitud Incorrecta."})
    else:
        if 'action' in request.GET:
            action = request.GET['action']
            if action == 'aprobarsilabo':
                try:
                    data['title'] = u'Aprobar Silabo'
                    data['archivo'] = archivo = Archivo.objects.filter(pk=request.GET['id'])[0]
                    form = ArchivoForm(initial={'observacion': archivo.observacion,
                                                'aprobado': archivo.aprobado})
                    data['form'] = form
                    return render(request, "aprobar_silabo/aprobarsilabo.html", data)
                except Exception as ex:
                    pass

            elif action == 'versilabos':
                try:
                    data['title'] = u'Silabos Materia'
                    materia = Materia.objects.filter(status=True, pk=request.GET['id'])[0]
                    data['archivos'] = archivo = Archivo.objects.filter(materia=materia,
                                                                        archivo__contains='.doc').order_by('-id')
                    data['ultimo'] = Archivo.objects.filter(materia=materia, archivo__contains='.doc').order_by('-id')[
                        0]
                    return render(request, "aprobar_silabo/versilabos.html", data)
                except Exception as ex:
                    pass

            elif action == 'listadosilabos':
                try:
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
                    # ws.write_merge(0, 0, 0, 10, 'UNIVERSIDAD ESTATAL DE MILAGRO', title)
                    response = HttpResponse(content_type="application/ms-excel")
                    response['Content-Disposition'] = 'attachment; filename=silabo' + random.randint(1, 10000).__str__() + '.xls'
                    columns = [
                        (u"MATERIA", 8000),
                        (u"PROFESOR", 10000),
                        (u"NIVEL CARRERA SESION", 8000),
                        (u"TIENE SILABO", 2000),
                        (u"TIENE PLAN ANALÍTICO", 2000),
                    ]
                    row_num = 0
                    for col_num in range(len(columns)):
                        ws.write(row_num, col_num, columns[col_num][0], font_style)
                        ws.col(col_num).width = columns[col_num][1]
                    date_format = xlwt.XFStyle()
                    date_format.num_format_str = 'yyyy/mm/dd'
                    # if miscarreras:
                    #     listaprofesores =  ProfesorMateria.objects.filter(materia__asignaturamalla__malla__carrera__in=miscarreras, materia__nivel__periodo=periodo, activo=True, principal=True).distinct().order_by('profesor')
                    # else:
                    listaprofesores = ProfesorMateria.objects.filter(materia__nivel__periodo=periodo, activo=True,
                                                                     principal=True).distinct().order_by('profesor')
                    # listaprofesores =  ProfesorMateria.objects.filter(materia__asignaturamalla__malla__carrera__in=miscoordinaciones).filter(materia__nivel__periodo=periodo, activo=True, principal=True).distinct().order_by('profesor')
                    row_num = 1
                    for profesores in listaprofesores:
                        tienearchivo = 'NO'
                        if Archivo.objects.values('id').filter(materia=profesores.materia,
                                                               tipo_id=ARCHIVO_TIPO_SYLLABUS,
                                                               archivo__contains='.doc').exists():
                            tienearchivo = 'SI'
                        tieneplan = 'NO'
                        if profesores.materia.asignaturamalla.programaanaliticoasignatura():
                            tieneplan = 'SI'
                        i = 0
                        campo1 = profesores.materia.asignatura.nombre
                        campo2 = profesores.profesor.persona.apellido1 + ' ' + profesores.profesor.persona.apellido2 + ' ' + profesores.profesor.persona.nombres
                        campo3 = profesores.materia.nivel.paralelo
                        if profesores.materia.nivel.carrera:
                            campo3 = campo3 + ' - ' + profesores.materia.nivel.carrera.alias
                        elif profesores.materia.asignaturamalla.malla.carrera:
                            campo3 = campo3 + ' - ' + profesores.materia.asignaturamalla.malla.carrera.alias
                        ws.write(row_num, 0, campo1, font_style2)
                        ws.write(row_num, 1, campo2, font_style2)
                        ws.write(row_num, 2, campo3, font_style2)
                        ws.write(row_num, 3, tienearchivo, font_style2)
                        ws.write(row_num, 4, tieneplan, font_style2)
                        row_num += 1
                    wb.save(response)
                    return response
                except Exception as ex:
                    pass

            elif action == 'listadosilabosdigitales':
                try:
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
                    # ws.write_merge(0, 0, 0, 10, 'UNIVERSIDAD ESTATAL DE MILAGRO', title)
                    response = HttpResponse(content_type="application/ms-excel")
                    response[
                        'Content-Disposition'] = 'attachment; filename=silabo' + random.randint(
                        1, 10000).__str__() + '.xls'

                    columns = [
                        (u"FACULTAD", 10000),
                        (u"CARRERA", 10000),
                        (u"ASIGNATURA", 10000),
                        (u"NIVEL", 6000),
                        (u"PARALELO", 8000),
                        (u"PROFESOR", 10000),
                        (u"TIENE SILABO", 5000),
                        (u"FECHA DE CREACIÓN DEL SÍLABO", 7000),
                        (u"POCENTAJE PLANIFICADO", 7000),
                        (u"ESTADO APROBACION DEL SÍLABO", 10000),
                        (u"USUARIO QUIEN APROBÓ EL SÍLABO", 10000),
                        (u"OBSERVACIÓN DE APROBACION", 10000),
                        (u"FECHA DE APROBACION", 10000),
                        (u"TIENE PROGRAMA ANALITICO", 15000),
                        (u"FECHA DE CREACIÓN DE PROGRAMA ANALITICO", 15000),
                        (u"SÍLABO (FIRMADO Y ESCANEADO)", 15000),
                        (u"TIENE GUÍA DE PRÁCTICA", 8000),
                        (u"CANTIDAD G.P", 8000),
                    ]
                    row_num = 0
                    for col_num in range(len(columns)):
                        ws.write(row_num, col_num, columns[col_num][0], font_style)
                        ws.col(col_num).width = columns[col_num][1]
                    date_format = xlwt.XFStyle()
                    date_format.num_format_str = 'yyyy/mm/dd'
                    # if miscarreras:
                    #     listaprofesores =  ProfesorMateria.objects.filter(materia__asignaturamalla__malla__carrera__in=miscarreras, materia__nivel__periodo=periodo, activo=True, principal=True).distinct().order_by('profesor')
                    # else:
                    listamaterias = ProfesorMateria.objects.filter(materia__nivel__periodo=periodo, activo=True,
                                                                   principal=True).distinct().order_by(
                        'materia__asignaturamalla__malla__carrera')
                    # listaprofesores =  ProfesorMateria.objects.filter(materia__asignaturamalla__malla__carrera__in=miscoordinaciones).filter(materia__nivel__periodo=periodo, activo=True, principal=True).distinct().order_by('profesor')
                    row_num = 1
                    for materia in listamaterias:
                        facultad = '%s' % materia.materia.asignaturamalla.malla.carrera.coordinaciones()[
                            0].nombre if materia.materia.asignaturamalla.malla.carrera.coordinaciones() else ""
                        campo1 = '%s' % materia.materia.asignaturamalla.malla.carrera.nombre_completo()
                        campo2 = '%s' % materia.materia.asignaturamalla.asignatura.nombre
                        campo3 = '%s' % materia.materia.asignaturamalla.nivelmalla
                        campo4 = '%s' % materia.materia.paralelo if materia.materia.paralelo else ''
                        campo5 = '%s' % materia.profesor.persona.nombre_completo_inverso()
                        campo6 = 'SI' if materia.materia.tiene_silabo() else 'NO'
                        campo7 = materia.materia.silabo_actual().fecha_creacion.strftime(
                            "%d-%m-%Y") if materia.materia.tiene_silabo() else ''
                        campo8 = str(
                            materia.materia.silabo_actual().estado_planificacion_clases()) + ' %' if materia.materia.tiene_silabo() and materia.materia.tiene_silabo_semanal() else ''  # porcentaje
                        estado = None
                        if materia.materia.silabo_actual():
                            if materia.materia.silabo_actual().estado_aprobacion():
                                estado = materia.materia.silabo_actual().estado_aprobacion()
                        campo9 = ''
                        if materia.materia.tiene_silabo():
                            campo9 = 'PENDIENTE'
                        campo10 = ''
                        campo11 = ''
                        campo12 = ''
                        if estado:
                            campo9 = '%s' % estado.get_estadoaprobacion_display()
                            campo10 = '%s' % estado.persona.nombre_completo_inverso()
                            campo11 = '%s' % estado.observacion
                            campo12 = '%s' % estado.fecha.strftime("%d-%m-%Y")
                        campo13 = ''
                        campo14 = ''
                        campo15 = 'NO'
                        campo16 = ''
                        campo17 = ''
                        if materia.materia.silabo_actual():
                            campo13 = 'DESACTIVADO'
                            if materia.materia.silabo_actual().programaanaliticoasignatura.activo:
                                campo13 = 'ACTIVO'
                            campo14 = '%s' % materia.materia.silabo_actual().programaanaliticoasignatura.fecha_creacion.strftime(
                                "%d-%m-%Y")
                            if materia.materia.silabo_actual().numero_guia_practicas():
                                campo15 = 'SI'
                                campo16 = str(materia.materia.silabo_actual().numero_guia_practicas())
                            campo17 = 'NO'
                            if materia.materia.silabo_actual().silabofirmado:
                                campo17 = 'SI'
                        ws.write(row_num, 0, facultad, font_style2)
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
                        ws.write(row_num, 15, campo17, font_style2)
                        ws.write(row_num, 16, campo15, font_style2)
                        ws.write(row_num, 17, campo16, font_style2)
                        row_num += 1
                    wb.save(response)
                    return response
                except Exception as ex:
                    pass

            elif action == 'reporterecursoscompenente':
                try:

                    # reporte_encuesta_grupo_estudiante_background()
                    coordinacion = Coordinacion.objects.get(pk=request.GET['cod_facultad'])
                    cadenaparcial = list(request.GET['cod_parcial'])
                    noti = Notificacion(cuerpo='Generación de reporte de excel en progreso',
                                        titulo='Reporte consolidado de cumplimiento de actividades y recursos de aprendizaje', destinatario=persona,
                                        url='',
                                        prioridad=1, app_label='SGA',
                                        fecha_hora_visible=datetime.now() + timedelta(days=1), tipo=2,
                                        en_proceso=True)
                    noti.save(request)
                    reporte_recurso_aprendizaje_background(request=request, notiid=noti.pk, periodo=periodo, coordinacion=coordinacion, codcarrera=request.GET['cod_carrera'], tipo='pdf', cadenaparcial=cadenaparcial).start()
                    return JsonResponse({"result": True,
                                         "mensaje": u"El reporte se está realizando. Verifique su apartado de notificaciones después de unos minutos.",
                                         "btn_notificaciones": traerNotificaciones(request, data, persona)})

                except Exception as ex:
                    print('Error on line {}'.format(sys.exc_info()[-1].tb_lineno))
                    pass

            elif action == 'reportemensualcumplimiento':
                try:

                    # reporte_encuesta_grupo_estudiante_background()
                    # hoy = datetime.now()
                    # pastmonth = date(hoy.year, hoy.month, 1) - timedelta(days=1)
                    # fdaypastmonth = date(pastmonth.year, pastmonth.month, 1)
                    # finicio = convertir_fecha_invertida(request.GET.get('finicio', f'{fdaypastmonth}'))
                    # ffin = convertir_fecha_invertida(request.GET.get('ffin', f'{pastmonth}'))
                    mes_selected = int(request.GET.get('id_mes'))
                    if mes_selected <= 0:
                        return JsonResponse({"result": False, "mensaje": u"Debe seleccionar un mes valido"})
                    fecha_año = list(rrule(YEARLY, dtstart=periodo.inicio, until=periodo.fin))
                    finicio = date(fecha_año[0].year, mes_selected, 1)
                    siguiente_mes = finicio.replace(day=28) + timedelta(days=4)
                    ffin = siguiente_mes - timedelta(days=siguiente_mes.day)

                    now = datetime.now()
                    # finicio, ffin = date(now.year, mes_selected, 1), date(now.year, mes_selected, calendar.monthrange(now.year, mes_selected)[1])

                    coordinacion = Coordinacion.objects.get(pk=request.GET['cod_facultad'])
                    noti = Notificacion(cuerpo='Generación de reporte de excel en progreso',
                                        titulo='Reporte consolidado de cumplimiento de actividades y recursos de aprendizaje',
                                        destinatario=persona,
                                        url='',
                                        prioridad=1, app_label='SGA',
                                        fecha_hora_visible=datetime.now() + timedelta(days=1), tipo=2,
                                        en_proceso=True)
                    noti.save(request)
                    reporte_cumplimiento_background_v3(request=request, notiid=noti.pk, periodo=periodo, coordinacion=coordinacion, codcarrera=request.GET['cod_carrera'], finicio=finicio, ffin=ffin, tipo='pdf').start()
                    return JsonResponse({"result": True,
                                         "mensaje": u"El reporte se está realizando. Verifique su apartado de notificaciones después de unos minutos.",
                                         "btn_notificaciones": traerNotificaciones(request, data, persona)})

                except Exception as ex:
                    print('Error on line {}'.format(sys.exc_info()[-1].tb_lineno))
                    pass

            elif action == 'listar_silabos':
                try:
                    # data['materia'] = materia = Materia.objects.get(pk=pm.materia.id)
                    data['materia'] = materia = Materia.objects.get(pk=int(request.GET['id']))
                    data['profesor'] = materia.profesor_principal()

                    coordinadorprograma = None
                    coordinadoracademico = None
                    cp = CoordinadorCarrera.objects.filter(periodo=periodo, carrera=materia.asignaturamalla.malla.carrera, tipo=3)
                    if not cp:
                        return JsonResponse({"result": "bad", "mensaje": u"No tiene configurado director de carrera en el periodo actual, la configuración se la realiza en el módulo Coordinaciones."})
                    coorpos = materia.asignaturamalla.malla.carrera.coordinacion_carrera().responsablecoordinacion_set.filter(periodo=periodo, tipo=1)
                    if cp:
                        coordinadorprograma = cp[0].persona
                    if coorpos:
                        coordinadoracademico = coorpos[0].persona
                    data['coordinadorprograma'] = coordinadorprograma
                    data['coordinadoracademico'] = coordinadoracademico

                    # data['profesor'] = pm.profesor
                    data['silabos'] = materia.silabo_set.filter(status=True).order_by('fecha_creacion')
                    # data['silabos'] = materia.silabo_set.filter(profesor=pm.profesor).order_by('fecha_creacion')
                    data['aprobar'] = variable_valor('APROBAR_SILABO')
                    data['rechazar'] = variable_valor('RECHAZAR_SILABO')
                    data['pendiente'] = variable_valor('PENDIENTE_SILABO')
                    data['coordinacion_id']= cp.first().coordinacion().id if cp.first().coordinacion() else 0
                    template = get_template("aprobar_silabo/listasilabos.html")
                    json_content = template.render(data)
                    return JsonResponse({"result": "ok", 'data': json_content})
                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})
                    pass

            elif action == 'listar_recursos':
                try:
                    data['materia'] = materia = Materia.objects.get(pk=int(request.GET['id']))
                    data['profesor'] = materia.profesor_principal()
                    data['silabos'] = materia.silabo_set.filter(status=True).order_by('fecha_creacion')
                    template = get_template("aprobar_silabo/listarecursos.html")
                    json_content = template.render(data)
                    return JsonResponse({"result": "ok", 'data': json_content})
                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})
                    pass


            elif action == 'listar_recursossilabos':
                try:
                    data['silabocab'] = silabocab = Silabo.objects.get(pk=request.GET['id'], status=True)
                    data['silabosemanal'] = silabosemanal = silabocab.silabosemanal_set.filter(status=True)
                    data['listadounidades'] = DetalleSilaboSemanalTema.objects.values_list(
                        'temaunidadresultadoprogramaanalitico__unidadresultadoprogramaanalitico_id').filter(
                        silabosemanal_id__in=silabosemanal.values_list('id'),
                        temaunidadresultadoprogramaanalitico__status=True).distinct()
                    idcoordinacion = silabocab.materia.asignaturamalla.malla.carrera.mi_coordinacion2()
                    if silabocab.versionrecurso == 1:
                        return render(request, "aprobar_silabo/listarecursossilabos.html", data)
                    if silabocab.versionrecurso == 2 and idcoordinacion == 7 or idcoordinacion == 9 or idcoordinacion == 10:
                        return render(request, "aprobar_silabo/listarecursossilabosvdos.html", data)
                    else:
                        return render(request, "aprobar_silabo/listarecursossilabosvtres.html", data)
                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})
                    pass

            elif action == 'detalle_temasxplanificar':
                try:
                    silabo = Silabo.objects.get(pk=int(request.GET['ids']))
                    stemas = DetalleSilaboSemanalTema.objects.values("temaunidadresultadoprogramaanalitico_id").filter(
                        silabosemanal__silabo=silabo, status=True)
                    ssubtemas = DetalleSilaboSemanalSubtema.objects.values(
                        "subtemaunidadresultadoprogramaanalitico_id").filter(silabosemanal__silabo=silabo, status=True)
                    tem = TemaUnidadResultadoProgramaAnalitico.objects.values_list("id", flat=True).filter(status=True,
                                                                                                           unidadresultadoprogramaanalitico__contenidoresultadoprogramaanalitico__programaanaliticoasignatura_id=silabo.programaanaliticoasignatura.id).exclude(
                        pk__in=stemas)
                    data['subtemas'] = subtemas = SubtemaUnidadResultadoProgramaAnalitico.objects.filter(status=True,
                                                                                                         temaunidadresultadoprogramaanalitico__unidadresultadoprogramaanalitico__contenidoresultadoprogramaanalitico__programaanaliticoasignatura_id=silabo.programaanaliticoasignatura.id).exclude(
                        pk__in=ssubtemas)
                    st = subtemas.values_list("temaunidadresultadoprogramaanalitico_id", flat=True).all().distinct(
                        'temaunidadresultadoprogramaanalitico_id')
                    data['temas'] = TemaUnidadResultadoProgramaAnalitico.objects.filter(
                        Q(pk__in=st) | Q(pk__in=tem)).order_by("unidadresultadoprogramaanalitico__orden")
                    template = get_template("pro_planificacion/detalle_temasxplanificar.html")
                    json_content = template.render(data)
                    return JsonResponse({"result": "ok", 'data': json_content})
                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})
                    pass

            elif action == 'seguimientosilabo':
                try:
                    data['title'] = u'Seguimiento de Sílabo'
                    materia = Materia.objects.get(pk=request.GET['id'])
                    data['silabo'] = materia.silabo_actual()
                    data['profesormateria'] = ProfesorMateria.objects.filter(materia=materia, status=True)[0]
                    silabo = materia.silabo_actual()
                    data['semanas'] = silabo.silabosemanal_set.filter(status=True).order_by('numsemana')
                    return render(request, "aprobar_silabo/seguimientosilabo.html", data)
                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})
                    pass

            elif action == 'confirmarreactivo':
                try:
                    data['title'] = u'Confirmar Reactivo'
                    data['materia'] = Materia.objects.get(pk=request.GET['idmate'])
                    data['iddetalle'] = request.GET['iddetalle']
                    if 's' in request.GET:
                        data['search'] = request.GET['s']
                    if 'nid' in request.GET:
                        data['nid'] = request.GET['nid']
                    if 'mid' in request.GET:
                        data['mid'] = request.GET['mid']
                    return render(request, 'aprobar_silabo/confirmarreactivo.html', data)
                except Exception as ex:
                    pass

            elif action == 'eliminarconfirmacion':
                try:
                    data['title'] = u'Eliminar Confirmación'
                    data['materia'] = Materia.objects.get(pk=request.GET['idmate'])
                    data['iddetalle'] = request.GET['iddetalle']
                    if 's' in request.GET:
                        data['search'] = request.GET['s']
                    if 'nid' in request.GET:
                        data['nid'] = request.GET['nid']
                    if 'mid' in request.GET:
                        data['mid'] = request.GET['mid']
                    return render(request, 'aprobar_silabo/eliminarconfirmacion.html', data)
                except Exception as ex:
                    pass

            elif action == 'reportereactivo':
                try:
                    periodo = request.GET['periodo']

                    response = HttpResponse(content_type="application/ms-excel")
                    response['Content-Disposition'] = 'attachment; filename=reactivo.xls'
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

                    ws.col(0).width = 6000
                    ws.col(1).width = 6000
                    ws.col(2).width = 6000
                    ws.col(3).width = 6000
                    ws.col(4).width = 6000
                    ws.col(5).width = 6000
                    ws.col(6).width = 6000

                    ws.write(4, 0, 'FACULTAD')
                    ws.write(4, 1, 'CARRERA')
                    ws.write(4, 2, 'NIVEL')
                    ws.write(4, 3, 'PARALELO')
                    ws.write(4, 4, 'ASIGNATURA')
                    ws.write(4, 5, 'DOCENTE')
                    ws.write(4, 6, 'CONFIRMADO REACTIVO 1')
                    ws.write(4, 7, 'FECHA CONFIRMACION')
                    ws.write(4, 8, 'CONFIRMADO REACTIVO 2')
                    ws.write(4, 9, 'FECHA CONFIRMACION')

                    a = 4
                    date_format = xlwt.XFStyle()
                    date_format.num_format_str = 'yyyy/mm/dd'
                    materias = Materia.objects.filter(nivel__periodo=periodo, status=True,
                                                      profesormateria__isnull=False,
                                                      asignaturamalla__malla__carrera__in=miscarreras).distinct().order_by(
                        'asignaturamalla__malla__carrera__coordinacion', 'asignaturamalla__nivelmalla',
                        'asignaturamalla__malla__carrera', 'paralelo').exclude(
                        asignaturamalla__malla__carrera__coordinacion__id__in=[9])
                    for materia in materias:
                        a += 1
                        ws.write(a, 0, u'%s' % materia.asignaturamalla.malla.carrera.coordinacion_set.all()[0].nombre)
                        ws.write(a, 1, u'%s' % materia.asignaturamalla.malla.carrera.nombre)
                        ws.write(a, 2, u'%s' % materia.asignaturamalla.nivelmalla.nombre)
                        ws.write(a, 3, u'%s' % materia.paralelo)
                        ws.write(a, 4, u'%s' % materia.asignatura.nombre)
                        ws.write(a, 5,
                                 u'%s' % materia.profesor_materia_principal().profesor.persona.nombre_completo_inverso())
                        reactivo1 = materia.reactivomateria_set.filter(status=True).exclude(
                            detallemodelo__nombre__icontains='EX2')
                        reactivo_1 = 'NO'
                        fecha1 = ''
                        if reactivo1.values('id').exists():
                            reactivo_1 = 'SI'
                            fecha1 = reactivo1[0].fecha
                        reactivo2 = materia.reactivomateria_set.filter(status=True,
                                                                       detallemodelo__nombre__icontains='EX2')
                        reactivo_2 = 'NO'
                        fecha2 = ''
                        if reactivo2.values('id').exists():
                            reactivo_2 = 'SI'
                            fecha2 = reactivo2[0].fecha
                        ws.write(a, 6, u'%s' % reactivo_1)
                        ws.write(a, 7, u'%s' % fecha1)
                        ws.write(a, 8, u'%s' % reactivo_2)
                        ws.write(a, 9, u'%s' % fecha2)

                    a += 1
                    # ws.write_merge(a + 2, a + 2, 0, 1, datetime.today(), date_format)
                    wb.save(response)
                    return response
                except Exception as ex:
                    pass

            elif action == 'guiapracticas':
                try:
                    data['silabo'] = silabo = Silabo.objects.get(pk=int(request.GET['id']))
                    data['materia'] = '%s - %s - %s %s' % (
                        silabo.materia.asignaturamalla.asignatura, silabo.materia.asignaturamalla.nivelmalla,
                        silabo.materia.paralelo, silabo.materia.nivel.paralelo)
                    data['practicas'] = GPGuiaPracticaSemanal.objects.filter(status=True,
                                                                             silabosemanal__silabo=silabo).order_by(
                        'silabosemanal')
                    template = get_template("aprobar_silabo/guiapracticas.html")
                    json_content = template.render(data)
                    return JsonResponse({"result": "ok", 'html': json_content})
                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})
                    pass

            elif action == 'revisarpractica':
                try:
                    data['title'] = u'Rechazar Guía de práctica'
                    data['estados'] = ([2, 'REVISADO'], [4, 'RECHAZADO'])
                    data['practica'] = GPGuiaPracticaSemanal.objects.get(pk=request.GET['id'])
                    template = get_template("aprobar_silabo/revisionguiapractica.html")
                    json_content = template.render(data)
                    return JsonResponse({"result": "ok", 'data': json_content})
                except Exception as ex:
                    pass

            elif action == 'aprobacionguiaspracticas':
                try:
                    data['title'] = u'Confirmar aprobación de guiás de prácticas'
                    data['carreras'] = persona.mis_carreras().values_list('nombre')
                    data['period'] = periodo
                    return render(request, 'aprobar_silabo/aprobarguiapractica.html', data)
                except Exception as ex:
                    pass

            elif action == 'listaguiapractica':
                try:
                    data['title'] = u'Listado de guías de prácticas'
                    search = None
                    practicas = GPGuiaPracticaSemanal.objects.filter(
                        silabosemanal__silabo__materia__profesormateria__profesor__coordinacion__carrera__in=persona.mis_carreras(),
                        silabosemanal__silabo__materia__nivel__periodo=periodo).distinct().order_by(
                        'silabosemanal__silabo', 'silabosemanal')
                    if 's' in request.GET:
                        search = request.GET['s']
                        s = search.split(" ")
                        if len(s) == 2:
                            practicas = practicas.filter((Q(
                                silabosemanal__silabo__materia__asignaturamalla__asignatura__nombre__icontains=s[
                                    0]) & Q(
                                silabosemanal__silabo__materia__asignaturamalla__asignatura__nombre__icontains=s[
                                    1])) | (Q(
                                silabosemanal__silabo__materia__profesormateria__profesor__persona__nombres__icontains=
                                s[0]) & Q(
                                silabosemanal__silabo__materia__profesormateria__profesor__persona__nombres__icontains=
                                s[1])) | (Q(
                                silabosemanal__silabo__materia__profesormateria__profesor__persona__apellido1__icontains=
                                s[0]) & Q(
                                silabosemanal__silabo__materia__profesormateria__profesor__persona__apellido2__icontains=
                                s[1])))
                        else:
                            practicas = practicas.filter(Q(
                                silabosemanal__silabo__materia__asignaturamalla__asignatura__nombre__icontains=search) | Q(
                                silabosemanal__silabo__materia__profesormateria__profesor__persona__nombres__icontains=search) | Q(
                                silabosemanal__silabo__materia__profesormateria__profesor__persona__apellido1__icontains=search))
                    paging = MiPaginador(practicas, 20)
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
                    data['practicas'] = page.object_list
                    data['search'] = search if search else ""
                    return render(request, 'aprobar_silabo/listaguiaspracticas.html', data)
                except Exception as ex:
                    pass

            elif action == 'configuracionrecursos':
                try:
                    data['title'] = u'Configuración de recursos'
                    search = None
                    configuracion = ConfiguracionRecurso.objects.filter(status=True, periodo=periodo, carrera__id__in=persona.mis_carreras().values_list('id', flat=True))
                    data['periodos_select'] = Periodo.objects.filter(id__in=ConfiguracionRecurso.objects.values_list('periodo_id').filter(status=True, carrera__id__in=persona.mis_carreras().values_list('id', flat=True))).exclude(id=periodo.id)
                    if 's' in request.GET:
                        search = request.GET['s']
                        s = search.split(" ")
                        if len(s) == 2:
                            configuracion = configuracion.filter(Q(carrera__nombre__icontains=s[0]) | Q(carrera__nombre__icontains=s[1]) |
                                                                 Q(tiporecurso__descripcion__icontains=s[0]) | Q(tiporecurso__descripcion__icontains=s[1])
                                                                 | Q(periodo__nombre__icontains=s[0]) | Q(periodo__nombre__icontains=s[1]))
                        else:
                            configuracion = configuracion.filter(Q(carrera__nombre__icontains=search) | Q(tiporecurso__descripcion__icontains=search) | Q(periodo__nombre__icontains=search))
                    paging = MiPaginador(configuracion, 5)
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
                    data['configuraciones'] = page.object_list
                    data['search'] = search if search else ""
                    return render(request, 'aprobar_silabo/configuracionrecursos.html', data)
                except Exception as ex:
                    pass

            elif action == 'configuraciontiporecursos':
                try:
                    data['title'] = u'Configuración de tipos de recursos'
                    search = None
                    configuracion = TipoRecurso.objects.filter(status=True)
                    if 's' in request.GET:
                        search = request.GET['s']
                        s = search.split(" ")
                        if len(s) == 2:
                            configuracion = configuracion.filter(
                                Q(descripcion__icontains=s[0]) & Q(descripcion__icontains=s[1]))
                        else:
                            configuracion = configuracion.filter(descripcion__icontains=search)
                    paging = MiPaginador(configuracion, 25)
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
                    data['tiporecursos'] = page.object_list
                    data['search'] = search if search else ""
                    return render(request, 'aprobar_silabo/configuraciontiporecursos.html', data)
                except Exception as ex:
                    pass

            elif action == 'addtiporecurso':
                try:
                    data['title'] = u'Adicionar Tipo de Recurso'
                    form = TipoRecursoForm()
                    data['form'] = form
                    return render(request, 'aprobar_silabo/addtiporecursos.html', data)
                except Exception as ex:
                    pass

            elif action == 'edittiporecursos':
                try:
                    data['title'] = u'Editar Tipo de Recurso'
                    data['tiporecurso'] = tiporecurso = TipoRecurso.objects.get(pk=request.GET['id'])
                    initial = model_to_dict(tiporecurso)
                    form = TipoRecursoForm(initial=initial)
                    data['form'] = form
                    return render(request, 'aprobar_silabo/edittiporecursos.html', data)
                except Exception as ex:
                    pass

            elif action == 'deletetiporecursos':
                try:
                    data['title'] = u'Eliminar Tipo de Recurso'
                    data['tiporecurso'] = TipoRecurso.objects.get(pk=request.GET['id'])
                    return render(request, 'aprobar_silabo/deletetiporecursos.html', data)
                except Exception as ex:
                    pass

            elif action == 'addconfiguracionrecursos':
                try:
                    f = ConfiguracionRecursoForm()
                    data['title'] = u'Adicionar configuraciòn de Recurso'
                    f.inicializar(periodo)
                    f.inicializar_carrera(persona.mis_carreras())
                    data['form'] = f
                    return render(request, 'aprobar_silabo/addconfiguracionrecursos.html', data)
                except Exception as ex:
                    pass

            elif action == 'editconfiguracionrecursos':
                try:
                    data['title'] = u'Editar Configuracion de Recurso'
                    data['configuracion'] = configuracion = ConfiguracionRecurso.objects.get(pk=request.GET['id'])
                    initial = model_to_dict(configuracion)
                    form = ConfiguracionRecursoForm(initial=initial)
                    form.inicializar_carrera(persona.mis_carreras())
                    data['form'] = form
                    return render(request, 'aprobar_silabo/editconfiguracionrecursos.html', data)
                except Exception as ex:
                    pass

            elif action == 'deleteconfiguracionrecursos':
                try:
                    data['title'] = u'Eliminar Configuracion de Recurso'
                    data['configuracion'] = ConfiguracionRecurso.objects.get(pk=request.GET['id'])
                    return render(request, 'aprobar_silabo/deleteconfiguracionrecursos.html', data)
                except Exception as ex:
                    pass

            elif action == 'addlistaverificacion':
                try:
                    data['title'] = u'Adicionar Lista de Verificación'
                    data['id_tiporecurso'] = int(request.GET['id'])
                    f = ListaVerificacionForm()
                    data['form'] = f
                    return render(request, 'aprobar_silabo/addlistaverificacion.html', data)
                except Exception as ex:
                    pass

            elif action == 'editlistaverificacion':
                try:
                    data['title'] = u'Editar Lista de Verificación'
                    data['listaverificacion'] = listaverificacion = ListaVerificacion.objects.get(pk=request.GET['id'])
                    initial = model_to_dict(listaverificacion)
                    f = ListaVerificacionForm(initial=initial)
                    data['form'] = f
                    return render(request, 'aprobar_silabo/editlistaverificacion.html', data)
                except Exception as ex:
                    pass

            elif action == 'deletelistaverificacion':
                try:
                    data['title'] = u'Borrar Lista de Verificación'
                    data['listaverificacion'] = ListaVerificacion.objects.get(pk=request.GET['id'])
                    return render(request, 'aprobar_silabo/deletelistaverificacion.html', data)
                except Exception as ex:
                    pass

            elif action == 'descargarsilaboszip':
                try:
                    noti = Notificacion(cuerpo='Generación zip en progreso',
                                        titulo=f'Generacion de archivo de los sílabos al periodo: {periodo.nombre}',
                                        destinatario=persona,
                                        url='',
                                        prioridad=1, app_label='SGA',
                                        fecha_hora_visible=datetime.now() + timedelta(days=1), tipo=2,
                                        en_proceso=True)
                    noti.save(request)
                    genera_zip_silabos_background(request=request, notiid=noti.pk,persona=persona,periodo=periodo).start()
                    return JsonResponse({"result": True,
                                         "mensaje": u"El archivo (zip) se está generando. Verifique su apartado de notificaciones después de unos minutos.",
                                         "btn_notificaciones": traerNotificaciones(request, data, persona)})
                except Exception as ex:
                    pass

            elif action == 'delformato':
                try:
                    data['title'] = u'Eliminar formato'
                    data['configuracion'] = ConfiguracionRecurso.objects.get(pk=request.GET['idc'])
                    data['formato'] = FormatoArchivo.objects.get(pk=request.GET['idf'])
                    return render(request, "aprobar_silabo/delformato.html", data)
                except Exception as ex:
                    pass


            elif action == 'configuracionlistaverificacion':
                try:
                    data['title'] = u'Configuración de listas de verificación'
                    search = None
                    data['tiporecurso'] = tiporecurso = TipoRecurso.objects.get(pk=int(request.GET['id']))
                    listasverificacion = ListaVerificacion.objects.filter(status=True, tiporecurso=tiporecurso)
                    if 's' in request.GET:
                        search = request.GET['s']
                        s = search.split(" ")
                        if len(s) == 2:
                            listasverificacion = listasverificacion.filter(
                                Q(descripcion__icontains=s[0]) & Q(descripcion__icontains=s[1]))
                        else:
                            listasverificacion = listasverificacion.filter(descripcion__icontains=search)
                    paging = MiPaginador(listasverificacion, 25)
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
                    data['listasverificacion'] = page.object_list
                    data['search'] = search if search else ""
                    return render(request, 'aprobar_silabo/configuracionlistasverificacion.html', data)
                except Exception as ex:
                    pass

            return HttpResponseRedirect(request.path)
        else:
            try:
                data['title'] = u'Aprobar sílabo y confirmación de reactivo de materias'
                if not request.session['periodo'].visible:
                    return HttpResponseRedirect("/?info=Periodo Inactivo.")
                filtro_carreras = Q(status=True)
                if not persona.usuario.is_superuser:
                    filtro_carreras = filtro_carreras & (Q(coordinadorcarrera__in=persona.gruposcarrera(periodo)) | Q(pk__in=persona.mis_carreras().values_list("id", flat=True).distinct()))
                miscarreras = Carrera.objects.filter(filtro_carreras).distinct()
                if miscarreras.values("id").exists():
                    data['mallas'] = eMallas = Malla.objects.filter(pk__in=Materia.objects.values_list('asignaturamalla__malla_id', flat=True).filter(status=True, asignaturamalla__malla__carrera__in=miscarreras,nivel__periodo=periodo).distinct()).distinct()
                else:
                    data['mallas'] = eMallas = Malla.objects.filter(pk__in=Materia.objects.values_list('asignaturamalla__malla_id', flat=True).filter(status=True, nivel__periodo=periodo).distinct()).distinct()
                    miscarreras = Carrera.objects.filter(pk__in=eMallas.values_list('carrera__id', flat=True)).distinct()
                data['nivelmalla'] = NivelMalla.objects.filter(status=True)
                url_vars = ''
                search = None
                mallaid = None
                nivelmallaid = None
                ids = None
                filtro = Q(activo=True) & Q(status=True) & Q(materia__nivel__periodo__visible=True) & \
                         Q(materia__nivel__periodo=periodo) & Q(materia__status=True)

                if miscarreras:
                    filtro = filtro & Q(materia__asignaturamalla__malla__carrera__in=miscarreras)
                if 'nid' in request.GET:
                    nid = int(request.GET['nid'])
                    url_vars += f'&nid={nid}'
                    if int(request.GET['nid']) > 0:
                        nivelmallaid = NivelMalla.objects.get(pk=int(request.GET['nid']))
                        filtro = filtro & Q(materia__asignaturamalla__nivelmalla__id=nivelmallaid.id)
                    else:
                        nivelmallaid = int(request.GET['nid'])
                if 'mid' in request.GET:
                    mid = int(request.GET['mid'])
                    url_vars += f'&mid={mid}'
                    if int(request.GET['mid']) > 0:
                        mallaid = Malla.objects.get(pk=int(request.GET['mid']))
                        filtro = filtro & Q(materia__asignaturamalla__malla__carrera__id=mallaid.carrera.id)
                    else:
                        mallaid = int(request.GET['mid'])
                if 'id' in request.GET:
                    ids = int(request.GET['id'])
                    filtro = filtro & Q(materia__id=int(request.GET['id']))

                if 's' in request.GET:
                    search = request.GET['s']
                    url_vars += f'&s={search}'
                    s = search.split(" ")
                    if len(s) == 2:
                        filtro = filtro & Q((Q(profesor__persona__nombres__icontains=s[0]) &
                                             Q(profesor__persona__apellido1__icontains=s[1])) |
                                            (Q(profesor__persona__apellido1__icontains=s[0]) &
                                             Q(profesor__persona__apellido2__icontains=s[1])) |
                                            (Q(materia__asignatura__nombre__icontains=s[0]) &
                                             Q(materia__asignatura__nombre__icontains=s[1])))
                    else:
                        filtro = filtro & Q(Q(profesor__persona__apellido1__icontains=search) |
                                            Q(profesor__persona__apellido2__icontains=search) |
                                            Q(materia__asignatura__nombre__icontains=search))

                eProfesorMaterias = ProfesorMateria.objects.filter(filtro).distinct('materia').order_by('materia')
                paging = MiPaginador(eProfesorMaterias, 25)
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

                ids_profesormateria_pagina = [profesormateria.id for profesormateria in page.object_list]
                profesormateria_listado = ProfesorMateria.objects.filter(id__in=ids_profesormateria_pagina).\
                    annotate(tienecreadosilabo=Exists(Silabo.objects.filter(status=True, materia_id=OuterRef('materia_id'))),
                             totalguiapractica=Count('id', filter=Q(materia__silabo__silabosemanal__gpguiapracticasemanal__status=True)),
                             tienesilaboword=Exists(Archivo.objects.filter(status=True, tipo_id=8, archivo__contains='.doc', materia_id=OuterRef('materia_id'))))

                data['listadounidades'] = periodo.unidadesperiodo_set.values_list('descripcion', 'orden', 'fechainicio', 'fechafin', 'tipoprofesor__nombre').filter(status=True).order_by('fechainicio')
                data['page'] = page
                data['profesormaterias'] = profesormateria_listado
                data['search'] = search if search else ""
                data["url_vars"] = url_vars
                data['mid'] = mallaid.id if mallaid else 0
                data['nid'] = nivelmallaid.id if nivelmallaid else 0
                data['ids'] = ids
                data['persona'] = persona
                data['aprobar'] = variable_valor('APROBAR_SILABO')
                data['rechazar'] = variable_valor('RECHAZAR_SILABO')
                data['pendiente'] = variable_valor('PENDIENTE_SILABO')
                data['periodo'] = periodo
                listadomeses = []
                fechas_mensuales = list(rrule(MONTHLY, dtstart=periodo.inicio, until=periodo.fin))
                for fechames in fechas_mensuales:
                    listadomeses.append(fechames)
                data['listadomeses'] = listadomeses
                d = datetime.now()
                data['horasegundo'] = d.strftime('%Y%m%d_%H%M%S')
                return render(request, "aprobar_silabo/view.html", data)
            except Exception as ex:
                return HttpResponseRedirect(f"/?info={ex.__str__()}")
