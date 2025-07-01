# -*- coding: UTF-8 -*-
import io
import json
import os
import sys

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.db.models import Q, Sum, Count
from django.forms import model_to_dict
from django.http import HttpResponse, HttpResponseRedirect,JsonResponse
from django.shortcuts import render, redirect
from django.template import RequestContext
from django.template.loader import get_template
from django.core.files import File
from datetime import datetime

from unidecode import unidecode

from core.choices.models.sagest import ESTADO_REVISION_EVIDENCIA, ACCION_HISTORIAL_EVIDENCIA
from core.firmar_documentos import obtener_posicion_x_y_saltolinea
from core.firmar_documentos_ec import JavaFirmaEc
from decorators import secure_module
from sagest.forms import PeriodoPoaForm, EvaluacionPoaForm, UsuarioPermisoForm, PrevalidacionForm, AccionDocumentoRevisaActividadForm, EvidenciaDocumentalForm, AccionDocumentoRevisaForm, \
    ValidacionPOAForm, SeguimientoPoaForm, AgendarSeguimientoPoaForm, EditarSeguimientoPoaForm
from sagest.funciones import encrypt_id, carreras_departamento, get_departamento, choice_indice
from sagest.models import PeriodoPoa, InformeGenerado, EvaluacionPeriodoPoa, UsuarioEvidencia, SeccionDepartamento, ObjetivoEstrategico, TIPO_MATRIZPOAARCHIVO, Departamento, MatrizValoracionPoa, \
    AccionDocumento, EvidenciaDocumentalPoa, RubricaPoa, AccionDocumentoDetalle, AccionDocumentoDetalleRecord, HistorialValidacionEvidencia, MatrizArchivosPoa, TIPOS_USUARIO, \
    MatrizEvaluacionFirmasPoa, HistorialFirmaArchivoPoa, SeguimientoPoa, DetalleSeguimientoPoa
from sga.commonviews import adduserdata
from sga.funciones import MiPaginador, generar_nombre, log, notificacion, validar_archivo
from sga.funcionesxhtml2pdf import conviert_html_to_pdf, conviert_html_to_pdf_save_file_model
from sga.models import Carrera, Persona, MONTH_CHOICES, CUENTAS_CORREOS
from sga.tasks import send_html_mail
from sga.templatetags.sga_extras import encrypt, fecha_natural
from core.choices.models.sagest import ESTADO_SEGUIMIENTO_POA


