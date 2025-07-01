# -*- coding: UTF-8 -*-
from decimal import Decimal
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.db.models import Q
from django.http import JsonResponse, HttpResponseRedirect
from django.shortcuts import render
from decorators import secure_module
from sagest.forms import GarantiasForm, RamoForm, ExtenderGrantiaForm, GarantiasComplementariasForm, RamosDocumentoForm
from sagest.models import datetime, Garantias, TipoRamo, GarantiaRamo, HistorialGarantias, \
    GarantiaComplementaria, GarantiaRamoComplementario
from settings import PORCENTAJE_ASEGURADO, PERSONA_AUTORIZA_COMPROBANTE_INGRESO_ID
from sga.commonviews import adduserdata
from sga.funciones import MiPaginador, log, null_to_decimal, generar_nombre
from django.template import Context
from django.template.loader import get_template


@login_required(redirect_field_name='ret', login_url='/loginsagest')
@transaction.atomic()
@secure_module
def view(request):
    data = {}
    adduserdata(request, data)
    if request.method == 'POST':
        action = request.POST['action']
        if action == 'add':
            try:
                f = GarantiasForm(request.POST)
                if f.is_valid():
                    if f.cleaned_data['fechafin'] < f.cleaned_data['fechainicio']:
                        return JsonResponse({"result": "bad", "mensaje": u"La fecha final no puede ser menor a la inicial."})
                    garantia = Garantias(numero=f.cleaned_data['numero'],
                                         contratista_id=f.cleaned_data['contratista'],
                                         concepto=f.cleaned_data['concepto'],
                                         proceso=f.cleaned_data['proceso'],
                                         aseguradora=f.cleaned_data['aseguradora'],
                                         monto=f.cleaned_data['monto'],
                                         fechainicio=f.cleaned_data['fechainicio'],
                                         fechafin=f.cleaned_data['fechafin'],
                                         fechafinreal=f.cleaned_data['fechafin'],
                                         autoriza_id=PERSONA_AUTORIZA_COMPROBANTE_INGRESO_ID)
                    garantia.save(request)
                    log(u'Adiciono garantia: %s' % garantia, request, "add")
                    return JsonResponse({"result": "ok"})
                else:
                     raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        if action == 'cargararchivo':
            try:
                if 'archivo' in request.FILES:
                    newfile = request.FILES['archivo']
                    if newfile.size > 10485760:
                        return JsonResponse({"result": "bad", "mensaje": u"Error, Tamaño de archivo Maximo permitido es de 10Mb"})
                    else:
                        newfiles = request.FILES['archivo']
                        newfilesd = newfiles._name
                        ext = newfilesd[newfilesd.rfind("."):]
                        if not ext.lower() == '.pdf':
                            return JsonResponse({"result": "bad", "mensaje": u"Error, solo archivos .pdf."})
                f = RamosDocumentoForm(request.POST)
                if 'archivo' in request.FILES:
                    newfile = request.FILES['archivo']
                    if newfile.size > 10485760:
                        return JsonResponse({"result": "bad", "mensaje": u"Error, Tamaño de archivo Maximo permitido es de 10Mb"})
                    else:
                        newfiles = request.FILES['archivo']
                        newfilesd = newfiles._name
                        ext = newfilesd[newfilesd.rfind("."):]
                        if not ext.lower() == '.pdf':
                            return JsonResponse({"result": "bad", "mensaje": u"Error, solo archivos .pdf."})
                garantiaramos = GarantiaRamo.objects.get(pk=int(request.POST['id']), status=True)
                if f.is_valid():
                    if 'archivo' in request.FILES:
                        newfile = request.FILES['archivo']
                        newfile._name = generar_nombre("evidenciaramo_", newfile._name)
                        garantiaramos.archivo = newfile
                        garantiaramos.save(request)
                    log(u'Subio evidencia ramos: %s' % garantiaramos, request, "edit")
                    return JsonResponse({"result": "ok"})
                else:
                    raise NameError('Error')

            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        # if action == 'envionotificacion':
        #     try:
        #         insretenciones = GarantiaRamo.objects.get(pk=request.POST['idinscripcioncohorte'])
        #         insretenciones.fecha_emailnotificacion = datetime.now()
        #         insretenciones.estado_emailnotificacion = True
        #         insretenciones.persona_envianotificacion = persona
        #         insretenciones.save(request)
        #         # per = Persona.objects.get(cedula='0923363030')
        #         log(u'Envio email envio retencion proveedor: %s' % (insretenciones), request, "add")
        #         if insretenciones.proveedor.email:
        #             asunto = u"RETENCIONES - ARCHIVOS"
        #             send_html_mail(asunto, "emails/notificar_retencion.html",
        #                            {'sistema': request.session['nombresistema'],'proveedor': insretenciones.proveedor,'insretenciones': insretenciones}, insretenciones.proveedor.emailpersonal(), [],
        #                            [insretenciones.archivopdf, insretenciones.archivoxml, ], cuenta=CUENTAS_CORREOS[1][1])
        #
        #         return JsonResponse({"result": "ok"})
        #     except Exception as ex:
        #         transaction.set_rollback(True)
        #         return JsonResponse({"result": "bad", "mensaje": u"Error al aprobar."})

        if action == 'addcomp':
            try:
                f = GarantiasComplementariasForm(request.POST)
                if f.is_valid():
                    if f.cleaned_data['fechafin'] < f.cleaned_data['fechainicio']:
                        return JsonResponse({"result": "bad", "mensaje": u"La fecha final no puede ser menor a la inicial."})
                    garantia = Garantias.objects.get(pk=request.POST['id'])
                    garantiacomp = GarantiaComplementaria(numero=f.cleaned_data['numero'],
                                                          garantia=garantia,
                                                         concepto=f.cleaned_data['concepto'],
                                                         monto=f.cleaned_data['monto'],
                                                         fechainicio=f.cleaned_data['fechainicio'],
                                                         fechafin=f.cleaned_data['fechafin'])
                    garantiacomp.save(request)
                    log(u'Adiciono garantia comp: %s' % garantiacomp, request, "add")
                    return JsonResponse({"result": "ok"})
                else:
                     raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        if action == 'addramo':
            try:
                f = RamoForm(request.POST)
                if f.is_valid():
                    garantia = Garantias.objects.get(pk=request.POST['garantia'])
                    if f.cleaned_data['fechafin'] < garantia.fechafin:
                        return JsonResponse({"result": "bad", "mensaje": u"La fecha final no puede ser menor a la del contrato %s." % garantia.fechafin})
                    if Decimal(f.cleaned_data['monto']) > garantia.monto:
                        return JsonResponse({"result": "bad", "mensaje": u"El monto asegurado no puede ser mayor al del contrato."})
                    tipo = f.cleaned_data['tipo']
                    monto = null_to_decimal(f.cleaned_data['monto'], 2) + garantia.total_asegurado()
                    porcentaje = 0
                    if not garantia.tiene_ramo_anticipo() and not garantia.tiene_ramo_cumplimiento():
                        porcentaje = f.cleaned_data['porcentaje']
                    if monto > garantia.monto:
                        return JsonResponse({"result": "bad", "mensaje": u"La suma de los ramos es mayor al valor del contrato %s." % garantia.monto})
                    ultimafecha = None
                    if GarantiaRamo.objects.filter(garantia=garantia).exists():
                        ultimafecha = GarantiaRamo.objects.filter(garantia=garantia)[0].fechafin
                    ramo = GarantiaRamo(tipo=f.cleaned_data['tipo'],
                                        garantia=garantia,
                                        numerodocumento=f.cleaned_data['numero'],
                                        fechainicio=ultimafecha if ultimafecha else garantia.fechafin,
                                        porcentaje=porcentaje,
                                        fechafin=f.cleaned_data['fechafin'],
                                        montoasegurado=f.cleaned_data['monto'])
                    ramo.save(request)
                    garantia.actualiza_total()
                    log(u'Adiciono garantia: %s' % garantia, request, "add")
                    return JsonResponse({"result": "ok"})
                else:
                     raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        if action == 'addramocomp':
            try:
                f = RamoForm(request.POST)
                if f.is_valid():
                    garantia = GarantiaComplementaria.objects.get(pk=request.POST['garantia'])
                    if f.cleaned_data['fechafin'] <= garantia.fechafin:
                        return JsonResponse({"result": "bad", "mensaje": u"La fecha final no puede ser menor a la del contrato %s." % garantia.fechafin})
                    if Decimal(f.cleaned_data['monto']) > garantia.monto:
                        return JsonResponse({"result": "bad", "mensaje": u"El monto asegurado no puede ser mayor al del contrato."})
                    tipo = f.cleaned_data['tipo']
                    monto = f.cleaned_data['monto'] + garantia.total_asegurado()
                    porcentaje = 0
                    if not garantia.tiene_ramo_anticipo() and not garantia.tiene_ramo_cumplimiento():
                        porcentaje = f.cleaned_data['porcentaje']
                    if monto > garantia.monto:
                        return JsonResponse({"result": "bad", "mensaje": u"La suma de los ramos es mayor al valor del contrato %s." % garantia.monto})
                    ultimafecha = None
                    if GarantiaRamoComplementario.objects.filter(garantia=garantia).exists():
                        ultimafecha = GarantiaRamoComplementario.objects.filter(garantia=garantia)[0].fechafin
                    ramo = GarantiaRamoComplementario(tipo=f.cleaned_data['tipo'],
                                        garantia=garantia,
                                        numerodocumento=f.cleaned_data['numero'],
                                        fechainicio=ultimafecha if ultimafecha else garantia.fechafin,
                                        porcentaje=porcentaje,
                                        fechafin=f.cleaned_data['fechafin'],
                                        montoasegurado=f.cleaned_data['monto'])
                    ramo.save(request)
                    garantia.actualiza_total()
                    log(u'Adiciono garantia: %s' % garantia, request, "add")
                    return JsonResponse({"result": "ok"})
                else:
                     raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        if action == 'extender':
            try:
                f = ExtenderGrantiaForm(request.POST)
                if f.is_valid():
                    garantia = Garantias.objects.get(pk=request.POST['garantia'])
                    if f.cleaned_data['fechafin'] <= garantia.fechafin:
                        return JsonResponse({"result": "bad", "mensaje": u"La fecha final no puede ser menor a la original del contrato %s." % garantia.fechafin})
                    extender = HistorialGarantias(garantia=garantia,
                                                  fechafinanterior=garantia.fechafin,
                                                  fechafin=f.cleaned_data['fechafin'],
                                                  motivo=f.cleaned_data['motivo'])
                    extender.save(request)
                    garantia.fechafin = f.cleaned_data['fechafin']
                    garantia.save(request)
                    log(u'Adiciono garantia: %s' % garantia, request, "add")
                    return JsonResponse({"result": "ok"})
                else:
                     raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        if action == 'editramo':
            try:
                f = RamoForm(request.POST)
                if f.is_valid():
                    ramo = GarantiaRamo.objects.get(pk=request.POST['id'])
                    garantia = ramo.garantia
                    if f.cleaned_data['fechafin'] < garantia.fechafin:
                        return JsonResponse({"result": "bad", "mensaje": u"La fecha final no puede ser menor a la del contrato %s." % garantia.fechafin})
                    if Decimal(f.cleaned_data['monto']) > garantia.monto:
                        return JsonResponse({"result": "bad", "mensaje": u"El monto asegurado no puede ser mayor al del contrato."})
                    monto = f.cleaned_data['monto']
                    if monto > garantia.total_asegurado():
                        return JsonResponse({"result": "bad", "mensaje": u"La suma de los ramos es mayor al valor del contrato %s." % garantia.monto})
                    tipo = f.cleaned_data['tipo']
                    ramo.tipo = tipo
                    ramo.numerodocumento = f.cleaned_data['numero']
                    porcentaje = f.cleaned_data['porcentaje'] if tipo.id == 2 else PORCENTAJE_ASEGURADO
                    ramo.fechainicio = garantia.fechafin
                    ramo.fechafin = f.cleaned_data['fechafin']
                    ramo.montoasegurado = f.cleaned_data['monto']
                    ramo.save(request)
                    garantia.fechafin = f.cleaned_data['fechafin']
                    garantia.save(request)
                    garantia.actualiza_total()
                    log(u'Adiciono garantia: %s' % garantia, request, "add")
                    return JsonResponse({"result": "ok"})
                else:
                     raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'edit':
            try:
                f = GarantiasForm(request.POST)
                if f.is_valid():
                    garantia = Garantias.objects.get(pk=request.POST['id'])
                    garantia.numero = f.cleaned_data['numero']
                    garantia.concepto = f.cleaned_data['concepto']
                    garantia.proceso = f.cleaned_data['proceso']
                    garantia.contratista_id = f.cleaned_data['contratista']
                    garantia.aseguradora = f.cleaned_data['aseguradora']
                    if not garantia.tiene_ramo():
                        garantia.fechainicio = f.cleaned_data['fechainicio']
                        garantia.fechafin = f.cleaned_data['fechafin']
                        garantia.fechafinreal = f.cleaned_data['fechafin']
                        garantia.monto = f.cleaned_data['monto']
                    garantia.save(request)
                    log(u'Modifico garantia: %s' % garantia, request, "edit")
                    return JsonResponse({"result": "ok"})
                else:
                     raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'editcomp':
            try:
                f = GarantiasComplementariasForm(request.POST)
                if f.is_valid():
                    garantia = GarantiaComplementaria.objects.get(pk=request.POST['id'])
                    garantia.numero = f.cleaned_data['numero']
                    garantia.concepto = f.cleaned_data['concepto']
                    if not garantia.tiene_ramo():
                        garantia.fechainicio = f.cleaned_data['fechainicio']
                        garantia.fechafin = f.cleaned_data['fechafin']
                        garantia.monto = f.cleaned_data['monto']
                    garantia.save(request)
                    log(u'Modifico garantia: %s' % garantia, request, "edit")
                    return JsonResponse({"result": "ok"})
                else:
                     raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        if action == 'detalle_ramo':
            try:
                data['garantia'] = garantia = Garantias.objects.get(pk=int(request.POST['id']))
                data['cumplimientos'] = garantia.garantiaramo_set.filter(tipo=1).order_by('-id')
                data['historiales'] = garantia.historialgarantias_set.all().order_by('-id')
                data['usos'] = garantia.garantiaramo_set.filter(tipo=2).order_by('-id')
                template = get_template("rec_garantias/detalle.html")
                json_content = template.render(data)
                return JsonResponse({"result": "ok", 'html': json_content})
            except Exception as ex:
                return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

        if action == 'detalle_ramo_comp':
            try:
                data['garantia'] = garantia = GarantiaComplementaria.objects.get(pk=int(request.POST['id']))
                data['cumplimientos'] = garantia.garantiaramocomplementario_set.filter(tipo=1).order_by('-id')
                data['usos'] = garantia.garantiaramocomplementario_set.filter(tipo=2).order_by('-id')
                template = get_template("rec_garantias/detallecomp.html")
                json_content = template.render(data)
                return JsonResponse({"result": "ok", 'html': json_content})
            except Exception as ex:
                return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

        if action == 'delete':
            try:
                garantia = Garantias.objects.get(pk=request.POST['id'])
                log(u'Elimino garantia: %s' % garantia, request, "del")
                garantia.delete()
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al eliminar los datos."})

        if action == 'deleteramo':
            try:
                ramo = GarantiaRamo.objects.get(pk=request.POST['id'])
                garantia = ramo.garantia
                garantia.save(request)
                log(u'Elimino ramo: %s' % ramo, request, "del")
                ramo.delete()
                garantia.actualiza_total()
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al eliminar los datos."})

        if action == 'deleteramocomp':
            try:
                ramo = GarantiaRamoComplementario.objects.get(pk=request.POST['id'])
                garantia = ramo.garantia
                garantia.save(request)
                log(u'Elimino ramo: %s' % ramo, request, "del")
                ramo.delete()
                garantia.actualiza_total()
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al eliminar los datos."})

        if action == 'deletecomp':
            try:
                complementario = GarantiaComplementaria.objects.get(pk=request.POST['id'])
                log(u'Elimino Garantia complementario: %s [%s]' % (complementario,complementario.id), request, "del")
                complementario.delete()
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al eliminar los datos."})

        if action == 'calculo_seguro':
            try:
                tipo = TipoRamo.objects.get(pk=int(request.POST['id']))
                garantia = Garantias.objects.get(pk=int(request.POST['g']))
                porcentaje = Decimal(request.POST['porcentaje']) / Decimal(100)
                monto = 0
                monto = garantia.monto * porcentaje
                return JsonResponse({"result": "ok", "monto": float(monto)})
            except Exception as ex:
                return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos"})

        if action == 'calculo_seguro_comp':
            try:
                tipo = TipoRamo.objects.get(pk=int(request.POST['id']))
                garantia = GarantiaComplementaria.objects.get(pk=int(request.POST['g']))
                porcentaje = Decimal(request.POST['porcentaje']) / Decimal(100)
                monto = 0
                monto = garantia.monto * porcentaje
                return JsonResponse({"result": "ok", "monto": float(monto)})
            except Exception as ex:
                return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos"})

        return JsonResponse({"result": "bad", "mensaje": u"Solicitud Incorrecta."})
    else:
        if 'action' in request.GET:
            action = request.GET['action']

            if action == 'add':
                try:
                    data['title'] = u'Nueva Garantía'
                    form = GarantiasForm()
                    data['form'] = form
                    return render(request, "rec_garantias/add.html", data)
                except Exception as ex:
                    pass

            if action == 'addcomp':
                try:
                    data['title'] = u'Nueva Contrato Complementario'
                    form = GarantiasComplementariasForm()
                    data['garantia'] = Garantias.objects.get(id=int(request.GET['id']))
                    data['form'] = form
                    return render(request, "rec_garantias/addcomp.html", data)
                except Exception as ex:
                    pass

            if action == 'addramo':
                try:
                    data['title'] = u'Nueva Garantía'
                    numero = 0
                    data['garantia'] = garantia = Garantias.objects.get(pk=int(request.GET['id']))
                    data['porciento'] = PORCENTAJE_ASEGURADO
                    tiene_cumplimiento = 0
                    if garantia.tiene_ramo_cumplimiento():
                        tiene_cumplimiento = 1
                    data['tiene_cumplimiento'] = tiene_cumplimiento
                    tiene_anticipo = 0
                    if garantia.tiene_ramo_anticipo():
                        tiene_anticipo = 1
                    data['tiene_anticipo'] = tiene_anticipo
                    fechafin = datetime.now().date()
                    if GarantiaRamo.objects.filter(garantia=garantia).exists():
                        numero = GarantiaRamo.objects.filter(garantia=garantia).order_by('-id')[0].numerodocumento
                        fechafin = GarantiaRamo.objects.filter(garantia=garantia).order_by('-id')[0].fechafin
                    form = RamoForm(initial={'numero': numero,
                                             'fechafin': fechafin})
                    data['form'] = form
                    return render(request, "rec_garantias/addramo.html", data)
                except Exception as ex:
                    pass

            if action == 'addramocomp':
                try:
                    data['title'] = u'Nueva Garantía'
                    numero = 0
                    data['garantia'] = garantia = GarantiaComplementaria.objects.get(pk=int(request.GET['id']))
                    data['porciento'] = PORCENTAJE_ASEGURADO
                    tiene_cumplimiento = 0
                    if garantia.tiene_ramo_cumplimiento():
                        tiene_cumplimiento = 1
                    data['tiene_cumplimiento'] = tiene_cumplimiento
                    tiene_anticipo = 0
                    if garantia.tiene_ramo_anticipo():
                        tiene_anticipo = 1
                    data['tiene_anticipo'] = tiene_anticipo
                    fechafin = datetime.now().date()
                    if GarantiaRamoComplementario.objects.filter(garantia=garantia).exists():
                        numero = GarantiaRamoComplementario.objects.filter(garantia=garantia).order_by('-id')[0].numerodocumento
                        fechafin = GarantiaRamoComplementario.objects.filter(garantia=garantia).order_by('-id')[0].fechafin
                    form = RamoForm(initial={'numero': numero,
                                             'fechafin': fechafin})
                    data['form'] = form
                    return render(request, "rec_garantias/addramocomp.html", data)
                except Exception as ex:
                    pass

            if action == 'extender':
                try:
                    data['title'] = u'Extender Contrato'
                    data['garantia'] = garantia = Garantias.objects.get(pk=int(request.GET['id']))
                    data['form'] = ExtenderGrantiaForm()
                    return render(request, "rec_garantias/extender.html", data)
                except Exception as ex:
                    pass

            if action == 'ramos':
                try:
                    data['title'] = u'Ramos'
                    data['garantia'] = garantia = Garantias.objects.get(pk=int(request.GET['id']))
                    data['ramos'] = garantia.garantiaramo_set.all().order_by('-id')
                    return render(request, "rec_garantias/ramos.html", data)
                except Exception as ex:
                    pass

            if action == 'ramoscomp':
                try:
                    data['title'] = u'Ramos'
                    data['garantia'] = garantia = GarantiaComplementaria.objects.get(pk=int(request.GET['id']))
                    data['ramos'] = garantia.garantiaramocomplementario_set.all().order_by('-id')
                    return render(request, "rec_garantias/ramoscomp.html", data)
                except Exception as ex:
                    pass

            if action == 'complementarios':
                try:
                    data['title'] = u'Contratos complementarios'
                    data['garantia'] = garantia = Garantias.objects.get(pk=int(request.GET['id']))
                    data['complementarios'] = garantia.garantiacomplementaria_set.all().order_by('-id')
                    return render(request, "rec_garantias/complementarios.html", data)
                except Exception as ex:
                    pass

            elif action == 'edit':
                try:
                    data['title'] = u'Editar Garantia'
                    data['garantia'] = garantia = Garantias.objects.get(pk=request.GET['id'])
                    form = GarantiasForm(initial={'numero': garantia.numero,
                                                  'fechainicio': garantia.fechainicio,
                                                  'fechafin': garantia.fechafin,
                                                  'contratista': garantia.contratista.id,
                                                  'concepto': garantia.concepto,
                                                  'proceso': garantia.proceso,
                                                  'aseguradora': garantia.aseguradora,
                                                  'monto': garantia.monto})
                    form.editar(garantia)
                    data['form'] = form
                    return render(request, "rec_garantias/edit.html", data)
                except Exception as ex:
                    pass

            elif action == 'cargararchivo':
                try:
                    data['title'] = u'Evidencias de requisitos de maestría'
                    data['id'] = request.GET['id']
                    data['idevidencia'] = request.GET['idevidencia']
                    data['garantiaramos'] = garantiaramos = GarantiaRamo.objects.get(pk=int(request.GET['idevidencia']), status=True)
                    form = RamosDocumentoForm()
                    data['form'] = form
                    template = get_template("rec_garantias/add_detalleramos.html")
                    json_content = template.render(data)
                    return JsonResponse({"result": "ok", 'data': json_content, "nombre": "SUBIR DOCUMENTO DE REQUISITO " + str(garantiaramos.tipo.nombre)})
                except Exception as ex:
                    pass

            elif action == 'editcomp':
                try:
                    data['title'] = u'Editar Garantia'
                    data['garantia'] = garantia = GarantiaComplementaria.objects.get(pk=request.GET['id'])
                    form = GarantiasComplementariasForm(initial={'numero': garantia.numero,
                                                  'fechainicio': garantia.fechainicio,
                                                  'fechafin': garantia.fechafin,
                                                  'concepto': garantia.concepto,
                                                  'monto': garantia.monto})
                    form.editar(garantia)
                    data['form'] = form
                    return render(request, "rec_garantias/editcomp.html", data)
                except Exception as ex:
                    pass

            elif action == 'editramo':
                try:
                    # puede_realizar_accion(request, 'sga.puede_modificar_administrativos')
                    data['title'] = u'Editar Ramo'
                    data['ramo'] = ramo = GarantiaRamo.objects.get(pk=request.GET['id'])
                    form = RamoForm(initial={'numero': ramo.numerodocumento,
                                             'fechafin': ramo.fechafin,
                                             'porcentaje': ramo.porcentaje,
                                             'tipo': ramo.tipo,
                                             'monto': ramo.montoasegurado})
                    data['form'] = form
                    return render(request, "rec_garantias/editramo.html", data)
                except Exception as ex:
                    pass

            if action == 'delete':
                try:
                    # puede_realizar_accion(request, 'sagest.puede_modificar_catalogo')
                    data['title'] = u'Eliminar Garantia'
                    data['garantia'] = Garantias.objects.get(pk=request.GET['id'])
                    return render(request, 'rec_garantias/delete.html', data)
                except Exception as ex:
                    pass

            if action == 'deleteramo':
                try:
                    # puede_realizar_accion(request, 'sagest.puede_modificar_catalogo')
                    data['title'] = u'Eliminar Ramo'
                    data['ramo'] = ramo = GarantiaRamo.objects.get(pk=request.GET['id'])
                    data['garantia'] = ramo.garantia
                    return render(request, 'rec_garantias/deleteramo.html', data)
                except Exception as ex:
                    pass

            if action == 'deleteramocomp':
                try:
                    # puede_realizar_accion(request, 'sagest.puede_modificar_catalogo')
                    data['title'] = u'Eliminar Ramo'
                    data['ramo'] = ramo = GarantiaRamoComplementario.objects.get(pk=request.GET['id'])
                    data['garantia'] = ramo.garantia
                    return render(request, 'rec_garantias/deleteramocomp.html', data)
                except Exception as ex:
                    pass

            if action == 'deletecomp':
                try:
                    data['title'] = u'Eliminar complementaria'
                    data['complementario'] = comp = GarantiaComplementaria.objects.get(pk=request.GET['id'])
                    data['garantia']= comp.garantia
                    return render(request, 'rec_garantias/deletecomplementario.html', data)
                except Exception as ex:
                    pass

            return HttpResponseRedirect(request.path)
        else:
            data['title'] = u'Garantías'
            search = None
            ids = None
            if 's' in request.GET:
                search = request.GET['s'].strip()
                ss = search.split(' ')
                if len(ss) == 1:
                    garantias = Garantias.objects.filter(Q(contratista__nombres__icontains=search) |
                                                     Q(contratista__apellido1__icontains=search) |
                                                     Q(contratista__apellido2__icontains=search) |
                                                     Q(contratista__cedula__icontains=search) |
                                                     Q(contratista__ruc__icontains=search) |
                                                     Q(concepto__icontains=search) |
                                                     Q(aseguradora__nombre__icontains=search)).distinct()
                else:
                    garantias = Garantias.objects.filter(Q(contratista__apellido1__icontains=ss[0]) &
                                                     Q(contratista__apellido2__icontains=ss[1])).distinct()
            elif 'id' in request.GET:
                ids = request.GET['id']
                garantias = Garantias.objects.filter(id=ids).distinct()
            else:
                garantias = Garantias.objects.all()
            paging = MiPaginador(garantias, 25)
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
            data['search'] = search if search else ""
            data['garantias'] = page.object_list
            try:
                return render(request, "rec_garantias/view.html", data)
            except Exception as ex:
                pass

