# -*- coding: UTF-8 -*-
from datetime import datetime, timedelta
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db import transaction
from django.db.models import Q, F
from django.forms import model_to_dict
from django.http import HttpResponseRedirect, JsonResponse
from django.shortcuts import render
from django.template.context import Context
from django.template.loader import get_template

from decorators import secure_module
from sagest.forms import AccionDocumentoDetalleForm, AccionDocumentoDetalleNewForm, SeguimientoForm, SolicitudSeguimientoPoaForm
from sagest.funciones import encrypt_id
from sagest.models import AccionDocumentoDetalle, UsuarioEvidencia, AccionDocumentoDetalleRecord, PoaArchivo, \
    AccionDocumento, PeriodoPoa, SeguimientoPoa, HistorialValidacionEvidencia, Departamento, InformeGenerado, \
ObjetivoEstrategico
from sga.commonviews import adduserdata
from sga.funciones import generar_nombre, log, MiPaginador
from sga.models import MESES_CHOICES, MONTH_CHOICES


@login_required(redirect_field_name='ret', login_url='/loginsagest')
@transaction.atomic()
@secure_module
def view(request):
    data = {}
    adduserdata(request, data)
    persona = request.session['persona']
    usuario = request.user
    hoy = datetime.now()
    data['ususarioevidencia'] = usuarioevidencia = UsuarioEvidencia.objects.filter(status=True, userpermiso=usuario, tipopermiso=1).first()
    if not usuarioevidencia:
        return HttpResponseRedirect("/?info=No tiene permisos asignado para este modulo.")
    if request.method == 'POST':
        action = request.POST['action']

        if action == 'add_evidencia':
            try:
                id, idp = encrypt_id(request.POST.get('id', 0)), encrypt_id(request.POST['idp'])
                eAccionDetalle = AccionDocumentoDetalle.objects.get(pk=idp)
                eAccionDetalleRecord  = AccionDocumentoDetalleRecord.objects.get(pk=id) if id > 0 else None
                f = AccionDocumentoDetalleNewForm(request.POST, request.FILES, instancia=eAccionDetalleRecord)
                meta = eAccionDetalle.meta_documento()
                estado = 1
                if not eAccionDetalleRecord or not eAccionDetalleRecord.estadorevision == 3:
                    f.fields['observacion_envia'].required = False
                if not f.is_valid():
                    form_error = [{k: v[0]} for k, v in f.errors.items()]
                    return JsonResponse({'result': True, "form": form_error, "mensaje": "Error en el formulario"})
                if eAccionDetalleRecord:
                    if not eAccionDetalleRecord.estadorevision in eAccionDetalleRecord.estados_subirevidencia():
                        raise NameError(f'No puede subir evidencia por que se encuentra {eAccionDetalleRecord.get_estadorevision_display().lower()}')
                    estado = 5 if not eAccionDetalleRecord.estadorevision == 7 else 7
                    meta = eAccionDetalleRecord.meta if eAccionDetalleRecord.meta else meta
                    if eAccionDetalleRecord.puede_ponerobservacion():
                        eAccionDetalleRecord.observacion_envia = f.cleaned_data['observacion_envia']
                    eAccionDetalleRecord.logros = f.cleaned_data['logros']
                    eAccionDetalleRecord.nudos = f.cleaned_data['nudos']
                    eAccionDetalleRecord.archivo = f.cleaned_data['archivo']
                    eAccionDetalleRecord.estadorevision = estado
                    eAccionDetalleRecord.meta = meta
                    eAccionDetalleRecord.numero = f.cleaned_data['numero']
                    eAccionDetalleRecord.usuario_envia = usuario
                    eAccionDetalleRecord.estado_accion_aprobacion = 7
                    eAccionDetalleRecord.rubrica_aprobacion_id = 7
                    eAccionDetalleRecord.estado_accion_revisa = 7
                    eAccionDetalleRecord.rubrica_revisa_id = 7
                    eAccionDetalleRecord.fecha_envia = hoy
                    eAccionDetalleRecord.save(request)
                    log(u'Edito evidencia poa: %s' % eAccionDetalleRecord, request, "edit")
                else:
                    eAccionDetalleRecord = AccionDocumentoDetalleRecord(acciondocumentodetalle_id=idp,
                                                                        logros=f.cleaned_data['logros'],
                                                                        nudos=f.cleaned_data['nudos'],
                                                                        meta=meta,
                                                                        numero=f.cleaned_data['numero'],
                                                                        # observacion_envia=f.cleaned_data['observacion_envia'],
                                                                        archivo=f.cleaned_data['archivo'],
                                                                        usuario_envia=usuario,
                                                                        estado_accion_aprobacion=7,
                                                                        rubrica_aprobacion_id=7,
                                                                        estado_accion_revisa=7,
                                                                        rubrica_revisa_id=7,
                                                                        fecha_envia=hoy)
                    eAccionDetalleRecord.save(request)
                    log(u'Añado evidencia poa: %s' % eAccionDetalleRecord, request, "add")
                eAccionDetalle.estado_accion = 7
                eAccionDetalle.estado_rubrica_id = 7
                eAccionDetalle.save(request)
                observacion = f.cleaned_data['observacion_envia']
                if not observacion and estado == 1:
                    observacion = 'Primer registro de carga de evidencia'
                historial = HistorialValidacionEvidencia(evidencia=eAccionDetalleRecord,
                                                         metaejecutada=f.cleaned_data['numero'],
                                                         persona=persona,
                                                         estadorevision=estado,
                                                         observacion=observacion,
                                                         archivo=eAccionDetalleRecord.archivo)
                historial.save(request)
                return JsonResponse({"result": False})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": True, "mensaje": f"Error: {ex}"})

        elif action == 'addseguimiento':
            try:
                form = SeguimientoForm(request.POST)
                if not form.is_valid():
                    form_error = [{k: v[0]} for k, v in form.errors.items()]
                    return JsonResponse({'result': False, "form": form_error, "mensaje": "Error en el formulario"})
                seguimiento = SeguimientoPoa(detalle=form.cleaned_data['detalle'],
                                             unidadorganica=usuarioevidencia.unidadorganica,
                                             gestion=usuarioevidencia.gestion,
                                             carrera=usuarioevidencia.carrera,
                                             persona=persona)
                seguimiento.save(request)
                for u in usuarioevidencia.usuarios_seguimiento():
                    seguimiento.responsables.add(u.get_persona())
                seguimiento.save(request)
                log(u'Añado seguimiento poa: %s' % seguimiento, request, "add")
                return JsonResponse({"result": False})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": True, "mensaje": f"Error: {ex}"})

        elif action == 'editseguimiento':
            try:
                id = encrypt_id(request.POST['id'])
                seguimiento = SeguimientoPoa.objects.get(pk=id)
                form = SeguimientoForm(request.POST, instancia=seguimiento)
                if not form.is_valid():
                    form_error = [{k: v[0]} for k, v in form.errors.items()]
                    return JsonResponse({'result': False, "form": form_error, "mensaje": "Error en el formulario"})

                seguimiento.detalle = form.cleaned_data['detalle']
                seguimiento.save(request)
                log(u'Edito seguimiento poa: %s' % seguimiento, request, "edit")
                return JsonResponse({"result": False})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": True, "mensaje": f"Error: {ex}"})

        elif action == 'delseguimiento':
            try:
                id = encrypt_id(request.POST['id'])
                seguimiento = SeguimientoPoa.objects.get(pk=id)
                seguimiento.status=False
                seguimiento.save(request)
                log(u'Elimino seguimiento poa: %s' % seguimiento, request, "del")
                return JsonResponse({"error": False})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"erro": True, "mensaje": f"Error: {ex}"})

        elif action == 'solicitarseguimiento':
            try:
                f = SolicitudSeguimientoPoaForm(request.POST)
                if f.is_valid():
                    seguimiento = SeguimientoPoa(detalle=f.cleaned_data['detalle'].strip().upper(),
                                                 unidadorganica=usuarioevidencia.unidadorganica,
                                                 carrera=usuarioevidencia.carrera,
                                                 gestion=usuarioevidencia.gestion,
                                                 persona=persona)
                    if 'sugeirfecha' in request.POST:
                        seguimiento.fechasugerida = f.cleaned_data['fechasugerida']
                        seguimiento.horasugerida = f.cleaned_data['horasugerida']
                        seguimiento.sugierefechayhora = True
                    seguimiento.save(request)
                    # for u in usuarioevidencia.usuarios_seguimiento():
                    #     seguimiento.responsables.add(u.get_persona())
                    # seguimiento.save(request)
                    log(u'Añado solicitud seguimiento poa: %s' % seguimiento, request, "add")
                    return JsonResponse({"result": False})
                return JsonResponse({"result": True, "mensaje": "Error en el formulario"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": True, "mensaje": f"Error: {ex}"})

        elif action == 'delsolicitudseguimiento':
            try:
                id = encrypt_id(request.POST['id'])
                seguimiento = SeguimientoPoa.objects.get(pk=id)
                seguimiento.status=False
                seguimiento.save(request)
                log(u'Elimino solicitud seguimiento poa: %s' % seguimiento, request, "del")
                return JsonResponse({'result': 'ok', 'mensaje': 'Registro eliminado correctamente.'})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({'result': 'bad', 'mensaje': f'Error al eliminar el registro: {ex}'})

        return JsonResponse({"result": "bad", "mensaje": "Solicitud Incorrecta."})
    else:
        if 'action' in request.GET:
            data['action'] = action = request.GET['action']
            #Subir evidencia
            if action == 'evidencias':
                try:
                    data['title'] = u'Subir Evidencia'
                    data['periodopoaactivo'] = periodopoaactivo = PeriodoPoa.objects.get(id=encrypt_id(request.GET['id']))
                    if periodopoaactivo:
                        hoymaxmesanterior = datetime.now().date() - timedelta(days=periodopoaactivo.diassubir)
                        data['mes'] = MESES_CHOICES[hoy.month - 1][1]
                        orden = 'acciondocumento__indicadorpoa__objetivooperativo__objetivotactico__objetivoestrategico__orden', \
                                'acciondocumento__indicadorpoa__objetivooperativo__objetivotactico__orden', \
                                'acciondocumento__indicadorpoa__objetivooperativo__orden', \
                                'acciondocumento__indicadorpoa__orden', 'acciondocumento__orden'
                        filtro = Q(acciondocumento__status=True, mostrar=True, status=True,
                                   acciondocumento__indicadorpoa__objetivooperativo__objetivotactico__objetivoestrategico__periodopoa__ingresar=True,
                                   acciondocumento__indicadorpoa__objetivooperativo__objetivotactico__objetivoestrategico__periodopoa=periodopoaactivo,
                                   acciondocumento__indicadorpoa__objetivooperativo__objetivotactico__objetivoestrategico__departamento=usuarioevidencia.unidadorganica)

                        if usuarioevidencia.carrera:
                            filtroante = filtro = filtro & Q(acciondocumento__indicadorpoa__objetivooperativo__objetivotactico__objetivoestrategico__carrera=usuarioevidencia.carrera)
                            filtro = filtro & Q(inicio__lte=hoy, fin__gte=hoy, )
                            filtroante = filtroante & Q(inicio__lte=hoymaxmesanterior, fin__gte=hoymaxmesanterior)
                        elif usuarioevidencia.gestion:
                            filtroante = filtro = filtro & Q(acciondocumento__indicadorpoa__objetivooperativo__objetivotactico__objetivoestrategico__gestion=usuarioevidencia.gestion)
                            filtro = filtro & Q(inicio__lte=hoy, fin__gte=hoy)
                            filtroante = filtroante & Q(inicio__lte=hoymaxmesanterior, fin__gte=hoymaxmesanterior)
                        else:
                            filtroante = filtro = filtro & Q(acciondocumento__indicadorpoa__objetivooperativo__objetivotactico__objetivoestrategico__carrera__isnull=True,
                                                             acciondocumento__indicadorpoa__objetivooperativo__objetivotactico__objetivoestrategico__gestion__isnull=True)
                            filtro = filtro & Q(inicio__lte=hoy, fin__gte=hoy)
                            filtroante = filtroante & Q(inicio__lte=hoymaxmesanterior, fin__gte=hoymaxmesanterior)

                        acciondocumento = AccionDocumentoDetalle.objects.filter(filtro).order_by(*orden)
                        acciondocumentoante = AccionDocumentoDetalle.objects.filter(filtroante).order_by(*orden)

                        if acciondocumento and acciondocumentoante:
                            acciondocumento = (acciondocumento | acciondocumentoante).order_by(*orden).distinct()
                        elif acciondocumentoante and not acciondocumento:
                            acciondocumento = acciondocumentoante.order_by(*orden).distinct()
                        if acciondocumento:
                            periodopoa = acciondocumento.first().acciondocumento.indicadorpoa.objetivooperativo.objetivotactico.objetivoestrategico.periodopoa
                            data['p'] = PoaArchivo.objects.filter(unidadorganica=usuarioevidencia.unidadorganica, status=True, periodopoa=periodopoa).order_by('-fecha').first()
                        data['acciondocumento'] = acciondocumento
                    return render(request, "poa_subirevidencia/view.html", data)
                except Exception as ex:
                    return HttpResponseRedirect(f'/?info=Algo salio mal: {ex}')

            if action == 'ver_observacion':
                try:
                    data = {}
                    acciondocumento = AccionDocumento.objects.get(pk=int(request.GET['iddocumento']))
                    return JsonResponse({"result": "ok", 'data': acciondocumento.observacion})
                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

            elif action == 'ver_medio':
                try:
                    data = {}
                    acciondocumento = AccionDocumento.objects.get(pk=int(request.GET['iddocumento']))
                    return JsonResponse({"result": "ok", 'data': acciondocumento.medioverificacion.nombre})
                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

            elif action == 'add_evidencia':
                try:
                    acciondocumentodetalle = AccionDocumentoDetalle.objects.get(pk=int(request.GET['id']))
                    record = int(request.GET['idex']) if request.GET['idex'] else 0
                    metas, meta = acciondocumentodetalle.metas_documentos(), None
                    if record == 0:
                         form= AccionDocumentoDetalleNewForm()
                    else:
                        data['eRecord'] = acciondocumentodetallerecord = AccionDocumentoDetalleRecord.objects.get(pk=record)
                        meta = acciondocumentodetallerecord.meta
                        form = AccionDocumentoDetalleNewForm(initial=model_to_dict(acciondocumentodetallerecord), instancia=acciondocumentodetallerecord)
                    form.fields['meta'].queryset = metas
                    data['meta'] = metas.first() if not meta else meta
                    data['permite_modificar'] = True
                    data['id'] = record
                    data['eAccionDetalle'] = acciondocumentodetalle
                    data['idp'] = acciondocumentodetalle.id
                    data['form'] = form
                    data['estadosexcluir'] = [3, 5]
                    template = get_template("poa_subirevidencia/modal/formsubirevidencia.html")
                    json_content = template.render(data)
                    return JsonResponse({"result": True, 'data': json_content})
                except Exception as ex:
                    return JsonResponse({"result": False, "mensaje": f"Error {ex}"})

            elif action == 'historialvalidacion':
                try:
                    data['id'] = id = encrypt_id(request.GET['id'])
                    data['eDocumentoRecord'] = AccionDocumentoDetalleRecord.objects.get(pk=id)
                    template = get_template("poa_subirevidencia/modal/historialvalidacion.html")
                    json_content = template.render(data)
                    return JsonResponse({"result": True, 'data': json_content})
                except Exception as ex:
                    return JsonResponse({"result": False, "mensaje": f"Error {ex}"})

            #Acciones correctivas
            if action == 'revisadepartamento':
                try:
                    data['title'] = u'POA Ingresar y consultar evidencias.'
                    usuario=usuarioevidencia
                    data['departamento'] = departamento = Departamento.objects.get(pk=usuario.unidadorganica_id)
                    data['meses'] = MONTH_CHOICES
                    data['idp'] = int(request.GET['idp'])
                    fechamax = None
                    if int(request.GET['idp']) < 4:
                        data['idd'] = departamento.id
                        informegenerado = InformeGenerado.objects.filter(departamento=departamento, status=True).order_by("-id")
                        fechamax = informegenerado[0].fechamax if informegenerado.exists() else datetime.now().date() - timedelta(days=1)
                        if informegenerado.exists():
                            if informegenerado[0].tipo == 2 and not informegenerado[0].procesado:
                                fechamax = datetime.now().date() - timedelta(days=1)
                        data['fechamax'] = fechamax
                        data['habilitado'] = True if datetime.now().date() <= fechamax else False
                        data['mes_actual'] = 12 if PeriodoPoa.objects.get(pk=int(request.GET['idp'])).anio < datetime.now().year else datetime.now().month
                        data['documento'] = AccionDocumento.objects.filter(status=True, acciondocumentodetalle__status=True, acciondocumentodetalle__mostrar=True, indicadorpoa__objetivooperativo__objetivotactico__objetivoestrategico__departamento_id=departamento.id, indicadorpoa__objetivooperativo__objetivotactico__objetivoestrategico__periodopoa_id=int(request.GET['idp'])).order_by('indicadorpoa__objetivooperativo', 'indicadorpoa').distinct()
                        d = PoaArchivo.objects.filter(unidadorganica=departamento, status=True, periodopoa_id=int(request.GET['idp'])).order_by('-fecha')
                        if d:
                            data['p'] = d[0]
                        return render(request, "poa_subirevidatrasada/poadepartamento.html", data)
                    else:
                        if usuario.carrera_id:
                            data['idd'] = departamento.id
                            informegenerado = InformeGenerado.objects.filter(departamento=departamento, status=True, periodopoa_id=data['idp']).order_by("-id")
                            if departamento.id in[7, 13]:
                                fechamax = informegenerado[0].fechamax if informegenerado.exists() else datetime.now().date() # - timedelta(days=1)
                            else:
                                # fechamax = informegenerado[0].fechamax if informegenerado.exists() else datetime.now().date() - timedelta(days=1)
                                informefechamax = InformeGenerado.objects.filter(departamento=departamento, status=True,periodopoa_id=data['idp'],carrera_id=usuario.carrera_id).order_by("-fechamax")
                                fechamax = informefechamax[0].fechamax
                            # if informegenerado.exists():
                            #     if informegenerado[0].tipo == 2 and not informegenerado[0].procesado:
                            #         fechamax = datetime.now().date() - timedelta(days=1)
                            data['fechamax'] = fechamax
                            data['habilitado'] = True if datetime.now().date() <= fechamax else False
                            data['mes_actual'] = 12 if PeriodoPoa.objects.get(
                                pk=int(request.GET['idp'])).anio < datetime.now().year else datetime.now().month
                            data['documento'] = AccionDocumento.objects.filter(status=True,
                                                                               acciondocumentodetalle__status=True,
                                                                               acciondocumentodetalle__mostrar=True,
                                                                               indicadorpoa__objetivooperativo__objetivotactico__objetivoestrategico__departamento_id=departamento.id,
                                                                               indicadorpoa__objetivooperativo__objetivotactico__objetivoestrategico__carrera_id=usuario.carrera_id,
                                                                               indicadorpoa__objetivooperativo__objetivotactico__objetivoestrategico__periodopoa_id=int(
                                                                                   request.GET['idp'])).order_by(
                                'indicadorpoa__objetivooperativo', 'indicadorpoa').distinct()
                            d = PoaArchivo.objects.filter(unidadorganica=departamento, status=True,
                                                          periodopoa_id=int(request.GET['idp'])).order_by('-fecha')
                            if d:
                                data['p'] = d[0]
                        else:
                            data['idd'] = departamento.id
                            informegenerado = InformeGenerado.objects.filter(departamento=departamento, status=True, periodopoa_id=data['idp']).order_by("-id")
                            if departamento.id in[7, 13]:
                                fechamax = informegenerado[0].fechamax if informegenerado.exists() else datetime.now().date() # - timedelta(days=1)
                            else:
                                informefechamax = InformeGenerado.objects.filter(departamento=departamento, status=True,periodopoa_id=data['idp'],carrera__isnull=True).order_by("-fechamax")
                                if informefechamax:
                                    fechamax = informefechamax[0].fechamax
                                # fechamax = informegenerado[0].fechamax if informegenerado.exists() else datetime.now().date() - timedelta(days=1)
                            # if informegenerado.exists():
                            #     if informegenerado[0].tipo == 2 and not informegenerado[0].procesado:
                            #         fechamax = datetime.now().date() - timedelta(days=1)
                            if fechamax:
                                data['fechamax'] = fechamax
                                data['habilitado'] = True if datetime.now().date() <= fechamax else False
                            data['mes_actual'] = 12 if PeriodoPoa.objects.get(pk=int(request.GET['idp'])).anio < datetime.now().year else datetime.now().month
                            data['documento'] = AccionDocumento.objects.filter(status=True,
                                                                               acciondocumentodetalle__status=True,
                                                                               acciondocumentodetalle__mostrar=True,
                                                                               indicadorpoa__objetivooperativo__objetivotactico__objetivoestrategico__departamento_id=departamento.id,
                                                                               indicadorpoa__objetivooperativo__objetivotactico__objetivoestrategico__carrera__isnull=True,
                                                                               indicadorpoa__objetivooperativo__objetivotactico__objetivoestrategico__periodopoa_id=int(
                                                                                   request.GET['idp'])).order_by(
                                'indicadorpoa__objetivooperativo', 'indicadorpoa').distinct()
                            d = PoaArchivo.objects.filter(unidadorganica=departamento, status=True,
                                                          periodopoa_id=int(request.GET['idp'])).order_by('-fecha')
                            if d:
                                data['p'] = d[0]

                        return render(request, "poa_subirevidatrasada/poadepartamentocarrera.html", data)
                except Exception as ex:
                    pass

            if action == 'revisadepartamentodos':
                try:
                    data['title'] = u'POA Ingresar y consultar evidencias.'
                    data['departamento'] = departamento = usuarioevidencia.unidadorganica
                    data['meses'] = MONTH_CHOICES
                    data['idp'] = int(request.GET['idp'])
                    data['periodopoa'] = periodopoa = PeriodoPoa.objects.get(pk=data['idp'])
                    data['informegenerado'] = periodopoa.informe_generado(usuarioevidencia)
                    data['habilitado'] = periodopoa.puede_subirevidenciaatrasada(usuarioevidencia)
                    data['mes_actual'] = 12 if periodopoa.anio < datetime.now().year else datetime.now().month
                    orden = 'indicadorpoa__objetivooperativo__objetivotactico__objetivoestrategico__orden',\
                            'indicadorpoa__objetivooperativo__objetivotactico__orden',\
                            'indicadorpoa__objetivooperativo__orden', 'indicadorpoa__orden',\
                            'orden'
                    filtro = Q(status=True, acciondocumentodetalle__status=True, acciondocumentodetalle__mostrar=True,
                               indicadorpoa__objetivooperativo__objetivotactico__objetivoestrategico__periodopoa=periodopoa,
                               indicadorpoa__objetivooperativo__objetivotactico__objetivoestrategico__periodopoa__ingresar=True,
                               indicadorpoa__objetivooperativo__objetivotactico__objetivoestrategico__departamento=usuarioevidencia.unidadorganica,
                               indicadorpoa__objetivooperativo__objetivotactico__objetivoestrategico__carrera=usuarioevidencia.carrera,
                               indicadorpoa__objetivooperativo__objetivotactico__objetivoestrategico__gestion=usuarioevidencia.gestion)
                    data['documento'] = AccionDocumento.objects.filter(filtro).order_by(*orden).distinct()
                    d = PoaArchivo.objects.filter(unidadorganica=departamento, status=True, periodopoa=periodopoa).order_by('-fecha')
                    if d:
                        data['p'] = d[0]
                    return render(request, "poa_subirevidencia/accionescorrectivas.html", data)
                except Exception as ex:
                    messages.error(request, f'Error:{ex}')

            elif action == 'verificarseguimiento':
                try:
                    data['title'] = u'Seguimiento POA'
                    search, url_vars = request.GET.get('s', ''), f''
                    filtro = Q(status=True, persona=persona,
                               unidadorganica=usuarioevidencia.unidadorganica,
                               carrera=usuarioevidencia.carrera,
                               gestion=usuarioevidencia.gestion)
                    if search:
                        data['s'] = search
                        filtro = filtro & Q(descripcion__icontains=search)
                        url_vars += f'&s={search}'

                    data['periodopoa'] = periodopoa = PeriodoPoa.objects.get(pk=encrypt_id(request.GET['id']))
                    data['eObjetivo'] = ObjetivoEstrategico.objects.filter(status=True, periodopoa=periodopoa,
                                                                   departamento=usuarioevidencia.unidadorganica,
                                                                   carrera=usuarioevidencia.carrera,
                                                                   gestion=usuarioevidencia.gestion).first()
                    listado = SeguimientoPoa.objects.filter(filtro)
                    paginator = MiPaginador(listado, 15)
                    page = int(request.GET.get('page', 1))
                    paginator.rangos_paginado(page)
                    data['paging'] = paging = paginator.get_page(page)
                    data['listado'] = paging.object_list
                    data['url_vars'] = url_vars
                    return render(request, "poa_subirevidencia/verificarseguimiento.html", data)
                except Exception as ex:
                    return HttpResponseRedirect(f'/?info=Algo salio mal: {ex}')

            elif action == 'solicitarseguimiento':
                try:
                    data['title'] = u'Solicitar seguimiento POA'
                    form = SolicitudSeguimientoPoaForm()
                    data['form'] = form
                    data['switchery'] = True
                    template = get_template("poa_subirevidencia/modal/formsolicitudseguimiento.html")
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    return HttpResponseRedirect(f'/?info=Algo salio mal: {ex}')

            elif action == 'detalleseguimientopoa':
                try:
                    data['seguimeinto'] = seguimeinto = SeguimientoPoa.objects.get(pk=encrypt_id(request.GET['id']))
                    data['detalles'] = seguimeinto.get_detalles()
                    template = get_template("poa_periodos/modal/detalleseguimientopoa.html")
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    return JsonResponse({"result": False, 'mensaje': f'Error: {ex}'})

            elif action == 'sin_evidencia' or action == 'con_evidencia':
                try:
                    data = {}
                    acciondocumentodetalle = AccionDocumentoDetalle.objects.get(pk=int(request.GET['iddocdet']))
                    data['documentodetallerecord'] = {}
                    if int(request.GET['record']) == 0:
                        data['form'] = AccionDocumentoDetalleForm
                    else:
                        acciondocumentodetallerecord = AccionDocumentoDetalleRecord.objects.get(pk=int(request.GET['record']))
                        data['form'] = AccionDocumentoDetalleForm(initial={'observacion_envia': acciondocumentodetallerecord.observacion_envia})
                        data['documentodetallerecord'] = acciondocumentodetallerecord
                    data['permite_modificar'] = True
                    data['record'] = int(request.GET['record'])
                    data['modadd'] = True if int(request.GET['listo']) == 0 else False
                    data['records'] = acciondocumentodetalle.acciondocumentodetallerecord_set.all().order_by("-id")
                    data['acciondocumentodetalle'] = acciondocumentodetalle.__str__()
                    data['id'] = acciondocumentodetalle.id
                    data['idp'] = int(request.GET['idp'])
                    template = get_template("poa_subirevidatrasada/add_evidencia.html")
                    json_content = template.render(data)
                    return JsonResponse({"result": "ok", 'data': json_content})
                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

            elif action == 'sin_evidenciados' or action == 'con_evidenciados':
                try:
                    data = {}
                    idp, iddocdet, record, bloqueo, idd = int(request.GET.get('idex[id]', 0) or 0), \
                                                        int(request.GET.get('idex[iddocdet]', 0) or 0),\
                                                        int(request.GET.get('idex[record]', 0) or 0),\
                                                        int(request.GET.get('idex[listo]', 0) or 0),\
                                                        int(request.GET.get('idex[idd]', 0) or 0),
                    acciondocumentodetalle = AccionDocumentoDetalle.objects.get(pk=iddocdet)
                    metas, meta = acciondocumentodetalle.metas_documentos(), None
                    if not record:
                        form = AccionDocumentoDetalleNewForm()
                    else:
                        data['eRecord'] = acciondocumentodetallerecord = AccionDocumentoDetalleRecord.objects.get(pk=record)
                        meta = acciondocumentodetallerecord.meta
                        form = AccionDocumentoDetalleNewForm(initial=model_to_dict(acciondocumentodetallerecord), instancia=acciondocumentodetallerecord)
                    data['permite_modificar'] = True
                    data['form'] = form
                    form.fields['meta'].queryset = metas
                    data['meta'] = metas.first() if not meta else meta
                    data['id'] = record
                    data['modadd'] = bloqueo == 0
                    data['records'] = acciondocumentodetalle.acciondocumentodetallerecord_set.all().order_by("-id")
                    data['eAccionDetalle'] = acciondocumentodetalle
                    data['idp'] = acciondocumentodetalle.id
                    template = get_template("poa_subirevidencia/modal/formsubirevidenciaatrasada.html")
                    json_content = template.render(data)
                    return JsonResponse({"result": True, 'data': json_content})
                except Exception as ex:
                    return JsonResponse({"result": False, "mensaje": f"Error al obtener los datos: {ex}."})

            # Seguimientos
            elif action == 'seguimientos':
                try:
                    data['title'] = u'Solicitudes de seguimientos'
                    search, filtro, url_vars = request.GET.get('s', ''), \
                                               Q(status=True, unidadorganica=usuarioevidencia.unidadorganica), \
                                               f'&action={action}'
                    if search:
                        # filtro = filtro_ususario(search, filtro)
                        data['s'] = search
                        url_vars += f'&s={search}'
                    if usuarioevidencia.carrera:
                        filtro &= Q(carrera=usuarioevidencia.carrera)
                    elif usuarioevidencia.gestion:
                        filtro &= Q(gestion=usuarioevidencia.gestion)
                    else:
                        filtro &= Q(carrera__isnull=True, gestion__isnull=True)
                    listado = SeguimientoPoa.objects.filter(filtro)
                    paginator = MiPaginador(listado, 20)
                    page = int(request.GET.get('page', 1))
                    paginator.rangos_paginado(page)
                    data['paging'] = paging = paginator.get_page(page)
                    data['listado'] = paging.object_list
                    data['url_vars'] = url_vars
                    return render(request, 'poa_subirevidencia/seguimientos.html', data)
                except Exception as ex:
                    messages.error(request, f'Error: {ex}')

            elif action == 'addseguimiento':
                try:
                    form = SeguimientoForm()
                    data['form'] = form
                    template = get_template("ajaxformmodal.html")
                    json_content = template.render(data)
                    return JsonResponse({"result": True, 'data': json_content})
                except Exception as ex:
                    return JsonResponse({"result": False, "mensaje": f"Error {ex}"})

            elif action == 'editseguimiento':
                try:
                    data['id'] = id = encrypt_id(request.GET['id'])
                    seguimiento = SeguimientoPoa.objects.get(pk=id)
                    form = SeguimientoForm(initial=model_to_dict(seguimiento))
                    data['form'] = form
                    template = get_template("ajaxformmodal.html")
                    json_content = template.render(data)
                    return JsonResponse({"result": True, 'data': json_content})
                except Exception as ex:
                    return JsonResponse({"result": False, "mensaje": f"Error {ex}"})

            return HttpResponseRedirect(request.path)
        else:
            try:
                data['title'] = u'Gestionar evidencias POA'
                search, filtro, url_vars = request.GET.get('s', ''), \
                                           Q(status=True, mostrar=True), \
                                           f''
                if search:
                    data['s'] = search
                    filtro = filtro & Q(descripcion__icontains=search)
                    url_vars += f'&s={search}'
                listado = PeriodoPoa.objects.filter(filtro).order_by('-id')
                paginator = MiPaginador(listado, 20)
                page = int(request.GET.get('page', 1))
                paginator.rangos_paginado(page)
                data['paging'] = paging = paginator.get_page(page)
                data['listado'] = paging.object_list
                data['url_vars'] = url_vars
                return render(request, "poa_subirevidencia/periodos.html", data)
            except Exception as ex:
                return HttpResponseRedirect(f'/?info=Algo salio mal: {ex}')