@login_required(redirect_field_name='ret', login_url='/loginsagest')
@transaction.atomic()
@secure_module
def view(request):
    data = {}
    adduserdata(request, data)
    periodo = request.session['periodo']
    persona = request.session['persona']
    usuario = request.user
    hoy = datetime.now()
    data['es_validador'] = es_validador(usuario) or usuario.is_superuser
    if request.method == 'POST':
        action = request.POST['action']

        #PERIODOS POA
        if action == 'add':
            try:
                f = PeriodoPoaForm(request.POST, request.FILES)
                if not f.is_valid():
                    form_error = [{k: v[0]} for k, v in f.errors.items()]
                    return JsonResponse({'result': False, "form": form_error, "mensaje": "Error en el formulario"})
                newfile = None
                if 'archivo' in request.FILES:
                    newfile = request.FILES['archivo']
                    newfile._name = generar_nombre("periodopoa_", newfile._name)
                periodopoa = PeriodoPoa(anio=f.cleaned_data['anio'],
                                        descripcion=f.cleaned_data['descripcion'],
                                        diassubir=f.cleaned_data['diassubir'],
                                        diascorreccion=f.cleaned_data['diascorreccion'],
                                        mostrar=f.cleaned_data['mostrar'],
                                        matrizvaloracion=f.cleaned_data['matrizvaloracion'],
                                        matrizevaluacion=f.cleaned_data['matrizevaluacion'],
                                        archivo=newfile)
                periodopoa.save(request)
                log(u'añadio periodo poa: %s' % periodopoa, request, "add")
                return JsonResponse({"result": False})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": f"Error:{ex}"})

        elif action == 'edit':
            try:
                periodopoa = PeriodoPoa.objects.get(pk=encrypt_id(request.POST['id']))
                f = PeriodoPoaForm(request.POST, request.FILES)
                if not f.is_valid():
                    form_error = [{k: v[0]} for k, v in f.errors.items()]
                    return JsonResponse({'result': False, "form": form_error, "mensaje": "Error en el formulario"})
                newfile = None
                if 'archivo' in request.FILES:
                    newfile = request.FILES['archivo']
                    newfile._name = generar_nombre("periodopoa_", newfile._name)
                    periodopoa.archivo = newfile
                periodopoa.anio = f.cleaned_data['anio']
                periodopoa.diassubir = f.cleaned_data['diassubir']
                periodopoa.diascorreccion = f.cleaned_data['diascorreccion']
                periodopoa.mostrar = f.cleaned_data['mostrar']
                periodopoa.descripcion = f.cleaned_data['descripcion']
                periodopoa.matrizvaloracion = f.cleaned_data['matrizvaloracion']
                periodopoa.matrizevaluacion = f.cleaned_data['matrizevaluacion']
                periodopoa.save(request)
                log(u'edito periodo poa: %s' % periodopoa, request, "edit")
                return JsonResponse({"result": False})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": f"Error:{ex}"})

        elif action == 'delete':
            try:
                periodopoa = PeriodoPoa.objects.get(pk=request.POST['id'])
                periodopoa.status = False
                periodopoa.save(request)
                log(u'cambio estado de periodo poa: %s' % periodopoa, request, "edit")
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al eliminar los datos."})

        elif action == 'activar':
            try:
                periodopoa = PeriodoPoa.objects.get(pk=request.POST['id'])
                periodopoa.edicion = not periodopoa.edicion
                periodopoa.save(request)
                log(u'activo periodo poa: %s' % periodopoa, request, "edit")
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al activar el periodo."})

        elif action == 'cambiaestado':
            try:
                periodopoa = PeriodoPoa.objects.get(pk=request.POST['periodoid'])
                PeriodoPoa.objects.filter(status=True).update(activo=False)
                if periodopoa.activo:
                    periodopoa.activo = False
                else:
                    periodopoa.activo = True
                periodopoa.save()
                log(u'cambio estado periodo poa: %s' % periodopoa, request, "edit")
                return JsonResponse({'result': 'ok', 'valor': periodopoa.activo})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'duplicar':
            try:
                periodopoa = PeriodoPoa.objects.get(pk=request.POST['id'])
                periodopoa.ingresar = False
                periodopoa.save(request)
                periodopoa.id = None
                periodopoa.mostrar = False
                periodopoa.archivo = None
                periodopoa.ingresar = True
                periodopoa.edicion = True
                periodopoa.descripcion = 'TRASPASO, EDITE LA DESCRIPCION'
                periodopoa.save(request)
                a = PeriodoPoa.objects.get(pk=request.POST['id'])
                for i in InformeGenerado.objects.filter(periodopoa=a):
                    i.id = None
                    i.periodopoa = periodopoa
                    i.save(request)
                for p in PeriodoPoa.objects.filter(pk=request.POST['id']):
                    for oe in p.objetivoestrategico_set.all():
                        aux_oe = oe.objetivotactico_set.all()
                        oe.id = None
                        oe.periodopoa = periodopoa
                        oe.save(request)
                        for ot in aux_oe:
                            aux_ot = ot.objetivooperativo_set.all()
                            ot.id = None
                            ot.objetivoestrategico = oe
                            ot.save(request)
                            for oo in aux_ot:
                                aux_oo = oo.indicadorpoa_set.all()
                                oo.id = None
                                oo.objetivotactico = ot
                                oo.save(request)
                                for i in aux_oo:
                                    aux_i = i.acciondocumento_set.all()
                                    i.id = None
                                    i.objetivooperativo = oo
                                    i.save(request)
                                    for ad in aux_i:
                                        aux_ad = ad.acciondocumentodetalle_set.all()
                                        ad.id = None
                                        ad.indicadorpoa = i
                                        ad.save(request)
                                        for acd in aux_ad:
                                            aux_acd = acd.acciondocumentodetallerecord_set.all()
                                            acd.id = None
                                            acd.acciondocumento = ad
                                            acd.save(request)
                                            for adr in aux_acd:
                                                adr.id = None
                                                adr.acciondocumentodetalle = acd
                                                adr.save(request)
                log(u'duplico periodo poa: %s' % periodopoa, request, "edit")
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al procesar el traspaso."})

        # EVALUACION PERIODO POA
        elif action == 'editarperiodoevaluacion':
            try:
                f = EvaluacionPoaForm(request.POST)
                evaluacionpoa = EvaluacionPeriodoPoa.objects.get(pk=encrypt(request.POST['id']))
                if f.is_valid():
                    evaluacionpoa.descripcion = f.cleaned_data['descripcion']
                    evaluacionpoa.fechainicio = f.cleaned_data['fechainicio']
                    evaluacionpoa.fechafin = f.cleaned_data['fechafin']
                    evaluacionpoa.informeanual = f.cleaned_data['informeanual']
                    # evaluacionpoa.porcentajedesempeno = f.cleaned_data['porcentajedesempeno']
                    # evaluacionpoa.porcentajemeta = f.cleaned_data['porcentajemeta']
                    evaluacionpoa.save(request)
                    log(u'Editó evaluacion periodo poa: %s' % evaluacionpoa, request, "edit")
                    return JsonResponse({"result": False })
                else:
                    raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": True, "mensaje": u"Error al guardar los datos."})

        elif action == 'addperiodoevaluacion':
            try:
                f = EvaluacionPoaForm(request.POST)
                f.data['fechainicio'].replace("-", "/")
                f.data['fechafin'].replace("-", "/")
                if f.is_valid():
                    periodopoa = PeriodoPoa.objects.get(pk=int(encrypt(request.POST['idperiodopoa'])))
                    evaluacionpoa = EvaluacionPeriodoPoa(periodopoa=periodopoa,
                                                         descripcion=f.cleaned_data['descripcion'].upper(),
                                                         fechainicio=f.cleaned_data['fechainicio'],
                                                         fechafin=f.cleaned_data['fechafin'],
                                                         # porcentajedesempeno=f.cleaned_data['porcentajedesempeno'],
                                                         # porcentajemeta=f.cleaned_data['porcentajemeta'],
                                                         informeanual=f.cleaned_data['informeanual']
                    )
                    evaluacionpoa.save(request)
                    log(u'Añadió evaluación periodo poa: %s' % evaluacionpoa, request, "add")
                    return JsonResponse({"result": False})
                else:
                    raise NameError('Error')
            except Exception as ex:
                print([{k: v[0]} for k, v in f.errors.items()])
                transaction.set_rollback(True)
                return JsonResponse({"result": True, "mensaje": u"Error al guardar los datos."})

        elif action == 'deleteperiodopoa':
            try:
                evaluacionperiodopoa = evaluacion = EvaluacionPeriodoPoa.objects.get(pk=int(request.POST['id']))
                evaluacionperiodopoa.delete()
                log(u'Eliminó evaluación periodo poa: %s' % evaluacion, request, "delete")
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": "Error al guardar los datos."})

        # PERMISOS POA
        elif action == 'addpermisoseguimiento':
            try:
                tipo = encrypt_id(request.POST['idp'])
                form = UsuarioPermisoForm(request.POST)
                if tipo == 4:
                    form.fields['unidadorganica'].required = False
                if not form.is_valid():
                    transaction.set_rollback(True)
                    form_error = [{k: v[0]} for k, v in form.errors.items()]
                    return JsonResponse({'result': True, "form": form_error, "mensaje": "Error en el formulario"})
                usuarioevidencia = UsuarioEvidencia(tipopermiso=tipo,
                                                    userpermiso=form.cleaned_data['persona'].usuario,
                                                    unidadorganica=form.cleaned_data['unidadorganica'],
                                                    gestion=form.cleaned_data['gestion'],
                                                    carrera=form.cleaned_data['carrera'],
                                                    activo=form.cleaned_data['activo'],
                                                    cargo_text=form.cleaned_data['cargo_text'],
                                                    firmainforme=form.cleaned_data['firmainforme'],
                                                    tipousuario=form.cleaned_data['tipousuario'])
                usuarioevidencia.save(request)
                log(f'Agrego permiso: {usuarioevidencia}', request, 'add')
                return JsonResponse({'result': False, 'mensaje': 'Guardado con éxito'})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({'result': True, 'mensaje': str(ex)})

        elif action == 'editpermisoseguimiento':
            try:
                instancia = UsuarioEvidencia.objects.get(pk=encrypt_id(request.POST['id']))

                form = UsuarioPermisoForm(request.POST, instancia=instancia)
                if instancia.tipopermiso == 4:
                    form.fields['unidadorganica'].required = False
                if not form.is_valid():
                    transaction.set_rollback(True)
                    form_error = [{k: v[0]} for k, v in form.errors.items()]
                    return JsonResponse({'result': True, "form": form_error, "mensaje": "Error en el formulario"})
                instancia.userpermiso = form.cleaned_data['persona'].usuario
                instancia.unidadorganica = form.cleaned_data['unidadorganica']
                instancia.gestion = form.cleaned_data['gestion']
                instancia.carrera = form.cleaned_data['carrera']
                instancia.tipousuario = form.cleaned_data['tipousuario']
                instancia.activo = form.cleaned_data['activo']
                instancia.cargo_text = form.cleaned_data['cargo_text']
                instancia.firmainforme=form.cleaned_data['firmainforme']
                instancia.save(request)
                log(f'Edito permiso: {instancia}', request, 'edit')
                return JsonResponse({'result': False, 'mensaje': 'Guardado con éxito'})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({'result': True, 'mensaje': str(ex)})

        elif action == 'delpermisoseguimiento':
            try:
                instancia = UsuarioEvidencia.objects.get(pk=encrypt_id(request.POST['id']))
                instancia.status=False
                instancia.save(request)
                log(f'Elimino permiso de seguimiento: {instancia}', request, 'del')
                return JsonResponse({'error': False, 'mensaje': 'Guardado con éxito'})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({'error': True, 'mensaje': str(ex)})

        # REVISAR EVIDENCIA
        elif action == 'prevalidar':
            try:
                record = AccionDocumentoDetalleRecord.objects.get(pk=encrypt_id(request.POST['idrecord']))
                form = PrevalidacionForm(request.POST)
                if not form.is_valid():
                    return JsonResponse({'result': True, "form": [{k: v[0]} for k, v in form.errors.items()], "message": "Error en el formulario"})
                if not record.meta:
                    record.meta = record.acciondocumentodetalle.meta_documento()
                    record.save(request)
                notificar = form.cleaned_data['notificar']
                observacion = form.cleaned_data['observacion_validador']
                estadorevision = int(form.cleaned_data['estadorevision'])
                historial = HistorialValidacionEvidencia(evidencia=record,
                                                         persona=persona,
                                                         accion=3 if notificar else 2,
                                                         estadorevision=estadorevision,
                                                         metaejecutada=form.cleaned_data['numero'],
                                                         observacion=observacion,
                                                         archivo=record.archivo)
                historial.save(request)
                record.numero = form.cleaned_data['numero']
                record.aplica_calculo = form.cleaned_data['aplica_calculo']
                record.persona_validador = persona
                record.fecha_validacion = hoy
                estado_texto = historial.estadorevision_text()
                if notificar or estadorevision in [9, 7]:
                    record.estadorevision = estadorevision
                    record.observacion_validador = observacion
                elif estadorevision in [2, 3] or record.estadorevision == 10:
                    record.estadorevision = 9
                if notificar:
                    record.observacion_validador = observacion
                    notificar_usuarios_registra(request, record, estado_texto, observacion)

                record.save(request)
                context = {}
                context['id'] = historial.id
                context['observacion'] = historial.observacion
                context['fecha_creacion'] = historial.fecha_creacion.strftime('%d-%m-%Y %H:%M')
                context['metaejecutada'] = historial.metaejecutada
                context['persona'] = persona.nombre_completo_minus()
                context['color_estado'] = historial.color_estadorevision()
                context['accion'] = historial.accion_text()
                context['estadorevision'] = estado_texto
                context['archivo'] = historial.archivo.url if historial.archivo else ''
                log(u'Prevalido evidencia de actividad: %s' % record, request, "edit")
                return JsonResponse({'result': True, 'data_return': True, 'data': context, 'mensaje': 'Validación realizada con éxito.'})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": True, "mensaje": u"Error al guardar los datos."})

        elif action == 'sin_evidencia':
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

        elif action == 'sin_evidenciados':
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

        elif action == 'con_evidencia':
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

        elif action == 'con_evidenciados':
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

        elif action == 'remitir':
            try:
                ids_records = request.POST.getlist('ids_remitir')
                objetivo = ObjetivoEstrategico.objects.get(pk=encrypt_id(request.POST['id']))
                records = AccionDocumentoDetalleRecord.objects.filter(id__in=ids_records)
                for r in records:
                    validacion = r.get_historial_last()
                    if validacion.estadorevision in [2]:
                        r.estadorevision = 10
                        r.observacion_validador = validacion.observacion
                        r.remitido = True
                        r.save(request)
                        historial = HistorialValidacionEvidencia(evidencia=r,
                                                                 persona=persona,
                                                                 accion=4,
                                                                 estadorevision=10,
                                                                 metaejecutada=r.numero,
                                                                 observacion=validacion.observacion,
                                                                 archivo=r.archivo)
                        historial.save(request)
                        log(u'Remito para aprobación: %s' % r, request, "edit")
                notificar_responsables(request, objetivo)
                return JsonResponse({'result': False, 'mensaje': 'Remitido con éxito.'})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": True, "mensaje": f"Error al guardar los datos: {ex}"})

        elif action == 'validar':
            try:
                record = AccionDocumentoDetalleRecord.objects.get(id=encrypt_id(request.POST['id']))
                form = ValidacionPOAForm(request.POST)
                if not form.is_valid():
                    return JsonResponse({'result': True, "form": [{k: v[0]} for k, v in form.errors.items()], "message": "Error en el formulario"})
                usuario_evidencia = get_validador(usuario)
                if not usuario_evidencia:
                    raise NameError('Acción no permitida no es un responsable de validación o aprobación.')
                observacion = form.cleaned_data['observacion_aprobacion']
                estadorevision = int(form.cleaned_data['estadorevision'])
                if estadorevision in [6, 7]:
                    record.estadorevision=estadorevision
                    responsables = responsables_validar()
                    if not responsables.filter(tipousuario=4).exists() or not responsables.filter(tipousuario=5).exists():
                        raise NameError('No se puede validar, existen responsables de validación por configurar.')
                    for resp in responsables:
                        if resp.tipousuario == 4:
                            record.usuario_revisa = resp.userpermiso
                            record.observacion_revisa = observacion
                            record.fecha_revisa = hoy
                            record.save(request)
                        elif resp.tipousuario == 5:
                            record.observacion_aprobacion = observacion
                            record.usuario_aprobacion = resp.userpermiso
                            record.fecha_aprobacion = hoy
                            record.save(request)
                else:
                    record.estadorevision = 9
                    record.usuario_revisa = persona.usuario
                    record.observacion_revisa = observacion
                    observacion = form.cleaned_data['mensaje']
                record.save(request)
                historial = HistorialValidacionEvidencia(evidencia=record,
                                                         persona=persona,
                                                         accion=3,
                                                         estadorevision=estadorevision,
                                                         metaejecutada=record.numero,
                                                         observacion=observacion,
                                                         archivo=record.archivo)
                historial.save(request)
                log(u'Valido evidencia: %s' % record, request, "edit")
                return JsonResponse({'result': False, 'mensaje': 'Validado con éxito.'})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": True, "mensaje": f"Error al guardar los datos: {ex}"})

        # FECHAS MÁXIMAS DE APERTURA DE EVIDENCIAS
        elif action == 'addfechaaperturaevidencia':
            try:
                idobjetivo = request.POST['idobjetivo']
                objetivo = ObjetivoEstrategico.objects.get(pk=encrypt_id(idobjetivo))
                fecha = request.POST['fecha']
                aperturafecha = InformeGenerado(periodopoa=objetivo.periodopoa,
                                                departamento=objetivo.departamento,
                                                gestion=objetivo.gestion,
                                                carrera=objetivo.carrera,
                                                fechamax=fecha)
                aperturafecha.save(request)
                return JsonResponse({'result': True})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({'result': False, 'mensaje': f'Error: {ex})'})

        # INFORME DE EVALUACIÓN SEMESTRAL
        elif action == 'generarinforme':
            try:
                listado = json.loads(request.POST['lista_items1'])
                matriz = MatrizValoracionPoa.objects.get(pk=encrypt_id(request.POST['id']))
                idsrecords = []
                for l in listado:
                    idrecord = int(l['id_record']) if 'id_record' in l else 0
                    numero_meta = float(l['numero_meta']) if 'numero_meta' in l else 0
                    observacion = l['observacion']
                    idsrecords.append(idrecord)
                    record = AccionDocumentoDetalleRecord.objects.get(pk=idrecord)
                    if numero_meta != record.numero or observacion != record.observacion_aprobacion:
                        historial = HistorialValidacionEvidencia(evidencia=record,
                                                                 persona=persona,
                                                                 accion=3,
                                                                 estadorevision=6,
                                                                 observacion=observacion,
                                                                 archivo=record.archivo,
                                                                 metaejecutada=numero_meta)
                        historial.save(request)
                    if record.aplica_calculo and not record.estadorevision == 7:
                        record.numero = numero_meta
                        record.cumplimiento = record.calcular_cumplimiento(numero_meta)
                    record.observacion_aprobacion = observacion
                    record.save(request)
                orden = orden_records()
                records = AccionDocumentoDetalleRecord.objects.filter(id__in=idsrecords).order_by(*orden)
                url_file = generar_informe_poa(records, matriz, request)
                return JsonResponse({"result": False, "mensaje": "Informe generado con éxito."})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": True, "mensaje": f"Error al generar informe: {ex}"})

        elif action == 'firmarinforme':
            try:
                certificado = request.FILES["firma"]
                contrasenaCertificado = request.POST['palabraclave']
                razon = request.POST['razon'] if 'razon' in request.POST else ''
                extension_certificado = os.path.splitext(certificado.name)[1][1:]
                bytes_certificado = certificado.read()
                matriz_archivo = MatrizArchivosPoa.objects.get(pk=encrypt_id(request.POST['id']))
                archivo_ = matriz_archivo.archivo
                responsable_firma = matriz_archivo.get_persona_firma(persona)
                if responsable_firma.firmado:
                    raise NameError('El archivo ya fue firmado.')
                nombres = persona.nombre_completo_titulo()
                palabras = f'{nombres} {responsable_firma.get_cargo_text()}'
                x, y, numPage = obtener_posicion_x_y_saltolinea(archivo_.url, palabras, True, True)
                if not x and not y:
                    raise NameError('No se encontró la posición para la firma.')
                datau = JavaFirmaEc(
                    archivo_a_firmar=archivo_, archivo_certificado=bytes_certificado,
                    extension_certificado=extension_certificado,
                    password_certificado=contrasenaCertificado,
                    page=int(numPage), reason=razon, lx=x-20, ly=y-20).sign_and_get_content_bytes()
                archivo_ = io.BytesIO()
                archivo_.write(datau)
                archivo_.seek(0)

                _name = f'DPI_EVPOA_{matriz_archivo.fecha.year}_{matriz_archivo.numeroinforme}_firmado_{responsable_firma.id}.pdf'
                file_obj = File(archivo_, name=f"{_name}.pdf")

                responsable_firma.firmado = True
                responsable_firma.save(request)
                matriz_archivo.archivo = file_obj
                matriz_archivo.estado = 3 if matriz_archivo.firmado_all() else 2
                matriz_archivo.save(request)
                historial = HistorialFirmaArchivoPoa(matrizarchivo=matriz_archivo, archivo=file_obj, persona=persona, estado=3)
                historial.save(request)
                return JsonResponse({"result": False, "mensaje": "Guardado con exito", }, safe=False)
            except Exception as ex:
                textoerror = '{} Linea:{}'.format(ex, sys.exc_info()[-1].tb_lineno)
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error: %s" % textoerror})

        # SEGUIMIENTO POA
        elif action == 'addseguimientopoa':
            try:
                f = SeguimientoPoaForm(request.POST)
                if f.is_valid():
                    estado = int(f.cleaned_data['estado'])
                    eObjetivo = ObjetivoEstrategico.objects.get(pk=encrypt_id(request.POST['id']))
                    seguimiento = SeguimientoPoa(unidadorganica=eObjetivo.departamento,
                                                 gestion=eObjetivo.gestion,
                                                 carrera=eObjetivo.carrera,
                                                 personaseguimiento=persona,
                                                 persona=f.cleaned_data['persona'],
                                                 detalle=f.cleaned_data['detalle'].strip().upper(),
                                                 fechaagenda=f.cleaned_data['fecha'],
                                                 horaagenda=f.cleaned_data['hora'],
                                                 estado=estado)
                    registrador = seguimiento.persona
                    if estado == 2:
                        titulo = u"SEGUIMIENTO POA AGENDADO"
                        cuerpo = (f'En el marco del control, seguimiento y evaluación de la planificación operativa anual se agenda una reunión de trabajo '
                                  f'para el {fecha_natural(seguimiento.fechaagenda)} a las {seguimiento.horaagenda.strftime("%H:%M")} para revisar los avances de la gestión realizada por su Unidad.')

                        notificatodos = f.cleaned_data['notificatodos']
                        if notificatodos:
                            seguimiento.notificatodos = True
                            enviar_correo_notificacion_todos(request, eObjetivo, seguimiento, titulo, cuerpo)
                        else:
                            enviar_correo_notificacion(request, seguimiento, titulo, cuerpo)

                    elif estado == 3:
                        seguimiento.fechafinaliza = datetime.now()
                        seguimiento.observaciondpi = f.cleaned_data['observacion'].strip().upper()

                    seguimiento.save(request)

                    documentos = request.FILES.getlist('adjuntos')
                    lista_items1 = json.loads(request.POST['lista_items1'])
                    ids_excl = [int(item['id_adjunto']) for item in lista_items1 if item['id_adjunto']]
                    # Validar los archivos
                    for d in documentos:
                        items = [item for item in lista_items1 if item['archivo'] == d._name]
                        if len(items) > 1 and all(item['size'] == items[0]['size'] for item in items):
                            raise NameError(
                                f'Error, archivos duplicados {d._name}, remplace uno de los archivos duplicados.')

                        resp = validar_archivo(items[0]['descripcion'], d, ['*'], '4MB')
                        if resp['estado'] != "OK":
                            raise NameError(f"{resp['mensaje']}.")

                    for d in documentos:
                        items = [item for item in lista_items1 if item['archivo'] == d._name]
                        if not items[0]['id_adjunto']:
                            d._name = generar_nombre(f"adjunto_{seguimiento.id}_", d._name)
                            detalle = DetalleSeguimientoPoa(
                                solicitud=seguimiento,
                                persona=persona,
                                observacion=items[0]['descripcion'],
                                archivo=d)
                            detalle.save(request)
                        else:
                            detalle = DetalleSeguimientoPoa.objects.get(id=items[0]['id_adjunto'])
                            detalle.observacion = items[0]['descripcion']
                            detalle.archivo = d
                            detalle.save(request)
                        ids_excl.append(detalle.id)
                    for items in lista_items1:
                        if items['id_adjunto']:
                            detalle = DetalleSeguimientoPoa.objects.get(id=int(items['id_adjunto']))
                            detalle.observacion = items['descripcion']
                            detalle.save(request, update_fields=['observacion'])
                    seguimiento.get_detalles().exclude(id__in=ids_excl).update(status=False)

                    log(u'Añadió seguimiento poa: %s' % seguimiento, request, "add")
                    return JsonResponse({"result": False})
                else:
                    raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": True, "mensaje": f"Error al guardar los datos: {ex}"})

        elif action == 'editseguimientopoa':
            try:
                f = EditarSeguimientoPoaForm(request.POST)
                if f.is_valid():
                    seguimiento = SeguimientoPoa.objects.filter(pk=encrypt_id(request.POST['idp'])).first()
                    seguimiento.observaciondpi = f.cleaned_data['observacion'].strip().upper()
                    seguimiento.detalle = f.cleaned_data['detalle'].strip().upper()
                    seguimiento.save(request)

                    documentos = request.FILES.getlist('adjuntos')
                    lista_items1 = json.loads(request.POST['lista_items1'])
                    ids_excl = [int(item['id_adjunto']) for item in lista_items1 if item['id_adjunto']]
                    # Validar los archivos
                    for d in documentos:
                        items = [item for item in lista_items1 if item['archivo'] == d._name]
                        if len(items) > 1 and all(item['size'] == items[0]['size'] for item in items):
                            raise NameError(
                                f'Error, archivos duplicados {d._name}, remplace uno de los archivos duplicados.')

                        resp = validar_archivo(items[0]['descripcion'], d, ['*'], '4MB')
                        if resp['estado'] != "OK":
                            raise NameError(f"{resp['mensaje']}.")

                    for d in documentos:
                        items = [item for item in lista_items1 if item['archivo'] == d._name]
                        if not items[0]['id_adjunto']:
                            d._name = generar_nombre(f"adjunto_{seguimiento.id}_", d._name)
                            detalle = DetalleSeguimientoPoa(
                                solicitud=seguimiento,
                                persona=persona,
                                observacion=items[0]['descripcion'],
                                archivo=d)
                            detalle.save(request)
                        else:
                            detalle = DetalleSeguimientoPoa.objects.get(id=items[0]['id_adjunto'])
                            detalle.observacion = items[0]['descripcion']
                            detalle.archivo = d
                            detalle.save(request)
                        ids_excl.append(detalle.id)
                    for items in lista_items1:
                        if items['id_adjunto']:
                            detalle = DetalleSeguimientoPoa.objects.get(id=int(items['id_adjunto']))
                            detalle.observacion = items['descripcion']
                            detalle.save(request, update_fields=['observacion'])
                    seguimiento.get_detalles().exclude(id__in=ids_excl).update(status=False)

                    log(u'Añadió seguimiento poa: %s' % seguimiento, request, "add")
                    return JsonResponse({"result": False})
                else:
                    raise NameError('Error en el formulario')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": True, "mensaje": u"Error al guardar los datos."})

        elif action == 'finalizarseguimientopoa':
            try:
                f = EditarSeguimientoPoaForm(request.POST)
                if f.is_valid():
                    seguimiento = SeguimientoPoa.objects.filter(pk=encrypt_id(request.POST['idp'])).first()
                    seguimiento.observaciondpi = f.cleaned_data['observacion'].strip().upper()
                    seguimiento.estado = 3
                    seguimiento.fechafinaliza = datetime.now()
                    seguimiento.save(request)

                    documentos = request.FILES.getlist('adjuntos')
                    lista_items1 = json.loads(request.POST['lista_items1'])
                    ids_excl = [int(item['id_adjunto']) for item in lista_items1 if item['id_adjunto']]
                    # Validar los archivos
                    for d in documentos:
                        items = [item for item in lista_items1 if item['archivo'] == d._name]
                        if len(items) > 1 and all(item['size'] == items[0]['size'] for item in items):
                            raise NameError(
                                f'Error, archivos duplicados {d._name}, remplace uno de los archivos duplicados.')

                        resp = validar_archivo(items[0]['descripcion'], d, ['*'], '4MB')
                        if resp['estado'] != "OK":
                            raise NameError(f"{resp['mensaje']}.")

                    for d in documentos:
                        items = [item for item in lista_items1 if item['archivo'] == d._name]
                        if not items[0]['id_adjunto']:
                            d._name = generar_nombre(f"adjunto_{seguimiento.id}_", d._name)
                            detalle = DetalleSeguimientoPoa(
                                solicitud=seguimiento,
                                persona=persona,
                                observacion=items[0]['descripcion'],
                                archivo=d)
                            detalle.save(request)
                        else:
                            detalle = DetalleSeguimientoPoa.objects.get(id=items[0]['id_adjunto'])
                            detalle.observacion = items[0]['descripcion']
                            detalle.archivo = d
                            detalle.save(request)
                        ids_excl.append(detalle.id)
                    for items in lista_items1:
                        if items['id_adjunto']:
                            detalle = DetalleSeguimientoPoa.objects.get(id=int(items['id_adjunto']))
                            detalle.observacion = items['descripcion']
                            detalle.save(request, update_fields=['observacion'])
                    seguimiento.get_detalles().exclude(id__in=ids_excl).update(status=False)

                    log(u'Añadió seguimiento poa: %s' % seguimiento, request, "add")
                    return JsonResponse({"result": False})
                else:
                    raise NameError('Error en el formulario')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": True, "mensaje": u"Error al guardar los datos."})

        elif action == 'agendarseguimientopoa':
            try:
                f = AgendarSeguimientoPoaForm(request.POST)
                if f.is_valid():
                    eObjetivo = ObjetivoEstrategico.objects.get(pk=encrypt_id(request.POST['id']))
                    seguimiento = SeguimientoPoa.objects.filter(pk=encrypt_id(request.POST['idp'])).first()
                    seguimiento.estado = 2
                    seguimiento.fechaagenda = f.cleaned_data['fecha']
                    seguimiento.horaagenda = f.cleaned_data['hora']
                    seguimiento.detalle = f.cleaned_data['detalle'].strip().upper()
                    seguimiento.personaseguimiento = persona
                    seguimiento.save(request)
                    titulo = u"SEGUIMIENTO POA AGENDADO"
                    cuerpo = (f'En el marco del control, seguimiento y evaluación de la planificación operativa anual se agenda una reunión de trabajo '
                              f'para el {fecha_natural(seguimiento.fechaagenda)} a las {seguimiento.horaagenda.strftime("%H:%M")} para revisar los avances de la gestión realizada por su Unidad.')

                    notificatodos = f.cleaned_data['notificatodos']
                    if notificatodos:
                        seguimiento.notificatodos = True
                        enviar_correo_notificacion_todos(request, eObjetivo, seguimiento, titulo, cuerpo)
                    else:
                        enviar_correo_notificacion(request, seguimiento, titulo, cuerpo)
                    log(u'Agendó seguimiento poa: %s' % seguimiento, request, "edit")
                    return JsonResponse({"result": False})
                return JsonResponse({"result": True, "mensaje": u"Error al guardar los datos."})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": True, "mensaje": u"Error al guardar los datos."})

        elif action == 'reagendarseguimientopoa':
            try:
                f = AgendarSeguimientoPoaForm(request.POST)
                if f.is_valid():
                    eObjetivo = ObjetivoEstrategico.objects.get(pk=encrypt_id(request.POST['id']))
                    seguimiento = SeguimientoPoa.objects.filter(pk=encrypt_id(request.POST['idp'])).first()
                    seguimiento.estado = 5
                    fechaanterior = seguimiento.fechaagenda
                    horaanterior = seguimiento.horaagenda
                    seguimiento.fechaagenda = f.cleaned_data['fecha']
                    seguimiento.horaagenda = f.cleaned_data['hora']
                    seguimiento.detalle = f.cleaned_data['detalle'].strip().upper()
                    seguimiento.personaseguimiento = persona
                    seguimiento.save(request)
                    titulo = u"SEGUIMIENTO POA REAGENDADO"
                    cuerpo = ( f'En el marco del control, seguimiento y evaluación de la planificación operativa anual se informa que la reunión de trabajo '
                               f'agendada para el {fecha_natural(fechaanterior)} a las {horaanterior.strftime("%H:%M")}, '
                                f'ha sido reagendada para el día {fecha_natural(seguimiento.fechaagenda)} a las {seguimiento.horaagenda.strftime("%H:%M")}')
                    if seguimiento.notificatodos:
                        enviar_correo_notificacion_todos(request, eObjetivo, seguimiento, titulo, cuerpo, fechaanterior, horaanterior)
                    else:
                        enviar_correo_notificacion(request, seguimiento, titulo, cuerpo, fechaanterior, horaanterior)
                    log(u'Reagendó seguimiento poa: %s' % seguimiento, request, "edit")
                    return JsonResponse({"result": False})
                return JsonResponse({"result": True, "mensaje": u"Error al guardar los datos."})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": True, "mensaje": u"Error al guardar los datos."})

        elif action == 'delseguimientopoa':
            try:
                seguimiento = SeguimientoPoa.objects.get(pk=encrypt_id(request.POST['id']))
                seguimiento.status = False
                seguimiento.save(request)
                log(u'Eliminó seguimiento poa: %s' % seguimiento, request, "delete")
                return JsonResponse({"result": 'ok', 'mensaje': 'Registro eliminado con éxito.'})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": 'bad', "mensaje": u"Error al eliminar registro."})

        elif action == 'cancelarseguimientopoa':
            try:
                seguimiento = SeguimientoPoa.objects.get(pk=encrypt_id(request.POST['id']))
                eObjetivo = ObjetivoEstrategico.objects.get(pk=encrypt_id(request.POST['idx']))
                seguimiento.observaciondpi = request.POST['message']
                seguimiento.estado = 4
                seguimiento.save(request)
                titulo = u"SEGUIMIENTO POA CANCELADO"
                cuerpo = (f'En el marco del control, seguimiento y evaluación de la planificación operativa anual se informa que la reunión de trabajo '
                          f'agendada para el {fecha_natural(seguimiento.fechaagenda)} a las {seguimiento.horaagenda.strftime("%H:%M")}, '
                          f'ha sido cancelada, observación: {seguimiento.observaciondpi}')
                if seguimiento.notificatodos:
                    enviar_correo_notificacion_todos(request, eObjetivo, seguimiento, titulo, cuerpo)
                else:
                    enviar_correo_notificacion(request, seguimiento, titulo, cuerpo)
                log(u'Canceló seguimiento poa: %s' % seguimiento, request, "edit")
                return JsonResponse({"result": 'ok', 'mensaje': 'Seguimiento cancelado con éxito.'})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": 'bad', "mensaje": u"Error al cancelar Seguimiento."})

        return JsonResponse({"result": "bad", "mensaje": u"Solicitud Incorrecta."})
    else:
        if 'action' in request.GET:
            data['action'] = action = request.GET['action']

            if action == 'add':
                try:
                    data['title'] = u'Adicionar Periodo POA'
                    data['action'] = 'add'
                    data['switchery'] = True
                    data['form'] = PeriodoPoaForm()
                    template = get_template('poa_periodos/add.html')
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    pass

            elif action == 'edit':
                try:
                    data['title'] = u'Modificar Periodo POA'
                    data['action'] = 'edit'
                    data['switchery'] = True
                    data['periodo'] = periodo = PeriodoPoa.objects.get(pk=request.GET['id'])
                    data['id'] = periodo.id
                    data['form'] = PeriodoPoaForm(initial={'descripcion': periodo.descripcion,
                                                           'anio': periodo.anio,
                                                           'diassubir': periodo.diassubir,
                                                           'diascorreccion': periodo.diascorreccion,
                                                           'matrizvaloracion': periodo.matrizvaloracion,
                                                           'matrizevaluacion': periodo.matrizevaluacion,
                                                           'mostrar': periodo.mostrar})
                    template = get_template('poa_periodos/edit.html')
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    pass

            elif action == 'delete':
                try:
                    data['title'] = u'Eliminar Periodo POA'
                    data['periodo'] = PeriodoPoa.objects.get(pk=request.GET['id'])
                    return render(request, 'poa_periodos/delete.html', data)
                except Exception as ex:
                    pass

            elif action == 'activar':
                try:
                    data['title'] = u'Edición Total POA'
                    data['periodo'] = PeriodoPoa.objects.get(pk=int(request.GET['id']))
                    return render(request, 'poa_periodos/ediciontotal.html', data)
                except Exception as ex:
                    pass

            elif action == 'listadoevaluacion':

                try:
                    data['title'] = u'Listado Evaluación POA'
                    data['periodo'] = periodopoa = PeriodoPoa.objects.get(pk=int(request.GET['idperiodopoa']))
                    search= request.GET.get('s', '')
                    url_vars = f"&action=listadoevaluacion&idperiodopoa="+str(periodopoa.id)
                    search = None
                    tipo = None
                    if 's' in request.GET:
                        search = request.GET['s']
                        # if search:
                        listadoevaluacion = periodopoa.evaluacionperiodopoa_set.filter(descripcion__icontains=search, status=True).order_by('id')
                        url_vars += "&s={}".format(search)
                    else:
                        listadoevaluacion= periodopoa.evaluacionperiodopoa_set.filter(status=True).order_by('id')

                    paging = MiPaginador(listadoevaluacion, 25)
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
                    data['fechaactual'] = datetime.now().date().year
                    data['search'] = search if search else ""
                    data['listadoevaluacion'] = page.object_list
                    data['url_vars'] = url_vars
                    template = 'poa_periodos/listadoevaluacion_v2.html' if periodopoa.anio > 2023 else 'poa_periodos/listadoevaluacion.html'
                    return render(request, template, data)
                except Exception as ex:
                    pass

            elif action == 'editarperiodoevaluacion':
                try:
                    data['title'] = u'Editar Evaluación POA'
                    data['action'] = 'editarperiodoevaluacion'
                    data['id'] = (encrypt(request.GET['id']))
                    data['switchery'] = True
                    data['evaluacionperiodopoa'] = evaluacionperiodopoa = EvaluacionPeriodoPoa.objects.get(pk=int(encrypt(request.GET['id'])))
                    data['form'] = EvaluacionPoaForm(initial={'descripcion': evaluacionperiodopoa.descripcion,
                                                              'fechainicio': evaluacionperiodopoa.fechainicio,
                                                              'fechafin': evaluacionperiodopoa.fechafin,
                                                              # 'porcentajedesempeno': evaluacionperiodopoa.porcentajedesempeno,
                                                              # 'porcentajemeta': evaluacionperiodopoa.porcentajemeta,
                                                              'informeanual':evaluacionperiodopoa.informeanual})
                    template = get_template('poa_periodos/editarperiodoevaluacion.html')
                    return JsonResponse({"result": True, 'data': template.render(data)})

                    # return render(request, 'poa_periodos/editarperiodoevaluacion.html', data)
                except Exception as ex:
                    pass

            elif action == 'duplicar':
                try:
                    data['title'] = u'Traspaso POA'
                    data['periodo'] = PeriodoPoa.objects.get(pk=int(request.GET['id']))
                    return render(request, 'poa_periodos/traspaso.html', data)
                except Exception as ex:
                    pass

            elif action == 'addperiodoevaluacion':
                try:
                    data['title'] = u'Adicionar Evaluación Periodo POA'
                    data['action'] = 'addperiodoevaluacion'
                    data['switchery'] = True
                    data['idperiodo'] = int(request.GET['id'])
                    data['periodopoa'] = PeriodoPoa.objects.get(pk=int(request.GET['id']))
                    form = EvaluacionPoaForm()
                    data['form'] = form
                    template = get_template('poa_periodos/addevaluacionpoa.html')
                    return JsonResponse({"result": True, 'data': template.render(data)})

                    #return render(request, 'poa_periodos/addevaluacionpoa.html', data)
                except Exception as ex:
                    pass

            elif action == 'deleteperiodopoa':
                try:
                    data['title'] = u'Eliminar Evaluación POA'
                    data['evaluacionperiodopoa'] = EvaluacionPeriodoPoa.objects.get(pk=request.GET['id'])
                    return render(request, 'poa_periodos/deleteevaluacionpoa.html', data)
                except Exception as ex:
                    pass

            # PERMISOS
            elif action == 'permisosevidencia':
                try:
                    tipo = int(request.GET.get('tipo', 1))
                    if tipo == 1:
                        data['title'] = u'Responsables de registran evidencia'
                        request.session['viewactivopoa'] = ['permisos', 'registradores']
                    elif tipo == 2:
                        data['title'] = u'Responsables de dar seguimiento'
                        request.session['viewactivopoa'] = ['permisos', 'seguimiento']
                    elif tipo == 3:
                        data['title'] = u'Usuarios consultores'
                        request.session['viewactivopoa'] = ['permisos', 'consultores']
                    elif tipo == 4:
                        data['title'] = u'Responsables de validar y aprobar evidencia'
                        request.session['viewactivopoa'] = ['permisos', 'validadores']
                    search, filtro, url_vars = request.GET.get('s', ''),\
                                               Q(status=True, tipopermiso=tipo), \
                                               f'&action={action}&tipo={tipo}'
                    if search:
                        filtro = filtro_ususario(search, filtro)
                        filtro |= (Q(unidadorganica__nombre__unaccent__icontains=search) |
                                   Q(gestion__descripcion__unaccent__icontains=search) |
                                   Q(carrera__nombre__unaccent__icontains=search)) & Q(status=True, tipopermiso=tipo)
                        data['s'] = search
                        url_vars += f'&s={search}'
                    listado = UsuarioEvidencia.objects.filter(filtro).order_by('unidadorganica__departamento__nombre',
                                                                               'unidadorganica__gestion__descripcion',
                                                                               'unidadorganica__carrera__nombre').distinct()
                    paginator = MiPaginador(listado, 20)
                    page = int(request.GET.get('page', 1))
                    paginator.rangos_paginado(page)
                    data['paging'] = paging = paginator.get_page(page)
                    data['listado'] = paging.object_list
                    data['url_vars'] = url_vars
                    data['tipo'] = tipo
                    return render(request, 'poa_periodos/perms_seguimiento.html', data)
                except Exception as ex:
                    messages.error(request, f'Error: {ex}')

            elif action == 'addpermisoseguimiento':
                try:
                    data['tipo'] = tipo = encrypt_id(request.GET.get('idex', 1))
                    form = UsuarioPermisoForm()
                    if tipo == 4:
                        form.fields['unidadorganica'].required = False
                        form.fields['tipousuario'].choices = TIPOS_USUARIO[3:]
                    else:
                        form.fields['tipousuario'].choices = TIPOS_USUARIO[:3]
                    form.fields['gestion'].queryset = SeccionDepartamento.objects.none()
                    form.fields['carrera'].queryset = Carrera.objects.none()
                    form.fields['persona'].queryset = Persona.objects.none()
                    data['form'] = form
                    data['switchery']=True
                    data['idp'] = encrypt_id(request.GET['idex'])
                    template = get_template("poa_periodos/modal/formpermisos.html")
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    return JsonResponse({"result": False, 'message': str(ex)})

            elif action == 'editpermisoseguimiento':
                try:
                    data['tipo'] = tipo = encrypt_id(request.GET.get('idex', 1))
                    data['id'] = id = encrypt_id(request.GET['id'])
                    permiso = UsuarioEvidencia.objects.get(pk=id)
                    pers = permiso.get_persona()
                    form = UsuarioPermisoForm(initial=model_to_dict(permiso))
                    if tipo == 4:
                        form.fields['unidadorganica'].required = False
                        form.fields['tipousuario'].choices = TIPOS_USUARIO[3:]
                    else:
                        form.fields['tipousuario'].choices = TIPOS_USUARIO[:3]
                        form.fields['gestion'].queryset = SeccionDepartamento.objects.filter(departamento=permiso.unidadorganica, status=True)
                        form.fields['carrera'].queryset = carreras_departamento(permiso.unidadorganica, periodo)
                    form.fields['persona'].queryset = Persona.objects.filter(id=pers.id)
                    form.fields['persona'].initial = pers.id
                    data['switchery'] = True
                    data['form'] = form
                    template = get_template("poa_periodos/modal/formpermisos.html")
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    return JsonResponse({"result": False, 'mensaje': str(ex)})

            # REVISAR EVIDENCIAS
            elif action == 'gestionarevidencias':
                try:
                    data['title'] = u'Departamento revisión documentos.'
                    data['periodo'] = idp = encrypt_id(request.GET['idp'])
                    data['objetivos'] = ObjetivoEstrategico.objects.filter(periodopoa_id=idp, status=True)\
                                                                            .order_by('departamento_id', 'carrera_id', 'gestion_id')\
                                                                            .distinct('departamento_id', 'carrera_id', 'gestion_id')
                    data['periodopoa'] = periodopoa = PeriodoPoa.objects.get(pk=idp)
                    data['evaluacionperiodopoa'] = evaluacionperiodopoa = periodopoa.evaluacionperiodopoa_set.filter(status=True).order_by('id')
                    data['totalevaluacionperiodopoa'] = evaluacionperiodopoa.count()
                    data['tipomatrizarchivo'] = tipo_matriz(periodopoa)
                    data['new'] = True
                    request.session['viewactivopoa'] = ['general', 'periodos']
                    return render(request, "poa_periodos/gestionar_evidencia.html", data)
                except Exception as ex:
                    messages.error(request, f'Error: {ex}')

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
                    data['eObjetivo'] = eObjetivo = ObjetivoEstrategico.objects.get(pk=encrypt_id(request.GET['id']))
                    data['idp'] = eObjetivo.periodopoa.id
                    data['idd'] = eObjetivo.departamento.id
                    data['idg'] = eObjetivo.gestion.id if eObjetivo.gestion else 0
                    data['idc'] = eObjetivo.carrera.id if eObjetivo.carrera else 0
                    data['departamento'] = eObjetivo.departamento
                    data['periodopoa'] = eObjetivo.periodopoa
                    filtro = Q(status=True, acciondocumentodetalle__status=True,
                               indicadorpoa__objetivooperativo__objetivotactico__objetivoestrategico__periodopoa=eObjetivo.periodopoa,
                               indicadorpoa__objetivooperativo__objetivotactico__objetivoestrategico__periodopoa__status=True,
                               indicadorpoa__objetivooperativo__objetivotactico__objetivoestrategico__departamento=eObjetivo.departamento,
                               indicadorpoa__objetivooperativo__objetivotactico__objetivoestrategico__carrera=eObjetivo.carrera,
                               indicadorpoa__objetivooperativo__objetivotactico__objetivoestrategico__gestion=eObjetivo.gestion,
                               indicadorpoa__objetivooperativo__objetivotactico__objetivoestrategico__departamento__status=True)
                    orden = ('indicadorpoa__objetivooperativo__objetivotactico__objetivoestrategico__orden',
                             'indicadorpoa__objetivooperativo__objetivotactico__orden',
                             'indicadorpoa__objetivooperativo__orden', 'indicadorpoa__orden', 'orden')
                    data['documentos'] = documentos = AccionDocumento.objects.filter(filtro).order_by(*orden).distinct()
                    # cont = 0
                    records = AccionDocumentoDetalleRecord.objects.filter(acciondocumentodetalle__acciondocumento__in=documentos,
                                                                            status=True).exclude(estadorevision=10)
                    # for r in records:
                    #     validacion = r.get_historial_last()
                    #     if validacion.estadorevision in [2]:
                    #         cont += 1
                    # data['total_remitir'] = cont
                    data['ids_records'] = list(records.values_list('id', flat=True))
                    return render(request, "poa_periodos/revision_evidencias.html", data)
                except Exception as ex:
                    messages.error(request, 'Error al cargar la página: %s' % ex)

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
                        observacion = acciondocumentodetallerecord.observacion_validador
                        validacion = acciondocumentodetallerecord.get_validacion_last()
                        if validacion:
                            observacion = acciondocumentodetallerecord.get_observacion()
                            form_pre = PrevalidacionForm(initial={'estadorevision': validacion.estadorevision,
                                                                                   'numero': validacion.metaejecutada,
                                                                                   'observacion_validador': observacion,
                                                                                   'aplica_calculo': acciondocumentodetallerecord.aplica_calculo,
                                                                                   'notificar': validacion.accion == 3})
                        else:
                            form_pre = PrevalidacionForm(initial={'estadorevision': acciondocumentodetallerecord.estadorevision,
                                                                   'numero': acciondocumentodetallerecord.numero,
                                                                   'observacion_validador': observacion,
                                                                   'aplica_calculo': True})
                    data['formprevalidacion'] = form_pre
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

            elif action == 'remitir':
                try:
                    ids_records = eval(request.GET['idex'])
                    data['objetivo'] = objetivo = ObjetivoEstrategico.objects.get(id=encrypt_id(request.GET['id']))
                    records = AccionDocumentoDetalleRecord.objects.filter(id__in=ids_records)
                    ids_revisados = []
                    for r in records:
                        validacion = r.get_historial_last()
                        if validacion and validacion.estadorevision in [2]:
                            ids_revisados.append(r.id)
                    data['id']= objetivo.id
                    data['eRecords'] = AccionDocumentoDetalleRecord.objects.filter(id__in=ids_revisados)
                    template = get_template("poa_periodos/modal/formremitir.html")
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    return JsonResponse({"result": False, 'mensaje': f'Error al obtener los datos: {ex}'})


            # VALIDAR EVIDENCIA
            elif action == 'validarvidencias':
                try:
                    data['title'] = u"Aprobar Evidencias POA"
                    data['objetivo'] = objetivo = ObjetivoEstrategico.objects.get(pk=encrypt_id(request.GET['id']))
                    periodopoa = objetivo.periodopoa
                    search, url_vars, estado, evaluacion = request.GET.get('s', ''), \
                                               f'&action={action}&id={objetivo.id}', \
                                               request.GET.get('estado', ''), \
                                               request.GET.get('evaluacion', '')
                    estadosrevision = [10, 8, 6, 7]
                    filtro = Q(status=True, estadorevision__in=estadosrevision,
                               acciondocumentodetalle__acciondocumento__indicadorpoa__objetivooperativo__objetivotactico__objetivoestrategico__periodopoa=objetivo.periodopoa,
                               acciondocumentodetalle__acciondocumento__indicadorpoa__objetivooperativo__objetivotactico__objetivoestrategico__periodopoa__status=True,
                               acciondocumentodetalle__acciondocumento__indicadorpoa__objetivooperativo__objetivotactico__objetivoestrategico__departamento=objetivo.departamento,
                               acciondocumentodetalle__acciondocumento__indicadorpoa__objetivooperativo__objetivotactico__objetivoestrategico__carrera=objetivo.carrera,
                               acciondocumentodetalle__acciondocumento__indicadorpoa__objetivooperativo__objetivotactico__objetivoestrategico__gestion=objetivo.gestion,
                               acciondocumentodetalle__acciondocumento__indicadorpoa__objetivooperativo__objetivotactico__objetivoestrategico__departamento__status=True)

                    if estado:
                        data['estado'] = estado = int(estado)
                        filtro &= Q(estadorevision=estado)
                        url_vars += f'&estado={estado}'
                    if evaluacion:
                        data['evaluacion'] = evaluacion = int(evaluacion)
                        filtro &= Q(meta__evaluacionperiodo_id=evaluacion)
                        url_vars += f'&evaluacion={evaluacion}'
                    if search:
                        filtro &= Q(acciondocumentodetalle__acciondocumento__descripcion__icontains=search)
                        data['s'] = search
                        url_vars += f'&s={search}'

                    listado = AccionDocumentoDetalleRecord.objects.filter(filtro).order_by('-fecha_validacion')
                    paginator = MiPaginador(listado, 20)
                    page = int(request.GET.get('page', 1))
                    paginator.rangos_paginado(page)
                    data['paging'] = paging = paginator.get_page(page)
                    data['estados'] = choice_indice(ESTADO_REVISION_EVIDENCIA, tuple(estadosrevision))
                    data['listado'] = paging.object_list
                    data['evaluaciones'] = periodopoa.evaluaciones()
                    data['url_vars'] = url_vars
                    return render(request, 'poa_periodos/aprobarevidencias.html', data)
                except Exception as ex:
                    messages.error(request, f'Error: {ex}')

            elif action == 'validar':
                try:
                    data['eDocumentoRecord'] = record = AccionDocumentoDetalleRecord.objects.get(pk=encrypt_id(request.GET['id']))
                    data['rubrica'] = RubricaPoa.objects.filter(muestraformulario=True, status=True).order_by('orden')
                    form = ValidacionPOAForm(initial={'estadorevision': record.estadorevision,
                                                      'observacion_aprobacion': record.get_observacion()})
                    data['form'] = form
                    data['meta'] = record.meta
                    data['id'] = record.id
                    data['eAccionDetalle'] = record.acciondocumentodetalle
                    template = get_template("poa_periodos/modal/formvalidar.html")
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    return JsonResponse({"result": False, 'mensaje': f'Error: {ex}'})


            # MATRIZ DE EVALUACIÓN SEMESTRAL
            elif action == 'periodosevaluacion':
                try:
                    data['title'] = u'Matriz de evaluación semestral.'
                    data['eObjetivo'] = eObjetivo = ObjetivoEstrategico.objects.get(pk=encrypt_id(request.GET['id']))
                    data['departamento'] = eObjetivo.departamento
                    data['periodopoa'] = periodopoa = eObjetivo.periodopoa
                    filtro = Q(evaluacionperiodo__periodopoa=periodopoa,
                                departamento=eObjetivo.departamento,
                                gestion=eObjetivo.gestion,
                                carrera=eObjetivo.carrera,
                                status=True)
                    matrices = MatrizValoracionPoa.objects.filter(filtro)
                    if not matrices.exists():
                        for evaluacion in periodopoa.evaluacionperiodopoa_set.filter(status=True):
                            matrizpoa = MatrizValoracionPoa(evaluacionperiodo=evaluacion,
                                                            departamento=eObjetivo.departamento,
                                                            gestion=eObjetivo.gestion,
                                                            carrera=eObjetivo.carrera)
                            matrizpoa.save(request)
                        matrices = MatrizValoracionPoa.objects.filter(filtro)
                    data['listado'] = matrices.order_by('evaluacionperiodo_id')
                    request.session['viewactivopoa'] = ['general', 'periodos']
                    return render(request, "poa_periodos/periodoevaluacion.html", data)
                except Exception as ex:
                    messages.error(request, f'Error: {ex}')


            # SEGUIMIENTO POA
            elif action == 'seguimientopoa':
                try:
                    data['title'] = u'Seguimiento POA'
                    data['eObjetivo'] = eObjetivo = ObjetivoEstrategico.objects.get(pk=encrypt_id(request.GET['id']))
                    data['periodopoa'] = eObjetivo.periodopoa
                    filtro = Q(status=True, unidadorganica=eObjetivo.departamento, gestion=eObjetivo.gestion, carrera=eObjetivo.carrera)
                    request.session['viewactivopoa'] = ['general', 'periodos']

                    listado = SeguimientoPoa.objects.filter(filtro)
                    paginator = MiPaginador(listado, 10)
                    page = int(request.GET.get('page', 1))
                    paginator.rangos_paginado(page)
                    data['paging'] = paging = paginator.get_page(page)
                    data['listado'] = paging.object_list
                    # data['url_vars'] = url_vars
                    return render(request, "poa_periodos/seguimientopoa.html", data)
                except Exception as ex:
                    messages.error(request, f'Error: {ex}')

            elif action == 'addseguimientopoa':
                try:
                    data['id'] = id_objetivo = request.GET['id']
                    data['eObjetivo'] = eObjetivo = ObjetivoEstrategico.objects.get(pk=encrypt_id(id_objetivo))
                    data['departamento'] = departamento = eObjetivo.departamento
                    data['periodopoa'] = periodopoa = eObjetivo.periodopoa
                    data['switchery'] = True
                    form = SeguimientoPoaForm()
                    filtro = Q(status=True, tipopermiso=1, unidadorganica=departamento, gestion=eObjetivo.gestion, carrera=eObjetivo.carrera)
                    usuarios = UsuarioEvidencia.objects.filter(filtro)
                    ids_personas = [u.get_persona().id for u in usuarios]
                    form.fields['estado'].choices = ESTADO_SEGUIMIENTO_POA[1:3]
                    form.fields['persona'].queryset = registradores =  Persona.objects.filter(id__in=ids_personas)
                    if registradores:
                        form.fields['persona'].initial = registradores[0].id

                    data['form'] = form
                    template = get_template("poa_periodos/modal/formseguimientopoa.html")
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    messages.error(request, f'{ex}')

            elif action == 'editseguimientopoa':
                try:
                    data['id'] = id_objetivo = request.GET['id']
                    data['eObjetivo'] = eObjetivo = ObjetivoEstrategico.objects.get(pk=encrypt_id(id_objetivo))
                    data['idp'] = id = encrypt_id(request.GET['idex'])
                    seguimiento = SeguimientoPoa.objects.get(pk=id)
                    form = EditarSeguimientoPoaForm()
                    data['detalleseguimiento'] = DetalleSeguimientoPoa.objects.filter(solicitud=seguimiento,
                                                                                      status=True).order_by('id')

                    form.fields['detalle'].initial = seguimiento.detalle
                    form.fields['observacion'].initial = seguimiento.observaciondpi
                    data['form'] = form
                    template = get_template("poa_periodos/modal/formeditseguimientopoa.html")
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    messages.error(request, f'{ex}')

            elif action == 'finalizarseguimientopoa':
                try:
                    data['idp'] = id = encrypt_id(request.GET['idex'])
                    seguimiento = SeguimientoPoa.objects.get(pk=id)
                    data['detalleseguimiento'] = DetalleSeguimientoPoa.objects.filter(solicitud=seguimiento,
                                                                                      status=True).order_by('id')
                    form = EditarSeguimientoPoaForm()
                    data['form'] = form
                    data['finalizar'] = True
                    template = get_template("poa_periodos/modal/formeditseguimientopoa.html")
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    messages.error(request, f'{ex}')

            elif action == 'agendarseguimientopoa':
                try:
                    data['id'] = encrypt_id(request.GET['id'])
                    data['idp'] = id = encrypt_id(request.GET['idex'])
                    data['seguimiento'] = seguimiento = SeguimientoPoa.objects.get(pk=id)
                    form = AgendarSeguimientoPoaForm()
                    form.fields['detalle'].initial = seguimiento.detalle
                    if seguimiento.sugierefechayhora:
                        form.fields['fecha'].initial = seguimiento.fechasugerida.date()
                        form.fields['hora'].initial = seguimiento.horasugerida
                    data['form'] = form
                    data['switchery'] = True
                    template = get_template('poa_periodos/modal/formagendarseguimiento.html')
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    return JsonResponse({"result": False, 'mensaje': f'Error: {ex}'})

            elif action == 'reagendarseguimientopoa':
                try:
                    data['id'] = encrypt_id(request.GET['id'])
                    data['idp'] = id = encrypt_id(request.GET['idex'])
                    data['seguimiento'] = seguimiento = SeguimientoPoa.objects.get(pk=id)
                    form = AgendarSeguimientoPoaForm()
                    form.fields['detalle'].initial = seguimiento.detalle
                    form.fields['fecha'].initial = seguimiento.fechaagenda.date()
                    form.fields['hora'].initial = seguimiento.horaagenda
                    data['form'] = form
                    data['reagendar'] = True
                    template = get_template('poa_periodos/modal/formagendarseguimiento.html')
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    return JsonResponse({"result": False, 'mensaje': f'Error: {ex}'})

            elif action == 'detalleseguimientopoa':
                try:
                    data['seguimeinto'] = seguimeinto = SeguimientoPoa.objects.get(pk=encrypt_id(request.GET['id']))
                    data['detalles'] = seguimeinto.get_detalles()
                    template = get_template("poa_periodos/modal/detalleseguimientopoa.html")
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    return JsonResponse({"result": False, 'mensaje': f'Error: {ex}'})

            elif action == 'generarinforme':
                try:
                    data['matriz'] = matriz = MatrizValoracionPoa.objects.get(pk=encrypt_id(request.GET['id']))
                    data['listado'] = matriz.acciones_documentos_record()
                    data['id'] = matriz.id
                    data['eObjetivo'] = matriz.get_objetivoestrategico()
                    template = get_template("poa_periodos/modal/formgenerarinforme.html")
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    return JsonResponse({"result": False, 'mensaje': f'Error: {ex}'})

            elif action == 'firmarinforme':
                try:
                    data['id'] = encrypt_id(request.GET['id'])
                    template = get_template("formfirmaelectronicamasiva.html")
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    return JsonResponse({"result": False, 'mensaje': f'Error: {ex}'})

            # OPCIONES ANTIGUAS
            elif action == 'descargarevidenciadocumentalpdf':
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

            elif action == 'matrizvaloracionpoa':
                try:
                    data['title'] = u'Matriz valoración poa'
                    data['matriz'] = matriz = MatrizValoracionPoa.objects.get(id=encrypt_id(request.GET['id']))
                    data['evaluacionperiodo'] = evaluacionperiodo = matriz.evaluacionperiodo
                    data['rubricapoa'] = RubricaPoa.objects.filter(muestraformulario=True, status=True)
                    data['departamento'] = matriz.departamento
                    data['periodopoa'] = periodopoa = evaluacionperiodo.periodopoa
                    data['periodo'] = periodopoa.id
                    existematriz = 0
                    existearchivo = 0
                    if not matriz.detallematrizvaloracionpoa_set.filter(status=True):
                        filtro = Q(acciondocumento__indicadorpoa__objetivooperativo__objetivotactico__objetivoestrategico__departamento=matriz.departamento,
                                   acciondocumento__indicadorpoa__objetivooperativo__objetivotactico__objetivoestrategico__departamento__status=True,
                                   acciondocumento__indicadorpoa__objetivooperativo__objetivotactico__objetivoestrategico__gestion=matriz.gestion,
                                   acciondocumento__indicadorpoa__objetivooperativo__objetivotactico__objetivoestrategico__carrera=matriz.carrera,
                                   acciondocumento__indicadorpoa__objetivooperativo__objetivotactico__objetivoestrategico__periodopoa=periodopoa,
                                   acciondocumento__indicadorpoa__objetivooperativo__objetivotactico__objetivoestrategico__periodopoa__status=True,
                                   acciondocumento__status=True, status=True)
                        if evaluacionperiodo.informeanual:
                            filtro &= Q(acciondocumento__status=True, status=True,
                                        inicio__year=evaluacionperiodo.fechainicio.year) & \
                                       Q(Q(acciondocumentodetallerecord__isnull=True) |
                                        Q(acciondocumentodetallerecord__procesado=False) |
                                        Q(acciondocumentodetallerecord__procesado=True,
                                          acciondocumentodetallerecord__rubrica_aprobacion_id=3))
                        else:
                            filtro &= Q(inicio__gte=evaluacionperiodo.fechainicio, fin__lte=evaluacionperiodo.fechafin)
                        listindicadores = AccionDocumentoDetalle.objects.filter(filtro).order_by('acciondocumento__indicadorpoa__id')
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

            return HttpResponseRedirect(request.path)
        else:
            data['title'] = u'Periodos POA'
            search, url_vars = request.GET.get('s', ''),''
            search = None
            tipo = None
            if 's' in request.GET:
                search = request.GET['s']
            #if search:
                periodos = PeriodoPoa.objects.filter(descripcion__icontains=search, status=True).order_by('-id')
                url_vars += "&s={}".format(search)

            else:
                periodos = PeriodoPoa.objects.filter(status=True).order_by('-id')
            paging = MiPaginador(periodos, 25)
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
            data['fechaactual'] = datetime.now().date().year
            data['search'] = search if search else ""
            data['periodos'] = page.object_list
            data['url_vars'] = url_vars
            request.session['viewactivopoa'] = ['general', 'periodos']
            return render(request, "poa_periodos/view.html", data)

