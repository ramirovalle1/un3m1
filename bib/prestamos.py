# -*- coding: latin-1 -*-
from datetime import datetime
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.db.models import Q
from django.http import HttpResponseRedirect, JsonResponse
from django.shortcuts import render
from bib.models import PrestamoDocumento, ReservaDocumento
from decorators import secure_module
from settings import DOCUMENTOS_COLECCION
from sga.commonviews import adduserdata
from sga.forms import ExtenderPrestamoForm
from sga.funciones import MiPaginador, log, puede_realizar_accion


@login_required(redirect_field_name='ret', login_url='/loginsga')
@secure_module
@transaction.atomic()
def view(request):
    data = {}
    adduserdata(request, data)
    persona = request.session['persona']
    if request.method == 'POST':
        action = request.POST['action']

        if action == 'anularreserva':
            try:
                data['title'] = u'Anular reserva'
                reserva = ReservaDocumento.objects.get(pk=request.POST['id'])
                reserva.anulado = True
                reserva.save(request)
                log(u'Anulo reserva de documento: %s' % reserva, request, "del")
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        if action == 'extender':
            try:
                prestamo = PrestamoDocumento.objects.get(pk=request.POST['id'])
                f = ExtenderPrestamoForm(request.POST)
                if f.is_valid():
                    prestamo.tiempo += prestamo.tiempo_pasado_dias() * 24 + prestamo.tiempo_pasado_horas() + f.cleaned_data['horas']
                    prestamo.save(request)
                    log(u'Extendio prestamo de documento: %s' % prestamo, request, "edit")
                    return JsonResponse({"result": "ok"})
                else:
                     raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        return JsonResponse({"result": "bad", "mensaje": u"Solicitud Incorrecta."})
    else:
        if 'action' in request.GET:
            action = request.GET['action']

            if action == 'recibir':
                try:
                    puede_realizar_accion(request, 'sga.puede_modificar_prestamos_biblioteca')
                    prestamo = PrestamoDocumento.objects.get(pk=request.GET['id'])
                    prestamo.responsablerecibido = request.session['persona']
                    prestamo.recibido = True
                    prestamo.fecharecibido = datetime.now().date()
                    prestamo.horarecibido = datetime.now().time()
                    prestamo.save(request)
                    log(u'Recibio documento de prestamo: %s' % prestamo, request, "edit")
                    return HttpResponseRedirect(request.path)
                except Exception as ex:
                    pass

            elif action == 'reservas':
                try:
                    puede_realizar_accion(request, 'sga.puede_modificar_prestamos_biblioteca')
                    data['title'] = u'Reservas de libros'
                    reservas = ReservaDocumento.objects.filter(entregado=False, anulado=False, limitereserva__gte=datetime.now())
                    data['reservas'] = reservas
                    return render(request, "biblioteca/reservas.html", data)
                except Exception as ex:
                    pass

            elif action == 'extender':
                try:
                    puede_realizar_accion(request, 'sga.puede_modificar_prestamos_biblioteca')
                    data['title'] = u'Extender prestamo'
                    prestamo = PrestamoDocumento.objects.get(pk=request.GET['id'])
                    data['form'] = ExtenderPrestamoForm(initial={"horas": 1})
                    data['prestamo'] = prestamo
                    return render(request, "biblioteca/extender.html", data)
                except Exception as ex:
                    pass

            elif action == 'anularreserva':
                try:
                    puede_realizar_accion(request, 'sga.puede_modificar_prestamos_biblioteca')
                    data['title'] = u'Anular reserva'
                    data['reserva'] = ReservaDocumento.objects.get(pk=request.GET['id'])
                    return render(request, "biblioteca/anularreserva.html", data)
                except Exception as ex:
                    pass

            return HttpResponseRedirect(request.path)
        else:
            data['title'] = u'Prestamo de documentos'
            search = None
            if 's' in request.GET:
                search = request.GET['s']
            if search:
                prestamos = PrestamoDocumento.objects.filter(Q(documento__codigo__icontains=search) |
                                                             Q(documento__nombre__icontains=search) |
                                                             Q(persona__nombres__icontains=search) |
                                                             Q(persona__apellido1__icontains=search) |
                                                             Q(persona__apellido2__icontains=search)).order_by('recibido', 'fechaentrega')
            else:
                prestamos = PrestamoDocumento.objects.all().order_by('recibido', 'fechaentrega')
            paging = MiPaginador(prestamos, 25)
            p = 1
            try:
                if 'page' in request.GET:
                    p = int(request.GET['page'])
                page = paging.page(p)
            except Exception as ex:
                page = paging.page(p)
            data['paging'] = paging
            data['rangospaging'] = paging.rangos_paginado(p)
            data['page'] = page
            data['search'] = search if search else ""
            data['prestamos'] = page.object_list
            data['persona'] = request.session['persona']
            data['coleccion'] = DOCUMENTOS_COLECCION
            data['prestamos_hoy'] = PrestamoDocumento.objects.filter(fechaentrega=datetime.now().date()).count()
            data['prestamos_activos'] = PrestamoDocumento.objects.filter(recibido=False).count()
            data['prestamos_totales'] = PrestamoDocumento.objects.all().count()
            data['prestamos_entregados'] = PrestamoDocumento.objects.filter(responsableentrega=data['persona']).count()
            return render(request, "biblioteca/prestamos.html", data)
