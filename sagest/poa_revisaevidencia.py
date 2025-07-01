# -*- coding: UTF-8 -*-

import json

from datetime import datetime, timedelta

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.db.models import Q
from django.forms import model_to_dict
from django.http import HttpResponse, HttpResponseRedirect, JsonResponse
from django.shortcuts import render
from django.template.context import Context
from django.template.loader import get_template

from decorators import secure_module
from sagest.forms import AccionDocumentoRevisaForm, EvidenciaDocumentalForm, AccionDocumentoRevisaActividadForm, \
    ExpertoMatrizValoracionForm, ExpertoExternoMatrizValoracionForm, ArchivoActivoBajaForm, ArchivoMatrizValoracionForm, \
    FirmasMatrizValoracionForm, ArchivoMatrizForm, ArchivoMatrizEvaluacionForm, PrevalidacionForm
from sagest.funciones import encrypt_id
from sagest.models import AccionDocumentoDetalle, AccionDocumentoDetalleRecord, PeriodoPoa, Departamento, \
    AccionDocumento, InformeGenerado, ObjetivoEstrategico, EvidenciaDocumentalPoa, RubricaPoa, IndicadorPoa, \
    EvaluacionPeriodoPoa, MatrizValoracionPoa, DetalleMatrizValoracionPoa, MatrizValoracionExpertosPoa, \
    MatrizEvaluacionFirmasPoa, MatrizArchivosPoa, TIPO_MATRIZPOAARCHIVO, DetalleMatrizEvaluacionPoa, HistorialValidacionEvidencia, UsuarioEvidencia
from settings import PERSONA_APRUEBA_POA
from sga.commonviews import adduserdata
from sga.funcionesxhtml2pdf import conviert_html_to_pdf, download_html_to_pdf
from sga.models import MONTH_CHOICES, MESES_CHOICES, Persona, Carrera
from sga.funciones import log, numeroactividades, ultimocodigoactividad, generar_nombre, notificacion


