# -*- coding: latin-1 -*-
import json
from itertools import count
import random
from django.contrib.auth.decorators import login_required
from django.db import transaction
from sga.templatetags.sga_extras import encrypt
from django.db.models import Sum
from django.http import HttpResponseRedirect, JsonResponse, HttpResponse
from django.shortcuts import render
from django.template.loader import get_template
from django.template.context import Context
from django.db.models.query_utils import Q
from datetime import datetime, timedelta, date
from xlwt import *
from xlwt import easyxf
import xlwt

from decorators import secure_module, last_access
from sagest.models import PrestamoActivosOperaciones, ActivoTecnologico, AuditoriaPrestamoActivosOperaciones
from sga.models import Persona
from sga.commonviews import adduserdata
from sagest.forms import PrestamoActivoForm
from sga.funciones import MiPaginador, log, notificacion
from sga.funcionesxhtml2pdf import conviert_html_to_pdf
from core.choices.models.general import MY_CUENTAS_CORREOS
from sga.tasks import send_html_mail, conectar_cuenta

IDS_MODULOS_OPERACIONES = [451, 463]


@login_required(redirect_field_name='ret', login_url='/loginsga')
@secure_module
@last_access
@transaction.atomic()
def view(request):
    data = {}
    adduserdata(request, data)
    data['persona'] = persona = request.session['persona']
    perfilprincipal = request.session['perfilprincipal']
    if request.method == 'POST':
        if 'action' in request.POST:
            action = request.POST['action']

            if action == 'addprestamo':
                try:
                    form = PrestamoActivoForm(request.POST)
                    if form.is_valid():
                        hoy = datetime.now().date()
                        consultarprestamo = PrestamoActivosOperaciones.objects.filter(status=True, activotecnologico_id=form.cleaned_data['activotecnologico'], estado=1)
                        consultarresponsable = ActivoTecnologico.objects.get(id=int(form.cleaned_data['activotecnologico']))

                        if (consultarresponsable.activotecnologico.responsable_id == int(form.cleaned_data['personarecibe'])):
                            return JsonResponse({"result": "bad", "mensaje": "La persona que entrega debe de ser distinta a la persona que recibe"})

                        if consultarprestamo:
                            return JsonResponse({"result": "bad", "mensaje": "Préstamo existente con el mismo activo"})

                        # if not form.cleaned_data['desde'] >= hoy and form.cleaned_data['hasta'] >= hoy:
                        #     return JsonResponse({"result": "bad", "mensaje": "Las fechas ingresadas deben de ser superiores o iguales a la fecha actual"})

                        if not form.cleaned_data['hasta'] >= form.cleaned_data['desde']:
                            return JsonResponse({"result": "bad", "mensaje": "La fecha final debe de ser superior o igual a la fecha de inicio."})

                        nuevoprestamo = PrestamoActivosOperaciones(
                            activotecnologico_id=form.cleaned_data['activotecnologico'],
                            personaentrega_id=request.POST['id_personaentrega'],
                            personarecibe_id=form.cleaned_data['personarecibe'],
                            desde=form.cleaned_data['desde'],
                            hasta=form.cleaned_data['hasta'],
                            estado=1,
                            observacion=form.cleaned_data['observacion']
                        )
                        nuevoprestamo.save(request)
                        log(u'Registro nuevo prestamo %s - %s' % (persona, nuevoprestamo), request, "add")
                        auditoria = AuditoriaPrestamoActivosOperaciones(
                            prestamo=nuevoprestamo,
                            personaentrega=nuevoprestamo.personaentrega,
                            personarecibe=nuevoprestamo.personarecibe,
                            desde=nuevoprestamo.desde,
                            hasta=nuevoprestamo.hasta,
                            fechadevolucion=nuevoprestamo.fechadevolucion,
                            observacion=nuevoprestamo.observacion,
                            estado=1
                        )
                        auditoria.save(request)
                        log(u'Auditoria nuevo prestamo %s - %s' % (persona, auditoria), request, "add")
                        asunto = u"Préstamo del activo tecnológico " + str(nuevoprestamo.activotecnologico)
                        send_html_mail(asunto, "emails/notificarprestamoactivo.html",
                                       {'sistema': request.session['nombresistema'], 'Activo': nuevoprestamo.activotecnologico,
                                        'responsable': nuevoprestamo.personaentrega,
                                        'personarecibe': nuevoprestamo.personarecibe,
                                        'activo': nuevoprestamo.activotecnologico,
                                        'personaejecuta':persona},
                                       ['operaciones.tic@unemi.edu.ec'], [],
                                       cuenta=MY_CUENTAS_CORREOS[16][1])
                        return JsonResponse({"result": "ok"})
                    else:
                        transaction.set_rollback(True)
                        return JsonResponse({'result': False, "form": [{k: v[0]} for k, v in form.errors.items()],
                                             "mensaje": "Error en el formulario"})
                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje": "Error al registrar el préstamo"})

            elif action == 'editarprestamo':
                try:
                    form = PrestamoActivoForm(request.POST)
                    actualiza_datos = False
                    if form.is_valid():
                        idprestamo = int(request.POST['idprestamo'])
                        hoy = datetime.now().date()
                        # if (form.cleaned_data['desde'] >= hoy and form.cleaned_data['hasta'] >= hoy):
                        consultarresponsable = ActivoTecnologico.objects.get(id=int(form.cleaned_data['activotecnologico']))

                        if (consultarresponsable.activotecnologico.responsable_id == int(form.cleaned_data['personarecibe'])):
                            return JsonResponse({"result": "bad", "mensaje": "La persona que entrega debe de ser distinta a la persona que recibe"})

                        if not form.cleaned_data['hasta'] >= form.cleaned_data['desde']:
                            return JsonResponse({"result": "bad", "mensaje": "La fecha final debe de ser superior o igual a la fecha de inicio."})

                        edicionprestamo = PrestamoActivosOperaciones.objects.get(id=idprestamo)
                        if edicionprestamo.personarecibe_id != form.cleaned_data[
                            'personarecibe'] or edicionprestamo.desde != form.cleaned_data[
                            'desde'] or edicionprestamo.hasta != form.cleaned_data[
                            'hasta'] or edicionprestamo.observacion != form.cleaned_data['observacion']:
                            actualiza_datos = True
                        edicionprestamo.activotecnologico_id = form.cleaned_data['activotecnologico']
                        edicionprestamo.personaentrega_id = request.POST['id_personaentrega']
                        edicionprestamo.personarecibe_id = form.cleaned_data['personarecibe']
                        edicionprestamo.desde = form.cleaned_data['desde']
                        edicionprestamo.hasta = form.cleaned_data['hasta']
                        edicionprestamo.observacion = form.cleaned_data['observacion']
                        edicionprestamo.save(request)
                        log(u'Edita prestamo %s - %s' % (persona, edicionprestamo), request, "act")
                        if actualiza_datos:
                            auditoria = AuditoriaPrestamoActivosOperaciones(
                                prestamo=edicionprestamo,
                                personaentrega_id=request.POST['id_personaentrega'],
                                personarecibe_id=form.cleaned_data['personarecibe'],
                                desde=form.cleaned_data['desde'],
                                hasta=form.cleaned_data['hasta'],
                                fechadevolucion=edicionprestamo.fechadevolucion,
                                observacion=form.cleaned_data['observacion'],
                                estado=3
                            )
                            auditoria.save(request)
                            log(u'Auditoria actualiza prestamo %s - %s' % (persona, auditoria), request, "add")
                        return JsonResponse({"result": "ok"})

                        # else:
                        #     return JsonResponse(
                        #         {"result": "bad",
                        #          "mensaje": "Las fechas ingresadas deben de ser superiores o iguales a la fecha actual"})
                    else:
                        return JsonResponse(
                            {"result": "bad", "mensaje": "Por favor, llene el formulario correctamente."})
                except Exception as ex:
                    pass

            elif action == 'deleteprestamo':
                try:
                    deleteprestamo = PrestamoActivosOperaciones.objects.get(id=int(request.POST['id']))
                    deleteprestamo.status = False
                    deleteprestamo.save(request)
                    log(u'Elimina préstamo: %s' % deleteprestamo, request, "del")
                    auditoria = AuditoriaPrestamoActivosOperaciones(
                        prestamo=deleteprestamo,
                        personaentrega=deleteprestamo.personaentrega,
                        personarecibe=deleteprestamo.personarecibe,
                        desde=deleteprestamo.desde,
                        hasta=deleteprestamo.hasta,
                        fechadevolucion=deleteprestamo.fechadevolucion,
                        observacion=deleteprestamo.observacion,
                        estado=5
                    )
                    auditoria.save(request)
                    log(u'Auditoria elimina prestamo %s - %s' % (persona, auditoria), request, "add")
                    return JsonResponse({"result": "ok"})
                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje": u'Error al eliminar el préstamo'})

            elif action == 'notificartraspaso':
                try:
                    prestamoactivo = PrestamoActivosOperaciones.objects.get(id=int(request.POST['id']))
                    titulo = "Notificación de traspaso"
                    cuerpo = "Se notifica que se realizará el traspaso del activo: %s" % (
                        prestamoactivo.activotecnologico.activotecnologico)
                    notificacion(titulo,
                                 cuerpo, prestamoactivo.personarecibe, None,
                                 'mis_activos', prestamoactivo.pk,
                                 1, 'sga', prestamoactivo, request)
                    notificacion(titulo,
                                 cuerpo, prestamoactivo.personarecibe, None,
                                 'mis_activos', prestamoactivo.pk,
                                 1, 'sagest', prestamoactivo, request)
                    auditoria = AuditoriaPrestamoActivosOperaciones(
                        prestamo=prestamoactivo,
                        personaentrega=prestamoactivo.personaentrega,
                        personarecibe=prestamoactivo.personarecibe,
                        desde=prestamoactivo.desde,
                        hasta=prestamoactivo.hasta,
                        fechadevolucion=prestamoactivo.fechadevolucion,
                        observacion=prestamoactivo.observacion,
                        estado=4
                    )
                    auditoria.save(request)
                    log(u'Auditoria notifica traspaso - prestamo %s - %s' % (persona, auditoria), request, "add")
                    return JsonResponse({"result": "ok"})
                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje": u'Error al notificar traspaso'})

            elif action == 'confirmardevolucionactivo':
                try:
                    idprestamo = int(request.POST['id'])
                    devolucionactivo = PrestamoActivosOperaciones.objects.get(id=idprestamo)
                    devolucionactivo.fechadevolucion = datetime.now().date()
                    devolucionactivo.estado = 2
                    devolucionactivo.save(request)
                    log(u'Confirma devolucion %s - %s' % (persona, devolucionactivo), request, "act")
                    auditoria = AuditoriaPrestamoActivosOperaciones(
                        prestamo=devolucionactivo,
                        personaentrega=devolucionactivo.personaentrega,
                        personarecibe=devolucionactivo.personarecibe,
                        desde=devolucionactivo.desde,
                        hasta=devolucionactivo.hasta,
                        fechadevolucion=devolucionactivo.fechadevolucion,
                        observacion=devolucionactivo.observacion,
                        estado=7
                    )
                    auditoria.save(request)
                    log(u'Auditoria devolucion - prestamo %s - %s' % (persona, auditoria), request, "add")
                    return JsonResponse({"result": "ok"})
                except Exception as ex:
                    return JsonResponse({"result":"bad", "mensaje":u'Error al confirmar la devolución del activo'})

            elif action == 'rechazadevolucionactivo':
                try:
                    idprestamo = int(request.POST['id'])
                    devolucionactivo = PrestamoActivosOperaciones.objects.get(id=idprestamo)
                    devolucionactivo.estado = 1
                    devolucionactivo.save(request)
                    log(u'Rechaza devolucion %s - %s' % (persona, devolucionactivo), request, "act")
                    auditoria = AuditoriaPrestamoActivosOperaciones(
                        prestamo=devolucionactivo,
                        personaentrega=devolucionactivo.personaentrega,
                        personarecibe=devolucionactivo.personarecibe,
                        desde=devolucionactivo.desde,
                        hasta=devolucionactivo.hasta,
                        fechadevolucion=devolucionactivo.fechadevolucion,
                        observacion=devolucionactivo.observacion,
                        estado=9
                    )
                    auditoria.save(request)
                    auditoria = AuditoriaPrestamoActivosOperaciones(
                        prestamo=devolucionactivo,
                        personaentrega=devolucionactivo.personaentrega,
                        personarecibe=devolucionactivo.personarecibe,
                        desde=devolucionactivo.desde,
                        hasta=devolucionactivo.hasta,
                        fechadevolucion=devolucionactivo.fechadevolucion,
                        observacion=devolucionactivo.observacion,
                        estado=10
                    )
                    auditoria.save(request)
                    log(u'Auditoria rechaza devolucion - prestamo %s - %s' % (persona, auditoria), request, "add")
                    return JsonResponse({"result": "ok"})
                except Exception as ex:
                    return JsonResponse({"result":"bad", "mensaje":u'Error al confirmar la devolución del activo'})

            elif action == 'devolverprestamoactivo':
                try:
                    idprestamo = int(request.POST['id'])
                    devolucionactivo = PrestamoActivosOperaciones.objects.get(id=idprestamo)
                    devolucionactivo.fechadevolucion = datetime.now().date()
                    devolucionactivo.estado = 5
                    devolucionactivo.save(request)
                    log(u'Devuelve activo %s - %s' % (persona, devolucionactivo), request, "act")
                    auditoria = AuditoriaPrestamoActivosOperaciones(
                        prestamo=devolucionactivo,
                        personaentrega=devolucionactivo.personaentrega,
                        personarecibe=devolucionactivo.personarecibe,
                        desde=devolucionactivo.desde,
                        hasta=devolucionactivo.hasta,
                        fechadevolucion=devolucionactivo.fechadevolucion,
                        observacion=devolucionactivo.observacion,
                        estado=6
                    )
                    auditoria.save(request)
                    log(u'Auditoria devolucion - prestamo %s - %s' % (persona, auditoria), request, "add")
                    return JsonResponse({"result": "ok"})
                except Exception as ex:
                    return JsonResponse({"result":"bad", "mensaje":u'Error al confirmar la devolución del activo'})

        return JsonResponse({"result": "bad", "mensaje": u"Solicitud Incorrecta."})
    else:
        if 'action' in request.GET:
            action = request.GET['action']

            if action == 'addprestamo':
                try:
                    data['title'] = u'Registrar nuevo préstamo'
                    form = PrestamoActivoForm()
                    fecha_actual = date.today()
                    numero_dias = timedelta(15)
                    fechaaumentada = fecha_actual + numero_dias
                    form.fields['hasta'].initial = fechaaumentada
                    data['form'] = form
                    data['action'] = 'addprestamo'
                    return render(request, "operaciones_prestamoactivos/addprestamo.html", data)
                except Exception as ex:
                    pass

            elif action == 'buscarpersona':
                try:
                    q = request.GET['q'].upper().strip()
                    s = q.split(" ")

                    if s.__len__() == 1:
                        # activo = ActivoFijo.objects.filter(Q(codigogobierno__icontains=q) | Q(codigointerno__icontains=s[0]) | Q(serie__icontains=q),status=True, catalogo__equipoelectronico=True if tipo == 2 else False).distinct()[:20]
                        personarecibe = Persona.objects.filter((
                                                                       Q(nombres__icontains=s[0]) | Q(
                                                                   cedula__icontains=s[0]) | Q(
                                                                   apellido1__icontains=s[0]) | Q(
                                                                   apellido2__icontains=s[0])) & Q(status=True) & (
                                                                       Q(perfilusuario__administrativo__isnull=False) | Q(
                                                                   perfilusuario__profesor__isnull=False))).distinct()[
                                        :20]
                    else:
                        personarecibe = Persona.objects.filter((
                                                                       Q(nombres__icontains=q) | (Q(
                                                                   apellido1__icontains=s[0]) & Q(
                                                                   apellido2__icontains=s[1]))) & Q(status=True) & (
                                                                       Q(perfilusuario__administrativo__isnull=False) | Q(
                                                                   perfilusuario__profesor__isnull=False))).distinct()[
                                        :20]

                    data = {"result": "ok",
                            "results": [{"id": x.id, "identificacion": x.cedula, "name": x.__str__()} for x in
                                        personarecibe]}
                    return JsonResponse(data)
                except Exception as ex:
                    pass

            elif action == 'buscaractivotecnologico':
                try:
                    q = request.GET['q'].upper().strip()
                    s = q.split(" ")
                    filtros = (Q(activotecnologico__catalogo__equipoelectronico=True) &
                               Q(activotecnologico__catalogo__status=True) &
                               Q(activotecnologico__statusactivo=1) &
                               Q(activotecnologico__status=True) &
                               Q(activotecnologico__procesobaja=False) &
                               Q(activotecnologico__catalogo__clasificado=True) &
                               (Q(activotecnologico__archivobaja='') | Q(activotecnologico__archivobaja__isnull=False))
                               )

                    if s.__len__() == 1:
                        # activo = ActivoFijo.objects.filter(Q(codigogobierno__icontains=q) | Q(codigointerno__icontains=s[0]) | Q(serie__icontains=q),status=True, catalogo__equipoelectronico=True if tipo == 2 else False).distinct()[:20]
                        filtros = filtros & (
                            (Q(activotecnologico__codigogobierno__icontains=s[0])
                             | Q(activotecnologico__codigointerno__icontains=s[0])
                             | Q(activotecnologico__serie__icontains=s[0])
                             | Q(activotecnologico__modelo__icontains=s[0])
                             | Q(activotecnologico__responsable__nombres__icontains=s[0])
                             | Q(activotecnologico__responsable__apellido1__icontains=s[0])
                             | Q(activotecnologico__responsable__apellido2__icontains=s[0]))
                        )
                    else:
                        filtros = filtros & (
                            (Q(activotecnologico__codigogobierno__icontains=q)
                             | Q(activotecnologico__codigointerno__icontains=q)
                             | Q(activotecnologico__serie__icontains=q)
                             | Q(activotecnologico__modelo__icontains=q)
                             | Q(activotecnologico__responsable__nombres__icontains=q)
                             | Q(activotecnologico__responsable__apellido1__icontains=q)
                             | Q(activotecnologico__responsable__apellido2__icontains=q))
                        )

                    activotecnologico = ActivoTecnologico.objects.filter(filtros).distinct()[:20]

                    data = {"result": "ok", "results": [
                        {"id": x.id, "name": x.__str__(), "responsable": x.activotecnologico.responsable.__str__(),
                         "idresponsable": x.activotecnologico.responsable.id} for x in activotecnologico]}
                    return JsonResponse(data)
                except Exception as ex:
                    pass

            elif action == 'editarprestamo':
                try:
                    data['title'] = u'Editar préstamo'
                    data['prestamoactivo'] = editarprestamo = PrestamoActivosOperaciones.objects.get(
                        pk=int(request.GET['id']))
                    form = PrestamoActivoForm(initial={'desde': editarprestamo.desde,
                                                       'hasta': editarprestamo.hasta,
                                                       'observacion': editarprestamo.observacion})
                    form.cargar_activotecnologico(editarprestamo.activotecnologico)
                    form.cargar_personarecibe(editarprestamo.personarecibe)
                    data['form'] = form
                    return render(request, "operaciones_prestamoactivos/editarprestamo.html", data)
                except Exception as ex:
                    pass

            elif action == 'auditoriaprestamo':
                try:
                    auditoriaprestamo = AuditoriaPrestamoActivosOperaciones.objects.filter(prestamo_id=int(request.GET['id'])).order_by('-id')
                    data['registroauditorias'] = auditoriaprestamo
                    template = get_template('operaciones_prestamoactivos/modal/auditoriaprestamo.html')
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    pass

            elif action == 'generarreporte':
                try:
                    hoy = datetime.now().date()
                    tiporeporte = int(request.GET['tiporeporte'])
                    estadoprestamo = int(request.GET['estadoprestamo'])
                    filtro = Q(status=True)

                    if estadoprestamo != 0:
                        if estadoprestamo != 3:
                            filtro = filtro & Q(estado=estadoprestamo)

                    if estadoprestamo == 3:
                        lista_activos = []
                        activosprestados = PrestamoActivosOperaciones.objects.filter(status=True, estado=1)
                        for activoprestado in activosprestados:
                            if not hoy <= activoprestado.hasta:
                                lista_activos.append(activoprestado.id)
                        filtro = filtro & Q(id__in=lista_activos)

                    if tiporeporte == 1:
                        activotecnologico = request.GET['activotecnologico']
                        filtro = filtro & Q(activotecnologico_id=activotecnologico)


                    if tiporeporte == 2:
                        fechadesde = request.GET['fechadesde']
                        fechahasta = request.GET['fechahasta']
                        filtro = filtro & (Q(fechadesde=fechadesde) & Q(fechahasta=fechahasta))

                    if tiporeporte == 3:
                        fechadevolucion = request.GET['fechadevolucion']
                        filtro = filtro & Q(fechadevolucion=fechadevolucion)

                    if tiporeporte == 4:
                        personaentrega = request.GET['personaentrega']
                        filtro = filtro & Q(personaentrega_id=personaentrega)

                    if tiporeporte == 5:
                        personarecibe = request.GET['personarecibe']
                        filtro = filtro & Q(personarecibe_id=personarecibe)

                    resultado_busqueda = PrestamoActivosOperaciones.objects.filter(filtro)
                    data['resultado_busqueda'] = resultado_busqueda
                    return conviert_html_to_pdf('operaciones_prestamoactivos/reportes/prestamos.html', {'pagesize': 'A4','data': data,},)
                except Exception as ex:
                    pass

            return HttpResponseRedirect(request.path)
        else:
            try:
                data['title'] = 'Préstamo de activos'
                data['fechaactual'] = datetime.now().date()
                filtros, s, url_vars = Q(status=True), request.GET.get('s', ''), ''
                id_estadoprestamo = 0
                search = None
                id_personaprestamo = 0
                if 'id_estadoprestamo' in request.GET:
                    id_estadoprestamo = int(request.GET['id_estadoprestamo'])
                    if id_estadoprestamo != 0:
                        filtros = filtros & Q(estado=id_estadoprestamo)

                if 'id_personaprestamo' in request.GET:
                    id_personaprestamo = int(request.GET['id_personaprestamo'])

                data['len'] = len = 1  # Number of items pr page


                if s:
                    search = request.GET['s'].strip()
                    ss = search.split(' ')
                    if ss.__len__() == 1:
                        if id_personaprestamo == 0:
                            filtros = filtros & (Q(personaentrega__nombres__icontains=search) |
                                                 Q(personaentrega__apellido1__icontains=search) |
                                                 Q(personaentrega__apellido2__icontains=search) |
                                                 Q(personaentrega__cedula=search) |
                                                 Q(personarecibe__nombres__icontains=search) |
                                                 Q(personarecibe__apellido1__icontains=search) |
                                                 Q(personarecibe__apellido2__icontains=search) |
                                                 Q(personarecibe__cedula=search) |
                                                 Q(activotecnologico__activotecnologico__codigogobierno__icontains=search) |
                                                 Q(activotecnologico__activotecnologico__codigointerno__icontains=search) |
                                                 Q(activotecnologico__activotecnologico__serie__icontains=search) |
                                                 Q(activotecnologico__activotecnologico__modelo__icontains=search) |
                                                 Q(activotecnologico__activotecnologico__catalogo__descripcion__icontains=search) |
                                                 Q(activotecnologico__activotecnologico__descripcion__icontains=search))
                        elif id_personaprestamo == 1:
                                filtros = filtros & (Q(personaentrega__nombres__icontains=search) |
                                                     Q(personaentrega__apellido1__icontains=search) |
                                                     Q(personaentrega__apellido2__icontains=search) |
                                                     Q(personaentrega__cedula=search))
                        elif id_personaprestamo == 2:
                                filtros = filtros & (Q(personarecibe__nombres__icontains=search) |
                                                     Q(personarecibe__apellido1__icontains=search) |
                                                     Q(personarecibe__apellido2__icontains=search) |
                                                     Q(personarecibe__cedula=search))
                        elif id_personaprestamo == 3:
                                filtros = filtros & (Q(activotecnologico__activotecnologico__codigogobierno__icontains=search) |
                                                     Q(activotecnologico__activotecnologico__codigointerno__icontains=search) |
                                                     Q(activotecnologico__activotecnologico__serie__icontains=search) |
                                                     Q(activotecnologico__activotecnologico__modelo__icontains=search) |
                                                     Q(activotecnologico__activotecnologico__catalogo__descripcion__icontains=search) |
                                                       Q(activotecnologico__activotecnologico__descripcion__icontains=search))
                    else:
                        if id_personaprestamo == 0:
                            filtros = filtros & (Q(personaentrega__nombres__icontains=search) |
                                                 (Q(personaentrega__apellido1__icontains=ss[0]) &
                                                 Q(personaentrega__apellido2__icontains=ss[1])) |
                                                 Q(personarecibe__nombres__icontains=search) |
                                                 (Q(personarecibe__apellido1__icontains=ss[0]) |
                                                 Q(personarecibe__apellido2__icontains=ss[1])) |
                                                 Q(activotecnologico__activotecnologico__descripcion__icontains=search) |
                                                 Q(activotecnologico__activotecnologico__catalogo__descripcion__icontains=search))
                        elif id_personaprestamo == 1:
                                filtros = filtros & (Q(personaentrega__nombres__icontains=search) |
                                                     (Q(personaentrega__apellido1__icontains=ss[0]) &
                                                     Q(personaentrega__apellido2__icontains=ss[1])))
                        elif id_personaprestamo == 2:
                                filtros = filtros & (Q(personarecibe__nombres__icontains=search) |
                                                     (Q(personarecibe__apellido1__icontains=ss[0]) &
                                                     Q(personarecibe__apellido2__icontains=ss[1])))
                        elif id_personaprestamo == 3:
                                filtros = filtros & (Q(activotecnologico__activotecnologico__descripcion__icontains=search) |
                                                     Q(activotecnologico__activotecnologico__catalogo__descripcion__icontains=search) |
                                                     Q(activotecnologico__activotecnologico__serie__icontains=ss) |
                                                     Q(activotecnologico__activotecnologico__modelo__icontains=ss))

                    data['s'] = f"{s}"
                    url_vars += f"&s={s}"

                if s == '':
                    if id_personaprestamo == 0:
                        filtros = Q(status=True)
                        if id_estadoprestamo != 0:
                            filtros = filtros & Q(estado=id_estadoprestamo)

                resultados = PrestamoActivosOperaciones.objects.filter(filtros).order_by('-id')

                paging = MiPaginador(resultados, 50)
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
                data['prestamoactivosoperaciones'] = page.object_list
                data['url_vars'] = url_vars
                data['id_estadoprestamo'] = id_estadoprestamo
                data['id_personaprestamo'] = id_personaprestamo
                return render(request, "operaciones_prestamoactivos/view.html", data)
            except Exception as ex:
                pass
