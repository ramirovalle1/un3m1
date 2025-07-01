# -*- coding: latin-1 -*-
import json
from decimal import Decimal
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.db.models import Q
from django.http import HttpResponseRedirect, JsonResponse
from django.shortcuts import render
from django.template import Context
from django.template.loader import get_template
from decorators import secure_module, last_access
from datetime import *
from sga.commonviews import adduserdata
from sga.funciones import MiPaginador, proximafecha, convertir_fecha, log
from sga.models import DetalleConvenioPago, null_to_decimal, ConvenioPagoInscripcion, Periodo


@login_required(redirect_field_name='ret', login_url='/loginsga')
@secure_module
@last_access
@transaction.atomic()
def view(request):
    data = {}
    adduserdata(request, data)
    persona = request.session['persona']
    if request.method == 'POST':
        action = request.POST['action']

        if action == 'detalle_convenio':
            try:
                data['detalle'] = detalle = DetalleConvenioPago.objects.get(pk=int(request.POST['id']))
                data['detalles'] = detalle.conveniopagoinscripcion_set.all()
                template = get_template("alu_conveniopago/detalle.html")
                json_content = template.render(data)
                return JsonResponse({"result": "ok", 'html': json_content})
            except Exception as ex:
                return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

        if action == 'eliminardetalle':
            try:
                detalle = ConvenioPagoInscripcion.objects.get(pk=int(request.POST['id']))
                convenio = detalle.detalleconveniopago
                detalle.delete()
                convenio.meses = convenio.conveniopagoinscripcion_set.count()
                convenio.save(request)
                valorcuota = null_to_decimal(convenio.valor_total_diferido() / convenio.meses, 2)
                convenio.conveniopagoinscripcion_set.update(valorcuota=valorcuota)
                convenio.verifica_diferencia(request)
                log(u"Elimina convenio de pago inscripcion en alumno convenio de pago : %s-[%s] - %s" % (detalle, detalle.id, detalle.detalleconveniopago), request, "del")
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."}),

        if action == 'adicionar':
            try:
                detalle = DetalleConvenioPago.objects.get(pk=int(request.POST['id']))
                fechamaxima = detalle.conveniopagoinscripcion_set.all().order_by('-fecha')[0].fecha
                fechacobrofinal = proximafecha(fechamaxima, 3, detalle.conveniopago.inicioproceso.day)
                cpi = ConvenioPagoInscripcion(detalleconveniopago=detalle,
                                              fecha=fechacobrofinal,
                                              valorcuota=0)
                cpi.save(request)
                detalle.meses += 1
                detalle.save(request)
                valorcuota = null_to_decimal(detalle.valor_total_diferido() / detalle.meses, 2)
                detalle.conveniopagoinscripcion_set.update(valorcuota=valorcuota)
                detalle.verifica_diferencia(request)
                log(u"Adiciona convenio de pago inscripcion en alumno convenio de pago : %s-[%s] - desde el detalle convenio - %s" % (cpi, cpi.id, detalle), request, "add")
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        if action == 'confirmar_convenio':
            try:
                convenio = DetalleConvenioPago.objects.get(id=int(request.POST['id']))
                valorconvenio = convenio.valor_total_diferido()
                datos = json.loads(request.POST['datos'])
                valor = 0
                for d in datos:
                    valor += null_to_decimal(d['valor'], 2)
                if valor != valorconvenio:
                    return JsonResponse({"result": "bad", "mensaje": u"El valor total de las cuotas no es igual al valor del convenio"})
                for d in datos:
                    cpi = ConvenioPagoInscripcion.objects.get(id=int(d['id']))
                    cpi.fecha = convertir_fecha(d['fecha'])
                    cpi.valorcuota = Decimal(d['valor'])
                    cpi.save(request)
                log(
                    u"Confirma convenio de pago inscripcion en alumno convenio de pago : %s-[%s] - valor de convenio: %s" % (convenio, convenio.id, valorconvenio), request, "add")
                return JsonResponse({"result": "ok", "reload": 'False'})
            except Exception as ex:
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos"})

        return JsonResponse({"result": "bad", "mensaje": u"Solicitud Incorrecta."})
    else:
        inscripcion = persona.inscripcion_principal()
        if not Periodo.objects.filter(nombre__icontains='IPEC', id=inscripcion.matricula().nivel.periodo.id):
            return HttpResponseRedirect(u"/?info=No tiene permiso para acceder a este módulo.")
        if DetalleConvenioPago.objects.values('id').filter(inscripcion__persona=persona).exists():
            convenio = DetalleConvenioPago.objects.filter(inscripcion__persona=persona)[0]
            if not convenio.conveniopago.inicioproceso < datetime.now().date() < convenio.conveniopago.finproceso:
                return HttpResponseRedirect(u"/?info=El proceso no está activo.")
        if 'action' in request.GET:
            action = request.GET['action']

            if action == 'edit':
                try:
                    data['title'] = u'Editar Convenio'
                    data['convenio'] = convenio = DetalleConvenioPago.objects.get(pk=request.GET['id'])
                    data['detalles'] = convenio.conveniopagoinscripcion_set.all()
                    return render(request, "alu_conveniopago/edit.html", data)
                except Exception as ex:
                    pass

            if action == 'add':
                try:
                    data['title'] = u'Confirmar adicionar un mes'
                    data['convenio'] = DetalleConvenioPago.objects.get(pk=int(request.GET['id']))
                    return render(request, "alu_conveniopago/adicionar.html", data)
                except:
                    pass

            if action == 'eliminardetalle':
                try:
                    data['title'] = u'Confirmar eliminar mes'
                    data['convenio'] = convenio = ConvenioPagoInscripcion.objects.get(pk=int(request.GET['id']))
                    return render(request, "alu_conveniopago/eliminar.html", data)
                except:
                    pass

            return HttpResponseRedirect(request.path)
        else:
            data['title'] = u'Convenios de Pago'
            search = None
            ids = None
            if 's' in request.GET:
                search = request.GET['s']
                convenios = DetalleConvenioPago.objects.filter(Q(meses__icontains=search), inscripcion__persona=persona).distinct()
            elif 'id' in request.GET:
                ids = request.GET['id']
                convenios = DetalleConvenioPago.objects.filter(id=ids, inscripcion__persona=persona)
            else:
                convenios = DetalleConvenioPago.objects.filter(inscripcion__persona=persona)
            paging = MiPaginador(convenios, 25)
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
            data['ids'] = ids if ids else ""
            data['convenios'] = page.object_list
            return render(request, "alu_conveniopago/view.html", data)