@login_required(redirect_field_name='ret', login_url='/loginsagest')
@transaction.atomic()
@secure_module
def view(request):
    data = {'title': u'Revisar Evidencia'}
    adduserdata(request, data)
    persona = request.session['persona']
    usuario = request.user
    hoy = datetime.now()
    if request.method == 'POST':
        action = request.POST['action']
        if action == 'sin_evidencia':
            try:
                f = AccionDocumentoRevisaForm(request.POST)
                if f.is_valid():
                    if int(request.POST['record']) == 0:
                        acciondocumentodetallerecord = AccionDocumentoDetalleRecord(acciondocumentodetalle_id=int(request.POST['id']),
                                                                                    observacion_envia="SAGES: NO EXITE REGISTRADO EVIDENCIA",
                                                                                    observacion_revisa=f.cleaned_data['observacion'],
                                                                                    usuario_revisa=request.user,
                                                                                    estado_accion_revisa=f.cleaned_data['estado_accion'],
                                                                                    estado_accion_aprobacion=7,
                                                                                    fecha_revisa=datetime.now())
                    else:
                        acciondocumentodetallerecord = AccionDocumentoDetalleRecord.objects.get(pk=int(request.POST['record']))
                        acciondocumentodetallerecord.observacion_revisa = f.cleaned_data['observacion']
                        acciondocumentodetallerecord.usuario_revisa = request.user
                        acciondocumentodetallerecord.estado_accion_revisa = f.cleaned_data['estado_accion']
                        acciondocumentodetallerecord.fecha_revisa = datetime.now()
                    acciondocumentodetallerecord.save(request)
                    acciondocumentodetallerecord.acciondocumentodetalle.estado_accion = 4
                    acciondocumentodetallerecord.acciondocumentodetalle.save(request)
                    log(u'añadio documento con revision sin evidencia: %s' % acciondocumentodetallerecord.id, request, "add")
                    return JsonResponse({"result": "ok"})
                else:
                    raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return HttpResponse(json.dumps({"result": "bad", "mensaje": "Error al guardar los datos."}), content_type="application/json")

        if action == 'sin_evidenciados':
            try:
                f = AccionDocumentoRevisaActividadForm(request.POST)
                if f.is_valid():
                    if int(request.POST['record']) == 0:
                        acciondocumentodetallerecord = AccionDocumentoDetalleRecord(acciondocumentodetalle_id=int(request.POST['id']),
                                                                                    observacion_envia="SAGES: NO EXITE REGISTRADO EVIDENCIA",
                                                                                    observacion_revisa=f.cleaned_data['observacion'],
                                                                                    usuario_revisa=request.user,
                                                                                    estado_accion_revisa=f.cleaned_data['rubrica'].id,
                                                                                    rubrica_revisa=f.cleaned_data['rubrica'],
                                                                                    estado_accion_aprobacion=7,
                                                                                    rubrica_aprobacion_id=7,
                                                                                    fecha_revisa=datetime.now())
                    else:
                        acciondocumentodetallerecord = AccionDocumentoDetalleRecord.objects.get(pk=int(request.POST['record']))
                        acciondocumentodetallerecord.observacion_revisa = f.cleaned_data['observacion']
                        acciondocumentodetallerecord.usuario_revisa = request.user
                        acciondocumentodetallerecord.estado_accion_revisa = f.cleaned_data['rubrica'].id
                        acciondocumentodetallerecord.rubrica_revisa = f.cleaned_data['rubrica']
                        acciondocumentodetallerecord.fecha_revisa = datetime.now()
                    acciondocumentodetallerecord.save(request)
                    acciondocumentodetallerecord.acciondocumentodetalle.estado_accion = 4
                    acciondocumentodetallerecord.acciondocumentodetalle.estado_rubrica_id = 4
                    acciondocumentodetallerecord.acciondocumentodetalle.save(request)
                    log(u'añadio documento con revision sin evidencia: %s' % acciondocumentodetallerecord.id, request, "add")
                    return JsonResponse({"result": "ok"})
                else:
                    raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return HttpResponse(json.dumps({"result": "bad", "mensaje": "Error al guardar los datos."}), content_type="application/json")


        if action == 'con_evidencia':
            try:
                f = AccionDocumentoRevisaForm(request.POST)
                if f.is_valid():
                    if int(request.POST['record']) == 0:
                        acciondocumentodetallerecord = AccionDocumentoDetalleRecord(acciondocumentodetalle_id=int(request.POST['id']),
                                                                                    observacion_revisa=f.cleaned_data['observacion'],
                                                                                    usuario_revisa=request.user,
                                                                                    estado_accion_revisa=f.cleaned_data['estado_accion'],
                                                                                    estado_accion_aprobacion=7,
                                                                                    fecha_revisa=datetime.now())
                    else:
                        acciondocumentodetallerecord = AccionDocumentoDetalleRecord.objects.get(pk=int(request.POST['record']))
                        acciondocumentodetallerecord.observacion_revisa = f.cleaned_data['observacion']
                        acciondocumentodetallerecord.usuario_revisa = request.user
                        acciondocumentodetallerecord.estado_accion_revisa = f.cleaned_data['estado_accion']
                        acciondocumentodetallerecord.fecha_revisa = datetime.now()
                    acciondocumentodetallerecord.save(request)
                    acciondocumentodetallerecord.acciondocumentodetalle.estado_accion = 4
                    acciondocumentodetallerecord.acciondocumentodetalle.save(request)
                    log(u'añadio documento con revision con evidencia: %s' % acciondocumentodetallerecord.id, request,
                        "add")
                    return HttpResponse(json.dumps({"result": "ok"}), content_type="application/json")
                else:
                    raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return HttpResponse(json.dumps({"result": "bad", "mensaje": "Error al guardar los datos."}), content_type="application/json")

        if action == 'con_evidenciados':
            try:
                f = AccionDocumentoRevisaActividadForm(request.POST)
                if f.is_valid():
                    if int(request.POST['record']) == 0:
                        acciondocumentodetallerecord = AccionDocumentoDetalleRecord(acciondocumentodetalle_id=int(request.POST['id']),
                                                                                    observacion_revisa=f.cleaned_data['observacion'],
                                                                                    usuario_revisa=request.user,
                                                                                    estado_accion_revisa=f.cleaned_data['rubrica'].id,
                                                                                    rubrica_revisa=f.cleaned_data['rubrica'],
                                                                                    estado_accion_aprobacion=7,
                                                                                    rubrica_aprobacion_id=7,
                                                                                    fecha_evidencia=f.cleaned_data['fecha_evidencia'],
                                                                                    fecha_revisa=datetime.now())
                    else:
                        acciondocumentodetallerecord = AccionDocumentoDetalleRecord.objects.get(pk=int(request.POST['record']))
                        acciondocumentodetallerecord.observacion_revisa = f.cleaned_data['observacion']
                        acciondocumentodetallerecord.usuario_revisa = request.user
                        acciondocumentodetallerecord.estado_accion_revisa = f.cleaned_data['rubrica'].id
                        acciondocumentodetallerecord.rubrica_revisa = f.cleaned_data['rubrica']
                        acciondocumentodetallerecord.fecha_revisa = datetime.now()
                        acciondocumentodetallerecord.fecha_evidencia = f.cleaned_data['fecha_evidencia']
                    acciondocumentodetallerecord.save(request)
                    acciondocumentodetallerecord.acciondocumentodetalle.estado_accion = 4
                    acciondocumentodetallerecord.acciondocumentodetalle.estado_rubrica_id = 4
                    acciondocumentodetallerecord.acciondocumentodetalle.save(request)
                    log(u'añadio documento con revision con evidencia: %s' % acciondocumentodetallerecord.id, request,
                        "add")
                    return HttpResponse(json.dumps({"result": "ok"}), content_type="application/json")
                else:
                    raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return HttpResponse(json.dumps({"result": "bad", "mensaje": "Error al guardar los datos."}), content_type="application/json")

        if action == 'descargarpoapdf':
            try:
                departamento = Departamento.objects.get(pk=request.POST['iddepartamento'])
                periodopoa = PeriodoPoa.objects.get(pk=request.POST['idperiodopoa'])
                reportepdf = departamento.pdf_poadepartamento(periodopoa)
                return reportepdf
            except Exception as ex:
                pass

        if action == 'addevidenciadocumental':
            try:
                evidenciadocumental = EvidenciaDocumentalPoa(evidencia=request.POST['evidencia'],
                                                             descripcion=request.POST['descripcion'],
                                                             acciondocumentodetalle_id=request.POST['documentodetalle'])
                evidenciadocumental.save(request)
                log(u'Adicinó evidencia documental: %s' % evidenciadocumental, request, "add")
                return JsonResponse({"result": "ok", 'codigoevid': evidenciadocumental.id, 'evidencia': evidenciadocumental.evidencia, 'descripcion': evidenciadocumental.descripcion })
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        if action == 'editevidenciadocumental':
            try:
                evidencia = EvidenciaDocumentalPoa.objects.get(pk=request.POST['codievid'])
                evidencia.evidencia = request.POST['evidencia']
                evidencia.descripcion = request.POST['descripcion']
                evidencia.save(request)
                log(u'Modifico evidencia documental: %s ' % evidencia, request, "edit")
                return JsonResponse({"result": "ok", "evidencia": evidencia.evidencia, "descripcion": evidencia.descripcion })
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        if action == 'itemevidenciadocumental':
            try:
                evidenciadocumental = EvidenciaDocumentalPoa.objects.get(pk=request.POST['id'])
                evidencia = evidenciadocumental.evidencia
                idevidencia = evidenciadocumental.id
                return JsonResponse({"result": "ok", 'evidencia': evidencia, 'codigoevid': idevidencia})
            except Exception as ex:
                return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

        if action == 'eliminarevidenciadocumental':
            try:
                evidenciadocumental = EvidenciaDocumentalPoa.objects.get(pk=request.POST['idcodigoevid'])
                log(u'Eliminó evidencia documental: %s' % evidenciadocumental, request, "del")
                evidenciadocumental.delete()
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al eliminar los datos."})

        if action == 'addmatrizvaloracion':
            try:
                lista = request.POST['listamatriz']
                idevaluacionperiodo = request.POST['idevaluacionperiodo']
                iddepartamento = request.POST['iddepartamento']
                if not MatrizValoracionPoa.objects.filter(departamento_id=iddepartamento, evaluacionperiodo_id=idevaluacionperiodo, status=True).exists():
                    matriz = MatrizValoracionPoa(departamento_id=iddepartamento, evaluacionperiodo_id=idevaluacionperiodo, status=True)
                    matriz.save(request)
                    for lis in lista.split('|'):
                        cadenalista = lis.split('_')
                        codigorubrica = cadenalista[0]
                        cumplimiento = cadenalista[1]
                        observacion = cadenalista[2]
                        codigoactividad = cadenalista[3]
                        detallematriz = DetalleMatrizValoracionPoa(matrizvaloracion=matriz,
                                                                   actividad_id=codigoactividad,
                                                                   estado_rubrica_id=codigorubrica,
                                                                   cumplimiento=cumplimiento,
                                                                   descripcion=observacion)
                        detallematriz.save(request)
                else:
                    matriz = MatrizValoracionPoa.objects.get(departamento_id=iddepartamento, evaluacionperiodo_id=idevaluacionperiodo, status=True)
                    for lis in lista.split('|'):
                        cadenalista = lis.split('_')
                        codigorubrica = cadenalista[0]
                        cumplimiento = cadenalista[1]
                        observacion = cadenalista[2]
                        codigoactividad = cadenalista[3]
                        if DetalleMatrizValoracionPoa.objects.filter(matrizvaloracion=matriz, actividad_id=codigoactividad, status=True):
                            detallematriz = DetalleMatrizValoracionPoa.objects.get(matrizvaloracion=matriz, actividad_id=codigoactividad, status=True)
                        else:
                            detallematriz = DetalleMatrizValoracionPoa(matrizvaloracion=matriz,
                                                                       actividad_id=codigoactividad,
                                                                       estado_rubrica_id=codigorubrica,
                                                                       cumplimiento=cumplimiento,
                                                                       descripcion=observacion)
                            detallematriz.save(request)
                        detallematriz.estado_rubrica_id = codigorubrica
                        detallematriz.cumplimiento = cumplimiento
                        detallematriz.descripcion = observacion
                        detallematriz.save(request)
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        if action == 'actualizamatrizvaloracion':
            try:
                lista = DetalleMatrizEvaluacionPoa.objects.get(pk=request.POST['iddetmatrizvaloracion'])
                lista.semanaplanificada = request.POST['id_semanaplan']
                lista.semanaejecutada = request.POST['id_semanaejec']
                lista.cumplimientosemana = request.POST['porcentajesemana']
                lista.indicadoreficacia = request.POST['cod_eficacia']
                lista.indicadoreficienciatiempo = request.POST['cod_eficienciatiempo']
                lista.indicadoreficiencia = request.POST['cod_eficienciatp']
                lista.indicadordesempeno = request.POST['cod_desempeno']
                lista.save(request)
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al actualizar los datos."})

        if action == 'actualizamatrizvaloracionpresupuesto':
            try:
                lista = DetalleMatrizEvaluacionPoa.objects.get(pk=request.POST['iddetmatrizvaloracion'])
                lista.presupuestoreformado = request.POST['cod_planreformado']
                lista.presupuestoutilizado = request.POST['cod_planutilizado']
                lista.indicadoreficienciapresupuesto = request.POST['cod_eficienciapresupuesto']
                lista.indicadoreficiencia = request.POST['cod_eficienciatp']
                lista.indicadordesempeno = request.POST['cod_desempeno']
                lista.save(request)
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al actualizar los datos."})

        if action == 'actualizacumplimientototal':
            try:
                lista = DetalleMatrizEvaluacionPoa.objects.get(pk=request.POST['iddetmatrizvaloracion'])

                lista.metaejecutada = request.POST['cod_metaejecutada']
                if not request.POST['cod_cumplimientoejecutado'] == '-':
                    lista.cumplimientometa = request.POST['cod_cumplimientoejecutado']
                if lista.matrizvaloracion.evaluacionperiodo.informeanual:
                    lista.cumplimientoindicador = request.POST['cod_cumplimientoindicador']
                    lista.cumplimientoobjoperativo = request.POST['cod_cumplimientoobjetivo']
                lista.save(request)
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al actualizar los datos."})

        if action == 'actualizaresultadosevaluacion':
            try:
                lista = DetalleMatrizEvaluacionPoa.objects.get(pk=request.POST['iddetmatrizvaloracion'])
                lista.observacion = request.POST['cod_observacion']
                lista.recomendacion = request.POST['cod_recomendacion']
                lista.save(request)
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al actualizar los datos."})

        if action == 'matrizvaloracion_pdf':
            try:
                data['evaluacionperiodo'] = evaluacionperiodo = EvaluacionPeriodoPoa.objects.get(pk=int(request.POST['idevaluacionperiodo']))
                data['rubricapoa'] = RubricaPoa.objects.filter(muestraformulario=True, status=True)
                data['departamento'] = departamento = Departamento.objects.get(pk=int(request.POST['idd']))
                data['matriz'] = matriz = MatrizValoracionPoa.objects.get(evaluacionperiodo=evaluacionperiodo, departamento=departamento, status=True)
                data['listadoexperto'] = matriz.matrizvaloracionexpertospoa_set.filter(status=True)
                listindicadores = matriz.detallematrizvaloracionpoa_set.filter(status=True)
                data['documento'] = ObjetivoEstrategico.objects.filter(pk__in=listindicadores.values_list('actividad__objetivooperativo__objetivotactico__objetivoestrategico_id').filter(status=True).distinct().order_by('actividad__objetivooperativo__objetivotactico__objetivoestrategico_id')).order_by('orden', 'programa_id',)
                data['hoy'] = datetime.now().date()
                return download_html_to_pdf(
                    'poa_revisaevidencia/matrizvaloracion_pdf.html',
                    {
                        'pagesize': 'A4',
                        'data': data,
                    }
                )
            except Exception as ex:
                pass

        if action == 'matrizevaluacion_pdf':
            try:
                data['title'] = u'Matriz de evaluación semestral.'
                listaaplicar = []
                cadena = request.POST['listamatriz'].split(',')
                for elemento in cadena:
                    if elemento:
                        listaaplicar.append(int(elemento))
                data['listamatriz'] = listaaplicar
                data['totalpromediodesempeno'] = request.POST['totalpromediodesempeno']
                data['totalpromedioobjetivo'] = request.POST['totalpromedioobjetivo']
                data['evaluacionperiodo'] = evaluacionperiodo = EvaluacionPeriodoPoa.objects.get(pk=int(request.POST['idevaluacionperiodo']))
                data['departamento'] = departamento = Departamento.objects.get(pk=int(request.POST['idd']))
                matriz = MatrizValoracionPoa.objects.get(evaluacionperiodo=evaluacionperiodo, departamento=departamento,status=True)
                listindicadores = matriz.detallematrizevaluacionpoa_set.filter(status=True)
                data['documento'] = ObjetivoEstrategico.objects.filter(pk__in=listindicadores.values_list('actividad__objetivooperativo__objetivotactico__objetivoestrategico_id').filter(status=True).distinct().order_by('actividad__objetivooperativo__objetivotactico__objetivoestrategico_id')).order_by('programa_id','orden')
                data['listafirmas'] = matriz.matrizevaluacionfirmaspoa_set.filter(status=True).order_by('tipofirma')
                if  evaluacionperiodo.informeanual:
                    pagina = 'poa_revisaevidencia/matrizevaluacionanual_pdf.html'
                else:
                    pagina = 'poa_revisaevidencia/matrizevaluacion_pdf.html'
                return download_html_to_pdf(
                    pagina,
                    {
                        'pagesize': 'A4',
                        'data': data,
                    }
                )
            except Exception as ex:
                pass


        if action == 'informematrizevaluacion_pdf':
            try:
                data['title'] = u'Matriz de evaluación semestral.'
                listaaplicar = []
                listadesempeno = []
                cadena = request.POST['listamatriz'].split(',')
                cadenadesempeno = request.POST['listamatrizdesem'].split(',')
                for elemento in cadena:
                    if elemento:
                        listaaplicar.append(int(elemento))
                for elementodesempeno in cadenadesempeno:
                    if elementodesempeno:
                        listadesempeno.append(int(elementodesempeno))
                data['listamatriz'] = listaaplicar
                data['listadesempeno'] = listadesempeno
                data['totalpromediodesempeno'] = request.POST['totalpromediodesempeno']
                data['evaluacionperiodo'] = evaluacionperiodo = EvaluacionPeriodoPoa.objects.get(pk=int(request.POST['idevaluacionperiodo']))
                data['departamento'] = departamento = Departamento.objects.get(pk=int(request.POST['idd']))
                data['matriz'] = matriz = MatrizValoracionPoa.objects.get(evaluacionperiodo=evaluacionperiodo, departamento=departamento,status=True)
                if matriz.matrizarchivospoa_set.filter(tipomatrizarchivo=3, status=True):
                    data['matrizinforme'] = matriz.matrizarchivospoa_set.get(tipomatrizarchivo=3, status=True)
                mes = ["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre"]
                data['fecha'] = u"%s de %s del %s" % (matriz.fecha.day, str(mes[matriz.fecha.month - 1]), matriz.fecha.year)
                listindicadores = matriz.detallematrizevaluacionpoa_set.filter(status=True)
                data['documento'] = ObjetivoEstrategico.objects.filter(pk__in=listindicadores.values_list('actividad__objetivooperativo__objetivotactico__objetivoestrategico_id').filter(status=True).distinct().order_by('actividad__objetivooperativo__objetivotactico__objetivoestrategico_id')).order_by('orden', 'programa_id')
                data['listafirmas'] = numerolistasfirmas = matriz.matrizevaluacionfirmaspoa_set.filter(status=True).order_by('tipofirma')
                data['numlistafirmas'] = numerolistasfirmas.count()
                if numerolistasfirmas.count() > 2:
                    data['responsable'] = numerolistasfirmas.filter(tipofirma=1)[0]
                    data['revisor'] = numerolistasfirmas.filter(tipofirma=2)[0]
                    data['aprobador'] = numerolistasfirmas.filter(tipofirma=3)[0]
                data['fechahoy'] = datetime.now().date()
                if evaluacionperiodo.informeanual:
                    data['id_totalobjetivo'] = request.POST['id_totalobjetivo']
                    pagina = 'poa_revisaevidencia/informematrizevaluacionanual_pdf.html'
                else:
                    pagina = 'poa_revisaevidencia/informematrizevaluacion_pdf.html'
                return download_html_to_pdf(
                    pagina,
                    {
                        'pagesize': 'A4',
                        'data': data,
                    }
                )
            except Exception as ex:
                pass

        elif action == 'addexperto':
            try:
                f = ExpertoMatrizValoracionForm(request.POST)
                if f.is_valid():
                    matriz = MatrizValoracionPoa.objects.get(pk=int(request.POST['id']))
                    matrizexpertos = MatrizValoracionExpertosPoa(matriz=matriz,
                                                                 personaexperto_id=f.cleaned_data['experto'],
                                                                 denominacion_id=f.cleaned_data['denominacion'])
                    matrizexpertos.save(request)
                    log(u'Adicionó experto a matriz valoracion poa: %s' % matriz, request,"add")
                    return JsonResponse({"result": "ok"})
                else:
                    raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'addfirma':
            try:
                f = FirmasMatrizValoracionForm(request.POST)
                if f.is_valid():
                    matriz = MatrizValoracionPoa.objects.get(pk=int(request.POST['id']))
                    matrizfirmas = MatrizEvaluacionFirmasPoa(matriz=matriz,
                                                             personafirma_id=f.cleaned_data['personafirma'],
                                                             tipofirma=f.cleaned_data['tipofirma'])
                    matrizfirmas.save(request)
                    log(u'Adicionó firma a matriz evaluacion poa: %s' % matrizfirmas, request,"add")
                    return JsonResponse({"result": "ok"})
                else:
                    raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'addexpertoexterno':
            try:
                f = ExpertoExternoMatrizValoracionForm(request.POST)
                if f.is_valid():
                    matriz = MatrizValoracionPoa.objects.get(pk=int(request.POST['id']))
                    matrizexpertosexternos = MatrizValoracionExpertosPoa(matriz=matriz,
                                                                         personaexterna=f.cleaned_data['personaexterna'],
                                                                         cargopersonaexterna=f.cleaned_data['cargopersonaexterna'])
                    matrizexpertosexternos.save(request)
                    log(u'Adicionó experto externo a matriz valoracion poa: %s' % matriz, request,"add")
                    return JsonResponse({"result": "ok"})
                else:
                    raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'delexperto':
            try:
                experto = MatrizValoracionExpertosPoa.objects.get(pk=int(request.POST['id']))
                experto.delete()
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'delfirma':
            try:
                firma = MatrizEvaluacionFirmasPoa.objects.get(pk=int(request.POST['id']))
                firma.delete()
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'generarmatrizevaluacion':
            try:
                hoy = datetime.now().date()
                if request.POST['totalpromediodesempeno'] == '-':
                    totalpromediodesempeno = 0
                else:
                    totalpromediodesempeno = request.POST['totalpromediodesempeno']
                totalpromedioobjetivo = request.POST['totalpromedioobjetivo']
                if not MatrizArchivosPoa.objects.filter(matrizvaloracionpoa_id=request.POST['idmatrizpoa'], tipomatrizarchivo=2, status=True):
                    matrizevaluacion = MatrizArchivosPoa(matrizvaloracionpoa_id=request.POST['idmatrizpoa'],
                                                         fecha=hoy,
                                                         totaldesempeno=totalpromediodesempeno,
                                                         totalobjetivo=totalpromedioobjetivo,
                                                         tipomatrizarchivo=2)
                    matrizevaluacion.save(request)
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'generarinforme':
            try:
                hoy = datetime.now().date()
                numeroinforme = 1
                if MatrizArchivosPoa.objects.filter(fecha__year=hoy.year, tipomatrizarchivo=3):
                    matrizarchivos = MatrizArchivosPoa.objects.filter(fecha__year=hoy.year, tipomatrizarchivo=3).order_by('-numeroinforme')[0]
                    numeroinforme = matrizarchivos.numeroinforme + 1
                if not MatrizArchivosPoa.objects.filter(matrizvaloracionpoa_id=request.POST['idmatrizpoa'], tipomatrizarchivo=3, status=True):
                    matrizarchivo = MatrizArchivosPoa(matrizvaloracionpoa_id=request.POST['idmatrizpoa'],
                                                      numeroinforme=numeroinforme,
                                                      fecha=hoy,
                                                      tipomatrizarchivo=3)
                    matrizarchivo.save(request)
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'addarchivomatrizvaloracion':
            try:
                f = ArchivoMatrizValoracionForm(request.POST, request.FILES)
                # 2.5MB - 2621440
                # 5MB - 5242880
                # 10MB - 10485760
                # 20MB - 20971520
                # 50MB - 5242880
                # 100MB 104857600
                # 250MB - 214958080
                # 500MB - 429916160
                if 'archivomatrizvaloracion' in request.FILES:
                    d = request.FILES['archivomatrizvaloracion']
                    newfile = None
                    newfilesd = d._name
                    ext = newfilesd[newfilesd.rfind("."):]
                    if ext == '.pdf' or ext == '.PDF':
                        a = 1
                    else:
                        return JsonResponse({"result": "bad", "mensaje": u"Error, solo archivos .pdf."})
                    if d.size > 5242880:
                        return JsonResponse({"result": "bad", "mensaje": u"Error, archivo mayor a 4 Mb."})
                if f.is_valid():
                    matriz = MatrizValoracionPoa.objects.get(pk=request.POST['id'])
                    matriz.fecha = f.cleaned_data['fecha']
                    if 'archivomatrizvaloracion' in request.FILES:
                        newfile = request.FILES['archivomatrizvaloracion']
                        newfile._name = generar_nombre("arcmatrizval_", newfile._name)
                        matriz.archivo=newfile
                    matriz.save(request)
                    return JsonResponse({"result": "ok"})
                else:
                    raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'actualizarmatrizarchivo':
            try:
                f = ArchivoMatrizForm(request.POST, request.FILES)
                if 'archivo' in request.FILES:
                    d = request.FILES['archivo']
                    newfile = None
                    newfilesd = d._name
                    ext = newfilesd[newfilesd.rfind("."):]
                    if ext == '.pdf' or ext == '.PDF':
                        a = 1
                    else:
                        return JsonResponse({"result": "bad", "mensaje": u"Error, solo archivos .pdf."})
                    if d.size > 5242880:
                        return JsonResponse({"result": "bad", "mensaje": u"Error, archivo mayor a 4 Mb."})
                if f.is_valid():
                    matrizarchivo = MatrizArchivosPoa.objects.get(pk=request.POST['id'])
                    matrizarchivo.numeroacta = f.cleaned_data['numeroacta']
                    matrizarchivo.fecha = f.cleaned_data['fecha']
                    matrizarchivo.numeroinforme = f.cleaned_data['numeroinforme']
                    if 'archivo' in request.FILES:
                        newfile = request.FILES['archivo']
                        newfile._name = generar_nombre("informesemestral_", newfile._name)
                        matrizarchivo.archivo=newfile
                        listadoindicadores = matrizarchivo.matrizvaloracionpoa.detallematrizevaluacionpoa_set.filter(status=True)
                        for indi in listadoindicadores:
                            listadorecord = AccionDocumentoDetalleRecord.objects.filter(acciondocumentodetalle__acciondocumento__indicadorpoa=indi.actividad, procesado=False, status=True)
                            for lista in listadorecord:
                                lista.rubrica_revisa=indi.estado_rubrica
                                lista.rubrica_aprobacion=indi.estado_rubrica
                                lista.fecha_aprobacion=datetime.now()
                                lista.usuario_revisa=request.user
                                lista.usuario_aprobacion=request.user
                                lista.observacion_revisa='-'
                                lista.observacion_aprobacion='-'
                                lista.estado_accion_revisa=indi.estado_rubrica.id
                                lista.estado_accion_aprobacion=indi.estado_rubrica.id
                                lista.procesado=True
                                lista.save(request)

                                acciondoumento = lista.acciondocumentodetalle
                                acciondoumento.estado_rubrica=indi.estado_rubrica
                                acciondoumento.mostrar=True
                                acciondoumento.estado_accion=indi.estado_rubrica.id
                                acciondoumento.save(request)

                                listaevidencia = EvidenciaDocumentalPoa.objects.filter(acciondocumentodetalle=lista.acciondocumentodetalle, evaluacionperiodo__isnull=True, status=True)
                                for evi in listaevidencia:
                                    evi.evaluacionperiodo=matrizarchivo.matrizvaloracionpoa.evaluacionperiodo
                                    evi.save(request)
                    matrizarchivo.save(request)
                    return JsonResponse({"result": "ok"})
                else:
                    raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'actualizarmatrizevaluacion':
            try:
                f = ArchivoMatrizEvaluacionForm(request.POST, request.FILES)
                if 'archivo' in request.FILES:
                    d = request.FILES['archivo']
                    newfile = None
                    newfilesd = d._name
                    ext = newfilesd[newfilesd.rfind("."):]
                    if ext == '.pdf' or ext == '.PDF':
                        a = 1
                    else:
                        return JsonResponse({"result": "bad", "mensaje": u"Error, solo archivos .pdf."})
                    if d.size > 5242880:
                        return JsonResponse({"result": "bad", "mensaje": u"Error, archivo mayor a 4 Mb."})
                if f.is_valid():
                    matrizarchivo = MatrizArchivosPoa.objects.get(pk=request.POST['id'])
                    matrizarchivo.fecha = f.cleaned_data['fecha']
                    if 'archivo' in request.FILES:
                        newfile = request.FILES['archivo']
                        newfile._name = generar_nombre("matrizevalemestral_", newfile._name)
                        matrizarchivo.archivo=newfile
                    matrizarchivo.save(request)
                    return JsonResponse({"result": "ok"})
                else:
                    raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'aplicaindicador':
            try:
                detallematriz = DetalleMatrizEvaluacionPoa.objects.filter(actividad__objetivooperativo_id=request.POST['codigoindi'], matrizvaloracion__evaluacionperiodo__informeanual=True, status=True)
                for det in detallematriz:
                    if det.aplica:
                        det.aplica=False
                        det.save(request)
                    else:
                        det.aplica = True
                        det.save(request)
                return JsonResponse({'result': 'ok', 'valor': det.aplica})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'prevalidar':
            try:
                record = AccionDocumentoDetalleRecord.objects.get(pk=encrypt_id(request.POST['idrecord']))
                form = PrevalidacionForm(request.POST)
                if not form.is_valid():
                    return JsonResponse({'result': True, "form": [{k: v[0]} for k, v in form.errors.items()], "message": "Error en el formulario"})
                notificar = form.cleaned_data['notificar']
                if not record.meta:
                    record.meta = record.acciondocumentodetalle.meta_documento()
                    record.save(request)
                if notificar:
                    record.numero = form.cleaned_data['numero']
                    record.estadorevision = form.cleaned_data['estadorevision']
                    record.usuario_revisa = usuario
                    record.fecha_revisa = hoy
                    record.observacion_revisa = form.cleaned_data['observacion_revisa']
                    record.save(request)
                    responsable = record.usuario_envia.persona_set.filter(status=True).first()
                    titulo = f"Validación de evidencia POA ({record.get_estadorevision_display()})"
                    mensaje = f'Se ha validado la evidencia de la actividad {record.acciondocumentodetalle.acciondocumento} con la meta ejecutada: {record.numero} y estado {record.get_estadorevision_display()}'
                    notificacion(titulo, mensaje, responsable, None,
                                 f'/poa_subirevidencia', record.pk, 1, 'sagest',
                                 AccionDocumentoDetalleRecord, request)

                historial = HistorialValidacionEvidencia(evidencia=record,
                                                         persona=persona,
                                                         accion=3 if notificar else 2,
                                                         estadorevision=form.cleaned_data['estadorevision'],
                                                         metaejecutada=form.cleaned_data['numero'],
                                                         observacion=form.cleaned_data['observacion_revisa'],
                                                         archivo=record.archivo)
                historial.save(request)
                log(u'Prevalido evidencia de actividad: %s' % record, request, "edit")
                return JsonResponse({'result': True, 'data_return': True, 'mensaje': 'Validación realizada con éxito.'})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": True, "mensaje": u"Error al guardar los datos."})


        return HttpResponse(json.dumps({"result": "bad", "mensaje": "Solicitud Incorrecta."}), content_type="application/json")
    else:
        if 'action' in request.GET:
            action = request.GET['action']

            if action == 'revisadepartamento':
                try:
                    data['title'] = u'Departamento revisión documentos.'
                    data['new'] = request.GET.get('new', False)
                    if int(request.GET['idp']) < 4:
                        data['departamento'] = Departamento.objects.filter(objetivoestrategico__periodopoa_id=int(request.GET['idp']), objetivoestrategico__status=True).distinct()
                        data['periodo'] = int(request.GET['idp'])
                        data['periodopoa'] = PeriodoPoa.objects.get(pk=int(request.GET['idp']))
                        return render(request, "poa_revisaevidencia/revisadepartamento.html", data)
                    else:
                        data['departamento'] = ObjetivoEstrategico.objects.values('departamento__id','departamento__nombre','carrera__id','carrera__nombre').filter(periodopoa_id=int(request.GET['idp']), status=True).distinct().order_by('departamento__nombre','departamento__id','carrera__id','carrera__nombre')
                        data['periodo'] = int(request.GET['idp'])
                        data['periodopoa'] = PeriodoPoa.objects.get(pk=int(request.GET['idp']))
                        return render(request, "poa_revisaevidencia/revisadepartamentocarrera.html", data)
                except Exception as ex:
                    pass

            if action == 'revisadepartamentodos':
                try:
                    data['title'] = u'Departamento revisión documentos.'
                    # data['departamento'] = ObjetivoEstrategico.objects.values('departamento__id','departamento__nombre','carrera__id','carrera__nombre').filter(periodopoa_id=int(request.GET['idp']), status=True).distinct().order_by('departamento__nombre','departamento__id','carrera__id','carrera__nombre')
                    data['departamento'] = ObjetivoEstrategico.objects.filter(periodopoa_id=int(request.GET['idp']), status=True).order_by('departamento_id', 'carrera_id', 'gestion_id').distinct('departamento_id','carrera_id','gestion_id')
                    data['periodo'] = int(request.GET['idp'])
                    data['periodopoa'] = periodopoa = PeriodoPoa.objects.get(pk=int(request.GET['idp']))
                    data['evaluacionperiodopoa'] = evaluacionperiodopoa = periodopoa.evaluacionperiodopoa_set.filter(status=True).order_by('id')
                    data['totalevaluacionperiodopoa'] = evaluacionperiodopoa.count()
                    data['tipomatrizarchivo'] = TIPO_MATRIZPOAARCHIVO
                    return render(request, "poa_revisaevidencia/revisadepartamentodos.html", data)
                except Exception as ex:
                    pass

            if action == 'addarchivomatrizvaloracion':
                try:
                    data['title'] = u'Subir archivo matriz valoración'
                    data['matrizvaloracion'] = matriz = MatrizValoracionPoa.objects.get(evaluacionperiodo_id=request.GET['id'],departamento=request.GET['idd'], status=True)
                    form = ArchivoMatrizValoracionForm(initial={'fecha': matriz.fecha})
                    data['form'] = form
                    return render(request, "poa_revisaevidencia/addarchivomatrizvaloracion.html", data)
                except Exception as ex:
                    pass

            if action == 'actualizarmatrizarchivo':
                try:
                    data['title'] = u'Actualizar o subir informe firmado'
                    data['matrizarchivo'] = matrizarchivo = MatrizArchivosPoa.objects.get(matrizvaloracionpoa_id=request.GET['idmatriz'], tipomatrizarchivo=3, status=True)
                    if request.GET['totalpromediodesempeno'] == '-':
                        matrizarchivo.totaldesempeno=0
                    else:
                        matrizarchivo.totaldesempeno = request.GET['totalpromediodesempeno']
                    matrizarchivo.totalobjetivo = request.GET['id_totalobjetivo']
                    matrizarchivo.save(request)
                    form = ArchivoMatrizForm(initial={'numeroacta': matrizarchivo.numeroacta,
                                                      'fecha': matrizarchivo.fecha,
                                                      'numeroinforme': matrizarchivo.numeroinforme})
                    data['form'] = form
                    return render(request, "poa_revisaevidencia/actualizarmatrizarchivo.html", data)
                except Exception as ex:
                    pass

            if action == 'actualizarmatrizevaluacion':
                try:
                    data['title'] = u'Actualizar o subir matriz de evaluación'
                    data['matrizarchivo'] = matrizarchivo = MatrizArchivosPoa.objects.get(matrizvaloracionpoa_id=request.GET['idmatriz'], tipomatrizarchivo=2 , status=True)
                    if request.GET['totalpromediodesempeno'] == '-':
                        matrizarchivo.totaldesempeno = 0
                    else:
                        matrizarchivo.totaldesempeno = request.GET['totalpromediodesempeno']
                    matrizarchivo.totalobjetivo = request.GET['totalpromedioobjetivo']
                    matrizarchivo.save(request)
                    form = ArchivoMatrizEvaluacionForm(initial={'fecha': matrizarchivo.fecha})
                    data['form'] = form
                    return render(request, "poa_revisaevidencia/actualizarmatrizevaluacion.html", data)
                except Exception as ex:
                    pass

            if action == 'periodosevaluacion':
                try:
                    data['title'] = u'Matriz de evaluación semestral.'
                    data['departamento'] = departamento =  Departamento.objects.get(pk=int(request.GET['idd']))
                    data['periodopoa'] = periodo = PeriodoPoa.objects.get(pk=int(request.GET['idp']))
                    if not departamento.matrizvaloracionpoa_set.filter(evaluacionperiodo__periodopoa=periodo, status=True):
                        for peri in periodo.evaluacionperiodopoa_set.filter(status=True):
                            matrizpoa = MatrizValoracionPoa(evaluacionperiodo=peri, departamento=departamento)
                            matrizpoa.save(request)
                    data['listadomatrizpoa'] = departamento.matrizvaloracionpoa_set.filter(evaluacionperiodo__periodopoa=periodo, status=True).order_by('evaluacionperiodo__id')
                    return render(request, "poa_revisaevidencia/periodosevaluacion.html", data)
                except Exception as ex:
                    pass

            if action == 'matrizevaluacion':
                try:
                    data['title'] = u'Matriz de evaluación semestral.'
                    data['evaluacionperiodo'] = evaluacionperiodo = EvaluacionPeriodoPoa.objects.get(pk=int(request.GET['evaluacionperiodo']))
                    data['porcentajedesempeno'] = evaluacionperiodo.porcentajedesempeno / 100
                    data['porcentajemeta'] = evaluacionperiodo.porcentajemeta / 100
                    data['departamento'] = departamento = Departamento.objects.get(pk=int(request.GET['idd']))
                    data['periodo'] = int(request.GET['idp'])
                    mostrargenerar = False
                    generarinforme = True
                    hoy = datetime.now().date()
                    if hoy > evaluacionperiodo.fechafin:
                        mostrargenerar = True
                    data['mostrargenerar'] = mostrargenerar
                    data['periodopoa'] = periodopoa = PeriodoPoa.objects.get(pk=int(request.GET['idp']))
                    data['matriz'] = matriz = MatrizValoracionPoa.objects.get(evaluacionperiodo=evaluacionperiodo, departamento=departamento, status=True)
                    if matriz.matrizarchivospoa_set.filter(status=True, tipomatrizarchivo=2):
                        generarinforme = False
                        data['matrizarchivo'] = matriz.matrizarchivospoa_set.get(tipomatrizarchivo=2, status=True)
                    data['generarinforme'] = generarinforme
                    if matriz.detallematrizevaluacionpoa_set.filter(status=True):
                        listindicadores = matriz.detallematrizevaluacionpoa_set.filter(status=True)
                    else:
                        listadomatrizvaloracion = DetalleMatrizValoracionPoa.objects.filter(matrizvaloracion__evaluacionperiodo__periodopoa=periodopoa, matrizvaloracion__departamento=departamento, status=True).order_by('-id')
                        for lisvaloracion in listadomatrizvaloracion:
                            if not DetalleMatrizEvaluacionPoa.objects.filter(matrizvaloracion=matriz,actividad=lisvaloracion.actividad, status=True):
                                detalleevaluacion =DetalleMatrizEvaluacionPoa(matrizvaloracion=matriz,
                                                                              actividad=lisvaloracion.actividad,
                                                                              cumplimiento=lisvaloracion.cumplimiento,
                                                                              estado_rubrica=lisvaloracion.estado_rubrica,
                                                                              semanaplanificada=lisvaloracion.semanaplanificada,
                                                                              semanaejecutada=lisvaloracion.semanaejecutada,
                                                                              cumplimientosemana=lisvaloracion.cumplimientosemana)
                                detalleevaluacion.save(request)
                        listindicadores = matriz.detallematrizevaluacionpoa_set.filter(status=True)
                    data['documento'] = ObjetivoEstrategico.objects.filter(pk__in=listindicadores.values_list('actividad__objetivooperativo__objetivotactico__objetivoestrategico_id').filter(status=True).distinct().order_by('actividad__objetivooperativo__objetivotactico__objetivoestrategico_id')).order_by('programa_id', 'orden')
                    return render(request, "poa_revisaevidencia/matrizevaluacion.html", data)
                except Exception as ex:
                    pass

            if action == 'matrizresultadoevaluacion':
                try:
                    data['title'] = u'Matriz de resultado evaluación semestral.'
                    data['evaluacionperiodo'] = evaluacionperiodo = EvaluacionPeriodoPoa.objects.get(pk=int(request.GET['evaluacionperiodo']))
                    mostrargenerar = False
                    generarinforme = True
                    hoy = datetime.now().date()
                    if hoy > evaluacionperiodo.fechafin:
                        mostrargenerar = True
                    data['mostrargenerar'] = mostrargenerar
                    data['departamento'] = departamento = Departamento.objects.get(pk=int(request.GET['idd']))
                    data['periodo'] = int(request.GET['idp'])
                    data['periodopoa'] = PeriodoPoa.objects.get(pk=int(request.GET['idp']))
                    data['matriz'] = matriz = MatrizValoracionPoa.objects.get(evaluacionperiodo=evaluacionperiodo, departamento=departamento, status=True)
                    if matriz.matrizarchivospoa_set.filter(status=True, tipomatrizarchivo=3):
                        generarinforme = False
                        data['matrizarchivo'] = matriz.matrizarchivospoa_set.get(tipomatrizarchivo=3, status=True)
                    data['generarinforme'] = generarinforme
                    listindicadores = matriz.detallematrizevaluacionpoa_set.filter(status=True)
                    data['documento'] = ObjetivoEstrategico.objects.filter(pk__in=listindicadores.values_list('actividad__objetivooperativo__objetivotactico__objetivoestrategico_id').filter(status=True).distinct().order_by('actividad__objetivooperativo__objetivotactico__objetivoestrategico_id')).order_by('programa_id', 'orden')
                    return render(request, "poa_revisaevidencia/matrizresultadoevaluacion.html", data)
                except Exception as ex:
                    pass

            if action == 'descargarevidenciadocumentalpdf':
                try:
                    data = {}
                    data['matriz'] = matriz = MatrizValoracionPoa.objects.get(pk=request.GET['idmatriz'], status=True)
                    data['departamento'] = departamento = Departamento.objects.get(pk=request.GET['idd'])
                    data['periodopoaevaluacion'] = periodopoaevaluacion = EvaluacionPeriodoPoa.objects.get(pk=request.GET['evaluacionperiodo'])
                    if matriz.matrizarchivospoa_set.filter(tipomatrizarchivo=3, status=True):
                        if matriz.matrizarchivospoa_set.filter(archivo='', tipomatrizarchivo=3, status=True):
                            sineval = False
                            evidenciadocumental = EvidenciaDocumentalPoa.objects.filter(acciondocumentodetalle__acciondocumento__indicadorpoa__objetivooperativo__objetivotactico__objetivoestrategico__periodopoa=periodopoaevaluacion.periodopoa,
                                                                                        acciondocumentodetalle__acciondocumento__indicadorpoa__objetivooperativo__objetivotactico__objetivoestrategico__departamento=departamento,
                                                                                        status=True, evaluacionperiodo__isnull=True)
                        else:
                            sineval = True
                            evidenciadocumental = EvidenciaDocumentalPoa.objects.filter(acciondocumentodetalle__acciondocumento__indicadorpoa__objetivooperativo__objetivotactico__objetivoestrategico__periodopoa=periodopoaevaluacion.periodopoa,
                                                                                        acciondocumentodetalle__acciondocumento__indicadorpoa__objetivooperativo__objetivotactico__objetivoestrategico__departamento=departamento,
                                                                                        status=True, evaluacionperiodo=periodopoaevaluacion)
                    else:
                        sineval = False
                        evidenciadocumental = EvidenciaDocumentalPoa.objects.filter(acciondocumentodetalle__acciondocumento__indicadorpoa__objetivooperativo__objetivotactico__objetivoestrategico__periodopoa=periodopoaevaluacion.periodopoa,
                                                                                    acciondocumentodetalle__acciondocumento__indicadorpoa__objetivooperativo__objetivotactico__objetivoestrategico__departamento=departamento,
                                                                                    status=True, evaluacionperiodo__isnull=True)
                    data['sineval'] = sineval
                    data['objetivosestratejicos'] = ObjetivoEstrategico.objects.filter(pk__in=evidenciadocumental.values_list('acciondocumentodetalle__acciondocumento__indicadorpoa__objetivooperativo__objetivotactico__objetivoestrategico__id'), status=True)
                    if evidenciadocumental:
                        data['userelabora'] = Persona.objects.get(usuario_id=evidenciadocumental[0].usuario_creacion_id)
                    return conviert_html_to_pdf(
                        'poa_revisaevidencia/descargarevidenciadocumentalpdf.html',
                        {
                            'pagesize': 'A4',
                            'data': data,
                        }
                    )
                except Exception as ex:
                    pass

            if action == 'matrizvaloracionpoa':
                try:
                    data['title'] = u'Matriz valoración poa'
                    data['evaluacionperiodo'] = evaluacionperiodo = EvaluacionPeriodoPoa.objects.get(pk=int(request.GET['evaluacionperiodo']))
                    data['rubricapoa'] = RubricaPoa.objects.filter(muestraformulario=True, status=True)
                    data['departamento'] = departamento = Departamento.objects.get(pk=int(request.GET['idd']))
                    data['periodo'] = int(request.GET['idp'])
                    data['periodopoa'] = PeriodoPoa.objects.get(pk=int(request.GET['idp']))
                    existematriz = 0
                    existearchivo = 0
                    data['matriz'] = matriz = MatrizValoracionPoa.objects.get(evaluacionperiodo=evaluacionperiodo, departamento=departamento, status=True)
                    if not matriz.detallematrizvaloracionpoa_set.filter(status=True):
                        if evaluacionperiodo.informeanual:
                            lista1 = AccionDocumentoDetalle.objects.filter(acciondocumento__indicadorpoa__objetivooperativo__objetivotactico__objetivoestrategico__departamento_id=int(request.GET['idd']),
                                                                           acciondocumento__indicadorpoa__objetivooperativo__objetivotactico__objetivoestrategico__departamento__status=True,
                                                                           acciondocumento__indicadorpoa__objetivooperativo__objetivotactico__objetivoestrategico__periodopoa_id=int(request.GET['idp']),
                                                                           acciondocumento__indicadorpoa__objetivooperativo__objetivotactico__objetivoestrategico__periodopoa__status=True,
                                                                           # acciondocumento__status=True,status=True,inicio__gte=evaluacionperiodo.fechainicio, fin__lte=evaluacionperiodo.fechafin)
                                                                           acciondocumento__status=True,status=True, acciondocumentodetallerecord__procesado=False, inicio__year=evaluacionperiodo.fechainicio.year)
                            lista2 = AccionDocumentoDetalle.objects.filter(acciondocumento__indicadorpoa__objetivooperativo__objetivotactico__objetivoestrategico__departamento_id=int(request.GET['idd']),
                                                                           acciondocumento__indicadorpoa__objetivooperativo__objetivotactico__objetivoestrategico__departamento__status=True,
                                                                           acciondocumento__indicadorpoa__objetivooperativo__objetivotactico__objetivoestrategico__periodopoa_id=int(request.GET['idp']),
                                                                           acciondocumento__indicadorpoa__objetivooperativo__objetivotactico__objetivoestrategico__periodopoa__status=True,
                                                                           acciondocumento__status=True, status=True, acciondocumentodetallerecord__isnull=True,inicio__year=evaluacionperiodo.fechainicio.year)
                            lista3 = AccionDocumentoDetalle.objects.filter(acciondocumento__indicadorpoa__objetivooperativo__objetivotactico__objetivoestrategico__departamento_id=int(request.GET['idd']),
                                                                           acciondocumento__indicadorpoa__objetivooperativo__objetivotactico__objetivoestrategico__departamento__status=True,
                                                                           acciondocumento__indicadorpoa__objetivooperativo__objetivotactico__objetivoestrategico__periodopoa_id=int(request.GET['idp']),
                                                                           acciondocumento__indicadorpoa__objetivooperativo__objetivotactico__objetivoestrategico__periodopoa__status=True,
                                                                           acciondocumento__status=True, status=True, acciondocumentodetallerecord__procesado=True, acciondocumentodetallerecord__rubrica_aprobacion_id=3, inicio__year=evaluacionperiodo.fechainicio.year).exclude(acciondocumento__indicadorpoa__id__in=lista1.values_list('acciondocumento__indicadorpoa__id'))
                            listindicadores = lista1 | lista2 | lista3

                        else:
                            lista1 = AccionDocumentoDetalle.objects.filter(acciondocumento__indicadorpoa__objetivooperativo__objetivotactico__objetivoestrategico__departamento_id=int(request.GET['idd']),
                                                                           acciondocumento__indicadorpoa__objetivooperativo__objetivotactico__objetivoestrategico__departamento__status=True,
                                                                           acciondocumento__indicadorpoa__objetivooperativo__objetivotactico__objetivoestrategico__periodopoa_id=int(request.GET['idp']),
                                                                           acciondocumento__indicadorpoa__objetivooperativo__objetivotactico__objetivoestrategico__periodopoa__status=True,
                                                                           acciondocumento__status=True,status=True,inicio__gte=evaluacionperiodo.fechainicio, fin__lte=evaluacionperiodo.fechafin)
                            listindicadores = lista1
                        data['documento'] = ObjetivoEstrategico.objects.filter(pk__in=listindicadores.values_list('acciondocumento__indicadorpoa__objetivooperativo__objetivotactico__objetivoestrategico_id').distinct()).order_by('orden', 'programa_id')
                        data['totalactividades'] = listindicadores.values_list('acciondocumento__indicadorpoa__id').distinct().order_by('acciondocumento__indicadorpoa__id')
                    else:
                        existematriz = 1
                        if matriz.archivo:
                            existearchivo = 1
                        listindicadores = matriz.detallematrizvaloracionpoa_set.filter(status=True)
                        data['documento'] = ObjetivoEstrategico.objects.filter(pk__in=listindicadores.values_list('actividad__objetivooperativo__objetivotactico__objetivoestrategico_id').filter(status=True).distinct().order_by('actividad__objetivooperativo__objetivotactico__objetivoestrategico_id')).order_by('orden', 'programa_id')
                        data['totalactividades'] = listindicadores.values_list('actividad_id').filter(status=True).distinct().order_by('actividad_id')
                    data['existematriz'] = existematriz
                    data['existearchivo'] = existearchivo
                    return render(request, "poa_revisaevidencia/matrizvaloracionpoa.html", data)
                except Exception as ex:
                    pass

            elif action == 'listadoexpertos':
                try:
                    data['title'] = u'Listado Expertos'
                    data['matrizvaloracion'] = matriz = MatrizValoracionPoa.objects.get(evaluacionperiodo_id=int(request.GET['idpeval']), departamento_id=int(request.GET['idd']), status=True)
                    data['listaexpertos'] = matriz.matrizvaloracionexpertospoa_set.filter(status=True)
                    return render(request, "poa_revisaevidencia/listadoexpertos.html", data)
                except Exception as ex:
                    pass

            elif action == 'listadofirmas':
                try:
                    data['title'] = u'Listado Firmas'
                    data['matrizvaloracion'] = matriz = MatrizValoracionPoa.objects.get(evaluacionperiodo_id=int(request.GET['idpeval']), departamento_id=int(request.GET['idd']), status=True)
                    data['listadofirmas'] = matriz.matrizevaluacionfirmaspoa_set.filter(status=True).order_by('tipofirma')
                    return render(request, "poa_revisaevidencia/listadofirmas.html", data)
                except Exception as ex:
                    pass

            elif action == 'addexperto':
                try:
                    data['title'] = u'Adicionar experto'
                    data['matriz'] = MatrizValoracionPoa.objects.get(pk=int(request.GET['idmatrizvaloracion']))
                    form = ExpertoMatrizValoracionForm()
                    data['form'] = form
                    return render(request, "poa_revisaevidencia/addexperto.html", data)
                except Exception as ex:
                    pass

            elif action == 'addfirma':
                try:
                    data['title'] = u'Adicionar firma'
                    data['matriz'] = MatrizValoracionPoa.objects.get(pk=int(request.GET['idmatrizvaloracion']))
                    form = FirmasMatrizValoracionForm()
                    data['form'] = form
                    return render(request, "poa_revisaevidencia/addfirma.html", data)
                except Exception as ex:
                    pass

            elif action == 'addexpertoexterno':
                try:
                    data['title'] = u'Adicionar experto'
                    data['matriz'] = MatrizValoracionPoa.objects.get(pk=int(request.GET['idmatrizvaloracion']))
                    form = ExpertoExternoMatrizValoracionForm()
                    data['form'] = form
                    return render(request, "poa_revisaevidencia/addexpertoexterno.html", data)
                except Exception as ex:
                    pass

            elif action == 'delexperto':
                try:
                    data['title'] = u'Eliminar Experto'
                    data['matrizexperto'] = MatrizValoracionExpertosPoa.objects.get(pk=int(request.GET['idexperto']))
                    return render(request, "poa_revisaevidencia/delexperto.html", data)
                except Exception as ex:
                    pass

            elif action == 'delfirma':
                try:
                    data['title'] = u'Eliminar firma'
                    data['matrizfirma'] = MatrizEvaluacionFirmasPoa.objects.get(pk=int(request.GET['idfirma']))
                    return render(request, "poa_revisaevidencia/delfirma.html", data)
                except Exception as ex:
                    pass

            elif action == 'poadepartamento':
                try:
                    data['title'] = u'Revisión POA.'
                    if int(request.GET['idp']) < 4:
                        data['departamento'] = Departamento.objects.get(pk=int(request.GET['idd']))
                        data['meses'] = [x[1][:3] for x in MONTH_CHOICES]
                        data['idp'] = int(request.GET['idp'])
                        data['idd'] = int(request.GET['idd'])
                        data['periodopoa'] = PeriodoPoa.objects.get(pk=int(request.GET['idp']))
                        data['documento'] = AccionDocumento.objects.filter(status=True, acciondocumentodetalle__status=True, indicadorpoa__objetivooperativo__objetivotactico__objetivoestrategico__departamento_id=int(request.GET['idd']), indicadorpoa__objetivooperativo__objetivotactico__objetivoestrategico__departamento__status=True, indicadorpoa__objetivooperativo__objetivotactico__objetivoestrategico__periodopoa_id=int(request.GET['idp']), indicadorpoa__objetivooperativo__objetivotactico__objetivoestrategico__periodopoa__status=True).order_by('indicadorpoa__objetivooperativo', 'indicadorpoa').distinct()
                        return render(request, "poa_revisaevidencia/poadepartamento.html", data)
                    else:
                        data['departamento'] = Departamento.objects.get(pk=int(request.GET['idd']))
                        data['meses'] = [x[1][:3] for x in MONTH_CHOICES]
                        data['idp'] = int(request.GET['idp'])
                        data['idd'] = int(request.GET['idd'])
                        idc = request.GET['idc']
                        data['idc'] = int(request.GET['idc'])
                        data['carrera'] = ''
                        if idc != '0':
                            data['carrera'] = Carrera.objects.get(pk=int(request.GET['idc']))
                        data['periodopoa'] = PeriodoPoa.objects.get(pk=int(request.GET['idp']))
                        if idc == '0':
                            data['documento'] = AccionDocumento.objects.filter(status=True,acciondocumentodetalle__status=True, indicadorpoa__objetivooperativo__objetivotactico__objetivoestrategico__departamento_id=int(request.GET['idd']), indicadorpoa__objetivooperativo__objetivotactico__objetivoestrategico__carrera__isnull=True, indicadorpoa__objetivooperativo__objetivotactico__objetivoestrategico__departamento__status=True, indicadorpoa__objetivooperativo__objetivotactico__objetivoestrategico__periodopoa_id=int(request.GET['idp']), indicadorpoa__objetivooperativo__objetivotactico__objetivoestrategico__periodopoa__status=True).order_by('indicadorpoa__objetivooperativo', 'indicadorpoa').distinct()
                        else:
                            data['documento'] = AccionDocumento.objects.filter(status=True,acciondocumentodetalle__status=True, indicadorpoa__objetivooperativo__objetivotactico__objetivoestrategico__departamento_id=int(request.GET['idd']),indicadorpoa__objetivooperativo__objetivotactico__objetivoestrategico__carrera__id=int(request.GET['idc']), indicadorpoa__objetivooperativo__objetivotactico__objetivoestrategico__departamento__status=True, indicadorpoa__objetivooperativo__objetivotactico__objetivoestrategico__periodopoa_id=int(request.GET['idp']), indicadorpoa__objetivooperativo__objetivotactico__objetivoestrategico__periodopoa__status=True).order_by('indicadorpoa__objetivooperativo', 'indicadorpoa').distinct()
                        return render(request, "poa_revisaevidencia/poadepartamentocarrera.html", data)
                except Exception as ex:
                    pass

            elif action == 'poadepartamentodos':
                try:
                    data['title'] = u'Revisión POA.'
                    data['new'] = request.GET.get('new', False)
                    data['meses'] = [x[1][:3] for x in MONTH_CHOICES]
                    idp, idd, idc, idg = request.GET.get('idp',''), request.GET.get('idd', ''), request.GET.get('idc', 0), request.GET.get('idg', 0)
                    if not idp or not idd:
                        raise NameError('Error no se rececpto el periodo o el departamento')
                    data['idp'] = int(idp)
                    data['idd'] = int(idd)
                    data['idg'] = idg = int(idg) if idg else 0
                    data['idc'] = idc = int(idc) if idc else 0
                    data['departamento'] = Departamento.objects.get(pk=idd)
                    data['periodopoa'] = PeriodoPoa.objects.get(pk=idp)
                    filtro = Q(status=True, acciondocumentodetalle__status=True,
                               indicadorpoa__objetivooperativo__objetivotactico__objetivoestrategico__periodopoa_id=idp,
                               indicadorpoa__objetivooperativo__objetivotactico__objetivoestrategico__periodopoa__status=True,
                               indicadorpoa__objetivooperativo__objetivotactico__objetivoestrategico__departamento_id=idd,
                               indicadorpoa__objetivooperativo__objetivotactico__objetivoestrategico__departamento__status=True)
                    orden = ('indicadorpoa__objetivooperativo__objetivotactico__objetivoestrategico__orden',
                             'indicadorpoa__objetivooperativo__objetivotactico__orden',
                             'indicadorpoa__objetivooperativo__orden', 'indicadorpoa__orden', 'orden')
                    if idc > 0:
                        data['carrera'] = Carrera.objects.get(pk=idc)
                        filtro &= Q(indicadorpoa__objetivooperativo__objetivotactico__objetivoestrategico__carrera_id=idc)
                    elif idg > 0:
                        filtro &= Q(indicadorpoa__objetivooperativo__objetivotactico__objetivoestrategico__gestion_id=idg)
                    else:
                        filtro &= Q(indicadorpoa__objetivooperativo__objetivotactico__objetivoestrategico__gestion__isnull=True,
                                    indicadorpoa__objetivooperativo__objetivotactico__objetivoestrategico__carrera__isnull=True)
                    data['documento'] = AccionDocumento.objects.filter(filtro).order_by(*orden).distinct()
                    return render(request, "poa_revisaevidencia/poadepartamentodos.html", data)
                except Exception as ex:
                    messages.error(request, 'Error al cargar la página: %s' % ex)

            elif action == 'sin_evidencia':
                try:
                    data = {}
                    acciondocumentodetalle = AccionDocumentoDetalle.objects.get(pk=int(request.GET['iddocdet']))
                    if int(request.GET['record']) == 0:
                        form = AccionDocumentoRevisaForm()
                    else:
                        acciondocumentodetallerecord = AccionDocumentoDetalleRecord.objects.get(pk=int(request.GET['record']))
                        form = AccionDocumentoRevisaForm(initial={'observacion': acciondocumentodetallerecord.observacion_revisa,
                                                                  'estado_accion': acciondocumentodetallerecord.estado_accion_revisa})
                    data['records'] = acciondocumentodetalle.acciondocumentodetallerecord_set.all().order_by("-id")
                    form.tipo_sin_evidencia(1)
                    data['form'] = form
                    data['modadd'] = True if int(request.GET['listo']) == 0 else False
                    data['record'] = int(request.GET['record'])
                    data['idp'] = int(request.GET['idp'])
                    data['idd'] = int(request.GET['idd'])
                    data['permite_modificar'] = True
                    data['acciondocumentodetalle'] = acciondocumentodetalle.__str__()
                    data['id'] = acciondocumentodetalle.id
                    if int(request.GET['idp']) < 4:
                        template = get_template("poa_revisaevidencia/sin_evidencia.html")
                    else:
                        data['idc'] = int(request.GET['idc'])
                        template = get_template("poa_revisaevidencia/sin_evidenciacarrera.html")
                    json_content = template.render(data)
                    return HttpResponse(json.dumps({"result": "ok", 'data': json_content}), content_type="application/json")
                except Exception as ex:
                    return HttpResponse(json.dumps({"result": "bad", "mensaje": u"Error al obtener los datos."}), content_type="application/json")

            elif action == 'sin_evidenciados':
                try:
                    data = {}
                    acciondocumentodetalle = AccionDocumentoDetalle.objects.get(pk=int(request.GET['iddocdet']))
                    if int(request.GET['record']) == 0:
                        form = AccionDocumentoRevisaActividadForm()
                    else:
                        acciondocumentodetallerecord = AccionDocumentoDetalleRecord.objects.get(pk=int(request.GET['record']))
                        form = AccionDocumentoRevisaActividadForm(initial={'observacion': acciondocumentodetallerecord.observacion_revisa,
                                                                           'rubrica': acciondocumentodetallerecord.rubrica_revisa})
                    data['records'] = acciondocumentodetalle.acciondocumentodetallerecord_set.all().order_by("-id")
                    form.tipo_sin_evidencia()
                    data['rubrica'] = RubricaPoa.objects.filter(muestraformulario=True, status=True)
                    data['form'] = form
                    noevidencia = False
                    if MatrizArchivosPoa.objects.filter(matrizvaloracionpoa__evaluacionperiodo__informeanual=True, matrizvaloracionpoa__evaluacionperiodo__periodopoa_id=request.GET['idp'], matrizvaloracionpoa__departamento_id=request.GET['idd'], tipomatrizarchivo=3, status=True):
                        matriz = MatrizArchivosPoa.objects.get(matrizvaloracionpoa__evaluacionperiodo__informeanual=True, matrizvaloracionpoa__evaluacionperiodo__periodopoa_id=request.GET['idp'], matrizvaloracionpoa__departamento_id=request.GET['idd'], tipomatrizarchivo=3, status=True)
                        if matriz.archivo:
                            noevidencia = True
                    data['noevidencia'] = noevidencia
                    data['modadd'] = False
                    data['record'] = int(request.GET['record'])
                    data['idp'] = int(request.GET['idp'])
                    data['idd'] = int(request.GET['idd'])
                    data['permite_modificar'] = True
                    data['acciondocumentodetalle'] = acciondocumentodetalle.__str__()
                    data['id'] = acciondocumentodetalle.id
                    data['idc'] = int(request.GET['idc'])
                    data['acciondocumental'] = acciondocumentodetalle.evidenciadocumentalpoa_set.filter(status=True)
                    data['formevid'] = EvidenciaDocumentalForm()
                    template = get_template("poa_revisaevidencia/sin_evidenciados.html")
                    json_content = template.render(data)
                    return HttpResponse(json.dumps({"result": "ok", 'data': json_content}), content_type="application/json")
                except Exception as ex:
                    return HttpResponse(json.dumps({"result": "bad", "mensaje": u"Error al obtener los datos."}), content_type="application/json")


            elif action == 'ver_observacion':
                try:
                    data = {}
                    acciondocumento = AccionDocumento.objects.get(pk=int(request.GET['iddocumento']))
                    return HttpResponse(json.dumps({"result": "ok", 'data': acciondocumento.observacion}), content_type="application/json")
                except Exception as ex:
                    return HttpResponse(json.dumps({"result": "bad", "mensaje": u"Error al obtener los datos."}), content_type="application/json")

            elif action == 'ver_medio':
                try:
                    data = {}
                    acciondocumento = AccionDocumento.objects.get(pk=int(request.GET['iddocumento']))
                    return HttpResponse(json.dumps({"result": "ok", 'data': acciondocumento.medioverificacion.nombre}), content_type="application/json")
                except Exception as ex:
                    return HttpResponse(json.dumps({"result": "bad", "mensaje": u"Error al obtener los datos."}), content_type="application/json")

            elif action == 'con_evidencia':
                try:
                    data = {}
                    acciondocumentodetalle = AccionDocumentoDetalle.objects.get(pk=int(request.GET['iddocdet']))
                    if int(request.GET['record']) == 0:
                        form = AccionDocumentoRevisaForm()
                    else:
                        acciondocumentodetallerecord = AccionDocumentoDetalleRecord.objects.get(pk=int(request.GET['record']))
                        form = AccionDocumentoRevisaForm(initial={'observacion': acciondocumentodetallerecord.observacion_revisa,
                                                                  'estado_accion': acciondocumentodetallerecord.estado_accion_revisa})
                        data['documentodetallerecord'] = acciondocumentodetallerecord
                    data['records'] = acciondocumentodetalle.acciondocumentodetallerecord_set.all().order_by("-id")
                    form.tipo_sin_evidencia(2)
                    data['form'] = form
                    data['modadd'] = True if int(request.GET['listo']) == 0 else False
                    data['record'] = int(request.GET['record'])
                    data['idp'] = int(request.GET['idp'])
                    data['idd'] = int(request.GET['idd'])
                    data['permite_modificar'] = True
                    data['acciondocumentodetalle'] = acciondocumentodetalle.__str__()
                    data['id'] = acciondocumentodetalle.id
                    if int(request.GET['idp']) < 4:
                        template = get_template("poa_revisaevidencia/con_evidencia.html")
                    else:
                        data['idc'] = int(request.GET['idc'])
                        template = get_template("poa_revisaevidencia/con_evidenciacarrera.html")
                    json_content = template.render(data)
                    return HttpResponse(json.dumps({"result": "ok", 'data': json_content}), content_type="application/json")
                except Exception as ex:
                    return HttpResponse(json.dumps({"result": "bad", "mensaje": u"Error al obtener los datos."}), content_type="application/json")

            elif action == 'con_evidenciados':
                try:
                    data = {}
                    acciondocumentodetalle = AccionDocumentoDetalle.objects.get(pk=int(request.GET['iddocdet']))
                    if int(request.GET['record']) == 0:
                        form = AccionDocumentoRevisaActividadForm()
                    else:
                        acciondocumentodetallerecord = AccionDocumentoDetalleRecord.objects.get(pk=int(request.GET['record']))
                        form = AccionDocumentoRevisaActividadForm(initial={'observacion': acciondocumentodetallerecord.observacion_revisa,
                                                                           'fecha_evidencia': acciondocumentodetallerecord.fecha_evidencia,
                                                                           'rubrica': acciondocumentodetallerecord.rubrica_revisa})
                        data['eDocumentoRecord'] = acciondocumentodetallerecord
                        data['meta'] = acciondocumentodetallerecord.meta if acciondocumentodetallerecord.meta else acciondocumentodetalle.meta_documento()
                        validacion = acciondocumentodetallerecord.get_validacion_last()
                        if validacion:
                            data['formprevalidacion'] = PrevalidacionForm(initial={'estadorevision': validacion.estadorevision,
                                                                                   'numero': validacion.metaejecutada,
                                                                                   'observacion_revisa': validacion.observacion,
                                                                                   'notificar': validacion.accion == 3})
                        else:
                            data['formprevalidacion'] = PrevalidacionForm(initial=model_to_dict(acciondocumentodetallerecord))

                    data['records'] = acciondocumentodetalle.acciondocumentodetallerecord_set.all().order_by("-id")
                    form.tipo_sin_evidencia()
                    data['rubrica'] = RubricaPoa.objects.filter(muestraformulario=True, status=True).order_by('orden')
                    data['form'] = form
                    # data['modadd'] = True if int(request.GET['listo']) == 0 else False
                    data['modadd'] = False
                    data['record'] = int(request.GET['record'])
                    data['idp'] = int(request.GET['idp'])
                    data['idd'] = int(request.GET['idd'])
                    data['permite_modificar'] = True
                    data['eAccionDetalle'] = acciondocumentodetalle
                    data['id'] = acciondocumentodetalle.id
                    data['idc'] = int(request.GET['idc'])
                    noevidencia = False
                    if MatrizArchivosPoa.objects.filter(matrizvaloracionpoa__evaluacionperiodo__informeanual=True, matrizvaloracionpoa__evaluacionperiodo__periodopoa_id=data['idp'], matrizvaloracionpoa__departamento_id=data['idd'], tipomatrizarchivo=3, status=True):
                        matriz =  MatrizArchivosPoa.objects.get(matrizvaloracionpoa__evaluacionperiodo__informeanual=True, matrizvaloracionpoa__evaluacionperiodo__periodopoa_id=data['idp'], matrizvaloracionpoa__departamento_id=data['idd'], tipomatrizarchivo=3, status=True)
                        if matriz.archivo:
                            noevidencia = True
                    data['noevidencia'] = noevidencia
                    data['acciondocumental'] = acciondocumentodetalle.evidenciadocumentalpoa_set.filter(status=True)
                    data['formevid'] = EvidenciaDocumentalForm()
                    template = get_template("poa_revisaevidencia/con_evidenciados.html")
                    json_content = template.render(data)
                    return HttpResponse(json.dumps({"result": "ok", 'data': json_content}), content_type="application/json")
                except Exception as ex:
                    return HttpResponse(json.dumps({"result": "bad", "mensaje": u"Error al obtener los datos."}), content_type="application/json")

            elif action == 'monitoreo':
                try:
                    data = {}
                    data['idp'] = int(request.GET['idp'])
                    data['idd'] = int(request.GET['idd'])
                    data['meses'] = [x[1] for x in MONTH_CHOICES]
                    data['mes'] = datetime.now().month - 1
                    data['departamento'] = Departamento.objects.get(pk=int(request.GET['idd']))
                    if not Persona.objects.filter(usuario__usuarioevidencia__tipousuario=2, usuario__usuarioevidencia__unidadorganica_id=int(request.GET['idd'])).exists():
                        return HttpResponse(json.dumps({"result": "bad", "mensaje": u"Este departamento no tiene configurado el director, realizarlo en la opcion - Poa Usuario registra"}), content_type="application/json")
                    template = get_template("poa_revisaevidencia/monitoreo_view.html")
                    json_content = template.render(data)
                    return HttpResponse(json.dumps({"result": "ok", 'data': json_content}), content_type="application/json")
                except Exception as ex:
                    return HttpResponse(json.dumps({"result": "bad", "mensaje": u"Error al obtener los datos."}), content_type="application/json")

            elif action == 'monitoreo_pdf':
                try:
                    data = datosinforme(int(request.GET['idp']), int(request.GET['idd']), int(request.GET['mes']))
                    firma = [Persona.objects.get(usuario=request.user), Persona.objects.get(pk=PERSONA_APRUEBA_POA),
                             Persona.objects.get(usuario__usuarioevidencia__tipousuario=2, usuario__usuarioevidencia__unidadorganica_id=int(request.GET['idd']))]
                    data['firma'] = firma
                    return conviert_html_to_pdf('poa_revisaevidencia/monitoreo_pdf.html', {'pagesize': 'A4', 'data': data})
                except Exception as ex:
                    return render(request, "noexistedatos.html", data)

            elif action == 'informe':
                try:
                    data = {}
                    data['idp'] = int(request.GET['idp'])
                    data['idd'] = int(request.GET['idd'])
                    data['mes'] = mes = int(request.GET['mes'])
                    informe = InformeGenerado.objects.filter(mes=mes, periodopoa_id=int(request.GET['idp']), departamento_id=int(request.GET['idd']), status=True)
                    data['informepre'] = informe.filter(tipo=1)[0] if informe.filter(tipo=1).exists() else {}
                    data['informefin'] = informe.filter(tipo=2)[0] if informe.filter(tipo=2).exists() else {}
                    template = get_template("poa_revisaevidencia/informe_view.html")
                    json_content = template.render(data)
                    return HttpResponse(json.dumps({"result": "ok", 'data': json_content}), content_type="application/json")
                except Exception as ex:
                    return HttpResponse(json.dumps({"result": "bad", "mensaje": u"Error al obtener los datos."}), content_type="application/json")

            return HttpResponseRedirect(request.path)
        else:
            periodo = PeriodoPoa.objects.filter(status=True).order_by('-id')
            data['periodo'] = periodo
            return render(request, "poa_revisaevidencia/view.html", data)