def es_validador(usuario):
    return responsables_validar().filter(userpermiso=usuario).exists()

def get_validador_tipo(usuario, tipousuario):
    return responsables_validar().filter(userpermiso=usuario, tipousuario=tipousuario).last()

def get_validador(usuario):
    return responsables_validar().filter(userpermiso=usuario).last()

def responsables_validar():
    return UsuarioEvidencia.objects.filter(status=True, activo=True, tipopermiso=4)

def filtro_ususario(search, filtro):
    q = search.upper().strip()
    s = q.split(" ")
    if len(s) == 1:
        filtro = filtro & ((Q(userpermiso__persona__nombres__icontains=q) |
                            Q(userpermiso__persona__apellido1__icontains=q) |
                            Q(userpermiso__persona__cedula__icontains=q) |
                            Q(userpermiso__persona__cedula__icontains=q) |
                            Q(userpermiso__persona__apellido2__icontains=q) |
                            Q(userpermiso__persona__cedula__contains=q)))
    elif len(s) == 2:
        filtro = filtro & ((Q(userpermiso__persona__apellido1__contains=s[0]) & Q(userpermiso__persona__apellido2__contains=s[1])) |
                           (Q(userpermiso__persona__nombres__icontains=s[0]) & Q(userpermiso__persona__nombres__icontains=s[1])) |
                           (Q(userpermiso__persona__nombres__icontains=s[0]) & Q(userpermiso__persona__apellido1__contains=s[1])))
    else:
        filtro = filtro & (
                (Q(userpermiso__persona__nombres__contains=s[0]) & Q(userpermiso__persona__apellido1__contains=s[1]) & Q(userpermiso__persona__apellido2__contains=s[2])) |
                (Q(userpermiso__persona__nombres__contains=s[0]) & Q(userpermiso__persona__nombres__contains=s[1]) & Q(userpermiso__persona__apellido1__contains=s[2])))
    return filtro

def notificar_responsables(request, objetivo):
    responsables = UsuarioEvidencia.objects.filter(status=True, activo=True, tipousuario__in=[4, 5], tipopermiso=4)
    for responsable in responsables:
        titulo = f"Se ha remitido evidencias POA para su aprobación"
        mensaje = f'Se ha remitido evidencias POA para su aprobación'
        notificacion(titulo, mensaje, responsable.get_persona(), None,
                     f'{request.path}?action=validarvidencias&id={encrypt(objetivo.pk)}',
                     responsable.pk, 1, 'sagest', UsuarioEvidencia, request)

def notificar_usuarios_registra(request, record, estado='Rechazado', obs=''):
    objetivo = record.get_objetivoestrategico()
    usuarios = UsuarioEvidencia.objects.filter(status=True,
                                               unidadorganica=objetivo.departamento,
                                               gestion=objetivo.gestion,
                                               carrera=objetivo.carrera,
                                               activo=True, tipopermiso=1)
    for u in usuarios:
        responsable = u.get_persona()
        titulo = f"Validación de evidencia POA ({estado})"
        mensaje = f'La Dirección de Planificación Institucional ha procedido con la revisión de la ' \
                  f'evidencia <b>{record.acciondocumentodetalle.acciondocumento}</b> correspondiente al ' \
                  f'indicador <b>{record.get_objetivooperativo()}</b> la cual se encuentra en ' \
                  f'estado {estado.lower()}, se sugiere realizar los ajustes y registrar la documentación en la opción acciones correctivas'
        url_redirect = f'/poa_subirevidencia'
        if record.puede_subirevidencia():
            url_redirect += f'?action=evidencias&id={encrypt(record.get_periodo().id)}'
        else:
            url_redirect += f'?action=revisadepartamentodos&idp={record.get_periodo().id}'
        notificacion(titulo, mensaje, responsable, None,
                     url_redirect, record.pk, 1, 'sga-sagest',
                     AccionDocumentoDetalleRecord, request)
        lista_email = responsable.lista_emails()
        # lista_email = ['jguachuns@unemi.edu.ec', ]
        datos_email = {'sistema': request.session['nombresistema'],
                       'tiposistema_': 2,
                       'fecha': datetime.now().date(),
                       'hora': datetime.now().time(),
                       'persona': responsable,
                       'mensaje': mensaje,
                       'observacion': obs,
                       'titulo_': titulo,
                       'url_redirect': url_redirect,
                       }
        template = "emails/notificacionpoa.html"
        send_html_mail(titulo, template, datos_email, lista_email, [], [], cuenta=CUENTAS_CORREOS[0][1])