def datosinforme(idp, idd, mes):
    data = {}
    data['idp'] = idp
    data['idd'] = idd
    periodo = PeriodoPoa.objects.get(pk=idp)
    departamento = Departamento.objects.get(pk=idd)
    data['periodo'] = periodo
    fechafinanterior = (datetime(periodo.anio, mes, 1, 0, 0, 0) - timedelta(days=1)).date()
    data['departamento'] = departamento
    data['mesid'] = mes
    data['mes'] = MESES_CHOICES[mes - 1][1]
    evidencias = AccionDocumentoDetalle.objects.filter(acciondocumento__status=True, mostrar=True, acciondocumento__indicadorpoa__objetivooperativo__objetivotactico__objetivoestrategico__periodopoa=periodo, acciondocumento__indicadorpoa__objetivooperativo__objetivotactico__objetivoestrategico__departamento=departamento, status=True).distinct()
    evidencia_mes = evidencias.filter(inicio__month=mes).distinct()
    listadelmes = []
    for e in evidencia_mes.order_by("acciondocumento__indicadorpoa__objetivooperativo", "acciondocumento"):
        if e not in listadelmes:
            listadelmes.append(e)
    excluir = []
    for e in evidencias:
        if e.inicio.month != e.fin.month:
            if e.inicio.month <= mes <= e.fin.month:
                excluir.append(e)
                if e not in listadelmes:
                    listadelmes.append(e)
    lista = []
    for p in AccionDocumentoDetalle.objects.filter(acciondocumento__status=True, mostrar=True, inicio__lt=fechafinanterior, acciondocumento__indicadorpoa__objetivooperativo__objetivotactico__objetivoestrategico__periodopoa=periodo, acciondocumento__indicadorpoa__objetivooperativo__objetivotactico__objetivoestrategico__departamento=departamento, status=True).order_by("-inicio", "acciondocumento__indicadorpoa__objetivooperativo", "acciondocumento").distinct():
        if not (p.estado_accion in [6, 2]):
            if p.acciondocumentodetallerecord_set.exists():
                record = p.detrecord()
                if record.exists():
                    if not record[0] in excluir:
                        if record[0].acciondocumentodetalle.inicio.month == record[0].acciondocumentodetalle.fin.month:
                            if record[0] not in lista:
                                lista.append(record[0])
                        else:
                            if record[0].acciondocumentodetalle.inicio.month <= mes <= record[0].acciondocumentodetalle.fin.month:
                                if record[0] not in listadelmes:
                                    listadelmes.append(record[0])
                            else:
                                if record[0] not in lista:
                                    lista.append(record[0])

    data['evidencia_anterior'] = lista
    data['evidencia_mes'] = listadelmes
    return data