def tipo_matriz(periodopoa):
    cont = 0
    if not periodopoa.matrizvaloracion:
        cont = 1
    if not periodopoa.matrizevaluacion:
        cont = 2
    return TIPO_MATRIZPOAARCHIVO[cont:]

def generar_informe_poa(records, matriz, request):
    data = {}
    data['hoy'] = hoy = datetime.now()
    numeroinforme = matriz.secuencual_informe()
    cumplimiento = calcular_cumplimiento(records)
    matriz_archivo = matriz.get_informe()
    if not matriz_archivo:
        matriz_archivo = MatrizArchivosPoa(matrizvaloracionpoa=matriz,
                                           numeroinforme=numeroinforme,
                                           fecha=hoy.date(),
                                           totaldesempeno=cumplimiento,
                                           tipomatrizarchivo=3)
    else:
        matriz_archivo.estado = 1
        matriz_archivo.fecha = hoy.date()
        matriz_archivo.totaldesempeno = cumplimiento
        if not matriz_archivo.numeroinforme:
            matriz_archivo.numeroinforme = numeroinforme
    matriz_archivo.save(request)
    usuarios_evidenciafirma = matriz.responsables_firmar_informe()
    # ELIMINAMOS REGISTROS ANTIGUOS DE FIRMA PARA CREAR UNOS NUEVOS POR QUE SE VA A GENERAR UN NUEVO INFORME
    MatrizEvaluacionFirmasPoa.objects.filter(matriz=matriz, matrizarchivo=matriz_archivo, status=True).update(status=False)
    if not usuarios_evidenciafirma:
        raise NameError('No se han definido los responsables de firma para el informe.')
    # CREAMOS LOS REGISTROS DE FIRMA CON LOS USUARIOS A FIRMAR
    for idx, ue in enumerate(usuarios_evidenciafirma):
        responsable = ue.get_persona()
        responable_firma = MatrizEvaluacionFirmasPoa(
            matriz=matriz,
            matrizarchivo=matriz_archivo,
            personafirma=responsable,
            tipofirma=ue.tipo_firma(),
            cargo=responsable.mi_cargo_administrativo(),
            cargo_text=str(ue.get_cargo()),
            orden=idx+1)
        responable_firma.save(request)

    data['records'] = records
    data['responsables_firma'] = matriz_archivo.responsables_firma()
    data['pagesize'] = 'A4 landscape'
    data['matriz_archivo'] = matriz_archivo
    data['matriz'] = matriz
    data['evaluacionperiodo'] = evaluacionperiodo = matriz.evaluacionperiodo
    name_file = f'DPI_EVPOA_{hoy.year}_{numeroinforme}.pdf'
    template = 'poa_periodos/informesemestralpoa_pdf.html'
    pdf_file, response = conviert_html_to_pdf_save_file_model(template, data, name_file)

    matriz_archivo.archivo = pdf_file
    matriz_archivo.save(request)
    historial = HistorialFirmaArchivoPoa(matrizarchivo=matriz_archivo, archivo=pdf_file, persona=request.session['persona'])
    historial.save(request)
    return matriz_archivo.archivo.url

def calcular_cumplimiento(records):
    records = records.exclude(Q(aplica_calculo=False) | Q(estadorevision=7))
    # Calcula la suma del campo 'cumplimiento' y el total de registros
    result = records.aggregate(total_cumplimiento=Sum('cumplimiento'), total_registros=Count('id'))

    # Extrae los valores de la suma total y el total de registros
    total_cumplimiento = result['total_cumplimiento'] or 0
    total_registros = result['total_registros']

    # Calcula la división
    if total_registros > 0:
        promedio = round(total_cumplimiento/total_registros, 2)
    else:
        promedio = 0.00
    return promedio

def orden_records():
    orden = 'acciondocumentodetalle__acciondocumento__indicadorpoa__objetivooperativo__objetivotactico__objetivoestrategico__orden', \
            'acciondocumentodetalle__acciondocumento__indicadorpoa__objetivooperativo__objetivotactico__orden', \
            'acciondocumentodetalle__acciondocumento__indicadorpoa__objetivooperativo__orden', \
            'acciondocumentodetalle__acciondocumento__indicadorpoa__orden', \
            'acciondocumentodetalle__acciondocumento__orden'
    return orden

def enviar_correo_notificacion_todos(request, eObjetivo, seguimiento, titulo, cuerpo, fechaanterior=None, horaanterior=None):
    try:
        list_mail = []
        filtro = Q(status=True, tipopermiso=1, unidadorganica=eObjetivo.departamento,
                   gestion=eObjetivo.gestion, carrera=eObjetivo.carrera)
        registradores = UsuarioEvidencia.objects.filter(filtro)
        # list_mail.append('elvis.alarcon.reyes@gmail.com')
        for r in registradores:
            per = r.get_persona()
            notificacion(titulo, cuerpo, per, None, f'/notificacion', per.pk, 2, 'sga-sagest', SeguimientoPoa, request)
            if per.emailinst:
                list_mail.append(per.emailinst)
        if seguimiento.personaseguimiento.emailinst:
            list_mail.append(seguimiento.personaseguimiento.emailinst)

        registrador = seguimiento.persona
        template = "emails/notificar_seguimiento_poa.html"
        datos_email = {'sistema': 'SAGEST',
                       'registrador': registrador,
                       'notificatodos': True,
                       'fechaanterior': fechaanterior,
                       'horaanterior': horaanterior,
                       'eSeguimiento': seguimiento}
        send_html_mail(titulo, template, datos_email, list_mail, [], [], CUENTAS_CORREOS[1][1])
    except Exception as ex:
        raise NameError(f'Error al enviar notificación: {ex}')


def enviar_correo_notificacion(request, seguimiento, titulo, cuerpo, fechaanterior=None, horaanterior=None):
    try:
        list_mail = []
        if seguimiento.persona.emailinst:
            # list_mail.append('elvis.alarcon.reyes@gmail.com')
            list_mail.append(seguimiento.persona.emailinst)
        notificacion(titulo, cuerpo, seguimiento.persona,
                     None, f'/notificacion', seguimiento.persona.pk, 2, 'sga-sagest',
                     SeguimientoPoa, request)
        if seguimiento.personaseguimiento.emailinst:
            list_mail.append(seguimiento.personaseguimiento.emailinst)
        registrador = seguimiento.persona
        template = "emails/notificar_seguimiento_poa.html"
        datos_email = {'sistema': 'SAGEST',
                       'registrador': registrador,
                       'notificatodos': False,
                       'fechaanterior': fechaanterior,
                       'horaanterior': horaanterior,
                       'eSeguimiento': seguimiento}
        send_html_mail(titulo, template, datos_email, list_mail, [], [], CUENTAS_CORREOS[1][1])
    except Exception as ex:
        raise NameError(f'Error al enviar notificación: {ex}')